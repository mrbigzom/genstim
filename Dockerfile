FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    U2NET_HOME=/home/genstim/.u2net

WORKDIR /app

RUN addgroup --system genstim && adduser --system --ingroup genstim genstim

COPY pyproject.toml README.md ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN pip install --upgrade pip && pip install .

RUN mkdir -p "$U2NET_HOME" && chown -R genstim:genstim "$U2NET_HOME"

USER genstim

RUN python -c "from rembg import new_session; new_session('u2netp')"

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
