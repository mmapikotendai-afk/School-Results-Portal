"""Result retrieval, ranking and the grading scale. Administrator only.

Teachers reach their own subjects through the teacher portal; these routes are
the school-wide view, so they are gated on ADMIN.
"""

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.enrollment import StudentSubject
from app.models.enums import EducationLevel, EnrollmentStatus
from app.models.examination import Examination
from app.models.result import Result, ResultAuditLog
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.results import (
    AuditEntry,
    ExaminationResults,
    GradeBandRead,
    GradingScale,
    GradingScaleUpdate,
    RecalculationResult,
    ResultAudit,
    ResultEdit,
    StudentResultRecord,
    SubjectResult,
    SubjectSummary,
    TeacherResults,
)
from app.services import csv_export_service, export_service, report_access
from app.services.academic_service import AcademicService
from app.services.grading_service import GradingService, validate_scale
from app.services.results_engine import ResultsEngine
from app.services.school_service import SchoolService

router = APIRouter(
    prefix="/admin",
    tags=["Administration - Results"],
    dependencies=[Depends(require_admin)],
)


def _get_exam(db: Session, exam_id: int) -> Examination:
    exam = AcademicService(db).get_examination(exam_id)
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found."
        )
    return exam


def _subject_line(result: Result) -> SubjectResult:
    return SubjectResult(
        result_id=result.id,
        subject_id=result.subject_id,
        subject_name=result.subject.name if result.subject else "",
        subject_code=result.subject.code if result.subject else "",
        marks=result.marks,
        grade=result.grade,
        remarks=result.remarks,
    )


def _enrolled_counts(db: Session, exam: Examination, student_ids: List[int]) -> Dict[int, int]:
    """How many subjects each student is enrolled in for the examination's year.

    Lets the record say whether a set of marks is complete, rather than leaving
    a half-marked student looking the same as a fully marked one.
    """
    if not student_ids or exam.term is None:
        return {}

    from sqlalchemy import func

    rows = (
        db.query(StudentSubject.student_id, func.count(StudentSubject.id))
        .filter(
            StudentSubject.student_id.in_(student_ids),
            StudentSubject.academic_year_id == exam.term.academic_year_id,
            StudentSubject.status == EnrollmentStatus.ACTIVE,
        )
        .group_by(StudentSubject.student_id)
        .all()
    )
    return {sid: count for sid, count in rows}


def _record(student: Student, results: List[Result], enrolled: int) -> StudentResultRecord:
    marks = [r.marks for r in results]
    total = sum(marks, start=type(marks[0])(0)) if marks else 0
    return StudentResultRecord(
        student_id=student.id,
        student_number=student.student_number,
        student_name=student.full_name,
        class_id=student.class_id,
        class_name=student.school_class.name if student.school_class else None,
        level=student.school_class.level if student.school_class else None,
        subjects=sorted(
            (_subject_line(r) for r in results), key=lambda s: s.subject_name
        ),
        subjects_marked=len(results),
        subjects_enrolled=enrolled,
        total_marks=total,
        average=round(float(total) / len(marks), 2) if marks else None,
        is_complete=bool(results) and len(results) >= enrolled,
    )


# --------------------------------------------------------- grading scale


@router.get(
    "/grading-scale",
    response_model=List[GradingScale],
    summary="The configured grading scale",
)
def grading_scale(db: Session = Depends(get_db)) -> List[GradingScale]:
    """The scale each level grades on.

    Seeded from sensible defaults on first read, then entirely the school's to
    change. Nothing in the frontend hard-codes a grade.
    """
    service = GradingService(db)
    return [
        GradingScale(
            level=level,
            bands=[GradeBandRead.model_validate(b) for b in service.bands_for(level)],
        )
        for level in EducationLevel
    ]


