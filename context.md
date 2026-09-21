# context.md — current state of the IPsec Analyzer project

Written 2026-09-21 from the repository as it stands: the PRD
(`Passive IPsec VPN Protocol Analysis Platform — PRD v3.pdf`),
`MVP_BUILD_PROMPT.md`, `ARCHITECTURE.md`, `CLAUDE.md`, the eleven phase
reports in `reports/`, and the source tree itself. Test state below was
observed by running `make test`, not estimated.

**Read this first, then the specific document you need.** This file is a
map, not a replacement for the four authoritative documents. Where it
disagrees with `ARCHITECTURE.md` (layout/layering) or
`MVP_BUILD_PROMPT.md` (build order/acceptance), those win.

> ⚠️ `reports/PROJECT_STATUS.md` is **stale**. It describes the project
> as of Phase 3 ("three of seven phases done, 323 tests, no way to point
> it at a real .pcap"). All of that has since been superseded — Phases 4,
> 5, 5a, 6, 6a, 6b and 6c are complete. Treat this file as the current
> status and `PROJECT_STATUS.md` as a historical snapshot.

---

## 1. One-paragraph summary

`ipsec-analyzer` is a command-line tool that reads an IPsec (IKEv2/ESP)
packet capture and produces a security assessment report — **without
decrypting anything and without touching the network**. It dissects the
plaintext IKE handshake through `tshark -T json`, infers what it can
about the ESP data-plane cipher from packet-size arithmetic alone,
evaluates 15 declarative policy rules against the result, and writes a
self-contained HTML report plus a `findings.json` document. Every fact it
reports carries a provenance tier saying how it was obtained. **The MVP
is complete and working end to end**; everything remaining is explicitly
team/later (`[T]`) scope that must not be started without being asked for
by name.

## 2. The three ideas the design rests on

From the PRD, restated in `MVP_BUILD_PROMPT.md` §1:

1. **Provenance.** Every value is a `Claim` carrying a tier, confidence,
   method, evidence frames and caveats. The report shows which is which;
   the policy engine knows which tier it is allowed to act on.
2. **Elimination before ranking.** Evidence either *eliminates*
   candidates (hard, reproducible — framing arithmetic, plaintext fields)
   or *ranks* survivors (soft priors — fingerprints, models). Never both.
   A ranking can never resurrect an eliminated candidate. Enforced
   structurally: `rank()` cannot return a `CandidateSet`.
3. **Verdict lifting.** IKEv2 hides the ESP cipher and some suites are
   provably indistinguishable on the wire. Rather than guess, narrow to a
   candidate set and evaluate the *risk question* across the whole set.
   Unanimity → a confident verdict without naming the cipher.
   Disagreement → `verdict_ambiguous` naming both sides.

## 3. The eight invariants (from `CLAUDE.md` / build prompt §2)

Enforced in code, not by discipline. Violating one is a bug even if tests
pass.

1. No tier promotion (`Claim.__post_init__` raises `TierPromotionError`).
2. `OBSERVED` means confidence exactly 1.0.
3. `NOT_OBSERVABLE` carries no value — absence, not low confidence.
4. Never hand-roll a protocol dissector — IKE goes through `tshark -T json`.
5. Framing constants are never invented — every one lives in
   `core/constants.py` with its RFC section.
6. A failing deterministic estimator returns `NOT_OBSERVABLE` — never a
   fallback heuristic or loosened tolerance.
7. Never weaken a test to make it pass.
8. No new runtime dependencies without asking. Approved: scapy, pyyaml,
   jinja2, pytest, tshark (subprocess).

Plus: no async/streaming, no network calls at runtime ever,
`core/{claims,candidates,constants}.py` frozen (changes require asking).

## 4. Status: what is built

| Phase | Name | Status |
|---|---|---|
| 0 | Scaffold + frozen contracts (`Claim`, `CandidateSet`, 44-suite framing table) | ✅ |
| 1 | Synthetic oracles (`synth/`) | ✅ |
| 2 | Notify posture / downgrade exposure — F3b | ✅ |
| 3 | ESP constraint engine — F6b | ✅ |
| 4 | Real capture path (`protocol/`, 12 real captures) | ✅ |
| 5 | Policy engine + verdict lifting (`assessment/`) | ✅ |
| 5a | Correctness pass before Phase 6 (6 fixes) | ✅ |
| 6 | Report + CLI (`output/`, `cli.py`, `findings.json` schema 1.0) | ✅ |
| 6a | Closeout verification, golden fixture, README | ✅ |
| 6b | Report output fix pass (negative claims, `PassedCheck`, transform names) | ✅ |
| 6c | Packaging + CLI ergonomics (`./ipsec-analyze`, `Makefile`, baked image) | ✅ |
| 6d | GCD estimator abstention-reason pass (`gcd_estimator.py` returns *why*, not bare `None`) | ✅ |

`MVP_BUILD_PROMPT.md` names no phase beyond 6. Phases 5a/6a/6b/6c/6d were
review-driven correctness passes, not new scope.

**Tests: `544 passed in 12.21s`** — observed by running `make test` on
2026-09-21 (Phase 6d), up from 540 in `reports/phase-6c.md`'s figure (4
new tests for the GCD abstention-reason split — see `reports/phase-6d.md`).

