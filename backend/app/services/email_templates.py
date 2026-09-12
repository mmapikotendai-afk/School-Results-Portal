"""Rendering for the transactional emails the portal sends.

Email clients are not browsers. Outlook renders through Word, Gmail strips
`<style>` blocks it dislikes, and almost none of them support flexbox or grid.
So the markup here is deliberately old-fashioned: nested tables, inline styles,
and a single media query for narrow screens. It is not how the web app is
built, and it is not meant to be.

Every message is sent as multipart/alternative, so a client that refuses HTML
still shows a readable plain-text version rather than an empty body.
"""

from html import escape
from typing import List, Optional, Tuple

# Pulled from the portal palette so the mail matches the app it comes from.
BRAND = "#0d1538"
BRAND_LIGHT = "#142058"
INK = "#1e293b"
INK_MUTED = "#64748b"
BORDER = "#e2e8f0"
CANVAS = "#f8fafc"
WARNING_BG = "#fffbeb"
WARNING_BORDER = "#fcd34d"
WARNING_INK = "#92400e"

ROLE_LABEL = {
    "ADMIN": "Administrator",
    "TEACHER": "Teacher",
    "STUDENT": "Student",
}


def role_label(role: str) -> str:
    """Human wording for a role, for the body of the email."""
    return ROLE_LABEL.get(str(role).upper(), str(role).title())


def _row(
    label: str,
    value: str,
    mono: bool = False,
    emphasis: bool = False,
    first: bool = False,
) -> str:
    """One label/value pair in the account details table.

    Rows are separated by a rule on the top edge, so the first one goes
    without: a line above the first label has nothing to divide.
    """
    family = (
        "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
        if mono
        else "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif"
    )
    value_style = (
        f"font-family:{family};font-size:{'18px' if emphasis else '15px'};"
        f"color:{BRAND if emphasis else INK};"
        f"font-weight:{'700' if emphasis else '500'};"
        "letter-spacing:0.02em;word-break:break-all;"
    )
    return f"""
              <tr>
                <td style="padding:{'4px' if first else '12px'} 0 4px 0;
                           {'' if first else f'border-top:1px solid {BORDER};'}">
                  <span style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                               font-size:12px;text-transform:uppercase;letter-spacing:0.08em;
                               color:{INK_MUTED};font-weight:600;">{escape(label)}</span>
                </td>
              </tr>
              <tr>
                <td style="padding:0 0 12px 0;">
                  <span style="{value_style}">{escape(value)}</span>
                </td>
              </tr>"""


