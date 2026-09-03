# School Results Management & Report Card Portal

A focused portal for collecting examination results from teachers, validating and
combining them, and publishing school-branded report cards.

It is **not** a general school management system. There is no parent portal, no public
registration, and no attendance, assignments, announcements, fees, payments or timetables.

## What it does

1. Manage students and teachers
2. Manage student subject enrollment
3. Let teachers upload examination results as CSV files
4. Validate uploaded results
5. Match results using unique student numbers
6. Ensure students only receive results for subjects they are enrolled in
7. Combine results uploaded by different teachers
8. Let authorised users correct results
9. Monitor teacher result submissions and deadlines
10. Let administrators publish completed results
11. Generate professional school-branded report cards
12. Let authorised users download results as PDF and CSV

## Roles

`ADMIN` · `TEACHER` · `STUDENT` — accounts are created by administrators only.

## Stack

| Layer    | Technology                                       |
| -------- | ------------------------------------------------ |
| Frontend | React 19 + JavaScript (no TypeScript), Vite       |
| Styling  | Tailwind CSS v4 (`@tailwindcss/vite`)            |
| Icons    | Font Awesome 7 (`@fortawesome/react-fontawesome`)|
| Routing  | React Router v7                                  |
| HTTP     | Axios                                            |
| Backend  | Python 3.11+ / FastAPI                           |
| ORM      | SQLAlchemy 2.x                                   |
| Database | MySQL 8 (PyMySQL driver)                         |
| Auth     | JWT (PyJWT) + bcrypt                             |

## Layout

```
School Magement Portal/
├── backend/
│   ├── app/
│   │   ├── auth/           JWT creation/verification, bearer scheme
│   │   ├── dependencies/   get_current_user, require_roles
│   │   ├── models/         SQLAlchemy ORM models
│   │   ├── routers/        HTTP endpoints (health, auth, ...)
│   │   ├── schemas/        Pydantic request/response models
│   │   ├── services/       Business logic
│   │   ├── utils/          Password hashing, grade banding
│   │   ├── config.py       Environment-driven settings
│   │   ├── database.py     Engine, session factory, Base
│   │   └── main.py         FastAPI app
│   ├── scripts/init_db.py  Create tables + first admin
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── src/
        ├── components/     ui/ primitives, common/, routing/ guards
        ├── context/        AuthContext
        ├── hooks/          useAuth, useApiHealth, useDocumentTitle
        ├── layouts/        AuthLayout, PortalLayout, Sidebar, Topbar
        ├── lib/            Font Awesome registration
        ├── pages/          Landing, Login, 404, role dashboards
        ├── services/       Axios client + API services
        ├── utils/          constants, roles, storage, formatting
        ├── App.jsx         Route table
        └── index.css       Tailwind theme / design system
```

---

## Setup

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.11+**
- **MySQL 8** running and reachable

### 1. Create the MySQL database

```sql
CREATE DATABASE school_results_portal
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'portal_user'@'localhost' IDENTIFIED BY 'your-strong-password';
GRANT ALL PRIVILEGES ON school_results_portal.* TO 'portal_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Backend

```bash
cd backend

python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env` from the template and fill in **your own** values:

```bash
cp .env.example .env       # Windows: copy .env.example .env
```

Set at minimum `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` and `SECRET_KEY`.
Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> No credentials are hard-coded anywhere in the source, and `backend/.env` is gitignored.

Create the tables and your first administrator:

```bash
# Windows (PowerShell)
$env:ADMIN_EMAIL="admin@yourschool.edu"; $env:ADMIN_PASSWORD="a-strong-password"; $env:ADMIN_USERNAME="admin"; python -m scripts.init_db

# macOS / Linux
ADMIN_EMAIL=admin@yourschool.edu ADMIN_PASSWORD=a-strong-password ADMIN_USERNAME=admin python -m scripts.init_db
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

- API root — <http://127.0.0.1:8000/>
- Interactive docs — <http://127.0.0.1:8000/docs>
- Health check — <http://127.0.0.1:8000/api/v1/health>

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env       # Windows: copy .env.example .env
npm run dev
```

Open <http://localhost:5173>.

Requests to `/api` are proxied to `http://127.0.0.1:8000` by `vite.config.js`, so in
development the browser makes same-origin calls and CORS never applies. For production,
point `VITE_API_BASE_URL` at the deployed API origin — the backend `CORS_ORIGINS` setting
must then list the frontend origin.

