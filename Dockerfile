# Canonical dev/execution environment for this project (MVP_BUILD_PROMPT.md
# §3: "Docker is the development and execution environment"). Run tests and
# CLI invocations inside it rather than depending on the host Python — this
# host's Homebrew toolchain in particular is broken for any compiled
# C-extension package (Python's pyexpat, Wireshark's tshark) against macOS
# 26 ("Tahoe"), but the point of building this in Phase 0 is to not depend
# on host Python at all, on any machine.
FROM python:3.11-slim

# Pinned for reproducibility. Update deliberately, not silently, if tshark's
# `-T json` output shape ever needs to be re-baselined against a newer
# release.
ARG TSHARK_VERSION=4.4.18-0+deb13u1

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        tshark=${TSHARK_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# Approved dependencies only (MVP_BUILD_PROMPT.md §3): scapy, pyyaml,
# jinja2, pytest. The project itself is not installed here — it's mounted
# at runtime (see CLAUDE.md) so code changes don't require an image rebuild.
RUN pip install --no-cache-dir scapy pyyaml jinja2 pytest

WORKDIR /work
