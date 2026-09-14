# Contributor instructions

Glycomass runs from `src/glycomass/` on Python 3.14. Follow the setup and check
commands in [README.md](README.md); deployment is described in
[deploy/README.md](deploy/README.md).

## Code map

- `core/`: framework-independent compositions, calculators, isotope profiles,
  and MGF identifier pipeline.
- `web/`: FastAPI JSON API, Jinja/HTMX pages, and vendored uPlot charts.
- `db/` and `alembic/`: async SQLAlchemy models and migrations.
- `worker/`: arq jobs with cancellable child-process computation.
- `tests/`, `fixtures/`: regression tests and recorded legacy outputs.

## Constraints

- Preserve numerical tolerances in the legacy parity tests. These fixtures
  establish compatibility, not independent scientific correctness. Document
  intentional chemistry changes and validate them against independent data.
- Read [engine notes](docs/engine.md) before changing mass formulas, Gaussian
  widths, isotope coverage, or identifier logic.
- Keep computation out of the worker event loop. Preserve cancellation,
  bounded uploads, and durable job completion before deleting source files.
- Permalinks store inputs and recompute results with the current engine;
  scientific changes therefore affect existing shared links.
- Profile samples are display data; discrete isotope peaks drive the peak table.
  Preserve full-precision API values and scalar mass calculations.
- The legacy Flask application in `app/` is retained for historical reference.
  `tools/legacy-fixtures/` imports its calculator to reproduce fixtures. New
  features belong in `src/glycomass/`, not the legacy application.
- Never commit credentials, runtime data, or private history backups.
- The staging hostname currently shares the live application and database.
  See the deployment guide before deploying; application changes merged to
  master deploy automatically after CI passes.
