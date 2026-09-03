"""CSV result import: parse, validate, preview, then commit or reject as a whole.

The validation rules are the product requirements, restated as code:

  1.  the file must be readable CSV
  2.  the required columns must be present
  3.  the student number must exist
  4.  the student account must be active
  5.  the student must be enrolled in the selected subject
  6.  the teacher must be authorised for the subject (enforced at the route)
  7.  the mark must be numeric
  8.  the mark must be between 0 and 100
  9.  a student number must not appear twice in one file
  10. a mark already on record is detected and reported before it is replaced
  11. the examination must be accepting submissions (enforced at the route)
  12. the student, subject and examination combination must be valid

Every row is reported either way, valid or not, so the teacher gets a full
preview table rather than a list of complaints. A file is committed whole or
not at all: a partial apply would leave them unable to tell which half of
their spreadsheet had landed.
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import Dict, List, NamedTuple, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.enums import EducationLevel
from app.models.examination import Examination
from app.models.result import Result, ResultAuditLog
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.teacher_view import PreviewRow, RowError, UploadReport
from app.services.grading_service import GradingService
from app.services.submission_service import SubmissionService
from app.services.teacher_portal_service import TeacherPortalService
from app.services.csv_export_service import spreadsheet_safe

# Marks are held as a percentage, so the scale is fixed here rather than per
# subject. A school marking out of something else converts before uploading.
MAX_MARKS = Decimal("100")

# Accepted spellings of each column, lowercased and stripped. Being generous
# here costs nothing and saves a teacher re-exporting their spreadsheet.
# student_name is deliberately absent: the name is never read back.
COLUMN_ALIASES = {
    "student_number": {
        "student_number", "studentnumber", "student number", "student no",
        "student_no", "studentno", "candidate number", "candidate_number", "number",
    },
    "marks": {"marks", "mark", "score", "scores", "result", "results", "grade_mark"},
    "remarks": {"remarks", "remark", "comment", "comments", "note", "notes"},
}

# The template carries exactly three columns. student_number is the matching
# key; student_name is there only so a teacher can see who they are marking and
# is ignored on the way back in; marks is the column to fill.
#
# A remarks column is still accepted on upload if a school chooses to add one,
# but it is not part of the template a teacher is handed.
TEMPLATE_COLUMNS = ["student_number", "student_name", "marks"]

# A spreadsheet saved from Excel often carries a UTF-8 BOM; utf-8-sig eats it.
ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000


class KnownStudent(NamedTuple):
    """A student as the importer needs them while validating."""

    id: int
    name: str
    is_active: bool


def decode(raw: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Decode an uploaded file, trying the encodings a school actually produces."""
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return None, "The file could not be read as text. Save it as CSV (UTF-8) and try again."


def resolve_columns(fieldnames: List[str]) -> Tuple[Dict[str, str], Optional[str]]:
    """Map the file's headers onto the columns we need.

    Returns (mapping, error). The mapping is canonical name -> actual header,
    so the rest of the import never has to think about spelling.
    """
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

    missing = [c for c in ("student_number", "marks") if c not in mapping]
    if missing:
        found = ", ".join(h for h in fieldnames if h) or "nothing"
        return {}, (
            f"The file is missing a {' and '.join(missing)} column. "
            f"Found: {found}. Download the template to get the right headings."
        )
    return mapping, None


