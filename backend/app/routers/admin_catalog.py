"""Subject and class catalogue. Administrator only."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.schemas.catalog import (
    ClassCreate,
    ClassRead,
    ClassUpdate,
    ClassWithCount,
    SubjectCreate,
    SubjectRead,
    SubjectUpdate,
)
from app.schemas.people import StatusUpdate
from app.services.catalog_service import CatalogService

router = APIRouter(
    prefix="/admin",
    tags=["Administration - Catalogue"],
    dependencies=[Depends(require_admin)],
)


# ------------------------------------------------------------- subjects


@router.get("/subjects", response_model=List[SubjectRead], summary="List subjects")
def list_subjects(
    search: Optional[str] = Query(default=None),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    return CatalogService(db).list_subjects(search=search, include_inactive=include_inactive)


@router.post(
    "/subjects",
    response_model=SubjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a subject",
)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    subject, error = CatalogService(db).create_subject(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return subject


@router.put("/subjects/{subject_id}", response_model=SubjectRead, summary="Edit a subject")
def update_subject(subject_id: int, payload: SubjectUpdate, db: Session = Depends(get_db)):
    service = CatalogService(db)
    subject = service.get_subject(subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    updated, error = service.update_subject(subject, payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return updated


@router.get(
    "/subjects/{subject_id}/usage",
    summary="How much history a subject carries",
)
def subject_usage(subject_id: int, db: Session = Depends(get_db)):
    """Shown in the confirmation dialog before a subject is deactivated."""
    service = CatalogService(db)
    if service.get_subject(subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")
    return service.subject_usage(subject_id)


@router.patch(
    "/subjects/{subject_id}/status",
    response_model=SubjectRead,
    summary="Activate or deactivate a subject",
)
def set_subject_status(
    subject_id: int, payload: StatusUpdate, db: Session = Depends(get_db)
):
    """Subjects are retired, never deleted.

    Results and enrollment history reference the subject, so removing the row
    would take that history with it.
    """
    service = CatalogService(db)
    subject = service.get_subject(subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")
    return service.set_subject_active(subject, payload.is_active)


# -------------------------------------------------------------- classes


@router.get("/classes", response_model=List[ClassWithCount], summary="List classes")
def list_classes(
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    rows = CatalogService(db).list_classes(include_inactive=include_inactive)
    return [
        ClassWithCount(**ClassRead.model_validate(school_class).model_dump(), student_count=count)
        for school_class, count in rows
    ]


@router.post(
    "/classes",
    response_model=ClassRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a class",
)
def create_class(payload: ClassCreate, db: Session = Depends(get_db)):
    """Class names are free text. Nothing is hard-coded or pre-seeded."""
    school_class, error = CatalogService(db).create_class(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return school_class


@router.put("/classes/{class_id}", response_model=ClassRead, summary="Edit a class")
def update_class(class_id: int, payload: ClassUpdate, db: Session = Depends(get_db)):
    service = CatalogService(db)
    school_class = service.get_class(class_id)
    if school_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found.")

    updated, error = service.update_class(school_class, payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return updated


@router.patch(
    "/classes/{class_id}/status",
    response_model=ClassRead,
    summary="Activate or deactivate a class",
)
def set_class_status(class_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    service = CatalogService(db)
    school_class = service.get_class(class_id)
    if school_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found.")

    if not payload.is_active and service.class_student_count(class_id) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This class still has students in it. Move them to another class "
                "before deactivating it."
            ),
        )

    updated, error = service.update_class(school_class, ClassUpdate(is_active=payload.is_active))
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return updated
