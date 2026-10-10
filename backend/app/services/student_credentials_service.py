"""Student-number allocation and one-time printable credential issuance."""

import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.academic_year import AcademicYear
from app.models.student import Student
from app.models.student_enrollment import CredentialAudit, StudentNumberSequence
from app.schemas.people import CredentialSlip
from app.services.school_service import SchoolService


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class StudentCredentialsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def admission_year(self, academic_year_id: int) -> int:
        year = self.db.get(AcademicYear, academic_year_id)
        if year is None:
            raise ValueError("That academic year does not exist.")
        match = re.search(r"(?:19|20)\d{2}", year.name or "")
        return int(match.group(0)) if match else (
            year.start_date.year if year.start_date else datetime.now().year
        )

    def allocate_student_number(self, academic_year_id: int) -> str:
        """Commit an allocation independently so issued numbers are never recycled."""
        year = self.db.query(AcademicYear).filter(AcademicYear.id == academic_year_id).first()
        if year is None:
            raise ValueError("That academic year does not exist.")

        full_year = self.admission_year(academic_year_id)
        year_code = str(full_year)[-2:]
        bind = self.db.get_bind()
        for _attempt in range(5):
            sequence_db = Session(bind=bind, autoflush=False)
            try:
                if (bind.dialect.name == "sqlite"
                        and bind.pool.__class__.__name__ != "StaticPool"):
                    sequence_db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                sequence = (
                    sequence_db.query(StudentNumberSequence)
                    .filter(StudentNumberSequence.year_code == year_code)
                    .with_for_update()
                    .first()
                )
                if sequence is None:
                    sequence = StudentNumberSequence(year_code=year_code, next_value=2)
                    sequence_db.add(sequence)
                    value = 1
                else:
                    value = sequence.next_value
                    sequence.next_value += 1
                if value > 999:
                    sequence_db.rollback()
                    raise ValueError(
                        f"The {full_year} admission sequence is full (999 students). "
                        "Create no further admissions for that year until the school policy is reviewed."
                    )
                sequence_db.commit()
            except (IntegrityError, OperationalError):
                sequence_db.rollback()
                time.sleep(0.01 * (_attempt + 1))
                continue
            finally:
                sequence_db.close()

            number = f"{settings.STUDENT_NUMBER_PREFIX.strip().upper()}{year_code}{value:03d}"
            if not self.db.query(Student.id).filter(Student.student_number == number).first():
                return number
        raise ValueError("A student number could not be reserved safely. Try again.")

    def issue_slip(
        self,
        student: Student,
        temporary_password: str,
        actor_user_id: int,
        action: str,
        batch_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> CredentialSlip:
        batch_id = batch_id or str(uuid.uuid4())
        expires_at = expires_at or (
            utcnow() + timedelta(minutes=settings.CREDENTIAL_SLIP_TTL_MINUTES)
        )
        school = SchoolService(self.db).get()
        self.db.add(
            CredentialAudit(
                user_id=student.user_id,
                student_id=student.id,
                actor_user_id=actor_user_id,
                action=action,
                batch_id=batch_id,
                expires_at=expires_at,
            )
        )
        return CredentialSlip(
            student_id=student.id,
            school_name=school.school_name if school else settings.SCHOOL_NAME,
            student_name=student.full_name,
            student_number=student.student_number,
            temporary_password=temporary_password,
            portal_url=settings.FRONTEND_URL,
            instructions=(
                "Sign in with your student number and temporary password. "
                "You must choose a new password immediately. Keep it private."
            ),
            batch_id=batch_id,
            expires_at=expires_at,
        )

    def consume_batch(self, batch_id: str, actor_user_id: int) -> bool:
        rows: Iterable[CredentialAudit] = (
            self.db.query(CredentialAudit)
            .filter(CredentialAudit.batch_id == batch_id)
            .with_for_update()
            .all()
        )
        rows = list(rows)
        if not rows or any(row.actor_user_id != actor_user_id for row in rows):
            return False
        now = utcnow()
        if any(row.consumed_at is not None or row.expires_at < now for row in rows):
            return False
        for row in rows:
            row.consumed_at = now
        self.db.commit()
        return True
