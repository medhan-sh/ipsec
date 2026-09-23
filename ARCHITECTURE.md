# IPsec Analyzer — Architecture and Scaffold

Companion to **PRD v3** and **MVP_BUILD_PROMPT.md**. This document is authoritative for
repository layout, layering and the contracts between components. Where it disagrees
with a sketch elsewhere, this wins.

---

## 1. The shape of the thing

**The analyzer is a library.** The CLI is one consumer of it. The HTML report is another.
The web dashboard, when it exists, is a third. None of them are the product — the library is.

This is the single decision that lets six people work in parallel without collisions, and
it is the decision most likely to be quietly violated. The engine must never know that HTTP
exists. If `assessment/` ever imports from `output/`, the architecture has failed.

```
                    ┌──────────────────────────────────────────┐
                    │  FRONTENDS                               │
                    │  cli.py   report.html   web/ (React)     │
                    └───────────────────┬──────────────────────┘
                                        │  findings.json
                    ┌───────────────────▼──────────────────────┐
                    │  ASSESSMENT — what it means              │
                    │  policy engine · verdict lifting ·        │
                    │  scoring · coverage                       │
                    └───────────────────┬──────────────────────┘
                                        │  ClaimLedger
                    ┌───────────────────▼──────────────────────┐
                    │  INFERENCE — what the wire implies       │
                    │  notify posture · ESP constraints ·       │
                    │  control plane · fingerprint · classifier │
                    └───────────────────┬──────────────────────┘
                                        │  PacketRecord[] + IkeExchange[]
                    ┌───────────────────▼──────────────────────┐
                    │  PROTOCOL — what the wire says           │
                    │  ingest · demux · ike_parse · sa_graph    │
                    └───────────────────┬──────────────────────┘
                                        │
                    ┌───────────────────▼──────────────────────┐
                    │  CORE — the spine, imported by all       │
                    │  claims · candidates · ledger · constants │
                    └──────────────────────────────────────────┘
```

**Dependency rule: imports point downward only.** `core` imports nothing from the project.
`protocol` imports only `core`. `inference` imports `core` and `protocol`. `assessment`
imports `core` and reads a `ClaimLedger` — it never touches packets. `output` imports
nothing but the findings document.

Enforce this with a test that walks the import graph. It is worth the twenty lines.

---

## 2. Tech stack

### MVP (week one, solo)

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | tshark integration, scapy, and the ML ecosystem all live here |
| pcap reading | `scapy` | Handles pcapng natively, forgiving API. Slow on large files — irrelevant for the few-MB public captures |
| IKE dissection | `tshark -T json` via `subprocess` | Never hand-roll a dissector. Call tshark directly, **not** pyshark — pyshark wraps it in an async layer that is flaky and hides errors |
| Policy rules | `pyyaml` | Rules are data, not code |
| Report | `jinja2` | One self-contained HTML file |
| Tests | `pytest` | — |
| Data modelling | stdlib `dataclasses` | `claims.py` is already dataclasses; do not introduce a second validation system in week one |
| Storage | none — JSON on disk | A database in week one is pure cost |

That is the entire MVP dependency list. Anything else needs a reason.

### Added later, by the team

| Component | Choice | Phase | Notes |
|---|---|---|---|
| API | FastAPI | Week 3 | Same process as the engine, no IPC. Pydantic arrives with it — that is the right moment, not before |
| Frontend | React + Vite | Week 3 | Reads `findings.json`, nothing else |
| SA graph viz | React Flow or Cytoscape.js | Week 3 | The SA state machine is a real graph; do not draw it with a chart library |
| Classifier | LightGBM | Week 2 | Plus `scikit-learn` for calibration and the conformal wrapper |
| Feature extraction | `numpy`, `pandas` | Week 2 | Arrives with the classifier, not before |
| Testbed | strongSwan, libreswan, network namespaces, `tc netem` | Week 1, parallel | Owned by two people from day zero |
| Ground truth | `ip xfrm state` / `ip xfrm policy` dumps | Week 1, parallel | Part of the testbed |
| History (optional) | SQLite | Week 4 | Only if multi-capture comparison is wanted. Not Postgres |

