# Database migrations

## 2026-10-09: email-free student accounts

Back up the database, set the application environment variables, then stop
the API and run this from `backend`:

```powershell
$env:DEBUG='false'
.\.venv\Scripts\python.exe scripts\migrate_email_free_students.py
```

The migration makes `users.email` nullable, creates `student_enrollments`,
`student_number_sequences`, and `credential_audits`, assigns each existing
student's permanent number as their username, clears student email values, and creates a current enrollment
without changing student IDs or result rows. It aborts on username collisions
or when students exist without an active academic year. Running it again is
safe.

## 2026-10-09: permanent numbers and progression

After the email-free migration, run:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_permanent_numbers_progression.py
```

This adds `students.admission_year`, explicit class Form values, immutable Form,
class-name and academic-level snapshots to annual enrollment, and the progression
audit table. Existing student IDs and result rows are counted before and after.
Ambiguous legacy class names cause the migration to stop instead of guessing.

## 2026-10-10: email-free teacher accounts

```powershell
$env:DEBUG='false'
.\.venv\Scripts\python.exe scripts\migrate_email_free_teachers.py
```

Teachers sign in with their employee number. The migration clears teacher email
addresses, keeps administrators unchanged, and creates the one-time printable
teacher credential audit table. Existing teachers retain their password hashes.
