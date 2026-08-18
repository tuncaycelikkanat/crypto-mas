# Pure Python Backend Runtime (Decoupled from Frontend)
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-install-project

COPY . .

EXPOSE 8000

# Automatically run database migrations on container startup, then start FastAPI
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn crypto_mas.apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]