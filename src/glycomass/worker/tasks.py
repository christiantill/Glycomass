from __future__ import annotations

import contextlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from glycomass.config import get_settings
from glycomass.core.identifier import pipeline
from glycomass.db.models import IdentifierJob
from glycomass.db.session import get_sessionmaker


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
            summary = pipeline.process_mgf(job.upload_path, result_path)
            job.status = "done"
            job.result_path = result_path
            job.summary = json.dumps(summary)
            # The cleaned result supersedes the source upload; drop it to bound disk
            # growth (result retention/TTL is a separate follow-up).
            with contextlib.suppress(OSError):
                Path(job.upload_path).unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001 - record any failure on the row
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
        await session.commit()


async def identifier_task(ctx: dict[str, object], job_id: str) -> None:  # arq entrypoint
    await run_identifier_job(job_id)
