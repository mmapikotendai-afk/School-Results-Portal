"""Academic years, terms, examinations and result publication."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.academic_year import AcademicYear, Term
from app.models.assignment import TeacherSubject
from app.models.enrollment import StudentSubject
from app.models.enums import EnrollmentStatus, ExaminationStatus, SubmissionStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.submission import ResultSubmission
from app.schemas.academic import (
    AcademicYearCreate,
    AcademicYearUpdate,
    ExaminationCreate,
    ExaminationUpdate,
    TermCreate,
    TermUpdate,
)

S = ExaminationStatus

# The only status moves an examination may make. Everything else is rejected,
# so results cannot be published straight out of DRAFT, and a published
# examination has to be pulled back for review before it can change again.
ALLOWED_TRANSITIONS: Dict[ExaminationStatus, List[ExaminationStatus]] = {
    S.DRAFT: [S.SUBMISSION_OPEN],
    S.SUBMISSION_OPEN: [S.SUBMISSION_COMPLETE, S.DRAFT],
    S.SUBMISSION_COMPLETE: [S.UNDER_REVIEW, S.SUBMISSION_OPEN],
    S.UNDER_REVIEW: [S.PUBLISHED, S.SUBMISSION_OPEN],
    S.PUBLISHED: [S.UNDER_REVIEW],
}


def utcnow() -> datetime:
    """Naive UTC, matching how MySQL DATETIME columns are stored here."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AcademicService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ---------------------------------------------------- academic years

    def active_year(self) -> Optional[AcademicYear]:
        return (
            self.db.query(AcademicYear)
            .filter(AcademicYear.is_active.is_(True))
            .order_by(AcademicYear.id.desc())
            .first()
        )

    def resolve_year_id(self, academic_year_id: Optional[int]) -> Optional[int]:
        """Fall back to the active year when the caller did not name one."""
        if academic_year_id is not None:
            return academic_year_id
        year = self.active_year()
        return year.id if year else None

    def list_years(self) -> List[Tuple[AcademicYear, int]]:
        return (
            self.db.query(AcademicYear, func.count(Term.id))
            .outerjoin(Term, Term.academic_year_id == AcademicYear.id)
            .group_by(AcademicYear.id)
            .order_by(AcademicYear.name.desc())
            .all()
        )

    def get_year(self, year_id: int) -> Optional[AcademicYear]:
        return self.db.query(AcademicYear).filter(AcademicYear.id == year_id).first()

    def create_year(
        self, payload: AcademicYearCreate
    ) -> Tuple[Optional[AcademicYear], Optional[str]]:
        if self.db.query(AcademicYear.id).filter(AcademicYear.name == payload.name).first():
            return None, f"An academic year named {payload.name} already exists."

        year = AcademicYear(
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_active=False,
        )
        self.db.add(year)
        self.db.flush()
        if payload.is_active:
            self._make_year_active(year)
        self.db.commit()
        self.db.refresh(year)
        return year, None

    def update_year(
        self, year: AcademicYear, payload: AcademicYearUpdate
    ) -> Tuple[Optional[AcademicYear], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)
        name = data.get("name")
        if name and name != year.name:
            clash = (
                self.db.query(AcademicYear.id)
                .filter(AcademicYear.name == name, AcademicYear.id != year.id)
                .first()
            )
            if clash:
                return None, f"An academic year named {name} already exists."

        for field, value in data.items():
            setattr(year, field, value)
        self.db.commit()
        self.db.refresh(year)
        return year, None

    def _make_year_active(self, year: AcademicYear) -> None:
        """Exactly one year is active, so activating one stands the rest down."""
        self.db.query(AcademicYear).filter(AcademicYear.id != year.id).update(
            {AcademicYear.is_active: False}, synchronize_session=False
        )
        year.is_active = True

    def activate_year(self, year: AcademicYear) -> AcademicYear:
        self._make_year_active(year)
        self.db.commit()
        self.db.refresh(year)
        return year

    # ---------------------------------------------------------- terms

    def active_term(self) -> Optional[Term]:
        return (
            self.db.query(Term)
            .filter(Term.is_active.is_(True))
            .order_by(Term.id.desc())
            .first()
        )

    def list_terms(self, academic_year_id: Optional[int] = None) -> List[Tuple[Term, int]]:
        query = (
            self.db.query(Term, func.count(Examination.id))
            .outerjoin(Examination, Examination.term_id == Term.id)
            .options(joinedload(Term.academic_year))
            .group_by(Term.id)
        )
        if academic_year_id:
            query = query.filter(Term.academic_year_id == academic_year_id)
        return query.order_by(Term.academic_year_id.desc(), Term.name).all()

    def get_term(self, term_id: int) -> Optional[Term]:
        return self.db.query(Term).filter(Term.id == term_id).first()

    def create_term(self, payload: TermCreate) -> Tuple[Optional[Term], Optional[str]]:
        if not self.get_year(payload.academic_year_id):
            return None, "That academic year does not exist."

        clash = (
            self.db.query(Term.id)
            .filter(
                Term.academic_year_id == payload.academic_year_id,
                Term.name == payload.name,
            )
            .first()
        )
        if clash:
            return None, f"That academic year already has a term named {payload.name}."

        term = Term(
            academic_year_id=payload.academic_year_id,
            name=payload.name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_active=False,
        )
        self.db.add(term)
        self.db.flush()
        if payload.is_active:
            self._make_term_active(term)
        self.db.commit()
        self.db.refresh(term)
        return term, None

    def update_term(
        self, term: Term, payload: TermUpdate
    ) -> Tuple[Optional[Term], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)
        name = data.get("name")
        if name and name != term.name:
            clash = (
                self.db.query(Term.id)
                .filter(
                    Term.academic_year_id == term.academic_year_id,
                    Term.name == name,
                    Term.id != term.id,
                )
                .first()
            )
            if clash:
                return None, f"That academic year already has a term named {name}."

        for field, value in data.items():
            setattr(term, field, value)
        self.db.commit()
        self.db.refresh(term)
        return term, None

    def _make_term_active(self, term: Term) -> None:
        self.db.query(Term).filter(Term.id != term.id).update(
            {Term.is_active: False}, synchronize_session=False
        )
        term.is_active = True

    def activate_term(self, term: Term) -> Term:
        self._make_term_active(term)
        self.db.commit()
        self.db.refresh(term)
        return term

    # --------------------------------------------------- examinations

    def list_examinations(
        self, term_id: Optional[int] = None, status: Optional[ExaminationStatus] = None
    ) -> List[Examination]:
        query = self.db.query(Examination).options(
            joinedload(Examination.term).joinedload(Term.academic_year)
        )
        if term_id:
            query = query.filter(Examination.term_id == term_id)
        if status:
            query = query.filter(Examination.status == status)
        return query.order_by(Examination.created_at.desc()).all()

    def get_examination(self, exam_id: int) -> Optional[Examination]:
        return (
            self.db.query(Examination)
            .options(joinedload(Examination.term).joinedload(Term.academic_year))
            .filter(Examination.id == exam_id)
            .first()
        )

    def current_examination(self) -> Optional[Examination]:
        """The examination the dashboard reports on.

        Preference goes to one that is actively being worked on in the active
        term; otherwise the most recently created examination anywhere, so a
        newly set-up school still sees something.
        """
        live = [S.SUBMISSION_OPEN, S.SUBMISSION_COMPLETE, S.UNDER_REVIEW]

        term = self.active_term()
        if term:
            exam = (
                self.db.query(Examination)
                .filter(Examination.term_id == term.id, Examination.status.in_(live))
                .order_by(Examination.created_at.desc())
                .first()
            )
            if exam:
                return exam

        exam = (
            self.db.query(Examination)
            .filter(Examination.status.in_(live))
            .order_by(Examination.created_at.desc())
            .first()
        )
        if exam:
            return exam

        return (
            self.db.query(Examination).order_by(Examination.created_at.desc()).first()
        )

    def create_examination(
        self, payload: ExaminationCreate
    ) -> Tuple[Optional[Examination], Optional[str]]:
        if not self.get_term(payload.term_id):
            return None, "That term does not exist."

        clash = (
            self.db.query(Examination.id)
            .filter(
                Examination.term_id == payload.term_id, Examination.name == payload.name
            )
            .first()
        )
        if clash:
            return None, f"That term already has an examination named {payload.name}."

        exam = Examination(
            term_id=payload.term_id,
            name=payload.name,
            submission_deadline=payload.submission_deadline,
            status=S.DRAFT,
        )
        self.db.add(exam)
        self.db.commit()
        self.db.refresh(exam)
        return exam, None

    def update_examination(
        self, exam: Examination, payload: ExaminationUpdate
    ) -> Tuple[Optional[Examination], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)
        name = data.get("name")
        if name and name != exam.name:
            clash = (
                self.db.query(Examination.id)
                .filter(
                    Examination.term_id == exam.term_id,
                    Examination.name == name,
                    Examination.id != exam.id,
                )
                .first()
            )
            if clash:
                return None, f"That term already has an examination named {name}."

        for field, value in data.items():
            setattr(exam, field, value)
        self.db.commit()
        self.db.refresh(exam)
        return exam, None

    # ------------------------------------------- status and publication

    def allowed_transitions(self, exam: Examination) -> List[ExaminationStatus]:
        return ALLOWED_TRANSITIONS.get(exam.status, [])

    def set_status(
        self,
        exam: Examination,
        new_status: ExaminationStatus,
        acting_user_id: Optional[int] = None,
    ) -> Tuple[Optional[Examination], Optional[str]]:
        if new_status == exam.status:
            return exam, None

        if new_status not in self.allowed_transitions(exam):
            allowed = ", ".join(s.value for s in self.allowed_transitions(exam)) or "none"
            return None, (
                f"An examination that is {exam.status.value} cannot move to "
                f"{new_status.value}. Allowed next steps: {allowed}."
            )

        if new_status == S.PUBLISHED:
            can, reason = self.can_publish(exam)
            if not can:
                return None, reason

        exam.status = new_status
        if new_status == S.PUBLISHED:
            exam.published_at = utcnow()
            exam.published_by_id = acting_user_id
        else:
            # Pulling an examination back clears the record of its publication;
            # re-publishing is a fresh decision by whoever makes it.
            exam.published_at = None
            exam.published_by_id = None

        # Opening submissions is what creates the tracking rows, so the
        # monitor reflects the assignments as they stand at that moment.
        if new_status == S.SUBMISSION_OPEN:
            self.sync_submission_tracking(exam)

        self.db.commit()
        self.db.refresh(exam)
        return exam, None

    def missing_submissions(self, exam: Examination) -> List[ResultSubmission]:
        """The required submissions that have not been delivered.

        Required means an active teacher-subject assignment for this
        examination. A subject with nobody enrolled owes nothing and is
        already counted complete, so it never appears here.
        """
        from app.services.submission_service import SubmissionService

        return SubmissionService(self.db).outstanding(exam)

    def can_publish(self, exam: Examination) -> Tuple[bool, Optional[str]]:
        """Whether this examination may be published, and why not if it may not.

        Publication is withheld until every required submission is in. A
        partially collected examination published early shows some students a
        report card with subjects silently missing from it, which is worse
        than showing them nothing yet.
        """
        count = (
            self.db.query(func.count(Result.id))
            .filter(Result.examination_id == exam.id)
            .scalar()
            or 0
        )
        if count == 0:
            return False, (
                "There are no results recorded for this examination, so there is "
                "nothing to publish."
            )

        missing = self.missing_submissions(exam)
        if missing:
            names = ", ".join(
                f"{m.subject.name} ({m.teacher.full_name})" for m in missing[:3]
            )
            more = f" and {len(missing) - 3} more" if len(missing) > 3 else ""
            return False, (
                f"{len(missing)} required submission"
                f"{'' if len(missing) == 1 else 's'} "
                f"{'is' if len(missing) == 1 else 'are'} still missing: {names}{more}. "
                "Collect them, or upload on behalf of the teacher, before publishing."
            )

        return True, None

    def is_ready_to_close(self, exam: Examination) -> bool:
        """True when every required submission is in.

        Drives the "All Required Results Submitted" signal. It is only ever a
        signal: closing submissions and publishing both remain deliberate acts.
        """
        from app.services.submission_service import SubmissionService

        rows = SubmissionService(self.db).recalculate(exam)
        return bool(rows) and not any(
            r.status in {SubmissionStatus.PENDING, SubmissionStatus.PARTIAL,
                         SubmissionStatus.OVERDUE}
            for r in rows
        )

    def sync_submission_tracking(self, exam: Examination) -> int:
        """Create tracking rows for assignments that do not have one yet."""
        from app.services.submission_service import SubmissionService

        created, _total = SubmissionService(self.db).sync(exam, commit=False)
        return created

    # ------------------------------------------------------- rollups

    def submission_rollup(self, exam_id: int) -> Dict[str, int]:
        """Counts behind the progress bars.

        Recomputed on read from enrolment and results, so a deadline that
        passed a minute ago is reflected without any scheduled job.
        """
        from app.services.submission_service import SubmissionService

        exam = self.get_examination(exam_id)
        if exam is None:
            return {"total": 0, "done": 0, "pending": 0, "overdue": 0, "progress": 0}
        return SubmissionService(self.db).rollup(exam)

    def result_count(self, exam_id: int) -> int:
        return (
            self.db.query(func.count(Result.id))
            .filter(Result.examination_id == exam_id)
            .scalar()
            or 0
        )
