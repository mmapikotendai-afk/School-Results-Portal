"""Create the login_attempts table on a database that predates it.

`init_db` uses SQLAlchemy's create_all, which creates missing *tables* but
never alters or notices anything else, so it already handles this one. This
script exists so the change can be applied deliberately, reported on, and run
against a database without also running the rest of init_db - and so there is
a record of when the table arrived.

Safe to run more than once: it creates the table only when it is absent, and
touches no existing row.

    python -m scripts.add_login_attempts
"""

import sys

from sqlalchemy import inspect

from app.database import engine
from app.models.login_attempt import LoginAttempt

TABLE = LoginAttempt.__tablename__


def main() -> int:
    inspector = inspect(engine)
    print(f"Database : {engine.url.get_backend_name()} / {engine.url.database}")

    if TABLE in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns(TABLE)]
        print(f"Table    : {TABLE} already exists ({len(columns)} columns)")
        print("Nothing to do.")
        return 0

    print(f"Creating : {TABLE} ...")
    LoginAttempt.__table__.create(bind=engine)

    columns = [c["name"] for c in inspect(engine).get_columns(TABLE)]
    print(f"Created  : {TABLE} with columns {', '.join(columns)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
