from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from glycomass.config import get_settings
from glycomass.db.models import IdentifierJob
from glycomass.db.session import get_sessionmaker
from glycomass.performance import measure


async def run_identifier_job(
    job_id: str, *, sessionmaker: async_sessionmaker[AsyncSession] | None = None
) -> None:
    """Process one identifier job: run the MGF pipeline and update the job row.

    Independent of arq so it can be unit-tested directly. ``sessionmaker`` is
    overridable for tests.
    """
    sm = sessionmaker or get_sessionmaker()
    settings = get_settings()
    async with sm() as session:
        job = (
            await session.execute(select(IdentifierJob).where(IdentifierJob.id == job_id))
        ).scalar_one()
        job.status = "running"
        await session.commit()
        try:
            settings.result_dir.mkdir(parents=True, exist_ok=True)
            result_path = str(settings.result_dir / f"{job_id}.mgf")
            with measure("identifier.job", job_id=job_id):
                summary = await process_mgf(job.upload_path, result_path)
            job.status = "done"
            job.result_path = result_path
            job.summary = json.dumps(summary)
        except Exception as exc:  # noqa: BLE001 - record any failure on the row
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
        await session.commit()
        if job.status == "done":
            # Retain the source until the result and status are durably committed.
            with contextlib.suppress(OSError):
                Path(job.upload_path).unlink(missing_ok=True)


async def process_mgf(upload_path: str, result_path: str) -> dict[str, object]:
    """Keep CPU work off the arq loop; reap the child even on timeout/shutdown."""
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-P", "-m", "glycomass.worker.process", upload_path, result_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate()
        if stderr:
            # Child timings use stderr; stdout remains the JSON result protocol.
            sys.stderr.write(stderr.decode(errors="replace"))
        if process.returncode:
            raise RuntimeError(stderr.decode(errors="replace")[-2000:])
        summary: dict[str, object] = json.loads(stdout)
        return summary
    finally:
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            await process.wait()


async def identifier_task(ctx: dict[str, object], job_id: str) -> None:  # arq entrypoint
    await run_identifier_job(job_id)
