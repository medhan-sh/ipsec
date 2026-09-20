"""Frozen contract. Do not modify without asking — see CLAUDE.md invariant 8 (§2 of MVP_BUILD_PROMPT.md).

Every framing constant below (explicit_iv, pad_granularity, icv_len) is a
factual claim about a wire format, sourced to an RFC and section. A wrong
value here silently corrupts every downstream inference, so the whole table
is marked for hand verification — see reports/phase-0.md for the checklist.

Invariant 5 (never hand-invent a framing constant): every row here traces to
a cited RFC. Where a value was derived by combining two RFCs (e.g. a cipher
RFC for IV/padding and a separate integrity RFC for ICV length), both are
cited.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuiteFraming:
    suite_id: str        # e.g. "AES-128-GCM-16"
    family: str          # "cbc" | "counter"
    explicit_iv: int     # bytes on the wire before ciphertext
    pad_granularity: int # 16 for AES-CBC, 8 for 64-bit block CBC, 4 for counter
    icv_len: int         # bytes
    rfc: str             # e.g. "RFC 4106 §3"


# VERIFY BY HAND — every row below. See reports/phase-0.md for the full
# checklist with one line per constant for manual cross-checking against the
# cited RFC section.
#
# CBC family: explicit_iv == pad_granularity == cipher block size (16 bytes
# for AES/Camellia per RFC 3602 §2 / RFC 5529 §3.2; 8 bytes for legacy
# 64-bit-block ciphers per RFC 2451 §3 / RFC 2405 §2). icv_len is the
# truncated MAC length of the paired integrity transform (RFC 2404 §3,
# RFC 2403 §3, RFC 4868 §2.3, RFC 3566 §2).
#
# counter/AEAD family: explicit_iv is the 8-byte wire nonce/IV field common
# to CTR (RFC 3686 §3.1), GCM (RFC 4106 §3.1), CCM (RFC 4309 §3), and
# ChaCha20-Poly1305 (RFC 7634 §2). pad_granularity is 4 bytes: these modes
# have no block-chaining requirement, only the base ESP 4-byte alignment
# (RFC 4303 §2.4). icv_len is the authentication tag length, which for
# combined-mode ciphers is chosen at negotiation time from the values below.
#
# NULL encryption (RFC 2410) has a zero-length IV and a block size of 1
# byte, so it is classified under "counter" here purely because its padding
# arithmetic (align to 4, no chaining) matches that family's formula in
# synth_esp.py — it is NOT an AEAD/counter-mode cipher. Flagged as an open
# question in reports/phase-0.md for human review of this classification.
_TABLE: tuple[SuiteFraming, ...] = (
    # --- CBC, 16-byte block (AES, Camellia) ---
    SuiteFraming("AES-128-CBC + HMAC-SHA1-96", "cbc", 16, 16, 12, "RFC 3602, RFC 2404"),
    SuiteFraming("AES-128-CBC + HMAC-MD5-96", "cbc", 16, 16, 12, "RFC 3602, RFC 2403"),
    SuiteFraming("AES-128-CBC + HMAC-SHA256-128", "cbc", 16, 16, 16, "RFC 3602, RFC 4868 §2.3"),
    SuiteFraming("AES-128-CBC + HMAC-SHA384-192", "cbc", 16, 16, 24, "RFC 3602, RFC 4868 §2.3"),
    SuiteFraming("AES-128-CBC + HMAC-SHA512-256", "cbc", 16, 16, 32, "RFC 3602, RFC 4868 §2.3"),
    SuiteFraming("AES-128-CBC + AES-XCBC-96", "cbc", 16, 16, 12, "RFC 3602, RFC 3566 §2"),
    SuiteFraming("AES-192-CBC + HMAC-SHA1-96", "cbc", 16, 16, 12, "RFC 3602, RFC 2404"),
    SuiteFraming("AES-192-CBC + HMAC-SHA256-128", "cbc", 16, 16, 16, "RFC 3602, RFC 4868 §2.3"),
    SuiteFraming("AES-256-CBC + HMAC-SHA1-96", "cbc", 16, 16, 12, "RFC 3602, RFC 2404"),
    SuiteFraming("AES-256-CBC + HMAC-SHA256-128", "cbc", 16, 16, 16, "RFC 3602, RFC 4868 §2.3"),
    SuiteFraming("AES-256-CBC + HMAC-SHA384-192", "cbc", 16, 16, 24, "RFC 3602, RFC 4868 §2.3"),
    SuiteFraming("AES-256-CBC + HMAC-SHA512-256", "cbc", 16, 16, 32, "RFC 3602, RFC 4868 §2.3"),
    SuiteFraming("AES-256-CBC + AES-XCBC-96", "cbc", 16, 16, 12, "RFC 3602, RFC 3566 §2"),
    SuiteFraming("Camellia-128-CBC + HMAC-SHA1-96", "cbc", 16, 16, 12, "RFC 5529 §3.2, RFC 2404"),
    SuiteFraming("Camellia-256-CBC + HMAC-SHA256-128", "cbc", 16, 16, 16, "RFC 5529 §3.2, RFC 4868 §2.3"),

    # --- CBC, 8-byte block (legacy 64-bit block ciphers) ---
    SuiteFraming("3DES-CBC + HMAC-SHA1-96", "cbc", 8, 8, 12, "RFC 2451 §3, RFC 2404"),
    SuiteFraming("3DES-CBC + HMAC-MD5-96", "cbc", 8, 8, 12, "RFC 2451 §3, RFC 2403"),
    SuiteFraming("3DES-CBC + HMAC-SHA256-128", "cbc", 8, 8, 16, "RFC 2451 §3, RFC 4868 §2.3"),
    SuiteFraming("DES-CBC + HMAC-MD5-96", "cbc", 8, 8, 12, "RFC 2405 §2, RFC 2403"),
    SuiteFraming("DES-CBC + HMAC-SHA1-96", "cbc", 8, 8, 12, "RFC 2405 §2, RFC 2404"),
    SuiteFraming("CAST-128-CBC + HMAC-SHA1-96", "cbc", 8, 8, 12, "RFC 2451 §3, RFC 2404"),
    SuiteFraming("Blowfish-CBC + HMAC-SHA1-96", "cbc", 8, 8, 12, "RFC 2451 §3, RFC 2404"),
    SuiteFraming("IDEA-CBC + HMAC-SHA1-96", "cbc", 8, 8, 12, "RFC 2451 §3, RFC 2404"),

    # --- NULL encryption (see classification caveat above) ---
    SuiteFraming("NULL-ENC + HMAC-SHA1-96", "counter", 0, 4, 12, "RFC 2410, RFC 2404"),
    SuiteFraming("NULL-ENC + HMAC-SHA256-128", "counter", 0, 4, 16, "RFC 2410, RFC 4868 §2.3"),

    # --- Counter / AEAD ---
    SuiteFraming("AES-128-GCM-16", "counter", 8, 4, 16, "RFC 4106 §3"),
    SuiteFraming("AES-128-GCM-12", "counter", 8, 4, 12, "RFC 4106 §3"),
    SuiteFraming("AES-128-GCM-8", "counter", 8, 4, 8, "RFC 4106 §3"),
    SuiteFraming("AES-192-GCM-16", "counter", 8, 4, 16, "RFC 4106 §3"),
    SuiteFraming("AES-192-GCM-12", "counter", 8, 4, 12, "RFC 4106 §3"),
    SuiteFraming("AES-256-GCM-16", "counter", 8, 4, 16, "RFC 4106 §3"),
    SuiteFraming("AES-256-GCM-12", "counter", 8, 4, 12, "RFC 4106 §3"),
    SuiteFraming("AES-256-GCM-8", "counter", 8, 4, 8, "RFC 4106 §3"),
    SuiteFraming("AES-128-CCM-16", "counter", 8, 4, 16, "RFC 4309 §3"),
    SuiteFraming("AES-128-CCM-12", "counter", 8, 4, 12, "RFC 4309 §3"),
    SuiteFraming("AES-128-CCM-8", "counter", 8, 4, 8, "RFC 4309 §3"),
    SuiteFraming("AES-256-CCM-16", "counter", 8, 4, 16, "RFC 4309 §3"),
    SuiteFraming("AES-256-CCM-12", "counter", 8, 4, 12, "RFC 4309 §3"),
    SuiteFraming("AES-256-CCM-8", "counter", 8, 4, 8, "RFC 4309 §3"),
    SuiteFraming("ChaCha20-Poly1305", "counter", 8, 4, 16, "RFC 7634 §2"),
    SuiteFraming("AES-128-CTR + HMAC-SHA1-96", "counter", 8, 4, 12, "RFC 3686 §3.1, RFC 2404"),
    SuiteFraming("AES-128-CTR + HMAC-SHA256-128", "counter", 8, 4, 16, "RFC 3686 §3.1, RFC 4868 §2.3"),
    SuiteFraming("AES-256-CTR + HMAC-SHA1-96", "counter", 8, 4, 12, "RFC 3686 §3.1, RFC 2404"),
    SuiteFraming("AES-256-CTR + HMAC-SHA256-128", "counter", 8, 4, 16, "RFC 3686 §3.1, RFC 4868 §2.3"),
)

SUITE_FRAMINGS: dict[str, SuiteFraming] = {s.suite_id: s for s in _TABLE}

assert len(SUITE_FRAMINGS) == len(_TABLE), "duplicate suite_id in constants table"
