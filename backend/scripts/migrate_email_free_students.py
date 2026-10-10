"""Safely migrate an existing database to email-free student accounts.

Run once from the backend directory:
    python scripts/migrate_email_free_students.py

The script is idempotent. It preserves primary keys and results, makes only
the users.email column nullable, creates the new enrollment/audit tables, and
backfills current enrollment plus student-number usernames.
"""

import re
import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402,F401
    AcademicYear,
    CredentialAudit,
    Result,
    Student,
    StudentEnrollment,
    StudentEnrollmentStatus,
    StudentNumberSequence,
    User,
)


def make_email_nullable() -> None:
    email = next(c for c in inspect(engine).get_columns("users") if c["name"] == "email")
    if email.get("nullable"):
        return
    dialect = engine.dialect.name
    with engine.begin() as connection:
        if dialect == "mysql":
            connection.execute(text("ALTER TABLE users MODIFY COLUMN email VARCHAR(255) NULL"))
        elif dialect == "postgresql":
            connection.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
        else:
            raise RuntimeError(
                f"Automatic nullable-column migration is not supported for {dialect}."
            )


def main() -> None:
    before = {}
    with SessionLocal() as db:
        before = {
            "users": db.query(User).count(),
            "students": db.query(Student).count(),
            "results": db.query(Result).count(),
        }

    make_email_nullable()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            StudentEnrollment.__table__,
            StudentNumberSequence.__table__,
            CredentialAudit.__table__,
        ],
    )

    with SessionLocal() as db:
        active_year = (
            db.query(AcademicYear)
            .filter(AcademicYear.is_active.is_(True))
            .order_by(AcademicYear.id.desc())
            .first()
        )
        if db.query(Student).count() and active_year is None:
            raise RuntimeError("Set an active academic year before running this migration.")

        for student in db.query(Student).all():
            username = student.student_number.strip().upper()
            collision = (
                db.query(User.id)
                .filter(User.username == username, User.id != student.user_id)
                .first()
            )
            if collision:
                raise RuntimeError(
                    f"Cannot assign {student.student_number} as a login username; it is already used."
                )
            student.user.username = username
            student.user.email = None

            existing = (
                db.query(StudentEnrollment.id)
                .filter(
                    StudentEnrollment.student_id == student.id,
                    StudentEnrollment.academic_year_id == active_year.id,
                )
                .first()
            )
            if not existing:
                db.add(
                    StudentEnrollment(
                        student_id=student.id,
                        academic_year_id=active_year.id,
                        class_id=student.class_id,
                        status=(
                            StudentEnrollmentStatus.ACTIVE
                            if student.user.is_active
                            else StudentEnrollmentStatus.WITHDRAWN_NOT_RETURNED
                        ),
                    )
                )

        for year in db.query(AcademicYear).all():
            match = re.search(r"(?:19|20)\d{2}", year.name or "")
            full_year = int(match.group(0)) if match else (
                year.start_date.year if year.start_date else None
            )
            if not full_year:
                continue
            code = str(full_year)[-2:]
            pattern = re.compile(
                rf"^{re.escape(settings.STUDENT_NUMBER_PREFIX)}{code}(\d+)$", re.IGNORECASE
            )
            highest = 0
            for (number,) in db.query(Student.student_number).all():
                found = pattern.match(number or "")
                if found:
                    highest = max(highest, int(found.group(1)))
            sequence = db.get(StudentNumberSequence, code)
            if sequence is None:
                db.add(StudentNumberSequence(year_code=code, next_value=highest + 1))
            elif sequence.next_value <= highest:
                sequence.next_value = highest + 1

        db.commit()

        after = {
            "users": db.query(User).count(),
            "students": db.query(Student).count(),
            "results": db.query(Result).count(),
        }
        if after != before:
            raise RuntimeError(f"Integrity check failed: before={before}, after={after}")
        print(f"Migration complete. Preserved counts: {after}")


if __name__ == "__main__":
    main()
