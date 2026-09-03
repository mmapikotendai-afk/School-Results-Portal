"""The results engine: reading results back, and ranking them.

The database is the source of truth. A result is identified by exactly one
thing - the (student, subject, examination) triple the unique key enforces -
so marks uploaded by different teachers for the same student combine into one
record without any merging logic here. Mathematics from one teacher and
English from another simply appear as two rows for the same student.

Ranking is the part that needs care. A position is only meaningful against a
comparable group, so this module is deliberate about who is in one:

  - only students whose accounts are active
  - only students actually enrolled in the examination's academic year
  - only students who have at least one mark in that examination
  - when ranking within a class, only that class

A student sitting no papers is not last; they are not in the ranking at all.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

from app.models.academic_year import Term
from app.models.enrollment import StudentSubject
from app.models.enums import EnrollmentStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.student import Student
from app.models.subject import Subject
from app.models.user import User
from app.services.grading_service import GradingService


def _average(values: Sequence[Decimal]) -> Optional[float]:
    if not values:
        return None
    return round(float(sum(values)) / len(values), 2)


class StudentAggregate:
    """One student's standing in one examination."""

    def __init__(self, student: Student) -> None:
        self.student = student
        self.results: List[Result] = []
        self.position: Optional[int] = None

    @property
    def total(self) -> Decimal:
        return sum((r.marks for r in self.results), Decimal("0"))

    @property
    def average(self) -> Optional[float]:
        return _average([r.marks for r in self.results])

    @property
    def subjects_marked(self) -> int:
        return len(self.results)


