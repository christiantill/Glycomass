# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.10.2 AS uv
FROM python:3.14-slim-bookworm AS builder
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock LICENSE NOTICE README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim-bookworm AS runtime
LABEL org.opencontainers.image.source="https://github.com/christiantill/Glycomass"
LABEL org.opencontainers.image.licenses="Apache-2.0"
RUN groupadd --gid 10001 glycomass && useradd --uid 10001 --gid glycomass --no-create-home glycomass \
    && mkdir -p /data/uploads /data/results && chown -R glycomass:glycomass /data
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY LICENSE NOTICE ./
COPY --chmod=755 deploy/entrypoint.sh /usr/local/bin/glycomass-entrypoint
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    GLYCOMASS_ENVIRONMENT=production GLYCOMASS_LOG_JSON=true \
    GLYCOMASS_UPLOAD_DIR=/data/uploads GLYCOMASS_RESULT_DIR=/data/results
USER glycomass
EXPOSE 8000
ENTRYPOINT ["glycomass-entrypoint"]
CMD ["web"]
