"""One-time printable credentials for email-free teacher accounts."""

import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.student_enrollment import TeacherCredentialAudit
from app.models.teacher import Teacher
from app.schemas.people import TeacherCredentialSlip
from app.services.academic_service import utcnow
from app.services.school_service import SchoolService


class TeacherCredentialsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def issue_slip(
        self, teacher: Teacher, temporary_password: str, actor_user_id: int,
        action: str, batch_id: str | None = None,
    ) -> TeacherCredentialSlip:
        batch_id = batch_id or str(uuid.uuid4())
        expires_at = utcnow() + timedelta(minutes=settings.CREDENTIAL_SLIP_TTL_MINUTES)
        school = SchoolService(self.db).get()
        self.db.add(TeacherCredentialAudit(
            user_id=teacher.user_id, teacher_id=teacher.id, actor_user_id=actor_user_id,
            action=action, batch_id=batch_id, expires_at=expires_at,
        ))
        return TeacherCredentialSlip(
            teacher_id=teacher.id,
            school_name=school.school_name if school else settings.SCHOOL_NAME,
            teacher_name=teacher.full_name,
            employee_number=teacher.employee_number,
            temporary_password=temporary_password,
            portal_url=settings.FRONTEND_URL,
            instructions=(
                "Sign in with your employee number and temporary password. "
                "You must choose a new password immediately. Keep it private."
            ),
            batch_id=batch_id, expires_at=expires_at,
        )

    def consume_batch(self, batch_id: str, actor_user_id: int) -> bool:
        rows = self.db.query(TeacherCredentialAudit).filter(
            TeacherCredentialAudit.batch_id == batch_id
        ).with_for_update().all()
        if not rows or any(row.actor_user_id != actor_user_id for row in rows):
            return False
        now = utcnow()
        if any(row.consumed_at is not None or row.expires_at < now for row in rows):
            return False
        for row in rows:
            row.consumed_at = now
        self.db.commit()
        return True
