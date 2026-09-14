# Glycomass

Calculate theoretical masses and isotope spectra for glycans, glycopeptides, and
glycoproteins, and process MGF files with a glycopeptide identifier.

The live service at https://glycomass.com runs from `src/glycomass/`: Python 3.14,
FastAPI, Jinja2/HTMX, uPlot, PostgreSQL, and an arq worker backed by Redis.
The former Flask application in `app/` is retained as a legacy reference.

## Cite Glycomass

If you use Glycomass calculations, spectra, or identifier results in a paper,
preprint, thesis, or other research output, please cite the software and state the
version or commit used. For the hosted service, also record the access date.

**Bärenfänger, Melissa, and Till, Christian. Glycomass [Computer software].
https://github.com/christiantill/Glycomass**

Machine-readable metadata is in [CITATION.cff](CITATION.cff).
Melissa Bärenfänger: [ORCID 0000-0002-2855-924X](https://orcid.org/0000-0002-2855-924X).
A software release DOI can be added after archival; none is assigned here yet.

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

## Documentation

- [Contributor instructions](CLAUDE.md)
- [Engine behavior and scientific follow-ups](docs/engine.md)
- [Performance logs and measurements](docs/performance.md)
- [Deployment and operations](deploy/README.md)
- [Public release checklist](docs/release.md)

## License

Glycomass is licensed under the [Apache License 2.0](LICENSE), permitting commercial
use, modification, and redistribution subject to its notice requirements.
Academic citation is requested. Vendored dependencies retain their own licenses.
