from arq.connections import RedisSettings


def test_worker_settings_registers_identifier_task():
    # Import-time smoke: WorkerSettings builds RedisSettings.from_dsn() and the function
    # list at class-definition time; this is the entrypoint arq loads in production.
    from glycomass.worker.settings import WorkerSettings

    assert isinstance(WorkerSettings.redis_settings, RedisSettings)
    # The route enqueues by the string "identifier_task"; that must match a registered fn.
    names = {fn.__name__ for fn in WorkerSettings.functions}
    assert "identifier_task" in names
