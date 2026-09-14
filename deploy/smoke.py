"""Exercise a running deployment with synthetic inputs (creates a job/permalinks).

Run: python3 deploy/smoke.py https://staging.glycomass.com
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request

base = sys.argv[1].rstrip("/")


def request(path, data=None, headers=None):
    req = urllib.request.Request(base + path, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode()


assert json.loads(request("/api/v1/health"))["status"] == "ok"
assert "0000-0002-2855-924X" in request("/citation")
for kind, inputs in [
    ("peptide", {"sequence": "PEPTIDE", "charge": 1}),
    ("protein", {"sequence": "PEPTIDE", "charge": 1, "resolution": "medium"}),
    ("glycan", {"hex": 3, "charge": 1}),
]:
    html = request(
        "/" + kind,
        urllib.parse.urlencode(inputs).encode(),
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    match = re.search(r"/c/([a-f0-9]{12})", html)
    assert match, f"{kind}: calculation did not save a permalink"
    assert "spectrum" in request("/c/" + match[1]).lower()

mgf = (
    "BEGIN IONS\nTITLE=deployment_smoke\nPEPMASS=1200.0\nCHARGE=2+\n"
    "366.14 100.0\n800.0 50.0\n1003.0794 90.0\n1300.0 20.0\nEND IONS\n"
)
boundary = "glycomass-deployment-smoke"
body = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="mgf_file"; filename="smoke.mgf"\r\n'
    "Content-Type: text/plain\r\n\r\n"
    + mgf
    + f"\r\n--{boundary}--\r\n"
).encode()
html = request("/identifier", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
match = re.search(r"/identifier/([a-f0-9-]+)", html)
assert match, "Upload did not return a job"
job_path = "/identifier/" + match[1]
for _ in range(30):
    status = request(job_path)
    if "/download" in status:
        break
    if "failed" in status.lower():
        raise AssertionError("Identifier job failed")
    time.sleep(1)
else:
    raise AssertionError("Identifier job did not finish within 30 seconds")
assert "BEGIN IONS" in request(job_path + "/download")
print("PASS: health, citation, all calculators, saved permalinks, queued worker, result download")
