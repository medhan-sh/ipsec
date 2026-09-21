# Phase 6c: setting ENTRYPOINT ["ipsec-analyze"] on the image (so
# `./ipsec-analyze` and `docker run ipsec-analyzer:dev --help` both work
# without spelling out `python -m ipsec_analyzer.cli`) means the old test
# command — `docker run ... ipsec-analyzer:dev python -m pytest tests/`
# — now runs as `ipsec-analyze python -m pytest tests/` and fails
# immediately (argparse doesn't recognize `python` as a capture file).
# `--entrypoint pytest` overrides the image's entrypoint for exactly this
# one invocation; `pytest` is already an installed console script (a
# `[project.optional-dependencies] dev` dependency), so this doesn't need
# anything the image doesn't already have.

IMAGE := ipsec-analyzer:dev

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
# Same reasoning as ./ipsec-analyze: without this, anything the container
# writes into the bind-mounted tree (.pytest_cache, __pycache__) is
# root-owned on the host.
DOCKER_USER := --user $(shell id -u):$(shell id -g)
else
DOCKER_USER :=
endif

.PHONY: build test clean

build:
	docker build -t $(IMAGE) .

# Depends on `build`, not just an existence check like ./ipsec-analyze's
# auto-build — `make test` exists to validate the *current* source tree,
# so it must pick up local edits every run. Docker's own layer cache
# keeps a no-op rebuild fast (seconds, not a full reinstall).
test: build
	docker run --rm $(DOCKER_USER) -v "$(CURDIR)":/work -w /work --entrypoint pytest $(IMAGE) tests/ -v

clean:
	rm -f report.html findings.json
	rm -f captures/*.report.html captures/*.findings.json
