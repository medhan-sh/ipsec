# Task — make the ESP granularity estimator say *why* it abstained

Read `context.md` first (current state of the whole project: what is built,
the invariants, how to run it). Then `CLAUDE.md` (invariants, restated),
and `MVP_BUILD_PROMPT.md` §8 (the phase-report template you must write at
the end). `ARCHITECTURE.md` is authoritative on layout/layering.

Baseline before you touch anything: `make test` → `540 passed`.

---

## The problem

`estimate_granularity()` in
`src/ipsec_analyzer/inference/esp_constraints/gcd_estimator.py` abstains for
two structurally different reasons and returns bare `None` for both,
discarding the distinction it already computed:

```python
if len(distinct) < MIN_DISTINCT_VALUES:   # branch A
    return None
...
if g not in VALID_GRANULARITIES:          # branch B
    return None
```

Its one caller, `_granularity_channel()` in
`src/ipsec_analyzer/inference/esp_constraints/engine.py` (~line 199), can
therefore only emit a single disjunctive caveat:

> "GCD of pairwise E differences did not land in {4, 8, 16}, **or** fewer
> than 8 distinct E values were observed — possible TFC padding or
> insufficient data; not interpolated or rounded to the nearest valid
> granularity"

## Why this matters (this is not cosmetic)

The two branches need *opposite* remediation advice, and the report is
about to start printing that advice:

| Branch | Meaning | Correct advice |
|---|---|---|
| TFC gate fired (already distinct, leave alone) | one length dominates near MTU | padding is deliberate; size arithmetic will never work on this flow |
| **A** — fewer than `MIN_DISTINCT_VALUES` distinct lengths | not enough traffic diversity | **re-capture the same tunnel with mixed-size/bulk traffic** — this becomes answerable |
| **B** — GCD computed but landed off-lattice (1, 2, 3, 5…) | residue structure is inconsistent | **re-capturing may not help** — suggests TFC the gate missed, two tunnels merged under one SPI grouping, or an encapsulation-stripping bug |

Today a report cannot tell A from B, so it would confidently give branch-B
captures the branch-A advice. Fixing the estimator is what makes that
advice safe to print at all.

## What to build

Change `estimate_granularity()` to return a small frozen result carrying:

- the granularity (`int`) or `None`,
- which branch it took, from a **closed vocabulary** (validate it — the
  same standard `rules/schema.py` applies to `gap_kind` and condition `op`),
- the observed distinct-length count,
- the raw GCD when one was actually computed (branch B), `None` otherwise.

Then have `_granularity_channel()` build a **specific** caveat per branch,
naming the observed numbers. Branch A should read roughly:
`"only N distinct ESP payload lengths observed; at least 8 are needed for
a GCD estimate"`. Branch B should name the raw GCD it rejected and say
plainly that it was not rounded to the nearest valid granularity.

**Do it as one function with one set of branches.** Do *not* keep the
current signature and add a separate `diagnose()` helper — that duplicates
the branch logic, the two copies can drift, and the report then explains an
abstention that didn't happen. (`tests/test_tier_sync.py` exists in this
repo precisely because duplicated knowledge in two files drifted once.)

## Invariants — check each explicitly in the report

- **#6** (a failing deterministic estimator returns `NOT_OBSERVABLE`) —
  must stay true. You are enriching *why* it abstained. Do not add a
  tolerance, a nearest-match, or a fallback. If you feel tempted to return
  a "best guess" alongside the reason, that is the invariant talking.
- **#3** (`NOT_OBSERVABLE` carries no value) — `Claim.value` stays `None`.
  The diagnostics go in `caveats`. **Do not** put the distinct-length count
  into `value` because it happens to be data you now have.
- **#7** (never weaken a test) — the existing test asserting the old caveat
  string will fail. That is a legitimate contract change: update it and
  argue it in the report's Deviations section. Do not silently edit the
  assertion.
- `core/claims.py`, `core/candidates.py`, `core/constants.py` are frozen.
  This change needs none of them — `caveats` already exists on `Claim`.

## Scope — do not wander

- Touch `gcd_estimator.py`, `engine.py`'s `_granularity_channel`, their
  tests, and the golden fixture. Nothing else.
- **Do not** change the report template or `cli.py`. The caveat already
  renders in today's HTML, so this pass improves the existing report with
  zero template work. The report/UX redesign is a separate follow-up.
- **Do not** change the TFC-gate branch's caveat — it is already specific.
- **Do not** change `confidence=0.0` on the abstention `Claim`s. That is
  existing behaviour, normalised to `null` at serialisation time in
  Phase 6b. Out of scope here.
- Do not start any `[T]`/team-scope work (see `context.md` §10).

## Tests

- One test per branch, asserting the branch tag *and* the numbers that
  appear in the caveat.
- A test that the closed vocabulary rejects an unknown branch value.
- A real-capture test. `captures/weberblog_ikev2.pcap` is expected to hit
  branch A — **observe the actual distinct-length count and assert that
  observed number.** Do not assume it is 2; `captures/FETCH.md` describes
  distinct *wire* lengths, which is not necessarily what the estimator
  sees after the 8-byte SPI+sequence header is subtracted. Run it, read
  the number, then write the assertion.
- Keep the existing all-44-suites coverage passing unchanged.

## Finishing

1. `make test` — paste the **verbatim** final line into the report. This
   project's rule is observe and paste, never estimate.
2. Regenerate `tests/fixtures/golden_findings.json` (the caveat text
   legitimately changes) and verify it is byte-identical across three
   container runs with three different `PYTHONHASHSEED` values before
   committing it — the discipline established in `reports/phase-6a.md`
   and repeated in `6b`/`6c`.
3. Write `reports/phase-6d.md` to the template in `MVP_BUILD_PROMPT.md` §8.
   The **Refused** section is not optional — record the near-misses,
   especially anything that tempted you toward returning a value alongside
   an abstention.
4. Update `context.md` if anything in it is now stale.
