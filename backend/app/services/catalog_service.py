"""Subject and class catalogue management.

Nothing here is seeded or hard-coded: every subject and every class name is
created by an administrator at runtime.
"""

from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.enrollment import StudentSubject
from app.models.result import Result
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.subject import Subject
from app.schemas.catalog import ClassCreate, ClassUpdate, SubjectCreate, SubjectUpdate


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --------------------------------------------------------- subjects

    def list_subjects(
        self, search: Optional[str] = None, include_inactive: bool = True
    ) -> List[Subject]:
        query = self.db.query(Subject)
        if not include_inactive:
            query = query.filter(Subject.is_active.is_(True))
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(or_(Subject.name.like(term), Subject.code.like(term)))
        return query.order_by(Subject.name).all()

    def get_subject(self, subject_id: int) -> Optional[Subject]:
        return self.db.query(Subject).filter(Subject.id == subject_id).first()

    def create_subject(self, payload: SubjectCreate) -> Tuple[Optional[Subject], Optional[str]]:
        if self.db.query(Subject.id).filter(Subject.code == payload.code).first():
            return None, f"A subject with code {payload.code} already exists."

        subject = Subject(name=payload.name, code=payload.code, level=payload.level)
        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        return subject, None

    def update_subject(
        self, subject: Subject, payload: SubjectUpdate
    ) -> Tuple[Optional[Subject], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)

        code = data.get("code")
        if code and code != subject.code:
            clash = (
                self.db.query(Subject.id)
                .filter(Subject.code == code, Subject.id != subject.id)
                .first()
            )
            if clash:
                return None, f"A subject with code {code} already exists."

        for field, value in data.items():
            setattr(subject, field, value)

        self.db.commit()
        self.db.refresh(subject)
        return subject, None

    def set_subject_active(self, subject: Subject, is_active: bool) -> Subject:
        """Deactivate rather than delete.

        A subject that has ever been examined is referenced by results and by
        enrollment history, so removing it would take those with it.
        """
        subject.is_active = is_active
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def subject_usage(self, subject_id: int) -> dict:
        """How much history a subject carries, shown before deactivating it."""
        return {
            "enrollments": self.db.query(func.count(StudentSubject.id))
            .filter(StudentSubject.subject_id == subject_id)
            .scalar()
            or 0,
            "results": self.db.query(func.count(Result.id))
            .filter(Result.subject_id == subject_id)
            .scalar()
            or 0,
        }

    # ---------------------------------------------------------- classes

    def list_classes(self, include_inactive: bool = True) -> List[Tuple[SchoolClass, int]]:
        """Classes with their roll size, ordered by level then name."""
        query = (
            self.db.query(SchoolClass, func.count(Student.id))
            .outerjoin(Student, Student.class_id == SchoolClass.id)
            .group_by(SchoolClass.id)
        )
        if not include_inactive:
            query = query.filter(SchoolClass.is_active.is_(True))
        return query.order_by(SchoolClass.level, SchoolClass.name).all()

    def get_class(self, class_id: int) -> Optional[SchoolClass]:
        return self.db.query(SchoolClass).filter(SchoolClass.id == class_id).first()

    def create_class(self, payload: ClassCreate) -> Tuple[Optional[SchoolClass], Optional[str]]:
        if self.db.query(SchoolClass.id).filter(SchoolClass.name == payload.name).first():
            return None, f"A class named {payload.name} already exists."

        school_class = SchoolClass(name=payload.name, level=payload.level)
        self.db.add(school_class)
        self.db.commit()
        self.db.refresh(school_class)
        return school_class, None

    def update_class(
        self, school_class: SchoolClass, payload: ClassUpdate
    ) -> Tuple[Optional[SchoolClass], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)

        name = data.get("name")
        if name and name != school_class.name:
            clash = (
                self.db.query(SchoolClass.id)
                .filter(SchoolClass.name == name, SchoolClass.id != school_class.id)
                .first()
            )
            if clash:
                return None, f"A class named {name} already exists."

        for field, value in data.items():
            setattr(school_class, field, value)

        self.db.commit()
        self.db.refresh(school_class)
        return school_class, None

    def class_student_count(self, class_id: int) -> int:
        return (
            self.db.query(func.count(Student.id))
            .filter(Student.class_id == class_id)
            .scalar()
            or 0
        )
