"""Print-ready A4 report cards built only from recorded school data."""

from datetime import date
from decimal import Decimal
from typing import Optional

from fpdf import FPDF

from app.services.report_card_service import ReportCard, ReportLine
from app.utils.pdf import draw_logo

PAGE_W, PAGE_H = 210, 297
MARGIN = 9
CONTENT_W = PAGE_W - 2 * MARGIN

NAVY = (24, 70, 108)
NAVY_DARK = (16, 49, 77)
PALE_BLUE = (224, 235, 245)
PALEST_BLUE = (243, 248, 252)
INK = (17, 24, 39)
MUTED = (77, 91, 108)
RULE = (129, 154, 178)

_REPLACEMENTS = {"â€˜": "'", "â€™": "'", "â€œ": '"', "â€": '"', "â€“": "-", "â€”": "-", "Â·": "-", "â€¦": "..."}


def _text(value: object) -> str:
    """Core PDF fonts are Latin-1; keep one unexpected character harmless."""
    if value is None:
        return ""
    text = str(value)
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


def _pretty_enum(value: Optional[str]) -> str:
    return _text(value or "-").replace("_", " ").title()


def _date(value: Optional[date]) -> str:
    return value.strftime("%d %B %Y").upper() if value else "-"


class ReportCardPDF(FPDF):
    """Traditional blue-and-white A4 report card for paper or download."""

    COLUMNS = (("SUBJECT", 73, "L"), ("MARK (%)", 28, "C"), ("GRADE", 31, "C"), ("REMARKS", 60, "L"))

    def __init__(self, card: ReportCard, logo_path: Optional[str] = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.card = card
        self.logo_path = logo_path
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_title(f"{card.student_name} - {card.examination_name}")
        self.set_author(_text(card.school.school_name))

    def _watermark(self) -> None:
        mode = (self.card.school.report_watermark or "name").lower()
        if mode == "none":
            return
        if mode == "logo" and self.logo_path:
            with self.local_context(fill_opacity=0.055, stroke_opacity=0.055):
                if draw_logo(self, self.logo_path, x=45, y=92, w=120):
                    return
        name = _text(self.card.school.school_name).upper()
        if not name:
            return
        self.set_font("Times", "B", 39)
        self.set_text_color(150, 160, 171)
        with self.local_context(fill_opacity=0.055, stroke_opacity=0.055):
            width = self.get_string_width(name)
            self.text((PAGE_W - width) / 2, 190, name)
        self.set_text_color(*INK)

    def _section_bar(self, title: str, height: float = 7.5) -> None:
        y = self.get_y()
        self.set_fill_color(*NAVY)
        self.set_draw_color(*NAVY_DARK)
        self.rect(MARGIN, y, CONTENT_W, height, style="DF")
        self.set_xy(MARGIN + 3, y + 1)
        self.set_font("Times", "B", 10.5)
        self.set_text_color(255, 255, 255)
        self.cell(CONTENT_W - 6, height - 2, _text(title).upper())
        self.set_text_color(*INK)
        self.set_y(y + height)

    def header(self) -> None:
        self._watermark()
        self.set_draw_color(*NAVY)
        self.set_line_width(0.55)
        self.rect(3, 3, PAGE_W - 6, PAGE_H - 6)
        self.set_line_width(0.18)
        self.rect(4.5, 4.5, PAGE_W - 9, PAGE_H - 9)
        top = 10
        draw_logo(self, self.logo_path, x=MARGIN + 2, y=top, h=24)
        self.set_xy(MARGIN + 30, top + 1)
        self.set_font("Times", "B", 22)
        self.set_text_color(*INK)
        self.cell(120, 9, _text(self.card.school.school_name).upper(), align="C")
        if self.card.school.motto:
            self.set_xy(MARGIN + 30, top + 11)
            self.set_font("Times", "", 9.5)
            self.cell(120, 5, _text(self.card.school.motto).upper(), align="C")
        contact = [part for part in (self.card.school.address, self.card.school.phone) if part]
        self.set_xy(PAGE_W - MARGIN - 38, top + 1)
        self.set_font("Times", "", 7.7)
        self.multi_cell(38, 4.2, "\n".join(_text(part) for part in contact), align="R")
        self.set_draw_color(*NAVY)
        self.set_line_width(0.7)
        self.line(MARGIN, 36, PAGE_W - MARGIN, 36)
        self.set_fill_color(*PALE_BLUE)
        self.set_draw_color(*PALE_BLUE)
        self.rect(49, 39, 112, 9, style="F")
        self.set_xy(MARGIN, 40.1)
        self.set_font("Times", "B", 15)
        self.cell(CONTENT_W, 6.3, "STUDENT REPORT CARD", align="C")
        year = _text(self.card.academic_year_name or "-")
        term = _text(self.card.term_name or self.card.examination_name or "-")
        self.set_xy(MARGIN, 50.2)
        self.set_font("Times", "B", 10)
        self.cell(CONTENT_W, 5.5, f"ACADEMIC YEAR: {year}    |    TERM: {term}", align="C")
        self.set_y(59)
        if not self.card.is_published:
            self.set_fill_color(254, 243, 199)
            self.set_draw_color(217, 160, 30)
            self.set_text_color(120, 82, 8)
            self.set_font("Times", "B", 8.5)
            self.cell(CONTENT_W, 5.8, "PROVISIONAL - RESULTS HAVE NOT BEEN PUBLISHED", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*INK)
            self.ln(2)

    def student_block(self) -> None:
        y, h = self.get_y(), 28
        self.set_fill_color(*PALEST_BLUE)
        self.set_draw_color(*NAVY)
        self.set_line_width(0.25)
        self.rect(MARGIN, y, CONTENT_W, h, style="DF")
        left = (("STUDENT NAME", self.card.student_name), ("STUDENT NUMBER", self.card.student_number), ("FORM / CLASS", self.card.class_name or "-"), ("ACADEMIC LEVEL", _pretty_enum(self.card.academic_level)))
        right = (("DATE OF BIRTH", _date(self.card.date_of_birth)), ("GENDER", _pretty_enum(self.card.gender)), ("FORM", _pretty_enum(self.card.form_level)), ("EXAMINATION", self.card.examination_name or "-"))
        for index, ((left_label, left_value), (right_label, right_value)) in enumerate(zip(left, right)):
            row_y = y + 3 + index * 6
            self.set_xy(MARGIN + 4, row_y)
            self.set_font("Times", "B", 8.5)
            self.cell(35, 4, _text(left_label))
            self.set_font("Times", "", 9.2)
            self.cell(52, 4, _text(left_value)[:42])
            self.set_xy(MARGIN + 104, row_y)
            self.set_font("Times", "B", 8.5)
            self.cell(30, 4, _text(right_label))
            self.set_font("Times", "", 9.2)
            self.cell(48, 4, _text(right_value)[:34])
        self.set_y(y + h + 4)

    def _table_head(self) -> None:
        self._section_bar("Subject results")
        self.set_fill_color(*PALE_BLUE)
        self.set_draw_color(*RULE)
        self.set_font("Times", "B", 9)
        for title, width, align in self.COLUMNS:
            self.cell(width, 7, title, border=1, align=align, fill=True)
        self.ln()

    def results_table(self) -> None:
        self._table_head()
        stripe = False
        for line in self.card.lines:
            if self.will_page_break(7):
                self.add_page()
                self._table_head()
            self._result_row(line, stripe)
            stripe = not stripe
        if not self.card.lines:
            self.set_font("Times", "I", 9)
            self.set_text_color(*MUTED)
            self.cell(CONTENT_W, 7, "No subject results have been recorded for this examination.", border=1, align="C")
            self.ln()
            self.set_text_color(*INK)
        self._totals_row()
        self.ln(4)

    def _result_row(self, line: ReportLine, stripe: bool) -> None:
        blank = line.is_blank or line.marks is None
        if stripe:
            self.set_fill_color(*PALEST_BLUE)
        values = ((line.subject_name, 73, "L"), ("" if blank else f"{line.marks:.0f}", 28, "C"), ("" if blank else line.grade or "", 31, "C"), ("" if blank else line.remarks or "", 60, "L"))
        self.set_font("Times", "", 9.2)
        self.set_draw_color(*RULE)
        for value, width, align in values:
            self.cell(width, 7, _text(value)[:44], border=1, align=align, fill=stripe)
        self.ln()

    def _totals_row(self) -> None:
        possible = self.card.subjects_counted * 100
        avg = f"{self.card.average:.1f}%" if self.card.average is not None else "-"
        overall = (self.card.overall or "-").split(" - ", 1)[0]
        cells = (("TOTAL MARKS", 35), (f"{self.card.total_marks:.0f} / {possible}" if possible else "-", 29), ("AVERAGE", 31), (avg, 31), ("OVERALL GRADE", 43), (overall, 23))
        self.set_font("Times", "B", 8.8)
        self.set_fill_color(*PALE_BLUE)
        self.set_draw_color(*NAVY)
        for value, width in cells:
            self.cell(width, 8.5, _text(value), border=1, align="C", fill=True)
        self.ln()

    def summary(self) -> None:
        if self.will_page_break(43):
            self.add_page()
        y, left_w, gap, right_w = self.get_y(), 92, 4, 95
        self._boxed_summary(MARGIN, y, left_w, "TERM SUMMARY", (("Class position", self._position()), ("Subjects assessed", str(self.card.subjects_counted)), ("Total marks", f"{self.card.total_marks:.0f}"), ("Overall performance", self.card.overall or "-")))
        self._boxed_summary(MARGIN + left_w + gap, y, right_w, "RESULTS NOTE", (("Record", "Official examination results" if self.card.is_published else "Provisional results"), ("Examination", self.card.examination_name or "-"), ("Class", self.card.class_name or "-"), ("", "Marks and grades follow the school's published scale.")))
        self.set_y(y + 41)
        self._section_bar("Head teacher's remarks", 7)
        self.set_fill_color(*PALEST_BLUE)
        self.set_draw_color(*NAVY)
        self.rect(MARGIN, self.get_y(), CONTENT_W, 13, style="DF")
        self.set_xy(MARGIN + 4, self.get_y() + 3)
        self.set_font("Times", "I", 9)
        self.set_text_color(*MUTED)
        self.multi_cell(CONTENT_W - 8, 4, "Official results record. Please contact the school administration for any correction or clarification.")
        self.set_text_color(*INK)
        self.set_y(y + 65)

    def _boxed_summary(self, x: float, y: float, width: float, title: str, rows: tuple[tuple[str, str], ...]) -> None:
        self.set_draw_color(*NAVY)
        self.set_fill_color(*PALEST_BLUE)
        self.rect(x, y, width, 37, style="DF")
        self.set_fill_color(*NAVY)
        self.rect(x, y, width, 7, style="F")
        self.set_xy(x + 3, y + 1)
        self.set_font("Times", "B", 10)
        self.set_text_color(255, 255, 255)
        self.cell(width - 6, 4.8, title)
        self.set_text_color(*INK)
        for index, (label, value) in enumerate(rows):
            row_y = y + 10 + index * 6
            self.set_xy(x + 4, row_y)
            self.set_font("Times", "", 8.6)
            self.cell(35, 4.2, _text(label))
            self.set_font("Times", "B" if index < 3 else "", 8.6)
            self.cell(width - 43, 4.2, _text(value)[:52])

    def _position(self) -> str:
        return f"{self.card.position} / {self.card.ranked_out_of}" if self.card.position and self.card.ranked_out_of else "Not available"

    def signature_block(self) -> None:
        if self.will_page_break(28):
            self.add_page()
        y = self.get_y() + 9
        for index, label in enumerate(("Class Teacher", "Head of Form", "Head Teacher")):
            x, width = MARGIN + index * 67.5, 55
            self.set_draw_color(*INK)
            self.line(x, y, x + width, y)
            self.set_xy(x, y + 2)
            self.set_font("Times", "B", 8.5)
            self.cell(width, 4, label, align="C")
            self.set_font("Times", "", 7.8)
            self.cell(width, 4, "Signature & Date", align="C")
        self.set_y(y + 13)
        self.grading_key()

    def grading_key(self) -> None:
        bands = self.card.grading_bands[:7]
        if not bands:
            return
        if self.will_page_break(21):
            self.add_page()
        self._section_bar("Grading key", 6.5)
        label_w, band_w = 35, (CONTENT_W - 35) / len(bands)
        self.set_draw_color(*RULE)
        self.set_fill_color(*PALE_BLUE)
        self.set_font("Times", "B", 8)
        self.cell(label_w, 6, "GRADE", border=1, align="C", fill=True)
        for band in bands:
            self.cell(band_w, 6, _text(band["grade"]), border=1, align="C", fill=True)
        self.ln()
        self.set_font("Times", "", 8)
        self.cell(label_w, 6, "MARK RANGE", border=1, align="C")
        for index, band in enumerate(bands):
            lower = Decimal(str(band["minimum"]))
            upper = Decimal("100") if index == 0 else Decimal(str(bands[index - 1]["minimum"])) - Decimal("0.01")
            self.cell(band_w, 6, f"{lower:g} - {upper:g}", border=1, align="C")
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(*RULE)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.ln(1)
        self.set_font("Times", "", 7)
        self.set_text_color(*MUTED)
        generated = self.card.generated_at.strftime("%d %B %Y %H:%M")
        self.cell(CONTENT_W / 2, 4, _text(self.card.school.school_name), align="L")
        self.cell(CONTENT_W / 2, 4, f"Generated {generated}", align="R", new_x="LMARGIN", new_y="NEXT")
        if self.card.scope_note:
            self.set_font("Times", "I", 6.5)
            self.cell(CONTENT_W, 3.5, _text(self.card.scope_note), align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Times", "", 7)
        self.cell(CONTENT_W, 3.5, f"Page {self.page_no()} of {{nb}}", align="C")
        self.set_text_color(*INK)


def render_report_card(card: ReportCard, logo_path: Optional[str] = None) -> bytes:
    pdf = ReportCardPDF(card, logo_path)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.student_block()
    pdf.results_table()
    pdf.summary()
    pdf.signature_block()
    return bytes(pdf.output())