### 4. Verify the two are talking

The landing page footer and the login page both show a live **API status badge**:

| Badge                       | Meaning                                           |
| --------------------------- | ------------------------------------------------- |
| `API connected` (green)     | React reached FastAPI, and FastAPI reached MySQL   |
| `API up · database offline` | React reached FastAPI, but MySQL is misconfigured  |
| `API unreachable` (red)     | The backend is not running, or the proxy is wrong  |

From a terminal:

```bash
curl http://localhost:5173/api/v1/health
```

A healthy, fully configured system responds with `"status": "ok"` and
`"database": "connected"`.

---

## Authentication

JWT bearer tokens, bcrypt password hashing, and role checks enforced on the server.

**There is no public registration.** No register or sign-up route exists in the API or
the UI. Teacher and student accounts are created only by an administrator, through
`POST /api/v1/admin/accounts`.

### API

| Method | Path | Auth | Purpose |
| ------ | ---- | ---- | ------- |
| GET | `/` | - | Service info |
| GET | `/api/v1/health` | - | API + MySQL status |
| GET | `/api/v1/ping` | - | Liveness probe (no DB) |
| POST | `/api/v1/auth/login` | - | Sign in with username **or** email; returns JWT + profile |
| POST | `/api/v1/auth/logout` | Bearer | Revokes the token server-side |
| GET | `/api/v1/auth/me` | Bearer | Current user profile |
| POST | `/api/v1/auth/change-password` | Bearer | Change own password; ends every session |
| GET | `/api/v1/auth/password-policy` | - | The rules the API enforces |
| GET | `/api/v1/admin/accounts` | **ADMIN** | List accounts |
| — | `/api/v1/admin/dashboard` | **ADMIN** | Head counts, current examination, submission progress |
| — | `/api/v1/admin/students` | **ADMIN** | Search, add, edit, deactivate; `/subjects` manages enrollment |
| — | `/api/v1/admin/teachers` | **ADMIN** | Search, add, edit, deactivate; `/subjects` manages assignment |
| — | `/api/v1/admin/subjects` | **ADMIN** | Catalogue; `/status` retires, `/usage` reports history |
| — | `/api/v1/admin/classes` | **ADMIN** | Forms and streams |
| — | `/api/v1/admin/academic-years` | **ADMIN** | Years; `/activate` makes one current |
| — | `/api/v1/admin/terms` | **ADMIN** | Terms; `/activate` makes one current |
| — | `/api/v1/admin/examinations` | **ADMIN** | Lifecycle, `/status` publishes, `/submissions` monitors, `/outstanding` chases |
| GET | `/api/v1/teacher/dashboard` | **TEACHER** | My subjects, deadline, submission status |
| — | `/api/v1/teacher/examinations/{e}/subjects/{s}/marksheet` | **TEACHER** | Read and save the roll |
| GET | `/api/v1/teacher/template-options` | **TEACHER** | Examinations and subjects I may generate a template for |
| GET | `/api/v1/teacher/examinations/{e}/subjects/{s}/template.csv` | **TEACHER** | Pre-filled CSV template (`?class_id=` narrows it) |
| GET | `/api/v1/teacher/examinations/{e}/subjects/{s}/classes` | **TEACHER** | Classes in this subject roll |
| POST | `/api/v1/teacher/examinations/{e}/subjects/{s}/upload` | **TEACHER** | Upload marks (`?validate_only=true` to check first) |
| GET | `/api/v1/teacher/examinations/{e}/subjects/{s}/export.csv` `.pdf` | **TEACHER** | Download the mark sheet |
| PUT | `/api/v1/teacher/results/{id}` | **TEACHER** | Correct one mark (audited) |
| GET | `/api/v1/student/results` | **STUDENT** | Own published results only |
| — | `/api/v1/admin/school` | **ADMIN** | School information and `/logo` upload |
| POST | `/api/v1/admin/accounts` | **ADMIN** | Create a teacher or student account |
| PATCH | `/api/v1/admin/accounts/{id}/status` | **ADMIN** | Activate / deactivate |
| POST | `/api/v1/admin/accounts/{id}/reset-password` | **ADMIN** | Issue a new password |

### Authorization is enforced on the server

Frontend route guards decide what to *render*. They are not the security boundary.
Every protected endpoint re-checks the token and the role through
[`app/dependencies/auth.py`](backend/app/dependencies/auth.py), so bypassing a guard in
the browser reveals nothing:

