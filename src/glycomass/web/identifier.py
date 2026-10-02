from __future__ import annotations

import contextlib
import math
import shutil
from pathlib import Path
from typing import BinaryIO

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from starlette.concurrency import run_in_threadpool

from glycomass.config import get_settings
from glycomass.db.models import IdentifierJob
from glycomass.db.session import get_sessionmaker
from glycomass.logging_config import get_logger
from glycomass.web.pages import templates
from glycomass.web.upload_limit import IDENTIFIER_UNAVAILABLE

router = APIRouter()


async def _get_arq_pool(request: Request) -> ArqRedis:
    """Return a process-wide arq (Redis) pool, creating it once and caching it on
    ``app.state`` so each upload reuses one pool (closed on shutdown) instead of
    leaking a fresh connection pool per request."""
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is None:
        async with request.app.state.arq_pool_lock:
            pool = request.app.state.arq_pool
            if pool is None:
                pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
                request.app.state.arq_pool = pool
    return pool


def _write_upload(src: BinaryIO, dest: Path) -> None:
    with dest.open("wb") as fh:
        shutil.copyfileobj(src, fh)


def _recognizable_mgf(src: BinaryIO) -> bool:
    """Check the first complete spectrum without retaining the upload in memory."""
    inside = False
    peaks = 0
    precursor = False
    try:
        while line := src.readline(4097):
            if len(line) > 4096:
                return False
            line = line.strip()
            if line == b"BEGIN IONS":
                if inside:
                    return False
                inside = True
            elif inside and line == b"END IONS":
                return precursor and peaks > 0
            elif inside and line.startswith(b"PEPMASS="):
                value = float(line.split(b"=", 1)[1].split()[0])
                precursor = math.isfinite(value) and value > 0
            elif inside and line and b"=" not in line and not line.startswith((b"#", b";", b"!")):
                columns = line.split()
                mz, intensity = float(columns[0]), float(columns[1])
                if not (math.isfinite(mz) and math.isfinite(intensity) and mz > 0 and intensity >= 0):
                    return False
                peaks += 1
        return False
    except (ValueError, IndexError):
        return False
    finally:
        src.seek(0)


@router.get("/identifier", response_class=HTMLResponse)
def identifier_page(request: Request) -> HTMLResponse:
    if not get_settings().identifier_enabled:
        return templates.TemplateResponse(
            request, "identifier.html", {"unavailable": IDENTIFIER_UNAVAILABLE}, status_code=503,
        )
    return templates.TemplateResponse(request, "identifier.html")


@router.post("/identifier", response_class=HTMLResponse)
async def identifier_upload(request: Request, mgf_file: UploadFile) -> HTMLResponse:
    settings = get_settings()
    if mgf_file.size is not None and mgf_file.size > settings.max_upload_bytes:
        return templates.TemplateResponse(
            request,
            "_error.html",
            {"message": "File exceeds the maximum upload size."},
            status_code=413,
        )
    if not await run_in_threadpool(_recognizable_mgf, mgf_file.file):
        return templates.TemplateResponse(
            request, "_error.html", {"message": "Upload a valid MGF with at least one spectrum, precursor mass, and peak."},
            status_code=422,
        )
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    sm = get_sessionmaker()
    # Insert the job row in a short session, then persist the upload OUTSIDE the
    # session and OFF the event loop (the copy can be large; don't hold a DB
    # transaction or block the loop while it runs).
    async with sm() as session:
        job = IdentifierJob(upload_path="")
        session.add(job)
        await session.commit()
        jid = job.id
    dest = settings.upload_dir / f"{jid}.mgf"
    try:
        await run_in_threadpool(_write_upload, mgf_file.file, dest)
        async with sm() as session:
            row = await session.get(IdentifierJob, jid)
            if row is not None:
                row.upload_path = str(dest)
                await session.commit()
    except Exception:
        with contextlib.suppress(OSError):
            dest.unlink(missing_ok=True)
        try:
            async with sm() as session:
                row = await session.get(IdentifierJob, jid)
                if row is not None:
                    row.status = "failed"
                    row.error = "Could not persist the upload."
                    await session.commit()
        except Exception:
            get_logger(__name__).exception("upload_failure_cleanup_failed", job_id=jid)
        return templates.TemplateResponse(
            request, "_error.html", {"message": "Could not save the upload — please retry."}, status_code=503,
        )

    try:
        pool = await _get_arq_pool(request)
        await pool.enqueue_job("identifier_task", jid)
    except Exception:
        async with sm() as session:
            row = await session.get(IdentifierJob, jid)
            if row is not None:
                row.status = "failed"
                row.error = "Could not queue the job (queue unavailable)."
                await session.commit()
        with contextlib.suppress(OSError):
            dest.unlink(missing_ok=True)
        return templates.TemplateResponse(
            request,
            "_error.html",
            {"message": "Could not queue the job — please retry."},
            status_code=503,
        )
    return templates.TemplateResponse(request, "_job.html", {"job_id": jid, "status": "queued"})


@router.get("/identifier/{job_id}", response_class=HTMLResponse)
async def identifier_status(request: Request, job_id: str) -> HTMLResponse:
    sm = get_sessionmaker()
    async with sm() as session:
        job = await session.get(IdentifierJob, job_id)
    status = job.status if job else "unknown"
    error = job.error if job else None
    return templates.TemplateResponse(
        request, "_job.html", {"job_id": job_id, "status": status, "error": error}
    )


@router.get("/identifier/{job_id}/download")
async def identifier_download(job_id: str) -> FileResponse:
    sm = get_sessionmaker()
    async with sm() as session:
        job = await session.get(IdentifierJob, job_id)
    if (
        not job
        or job.status != "done"
        or not job.result_path
        or not Path(job.result_path).exists()
    ):
        raise HTTPException(status_code=404, detail="Result not ready")
    return FileResponse(job.result_path, filename="cleaned.mgf", media_type="text/plain")
