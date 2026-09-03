"""What a student can see of their own results. Student role only."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import require_student
from app.models.student import Student
from app.models.user import User
from app.schemas.student_view import (
    StudentExaminationResults,
    StudentHistory,
    StudentResultsResponse,
)
from app.services import csv_export_service, export_service, report_access
from app.services.results_engine import ResultsEngine
from app.services.school_service import SchoolService
from app.services.student_result_service import StudentResultService

router = APIRouter(prefix="/student", tags=["Student"])


def _profile(user: User) -> Student:
    """The student record behind the signed-in account.

    Everything here is scoped to this record, so there is no student id in any
    path or query: one student cannot ask for another student results by
    changing a number in the URL.
    """
    if user.student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No student record is linked to this account.",
        )
    return user.student


@router.get(
    "/results",
    response_model=StudentResultsResponse,
    summary="My published results",
)
def my_results(
    user: User = Depends(require_student), db: Session = Depends(get_db)
) -> StudentResultsResponse:
    """Every result the school has published for this student.

    Unpublished examinations are named but carry no marks. Results published
    in earlier terms stay here permanently.
    """
    return StudentResultService(db).results_for(_profile(user))


@router.get(
    "/results/{examination_id}",
    response_model=StudentExaminationResults,
    summary="My results for one examination",
)
def my_examination_results(
    examination_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> StudentExaminationResults:
    """One published examination.

    An examination that is not published returns 404 rather than 403, so
    probing ids cannot reveal that unpublished results exist.
    """
    entry = StudentResultService(db).published_examination_for(
        _profile(user), examination_id
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published results are available for that examination.",
        )
    return entry


@router.get(
    "/history",
    response_model=StudentHistory,
    summary="My results history",
)
def my_history(
    user: User = Depends(require_student), db: Session = Depends(get_db)
) -> StudentHistory:
    """Every examination on this student's record, published or not.

    An unpublished entry appears by name so the student knows the school has
    an examination for them, and carries no mark, grade or average.
    """
    return StudentResultService(db).history_for(_profile(user))


def _published_or_404(db: Session, user: User, examination_id: int):
    """Resolve one published examination for the signed-in student.

    Both "not yours" and "not published" produce the same 404 as "does not
    exist", so no id can be used to learn that results exist elsewhere.
    """
    student = _profile(user)
    entry = StudentResultService(db).published_examination_for(student, examination_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published results are available for that examination.",
        )
    return student, entry


def _school(db: Session):
    record = SchoolService(db).get_or_create(settings.SCHOOL_NAME)
    logo = None
    if record.logo_path:
        candidate = Path(settings.UPLOAD_DIR) / record.logo_path
        # SVG renders in a browser but cannot be embedded by the PDF writer.
        if candidate.exists() and candidate.suffix.lower() != ".svg":
            logo = str(candidate)
    return record, logo


@router.get(
    "/results/{examination_id}/export.csv",
    summary="Download my results as CSV",
    response_class=Response,
)
def export_my_results_csv(
    examination_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> Response:
    """This student's own results for one published examination.

    Generated from the results table, so any correction the school has made
    since the marks were uploaded is reflected here.
    """
    student, _entry = _published_or_404(db, user, examination_id)

    results = ResultsEngine(db).for_student(student.id, examination_id)
    school, _logo = report_access.school_and_logo(db)

    body = csv_export_service.write_csv(results)
    term, _scope = csv_export_service.term_and_scope(results)
    filename = csv_export_service.csv_filename(
        school.school_name, term, student.student_number
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/results/{examination_id}/export.pdf",
    summary="Download my statement of results",
    response_class=Response,
)
def export_my_results_pdf(
    examination_id: int,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> Response:
    """The school report card, on the school's own letterhead.

    Generated by the same engine an administrator uses; what differs is the
    scope, which for a student is their own published results and nothing else.
    """
    student = _profile(user)
    card = report_access.for_student(db, student, examination_id)
    body = report_access.render(db, card)

    filename = export_service.safe_filename(
        student.student_number, card.examination_name, "report-card"
    ) + ".pdf"
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
