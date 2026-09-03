"""Who may generate which report card.

The report card engine itself has no notion of roles. This module decides the
scope a caller is entitled to and hands it in, so a report can only ever be
built from data the caller was already allowed to see. Every route that
produces a report card goes through here.
"""

from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.assignment import TeacherSubject
from app.models.enums import ExaminationStatus
from app.models.examination import Examination
from app.models.school_settings import SchoolSettings
from app.models.student import Student
from app.models.teacher import Teacher
from app.services.report_card_service import (
    ReportCard,
    ReportCardService,
    load_examination,
    load_student,
)
from app.services.report_pdf import render_report_card
from app.services.school_service import SchoolService

# Deliberately identical whether the record does not exist, is not published,
# or belongs to somebody else. A 403 would confirm that something is there.
NOT_AVAILABLE = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="No report card is available for that examination.",
)


def school_and_logo(db: Session) -> Tuple[SchoolSettings, Optional[str]]:
    """The school record and a logo path the PDF writer can actually embed."""
    school = SchoolService(db).get_or_create(settings.SCHOOL_NAME)

    logo = None
    if school.logo_path:
        candidate = Path(settings.UPLOAD_DIR) / school.logo_path
        # SVG renders in a browser but cannot be embedded by the PDF writer.
        if candidate.exists() and candidate.suffix.lower() != ".svg":
            logo = str(candidate)

    return school, logo


def _resolve(db: Session, student_id: int, examination_id: int) -> Tuple[Student, Examination]:
    student = load_student(db, student_id)
    exam = load_examination(db, examination_id)
    if student is None or exam is None or exam.term is None:
        raise NOT_AVAILABLE
    return student, exam


def for_student(db: Session, student: Student, examination_id: int) -> ReportCard:
    """A student's own report card.

    Only a published examination produces one: an unpublished report card is
    exactly the thing the publication rule exists to withhold.
    """
    exam = load_examination(db, examination_id)
    if exam is None or exam.term is None or exam.status != ExaminationStatus.PUBLISHED:
        raise NOT_AVAILABLE

    school, _logo = school_and_logo(db)
    card = ReportCardService(db).build(student, exam, school)
    if not card.lines:
        raise NOT_AVAILABLE
    return card


def for_teacher(
    db: Session, teacher: Teacher, student_id: int, examination_id: int
) -> ReportCard:
    """A report card limited to the subjects this teacher is assigned.

    A teacher is not entitled to a student's full record - that would expose
    marks from every other teacher's subject. What they get is a statement for
    their own subjects, labelled as such so a partial document can never be
    mistaken for the school's report card.
    """
    student, exam = _resolve(db, student_id, examination_id)

    subject_ids: List[int] = [
        row.subject_id
        for row in db.query(TeacherSubject.subject_id).filter(
            TeacherSubject.teacher_id == teacher.id,
            TeacherSubject.academic_year_id == exam.term.academic_year_id,
            TeacherSubject.is_active.is_(True),
        )
    ]
    if not subject_ids:
        raise NOT_AVAILABLE

    school, _logo = school_and_logo(db)
    card = ReportCardService(db).build(
        student,
        exam,
        school,
        subject_ids=subject_ids,
        scope_note=(
            f"Subject statement covering only the subjects taught by "
            f"{teacher.full_name}. This is not the full school report card."
        ),
        # A position across subjects the teacher cannot see would be
        # meaningless, and would leak the standing of students they do not teach.
        include_position=False,
    )
    if not card.lines:
        raise NOT_AVAILABLE
    return card


def for_admin(db: Session, student_id: int, examination_id: int) -> ReportCard:
    """Any student, at any stage.

    Administrators review report cards before publication, so an unpublished
    examination is allowed here - the document marks itself PROVISIONAL rather
    than being withheld.
    """
    student, exam = _resolve(db, student_id, examination_id)

    school, _logo = school_and_logo(db)
    card = ReportCardService(db).build(student, exam, school)
    if not card.lines:
        raise NOT_AVAILABLE
    return card


def render(db: Session, card: ReportCard) -> bytes:
    """Render a built card, using the school's crest where one is set."""
    _school, logo = school_and_logo(db)
    return render_report_card(card, logo)
