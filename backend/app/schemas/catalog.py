"""Schemas for the subject and class catalogues."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EducationLevel, SubjectLevel


def _clean(value: Optional[str]) -> Optional[str]:
    return value.strip() if isinstance(value, str) else value


# --------------------------------------------------------------- subjects


class SubjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=1, max_length=20)
    level: SubjectLevel = SubjectLevel.BOTH

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()

    @field_validator("code")
    @classmethod
    def _code(cls, v: str) -> str:
        # Codes are matched and printed on mark sheets, so they are normalised
        # to a single canonical form rather than trusted as typed.
        return v.strip().upper()


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    level: Optional[SubjectLevel] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _clean(v)

    @field_validator("code")
    @classmethod
    def _code(cls, v):
        return v.strip().upper() if v else v


class SubjectRead(SubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime


class SubjectSummary(BaseModel):
    """Compact form for pickers and chips."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    level: SubjectLevel


# ---------------------------------------------------------------- classes


class ClassBase(BaseModel):
    # Free text so any convention works: 1C, Form 4A, Lower 6 Sciences.
    name: str = Field(min_length=1, max_length=60)
    level: EducationLevel

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()


class ClassCreate(ClassBase):
    pass


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    level: Optional[EducationLevel] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return _clean(v)


class ClassRead(ClassBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime


class ClassSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    level: EducationLevel


class ClassWithCount(ClassRead):
    """Class list rows carry their roll size, so an empty class is obvious."""

    student_count: int = 0
