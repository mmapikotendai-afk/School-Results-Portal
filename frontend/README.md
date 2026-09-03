# Frontend — School Results Portal

React 19 + JavaScript (no TypeScript), built with Vite, styled with Tailwind CSS v4.

See the [project README](../README.md) for full setup instructions.

## Quick start

```
npm install
cp .env.example .env
npm run dev
```

The dev server runs on <http://localhost:5173> and proxies `/api` to the FastAPI
backend on <http://127.0.0.1:8000> (see `vite.config.js`).

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
