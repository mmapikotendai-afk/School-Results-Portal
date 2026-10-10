"""Isolated regression tests: never connect to the configured school database."""

import os
import secrets

os.environ.update({
    "SECRET_KEY": secrets.token_urlsafe(48),
    "DATABASE_URL": "mysql+pymysql://test:test@127.0.0.1/unused_test_database",
    "ENVIRONMENT": "test",
    "DEBUG": "false",
    "EMAIL_ENABLED": "false",
    "BCRYPT_ROUNDS": "10",
})

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db, monkeypatch, tmp_path):
    from app.config import settings
    from app.database import get_db
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    from app.main import app

    # main is imported once; give its StaticFiles mount a fresh directory too.
    for route in app.routes:
        if getattr(route, "name", None) == "uploads":
            route.app.directory = str(tmp_path)
            route.app.all_directories = [str(tmp_path)]

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    monkeypatch.setattr("app.main.check_database_connection", lambda: (True, None))
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def school_data(db):
    from decimal import Decimal

    year = models.AcademicYear(name="2026")
    term = models.Term(name="Term 1", academic_year=year)
    exam = models.Examination(name="Final", term=term,
                              status=models.ExaminationStatus.UNDER_REVIEW)
    classroom = models.SchoolClass(name="Form 4", level=models.EducationLevel.O_LEVEL,
                                   form_level=models.FormLevel.FORM_4)
    subjects = [models.Subject(name="Mathematics", code="MATH"),
                models.Subject(name="English", code="ENG")]
    school = models.SchoolSettings(school_name="Test School")
    db.add_all([year, term, exam, classroom, school, *subjects])
    students = []
    for index in range(3):
        user = models.User(email=f"student{index}@example.com", username=f"student{index}",
                           full_name=f"Student {index}", password_hash="unused",
                           role=models.UserRole.STUDENT)
        student = models.Student(user=user, student_number=f"S{index}", admission_year=2026, first_name="Student",
                                 last_name=str(index), school_class=classroom)
        db.add(student)
        students.append(student)
    db.flush()
    for student, mark in zip(students, [80, 70, 60]):
        for subject in subjects:
            db.add(models.StudentSubject(student_id=student.id, subject_id=subject.id,
                                         academic_year_id=year.id))
            db.add(models.Result(student_id=student.id, subject_id=subject.id,
                                 examination_id=exam.id, marks=Decimal(mark), grade="A"))
    db.commit()
    return {"year": year, "exam": exam, "students": students, "subjects": subjects,
            "classroom": classroom, "school": school}
