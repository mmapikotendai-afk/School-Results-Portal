"""Student management. Administrator only."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.enums import EnrollmentStatus
from app.models.student import Student
from app.schemas.catalog import ClassSummary, SubjectSummary
from app.schemas.common import Page
from app.schemas.people import (
    EnrollmentChange,
    StatusUpdate,
    StudentCreate,
    StudentCreated,
    StudentDetail,
    StudentRead,
    StudentUpdate,
    SubjectSelection,
)
from app.services.academic_service import AcademicService
from app.services.account_service import AccountService
from app.services.people_service import StudentService

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

    student, password, error = service.create(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)

    year_id = service.academic.resolve_year_id(payload.academic_year_id)
    detail = _to_detail(db, student, year_id)
    # Shown once so the office can pass the credentials on; it is never stored
    # in plaintext and cannot be retrieved again.
    return StudentCreated(**detail.model_dump(), initial_password=password)


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
