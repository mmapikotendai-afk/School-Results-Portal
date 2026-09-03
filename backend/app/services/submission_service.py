"""Submission tracking: deriving where every teacher stands on an examination.

The status of a submission is never simply declared. It is computed from four
things, exactly as the workflow describes:

  1. assigned teachers   - teacher_subjects rows that are still active
  2. assigned subjects   - the subject on each of those assignments
  3. examination         - its term, academic year and submission deadline
  4. submission records  - the results actually on record for that subject

Recomputing rather than storing a flag means the monitor cannot drift: a
student enrolled after the deadline raises the expected count, and a mark
uploaded late flips the row to LATE, without anything having to remember to
update a field.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import TeacherSubject
from app.models.enrollment import StudentSubject
from app.models.enums import EnrollmentStatus, SubmissionStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.student import Student
from app.models.submission import ResultSubmission
from app.models.user import User
from app.services.academic_service import utcnow

# Statuses meaning "this teacher still owes us marks".
OUTSTANDING = {SubmissionStatus.PENDING, SubmissionStatus.PARTIAL, SubmissionStatus.OVERDUE}

# Statuses meaning "everything expected has been received".
COMPLETE = {SubmissionStatus.SUBMITTED, SubmissionStatus.LATE}


class SubmissionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------- the counts

    def expected_counts(self, exam: Examination) -> Dict[int, int]:
        """How many marks each subject owes: its active enrolment roll.

        Counts only students whose accounts are still active. A learner who has
        left the school is not owed a mark, and leaving them in the total would
        make it impossible for the teacher to ever reach a complete submission.

        One grouped query rather than one per subject, so the monitor stays
        cheap on a school with a long subject list.
        """
        year_id = exam.term.academic_year_id if exam.term else None
        if year_id is None:
            return {}

        rows = (
            self.db.query(StudentSubject.subject_id, func.count(StudentSubject.id))
            .join(Student, Student.id == StudentSubject.student_id)
            .join(User, Student.user_id == User.id)
            .filter(
                StudentSubject.academic_year_id == year_id,
                StudentSubject.status == EnrollmentStatus.ACTIVE,
                User.is_active.is_(True),
            )
            .group_by(StudentSubject.subject_id)
            .all()
        )
        return {subject_id: count for subject_id, count in rows}

    def submitted_counts(self, exam: Examination) -> Dict[int, int]:
        """How many marks are actually on record for each subject.

        Counted per subject rather than per teacher: where two teachers share a
        subject the schema has no way to attribute a mark to one of them, so
        they share the progress figure for it.
        """
        rows = (
            self.db.query(Result.subject_id, func.count(Result.id))
            .filter(Result.examination_id == exam.id)
            .group_by(Result.subject_id)
            .all()
        )
        return {subject_id: count for subject_id, count in rows}

    # ------------------------------------------------------ the status

    @staticmethod
    def derive_status(
        expected: int,
        submitted: int,
        deadline: Optional[datetime],
        submitted_at: Optional[datetime],
        now: Optional[datetime] = None,
    ) -> SubmissionStatus:
        """Work out where one submission stands.

        A subject with nobody enrolled owes nothing, so it counts as done
        rather than sitting permanently overdue on the monitor.
        """
        now = now or utcnow()
        past_deadline = bool(deadline and now > deadline)

        if expected == 0:
            return SubmissionStatus.SUBMITTED

        if submitted >= expected:
            # Complete. Whether it counts as late is decided by when the marks
            # arrived, not by whether the deadline has since passed.
            finished_late = bool(deadline and submitted_at and submitted_at > deadline)
            # No recorded submission time and the deadline has gone is still late.
            if finished_late or (past_deadline and submitted_at is None):
                return SubmissionStatus.LATE
            return SubmissionStatus.SUBMITTED

        if past_deadline:
            return SubmissionStatus.OVERDUE

        return SubmissionStatus.PARTIAL if submitted > 0 else SubmissionStatus.PENDING

    def recalculate(self, exam: Examination, commit: bool = True) -> List[ResultSubmission]:
        """Refresh every tracking row for an examination and return them.

        Called on the read paths, so the monitor and the dashboard are correct
        the moment a deadline passes. No scheduled job is involved: the status
        is a function of the data and the clock, evaluated when it is asked for.
        """
        rows = (
            self.db.query(ResultSubmission)
            .options(
                joinedload(ResultSubmission.teacher),
                joinedload(ResultSubmission.subject),
                joinedload(ResultSubmission.submitted_by),
            )
            .filter(ResultSubmission.examination_id == exam.id)
            .all()
        )
        if not rows:
            return []

        expected_by_subject = self.expected_counts(exam)
        submitted_by_subject = self.submitted_counts(exam)
        now = utcnow()
        changed = False

        for row in rows:
            expected = expected_by_subject.get(row.subject_id, 0)
            submitted = submitted_by_subject.get(row.subject_id, 0)
            status = self.derive_status(
                expected, submitted, exam.submission_deadline, row.submitted_at, now
            )

            if (
                row.expected_count != expected
                or row.submitted_count != submitted
                or row.status != status
            ):
                row.expected_count = expected
                row.submitted_count = submitted
                row.status = status
                changed = True

        if changed and commit:
            self.db.commit()
        return rows

    # ------------------------------------------------------- rollups

    def rollup(self, exam: Examination) -> Dict[str, int]:
        """Counts behind the progress bars, from freshly recomputed rows."""
        rows = self.recalculate(exam)

        complete = sum(1 for r in rows if r.status in COMPLETE)
        overdue = sum(1 for r in rows if r.status == SubmissionStatus.OVERDUE)
        return {
            "total": len(rows),
            "done": complete,
            "pending": len(rows) - complete,
            "overdue": overdue,
            "progress": round(complete / len(rows) * 100) if rows else 0,
        }

    def outstanding(self, exam: Examination) -> List[ResultSubmission]:
        """Teachers who still owe marks, worst first, for chasing up."""
        rows = self.recalculate(exam)
        order = {
            SubmissionStatus.OVERDUE: 0,
            SubmissionStatus.PARTIAL: 1,
            SubmissionStatus.PENDING: 2,
        }
        return sorted(
            (r for r in rows if r.status in OUTSTANDING),
            key=lambda r: (order.get(r.status, 9), r.teacher.last_name if r.teacher else ""),
        )

    # -------------------------------------------------------- syncing

    def sync(self, exam: Examination, commit: bool = True) -> Tuple[int, int]:
        """Create tracking rows for assignments that do not have one yet.

        Returns (created, total). Existing rows are left alone, so re-running
        this never resets a submission already recorded; only the counts are
        brought up to date, by the recalculation that follows.
        """
        year_id = exam.term.academic_year_id if exam.term else None
        if year_id is None:
            return 0, 0

        assignments = (
            self.db.query(TeacherSubject)
            .filter(
                TeacherSubject.academic_year_id == year_id,
                TeacherSubject.is_active.is_(True),
            )
            .all()
        )

        existing = {
            row.teacher_subject_id
            for row in self.db.query(ResultSubmission.teacher_subject_id).filter(
                ResultSubmission.examination_id == exam.id
            )
        }

        created = 0
        for assignment in assignments:
            if assignment.id in existing:
                continue
            self.db.add(
                ResultSubmission(
                    examination_id=exam.id,
                    teacher_subject_id=assignment.id,
                    teacher_id=assignment.teacher_id,
                    subject_id=assignment.subject_id,
                    status=SubmissionStatus.PENDING,
                    expected_count=0,
                    submitted_count=0,
                )
            )
            created += 1

        self.db.flush()
        self.recalculate(exam, commit=False)
        if commit:
            self.db.commit()

        return created, len(assignments)