def render_credentials_email(
    school_name: str,
    recipient_name: str,
    role: str,
    login_identifier: str,
    temporary_password: str,
    login_url: str,
    identifier_label: str = "Login Email",
    account_number: Optional[Tuple[str, str]] = None,
    reissued: bool = False,
) -> Tuple[str, str, str]:
    """Build the credential email.

    Returns (subject, html_body, text_body). The temporary password is placed
    into the rendered strings and nowhere else: nothing here writes to a log,
    a file or the database.

    `account_number` is an optional (label, value) pair, so a student sees
    their student number and a teacher their employee number.
    """
    account_type = role_label(role)
    verb = "has been reset" if reissued else "has been created"
    subject = (
        f"Your {school_name} portal password has been reset"
        if reissued
        else f"Your {school_name} portal account has been created"
    )

    detail_rows: List[str] = [_row("Account Type", account_type, first=True)]
    if account_number:
        detail_rows.append(_row(account_number[0], account_number[1], mono=True))
    detail_rows.append(_row(identifier_label, login_identifier, mono=True))
    detail_rows.append(
        _row("Temporary Password", temporary_password, mono=True, emphasis=True)
    )

    intro = (
        f"The password for your account on the {school_name} Results Portal "
        f"{verb}. Use the temporary password below to sign in."
        if reissued
        else f"An account {verb} for you on the {school_name} Results Portal. "
        "Use the details below to sign in for the first time."
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<title>{escape(subject)}</title>
<style>
  /* Gmail and Outlook.com honour this; the rest fall back to the inline
     styles, which already work at any width. */
  @media only screen and (max-width:600px) {{
    .wrap {{ width:100% !important; }}
    .pad {{ padding-left:22px !important; padding-right:22px !important; }}
    .btn {{ display:block !important; text-align:center !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:{CANVAS};">
  <!-- Preheader: the grey line of text an inbox shows next to the subject. -->
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">
    Your sign-in details for the {escape(school_name)} Results Portal.
  </div>

  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
         style="background-color:{CANVAS};">
    <tr>
      <td align="center" style="padding:32px 12px;">

        <table role="presentation" class="wrap" cellpadding="0" cellspacing="0" border="0"
               width="100%" style="width:100%;max-width:600px;background-color:#ffffff;
               border:1px solid {BORDER};border-radius:12px;overflow:hidden;">

          <!-- Masthead -->
          <tr>
            <td class="pad" style="background-color:{BRAND};padding:28px 40px;">
              <h1 style="margin:0;font-family:Georgia,'Times New Roman',serif;
                         font-size:22px;line-height:1.3;color:#ffffff;font-weight:600;">
                {escape(school_name)}
              </h1>
              <p style="margin:6px 0 0 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                        font-size:12px;letter-spacing:0.1em;text-transform:uppercase;
                        color:#c7d2fe;font-weight:600;">
                Results Management Portal
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td class="pad" style="padding:36px 40px 8px 40px;">
              <h2 style="margin:0 0 20px 0;font-family:Georgia,'Times New Roman',serif;
                         font-size:20px;line-height:1.35;color:{INK};font-weight:600;">
                Your school portal account {escape(verb)}
              </h2>

              <p style="margin:0 0 16px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                        font-size:15px;line-height:1.6;color:{INK};">
                Dear {escape(recipient_name)},
              </p>
              <p style="margin:0 0 24px 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                        font-size:15px;line-height:1.6;color:{INK};">
                {escape(intro)}
              </p>
            </td>
          </tr>

          <!-- Account details -->
          <tr>
            <td class="pad" style="padding:0 40px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                     style="background-color:{CANVAS};border:1px solid {BORDER};
                            border-radius:10px;padding:8px 20px;">
                <tr><td style="padding:8px 0;">
                  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                    {"".join(detail_rows)}
                  </table>
                </td></tr>
              </table>
            </td>
          </tr>

          <!-- Call to action -->
          <tr>
            <td class="pad" align="center" style="padding:28px 40px 8px 40px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="border-radius:8px;background-color:{BRAND};">
                    <a class="btn" href="{escape(login_url, quote=True)}"
                       style="display:inline-block;padding:14px 32px;
                              font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                              font-size:15px;font-weight:600;color:#ffffff;
                              text-decoration:none;border-radius:8px;">
                      Login to School Portal
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:14px 0 0 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                        font-size:12px;line-height:1.5;color:{INK_MUTED};">
                Or paste this address into your browser:<br>
                <span style="color:{BRAND_LIGHT};word-break:break-all;">{escape(login_url)}</span>
              </p>
            </td>
          </tr>

          <!-- What happens next -->
          <tr>
            <td class="pad" style="padding:24px 40px 0 40px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                     style="background-color:{WARNING_BG};border:1px solid {WARNING_BORDER};
                            border-radius:10px;">
                <tr>
                  <td style="padding:16px 20px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                             font-size:14px;line-height:1.6;color:{WARNING_INK};">
                    <strong style="display:block;margin-bottom:6px;">
                      You must change this password after your first login.
                    </strong>
                    Once you change it you will be signed out automatically and will
                    need to sign in again using your new password. This temporary
                    password stops working at that moment.
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Security warning -->
          <tr>
            <td class="pad" style="padding:20px 40px 32px 40px;">
              <p style="margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                        font-size:14px;line-height:1.6;color:{INK};">
                <strong>Please do not share your login credentials with anyone.</strong>
                Staff at the school will never ask you for your password. If you did
                not expect this email, contact the school office straight away.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td class="pad" style="padding:20px 40px 28px 40px;border-top:1px solid {BORDER};">
              <p style="margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                        font-size:13px;line-height:1.6;color:{INK_MUTED};">
                Regards,<br>
                <strong style="color:{INK};">{escape(school_name)}</strong><br>
                School Results Management Portal
              </p>
              <p style="margin:14px 0 0 0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                        font-size:11px;line-height:1.5;color:{INK_MUTED};">
                This is an automated message. Please do not reply to it.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    number_line = (
        f"{account_number[0]}:\n    {account_number[1]}\n\n" if account_number else ""
    )
    text = f"""{school_name}
Results Management Portal

YOUR SCHOOL PORTAL ACCOUNT {verb.upper()}

Dear {recipient_name},

{intro}

Account Type:
    {account_type}

{number_line}{identifier_label}:
    {login_identifier}

Temporary Password:
    {temporary_password}

Sign in here:
    {login_url}

YOU MUST CHANGE THIS PASSWORD AFTER YOUR FIRST LOGIN.
Once you change it you will be signed out automatically and will need to
sign in again using your new password. This temporary password stops
working at that moment.

Please do not share your login credentials with anyone. Staff at the school
will never ask you for your password. If you did not expect this email,
contact the school office straight away.

Regards,
{school_name}
School Results Management Portal

This is an automated message. Please do not reply to it.
"""

    return subject, html, text
