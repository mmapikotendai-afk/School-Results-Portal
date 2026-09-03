"""What a student may see of their own results.

Two rules govern everything here, and both are enforced in this one place so
there is no second path that could disagree with them:

  1. A result is visible only when the examination it belongs to is PUBLISHED.
     An examination still being collected, closed, or under review discloses
     nothing at all - not the mark, not the grade, not whether one exists.

  2. Publication is permanent from the student point of view. Results released
     in an earlier term stay visible for good; opening a new examination never
     hides what has already been published.
"""

from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.academic_year import Term
from app.models.enrollment import StudentSubject
from app.models.enums import EnrollmentStatus, ExaminationStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.student import Student
from app.schemas.student_view import (
    HistoryEntry,
    PendingExamination,
    StudentExaminationResults,
    StudentHistory,
    StudentResultRow,
    StudentResultsResponse,
)

# What a student is told about an examination that is not published yet.
# The headline is the same in every case - the results are not available - and
# the detail only explains how far along the school is. None of it discloses a
# mark, a grade, or even whether one exists for this student.
PENDING_HEADLINE = "Results Not Yet Published"

PENDING_MESSAGE = {
    ExaminationStatus.DRAFT: "This examination has not started yet.",
    ExaminationStatus.SUBMISSION_OPEN: (
        "The school is currently completing the results submission process."
    ),
    ExaminationStatus.SUBMISSION_COMPLETE: (
        "All results have been submitted and are being checked by the school."
    ),
    ExaminationStatus.UNDER_REVIEW: (
        "Your results are being reviewed by the school before they are released."
    ),
}


