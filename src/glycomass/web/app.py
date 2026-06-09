from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from glycomass.config import get_settings
from glycomass.logging_config import configure_logging
from glycomass.web.api.v1 import router as api_router

_HERE = Path(__file__).parent
_STATIC = _HERE / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(json_output=settings.log_json, level=settings.log_level)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Glycomass", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
    app.include_router(api_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("glycomass.web.app:app", host="0.0.0.0", port=8000)
