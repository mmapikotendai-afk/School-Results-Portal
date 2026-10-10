"""Resolve academic context from the immutable annual enrollment snapshot."""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.enums import EducationLevel
from app.models.student_enrollment import StudentEnrollment


def student_enrollment_for(db: Session, student_id: int, academic_year_id: int):
    return db.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == student_id,
        StudentEnrollment.academic_year_id == academic_year_id,
    ).first()


def student_academic_level(
    db: Session,
    student_id: int,
    academic_year_id: int,
    fallback: Optional[EducationLevel] = None,
) -> Optional[EducationLevel]:
    enrollment = student_enrollment_for(db, student_id, academic_year_id)
    return enrollment.academic_level if enrollment else fallback