class ResultsEngine:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.grading = GradingService(db)

    # ------------------------------------------------------- retrieval

    def _base(self):
        return (
            self.db.query(Result)
            .options(
                joinedload(Result.subject),
                joinedload(Result.student).joinedload(Student.school_class),
                joinedload(Result.student).joinedload(Student.user),
                joinedload(Result.examination)
                .joinedload(Examination.term)
                .joinedload(Term.academic_year),
                joinedload(Result.uploaded_by),
            )
        )

    def for_student(
        self, student_id: int, examination_id: Optional[int] = None
    ) -> List[Result]:
        """Every result for one student, optionally within one examination."""
        query = self._base().filter(Result.student_id == student_id)
        if examination_id:
            query = query.filter(Result.examination_id == examination_id)
        return query.all()

    def for_subject(self, subject_id: int, examination_id: int) -> List[Result]:
        """Every mark in one subject for one examination."""
        return (
            self._base()
            .filter(Result.subject_id == subject_id, Result.examination_id == examination_id)
            .all()
        )

    def for_examination(
        self, examination_id: int, class_id: Optional[int] = None
    ) -> List[Result]:
        """Every mark in one examination, optionally narrowed to a class."""
        query = self._base().filter(Result.examination_id == examination_id)
        if class_id is not None:
            query = query.join(Student, Result.student_id == Student.id).filter(
                Student.class_id == class_id
            )
        return query.all()

    def for_teacher(self, teacher_id: int, examination_id: int) -> List[Result]:
        """Every mark in the subjects one teacher is responsible for.

        Scoped through their active assignments for the examination's year, so
        it answers "what have I got in" rather than "what exists".
        """
        from app.models.assignment import TeacherSubject

        exam = self.db.query(Examination).filter(Examination.id == examination_id).first()
        if exam is None or exam.term is None:
            return []

        subject_ids = [
            row.subject_id
            for row in self.db.query(TeacherSubject.subject_id).filter(
                TeacherSubject.teacher_id == teacher_id,
                TeacherSubject.academic_year_id == exam.term.academic_year_id,
                TeacherSubject.is_active.is_(True),
            )
        ]
        if not subject_ids:
            return []

        return (
            self._base()
            .filter(
                Result.examination_id == examination_id,
                Result.subject_id.in_(subject_ids),
            )
            .all()
        )

    def for_class(self, class_id: int, examination_id: int) -> List[Result]:
        """Every mark for one class in one examination."""
        return self.for_examination(examination_id, class_id=class_id)

    # --------------------------------------------------------- ranking

    def eligible_students(
        self, exam: Examination, class_id: Optional[int] = None
    ) -> List[Student]:
        """Who belongs in this examination's ranking group.

        Active accounts, enrolled for the examination's academic year, and -
        when ranking a class - in that class. Students who should not be
        compared are excluded here rather than filtered out afterwards, so no
        caller can accidentally rank against the wrong group.
        """
        if exam.term is None:
            return []

        query = (
            self.db.query(Student)
            .join(User, Student.user_id == User.id)
            .join(StudentSubject, StudentSubject.student_id == Student.id)
            .options(joinedload(Student.school_class))
            .filter(
                User.is_active.is_(True),
                StudentSubject.academic_year_id == exam.term.academic_year_id,
                StudentSubject.status == EnrollmentStatus.ACTIVE,
            )
        )
        if class_id is not None:
            query = query.filter(Student.class_id == class_id)

        # A student enrolled in several subjects joins several times.
        return list({s.id: s for s in query.all()}.values())

    def rank(
        self, exam: Examination, class_id: Optional[int] = None
    ) -> List[StudentAggregate]:
        """Rank the eligible students in an examination, best average first.

        Ranked on average rather than total, because students sit different
        numbers of subjects and a total would simply reward taking more.

        Ties share a position and the next position skips accordingly, so two
        students tied at 1st are followed by 3rd, not 2nd.

        A student with no marks in this examination is left out entirely: they
        did not come last, they were not measured.
        """
        eligible = {s.id: s for s in self.eligible_students(exam, class_id)}
        if not eligible:
            return []

        aggregates: Dict[int, StudentAggregate] = {}
        for result in self.for_examination(exam.id, class_id=class_id):
            student = eligible.get(result.student_id)
            if student is None:
                # Marked, but not part of this ranking group.
                continue
            aggregates.setdefault(result.student_id, StudentAggregate(student))
            aggregates[result.student_id].results.append(result)

        ordered = sorted(
            aggregates.values(),
            key=lambda a: (-(a.average or 0), a.student.last_name, a.student.first_name),
        )

        previous_average: Optional[float] = None
        previous_position = 0
        for index, entry in enumerate(ordered, start=1):
            if previous_average is not None and entry.average == previous_average:
                entry.position = previous_position
            else:
                entry.position = index
                previous_position = index
                previous_average = entry.average

        return ordered

    def position_of(
        self, student_id: int, exam: Examination, class_id: Optional[int] = None
    ) -> tuple[Optional[int], int]:
        """One student's position, and how many were ranked alongside them."""
        ranked = self.rank(exam, class_id)
        for entry in ranked:
            if entry.student.id == student_id:
                return entry.position, len(ranked)
        return None, len(ranked)

    # ------------------------------------------------------ statistics

    def subject_summary(self, subject_id: int, examination_id: int) -> dict:
        """How a subject performed: average, spread and pass rate."""
        results = self.for_subject(subject_id, examination_id)
        if not results:
            return {
                "count": 0, "average": None, "highest": None, "lowest": None,
                "pass_count": 0, "pass_rate": None, "grade_distribution": {},
            }

        marks = [r.marks for r in results]
        distribution: Dict[str, int] = {}
        passes = 0
        for r in results:
            key = r.grade or "-"
            distribution[key] = distribution.get(key, 0) + 1
            level = (
                r.student.school_class.level
                if r.student and r.student.school_class
                else None
            )
            if level and self.grading.is_pass(r.grade, level):
                passes += 1

        return {
            "count": len(results),
            "average": _average(marks),
            "highest": float(max(marks)),
            "lowest": float(min(marks)),
            "pass_count": passes,
            "pass_rate": round(passes / len(results) * 100, 1),
            "grade_distribution": dict(
                sorted(distribution.items(), key=lambda kv: kv[0])
            ),
        }

    # ------------------------------------------------- recalculation

    def recalculate_grades(self, examination_id: int) -> int:
        """Re-apply the current scale to every mark in an examination.

        Needed when the school edits its grading scale: the marks are
        unchanged but the grades and remarks derived from them are now stale,
        and a report card must never show a grade the scale no longer gives.
        """
        results = (
            self.db.query(Result)
            .options(joinedload(Result.student).joinedload(Student.school_class))
            .filter(Result.examination_id == examination_id)
            .all()
        )

        system_remarks = _system_remarks(self.grading)

        changed = 0
        for result in results:
            level = (
                result.student.school_class.level
                if result.student and result.student.school_class
                else None
            )
            grade, remark = self.grading.grade_for(result.marks, level)

            # Only replace a remark the system produced; a teacher's own
            # comment is theirs to keep.
            system_written = not result.remarks or result.remarks in system_remarks

            if result.grade != grade or (system_written and result.remarks != remark):
                result.grade = grade
                if system_written:
                    result.remarks = remark
                changed += 1

        if changed:
            self.db.commit()
        return changed


def _system_remarks(grading: GradingService) -> set:
    """Every remark the system has ever generated for itself.

    Recalculation replaces a remark only if the system wrote it, so a comment
    a teacher typed is never overwritten. That means recognising remarks from
    scales no longer in use as well as the current one - otherwise a grade
    would update while a remark from a previous scale stayed frozen beside it,
    which is worse than either updating or leaving both alone.
    """
    from app.models.enums import EducationLevel
    from app.services.grading_service import DEFAULT_BANDS
    from app.utils.grading import LEGACY_REMARKS

    remarks = set(LEGACY_REMARKS)
    for level in EducationLevel:
        remarks.update(b.remark for b in grading.bands_for(level))
        remarks.update(r for _, _, r, _ in DEFAULT_BANDS.get(level, []))
    return remarks


def subject_row(result: Result) -> dict:
    """One subject line, shared by every retrieval shape."""
    return {
        "result_id": result.id,
        "subject_id": result.subject_id,
        "subject_name": result.subject.name if result.subject else "",
        "subject_code": result.subject.code if result.subject else "",
        "marks": result.marks,
        "grade": result.grade,
        "remarks": result.remarks,
    }
