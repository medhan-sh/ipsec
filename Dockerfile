# Canonical dev/execution environment for this project (MVP_BUILD_PROMPT.md
# §3: "Docker is the development and execution environment"). Run tests and
# CLI invocations inside it rather than depending on the host Python — this
# host's Homebrew toolchain in particular is broken for any compiled
# C-extension package (Python's pyexpat, Wireshark's tshark) against macOS
# 26 ("Tahoe"), but the point of building this in Phase 0 is to not depend
# on host Python at all, on any machine.
#
# Amendment (Phase 6c): the package is now properly `pip install`ed into
# the image, not mounted at runtime — Docker is meant to be invisible
# behind `./ipsec-analyze`, and that only works if the `ipsec-analyze`
# console script and `import ipsec_analyzer` both work with no PYTHONPATH.
# `docker run --rm ipsec-analyzer:dev --help` must print CLI help.
FROM python:3.11-slim

# Pinned for reproducibility. Update deliberately, not silently, if tshark's
# `-T json` output shape ever needs to be re-baselined against a newer
# release. Confirmed available in this base image's apt repository at the
# time of this amendment (`apt-cache madison tshark` inside a fresh
# python:3.11-slim container, both trixie/main and trixie-security) — if a
# future rebuild finds this exact version no longer offered, that is a
# real event worth noticing, not something to silently loosen to `tshark`
# unpinned.
ARG TSHARK_VERSION=4.4.18-0+deb13u1

# DEBIAN_FRONTEND=noninteractive is load-bearing, not decorative: tshark's
# postinst asks a debconf question (whether non-root users may capture
# live traffic) that has no answer without a TTY, and the build hangs
# waiting for one otherwise. This tool only ever reads capture files
# handed to it — it never opens a live interface — so the question's
# answer is moot either way; what matters is that nothing here prompts.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        tshark=${TSHARK_VERSION} \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Dependencies first, keyed only on pyproject.toml — editing anything
# under src/ later must not reinstall scapy. Listed explicitly (matching
# pyproject.toml's own `dependencies` + `optional-dependencies.dev`)
# rather than `pip install .` at this stage, since that would need `src/`
# already present and would defeat this layer's own caching purpose.
COPY pyproject.toml ./
RUN pip install --no-cache-dir scapy pyyaml jinja2 pytest

# The package itself, installed properly into site-packages so the
# `ipsec-analyze` console script (registered in pyproject.toml's
# `[project.scripts]`) and `import ipsec_analyzer` both work with no
# PYTHONPATH, independent of whatever gets bind-mounted at /work at
# `docker run` time (a real capture directory, not this build context).
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

# /work is the runtime mount point (see ./ipsec-analyze) and the
# container's default working directory, so relative capture paths like
# `captures/x.pcap` resolve against whatever the wrapper mounted there.
WORKDIR /work
ENTRYPOINT ["ipsec-analyze"]
