"""Create the database schema and an initial administrator account.

Usage (from the `backend` directory, with the virtualenv active):

    python -m scripts.init_db

The admin credentials are read from the environment so nothing is hard-coded:

    ADMIN_EMAIL=admin@school.edu ADMIN_PASSWORD=... ADMIN_NAME="Head Teacher" \
        python -m scripts.init_db
"""

import os
import sys

from app.database import SessionLocal, init_db
from app.models.enums import UserRole
from app.models.user import User
from app.utils.security import hash_password


def main() -> int:
    print("Creating tables ...")
    init_db()
    print("Tables are up to date.")

    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    full_name = os.getenv("ADMIN_NAME", "System Administrator")
    username = os.getenv("ADMIN_USERNAME")

    if not email or not password:
        print(
            "\nSkipped admin creation. To create one, re-run with ADMIN_EMAIL and "
            "ADMIN_PASSWORD set in the environment."
        )
        return 0

    db = SessionLocal()
    try:
        normalised = email.strip().lower()
        if db.query(User).filter(User.email == normalised).first():
            print(f"Admin '{normalised}' already exists - nothing to do.")
            return 0

        db.add(
            User(
                email=normalised,
                username=username.strip().lower() if username else None,
                full_name=full_name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
                # Surfaced in Settings > Security only - never as a login banner.
                must_change_password=True,
            )
        )
        db.commit()
        print(f"Created administrator: {normalised}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
