import json
from pathlib import Path

import pytest

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "legacy_masscalc.json"


@pytest.fixture(scope="session")
def legacy_fixtures() -> dict:
    return json.loads(_FIXTURES.read_text())
