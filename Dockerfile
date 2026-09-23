# Canonical dev/execution environment for this project (MVP_BUILD_PROMPT.md
# §3: "Docker is the development and execution environment"). Run tests and
# CLI/TUI invocations inside it rather than depending on host Python.
#
# Amendment (Phase 6c): the package is properly `pip install`ed into
# the image, not mounted at runtime — Docker is meant to be invisible
# behind `./ipsec-analyze` and `./ipsec-tui`, and that only works if the
# console scripts and `import ipsec_analyzer` both work with no PYTHONPATH.
FROM python:3.11-slim

# Cross-platform environment settings: UTF-8 encoding and 256-color support
# for rich Textual TUI rendering across Linux, macOS, and Windows/WSL.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TERM=xterm-256color \
    PYTHONPATH=/work/src

# Pinned for reproducibility. Update deliberately, not silently, if tshark's
# `-T json` output shape ever needs to be re-baselined against a newer
# release. Confirmed available in this base image's apt repository at the
# time of this amendment (`apt-cache madison tshark` inside python:3.11-slim).
# Includes graceful fallback to general tshark package if architecture mirrors drift.
ARG TSHARK_VERSION=4.4.18-0+deb13u1

# DEBIAN_FRONTEND=noninteractive is load-bearing: tshark's postinst asks a
# debconf question (whether non-root users may capture live traffic) that
# has no answer without a TTY, and the build hangs waiting for one otherwise.
RUN apt-get update \
    && (DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tshark=${TSHARK_VERSION} \
        || DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tshark) \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Dependencies first, keyed only on pyproject.toml — editing anything
# under src/ later must not reinstall dependencies. Listed explicitly
# rather than `pip install .` at this stage for layer caching.
COPY pyproject.toml ./
RUN pip install --no-cache-dir scapy pyyaml jinja2 pytest textual

# The package itself, installed properly into site-packages so the
# `ipsec-analyze` and `ipsec-tui` console scripts both work with no
# PYTHONPATH, independent of whatever gets bind-mounted at /work.
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

# Entrypoint script providing flexible dispatch between CLI analysis,
# interactive TUI console, test suite, and custom shells.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# /work is the runtime mount point and default working directory.
# Relaxed permissions ensure arbitrary non-root host UIDs on Linux (--user)
# have write permissions for output reports and temporary files.
WORKDIR /work
RUN chmod 777 /work /tmp

ENTRYPOINT ["docker-entrypoint.sh"]
