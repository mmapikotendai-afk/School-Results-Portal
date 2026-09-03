"""School information and the administrator dashboard rollup."""

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import ExaminationStatus, UserRole
from app.models.examination import Examination
from app.models.result import Result
from app.models.school_class import SchoolClass
from app.models.school_settings import SchoolSettings
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.school import (
    CurrentExamination,
    DashboardStats,
    OutstandingLine,
    PublicationState,
    SchoolSettingsUpdate,
)
from app.services.academic_service import AcademicService, utcnow


class SchoolService:
    """Reads and writes the single school_settings row."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self) -> Optional[SchoolSettings]:
        return self.db.query(SchoolSettings).order_by(SchoolSettings.id).first()

    def get_or_create(self, default_name: str = "Your School") -> SchoolSettings:
        """The table holds exactly one row; create it on first read."""
        settings = self.get()
        if settings is None:
            settings = SchoolSettings(school_name=default_name)
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update(self, payload: SchoolSettingsUpdate) -> SchoolSettings:
        """Save the school record.

        Values are stored as Pydantic validated them. Only EmailStr is
        converted, because it is a str subclass the driver would otherwise
        bind as an unexpected type; coercing everything to str would turn a
        boolean into the string "False", which is not false to anybody.
        """
        settings = self.get_or_create(payload.school_name)

        for field, value in payload.model_dump(exclude_unset=True).items():
            if isinstance(value, str):
                value = str(value)
            setattr(settings, field, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    def set_logo(self, logo_path: Optional[str]) -> SchoolSettings:
        settings = self.get_or_create()
        settings.logo_path = logo_path
        self.db.commit()
        self.db.refresh(settings)
        return settings


class DashboardService:
    """Everything the administrator overview needs, assembled in one place."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.academic = AcademicService(db)

    def _count(self, model, *filters) -> int:
        query = self.db.query(func.count(model.id))
        for condition in filters:
            query = query.filter(condition)
        return query.scalar() or 0

    def stats(self) -> DashboardStats:
        stats = DashboardStats()

        # Head counts reflect active accounts, which is what "how many students
        # do we have" means to an administrator.
        stats.total_students = (
            self.db.query(func.count(Student.id))
            .join(User, Student.user_id == User.id)
            .filter(User.is_active.is_(True), User.role == UserRole.STUDENT)
            .scalar()
            or 0
        )
        stats.total_teachers = (
            self.db.query(func.count(Teacher.id))
            .join(User, Teacher.user_id == User.id)
            .filter(User.is_active.is_(True), User.role == UserRole.TEACHER)
            .scalar()
            or 0
        )
        stats.total_subjects = self._count(Subject, Subject.is_active.is_(True))
        stats.total_classes = self._count(SchoolClass, SchoolClass.is_active.is_(True))

        year = self.academic.active_year()
        term = self.academic.active_term()
        stats.active_year_name = year.name if year else None
        stats.active_term_name = term.name if term else None

        exam = self.academic.current_examination()
        if exam:
            deadline = exam.submission_deadline
            stats.current_examination = CurrentExamination(
                id=exam.id,
                name=exam.name,
                term_name=exam.term.name if exam.term else None,
                academic_year_name=(
                    exam.term.academic_year.name
                    if exam.term and exam.term.academic_year
                    else None
                ),
                status=exam.status,
                submission_deadline=deadline,
                is_past_deadline=bool(deadline and utcnow() > deadline),
            )

            rollup = self.academic.submission_rollup(exam.id)
            stats.submissions_total = rollup["total"]
            stats.submissions_complete = rollup["done"]
            stats.submissions_pending = rollup["pending"]
            stats.submissions_overdue = rollup["overdue"]
            stats.submission_progress = (
                round(rollup["done"] / rollup["total"] * 100)
                if rollup["total"]
                else 0
            )

            self._outstanding(stats, exam)
            stats.publication = self._publication(exam, rollup)

        # Publication is governed by the examination status, so a result is
        # published exactly when the examination it belongs to is.
        published_exam_ids = [
            row.id
            for row in self.db.query(Examination.id).filter(
                Examination.status == ExaminationStatus.PUBLISHED
            )
        ]
        total_results = self._count(Result)
        if published_exam_ids:
            stats.results_published = (
                self.db.query(func.count(Result.id))
                .filter(Result.examination_id.in_(published_exam_ids))
                .scalar()
                or 0
            )
        stats.results_unpublished = total_results - stats.results_published

        return stats

    def _outstanding(self, stats: DashboardStats, exam: Examination) -> None:
        """Name the teachers who still owe results, split by overdue or not."""
        from app.models.enums import SubmissionStatus
        from app.services.submission_service import SubmissionService

        deadline = exam.submission_deadline
        now = utcnow()

        for row in SubmissionService(self.db).outstanding(exam):
            days = None
            if deadline and now > deadline:
                # Whole days, so "1 day overdue" means a day has actually passed.
                days = (now - deadline).days

            line = OutstandingLine(
                submission_id=row.id,
                teacher_id=row.teacher_id,
                teacher_name=row.teacher.full_name if row.teacher else "",
                subject_id=row.subject_id,
                subject_name=row.subject.name if row.subject else "",
                subject_code=row.subject.code if row.subject else "",
                deadline=deadline,
                days_overdue=days if row.status == SubmissionStatus.OVERDUE else None,
                submitted_count=row.submitted_count,
                expected_count=row.expected_count,
            )

            if row.status == SubmissionStatus.OVERDUE:
                stats.overdue_submissions.append(line)
            else:
                stats.pending_submissions.append(line)

    @staticmethod
    def _publication(exam: Examination, rollup: dict) -> PublicationState:
        """The one sentence that says where this examination has got to."""
        if exam.status == ExaminationStatus.PUBLISHED:
            return PublicationState(
                state="published",
                label="Results Published",
                detail="Students can view their results.",
                published_at=exam.published_at,
                published_by=exam.published_by.full_name if exam.published_by else None,
            )

        if exam.status in (
            ExaminationStatus.SUBMISSION_COMPLETE,
            ExaminationStatus.UNDER_REVIEW,
        ):
            return PublicationState(
                state="awaiting_review",
                label="Results Awaiting Review",
                detail="All required results are in and can be reviewed, then published.",
            )

        outstanding = rollup.get("pending", 0)
        return PublicationState(
            state="awaiting_submissions",
            label="Results Awaiting Submissions",
            detail=(
                f"{outstanding} subject{'' if outstanding == 1 else 's'} still to be "
                "submitted before results can be published."
                if outstanding
                else "Submissions have not been opened yet."
            ),
        )
