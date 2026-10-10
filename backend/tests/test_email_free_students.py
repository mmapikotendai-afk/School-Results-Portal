"""Acceptance coverage for email-free student admissions and access."""

import io

from app import models
from app.config import settings
from app.dependencies.auth import require_admin
from app.models.enums import StudentEnrollmentStatus, UserRole
from app.utils.security import hash_password, verify_password


ADMIN_PASSWORD = "AdminReview!234"


def setup_admissions(db):
    year = models.AcademicYear(name="2026", is_active=True)
    classroom = models.SchoolClass(name="Form 1A", level=models.EducationLevel.O_LEVEL,
                                   form_level=models.FormLevel.FORM_1)
    subject = models.Subject(name="English", code="ENG")
    admin = models.User(
        email="admin@example.com",
        username="admin",
        full_name="School Admin",
        password_hash=hash_password(ADMIN_PASSWORD),
        role=UserRole.ADMIN,
    )
    db.add_all([year, classroom, subject, admin])
    db.commit()
    return year, classroom, subject, admin


def authorise_admin(client, admin):
    client.app.dependency_overrides[require_admin] = lambda: admin


def test_student_creation_without_email_and_one_time_credentials(client, db):
    year, classroom, subject, admin = setup_admissions(db)
    authorise_admin(client, admin)

    response = client.post(
        "/api/v1/admin/students",
        json={
            "first_name": "Rudo",
            "last_name": "Moyo",
            "date_of_birth": "2012-04-18",
            "gender": "FEMALE",
            "class_id": classroom.id,
            "academic_year_id": year.id,
            "subject_ids": [subject.id],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "email" not in body
    assert body["student_number"] == "PHS26001"
    password = body["credential"]["temporary_password"]

    student = db.query(models.Student).filter_by(student_number="PHS26001").one()
    assert student.user.username == "PHS26001"
    assert student.user.email is None
    assert verify_password(password, student.user.password_hash)
    assert student.user.must_change_password
    enrollment = db.query(models.StudentEnrollment).filter_by(student_id=student.id).one()
    assert enrollment.status == StudentEnrollmentStatus.ACTIVE
    audit = db.query(models.CredentialAudit).filter_by(student_id=student.id).one()
    assert password not in repr(vars(audit))

    batch_id = body["credential"]["batch_id"]
    assert client.post(f"/api/v1/admin/students/credential-batches/{batch_id}/consume").status_code == 200
    assert client.post(f"/api/v1/admin/students/credential-batches/{batch_id}/consume").status_code == 410


def test_student_number_login_first_change_and_inactive_recheck(client, db):
    year, classroom, _subject, _admin = setup_admissions(db)
    temporary = "Temporary!234"
    user = models.User(
        email=None,
        username="phs26002",
        full_name="Tari Moyo",
        password_hash=hash_password(temporary),
        role=UserRole.STUDENT,
        must_change_password=True,
    )
    student = models.Student(
        user=user,
        student_number="PHS26002",
        admission_year=2026,
        first_name="Tari",
        last_name="Moyo",
        class_id=classroom.id,
    )
    db.add(student)
    db.flush()
    enrollment = models.StudentEnrollment(
        student_id=student.id,
        academic_year_id=year.id,
        class_id=classroom.id,
        class_name_snapshot=classroom.name,
        form_level=classroom.form_level,
        academic_level=classroom.level,
        status=StudentEnrollmentStatus.ACTIVE,
    )
    db.add(enrollment)
    db.commit()

    login = client.post("/api/v1/auth/login", json={"identifier": "PHS26002", "password": temporary})
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True
    token = login.json()["access_token"]
    client.cookies.clear()
    blocked = client.get("/api/v1/student/results", headers={"Authorization": f"Bearer {token}"})
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "password_change_required"

    changed = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": temporary,
            "new_password": "PrivateStudent!789",
            "confirm_password": "PrivateStudent!789",
        },
    )
    assert changed.status_code == 200
    new_login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "phs26002", "password": "PrivateStudent!789"},
    )
    assert new_login.status_code == 200

    enrollment.status = StudentEnrollmentStatus.TRANSFERRED_OUT
    db.commit()
    denied = client.get("/api/v1/student/results")
    assert denied.status_code == 403
    assert client.post(
        "/api/v1/auth/login",
        json={"identifier": "PHS26002", "password": "PrivateStudent!789"},
    ).status_code == 403


