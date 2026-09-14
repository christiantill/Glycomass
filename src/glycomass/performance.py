"""Low-volume timings for expensive operations; fields must contain counts, not inputs."""
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from glycomass.config import get_settings
from glycomass.logging_config import get_logger


@contextmanager
def measure(operation: str, **dimensions: int | float | str) -> Iterator[dict[str, int | float | str]]:
    started = perf_counter()
    outcome = "ok"
    try:
        yield dimensions
    except BaseException:
        outcome = "failed"
        raise
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        logger = get_logger("glycomass.performance")
        emit = logger.warning if elapsed_ms >= get_settings().slow_operation_ms else logger.debug
        emit("operation_timing", operation=operation, elapsed_ms=round(elapsed_ms, 3),
             outcome=outcome, **dimensions)
