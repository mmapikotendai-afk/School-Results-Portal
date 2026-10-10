"""Student and teacher management, including enrollment and assignment."""

import uuid

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import TeacherSubject
from app.models.enrollment import StudentSubject
from app.models.enums import EducationLevel, EnrollmentStatus, ProgressionAction, StudentEnrollmentStatus, SubjectLevel, UserRole
from app.models.school_class import SchoolClass
from app.models.student import Student
from app.models.student_enrollment import EnrollmentAudit, StudentEnrollment
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
from app.services.student_credentials_service import StudentCredentialsService

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

    def year_enrollment(
        self, student_id: int, academic_year_id: Optional[int] = None
    ) -> Optional[StudentEnrollment]:
        year_id = self.academic.resolve_year_id(academic_year_id)
        if not year_id:
            return None
        return (
            self.db.query(StudentEnrollment)
            .filter(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.academic_year_id == year_id,
            )
            .first()
        )

    def set_enrollment_status(
        self,
        student: Student,
        status: StudentEnrollmentStatus,
        academic_year_id: Optional[int] = None,
        actor_user_id: Optional[int] = None,
    ) -> Tuple[Optional[StudentEnrollment], Optional[str]]:
        year_id = self.academic.resolve_year_id(academic_year_id)
        if not year_id:
            return None, "Choose an academic year."
        enrollment = self.year_enrollment(student.id, year_id)
        previous_status = enrollment.status if enrollment else None
        if enrollment is None:
            school_class = self.db.get(SchoolClass, student.class_id) if student.class_id else None
            if school_class is None:
                return None, "Assign a class before creating an enrollment."
            enrollment = StudentEnrollment(
                student_id=student.id,
                academic_year_id=year_id,
                class_id=student.class_id,
                class_name_snapshot=school_class.name,
                form_level=school_class.form_level,
                academic_level=school_class.level,
                status=status,
            )
            self.db.add(enrollment)
        else:
            enrollment.status = status
            enrollment.class_id = student.class_id
        if actor_user_id is not None:
            self.db.flush()
            self.db.add(EnrollmentAudit(
                student_id=student.id,
                actor_user_id=actor_user_id,
                action=ProgressionAction.STATUS_CHANGE.value,
                batch_id=str(uuid.uuid4()),
                from_academic_year_id=year_id,
                to_academic_year_id=year_id,
                from_form_level=enrollment.form_level.value,
                to_form_level=enrollment.form_level.value,
                from_class_name=enrollment.class_name_snapshot,
                to_class_name=enrollment.class_name_snapshot,
                from_status=previous_status.value if previous_status else None,
                to_status=status.value,
            ))
        if status != StudentEnrollmentStatus.ACTIVE:
            student.user.token_version += 1
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment, None

    # ------------------------------------------------------- creating

    def create(
        self, payload: StudentCreate, commit: bool = True
    ) -> Tuple[Optional[Student], Optional[str], Optional[str]]:
        """Create a student and their portal account.

        Returns (student, temporary_password, error). The password is returned
        once for the printable slip and stored only as a bcrypt hash.
        """
        if not payload.class_id:
            return None, None, "Choose the class for this admission."
        if not self.db.query(SchoolClass.id).filter(
            SchoolClass.id == payload.class_id
        ).first():
            return None, None, "That class does not exist."

        year_id = self.academic.resolve_year_id(payload.academic_year_id)
        if not year_id:
            return None, None, "Choose an academic year for this admission."

        duplicate_person = (
            self.db.query(Student.id)
            .filter(
                func.lower(Student.first_name) == payload.first_name.casefold(),
                func.lower(Student.last_name) == payload.last_name.casefold(),
                Student.date_of_birth == payload.date_of_birth,
            )
            .first()
        )
        if duplicate_person:
            return None, None, (
                "A student with this exact name and date of birth already exists. "
                "Verify the existing record before admitting them again."
            )

        credentials = StudentCredentialsService(self.db)
        try:
            student_number = credentials.allocate_student_number(year_id)
        except ValueError as exc:
            return None, None, str(exc)

        username = student_number
        if self.db.query(User.id).filter(User.username == username).first():
            return None, None, "The generated student number is already in use. Try again."

        password = generate_temporary_password()

        user = User(
            email=None,
            username=username,
            full_name=f"{payload.first_name} {payload.last_name}",
            password_hash=hash_password(password),
            role=UserRole.STUDENT,
            is_active=True,
            must_change_password=True,
        )
        user.student = Student(
            student_number=student_number,
            admission_year=credentials.admission_year(year_id),
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            class_id=payload.class_id,
        )
        self.db.add(user)
        self.db.flush()

        self.db.add(
            StudentEnrollment(
                student_id=user.student.id,
                academic_year_id=year_id,
                class_id=payload.class_id,
                class_name_snapshot=self.db.get(SchoolClass, payload.class_id).name,
                form_level=self.db.get(SchoolClass, payload.class_id).form_level,
                academic_level=self.db.get(SchoolClass, payload.class_id).level,
                status=StudentEnrollmentStatus.ACTIVE,
            )
        )

        if payload.subject_ids:
            self.set_subjects(user.student, payload.subject_ids, year_id)

        if commit:
            self.db.commit()
            self.db.refresh(user.student)
        else:
            self.db.flush()
        return user.student, password, None

    # ------------------------------------------------------- updating

    def update(
        self, student: Student, payload: StudentUpdate
    ) -> Tuple[Optional[Student], Optional[str]]:
        data = payload.model_dump(exclude_unset=True)

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

    def valid_subject_ids(
        self, subject_ids: Sequence[int], level: Optional[EducationLevel] = None
    ) -> Tuple[bool, Optional[str]]:
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
        if level is not None:
            allowed = (
                {SubjectLevel.O_LEVEL, SubjectLevel.BOTH}
                if level == EducationLevel.O_LEVEL
                else {SubjectLevel.A_LEVEL, SubjectLevel.BOTH}
            )
            incompatible = self.db.query(Subject.id).filter(
                Subject.id.in_(list(subject_ids)), ~Subject.level.in_(allowed)
            ).first()
            if incompatible:
                return False, f"One or more subjects are not offered at {level.value.replace('_', '-')}."
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
        plaintext is returned once to an authorised administrator for a
        short-lived printable credential slip and is never persisted.
        """
        number = payload.employee_number
        if self.db.query(Teacher.id).filter(Teacher.employee_number == number).first():
            return None, None, f"Employee number {number} is already in use."

        username = number.lower()
        if self.db.query(User.id).filter(User.username == username).first():
            return None, None, f"Employee number {number} is already in use as a sign-in name."

        password = generate_temporary_password()

        user = User(
            email=None,
            username=username,
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
            username_clash = (
                self.db.query(User.id)
                .filter(User.username == number.lower(), User.id != teacher.user_id)
                .first()
            )
            if username_clash:
                return None, f"Employee number {number} is already in use as a sign-in name."
            teacher.employee_number = number
            teacher.user.username = number.lower()

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
