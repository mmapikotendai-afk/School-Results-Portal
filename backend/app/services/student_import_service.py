"""Bulk student enrollment from a CSV file.

This is the administrator's import, and it is deliberately not the teacher's.
The teacher's CSV carries marks for students who already exist; this one
creates the students themselves, their portal accounts and their first subject
enrollments. Keeping them apart is what stops a marks file ever creating a
learner, or an enrollment file ever touching a result.

The class, the academic year and the subject list come from the screen, not
from the file. The file carries only who the students are. A class column in
the CSV would let one careless row put a Form 1 learner into Upper 6, and the
administrator would have no reason to look for it - so the column does not
exist, and the selected class is applied to every row.

Nothing is written until the whole file is valid. A partly applied import is
worse than a refused one: the administrator cannot tell which half landed, and
re-uploading would collide with the students already created.
"""

import csv
import io
import uuid
from datetime import timedelta
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.enums import Gender
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.subject import Subject
from app.schemas.people import (
    StudentImportReport,
    StudentImportRow,
    StudentImportResult,
    StudentImportRowError,
)
from app.schemas.people import StudentCreate
from app.services.academic_service import AcademicService
from app.services.people_service import StudentService
from app.services.student_credentials_service import StudentCredentialsService, utcnow

# Accepted spellings of each column, lowercased and stripped. Being generous
# here costs nothing and saves an administrator re-exporting a spreadsheet.
COLUMN_ALIASES = {
    "first_name": {"first_name", "firstname", "first name", "given name", "given_name"},
    "last_name": {
        "last_name", "lastname", "last name", "surname", "family name", "family_name",
    },
    "date_of_birth": {
        "date_of_birth", "dateofbirth", "date of birth", "dob", "birth date",
        "birth_date", "birthdate",
    },
    "gender": {"gender", "sex"},
}

REQUIRED_COLUMNS = ("first_name", "last_name", "date_of_birth", "gender")

TEMPLATE_COLUMNS = [
    "first_name",
    "last_name",
    "date_of_birth",
    "gender",
]

# Two rows of example data, so the shape of each column is obvious without
# reading any documentation. The administrator replaces them.
TEMPLATE_EXAMPLES = [
    ["Tendai", "Mapiko", "2009-05-14", "Male"],
    ["Rudo", "Chikore", "2009-02-11", "Female"],
]

# A spreadsheet saved from Excel often carries a UTF-8 BOM; utf-8-sig eats it.
ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

MAX_UPLOAD_BYTES = 2 * 1024 * 1024

# One class at a time. Well above any real class, and low enough that the
# import finishes inside a single request while keeping one class atomic.
MAX_ROWS = 300

GENDER_WORDS = {
    "male": Gender.MALE, "m": Gender.MALE, "boy": Gender.MALE,
    "female": Gender.FEMALE, "f": Gender.FEMALE, "girl": Gender.FEMALE,
}

# Day-first before month-first: a school in Zimbabwe writes 05/14/2009 never,
# and 14/05/2009 often. ISO is tried first and is what the template produces.
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d")


