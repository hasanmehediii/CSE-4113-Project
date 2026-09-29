# DubsiBhai API

Core FastAPI application. From this directory:

```powershell
./run.ps1
```

The launcher installs locked dependencies before starting FastAPI with reload. Press Ctrl+C to stop.
Run `uv run pytest` in this directory for tests.

Swagger UI: http://localhost:8000/docs. Liveness: `/health` and `/api/v1/health`.
Configuration is in `app/core/config.py` and reads the root `.env`.
CORS permits the local Next.js app on port 3000 by default.
Authentication is implemented under `/api/v1/auth`. Start PostgreSQL, Redis, Mailpit,
the API, and Nginx together from the repository root:

```powershell
docker compose -f infra/docker-compose.dev.yml up --build
```

Nginx exposes the API at `http://localhost:8080/api/v1`; Mailpit is at
`http://localhost:8025`. For local `./run.ps1`, first start the DB, Redis and
Mailpit services, then run `uv run alembic upgrade head` in `apps/api`.
Configure a production database, Redis, SMTP provider, random `AUTH_SECRET`,
`ENVIRONMENT=production`, `COOKIE_SECURE=true`, explicit HTTPS CORS origins,
`GOOGLE_CLIENT_ID`, and the actual trusted proxy CIDR. Terminate HTTPS at your
edge and keep the API private behind that proxy.
Use a same-site frontend/API deployment for the `SameSite=Lax` cookie policy.
Email currently uses FastAPI background delivery; add a durable outbox and
delivery monitoring before depending on guaranteed email delivery in production.
Schedule `uv run python -m app.workers.prune_auth` daily to remove expired
sessions and verification/reset tokens.

Browser flow: `GET /auth/csrf` returns a token and sets an HttpOnly CSRF cookie.
Send the returned token as `X-CSRF-Token` with every POST/DELETE request, an
allowed `Origin`, and `credentials: 'include'`. After login the CSRF token
rotates: call `/auth/csrf` again before the next mutation. The session cookie
is HttpOnly and expires on idle/absolute deadlines. Email verification and reset
links arrive in Mailpit in development. Set `FRONTEND_URL` to your web origin
(default `http://localhost:3000`; HTTPS is required in production). Links target
`/verify-email` or `/reset-password`, with the token in the URL fragment so it
does not enter HTTP access logs. Password login accepts email only;
phone login awaits a verified SMS channel. Google login uses a one-time nonce:
POST `/auth/google/nonce`, pass its returned nonce to Google Identity Services,
then POST the Google credential and nonce to `/auth/google`. Existing email
accounts are deliberately not linked by matching email alone.

The API uses Redis atomic leaky buckets for auth IP and account limits. Nginx
adds an IP edge limit. Redis outages reject auth requests (503). Current
sessions are revocable in PostgreSQL. Run `uv run pytest` for auth tests.
