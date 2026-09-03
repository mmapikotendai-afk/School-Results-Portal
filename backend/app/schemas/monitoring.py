"""Schemas for the administrator's submission monitor."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import ExaminationStatus, SubmissionStatus


class MonitorRow(BaseModel):
    """One teacher-and-subject line on the monitor."""

    submission_id: int

    # The teacher responsible for this subject. This never changes because
    # somebody else uploaded on their behalf.
    teacher_id: int
    teacher_name: str
    employee_number: str
    teacher_email: Optional[str] = None
    teacher_phone: Optional[str] = None

    subject_id: int
    subject_name: str
    subject_code: str

    deadline: Optional[datetime] = None
    status: SubmissionStatus

    # First delivery: what lateness is judged against.
    submitted_at: Optional[datetime] = None
    # Most recent upload, which may be a later correction by someone else.
    last_upload_at: Optional[datetime] = None

    # Who actually performed the upload. Usually the responsible teacher; an
    # administrator when they stepped in.
    uploaded_by: Optional[str] = None
    uploaded_by_id: Optional[int] = None
    uploaded_on_behalf: bool = Field(
        default=False,
        description="True when somebody other than the responsible teacher uploaded",
    )
    notes: Optional[str] = None

    expected_count: int = 0
    submitted_count: int = 0
    is_overdue: bool = False


class SubmissionMonitor(BaseModel):
    """The whole monitor for one examination."""

    examination_id: int
    examination_name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    examination_status: ExaminationStatus
    deadline: Optional[datetime] = None
    is_past_deadline: bool = False

    rows: List[MonitorRow] = Field(default_factory=list)

    total_subjects: int = 0
    submitted_subjects: int = 0
    pending_subjects: int = 0
    overdue_subjects: int = 0
    progress: int = Field(default=0, description="Percentage complete, 0-100")

    uploaded_on_behalf_count: int = 0


class MissingStudent(BaseModel):
    """An enrolled student with no mark yet in this subject."""

    student_id: int
    student_number: str
    student_name: str
    class_name: Optional[str] = None


class SubmissionDetail(MonitorRow):
    """One submission opened up: who is responsible, and what is outstanding."""

    examination_id: int
    examination_name: str
    missing_students: List[MissingStudent] = Field(default_factory=list)
    can_upload_on_behalf: bool = False
    blocked_reason: Optional[str] = None
