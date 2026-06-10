from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_chain_upgrades_and_downgrades(tmp_path, monkeypatch):
    """Run the real Alembic chain (0001 -> 0002) against a temp SQLite DB, then unwind it.

    The rest of the suite builds the schema via Base.metadata.create_all, so without this
    the migration scripts (the production schema path) are never executed and could drift
    from the models undetected.
    """
    db_path = tmp_path / "m.db"
    monkeypatch.setenv("GLYCOMASS_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    from glycomass.config import get_settings

    get_settings.cache_clear()
    cfg = Config("alembic.ini")

    command.upgrade(cfg, "head")
    sync_url = f"sqlite:///{db_path}"
    eng = create_engine(sync_url)
    try:
        tables = set(inspect(eng).get_table_names())
    finally:
        eng.dispose()
    assert {"identifier_jobs", "permalinks", "alembic_version"} <= tables

    command.downgrade(cfg, "base")
    eng = create_engine(sync_url)
    try:
        tables = set(inspect(eng).get_table_names())
    finally:
        eng.dispose()
    assert "identifier_jobs" not in tables
    assert "permalinks" not in tables