@router.put(
    "/grading-scale/{level}",
    response_model=GradingScale,
    summary="Replace the grading scale for a level",
)
def update_grading_scale(
    level: EducationLevel, payload: GradingScaleUpdate, db: Session = Depends(get_db)
) -> GradingScale:
    """Replace a level's scale.

    Validated before it is stored: a scale that skips a symbol, repeats a
    threshold or fails to reach zero would silently misgrade somebody.

    Existing results keep the grades they were given until an examination is
    recalculated, so changing the scale never silently rewrites history.
    """
    bands = [b.model_dump() for b in payload.bands]
    problem = validate_scale(bands)
    if problem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    service = GradingService(db)
    saved = service.replace_scale(level, bands)
    return GradingScale(
        level=level, bands=[GradeBandRead.model_validate(b) for b in saved]
    )


@router.post(
    "/examinations/{exam_id}/recalculate-grades",
    response_model=RecalculationResult,
    summary="Re-apply the current scale to an examination",
)
def recalculate_grades(exam_id: int, db: Session = Depends(get_db)) -> RecalculationResult:
    """Bring an examination's grades back in step with the scale.

    Marks are never touched - only the grade and remark derived from them.
    A remark a teacher wrote themselves is left alone; only remarks the scale
    generated are replaced.
    """
    exam = _get_exam(db, exam_id)
    engine = ResultsEngine(db)

    total = len(engine.for_examination(exam.id))
    changed = engine.recalculate_grades(exam.id)

    return RecalculationResult(
        examination_id=exam.id,
        examination_name=exam.name,
        results_examined=total,
        grades_changed=changed,
        detail=(
            f"{changed} of {total} grades updated to match the current scale."
            if changed
            else f"All {total} grades already match the current scale."
        ),
    )


# ------------------------------------------------------------ retrieval


@router.get(
    "/examinations/{exam_id}/results",
    response_model=ExaminationResults,
    summary="Results for an examination, optionally by class and ranked",
)
def examination_results(
    exam_id: int,
    class_id: Optional[int] = Query(default=None, description="Narrow to one class"),
    ranked: bool = Query(default=True, description="Include positions"),
    db: Session = Depends(get_db),
) -> ExaminationResults:
    """Every student's results in one examination.

    Ranking, when requested, covers only students who are active, enrolled for
    this examination's year, and have at least one mark - and, when a class is
    given, only that class. A student who sat nothing is absent from the
    ranking rather than placed last.
    """
    exam = _get_exam(db, exam_id)
    engine = ResultsEngine(db)

    school_class = None
    if class_id is not None:
        school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if school_class is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Class not found."
            )

    response = ExaminationResults(
        examination_id=exam.id,
        examination_name=exam.name,
        term_name=exam.term.name if exam.term else None,
        academic_year_name=(
            exam.term.academic_year.name if exam.term and exam.term.academic_year else None
        ),
        status=exam.status.value,
        class_id=class_id,
        class_name=school_class.name if school_class else None,
        ranked=ranked,
    )

    aggregates = engine.rank(exam, class_id) if ranked else None
    if aggregates is None:
        grouped: Dict[int, List[Result]] = {}
        students: Dict[int, Student] = {}
        for r in engine.for_examination(exam.id, class_id=class_id):
            grouped.setdefault(r.student_id, []).append(r)
            students[r.student_id] = r.student
        enrolled = _enrolled_counts(db, exam, list(students))
        records = [
            _record(students[sid], rows, enrolled.get(sid, len(rows)))
            for sid, rows in grouped.items()
        ]
        records.sort(key=lambda r: r.student_name)
    else:
        enrolled = _enrolled_counts(db, exam, [a.student.id for a in aggregates])
        records = []
        for entry in aggregates:
            record = _record(
                entry.student, entry.results, enrolled.get(entry.student.id, entry.subjects_marked)
            )
            record.position = entry.position
            record.ranked_out_of = len(aggregates)
            records.append(record)

    response.students = records
    response.student_count = len(records)
    response.result_count = sum(r.subjects_marked for r in records)
    averages = [r.average for r in records if r.average is not None]
    response.average = round(sum(averages) / len(averages), 2) if averages else None
    return response


