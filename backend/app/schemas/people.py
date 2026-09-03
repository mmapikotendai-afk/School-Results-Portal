"""Schemas for student and teacher management."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import EducationLevel, Gender
from app.schemas.catalog import ClassSummary, SubjectSummary
from app.utils.security import MAX_PASSWORD_BYTES, MIN_PASSWORD_LENGTH, password_policy_errors


def _strip(value: Optional[str]) -> Optional[str]:
    return value.strip() if isinstance(value, str) else value


class InitialPassword(BaseModel):
    """Optional starting password for a provisioned account.

    Left empty, one is generated and returned once so the office can hand it
    over. Either way the account is flagged must_change_password.
    """

    initial_password: Optional[str] = Field(
        default=None, min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_BYTES
    )

    @field_validator("initial_password")
    @classmethod
    def _policy(cls, v):
        if v:
            errors = password_policy_errors(v)
            if errors:
                raise ValueError(" ".join(errors))
        return v


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


class StudentCreate(StudentBase, InitialPassword):
    """Create a student and the portal account that goes with it.

    Email is optional: when it is omitted one is derived from the student
    number, so a learner without a mailbox still gets an account they can sign
    in to with their student number.
    """

    email: Optional[EmailStr] = None

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
    """Returned once on creation, carrying the password to hand over."""

    initial_password: Optional[str] = None


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


class TeacherCreate(TeacherBase, InitialPassword):
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
    initial_password: Optional[str] = None


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