Source: ~4,100 LOC across `src/ipsec_analyzer/`; ~3,600 LOC of tests.

## 5. How to run it

Docker is the canonical environment and is now invisible behind two entry
points (Phase 6c). The image bakes the package in at build time — it is
**no longer mounted at runtime**.

```bash
./ipsec-analyze captures/weberblog_ikev2.pcap   # builds image on first use, then analyses
make test                                       # rebuilds image, runs full suite
make build                                      # just (re)build the image
make clean                                      # remove generated reports
```

A flagless run writes both outputs beside the capture:
`<name>.report.html` and `<name>.findings.json`. `-o` / `--json` override
each independently; both must resolve under `$PWD` (the wrapper refuses
otherwise, because the container can only see `$PWD` and `--rm` would
silently discard anything written elsewhere).

**Gotcha:** `./ipsec-analyze` auto-builds only when the image is
*missing*, never when source has changed. After editing source, run
`make build` before `./ipsec-analyze`, or use `make test` (which always
rebuilds).

Image: `python:3.11-slim` + TShark pinned to `4.4.18-0+deb13u1` via a
`TSHARK_VERSION` build arg (tshark's JSON shape varies across releases).
Docker was originally adopted because this host's Homebrew toolchain is
broken for compiled C-extension packages on macOS 26; the revised build
prompt has since made it canonical regardless.

## 6. Architecture as built

```
src/ipsec_analyzer/
├── core/          THE SPINE — frozen. Imports nothing project-local.
│   ├── claims.py       Tier, Claim, TierPromotionError            (60 LOC)
│   ├── candidates.py   CandidateSet, eliminate(), rank()          (53)
│   ├── constants.py    44 SuiteFraming entries, DH groups,
│   │                   notify types, weak IKE transform IDs      (285)
│   └── ledger.py       ClaimLedger — collection + query           (66)
├── protocol/      LAYER 1: what the wire says
│   ├── records.py      PacketRecord                               (37)
│   ├── ingest.py       scapy pcap/pcapng → PacketRecord[]         (96)
│   ├── demux.py        port/proto routing, NAT-T marker,
│   │                   SPI grouping, ah.detected claim           (206)
│   ├── ike_parse.py    tshark JSON → IkeMessage[], IKE SA claims (573)
│   └── coverage.py     CaptureCoverage incl. tshark_version       (66)
├── inference/     LAYER 2: what the wire implies
│   ├── notify_posture.py      F3b — downgrade exposure           (283)
│   ├── pipeline.py            the single real-capture→inference
│   │                          adapter (shared by tests and cli)   (75)
│   └── esp_constraints/       F6b
│       ├── gcd_estimator.py   padding granularity via GCD,
│       │                      returns why it abstained (Phase 6d) (103)
│       ├── tfc_gate.py        TFC detection → hard abstain        (38)
│       ├── anchor_solver.py   ICV length via TCP pure-ACK anchor (117)
│       └── engine.py          orchestration + NULL-ENC channel   (425)
├── assessment/    LAYER 3: what it means
│   ├── engine.py       evaluate_rules → Finding/PassedCheck/
│   │                   CoverageGap + coverage counts
│   ├── verdict.py      lift_verdict, confidentiality_acceptable,
│   │                   integrity_acceptable                      (195)
│   └── rules/          schema.py (closed eq/in/intersects
│                       condition language, no eval) + rules.yaml (15 rules)
├── output/        LAYER 4: how it is shown — imports NOTHING project-local
│   ├── findings.py     dict assembly → findings.json (schema 1.0) (58)
│   ├── report.py       findings.json → HTML                      (103)
│   └── templates/report.html.j2   inline CSS, zero JS, zero network
├── synth/         test oracles, not shipped logic (RFC 4303 framing generator,
│                  IKE_SA_INIT builder) — production code never imports this
└── cli.py         the composition root: every typed→dict conversion (352)
```

**The layering rule**, enforced by `tests/test_import_graph.py`:
`core` → nothing; `synth` → `core` only; `inference` → `core` +
`protocol`; `assessment` → `core`; `output` → **nothing project-local**
(that is why `report.py` duplicates `Tier`'s member names as strings,
kept honest by `tests/test_tier_sync.py`). `cli.py` is the only place the
layers meet.

## 7. What the analysis actually does

**IKE side (F3b, Phase 2 + 4).** `tshark` dissects IKE_SA_INIT. The tool
extracts SA parameters (encryption/integrity/PRF/DH transform IDs,
resolved to IANA names since Phase 6b) and answers three questions from
notify presence: downgrade protection state (notify 16447, a four-state
lattice — protection requires **both** peers, and the responder sends it
unconditionally, so a boolean check would pass a half-protected tunnel),
hybrid post-quantum deployment (16441), and PPK use (16445/16446). When
downgrade protection is incomplete it grades exposure by reason
(hybrid-PQ > mixed-strength DH groups > any weak group > none). If the
capture lacks one half of IKE_SA_INIT, the answer is `NOT_OBSERVABLE` —
a *positive* observation from the captured half still counts, a
*negative* conclusion needs both.

**ESP side (F6b, Phase 3 + 4).** Packet sizes leak framing structure.
`tfc_gate` runs first and hard-gates everything to `NOT_OBSERVABLE` if
traffic-flow-confidentiality padding is present. `gcd_estimator` takes
the GCD of pairwise length differences — a clean 4, 8 or 16 with ≥8
distinct lengths, or abstention, never a nearest match. `anchor_solver`
finds the modal small reverse-direction packet in a unidirectional burst
(a TCP pure ACK at 40 or 52 bytes), and solves exactly for ICV length;
both anchor sizes are kept if both are plausible. `engine.py` runs these
as `eliminate()` calls with a recorded plain-English reason per removal,
plus a NULL-cipher channel that inspects actual ciphertext prefix bytes
(NULL-ENC otherwise survives size arithmetic on nearly every real
capture by coincidence, which would both poison every "all survivors are
strong" verdict and falsely flag every capture).

**Assessment (F9, Phase 5).** 15 YAML rules, each with `id`, `target`,
`min_tier`, `condition`, `severity`, `category`, `gap_kind`,
`references`, `recommendation`, `title`. Each rule yields exactly one of:
a `Finding` (assessable and fired), a `PassedCheck` (assessable and
clean — added in 6b, so a clean capture doesn't render as an empty
table), or a `CoverageGap` (`min_tier` unmet). Headline: "15 rules total
— X found, Y passed, Z gaps". `verdict.py` lifts
`confidentiality_acceptable` / `integrity_acceptable` across each
surviving candidate set.

**Output (F11 subset, Phase 6).** `findings.json` at frozen
`schema_version: "1.0"`, and one HTML file with no `<script>`, no
`<link>`, no `http(s)://` reference anywhere — collapsible sections use
`<details>`. Tier colour-coding with a legend; every finding's evidence
frame numbers are in-page anchors into a frame-evidence index; candidate
sets rendered as sets with `indistinguishable` groups called out
explicitly.

**Reference result** (`captures/weberblog_ikev2.pcap`): `15 rules total
— 0 found, 11 passed, 4 gaps`; four ESP tunnels each at `42 of 44`
surviving suites (this capture's ping traffic has only **1** distinct
post-header ESP payload length per tunnel — real, but too uniform for a
positive identification, and the tool correctly abstains rather than
guessing; the estimator's caveat now says so explicitly:
`estimate_granularity()`'s `insufficient_distinct_values` branch, see
`reports/phase-6d.md`). Note: `captures/FETCH.md` and two pre-existing
test comments (`tests/test_cli.py`, `tests/integration/test_end_to_end.py`)
say "2 distinct wire lengths" — that was never re-verified against what
the estimator actually sees after the 8-byte SPI+sequence header is
subtracted, and Phase 6d's own real-capture test found it to be 1, not 2.
Left uncorrected in those files (out of Phase 6d's scope); worth a small
follow-up.

## 8. Test data

12 captures in `captures/` (gitignored; `captures/FETCH.md` is the
tracked URL+sha256 manifest with reproduction commands):

- **6 Wireshark IKEv2 decrypt vectors** — ground truth in the filename
  (AES-128-CCM-12, 3DES-SHA1, AES-192-CTR, AES-256-CBC, AES-256-GCM-16,
  AES-256-GCM-8). All six are handshake-only: **zero ESP packets**, so
  they prove IKE SA extraction, not candidate sets.
- **3 locally derived truncation fixtures** from the GCM-16 capture —
  a between-frames cut, an `editcap -s 100` snaplen cut, and one with the
  IKE_SA_INIT *response* excised (the only fixture that drives
  `assess_notify_posture` with exactly one real half).
- **`ipsec_multi_algo_natt.pcapng`** — real NAT-T (UDP/4500) with three
  sequential Child SAs; too few distinct sizes per SA for a positive ID.
- **`weberblog_ikev1.pcap` / `weberblog_ikev2.pcap`** — real
  firewall-to-firewall IPv6 sessions with hundreds of real ESP packets.
  These are what the build prompt's "the Palo Alto and Fortinet captures"
  means here; **the vendor attribution was never verified** against the
  capture data and the source post doesn't name them.
- **`weberblog_ikev2_midsession.pcap`** — derived, IKE_SA_INIT removed,
  for the mid-session-capture abstention criterion.
- **`http.pcap`** — non-IPsec negative case.

`tests/fixtures/golden_findings.json` pins the full document for
`weberblog_ikev2.pcap` and is verified deterministic across processes
with distinct `PYTHONHASHSEED` (building it caught a real cross-process
non-determinism bug in candidate-set serialization, fixed at source in
Phase 6a).

## 9. Known gaps and limitations (all disclosed, none hidden)

- **The 44-suite framing table has never been hand-checked line by line
  against the RFC texts.** Every entry is cited and marked
  `# VERIFY BY HAND`; the checklist is in `reports/phase-0.md`. This is
  the one place a wrong number would silently corrupt everything
  downstream.
- **No real capture has yet produced a positive ESP cipher
  identification** — every available capture is either handshake-only or
  too size-uniform. The engine is proven against synthetic oracles across
  all 44 suites and correctly abstains on all real data so far.
- **PFS and anti-replay are permanent coverage gaps.** Anti-replay is
  structurally unobservable (receiver-side policy); PFS is
  `not_implemented` — this MVP doesn't parse CREATE_CHILD_SA. The
  `gap_kind` vocabulary distinguishes the two honestly.
- **Mixed-outcome-per-rule simplification**: a rule matching several
  claims (multi-tunnel) counts once for the headline; a rule that both
  fires and passes across different tunnels resolves to one outcome.
  Disclosed in `reports/phase-6b.md`.
- **`./ipsec-analyze` does not detect a stale image** (see §5).
- **The `--user` uid/gid mapping is verified at the mechanism level
  only**, never on a real Linux host (this machine is macOS).
- **No IKEv1 SA-parameter extraction, no RFC 7383 reassembly, no deep AH
  analysis, no TCP/4500, no live capture.**
- `findings.json` deviates from `ARCHITECTURE.md` §5's sketch in exactly
  one direction: `detail` was removed (it never carried independent
  content); `Finding.scope`, `CoverageGap.gap_kind`, `Verdict.basis_tier`,
  `passes[]` and `coverage.tshark_version` were added.

## 10. Out of scope — do not build without being asked

`MVP_BUILD_PROMPT.md` §7 and `ARCHITECTURE.md`'s `[T]` markers. Do not
build, stub, or scaffold for:

lab testbed (F13) · ML traffic classifier (F7) · conformal prediction ·
SHAP · implementation fingerprint database (F8) · CVE lookup · SA graph /
rekey lineage (F4) · control-plane inference: PFS, auth method, mode,
rekey (F5) · `assessment/scoring.py` (F10) · interactive dashboard (F12) ·
live capture / replay-as-live · RFC 7383 reassembly · deep AH analysis ·
TCP/4500 · any REST API · the LLM narrative layer.

The PRD (v3, 31 pages) specifies F1–F13 for the full platform; this
repository implements the MVP slice: F1 (file only), F2, F3, **F3b**, F6b,
F9 and the technical half of F11. The two `[T]` subsystems that would
most change the product are F8 (fingerprinting — ranks only, never
eliminates) and F7 (classification — windowed, with an anti-leakage
protocol the PRD specifies in detail: grouped splits, excluded features,
four negative controls including a generator-identity probe, and
*clustered* conformal prediction because plain Mondrian starves the rare
classes).

## 11. Repository and process notes

- Branch `phase6`, main branch `main`, working tree clean at time of
  writing. Last commit `105df30 cli functionality`.
- **`reports/` is gitignored** (last line of `.gitignore`), so the eleven
  phase reports — the project's actual audit trail — exist only on disk,
  not in git history. Same for `captures/*` (except `.gitkeep` and
  `FETCH.md`).
- `ARCHITECTURE.md` expects a `PRD.md` exported from the doc; only the
  PDF is present, and it has no extractable text layer without
  CID/ToUnicode decoding (no `pdftotext` on this host).
- `conftest.py` is at the repo root, not `tests/` as the scaffold sketch
  shows; `pyproject.toml`'s `pythonpath = ["src"]` is what actually makes
  imports work under pytest.
- **Process discipline used throughout**, and worth continuing: every
  phase writes `reports/phase-N.md` to the template in
  `MVP_BUILD_PROMPT.md` §8, standing alone for a reviewer who never saw
  the conversation — including a mandatory **Refused** section (near
  misses: a tolerance nearly added, a constant nearly inferred, a
  dissector nearly written) and **Deviations**. Test counts are pasted
  from an observed run, never estimated.
