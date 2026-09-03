"""Schemas for what a student is allowed to see of their own results."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import EducationLevel


class StudentResultRow(BaseModel):
    """One published mark in one subject."""

    subject_id: int
    subject_name: str
    subject_code: str
    marks: Decimal
    grade: Optional[str] = None
    remarks: Optional[str] = None


class StudentExaminationResults(BaseModel):
    """One published examination and the student marks in it."""

    examination_id: int
    examination_name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    published_at: Optional[datetime] = None

    results: List[StudentResultRow] = Field(default_factory=list)

    subjects_taken: int = 0
    average: Optional[float] = None
    best_subject: Optional[str] = None


class PendingExamination(BaseModel):
    """An examination in progress, named but with no marks disclosed.

    Deliberately carries no scores, no grades and no counts: telling a student
    a result exists but withholding it is fine, showing any of it is not.
    """

    examination_id: int
    examination_name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    status: str = Field(description="Always a pre-publication status")
    headline: str = "Results Not Yet Published"
    message: str


class HistoryEntry(BaseModel):
    """One examination in the student's history.

    Carries whether it is published, and nothing about the marks unless it is.
    An unpublished entry exists on the list so the student can see the school
    has an examination for them, but discloses no figure of any kind.
    """

    examination_id: int
    examination_name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None

    is_published: bool = False
    published_at: Optional[datetime] = None

    # Populated only when published.
    subjects_taken: Optional[int] = None
    average: Optional[float] = None

    # Shown in place of results when it is not.
    headline: Optional[str] = None
    message: Optional[str] = None


class StudentHistory(BaseModel):
    """The results history list on the student dashboard."""

    student_number: str
    full_name: str
    class_name: Optional[str] = None
    level: Optional[EducationLevel] = None

    entries: List[HistoryEntry] = Field(default_factory=list)
    published_count: int = 0
    pending_count: int = 0


class StudentResultsResponse(BaseModel):
    """Everything the student results screen needs, in one request."""

    student_number: str
    full_name: str
    class_name: Optional[str] = None
    level: Optional[EducationLevel] = None

    # Published examinations, newest first. This is the whole record: results
    # published in earlier terms stay here permanently.
    published: List[StudentExaminationResults] = Field(default_factory=list)

    # Named only, never scored.
    in_progress: List[PendingExamination] = Field(default_factory=list)

    enrolled_subjects: List[str] = Field(default_factory=list)
