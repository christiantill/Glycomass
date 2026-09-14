from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from glycomass.core import NegativeIonSodiumError
from glycomass.db.models import Permalink
from glycomass.db.session import get_sessionmaker
from glycomass.logging_config import get_logger
from glycomass.web.permalinks import DEFAULTS, TEMPLATES, compute_result, save_permalink

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()
logger = get_logger(__name__)


async def _try_save(kind: str, inputs: dict[str, Any]) -> str | None:
    """Persist a permalink best-effort; never let a DB problem break the calculation.

    The ``except`` is intentionally broad: the calculation is the primary feature and must
    succeed even if persistence is misconfigured/down. Failures are logged (not silent) so
    an ongoing persistence outage is observable rather than masked.
    """
    try:
        sm = get_sessionmaker()
        async with sm() as session:
            return await save_permalink(session, kind, inputs)
    except Exception:
        logger.warning("permalink_save_failed", kind=kind, exc_info=True)
        return None


def _page(
    request: Request,
    kind: str,
    *,
    inputs: dict[str, Any] | None = None,
    result: object | None = None,
    slug: str | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        TEMPLATES[kind],
        {"inputs": inputs or DEFAULTS[kind], "result": result, "slug": slug},
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/peptide", response_class=HTMLResponse)
def peptide_page(request: Request) -> HTMLResponse:
    return _page(request, "peptide")


@router.get("/citation", response_class=HTMLResponse)
def citation_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "citation.html")


@router.post("/peptide", response_class=HTMLResponse)
async def peptide_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), carbamidomethyl: bool = Form(False), deamidation: int = Form(0),
) -> HTMLResponse:
    inputs: dict[str, Any] = {
        "sequence": sequence, "hex": hex, "hexnac": hexnac, "fuc": fuc, "sia": sia,
        "charge": charge, "carbamidomethyl": carbamidomethyl, "deamidation": deamidation,
    }
    result = await run_in_threadpool(compute_result, "peptide", inputs)
    slug = await _try_save("peptide", inputs)
    return templates.TemplateResponse(request, "_result.html", {"result": result, "slug": slug})


@router.get("/protein", response_class=HTMLResponse)
def protein_page(request: Request) -> HTMLResponse:
    return _page(request, "protein")


@router.post("/protein", response_class=HTMLResponse)
async def protein_result(
    request: Request,
    sequence: str = Form(...),
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), deamidation: int = Form(0),
    disulfide_bridges: int = Form(0), resolution: str = Form("medium"),
) -> HTMLResponse:
    inputs: dict[str, Any] = {
        "sequence": sequence, "hex": hex, "hexnac": hexnac, "fuc": fuc, "sia": sia,
        "charge": charge, "deamidation": deamidation,
        "disulfide_bridges": disulfide_bridges, "resolution": resolution,
    }
    try:
        result = await run_in_threadpool(compute_result, "protein", inputs)
    except KeyError:
        return templates.TemplateResponse(
            request, "_error.html", {"message": f"Unknown resolution: {resolution}"}
        )
    slug = await _try_save("protein", inputs)
    return templates.TemplateResponse(request, "_result.html", {"result": result, "slug": slug})


@router.get("/glycan", response_class=HTMLResponse)
def glycan_page(request: Request) -> HTMLResponse:
    return _page(request, "glycan")


@router.post("/glycan", response_class=HTMLResponse)
async def glycan_result(
    request: Request,
    hex: int = Form(0), hexnac: int = Form(0), fuc: int = Form(0), sia: int = Form(0),
    charge: int = Form(1), sodium: bool = Form(False), modification: str = Form("None"),
) -> HTMLResponse:
    inputs: dict[str, Any] = {
        "hex": hex, "hexnac": hexnac, "fuc": fuc, "sia": sia,
        "charge": charge, "sodium": sodium, "modification": modification,
    }
    try:
        result = await run_in_threadpool(compute_result, "glycan", inputs)
    except NegativeIonSodiumError as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    slug = await _try_save("glycan", inputs)
    return templates.TemplateResponse(request, "_result.html", {"result": result, "slug": slug})


@router.get("/c/{slug}", response_class=HTMLResponse)
async def shared(request: Request, slug: str) -> HTMLResponse:
    sm = get_sessionmaker()
    async with sm() as session:
        row = await session.get(Permalink, slug)
    if row is None:
        return templates.TemplateResponse(request, "_not_found.html", {}, status_code=404)
    result = await run_in_threadpool(compute_result, row.kind, row.inputs)
    return _page(request, row.kind, inputs=row.inputs, result=result, slug=slug)
