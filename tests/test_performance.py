import json
import os
import subprocess
import sys

import pytest
import structlog

from glycomass.config import get_settings
from glycomass.performance import measure


@pytest.mark.parametrize("elapsed,level", [(0.1, "debug"), (1.0, "warning"), (2.5, "warning")])
def test_timing_threshold_and_dimensions(monkeypatch, elapsed, level):
    ticks = iter([10, 10 + elapsed])
    monkeypatch.setattr("glycomass.performance.perf_counter", lambda: next(ticks))
    with structlog.testing.capture_logs() as logs, measure("test.operation", peaks=20) as timing:
        timing["grid_points"] = 200
    assert logs == [{
        "event": "operation_timing", "operation": "test.operation", "elapsed_ms": elapsed * 1000,
        "outcome": "ok", "peaks": 20, "grid_points": 200, "log_level": level,
    }]


def test_failed_timing_preserves_exception_without_logging_contents():
    with (
        structlog.testing.capture_logs() as logs,
        pytest.raises(ValueError, match="private input"),
        measure("test.failure"),
    ):
        raise ValueError("private input")
    assert logs[0]["outcome"] == "failed"
    assert "private input" not in str(logs)


def test_configurable_threshold_rejects_negative(monkeypatch):
    monkeypatch.setenv("GLYCOMASS_SLOW_OPERATION_MS", "-1")
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        get_settings()


def test_child_timing_logs_do_not_corrupt_json_result(tmp_path):
    result = subprocess.run([
        sys.executable, "-P", "-m", "glycomass.worker.process",
        "tests/identifier/sample.mgf", str(tmp_path / "out.mgf"),
    ], capture_output=True, text=True, check=True, env={
        **os.environ, "GLYCOMASS_LOG_JSON": "true", "GLYCOMASS_SLOW_OPERATION_MS": "0",
    })
    assert json.loads(result.stdout)["identified"] == 1
    events = [json.loads(line) for line in result.stderr.splitlines()]
    assert {event["operation"] for event in events} == {
        "identifier.read", "identifier.select", "identifier.match_and_filter", "identifier.write",
    }
    assert all(event["level"] == "warning" for event in events)
    assert all("sample.mgf" not in str(event) for event in events)


@pytest.mark.asyncio
async def test_parent_forwards_child_timings_and_still_returns_summary(tmp_path, monkeypatch, capsys):
    from glycomass.worker.tasks import process_mgf

    monkeypatch.setenv("GLYCOMASS_SLOW_OPERATION_MS", "0")
    monkeypatch.setenv("GLYCOMASS_LOG_JSON", "true")
    result = await process_mgf("tests/identifier/sample.mgf", str(tmp_path / "out.mgf"))
    assert result["identified"] == 1
    events = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert len(events) == 4
    assert events[0]["operation"] == "identifier.read"
