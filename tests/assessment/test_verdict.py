from ipsec_analyzer.assessment.verdict import AmbiguousVerdict, Verdict, lift_verdict
from ipsec_analyzer.core.candidates import CandidateSet
from ipsec_analyzer.core.claims import Tier
from ipsec_analyzer.core.constants import SUITE_FRAMINGS


def _candidate_set(surviving_ids):
    universe = frozenset(SUITE_FRAMINGS)
    return CandidateSet(universe=universe, surviving=frozenset(surviving_ids), eliminated_by=())


# Every suite sharing (counter, 4, 8, 16) — genuinely indistinguishable
# strong AEAD variants (see Phase 3's indistinguishable-groups tests).
_STRONG_AEAD_16_GROUP = {
    sid
    for sid, f in SUITE_FRAMINGS.items()
    if f.family == "counter" and f.pad_granularity == 4 and f.explicit_iv == 8 and f.icv_len == 16
}

_WEAK_64BIT_BLOCK_SUITES = {sid for sid, f in SUITE_FRAMINGS.items() if f.pad_granularity == 8}


class TestUnanimousVerdicts:
    def test_all_strong_aead_yields_confidentiality_acceptable_true(self):
        assert len(_STRONG_AEAD_16_GROUP) > 1, "test fixture assumption: this group has multiple real members"
        cs = _candidate_set(_STRONG_AEAD_16_GROUP)
        verdict = lift_verdict(cs, "confidentiality_acceptable")
        assert isinstance(verdict, Verdict)
        assert verdict.outcome is True
        assert verdict.confidence == 1.0
        # "without naming a cipher" — the basis must not single out one
        # specific suite name as *the* answer
        for suite_id in _STRONG_AEAD_16_GROUP:
            assert suite_id not in verdict.basis

    def test_g_equals_8_yields_weak_crypto_verdict(self):
        assert len(_WEAK_64BIT_BLOCK_SUITES) > 1
        cs = _candidate_set(_WEAK_64BIT_BLOCK_SUITES)
        verdict = lift_verdict(cs, "confidentiality_acceptable")
        assert isinstance(verdict, Verdict)
        assert verdict.outcome is False
        assert verdict.confidence == 1.0

    def test_single_survivor_is_still_unanimous(self):
        one_suite = next(iter(_STRONG_AEAD_16_GROUP))
        cs = _candidate_set({one_suite})
        verdict = lift_verdict(cs, "confidentiality_acceptable")
        assert isinstance(verdict, Verdict)
        assert verdict.outcome is True
        assert verdict.confidence == 1.0


class TestAmbiguousVerdicts:
    def test_split_candidate_set_yields_ambiguous_verdict(self):
        strong_suite = next(iter(_STRONG_AEAD_16_GROUP))
        weak_suite = next(iter(_WEAK_64BIT_BLOCK_SUITES))
        cs = _candidate_set({strong_suite, weak_suite})
        verdict = lift_verdict(cs, "confidentiality_acceptable")
        assert isinstance(verdict, AmbiguousVerdict)
        assert verdict.surviving_true == frozenset({strong_suite})
        assert verdict.surviving_false == frozenset({weak_suite})

    def test_ambiguous_verdict_names_which_candidates_drive_which_outcome(self):
        strong_suites = set(list(_STRONG_AEAD_16_GROUP)[:2])
        weak_suite = next(iter(_WEAK_64BIT_BLOCK_SUITES))
        cs = _candidate_set(strong_suites | {weak_suite})
        verdict = lift_verdict(cs, "confidentiality_acceptable")
        assert isinstance(verdict, AmbiguousVerdict)
        assert verdict.surviving_true == frozenset(strong_suites)
        assert verdict.surviving_false == frozenset({weak_suite})
        assert str(len(strong_suites)) in verdict.basis or "2" in verdict.basis


class TestEmptyCandidateSet:
    def test_empty_surviving_set_returns_none(self):
        cs = _candidate_set(set())
        assert lift_verdict(cs, "confidentiality_acceptable") is None


class TestPredicateCoversWholeTable:
    def test_every_suite_has_a_predicate_value(self):
        from ipsec_analyzer.assessment.verdict import PREDICATES

        predicate = PREDICATES["confidentiality_acceptable"]
        assert set(predicate) == set(SUITE_FRAMINGS)

    def test_null_encryption_is_never_acceptable(self):
        from ipsec_analyzer.assessment.verdict import PREDICATES

        predicate = PREDICATES["confidentiality_acceptable"]
        null_suites = {sid for sid, f in SUITE_FRAMINGS.items() if f.explicit_iv == 0}
        assert null_suites, "test fixture assumption: NULL-ENC suites exist in the table"
        for suite_id in null_suites:
            assert predicate[suite_id] is False


