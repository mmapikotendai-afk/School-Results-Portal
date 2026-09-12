"""Check that email delivery is configured, without creating an account.

    python -m scripts.send_test_email you@example.com

Reports what the configuration resolves to, then attempts one send. Use it
after filling in the EMAIL_* variables in backend/.env, so a misconfiguration
surfaces here rather than when a real teacher is waiting for their password.

Nothing is printed that would be unsafe in a terminal transcript: the SMTP
password is shown only as whether it is set.
"""

import sys

from app.config import settings
from app.services.email_service import send_test_email


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.send_test_email <recipient@example.com>")
        return 2

    recipient = sys.argv[1].strip()

    print("Email configuration")
    print("-------------------")
    print(f"  EMAIL_ENABLED    {settings.EMAIL_ENABLED}")
    print(f"  EMAIL_PROVIDER   {settings.EMAIL_PROVIDER}")
    if settings.EMAIL_PROVIDER == "smtp":
        print(f"  EMAIL_HOST       {settings.EMAIL_HOST or '(not set)'}")
        print(f"  EMAIL_PORT       {settings.EMAIL_PORT}")
        print(f"  EMAIL_USERNAME   {settings.EMAIL_USERNAME or '(not set)'}")
        # Never print the value itself.
        print(f"  EMAIL_PASSWORD   {'set' if settings.EMAIL_PASSWORD else '(not set)'}")
        print(f"  TLS / SSL        {settings.EMAIL_USE_TLS} / {settings.EMAIL_USE_SSL}")
    else:
        print(f"  EMAIL_OUTBOX_DIR {settings.EMAIL_OUTBOX_DIR}")
    print(f"  From             {settings.email_from_name} <{settings.email_from_address}>")
    print(f"  FRONTEND_URL     {settings.FRONTEND_URL}")
    print()

    problem = settings.email_configuration_error()
    if problem:
        print(f"Not ready to send: {problem}")
        print("\nFix backend/.env and run this again.")
        return 1

    print(f"Sending a test message to {recipient} ...")
    result = send_test_email(recipient)

    print(f"\n  status: {result.status.value}")
    print(f"  {result.detail}")
    if result.error:
        print(f"  error:  {result.error}")

    if result.status.value == "SENT" and settings.EMAIL_PROVIDER == "file":
        print(f"\nWritten to {settings.EMAIL_OUTBOX_DIR}/ - open the .eml file to read it.")

    return 0 if result.sent else 1


if __name__ == "__main__":
    sys.exit(main())
