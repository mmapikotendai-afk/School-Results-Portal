"""Exporting a mark sheet as CSV and as PDF."""

import csv
import io
import re
from datetime import datetime
from typing import Optional

from fpdf import FPDF

from app.schemas.teacher_view import MarkSheet
from app.services.csv_export_service import spreadsheet_safe
from app.utils.pdf import draw_logo

# Core PDF fonts are Latin-1 only. Rather than ship a Unicode font file, text
# is folded to the nearest ASCII so a stray curly quote cannot break an export.
_REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "·": "-", "…": "...",
}


def _ascii(text: Optional[str]) -> str:
    if not text:
        return ""
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def safe_filename(*parts: str) -> str:
    """Build a download filename that every operating system will accept."""
    joined = "-".join(p for p in parts if p)
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", joined).strip("-")
    return cleaned or "export"


def marksheet_to_csv(sheet: MarkSheet) -> str:
    """The mark sheet as CSV.

    Deliberately the same shape as the upload template, so a downloaded sheet
    can be edited and uploaded straight back.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["student_number", "student_name", "marks", "grade", "remarks"])
    for row in sheet.rows:
        writer.writerow([spreadsheet_safe(cell) for cell in (
            row.student_number,
            row.student_name,
            "" if row.marks is None else f"{row.marks:.2f}",
            row.grade or "",
            row.remarks or "",
        )])
    return buffer.getvalue()


class MarkSheetPDF(FPDF):
    """A mark sheet with the school masthead repeated on every page."""

    def __init__(self, sheet: MarkSheet, school_name: str, logo_path: Optional[str] = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.sheet = sheet
        self.school_name = _ascii(school_name)
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=18)

    def header(self) -> None:
        draw_logo(self, self.logo_path, x=12, y=10, h=14)

        self.set_font("Helvetica", "B", 14)
        self.cell(0, 7, self.school_name, align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 10)
        self.cell(0, 5, "Subject Mark Sheet", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "B", 11)
        title = f"{_ascii(self.sheet.subject_name)} ({_ascii(self.sheet.subject_code)})"
        self.cell(0, 6, title, align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 9)
        context = " - ".join(
            filter(
                None,
                [
                    _ascii(self.sheet.examination_name),
                    _ascii(self.sheet.term_name),
                    _ascii(self.sheet.academic_year_name),
                ],
            )
        )
        self.cell(0, 5, context, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self._table_head()

    def _table_head(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(232, 236, 244)
        for label, width, align in self._columns():
            self.cell(width, 7, label, border=1, align=align, fill=True)
        self.ln()

    @staticmethod
    def _columns():
        # (heading, width in mm, alignment) - widths total the printable area.
        return [
            ("#", 10, "C"),
            ("Student number", 38, "L"),
            ("Student name", 62, "L"),
            ("Mark", 18, "C"),
            ("Grade", 16, "C"),
            ("Remarks", 42, "L"),
        ]

    def body(self) -> None:
        self.set_font("Helvetica", "", 9)
        fill = False
        for index, row in enumerate(self.sheet.rows, start=1):
            # Repeat the column headings when the table breaks across a page.
            if self.will_page_break(7):
                self.add_page()

            self.set_fill_color(247, 249, 252)
            values = [
                (str(index), 10, "C"),
                (_ascii(row.student_number), 38, "L"),
                (_ascii(row.student_name)[:38], 62, "L"),
                ("-" if row.marks is None else f"{row.marks:.0f}", 18, "C"),
                (row.grade or "-", 16, "C"),
                (_ascii(row.remarks)[:26], 42, "L"),
            ]
            for text, width, align in values:
                self.cell(width, 6.5, text, border=1, align=align, fill=fill)
            self.ln()
            fill = not fill

    def summary(self) -> None:
        self.ln(4)
        self.set_font("Helvetica", "", 9)
        marked = [r for r in self.sheet.rows if r.marks is not None]
        average = sum(float(r.marks) for r in marked) / len(marked) if marked else None

        lines = [
            f"Enrolled: {self.sheet.expected_count}",
            f"Marked: {len(marked)}",
            f"Outstanding: {self.sheet.expected_count - len(marked)}",
        ]
        if average is not None:
            lines.append(f"Average: {average:.1f}")
        self.cell(0, 5, "   ".join(lines), new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 118, 132)
        stamp = datetime.now().strftime("%d %B %Y at %H:%M")
        status = self.sheet.status.value.replace("_", " ").title()
        self.cell(
            0, 5, f"Status: {status}. Generated {stamp}.", new_x="LMARGIN", new_y="NEXT"
        )
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 137, 150)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="C")


def marksheet_to_pdf(
    sheet: MarkSheet, school_name: str, logo_path: Optional[str] = None
) -> bytes:
    """Render the mark sheet as a PDF."""
    pdf = MarkSheetPDF(sheet, school_name, logo_path)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.body()
    pdf.summary()
    return bytes(pdf.output())


def student_results_to_csv(entry, student_name: str, student_number: str, class_name: str) -> str:
    """One published examination as CSV, for the student's own records."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    writer.writerow(["Student", spreadsheet_safe(student_name)])
    writer.writerow(["Student number", spreadsheet_safe(student_number)])
    writer.writerow(["Class", spreadsheet_safe(class_name or "")])
    writer.writerow(["Examination", spreadsheet_safe(entry.examination_name)])
    writer.writerow(["Term", spreadsheet_safe(entry.term_name or "")])
    writer.writerow(["Academic year", spreadsheet_safe(entry.academic_year_name or "")])
    writer.writerow([])

    writer.writerow(["subject_code", "subject", "marks", "grade", "remarks"])
    for row in entry.results:
        writer.writerow([spreadsheet_safe(cell) for cell in (
            row.subject_code, row.subject_name,
            f"{row.marks:.2f}", row.grade or "", row.remarks or "",
        )])

    writer.writerow([])
    writer.writerow(["Subjects taken", entry.subjects_taken])
    if entry.average is not None:
        writer.writerow(["Average", entry.average])
    return buffer.getvalue()


