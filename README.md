# GenStim AI

GenStim AI is an international Telegram bot MVP built with Python 3.12, aiogram 3,
FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, and Docker Compose.

The current release provides English and Russian menus, user accounts with three free
credits, referral links, localized command handlers, generation history, an HTTP health
endpoint, six local CPU-only creation tools, and an opt-in Telegram Stars payment flow.
No paid AI API is configured.

## Quick start with Docker

Requirements: Docker Engine with Docker Compose and a Telegram bot token from
[@BotFather](https://t.me/BotFather).

1. Copy the environment template:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` locally and set `BOT_TOKEN`. Never paste the token into source files,
   commits, issues, or chat messages. The example `DATABASE_URL` is already configured
   for the Compose network. None of the creation tools requires an API key.

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

## Local CPU tools

The `/create` menu exposes only implemented tools. Every successful operation costs one
credit and creates a completed `/history` record. Failed operations do not spend a credit.

- **Background Removal** — `rembg` with the local `u2netp` model; transparent PNG.
- **QR Designer** — `python-qrcode`; local, scannable PNG from text or a URL (up to 1024
  characters and 2048 UTF-8 bytes).
- **Meme Generator** — Pillow and bundled local template definitions; PNG with English or
  Russian top and bottom text.
- **Pixel Avatar** — Pillow pixelation, palette reduction, and nearest-neighbor upscale;
  three pixel sizes and a 512×512 PNG result.
- **Passport / ID Photo** — local `rembg`, OpenCV face detection, and Pillow composition;
  413×531 PNG on a white, light-gray, or light-blue background. This utility does not
  guarantee official acceptance; users must verify the requirements for their document.
- **Stickers** — local `rembg` and Pillow outline/composition; transparent 512×512 WebP no
  larger than Telegram's 512 KiB static-sticker limit.

AI Avatars, Pet AI, Couple & Family, Baby, Game Character, Roast Me, Photo Enhance, and
Anime remain in the internal feature registry for future work but are hidden from users.

## Telegram Stars payments

Telegram Stars buy internal GenStim credits. Top-up packages are centralized in
`app/payments/catalog.py`: 10 Stars add 10 credits, 25 Stars add 30 credits, and 50 Stars
add 65 credits. Function costs are configured separately in `app/credits/catalog.py`; the
six implemented local tools currently cost one credit per successful result.

The bot creates an `XTR` invoice with no payment provider token. It validates the user,
package, payload, currency, price, and credited amount during pre-checkout and again when
Telegram sends `successful_payment`. The payment record and balance increment are persisted
in one database transaction. Unique Telegram charge IDs and locked payment/user rows prevent
duplicate delivery from adding credits twice. Generations only spend the internal balance.
Refund timestamps and identifiers remain reserved in the schema for a later refund workflow;
this release does not expose refunds or Stars withdrawal.

No new environment variable, API key, TON wallet, smart contract, or BotFather payment
provider configuration is required for Telegram Stars.

Image tools accept JPEG, PNG, WebP, and HEIC files up to 20 MiB and 25 megapixels. Input
files live only in per-request temporary directories, are removed after success or failure,
and are never written to application logs. QR payloads and meme text are not logged.

The direct libraries added for these tools use permissive licenses suitable for commercial
applications: `qrcode` is BSD-3-Clause, OpenCV 4.5+ is Apache-2.0, Pillow is MIT-CMU, and
the DejaVu font package permits use and redistribution as part of a larger software package.
This is a technical compatibility review, not legal advice; preserve dependency license
notices when distributing the application.

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
separate so future AI generation, sticker packs, background jobs, referral
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
