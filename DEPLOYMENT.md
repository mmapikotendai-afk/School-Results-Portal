# Deploying for testing — Render + Neon + Vercel

Three pieces, deployed separately, all on free tiers:

| Piece | Where | Cost |
|---|---|---|
| FastAPI backend | Render | free |
| Postgres database | Neon | free |
| React frontend | Vercel | free |

Two things about the free tiers are worth knowing before you rely on this:

- **Render spins the service down after 15 minutes without traffic**, and takes
  about a minute to come back. The first person to sign in after a quiet spell
  waits. Fine for testing, not for a school day — the fix is a paid instance,
  not a workaround.
- **Render's own free Postgres expires 30 days after creation.** That is why the
  database is on Neon instead, whose free tier does not expire.

---

## 1. Database — Neon

1. Sign up at <https://neon.tech>, create a project.
2. Copy the connection string:

   ```
   postgresql://user:password@ep-something.aws.neon.tech/neondb?sslmode=require
   ```

Nothing needs converting. `_normalise_database_url` in `app/config.py` rewrites
the scheme to `postgresql+psycopg://` on the way through, because SQLAlchemy
refuses the `postgres://` form some providers still hand out rather than
guessing what was meant.

The database starts empty. The build step below creates every table.

---

## 2. Backend — Render

1. At <https://dashboard.render.com> choose **New → Blueprint** and point it at
   this GitHub repository. Render reads `render.yaml` and proposes the service.
2. It will ask for the values marked `sync: false` — those are the secrets, and
   they are deliberately not in the repository.

### Environment variables

```
DATABASE_URL          postgresql://…?sslmode=require      (from Neon)
SECRET_KEY            a fresh 64-byte key — see below
CORS_ORIGINS          https://your-project.vercel.app
FRONTEND_URL          https://your-project.vercel.app

EMAIL_ENABLED         true
EMAIL_PROVIDER        smtp
EMAIL_HOST            smtp-relay.brevo.com
EMAIL_PORT            587
EMAIL_USE_TLS         true
EMAIL_USE_SSL         false
EMAIL_USERNAME        b84b01001@smtp-brevo.com
EMAIL_PASSWORD        your Brevo SMTP key
EMAIL_FROM            mmapikotendai@gmail.com
EMAIL_FROM_NAME       Presbyterian High School

SCHOOL_NAME           Presbyterian High School
SCHOOL_MOTTO          Knowledge. Integrity. Service.
STUDENT_EMAIL_DOMAIN  students.internal

ADMIN_EMAIL           you@example.com
ADMIN_PASSWORD        a strong password
ADMIN_NAME            Head Teacher
```

Generate the signing key rather than reusing the development one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`CORS_ORIGINS` and `FRONTEND_URL` are the same URL but different jobs:
CORS_ORIGINS decides which browser origins the API will answer at all;
FRONTEND_URL is the sign-in link written into every credential email. Fill them
in after step 3, when Vercel has given you a domain.

`ADMIN_*` are read only when no administrator exists. **Delete all three after
the first successful deploy** — they are a bootstrap, not configuration.

`ENVIRONMENT=production` and `DEBUG=false` are set in `render.yaml` itself.
DEBUG=false also withdraws `/docs`, `/redoc` and `/openapi.json`.

### What the blueprint does

- **Build**: `pip install -r requirements.txt && python -m scripts.init_db`.
  `init_db` creates missing tables and, on an empty database, the first
  administrator. It is idempotent — `create_all` never alters a table that
  already exists — so it is safe on every deploy, and a failure fails the build
  rather than leaving a half-migrated service taking traffic.
- **Start**: uvicorn on Render's `$PORT`, with `--proxy-headers` so the
  application sees the real client address through Render's router rather than
  the router's own. The rate limiter counts per address, so without this every
  caller would look like the same one.
- **Health check**: `/api/v1/health`, which reports database connectivity too.

Verify:

```bash
curl https://your-service.onrender.com/api/v1/health
```

`"database": "connected"` means Neon is reachable. Allow a minute on the first
call if the service has spun down.

---

## 3. Frontend — Vercel

1. At <https://vercel.com/new> import this GitHub repository.
2. Set **Root Directory** to `frontend`. Vercel then reads `frontend/vercel.json`
   and detects Vite; leave the build settings alone.
3. Add one environment variable:

   ```
   VITE_API_BASE_URL = https://your-service.onrender.com/api/v1
   ```

   Vite reads this at **build** time, not run time, so changing it later needs a
   redeploy — a page refresh will not pick it up.

4. Deploy, then go back to Render and set `CORS_ORIGINS` and `FRONTEND_URL` to
   the Vercel URL.

`vercel.json` rewrites every path to `index.html`. Without it, reloading
`/admin/students` asks Vercel for a file that was never built and returns 404 —
that route only exists once React Router is running. Static files are matched
first, so assets are unaffected.

---

## Order of operations

The two sides each need the other's URL, so:

1. Neon → connection string
2. Render → deploy with a placeholder `CORS_ORIGINS`; note the `.onrender.com` URL
3. Vercel → deploy with `VITE_API_BASE_URL` pointing at Render; note the URL
4. Render → set the real `CORS_ORIGINS` and `FRONTEND_URL`, redeploy
5. Sign in as `ADMIN_EMAIL`, then delete the three `ADMIN_*` variables

---

## Known limits of this setup

**Uploaded files do not survive.** Render's free filesystem is ephemeral, so the
school crest uploaded through Settings is lost on every redeploy, restart and
spin-down. Report cards and mark sheets are generated on demand and are
unaffected. Real use needs object storage (S3, Cloudinary) for uploads.

**The rate limiter counts per process.** `app/utils/rate_limit.py` holds counters
in memory, so more than one instance multiplies the effective limit by the
instance count. One instance is correct here.

**There are no migrations.** `init_db` creates missing *tables*; it never alters
existing ones. Changing an existing table needs a hand-written script, as
`scripts/add_email_columns.py` shows. Alembic is the fix when the schema starts
moving.

**Development is still MySQL.** Both drivers are installed and the models are
portable SQLAlchemy — all 17 tables compile for either — but running different
databases locally and in production is a real source of surprises. Pointing
local development at a second Neon database closes that gap when you want it
closed.
