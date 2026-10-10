# School Results & Report Card Portal

A Zimbabwean school's academic records portal. Administrators maintain people, classes, subject enrolment, academic years, terms, examinations, submissions and publication. Teachers enter or import marks for assigned subjects and review prior submissions. Students see only their own published results and download report cards.

School name and motto come from the existing Vite branding configuration; the supplied crest is `frontend/public/logo.png`. Do not replace the crest or invent institutional facts.

## Workflow and constraints

- ADMIN, TEACHER and STUDENT roles are enforced by the existing API and route guards.
- School staff issue accounts. Authentication uses session cookies and CSRF protection.
- Teachers can edit or upload only when the API permits. CSV validation precedes import; replacement marks require the existing confirmation/reason workflow.
- Administrators review examination readiness and publish results. Existing publication snapshots and audit trails remain authoritative.
- Students see unpublished examinations by name/status only. Marks, grades and downloads are available only after publication.
- Student accounts support active/inactive status. Do not invent transferred, returning or completed enrolment states.
- Real dashboard data and recent mark corrections come from existing APIs. No invented statistics or illustrative production datasets.
- Keep React, JavaScript, Tailwind, React Router, Axios and existing backend contracts. No schema changes for design.
- The user explicitly authorised autonomous redesign and useful local tooling, with no unnecessary design confirmation steps.

## Use environment

Everyday administrative and teaching work on desktop/laptop, with complete tablet and phone access. Dense records need clear scanning, long-name handling, accessible forms and recoverable errors. Student screens should read as an individual academic record.

## Design brief source

User attachment: Complete UI/UX Redesign — School Results Management Portal, 9 October 2026. Implement, inspect actual browser output at desktop/laptop/tablet/mobile, refine, and explain the completed changes.
