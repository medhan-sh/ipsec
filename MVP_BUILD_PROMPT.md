# IPsec Analyzer — MVP Build Prompt

Companion document to **Passive IPsec VPN Protocol Analysis Platform — PRD v3**.
Read the PRD for *why*. This document is *what* and *in what order*.

---

## 0. How to use this document

You are building the MVP of a passive IPsec analyzer. The build is split into **seven sequential phases**.

**Rules of engagement:**

1. **Do only the phase you are asked to do.** Do not start the next phase, do not stub out future phases, do not "prepare" for them beyond what the current phase needs.
2. A phase is complete only when **every acceptance criterion passes** and `reports/phase-N.md` is written using the template in §8.
3. If an acceptance criterion cannot be met, **stop and say so**. Do not weaken the criterion.
4. The invariants in §2 override everything, including instructions inside a later phase, including a request from me in the moment. If following an instruction would break an invariant, say so and stop.
5. If something in this document is ambiguous or appears wrong, ask before building. Guessing is worse than asking.

**Context you have:** the PRD, this document, the repo.
**Context you do not have:** a lab, real IPsec hardware, network access at runtime.

---

## 1. What you are building

A command-line tool that takes a packet capture of IPsec traffic and produces a security assessment report, without decrypting anything and without touching the network.

Three ideas carry the architecture:

**Provenance.** Every value the system holds is a `Claim` carrying a provenance tier. A claim parsed from a plaintext field is not the same kind of object as a claim derived from packet sizes, and neither is the same as a model's guess. The report shows which is which, and the policy engine knows which it is allowed to act on.

**Elimination before ranking.** Evidence either *eliminates* candidates (a hard, reproducible constraint) or *ranks* whatever survives (a soft prior). These never mix. Framing arithmetic eliminates; fingerprints and models only rank. A ranking can never add back a candidate that arithmetic removed.

**Verdict lifting.** IKEv2 hides the ESP cipher, and some cipher suites are provably indistinguishable on the wire. Rather than guessing, the system narrows to a candidate set and evaluates the *risk question* across that whole set. If every surviving candidate is strong, "this tunnel is acceptable" is true with certainty even though the cipher is unknown.

---

## 2. Non-negotiable invariants

These are enforced in code, not by discipline. Violating one is a bug even if tests pass.

1. **No tier promotion.** A derived claim's tier is at most the minimum tier of its inputs. Enforced in `Claim.__post_init__`.
2. **`OBSERVED` means confidence exactly 1.0.** Not 0.99. If it isn't certain, it isn't observed.
3. **`NOT_OBSERVABLE` carries no value.** It is the absence of a claim, not a low-confidence claim.
4. **Never hand-roll a protocol dissector.** IKE parsing goes through `tshark -T json`. If tshark cannot do it, we abstain.
5. **Framing constants are never invented.** Every IV length, ICV length and block size lives in `constants.py` with its RFC and section in a comment. If a value is needed that isn't there, stop and ask — do not infer it.
6. **A failing deterministic estimator returns `NOT_OBSERVABLE`.** Never a fallback heuristic, never a loosened tolerance, never a "best guess". If the GCD estimator cannot find a clean answer, that is the correct answer and it must be reported as such.
7. **Never weaken a test to make it pass.** If a test fails, either the code is wrong or the test encodes a wrong expectation. Changing an assertion to match observed behaviour is forbidden unless you explicitly flag it and explain why the original expectation was wrong.
8. **No new runtime dependencies without asking.** The approved list is in §3.

Additional constraints for this MVP:

- No async, no streaming, no bounded-memory work. Load the capture, process it, exit.
- No network calls at runtime, ever. Not for CVE lookups, not for anything.
- `claims.py` and `constants.py` are **frozen** after Phase 0. Changing them requires asking me first.

---

## 3. Stack

- Python 3.11+
- `scapy` — pcap/pcapng reading and IP/UDP layer access
- `pyyaml` — policy rules
- `jinja2` — report template
- `pytest` — tests
- `tshark` — external binary, called via `subprocess`, for IKE dissection

