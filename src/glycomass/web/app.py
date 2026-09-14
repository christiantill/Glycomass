from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from glycomass.config import get_settings
from glycomass.db.session import dispose_engine
from glycomass.logging_config import configure_logging
from glycomass.web.api.v1 import router as api_router
from glycomass.web.identifier import router as identifier_router
from glycomass.web.pages import router as pages_router
from glycomass.web.upload_limit import UploadLimitMiddleware

_HERE = Path(__file__).parent
_STATIC = _HERE / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(json_output=settings.log_json, level=settings.log_level)
    try:
        yield
    finally:
        # Close the lazily-created shared arq (Redis) pool and the DB engine cleanly.
        pool = getattr(app.state, "arq_pool", None)
        if pool is not None:
            closer = getattr(pool, "aclose", None) or getattr(pool, "close", None)
            if closer is not None:
                await closer()
        await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="Glycomass", version="0.1.0", lifespan=lifespan)
    app.state.arq_pool = None

    app.add_middleware(UploadLimitMiddleware)

    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
    app.include_router(api_router)
    app.include_router(identifier_router)
    app.include_router(pages_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("glycomass.web.app:app", host="0.0.0.0", port=8000)
