# CLAUDE.md — invariants for this repo

Full spec: `MVP_BUILD_PROMPT.md` (build order, phases, acceptance criteria).
This file restates the non-negotiable invariants (§2) so they stay visible
in every session working in this repo. Enforced in code, not by discipline —
violating one is a bug even if tests pass.

1. **No tier promotion.** A derived claim's tier is at most the minimum tier
   of its inputs. Enforced in `Claim.__post_init__` (`claims.py`).
2. **`OBSERVED` means confidence exactly 1.0.** Not 0.99. If it isn't
   certain, it isn't observed.
3. **`NOT_OBSERVABLE` carries no value.** It is the absence of a claim, not
   a low-confidence claim.
4. **Never hand-roll a protocol dissector.** IKE parsing goes through
   `tshark -T json`. If tshark cannot do it, we abstain.
5. **Framing constants are never invented.** Every IV length, ICV length and
   block size lives in `constants.py` with its RFC and section in a
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
- `claims.py` and `constants.py` are **frozen** as of Phase 0. Changing them
  requires asking first.
- Do only the phase currently in progress. Do not stub out or prepare for
  later phases (see `MVP_BUILD_PROMPT.md` §7 for the explicit out-of-scope
  list).
