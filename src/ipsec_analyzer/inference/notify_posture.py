"""F3b — differentiator 1: notify posture and downgrade exposure.

Classifies IKE_SA_INIT's four-state notify posture lattice on
IKE_SA_INIT_FULL_TRANSCRIPT_AUTH (16447,
draft-ietf-ipsecme-ikev2-downgrade-prevention-08) and, when protection
isn't complete, the severity of what's exposed.

Deliberately takes plain notify-type/DH-group iterables and frame numbers
rather than synth_ike's `IkeSaInitExchange` dataclass directly: `synth/` is
a test oracle, and ARCHITECTURE.md's dependency rule doesn't let
`inference/` import it. Tests build fixtures with synth_ike and unpack
their fields into this module's functions (Phase 2's "consumes synth_ike
output only" is satisfied at the test-data level); Phase 4 will unpack
tshark-parsed data into the same shape.

Every claim here is OBSERVED at confidence 1.0: each value comes directly
from a notify payload or transform proposal that either was or wasn't
present in the exchange — nothing is inferred, so nothing needs to be less
than the tier meaning certainty.

No public capture is expected to actually contain notify 16447 yet — the
downgrade-prevention draft it comes from is about two months old at the
time this phase was built. This module is real, but it is expected to find
`NONE` on every real capture Phase 4 throws at it until vendors catch up.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from ipsec_analyzer.core.claims import Claim, Tier
from ipsec_analyzer.core.constants import (
    ADDITIONAL_KEY_EXCHANGE,
    IKE_SA_INIT_FULL_TRANSCRIPT_AUTH,
    PPK_IDENTITY_KEY,
    PPK_SUPPORT,
    STRONG_DH_GROUPS,
    WEAK_DH_GROUPS,
)


class DowngradeProtectionState(str, Enum):
    PROTECTED = "PROTECTED"
    PARTIAL_RESPONDER_LACKS = "PARTIAL_RESPONDER_LACKS"
    PARTIAL_INITIATOR_LACKS = "PARTIAL_INITIATOR_LACKS"
    NONE = "NONE"


class DowngradeExposureSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INFO = "INFO"


def classify_downgrade_protection_state(
    request_notify_types: Iterable[int],
    response_notify_types: Iterable[int],
) -> DowngradeProtectionState:
    """The four-state lattice. Protection requires the notify in BOTH
    messages — the responder sends it unconditionally when it supports it,
    so response-only is a real, common state that a boolean check (e.g.
    "either side has it") would wrongly treat as protected.
    """
    request_has = IKE_SA_INIT_FULL_TRANSCRIPT_AUTH in set(request_notify_types)
    response_has = IKE_SA_INIT_FULL_TRANSCRIPT_AUTH in set(response_notify_types)
    if request_has and response_has:
        return DowngradeProtectionState.PROTECTED
    if request_has and not response_has:
        return DowngradeProtectionState.PARTIAL_RESPONDER_LACKS
    if response_has:
        return DowngradeProtectionState.PARTIAL_INITIATOR_LACKS
    return DowngradeProtectionState.NONE


def classify_downgrade_exposure_severity(
    request_notify_types: Iterable[int],
    response_notify_types: Iterable[int],
    proposed_dh_groups: Iterable[int],
) -> DowngradeExposureSeverity:
    """Evaluated only when the protection state isn't PROTECTED (callers'
    responsibility to gate that — see assess_notify_posture). Checked in
    the priority order MVP_BUILD_PROMPT.md Phase 2 specifies: hybrid PQ
    exposure outranks a mixed proposal, which outranks a merely-weak one.

    `proposed_dh_groups` is the initiator's full SA proposal (every DH
    group offered, not just the one ultimately negotiated) — "proposal
    mixes weak and strong groups" is a property of what was offered, since
    that's what a downgrade attacker exploits.
    """
    all_notify_types = set(request_notify_types) | set(response_notify_types)
    if ADDITIONAL_KEY_EXCHANGE in all_notify_types:
        return DowngradeExposureSeverity.HIGH
    groups = set(proposed_dh_groups)
    has_weak = bool(groups & WEAK_DH_GROUPS)
    has_strong = bool(groups & STRONG_DH_GROUPS)
    if has_weak and has_strong:
        return DowngradeExposureSeverity.HIGH
    if has_weak:
        return DowngradeExposureSeverity.MEDIUM
    return DowngradeExposureSeverity.INFO


def assess_notify_posture(
    request_notify_types: Iterable[int],
    response_notify_types: Iterable[int],
    proposed_dh_groups: Iterable[int],
    request_frame: int,
    response_frame: int,
) -> list[Claim]:
    """The Claims for one IKE_SA_INIT exchange's notify posture.

    Always emits the downgrade-protection-state claim and the
    hybrid-PQ/PPK presence claims — each is a fact about the whole
    exchange (present-or-absent across both messages), so both frame
    numbers are the evidence for all of them regardless of value; a
    `False`/`NONE` claim still required inspecting both messages to reach.
    Emits the exposure-severity claim only when the state isn't
    PROTECTED — a fully protected exchange has no downgrade exposure left
    to grade.
    """
    evidence = (request_frame, response_frame)
    request_types = set(request_notify_types)
    response_types = set(response_notify_types)
    all_types = request_types | response_types

    state = classify_downgrade_protection_state(request_types, response_types)

    claims = [
        Claim(
            field="ike_sa_init.downgrade_protection_state",
            value=state.value,
            tier=Tier.OBSERVED,
            confidence=1.0,
            method="notify_posture.downgrade_protection_state",
            evidence=evidence,
        ),
        Claim(
            field="ike_sa_init.hybrid_pq_exposed",
            value=ADDITIONAL_KEY_EXCHANGE in all_types,
            tier=Tier.OBSERVED,
            confidence=1.0,
            method="notify_posture.hybrid_pq_exposed",
            evidence=evidence,
        ),
        Claim(
            field="ike_sa_init.ppk_in_use",
            value=bool(all_types & {PPK_SUPPORT, PPK_IDENTITY_KEY}),
            tier=Tier.OBSERVED,
            confidence=1.0,
            method="notify_posture.ppk_in_use",
            evidence=evidence,
        ),
    ]

    if state is not DowngradeProtectionState.PROTECTED:
        severity = classify_downgrade_exposure_severity(request_types, response_types, proposed_dh_groups)
        claims.append(
            Claim(
                field="ike_sa_init.downgrade_exposure_severity",
                value=severity.value,
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="notify_posture.downgrade_exposure_severity",
                evidence=evidence,
            )
        )
    return claims
