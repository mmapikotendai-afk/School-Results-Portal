"""Rendering a report card as a print-ready A4 document.

One renderer serves every role. What a report contains is decided upstream by
ReportCardService; this module only decides how it looks on the page.

Layout is built around A4 at 210x297mm with 14mm side margins, giving a 182mm
printable width that every column measurement below adds up to.
"""

from datetime import datetime
from typing import List, Optional

from fpdf import FPDF

from app.services.report_card_service import ReportCard, ReportLine

from app.utils.pdf import draw_logo

# Page geometry, in millimetres.
PAGE_W, PAGE_H = 210, 297
MARGIN = 14
CONTENT_W = PAGE_W - (2 * MARGIN)

# Core PDF fonts are Latin-1 only. Rather than ship a Unicode font file, text
# is folded to the nearest ASCII so a stray curly quote cannot break a report.
_REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "·": "-", "…": "...",
}

INK = (17, 24, 39)
MUTED = (110, 118, 132)
RULE = (200, 207, 218)
HEAD_FILL = (238, 242, 248)
STRIPE = (248, 250, 252)


def _ascii(text: Optional[str]) -> str:
    if not text:
        return ""
    for bad, good in _REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


class ReportCardPDF(FPDF):
    """An A4 report card on the school's letterhead."""

    # (heading, width mm, alignment) - widths total CONTENT_W.
    COLUMNS = [
        ("Subject", 74, "L"),
        ("Code", 24, "C"),
        ("Marks", 22, "C"),
        ("Grade", 22, "C"),
        ("Remarks", 40, "L"),
    ]

    def __init__(self, card: ReportCard, logo_path: Optional[str] = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.card = card
        self.logo_path = logo_path
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=24)
        self.set_title(f"{card.student_name} - {card.examination_name}")

    # ---------------------------------------------------------- watermark

    def _watermark(self) -> None:
        """A faint mark behind the content.

        Drawn first so everything else sits on top of it, and kept very light:
        a watermark that competes with the marks defeats the document.
        """
        mode = (self.card.school.report_watermark or "name").lower()
        if mode == "none":
            return

        if mode == "logo" and self.logo_path:
            size = 120
            with self.local_context(fill_opacity=0.06, stroke_opacity=0.06):
                drawn = draw_logo(
                    self,
                    self.logo_path,
                    x=(PAGE_W - size) / 2,
                    y=(PAGE_H - size) / 2,
                    w=size,
                )
            if drawn:
                return
            # An unusable crest falls through to the text watermark below, so
            # the page still carries one.

        text = _ascii(self.card.school.school_name).upper()
        if not text:
            return

        self.set_font("Helvetica", "B", 46)
        with self.local_context(fill_opacity=0.05, stroke_opacity=0.05):
            self.set_text_color(90, 100, 120)
            with self.rotation(38, x=PAGE_W / 2, y=PAGE_H / 2):
                width = self.get_string_width(text)
                self.set_xy((PAGE_W - width) / 2, PAGE_H / 2 - 10)
                self.cell(width, 20, text, align="C")
        self.set_text_color(*INK)

    # ------------------------------------------------------------- header

    def header(self) -> None:
        self._watermark()

        top = MARGIN
        draw_logo(self, self.logo_path, x=MARGIN, y=top, h=20)

        # The masthead is centred on the page, not on the space beside the
        # crest, so it stays put whether or not a logo is present.
        self.set_xy(MARGIN, top)
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*INK)
        self.cell(CONTENT_W, 8, _ascii(self.card.school.school_name),
                  align="C", new_x="LMARGIN", new_y="NEXT")

        if self.card.school.motto:
            self.set_font("Helvetica", "I", 8.5)
            self.set_text_color(*MUTED)
            self.cell(CONTENT_W, 4.5, _ascii(self.card.school.motto),
                      align="C", new_x="LMARGIN", new_y="NEXT")

        contact = " | ".join(
            filter(None, [_ascii(self.card.school.address), _ascii(self.card.school.phone)])
        )
        if contact:
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED)
            self.cell(CONTENT_W, 4, contact, align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(2)

        # Results title: the term is the headline a reader looks for.
        title = f"{_ascii(self.card.term_name or '')} RESULTS".strip().upper()
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*INK)
        self.cell(CONTENT_W, 7, title, align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 9)
        self.set_text_color(*MUTED)
        subtitle = f"Academic Year: {_ascii(self.card.academic_year_name or '-')}"
        self.cell(CONTENT_W, 5, subtitle, align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8.5)
        self.cell(CONTENT_W, 4.5, _ascii(self.card.examination_name),
                  align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(1.5)
        self.set_draw_color(*RULE)
        self.set_line_width(0.4)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.ln(4)

        if not self.card.is_published:
            self._draft_banner()

    def _draft_banner(self) -> None:
        """An unpublished report is a working document, and says so.

        Administrators review report cards before release; without this an
        unreleased copy is indistinguishable from a final one on paper.
        """
        self.set_fill_color(254, 243, 199)
        self.set_draw_color(217, 160, 30)
        self.set_text_color(146, 100, 10)
        self.set_font("Helvetica", "B", 8.5)
        self.cell(CONTENT_W, 6,
                  "PROVISIONAL - these results have not been published",
                  border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*INK)
        self.ln(3)

    # --------------------------------------------------- student details

    def student_block(self) -> None:
        """Who the report is for, boxed so it reads as identity, not content."""
        rows = [
            ("Student ID", self.card.student_number),
            ("Student Name", self.card.student_name),
            ("Class", self.card.class_name or "-"),
        ]

        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        start_y = self.get_y()
        self.rect(MARGIN, start_y, CONTENT_W, len(rows) * 6.5 + 3)

        self.set_y(start_y + 1.5)
        for label, value in rows:
            self.set_x(MARGIN + 3)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*MUTED)
            self.cell(32, 6.5, f"{label}:")
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*INK)
            self.cell(0, 6.5, _ascii(value), new_x="LMARGIN", new_y="NEXT")

        self.set_y(start_y + len(rows) * 6.5 + 3)
        self.ln(5)

    # -------------------------------------------------------- result table

    def _table_head(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*HEAD_FILL)
        self.set_draw_color(*RULE)
        self.set_text_color(*INK)
        self.set_line_width(0.2)
        for label, width, align in self.COLUMNS:
            self.cell(width, 7.5, label, border=1, align=align, fill=True)
        self.ln()

    def results_table(self) -> None:
        self._table_head()

        self.set_font("Helvetica", "", 9)
        stripe = False
        for line in self.card.lines:
            if self.will_page_break(7):
                self.add_page()
                self._table_head()
                self.set_font("Helvetica", "", 9)

            self.set_fill_color(*STRIPE)
            self._result_row(line, fill=stripe)
            stripe = not stripe

        self.ln(4)

    def _result_row(self, line: ReportLine, fill: bool) -> None:
        """One subject. A blank row is left genuinely blank - no mark is
        invented for a subject that has none."""
        blank = line.is_blank or line.marks is None

        values = [
            (_ascii(line.subject_name)[:40], 74, "L"),
            (_ascii(line.subject_code), 24, "C"),
            ("" if blank else f"{line.marks:.0f}", 22, "C"),
            ("" if blank else (line.grade or ""), 22, "C"),
            ("" if blank else _ascii(line.remarks)[:24], 40, "L"),
        ]

        for index, (text, width, align) in enumerate(values):
            if blank and index > 0:
                self.set_text_color(*MUTED)
            self.cell(width, 7, text, border=1, align=align, fill=fill)
            self.set_text_color(*INK)
        self.ln()

    # ------------------------------------------------------------ summary

    def summary(self) -> None:
        """Average, overall performance, and position where configured."""
        rows: List[tuple] = [
            ("Subjects", str(self.card.subjects_counted)),
            ("Total marks", f"{self.card.total_marks:.0f}"),
            ("Average", f"{self.card.average:.2f}" if self.card.average is not None else "-"),
        ]
        if self.card.overall:
            rows.append(("Overall performance", _ascii(self.card.overall)))
        if self.card.position:
            rows.append(
                ("Position in class", f"{self.card.position} of {self.card.ranked_out_of}")
            )

        box_h = len(rows) * 7 + 10
        if self.will_page_break(box_h):
            self.add_page()

        start_y = self.get_y()
        self.set_draw_color(*RULE)
        self.set_fill_color(250, 251, 253)
        self.rect(MARGIN, start_y, CONTENT_W, box_h, style="DF")

        self.set_xy(MARGIN + 4, start_y + 3)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(*INK)
        self.cell(0, 6, "SUMMARY", new_x="LMARGIN", new_y="NEXT")

        for label, value in rows:
            self.set_x(MARGIN + 4)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*MUTED)
            self.cell(48, 7, label)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*INK)
            self.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

        self.set_y(start_y + box_h)
        self.ln(6)

    def signature_block(self) -> None:
        """Room for a signature, because a report card gets signed."""
        if self.will_page_break(22):
            self.add_page()

        y = self.get_y() + 8
        width = 62
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)

        for index, label in enumerate(("Class Teacher", "Head Teacher")):
            x = MARGIN + index * (CONTENT_W - width)
            self.line(x, y, x + width, y)
            self.set_xy(x, y + 1)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED)
            self.cell(width, 4, label, align="C")

        self.set_y(y + 8)
        self.set_text_color(*INK)

    # ------------------------------------------------------------- footer

    def footer(self) -> None:
        self.set_y(-18)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())

        self.ln(1)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*MUTED)

        generated = self.card.generated_at.strftime("%d %B %Y at %H:%M")
        left = _ascii(self.card.school.school_name)
        self.cell(CONTENT_W / 2, 5, left, align="L")
        self.cell(CONTENT_W / 2, 5, f"Generated {generated}", align="R",
                  new_x="LMARGIN", new_y="NEXT")

        if self.card.scope_note:
            self.set_font("Helvetica", "I", 7)
            self.cell(CONTENT_W, 4, _ascii(self.card.scope_note),
                      align="L", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 7.5)
        self.cell(CONTENT_W, 4, f"Page {self.page_no()} of {{nb}}", align="C")


def render_report_card(card: ReportCard, logo_path: Optional[str] = None) -> bytes:
    """Render one report card to a print-ready A4 PDF."""
    pdf = ReportCardPDF(card, logo_path)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.student_block()
    pdf.results_table()
    pdf.summary()
    pdf.signature_block()
    return bytes(pdf.output())
