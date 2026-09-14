from fastapi.responses import HTMLResponse
from starlette.datastructures import Headers
from starlette.formparsers import MultiPartException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from glycomass.config import get_settings


class UploadLimitMiddleware:
    """Enforce the limit while receiving, including bodies without Content-Length."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] == "/identifier"
        ):
            await self.app(scope, receive, send)
            return

        response = HTMLResponse(
            '<div class="error-note">File exceeds the maximum upload size.</div>',
            status_code=413,
        )
        limit = get_settings().max_upload_bytes
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
