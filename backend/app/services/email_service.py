"""Transactional email delivery.

The provider lives behind a small backend interface, so swapping SendGrid for
Mailgun, Postmark, SES or a school's own relay is a change to `.env` rather
than a change to the application. Nothing outside this module knows how a
message is actually sent.

    send_account_credentials(db_user, temporary_password) -> DeliveryResult

Two backends ship:

  smtp   any transactional provider, since they all speak SMTP. Configured
         with EMAIL_HOST / EMAIL_PORT / EMAIL_USERNAME / EMAIL_PASSWORD.
  file   writes the rendered message to EMAIL_OUTBOX_DIR instead of sending.
         Development only, and refused outright when ENVIRONMENT is production.

On the handling of the password itself: it arrives as an argument, is rendered
into the message body, and is handed to the provider. It is never written to a
log line, never persisted, and never returned to the caller. The one place it
touches disk is the `file` backend, which exists precisely so a developer can
read it - and which cannot run in production.
"""

from __future__ import annotations

import logging
import re
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Optional, Tuple

from app.config import settings
from app.models.enums import EmailDeliveryStatus, UserRole
from app.models.user import User
from app.services.email_templates import render_credentials_email

logger = logging.getLogger(__name__)

# Provider errors get stored so an administrator can act on them, and the
# column is 255 characters. Anything longer is truncated on the way in.
MAX_ERROR_LENGTH = 240


def verify_deliverable(email: str) -> Optional[str]:
    """Return why this address cannot receive mail, or None if it can.

    Credentials are delivered by email and the plaintext is discarded, so an
    account created against an address that cannot receive mail is an account
    nobody can ever sign in to. This is the cheap check that runs *before*
    anything is written.

    What it establishes: the address parses, and its domain publishes a mail
    exchanger. That catches the common failure by a wide margin - a mistyped
    domain (gmial.com, nosuchschool.zw), which is what an administrator
    typing from a paper form actually gets wrong.

    What it cannot establish: whether a particular mailbox exists. No
    synchronous check can. A receiving server accepts the message and only
    reports an unknown recipient in a bounce, minutes later, long after this
    request has returned. Catching that requires a bounce webhook.

    A DNS failure is not treated as an undeliverable address. If the lookup
    itself cannot be performed - no network, resolver timeout - the address is
    allowed through and a warning is logged, because refusing to enrol
    students for the duration of a DNS outage is worse than the risk of one
    bad address slipping past.
    """
    if not settings.EMAIL_REQUIRE_DELIVERABLE:
        return None

    try:
        from email_validator import EmailNotValidError, validate_email
    except ImportError:  # pragma: no cover - dependency is declared
        logger.warning("email_validator is unavailable; skipping the deliverability check.")
        return None

    try:
        validate_email(email, check_deliverability=True)
        return None
    except EmailNotValidError as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001 - resolver failures must not block enrolment
        logger.warning("Could not verify deliverability of %s: %s", email, exc)
        return None


@dataclass
class DeliveryResult:
    """What happened when we tried to send. Never carries the password."""

    status: EmailDeliveryStatus
    detail: str
    error: Optional[str] = None

    @property
    def sent(self) -> bool:
        return self.status == EmailDeliveryStatus.SENT


class EmailError(Exception):
    """A provider refused the message or could not be reached."""


# --------------------------------------------------------------- backends


