# Reproduces the DEPLOYED Glycomass mass-calc stack to capture ground-truth fixtures.
# Throwaway image — runs tools/legacy-fixtures/gen_fixtures.py against app/masscalc.py.
#
# masscalc.py's NUMERIC output depends only on numpy (element arithmetic) + brainpy
# (isotopic distribution). matplotlib only renders the PNG we discard; rq is imported
# at module top but unused by the 3 functions. So we install just the pinned deps that
# affect results — Flask/boto3/etc. from requirements.txt are irrelevant here.
FROM python:3.7-slim

# git: fetch the pinned brainpy commit. build-essential: brainpy has a C/Cython extension.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/mpl \
    HOME=/tmp \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps first so brainpy (installed with --no-build-isolation below) can see them.
# Cython MUST be <3: the pinned 2017-era brainpy has Python-2 'print' statements in its
# .pyx files, which only compile under Cython's language_level=2 (the 0.29.x default).
RUN pip install "numpy==1.19.2" "Cython<3" setuptools wheel

# Pinned brainpy commit, built against the numpy above (no isolated build env).
RUN pip install --no-build-isolation \
    "brain-isotopic-distribution @ git+https://github.com/mobiusklein/brainpy.git@d27e726a67b086936990cbbcef74a827fc1542ff"

# Pinned matplotlib (PNG render path) + rq (module-top import in masscalc.py).
RUN pip install "matplotlib==3.3.2" "rq==1.5.2"

WORKDIR /work
