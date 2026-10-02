from fastapi.responses import HTMLResponse, JSONResponse
from starlette.datastructures import Headers
from starlette.formparsers import MultiPartException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from glycomass.config import get_settings

IDENTIFIER_UNAVAILABLE = (
    "The identifier is temporarily unavailable while it is being developed. "
    "The mass calculators are not affected."
)


class UploadLimitMiddleware:
    """Enforce the limit while receiving, including bodies without Content-Length."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        is_upload = path == "/identifier"
        is_calculator = path in {
            "/peptide", "/protein", "/glycan",
            "/api/v1/calculate/peptide", "/api/v1/calculate/protein", "/api/v1/calculate/glycan",
        }
        if scope["type"] != "http" or scope["method"] != "POST" or not (is_upload or is_calculator):
            await self.app(scope, receive, send)
            return

        if is_upload and not get_settings().identifier_enabled:
            # Refuse before receiving the body, so a disabled upload costs nothing.
            await HTMLResponse(
                f'<div class="error-note">{IDENTIFIER_UNAVAILABLE}</div>', status_code=503,
            )(scope, receive, send)
            return

        message = "File exceeds the maximum upload size." if is_upload else "Calculation request is too large."
        response = (
            JSONResponse({"detail": message}, status_code=413) if path.startswith("/api/")
            else HTMLResponse(f'<div class="error-note">{message}</div>', status_code=413)
        )
        # Allow URL-encoded 100,000-residue proteins, but bound parsing overhead.
        limit = get_settings().max_upload_bytes if is_upload else 1024 * 1024
        length = Headers(scope=scope).get("content-length", "")
        if length.isdigit() and int(length) > limit:
            await response(scope, receive, send)
            return

        received = 0
        exceeded = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    # The multipart parser closes temporary files on this exception.
                    raise MultiPartException("File exceeds the maximum upload size.")
            return message

        async def limited_send(message: Message) -> None:
            if exceeded:
                # Starlette translates MultiPartException to 400. Replace that with
                # the specific limit response, after its parser has cleaned up.
                if message["type"] == "http.response.start":
                    await response(scope, receive, send)
            else:
                await send(message)

        await self.app(scope, limited_receive, limited_send)
