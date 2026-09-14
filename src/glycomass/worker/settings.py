from __future__ import annotations

from arq.connections import RedisSettings

from glycomass.config import get_settings
from glycomass.logging_config import configure_logging
from glycomass.worker.tasks import identifier_task


async def startup(ctx: dict[str, object]) -> None:
    settings = get_settings()
    configure_logging(json_output=settings.log_json, level=settings.log_level)


class WorkerSettings:
    on_startup = startup
    max_jobs = 1  # bound memory use on the shared application host
    functions = [identifier_task]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
