"""Student management. Administrator only."""

from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.enums import EnrollmentStatus
from app.models.student import Student
from app.schemas.catalog import ClassSummary, SubjectSummary
from app.schemas.common import Page
from app.schemas.people import (
    EnrollmentChange,
    StudentImportReport,
    StudentImportResult,
    StatusUpdate,
    StudentCreate,
    StudentCreated,
    StudentDetail,
    StudentRead,
    StudentUpdate,
    SubjectSelection,
)
from app.schemas.user import CredentialDelivery
from app.services.academic_service import AcademicService
from app.services.account_service import AccountService
from app.services.people_service import StudentService
from app.services import student_import_service
from app.services.student_import_service import StudentImportService
from app.services import email_service
from app.services.provisioning_service import ProvisioningService

router = APIRouter(
    prefix="/admin/students",
    tags=["Administration - Students"],
    dependencies=[Depends(require_admin)],
)


def _to_read(student: Student, subject_count: int = 0) -> StudentRead:
    return StudentRead(
        id=student.id,
        student_number=student.student_number,
        first_name=student.first_name,
        last_name=student.last_name,
        full_name=student.full_name,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        email=student.user.email,
        is_active=student.user.is_active,
        school_class=(
            ClassSummary.model_validate(student.school_class)
            if student.school_class
            else None
        ),
        level=student.level,
        subject_count=subject_count,
        created_at=student.created_at,
    )


def _to_detail(db: Session, student: Student, year_id: Optional[int]) -> StudentDetail:
    """Build the single-student view, splitting current from dropped subjects."""
    service = StudentService(db)
    current, dropped = [], []

    if year_id:
        for row in service.enrollments(student.id, year_id):
            summary = SubjectSummary.model_validate(row.subject)
            (current if row.status == EnrollmentStatus.ACTIVE else dropped).append(summary)

    base = _to_read(student, subject_count=len(current))
    return StudentDetail(
        **base.model_dump(),
        subjects=sorted(current, key=lambda s: s.name),
        dropped_subjects=sorted(dropped, key=lambda s: s.name),
        academic_year_id=year_id,
    )


def _get(db: Session, student_id: int) -> Student:
    student = StudentService(db).get(student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found."
        )
    return student


def _delivery(user, result) -> CredentialDelivery:
    """Turn a delivery attempt into the shape the admin UI reads.

    Carries the address and the outcome. It never carries the password, and
    there is no field it could be put in.
    """
    return CredentialDelivery(
        email=user.email,
        status=result.status,
        sent=result.sent,
        sent_at=user.email_sent_at,
        detail=result.detail,
        can_resend=_has_real_mailbox(user.email),
    )


def _has_real_mailbox(email: str) -> bool:
    """False for a derived sign-in identifier, which routes nowhere."""
    domain = (settings.STUDENT_EMAIL_DOMAIN or "").strip().lower()
    return bool(domain) and not email.strip().lower().endswith(f"@{domain}")


@router.get("", response_model=Page[StudentRead], summary="Search students")
def list_students(
    search: Optional[str] = Query(default=None, description="Name, student number or email"),
    class_id: Optional[int] = Query(default=None),
    include_inactive: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[StudentRead]:
    service = StudentService(db)
    rows, total = service.search(
        search=search,
        class_id=class_id,
        include_inactive=include_inactive,
        page=page,
        page_size=page_size,
    )

    year_id = service.academic.resolve_year_id(None)
    items = [
        _to_read(
            student,
            subject_count=len(service.active_subject_ids(student.id, year_id))
            if year_id
            else 0,
        )
        for student in rows
    ]
    return Page[StudentRead](items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=StudentCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Add a student",
)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)) -> StudentCreated:
    """Create a student, their portal account, and their subject enrollment."""
    service = StudentService(db)

    valid, problem = service.valid_subject_ids(payload.subject_ids)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    # Checked before anything is written: an address that cannot receive mail
    # would produce a student nobody can ever sign in as, because the only
    # copy of the password goes into the message.
    undeliverable = email_service.verify_deliverable(str(payload.email))
    if undeliverable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"That email address cannot receive mail. {undeliverable}",
        )

    student, password, error = service.create(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    kept, result = ProvisioningService(db).deliver_or_discard(student.user, password)
    del password
    if not kept:
        # The account was removed again, so the administrator can correct the
        # address and re-submit rather than being left with a stranded row.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The student was not added: their credentials could not be emailed. "
                f"{result.error or result.detail}"
            ),
        )

    year_id = service.academic.resolve_year_id(payload.academic_year_id)
    detail = _to_detail(db, student, year_id)
    return StudentCreated(**detail.model_dump(), delivery=_delivery(student.user, result))


@router.post(
    "/{student_id}/resend-credentials",
    response_model=CredentialDelivery,
    summary="Resend login credentials to a student",
)
def resend_student_credentials(
    student_id: int, db: Session = Depends(get_db)
) -> CredentialDelivery:
    """Issue a fresh temporary password and email it.

    The previous password stops working immediately, and any session opened
    with it is ended.
    """
    student = _get(db, student_id)
    result = ProvisioningService(db).reissue_credentials(student.user)
    return _delivery(student.user, result)


# ------------------------------------------------- bulk import (CSV)
#
# Declared before the "/{student_id}" routes below: FastAPI matches in order,
# and "/import/template.csv" would otherwise be read as a student id.


