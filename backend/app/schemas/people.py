"""Schemas for student and teacher management."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import EducationLevel, Gender
from app.schemas.catalog import ClassSummary, SubjectSummary
from app.schemas.user import CredentialDelivery


def _strip(value: Optional[str]) -> Optional[str]:
    return value.strip() if isinstance(value, str) else value


# --------------------------------------------------------------- students


class StudentBase(BaseModel):
    student_number: str = Field(min_length=1, max_length=32)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    class_id: Optional[int] = None

    @field_validator("student_number")
    @classmethod
    def _number(cls, v: str) -> str:
        # Uppercased so STU-001 and stu-001 cannot both exist.
        return v.strip().upper()

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
    """Create a student and the portal account that goes with it.

    Email is required. It is the address the learner gave the school office,
    and it is where their temporary password is sent - so an account created
    without one would be an account nobody could ever sign in to. A derived
    `@STUDENT_EMAIL_DOMAIN` identifier is no longer accepted at creation for
    exactly that reason.
    """

    email: EmailStr

    # Subjects to enrol the student in, for the given (or active) year.
    subject_ids: List[int] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class StudentUpdate(BaseModel):
    student_number: Optional[str] = Field(default=None, min_length=1, max_length=32)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    class_id: Optional[int] = None
    email: Optional[EmailStr] = None

    @field_validator("student_number")
    @classmethod
    def _number(cls, v):
        return v.strip().upper() if v else v

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, v):
        return _strip(v)


class StudentRead(BaseModel):
    """Row shape for the student list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_number: str
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    email: str
    is_active: bool
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
    """Returned on creation, carrying the delivery outcome - not the password.

    The temporary password is emailed to the student and is never included in
    an API response. If delivery failed, the administrator resends, which
    issues a new password rather than disclosing the one already set.
    """

    delivery: CredentialDelivery


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
    email: EmailStr
    subject_ids: List[int] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class TeacherUpdate(BaseModel):
    employee_number: Optional[str] = Field(default=None, min_length=1, max_length=32)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    department: Optional[str] = Field(default=None, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=32)
    email: Optional[EmailStr] = None

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
    email: str
    is_active: bool
    subject_count: int = 0
    created_at: datetime


class TeacherDetail(TeacherRead):
    subjects: List[SubjectSummary] = Field(default_factory=list)
    academic_year_id: Optional[int] = None


class TeacherCreated(TeacherDetail):
    """As StudentCreated: the delivery outcome, never the password."""

    delivery: CredentialDelivery


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
