# CLAUDE.md — invariants for this repo

Full spec: `MVP_BUILD_PROMPT.md` (build order, phases, acceptance criteria)
and `ARCHITECTURE.md` (repository layout, layering, contracts between
components — authoritative over any layout sketch in the build prompt when
the two disagree, with one exception: MVP_BUILD_PROMPT.md's §3 on Docker is
newer than ARCHITECTURE.md's "Deliberately not used: ... Docker for the
MVP" line and supersedes it — see below). This file restates the
non-negotiable invariants (§2 of the build prompt) so they stay visible in
every session working in this repo. Enforced in code, not by discipline —
violating one is a bug even if tests pass.

1. **No tier promotion.** A derived claim's tier is at most the minimum tier
   of its inputs. Enforced in `Claim.__post_init__`
   (`src/ipsec_analyzer/core/claims.py`).
2. **`OBSERVED` means confidence exactly 1.0.** Not 0.99. If it isn't
   certain, it isn't observed.
3. **`NOT_OBSERVABLE` carries no value.** It is the absence of a claim, not
   a low-confidence claim.
4. **Never hand-roll a protocol dissector.** IKE parsing goes through
   `tshark -T json`. If tshark cannot do it, we abstain.
5. **Framing constants are never invented.** Every IV length, ICV length and
   block size lives in `src/ipsec_analyzer/core/constants.py` with its RFC
   and section in a comment. If a value is needed that isn't there, stop
   and ask — do not infer it.
6. **A failing deterministic estimator returns `NOT_OBSERVABLE`.** Never a
   fallback heuristic, never a loosened tolerance, never a "best guess".
7. **Never weaken a test to make it pass.** If a test fails, either the code
   is wrong or the test encodes a wrong expectation. Changing an assertion
   to match observed behaviour is forbidden unless explicitly flagged and
   explained.
8. **No new runtime dependencies without asking.** Approved: scapy, pyyaml,
   jinja2, pytest, tshark (via subprocess). Nothing else without asking.

Additional constraints:

- No async, no streaming, no bounded-memory work. Load the capture, process
  it, exit.
- No network calls at runtime, ever.
- `src/ipsec_analyzer/core/{claims,candidates,constants}.py` are **frozen**
  as of Phase 0 (candidates.py split out of claims.py, notify-type
  constants added to constants.py, and the whole `core/` package relocated
  under `src/ipsec_analyzer/` per ARCHITECTURE.md — all logged as
  amendments in reports/phase-1.md's addenda, after Phase 1). Changing them
  further requires asking first.
- Do only the phase currently in progress. Do not stub out or prepare for
  later phases (see `MVP_BUILD_PROMPT.md` §7 for the explicit out-of-scope
  list). `ARCHITECTURE.md`'s full scaffold names files for phases not yet
  built — those get created when their phase arrives, not before.
- **Docker is the canonical dev/execution environment** (MVP_BUILD_PROMPT.md
  §3, revised — this supersedes ARCHITECTURE.md's "Deliberately not used:
  ... Docker for the MVP", which predates that revision), but as of Phase
  6c it's an implementation detail behind two entry points, not something
  to invoke directly:
  ```
  ./ipsec-analyze captures/some-capture.pcap   # builds the image on first
                                                # use, then runs the CLI
  make test                                    # full suite, rebuilding
                                                # the image first
  make build                                   # just (re)build the image
  make clean                                   # remove generated reports
  ```
  The pinned image (Python 3.11 + TShark 4.4.18, version pinned via a
  `TSHARK_VERSION` build arg since tshark's JSON output shape varies
  across releases; scapy, pyyaml, jinja2, pytest, and the project itself
  all `pip install`ed into it) is built from the root `Dockerfile`.
  **Unlike before Phase 6c, the project is no longer mounted at runtime —
  it's baked into the image at build time**, so `ipsec-analyze` and
  `import ipsec_analyzer` both work with no `PYTHONPATH`. The practical
  consequence: `./ipsec-analyze` only rebuilds when the image doesn't
  exist yet, so a source change needs `make build` (or deleting the image)
  before `./ipsec-analyze` picks it up — `make test` doesn't have this
  gap, since it rebuilds every time before running. If you (the agent)
  edit source and then want to see it take effect via `./ipsec-analyze`
  rather than `make test`, rebuild first.

  Background: this host's Homebrew toolchain is broken for any compiled
  C-extension package (Python's `pyexpat`, Wireshark's `tshark`) against
  macOS 26 ("Tahoe") — confirmed across python@3.11/3.14 and the host
  tshark install, so it isn't fixable by reinstalling one package. Docker
  was originally adopted here as a workaround for that; the revised build
  prompt has since made it the standing canonical environment regardless.
