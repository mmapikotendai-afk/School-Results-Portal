"""Switch teacher accounts from email sign-in to employee-number sign-in."""

import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import TeacherCredentialAudit, UserRole  # noqa: E402,F401


def main() -> None:
    with engine.connect() as connection:
        before = connection.execute(text("SELECT COUNT(*) FROM teachers")).scalar_one()

    with SessionLocal() as db:
        rows = db.execute(text(
            "SELECT t.id AS teacher_id, t.employee_number, t.user_id "
            "FROM teachers t JOIN users u ON u.id = t.user_id "
            "WHERE u.role = 'TEACHER'"
        )).mappings().all()
        wanted = [row["employee_number"].strip().lower() for row in rows]
        if len(wanted) != len(set(wanted)):
            raise RuntimeError("Teacher employee numbers are not unique after normalisation.")
        for row, username in zip(rows, wanted):
            clash = db.execute(text(
                "SELECT id FROM users WHERE username = :username AND id != :user_id"
            ), {"username": username, "user_id": row["user_id"]}).first()
            if clash:
                raise RuntimeError(
                    f"Employee number {row['employee_number']} conflicts with another sign-in name."
                )
            db.execute(text(
                "UPDATE users SET username = :username, email = NULL, "
                "email_sent = 0, email_sent_at = NULL, email_last_error = NULL, "
                "email_delivery_status = 'NOT_SENT' WHERE id = :user_id"
            ), {"username": username, "user_id": row["user_id"]})
        db.commit()

    Base.metadata.create_all(bind=engine, tables=[TeacherCredentialAudit.__table__])
    with engine.connect() as connection:
        after = connection.execute(text("SELECT COUNT(*) FROM teachers")).scalar_one()
    if after != before:
        raise RuntimeError(f"Integrity check failed: before={before}, after={after}")
    print(f"Teacher email removal complete. Preserved teachers: {after}")


if __name__ == "__main__":
    main()
