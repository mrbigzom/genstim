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

2. Open `.env` locally and set `BOT_TOKEN` and `BACKGROUND_REMOVAL_API_KEY`. Never paste
   either token into source files, commits, issues, or chat messages. The example
   `DATABASE_URL` is already configured for the Compose network.

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

The `✂️ Background Removal` menu item uses Photoroom's dedicated Remove Background API.
The provider is isolated behind `BackgroundRemovalProvider`, so it can be replaced without
changing Telegram handlers. Photoroom's Basic endpoint currently costs $0.02 per processed
image and includes 10 free production calls for a new account.

To enable it:

1. Create a Photoroom API account at
   [photoroom.com/api](https://www.photoroom.com/api/remove-background) and enable a Basic
   Remove Background API key.
2. Put only the key value in your local `.env`:

   ```dotenv
   BACKGROUND_REMOVAL_API_KEY=your_photoroom_api_key_here
   ```

3. Rebuild/restart the app so it receives the environment change:

   ```powershell
   docker compose up -d --build
   ```

4. In Telegram, open `/create`, choose `✂️ Background Removal`, and send a JPEG, PNG,
   WebP, or HEIC image no larger than 20 MiB. The bot replies with a transparent PNG.
   Compare `/credits` before and after, then check `/history`: exactly one credit should
   be charged and one completed entry shown. An unsupported file, provider error, or
   timeout must not reduce the balance.

Source images are downloaded to a per-request temporary directory and removed after
success or failure. GenStim stores only generation metadata; it does not persist the input
or output image. Photoroom states that images processed through its API are not saved by
Photoroom.

## Project structure

```text
app/
  api/             FastAPI application and health endpoint
  bot/             aiogram dispatcher, handlers, keyboards, middleware
  core/            environment settings and logging
  db/              SQLAlchemy base and async session factory
  locales/         English and Russian messages
  models/          database models
  providers/       replaceable external AI provider adapters
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
- `BACKGROUND_REMOVAL_API_KEY` (Photoroom Basic API key)
- `BACKGROUND_REMOVAL_TIMEOUT_SECONDS` (default: `30`)
- `BACKGROUND_REMOVAL_MAX_RETRIES` (default: `2`)
- `BACKGROUND_REMOVAL_MAX_FILE_MB` (default: `20`)

`.env` is excluded by both `.gitignore` and `.dockerignore`. Configuration loads the bot
token and provider key as Pydantic `SecretStr` values, and the application never logs
them. Do not commit a real token or any other credential.

## Legal documents

- [Privacy Policy](PRIVACY.md)
- [Terms of Service](TERMS.md)
