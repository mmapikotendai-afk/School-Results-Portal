"""Schemas for administrator-confirmed annual student progression."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EducationLevel, FormLevel, ProgressionAction, StudentEnrollmentStatus


class EnrollmentHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    academic_year_name: str
    class_id: Optional[int] = None
    class_name: str
    form_level: FormLevel
    academic_level: EducationLevel
    status: StudentEnrollmentStatus
    enrolled_at: datetime
    status_changed_at: datetime


class ProgressionRosterRow(BaseModel):
    student_id: int
    student_number: str
    student_name: str
    class_id: Optional[int] = None
    class_name: str
    form_level: FormLevel
    academic_level: EducationLevel
    status: StudentEnrollmentStatus


class ProgressionRequest(BaseModel):
    student_ids: List[int] = Field(min_length=1, max_length=500)
    source_academic_year_id: int
    target_academic_year_id: int
    target_class_id: int
    action: ProgressionAction
    subject_ids: List[int] = Field(default_factory=list)


class ProgressionPreviewRow(BaseModel):
    student_id: int
    student_number: str
    student_name: str
    from_year: str
    from_form: FormLevel
    from_class: str
    to_year: str
    to_form: FormLevel
    to_class: str
    valid: bool = True
    message: str = "Ready"


class ProgressionPreview(BaseModel):
    action: ProgressionAction
    rows: List[ProgressionPreviewRow] = Field(default_factory=list)
    accepted: int = 0
    rejected: int = 0
    can_confirm: bool = False
    detail: str = ""


class ProgressionResult(BaseModel):
    action: ProgressionAction
    batch_id: str
    students_updated: int
    enrollments_created: int = 0
    enrollments_updated: int = 0
    subject_enrollments_created: int = 0
    detail: str


class ConfirmReturnRequest(BaseModel):
    student_ids: List[int] = Field(min_length=1, max_length=500)
    academic_year_id: int


class EnrollmentAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    batch_id: str
    from_academic_year_id: Optional[int] = None
    to_academic_year_id: int
    from_form_level: Optional[str] = None
    to_form_level: str
    from_class_name: Optional[str] = None
    to_class_name: str
    from_status: Optional[str] = None
    to_status: str
    created_at: datetime