def _import_target(db: Session, class_id: int, academic_year_id: Optional[int], subject_ids: List[int]):
    """Resolve the class, year and subjects chosen on screen, or refuse."""
    service = StudentImportService(db)
    school_class, year_id, subject_names, error = service.describe_target(
        class_id, academic_year_id, subject_ids
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return service, school_class, year_id, subject_names


def _parse_subject_ids(raw: Optional[str]) -> List[int]:
    """Subject ids arrive as a comma-separated form field alongside the file."""
    if not raw:
        return []
    try:
        return [int(part) for part in raw.split(",") if part.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The subject selection was not understood.",
        ) from None


@router.get(
    "/import/template.csv",
    summary="Download the bulk student import template",
    response_class=Response,
)
def student_import_template() -> Response:
    """A CSV with the headings the importer expects, and two example rows.

    Deliberately carries no class column: the class is chosen on screen and
    applied to every row, so a stray value in a file cannot put one learner in
    the wrong form.
    """
    body = student_import_service.build_template()
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="student-import-template.csv"'},
    )


@router.post(
    "/import/preview",
    response_model=StudentImportReport,
    summary="Validate a student CSV without creating anything",
)
async def preview_student_import(
    file: UploadFile = File(...),
    class_id: int = Form(...),
    academic_year_id: Optional[int] = Form(default=None),
    subject_ids: Optional[str] = Form(default=None),
    check_deliverable: bool = Form(default=False),
    db: Session = Depends(get_db),
) -> StudentImportReport:
    """Read the file and report on every row. Nothing is written."""
    chosen = _parse_subject_ids(subject_ids)
    service, school_class, year_id, subject_names = _import_target(
        db, class_id, academic_year_id, chosen
    )

    raw = await _read_csv(file)
    return service.validate(
        raw, school_class, year_id, subject_names, check_deliverable=check_deliverable
    )


@router.post(
    "/import",
    response_model=StudentImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Create every student in a validated CSV",
)
async def commit_student_import(
    file: UploadFile = File(...),
    class_id: int = Form(...),
    academic_year_id: Optional[int] = Form(default=None),
    subject_ids: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
) -> StudentImportResult:
    """Validate once more, then create the students, accounts and enrollments.

    Re-validating rather than trusting the preview is the point: the roll can
    change between the two requests, and the file is the only thing the client
    sends back. A file that no longer validates is refused whole.
    """
    chosen = _parse_subject_ids(subject_ids)
    service, school_class, year_id, subject_names = _import_target(
        db, class_id, academic_year_id, chosen
    )

    raw = await _read_csv(file)
    report = service.validate(raw, school_class, year_id, subject_names)
    if not report.can_import:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=report.detail or "That file cannot be imported.",
        )

    return service.commit(report, school_class, year_id, chosen, subject_names)


async def _read_csv(file: UploadFile) -> bytes:
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
    return raw


@router.get("/{student_id}", response_model=StudentDetail, summary="View a student")
def get_student(
    student_id: int,
    academic_year_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> StudentDetail:
    student = _get(db, student_id)
    year_id = AcademicService(db).resolve_year_id(academic_year_id)
    return _to_detail(db, student, year_id)


@router.put("/{student_id}", response_model=StudentDetail, summary="Edit a student")
def update_student(
    student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)
) -> StudentDetail:
    student = _get(db, student_id)
    updated, error = StudentService(db).update(student, payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    year_id = AcademicService(db).resolve_year_id(None)
    return _to_detail(db, updated, year_id)


@router.patch(
    "/{student_id}/status",
    response_model=StudentDetail,
    summary="Activate or deactivate a student",
)
def set_student_status(
    student_id: int, payload: StatusUpdate, db: Session = Depends(get_db)
) -> StudentDetail:
    """Deactivating suspends the account. The record and its history remain."""
    student = _get(db, student_id)
    AccountService(db).set_active(student.user, payload.is_active)
    db.refresh(student)

    year_id = AcademicService(db).resolve_year_id(None)
    return _to_detail(db, student, year_id)


@router.get(
    "/{student_id}/subjects",
    response_model=List[SubjectSummary],
    summary="Subjects a student currently studies",
)
def get_student_subjects(
    student_id: int,
    academic_year_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[SubjectSummary]:
    student = _get(db, student_id)
    year_id = AcademicService(db).resolve_year_id(academic_year_id)
    if not year_id:
        return []

    return [
        SubjectSummary.model_validate(row.subject)
        for row in StudentService(db).enrollments(student.id, year_id)
        if row.status == EnrollmentStatus.ACTIVE
    ]


@router.put(
    "/{student_id}/subjects",
    response_model=EnrollmentChange,
    summary="Set the subjects a student studies",
)
def set_student_subjects(
    student_id: int, payload: SubjectSelection, db: Session = Depends(get_db)
) -> EnrollmentChange:
    """Replace a student subject list for one academic year.

    Subjects removed from the list are marked INACTIVE and stamped with a drop
    date. Nothing is deleted, so past enrollment and any results recorded
    against it stay on the record.
    """
    student = _get(db, student_id)
    service = StudentService(db)

    valid, problem = service.valid_subject_ids(payload.subject_ids)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    year_id = service.academic.resolve_year_id(payload.academic_year_id)
    if not year_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active academic year. Create one before enrolling students.",
        )

    sync = service.set_subjects(student, payload.subject_ids, year_id)
    db.commit()
    return EnrollmentChange(**sync.as_dict())
