"""ike_parse.py — subprocess tshark -T json, consume the isakmp tree, emit
Claims at OBSERVED (MVP_BUILD_PROMPT.md Phase 4).

Invariant 4: never hand-roll a protocol dissector. This module never
interprets raw IKE bytes itself — it only reads fields tshark has already
dissected. The one place this module makes its own decision from raw
bytes (RFC 3948's non-ESP marker) lives in demux.py, not here, and is a
fixed-value check on one reserved field, not protocol dissection.

tshark's default `-T json` silently collapses repeated sibling payloads
(e.g. multiple Notify payloads in one message) into a single JSON key,
which a standard JSON parser then reads as "only the last one" — a real,
easy-to-miss gotcha confirmed against these real captures during this
phase's build, not a hypothetical. `--no-duplicate-keys` turns repeated
keys into JSON arrays instead, which this module requires and normalizes
via `_as_list()` for the (also real) case where an object happens to have
exactly one occurrence of something and so isn't a list at all.

Amendment (VERIFY BY HAND, same standard as constants.py): the payload and
transform type-code constants below are sourced to IANA's IKEv2
Parameters registry and RFC 7383, not the frozen core/constants.py table
(they're protocol structure codes, not ESP framing values) — cited here
following the same pattern as core/constants.py's notify-type amendment.

**Amendment after Phase 4's review: truncation can hide inside a single
frame, not just between frames.** `run_tshark_json` already handles the
case where a capture is cut off *between* packets (tshark exits non-zero
but still emits complete JSON for what it read). But a capture can also
be cut off *inside* the last captured packet's own bytes — tshark still
reports that frame (the ISAKMP header's first fields, including exchange
type and flags, are read first and survive), but any payload that needed
bytes past the cut point is silently absent from the dissection, with no
distinguishing signal in the payload data itself. Before this fix, that
frame looked identical to a real frame that legitimately has no Notify
payloads — meaning a truncated IKE_SA_INIT response could produce a
confident `NONE` downgrade-posture finding from data that was never
fully there, exactly the failure Phase 2's review already fixed once for
the *between-frames* case. tshark's own `frame.len` (the packet's real
original length) vs `frame.cap_len` (bytes actually present in the file)
tells us this per frame; `IkeMessage.is_fully_captured` is that
comparison, and `notify_posture_inputs`/`extract_ike_sa_init_claims` both
now refuse to trust a message that isn't.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from ipsec_analyzer.core.claims import Claim, Tier

# IANA "IKEv2 Payload Types" registry.
PAYLOAD_SA = "33"
PAYLOAD_KE = "34"
PAYLOAD_NOTIFY = "41"
PAYLOAD_FRAGMENT = "53"  # RFC 7383 §3: Encrypted and Authenticated Fragment

# IANA "Transform Type Values" registry (isakmp.tf.type).
TRANSFORM_TYPE_ENCR = "1"
TRANSFORM_TYPE_PRF = "2"
TRANSFORM_TYPE_INTEG = "3"
TRANSFORM_TYPE_DH = "4"

# IANA "IKEv2 Exchange Types" registry.
EXCHANGE_TYPE_IKE_SA_INIT = 34

_TSHARK_TIMEOUT_SECONDS = 60


class TsharkError(RuntimeError):
    """Raised when tshark itself fails to run or produce parseable JSON —
    never silently swallowed, since a broken tshark invocation is not the
    same thing as "no IPsec found" and must not be reported as one.
    """


def _as_list(value: Any) -> list[Any]:
    """Normalizes tshark's "--no-duplicate-keys" quirk: a field that
    occurred exactly once is a bare value/dict, not a one-element list.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


@dataclass(frozen=True)
class TsharkRunResult:
    frames: list[dict]
    exit_clean: bool  # False if tshark's exit code was non-zero (e.g. truncation) even though usable JSON was recovered