def decode(raw: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Decode an uploaded file, trying the encodings a school actually produces."""
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return None, "The file could not be read as text. Save it as CSV (UTF-8) and try again."


def resolve_columns(fieldnames: List[str]) -> Tuple[Dict[str, str], Optional[str]]:
    """Map the file's headers onto the columns we need."""
    if not fieldnames:
        return {}, "The file has no header row."

    mapping: Dict[str, str] = {}
    forbidden = {
        header.strip().lower().lstrip("ï»¿")
        for header in fieldnames
        if header and header.strip().lower().lstrip("ï»¿") in {
            "email", "email_address", "email address", "e-mail", "mail"
        }
    }
    if forbidden:
        return {}, (
            "Student email is not part of admissions. Remove the email column and "
            "use first_name,last_name,date_of_birth,gender."
        )
    for header in fieldnames:
        if header is None:
            continue
        key = header.strip().lower().lstrip("﻿")
        for canonical, aliases in COLUMN_ALIASES.items():
            if key in aliases and canonical not in mapping:
                mapping[canonical] = header

    missing = [c for c in REQUIRED_COLUMNS if c not in mapping]
    if missing:
        found = ", ".join(h for h in fieldnames if h) or "nothing"
        return {}, (
            f"The file is missing a {' and '.join(missing)} column. "
            f"Found: {found}. Download the template to get the right headings."
        )
    return mapping, None


def parse_date(raw: str) -> Tuple[Optional[date], Optional[str]]:
    """Turn a cell into a date of birth, or explain why it is not one."""
    text = (raw or "").strip()
    if not text:
        return None, None  # optional

    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        if parsed > date.today():
            return None, f"Date of birth {text} is in the future."
        if parsed.year < 1900:
            return None, f"Date of birth {text} is not a real date."
        return parsed, None

    return None, (
        f"{text!r} is not a date we recognise. Use 2009-05-14 or 14/05/2009."
    )


def parse_gender(raw: str) -> Tuple[Optional[Gender], Optional[str]]:
    text = (raw or "").strip().lower()
    if not text:
        return None, None  # optional
    value = GENDER_WORDS.get(text)
    if value is None:
        return None, f"{raw.strip()!r} is not a gender. Use Male or Female."
    return value, None


def build_template(school_class: Optional[SchoolClass] = None) -> str:
    """The CSV an administrator fills in.

    Carries no class column on purpose: the class is chosen on screen and
    applies to the whole file.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(TEMPLATE_COLUMNS)
    for row in TEMPLATE_EXAMPLES:
        writer.writerow(row)
    return buffer.getvalue()


class StudentImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.students = StudentService(db)
        self.academic = AcademicService(db)

    # ------------------------------------------------------------ context

    def describe_target(
        self, class_id: int, academic_year_id: Optional[int], subject_ids: Sequence[int]
    ) -> Tuple[Optional[SchoolClass], Optional[int], List[str], Optional[str]]:
        """Resolve and check what the administrator chose on screen.

        Returns (class, year_id, subject_names, error).
        """
        school_class = (
            self.db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        )
        if school_class is None:
            return None, None, [], "Choose a class to import these students into."

        year_id = self.academic.resolve_year_id(academic_year_id)
        if year_id is None:
            return None, None, [], (
                "There is no current academic year. Set one before importing "
                "students, or the subject enrollments have no year to belong to."
            )

        subject_ids = [int(s) for s in subject_ids or []]
        if subject_ids:
            valid, problem = self.students.valid_subject_ids(subject_ids, school_class.level)
            if not valid:
                return None, None, [], problem

        names = [
            row.name
            for row in self.db.query(Subject.name)
            .filter(Subject.id.in_(subject_ids))
            .order_by(Subject.name)
            .all()
        ] if subject_ids else []

        return school_class, year_id, names, None

    # --------------------------------------------------------- validation

    def _existing_people(self) -> set:
        return {
            (row.first_name.strip().casefold(), row.last_name.strip().casefold(), row.date_of_birth)
            for row in self.db.query(Student).all()
            if row.date_of_birth is not None
        }

    def validate(
        self,
        raw: bytes,
        school_class: SchoolClass,
        year_id: int,
        subject_names: List[str],
        check_deliverable: bool = False,
    ) -> StudentImportReport:
        """Read the file and report on every row, without writing anything."""
        report = StudentImportReport(
            class_id=school_class.id,
            class_name=school_class.name,
            academic_year_id=year_id,
            subjects=subject_names,
        )

        def fail(message: str) -> StudentImportReport:
            report.errors.append(StudentImportRowError(row=0, message=message))
            report.detail = message
            report.can_import = False
            return report

        if len(raw) > MAX_UPLOAD_BYTES:
            return fail("The file must be 2 MB or smaller.")

        text, decode_error = decode(raw)
        if decode_error:
            return fail(decode_error)

        try:
            reader = csv.DictReader(io.StringIO(text))
            fieldnames = reader.fieldnames or []
            raw_rows = list(reader)
        except csv.Error as exc:
            return fail(f"The file is not valid CSV: {exc}")

        mapping, column_error = resolve_columns(fieldnames)
        if column_error:
            return fail(column_error)

        existing_people = self._existing_people()
        seen_people: Dict[tuple, int] = {}

        for index, row in enumerate(raw_rows, start=2):  # line 1 is the header
            if index - 1 > MAX_ROWS:
                report.errors.append(
                    StudentImportRowError(
                        row=index,
                        message=(
                            f"The file has more than {MAX_ROWS} rows. Import one "
                            "class at a time."
                        ),
                    )
                )
                break

            def cell(key: str) -> str:
                header = mapping.get(key)
                return (row.get(header) or "").strip() if header else ""

            # A leading apostrophe is how a spreadsheet marks a cell as text.
            first_name = cell("first_name")
            last_name = cell("last_name")
            dob_raw = cell("date_of_birth")
            gender_raw = cell("gender")

            # A wholly blank line is padding, not an error.
            if not any((first_name, last_name, dob_raw, gender_raw)):
                continue

            report.total_rows += 1
            entry = StudentImportRow(
                row=index,
                student_number="Generated on confirmation",
                first_name=first_name,
                last_name=last_name,
            )

            def reject(message: str, entry=entry, index=index) -> None:
                entry.valid = False
                entry.message = message
                report.rows.append(entry)
                report.errors.append(
                    StudentImportRowError(
                        row=index, message=message
                    )
                )

            if not first_name:
                reject("No first name given.")
                continue
            if not last_name:
                reject("No last name given.")
                continue

            dob, dob_error = parse_date(dob_raw)
            if dob_error:
                reject(dob_error)
                continue

            gender, gender_error = parse_gender(gender_raw)
            if gender_error:
                reject(gender_error)
                continue

            if dob is None:
                reject("No date of birth given.")
                continue
            if gender is None:
                reject("No gender given.")
                continue

            person_key = (first_name.casefold(), last_name.casefold(), dob)
            if person_key in existing_people:
                reject("A student with this exact name and date of birth already exists. Verify the record before admitting them again.")
                continue
            if person_key in seen_people:
                reject(f"This exact name and date of birth also appears on row {seen_people[person_key]}.")
                continue
            seen_people[person_key] = index

            entry.date_of_birth = dob
            entry.gender = gender
            entry.valid = True
            entry.message = "Valid"
            report.rows.append(entry)

        report.accepted = sum(1 for r in report.rows if r.valid)
        report.rejected = len(report.errors)

        if report.rejected:
            report.can_import = False
            report.detail = (
                f"{report.rejected} row{'' if report.rejected == 1 else 's'} must be "
                "corrected before any student is added. Nothing has been imported."
            )
            return report

        if not report.accepted:
            report.can_import = False
            report.detail = "The file contained no students."
            return report

        report.can_import = True
        report.detail = (
            f"{report.accepted} student{'' if report.accepted == 1 else 's'} ready to "
            f"import into {school_class.name}. Nothing has been created yet."
        )
        return report

    # ------------------------------------------------------------- saving

    def commit(
        self,
        report: StudentImportReport,
        school_class: SchoolClass,
        year_id: int,
        subject_ids: Sequence[int],
        subject_names: List[str],
        actor_user_id: int,
    ) -> StudentImportResult:
        """Create the validated class and return one-time printable slips."""
        result = StudentImportResult(
            class_id=school_class.id,
            class_name=school_class.name,
            academic_year_id=year_id,
            subjects=subject_names,
        )

        credentials = StudentCredentialsService(self.db)
        subject_ids = [int(s) for s in subject_ids or []]
        batch_id = str(uuid.uuid4())
        expires_at = utcnow() + timedelta(minutes=10)

        for entry in report.rows:
            if not entry.valid:
                continue

            payload = StudentCreate(
                first_name=entry.first_name,
                last_name=entry.last_name,
                date_of_birth=entry.date_of_birth,
                gender=entry.gender,
                class_id=school_class.id,
                subject_ids=subject_ids,
                academic_year_id=year_id,
            )

            student, password, error = self.students.create(payload, commit=False)
            if error or student is None:
                self.db.rollback()
                raise ValueError(error or f"Row {entry.row} could not be created.")

            result.students_created += 1
            result.enrollments_created += len(subject_ids)

            slip = credentials.issue_slip(
                student, password, actor_user_id, "BULK_ISSUED", batch_id, expires_at
            )
            result.credentials.append(slip)
            del password

            result.credentials_issued += 1

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError(
                "The class list changed while it was being imported. No students were added; preview the file again."
            ) from exc
        result.batch_id = batch_id
        result.expires_at = expires_at
        result.detail = (
            f"{result.students_created} student{'' if result.students_created == 1 else 's'} "
            f"added to {school_class.name}. Print the credentials once before they expire."
        )
        return result
