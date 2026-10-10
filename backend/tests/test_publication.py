from decimal import Decimal

import pytest

from app import models
from app.services.academic_service import AcademicService
from app.services.publication_service import backfill_reports, capture_reports
from app.services.report_card_service import ReportCardService
from app.services.results_engine import ResultsEngine
from app.services.submission_service import SubmissionService


def publish(db, data):
    exam, error = AcademicService(db).set_status(
        data["exam"], models.ExaminationStatus.PUBLISHED
    )
    assert error is None
    return exam


@pytest.mark.parametrize("exclude", ["dropped", "inactive", "other_year"])
def test_stale_marks_do_not_complete_submission(db, school_data, exclude):
    data = school_data
    a, _, c = data["students"]
    subject = data["subjects"][0]
    enrollment = db.query(models.StudentSubject).filter_by(
        student_id=a.id, subject_id=subject.id
    ).one()
    if exclude == "dropped":
        enrollment.status = models.EnrollmentStatus.INACTIVE
    elif exclude == "inactive":
        a.user.is_active = False
    else:
        year = models.AcademicYear(name="2025")
        db.add(year)
        db.flush()
        enrollment.academic_year_id = year.id
    db.query(models.Result).filter_by(student_id=c.id, subject_id=subject.id).delete()
    db.commit()
    service = SubmissionService(db)
    expected = service.expected_counts(data["exam"])[subject.id]
    submitted = service.submitted_counts(data["exam"])[subject.id]
    assert (expected, submitted) == (2, 1)
    assert service.derive_status(expected, submitted, None, None) == models.SubmissionStatus.PARTIAL


def test_publication_blocked_by_missing_active_student_mark(db, school_data):
    data = school_data
    subject = data["subjects"][0]
    user = models.User(email="teacher@example.com", username="teacher", full_name="Teacher",
                       password_hash="unused", role=models.UserRole.TEACHER)
    teacher = models.Teacher(user=user, employee_number="T1", first_name="Test", last_name="Teacher")
    db.add(teacher)
    db.flush()
    assignment = models.TeacherSubject(teacher_id=teacher.id, subject_id=subject.id,
                                       academic_year_id=data["year"].id)
    db.add(assignment)
    db.flush()
    db.add(models.ResultSubmission(examination_id=data["exam"].id,
           teacher_subject_id=assignment.id, teacher_id=teacher.id, subject_id=subject.id))
    a, _, c = data["students"]
    db.query(models.StudentSubject).filter_by(student_id=a.id, subject_id=subject.id).one().status = models.EnrollmentStatus.INACTIVE
    db.query(models.Result).filter_by(student_id=c.id, subject_id=subject.id).delete()
    db.commit()
    result, error = AcademicService(db).set_status(data["exam"], models.ExaminationStatus.PUBLISHED)
    assert result is None and "missing" in error
    assert db.query(models.PublishedReport).count() == 0


def test_old_report_survives_promotion_dropped_subject_and_deactivation(db, school_data):
    data = school_data
    exam = publish(db, data)
    student = data["students"][1]
    service = ReportCardService(db)
    before = service.build(student, exam, data["school"])
    new_class = models.SchoolClass(name="Lower 6", level=models.EducationLevel.A_LEVEL,
                                   form_level=models.FormLevel.LOWER_6)
    db.add(new_class)
    student.school_class = new_class
    student.first_name = "Renamed"
    data["students"][0].user.is_active = False
    enrollment = db.query(models.StudentSubject).filter_by(
        student_id=student.id, subject_id=data["subjects"][0].id
    ).one()
    enrollment.status = models.EnrollmentStatus.INACTIVE
    data["subjects"][0].name = "Renamed subject"
    data["classroom"].name = "Renamed class"
    data["school"].report_show_position = False
    db.commit()
    after = service.build(student, exam, data["school"])
    for attr in ["student_name", "class_name", "lines", "subjects_counted", "average", "overall",
                 "position", "ranked_out_of"]:
        assert getattr(after, attr) == getattr(before, attr), attr
    assert (after.position, after.ranked_out_of) == (2, 3)
    assert len(ResultsEngine(db).for_examination(exam.id, data["classroom"].id)) == 6


