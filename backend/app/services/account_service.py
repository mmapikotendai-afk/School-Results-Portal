"""Administrator-only account provisioning.

This is the replacement for public registration: the only way a teacher or
student account comes into existence is an administrator creating it here.
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.user import AccountCreate
from app.utils.security import hash_password


class AccountService:
    """Create, list and administer portal accounts."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_accounts(
        self, role: Optional[UserRole] = None, include_inactive: bool = True
    ) -> List[User]:
        query = self.db.query(User)
        if role is not None:
            query = query.filter(User.role == role)
        if not include_inactive:
            query = query.filter(User.is_active.is_(True))
        return query.order_by(User.full_name).all()

    def validate_new_account(self, payload: AccountCreate) -> Optional[str]:
        """Check uniqueness and role requirements before writing anything.

        Returns a readable problem, or None when the account can be created.
        """
        email = payload.email.strip().lower()

        if self.db.query(User.id).filter(User.email == email).first():
            return "An account with that email address already exists."

        if payload.username:
            taken = self.db.query(User.id).filter(User.username == payload.username).first()
            if taken:
                return "That username is already taken."

        if payload.role == UserRole.STUDENT:
            if not payload.student_number:
                return "A student number is required for a student account."
            existing = (
                self.db.query(Student.id)
                .filter(Student.student_number == payload.student_number.strip())
                .first()
            )
            if existing:
                return "That student number is already assigned."

        if payload.role == UserRole.TEACHER:
            if not payload.employee_number:
                return "An employee number is required for a teacher account."
            existing = (
                self.db.query(Teacher.id)
                .filter(Teacher.employee_number == payload.employee_number.strip())
                .first()
            )
            if existing:
                return "That employee number is already assigned."

        if payload.role in (UserRole.STUDENT, UserRole.TEACHER):
            if not payload.first_name or not payload.last_name:
                return "A first name and last name are required."

        return None

    def create_account(self, payload: AccountCreate) -> Tuple[Optional[User], Optional[str]]:
        """Create a user and, for teachers and students, their profile row.

        The account starts flagged must_change_password, so the holder replaces
        the administrator-issued password from Settings, Security.
        """
        problem = self.validate_new_account(payload)
        if problem:
            return None, problem

        user = User(
            email=payload.email.strip().lower(),
            username=payload.username,
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
            must_change_password=True,
        )

        if payload.role == UserRole.STUDENT:
            user.student = Student(
                student_number=payload.student_number.strip(),
                first_name=payload.first_name.strip(),
                last_name=payload.last_name.strip(),
                class_id=payload.class_id,
            )
        elif payload.role == UserRole.TEACHER:
            user.teacher = Teacher(
                employee_number=payload.employee_number.strip(),
                first_name=payload.first_name.strip(),
                last_name=payload.last_name.strip(),
            )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user, None

    def set_active(self, user: User, is_active: bool) -> User:
        """Activate or deactivate an account.

        Deactivating bumps the token version, so any session the account holds
        stops working straight away rather than lingering until it expires.
        """
        user.is_active = is_active
        if not is_active:
            user.token_version += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_password(self, user: User, new_password: str) -> User:
        """Issue a new password and force the holder to change it on next use."""
        user.password_hash = hash_password(new_password)
        user.must_change_password = True
        user.token_version += 1
        self.db.commit()
        self.db.refresh(user)
        return user
