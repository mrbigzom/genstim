FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    REMBG_HOME=/opt/rembg \
    NUMBA_CACHE_DIR=/opt/rembg/numba-cache

WORKDIR /app

RUN apt-get update && \
    apt-get install --no-install-recommends --yes fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --system genstim && adduser --system --ingroup genstim genstim

COPY pyproject.toml README.md ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN mkdir -p /opt/rembg/numba-cache && \
    pip install --upgrade pip && pip install . && \
    python -c "from rembg import new_session; new_session('u2netp')" && \
    chown -R genstim:genstim /opt/rembg

ENV ORT_DISABLE_TELEMETRY=1

USER genstim

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
