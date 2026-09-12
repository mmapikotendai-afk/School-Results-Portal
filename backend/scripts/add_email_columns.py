"""Add the credential-delivery columns to an existing `users` table.

    python -m scripts.add_email_columns

`init_db` uses SQLAlchemy's create_all, which creates missing *tables* but
never alters an existing one. A database created before email provisioning was
added therefore has a `users` table without the delivery columns, and no way to
acquire them short of this script.

Safe to run more than once: each column is added only if it is absent, so a
second run reports "already present" and changes nothing. No row data is read,
written or moved.
"""

import sys

from sqlalchemy import inspect, text

from app.database import engine

TABLE = "users"

# Ordered as they should appear. MySQL ignores position without AFTER, which
# is fine - the ORM addresses columns by name.
COLUMNS = {
    "email_sent": "BOOLEAN NOT NULL DEFAULT 0",
    "email_sent_at": "DATETIME NULL",
    "email_delivery_status": (
        "ENUM('NOT_SENT','PENDING','SENT','FAILED','SKIPPED') "
        "NOT NULL DEFAULT 'NOT_SENT'"
    ),
    "email_last_error": "VARCHAR(255) NULL",
}


def main() -> int:
    inspector = inspect(engine)

    if TABLE not in inspector.get_table_names():
        print(
            f"The '{TABLE}' table does not exist. Run 'python -m scripts.init_db' "
            "first to create the schema."
        )
        return 1

    existing = {column["name"] for column in inspector.get_columns(TABLE)}
    missing = {name: ddl for name, ddl in COLUMNS.items() if name not in existing}

    if not missing:
        print(f"All credential-delivery columns are already present on '{TABLE}'.")
        return 0

    print(f"Adding {len(missing)} column(s) to '{TABLE}':")
    with engine.begin() as connection:
        for name, ddl in missing.items():
            print(f"  + {name}")
            # Identifiers here are module constants, not user input.
            connection.execute(text(f"ALTER TABLE `{TABLE}` ADD COLUMN `{name}` {ddl}"))

    print("\nDone. Existing accounts are marked NOT_SENT, which is accurate:")
    print("no credential email was ever sent for them. Use 'Resend Login")
    print("Credentials' in the admin UI to issue and deliver a new password.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