Nothing else without asking. No pandas, no numpy unless a phase explicitly calls for it, no web framework, no Docker.

---

## 4. Frozen contracts

Build these in Phase 0 exactly as specified. They are the spine everything else imports.

### 4.1 `claims.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class Tier(IntEnum):
    """Provenance tiers. Ordered: higher means stronger evidence.

    NOT_OBSERVABLE is the absence of a claim, not a weak claim.
    """
    NOT_OBSERVABLE = 0
    ML_PREDICTION = 1
    INFERRED_IMPLEMENTATION_DEFAULT = 2
    INFERRED_SIDE_CHANNEL = 3
    OBSERVED = 4


class TierPromotionError(Exception):
    """Raised when a derived claim would sit above the weakest of its inputs."""


@dataclass(frozen=True)
class Claim:
    field: str                       # dotted path, e.g. "child_sa.encryption"
    value: Any                       # None iff tier is NOT_OBSERVABLE
    tier: Tier
    confidence: float                # 0.0..1.0; exactly 1.0 when tier is OBSERVED
    method: str                      # short identifier of what produced this
    evidence: tuple[int, ...]        # frame numbers, may be empty for NOT_OBSERVABLE
    caveats: tuple[str, ...] = ()
    derived_from: tuple["Claim", ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence out of range: {self.confidence}")
        if self.tier is Tier.OBSERVED and self.confidence != 1.0:
            raise ValueError("OBSERVED claims must have confidence exactly 1.0")
        if self.tier is Tier.NOT_OBSERVABLE and self.value is not None:
            raise ValueError("NOT_OBSERVABLE claims must carry no value")
        if self.derived_from:
            ceiling = min(c.tier for c in self.derived_from)
            if self.tier > ceiling:
                raise TierPromotionError(
                    f"{self.field}: tier {self.tier.name} exceeds weakest input "
                    f"{ceiling.name}"
                )
```

### 4.2 `CandidateSet` (in `claims.py`)

```python
@dataclass(frozen=True)
class CandidateSet:
    universe: frozenset[str]                    # all suite ids considered
    surviving: frozenset[str]                   # those not yet eliminated
    eliminated_by: tuple[tuple[str, str], ...]  # (suite_id, human-readable derivation)
    indistinguishable: tuple[frozenset[str], ...] = ()


def eliminate(cs: CandidateSet, doomed: set[str], reason: str) -> CandidateSet:
    """Hard constraint. Removes candidates. Returns a new CandidateSet."""
    ...


def rank(cs: CandidateSet, scores: dict[str, float]) -> list[tuple[str, float]]:
    """Soft prior. Returns an ORDERING over cs.surviving.

    Deliberately does NOT return a CandidateSet: ranking can never change
    membership. Scores for suites not in cs.surviving are silently dropped.
    """
    ...
```

The asymmetry between `eliminate` and `rank` — one returns a set, one returns a list — is the whole point. Do not "improve" this by making them symmetric.

### 4.3 `constants.py`

```python
@dataclass(frozen=True)
class SuiteFraming:
    suite_id: str        # e.g. "AES-128-GCM-16"
    family: str          # "cbc" | "counter"
    explicit_iv: int     # bytes on the wire before ciphertext
    pad_granularity: int # 16 for AES-CBC, 8 for 64-bit block CBC, 4 for counter
    icv_len: int         # bytes
    rfc: str             # e.g. "RFC 4106 §3"
```

Exemplar rows — complete the table to roughly 40 entries covering the realistic
deployment space, and mark the whole table `# VERIFY BY HAND`:

| suite_id | family | explicit_iv | pad_granularity | icv_len | rfc |
|---|---|---|---|---|---|
| AES-128-CBC + HMAC-SHA1-96 | cbc | 16 | 16 | 12 | RFC 3602, RFC 2404 |
| AES-128-CBC + HMAC-SHA256-128 | cbc | 16 | 16 | 16 | RFC 3602, RFC 4868 |
| AES-256-CBC + HMAC-SHA256-128 | cbc | 16 | 16 | 16 | RFC 3602, RFC 4868 |
| 3DES-CBC + HMAC-SHA1-96 | cbc | 8 | 8 | 12 | RFC 2451, RFC 2404 |
| DES-CBC + HMAC-MD5-96 | cbc | 8 | 8 | 12 | RFC 2405, RFC 2403 |
| AES-128-GCM-16 | counter | 8 | 4 | 16 | RFC 4106 §3 |
| AES-256-GCM-16 | counter | 8 | 4 | 16 | RFC 4106 §3 |
| AES-128-GCM-12 | counter | 8 | 4 | 12 | RFC 4106 §3 |
| AES-128-CCM-12 | counter | 8 | 4 | 12 | RFC 4309 |
| AES-128-CTR + HMAC-SHA1-96 | counter | 8 | 4 | 12 | RFC 3686, RFC 2404 |
| ChaCha20-Poly1305 | counter | 8 | 4 | 16 | RFC 7634 |

In the Phase 0 report, list **every** constant you added with its RFC section so I can check them by hand. This is the one place a wrong value silently corrupts the entire product.

---

## 5. Repo layout

```
ipsec-analyzer/
  claims.py              # FROZEN after Phase 0
  constants.py           # FROZEN after Phase 0
  ingest.py
  demux.py
  ike_parse.py
  notify_posture.py
  esp_constraints.py
  verdict.py
  report.py
  templates/report.html.j2
  policy/
    engine.py
    rules.yaml
  synth/
    synth_esp.py
    synth_ike.py
  cli.py
  tests/
  reports/               # phase reports live here
  captures/              # downloaded public pcaps, gitignored
  CLAUDE.md
```

---

## 6. Phases

### Phase 0 — Scaffold and frozen contracts

**Goal:** the spine exists and cannot be violated.

**Build:** repo skeleton, `pyproject.toml`, `claims.py` and `constants.py` exactly per §4, `CLAUDE.md` restating §2, pytest wired up.

**Do not build:** anything that uses them.

**Acceptance:**
- `Claim` rejects an `OBSERVED` claim with confidence 0.99.
- `Claim` rejects a `NOT_OBSERVABLE` claim carrying a value.
- `Claim` raises `TierPromotionError` when a claim derived from an `ML_PREDICTION` input declares itself `OBSERVED`.
- `rank()` returns a list and has no code path that constructs a `CandidateSet`.
- `constants.py` has ≥ 35 suites, every one carrying an RFC reference.
- `pytest` passes.

**Report must additionally contain:** the full constants table as a checklist, one row per constant, with RFC section, for hand verification.

---

### Phase 1 — The synthetic oracles

**Goal:** generate labelled test data with no captures and no lab. This is what makes the rest of the build testable.

**Build:**

`synth/synth_esp.py` — given a `SuiteFraming` and a list of inner plaintext lengths, emit the ESP wire lengths per RFC 4303.

```
E = explicit_iv + ciphertext_len + icv_len

  cbc:      ciphertext_len = ceil((P + 2) / b) * b        where b = pad_granularity
  counter:  ciphertext_len = align(P + 2, 4)
```

where `E` is ESP bytes **after** the 8-byte SPI+Sequence header, and `P` is the inner plaintext length.

Worked cases to encode as tests (P = 40, a bare TCP ACK):

| family | b | ciphertext_len | E |
|---|---|---|---|
| counter | 4 | align(42,4) = 44 | 8 + 44 + icv = **52 + icv** |
| cbc | 16 | ceil(42/16)·16 = 48 | 16 + 48 + icv = **64 + icv** |
| cbc | 8 | ceil(42/8)·8 = 48 | 8 + 48 + icv = **56 + icv** |

So AES-128-GCM-16 with a bare ACK gives E = 68; with a 12-byte ICV, E = 64.

Also provide a mode that emits a full synthetic ESP flow: a realistic mix of MTU-sized packets one way and ACKs the other, with configurable packet count.

`synth/synth_ike.py` — build IKE_SA_INIT request/response pairs with configurable notify payloads (by type number), transform sets and DH groups. Output should be consumable by the Phase 2 code directly — it does **not** need to be a valid pcap.

**Do not build:** anything that consumes these yet. No pcap writing.

**Acceptance:**
- Round-trip property: for every suite in `constants.py` and every P in 20..1500, the generated E satisfies the congruence its family implies.
- The three worked cases above produce exactly the stated values.
- `synth_ike` can produce all four notify-posture states (both / request-only / response-only / neither).

---

### Phase 2 — Notify posture and downgrade exposure (F3b)

**Goal:** the first differentiator, testable entirely against `synth_ike`.

**Build:** `notify_posture.py`.

The four-state lattice on notify type **16447** (`IKE_SA_INIT_FULL_TRANSCRIPT_AUTH`, draft-ietf-ipsecme-ikev2-downgrade-prevention-08):

| in request | in response | state |
|---|---|---|
| yes | yes | `PROTECTED` |
| yes | no | `PARTIAL_RESPONDER_LACKS` |
| no | yes | `PARTIAL_INITIATOR_LACKS` |
| no | no | `NONE` |

Protection requires both. The responder sends it unconditionally when it supports it, so response-only is a real and common state — a boolean check would wrongly pass it.

Also detect: notify **16441** `ADDITIONAL_KEY_EXCHANGE` (RFC 9370) = hybrid post-quantum deployment; notifies **16445/16446** (RFC 9867) = PPK in use.

DH group sets:
- weak: `{1, 2, 5, 22, 23, 24}`
- strong: `{14, 15, 16, 17, 18, 19, 20, 21, 31, 32}`

Severity, evaluated only when state is not `PROTECTED`:
- `HIGH` — `ADDITIONAL_KEY_EXCHANGE` present (hybrid PQ deployment, exposed)
- `HIGH` — proposal mixes weak and strong groups
- `MEDIUM` — any weak group negotiable
- `INFO` — no weak method negotiable

All output is `Claim`s at `Tier.OBSERVED`, confidence 1.0.

**Do not build:** any pcap handling. This phase consumes `synth_ike` output only.

**Acceptance:**
- All four lattice states correctly identified.
- Response-only state does **not** report protected.
- All four severity branches exercised.
- Every emitted claim is `OBSERVED` with confidence 1.0 and non-empty evidence.
- No public capture is expected to contain 16447 — it is two months old. Note that in the report.

---

### Phase 3 — ESP constraint engine (F6b)

**Goal:** the second differentiator. The hardest phase. Budget the most time here.

**Build:** `esp_constraints.py`.

**3a. Granularity by GCD.** Collect `E` per SA per direction (subtract the UDP header first under NAT-T encapsulation). Compute the GCD of pairwise differences — equivalently `gcd(E_i - min(E))` over all i.

- `g == 16` → AES-CBC family
- `g == 8` → 64-bit block CBC family (3DES/DES/Blowfish/CAST) — **deterministic weak-crypto finding on its own**
- `g == 4` → counter/AEAD family
- anything else, or fewer than 8 distinct `E` values, or all `E` equal → `NOT_OBSERVABLE`

Do not interpolate, do not pick the nearest of {4,8,16}, do not add tolerance. Invariant 6 applies with full force here.

**3b. TFC gate.** Run **before** trusting any GCD result. Traffic-flow-confidentiality padding (RFC 4303) destroys the residue structure and does so silently. Flag TFC when the length distribution is implausibly uniform (e.g. one length dominates and sits near the MTU) or when the GCD does not land in {4, 8, 16}. On TFC suspicion the entire engine returns `NOT_OBSERVABLE` with a caveat naming TFC.

**3c. ICV by anchor.** Only the **TCP pure-ACK anchor** in this MVP.

- Find a sustained unidirectional burst (one direction carries the large majority of bytes over a window).
- In the reverse direction, take the modal smallest `E`; require at least K such packets at that length (K = 5).
- Hypotheses: inner `P = 40` (no TCP timestamps) or `P = 52` (with timestamps).
- With `g` already known, solve `icv = E_ack - (explicit_iv + ciphertext_len(P))` using the Phase 1 arithmetic.
- If both hypotheses yield a plausible ICV from the known set, report both and widen the candidate set rather than picking one.

**3d. Candidate set.** Start from the full universe in `constants.py`. `eliminate()` on family (from `g`) and on ICV (from the anchor), recording a human-readable derivation for each elimination. Populate `indistinguishable` with the framing-identical groups — suites sharing `(family, pad_granularity, explicit_iv, icv_len)` cannot ever be separated by this method, and key length never changes framing at all.

All claims at `Tier.INFERRED_SIDE_CHANNEL`.

**Do not build:** verdict lifting (Phase 5), fingerprint ranking, ESN inference, any anchor other than pure ACKs.

**Acceptance:**
- For every suite in `constants.py`, a synthetic flow from Phase 1 yields the correct family via GCD.
- For every suite, the ACK anchor recovers the correct `icv_len`.
- A synthetic TFC-padded flow returns `NOT_OBSERVABLE` and does **not** return a wrong answer.
- A flow with all-identical lengths returns `NOT_OBSERVABLE`.
- Framing-identical suites appear together in `indistinguishable` and are never separated.
- `eliminate()` derivations are human-readable strings that a report could print verbatim.

---

### Phase 4 — Real capture path

**Goal:** the first real finding from a real capture.

**Build:** `ingest.py` (scapy, pcap + pcapng, whole file into memory), `demux.py` (UDP/500 → IKE; UDP/4500 → non-ESP marker check → IKE or UDP-encapsulated ESP; IP proto 50 → ESP; IP proto 51 → flag AH deprecated and stop), `ike_parse.py` (subprocess `tshark -T json`, consume the `isakmp` tree, emit `Claim`s at `OBSERVED`).

Wire Phase 2 and Phase 3 to real parsed input.

Test captures — download into `captures/`, gitignored:
- Wireshark's own test suite, e.g. `test/captures/ikev2-decrypt-aes128ccm12.pcap`. **The filename encodes the true algorithm.** That is ground truth with no lab.
- Wireshark SampleCaptures wiki (ISAKMP/ESP samples).
- weberblog.net IKEv1 & IKEv2 captures (Palo Alto and Fortinet — real vendor diversity).

If RFC 7383 fragmentation is present, record the fact and abstain. Do not implement reassembly.

**Do not build:** live capture, replay, AH analysis, TCP/4500.

**Acceptance:**
- IKE SA cipher, integrity, PRF and DH group extracted correctly from at least three distinct public captures.
- ESP constraint engine runs on real ESP flows and its output is consistent with the algorithm encoded in the Wireshark test capture filename.
- A non-IPsec pcap produces a clean "no IPsec found" result, not a crash.
- A truncated / mid-session capture produces coverage gaps, not crashes or invented values.

---

### Phase 5 — Policy engine and verdict lifting

**Goal:** turn claims into findings, and answer the risk question across ambiguity.

**Build:** `policy/engine.py`, `policy/rules.yaml`, `verdict.py`.

Rule schema: `id`, `target` (dotted field path), `min_tier`, `condition`, `severity`, `category`, `references` (list), `recommendation`. A rule whose `min_tier` requirement is unmet emits a **coverage gap**, not a finding.

Fifteen rules for the MVP:

1. Weak DH group negotiated
2. IKEv1 in use
3. IKEv1 Aggressive Mode
4. Downgrade exposure — mixed-strength proposal (HIGH)
5. Downgrade exposure — hybrid PQ deployment (HIGH)
6. Downgrade exposure — weak group negotiable (MEDIUM)
7. Partial downgrade protection — name the deficient endpoint
8. 64-bit block cipher family in ESP
9. Truncated 96-bit ICV
10. NULL encryption
11. AH in use (deprecated)
12. Weak IKE SA cipher (DES / 3DES)
13. Weak IKE SA integrity (MD5 / SHA1)
14. PFS — coverage gap when not observable
15. Anti-replay — always a coverage gap (receiver-side policy, never observable)

Rules 14 and 15 must be *visible in the report as gaps*. They are the demonstration that the provenance model does real work.

**Verdict lifting** (`verdict.py`): evaluate each policy predicate across **every** surviving candidate. Unanimous agreement → emit the verdict at confidence 1.0 without naming a cipher. Disagreement → emit `verdict_ambiguous` naming which candidates drive which outcome.

**Acceptance:**
- A candidate set of all-strong AEAD suites yields "confidentiality acceptable" at confidence 1.0 with no cipher named.
- A candidate set from `g == 8` yields a weak-crypto verdict at confidence 1.0.
- A split candidate set yields `verdict_ambiguous` listing both sides.
- Rules 14 and 15 appear as coverage gaps on every capture.
- The engine reports assessable-vs-total checks as a headline number.

---

### Phase 6 — Report and CLI

**Goal:** something you can put in front of a person.

**Build:** `report.py` + `templates/report.html.j2` + `cli.py`.

One self-contained HTML file. Colour-code every value by provenance tier with a legend. Coverage counter at the top. Every finding links to its frame numbers. Candidate sets rendered as sets, with `indistinguishable` groups shown explicitly. Findings JSON emitted alongside.

CLI: `ipsec-analyze capture.pcap -o report.html [--json findings.json]`

**Do not build:** dashboard, web server, WebSocket, PDF, separate executive report, LLM narrative layer.

**Acceptance:**
- End-to-end on `ikev2-decrypt-aes128ccm12.pcap` produces a report containing: IKE SA parameters, notify posture state, an ESP candidate set consistent with the filename's algorithm, an explicit statement of what cannot be distinguished, a lifted risk verdict, a coverage count, and frame references on every finding.
- Same on the Palo Alto and Fortinet captures.
- Report opens standalone in a browser with no network access.

---

## 7. Explicitly out of scope for this MVP

Do not build, do not stub, do not scaffold for: the lab testbed, the ML traffic classifier, conformal prediction, SHAP, the implementation fingerprint database, CVE lookup, the interactive dashboard, live capture, replay-as-live, RFC 7383 reassembly, deep AH analysis, TCP/4500 encapsulation, any REST API, Docker, or the LLM narrative layer.

If a phase seems to need one of these, it doesn't. Ask.

---

## 8. Phase report template

Write to `reports/phase-N.md` at the end of every phase. A reviewing model reads this **without** seeing the conversation, so it must stand alone.

```markdown
# Phase N — <name>

## Summary
Two or three sentences: what now exists that did not before.

## Files
| File | Added/Changed | LOC | Purpose |

## Built
Bullet per item in the phase's Build list, each marked done / partial / not done.

## Tests
- Count, and how to run them.
- Test group names and what each covers.
- Explicit mapping: each acceptance criterion → the test that proves it.
- Anything untested and why.

## Invariant compliance
One line per invariant in §2: PASS/FAIL plus the file:line where it is enforced
or the reason it does not apply to this phase.

## Deviations from spec
Anything built differently from this document, with the reason. "None" is a
valid answer and should be the usual one.

## Refused
Things I was tempted to do, or that would have been easier, but that an
invariant forbade. Include near-misses — a tolerance I nearly added, a
constant I nearly inferred, a dissector I nearly wrote. This section is for
the reviewer's benefit; an empty section on a hard phase is suspicious.

## Known gaps
What does not work yet, what abstains, what is deferred to a later phase.

## Open questions
Anything needing a human decision before the next phase.
```

---

## 9. Refusal list

Push back and ask rather than doing any of these:

- Writing an ISAKMP or IKE dissector by hand.
- Inferring an IV, ICV or block-size constant not present in `constants.py`.
- Adding tolerance, rounding or a nearest-match fallback to the GCD estimator.
- Adding a heuristic that fires when a deterministic estimator abstains.
- Attaching a confidence below 1.0 to an `OBSERVED` claim, or any value to a `NOT_OBSERVABLE` one.
- Modifying `claims.py` or `constants.py` after Phase 0.
- Making `rank()` return a `CandidateSet`.
- Changing a test assertion to match what the code produced.
- Adding a dependency not in §3.
- Introducing async, threading or streaming.
- Making a network call at runtime.
- Building anything in §7.
