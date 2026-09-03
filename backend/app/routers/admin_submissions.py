"""Submission monitoring, and the administrator's backup upload.

Overdue is never something an administrator marks by hand. Status is derived
from the enrolment roll, the marks on record and the deadline, every time it
is read, so a submission becomes overdue the moment the deadline passes
whether or not anybody is looking.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.assignment import TeacherSubject
from app.models.enums import SubmissionStatus
from app.models.examination import Examination
from app.models.result import Result
from app.models.submission import ResultSubmission
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.monitoring import (
    MissingStudent,
    MonitorRow,
    SubmissionDetail,
    SubmissionMonitor,
)
from app.schemas.teacher_view import UploadReport
from app.services.academic_service import AcademicService, utcnow
from app.services.result_import_service import ResultImportService
from app.services.submission_service import SubmissionService
from app.services.teacher_portal_service import TeacherPortalService

router = APIRouter(
    prefix="/admin",
    tags=["Administration - Submissions"],
    dependencies=[Depends(require_admin)],
)


def _exam(db: Session, exam_id: int) -> Examination:
    found = AcademicService(db).get_examination(exam_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Examination not found."
        )
    return found


def _row(submission: ResultSubmission, deadline) -> MonitorRow:
    teacher = submission.teacher
    uploader_id = submission.submitted_by_id
    # The responsible teacher and the person who uploaded are different fields
    # precisely so this comparison is possible.
    on_behalf = bool(
        uploader_id and teacher and teacher.user_id and uploader_id != teacher.user_id
    )

    return MonitorRow(
        submission_id=submission.id,
        teacher_id=submission.teacher_id,
        teacher_name=teacher.full_name if teacher else "",
        employee_number=teacher.employee_number if teacher else "",
        teacher_email=teacher.user.email if teacher and teacher.user else None,
        teacher_phone=teacher.phone if teacher else None,
        subject_id=submission.subject_id,
        subject_name=submission.subject.name if submission.subject else "",
        subject_code=submission.subject.code if submission.subject else "",
        deadline=deadline,
        status=submission.status,
        submitted_at=submission.submitted_at,
        last_upload_at=submission.updated_at,
        uploaded_by=submission.submitted_by.full_name if submission.submitted_by else None,
        uploaded_by_id=uploader_id,
        uploaded_on_behalf=on_behalf,
        notes=submission.notes,
        expected_count=submission.expected_count,
        submitted_count=submission.submitted_count,
        is_overdue=submission.status == SubmissionStatus.OVERDUE,
    )


@router.get(
    "/examinations/{exam_id}/monitor",
    response_model=SubmissionMonitor,
    summary="Results submission monitor",
)
def monitor(exam_id: int, db: Session = Depends(get_db)) -> SubmissionMonitor:
    """Who owes results for this examination, and who has delivered.

    Statuses are recomputed on read from the roll, the marks and the clock, so
    nothing here needs an administrator to mark a teacher overdue.
    """
    exam = _exam(db, exam_id)
    rows = SubmissionService(db).recalculate(exam)

    deadline = exam.submission_deadline
    monitor_rows = sorted(
        (_row(r, deadline) for r in rows),
        # Worst first: the point of the screen is who needs chasing.
        key=lambda r: (
            {
                SubmissionStatus.OVERDUE: 0,
                SubmissionStatus.PARTIAL: 1,
                SubmissionStatus.PENDING: 2,
                SubmissionStatus.LATE: 3,
                SubmissionStatus.SUBMITTED: 4,
            }.get(r.status, 9),
            r.teacher_name,
        ),
    )

    done = sum(
        1 for r in monitor_rows if r.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.LATE)
    )
    overdue = sum(1 for r in monitor_rows if r.status == SubmissionStatus.OVERDUE)

    return SubmissionMonitor(
        examination_id=exam.id,
        examination_name=exam.name,
        term_name=exam.term.name if exam.term else None,
        academic_year_name=(
            exam.term.academic_year.name if exam.term and exam.term.academic_year else None
        ),
        examination_status=exam.status,
        deadline=deadline,
        is_past_deadline=bool(deadline and utcnow() > deadline),
        rows=monitor_rows,
        total_subjects=len(monitor_rows),
        submitted_subjects=done,
        pending_subjects=len(monitor_rows) - done,
        overdue_subjects=overdue,
        progress=round(done / len(monitor_rows) * 100) if monitor_rows else 0,
        uploaded_on_behalf_count=sum(1 for r in monitor_rows if r.uploaded_on_behalf),
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionDetail,
    summary="Open a submission and see who is responsible",
)
def submission_detail(submission_id: int, db: Session = Depends(get_db)) -> SubmissionDetail:
    """One submission in full: the responsible teacher, and who is unmarked.

    Opening a pending or overdue line should answer "who do I chase, and what
    exactly is missing", so it carries the teacher's contact details and the
    students still without a mark.
    """
    submission = (
        db.query(ResultSubmission)
        .options(
            joinedload(ResultSubmission.teacher).joinedload(Teacher.user),
            joinedload(ResultSubmission.subject),
            joinedload(ResultSubmission.submitted_by),
        )
        .filter(ResultSubmission.id == submission_id)
        .first()
    )
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found."
        )

    exam = _exam(db, submission.examination_id)
    SubmissionService(db).recalculate(exam)
    db.refresh(submission)

    portal = TeacherPortalService(db)
    enrolled = portal.enrolled_students(
        submission.subject_id, exam.term.academic_year_id
    )
    marked = {
        r.student_id
        for r in db.query(Result.student_id).filter(
            Result.examination_id == exam.id, Result.subject_id == submission.subject_id
        )
    }

    can_write, blocked = portal.writability(exam)
    base = _row(submission, exam.submission_deadline)

    return SubmissionDetail(
        **base.model_dump(),
        examination_id=exam.id,
        examination_name=exam.name,
        missing_students=[
            MissingStudent(
                student_id=s.id,
                student_number=s.student_number,
                student_name=s.full_name,
                class_name=s.school_class.name if s.school_class else None,
            )
            for s in enrolled
            if s.id not in marked
        ],
        can_upload_on_behalf=can_write,
        blocked_reason=blocked,
    )


@router.post(
    "/examinations/{exam_id}/subjects/{subject_id}/upload-on-behalf",
    response_model=UploadReport,
    summary="Upload results on behalf of a teacher",
)
async def upload_on_behalf(
    exam_id: int,
    subject_id: int,
    teacher_id: int = Query(..., description="The teacher who remains responsible"),
    validate_only: bool = Query(default=False),
    allow_replace: bool = Query(default=False),
    reason: str = Form(..., min_length=3, max_length=255),
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UploadReport:
    """A backup route for when a teacher cannot upload themselves.

    The responsible teacher is unchanged: they stay the owner of the subject on
    the monitor and in every submission record. What changes is only who
    performed the upload, which is recorded separately, along with the reason,
    so the distinction is visible afterwards rather than inferred.

    A reason is required. An administrator writing into somebody else's subject
    without saying why is exactly the thing an audit trail exists to prevent.
    """
    exam = _exam(db, exam_id)

    teacher = (
        db.query(Teacher)
        .options(joinedload(Teacher.user))
        .filter(Teacher.id == teacher_id)
        .first()
    )
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found.")

    # The teacher must genuinely be responsible for this subject: an
    # administrator may stand in for them, not invent the assignment.
    assignment = (
        db.query(TeacherSubject)
        .filter(
            TeacherSubject.teacher_id == teacher_id,
            TeacherSubject.subject_id == subject_id,
            TeacherSubject.academic_year_id == exam.term.academic_year_id,
            TeacherSubject.is_active.is_(True),
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{teacher.full_name} is not assigned to that subject for this "
                "examination, so results cannot be uploaded on their behalf."
            ),
        )

    portal = TeacherPortalService(db)
    can_write, blocked = portal.writability(exam)
    if not can_write:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=blocked)

    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a CSV file."
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty.")

    subject = assignment.subject
    stamped_reason = (
        f"Uploaded by {admin.full_name} (administrator) on behalf of "
        f"{teacher.full_name} on {utcnow():%d %b %Y at %H:%M}: {reason.strip()}"
    )

    # teacher stays the responsible party; admin is recorded as the uploader.
    report = ResultImportService(db).process(
        raw,
        teacher,
        admin,
        exam,
        subject,
        validate_only=validate_only,
        allow_replace=allow_replace,
        reason=stamped_reason,
    )

    if report.committed:
        tracking = portal.tracking_row(exam, teacher, subject_id)
        if tracking:
            tracking.notes = stamped_reason[:255]
            db.commit()
        report.detail = (
            f"{report.detail} Recorded as uploaded by {admin.full_name} on behalf of "
            f"{teacher.full_name}, who remains responsible for {subject.name}."
        )

    return report


@router.get(
    "/examinations/{exam_id}/subjects/{subject_id}/responsible-teachers",
    response_model=List[dict],
    summary="Who is responsible for a subject",
)
def responsible_teachers(
    exam_id: int, subject_id: int, db: Session = Depends(get_db)
) -> List[dict]:
    """The teachers an administrator may upload on behalf of for this subject."""
    exam = _exam(db, exam_id)
    rows = (
        db.query(TeacherSubject)
        .options(joinedload(TeacherSubject.teacher).joinedload(Teacher.user))
        .filter(
            TeacherSubject.subject_id == subject_id,
            TeacherSubject.academic_year_id == exam.term.academic_year_id,
            TeacherSubject.is_active.is_(True),
        )
        .all()
    )
    return [
        {
            "teacher_id": r.teacher_id,
            "teacher_name": r.teacher.full_name,
            "employee_number": r.teacher.employee_number,
            "email": r.teacher.user.email if r.teacher.user else None,
        }
        for r in rows
    ]
