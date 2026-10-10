# Frontend — School Results Portal

React 19 + JavaScript (no TypeScript), built with Vite, styled with Tailwind CSS v4.

See the [project README](../README.md) for full setup instructions.

## Quick start

```
npm install
cp .env.example .env
npm run dev
```

The dev server runs on <http://localhost:5173> and proxies `/api` and `/uploads` to the FastAPI
backend on <http://127.0.0.1:8000> (see `vite.config.js`).

Keep `VITE_API_BASE_URL=/api/v1` in production too. Set the backend host in both
proxy destinations in `vercel.json`; the browser must use its own origin for
session and CSRF cookies. Run `npm test`, `npm run lint`, and `npm run build`
to verify changes.

## Structure

| Path              | Contains                                                      |
| ----------------- | ------------------------------------------------------------- |
| `src/components/` | `ui/` primitives, `common/` shared pieces, `routing/` guards   |
| `src/context/`    | `AuthContext` — session state                                  |
| `src/hooks/`      | `useAuth`, `useApiHealth`, `useDocumentTitle`                  |
| `src/layouts/`    | `AuthLayout`, `PortalLayout`, `Sidebar`, `Topbar`              |
| `src/pages/`      | Landing, Login, 404 and the three role dashboards              |
| `src/services/`   | Axios client and per-domain API services                       |
| `src/utils/`      | Constants, roles, storage and formatting helpers               |
| `src/index.css`   | The design system — colour, type and elevation tokens          |

Import with the `@/` alias, which resolves to `src/` (configured in `vite.config.js`
and `jsconfig.json`).


## Interface design and browser verification

The Academic Register design is documented in [DESIGN.md](../DESIGN.md), with
product constraints in [PRODUCT.md](../PRODUCT.md) and the direction/research
record in [UI-DIRECTION.md](../UI-DIRECTION.md). Shared tokens live in
`src/index.css`. Fonts are bundled from Fontsource, with no external font request.
Role pages load on demand through React lazy imports.

From this directory, with the frontend and backend running locally:

```powershell
npm run test:ui
npm run test:ui:states
```

`test:ui` uses Playwright and installed Microsoft Edge. It reads existing active
local ADMIN, TEACHER and STUDENT accounts via the backend virtual environment
and creates ten-minute test tokens in memory. It does not reset credentials,
persist tokens, or write school records; browser API mutations are blocked.
It requires the local backend database/configuration and Windows virtualenv.

`test:ui:states` uses fully intercepted API fixtures for published results,
long names, empty/error/loading states, CSV selection, mark validation, downloads
and role redirects. It requires the frontend only. The fixture values are never
included in the application build or sent to the database.

Both scripts save screenshots and axe WCAG A/AA findings under the git-ignored
`backend/var/ui-review/` directory. Real-account captures contain school records;
keep these artifacts local. Set `UI_BROWSER` to another installed Playwright
browser channel or `UI_BASE_URL` to a different local frontend URL if needed.
Automated accessibility checks complement the recorded visual and keyboard review;
they are not a full accessibility certification.