class EmailBackend:
    """What a provider has to be able to do."""

    def send(self, message: EmailMessage) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class SMTPBackend(EmailBackend):
    """Delivery over SMTP, which every transactional provider offers."""

    def send(self, message: EmailMessage) -> None:
        host = settings.EMAIL_HOST
        port = settings.EMAIL_PORT
        timeout = settings.EMAIL_TIMEOUT

        try:
            if settings.EMAIL_USE_SSL:
                # Implicit TLS, normally port 465.
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as smtp:
                    self._authenticate_and_send(smtp, message)
            else:
                with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                    smtp.ehlo()
                    if settings.EMAIL_USE_TLS:
                        # STARTTLS, normally port 587.
                        smtp.starttls(context=ssl.create_default_context())
                        smtp.ehlo()
                    self._authenticate_and_send(smtp, message)
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailError(
                "The mail provider rejected the credentials in EMAIL_USERNAME / "
                f"EMAIL_PASSWORD ({exc.smtp_code})."
            ) from None
        except smtplib.SMTPRecipientsRefused:
            # Deliberately not echoing the address back into the error string.
            raise EmailError("The mail provider refused the recipient address.") from None
        except smtplib.SMTPException as exc:
            raise EmailError(f"The mail provider refused the message: {exc}") from None
        except (OSError, ssl.SSLError) as exc:
            raise EmailError(
                f"Could not reach the mail server at {host}:{port}: {exc}"
            ) from None

    @staticmethod
    def _authenticate_and_send(smtp: smtplib.SMTP, message: EmailMessage) -> None:
        # An unauthenticated relay is legitimate on an internal network, so
        # credentials are only offered when they have been configured.
        if settings.EMAIL_USERNAME:
            smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
        smtp.send_message(message)


class FileBackend(EmailBackend):
    """Write the message to disk rather than sending it. Development only.

    This is the one place a temporary password is written anywhere, and it is
    the whole point: without it there is no way to complete a sign-in flow
    locally without wiring up a real mail provider. The guard below is what
    keeps that convenience out of production.
    """

    def send(self, message: EmailMessage) -> None:
        if settings.ENVIRONMENT.strip().lower() in {"production", "prod"}:
            raise EmailError(
                "EMAIL_PROVIDER=file writes credentials to disk and cannot be "
                "used in production. Configure a real provider."
            )

        outbox = Path(settings.EMAIL_OUTBOX_DIR)
        outbox.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        recipient = re.sub(r"[^A-Za-z0-9._-]+", "_", message["To"] or "unknown")
        path = outbox / f"{stamp}-{recipient}-{uuid.uuid4().hex[:6]}.eml"

        try:
            path.write_bytes(bytes(message))
        except OSError as exc:
            raise EmailError(f"Could not write to the outbox directory: {exc}") from None

        # The path is safe to log. The contents are not, and are not logged.
        logger.info("Email written to the development outbox: %s", path)


def get_backend() -> EmailBackend:
    """The configured provider."""
    return FileBackend() if settings.EMAIL_PROVIDER == "file" else SMTPBackend()


# ---------------------------------------------------------------- sending


def _build_message(
    recipient_email: str,
    recipient_name: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> EmailMessage:
    """Assemble a multipart/alternative message.

    Plain text is set first and HTML added as the alternative, which is the
    order clients expect: the last part is the preferred one.
    """
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.email_from_name, settings.email_from_address))
    message["To"] = formataddr((recipient_name, recipient_email))
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()

    # Credentials are not marketing, and should not be bulk-filtered or
    # auto-replied to by an out-of-office responder.
    message["Auto-Submitted"] = "auto-generated"
    message["X-Auto-Response-Suppress"] = "All"

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    return message


def _is_deliverable(email: str) -> bool:
    """Whether an address is a real mailbox rather than a sign-in identifier.

    A learner with no email of their own is given `<number>@<STUDENT_EMAIL_DOMAIN>`
    so they still have something to sign in with. That address routes nowhere,
    and sending to it would produce a bounce for every such student.
    """
    domain = (settings.STUDENT_EMAIL_DOMAIN or "").strip().lower()
    return bool(email) and "@" in email and not (
        domain and email.strip().lower().endswith(f"@{domain}")
    )


def _account_number_for(user: User) -> Optional[Tuple[str, str]]:
    """The identifier the holder already knows themselves by, if any."""
    if user.student is not None:
        return ("Student Number", user.student.student_number)
    if user.teacher is not None:
        return ("Employee Number", user.teacher.employee_number)
    return None


