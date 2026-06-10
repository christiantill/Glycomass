from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from glycomass.config import get_settings
from glycomass.db.session import dispose_engine
from glycomass.logging_config import configure_logging
from glycomass.web.api.v1 import router as api_router
from glycomass.web.identifier import router as identifier_router
from glycomass.web.pages import router as pages_router

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

    @app.middleware("http")
    async def limit_upload_size(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Reject oversized uploads via Content-Length *before* the body is buffered to
        # disk during multipart parsing (the in-route mgf_file.size check is too late).
        if request.method == "POST" and request.url.path == "/identifier":
            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > get_settings().max_upload_bytes:
                return HTMLResponse(
                    '<div class="error-note">File exceeds the maximum upload size.</div>',
                    status_code=413,
                )
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
    app.include_router(api_router)
    app.include_router(identifier_router)
    app.include_router(pages_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("glycomass.web.app:app", host="0.0.0.0", port=8000)