def get_tshark_version() -> str:
    """The running tshark's version string (e.g. "4.4.18"). Added on
    review: Bug 1 in this phase (silently-collapsed duplicate JSON keys,
    fixed by `--no-duplicate-keys`) is proof that tshark's output shape is
    version-sensitive — invariant 4 makes tshark a trusted dependency, and
    for a tool whose whole pitch is auditable provenance, "which version
    of the dissector produced this observation" belongs in the record.
    This exists so Phase 6's report/findings.json can include it as
    evidence metadata; recorded here since ike_parse.py is what actually
    invokes tshark, not asserted from the Dockerfile's pinned version
    (the root `Dockerfile`'s `TSHARK_VERSION` build arg is what's
    installed; this is what's actually running, which is the fact that
    matters if the two ever drift).
    """
    try:
        result = subprocess.run(
            ["tshark", "--version"], capture_output=True, timeout=_TSHARK_TIMEOUT_SECONDS, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TsharkError(f"failed to run tshark --version: {exc}") from exc
    first_line = result.stdout.decode(errors="replace").splitlines()[0] if result.stdout else ""
    # First line looks like "TShark (Wireshark) 4.4.18." — extract just the version.
    parts = first_line.split()
    for part in parts:
        if part[:1].isdigit():
            return part.rstrip(".")
    return first_line  # fallback: whatever tshark printed, unparsed


def run_tshark_json(pcap_path: str) -> TsharkRunResult:
    """Runs tshark against the whole file, filtered to isakmp, and returns
    the parsed per-frame JSON objects plus whether tshark's own exit was
    clean.

    Confirmed by hand against a genuinely truncated capture (cut off
    mid-packet): tshark exits with a non-zero status *and still writes
    complete, valid JSON to stdout* for every packet it successfully read
    before the truncation. Treating a non-zero exit as an automatic hard
    failure — the obvious first approach — would turn exactly the
    "truncated capture produces coverage gaps, not a crash" acceptance
    criterion into a crash. So the exit code is not trusted as a
    pass/fail signal on its own: if stdout parses as valid JSON, that's
    the result, regardless of exit code — but the exit code itself is
    still surfaced as `exit_clean`, since a non-zero exit is real
    information ("this file was not read start-to-finish") that
    downstream coverage logic needs. `TsharkError` is raised only when
    there is no usable output at all — tshark couldn't be run, timed out,
    or produced output that doesn't parse as JSON — since those are
    environment problems, not findings about the capture.
    """
    try:
        result = subprocess.run(
            ["tshark", "-r", pcap_path, "-Y", "isakmp", "-T", "json", "--no-duplicate-keys"],
            capture_output=True,
            timeout=_TSHARK_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TsharkError(f"failed to run tshark against {pcap_path}: {exc}") from exc

    stdout = result.stdout.decode(errors="replace").strip()
    if not stdout:
        if result.returncode != 0:
            raise TsharkError(
                f"tshark exited {result.returncode} for {pcap_path} with no output: "
                f"{result.stderr.decode(errors='replace')}"
            )
        return TsharkRunResult(frames=[], exit_clean=True)  # no isakmp frames matched — valid, not an error

    try:
        frames = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise TsharkError(
            f"tshark produced unparseable JSON for {pcap_path} (exit {result.returncode}): {exc}"
        ) from exc

    return TsharkRunResult(frames=frames, exit_clean=result.returncode == 0)


@dataclass(frozen=True)
class IkeTransforms:
    encr_id: int | None = None
    encr_key_length: int | None = None
    prf_id: int | None = None
    integ_id: int | None = None
    dh_id: int | None = None


@dataclass(frozen=True)
class IkeMessage:
    frame_no: int
    exchange_type: int
    is_request: bool  # flag_i and not flag_r
    major_version: int = 2  # isakmp.version_tree.isakmp.mjver: 1 = IKEv1, 2 = IKEv2
    notify_types: tuple[int, ...] = ()
    transforms: IkeTransforms | None = None  # None if no SA payload in this message
    has_fragment: bool = False
    is_fully_captured: bool = True  # frame.cap_len >= frame.len — see module docstring


@dataclass(frozen=True)
class ParsedIke:
    messages: list[IkeMessage]
    tshark_exit_clean: bool


def _find_payloads(isakmp_layer: dict, payload_type: str) -> list[dict]:
    """Top-level payloads only — SA proposals/transforms are nested one
    level deeper inside the SA payload's own tree, walked separately by
    `_extract_transforms`.
    """
    types = _as_list(isakmp_layer.get("isakmp.typepayload"))
    trees = _as_list(isakmp_layer.get("isakmp.typepayload_tree"))
    return [tree for t, tree in zip(types, trees) if t == payload_type]


def _extract_transforms(sa_payload_tree: dict) -> IkeTransforms:
    """SA payload -> proposal(s) -> transform(s). Takes the first
    proposal's transforms — for a negotiated IKE_SA_INIT response there is
    exactly one proposal with exactly one transform per type (the single
    accepted combination); an initiator's *request* may offer several
    proposals; this module is used to extract the *negotiated* result
    from a response, so the first-proposal assumption is the intended one
    there (see extract_ike_sa_init_claims).

    Confirmed by hand against real tshark JSON output (not assumed from
    the field-name convention alone, which turned out to be misleading
    here): the outer `isakmp.typepayload` value at the proposal level is
    NOT the transform's type — it's a generic substructure-kind marker
    that tshark's dissector happens to set to the same value ("3") for
    every transform regardless of whether it's actually ENCR, PRF, INTEG,
    or DH. Each transform's *real* type lives in its own tree's
    `isakmp.tf.type` field, which is what this function actually reads.
    Trusting the outer marker instead (an earlier version of this
    function did) silently extracted only the integrity transform, if
    present, and nothing else, on every real capture tested.
    """
    proposal_trees = _as_list(sa_payload_tree.get("isakmp.typepayload_tree"))
    if not proposal_trees:
        return IkeTransforms()
    proposal = proposal_trees[0]
    if not isinstance(proposal, dict):
        return IkeTransforms()

    tf_trees = _as_list(proposal.get("isakmp.typepayload_tree"))

    encr_id = encr_key_length = prf_id = integ_id = dh_id = None
    for tf_tree in tf_trees:
        if not isinstance(tf_tree, dict):
            continue
        tf_type = tf_tree.get("isakmp.tf.type")
        if tf_type == TRANSFORM_TYPE_ENCR and "isakmp.tf.id.encr" in tf_tree:
            encr_id = int(tf_tree["isakmp.tf.id.encr"])
            attr = tf_tree.get("isakmp.ike2.attr")
            if isinstance(attr, dict) and "isakmp.ike2.attr.key_length" in attr:
                encr_key_length = int(attr["isakmp.ike2.attr.key_length"])
        elif tf_type == TRANSFORM_TYPE_PRF and "isakmp.tf.id.prf" in tf_tree:
            prf_id = int(tf_tree["isakmp.tf.id.prf"])
        elif tf_type == TRANSFORM_TYPE_INTEG and "isakmp.tf.id.integ" in tf_tree:
            integ_id = int(tf_tree["isakmp.tf.id.integ"])
        elif tf_type == TRANSFORM_TYPE_DH and "isakmp.tf.id.dh" in tf_tree:
            dh_id = int(tf_tree["isakmp.tf.id.dh"])

    return IkeTransforms(
        encr_id=encr_id, encr_key_length=encr_key_length, prf_id=prf_id, integ_id=integ_id, dh_id=dh_id
    )


def parse_ike_messages(pcap_path: str) -> ParsedIke:
    """The whole capture's IKE messages as plain data — one IkeMessage per
    ISAKMP frame tshark dissected — plus whether tshark's own run was
    clean. Frame numbers let every Claim built from these cite real
    evidence.
    """
    run_result = run_tshark_json(pcap_path)
    messages: list[IkeMessage] = []
    for frame in run_result.frames:
        layers = frame.get("_source", {}).get("layers", {})
        isakmp = layers.get("isakmp")
        if not isinstance(isakmp, dict):
            continue
        frame_layer = layers.get("frame", {})
        frame_no = int(frame_layer.get("frame.number", 0))
        frame_len = int(frame_layer.get("frame.len", 0))
        frame_cap_len = int(frame_layer.get("frame.cap_len", frame_len))
        is_fully_captured = frame_cap_len >= frame_len

        flags_tree = isakmp.get("isakmp.flags_tree", {})
        flag_i = flags_tree.get("isakmp.flag_i") == "1"
        flag_r = flags_tree.get("isakmp.flag_r") == "1"
        is_request = flag_i and not flag_r

        exchange_type = int(isakmp.get("isakmp.exchangetype", -1))

        version_tree = isakmp.get("isakmp.version_tree", {})
        mjver_raw = version_tree.get("isakmp.mjver")
        major_version = int(mjver_raw, 16) if mjver_raw else 2

        notify_types = tuple(
            int(tree["isakmp.notify.msgtype"])
            for tree in _find_payloads(isakmp, PAYLOAD_NOTIFY)
            if "isakmp.notify.msgtype" in tree
        )

        sa_payloads = _find_payloads(isakmp, PAYLOAD_SA)
        transforms = _extract_transforms(sa_payloads[0]) if sa_payloads else None

        has_fragment = bool(_find_payloads(isakmp, PAYLOAD_FRAGMENT))

        messages.append(
            IkeMessage(
                frame_no=frame_no,
                exchange_type=exchange_type,
                is_request=is_request,
                major_version=major_version,
                notify_types=notify_types,
                transforms=transforms,
                has_fragment=has_fragment,
                is_fully_captured=is_fully_captured,
            )
        )
    return ParsedIke(messages=messages, tshark_exit_clean=run_result.exit_clean)


def extract_ike_sa_init_claims(parsed: ParsedIke) -> list[Claim]:
    """OBSERVED claims for the negotiated IKE SA's cipher, integrity, PRF,
    and DH group — read from the IKE_SA_INIT *response*'s SA payload (the
    single proposal+transform combination the responder actually accepted,
    not the initiator's full offered list).

    Only a fully-captured response is trusted (see module docstring): a
    response frame that exists but was cut short mid-payload could be
    missing transforms that would have been extracted from the complete
    message, and reporting a *subset* of the real SA as if it were the
    whole thing would be a confident, wrong finding built from a coverage
    gap — exactly what invariant 3 forbids.

    Per MVP_BUILD_PROMPT.md Phase 4: "If RFC 7383 fragmentation is present,
    record the fact and abstain. Do not implement reassembly." — if any
    IKE_SA_INIT message in this capture carries a Fragment payload, this
    returns a single NOT_OBSERVABLE claim naming that instead of
    attempting extraction, since a fragmented message's SA payload may not
    even be present in a single frame.
    """
    init_messages = [m for m in parsed.messages if m.exchange_type == EXCHANGE_TYPE_IKE_SA_INIT]
    if any(m.has_fragment for m in init_messages):
        return [
            Claim(
                field="ike_sa.transforms",
                value=None,
                tier=Tier.NOT_OBSERVABLE,
                confidence=0.0,
                method="ike_parse.extract_ike_sa_init_claims",
                evidence=tuple(m.frame_no for m in init_messages if m.has_fragment),
                caveats=(
                    "RFC 7383 IKE message fragmentation detected; reassembly is out of "
                    "scope for this MVP, so the SA payload is not extracted from a "
                    "fragmented IKE_SA_INIT",
                ),
            )
        ]

    response = next(
        (m for m in init_messages if not m.is_request and m.transforms and m.is_fully_captured), None
    )
    if response is None or response.transforms is None:
        return []  # no fully-captured IKE_SA_INIT response with an SA payload — a coverage gap, not a claim

    t = response.transforms
    evidence = (response.frame_no,)
    claims: list[Claim] = []
    if t.encr_id is not None:
        claims.append(
            Claim(
                field="ike_sa.encryption",
                value={"transform_id": t.encr_id, "key_length": t.encr_key_length},
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="ike_parse.extract_ike_sa_init_claims",
                evidence=evidence,
            )
        )
    if t.integ_id is not None:
        claims.append(
            Claim(
                field="ike_sa.integrity",
                value=t.integ_id,
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="ike_parse.extract_ike_sa_init_claims",
                evidence=evidence,
            )
        )
    if t.prf_id is not None:
        claims.append(
            Claim(
                field="ike_sa.prf",
                value=t.prf_id,
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="ike_parse.extract_ike_sa_init_claims",
                evidence=evidence,
            )
        )
    if t.dh_id is not None:
        claims.append(
            Claim(
                field="ike_sa.dh_group",
                value=t.dh_id,
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="ike_parse.extract_ike_sa_init_claims",
                evidence=evidence,
            )
        )
    return claims


def notify_posture_inputs(parsed: ParsedIke) -> dict | None:
    """The plain-data shape inference/notify_posture.assess_notify_posture
    wants, extracted from this capture's IKE_SA_INIT exchange. Returns
    None if no *fully-captured* IKE_SA_INIT messages were observed at all.

    A request/response message that exists as a frame but was cut short
    mid-payload (`is_fully_captured is False`) is treated exactly like a
    message that was never captured — its notify_types may be an
    incomplete subset of what the real message carried, and reporting
    that subset as if it were complete could produce a confident wrong
    downgrade-posture finding (e.g. a truncated response missing notify
    16447 would look identical to a response that genuinely never sent
    it). This is the same principle Phase 2's review already established
    for the between-frames case, applied here to the within-frame case.

    protocol/ is allowed to know about inference/'s input shape without
    inference/ importing protocol/ back — ARCHITECTURE.md's dependency
    rule is about import direction, and returning a plain dict here (not
    an inference/-defined type) keeps protocol/ from needing to import
    inference/ at all.
    """
    init_messages = [m for m in parsed.messages if m.exchange_type == EXCHANGE_TYPE_IKE_SA_INIT]
    if not init_messages:
        return None

    request = next((m for m in init_messages if m.is_request and m.is_fully_captured), None)
    response = next((m for m in init_messages if not m.is_request and m.is_fully_captured), None)

    if request is None and response is None:
        return None  # nothing trustworthy observed — same as "no IKE_SA_INIT at all"

    proposed_dh_groups: tuple[int, ...] = ()
    if request is not None and request.transforms is not None and request.transforms.dh_id is not None:
        proposed_dh_groups = (request.transforms.dh_id,)

    return {
        "request_notify_types": request.notify_types if request is not None else None,
        "response_notify_types": response.notify_types if response is not None else None,
        "proposed_dh_groups": proposed_dh_groups,
        "request_frame": request.frame_no if request is not None else None,
        "response_frame": response.frame_no if response is not None else None,
    }


def extract_ikev1_detected_claim(parsed: ParsedIke) -> Claim | None:
    """OBSERVED claim that IKEv1 is in use, or None if every IKE message
    observed is IKEv2 (or there's no IKE traffic at all).

    Added on review: this project's SA-parameter extraction is IKEv2-
    shaped (`extract_ike_sa_init_claims` correctly returns nothing for an
    IKEv1 capture — the exchange types and SA structure genuinely
    differ), and "no claims" is indistinguishable on its own from "this
    tool is broken." This claim exists so an evaluator watching a real
    IKEv1 capture see an explicit result — "IKEv1 detected, SA parameter
    extraction not attempted (out of scope for this MVP)" — instead of a
    silent blank. IKEv1 itself being a deprecated protocol (RFC 9395) is
    a policy question for Phase 5's rules — not decided here; this claim
    only reports the observed fact, which is all this phase is scoped to
    do.
    """
    ikev1_messages = [m for m in parsed.messages if m.major_version == 1]
    if not ikev1_messages:
        return None
    return Claim(
        field="ike.version",
        value=1,
        tier=Tier.OBSERVED,
        confidence=1.0,
        method="ike_parse.extract_ikev1_detected_claim",
        evidence=tuple(m.frame_no for m in ikev1_messages),
        caveats=(
            "IKEv1 detected; this tool's SA-parameter extraction targets IKEv2's "
            "exchange types and payload structure and was not attempted for this "
            "capture's IKE messages — out of scope for this MVP, not a parse failure",
        ),
    )