**Deliberately not used:** pyshark, Docker for the MVP, any message queue, any ORM,
Celery, Redis, GraphQL, a component library. Each of these is a day you do not have.

---

## 3. CLI or dashboard?

**Both, eventually. CLI and a static report for the MVP.**

For week one the deliverable is `ipsec-analyze capture.pcap -o report.html` producing one
self-contained HTML file. No server, no build step, no frontend.

The reasoning is not only time. A static report is genuinely the better artifact for several
of the things you need: it opens with no network, it attaches to a submission, it cannot fail
on stage, and a reviewer can keep it. Real security tooling ships both a report and a console
for exactly this reason — the report is not a stepping stone to the dashboard, it is a
permanent deliverable that outlives it.

The problem statement does name an interactive dashboard, so the team builds one in week three.
Because the engine is a library emitting `findings.json`, that work touches nothing you wrote.
The dashboard is a React app reading a JSON document. It cannot break the analyzer, and the
analyzer cannot break it.

**What the dashboard adds that the report cannot:** live mode, the interactive SA state machine,
drill-down into individual frames, and comparing captures. Everything else the static report
already does.

---

## 4. Complete scaffold

`[MVP]` = week one, solo. `[T]` = team, later. Directories with no marker are structural.

```
ipsec-analyzer/
├── pyproject.toml                      [MVP]
├── README.md                           [MVP]
├── CLAUDE.md                           [MVP]  invariants, restated for the agent
├── ARCHITECTURE.md                     [MVP]  this file
├── PRD.md                              [MVP]  exported from the doc
├── MVP_BUILD_PROMPT.md                 [MVP]
├── .gitignore                          [MVP]  captures/, *.pcap, __pycache__, .venv
│
├── src/ipsec_analyzer/
│   │
│   ├── core/                           ── THE SPINE. Frozen after Phase 0.
│   │   ├── claims.py                   [MVP]  Tier, Claim, TierPromotionError
│   │   ├── candidates.py               [MVP]  CandidateSet, eliminate(), rank()
│   │   ├── ledger.py                   [MVP]  ClaimLedger — collection + query
│   │   └── constants.py                [MVP]  SuiteFraming table, DH groups, notify types
│   │
│   ├── protocol/                       ── LAYER 1: what the wire says
│   │   ├── records.py                  [MVP]  PacketRecord dataclass
│   │   ├── ingest.py                   [MVP]  pcap/pcapng → PacketRecord[]
│   │   ├── demux.py                    [MVP]  route by port / IP proto
│   │   ├── ike_parse.py                [MVP]  tshark -T json wrapper → IkeExchange[]
│   │   └── sa_graph.py                 [T]    SA reconstruction, rekey lineage
│   │
│   ├── inference/                      ── LAYER 2: what the wire implies
│   │   ├── notify_posture.py           [MVP]  F3b — differentiator 1
│   │   ├── esp_constraints/            [MVP]  F6b — differentiator 2
│   │   │   ├── engine.py               [MVP]  orchestrates the three below
│   │   │   ├── gcd_estimator.py        [MVP]  alignment granularity
│   │   │   ├── anchor_solver.py        [MVP]  ICV via TCP pure-ACK anchor
│   │   │   └── tfc_gate.py             [MVP]  detect padding, hard-gate to NOT_OBSERVABLE
│   │   ├── control_plane.py            [T]    PFS, auth method, mode, rekey
│   │   ├── fingerprint/                [T]
│   │   │   ├── vendor_id.py            [T]    exact MD5 prefix lookup + version parse
│   │   │   ├── structural.py           [T]    TAVO ordering, fuzzy fallback
│   │   │   └── vendor_ids.yaml         [T]    from the ike-scan database
│   │   └── classifier/                 [T]
│   │       ├── features.py             [T]    windowed, cipher-normalised
│   │       ├── model.py                [T]    LightGBM
│   │       └── conformal.py            [T]    clustered conformal — see PRD
│   │
│   ├── assessment/                     ── LAYER 3: what it means
│   │   ├── engine.py                   [MVP]  rule evaluation, coverage gaps
│   │   ├── verdict.py                  [MVP]  verdict lifting over candidate sets
│   │   ├── scoring.py                  [T]    risk / coverage / confidence scores
│   │   └── rules/
│   │       ├── schema.py               [MVP]  rule dataclass + validation
│   │       └── rules.yaml              [MVP]  15 rules for the MVP
│   │
│   ├── output/                         ── LAYER 4: how it is shown
│   │   ├── findings.py                 [MVP]  ClaimLedger → findings.json
│   │   ├── report.py                   [MVP]  findings.json → HTML
│   │   └── templates/
│   │       └── report.html.j2          [MVP]
│   │
│   ├── synth/                          ── test oracles, not shipped logic
│   │   ├── synth_esp.py                [MVP]  RFC 4303 framing generator
│   │   └── synth_ike.py                [MVP]  IKE_SA_INIT builder
│   │
│   └── cli.py                          [MVP]
│
├── tests/
│   ├── conftest.py                     [MVP]
│   ├── test_import_graph.py            [MVP]  enforces the dependency rule
│   ├── core/
│   │   ├── test_claims.py              [MVP]  no-promotion, tier invariants
│   │   └── test_candidates.py          [MVP]  eliminate/rank asymmetry
│   ├── synth/
│   │   ├── test_synth_esp.py           [MVP]  worked cases + round-trip property
│   │   └── test_synth_ike.py           [MVP]
│   ├── inference/
│   │   ├── test_notify_posture.py      [MVP]  four states × four severities
│   │   └── test_esp_constraints.py     [MVP]  all suites, TFC, degenerate inputs
│   ├── assessment/
│   │   ├── test_engine.py              [MVP]
│   │   └── test_verdict.py             [MVP]  unanimous / split / weak-family
│   └── integration/
│       └── test_end_to_end.py          [MVP]  against public captures
│
├── captures/                           gitignored — public pcaps
│   └── FETCH.md                        [MVP]  URLs + sha256 of each test capture
│
├── reports/                            phase reports for review
│   └── phase-N.md
│
├── testbed/                            [T]    owned by 2 people, starts day 0
│   ├── configs/                        [T]    swanctl.conf per configuration
│   ├── provision.sh                    [T]    netns + strongSwan setup
│   ├── capture.sh                      [T]    tcpdump + traffic generation
│   ├── groundtruth.sh                  [T]    ip xfrm state/policy dumps
│   └── matrix.yaml                     [T]    the configuration matrix
│
└── web/                                [T]    week 3
    ├── package.json                    [T]
    ├── vite.config.ts                  [T]
    └── src/                            [T]    reads findings.json, nothing else
```

