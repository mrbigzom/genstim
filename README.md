# GenStim AI

GenStim AI is an international Telegram bot MVP built with Python 3.12, aiogram 3,
FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, and Docker Compose.

The first release provides English and Russian menus, user accounts with three free
credits, referral links, localized command handlers, placeholder creation tools, and
an HTTP health endpoint. QR Designer creates decodable PNG files from text or URLs, and
Background Removal uses the local `rembg` `u2netp` model to create transparent PNG files.
Real paid AI providers and Telegram Stars payments are deliberately not connected yet.

## Quick start with Docker

Requirements: Docker Engine with Docker Compose and a Telegram bot token from
[@BotFather](https://t.me/BotFather).

1. Copy the environment template:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` locally and set `BOT_TOKEN`. Never paste the token into source files,
   commits, issues, or chat messages. The example `DATABASE_URL` is already configured
   for the Compose network. Background removal does not require an API key.

3. Build and start the application:

   ```powershell
   docker compose up --build
   ```

The container applies Alembic migrations before starting. The bot uses long polling,
and the API is available at `http://localhost:8000`. Check it with:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Stop the stack with `docker compose down`. Add `-v` only when you intentionally want
to delete the local PostgreSQL volume.

## Local development

Use Python 3.12 and a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

For local execution outside Docker, change the database host in `.env` from `db` to
`localhost`, start PostgreSQL, then run:

```powershell
alembic upgrade head
python -m app.main
```

Run quality checks:

```powershell
ruff check .
pytest
```

Generate a migration after changing a model:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Telegram commands

- `/start`, `/help`, `/create`, `/tools`
- `/credits`, `/history`, `/invite`, `/language`
- `/support`, `/paysupport`, `/terms`, `/privacy`

Telegram language is detected on first use: Russian Telegram clients start in Russian;
all others default to English. Users can switch manually with `/language`.

## Background Removal

The `✂️ Background Removal` menu item uses `rembg[cpu]` with the lightweight local
`u2netp` model. Inference runs inside the GenStim backend: user images are not sent to a
background-removal API, and no provider account or API key is required. The provider is
still isolated behind `BackgroundRemovalProvider`, so Telegram handlers remain independent
from the implementation.

The Docker build downloads the `u2netp` model into the image. After building, background
removal can run without provider network access:

```powershell
docker compose up -d --build
```

In Telegram, open `/create`, choose `✂️ Background Removal`, and send a JPEG, PNG, WebP,
or HEIC image no larger than 20 MiB and 25 megapixels. The bot replies with a transparent
PNG. Compare `/credits` before and after, then check `/history`: exactly one credit should
be charged and one completed entry shown. An unsupported, corrupted, oversized, or failed
image must not reduce the balance.

Source images are downloaded to a per-request temporary directory and removed after
success or failure. GenStim stores only generation metadata; it does not persist the input
or output image.

## Project structure

```text
app/
  api/             FastAPI application and health endpoint
  bot/             aiogram dispatcher, handlers, keyboards, middleware
  core/            environment settings and logging
  db/              SQLAlchemy base and async session factory
  locales/         English and Russian messages
  models/          database models
  providers/       replaceable local processing provider adapters
  repositories/    persistence operations
  services/        application rules
migrations/        Alembic environment and revisions
tests/             service, configuration, and API tests
```

The repository keeps transport, provider adapters, business rules, and persistence
separate so future AI generation, sticker packs, Telegram Stars, background jobs, referral
rewards, and an admin panel can be added without changing the MVP core.

## Configuration and secrets

Required variables are documented in `.env.example`:

- `BOT_TOKEN`
- `DATABASE_URL`
- `ADMIN_TELEGRAM_ID`
- `ENVIRONMENT`
- `BACKGROUND_REMOVAL_TIMEOUT_SECONDS` (default: `30`)
- `BACKGROUND_REMOVAL_MAX_FILE_MB` (default: `20`)
- `BACKGROUND_REMOVAL_MAX_PIXELS` (default: `25000000`)
- `BACKGROUND_REMOVAL_MAX_CONCURRENCY` (default: `1`)

`.env` is excluded by both `.gitignore` and `.dockerignore`. Configuration loads the bot
token as a Pydantic `SecretStr`, and the application never logs it. Do not commit a real
token or any other credential.

## Legal documents

- [Privacy Policy](PRIVACY.md)
- [Terms of Service](TERMS.md)
