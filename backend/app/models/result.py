"""Examination results and the audit trail of every change made to them."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Result(Base, TimestampMixin):
    """One student mark in one subject for one examination.

    The unique constraint on student, subject and examination is what makes
    results uploaded by different teachers combine into a single report card
    without duplication, and what makes a re-upload an update rather than a
    second row.
    """

    __tablename__ = "results"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "subject_id", "examination_id", name="uq_result_student_subject_exam"
        ),
        # Counting and listing marks for one subject in one examination -
        # the query behind submission progress and the mark sheet.
        Index("ix_results_exam_subject", "examination_id", "subject_id"),
        # Building one student report card.
        Index("ix_results_exam_student", "examination_id", "student_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    examination_id: Mapped[int] = mapped_column(
        ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False
    )

    # Numeric rather than float, so a mark of 67.50 is stored exactly.
    marks: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    # Grade symbol derived from the mark and the education level: A-U at
    # O-Level, A-F at A-Level. See app/utils/grading.py.
    grade: Mapped[Optional[str]] = mapped_column(String(4), index=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(255))

    # The teacher or administrator whose upload produced this row. Kept for
    # accountability, so it survives the user being deactivated or removed.
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        "uploaded_by", ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    student: Mapped["Student"] = relationship(back_populates="results")  # noqa: F821
    subject: Mapped["Subject"] = relationship(back_populates="results")  # noqa: F821
    examination: Mapped["Examination"] = relationship(back_populates="results")  # noqa: F821
    uploaded_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        back_populates="uploaded_results", foreign_keys=[uploaded_by_id]
    )
    audit_logs: Mapped[List["ResultAuditLog"]] = relationship(
        back_populates="result", cascade="all, delete-orphan", order_by="ResultAuditLog.changed_at"
    )

    def __repr__(self) -> str:
        return f"<Result student={self.student_id} subject={self.subject_id} marks={self.marks}>"


class ResultAuditLog(Base):
    """An immutable record of one correction to one result.

    Written by the service layer on every change to marks or grade, so a
    published mark can always be traced back to who altered it and why.
    """

    __tablename__ = "result_audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)

    result_id: Mapped[int] = mapped_column(
        ForeignKey("results.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Kept even if the account is later removed, so the trail is never orphaned
    # silently - the reason and the values always survive.
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        "changed_by", ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    old_marks: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    new_marks: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    old_grade: Mapped[Optional[str]] = mapped_column(String(4))
    new_grade: Mapped[Optional[str]] = mapped_column(String(4))

    reason: Mapped[Optional[str]] = mapped_column(String(500))

    changed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    result: Mapped["Result"] = relationship(back_populates="audit_logs")
    changed_by: Mapped[Optional["User"]] = relationship(  # noqa: F821
        back_populates="result_changes"
    )

    def __repr__(self) -> str:
        return f"<ResultAuditLog result={self.result_id} {self.old_marks} -> {self.new_marks}>"
