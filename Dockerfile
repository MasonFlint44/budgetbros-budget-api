FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY budget_api ./budget_api

EXPOSE 8000

CMD ["sh", "-c", ": \"${DATABASE_URL:?DATABASE_URL is required}\" && : \"${COGNITO_ISSUER:?COGNITO_ISSUER is required}\" && : \"${COGNITO_CLIENT_IDS:?COGNITO_CLIENT_IDS is required}\" && exec uv run fastapi run budget_api/main.py --host 0.0.0.0 --port 8000"]
