# Contributing to Glycomass

Bug reports and pull requests are welcome. For calculation issues, include the
inputs, observed and expected results, and an independent reference when available.
Avoid including private sequences or unpublished data in public issues.

The application uses Python 3.14, FastAPI, Jinja/HTMX, uPlot, PostgreSQL, and Redis.
Active code lives in `src/glycomass/`. The Flask application in `app/` is retained
for historical reference and fixture generation.

## Run locally

Install [uv](https://docs.astral.sh/uv/) and a C compiler (brainpy builds from
source), then:

```sh
uv sync --frozen --extra dev
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
uv run alembic upgrade head
uv run glycomass-api
```

In a second terminal, run `uv run arq glycomass.worker.settings.WorkerSettings`.
Open http://localhost:8000; API documentation is at http://localhost:8000/docs.
The Docker Compose file and example credentials are for local development only.

## Checks

```sh
uv run ruff check
uv run mypy
uv lock --check
uv run pytest
uv run pytest -m grid --no-cov
```

The calculators are checked against legacy numerical fixtures. The identifier
has structural tests and intentional corrections to the legacy research script;
it has no validated legacy numerical ground truth.

## Maintainer documentation

- [Code map and contributor constraints](CLAUDE.md)
- [Engine behavior and scientific follow-ups](docs/engine.md)
- [Performance logs and measurements](docs/performance.md)
- [Deployment and operations](deploy/README.md)

Application changes merged to `master` deploy after CI passes. Documentation-only
changes do not deploy. There is no hosted staging environment.
