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
tshark-parsed data into the same shape. `IKE_SA_INIT_FULL_TRANSCRIPT_AUTH`
and the other notify-type constants are imported from `core.constants`
(moved there from `synth/synth_ike.py` as a logged amendment after Phase
1's review — see reports/phase-1.md's addendum), not redefined here.

Claims are OBSERVED at confidence 1.0 when the relevant half of the
exchange was actually captured — each value then comes directly from a
notify payload that either was or wasn't present, nothing inferred.
**Amendment after Phase 2's review:** a capture that starts mid-session or
is truncated before IKE_SA_INIT means one or both messages were never
observed. Reporting that as "posture NONE" (neither peer supports
anti-downgrade) would be a confident, wrong finding manufactured from
missing data — exactly what invariant 3 exists to prevent, so it doesn't
actually carve out an exception to "there's no NOT_OBSERVABLE case at this
layer": there is one, and it's coverage, not a protocol fact. When either
message wasn't observed, the posture claim is NOT_OBSERVABLE and severity
is skipped (it's graded from posture-that-isn't-PROTECTED, and there's
nothing to grade without knowing posture). Presence is still reported
positively from whatever half *was* observed — seeing a notify is decisive
regardless of what else was missed; only the negative (not-present)
conclusion needs both halves before it's trustworthy.

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
    *,
    request_notify_types: Iterable[int],
    response_notify_types: Iterable[int],
) -> DowngradeProtectionState:
    """The four-state lattice. Protection requires the notify in BOTH
    messages — the responder sends it unconditionally when it supports it,
    so response-only is a real, common state that a boolean check (e.g.
    "either side has it") would wrongly treat as protected.

    Keyword-only: swapping which iterable is "request" and which is
    "response" silently inverts PARTIAL_RESPONDER_LACKS and
    PARTIAL_INITIATOR_LACKS, and no test would catch it at a call site that
    builds both sides correctly but passes them in the wrong slot (e.g. a
    future Phase 4 adapter). Requires this precondition already be true:
    both messages were actually observed — callers must not call this with
    data from a message that wasn't captured; see assess_notify_posture for
    the NOT_OBSERVABLE handling when that isn't the case.
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
    *,
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
    that's what a downgrade attacker exploits. Confirmed reading, not
    revisited: an INVALID_KE_PAYLOAD counter-suggestion from the responder
    names a single group, which isn't a "proposal" in the threat-model
    sense of "what's negotiable."

    Keyword-only for the same swap-risk reason as
    classify_downgrade_protection_state.
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
    *,
    request_notify_types: Iterable[int] | None,
    response_notify_types: Iterable[int] | None,
    proposed_dh_groups: Iterable[int],
    request_frame: int | None,
    response_frame: int | None,
) -> list[Claim]:
    """The Claims for one IKE_SA_INIT exchange's notify posture.

    `request_notify_types`/`response_notify_types` being `None` (as
    opposed to an empty iterable) means that half of the exchange was
    never observed in the capture — a mid-session start or a truncation
    before IKE_SA_INIT, not "the message was seen and had no notifies."
    That distinction is the whole fix from Phase 2's review: absence in
    the capture is not absence on the wire.

    - Both halves observed: behaves exactly as before — the
      downgrade-protection-state claim is OBSERVED, and severity is
      evaluated (and emitted) whenever state isn't PROTECTED.
    - Either half missing: downgrade-protection-state and severity are
      both skipped as findings; downgrade-protection-state is instead
      emitted as NOT_OBSERVABLE (a coverage gap), and severity isn't
      emitted at all (it grades a posture we don't actually know).
    - hybrid_pq_exposed / ppk_in_use follow the same principle at the
      per-claim level rather than being skipped wholesale: a positive
      finding from whichever half *was* observed is still fully decisive
      (seeing the notify is certain regardless of what else was missed),
      but a negative conclusion requires both halves to have been checked
      — otherwise it's downgraded to NOT_OBSERVABLE too.
    """
    request_observed = request_notify_types is not None
    response_observed = response_notify_types is not None
    fully_observed = request_observed and response_observed

    request_types = set(request_notify_types) if request_observed else set()
    response_types = set(response_notify_types) if response_observed else set()
    all_types = request_types | response_types

    evidence = tuple(f for f in (request_frame, response_frame) if f is not None)

    claims: list[Claim] = []

    if fully_observed:
        state = classify_downgrade_protection_state(
            request_notify_types=request_types, response_notify_types=response_types
        )
        claims.append(
            Claim(
                field="ike_sa_init.downgrade_protection_state",
                value=state.value,
                tier=Tier.OBSERVED,
                confidence=1.0,
                method="notify_posture.downgrade_protection_state",
                evidence=evidence,
            )
        )
    else:
        state = None
        claims.append(
            Claim(
                field="ike_sa_init.downgrade_protection_state",
                value=None,
                tier=Tier.NOT_OBSERVABLE,
                confidence=0.0,
                method="notify_posture.downgrade_protection_state",
                evidence=evidence,
                caveats=(
                    "IKE_SA_INIT request and/or response not observed (mid-session start "
                    "or truncated capture) — downgrade-protection posture cannot be "
                    "determined from a partial exchange",
                ),
            )
        )

    def _presence_claim(field: str, method: str, present_in_observed: bool) -> Claim:
        if present_in_observed:
            return Claim(
                field=field, value=True, tier=Tier.OBSERVED, confidence=1.0,
                method=method, evidence=evidence,
            )
        if fully_observed:
            return Claim(
                field=field, value=False, tier=Tier.OBSERVED, confidence=1.0,
                method=method, evidence=evidence,
            )
        return Claim(
            field=field, value=None, tier=Tier.NOT_OBSERVABLE, confidence=0.0,
            method=method, evidence=evidence,
            caveats=(
                "not present in the observed half(s) of IKE_SA_INIT, but the other "
                "half was not captured — absence cannot be confirmed from a partial "
                "exchange",
            ),
        )

    claims.append(
        _presence_claim(
            "ike_sa_init.hybrid_pq_exposed",
            "notify_posture.hybrid_pq_exposed",
            ADDITIONAL_KEY_EXCHANGE in all_types,
        )
    )
    claims.append(
        _presence_claim(
            "ike_sa_init.ppk_in_use",
            "notify_posture.ppk_in_use",
            bool(all_types & {PPK_SUPPORT, PPK_IDENTITY_KEY}),
        )
    )

    if fully_observed and state is not DowngradeProtectionState.PROTECTED:
        severity = classify_downgrade_exposure_severity(
            request_notify_types=request_types,
            response_notify_types=response_types,
            proposed_dh_groups=proposed_dh_groups,
        )
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
