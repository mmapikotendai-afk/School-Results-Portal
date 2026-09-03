"""Schemas for the results engine: retrieval, ranking and the grading scale."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EducationLevel


# ------------------------------------------------------- grading scale


class GradeBandIn(BaseModel):
    """One band of a proposed scale."""

    min_marks: Decimal = Field(ge=0, le=100, description="Inclusive lower bound, as a percentage")
    grade: str = Field(min_length=1, max_length=4)
    remark: str = Field(min_length=1, max_length=80)
    is_pass: bool = True

    @field_validator("grade")
    @classmethod
    def _grade(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("remark")
    @classmethod
    def _remark(cls, v: str) -> str:
        return v.strip()


class GradeBandRead(GradeBandIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: EducationLevel


class GradingScale(BaseModel):
    """The whole scale for one level, highest band first."""

    level: EducationLevel
    bands: List[GradeBandRead] = Field(default_factory=list)


class GradingScaleUpdate(BaseModel):
    """Replace a level's scale wholesale.

    Sent whole rather than patched band by band, so the scale can never be
    left with a gap or an overlap between two edits.
    """

    bands: List[GradeBandIn] = Field(min_length=1)


class RecalculationResult(BaseModel):
    examination_id: int
    examination_name: str
    results_examined: int
    grades_changed: int
    detail: str


# ------------------------------------------------------------ retrieval


class SubjectResult(BaseModel):
    """One subject line on a result record."""

    result_id: int
    subject_id: int
    subject_name: str
    subject_code: str
    marks: Decimal
    grade: Optional[str] = None
    remarks: Optional[str] = None


class StudentResultRecord(BaseModel):
    """One student's results in one examination, with their standing."""

    student_id: int
    student_number: str
    student_name: str
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    level: Optional[EducationLevel] = None

    subjects: List[SubjectResult] = Field(default_factory=list)

    subjects_marked: int = 0
    subjects_enrolled: int = 0
    total_marks: Decimal = Decimal("0")
    average: Optional[float] = None

    # Position within the ranking group, when one was requested.
    position: Optional[int] = None
    ranked_out_of: Optional[int] = None
    is_complete: bool = Field(
        default=True,
        description="Whether every enrolled subject has a mark",
    )


class ExaminationResults(BaseModel):
    """A whole examination, or one class within it."""

    examination_id: int
    examination_name: str
    term_name: Optional[str] = None
    academic_year_name: Optional[str] = None
    status: str

    class_id: Optional[int] = None
    class_name: Optional[str] = None

    students: List[StudentResultRecord] = Field(default_factory=list)

    student_count: int = 0
    result_count: int = 0
    average: Optional[float] = None
    ranked: bool = False


class SubjectSummary(BaseModel):
    """How one subject performed in one examination."""

    subject_id: int
    subject_name: str
    subject_code: str
    examination_id: int
    examination_name: str

    count: int = 0
    average: Optional[float] = None
    highest: Optional[float] = None
    lowest: Optional[float] = None
    pass_count: int = 0
    pass_rate: Optional[float] = None
    grade_distribution: Dict[str, int] = Field(default_factory=dict)

    students: List[StudentResultRecord] = Field(default_factory=list)


class TeacherResults(BaseModel):
    """Everything one teacher has in, across the subjects they are assigned."""

    teacher_id: int
    teacher_name: str
    employee_number: str
    examination_id: int
    examination_name: str

    subjects: List[SubjectSummary] = Field(default_factory=list)
    total_results: int = 0


# --------------------------------------------------------------- auditing


class AuditEntry(BaseModel):
    """One recorded change to one result.

    Answers the six questions the audit exists for: which result, who changed
    it, from what, to what, why, and when.
    """

    id: int
    result_id: int

    student_id: int
    student_number: str
    student_name: str
    subject_name: str
    subject_code: str
    examination_id: int
    examination_name: str

    old_marks: Optional[Decimal] = None
    new_marks: Optional[Decimal] = None
    old_grade: Optional[str] = None
    new_grade: Optional[str] = None

    changed_by: Optional[str] = None
    changed_by_role: Optional[str] = None
    reason: Optional[str] = None
    changed_at: datetime


class ResultAudit(BaseModel):
    """The full provenance of one mark."""

    result_id: int
    student_number: str
    student_name: str
    subject_name: str
    examination_name: str

    current_marks: Decimal
    current_grade: Optional[str] = None
    current_remarks: Optional[str] = None

    # Who put the current value there, and when it last moved.
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    changes: List[AuditEntry] = Field(default_factory=list)


class ResultEdit(BaseModel):
    """An administrator correcting a mark.

    A reason is required. A correction with no explanation is exactly what the
    audit trail exists to prevent.
    """

    marks: Decimal = Field(ge=0, le=100)
    remarks: Optional[str] = Field(default=None, max_length=255)
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("marks")
    @classmethod
    def _round(cls, value: Decimal) -> Decimal:
        return round(value, 2)

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        return value.strip()