class StudentResultService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def results_for(self, student: Student) -> StudentResultsResponse:
        """Build the student results view, published examinations only."""
        response = StudentResultsResponse(
            student_number=student.student_number,
            full_name=student.full_name,
            class_name=student.school_class.name if student.school_class else None,
            level=student.level,
            enrolled_subjects=self._enrolled_subject_names(student),
        )

        # Only PUBLISHED examinations are ever joined against the results
        # table, so an unpublished mark cannot reach the response by any route.
        rows = (
            self.db.query(Result)
            .join(Examination, Result.examination_id == Examination.id)
            .options(
                joinedload(Result.subject),
                joinedload(Result.examination)
                .joinedload(Examination.term)
                .joinedload(Term.academic_year),
            )
            .filter(
                Result.student_id == student.id,
                Examination.status == ExaminationStatus.PUBLISHED,
            )
            .all()
        )

        by_exam: dict[int, List[Result]] = {}
        for row in rows:
            by_exam.setdefault(row.examination_id, []).append(row)

        published: List[StudentExaminationResults] = []
        for exam_id, exam_rows in by_exam.items():
            exam = exam_rows[0].examination
            marks = [float(r.marks) for r in exam_rows]
            best = max(exam_rows, key=lambda r: r.marks)

            published.append(
                StudentExaminationResults(
                    examination_id=exam_id,
                    examination_name=exam.name,
                    term_name=exam.term.name if exam.term else None,
                    academic_year_name=(
                        exam.term.academic_year.name
                        if exam.term and exam.term.academic_year
                        else None
                    ),
                    published_at=exam.published_at,
                    results=sorted(
                        (
                            StudentResultRow(
                                subject_id=r.subject_id,
                                subject_name=r.subject.name,
                                subject_code=r.subject.code,
                                marks=r.marks,
                                grade=r.grade,
                                remarks=r.remarks,
                            )
                            for r in exam_rows
                        ),
                        key=lambda r: r.subject_name,
                    ),
                    subjects_taken=len(exam_rows),
                    average=round(sum(marks) / len(marks), 2) if marks else None,
                    best_subject=best.subject.name if best else None,
                )
            )

        # Newest first, so the most recent report is at the top.
        response.published = sorted(
            published,
            key=lambda e: (e.published_at is None, e.published_at),
            reverse=True,
        )

        response.in_progress = self._in_progress(student)
        return response

    def _in_progress(self, student: Student) -> List[PendingExamination]:
        """Examinations under way, named but with nothing disclosed.

        Naming them is a kindness: without it a student sitting an examination
        sees an empty screen and cannot tell whether the school has forgotten
        them. No mark, grade or count is included.
        """
        year_ids = {
            row.academic_year_id
            for row in self.db.query(StudentSubject.academic_year_id).filter(
                StudentSubject.student_id == student.id,
                StudentSubject.status == EnrollmentStatus.ACTIVE,
            )
        }
        if not year_ids:
            return []

        exams = (
            self.db.query(Examination)
            .join(Term, Examination.term_id == Term.id)
            .options(joinedload(Examination.term).joinedload(Term.academic_year))
            .filter(
                Term.academic_year_id.in_(year_ids),
                Examination.status != ExaminationStatus.PUBLISHED,
                # A draft examination is not yet real to anyone but the office.
                Examination.status != ExaminationStatus.DRAFT,
            )
            .order_by(Examination.created_at.desc())
            .all()
        )

        return [
            PendingExamination(
                examination_id=exam.id,
                examination_name=exam.name,
                term_name=exam.term.name if exam.term else None,
                academic_year_name=(
                    exam.term.academic_year.name
                    if exam.term and exam.term.academic_year
                    else None
                ),
                status=exam.status.value,
                headline=PENDING_HEADLINE,
                message=PENDING_MESSAGE.get(
                    exam.status, "Your results are not available yet."
                ),
            )
            for exam in exams
        ]

    def _enrolled_subject_names(self, student: Student) -> List[str]:
        rows = (
            self.db.query(StudentSubject)
            .options(joinedload(StudentSubject.subject))
            .filter(
                StudentSubject.student_id == student.id,
                StudentSubject.status == EnrollmentStatus.ACTIVE,
            )
            .all()
        )
        return sorted(row.subject.name for row in rows if row.subject)

    def history_for(self, student: Student) -> StudentHistory:
        """Every examination the student has, published or not.

        Built from the same results_for() call that enforces the publication
        rule, so the history cannot disagree with what the results screen
        shows. An unpublished entry carries a headline and a message and no
        figures at all.
        """
        full = self.results_for(student)

        entries = [
            HistoryEntry(
                examination_id=e.examination_id,
                examination_name=e.examination_name,
                term_name=e.term_name,
                academic_year_name=e.academic_year_name,
                is_published=True,
                published_at=e.published_at,
                subjects_taken=e.subjects_taken,
                average=e.average,
            )
            for e in full.published
        ]
        entries += [
            HistoryEntry(
                examination_id=p.examination_id,
                examination_name=p.examination_name,
                term_name=p.term_name,
                academic_year_name=p.academic_year_name,
                is_published=False,
                headline=p.headline,
                message=p.message,
            )
            for p in full.in_progress
        ]

        # Published first and newest first; unpublished after, since they are
        # the ones the student is waiting on rather than reading.
        entries.sort(
            key=lambda e: (
                not e.is_published,
                -(e.published_at.timestamp() if e.published_at else 0),
                e.examination_name,
            )
        )

        return StudentHistory(
            student_number=student.student_number,
            full_name=student.full_name,
            class_name=student.school_class.name if student.school_class else None,
            level=student.level,
            entries=entries,
            published_count=len(full.published),
            pending_count=len(full.in_progress),
        )

    def published_examination_for(
        self, student: Student, examination_id: int
    ) -> Optional[StudentExaminationResults]:
        """One published examination, or None.

        None covers both "no such examination" and "not published yet", so a
        student probing ids cannot tell an unpublished examination from one
        that does not exist.
        """
        full = self.results_for(student)
        for entry in full.published:
            if entry.examination_id == examination_id:
                return entry
        return None
