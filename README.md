# IPsec Analyzer

A passive, non-decrypting security assessment tool for IPsec (IKEv2/ESP)
packet captures. It reads a pcap/pcapng file, dissects the IKE handshake
via `tshark` and infers what it can about the ESP data-plane cipher from
packet sizes and timing alone, then checks the result against a fixed set
of policy rules and writes a self-contained HTML report plus a
`findings.json` document. Every fact it reports carries a provenance tier
saying how it was obtained, so a reader can tell an observed protocol
field apart from an inference and can't mistake either for a guess.

## Running it

Docker is the canonical environment (see `CLAUDE.md`/`MVP_BUILD_PROMPT.md`
for why: this project depends on a specific pinned `tshark` version, and
the host's own Python/tshark toolchain is not assumed to work) — but it's
an implementation detail, not something you need to think about. From a
fresh clone, with nothing built yet:

```bash
./ipsec-analyze captures/weberblog_ikev2.pcap
```

This builds the image the first time it's needed (every run after that
just uses it), analyses the capture, and writes both output files beside
it: `captures/weberblog_ikev2.report.html` (open it directly in a
browser — it needs no network access and no server) and
`captures/weberblog_ikev2.findings.json` (the same result as plain
data), printing both paths on success. `captures/your-capture.pcap` is
any pcap/pcapng file, anywhere under the current directory — see
`captures/FETCH.md` for how this project's own test captures were
obtained. `./ipsec-analyze --help` shows every flag, including `-o`/
`--json` to write the outputs somewhere else instead of the defaults.

On Linux, output files are written as your own user, not root — no
`sudo` needed to delete a report you just generated.

To run the test suite instead:

```bash
make test
```

## Provenance tiers

Every fact the tool reports is a `Claim` carrying one of five tiers,
ordered weakest to strongest. A rule engine result is only as trustworthy
as the weakest tier behind it, and the report always shows which tier
backs which value — nothing is presented as more certain than how it was
actually obtained.

| Tier | Meaning |
|---|---|
| `NOT_OBSERVABLE` | Not a weak claim — the absence of one. Either nothing on the wire could ever answer this question (e.g. whether the receiver enforces its anti-replay window), or this specific capture didn't contain enough to answer it (e.g. a truncated handshake, or too few ESP packets for a size-based estimator to reach a conclusion). Carries no value. |
| `ML_PREDICTION` | A statistical classifier's output. Defined in the tier lattice for a future phase; this MVP does not include a classifier and never produces a claim at this tier today. |
| `INFERRED_IMPLEMENTATION_DEFAULT` | Assumed from a common implementation default rather than derived from this capture's own traffic. Also defined in the lattice but not produced by any code path in this MVP today — reserved, not currently used. |
| `INFERRED_SIDE_CHANNEL` | Derived deterministically from packet sizes or timing — e.g. the ESP padding granularity recovered from the GCD of packet-length differences, or an integrity-check-value length recovered from a TCP ACK anchor. Exact given the observed data, but the underlying identification method (which packet is an ACK, which suites share a framing) is a heuristic, not a protocol guarantee, and any such caveat is attached to the claim itself. |
| `OBSERVED` | Read directly off the wire by `tshark`'s own dissector — an IKE transform ID, a notify payload's presence, an IP protocol number. Confidence is always exactly 1.0 at this tier; if it isn't certain, it isn't `OBSERVED`. |

## What this does not do

This tool never decrypts anything — ESP payloads are opaque ciphertext to
it throughout, and every ESP-side conclusion comes from packet sizes,
timing, and the small number of framing bytes (explicit IV, ICV) that
size arithmetic alone can expose, never from key material. It never
sends a packet, probes a live endpoint, or otherwise touches the network
it's analysing — it only reads a capture file someone already took. It
has no classifier, no fingerprint database, and no scoring model in this
MVP: findings come from a fixed, human-authored set of policy rules
checked against what was actually observed or inferred, not from a
trained model or a weighted risk score. It does not attempt IKEv1
Aggressive/Main Mode SA-parameter extraction, RFC 7383 message
reassembly, deep AH analysis, or live/replay capture — a truncated,
fragmented, or otherwise incomplete capture produces an explicit coverage
gap for whatever it couldn't determine, never a fabricated answer.