@router.get(
    "/examinations/{exam_id}/subjects/{subject_id}/results",
    response_model=SubjectSummary,
    summary="How one subject performed",
)
def subject_results(
    exam_id: int, subject_id: int, db: Session = Depends(get_db)
) -> SubjectSummary:
    """Every mark in one subject, with its average, spread and pass rate."""
    exam = _get_exam(db, exam_id)
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    engine = ResultsEngine(db)
    results = engine.for_subject(subject_id, exam_id)
    stats = engine.subject_summary(subject_id, exam_id)

    enrolled = _enrolled_counts(db, exam, [r.student_id for r in results])
    students = [
        _record(r.student, [r], enrolled.get(r.student_id, 1)) for r in results
    ]
    students.sort(key=lambda s: (-(s.average or 0), s.student_name))

    return SubjectSummary(
        subject_id=subject.id,
        subject_name=subject.name,
        subject_code=subject.code,
        examination_id=exam.id,
        examination_name=exam.name,
        students=students,
        **stats,
    )


@router.get(
    "/students/{student_id}/results",
    response_model=List[ExaminationResults],
    summary="One student's results across examinations",
)
def student_results(
    student_id: int,
    academic_year_id: Optional[int] = Query(default=None),
    term_id: Optional[int] = Query(default=None),
    examination_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[ExaminationResults]:
    """A student's full record, newest examination first.

    Each entry carries their position within their own class, which is the
    comparison a report card makes.
    """
    student = (
        db.query(Student)
        .options(joinedload(Student.school_class))
        .filter(Student.id == student_id)
        .first()
    )
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    engine = ResultsEngine(db)
    rows = engine.for_student(student_id, examination_id)

    # Year and term filter by the examination each result belongs to, so all
    # three narrow the same list rather than taking separate code paths.
    if term_id is not None:
        rows = [r for r in rows if r.examination and r.examination.term_id == term_id]
    if academic_year_id is not None:
        rows = [
            r
            for r in rows
            if r.examination
            and r.examination.term
            and r.examination.term.academic_year_id == academic_year_id
        ]

    by_exam: Dict[int, List[Result]] = {}
    for r in rows:
        by_exam.setdefault(r.examination_id, []).append(r)

    out: List[ExaminationResults] = []
    for exam_id, results in by_exam.items():
        exam = results[0].examination
        enrolled = _enrolled_counts(db, exam, [student_id])
        record = _record(student, results, enrolled.get(student_id, len(results)))

        # Position is against their own class, not the whole school.
        position, out_of = engine.position_of(student_id, exam, student.class_id)
        record.position = position
        record.ranked_out_of = out_of

        out.append(
            ExaminationResults(
                examination_id=exam.id,
                examination_name=exam.name,
                term_name=exam.term.name if exam.term else None,
                academic_year_name=(
                    exam.term.academic_year.name
                    if exam.term and exam.term.academic_year
                    else None
                ),
                status=exam.status.value,
                class_id=student.class_id,
                class_name=student.school_class.name if student.school_class else None,
                students=[record],
                student_count=1,
                result_count=record.subjects_marked,
                average=record.average,
                ranked=position is not None,
            )
        )

    out.sort(key=lambda e: e.examination_id, reverse=True)
    return out


@router.get(
    "/teachers/{teacher_id}/results",
    response_model=TeacherResults,
    summary="What one teacher has submitted",
)
def teacher_results(
    teacher_id: int,
    examination_id: int = Query(...),
    db: Session = Depends(get_db),
) -> TeacherResults:
    """Every subject a teacher is responsible for, and how each performed."""
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found.")

    exam = _get_exam(db, examination_id)
    engine = ResultsEngine(db)
    results = engine.for_teacher(teacher_id, examination_id)

    by_subject: Dict[int, List[Result]] = {}
    for r in results:
        by_subject.setdefault(r.subject_id, []).append(r)

    summaries = []
    for subject_id, rows in by_subject.items():
        subject = rows[0].subject
        stats = engine.subject_summary(subject_id, examination_id)
        summaries.append(
            SubjectSummary(
                subject_id=subject_id,
                subject_name=subject.name,
                subject_code=subject.code,
                examination_id=exam.id,
                examination_name=exam.name,
                **stats,
            )
        )
    summaries.sort(key=lambda s: s.subject_name)

    return TeacherResults(
        teacher_id=teacher.id,
        teacher_name=teacher.full_name,
        employee_number=teacher.employee_number,
        examination_id=exam.id,
        examination_name=exam.name,
        subjects=summaries,
        total_results=len(results),
    )


@router.get(
    "/classes/{class_id}/results",
    response_model=ExaminationResults,
    summary="A class result sheet, ranked",
)
def class_results(
    class_id: int,
    examination_id: int = Query(...),
    db: Session = Depends(get_db),
) -> ExaminationResults:
    """One class's results in one examination, ranked within the class.

    A class is the natural comparison group, so this is the ranking that
    appears on a report card.
    """
    return examination_results(
        exam_id=examination_id, class_id=class_id, ranked=True, db=db
    )


# ----------------------------------------------------- editing and audit


def _audit_entry(log: ResultAuditLog) -> AuditEntry:
    """One audit row, joined to the mark it describes."""
    result = log.result
    student = result.student if result else None
    return AuditEntry(
        id=log.id,
        result_id=log.result_id,
        student_id=student.id if student else 0,
        student_number=student.student_number if student else "",
        student_name=student.full_name if student else "",
        subject_name=result.subject.name if result and result.subject else "",
        subject_code=result.subject.code if result and result.subject else "",
        examination_id=result.examination_id if result else 0,
        examination_name=(
            result.examination.name if result and result.examination else ""
        ),
        old_marks=log.old_marks,
        new_marks=log.new_marks,
        old_grade=log.old_grade,
        new_grade=log.new_grade,
        changed_by=log.changed_by.full_name if log.changed_by else None,
        changed_by_role=log.changed_by.role.value if log.changed_by else None,
        reason=log.reason,
        changed_at=log.changed_at,
    )


def _audit_query(db: Session):
    """Audit rows with everything the display needs, in one query."""
    return db.query(ResultAuditLog).options(
        joinedload(ResultAuditLog.changed_by),
        joinedload(ResultAuditLog.result).joinedload(Result.subject),
        joinedload(ResultAuditLog.result).joinedload(Result.student),
        joinedload(ResultAuditLog.result).joinedload(Result.examination),
    )


@router.put(
    "/results/{result_id}",
    response_model=ResultAudit,
    summary="Correct a result",
)
def edit_result(
    result_id: int,
    payload: ResultEdit,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ResultAudit:
    """Correct a mark, recording the change on the audit trail.

    An administrator may correct a result at any point in the examination
    lifecycle, including after publication - schools do find genuine errors
    once results are out. What is not optional is the record of it: the old
    value, the new value, who made the change and why are all written before
    the correction is committed.
    """
    result = (
        db.query(Result)
        .options(
            joinedload(Result.student).joinedload(Student.school_class),
            joinedload(Result.subject),
            joinedload(Result.examination),
        )
        .filter(Result.id == result_id)
        .first()
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found.")

    level = (
        result.student.school_class.level
        if result.student and result.student.school_class
        else EducationLevel.O_LEVEL
    )
    grading = GradingService(db)
    grade, default_remark = grading.grade_for(payload.marks, level)

    if result.marks != payload.marks or result.grade != grade:
        db.add(
            ResultAuditLog(
                result_id=result.id,
                changed_by_id=admin.id,
                old_marks=result.marks,
                new_marks=payload.marks,
                old_grade=result.grade,
                new_grade=grade,
                reason=payload.reason,
            )
        )

    result.marks = payload.marks
    result.grade = grade
    if payload.remarks is not None:
        result.remarks = payload.remarks or default_remark
    db.commit()

    return result_audit(result_id, db)


@router.get(
    "/results/{result_id}/audit",
    response_model=ResultAudit,
    summary="The full history of one mark",
)
def result_audit(result_id: int, db: Session = Depends(get_db)) -> ResultAudit:
    """Where this mark came from and every change made to it since."""
    result = (
        db.query(Result)
        .options(
            joinedload(Result.student),
            joinedload(Result.subject),
            joinedload(Result.examination),
            joinedload(Result.uploaded_by),
        )
        .filter(Result.id == result_id)
        .first()
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found.")

    logs = (
        _audit_query(db)
        .filter(ResultAuditLog.result_id == result_id)
        .order_by(ResultAuditLog.changed_at.desc())
        .all()
    )

    return ResultAudit(
        result_id=result.id,
        student_number=result.student.student_number if result.student else "",
        student_name=result.student.full_name if result.student else "",
        subject_name=result.subject.name if result.subject else "",
        examination_name=result.examination.name if result.examination else "",
        current_marks=result.marks,
        current_grade=result.grade,
        current_remarks=result.remarks,
        uploaded_by=result.uploaded_by.full_name if result.uploaded_by else None,
        created_at=result.created_at,
        updated_at=result.updated_at,
        changes=[_audit_entry(log) for log in logs],
    )


@router.get(
    "/audit",
    response_model=List[AuditEntry],
    summary="Recent corrections across the school",
)
def audit_trail(
    student_id: Optional[int] = Query(default=None),
    examination_id: Optional[int] = Query(default=None),
    subject_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[AuditEntry]:
    """Every correction, newest first, optionally narrowed.

    This is the school-wide view of who has been changing marks - the question
    an audit trail is kept to answer.
    """
    query = _audit_query(db).join(Result, ResultAuditLog.result_id == Result.id)

    if student_id is not None:
        query = query.filter(Result.student_id == student_id)
    if examination_id is not None:
        query = query.filter(Result.examination_id == examination_id)
    if subject_id is not None:
        query = query.filter(Result.subject_id == subject_id)

    logs = query.order_by(ResultAuditLog.changed_at.desc()).limit(limit).all()
    return [_audit_entry(log) for log in logs]


# ------------------------------------------------------------- downloads


def _report_entry(exam: Examination, results: List[Result]):
    """Shape one examination the way the report card renderer expects.

    Built here rather than reusing the student portal builder, because an
    administrator may download a report card before publication - reviewing
    one before releasing it is much of the point.
    """
    from app.schemas.student_view import StudentExaminationResults, StudentResultRow

    marks = [float(r.marks) for r in results]
    best = max(results, key=lambda r: r.marks) if results else None

    return StudentExaminationResults(
        examination_id=exam.id,
        examination_name=exam.name,
        term_name=exam.term.name if exam.term else None,
        academic_year_name=(
            exam.term.academic_year.name if exam.term and exam.term.academic_year else None
        ),
        published_at=exam.published_at,
        results=sorted(
            (
                StudentResultRow(
                    subject_id=r.subject_id,
                    subject_name=r.subject.name,
                    subject_code=r.subject.code,
                    marks=r.marks,
                    grade=r.grade,
                    remarks=r.remarks,
                )
                for r in results
            ),
            key=lambda r: r.subject_name,
        ),
        subjects_taken=len(results),
        average=round(sum(marks) / len(marks), 2) if marks else None,
        best_subject=best.subject.name if best else None,
    )


def _student_and_results(db: Session, student_id: int, exam_id: int):
    student = (
        db.query(Student)
        .options(joinedload(Student.school_class))
        .filter(Student.id == student_id)
        .first()
    )
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    exam = _get_exam(db, exam_id)
    results = ResultsEngine(db).for_student(student_id, exam_id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This student has no results for that examination.",
        )
    return student, exam, results


def _school_branding(db: Session):
    record = SchoolService(db).get_or_create(settings.SCHOOL_NAME)
    logo = None
    if record.logo_path:
        candidate = Path(settings.UPLOAD_DIR) / record.logo_path
        # SVG renders in a browser but cannot be embedded by the PDF writer.
        if candidate.exists() and candidate.suffix.lower() != ".svg":
            logo = str(candidate)
    return record, logo


@router.get(
    "/students/{student_id}/results/{exam_id}/export.csv",
    summary="Download a student's results as CSV",
    response_class=Response,
)
def export_student_csv(
    student_id: int, exam_id: int, db: Session = Depends(get_db)
) -> Response:
    """One student's results for one examination.

    Generated from the results table, so corrections made through the portal
    appear in the download.
    """
    student, exam, results = _student_and_results(db, student_id, exam_id)
    school, _logo = report_access.school_and_logo(db)

    body = csv_export_service.write_csv(results)
    filename = csv_export_service.csv_filename(
        school.school_name,
        exam.term.name if exam.term else None,
        student.student_number,
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/students/{student_id}/results/{exam_id}/report-card.pdf",
    summary="Download a student's report card",
    response_class=Response,
)
def export_student_report_card(
    student_id: int, exam_id: int, db: Session = Depends(get_db)
) -> Response:
    """The school report card, available before publication for review.

    Generated by the same engine the student and teacher routes use. An
    unpublished examination is allowed here and the document marks itself
    PROVISIONAL, so a draft can never be mistaken for a released report.
    """
    card = report_access.for_admin(db, student_id, exam_id)
    body = report_access.render(db, card)

    filename = export_service.safe_filename(
        card.student_number, card.examination_name, "report-card"
    ) + ".pdf"
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/examinations/{exam_id}/export.csv",
    summary="Download a result dataset",
    response_class=Response,
)
def export_examination_csv(
    exam_id: int,
    class_id: Optional[int] = Query(default=None, description="Narrow to one class"),
    subject_id: Optional[int] = Query(default=None, description="Narrow to one subject"),
    db: Session = Depends(get_db),
) -> Response:
    """Every result in an examination, optionally narrowed to a class or subject.

    Read from the results table like every other export, so it always reflects
    the current state of the record rather than what was first uploaded.
    """
    exam = _get_exam(db, exam_id)
    engine = ResultsEngine(db)

    if subject_id is not None:
        results = engine.for_subject(subject_id, exam_id)
        if class_id is not None:
            results = [
                r for r in results if r.student and r.student.class_id == class_id
            ]
    else:
        results = engine.for_examination(exam_id, class_id=class_id)

    scope = None
    if class_id is not None:
        found = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        scope = found.name if found else None
    if subject_id is not None:
        found = db.query(Subject).filter(Subject.id == subject_id).first()
        code = found.code if found else None
        scope = f"{scope}_{code}" if scope and code else (code or scope)

    school, _logo = report_access.school_and_logo(db)
    body = csv_export_service.write_csv(results)
    filename = csv_export_service.csv_filename(
        school.school_name,
        exam.term.name if exam.term else None,
        scope or exam.name,
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/students/{student_id}/results/export.csv",
    summary="Download a student's complete result history",
    response_class=Response,
)
def export_student_history_csv(
    student_id: int,
    academic_year_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    """Every result on a student's record, across examinations."""
    student = (
        db.query(Student)
        .options(joinedload(Student.school_class))
        .filter(Student.id == student_id)
        .first()
    )
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    results = ResultsEngine(db).for_student(student_id)
    if academic_year_id is not None:
        results = [
            r
            for r in results
            if r.examination
            and r.examination.term
            and r.examination.term.academic_year_id == academic_year_id
        ]

    school, _logo = report_access.school_and_logo(db)
    body = csv_export_service.write_csv(results)
    filename = csv_export_service.csv_filename(
        school.school_name, None, student.student_number, suffix="Result_History"
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
