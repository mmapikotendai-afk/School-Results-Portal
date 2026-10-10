# Academic Register — implementation contract

Mode: Operate for authenticated workspaces; Read for a student's personal record; Persuade/orient for the public entry page.

## Direction decision

Compared two directions internally:
1. Academic Register: a light, collapsible rail; measured typographic hierarchy; compact census; results collection and publication at the centre.
2. Academic Council: top navigation with broad editorial sections. This offered a strong student experience but required nested menus for the administrator's fourteen destinations.

Selected Academic Register for direct navigation and record density. The crest, navy actions and a small red navigation marker preserve supplied identity. Public Sans serves controls/data; locally served Newsreader gives page and record headings their academic character. Soft neutral surfaces and modest 3–8px corners avoid both rigid paper imitation and generic dashboard styling.

## First viewport

Admin: term/year, compact active register counts, the current examination's actual submission breakdown, and publication readiness.
Teacher: examination context, outstanding work, filterable subject register and direct upload/mark-entry actions.
Student: personal identity and class, latest published subject marks when available, report-card download and examination history.

Signature interaction: a rail that collapses to labelled icon destinations on desktop and becomes a native, focus-trapping navigation dialog on smaller screens.

## Content and action contract

All data is API-backed. Admin correction history uses the existing audit endpoint. No unsupported enrolment statuses. Teacher permissions, validation and reason capture remain intact. Student API calls carry no student identifier and reveal only the signed-in student's authorised record. No production fixture data.

## Responsive and state contract

Desktop 1440×1000; laptop 1280×800; tablet 820×1180; mobile 390×844. Shared tables become labelled rows under 768px, including editable mark sheets. Filters wrap, names can break, modal bodies scroll independently of actions. Keyboard focus, Escape/return focus, disabled and pending controls, empty/search/error/loading states, and reduced motion must be verified.

## Research translated into decisions

- [Linear's interface refresh](https://linear.app/now/behind-the-latest-design-refresh): reduce competing chrome so task content leads; do not copy their layout or brand.
- [Carbon data-table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines): align record data, put filtering near its results, keep row actions consistent.
- [Impeccable](https://github.com/pbakaus/impeccable): Operate-mode hierarchy, restrained expression, authentic content, bounded screenshot inspection and finish review.
- [Playwright browser support](https://playwright.dev/docs/browsers): use locally installed Microsoft Edge for real render and interaction checks.

## Evidence

Local, read-only account review: `frontend/e2e/review.mjs`.
Isolated edge-state fixtures: `frontend/e2e/states.mjs`.
Screenshots and axe findings stay in ignored `backend/var/ui-review/`, because real captures contain school records. The edge-state script intercepts every API request; its sample marks never reach the database or production UI.

The Impeccable launcher failed on this Windows installation; context and craft guidance were read directly. No detector or concept-seed binary result is claimed.
