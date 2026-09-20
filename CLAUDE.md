# CLAUDE.md — invariants for this repo

Full spec: `MVP_BUILD_PROMPT.md` (build order, phases, acceptance criteria)
and `ARCHITECTURE.md` (repository layout, layering, contracts between
components — authoritative over any layout sketch in the build prompt when
the two disagree). This file restates the non-negotiable invariants (§2 of
the build prompt) so they stay visible in every session working in this
repo. Enforced in code, not by discipline — violating one is a bug even if
tests pass.

1. **No tier promotion.** A derived claim's tier is at most the minimum tier
   of its inputs. Enforced in `Claim.__post_init__` (`core/claims.py`).
2. **`OBSERVED` means confidence exactly 1.0.** Not 0.99. If it isn't
   certain, it isn't observed.
3. **`NOT_OBSERVABLE` carries no value.** It is the absence of a claim, not
   a low-confidence claim.
4. **Never hand-roll a protocol dissector.** IKE parsing goes through
   `tshark -T json`. If tshark cannot do it, we abstain.
5. **Framing constants are never invented.** Every IV length, ICV length and
   block size lives in `core/constants.py` with its RFC and section in a
   comment. If a value is needed that isn't there, stop and ask — do not
   infer it.
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
- `core/claims.py`, `core/candidates.py`, and `core/constants.py` are
  **frozen** as of Phase 0 (candidates.py split out of claims.py, and
  notify-type constants added to constants.py, on review after Phase 1 —
  see reports/phase-1.md's addendum). Changing them requires asking first.
- Do only the phase currently in progress. Do not stub out or prepare for
  later phases (see `MVP_BUILD_PROMPT.md` §7 for the explicit out-of-scope
  list). `ARCHITECTURE.md`'s full scaffold names files for phases not yet
  built — those get created when their phase arrives, not before.
- **Test/dev environment:** this host's Homebrew toolchain is currently
  broken for any compiled C-extension package (Python's `pyexpat`,
  Wireshark's `tshark`) against macOS 26 ("Tahoe") — confirmed across
  python@3.11/3.14 and the host tshark install, so it isn't fixable by
  reinstalling one package. Tests run in the pinned image built from
  `docker/test.Dockerfile` (Python 3.11 + TShark 4.4.18, pinned via
  `TSHARK_VERSION` build arg):
  ```
  docker build -t ipsec-analyzer-test:py3.11 -f docker/test.Dockerfile .
  docker run --rm -v "$PWD":/work -w /work ipsec-analyzer-test:py3.11 python -m pytest tests/ -v
  ```
  This is a local test-runner tool only — see ARCHITECTURE.md's "Deliberately
  not used: ... Docker for the MVP", which is about the shipped product, not
  how tests are run on a machine with a broken native toolchain.
