"""The report card engine.

One builder produces every report card in the system. A student downloading
their own, a teacher downloading the subjects they teach, and an administrator
downloading any student's all arrive here; what differs is the scope they are
allowed to ask for, decided before the data is gathered.

The scope is not a filter applied to a finished report. It is passed into the
query, so a report can only ever contain what the caller was entitled to see.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

from app.models.academic_year import Term
from app.models.enrollment import StudentSubject
from app.models.enums import EnrollmentStatus, ExaminationStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.school_settings import SchoolSettings
from app.models.student import Student
from app.models.subject import Subject
from app.services.grading_service import GradingService
from app.services.results_engine import ResultsEngine


@dataclass
class ReportLine:
    """One subject row on the report card."""

    subject_name: str
    subject_code: str
    marks: Optional[Decimal] = None
    grade: Optional[str] = None
    remarks: Optional[str] = None

    # True when the student studies this subject but has no mark recorded, or
    # when the subject is on the standard list and they do not study it. A
    # mark is never invented for either case.
    is_blank: bool = False


@dataclass
class ReportCard:
    """Everything one report card prints, already scoped to the caller."""

    school: SchoolSettings

    student_number: str
    student_name: str
    class_name: Optional[str]

    examination_name: str
    term_name: Optional[str]
    academic_year_name: Optional[str]
    is_published: bool

    lines: List[ReportLine] = field(default_factory=list)

    subjects_counted: int = 0
    total_marks: Decimal = Decimal("0")
    average: Optional[float] = None
    overall: Optional[str] = None

    position: Optional[int] = None
    ranked_out_of: Optional[int] = None

    # What the caller was allowed to see, printed on the document so a partial
    # report can never be mistaken for a complete one.
    scope_note: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.now)


class ReportCardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.grading = GradingService(db)
        self.engine = ResultsEngine(db)

    # ------------------------------------------------------------ building

    def build(
        self,
        student: Student,
        exam: Examination,
        school: SchoolSettings,
        subject_ids: Optional[Sequence[int]] = None,
        scope_note: Optional[str] = None,
        include_position: bool = True,
    ) -> ReportCard:
        """Assemble one report card.

        subject_ids restricts the report to a set of subjects. A teacher passes
        the subjects they are assigned; a student and an administrator pass
        None, meaning everything the student studies.
        """
        results = {
            r.subject_id: r
            for r in self.engine.for_student(student.id, exam.id)
            if subject_ids is None or r.subject_id in set(subject_ids)
        }

        enrolled = self._enrolled_subjects(student, exam, subject_ids)

        card = ReportCard(
            school=school,
            student_number=student.student_number,
            student_name=student.full_name,
            class_name=student.school_class.name if student.school_class else None,
            examination_name=exam.name,
            term_name=exam.term.name if exam.term else None,
            academic_year_name=(
                exam.term.academic_year.name if exam.term and exam.term.academic_year else None
            ),
            is_published=exam.status == ExaminationStatus.PUBLISHED,
            scope_note=scope_note,
        )

        omit_blank = (school.report_unenrolled or "omit") == "omit"

        for subject in enrolled:
            result = results.get(subject.id)
            if result is None:
                # Enrolled but unmarked. The row is printed blank rather than
                # dropped, because a missing subject is information: it says
                # the mark has not arrived, not that the student never took it.
                card.lines.append(
                    ReportLine(
                        subject_name=subject.name,
                        subject_code=subject.code,
                        is_blank=True,
                    )
                )
                continue

            card.lines.append(
                ReportLine(
                    subject_name=subject.name,
                    subject_code=subject.code,
                    marks=result.marks,
                    grade=result.grade,
                    remarks=result.remarks,
                )
            )

        # A subject on the school's standard list that the student does not
        # study: shown blank or left off, never given a mark.
        if not omit_blank and subject_ids is None:
            studied = {s.id for s in enrolled}
            standard = (
                self.db.query(Subject)
                .filter(Subject.is_active.is_(True), Subject.id.notin_(studied or [0]))
                .order_by(Subject.name)
                .all()
            )
            for subject in standard:
                card.lines.append(
                    ReportLine(
                        subject_name=subject.name,
                        subject_code=subject.code,
                        is_blank=True,
                    )
                )

        self._summarise(card, student, exam, include_position)
        return card

    def _enrolled_subjects(
        self,
        student: Student,
        exam: Examination,
        subject_ids: Optional[Sequence[int]],
    ) -> List[Subject]:
        """The subjects this student actually studies, for the right year."""
        if exam.term is None:
            return []

        query = (
            self.db.query(Subject)
            .join(StudentSubject, StudentSubject.subject_id == Subject.id)
            .filter(
                StudentSubject.student_id == student.id,
                StudentSubject.academic_year_id == exam.term.academic_year_id,
                StudentSubject.status == EnrollmentStatus.ACTIVE,
            )
        )
        if subject_ids is not None:
            query = query.filter(Subject.id.in_(list(subject_ids) or [0]))

        return sorted(query.all(), key=lambda s: s.name)

    def _summarise(
        self,
        card: ReportCard,
        student: Student,
        exam: Examination,
        include_position: bool,
    ) -> None:
        """Average, overall performance, and position where configured.

        Only marked subjects count towards the average: averaging a blank as
        zero would punish a student for a mark their teacher has not filed.
        """
        marked = [line for line in card.lines if line.marks is not None]
        card.subjects_counted = len(marked)

        if marked:
            card.total_marks = sum((line.marks for line in marked), Decimal("0"))
            card.average = round(float(card.total_marks) / len(marked), 2)

            level = student.school_class.level if student.school_class else None
            grade, remark = self.grading.grade_for(Decimal(str(card.average)), level)
            card.overall = f"{grade} - {remark}"

        show_position = include_position and (
            card.school.report_show_position if card.school else True
        )
        if show_position and marked:
            # Position is against the student's own class, which is the
            # comparison a report card is understood to make.
            position, out_of = self.engine.position_of(
                student.id, exam, student.class_id
            )
            card.position = position
            card.ranked_out_of = out_of


def load_student(db: Session, student_id: int) -> Optional[Student]:
    return (
        db.query(Student)
        .options(joinedload(Student.school_class), joinedload(Student.user))
        .filter(Student.id == student_id)
        .first()
    )


def load_examination(db: Session, exam_id: int) -> Optional[Examination]:
    return (
        db.query(Examination)
        .options(joinedload(Examination.term).joinedload(Term.academic_year))
        .filter(Examination.id == exam_id)
        .first()
    )
