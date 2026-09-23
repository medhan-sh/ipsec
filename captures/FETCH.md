# Test captures

Gitignored (per `.gitignore`); this file is the manifest ARCHITECTURE.md
calls for — URL and sha256 of each. Downloaded during Phase 4's build via
direct HTTP fetch; re-run the `curl`/`docker` commands below to reproduce
this directory from scratch.

## Wireshark test suite — IKEv2 decrypt vectors (ground truth in the filename)

Source: `https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/<name>`

| File | sha256 | Ground truth (from filename) |
|---|---|---|
| `ikev2-decrypt-aes128ccm12.pcap` | `46c7284a168ff3238c056f7229b78e28e7bd63e033cee533c17248b0685e2734` | AES-128-CCM-12 |
| `ikev2-decrypt-3des-sha1_160.pcap` | `ba93efc76b1abd2b9a5e633ed21daa16e35743c280e9174396bbc44c1f839a7a` | 3DES-CBC / HMAC-SHA1 |
| `ikev2-decrypt-aes192ctr.pcap` | `5251e0ed4a73d0aa1b18f043b8c91189a506e5d0ccba10200da35056be411589` | AES-192-CTR |
| `ikev2-decrypt-aes256cbc.pcapng` | `1a033591e44f3570fe99b36af0a0727e01b3076589611d2218f264caac326f40` | AES-256-CBC |
| `ikev2-decrypt-aes256gcm16.pcap` | `86505314cc2cbe68b1c4af270d099cab234e64595277bb572f18dfaab2654179` | AES-256-GCM-16 |
| `ikev2-decrypt-aes256gcm8.pcap` | `c2af503229fe6614c308da115987df42241ad934112889536c1bff68edf61e95` | AES-256-GCM-8 |

All six: IKE_SA_INIT + IKE_AUTH handshake only, no ESP data-plane traffic
captured. Used for the "IKE SA cipher/integrity/PRF/DH group extracted
correctly" acceptance criterion — all six were verified by hand to match
their filename's algorithm exactly (see `reports/phase-4.md`).

`ikev2-decrypt-aes256gcm16_truncated.pcap` (`4b3d1d3fd53c1d4abdaaaa302b53c067b8d4f84f91e9710cfb572c4493ac78f4`):
locally derived, not fetched — the first 724 of 1448 bytes of
`ikev2-decrypt-aes256gcm16.pcap`, cut mid-packet with a Python slice.
Reproduce: `data[:len(data)//2]`. Used for the truncated-capture
acceptance criterion. Note (found on review): tshark drops a packet cut
off at the very end of the file entirely rather than reporting it with a
partial payload — this fixture demonstrates a clean between-frames cut
(non-zero exit, but only whole frames reported), not the within-frame
case below.

