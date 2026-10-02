"""Isolated CPU-bound MGF processing entry point for the arq worker."""
import contextlib
import json
import sys
from pathlib import Path

from glycomass.config import get_settings
from glycomass.core.identifier.pipeline import process_mgf
from glycomass.logging_config import configure_logging

if __name__ == "__main__":
    # Under memory pressure the kernel should kill this child, not the arq parent:
    # the parent then records a clear failure and keeps consuming jobs.
    with contextlib.suppress(OSError):
        Path("/proc/self/oom_score_adj").write_text("1000")
    settings = get_settings()
    configure_logging(json_output=settings.log_json, level=settings.log_level)
    print(json.dumps(process_mgf(sys.argv[1], sys.argv[2])))
