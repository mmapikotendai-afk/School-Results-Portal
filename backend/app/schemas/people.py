"""Schemas for student and teacher management."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EducationLevel, Gender, StudentEnrollmentStatus
from app.schemas.catalog import ClassSummary, SubjectSummary


def _strip(value: Optional[str]) -> Optional[str]:
    return value.strip() if isinstance(value, str) else value


# --------------------------------------------------------------- students


class StudentBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    class_id: Optional[int] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, v: str) -> str:
        return v.strip()

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v):
        if v and v > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return v


class StudentCreate(StudentBase):
    """Admit a student; the permanent student number is generated server-side."""

    model_config = ConfigDict(extra="forbid")

    date_of_birth: date
    gender: Gender

    # Subjects to enrol the student in, for the given (or active) year.
    subject_ids: List[int] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class StudentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    class_id: Optional[int] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, v):
        return _strip(v)


class StudentRead(BaseModel):
    """Row shape for the student list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_number: str
    admission_year: int
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    is_active: bool
    enrollment_status: Optional[StudentEnrollmentStatus] = None
    school_class: Optional[ClassSummary] = None
    level: Optional[EducationLevel] = None
    subject_count: int = 0
    created_at: datetime


class StudentDetail(StudentRead):
    """Single student, with the subjects they currently study."""

    subjects: List[SubjectSummary] = Field(default_factory=list)
    dropped_subjects: List[SubjectSummary] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class StudentCreated(StudentDetail):
    """Returned once to the authorised administrator after admission."""

    credential: "CredentialSlip"


class CredentialSlip(BaseModel):
    student_id: int
    school_name: str
    student_name: str
    student_number: str
    temporary_password: str
    portal_url: str
    instructions: str
    batch_id: str
    expires_at: datetime


class AdminReauthentication(BaseModel):
    admin_password: str = Field(min_length=1, max_length=256)


class StudentEnrollmentStatusUpdate(BaseModel):
    status: StudentEnrollmentStatus
    academic_year_id: Optional[int] = None


# --------------------------------------------------------------- teachers


class TeacherBase(BaseModel):
    employee_number: str = Field(min_length=1, max_length=32)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    department: Optional[str] = Field(default=None, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=32)

    @field_validator("employee_number")
    @classmethod
    def _number(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, v: str) -> str:
        return v.strip()


class TeacherCreate(TeacherBase):
    model_config = ConfigDict(extra="forbid")

    subject_ids: List[int] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class TeacherUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_number: Optional[str] = Field(default=None, min_length=1, max_length=32)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    department: Optional[str] = Field(default=None, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=32)

    @field_validator("employee_number")
    @classmethod
    def _number(cls, v):
        return v.strip().upper() if v else v

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, v):
        return _strip(v)


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_number: str
    first_name: str
    last_name: str
    full_name: str
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    subject_count: int = 0
    created_at: datetime


class TeacherDetail(TeacherRead):
    subjects: List[SubjectSummary] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class TeacherCreated(TeacherDetail):
    """Returned only while an administrator issues a one-time teacher slip."""

    credential: "TeacherCredentialSlip"


class TeacherCredentialSlip(BaseModel):
    teacher_id: int
    school_name: str
    teacher_name: str
    employee_number: str
    temporary_password: str
    portal_url: str
    instructions: str
    batch_id: str
    expires_at: datetime


# ------------------------------------------------- enrollment / assignment


class SubjectSelection(BaseModel):
    """The complete set of subjects a student studies or a teacher teaches.

    Sent whole rather than as add/remove operations, so the client cannot
    leave the two lists out of step with each other.
    """

    subject_ids: List[int] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class EnrollmentChange(BaseModel):
    """What actually changed, so the UI can report it precisely."""

    added: List[str] = Field(default_factory=list)
    reactivated: List[str] = Field(default_factory=list)
    dropped: List[str] = Field(default_factory=list)
    unchanged: int = 0


class StatusUpdate(BaseModel):
    is_active: bool


# --------------------------------------------------- bulk student import


class StudentImportRow(BaseModel):
    """One line of the uploaded file, as the preview table shows it."""

    row: int
    student_number: str
    first_name: str = ""
    last_name: str = ""
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None

    valid: bool = False
    message: str = ""


class StudentImportRowError(BaseModel):
    """A row that cannot be imported."""

    row: int
    student_number: Optional[str] = None
    message: str


class StudentImportReport(BaseModel):
    """What validating the file found. Nothing has been written."""

    class_id: int
    class_name: str
    academic_year_id: int
    subjects: List[str] = Field(default_factory=list)

    total_rows: int = 0
    accepted: int = 0
    rejected: int = 0

    rows: List[StudentImportRow] = Field(default_factory=list)
    errors: List[StudentImportRowError] = Field(default_factory=list)

    # False until every row is valid: the import is all-or-nothing, because a
    # partly applied class cannot be re-uploaded without colliding with itself.
    can_import: bool = False
    detail: str = ""


class StudentImportResult(BaseModel):
    """What the confirmed import actually did."""

    class_id: int
    class_name: str
    academic_year_id: int
    subjects: List[str] = Field(default_factory=list)

    students_created: int = 0
    enrollments_created: int = 0
    credentials_issued: int = 0
    batch_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    credentials: List[CredentialSlip] = Field(default_factory=list)

    # Rows that could not be created at all, if the roll changed since preview.
    failed: List[StudentImportRowError] = Field(default_factory=list)

    detail: str = ""
    model_config = ConfigDict(extra="forbid")
