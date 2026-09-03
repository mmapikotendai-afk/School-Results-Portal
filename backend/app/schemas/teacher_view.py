"""Schemas for the teacher portal."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ExaminationStatus, SubmissionStatus


class TeacherSubjectCard(BaseModel):
    """One assigned subject for the current examination.

    This is the unit the teacher dashboard is built from: a subject, the
    examination it belongs to, when marks are due, and where they stand.
    """

    subject_id: int
    subject_name: str
    subject_code: str

    examination_id: int
    examination_name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    examination_status: ExaminationStatus

    submission_deadline: Optional[datetime] = None
    is_past_deadline: bool = False
    days_remaining: Optional[int] = None

    status: SubmissionStatus
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None

    expected_count: int = 0
    submitted_count: int = 0

    # Whether this teacher may write marks right now, and why not if they cannot.
    can_upload: bool = False
    locked_reason: Optional[str] = None


class TeacherDashboard(BaseModel):
    """Everything the teacher landing screen needs, in one request."""

    teacher_name: str
    employee_number: str

    current_examination: Optional[str] = None
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None

    subjects: List[TeacherSubjectCard] = Field(default_factory=list)

    total_subjects: int = 0
    submitted_subjects: int = 0
    outstanding_subjects: int = 0
    overdue_subjects: int = 0


class TemplateOption(BaseModel):
    """One (examination, subject) pair this teacher may generate a template for.

    The list is built from the teacher's own assignments, so the picker cannot
    offer a subject the server would then refuse.
    """

    examination_id: int
    examination_name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    examination_status: ExaminationStatus
    submission_deadline: Optional[datetime] = None

    subject_id: int
    subject_name: str
    subject_code: str

    enrolled_count: int = 0
    classes: List[str] = Field(default_factory=list)
    can_upload: bool = False


class ClassOption(BaseModel):
    """A class within a subject roll, for narrowing a template."""

    class_id: int
    class_name: str
    student_count: int


class MarkRow(BaseModel):
    """One student mark on the mark sheet."""

    result_id: Optional[int] = None
    student_id: int
    student_number: str
    student_name: str
    marks: Optional[Decimal] = None
    grade: Optional[str] = None
    remarks: Optional[str] = None
    updated_at: Optional[datetime] = None


class MarkSheet(BaseModel):
    """The full roll for one subject and examination, marked or not.

    Every actively enrolled student appears, so a teacher can see at a glance
    who is still missing a mark rather than having to compare two lists.
    """

    examination_id: int
    examination_name: str
    subject_id: int
    subject_name: str
    subject_code: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None

    status: SubmissionStatus
    submission_deadline: Optional[datetime] = None
    can_edit: bool = False
    locked_reason: Optional[str] = None

    rows: List[MarkRow] = Field(default_factory=list)
    expected_count: int = 0
    submitted_count: int = 0


class RowError(BaseModel):
    """One rejected line of an uploaded file."""

    row: int = Field(description="1-based line number in the uploaded file")
    student_number: Optional[str] = None
    message: str


class PreviewRow(BaseModel):
    """One line of the uploaded file, as the preview table shows it.

    The name shown is always the one on record, never the one in the file:
    the number is the identifier, and displaying the file's own name back
    would hide the very mismatch a teacher needs to notice.
    """

    row: int = Field(description="1-based line number in the uploaded file")
    student_number: str
    student_name: str = "Unknown"
    marks: Optional[Decimal] = None
    raw_marks: str = Field(default="", description="The cell exactly as supplied")

    valid: bool = False
    message: str = "Valid"

    # Rule 10: this row would replace a mark already on record.
    is_overwrite: bool = False
    existing_marks: Optional[Decimal] = None


class UploadReport(BaseModel):
    """What an upload did, or would do when validating only.

    Rejected rows never partially apply: a file is either committed whole or
    not at all, so a teacher is never left guessing which half went in.
    """

    validate_only: bool = False
    committed: bool = False

    total_rows: int = 0
    accepted: int = 0
    rejected: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0

    # Rows that would replace a mark already recorded.
    overwrites: int = 0

    # True when the only thing standing between this file and import is the
    # teacher confirming the replacements. Distinct from a validation failure:
    # the data is sound, the decision is not yet made.
    requires_replace_confirmation: bool = False
    replace_allowed: bool = False

    # Every parsed line, valid and invalid, in file order. This is what the
    # preview table renders.
    rows: List[PreviewRow] = Field(default_factory=list)

    errors: List[RowError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # The single flag the Confirm button reads. False whenever anything is
    # wrong, so the decision is made on the server, not in the browser.
    can_import: bool = False

    status: Optional[SubmissionStatus] = None
    submitted_at: Optional[datetime] = None
    detail: str = ""


class MarkUpdate(BaseModel):
    """Correct a single mark from the mark sheet."""

    marks: Decimal = Field(ge=0, le=100)
    remarks: Optional[str] = Field(default=None, max_length=255)
    reason: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Why the mark changed; recorded on the audit trail",
    )

    @field_validator("marks")
    @classmethod
    def _round(cls, value: Decimal) -> Decimal:
        # Two decimal places, matching the column, so 67.499 cannot become 67.5
        # on the way in and 67.50 on the way out.
        return round(value, 2)


class MarkEntry(BaseModel):
    """One mark in a bulk save from the on-screen mark sheet."""

    student_id: int
    marks: Optional[Decimal] = Field(default=None, ge=0, le=100)
    remarks: Optional[str] = Field(default=None, max_length=255)


class MarkSheetSave(BaseModel):
    """Save the mark sheet as edited on screen.

    A row left blank is skipped rather than treated as a zero: not yet marked
    and scored nothing are different things.
    """

    entries: List[MarkEntry] = Field(default_factory=list)
    reason: Optional[str] = Field(default=None, max_length=255)


class ResultReadOnly(BaseModel):
    """A submitted result as the teacher sees it back."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_number: str
    student_name: str
    marks: Decimal
    grade: Optional[str] = None
    remarks: Optional[str] = None
    updated_at: datetime