`ikev2-decrypt-aes256gcm16_snaplen.pcap` (`3afdca38ca119fa1bcdb0e26eaa6de9baa5a3e115f3c2958010de1dfe10a3f5e`):
locally derived, not fetched — `ikev2-decrypt-aes256gcm16.pcap` re-cut
with `editcap -s 100` (every frame truncated to 100 captured bytes,
`frame.len` still reporting each frame's true original length). Models a
small-snaplen capture (a historically common tcpdump default) rather than
an abrupt end-of-file cut: every frame is present and tshark exits clean,
but the IKE_SA_INIT request/response's SA payloads are silently absent
from the dissection because they start past byte 100. Used to prove
`ike_parse.py`'s per-frame `is_fully_captured` check (added on review) —
the fixture the between-frames truncated capture above cannot exercise,
since tshark simply omits an end-of-file-truncated frame rather than
reporting it incomplete.

`ikev2-decrypt-aes256gcm16_missing_response.pcap` (`8f05422ee4ee8f52b3ab0945d2f6eb1c6e3005b14c4c1bb3e31f4a90f6d23f6c`):
locally derived, not fetched — `ikev2-decrypt-aes256gcm16.pcap` with
`editcap -r` keeping every frame except frame 2 (the IKE_SA_INIT
response). Added for Phase 6a's closeout review: the other two truncated
fixtures above each produce a `notify_posture_inputs()` result where
*both* halves of IKE_SA_INIT are missing or *neither* is — neither one
actually drives `assess_notify_posture()` with exactly one side real and
the other `None` from genuine parser output. This fixture does: the
request (frame 1) is fully captured and real, and the response frame is
excised entirely, not truncated within itself — the same shape a
between-frames file cut produces when it happens to land between the two
IKE_SA_INIT messages rather than after both. Used by
`tests/inference/test_notify_posture.py::TestOneHalfMissingFromARealTruncatedCapture`.

## Wireshark wiki — real ESP data-plane traffic

Source: `https://wiki.wireshark.org/uploads/dc5b30a117424e6ed21c726771a4006b/ipsec_ikev2+esp_aes-gcm_aes-ctr_aes-cbc.tgz`
(page: `https://wiki.wireshark.org/SampleCaptures#ipsec`, "Example 2")

| File | sha256 |
|---|---|
| `ipsec_multi_algo_natt.pcapng` | `58c748c33388614a767d90345b38b827098d4d3f9609f7075e3ff58a4f49b6ad` |

Renamed from the archive's `capture.pcapng`. UDP/4500 (NAT-T) throughout —
exercises `demux.py`'s non-ESP-marker check. Three sequential Child SAs
with different algorithms (AES-GCM/NULL, AES-CTR/HMAC-SHA-256-128,
AES-CBC/HMAC-SHA-256-128, distinguished by SPI), each carrying only a
handful of ICMP-ping-sized ESP packets — real traffic, but too few
distinct packet sizes per SA for `esp_constraints`'s GCD estimator to
reach a positive identification (see reports/phase-4.md's honest
discussion of this).

## weberblog.net — real vendor firewall-to-firewall captures

Source: `https://weberblog.net/wp-content/uploads/2017/06/IKE-pcaps.zip`
(page: `https://weberblog.net/ikev1-ikev2-capture/`)

| File | sha256 |
|---|---|
| `weberblog_ikev1.pcap` | `289db7cabf920d9c563b6061d76e0b746cf4009ec395efc83cc804ed63c0dba7` |
| `weberblog_ikev2.pcap` | `b2c006dade28a708ecc8d08e30b9a0247ad1e803a6b7be1b4ce6cdf715d9ea09` |

Renamed from the archive's `IKEv1.pcap`/`IKEv2.pcap`. Two real firewalls
(vendor identity not independently verified from the capture itself — the
blog post doesn't name them for this specific post, unlike some of the
author's other posts) tunneling continuous ICMP pings over IPv6-only
IKEv1/IKEv2 VPN sessions. Hundreds of real ESP packets each, but only 2
distinct wire lengths per capture (fixed-size ping traffic) — like the
NAT-T capture above, real but too size-uniform for a positive cipher
identification; both correctly produce `NOT_OBSERVABLE` rather than a
guess.

`weberblog_ikev2_midsession.pcap` (`4c84095b8666d1c10b1b65c2906c77b4b2a67db9f04df0770005b2fd389e5b3d`):
locally derived, not fetched — `weberblog_ikev2.pcap` with `editcap -r ... 40-197`,
removing every frame with `isakmp.exchangetype==34` (both of the two
IKE_SA_INIT exchanges present in the original capture — there are two
because this demo re-established a second one partway through). Used for
the mid-session-capture acceptance criterion: `notify_posture_inputs()`
correctly returns `None` and `extract_ike_sa_init_claims()` correctly
returns no claims, rather than fabricating a `NONE` downgrade-posture
finding from data that was never captured.

## Non-IPsec negative case

Source: `https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/http.pcap`

| File | sha256 |
|---|---|
| `http.pcap` | `69e489a26a59208a1dd56fbea4c606b1e59e8ac32d3d4789ca6cc81e71bad3f2` |

Plain HTTP traffic, no IPsec anywhere. Used for the "a non-IPsec pcap
produces a clean 'no IPsec found' result, not a crash" acceptance
criterion.

## Reproducing this directory

```bash
cd captures
curl -sL -o ikev2-decrypt-aes128ccm12.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes128ccm12.pcap"
curl -sL -o ikev2-decrypt-3des-sha1_160.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-3des-sha1_160.pcap"
curl -sL -o ikev2-decrypt-aes192ctr.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes192ctr.pcap"
curl -sL -o ikev2-decrypt-aes256cbc.pcapng "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes256cbc.pcapng"
curl -sL -o ikev2-decrypt-aes256gcm16.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes256gcm16.pcap"
curl -sL -o ikev2-decrypt-aes256gcm8.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/ikev2-decrypt-aes256gcm8.pcap"
curl -sL -o http.pcap "https://gitlab.com/wireshark/wireshark/-/raw/master/test/captures/http.pcap"

curl -sL -o /tmp/ipsec_multi.tgz "https://wiki.wireshark.org/uploads/dc5b30a117424e6ed21c726771a4006b/ipsec_ikev2+esp_aes-gcm_aes-ctr_aes-cbc.tgz"
tar -xzf /tmp/ipsec_multi.tgz -C /tmp
cp "/tmp/ipsec_ikev2+esp_aes-gcm,aes-ctr,aes-cbc/capture.pcapng" ipsec_multi_algo_natt.pcapng

curl -sL -o /tmp/IKE-pcaps.zip "https://weberblog.net/wp-content/uploads/2017/06/IKE-pcaps.zip"
unzip -o /tmp/IKE-pcaps.zip -d /tmp/weberpcaps
cp /tmp/weberpcaps/IKEv1.pcap weberblog_ikev1.pcap
cp /tmp/weberpcaps/IKEv2.pcap weberblog_ikev2.pcap

python3 -c "d=open('ikev2-decrypt-aes256gcm16.pcap','rb').read(); open('ikev2-decrypt-aes256gcm16_truncated.pcap','wb').write(d[:len(d)//2])"
docker run --rm -v "$PWD/..":/work -w /work ipsec-analyzer:dev \
  editcap -r captures/ikev2-decrypt-aes256gcm16.pcap captures/ikev2-decrypt-aes256gcm16_missing_response.pcap 1 3-6
# editcap ships with the project's Docker image (tshark package):
docker run --rm -v "$PWD/..":/work -w /work ipsec-analyzer:dev \
  editcap -r captures/weberblog_ikev2.pcap captures/weberblog_ikev2_midsession.pcap 40-197
```
