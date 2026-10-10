"""Yearly student enrollment and immutable credential issuance audit rows."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EducationLevel, FormLevel, StudentEnrollmentStatus


class StudentEnrollment(Base):
    """A student's school-level enrollment for one academic year."""

    __tablename__ = "student_enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", name="uq_student_enrollment_year"),
        Index("ix_student_enrollments_year_status", "academic_year_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    class_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("classes.id", ondelete="SET NULL"), nullable=True
    )
    class_name_snapshot: Mapped[str] = mapped_column(String(60), nullable=False)
    form_level: Mapped[FormLevel] = mapped_column(Enum(FormLevel), nullable=False, index=True)
    academic_level: Mapped[EducationLevel] = mapped_column(
        Enum(EducationLevel), nullable=False, index=True
    )
    status: Mapped[StudentEnrollmentStatus] = mapped_column(
        Enum(StudentEnrollmentStatus), default=StudentEnrollmentStatus.ACTIVE,
        nullable=False, index=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    student: Mapped["Student"] = relationship(back_populates="year_enrollments")  # noqa: F821
    academic_year: Mapped["AcademicYear"] = relationship()  # noqa: F821
    school_class: Mapped[Optional["SchoolClass"]] = relationship()  # noqa: F821


class StudentNumberSequence(Base):
    """Transactionally allocated counter for one admission year code."""

    __tablename__ = "student_number_sequences"

    year_code: Mapped[str] = mapped_column(String(2), primary_key=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class CredentialAudit(Base):
    """Audit metadata for issuance and printing; never contains a password."""

    __tablename__ = "credential_audits"
    __table_args__ = (Index("ix_credential_audits_batch", "batch_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class TeacherCredentialAudit(Base):
    """One-time teacher credential issuance metadata; never a plaintext password."""

    __tablename__ = "teacher_credential_audits"
    __table_args__ = (Index("ix_teacher_credential_audits_batch", "batch_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class EnrollmentAudit(Base):
    """Immutable record of administrator-confirmed placement changes."""

    __tablename__ = "enrollment_audits"
    __table_args__ = (Index("ix_enrollment_audits_student_created", "student_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_academic_year_id: Mapped[Optional[int]] = mapped_column(Integer)
    to_academic_year_id: Mapped[int] = mapped_column(Integer, nullable=False)
    from_form_level: Mapped[Optional[str]] = mapped_column(String(20))
    to_form_level: Mapped[str] = mapped_column(String(20), nullable=False)
    from_class_name: Mapped[Optional[str]] = mapped_column(String(60))
    to_class_name: Mapped[str] = mapped_column(String(60), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
