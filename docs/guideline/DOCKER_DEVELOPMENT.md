# Docker development

Install Docker Desktop, enable its WSL 2/Linux-container backend, and start its
engine. Clone the repository and open PowerShell in its root. Node.js, Python,
PostgreSQL, Redis, and MongoDB do not need to be installed on the host.

```powershell
.\start.ps1
```

The script creates missing `.env` and `apps/web/.env.local` files from their
examples without replacing existing files. Docker downloads the database images,
builds all three apps using their lockfiles, starts dependencies in order, applies
Alembic migrations, and waits for the apps to become healthy. The first ML start
trains the bundled synthetic dataset and stores the classifier in a named volume.
First startup needs internet access and can take several minutes.

If PowerShell blocks the script, use a process-only policy override:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Stop any manually running frontend/API/ML servers first; they use the same ports.
If you used the older `infra/docker-compose.dev.yml` stack, stop its containers
without removing volumes before switching. Both stacks use the default `infra`
Compose project so the existing PostgreSQL volume can be reused.

| Service | Host address |
| --- | --- |
| Frontend | http://localhost:3000 |
| API and Swagger | http://localhost:8000/docs |
| ML and Swagger | http://localhost:8001/docs |
| API through Nginx | http://localhost:8080/api/v1/health |
| Development email inbox | http://localhost:8025 |
| PostgreSQL | `localhost:5432`, database/user `dubsibhai`, password `local-dev-only` |
| Redis | `localhost:6379` |
| MongoDB | `mongodb://localhost:27017/dubsibhai` |
| Development SMTP | `localhost:1025` |

These ports bind only to the local machine. This stack is for development and
uses local database credentials; it is not a production deployment.
The application currently uses PostgreSQL and Redis. MongoDB is provisioned for
future features; no existing application data is migrated into it.

## Daily work

```powershell
.\start.ps1             # Build changed images and start everything
.\start.ps1 -NoBuild    # Start using previously built images
.\start.ps1 -Logs       # Follow logs; Ctrl+C exits logs only
.\start.ps1 -Stop       # Stop containers, retaining databases and ML artifacts
```

API and ML `app` directories, API migrations, frontend `src` and `public`, and
the ML dataset are mounted from the checkout. Source edits trigger the dev
servers' reload behavior. Changes to dependencies, Dockerfiles, frontend config,
or files outside those mounts require rerunning `start.ps1` to rebuild images.

The Compose file is `infra/docker-compose.local.yml`. For direct Compose commands
use the same environment files as the launcher:

```powershell
docker compose --env-file .env --env-file apps/web/.env.local -f infra/docker-compose.local.yml ps
docker compose --env-file .env --env-file apps/web/.env.local -f infra/docker-compose.local.yml exec redis redis-cli ping
docker compose --env-file .env --env-file apps/web/.env.local -f infra/docker-compose.local.yml exec mongodb mongosh --quiet --eval 'db.adminCommand({ping: 1})'
```

No database images need a separate manual download. Named volumes retain
PostgreSQL, Redis, MongoDB, and ML weights across stops and image rebuilds.
Do not add `down --volumes` unless you intentionally want to delete their data.

## Google sign-in

Set `GOOGLE_CLIENT_ID` in the root `.env` and the matching
`NEXT_PUBLIC_GOOGLE_CLIENT_ID` in `apps/web/.env.local`. If only one is set, the
stack uses it for both apps. Client secrets are not required by this flow.
Rerun `start.ps1` after changing these values so Docker recreates the affected
containers. Register `http://localhost` and `http://localhost:3000` as authorized
JavaScript origins on the same Google OAuth web client.

Container settings override host-oriented URLs: the API connects to `db`,
`redis`, `mongodb`, and `ml-service` through Docker DNS. Browser requests still
use `http://localhost:8000`. Environment files are excluded from image builds.
Email verification and password reset messages appear in Mailpit.

## ML retraining

After changing the dataset, retrain explicitly, then restart the ML container:

```powershell
docker compose --env-file .env --env-file apps/web/.env.local -f infra/docker-compose.local.yml exec ml-service uv run --no-sync python -m app.train
docker compose --env-file .env --env-file apps/web/.env.local -f infra/docker-compose.local.yml restart ml-service
```

For a real dataset, pass `--data-source real` to the training command. The
classifier uses synthetic data by default; its metrics do not establish
performance on real complaints. A corrupt or incompatible existing artifact is
not overwritten automatically; retrain explicitly.

## Troubleshooting

- Engine unavailable: start Docker Desktop and select Linux containers.
- Port already allocated: stop the native server or competing container using
  the reported port, then rerun the launcher.
- Startup timeout: inspect `start.ps1 -Logs` for dependency, migration, training,
  or application errors. Increasing the timeout does not fix those failures.
- PostgreSQL authentication failure with an old volume: its credentials were
  initialized on first use. Keep the original credentials or back up the database
  before changing them; changing Compose variables does not reset the volume.
- MongoDB requires a CPU compatible with its supported instruction set; inspect
  its logs if it exits immediately on an older machine.
