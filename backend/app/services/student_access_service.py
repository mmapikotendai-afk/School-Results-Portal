"""Current-enrollment checks shared by login and every student endpoint."""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.academic_year import AcademicYear
from app.models.enums import StudentEnrollmentStatus
from app.models.student_enrollment import StudentEnrollment
from app.models.user import User


def current_enrollment(db: Session, user: User) -> Optional[StudentEnrollment]:
    if not user.student:
        return None
    return (
        db.query(StudentEnrollment)
        .join(AcademicYear, StudentEnrollment.academic_year_id == AcademicYear.id)
        .filter(
            StudentEnrollment.student_id == user.student.id,
            AcademicYear.is_active.is_(True),
        )
        .first()
    )


def has_active_current_enrollment(db: Session, user: User) -> bool:
    enrollment = current_enrollment(db, user)
    return bool(enrollment and enrollment.status == StudentEnrollmentStatus.ACTIVE)