def test_csv_import_without_email_generates_numbers_and_requires_reauth(client, db):
    year, classroom, subject, admin = setup_admissions(db)
    authorise_admin(client, admin)
    csv_bytes = (
        b"first_name,last_name,date_of_birth,gender\n"
        b"Tendai,Mapiko,2012-05-14,Male\n"
        b"Rudo,Chikore,2012-02-11,Female\n"
    )
    target = {
        "class_id": str(classroom.id),
        "academic_year_id": str(year.id),
        "subject_ids": str(subject.id),
    }
    preview = client.post(
        "/api/v1/admin/students/import/preview",
        data=target,
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["can_import"] is True
    assert db.query(models.Student).count() == 0

    refused = client.post(
        "/api/v1/admin/students/import",
        data={**target, "admin_password": "wrong"},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert refused.status_code == 403
    assert db.query(models.Student).count() == 0

    imported = client.post(
        "/api/v1/admin/students/import",
        data={**target, "admin_password": ADMIN_PASSWORD},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert body["students_created"] == 2
    assert body["credentials_issued"] == 2
    assert [row[0] for row in db.query(models.Student.student_number).order_by(models.Student.id)] == [
        "PHS26001",
        "PHS26002",
    ]


def test_student_admissions_reject_email_fields_and_csv_columns(client, db):
    year, classroom, _subject, admin = setup_admissions(db)
    authorise_admin(client, admin)
    response = client.post(
        "/api/v1/admin/students",
        json={
            "first_name": "Email",
            "last_name": "Removed",
            "date_of_birth": "2012-01-01",
            "gender": "FEMALE",
            "class_id": classroom.id,
            "academic_year_id": year.id,
            "email": "student@example.com",
        },
    )
    assert response.status_code == 422

    csv_bytes = (
        b"first_name,last_name,date_of_birth,gender,email\n"
        b"Email,Removed,2012-01-01,Female,student@example.com\n"
    )
    preview = client.post(
        "/api/v1/admin/students/import/preview",
        data={"class_id": str(classroom.id), "academic_year_id": str(year.id)},
        files={"file": ("students.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert preview.status_code == 200
    assert preview.json()["can_import"] is False
    assert "Remove the email column" in preview.json()["detail"]


def test_database_rejects_duplicate_student_number(db):
    from sqlalchemy.exc import IntegrityError

    one = models.User(email=None, username="one", full_name="One", password_hash="x", role=UserRole.STUDENT)
    two = models.User(email=None, username="two", full_name="Two", password_hash="x", role=UserRole.STUDENT)
    db.add_all([
        models.Student(user=one, student_number="PHS26099", admission_year=2026, first_name="One", last_name="Student"),
        models.Student(user=two, student_number="PHS26099", admission_year=2026, first_name="Two", last_name="Student"),
    ])
    try:
        db.commit()
        assert False, "duplicate student number was accepted"
    except IntegrityError:
        db.rollback()


def test_teacher_creation_and_reset_use_employee_number_without_email(client, db):
    year, _classroom, subject, admin = setup_admissions(db)
    authorise_admin(client, admin)
    created = client.post(
        "/api/v1/admin/teachers",
        json={
            "employee_number": "T-100",
            "first_name": "Tapiwa",
            "last_name": "Dube",
            "subject_ids": [subject.id],
            "academic_year_id": year.id,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert "email" not in body
    credential = body["credential"]
    assert credential["employee_number"] == "T-100"
    assert credential["temporary_password"]
    teacher = db.query(models.Teacher).filter_by(employee_number="T-100").one()
    assert teacher.user.email is None
    assert teacher.user.username == "t-100"

    login = client.post("/api/v1/auth/login", json={
        "identifier": "T-100", "password": credential["temporary_password"],
    })
    assert login.status_code == 200
    client.cookies.clear()

    reset = client.post(
        f"/api/v1/admin/teachers/{teacher.id}/reset-credentials",
        json={"admin_password": ADMIN_PASSWORD},
    )
    assert reset.status_code == 200, reset.text
    assert reset.json()["employee_number"] == "T-100"
    consumed = client.post(
        f"/api/v1/admin/teachers/credential-batches/{reset.json()['batch_id']}/consume"
    )
    assert consumed.status_code == 200
