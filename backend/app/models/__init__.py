"""ORM models.

Importing this package registers every model on the shared metadata, which is
what init_db() and any future migration tooling rely on. Import order matters
only in that every module must be imported before mapper configuration runs.

Tables
------
users                 accounts and roles
students              learner profiles, keyed by student_number
teachers              staff profiles, keyed by employee_number
subjects              subject catalogue, tagged O-Level / A-Level / both
classes               forms and streams, for example 1C or Lower 6 Sciences
academic_years        school years
terms                 terms within a year
examinations          sittings, deadlines and publication status
grade_bands           the school's configurable grading scale
student_subjects      subject enrollment per student per year
teacher_subjects      subject responsibility per teacher per year
results               one mark per student, subject and examination
result_audit_logs     immutable trail of corrections to results
result_submissions    submission tracking per examination and assignment
revoked_tokens        access tokens invalidated by signing out
school_settings       school identity for branded report cards
"""

from app.models.academic_year import AcademicYear, Term
from app.models.assignment import TeacherSubject
from app.models.enrollment import StudentSubject
from app.models.enums import (
    EducationLevel,
    EnrollmentStatus,
    ExaminationStatus,
    Gender,
    SubjectLevel,
    SubmissionStatus,
    UserRole,
)
from app.models.examination import Examination
from app.models.grade_band import GradeBand
from app.models.result import Result, ResultAuditLog
from app.models.revoked_token import RevokedToken
from app.models.school_class import SchoolClass
from app.models.school_settings import SchoolSettings
from app.models.student import Student
from app.models.subject import Subject
from app.models.submission import ResultSubmission
from app.models.teacher import Teacher
from app.models.user import User

__all__ = [
    "AcademicYear",
    "EducationLevel",
    "EnrollmentStatus",
    "Examination",
    "GradeBand",
    "ExaminationStatus",
    "Gender",
    "Result",
    "ResultAuditLog",
    "ResultSubmission",
    "RevokedToken",
    "SchoolClass",
    "SchoolSettings",
    "Student",
    "StudentSubject",
    "Subject",
    "SubjectLevel",
    "SubmissionStatus",
    "Teacher",
    "TeacherSubject",
    "Term",
    "User",
    "UserRole",
]
