"""Academic years, terms, examinations and result publication. Administrator only."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.user import User
from app.models.enums import ExaminationStatus, SubmissionStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.submission import ResultSubmission
from app.schemas.academic import (
    AcademicYearCreate,
    AcademicYearRead,
    AcademicYearUpdate,
    ExaminationCreate,
    ExaminationRead,
    ExaminationStatusUpdate,
    ExaminationUpdate,
    MissingSubmission,
    PublicationSummary,
    SubmissionRow,
    TermCreate,
    TermRead,
    TermUpdate,
)
from app.services.academic_service import AcademicService
from app.services.submission_service import SubmissionService

router = APIRouter(
    prefix="/admin",
    tags=["Administration - Academic"],
    dependencies=[Depends(require_admin)],
)


def _submission_row(row: ResultSubmission) -> SubmissionRow:
    """One monitor row. is_overdue mirrors the OVERDUE status so the client can
    highlight it without having to know the status vocabulary."""
    return SubmissionRow(
        id=row.id,
        teacher_id=row.teacher_id,
        teacher_name=row.teacher.full_name,
        employee_number=row.teacher.employee_number,
        subject_id=row.subject_id,
        subject_name=row.subject.name,
        subject_code=row.subject.code,
        status=row.status,
        submitted_at=row.submitted_at,
        submitted_by=row.submitted_by.full_name if row.submitted_by else None,
        expected_count=row.expected_count,
        submitted_count=row.submitted_count,
        is_overdue=row.status == SubmissionStatus.OVERDUE,
    )


def _term_read(term, examination_count: int = 0) -> TermRead:
    """Build a term row. The year name comes from the relationship, so it has
    to be set explicitly rather than inferred from the column set."""
    return TermRead(
        id=term.id,
        academic_year_id=term.academic_year_id,
        academic_year_name=term.academic_year.name if term.academic_year else None,
        name=term.name,
        start_date=term.start_date,
        end_date=term.end_date,
        is_active=term.is_active,
        examination_count=examination_count,
    )


def _exam_read(service: AcademicService, exam: Examination) -> ExaminationRead:
    rollup = service.submission_rollup(exam.id)
    return ExaminationRead(
        id=exam.id,
        term_id=exam.term_id,
        term_name=exam.term.name if exam.term else None,
        academic_year_name=(
            exam.term.academic_year.name if exam.term and exam.term.academic_year else None
        ),
        name=exam.name,
        submission_deadline=exam.submission_deadline,
        status=exam.status,
        published_at=exam.published_at,
        created_at=exam.created_at,
        submission_total=rollup["total"],
        submission_done=rollup["done"],
        submission_pending=rollup["pending"],
        submission_overdue=rollup["overdue"],
        result_count=service.result_count(exam.id),
        allowed_transitions=service.allowed_transitions(exam),
        all_required_submitted=service.is_ready_to_close(exam),
        published_by=exam.published_by.full_name if exam.published_by else None,
    )


# -------------------------------------------------------- academic years


@router.get("/academic-years", response_model=List[AcademicYearRead], summary="List academic years")
def list_years(db: Session = Depends(get_db)):
    return [
        AcademicYearRead(
            id=year.id,
            name=year.name,
            start_date=year.start_date,
            end_date=year.end_date,
            is_active=year.is_active,
            term_count=count,
        )
        for year, count in AcademicService(db).list_years()
    ]


@router.post(
    "/academic-years",
    response_model=AcademicYearRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an academic year",
)
def create_year(payload: AcademicYearCreate, db: Session = Depends(get_db)):
    year, error = AcademicService(db).create_year(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return AcademicYearRead.model_validate(year)


@router.put(
    "/academic-years/{year_id}",
    response_model=AcademicYearRead,
    summary="Edit an academic year",
)
def update_year(year_id: int, payload: AcademicYearUpdate, db: Session = Depends(get_db)):
    service = AcademicService(db)
    year = service.get_year(year_id)
    if year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found.")

    updated, error = service.update_year(year, payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return AcademicYearRead.model_validate(updated)


@router.post(
    "/academic-years/{year_id}/activate",
    response_model=AcademicYearRead,
    summary="Make this the current academic year",
)
def activate_year(year_id: int, db: Session = Depends(get_db)):
    """Activating one year stands every other year down: exactly one is current."""
    service = AcademicService(db)
    year = service.get_year(year_id)
    if year is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic year not found.")
    return AcademicYearRead.model_validate(service.activate_year(year))


# ------------------------------------------------------------------ terms


@router.get("/terms", response_model=List[TermRead], summary="List terms")
def list_terms(
    academic_year_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    return [
        _term_read(term, count)
        for term, count in AcademicService(db).list_terms(academic_year_id)
    ]


@router.post(
    "/terms",
    response_model=TermRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a term",
)
def create_term(payload: TermCreate, db: Session = Depends(get_db)):
    term, error = AcademicService(db).create_term(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return _term_read(term)


@router.put("/terms/{term_id}", response_model=TermRead, summary="Edit a term")
def update_term(term_id: int, payload: TermUpdate, db: Session = Depends(get_db)):
    service = AcademicService(db)
    term = service.get_term(term_id)
    if term is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found.")

    updated, error = service.update_term(term, payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return _term_read(updated)


@router.post(
    "/terms/{term_id}/activate",
    response_model=TermRead,
    summary="Make this the current term",
)
def activate_term(term_id: int, db: Session = Depends(get_db)):
    service = AcademicService(db)
    term = service.get_term(term_id)
    if term is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found.")
    return _term_read(service.activate_term(term))


# ----------------------------------------------------------- examinations


@router.get("/examinations", response_model=List[ExaminationRead], summary="List examinations")
def list_examinations(
    term_id: Optional[int] = Query(default=None),
    exam_status: Optional[ExaminationStatus] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    service = AcademicService(db)
    return [
        _exam_read(service, exam)
        for exam in service.list_examinations(term_id=term_id, status=exam_status)
    ]


@router.post(
    "/examinations",
    response_model=ExaminationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an examination",
)
def create_examination(payload: ExaminationCreate, db: Session = Depends(get_db)):
    service = AcademicService(db)
    exam, error = service.create_examination(payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return _exam_read(service, service.get_examination(exam.id))


@router.get(
    "/examinations/{exam_id}",
    response_model=ExaminationRead,
    summary="View an examination",
)
def get_examination(exam_id: int, db: Session = Depends(get_db)):
    service = AcademicService(db)
    exam = service.get_examination(exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found.")
    return _exam_read(service, exam)


@router.put(
    "/examinations/{exam_id}",
    response_model=ExaminationRead,
    summary="Edit an examination",
)
def update_examination(
    exam_id: int, payload: ExaminationUpdate, db: Session = Depends(get_db)
):
    service = AcademicService(db)
    exam = service.get_examination(exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found.")

    updated, error = service.update_examination(exam, payload)
    if error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error)
    return _exam_read(service, updated)


@router.patch(
    "/examinations/{exam_id}/status",
    response_model=ExaminationRead,
    summary="Move an examination through its lifecycle",
)
def set_examination_status(
    exam_id: int,
    payload: ExaminationStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Publication happens here.

    Only the transitions in ALLOWED_TRANSITIONS are accepted, so results cannot
    jump from DRAFT straight to PUBLISHED, and an examination with no marks in
    it cannot be published at all.
    """
    service = AcademicService(db)
    exam = service.get_examination(exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found.")

    updated, error = service.set_status(exam, payload.status, acting_user_id=admin.id)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return _exam_read(service, updated)


@router.get(
    "/examinations/{exam_id}/publication",
    response_model=PublicationSummary,
    summary="What publishing this examination would release",
)
def publication_summary(exam_id: int, db: Session = Depends(get_db)):
    """Backs the confirmation dialog, so publishing is never a blind action."""
    service = AcademicService(db)
    exam = service.get_examination(exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found.")

    results = db.query(Result).filter(Result.examination_id == exam_id).all()
    rollup = service.submission_rollup(exam_id)
    can, reason = service.can_publish(exam)
    missing = service.missing_submissions(exam)

    if can and exam.status != ExaminationStatus.PUBLISHED:
        if ExaminationStatus.PUBLISHED not in service.allowed_transitions(exam):
            can = False
            reason = (
                f"An examination that is {exam.status.value} cannot be published yet. "
                "Move it to UNDER_REVIEW first."
            )

    return PublicationSummary(
        examination_id=exam.id,
        examination_name=exam.name,
        status=exam.status,
        result_count=len(results),
        student_count=len({r.student_id for r in results}),
        subject_count=len({r.subject_id for r in results}),
        submissions_outstanding=rollup["pending"],
        can_publish=can,
        blocking_reason=reason,
        missing_submissions=[
            MissingSubmission(
                submission_id=m.id,
                subject_id=m.subject_id,
                subject_name=m.subject.name if m.subject else "",
                teacher_id=m.teacher_id,
                teacher_name=m.teacher.full_name if m.teacher else "",
                status=m.status,
                submitted_count=m.submitted_count,
                expected_count=m.expected_count,
            )
            for m in missing
        ],
        published_at=exam.published_at,
        published_by=exam.published_by.full_name if exam.published_by else None,
    )


@router.get(
    "/examinations/{exam_id}/submissions",
    response_model=List[SubmissionRow],
    summary="Submission tracking for an examination",
)
def examination_submissions(exam_id: int, db: Session = Depends(get_db)):
    """Who owes results for this examination, and who has delivered."""
    service = AcademicService(db)
    exam = service.get_examination(exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found.")

    # Recomputed from enrolment and results before being returned, so a
    # deadline that has just passed shows as OVERDUE without a scheduled job.
    rows = SubmissionService(db).recalculate(exam)

    return [_submission_row(row) for row in rows]


@router.get(
    "/examinations/{exam_id}/outstanding",
    response_model=List[SubmissionRow],
    summary="Teachers who still owe results, worst first",
)
def outstanding_submissions(exam_id: int, db: Session = Depends(get_db)):
    """The chase-up list: overdue first, then partial, then not started."""
    service = AcademicService(db)
    exam = service.get_examination(exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found.")

    return [_submission_row(row) for row in SubmissionService(db).outstanding(exam)]


@router.post(
    "/examinations/{exam_id}/sync-submissions",
    summary="Rebuild submission tracking from current assignments",
)
def sync_submissions(exam_id: int, db: Session = Depends(get_db)):
    """Pick up teacher assignments made after submissions were opened.

    Existing rows are left untouched, so a submission already recorded is never
    reset by running this.
    """
    service = AcademicService(db)
    exam = service.get_examination(exam_id)
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found.")

    created, total = SubmissionService(db).sync(exam)
    return {
        "created": created,
        "total": total,
        "detail": (
            f"Added {created} tracking row{'' if created == 1 else 's'}. "
            f"Now tracking {total} teacher-subject assignment{'' if total == 1 else 's'}."
        ),
    }