```python
router = APIRouter(dependencies=[Depends(require_admin)])
```

A token is rejected at four separate gates: signature and expiry, the revocation list,
the token version, and the account active flag.

### Errors carry a machine-readable code

Auth failures return `{"detail": {"code": ..., "message": ...}}` so the UI can tell an
expired session apart from a wrong password:

| Code | HTTP | When |
| ---- | ---- | ---- |
| `invalid_credentials` | 401 | Wrong password, **or** no such account (deliberately identical) |
| `account_inactive` | 403 | Credentials were right, but the account is deactivated |
| `token_missing` | 401 | No Authorization header |
| `token_expired` | 401 | Token past its expiry |
| `token_invalid` | 401 | Malformed or badly signed |
| `token_revoked` | 401 | Signed out, password changed, or account deactivated |
| `insufficient_role` | 403 | Authenticated, but the wrong role for this endpoint |

### Passwords

Only a bcrypt hash is ever stored, in `users.password_hash`. Work factor is set by
`BCRYPT_ROUNDS` (default 12, floor of 10).

Changing a password from **Settings > Security > Change Password** requires the current
password, a new one, and a confirmation. On success the API rehashes, replaces the hash,
increments `token_version` — which invalidates every token the account holds, on every
device — and the frontend signs the user out and redirects to `/login`.

The `must_change_password` flag on an administrator-issued account is shown **only** in
Settings > Security. It is deliberately never a login-time notification.

### Logout is real

A JWT cannot be recalled once issued, so signing out records the token `jti` in
`revoked_tokens` and the request dependency rejects it from then on. Rows are swept once
the token would have expired anyway, so the table stays small.

### Sessions in the browser

The token is kept in `localStorage` with its expiry, so a refresh does not sign the user
out, and a timer signs them out the moment it expires. On boot the profile is always
re-fetched from `/auth/me` rather than trusted from cache, so a revoked token or a
deactivated account is caught immediately.

`localStorage` is readable by any script on the origin, so it is only as safe as the app
is free of XSS. Tokens are short-lived and server-side revocable to limit the blast
radius; moving to an httpOnly cookie is the next hardening step, and would need CSRF
protection alongside it.

### Frontend routes

| Route | Access |
| ----- | ------ |
| `/` | Public landing page |
| `/login` | Public; redirects to your dashboard if already signed in |
| `/admin/dashboard` | ADMIN — overview and submission progress |
| `/admin/students` | ADMIN — search, add, edit, deactivate, manage subjects |
| `/admin/teachers` | ADMIN — staff records and subject assignment |
| `/admin/subjects`, `/admin/classes` | ADMIN — catalogues |
| `/admin/academic` | ADMIN — academic years and terms |
| `/admin/examinations` | ADMIN — lifecycle, submission monitor, publication |
| `/admin/school`, `/admin/settings` | ADMIN |
| `/teacher/dashboard`, `/teacher/settings` | TEACHER |
| `/student/dashboard`, `/student/settings` | STUDENT |

Signing in lands each role on their own dashboard. A signed-in user who reaches another
role's route is redirected to their own, not to `/login`.
## Database schema

Fifteen tables, all defined with the SQLAlchemy ORM in [backend/app/models/](backend/app/models/).

| Table | Purpose | Key constraints |
| ----- | ------- | --------------- |
| `users` | Accounts, roles and session state | `email` / `username` unique; `password_hash` only, never plaintext |
| `students` | Learner profiles | `student_number` **unique**; `user_id` unique |
| `teachers` | Staff profiles | `employee_number` unique; `user_id` unique |
| `subjects` | Subject catalogue | `code` unique; tagged O-Level / A-Level / both |
| `classes` | Forms and streams | `name` unique; `level` drives grading |
| `academic_years` | School years | `name` unique |
| `terms` | Terms within a year | unique (`academic_year_id`, `name`) |
| `examinations` | Sittings, deadlines, publication status | unique (`term_id`, `name`) |
| `student_subjects` | Subject enrollment per student per year | unique (`student_id`, `subject_id`, `academic_year_id`) |
| `teacher_subjects` | Subject responsibility per teacher per year | unique (`teacher_id`, `subject_id`, `academic_year_id`) |
| `results` | One mark per student, subject and examination | unique (`student_id`, `subject_id`, `examination_id`) |
| `result_audit_logs` | Immutable trail of every correction | old/new marks and grade, who changed it, and why |
| `result_submissions` | Submission tracking per examination + assignment | unique (`examination_id`, `teacher_subject_id`) |
| `school_settings` | School identity for branded report cards | single row |
| `revoked_tokens` | Tokens invalidated by signing out | `jti` unique; swept once expired |

