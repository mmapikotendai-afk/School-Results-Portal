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
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.enums import Gender
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.subject import Subject
from app.models.user import User
from app.schemas.people import (
    StudentImportReport,
    StudentImportRow,
    StudentImportResult,
    StudentImportRowError,
)
from app.schemas.people import StudentCreate
from app.services import email_service
from app.services.academic_service import AcademicService
from app.services.people_service import StudentService
from app.services.provisioning_service import ProvisioningService

# Accepted spellings of each column, lowercased and stripped. Being generous
# here costs nothing and saves an administrator re-exporting a spreadsheet.
COLUMN_ALIASES = {
    "student_number": {
        "student_number", "studentnumber", "student number", "student no",
        "student_no", "studentno", "candidate number", "candidate_number", "number",
    },
    "first_name": {"first_name", "firstname", "first name", "given name", "given_name"},
    "last_name": {
        "last_name", "lastname", "last name", "surname", "family name", "family_name",
    },
    "email": {"email", "email_address", "email address", "e-mail", "mail"},
    "date_of_birth": {
        "date_of_birth", "dateofbirth", "date of birth", "dob", "birth date",
        "birth_date", "birthdate",
    },
    "gender": {"gender", "sex"},
}

REQUIRED_COLUMNS = ("student_number", "first_name", "last_name", "email")

TEMPLATE_COLUMNS = [
    "student_number",
    "first_name",
    "last_name",
    "email",
    "date_of_birth",
    "gender",
]

# Two rows of example data, so the shape of each column is obvious without
# reading any documentation. The administrator replaces them.
TEMPLATE_EXAMPLES = [
    ["STU-001", "Tendai", "Mapiko", "tendai@example.com", "2009-05-14", "Male"],
    ["STU-002", "Rudo", "Chikore", "rudo@example.com", "2009-02-11", "Female"],
]

# A spreadsheet saved from Excel often carries a UTF-8 BOM; utf-8-sig eats it.
ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

MAX_UPLOAD_BYTES = 2 * 1024 * 1024

# One class at a time. Well above any real class, and low enough that the
# import finishes inside a single request even with an email per student.
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
            valid, problem = self.students.valid_subject_ids(subject_ids)
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

    def _existing_students(self) -> Dict[str, Tuple[int, Optional[str]]]:
        """Every student number already taken, with the class that holds it.

        Loaded once rather than queried per row, and the class name is carried
        along so a clash can say where the number already sits instead of only
        that it is taken.
        """
        rows = (
            self.db.query(Student.student_number, SchoolClass.name)
            .outerjoin(SchoolClass, Student.class_id == SchoolClass.id)
            .all()
        )
        return {r[0].strip().upper(): (0, r[1]) for r in rows}

    def _existing_emails(self) -> set:
        return {
            (row[0] or "").strip().lower()
            for row in self.db.query(User.email).all()
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

        taken_numbers = self._existing_students()
        taken_emails = self._existing_emails()

        seen_numbers: Dict[str, int] = {}
        seen_emails: Dict[str, int] = {}

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
            number = cell("student_number").lstrip("'").strip()
            first_name = cell("first_name")
            last_name = cell("last_name")
            email = cell("email").lower()
            dob_raw = cell("date_of_birth")
            gender_raw = cell("gender")

            # A wholly blank line is padding, not an error.
            if not any((number, first_name, last_name, email, dob_raw, gender_raw)):
                continue

            report.total_rows += 1
            entry = StudentImportRow(
                row=index,
                student_number=number or "-",
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

            def reject(message: str, entry=entry, number=number, index=index) -> None:
                entry.valid = False
                entry.message = message
                report.rows.append(entry)
                report.errors.append(
                    StudentImportRowError(
                        row=index, student_number=number or None, message=message
                    )
                )

            if not number:
                reject("No student number given.")
                continue
            if not first_name:
                reject("No first name given.")
                continue
            if not last_name:
                reject("No last name given.")
                continue

            key = number.upper()
            if key in seen_numbers:
                reject(f"Student number appears twice in this file (also on row {seen_numbers[key]}).")
                continue
            seen_numbers[key] = index

            if key in taken_numbers:
                _, held_by = taken_numbers[key]
                where = f" It is already in {held_by}." if held_by else ""
                reject(
                    f"Student number {number} already belongs to another student.{where}"
                )
                continue

            if not email:
                reject("No email address given. Credentials are sent there.")
                continue

            problem = email_service.address_problem(email, check_deliverable)
            if problem:
                reject(problem)
                continue

            if email in seen_emails:
                reject(f"Email appears twice in this file (also on row {seen_emails[email]}).")
                continue
            seen_emails[email] = index

            if email in taken_emails:
                reject(f"An account already exists for {email}.")
                continue

            dob, dob_error = parse_date(dob_raw)
            if dob_error:
                reject(dob_error)
                continue

            gender, gender_error = parse_gender(gender_raw)
            if gender_error:
                reject(gender_error)
                continue

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
    ) -> StudentImportResult:
        """Create every student in a validated report, then email each one.

        Creation and delivery are separated deliberately. A student whose
        credentials could not be emailed is kept, not discarded: unlike a
        single add, where the administrator is standing there and can correct
        the address, a failure here would silently drop one learner out of a
        class of forty. The import reports the failures and the administrator
        resends, which issues a fresh password.
        """
        result = StudentImportResult(
            class_id=school_class.id,
            class_name=school_class.name,
            academic_year_id=year_id,
            subjects=subject_names,
        )

        provisioning = ProvisioningService(self.db)
        subject_ids = [int(s) for s in subject_ids or []]

        for entry in report.rows:
            if not entry.valid:
                continue

            payload = StudentCreate(
                student_number=entry.student_number,
                first_name=entry.first_name,
                last_name=entry.last_name,
                email=entry.email,
                date_of_birth=entry.date_of_birth,
                gender=entry.gender,
                class_id=school_class.id,
                subject_ids=subject_ids,
                academic_year_id=year_id,
            )

            student, password, error = self.students.create(payload)
            if error or student is None:
                # The roll can change between validating and confirming.
                result.failed.append(
                    StudentImportRowError(
                        row=entry.row, student_number=entry.student_number, message=error or "Could not be created."
                    )
                )
                continue

            result.students_created += 1
            result.enrollments_created += len(subject_ids)

            delivery = provisioning.deliver_new_credentials(student.user, password)
            del password

            if delivery.sent:
                result.credentials_sent += 1
            else:
                result.credentials_failed += 1
                result.undelivered.append(
                    StudentImportRowError(
                        row=entry.row,
                        student_number=entry.student_number,
                        message=f"{entry.email}: {delivery.error or delivery.detail}",
                    )
                )

        parts = [f"{result.students_created} student{'' if result.students_created == 1 else 's'} added to {school_class.name}"]
        if result.credentials_failed:
            parts.append(
                f"{result.credentials_failed} could not be emailed - use Resend on those rows"
            )
        result.detail = ". ".join(parts) + "."
        return result