def send_account_credentials(
    user: User,
    temporary_password: str,
    reissued: bool = False,
) -> DeliveryResult:
    """Email a temporary password to the account holder.

    Returns a DeliveryResult rather than raising: a failure to deliver must not
    undo an account that was created successfully. The caller records the
    outcome on the user row and tells the administrator what to do next.

    `temporary_password` is used to render the message and is then discarded
    with the local frame. It is not logged, stored or returned.
    """
    problem = settings.email_configuration_error()
    if problem:
        return DeliveryResult(
            status=EmailDeliveryStatus.SKIPPED,
            detail=problem,
            error=problem,
        )

    if not _is_deliverable(user.email):
        return DeliveryResult(
            status=EmailDeliveryStatus.SKIPPED,
            detail=(
                f"{user.email} is a sign-in identifier, not a mailbox, so no "
                "email was sent. Give the account a real email address to "
                "deliver credentials."
            ),
        )

    account_number = _account_number_for(user)

    # Students sign in with their student number as readily as their address,
    # so the email names whichever is the more useful to them.
    identifier_label = "Login Email"
    login_identifier = user.email
    if user.role == UserRole.STUDENT and user.username:
        identifier_label = "Login Email or Username"
        login_identifier = f"{user.email}  ({user.username})"

    subject, html_body, text_body = render_credentials_email(
        school_name=settings.SCHOOL_NAME,
        recipient_name=user.full_name,
        role=user.role.value,
        login_identifier=login_identifier,
        temporary_password=temporary_password,
        login_url=f"{settings.FRONTEND_URL}/login",
        identifier_label=identifier_label,
        account_number=account_number,
        reissued=reissued,
    )

    message = _build_message(
        recipient_email=user.email,
        recipient_name=user.full_name,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    try:
        get_backend().send(message)
    except EmailError as exc:
        # The address is logged; the body and password are not.
        logger.warning("Credential email to %s failed: %s", user.email, exc)
        return DeliveryResult(
            status=EmailDeliveryStatus.FAILED,
            detail=(
                "The account was created, but the email could not be delivered."
            ),
            error=str(exc)[:MAX_ERROR_LENGTH],
        )
    except Exception as exc:  # noqa: BLE001 - delivery must never break creation
        logger.exception("Unexpected error sending credential email to %s", user.email)
        return DeliveryResult(
            status=EmailDeliveryStatus.FAILED,
            detail="The account was created, but the email could not be delivered.",
            error=f"{type(exc).__name__}: {exc}"[:MAX_ERROR_LENGTH],
        )

    logger.info("Credential email accepted for delivery to %s", user.email)
    return DeliveryResult(
        status=EmailDeliveryStatus.SENT,
        detail=f"Login credentials sent to {user.email}.",
    )


def send_test_email(recipient: str) -> DeliveryResult:
    """Prove the provider configuration end to end, with no account involved.

    Used by `python -m scripts.send_test_email`.
    """
    problem = settings.email_configuration_error()
    if problem:
        return DeliveryResult(
            status=EmailDeliveryStatus.SKIPPED, detail=problem, error=problem
        )

    message = _build_message(
        recipient_email=recipient,
        recipient_name=recipient,
        subject=f"{settings.SCHOOL_NAME} portal: email delivery test",
        html_body=(
            "<p style=\"font-family:Arial,sans-serif;font-size:15px;\">"
            "This is a test message from the School Results Portal. "
            "If you can read it, transactional email is configured correctly."
            "</p>"
        ),
        text_body=(
            "This is a test message from the School Results Portal.\n"
            "If you can read it, transactional email is configured correctly.\n"
        ),
    )

    try:
        get_backend().send(message)
    except EmailError as exc:
        return DeliveryResult(
            status=EmailDeliveryStatus.FAILED,
            detail="The test message could not be delivered.",
            error=str(exc)[:MAX_ERROR_LENGTH],
        )

    return DeliveryResult(
        status=EmailDeliveryStatus.SENT, detail=f"Test message sent to {recipient}."
    )