### The constraints that carry the rules

- **`results` unique on (student, subject, examination)** - this is what lets marks
  uploaded by *different teachers* combine into one report card without duplication, and
  makes a re-upload an update rather than a second row.
- **`student_subjects` is the authority** on which results a student may receive. An
  uploaded row is rejected when there is no ACTIVE enrollment for that student and subject.
- **Dropping a subject is never a delete.** It sets `status = INACTIVE` and stamps
  `dropped_at`. The enrollment row, and every result already attached to it, survives.
- **Corrections are audited.** A change writes a `result_audit_logs` row carrying
  `old_marks`, `new_marks`, `old_grade`, `new_grade`, `changed_by` and `reason`.
- **Accountability outlives accounts.** `results.uploaded_by`, `result_audit_logs.changed_by`
  and `result_submissions.submitted_by` are ON DELETE SET NULL, so removing a user never
  destroys the record of what was uploaded or changed.

### Submission tracking

One `result_submissions` row per examination per teacher-subject assignment answers the
whole monitoring question:

| Question | Column |
| -------- | ------ |
| Which teacher, for which subject? | `teacher_id`, `subject_id`, `teacher_subject_id` |
| Which examination? | `examination_id` |
| Have results been submitted? | `status`, `is_submitted` |
| When? | `submitted_at` |
| Who uploaded them? | `submitted_by` |
| Is it overdue? | `is_overdue`, against `examinations.submission_deadline` |
| How far along? | `expected_count`, `submitted_count` |

### Examination lifecycle and submission tracking

An examination moves one step at a time. `ALLOWED_TRANSITIONS` in
[`academic_service.py`](backend/app/services/academic_service.py) rejects anything else,
so results cannot be published straight out of `DRAFT`:

```
DRAFT -> SUBMISSION_OPEN -> SUBMISSION_COMPLETE -> UNDER_REVIEW -> PUBLISHED
           (teachers may upload)                                    |
           <-------------------- reopen / unpublish ----------------+
```

Opening submissions creates one `result_submissions` row per active
teacher-subject assignment.

**Submission status is derived, never declared.**
[`submission_service.py`](backend/app/services/submission_service.py) recomputes it on
every read from the four things the workflow names - assigned teachers, assigned
subjects, the examination and its deadline, and the results actually on record:

| Marks in | Deadline | Status |
| -------- | -------- | ------ |
| none | ahead | `PENDING` |
| some | ahead | `PARTIAL` |
| none or some | **passed** | `OVERDUE` |
| all | met | `SUBMITTED` |
| all | after | `LATE` |
| nobody enrolled | any | `SUBMITTED` (nothing owed) |

Because it is recomputed rather than stored, a deadline that passed a minute ago shows as
`OVERDUE` immediately - there is no scheduled job to run or miss. Enrolling a student
after the deadline raises the expected count and the row reverts to `OVERDUE` on its own.

`GET /admin/examinations/{id}/outstanding` returns the chase-up list, overdue first.

### What a teacher can and cannot do

Every subject-scoped route passes through `TeacherPortalService.authorise`
([`teacher_portal_service.py`](backend/app/services/teacher_portal_service.py)), which
requires an **active assignment for the academic year the examination sits in**. An
assignment that lapsed last year does not carry over.

A subject that is not assigned to the caller returns **404 — the same answer as a subject
that does not exist**, so the route cannot be used to enumerate what other teachers hold.
Correcting a result by id is authorised from the row itself, not from anything the caller
supplied, so one teacher cannot edit another's mark by guessing an id.

| Teacher can | Teacher cannot |
| ----------- | -------------- |
| Download the CSV template and upload marks | Create students or teachers (403) |
| View and edit their own subject's results | Change student enrolment (403) |
| Download CSV and PDF mark sheets | Reach another teacher's subject (404) |
| See their submission status and deadline | Publish results or move an examination (403) |
| Change their own password | Reach any admin route (403) |

