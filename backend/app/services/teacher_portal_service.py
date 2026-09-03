"""The teacher portal: what a teacher may see and change, and nothing else.

Authorisation is the whole point of this module. A teacher may only ever touch
a subject that is assigned to them for the academic year the examination sits
in, and `authorise` is the single gate every route passes through to establish
that. Nothing here takes a subject id on trust.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.academic_year import Term
from app.models.assignment import TeacherSubject
from app.models.enrollment import StudentSubject
from app.models.enums import EnrollmentStatus, ExaminationStatus, SubmissionStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.student import Student
from app.models.subject import Subject
from app.models.submission import ResultSubmission
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.teacher_view import (
    ClassOption,
    MarkRow,
    MarkSheet,
    TeacherDashboard,
    TeacherSubjectCard,
    TemplateOption,
)
from app.services.academic_service import AcademicService, utcnow
from app.services.submission_service import SubmissionService

# Marks may be written while an examination is being collected, and while it is
# closed but not yet in review. Once administrators are reviewing or the results
# are published, only they can change anything.
WRITABLE_STATUSES = {
    ExaminationStatus.SUBMISSION_OPEN,
    ExaminationStatus.SUBMISSION_COMPLETE,
}

LOCKED_REASON = {
    ExaminationStatus.DRAFT: "This examination has not been opened for submission yet.",
    ExaminationStatus.UNDER_REVIEW: (
        "This examination is being reviewed by the school. Contact the office to "
        "change a mark."
    ),
    ExaminationStatus.PUBLISHED: (
        "These results have been published and can no longer be changed here."
    ),
}


class NotAuthorised(Exception):
    """The teacher is not assigned to this subject for this examination."""


class TeacherPortalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.academic = AcademicService(db)
        self.submissions = SubmissionService(db)

    # ------------------------------------------------------ authorisation

    def assignment_for(
        self, teacher: Teacher, subject_id: int, academic_year_id: int
    ) -> Optional[TeacherSubject]:
        """The active assignment tying this teacher to this subject, or None."""
        return (
            self.db.query(TeacherSubject)
            .filter(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.subject_id == subject_id,
                TeacherSubject.academic_year_id == academic_year_id,
                TeacherSubject.is_active.is_(True),
            )
            .first()
        )

    def authorise(
        self, teacher: Teacher, examination_id: int, subject_id: int
    ) -> Tuple[Examination, Subject, TeacherSubject]:
        """Establish that this teacher may act on this subject and examination.

        Raises NotAuthorised for every failure - a subject that does not exist,
        an examination that does not exist, and a subject the teacher is not
        assigned to all fail identically. A teacher probing ids therefore
        cannot map out the school timetable from the responses.
        """
        exam = (
            self.db.query(Examination)
            .options(joinedload(Examination.term).joinedload(Term.academic_year))
            .filter(Examination.id == examination_id)
            .first()
        )
        if exam is None or exam.term is None:
            raise NotAuthorised

        subject = self.db.query(Subject).filter(Subject.id == subject_id).first()
        if subject is None:
            raise NotAuthorised

        # The assignment must be for the year the examination sits in. An
        # assignment that lapsed at the end of last year does not carry over.
        assignment = self.assignment_for(
            teacher, subject_id, exam.term.academic_year_id
        )
        if assignment is None:
            raise NotAuthorised

        return exam, subject, assignment

    @staticmethod
    def writability(exam: Examination) -> Tuple[bool, Optional[str]]:
        """Whether marks may be written, and the reason when they may not."""
        if exam.status in WRITABLE_STATUSES:
            return True, None
        return False, LOCKED_REASON.get(
            exam.status, "This examination is not accepting marks."
        )

    # --------------------------------------------------------- dashboard

    def dashboard(self, teacher: Teacher) -> TeacherDashboard:
        """The teacher landing screen: one card per assigned subject."""
        board = TeacherDashboard(
            teacher_name=teacher.full_name, employee_number=teacher.employee_number
        )

        exam = self.academic.current_examination()
        if exam is None or exam.term is None:
            return board

        board.current_examination = exam.name
        board.term_name = exam.term.name
        board.academic_year_name = (
            exam.term.academic_year.name if exam.term.academic_year else None
        )

        year_id = exam.term.academic_year_id
        assignments = (
            self.db.query(TeacherSubject)
            .options(joinedload(TeacherSubject.subject))
            .filter(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.academic_year_id == year_id,
                TeacherSubject.is_active.is_(True),
            )
            .all()
        )
        if not assignments:
            return board

        # Recompute once, then read the rows, rather than per subject.
        tracking = {row.subject_id: row for row in self.submissions.recalculate(exam)}

        can_write, locked_reason = self.writability(exam)
        deadline = exam.submission_deadline
        now = utcnow()
        past_deadline = bool(deadline and now > deadline)
        days_remaining = (deadline - now).days if deadline and not past_deadline else None

        for assignment in sorted(assignments, key=lambda a: a.subject.name):
            row = tracking.get(assignment.subject_id)
            board.subjects.append(
                TeacherSubjectCard(
                    subject_id=assignment.subject_id,
                    subject_name=assignment.subject.name,
                    subject_code=assignment.subject.code,
                    examination_id=exam.id,
                    examination_name=exam.name,
                    term_name=exam.term.name,
                    academic_year_name=board.academic_year_name,
                    examination_status=exam.status,
                    submission_deadline=deadline,
                    is_past_deadline=past_deadline,
                    days_remaining=days_remaining,
                    status=row.status if row else SubmissionStatus.PENDING,
                    submitted_at=row.submitted_at if row else None,
                    submitted_by=(
                        row.submitted_by.full_name if row and row.submitted_by else None
                    ),
                    expected_count=row.expected_count if row else 0,
                    submitted_count=row.submitted_count if row else 0,
                    can_upload=can_write,
                    locked_reason=locked_reason,
                )
            )

        board.total_subjects = len(board.subjects)
        board.submitted_subjects = sum(
            1
            for s in board.subjects
            if s.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.LATE)
        )
        board.overdue_subjects = sum(
            1 for s in board.subjects if s.status == SubmissionStatus.OVERDUE
        )
        board.outstanding_subjects = board.total_subjects - board.submitted_subjects
        return board

    # ---------------------------------------------------- template picker

    def template_options(self, teacher: Teacher) -> List[TemplateOption]:
        """Every (examination, subject) pair this teacher may work on.

        Built from the teacher's own active assignments, matched to the
        examinations in those academic years, so the picker can never offer a
        combination that authorise() would reject.
        """
        assignments = (
            self.db.query(TeacherSubject)
            .options(joinedload(TeacherSubject.subject))
            .filter(
                TeacherSubject.teacher_id == teacher.id,
                TeacherSubject.is_active.is_(True),
            )
            .all()
        )
        if not assignments:
            return []

        by_year: dict[int, List[TeacherSubject]] = {}
        for assignment in assignments:
            by_year.setdefault(assignment.academic_year_id, []).append(assignment)

        exams = (
            self.db.query(Examination)
            .join(Term, Examination.term_id == Term.id)
            .options(joinedload(Examination.term).joinedload(Term.academic_year))
            .filter(
                Term.academic_year_id.in_(list(by_year)),
                # A draft examination is not yet real to a teacher.
                Examination.status != ExaminationStatus.DRAFT,
            )
            .order_by(Examination.created_at.desc())
            .all()
        )

        options: List[TemplateOption] = []
        for exam in exams:
            can_write, _reason = self.writability(exam)
            for assignment in by_year.get(exam.term.academic_year_id, []):
                students = self.enrolled_students(
                    assignment.subject_id, exam.term.academic_year_id
                )
                class_names = sorted(
                    {s.school_class.name for s in students if s.school_class}
                )
                options.append(
                    TemplateOption(
                        examination_id=exam.id,
                        examination_name=exam.name,
                        term_name=exam.term.name,
                        academic_year_name=(
                            exam.term.academic_year.name if exam.term.academic_year else None
                        ),
                        examination_status=exam.status,
                        submission_deadline=exam.submission_deadline,
                        subject_id=assignment.subject_id,
                        subject_name=assignment.subject.name,
                        subject_code=assignment.subject.code,
                        enrolled_count=len(students),
                        classes=class_names,
                        can_upload=can_write,
                    )
                )
        return options

    def class_options(
        self, subject_id: int, academic_year_id: int
    ) -> List[ClassOption]:
        """The classes represented in a subject roll, with their head counts."""
        counts: dict[int, ClassOption] = {}
        for student in self.enrolled_students(subject_id, academic_year_id):
            if student.school_class is None:
                continue
            entry = counts.get(student.class_id)
            if entry is None:
                counts[student.class_id] = ClassOption(
                    class_id=student.class_id,
                    class_name=student.school_class.name,
                    student_count=1,
                )
            else:
                entry.student_count += 1
        return sorted(counts.values(), key=lambda c: c.class_name)

    # -------------------------------------------------------- mark sheet

    def enrolled_students(
        self,
        subject_id: int,
        academic_year_id: int,
        class_id: Optional[int] = None,
    ) -> List[Student]:
        """Exactly who may receive a mark for this subject.

        Three conditions, all required:

          - the student account is active, so someone who has left the school
            neither appears on the sheet nor counts against the teacher
          - their enrolment in this subject is ACTIVE, not dropped
          - the enrolment is for the academic year the examination sits in

        Passing class_id narrows it further, for a subject taught to several
        classes by different teachers.
        """
        query = (
            self.db.query(Student)
            .join(StudentSubject, StudentSubject.student_id == Student.id)
            .join(User, Student.user_id == User.id)
            .options(joinedload(Student.school_class))
            .filter(
                StudentSubject.subject_id == subject_id,
                StudentSubject.academic_year_id == academic_year_id,
                StudentSubject.status == EnrollmentStatus.ACTIVE,
                User.is_active.is_(True),
            )
        )
        if class_id is not None:
            query = query.filter(Student.class_id == class_id)

        return sorted(query.all(), key=lambda s: (s.last_name, s.first_name))

    def mark_sheet(
        self, teacher: Teacher, examination_id: int, subject_id: int
    ) -> MarkSheet:
        """The full roll for one subject, with any marks already recorded."""
        exam, subject, _assignment = self.authorise(teacher, examination_id, subject_id)
        year_id = exam.term.academic_year_id

        students = self.enrolled_students(subject_id, year_id)
        results = {
            r.student_id: r
            for r in self.db.query(Result).filter(
                Result.examination_id == exam.id, Result.subject_id == subject_id
            )
        }

        rows = []
        for student in students:
            result = results.get(student.id)
            rows.append(
                MarkRow(
                    result_id=result.id if result else None,
                    student_id=student.id,
                    student_number=student.student_number,
                    student_name=student.full_name,
                    marks=result.marks if result else None,
                    grade=result.grade if result else None,
                    remarks=result.remarks if result else None,
                    updated_at=result.updated_at if result else None,
                )
            )

        can_edit, locked_reason = self.writability(exam)
        tracking = self.tracking_row(exam, teacher, subject_id)

        return MarkSheet(
            examination_id=exam.id,
            examination_name=exam.name,
            subject_id=subject.id,
            subject_name=subject.name,
            subject_code=subject.code,
            term_name=exam.term.name,
            academic_year_name=(
                exam.term.academic_year.name if exam.term.academic_year else None
            ),
            status=tracking.status if tracking else SubmissionStatus.PENDING,
            submission_deadline=exam.submission_deadline,
            can_edit=can_edit,
            locked_reason=locked_reason,
            rows=rows,
            expected_count=len(students),
            submitted_count=sum(1 for r in rows if r.marks is not None),
        )

    def tracking_row(
        self, exam: Examination, teacher: Teacher, subject_id: int
    ) -> Optional[ResultSubmission]:
        return (
            self.db.query(ResultSubmission)
            .options(joinedload(ResultSubmission.submitted_by))
            .filter(
                ResultSubmission.examination_id == exam.id,
                ResultSubmission.teacher_id == teacher.id,
                ResultSubmission.subject_id == subject_id,
            )
            .first()
        )

    def stamp_submission(
        self, exam: Examination, teacher: Teacher, subject_id: int, user_id: int
    ) -> Optional[ResultSubmission]:
        """Record who delivered marks, and when they first arrived.

        These are two different facts and are treated as such:

        submitted_at holds the *first* delivery and is never moved, so
        correcting a mistake later cannot make an on-time submission look late.

        submitted_by holds whoever performed the *most recent* upload, so the
        monitor always attributes the marks currently on record to the person
        who actually put them there - including an administrator who uploaded
        on the teacher's behalf.
        """
        row = self.tracking_row(exam, teacher, subject_id)
        if row is None:
            return None

        if row.submitted_at is None:
            row.submitted_at = utcnow()

        row.submitted_by_id = user_id
        return row
