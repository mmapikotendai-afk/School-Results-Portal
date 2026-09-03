"""The teacher portal. Teacher role only.

Every route that names a subject passes through TeacherPortalService.authorise
first. A teacher who asks for a subject they are not assigned to gets 404, the
same answer as for a subject that does not exist, so the route cannot be used
to enumerate what other teachers hold.
"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_teacher
from app.models.enums import EducationLevel
from app.models.result import Result
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.teacher_view import (
    ClassOption,
    MarkSheet,
    MarkSheetSave,
    MarkUpdate,
    TeacherDashboard,
    TemplateOption,
    UploadReport,
)
from app.services import csv_export_service, export_service, report_access
from app.services.results_engine import ResultsEngine
from app.services.result_import_service import (
    MAX_MARKS,
    ResultImportService,
    apply_single_mark,
)
from app.services.school_service import SchoolService
from app.services.submission_service import SubmissionService
from app.services.teacher_portal_service import NotAuthorised, TeacherPortalService

router = APIRouter(prefix="/teacher", tags=["Teacher"])

# Deliberately identical for "does not exist" and "not yours".
NOT_YOURS = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="That subject is not assigned to you for this examination.",
)


def _teacher(user: User) -> Teacher:
    if user.teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No teacher record is linked to this account.",
        )
    return user.teacher


def _authorise(db: Session, user: User, examination_id: int, subject_id: int):
    """Resolve and authorise, or refuse. Used by every subject-scoped route."""
    service = TeacherPortalService(db)
    try:
        exam, subject, assignment = service.authorise(
            _teacher(user), examination_id, subject_id
        )
    except NotAuthorised:
        raise NOT_YOURS from None
    return service, exam, subject, assignment


def _require_writable(service: TeacherPortalService, exam) -> None:
    """Block writes once the school has taken the examination back."""
    can_write, reason = service.writability(exam)
    if not can_write:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)


# ------------------------------------------------------------- dashboard


@router.get("/dashboard", response_model=TeacherDashboard, summary="My teaching overview")
def dashboard(
    user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> TeacherDashboard:
    """The current examination, my subjects, the deadline and where I stand."""
    return TeacherPortalService(db).dashboard(_teacher(user))


@router.get(
    "/template-options",
    response_model=List[TemplateOption],
    summary="Examinations and subjects I can generate a template for",
)
def template_options(
    user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> List[TemplateOption]:
    """Every (examination, subject) pair this teacher is assigned to.

    Built from the teacher's own assignments, so the picker cannot offer a
    combination the download would then refuse.
    """
    return TeacherPortalService(db).template_options(_teacher(user))


@router.get(
    "/examinations/{examination_id}/subjects/{subject_id}/classes",
    response_model=List[ClassOption],
    summary="Classes represented in this subject roll",
)
def subject_classes(
    examination_id: int,
    subject_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> List[ClassOption]:
    """For narrowing a template when a subject is taught to several classes."""
    service, exam, _subject, _assignment = _authorise(db, user, examination_id, subject_id)
    return service.class_options(subject_id, exam.term.academic_year_id)


# ------------------------------------------------------------ mark sheet


@router.get(
    "/examinations/{examination_id}/subjects/{subject_id}/marksheet",
    response_model=MarkSheet,
    summary="The mark sheet for one of my subjects",
)
def mark_sheet(
    examination_id: int,
    subject_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> MarkSheet:
    """Every enrolled student, with any mark already recorded."""
    service, _exam, _subject, _assignment = _authorise(db, user, examination_id, subject_id)
    return service.mark_sheet(_teacher(user), examination_id, subject_id)


@router.put(
    "/examinations/{examination_id}/subjects/{subject_id}/marksheet",
    response_model=MarkSheet,
    summary="Save the mark sheet",
)
def save_mark_sheet(
    examination_id: int,
    subject_id: int,
    payload: MarkSheetSave,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> MarkSheet:
    """Save marks edited on screen.

    A blank entry is skipped, not stored as zero: not yet marked and scored
    nothing are different things, and only one of them belongs on a report card.
    """
    service, exam, subject, _assignment = _authorise(db, user, examination_id, subject_id)
    _require_writable(service, exam)

    teacher = _teacher(user)
    year_id = exam.term.academic_year_id
    enrolled = {s.id: s for s in service.enrolled_students(subject_id, year_id)}
    existing = {
        r.student_id: r
        for r in db.query(Result).filter(
            Result.examination_id == exam.id, Result.subject_id == subject_id
        )
    }

    wrote = False
    for entry in payload.entries:
        if entry.marks is None:
            continue

        student = enrolled.get(entry.student_id)
        if student is None:
            # Silently ignoring would let a crafted payload mark a student who
            # does not study this subject.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of those students is not enrolled in this subject.",
            )

        level = student.school_class.level if student.school_class else EducationLevel.O_LEVEL
        apply_single_mark(
            db,
            existing.get(entry.student_id),
            entry.student_id,
            exam,
            subject,
            round(entry.marks, 2),
            entry.remarks,
            user,
            level,
            payload.reason,
        )
        wrote = True

    if wrote:
        service.stamp_submission(exam, teacher, subject_id, user.id)
        db.flush()
        SubmissionService(db).recalculate(exam, commit=False)
        db.commit()

    return service.mark_sheet(teacher, examination_id, subject_id)


@router.put(
    "/results/{result_id}",
    response_model=MarkSheet,
    summary="Correct one mark",
)
def update_result(
    result_id: int,
    payload: MarkUpdate,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> MarkSheet:
    """Correct a single mark, recording the change on the audit trail."""
    result = (
        db.query(Result)
        .options(joinedload(Result.student).joinedload(Student.school_class))
        .filter(Result.id == result_id)
        .first()
    )
    if result is None:
        raise NOT_YOURS

    # The result names its own examination and subject, so authorisation is
    # derived from the row rather than from anything the caller supplied.
    service, exam, subject, _assignment = _authorise(
        db, user, result.examination_id, result.subject_id
    )
    _require_writable(service, exam)

    level = (
        result.student.school_class.level
        if result.student and result.student.school_class
        else EducationLevel.O_LEVEL
    )
    apply_single_mark(
        db, result, result.student_id, exam, subject,
        payload.marks, payload.remarks, user, level, payload.reason,
    )
    service.stamp_submission(exam, _teacher(user), subject.id, user.id)
    db.flush()
    SubmissionService(db).recalculate(exam, commit=False)
    db.commit()

    return service.mark_sheet(_teacher(user), exam.id, subject.id)


# ---------------------------------------------------------------- upload


@router.get(
    "/examinations/{examination_id}/subjects/{subject_id}/template.csv",
    summary="Download the CSV template",
    response_class=Response,
)
def download_template(
    examination_id: int,
    subject_id: int,
    class_id: Optional[int] = Query(
        default=None, description="Narrow the roll to a single class"
    ),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Response:
    """A CSV template for one subject and examination.

        student_number,student_name,marks
        STU-001,Tendai Mapiko,
        STU-002,John Doe,

    The roll is exactly those students who are active, actively enrolled in
    this subject, and enrolled for the academic year this examination sits in.
    Optionally narrowed to one class.

    student_number is the matching key and is pre-filled so it returns exactly
    as it went out. The name is informational: it is never read back on upload
    and is never used to identify a student.
    """
    service, exam, subject, _assignment = _authorise(db, user, examination_id, subject_id)
    students = service.enrolled_students(
        subject_id, exam.term.academic_year_id, class_id=class_id
    )

    body = ResultImportService(db).build_template(students, subject, exam)
    # The filename names the subject and examination, so a teacher holding
    # several templates can tell them apart before opening them.
    filename = export_service.safe_filename(subject.code, exam.name, "template") + ".csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/examinations/{examination_id}/subjects/{subject_id}/upload",
    response_model=UploadReport,
    summary="Upload results from a CSV file",
)
async def upload_results(
    examination_id: int,
    subject_id: int,
    file: UploadFile = File(...),
    validate_only: bool = Query(
        default=False, description="Check the file without saving anything"
    ),
    allow_replace: bool = Query(
        default=False,
        description="Confirm that marks already on record may be replaced",
    ),
    reason: Optional[str] = Form(
        default=None, description="Why existing marks are being replaced"
    ),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> UploadReport:
    """Validate a CSV of marks and, unless validating only, save it.

    The file is committed whole or not at all: if any row fails validation,
    nothing is written and the report says which rows to fix.

    A student who already has a mark for this subject and examination is never
    given a second row - the unique key on (student, subject, examination)
    makes that impossible - and is never quietly overwritten either. The
    import stops and reports the clash until allow_replace is passed.
    """
    service, exam, subject, _assignment = _authorise(db, user, examination_id, subject_id)
    _require_writable(service, exam)

    name = (file.filename or "").lower()
    if not name.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a CSV file. Export your spreadsheet as CSV first.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty."
        )

    return ResultImportService(db).process(
        raw,
        _teacher(user),
        user,
        exam,
        subject,
        validate_only=validate_only,
        allow_replace=allow_replace,
        reason=reason,
    )


# ---------------------------------------------------------------- export


@router.get(
    "/examinations/{examination_id}/subjects/{subject_id}/export.csv",
    summary="Download the mark sheet as CSV",
    response_class=Response,
)
def export_csv(
    examination_id: int,
    subject_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Response:
    """Every mark on record for this subject, in the standard export format.

    Generated from the results table, so a mark corrected since the original
    upload is the mark that appears here.
    """
    _service, exam, subject, _assignment = _authorise(db, user, examination_id, subject_id)

    results = ResultsEngine(db).for_subject(subject_id, examination_id)
    school, _logo = report_access.school_and_logo(db)

    body = csv_export_service.write_csv(results)
    filename = csv_export_service.csv_filename(
        school.school_name,
        exam.term.name if exam.term else None,
        subject.code,
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/examinations/{examination_id}/subjects/{subject_id}/export.pdf",
    summary="Download the mark sheet as PDF",
    response_class=Response,
)
def export_pdf(
    examination_id: int,
    subject_id: int,
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Response:
    """A printable mark sheet carrying the school name and crest."""
    service, exam, subject, _assignment = _authorise(db, user, examination_id, subject_id)
    sheet = service.mark_sheet(_teacher(user), examination_id, subject_id)

    school = SchoolService(db).get_or_create(settings.SCHOOL_NAME)
    logo = None
    if school.logo_path:
        candidate = Path(settings.UPLOAD_DIR) / school.logo_path
        # SVG is fine in a browser but not embeddable by the PDF writer.
        if candidate.exists() and candidate.suffix.lower() != ".svg":
            logo = str(candidate)

    body = export_service.marksheet_to_pdf(sheet, school.school_name, logo)
    filename = export_service.safe_filename(subject.code, exam.name, "marksheet") + ".pdf"
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/mark-scale", summary="The mark scale the API enforces")
def mark_scale(user: User = Depends(require_teacher)) -> dict:
    """So the form can show the same limits the server applies.

    Gated like everything else on this router: the router is the teacher
    portal, and an unauthenticated caller has no business reading any of it.
    """
    return {"min": 0, "max": float(MAX_MARKS), "decimals": 2}


@router.get(
    "/students/{student_id}/report-card.pdf",
    summary="A subject statement for one of my students",
    response_class=Response,
)
def student_subject_statement(
    student_id: int,
    examination_id: int = Query(...),
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Response:
    """A report card limited to the subjects this teacher is assigned.

    Built by the same engine as the student and administrator report cards.
    The difference is scope: a teacher sees their own subjects, so this cannot
    expose marks from another teacher's subject, and it is labelled a subject
    statement rather than the school report card.
    """
    card = report_access.for_teacher(db, _teacher(user), student_id, examination_id)
    body = report_access.render(db, card)

    filename = export_service.safe_filename(
        card.student_number, card.examination_name, "subject-statement"
    ) + ".pdf"
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
