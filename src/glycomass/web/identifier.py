from __future__ import annotations

import shutil
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import select

from glycomass.config import get_settings
from glycomass.db.models import IdentifierJob
from glycomass.db.session import get_sessionmaker
from glycomass.web.pages import templates

router = APIRouter()


@router.get("/identifier", response_class=HTMLResponse)
def identifier_page(request: Request) -> HTMLResponse:
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
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    sm = get_sessionmaker()
    async with sm() as session:
        job = IdentifierJob(upload_path="")
        session.add(job)
        await session.commit()
        jid = job.id
        dest = settings.upload_dir / f"{jid}.mgf"
        with dest.open("wb") as fh:
            shutil.copyfileobj(mgf_file.file, fh)
        job.upload_path = str(dest)
        await session.commit()
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job("identifier_task", jid)
    return templates.TemplateResponse(request, "_job.html", {"job_id": jid, "status": "queued"})


@router.get("/identifier/{job_id}", response_class=HTMLResponse)
async def identifier_status(request: Request, job_id: str) -> HTMLResponse:
    sm = get_sessionmaker()
    async with sm() as session:
        job = (
            await session.execute(select(IdentifierJob).where(IdentifierJob.id == job_id))
        ).scalar_one_or_none()
    status = job.status if job else "unknown"
    return templates.TemplateResponse(request, "_job.html", {"job_id": job_id, "status": status})


@router.get("/identifier/{job_id}/download")
async def identifier_download(job_id: str) -> FileResponse:
    sm = get_sessionmaker()
    async with sm() as session:
        job = (
            await session.execute(select(IdentifierJob).where(IdentifierJob.id == job_id))
        ).scalar_one_or_none()
    if (
        not job
        or job.status != "done"
        or not job.result_path
        or not Path(job.result_path).exists()
    ):
        raise HTTPException(status_code=404, detail="Result not ready")
    return FileResponse(job.result_path, filename="cleaned.mgf", media_type="text/plain")
