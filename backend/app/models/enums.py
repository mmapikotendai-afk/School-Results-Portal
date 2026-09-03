"""Enumerations shared by the ORM models and the Pydantic schemas.

Stored as native MySQL ENUM columns. SQLAlchemy persists the enum *name*
(for example "O_LEVEL"), which is what the API and CSV files exchange.
"""

import enum


class UserRole(str, enum.Enum):
    """The only three roles in the portal. There is no parent or public role."""

    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class EducationLevel(str, enum.Enum):
    """Secondary school level.

    O_LEVEL covers Forms 1-4, A_LEVEL covers Lower 6 and Upper 6. Grading
    bands, subject catalogues and report card layouts differ between the two,
    so the level is recorded on both classes and subjects.
    """

    O_LEVEL = "O_LEVEL"
    A_LEVEL = "A_LEVEL"


class SubjectLevel(str, enum.Enum):
    """Which level a subject belongs to.

    BOTH covers subjects offered at each level under the same code, so a
    school does not have to duplicate the catalogue entry.
    """

    O_LEVEL = "O_LEVEL"
    A_LEVEL = "A_LEVEL"
    BOTH = "BOTH"


class ExaminationStatus(str, enum.Enum):
    """Lifecycle of an examination sitting.

    DRAFT                 being set up, invisible to teachers
    SUBMISSION_OPEN       teachers may upload results
    SUBMISSION_COMPLETE   every responsible teacher has submitted
    UNDER_REVIEW          administrators are checking and correcting
    PUBLISHED             released, students may view their report cards
    """

    DRAFT = "DRAFT"
    SUBMISSION_OPEN = "SUBMISSION_OPEN"
    SUBMISSION_COMPLETE = "SUBMISSION_COMPLETE"
    UNDER_REVIEW = "UNDER_REVIEW"
    PUBLISHED = "PUBLISHED"


class EnrollmentStatus(str, enum.Enum):
    """Whether a student is currently studying a subject.

    Dropping a subject sets INACTIVE and stamps dropped_at. The row is never
    deleted, so historical enrollment and the results attached to it survive.
    """

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class SubmissionStatus(str, enum.Enum):
    """State of one teacher-and-subject result submission for an examination.

    PENDING    nothing uploaded yet, deadline still ahead
    PARTIAL    some marks uploaded, but not for every enrolled student
    OVERDUE    still incomplete after the deadline passed
    SUBMITTED  complete, on or before the deadline
    LATE       complete, but only after the deadline had passed

    Derived rather than declared: the status is recomputed from the enrolment
    roll and the results actually on record, so it cannot drift out of step
    with them. See app/services/submission_service.py.
    """

    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    OVERDUE = "OVERDUE"
    SUBMITTED = "SUBMITTED"
    LATE = "LATE"