class ReportCardPDF(FPDF):
    """A student's statement of results, on the school's own letterhead."""

    def __init__(self, entry, student, school_name: str, logo_path: Optional[str] = None,
                 motto: Optional[str] = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.entry = entry
        self.student = student
        self.school_name = _ascii(school_name)
        self.motto = _ascii(motto or "")
        self.logo_path = logo_path
        self.set_auto_page_break(auto=True, margin=20)

    def header(self) -> None:
        draw_logo(self, self.logo_path, x=12, y=10, h=16)

        self.set_font("Helvetica", "B", 16)
        self.cell(0, 8, self.school_name, align="C", new_x="LMARGIN", new_y="NEXT")
        if self.motto:
            self.set_font("Helvetica", "I", 9)
            self.cell(0, 5, self.motto, align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "B", 11)
        self.cell(0, 7, "STATEMENT OF RESULTS", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_draw_color(180, 188, 200)
        self.line(12, self.get_y(), 198, self.get_y())
        self.ln(4)

    def identity(self) -> None:
        """Who this is for, and which examination - the two facts that make a
        loose printed page unambiguous."""
        self.set_font("Helvetica", "", 10)
        rows = [
            ("Student", _ascii(self.student["name"])),
            ("Student number", _ascii(self.student["number"])),
            ("Class", _ascii(self.student.get("class_name") or "-")),
            ("Examination", _ascii(self.entry.examination_name)),
            ("Term", _ascii(self.entry.term_name or "-")),
            ("Academic year", _ascii(self.entry.academic_year_name or "-")),
        ]
        for label, value in rows:
            self.set_font("Helvetica", "", 9)
            self.set_text_color(110, 118, 132)
            self.cell(38, 6, label)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(0, 0, 0)
            self.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def results_table(self) -> None:
        columns = [("Subject", 78, "L"), ("Code", 24, "C"),
                   ("Mark", 20, "C"), ("Grade", 20, "C"), ("Remark", 44, "L")]

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(232, 236, 244)
        for label, width, align in columns:
            self.cell(width, 7, label, border=1, align=align, fill=True)
        self.ln()

        self.set_font("Helvetica", "", 9)
        fill = False
        self.set_fill_color(247, 249, 252)
        for row in self.entry.results:
            if self.will_page_break(7):
                self.add_page()
            values = [
                (_ascii(row.subject_name)[:44], 78, "L"),
                (_ascii(row.subject_code), 24, "C"),
                (f"{row.marks:.0f}", 20, "C"),
                (row.grade or "-", 20, "C"),
                (_ascii(row.remarks)[:26], 44, "L"),
            ]
            for text, width, align in values:
                self.cell(width, 6.5, text, border=1, align=align, fill=fill)
            self.ln()
            fill = not fill

    def summary(self) -> None:
        self.ln(4)
        self.set_font("Helvetica", "B", 10)
        parts = [f"Subjects taken: {self.entry.subjects_taken}"]
        if self.entry.average is not None:
            parts.append(f"Average: {self.entry.average:.2f}")
        if self.entry.best_subject:
            parts.append(f"Best subject: {_ascii(self.entry.best_subject)}")
        self.cell(0, 6, "     ".join(parts), new_x="LMARGIN", new_y="NEXT")

        self.ln(2)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(110, 118, 132)
        published = (
            self.entry.published_at.strftime("%d %B %Y")
            if self.entry.published_at
            else "-"
        )
        self.multi_cell(
            0, 4.5,
            f"Published by the school on {published}. Only subjects the student is "
            "enrolled in appear on this statement.",
        )
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-16)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 137, 150)
        stamp = datetime.now().strftime("%d %b %Y %H:%M")
        self.cell(0, 5, f"{self.school_name}  -  generated {stamp}  -  page {self.page_no()}",
                  align="C")


def student_results_to_pdf(entry, student: dict, school_name: str,
                           logo_path: Optional[str] = None,
                           motto: Optional[str] = None) -> bytes:
    """Render one published examination as a printable statement of results."""
    pdf = ReportCardPDF(entry, student, school_name, logo_path, motto)
    pdf.add_page()
    pdf.identity()
    pdf.results_table()
    pdf.summary()
    return bytes(pdf.output())