---

## 5. The contracts between layers

Four data shapes connect everything. Get these right and the parallel work composes.

### Protocol → Inference

```python
@dataclass(frozen=True)
class PacketRecord:
    frame_no: int           # 1-indexed, matches Wireshark
    ts: float               # epoch seconds
    src: str                # IP, family-agnostic string
    dst: str
    proto: int              # IP protocol number
    sport: int | None
    dport: int | None
    payload_len: int        # transport payload, UDP header already subtracted
    raw_offset: int         # byte offset into the capture, for evidence
```

`IkeExchange` carries the tshark-parsed tree plus the frame numbers it came from.
Inference modules never touch raw bytes — they read `PacketRecord` and `IkeExchange`.

### Inference → Assessment

A `ClaimLedger`: a collection of `Claim`s plus the `CandidateSet`s, queryable by dotted
field path. The assessment layer asks it questions (`ledger.get("ike_sa.dh_group")`) and
receives a `Claim` whose tier decides whether a rule may fire or must emit a gap.

### Assessment → Output

`findings.json` — the parallelization contract, and the thing the dashboard team codes
against before the dashboard exists.

```json
{
  "schema_version": "1.0",
  "capture": {
    "filename": "ikev2-decrypt-aes128ccm12.pcap",
    "sha256": "...",
    "packet_count": 142,
    "duration_s": 3.71,
    "truncated": false
  },
  "coverage": { "checks_total": 15, "checks_assessable": 11, "checks_gap": 4 },
  "claims": [
    {
      "field": "ike_sa.dh_group",
      "value": 19,
      "tier": "OBSERVED",
      "confidence": 1.0,
      "method": "tshark.isakmp.transform",
      "evidence": [3],
      "caveats": []
    }
  ],
  "candidate_sets": [
    {
      "sa_id": "spi:0x1a2b3c4d",
      "universe_size": 41,
      "surviving": ["AES-128-GCM-12", "AES-128-CCM-12", "AES-128-CTR+HMAC-SHA1-96"],
      "eliminated": [
        ["AES-128-CBC + HMAC-SHA1-96", "GCD of length differences = 4, implies 4-byte pad granularity; CBC requires 16"]
      ],
      "indistinguishable": [["AES-128-GCM-12", "AES-128-CCM-12"]]
    }
  ],
  "findings": [
    {
      "rule_id": "esp.truncated_icv",
      "severity": "MEDIUM",
      "category": "integrity",
      "title": "Truncated 96-bit integrity check value",
      "detail": "...",
      "tier": "INFERRED_SIDE_CHANNEL",
      "evidence": [17, 19, 23],
      "references": ["RFC 8221 §5"],
      "recommendation": "Review the negotiated integrity algorithm against ..."
    }
  ],
  "gaps": [
    {
      "rule_id": "esp.anti_replay",
      "reason": "Receiver-side policy; the sequence number is present regardless of enforcement",
      "required_tier": "OBSERVED",
      "actual_tier": "NOT_OBSERVABLE"
    }
  ],
  "verdicts": [
    {
      "predicate": "confidentiality_acceptable",
      "outcome": true,
      "confidence": 1.0,
      "basis": "All 3 surviving candidates are >=128-bit AEAD or equivalent"
    }
  ]
}
```

