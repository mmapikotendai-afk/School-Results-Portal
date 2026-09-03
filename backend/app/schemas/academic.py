"""Schemas for academic years, terms, examinations and publication."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ExaminationStatus, SubmissionStatus


def _check_range(start: Optional[date], end: Optional[date]) -> None:
    if start and end and end < start:
        raise ValueError("The end date must fall on or after the start date.")


# --------------------------------------------------------- academic years


class AcademicYearBase(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _dates(self):
        _check_range(self.start_date, self.end_date)
        return self


class AcademicYearCreate(AcademicYearBase):
    is_active: bool = False


class AcademicYearUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def _dates(self):
        _check_range(self.start_date, self.end_date)
        return self


class AcademicYearRead(AcademicYearBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    term_count: int = 0


# ------------------------------------------------------------------ terms


class TermBase(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _dates(self):
        _check_range(self.start_date, self.end_date)
        return self


class TermCreate(TermBase):
    academic_year_id: int
    is_active: bool = False


class TermUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def _dates(self):
        _check_range(self.start_date, self.end_date)
        return self


class TermRead(TermBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    academic_year_name: Optional[str] = None
    is_active: bool
    examination_count: int = 0


# ----------------------------------------------------------- examinations


class ExaminationBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    submission_deadline: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()


class ExaminationCreate(ExaminationBase):
    term_id: int


class ExaminationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    submission_deadline: Optional[datetime] = None


class ExaminationStatusUpdate(BaseModel):
    """Move an examination along its lifecycle.

    Only the transitions listed in academic_service.ALLOWED_TRANSITIONS are
    accepted, so results cannot be published straight out of DRAFT.
    """

    status: ExaminationStatus


class ExaminationRead(ExaminationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_id: int
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    status: ExaminationStatus
    published_at: Optional[datetime] = None
    created_at: datetime

    # Submission tracking rollup.
    submission_total: int = 0
    submission_done: int = 0
    submission_pending: int = 0
    submission_overdue: int = 0
    result_count: int = 0
    allowed_transitions: List[ExaminationStatus] = Field(default_factory=list)

    # True when every required submission is in. A signal only: closing
    # submissions and publishing both remain deliberate acts.
    all_required_submitted: bool = False
    published_by: Optional[str] = None


class SubmissionRow(BaseModel):
    """One teacher-and-subject submission for an examination."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    teacher_id: int
    teacher_name: str
    employee_number: str
    subject_id: int
    subject_name: str
    subject_code: str
    status: SubmissionStatus
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    expected_count: int = 0
    submitted_count: int = 0
    is_overdue: bool = False


class MissingSubmission(BaseModel):
    """A required submission that has not been delivered."""

    submission_id: int
    subject_id: int
    subject_name: str
    teacher_id: int
    teacher_name: str
    status: SubmissionStatus
    submitted_count: int = 0
    expected_count: int = 0


class PublicationSummary(BaseModel):
    """What publishing this examination would release, and what is holding it up."""

    examination_id: int
    examination_name: str
    status: ExaminationStatus
    result_count: int
    student_count: int
    subject_count: int
    submissions_outstanding: int
    can_publish: bool
    blocking_reason: Optional[str] = None

    # Named individually, so an administrator knows exactly who to chase
    # rather than only how many are outstanding.
    missing_submissions: List[MissingSubmission] = Field(default_factory=list)

    published_at: Optional[datetime] = None
    published_by: Optional[str] = None
