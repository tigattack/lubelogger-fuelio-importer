FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV CONFIG_DIR=/app/config
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=source=pyproject.toml,target=pyproject.toml \
    --mount=source=uv.lock,target=uv.lock \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --link-mode=copy

COPY src .

ENTRYPOINT ["python", "cli.py"]
