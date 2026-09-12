"""Back up every student record, then delete all of them.

    python -m scripts.purge_students            # dry run: report only
    python -m scripts.purge_students --confirm  # write the backup, then delete

Deleting a student cascades to their enrollments, their results, and the audit
logs attached to those results. That is more than the word "student" suggests,
so everything is written to a timestamped JSON file under EMAIL_OUTBOX_DIR's
parent (`var/`) before a single row is removed.

Teachers, administrators, subjects, classes, terms and examinations are left
alone. Only STUDENT-role users and the rows that hang off them are touched.

Password hashes are NOT included in the backup. Restoring one would restore a
credential nobody has any use for; the accounts would be re-provisioned and
their holders emailed a new temporary password, as any new account is.
"""

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path

from sqlalchemy import text

from app.database import engine

BACKUP_DIR = Path("var")

# Ordered so a restore could be replayed top to bottom: parents before children.
TABLES = {
    "users": """
        SELECT id, email, username, full_name, role, is_active,
               must_change_password, token_version, password_changed_at,
               last_login_at, email_sent, email_sent_at, email_delivery_status,
               created_at
        FROM users WHERE role = 'STUDENT'
    """,
    "students": "SELECT * FROM students",
    "student_subjects": """
        SELECT * FROM student_subjects
        WHERE student_id IN (SELECT id FROM students)
    """,
    "results": "SELECT * FROM results WHERE student_id IN (SELECT id FROM students)",
    "result_audit_logs": """
        SELECT * FROM result_audit_logs
        WHERE result_id IN (
            SELECT id FROM results WHERE student_id IN (SELECT id FROM students)
        )
    """,
}


def _jsonable(value):
    """Coerce a DB value into something json.dumps accepts.

    date has to be tested alongside datetime rather than after it: a plain
    date (students.date_of_birth) is not a datetime, so checking only for
    datetime lets it through to the encoder and fails the whole backup.
    """
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def main() -> int:
    confirm = "--confirm" in sys.argv

    with engine.connect() as connection:
        snapshot = {}
        for table, query in TABLES.items():
            rows = connection.execute(text(query)).mappings().all()
            snapshot[table] = [
                {k: _jsonable(v) for k, v in row.items()} for row in rows
            ]

    print("About to remove")
    print("---------------")
    for table, rows in snapshot.items():
        print(f"  {table:<20} {len(rows)}")

    if not any(snapshot.values()):
        print("\nNothing to do - there are no students.")
        return 0

    if not confirm:
        print("\nDry run. Re-run with --confirm to write the backup and delete.")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"backup-students-{stamp}.json"
    backup.write_text(
        json.dumps(
            {
                "taken_at": datetime.now(timezone.utc).isoformat(),
                "note": "Password hashes deliberately excluded.",
                "tables": snapshot,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nBackup written: {backup.resolve()}")
    print(f"  {backup.stat().st_size:,} bytes")

    # One transaction: either every student goes or none does. Deleting the
    # user rows is enough - students, enrollments, results and audit logs all
    # cascade from there - but the child tables are cleared explicitly first so
    # the counts below are real rather than inferred.
    print("\nDeleting ...")
    with engine.begin() as connection:
        removed = {}
        for statement, label in [
            ("""DELETE FROM result_audit_logs WHERE result_id IN (
                    SELECT id FROM results WHERE student_id IN (SELECT id FROM students))""",
             "result_audit_logs"),
            ("""DELETE FROM results WHERE student_id IN (SELECT id FROM students)""",
             "results"),
            ("""DELETE FROM student_subjects WHERE student_id IN (SELECT id FROM students)""",
             "student_subjects"),
            ("""DELETE FROM students""", "students"),
            ("""DELETE FROM users WHERE role = 'STUDENT'""", "users (STUDENT)"),
        ]:
            removed[label] = connection.execute(text(statement)).rowcount
            print(f"  {label:<20} {removed[label]}")

    with engine.connect() as connection:
        left = connection.execute(text("SELECT COUNT(*) FROM students")).scalar()
        teachers = connection.execute(text("SELECT COUNT(*) FROM teachers")).scalar()
        admins = connection.execute(
            text("SELECT COUNT(*) FROM users WHERE role='ADMIN'")
        ).scalar()

    print(f"\nStudents remaining: {left}")
    print(f"Untouched: {teachers} teacher(s), {admins} admin(s)")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