**Writes are also gated by examination status.** Marks may be written while an
examination is `SUBMISSION_OPEN` or `SUBMISSION_COMPLETE`. Once it moves to
`UNDER_REVIEW` or `PUBLISHED`, uploads and edits return **409** with the reason, and the
mark sheet becomes read-only — reading is always allowed.

### CSV template

The teacher picks an examination and one of their own subjects. Both lists come from
`/teacher/template-options`, built server-side from their assignments, so an unauthorised
subject is never even offered — and the download refuses it regardless.

The template is **pre-filled with the roll** for that subject and examination:

```
student_number,student_name,marks
STU-001,Tendai Mapiko,
STU-002,John Doe,
STU-003,Jane Smith,
```

A student appears only if **all three** hold:

- their account is **active** — someone who has left the school is not owed a mark, and
  counting them would make a complete submission impossible
- their enrolment in this subject is **ACTIVE**, not dropped
- the enrolment is for the **academic year the examination sits in**

`?class_id=` narrows it further, for a subject taught to several classes.

**`student_number` is the only matching key.** It is pre-filled so it returns exactly as
it went out. `student_name` is informational: it is never read on upload, and a file with
a name column but no student number is rejected outright. Verified — a row carrying the
right number and a completely wrong name still matches the right student.

### CSV upload

A file is **committed whole or not at all**. Any invalid row and nothing is written, so a
teacher is never left guessing which half landed. Validated per row:

| Rejected when | Message |
| ------------- | ------- |
| Mark is not a number | `'abc' is not a number.` |
| Mark below 0 or above 100 | `A mark cannot be above 100.` |
| Student is not enrolled in the subject | `Is not enrolled in Mathematics this year.` |
| No student has that number | `No student has that number.` |
| Same student twice in one file | `Appears twice in this file (also on row 2).` |
| Header row is missing a column | Names what is missing and what was found |

`?validate_only=true` reports exactly what would happen without saving; the upload dialog
always runs this first and shows the result before offering to save.

Re-uploading over an existing mark is treated as a **correction**: the old and new values
are written to `result_audit_logs` with the reason. Grades are derived from the student's
level (O-Level or A-Level) on the way in, and `submitted_at` records the *first*
delivery, so correcting a mistake never makes an on-time submission look late.

### What students can and cannot see

Enforced in one place, [`student_result_service.py`](backend/app/services/student_result_service.py),
so no second path can disagree with it:

- A result is visible **only** when its examination is `PUBLISHED`. One being collected,
  closed, or under review discloses nothing - not the mark, not the grade, not whether
  one exists.
- Publication is permanent to a student. Results released in an earlier term stay visible
  for good; opening a new examination never hides them.
- An examination in progress is **named but never scored**, so a student knows the school
  has not forgotten them.
- Probing `/student/results/{id}` for an unpublished examination returns **404, not 403**,
  so ids cannot be used to discover that unpublished results exist.
- There is no student id in any route: every response is scoped to the signed-in account.

### O-Level and A-Level

Both halves of the school are supported from one schema:

- `classes.level` is O_LEVEL or A_LEVEL, and a student level is derived from their class.
- `subjects.level` is O_LEVEL, A_LEVEL or BOTH, so one catalogue serves both.
- [backend/app/utils/grading.py](backend/app/utils/grading.py) holds separate bands -
  **A B C D E U** at O-Level, **A B C D E O F** at A-Level - and normalises to a
  percentage first, so a subject marked out of 50 grades on the same scale as one
  marked out of 100.

Class names are never hard-coded: 1C, 2B, Form 4A, Lower 6 Commercials and Upper 6
Sciences are all just rows an administrator creates in `classes`.

## Scripts

**Backend**

| Command                         | Purpose                       |
| ------------------------------- | ----------------------------- |
| `uvicorn app.main:app --reload` | Run the dev server            |
| `python -m scripts.init_db`     | Create tables / seed an admin |

**Frontend**

| Command           | Purpose                     |
| ----------------- | --------------------------- |
| `npm run dev`     | Vite dev server on :5173    |
| `npm run build`   | Production build to `dist/` |
| `npm run preview` | Serve the production build  |
| `npm run lint`    | Lint with oxlint            |

## Not built yet

The administrator portal, authentication, authorization and the database schema are
complete.

Still to come: **report card generation** — a per-student PDF across all subjects, and
the admin-side correction screen that reads `result_audit_logs` back.

Everything else is built and verified end to end: authentication, the administrator
portal, academic periods and publication, the teacher portal with CSV upload and
exports, and the student results view.
