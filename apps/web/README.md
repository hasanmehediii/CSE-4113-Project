# DubsiBhai Web

Next.js App Router with TypeScript, Tailwind CSS, and ESLint.
From this directory:

```powershell
./run.ps1
```

Open http://localhost:3000. The landing page, authentication pages, and account
page share a responsive pill navbar with persistent English/Bangla and light/dark
preferences. Theme follows the device setting until explicitly selected.
Optional frontend configuration goes in `.env.local` in this directory; see `.env.example`.
The launcher installs locked dependencies before starting Next.js. Press Ctrl+C to stop it.
Package configuration, dependencies, and the pnpm lockfile are local to this app.
Run `npx --yes pnpm@10.34.5 lint`, `npx --yes pnpm@10.34.5 typecheck`,
or `npx --yes pnpm@10.34.5 build` here for validation.

## Authentication setup

1. Start the API and its dependencies from the repository root:
   `docker compose -f infra/docker-compose.dev.yml up --build`.
2. Set `NEXT_PUBLIC_API_URL=http://localhost:8080` in `apps/web/.env.local`
   for Docker. For a separately running API, use `http://localhost:8000`.
   The client also accepts a URL ending in `/api/v1`.
3. Set the API's `FRONTEND_URL` to the frontend origin (default:
   `http://localhost:3000`). It is used for verification/reset email links.
   For Docker, supply API settings in the Compose service environment.
4. Start the web app, register, and open the email in Mailpit at
   `http://localhost:8025`. Follow the verification link, then sign in.

Routes: `/login`, `/register` (`/signup` redirects here), `/verify-email`,
`/resend-verification`, `/forgot-password`, `/reset-password`, and `/account`.
The account page shows email verification, active sessions, individual session
revocation, and sign-out for one or all sessions. Resetting a password revokes
all existing sessions. Email links use URL fragments to keep tokens out of HTTP
access logs; forms read the fragment locally and submit only on confirmation.

For Google sign-in, set the same OAuth web client ID as `GOOGLE_CLIENT_ID` on the
API and `NEXT_PUBLIC_GOOGLE_CLIENT_ID` on the frontend. Add the frontend origin to
the client's authorized JavaScript origins in Google Cloud. Restart/rebuild after
changing public environment variables. The Google button is omitted when no client
ID is configured. Existing email accounts are not automatically linked to Google.
Reference: https://developers.google.com/identity/gsi/web/reference/js-reference

Auth uses HttpOnly API cookies; no credentials or session tokens are saved in
browser storage. Requests include credentials and CSRF headers. Keep frontend
and API on the same site in production, configure HTTPS and exact CORS origins,
and use a real SMTP provider. `FRONTEND_URL` must use HTTPS in production.

Run `npx --yes pnpm@10.34.5 test` for client CSRF/cookie lifecycle tests.
The API suite covers login, verification, password reset, revoked sessions,
Google nonce replay, rate limits, and email-link construction.

The landing page and `/map` include an interactive OpenStreetMap embed of Dhaka,
with four selectable viewports. This external map requires internet access; an
external map link is also provided. Map documentation:
https://wiki.openstreetmap.org/wiki/Export#Embeddable_HTML

The map has no live road measurements yet. `DhakaMapPreview.tsx` keeps the base
map and empty monitoring panel together; a future map library/data integration
can replace the iframe to draw road-level overlays. No sample readings are
presented as live data. Complaint reporting and worker/admin dashboards remain
in development.