class TestIntegrityAcceptablePredicate:
    """Phase 5a review fix #4: a second predicate, drawn on integrity-tag
    strength rather than confidentiality, over the same candidate set.
    """

    def test_every_suite_has_a_predicate_value(self):
        from ipsec_analyzer.assessment.verdict import PREDICATES

        predicate = PREDICATES["integrity_acceptable"]
        assert set(predicate) == set(SUITE_FRAMINGS)

    def test_generic_hmac_sha1_and_md5_are_not_acceptable(self):
        from ipsec_analyzer.assessment.verdict import PREDICATES

        predicate = PREDICATES["integrity_acceptable"]
        weak_suites = {
            sid for sid in SUITE_FRAMINGS if "HMAC-SHA1" in sid or "HMAC-MD5" in sid
        }
        assert weak_suites, "test fixture assumption: HMAC-SHA1/MD5 suites exist in the table"
        for suite_id in weak_suites:
            assert predicate[suite_id] is False

    def test_aead_suites_are_acceptable_regardless_of_icv_len(self):
        from ipsec_analyzer.assessment.verdict import PREDICATES

        predicate = PREDICATES["integrity_acceptable"]
        for suite_id in ("AES-128-CCM-12", "AES-256-CCM-12", "AES-128-GCM-12"):
            assert predicate[suite_id] is True

    def test_demo_case_confidentiality_unanimous_integrity_splits(self):
        # This exact case is the demo the review asks for: four suites
        # that all agree confidentiality is acceptable (none is a 64-bit
        # block cipher or NULL-ENC), but split on integrity_acceptable —
        # three use an AEAD tag, one (AES-CTR + HMAC-SHA1-96) uses a
        # generic-composition HMAC-SHA1 transform RFC 8221 deprecates.
        suite_ids = {
            "AES-128-CCM-12",
            "AES-256-CCM-12",
            "AES-128-GCM-12",
            "AES-128-CTR + HMAC-SHA1-96",
        }
        assert suite_ids <= set(SUITE_FRAMINGS), "test fixture assumption: these suite_ids exist in the table"
        cs = _candidate_set(suite_ids)

        confidentiality_verdict = lift_verdict(cs, "confidentiality_acceptable")
        assert isinstance(confidentiality_verdict, Verdict)
        assert confidentiality_verdict.outcome is True
        assert confidentiality_verdict.confidence == 1.0

        integrity_verdict = lift_verdict(cs, "integrity_acceptable")
        assert isinstance(integrity_verdict, AmbiguousVerdict)
        assert integrity_verdict.surviving_true == frozenset(suite_ids - {"AES-128-CTR + HMAC-SHA1-96"})
        assert integrity_verdict.surviving_false == frozenset({"AES-128-CTR + HMAC-SHA1-96"})


class TestBasisTier:
    """Phase 5a review fix #5: Verdict carries basis_tier, the weakest
    tier among the claims that narrowed the candidate set — distinct from
    confidence, which stays 1.0 on unanimity regardless of evidence tier.
    """

    def test_basis_tier_reflects_the_weakest_narrowing_tier(self):
        cs = _candidate_set(_STRONG_AEAD_16_GROUP)
        verdict = lift_verdict(
            cs, "confidentiality_acceptable", narrowing_tiers=[Tier.INFERRED_SIDE_CHANNEL, Tier.OBSERVED]
        )
        assert isinstance(verdict, Verdict)
        assert verdict.confidence == 1.0
        assert verdict.basis_tier is Tier.INFERRED_SIDE_CHANNEL

    def test_side_channel_only_narrowing_yields_side_channel_basis_at_full_confidence(self):
        # The exact case the review names: confidence stays 1.0 (unanimity
        # is a fact about the surviving set) even though the evidence
        # behind it is side-channel-derived, not directly observed.
        cs = _candidate_set(_STRONG_AEAD_16_GROUP)
        verdict = lift_verdict(cs, "confidentiality_acceptable", narrowing_tiers=[Tier.INFERRED_SIDE_CHANNEL])
        assert verdict.confidence == 1.0
        assert verdict.basis_tier is Tier.INFERRED_SIDE_CHANNEL

    def test_no_narrowing_tiers_given_defaults_to_not_observable(self):
        cs = _candidate_set(_STRONG_AEAD_16_GROUP)
        verdict = lift_verdict(cs, "confidentiality_acceptable")
        assert verdict.basis_tier is Tier.NOT_OBSERVABLE