def test_teacher_report_stays_scoped_after_publication(db, school_data):
    data = school_data
    exam = publish(db, data)
    card = ReportCardService(db).build(data["students"][0], exam, data["school"],
        subject_ids=[data["subjects"][0].id], include_position=False, scope_note="Scoped")
    assert len(card.lines) == 1
    assert card.lines[0].subject_code == "MATH"
    assert card.position is None and card.ranked_out_of is None


def test_audited_correction_updates_published_report_and_historical_rank(db, school_data):
    from app.routers.admin_results import edit_result
    from app.schemas.results import ResultEdit

    data = school_data
    exam = publish(db, data)
    student = data["students"][1]
    student.school_class = models.SchoolClass(name="Lower 6", level=models.EducationLevel.A_LEVEL,
                                               form_level=models.FormLevel.LOWER_6)
    admin = models.User(email="admin@example.com", full_name="Admin", password_hash="unused",
                        role=models.UserRole.ADMIN)
    db.add(admin)
    db.commit()
    result = db.query(models.Result).filter_by(student_id=student.id,
             subject_id=data["subjects"][0].id).one()
    edit_result(result.id, ResultEdit(marks=Decimal("95"), reason="Verified correction"), db, admin)
    card = ReportCardService(db).build(student, exam, data["school"])
    assert card.class_name == "Form 4"
    assert card.average == 82.5
    assert card.position == 1
    assert db.query(models.ResultAuditLog).filter_by(result_id=result.id).count() == 1


def test_scale_changes_require_explicit_recalculation(db, school_data):
    from app.services.grading_service import GradingService

    data = school_data
    exam = publish(db, data)
    student = data["students"][1]
    service = ReportCardService(db)
    before = service.build(student, exam, data["school"]).overall
    student.school_class = models.SchoolClass(name="Lower 6", level=models.EducationLevel.A_LEVEL,
                                               form_level=models.FormLevel.LOWER_6)
    db.commit()
    GradingService(db).replace_scale(models.EducationLevel.O_LEVEL, [
        {"min_marks": 0, "grade": "X", "remark": "New scale", "is_pass": True},
    ])
    assert service.build(student, exam, data["school"]).overall == before
    ResultsEngine(db).recalculate_grades(exam.id)
    assert service.build(student, exam, data["school"]).overall == "X - New scale"
    assert {r.grade for r in ResultsEngine(db).for_student(student.id, exam.id)} == {"X"}


def test_backfill_preserves_recorded_marks_from_dropped_subjects_and_is_idempotent(db, school_data):
    data = school_data
    data["exam"].status = models.ExaminationStatus.PUBLISHED
    student = data["students"][0]
    db.query(models.StudentSubject).filter_by(student_id=student.id).update(
        {"status": models.EnrollmentStatus.INACTIVE}
    )
    db.commit()
    assert backfill_reports(db) == 3
    db.commit()
    assert backfill_reports(db) == 0
    assert len(ReportCardService(db).build(student, data["exam"], data["school"]).lines) == 2


def test_publication_context_rolls_back_with_transaction(db, school_data):
    exam = school_data["exam"]
    exam.status = models.ExaminationStatus.PUBLISHED
    assert capture_reports(db, exam) == 3
    db.rollback()
    assert db.query(models.PublishedReport).count() == 0
    assert exam.status == models.ExaminationStatus.UNDER_REVIEW


def test_backfill_does_not_add_new_enrollments_to_existing_publication(db, school_data):
    data = school_data
    exam = publish(db, data)
    user = models.User(email="new@example.com", full_name="New student", password_hash="unused",
                       role=models.UserRole.STUDENT)
    student = models.Student(user=user, student_number="NEW", admission_year=2026, first_name="New", last_name="Student")
    db.add(student)
    db.flush()
    db.add(models.StudentSubject(student_id=student.id, subject_id=data["subjects"][0].id,
                                 academic_year_id=data["year"].id))
    db.commit()
    assert backfill_reports(db) == 0
    assert db.get(models.PublishedReport, (exam.id, student.id)) is None


def test_republishing_captures_new_context(db, school_data):
    exam = publish(db, school_data)
    service = AcademicService(db)
    service.set_status(exam, models.ExaminationStatus.UNDER_REVIEW)
    assert db.query(models.PublishedReport).count() == 0
    school_data["classroom"].name = "Corrected class"
    db.commit()
    publish(db, school_data)
    card = ReportCardService(db).build(school_data["students"][0], exam, school_data["school"])
    assert card.class_name == "Corrected class"
