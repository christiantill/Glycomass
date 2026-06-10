import json
from pathlib import Path

import pytest

import glycomass.db.session as session_mod
from glycomass.config import get_settings

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "legacy_masscalc.json"


@pytest.fixture(scope="session")
def legacy_fixtures() -> dict:
    return json.loads(_FIXTURES.read_text())


@pytest.fixture(autouse=True)
def reset_app_globals():
    """Isolate process-global state between tests.

    Settings are ``lru_cache``d and the DB sessionmaker/engine are cached module globals;
    without this, any test that sets ``GLYCOMASS_*`` env or builds the app would leak its
    config/engine into later tests, causing order-dependent failures.
    """
    get_settings.cache_clear()
    session_mod._engine = None
    session_mod._sessionmaker = None
    yield
    get_settings.cache_clear()
    session_mod._engine = None
    session_mod._sessionmaker = None
