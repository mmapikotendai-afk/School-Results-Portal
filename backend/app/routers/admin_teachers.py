"""Teacher management. Administrator only."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.teacher import Teacher
from app.schemas.catalog import SubjectSummary
from app.schemas.common import Page
from app.schemas.people import (
    EnrollmentChange,
    StatusUpdate,
    SubjectSelection,
    TeacherCreate,
    TeacherCreated,
    TeacherDetail,
    TeacherRead,
    TeacherUpdate,
)
from app.schemas.user import CredentialDelivery
from app.services.academic_service import AcademicService
from app.services.account_service import AccountService
from app.services.people_service import StudentService, TeacherService
from app.services import email_service
from app.services.provisioning_service import ProvisioningService

router = APIRouter(
    prefix="/admin/teachers",
    tags=["Administration - Teachers"],
    dependencies=[Depends(require_admin)],
)


def _to_read(teacher: Teacher, subject_count: int = 0) -> TeacherRead:
    return TeacherRead(
        id=teacher.id,
        employee_number=teacher.employee_number,
        first_name=teacher.first_name,
        last_name=teacher.last_name,
        full_name=teacher.full_name,
        department=teacher.department,
        phone=teacher.phone,
        email=teacher.user.email,
        is_active=teacher.user.is_active,
        subject_count=subject_count,
        created_at=teacher.created_at,
    )


def _to_detail(db: Session, teacher: Teacher, year_id: Optional[int]) -> TeacherDetail:
    service = TeacherService(db)
    subjects = []
    if year_id:
        subjects = [
            SubjectSummary.model_validate(row.subject)
            for row in service.assignments(teacher.id, year_id)
            if row.is_active
        ]

    base = _to_read(teacher, subject_count=len(subjects))
    return TeacherDetail(
        **base.model_dump(),
        subjects=sorted(subjects, key=lambda s: s.name),
        academic_year_id=year_id,
    )


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


def _get(db: Session, teacher_id: int) -> Teacher:
    teacher = TeacherService(db).get(teacher_id)
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found."
        )
    return teacher


@router.get("", response_model=Page[TeacherRead], summary="Search teachers")
def list_teachers(
    search: Optional[str] = Query(default=None, description="Name, employee number or email"),
    include_inactive: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[TeacherRead]:
    service = TeacherService(db)
    rows, total = service.search(
        search=search, include_inactive=include_inactive, page=page, page_size=page_size
    )

    year_id = service.academic.resolve_year_id(None)
    items = [
        _to_read(
            teacher,
            subject_count=len(service.active_subject_ids(teacher.id, year_id))
            if year_id
            else 0,
        )
        for teacher in rows
    ]
    return Page[TeacherRead](items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=TeacherCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create a teacher",
)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)) -> TeacherCreated:
    service = TeacherService(db)

    valid, problem = StudentService(db).valid_subject_ids(payload.subject_ids)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    # Checked before anything is written: an address that cannot receive mail
    # would produce a teacher nobody can ever sign in as, because the only
    # copy of the password goes into the message.
    undeliverable = email_service.verify_deliverable(str(payload.email))
    if undeliverable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"That email address cannot receive mail. {undeliverable}",
        )

    teacher, password, error = service.create(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    kept, result = ProvisioningService(db).deliver_or_discard(teacher.user, password)
    del password
    if not kept:
        # The account was removed again, so the administrator can correct the
        # address and re-submit rather than being left with a stranded row.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The teacher was not added: their credentials could not be emailed. "
                f"{result.error or result.detail}"
            ),
        )

    year_id = service.academic.resolve_year_id(payload.academic_year_id)
    detail = _to_detail(db, teacher, year_id)
    return TeacherCreated(**detail.model_dump(), delivery=_delivery(teacher.user, result))


@router.post(
    "/{teacher_id}/resend-credentials",
    response_model=CredentialDelivery,
    summary="Resend login credentials to a teacher",
)
def resend_teacher_credentials(
    teacher_id: int, db: Session = Depends(get_db)
) -> CredentialDelivery:
    """Issue a fresh temporary password and email it.

    Not a re-send of the original: that password is not recoverable, by design.
    A new one is generated, which invalidates the old one and ends every
    session the account currently holds.
    """
    teacher = _get(db, teacher_id)
    result = ProvisioningService(db).reissue_credentials(teacher.user)
    return _delivery(teacher.user, result)


@router.get("/{teacher_id}", response_model=TeacherDetail, summary="View a teacher")
def get_teacher(
    teacher_id: int,
    academic_year_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> TeacherDetail:
    teacher = _get(db, teacher_id)
    year_id = AcademicService(db).resolve_year_id(academic_year_id)
    return _to_detail(db, teacher, year_id)


@router.put("/{teacher_id}", response_model=TeacherDetail, summary="Edit a teacher")
def update_teacher(
    teacher_id: int, payload: TeacherUpdate, db: Session = Depends(get_db)
) -> TeacherDetail:
    teacher = _get(db, teacher_id)
    updated, error = TeacherService(db).update(teacher, payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    year_id = AcademicService(db).resolve_year_id(None)
    return _to_detail(db, updated, year_id)


@router.patch(
    "/{teacher_id}/status",
    response_model=TeacherDetail,
    summary="Activate or deactivate a teacher",
)
def set_teacher_status(
    teacher_id: int, payload: StatusUpdate, db: Session = Depends(get_db)
) -> TeacherDetail:
    teacher = _get(db, teacher_id)
    AccountService(db).set_active(teacher.user, payload.is_active)
    db.refresh(teacher)

    year_id = AcademicService(db).resolve_year_id(None)
    return _to_detail(db, teacher, year_id)


@router.get(
    "/{teacher_id}/subjects",
    response_model=List[SubjectSummary],
    summary="Subjects a teacher is assigned",
)
def get_teacher_subjects(
    teacher_id: int,
    academic_year_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[SubjectSummary]:
    teacher = _get(db, teacher_id)
    year_id = AcademicService(db).resolve_year_id(academic_year_id)
    if not year_id:
        return []

    return [
        SubjectSummary.model_validate(row.subject)
        for row in TeacherService(db).assignments(teacher.id, year_id)
        if row.is_active
    ]


@router.put(
    "/{teacher_id}/subjects",
    response_model=EnrollmentChange,
    summary="Assign subjects to a teacher",
)
def set_teacher_subjects(
    teacher_id: int, payload: SubjectSelection, db: Session = Depends(get_db)
) -> EnrollmentChange:
    """Replace the subjects a teacher is responsible for in one academic year.

    Unassigning deactivates the assignment rather than deleting it, so the
    submission records that reference it are preserved.
    """
    teacher = _get(db, teacher_id)
    service = TeacherService(db)

    valid, problem = StudentService(db).valid_subject_ids(payload.subject_ids)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    year_id = service.academic.resolve_year_id(payload.academic_year_id)
    if not year_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active academic year. Create one before assigning subjects.",
        )

    sync = service.set_subjects(teacher, payload.subject_ids, year_id)
    db.commit()
    return EnrollmentChange(**sync.as_dict())
