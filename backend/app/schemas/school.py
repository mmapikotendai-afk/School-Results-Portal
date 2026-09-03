"""School information and the administrator dashboard."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import ExaminationStatus


class SchoolSettingsUpdate(BaseModel):
    """Branding used on generated report cards.

    The logo is uploaded separately, so logo_path is not settable here.
    """

    # Every field is optional, because the service applies only what was
    # actually sent (model_dump(exclude_unset=True)). Requiring school_name
    # here contradicted that: a caller changing one setting - the report
    # watermark, say, or just the telephone number - was rejected with a 422
    # unless it resent the school name alongside. Omitting a field now leaves
    # it as it was; sending one changes it.
    school_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=40)
    email: Optional[EmailStr] = None
    motto: Optional[str] = Field(default=None, max_length=255)

    # Report card format.
    report_show_position: Optional[bool] = None
    report_unenrolled: Optional[Literal["omit", "blank"]] = None
    report_watermark: Optional[Literal["logo", "name", "none"]] = None

    @field_validator("school_name")
    @classmethod
    def _name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else v


class SchoolSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_name: str
    logo_path: Optional[str] = None
    logo_url: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    motto: Optional[str] = None

    report_show_position: bool = True
    report_unenrolled: str = "omit"
    report_watermark: str = "name"

    updated_at: Optional[datetime] = None


class CurrentExamination(BaseModel):
    """The examination the dashboard is reporting on."""

    id: int
    name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    status: ExaminationStatus
    submission_deadline: Optional[datetime] = None
    is_past_deadline: bool = False


class OutstandingLine(BaseModel):
    """One teacher-and-subject that still owes results."""

    submission_id: int
    teacher_id: int
    teacher_name: str
    subject_id: int
    subject_name: str
    subject_code: str
    deadline: Optional[datetime] = None

    # Whole days past the deadline. Absent while the deadline is still ahead.
    days_overdue: Optional[int] = None
    submitted_count: int = 0
    expected_count: int = 0


class PublicationState(BaseModel):
    """Where the current examination stands, in one sentence.

    Three states, because that is what an administrator glancing at the
    dashboard needs to know: is it out, is it being checked, or are we still
    waiting on teachers.
    """

    state: Literal["published", "awaiting_review", "awaiting_submissions"]
    label: str
    detail: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None


class DashboardStats(BaseModel):
    """Everything the administrator overview needs, in one request."""

    total_students: int = 0
    total_teachers: int = 0
    total_subjects: int = 0
    total_classes: int = 0

    current_examination: Optional[CurrentExamination] = None

    # Submission progress for the current examination.
    submissions_total: int = 0
    submissions_complete: int = 0
    submissions_pending: int = 0
    submissions_overdue: int = 0
    submission_progress: int = Field(default=0, description="Percentage, 0-100")

    # Results across the whole system.
    results_published: int = 0
    results_unpublished: int = 0

    # Who still owes results, named rather than only counted, so the
    # dashboard answers "who do I chase" without a second screen.
    pending_submissions: List[OutstandingLine] = Field(default_factory=list)
    overdue_submissions: List[OutstandingLine] = Field(default_factory=list)

    publication: Optional[PublicationState] = None

    active_year_name: Optional[str] = None
    active_term_name: Optional[str] = None
