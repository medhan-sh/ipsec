"""Synthetic IKE_SA_INIT oracle for Phase 2 (notify posture) testing.

Produces IKE_SA_INIT request/response pairs as plain data — not pcap bytes,
not anything tshark would need to dissect. Phase 2's notify_posture.py will
consume this directly; Phase 4 will later feed it real tshark-parsed
exchanges instead. Nothing here is consumed yet — this phase only builds
the generator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from core.constants import IKE_SA_INIT_FULL_TRANSCRIPT_AUTH

NOTIFY_POSTURE_STATES = ("both", "request_only", "response_only", "neither")


@dataclass(frozen=True)
class IkeMessage:
    role: str                              # "initiator" | "responder"
    frame: int                             # synthetic frame number (future Claim evidence)
    notify_types: tuple[int, ...]          # notify payload type numbers present
    dh_groups: tuple[int, ...]             # DH transform group numbers in this message's proposal(s)
    transforms: tuple[tuple[str, int], ...] = ()  # e.g. (("ENCR", 20), ("PRF", 5), ("INTEG", 12))


@dataclass(frozen=True)
class IkeSaInitExchange:
    request: IkeMessage
    response: IkeMessage


def synth_ike_sa_init(
    request_notify_types: Iterable[int] = (),
    response_notify_types: Iterable[int] = (),
    request_dh_groups: Iterable[int] = (14,),
    response_dh_groups: Iterable[int] = (14,),
    request_transforms: Iterable[tuple[str, int]] = (),
    response_transforms: Iterable[tuple[str, int]] = (),
    request_frame: int = 1,
    response_frame: int = 2,
) -> IkeSaInitExchange:
    return IkeSaInitExchange(
        request=IkeMessage(
            role="initiator",
            frame=request_frame,
            notify_types=tuple(request_notify_types),
            dh_groups=tuple(request_dh_groups),
            transforms=tuple(request_transforms),
        ),
        response=IkeMessage(
            role="responder",
            frame=response_frame,
            notify_types=tuple(response_notify_types),
            dh_groups=tuple(response_dh_groups),
            transforms=tuple(response_transforms),
        ),
    )


def synth_downgrade_prevention_posture(state: str, **kwargs) -> IkeSaInitExchange:
    """Build a fixture for one cell of Phase 2's four-state notify-posture
    lattice on IKE_SA_INIT_FULL_TRANSCRIPT_AUTH (16447).

    state: one of NOTIFY_POSTURE_STATES — "both", "request_only",
    "response_only", "neither". Any other synth_ike_sa_init kwarg (e.g.
    dh_groups) may be passed through.
    """
    if state not in NOTIFY_POSTURE_STATES:
        raise ValueError(f"unknown notify posture state: {state!r}, expected one of {NOTIFY_POSTURE_STATES}")
    request_has = state in ("both", "request_only")
    response_has = state in ("both", "response_only")
    request_notify = (IKE_SA_INIT_FULL_TRANSCRIPT_AUTH,) if request_has else ()
    response_notify = (IKE_SA_INIT_FULL_TRANSCRIPT_AUTH,) if response_has else ()
    return synth_ike_sa_init(
        request_notify_types=request_notify,
        response_notify_types=response_notify,
        **kwargs,
    )
