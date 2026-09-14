#!/bin/sh
set -eu

case "${1:-web}" in
  web)
    # Single-host deployment: one web container applies additive migrations
    # before the proxy can mark it healthy. Never run multiple migration writers.
    alembic upgrade head
    # Only kamal-proxy can reach this container; no application port is
    # published on the host. Trust its scheme headers for HTTPS asset URLs.
    exec uvicorn glycomass.web.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'
    ;;
  worker)
    exec arq glycomass.worker.settings.WorkerSettings
    ;;
  *) exec "$@" ;;
esac
