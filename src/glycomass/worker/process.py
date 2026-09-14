"""Isolated CPU-bound MGF processing entry point for the arq worker."""
import json
import sys

from glycomass.core.identifier.pipeline import process_mgf

if __name__ == "__main__":
    print(json.dumps(process_mgf(sys.argv[1], sys.argv[2])))
