from __future__ import annotations

from arq.connections import RedisSettings

from glycomass.config import get_settings
from glycomass.worker.tasks import identifier_task


class WorkerSettings:
    max_jobs = 1  # bound memory use on the shared application host
    functions = [identifier_task]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