def parse_marks(raw: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """Turn a cell into a mark, or explain why it is not one."""
    text = (raw or "").strip()
    if not text:
        return None, "No mark given."

    # Tolerate a trailing percent sign and thousands separators.
    text = text.replace("%", "").replace(",", "").strip()

    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None, f"{raw.strip()!r} is not a number."

    if value.is_nan() or value.is_infinite():
        return None, f"{raw.strip()!r} is not a valid mark."
    if value < 0 or value > MAX_MARKS:
        return None, f"Mark must be between 0 and {MAX_MARKS:.0f}."

    return round(value, 2), None


class ResultImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portal = TeacherPortalService(db)
        # One grading service for the whole file, so the scale is read once
        # rather than once per student.
        self.grading = GradingService(db)

    def build_template(
        self, students: List[Student], subject: Subject, exam: Examination
    ) -> str:
        """A CSV pre-filled with the roll for one subject and examination.

        Pre-filling the student numbers is what makes matching reliable: they
        come back exactly as they went out, with no chance of a typo. The name
        is written alongside purely so the teacher can see who each row is; it
        is never read back, and never used to identify anybody.

            student_number,student_name,marks
            STU-001,Tendai Mapiko,
            STU-002,John Doe,
        """
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(TEMPLATE_COLUMNS)
        for student in students:
            # The name is decoration on this file, but it is still somebody's
            # typed text landing in a spreadsheet, so it gets the same guard.
            writer.writerow(
                [student.student_number, spreadsheet_safe(student.full_name), ""]
            )
        return buffer.getvalue()

    # --------------------------------------------------------- validation

    def _known_students(self) -> Dict[str, KnownStudent]:
        """Every student in the school, so each failure gets a precise reason.

        Without this, an unknown number and a withdrawn learner would produce
        the same unhelpful message.
        """
        rows = (
            self.db.query(Student)
            .options(joinedload(Student.user))
            .join(User, Student.user_id == User.id)
            .all()
        )
        return {
            s.student_number.upper(): KnownStudent(s.id, s.full_name, s.user.is_active)
            for s in rows
        }

    def process(
        self,
        raw: bytes,
        teacher: Teacher,
        user: User,
        exam: Examination,
        subject: Subject,
        validate_only: bool = False,
        allow_replace: bool = False,
        reason: Optional[str] = None,
    ) -> UploadReport:
        """Validate an uploaded file and, unless validating only, commit it.

        A row whose result already exists is never replaced silently. It is
        reported as a replacement, and the import is held until the caller
        passes allow_replace, so overwriting somebody's mark is always a
        decision somebody made rather than a side effect of uploading twice.
        """
        report = UploadReport(validate_only=validate_only, replace_allowed=allow_replace)

        def fail(message: str) -> UploadReport:
            """A problem with the file as a whole, rather than one row."""
            report.errors.append(RowError(row=0, message=message))
            report.detail = message
            report.can_import = False
            return report

        # Rule 1: the file must be readable.
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

        # Rule 2: the required columns must be present.
        mapping, column_error = resolve_columns(fieldnames)
        if column_error:
            return fail(column_error)

        year_id = exam.term.academic_year_id
        # Rules 5 and 12: the enrolment roll is the authority on who may be marked.
        enrolled = {
            s.student_number.upper(): s
            for s in self.portal.enrolled_students(subject.id, year_id)
        }
        known = self._known_students()

        # Rule 10: what is already on record for this subject and examination.
        existing = {
            r.student_id: r
            for r in self.db.query(Result).filter(
                Result.examination_id == exam.id, Result.subject_id == subject.id
            )
        }

        accepted: Dict[int, Tuple[Decimal, Optional[str]]] = {}
        seen: Dict[str, int] = {}

        for index, row in enumerate(raw_rows, start=2):  # line 1 is the header
            if index - 1 > MAX_ROWS:
                report.errors.append(
                    RowError(row=index, message=f"The file has more than {MAX_ROWS} rows.")
                )
                break

            # A leading apostrophe is how a spreadsheet marks a cell as text;
            # it is not part of the number, and Excel adds it on its own.
            number = (row.get(mapping["student_number"]) or "").strip().lstrip("'").strip().upper()
            raw_marks = (row.get(mapping["marks"]) or "").strip()
            remarks = (row.get(mapping.get("remarks", "")) or "").strip() or None

            # A wholly blank line is padding, not an error.
            if not number and not raw_marks:
                continue

            report.total_rows += 1
            entry = PreviewRow(
                row=index, student_number=number or "-", raw_marks=raw_marks
            )

            def reject(message: str, entry=entry, number=number, index=index) -> None:
                entry.valid = False
                entry.message = message
                report.rows.append(entry)
                report.errors.append(
                    RowError(row=index, student_number=number or None, message=message)
                )

            if not number:
                reject("No student number given.")
                continue

            # Rule 9: the same student must not appear twice.
            if number in seen:
                reject(f"Appears twice in this file (also on row {seen[number]}).")
                continue
            seen[number] = index

            record = known.get(number)

            # Rule 3: the student number must exist.
            if record is None:
                reject("Student not found.")
                continue

            # The name shown is the one on record, never the one in the file:
            # showing the file's name back would hide a mismatch.
            entry.student_name = record.name

            # Rule 4: the student account must be active.
            if not record.is_active:
                reject(f"{record.name} is no longer an active student.")
                continue

            # Rule 5: the student must be enrolled in this subject.
            student = enrolled.get(number)
            if student is None:
                reject(f"Not enrolled in {subject.name}.")
                continue

            # Rules 7 and 8: the mark must be a number between 0 and 100.
            marks, marks_error = parse_marks(raw_marks)
            if marks_error:
                reject(marks_error)
                continue

            entry.marks = marks
            entry.valid = True

            # Rule 10: flag, but do not reject, a mark already on record.
            previous = existing.get(student.id)
            if previous is not None:
                entry.is_overwrite = True
                entry.existing_marks = previous.marks
                entry.message = f"Valid - replaces the current mark of {previous.marks:.0f}"
                report.overwrites += 1
            else:
                entry.message = "Valid"

            report.rows.append(entry)
            accepted[student.id] = (marks, remarks[:255] if remarks else None)

        report.accepted = len(accepted)
        report.rejected = len(report.errors)

        absent = len(enrolled) - len(accepted)
        if absent > 0 and report.accepted:
            report.warnings.append(
                f"{absent} enrolled student{'' if absent == 1 else 's'} "
                f"{'has' if absent == 1 else 'have'} no mark in this file."
            )
        if report.overwrites:
            report.warnings.append(
                f"{report.overwrites} row{'' if report.overwrites == 1 else 's'} would "
                "replace a mark already recorded. Every change is logged."
            )

        # Nothing is written while anything is wrong.
        if report.rejected:
            report.can_import = False
            report.detail = (
                f"{report.rejected} row{'' if report.rejected == 1 else 's'} could not be "
                "accepted, so nothing was saved. Fix them and upload again."
            )
            return report

        if not accepted:
            report.can_import = False
            report.detail = "The file contained no marks."
            return report

        # Existing results block the import until replacement is confirmed.
        # The rows are valid; what is missing is the decision to overwrite.
        if report.overwrites and not allow_replace:
            report.requires_replace_confirmation = True
            report.can_import = False
            report.detail = (
                f"{report.overwrites} of these students already have a mark for "
                f"{subject.name}. Confirm that you want to replace them."
            )
            return report

        report.can_import = True

        if validate_only:
            replacing = (
                f", {report.overwrites} replacing an existing mark"
                if report.overwrites
                else ""
            )
            report.detail = (
                f"{report.accepted} row{'' if report.accepted == 1 else 's'} ready to "
                f"import{replacing}. Nothing has been saved yet."
            )
            return report

        self._commit(accepted, teacher, user, exam, subject, report, reason)
        return report

    # ------------------------------------------------------------- saving

    def _commit(
        self,
        accepted: Dict[int, Tuple[Decimal, Optional[str]]],
        teacher: Teacher,
        user: User,
        exam: Examination,
        subject: Subject,
        report: UploadReport,
        reason: Optional[str] = None,
    ) -> None:
        """Write the validated marks in a single transaction.

        Validation has already ruled out bad rows, but a constraint violation
        or a dropped connection part-way would otherwise leave half a class
        marked. Anything that goes wrong rolls the whole batch back.
        """
        existing = {
            r.student_id: r
            for r in self.db.query(Result).filter(
                Result.examination_id == exam.id, Result.subject_id == subject.id
            )
        }
        levels = self._levels_for(list(accepted))

        try:
            for student_id, (marks, remarks) in accepted.items():
                level = levels.get(student_id, EducationLevel.O_LEVEL)
                grade, default_remark = self.grading.grade_for(marks, level, MAX_MARKS)
                result = existing.get(student_id)

                if result is None:
                    self.db.add(
                        Result(
                            student_id=student_id,
                            subject_id=subject.id,
                            examination_id=exam.id,
                            marks=marks,
                            grade=grade,
                            remarks=remarks or default_remark,
                            uploaded_by_id=user.id,
                        )
                    )
                    report.created += 1
                    continue

                if result.marks == marks and not remarks:
                    report.unchanged += 1
                    continue

                # Replacing an existing mark is a correction, and every
                # correction is auditable.
                self.db.add(
                    ResultAuditLog(
                        result_id=result.id,
                        changed_by_id=user.id,
                        old_marks=result.marks,
                        new_marks=marks,
                        old_grade=result.grade,
                        new_grade=grade,
                        reason=(reason or "").strip() or "Replaced by a CSV upload",
                    )
                )
                result.marks = marks
                result.grade = grade
                if remarks:
                    result.remarks = remarks
                result.uploaded_by_id = user.id
                report.updated += 1

            self.portal.stamp_submission(exam, teacher, subject.id, user.id)
            self.db.flush()
            SubmissionService(self.db).recalculate(exam, commit=False)
            self.db.commit()
        except SQLAlchemyError:
            # All or nothing: half a class marked is worse than none.
            self.db.rollback()
            report.committed = False
            report.can_import = False
            report.created = report.updated = report.unchanged = 0
            report.detail = (
                "The results could not be saved, and nothing was changed. "
                "Please try again."
            )
            raise

        row = self.portal.tracking_row(exam, teacher, subject.id)
        if row:
            report.status = row.status
            report.submitted_at = row.submitted_at

        report.committed = True
        parts = []
        if report.created:
            parts.append(f"{report.created} added")
        if report.updated:
            parts.append(f"{report.updated} updated")
        if report.unchanged:
            parts.append(f"{report.unchanged} unchanged")
        report.detail = f"Results saved for {subject.name}: {', '.join(parts)}."

    def _levels_for(self, student_ids: List[int]) -> Dict[int, EducationLevel]:
        """Each student's level, which decides the grade band applied."""
        if not student_ids:
            return {}
        rows = self.db.query(Student).filter(Student.id.in_(student_ids)).all()
        return {
            s.id: (s.school_class.level if s.school_class else EducationLevel.O_LEVEL)
            for s in rows
        }


def apply_single_mark(
    db: Session,
    result: Optional[Result],
    student_id: int,
    exam: Examination,
    subject: Subject,
    marks: Decimal,
    remarks: Optional[str],
    user: User,
    level: EducationLevel,
    reason: Optional[str] = None,
    grading: Optional[GradingService] = None,
) -> Tuple[Result, bool]:
    """Create or correct one mark. Returns (result, was_created).

    Shared by the single-row edit and the on-screen mark sheet save, so both
    write the same audit trail, and both grade through the configured scale
    rather than a second copy of the rules.
    """
    grading = grading or GradingService(db)
    grade, default_remark = grading.grade_for(marks, level, MAX_MARKS)

    if result is None:
        created = Result(
            student_id=student_id,
            subject_id=subject.id,
            examination_id=exam.id,
            marks=marks,
            grade=grade,
            remarks=remarks or default_remark,
            uploaded_by_id=user.id,
        )
        db.add(created)
        return created, True

    if result.marks != marks or result.grade != grade:
        db.add(
            ResultAuditLog(
                result_id=result.id,
                changed_by_id=user.id,
                old_marks=result.marks,
                new_marks=marks,
                old_grade=result.grade,
                new_grade=grade,
                reason=reason or "Corrected by the subject teacher",
            )
        )

    result.marks = marks
    result.grade = grade
    if remarks is not None:
        result.remarks = remarks or default_remark
    result.uploaded_by_id = user.id
    return result, False
