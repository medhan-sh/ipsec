# Local test-runner image only — not part of the shipped product (see
# ARCHITECTURE.md: "Deliberately not used: ... Docker for the MVP"). The
# host machine's Homebrew toolchain is currently broken for *any* compiled
# C-extension package (Python's pyexpat, Wireshark's tshark) against macOS
# 26.2 ("Tahoe"), so this image exists purely to give tests (including
# Phase 4's tshark-based ike_parse.py) one stable place to run.
FROM python:3.11-slim

# Pinned for reproducibility. Update deliberately, not silently, if tshark's
# `-T json` output shape ever needs to be re-baselined against a newer
# release.
ARG TSHARK_VERSION=4.4.18-0+deb13u1

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        tshark=${TSHARK_VERSION} \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest pyyaml jinja2

WORKDIR /work
