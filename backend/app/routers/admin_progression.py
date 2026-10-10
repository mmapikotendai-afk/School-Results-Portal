"""Administrator-only student progression and enrollment history routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.student import Student
from app.models.enums import StudentEnrollmentStatus
from app.models.user import User
from app.schemas.progression import (
    ConfirmReturnRequest,
    EnrollmentAuditRead,
    EnrollmentHistoryItem,
    ProgressionPreview,
    ProgressionRequest,
    ProgressionResult,
    ProgressionRosterRow,
)
from app.services.progression_service import ProgressionService


router = APIRouter(
    prefix="/admin/progression",
    tags=["Administration - Progression"],
    dependencies=[Depends(require_admin)],
)


@router.get("/roster", response_model=List[ProgressionRosterRow])
def progression_roster(
    academic_year_id: int,
    class_id: int | None = Query(default=None),
    enrollment_status: StudentEnrollmentStatus | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return ProgressionService(db).roster(academic_year_id, class_id, enrollment_status)


@router.post("/preview", response_model=ProgressionPreview)
def preview_progression(
    payload: ProgressionRequest, db: Session = Depends(get_db)
) -> ProgressionPreview:
    return ProgressionService(db).preview(payload)


@router.post("/confirm", response_model=ProgressionResult)
def confirm_progression(
    payload: ProgressionRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProgressionResult:
    try:
        return ProgressionService(db).apply(payload, admin.id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/confirm-return", response_model=ProgressionResult)
def confirm_return(
    payload: ConfirmReturnRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProgressionResult:
    try:
        return ProgressionService(db).confirm_return(
            payload.student_ids, payload.academic_year_id, admin.id
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/students/{student_id}/history", response_model=List[EnrollmentHistoryItem]
)
def enrollment_history(student_id: int, db: Session = Depends(get_db)):
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return ProgressionService(db).history(student_id)


@router.get(
    "/students/{student_id}/audit", response_model=List[EnrollmentAuditRead]
)
def enrollment_audit(student_id: int, db: Session = Depends(get_db)):
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return ProgressionService(db).audit_history(student_id)
