"""Add immutable admission and annual progression history without rebuilding tables."""

import re
import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402,F401
    AcademicYear, EnrollmentAudit, FormLevel, Result, SchoolClass, Student,
    StudentEnrollment,
)


def form_from_name(name: str, academic_level: str) -> FormLevel:
    value = (name or "").lower().replace("-", " ")
    if "lower 6" in value or "form 5" in value:
        return FormLevel.LOWER_6
    if "upper 6" in value or "form 6" in value:
        return FormLevel.UPPER_6
    for number, form in ((1, FormLevel.FORM_1), (2, FormLevel.FORM_2),
                         (3, FormLevel.FORM_3), (4, FormLevel.FORM_4)):
        if re.search(rf"(?:form\s*)?{number}(?:\D|$)", value):
            return form
    raise RuntimeError(
        f"Cannot infer the Form for class {name!r}. Rename it to include Form 1-4, Lower 6 or Upper 6."
    )


def add_columns() -> None:
    dialect = engine.dialect.name
    schema = inspect(engine)
    class_columns = {column["name"] for column in schema.get_columns("classes")}
    student_columns = {column["name"] for column in schema.get_columns("students")}
    enrollment_columns = {column["name"] for column in schema.get_columns("student_enrollments")}
    with engine.begin() as connection:
        if dialect == "mysql":
            if "form_level" not in class_columns:
                connection.execute(text("ALTER TABLE classes ADD COLUMN form_level ENUM('FORM_1','FORM_2','FORM_3','FORM_4','LOWER_6','UPPER_6') NULL"))
            if "admission_year" not in student_columns:
                connection.execute(text("ALTER TABLE students ADD COLUMN admission_year INT NULL"))
            if "class_name_snapshot" not in enrollment_columns:
                connection.execute(text("ALTER TABLE student_enrollments ADD COLUMN class_name_snapshot VARCHAR(60) NULL"))
            if "form_level" not in enrollment_columns:
                connection.execute(text("ALTER TABLE student_enrollments ADD COLUMN form_level ENUM('FORM_1','FORM_2','FORM_3','FORM_4','LOWER_6','UPPER_6') NULL"))
            if "academic_level" not in enrollment_columns:
                connection.execute(text("ALTER TABLE student_enrollments ADD COLUMN academic_level ENUM('O_LEVEL','A_LEVEL') NULL"))
        elif dialect == "postgresql":
            connection.execute(text("DO $$ BEGIN CREATE TYPE formlevel AS ENUM ('FORM_1','FORM_2','FORM_3','FORM_4','LOWER_6','UPPER_6'); EXCEPTION WHEN duplicate_object THEN NULL; END $$"))
            if "form_level" not in class_columns:
                connection.execute(text("ALTER TABLE classes ADD COLUMN form_level formlevel NULL"))
            if "admission_year" not in student_columns:
                connection.execute(text("ALTER TABLE students ADD COLUMN admission_year INTEGER NULL"))
            if "class_name_snapshot" not in enrollment_columns:
                connection.execute(text("ALTER TABLE student_enrollments ADD COLUMN class_name_snapshot VARCHAR(60) NULL"))
            if "form_level" not in enrollment_columns:
                connection.execute(text("ALTER TABLE student_enrollments ADD COLUMN form_level formlevel NULL"))
            if "academic_level" not in enrollment_columns:
                connection.execute(text("ALTER TABLE student_enrollments ADD COLUMN academic_level educationlevel NULL"))
        else:
            raise RuntimeError(f"Unsupported migration database: {dialect}")


def require_columns() -> None:
    dialect = engine.dialect.name
    with engine.begin() as connection:
        if dialect == "mysql":
            connection.execute(text("ALTER TABLE classes MODIFY form_level ENUM('FORM_1','FORM_2','FORM_3','FORM_4','LOWER_6','UPPER_6') NOT NULL"))
            connection.execute(text("ALTER TABLE students MODIFY admission_year INT NOT NULL"))
            connection.execute(text("ALTER TABLE student_enrollments MODIFY class_name_snapshot VARCHAR(60) NOT NULL"))
            connection.execute(text("ALTER TABLE student_enrollments MODIFY form_level ENUM('FORM_1','FORM_2','FORM_3','FORM_4','LOWER_6','UPPER_6') NOT NULL"))
            connection.execute(text("ALTER TABLE student_enrollments MODIFY academic_level ENUM('O_LEVEL','A_LEVEL') NOT NULL"))
        else:
            for table, column in (
                ("classes", "form_level"), ("students", "admission_year"),
                ("student_enrollments", "class_name_snapshot"),
                ("student_enrollments", "form_level"),
                ("student_enrollments", "academic_level"),
            ):
                connection.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL"))


def year_number(year: AcademicYear) -> int:
    match = re.search(r"(?:19|20)\d{2}", year.name or "")
    if match:
        return int(match.group(0))
    if year.start_date:
        return year.start_date.year
    raise RuntimeError(f"Cannot determine the calendar year for academic year {year.name!r}.")


def main() -> None:
    # Count through SQL before mapping the new columns; the current ORM already
    # knows about them, while an unmigrated database quite correctly does not.
    with engine.connect() as connection:
        before = {
            "students": connection.execute(text("SELECT COUNT(*) FROM students")).scalar_one(),
            "results": connection.execute(text("SELECT COUNT(*) FROM results")).scalar_one(),
        }
    add_columns()

    with SessionLocal() as db:
        classes = {row.id: row for row in db.query(SchoolClass).all()}
        for school_class in classes.values():
            if school_class.form_level is None:
                school_class.form_level = form_from_name(school_class.name, school_class.level.value)

        for enrollment in db.query(StudentEnrollment).all():
            school_class = classes.get(enrollment.class_id)
            if school_class is None:
                raise RuntimeError(f"Enrollment {enrollment.id} has no class to snapshot.")
            enrollment.class_name_snapshot = enrollment.class_name_snapshot or school_class.name
            enrollment.form_level = enrollment.form_level or school_class.form_level
            enrollment.academic_level = enrollment.academic_level or school_class.level

        years = {row.id: row for row in db.query(AcademicYear).all()}
        for student in db.query(Student).all():
            if student.admission_year is None:
                first = (
                    db.query(StudentEnrollment)
                    .filter(StudentEnrollment.student_id == student.id)
                    .order_by(StudentEnrollment.academic_year_id, StudentEnrollment.id)
                    .first()
                )
                student.admission_year = (
                    year_number(years[first.academic_year_id])
                    if first else student.created_at.year
                )
        db.commit()

    require_columns()
    Base.metadata.create_all(bind=engine, tables=[EnrollmentAudit.__table__])
    with SessionLocal() as db:
        after = {"students": db.query(Student).count(), "results": db.query(Result).count()}
        if after != before:
            raise RuntimeError(f"Integrity check failed: before={before}, after={after}")
        print(f"Progression migration complete. Preserved counts: {after}")


if __name__ == "__main__":
    main()
