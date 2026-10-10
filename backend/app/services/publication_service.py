"""Freeze report context, while keeping audited mark corrections live.

These functions flush but never commit; publication and its contexts must be
saved in the same transaction. Backfilling captures only information still
available today, never guesses an overwritten historical class assignment.
"""

from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.enrollment import StudentSubject
from app.models.enums import EducationLevel, EnrollmentStatus, ExaminationStatus
from app.models.examination import Examination
from app.models.grade_band import GradeBand
from app.models.published_report import PublishedReport
from app.models.result import Result
from app.models.school_settings import SchoolSettings
from app.models.student import Student
from app.models.subject import Subject
from app.services.grading_service import DEFAULT_BANDS


def grading_bands(db: Session, level: EducationLevel) -> list[dict]:
    rows = db.query(GradeBand).filter(GradeBand.level == level).order_by(
        GradeBand.min_marks.desc()
    ).all()
    if rows:
        return [{"minimum": str(b.min_marks), "grade": b.grade, "remark": b.remark}
                for b in rows]
    return [{"minimum": str(m), "grade": g, "remark": r}
            for m, g, r, _ in DEFAULT_BANDS[level]]


def grade_from_context(marks: Decimal, context: dict) -> tuple[str, str]:
    bands = context["grading_bands"]
    for band in bands:
        if marks >= Decimal(band["minimum"]):
            return band["grade"], band["remark"]
    return bands[-1]["grade"], bands[-1]["remark"]


def published_context(
    db: Session, exam: Examination, student_id: int
) -> PublishedReport | None:
    if exam.status != ExaminationStatus.PUBLISHED:
        return None
    return db.get(PublishedReport, (exam.id, student_id))


def capture_reports(db: Session, exam: Examination) -> int:
    """Capture an examination once. Never extend a published cohort on deploy."""
    if exam.term is None:
        return 0
    db.flush()
    existing = db.query(PublishedReport.student_id).filter(
        PublishedReport.examination_id == exam.id
    ).first()
    # Publication is atomic, so one existing context means this examination
    # was already captured. New enrollments must not enter its old cohort.
    if existing is not None:
        return 0
    enrollments = db.query(StudentSubject).filter(
        StudentSubject.academic_year_id == exam.term.academic_year_id,
        StudentSubject.status == EnrollmentStatus.ACTIVE,
    ).all()
    enrolled: dict[int, set[int]] = {}
    for row in enrollments:
        enrolled.setdefault(row.student_id, set()).add(row.subject_id)
    marked: dict[int, set[int]] = {}
    for row in db.query(Result.student_id, Result.subject_id).filter(
        Result.examination_id == exam.id
    ):
        marked.setdefault(row.student_id, set()).add(row.subject_id)
    ids = enrolled.keys() | marked.keys()
    if not ids:
        return 0
    subjects = {s.id: s for s in db.query(Subject).all()}
    school = db.query(SchoolSettings).order_by(SchoolSettings.id).first()
    show_blanks = bool(school and school.report_unenrolled == "blank")
    scales = {level: grading_bands(db, level) for level in EducationLevel}
    students = db.query(Student).options(
        joinedload(Student.school_class), joinedload(Student.user)
    ).filter(Student.id.in_(ids)).all()
    for student in students:
        studied = enrolled.get(student.id, set()) | marked.get(student.id, set())
        visible = studied | ({s.id for s in subjects.values() if s.is_active}
                             if show_blanks else set())
        from app.services.enrollment_context import student_enrollment_for
        enrollment = student_enrollment_for(db, student.id, exam.term.academic_year_id)
        level = enrollment.academic_level if enrollment else (
            student.school_class.level if student.school_class else EducationLevel.O_LEVEL
        )
        db.add(PublishedReport(
            examination_id=exam.id,
            student_id=student.id,
            class_id=enrollment.class_id if enrollment else student.class_id,
            rank_eligible=bool(student.user.is_active and enrolled.get(student.id)),
            context={
                "student_number": student.student_number,
                "student_name": student.full_name,
                "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else None,
                "gender": student.gender.value if student.gender else None,
                "class_name": enrollment.class_name_snapshot if enrollment else (
                    student.school_class.name if student.school_class else None
                ),
                "form_level": enrollment.form_level.value if enrollment else (
                    student.school_class.form_level.value if student.school_class else None
                ),
                "level": level.value,
                "examination_name": exam.name,
                "term_name": exam.term.name,
                "academic_year_name": exam.term.academic_year.name,
                "grading_bands": scales[level],
                "show_position": school.report_show_position if school else True,
                "subjects": [
                    {"id": sid, "name": subjects[sid].name,
                     "code": subjects[sid].code, "studied": sid in studied}
                    for sid in sorted(visible, key=lambda sid: subjects[sid].name)
                ],
            },
        ))
    db.flush()
    return len(students)


def backfill_reports(db: Session) -> int:
    return sum(capture_reports(db, exam) for exam in db.query(Examination).filter(
        Examination.status == ExaminationStatus.PUBLISHED
    ).all())
