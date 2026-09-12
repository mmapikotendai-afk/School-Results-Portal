"""Student and teacher management, including enrollment and assignment."""

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import TeacherSubject
from app.models.enrollment import StudentSubject
from app.models.enums import EnrollmentStatus, UserRole
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.people import (
    StudentCreate,
    StudentUpdate,
    TeacherCreate,
    TeacherUpdate,
)
from app.services.academic_service import AcademicService, utcnow
from app.utils.security import generate_temporary_password, hash_password

# Kept as a module-level alias: password generation now lives beside hashing
# and the password policy, so the two cannot drift apart.
generate_password = generate_temporary_password


class EnrollmentSync:
    """Result of reconciling a subject selection against what is on record."""

    def __init__(self) -> None:
        self.added: List[str] = []
        self.reactivated: List[str] = []
        self.dropped: List[str] = []
        self.unchanged: int = 0

    def as_dict(self) -> Dict:
        return {
            "added": self.added,
            "reactivated": self.reactivated,
            "dropped": self.dropped,
            "unchanged": self.unchanged,
        }


class StudentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.academic = AcademicService(db)

    # ------------------------------------------------------- querying

    def _base_query(self):
        return self.db.query(Student).options(
            joinedload(Student.user), joinedload(Student.school_class)
        )

    def search(
        self,
        search: Optional[str] = None,
        class_id: Optional[int] = None,
        include_inactive: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[List[Student], int]:
        """Paginated student list. Returns (rows, total_before_paging)."""
        query = self._base_query().join(User, Student.user_id == User.id)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Student.student_number.like(term.upper()),
                    Student.first_name.like(term),
                    Student.last_name.like(term),
                    User.email.like(term),
                )
            )
        if class_id:
            query = query.filter(Student.class_id == class_id)
        if not include_inactive:
            query = query.filter(User.is_active.is_(True))

        total = query.with_entities(func.count(Student.id)).scalar() or 0

        rows = (
            query.order_by(Student.last_name, Student.first_name)
            .offset(max(0, (page - 1)) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def get(self, student_id: int) -> Optional[Student]:
        return self._base_query().filter(Student.id == student_id).first()

    def get_by_number(self, student_number: str) -> Optional[Student]:
        return (
            self._base_query()
            .filter(Student.student_number == student_number.strip().upper())
            .first()
        )

    # ------------------------------------------------------- creating

    def create(
        self, payload: StudentCreate
    ) -> Tuple[Optional[Student], Optional[str], Optional[str]]:
        """Create a student and their portal account.

        Returns (student, temporary_password, error). The password is returned
        to the caller in memory so it can be emailed; it is stored only as a
        bcrypt hash and must not be placed in an API response.
        """
        if self.get_by_number(payload.student_number):
            return None, None, f"Student number {payload.student_number} is already in use."

        if payload.class_id and not self.db.query(SchoolClass.id).filter(
            SchoolClass.id == payload.class_id
        ).first():
            return None, None, "That class does not exist."

        # Required by the schema, so there is no derived-address fallback here
        # any more: every new student has a real mailbox to be emailed at.
        email = str(payload.email).strip().lower()
        if self.db.query(User.id).filter(User.email == email).first():
            return None, None, f"An account already exists for {email}."

        # The student number doubles as the username, so a learner can sign in
        # with the identifier already printed on their record.
        username = payload.student_number.lower()
        if self.db.query(User.id).filter(User.username == username).first():
            username = None

        password = generate_temporary_password()

        user = User(
            email=email,
            username=username,
            full_name=f"{payload.first_name} {payload.last_name}",
            password_hash=hash_password(password),
            role=UserRole.STUDENT,
            is_active=True,
            must_change_password=True,
        )
        user.student = Student(
            student_number=payload.student_number,
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            class_id=payload.class_id,
        )
        self.db.add(user)
        self.db.flush()

        if payload.subject_ids:
            year_id = self.academic.resolve_year_id(payload.academic_year_id)
            if year_id:
                self.set_subjects(user.student, payload.subject_ids, year_id)

        self.db.commit()
        self.db.refresh(user.student)
        return user.student, password, None

    # ------------------------------------------------------- updating

    def update(
        self, student: Student, payload: StudentUpdate
    ) -> Tuple[Optional[Student], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)

        number = data.pop("student_number", None)
        if number and number != student.student_number:
            clash = (
                self.db.query(Student.id)
                .filter(Student.student_number == number, Student.id != student.id)
                .first()
            )
            if clash:
                return None, f"Student number {number} is already in use."
            student.student_number = number

        email = data.pop("email", None)
        if email:
            email = str(email).strip().lower()
            if email != student.user.email:
                clash = (
                    self.db.query(User.id)
                    .filter(User.email == email, User.id != student.user_id)
                    .first()
                )
                if clash:
                    return None, f"An account already exists for {email}."
                student.user.email = email

        class_id = data.get("class_id", "__unset__")
        if class_id != "__unset__" and class_id is not None:
            if not self.db.query(SchoolClass.id).filter(SchoolClass.id == class_id).first():
                return None, "That class does not exist."

        for field, value in data.items():
            setattr(student, field, value)

        # Keep the account display name in step with the record.
        student.user.full_name = f"{student.first_name} {student.last_name}"

        self.db.commit()
        self.db.refresh(student)
        return student, None

    # ----------------------------------------------------- enrollment

    def active_subject_ids(self, student_id: int, year_id: int) -> List[int]:
        return [
            row.subject_id
            for row in self.db.query(StudentSubject.subject_id).filter(
                StudentSubject.student_id == student_id,
                StudentSubject.academic_year_id == year_id,
                StudentSubject.status == EnrollmentStatus.ACTIVE,
            )
        ]

    def enrollments(self, student_id: int, year_id: int) -> List[StudentSubject]:
        return (
            self.db.query(StudentSubject)
            .options(joinedload(StudentSubject.subject))
            .filter(
                StudentSubject.student_id == student_id,
                StudentSubject.academic_year_id == year_id,
            )
            .all()
        )

    def set_subjects(
        self, student: Student, subject_ids: Sequence[int], year_id: int
    ) -> EnrollmentSync:
        """Reconcile a student subject list for one academic year.

        Dropping is never a delete: the row is marked INACTIVE and stamped with
        dropped_at, so the enrollment history and any results already recorded
        against it survive. Re-enrolling reuses that same row rather than
        creating a duplicate, which the unique key would reject anyway.
        """
        wanted = {int(s) for s in subject_ids}
        sync = EnrollmentSync()

        existing = {
            row.subject_id: row for row in self.enrollments(student.id, year_id)
        }
        names = self._subject_names(wanted | set(existing))

        for subject_id in wanted:
            row = existing.get(subject_id)
            if row is None:
                self.db.add(
                    StudentSubject(
                        student_id=student.id,
                        subject_id=subject_id,
                        academic_year_id=year_id,
                        status=EnrollmentStatus.ACTIVE,
                    )
                )
                sync.added.append(names.get(subject_id, str(subject_id)))
            elif row.status == EnrollmentStatus.INACTIVE:
                row.status = EnrollmentStatus.ACTIVE
                row.dropped_at = None
                sync.reactivated.append(names.get(subject_id, str(subject_id)))
            else:
                sync.unchanged += 1

        for subject_id, row in existing.items():
            if subject_id not in wanted and row.status == EnrollmentStatus.ACTIVE:
                row.status = EnrollmentStatus.INACTIVE
                row.dropped_at = utcnow()
                sync.dropped.append(names.get(subject_id, str(subject_id)))

        self.db.flush()
        return sync

    def _subject_names(self, subject_ids) -> Dict[int, str]:
        if not subject_ids:
            return {}
        rows = (
            self.db.query(Subject.id, Subject.name)
            .filter(Subject.id.in_(list(subject_ids)))
            .all()
        )
        return {row.id: row.name for row in rows}

    def valid_subject_ids(self, subject_ids: Sequence[int]) -> Tuple[bool, Optional[str]]:
        """Reject a selection naming a subject that does not exist or is retired."""
        if not subject_ids:
            return True, None
        found = {
            row.id
            for row in self.db.query(Subject.id).filter(
                Subject.id.in_(list(subject_ids)), Subject.is_active.is_(True)
            )
        }
        missing = set(subject_ids) - found
        if missing:
            return False, "One or more selected subjects do not exist or are inactive."
        return True, None


class TeacherService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.academic = AcademicService(db)

    def _base_query(self):
        return self.db.query(Teacher).options(joinedload(Teacher.user))

    def search(
        self,
        search: Optional[str] = None,
        include_inactive: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[List[Teacher], int]:
        query = self._base_query().join(User, Teacher.user_id == User.id)

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Teacher.employee_number.like(term.upper()),
                    Teacher.first_name.like(term),
                    Teacher.last_name.like(term),
                    User.email.like(term),
                )
            )
        if not include_inactive:
            query = query.filter(User.is_active.is_(True))

        total = query.with_entities(func.count(Teacher.id)).scalar() or 0
        rows = (
            query.order_by(Teacher.last_name, Teacher.first_name)
            .offset(max(0, (page - 1)) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def get(self, teacher_id: int) -> Optional[Teacher]:
        return self._base_query().filter(Teacher.id == teacher_id).first()

    def create(
        self, payload: TeacherCreate
    ) -> Tuple[Optional[Teacher], Optional[str], Optional[str]]:
        """Create a teacher and their portal account.

        Returns (teacher, temporary_password, error). As with students, the
        plaintext is for the email service only and never for a response body.
        """
        number = payload.employee_number
        if self.db.query(Teacher.id).filter(Teacher.employee_number == number).first():
            return None, None, f"Employee number {number} is already in use."

        email = str(payload.email).strip().lower()
        if self.db.query(User.id).filter(User.email == email).first():
            return None, None, f"An account already exists for {email}."

        password = generate_temporary_password()

        user = User(
            email=email,
            full_name=f"{payload.first_name} {payload.last_name}",
            password_hash=hash_password(password),
            role=UserRole.TEACHER,
            is_active=True,
            must_change_password=True,
        )
        user.teacher = Teacher(
            employee_number=number,
            first_name=payload.first_name,
            last_name=payload.last_name,
            department=payload.department,
            phone=payload.phone,
        )
        self.db.add(user)
        self.db.flush()

        if payload.subject_ids:
            year_id = self.academic.resolve_year_id(payload.academic_year_id)
            if year_id:
                self.set_subjects(user.teacher, payload.subject_ids, year_id)

        self.db.commit()
        self.db.refresh(user.teacher)
        return user.teacher, password, None

    def update(
        self, teacher: Teacher, payload: TeacherUpdate
    ) -> Tuple[Optional[Teacher], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)

        number = data.pop("employee_number", None)
        if number and number != teacher.employee_number:
            clash = (
                self.db.query(Teacher.id)
                .filter(Teacher.employee_number == number, Teacher.id != teacher.id)
                .first()
            )
            if clash:
                return None, f"Employee number {number} is already in use."
            teacher.employee_number = number

        email = data.pop("email", None)
        if email:
            email = str(email).strip().lower()
            if email != teacher.user.email:
                clash = (
                    self.db.query(User.id)
                    .filter(User.email == email, User.id != teacher.user_id)
                    .first()
                )
                if clash:
                    return None, f"An account already exists for {email}."
                teacher.user.email = email

        for field, value in data.items():
            setattr(teacher, field, value)

        teacher.user.full_name = f"{teacher.first_name} {teacher.last_name}"
        self.db.commit()
        self.db.refresh(teacher)
        return teacher, None

    # ----------------------------------------------------- assignment

    def assignments(self, teacher_id: int, year_id: int) -> List[TeacherSubject]:
        return (
            self.db.query(TeacherSubject)
            .options(joinedload(TeacherSubject.subject))
            .filter(
                TeacherSubject.teacher_id == teacher_id,
                TeacherSubject.academic_year_id == year_id,
            )
            .all()
        )

    def active_subject_ids(self, teacher_id: int, year_id: int) -> List[int]:
        return [
            row.subject_id
            for row in self.db.query(TeacherSubject.subject_id).filter(
                TeacherSubject.teacher_id == teacher_id,
                TeacherSubject.academic_year_id == year_id,
                TeacherSubject.is_active.is_(True),
            )
        ]

    def set_subjects(
        self, teacher: Teacher, subject_ids: Sequence[int], year_id: int
    ) -> EnrollmentSync:
        """Reconcile the subjects a teacher is responsible for in one year.

        Unassigning deactivates the row rather than deleting it, because
        result_submissions references the assignment: deleting would cascade
        and erase the record of what this teacher submitted.
        """
        wanted = {int(s) for s in subject_ids}
        sync = EnrollmentSync()

        existing = {row.subject_id: row for row in self.assignments(teacher.id, year_id)}
        names = self._subject_names(wanted | set(existing))

        for subject_id in wanted:
            row = existing.get(subject_id)
            if row is None:
                self.db.add(
                    TeacherSubject(
                        teacher_id=teacher.id,
                        subject_id=subject_id,
                        academic_year_id=year_id,
                        is_active=True,
                    )
                )
                sync.added.append(names.get(subject_id, str(subject_id)))
            elif not row.is_active:
                row.is_active = True
                sync.reactivated.append(names.get(subject_id, str(subject_id)))
            else:
                sync.unchanged += 1

        for subject_id, row in existing.items():
            if subject_id not in wanted and row.is_active:
                row.is_active = False
                sync.dropped.append(names.get(subject_id, str(subject_id)))

        self.db.flush()
        return sync

    def _subject_names(self, subject_ids) -> Dict[int, str]:
        if not subject_ids:
            return {}
        rows = (
            self.db.query(Subject.id, Subject.name)
            .filter(Subject.id.in_(list(subject_ids)))
            .all()
        )
        return {row.id: row.name for row in rows}
