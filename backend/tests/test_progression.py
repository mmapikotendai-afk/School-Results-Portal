"""Acceptance coverage for permanent numbers and annual student progression."""

from datetime import date
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.database import Base
from app.models.enums import ProgressionAction, StudentEnrollmentStatus
from app.schemas.progression import ProgressionRequest
from app.services.progression_service import ProgressionService
from app.services.student_credentials_service import StudentCredentialsService


def add_year_class(db, year_name, class_name, form, active=False):
    year = models.AcademicYear(
        name=year_name, start_date=date(int(year_name), 1, 1), is_active=active
    )
    classroom = models.SchoolClass(
        name=class_name, form_level=form, level=form.academic_level
    )
    db.add_all([year, classroom]); db.flush()
    return year, classroom


def add_student(db, year, classroom, number="PHS26001"):
    user = models.User(
        username=number, full_name="Rudo Moyo", password_hash="unused",
        role=models.UserRole.STUDENT,
    )
    student = models.Student(
        user=user, student_number=number, admission_year=2026,
        first_name="Rudo", last_name="Moyo", class_id=classroom.id,
    )
    db.add(student); db.flush()
    db.add(models.StudentEnrollment(
        student_id=student.id, academic_year_id=year.id, class_id=classroom.id,
        class_name_snapshot=classroom.name, form_level=classroom.form_level,
        academic_level=classroom.level, status=StudentEnrollmentStatus.ACTIVE,
    ))
    db.flush()
    return student


def test_number_sequences_reset_annually_and_never_reuse_reserved_value(db):
    year26, _ = add_year_class(db, "2026", "Form 1 A", models.FormLevel.FORM_1)
    year27, _ = add_year_class(db, "2027", "Form 1 B", models.FormLevel.FORM_1)
    db.commit()
    service = StudentCredentialsService(db)
    assert service.allocate_student_number(year26.id) == "PHS26001"
    # Simulate an admission that fails after reservation: 001 is still burned.
    assert service.allocate_student_number(year26.id) == "PHS26002"
    assert service.allocate_student_number(year27.id) == "PHS27001"
    for full_year in range(2028, 2032):
        year = models.AcademicYear(name=str(full_year), start_date=date(full_year, 1, 1))
        db.add(year); db.commit()
        assert service.allocate_student_number(year.id) == f"PHS{str(full_year)[-2:]}001"


def test_concurrent_number_reservations_are_unique(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'numbering.db'}",
        connect_args={"check_same_thread": False, "timeout": 10},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        year = models.AcademicYear(name="2026", start_date=date(2026, 1, 1))
        session.add(year); session.commit(); year_id = year.id

    def reserve(_):
        with Session(engine) as session:
            return StudentCredentialsService(session).allocate_student_number(year_id)

    with ThreadPoolExecutor(max_workers=12) as pool:
        numbers = list(pool.map(reserve, range(30)))
    assert len(numbers) == len(set(numbers)) == 30
    assert sorted(numbers) == [f"PHS26{value:03d}" for value in range(1, 31)]
    engine.dispose()


def test_number_sequence_reports_explicit_overflow(db):
    year, _ = add_year_class(db, "2026", "Form 1 A", models.FormLevel.FORM_1)
    db.add(models.StudentNumberSequence(year_code="26", next_value=1000)); db.commit()
    with pytest.raises(ValueError, match="sequence is full"):
        StudentCredentialsService(db).allocate_student_number(year.id)


def test_promotion_is_pending_until_return_is_confirmed_and_audited(db):
    source_year, form1 = add_year_class(db, "2026", "Form 1 A", models.FormLevel.FORM_1)
    target_year, form2 = add_year_class(db, "2027", "Form 2 A", models.FormLevel.FORM_2)
    admin = models.User(
        username="admin", email="admin@example.com", full_name="Admin",
        password_hash="unused", role=models.UserRole.ADMIN,
    )
    db.add(admin); db.flush()
    student = add_student(db, source_year, form1); db.commit()
    request = ProgressionRequest(
        student_ids=[student.id], source_academic_year_id=source_year.id,
        target_academic_year_id=target_year.id, target_class_id=form2.id,
        action=ProgressionAction.PROMOTE,
    )
    service = ProgressionService(db)
    assert service.preview(request).can_confirm
    service.apply(request, admin.id)
    target = db.query(models.StudentEnrollment).filter_by(
        student_id=student.id, academic_year_id=target_year.id
    ).one()
    assert target.status == StudentEnrollmentStatus.PENDING_RETURN
    assert student.class_id == form1.id
    service.confirm_return([student.id], target_year.id, admin.id)
    assert target.status == StudentEnrollmentStatus.ACTIVE
    assert student.class_id == form2.id
    assert db.query(models.EnrollmentAudit).filter_by(student_id=student.id).count() == 2


def test_form_four_to_lower_six_requires_explicit_transition_and_a_subject(db):
    source_year, form4 = add_year_class(db, "2026", "Form 4 A", models.FormLevel.FORM_4)
    target_year, lower6 = add_year_class(db, "2027", "Lower 6", models.FormLevel.LOWER_6)
    student = add_student(db, source_year, form4)
    subject = models.Subject(name="Mathematics", code="MATH", level=models.SubjectLevel.BOTH)
    db.add(subject); db.commit()
    service = ProgressionService(db)
    ordinary = ProgressionRequest(
        student_ids=[student.id], source_academic_year_id=source_year.id,
        target_academic_year_id=target_year.id, target_class_id=lower6.id,
        action=ProgressionAction.PROMOTE,
    )
    assert not service.preview(ordinary).can_confirm
    transition = ordinary.model_copy(update={
        "action": ProgressionAction.O_LEVEL_TO_A_LEVEL,
        "subject_ids": [subject.id],
    })
    assert service.preview(transition).can_confirm
