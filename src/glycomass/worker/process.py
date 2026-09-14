"""Isolated CPU-bound MGF processing entry point for the arq worker."""
import json
import sys

from glycomass.config import get_settings
from glycomass.core.identifier.pipeline import process_mgf
from glycomass.logging_config import configure_logging

if __name__ == "__main__":
    settings = get_settings()
    configure_logging(json_output=settings.log_json, level=settings.log_level)
    print(json.dumps(process_mgf(sys.argv[1], sys.argv[2])))
