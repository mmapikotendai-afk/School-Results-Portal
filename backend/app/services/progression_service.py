"""Transactional annual placement, promotion, return, and history workflows."""

import uuid
from types import SimpleNamespace
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from app.models.academic_year import AcademicYear
from app.models.enrollment import StudentSubject
from app.models.enums import (
    EnrollmentStatus,
    FormLevel,
    ProgressionAction,
    StudentEnrollmentStatus,
    SubjectLevel,
)
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.student_enrollment import EnrollmentAudit, StudentEnrollment
from app.models.subject import Subject
from app.schemas.progression import (
    EnrollmentHistoryItem,
    ProgressionPreview,
    ProgressionPreviewRow,
    ProgressionRosterRow,
    ProgressionRequest,
    ProgressionResult,
)
from app.services.people_service import StudentService


class ProgressionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def history(self, student_id: int) -> List[EnrollmentHistoryItem]:
        rows = (
            self.db.query(StudentEnrollment)
            .options(joinedload(StudentEnrollment.academic_year))
            .filter(StudentEnrollment.student_id == student_id)
            .order_by(StudentEnrollment.academic_year_id, StudentEnrollment.id)
            .all()
        )
        return [
            EnrollmentHistoryItem(
                id=row.id,
                academic_year_id=row.academic_year_id,
                academic_year_name=row.academic_year.name,
                class_id=row.class_id,
                class_name=row.class_name_snapshot,
                form_level=row.form_level,
                academic_level=row.academic_level,
                status=row.status,
                enrolled_at=row.enrolled_at,
                status_changed_at=row.status_changed_at,
            )
            for row in rows
        ]

    def roster(
        self, academic_year_id: int, class_id: Optional[int] = None,
        status: Optional[StudentEnrollmentStatus] = None,
    ) -> List[ProgressionRosterRow]:
        query = (
            self.db.query(StudentEnrollment)
            .options(joinedload(StudentEnrollment.student))
            .filter(StudentEnrollment.academic_year_id == academic_year_id)
        )
        if class_id is not None:
            query = query.filter(StudentEnrollment.class_id == class_id)
        if status is not None:
            query = query.filter(StudentEnrollment.status == status)
        rows = query.order_by(StudentEnrollment.class_name_snapshot, StudentEnrollment.student_id).all()
        return [
            ProgressionRosterRow(
                student_id=row.student_id,
                student_number=row.student.student_number,
                student_name=row.student.full_name,
                class_id=row.class_id,
                class_name=row.class_name_snapshot,
                form_level=row.form_level,
                academic_level=row.academic_level,
                status=row.status,
            )
            for row in rows
        ]

    def audit_history(self, student_id: int) -> List[EnrollmentAudit]:
        return (
            self.db.query(EnrollmentAudit)
            .filter(EnrollmentAudit.student_id == student_id)
            .order_by(EnrollmentAudit.created_at.desc(), EnrollmentAudit.id.desc())
            .all()
        )

    def preview(self, payload: ProgressionRequest) -> ProgressionPreview:
        source_year = self.db.get(AcademicYear, payload.source_academic_year_id)
        target_year = self.db.get(AcademicYear, payload.target_academic_year_id)
        target_class = self.db.get(SchoolClass, payload.target_class_id)
        report = ProgressionPreview(action=payload.action)
        if not source_year or not target_year or not target_class:
            report.detail = "Choose valid source and target years and a target class."
            report.rejected = len(payload.student_ids)
            return report

        subject_problem = self._subject_problem(payload, target_class)
        for student_id in dict.fromkeys(payload.student_ids):
            student = self.db.get(Student, student_id)
            source = self._enrollment(student_id, source_year.id)
            problem = subject_problem or self._placement_problem(
                payload, student, source, target_year, target_class
            )
            report.rows.append(
                ProgressionPreviewRow(
                    student_id=student_id,
                    student_number=student.student_number if student else "Unknown",
                    student_name=student.full_name if student else "Unknown student",
                    from_year=source_year.name,
                    from_form=source.form_level if source else target_class.form_level,
                    from_class=source.class_name_snapshot if source else "No enrollment",
                    to_year=target_year.name,
                    to_form=target_class.form_level,
                    to_class=target_class.name,
                    valid=problem is None,
                    message=problem or "Ready",
                )
            )
        report.accepted = sum(row.valid for row in report.rows)
        report.rejected = len(report.rows) - report.accepted
        report.can_confirm = report.accepted > 0 and report.rejected == 0
        report.detail = (
            f"{report.accepted} student{'' if report.accepted == 1 else 's'} ready."
            if report.can_confirm
            else f"{report.rejected} row{'' if report.rejected == 1 else 's'} must be corrected."
        )
        return report

    def apply(self, payload: ProgressionRequest, actor_user_id: int) -> ProgressionResult:
        preview = self.preview(payload)
        if not preview.can_confirm:
            raise ValueError(preview.detail)
        target_class = self.db.get(SchoolClass, payload.target_class_id)
        batch_id = str(uuid.uuid4())
        created = updated = subject_count = 0
        students = StudentService(self.db)

        for student_id in dict.fromkeys(payload.student_ids):
            student = self.db.get(Student, student_id)
            source = self._enrollment(student_id, payload.source_academic_year_id)
            target = self._enrollment(student_id, payload.target_academic_year_id)
            existing = target or source
            before = SimpleNamespace(
                academic_year_id=existing.academic_year_id,
                form_level=existing.form_level,
                class_name_snapshot=existing.class_name_snapshot,
                status=existing.status,
            )
            if target is None:
                target = StudentEnrollment(
                    student_id=student.id,
                    academic_year_id=payload.target_academic_year_id,
                    class_id=target_class.id,
                    class_name_snapshot=target_class.name,
                    form_level=target_class.form_level,
                    academic_level=target_class.level,
                    status=StudentEnrollmentStatus.PENDING_RETURN,
                )
                self.db.add(target)
                self.db.flush()
                created += 1
            else:
                target.class_id = target_class.id
                target.class_name_snapshot = target_class.name
                target.form_level = target_class.form_level
                target.academic_level = target_class.level
                updated += 1

            chosen_subjects = payload.subject_ids
            if payload.action != ProgressionAction.O_LEVEL_TO_A_LEVEL:
                chosen_subjects = [
                    row.subject_id
                    for row in self.db.query(StudentSubject).filter(
                        StudentSubject.student_id == student.id,
                        StudentSubject.academic_year_id == payload.source_academic_year_id,
                        StudentSubject.status == EnrollmentStatus.ACTIVE,
                    )
                ]
            students.set_subjects(student, chosen_subjects, payload.target_academic_year_id)
            subject_count += len(chosen_subjects)
            self._audit(student, actor_user_id, payload.action, batch_id, before, target)

        self.db.commit()
        return ProgressionResult(
            action=payload.action,
            batch_id=batch_id,
            students_updated=len(set(payload.student_ids)),
            enrollments_created=created,
            enrollments_updated=updated,
            subject_enrollments_created=subject_count,
            detail=(
                f"{len(set(payload.student_ids))} student placement"
                f"{'' if len(set(payload.student_ids)) == 1 else 's'} prepared as Pending Return. "
                "Confirm return separately when each student reports."
            ),
        )

    def confirm_return(
        self, student_ids: List[int], academic_year_id: int, actor_user_id: int
    ) -> ProgressionResult:
        batch_id = str(uuid.uuid4())
        rows: List[Tuple[Student, StudentEnrollment]] = []
        for student_id in dict.fromkeys(student_ids):
            student = self.db.get(Student, student_id)
            enrollment = self._enrollment(student_id, academic_year_id)
            if not student or not enrollment:
                raise ValueError("Every selected student must have an enrollment in the chosen year.")
            if enrollment.status != StudentEnrollmentStatus.PENDING_RETURN:
                raise ValueError(f"{student.student_number} is not Pending Return.")
            rows.append((student, enrollment))
        for student, enrollment in rows:
            old_status = enrollment.status
            enrollment.status = StudentEnrollmentStatus.ACTIVE
            student.class_id = enrollment.class_id
            self._audit(
                student, actor_user_id, ProgressionAction.CONFIRM_RETURN, batch_id,
                enrollment, enrollment, from_status=old_status,
            )
        self.db.commit()
        return ProgressionResult(
            action=ProgressionAction.CONFIRM_RETURN,
            batch_id=batch_id,
            students_updated=len(rows),
            enrollments_updated=len(rows),
            detail=f"Confirmed return for {len(rows)} student{'' if len(rows) == 1 else 's'}.",
        )

    def _enrollment(self, student_id: int, year_id: int) -> Optional[StudentEnrollment]:
        return self.db.query(StudentEnrollment).filter_by(
            student_id=student_id, academic_year_id=year_id
        ).first()

    def _placement_problem(self, payload, student, source, target_year, target_class):
        if not student:
            return "Student not found."
        if not source:
            return "No source-year enrollment exists."
        if source.status not in {
            StudentEnrollmentStatus.ACTIVE, StudentEnrollmentStatus.PENDING_RETURN
        }:
            return f"Source enrollment is {source.status.value.replace('_', ' ').lower()}."
        if payload.action == ProgressionAction.CHANGE_CLASS:
            if payload.source_academic_year_id != payload.target_academic_year_id:
                return "Change Class must stay within one academic year."
            if target_class.form_level != source.form_level:
                return "Change Class must stay in the same Form."
            return None
        if payload.source_academic_year_id == payload.target_academic_year_id:
            return "Promotion and repetition require a different academic year."
        if payload.action == ProgressionAction.REPEAT:
            return None if target_class.form_level == source.form_level else "Repeat Form must keep the same Form."
        if payload.action == ProgressionAction.O_LEVEL_TO_A_LEVEL:
            return None if (
                source.form_level == FormLevel.FORM_4
                and target_class.form_level == FormLevel.LOWER_6
            ) else "O-Level transition requires Form 4 to Lower 6."
        expected = source.form_level.next_form
        if source.form_level == FormLevel.FORM_4:
            return "Use O-Level to A-Level Transition or complete the student after Form 4."
        if expected is None:
            return "Upper 6 students must be completed or marked to repeat."
        return None if target_class.form_level == expected else f"Expected progression to {expected.value.replace('_', ' ').title()}."

    def _subject_problem(self, payload, target_class):
        if payload.action != ProgressionAction.O_LEVEL_TO_A_LEVEL:
            return None
        if not payload.subject_ids:
            return "Choose the student's new A-Level subjects."
        subjects = self.db.query(Subject).filter(Subject.id.in_(payload.subject_ids)).all()
        if len(subjects) != len(set(payload.subject_ids)):
            return "One or more selected subjects do not exist."
        if any(s.level not in {SubjectLevel.A_LEVEL, SubjectLevel.BOTH} or not s.is_active for s in subjects):
            return "Every transition subject must be an active A-Level or Both-level subject."
        return None

    def _audit(
        self, student, actor_id, action, batch_id, before, after,
        from_status=None,
    ):
        self.db.add(
            EnrollmentAudit(
                student_id=student.id,
                actor_user_id=actor_id,
                action=action.value,
                batch_id=batch_id,
                from_academic_year_id=before.academic_year_id if before else None,
                to_academic_year_id=after.academic_year_id,
                from_form_level=before.form_level.value if before else None,
                to_form_level=after.form_level.value,
                from_class_name=before.class_name_snapshot if before else None,
                to_class_name=after.class_name_snapshot,
                from_status=(from_status or before.status).value if before else None,
                to_status=after.status.value,
            )
        )