Freeze `schema_version` 1.0 at the end of MVP Phase 6 and hand it to the dashboard team.
They can build against a hand-written fixture before the engine produces a real one.

---

## 6. Who builds what

With six people and the contracts above, four workstreams run in parallel after week one.

| Stream | People | Starts | Depends on |
|---|---|---|---|
| Deterministic core (MVP) | you, 1 | now | nothing |
| Testbed + ground truth | 2 | **today** | nothing |
| Classifier | 1–2 | week 2 | testbed only |
| Fingerprint DB + CVE | 1 | week 2 | `core` contracts only |
| Dashboard | 1 | week 3 | `findings.json` schema only |

The testbed starting today is the important one. It is the longest pole in the whole project,
it blocks the classifier entirely, and it depends on nothing you are building. Every day it
does not start is a day added to the end.

---

## 7. Things that will be tempting and are wrong

**Putting the engine behind an API in week one.** Costs a day, buys nothing, and creates a
serialisation boundary you then have to maintain through every refactor.

**Building the dashboard before `findings.json` is frozen.** The schema will move, and the
frontend will be rewritten. Freeze the contract first, then build against it.

**Letting `assessment/` read packets.** It happens gradually — one rule needs "just the
timestamp" — and then the policy engine cannot be tested without a capture. Rules read the
ledger. Always.

**A shared `utils.py`.** It becomes a dependency cycle within a fortnight. Put helpers in the
layer that owns them.

**Making `rank()` symmetric with `eliminate()`.** See the build prompt. The asymmetry is the
architecture.
