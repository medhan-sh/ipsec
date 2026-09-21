import pytest

from ipsec_analyzer.assessment.engine import evaluate_rules
from ipsec_analyzer.assessment.rules.schema import load_default_rules
from ipsec_analyzer.core.claims import Claim, Tier
from ipsec_analyzer.core.ledger import ClaimLedger


def _claim(field, value, tier=Tier.OBSERVED, confidence=1.0, evidence=(1,)):
    return Claim(field=field, value=value, tier=tier, confidence=confidence, method="test", evidence=evidence)


@pytest.fixture(scope="module")
def rules():
    return load_default_rules()


class TestRulesLoadCleanly:
    def test_exactly_fifteen_rules(self, rules):
        assert len(rules) == 15

    def test_all_rule_ids_are_unique(self, rules):
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids))

    def test_every_rule_has_at_least_one_reference(self, rules):
        for rule in rules:
            assert rule.references, f"{rule.id} has no references"


class TestCoverageHeadlineNumber:
    def test_empty_ledger_is_all_gaps(self, rules):
        result = evaluate_rules(ClaimLedger(claims=()), rules)
        assert result.checks_total == 15
        assert result.checks_assessable == 0
        assert result.checks_gap == 15
        assert result.checks_found == 0
        assert result.checks_passed == 0
        assert result.findings == ()
        assert len(result.gaps) == 15

    def test_assessable_plus_gap_equals_total(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike_sa.dh_group", 14))
        result = evaluate_rules(ledger, rules)
        assert result.checks_assessable + result.checks_gap == result.checks_total

    def test_rules_14_and_15_always_appear_as_gaps(self, rules):
        # MVP_BUILD_PROMPT.md Phase 5: "Rules 14 and 15 must be visible in
        # the report as gaps... on every capture" — checked here against
        # both an empty ledger and a fully-populated one.
        for ledger in (
            ClaimLedger(claims=()),
            ClaimLedger.from_claims(
                _claim("ike_sa.dh_group", 14),
                _claim("ike_sa.encryption", {"transform_id": 20, "key_length": 256}),
            ),
        ):
            result = evaluate_rules(ledger, rules)
            gap_ids = {g.rule_id for g in result.gaps}
            assert "pfs_not_observable" in gap_ids
            assert "anti_replay_not_observable" in gap_ids

    def test_structural_gaps_report_not_observable_actual_tier(self, rules):
        # Matches ARCHITECTURE.md's own findings.json sketch: the
        # anti-replay gap shows actual_tier NOT_OBSERVABLE, not a bare
        # absence. Phase 5a review fix #2: this is no longer produced by an
        # injected Claim — CoverageGap's own constructor normalizes a
        # missing claim to NOT_OBSERVABLE (see TestNoInjectedClaims below).
        result = evaluate_rules(ClaimLedger(claims=()), rules)
        anti_replay_gap = next(g for g in result.gaps if g.rule_id == "anti_replay_not_observable")
        assert anti_replay_gap.actual_tier is Tier.NOT_OBSERVABLE
        pfs_gap = next(g for g in result.gaps if g.rule_id == "pfs_not_observable")
        assert pfs_gap.actual_tier is Tier.NOT_OBSERVABLE

    def test_min_tier_unmet_is_a_gap_not_a_finding(self, rules):
        # esp.granularity claim exists but at NOT_OBSERVABLE (the engine's
        # own abstention) — rule 8 requires INFERRED_SIDE_CHANNEL.
        ledger = ClaimLedger.from_claims(_claim("esp.granularity", None, tier=Tier.NOT_OBSERVABLE, confidence=0.0))
        result = evaluate_rules(ledger, rules)
        gap = next((g for g in result.gaps if g.rule_id == "sixty_four_bit_block_cipher_in_esp"), None)
        assert gap is not None
        assert gap.actual_tier is Tier.NOT_OBSERVABLE
        assert gap.required_tier is Tier.INFERRED_SIDE_CHANNEL

    def test_condition_false_is_neither_finding_nor_gap(self, rules):
        # Claim observed at sufficient tier, but the value doesn't trigger
        # the rule — assessed, and the answer is negative: a PassedCheck
        # (Phase 6b review item 2), not silence.
        ledger = ClaimLedger.from_claims(_claim("ike_sa.dh_group", 19))  # strong group
        result = evaluate_rules(ledger, rules)
        assert result.checks_assessable >= 1
        assert not any(f.rule_id == "weak_dh_group_negotiated" for f in result.findings)
        assert not any(g.rule_id == "weak_dh_group_negotiated" for g in result.gaps)
        assert any(p.rule_id == "weak_dh_group_negotiated" for p in result.passes)


class TestNoInjectedClaims:
    """Phase 5a review fix #2: assessment/ must not construct Claims — it
    reads a ClaimLedger. Confirms the ledger handed to evaluate_rules is
    never augmented, and that the NOT_OBSERVABLE actual_tier / gap_kind
    values for the two structural gaps come from CoverageGap's own
    normalization and rules.yaml's `gap_kind`, not a fabricated claim.
    """

    def test_ledger_passed_in_is_not_mutated_or_replaced(self, rules):
        ledger = ClaimLedger(claims=())
        evaluate_rules(ledger, rules)
        # ClaimLedger is frozen and evaluate_rules never had a handle that
        # could mutate it in place; this documents that the caller's own
        # ledger has no synthetic claims appended to it as a side effect.
        assert ledger.claims == ()
        assert not ledger.has_field("child_sa.pfs")
        assert not ledger.has_field("esp.anti_replay_enabled")

    def test_gap_kind_distinguishes_the_two_structural_gaps(self, rules):
        result = evaluate_rules(ClaimLedger(claims=()), rules)
        anti_replay_gap = next(g for g in result.gaps if g.rule_id == "anti_replay_not_observable")
        pfs_gap = next(g for g in result.gaps if g.rule_id == "pfs_not_observable")
        assert anti_replay_gap.gap_kind == "structurally_unobservable"
        assert pfs_gap.gap_kind == "not_implemented"

    def test_ordinary_gap_kind_is_not_observed_in_capture(self, rules):
        result = evaluate_rules(ClaimLedger(claims=()), rules)
        weak_dh_gap = next(g for g in result.gaps if g.rule_id == "weak_dh_group_negotiated")
        assert weak_dh_gap.gap_kind == "not_observed_in_capture"

    def test_every_rule_has_a_valid_gap_kind(self, rules):
        from ipsec_analyzer.assessment.rules.schema import VALID_GAP_KINDS

        for rule in rules:
            assert rule.gap_kind in VALID_GAP_KINDS

    def test_unknown_gap_kind_raises_at_load_time(self, tmp_path):
        from ipsec_analyzer.assessment.rules.schema import RuleValidationError, load_rules

        bad_yaml = tmp_path / "bad_rules.yaml"
        bad_yaml.write_text(
            """
- id: bogus
  title: "Bogus rule"
  target: some.field
  min_tier: OBSERVED
  condition:
    op: eq
    value: true
  severity: LOW
  category: test
  references: ["RFC 0000"]
  recommendation: "n/a"
  gap_kind: not_a_real_gap_kind
"""
        )
        with pytest.raises(RuleValidationError):
            load_rules(bad_yaml)


class TestIndividualRuleFindings:
    def test_weak_dh_group_negotiated(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike_sa.dh_group", 2))
        result = evaluate_rules(ledger, rules)
        finding = next(f for f in result.findings if f.rule_id == "weak_dh_group_negotiated")
        assert finding.severity == "HIGH"
        assert finding.evidence == (1,)

    def test_ikev1_in_use(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike.version", 1))
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "ikev1_in_use" for f in result.findings)

    def test_ikev1_aggressive_mode(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike.aggressive_mode", True))
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "ikev1_aggressive_mode" for f in result.findings)

    def test_downgrade_exposure_mixed_strength(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim("ike_sa_init.downgrade_exposure_severity", {"severity": "HIGH", "reason": "MIXED_STRENGTH_GROUPS"})
        )
        result = evaluate_rules(ledger, rules)
        finding = next(f for f in result.findings if f.rule_id == "downgrade_exposure_mixed_strength")
        assert finding.severity == "HIGH"

    def test_downgrade_exposure_hybrid_pq(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim("ike_sa_init.downgrade_exposure_severity", {"severity": "HIGH", "reason": "HYBRID_PQ_EXPOSED"})
        )
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "downgrade_exposure_hybrid_pq" for f in result.findings)
        # must not also fire the mixed-strength or weak-group rules
        assert not any(f.rule_id == "downgrade_exposure_mixed_strength" for f in result.findings)

    def test_downgrade_exposure_weak_group_negotiable(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim(
                "ike_sa_init.downgrade_exposure_severity", {"severity": "MEDIUM", "reason": "WEAK_GROUP_NEGOTIABLE"}
            )
        )
        result = evaluate_rules(ledger, rules)
        finding = next(f for f in result.findings if f.rule_id == "downgrade_exposure_weak_group_negotiable")
        assert finding.severity == "MEDIUM"

    def test_no_weak_group_reason_fires_no_downgrade_exposure_rule(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim("ike_sa_init.downgrade_exposure_severity", {"severity": "INFO", "reason": "NO_WEAK_GROUP"})
        )
        result = evaluate_rules(ledger, rules)
        downgrade_findings = [f for f in result.findings if f.category == "downgrade_protection"]
        assert downgrade_findings == []

    def test_partial_downgrade_protection_names_the_responder(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim("ike_sa_init.downgrade_protection_state", "PARTIAL_RESPONDER_LACKS")
        )
        result = evaluate_rules(ledger, rules)
        finding = next(f for f in result.findings if f.rule_id == "partial_downgrade_protection")
        assert "the responder" in finding.title
        assert "the responder" in finding.recommendation
        assert "PARTIAL_RESPONDER_LACKS" not in finding.title  # relabeled, not the raw enum string

    def test_partial_downgrade_protection_names_the_initiator(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim("ike_sa_init.downgrade_protection_state", "PARTIAL_INITIATOR_LACKS")
        )
        result = evaluate_rules(ledger, rules)
        finding = next(f for f in result.findings if f.rule_id == "partial_downgrade_protection")
        assert "the initiator" in finding.title

    def test_protected_state_fires_no_partial_protection_finding(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike_sa_init.downgrade_protection_state", "PROTECTED"))
        result = evaluate_rules(ledger, rules)
        assert not any(f.rule_id == "partial_downgrade_protection" for f in result.findings)

    def test_sixty_four_bit_block_cipher_in_esp(self, rules):
        ledger = ClaimLedger.from_claims(_claim("esp.granularity", 8, tier=Tier.INFERRED_SIDE_CHANNEL))
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "sixty_four_bit_block_cipher_in_esp" for f in result.findings)

    def test_sixteen_byte_granularity_does_not_fire_64_bit_rule(self, rules):
        ledger = ClaimLedger.from_claims(_claim("esp.granularity", 16, tier=Tier.INFERRED_SIDE_CHANNEL))
        result = evaluate_rules(ledger, rules)
        assert not any(f.rule_id == "sixty_four_bit_block_cipher_in_esp" for f in result.findings)

    def test_truncated_96_bit_icv(self, rules):
        ledger = ClaimLedger.from_claims(_claim("esp.icv_len", (12, 16), tier=Tier.INFERRED_SIDE_CHANNEL))
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "truncated_96_bit_icv" for f in result.findings)

    def test_128_bit_only_icv_does_not_fire_truncated_rule(self, rules):
        ledger = ClaimLedger.from_claims(_claim("esp.icv_len", (16,), tier=Tier.INFERRED_SIDE_CHANNEL))
        result = evaluate_rules(ledger, rules)
        assert not any(f.rule_id == "truncated_96_bit_icv" for f in result.findings)

    def test_null_encryption(self, rules):
        ledger = ClaimLedger.from_claims(_claim("esp.null_encryption_confirmed", True, tier=Tier.INFERRED_SIDE_CHANNEL))
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "null_encryption" for f in result.findings)

    def test_ah_in_use(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ah.detected", True))
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "ah_in_use" for f in result.findings)

    def test_weak_ike_sa_cipher(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike_sa.encryption", {"transform_id": 3, "key_length": None}))
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "weak_ike_sa_cipher" for f in result.findings)

    def test_strong_ike_sa_cipher_does_not_fire(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike_sa.encryption", {"transform_id": 20, "key_length": 256}))
        result = evaluate_rules(ledger, rules)
        assert not any(f.rule_id == "weak_ike_sa_cipher" for f in result.findings)

    def test_weak_ike_sa_integrity(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike_sa.integrity", 2))  # HMAC-SHA1-96
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "weak_ike_sa_integrity" for f in result.findings)


class TestMultipleMatchingClaimsPerRule:
    """Phase 5a review fix #3: evaluate_rules uses ClaimLedger.get_all(),
    not get() — a capture with several Child SA tunnels can produce
    several esp.granularity claims, and each one that trips a rule must
    surface as its own Finding, not collapse into a single one.
    """

    def test_two_esp_granularity_claims_from_different_spis_produce_two_findings(self, rules):
        # evidence stands in for the SPI-tunnel identity here: pipeline.py
        # already assigns each ESP tunnel's own frame numbers as a claim's
        # evidence (see engine.py's Finding.scope docstring), so two
        # claims from two different tunnels naturally carry two different
        # evidence tuples.
        ledger = ClaimLedger.from_claims(
            _claim("esp.granularity", 8, tier=Tier.INFERRED_SIDE_CHANNEL, evidence=(10, 11)),  # SPI 1's tunnel
            _claim("esp.granularity", 8, tier=Tier.INFERRED_SIDE_CHANNEL, evidence=(20, 21)),  # SPI 2's tunnel
        )
        result = evaluate_rules(ledger, rules)
        findings = [f for f in result.findings if f.rule_id == "sixty_four_bit_block_cipher_in_esp"]
        assert len(findings) == 2
        scopes = {f.scope for f in findings}
        assert scopes == {(10, 11), (20, 21)}
        assert result.checks_assessable >= 1

    def test_only_the_matching_claim_among_several_fires(self, rules):
        # One tunnel is weak (granularity 8), the other is not (16) — only
        # the weak one should produce a finding.
        ledger = ClaimLedger.from_claims(
            _claim("esp.granularity", 8, tier=Tier.INFERRED_SIDE_CHANNEL, evidence=(1,)),
            _claim("esp.granularity", 16, tier=Tier.INFERRED_SIDE_CHANNEL, evidence=(2,)),
        )
        result = evaluate_rules(ledger, rules)
        findings = [f for f in result.findings if f.rule_id == "sixty_four_bit_block_cipher_in_esp"]
        assert len(findings) == 1
        assert findings[0].scope == (1,)

    def test_single_claim_still_produces_a_single_finding(self, rules):
        # Regression guard: the common single-tunnel case must not
        # regress into duplicate findings.
        ledger = ClaimLedger.from_claims(_claim("esp.granularity", 8, tier=Tier.INFERRED_SIDE_CHANNEL))
        result = evaluate_rules(ledger, rules)
        findings = [f for f in result.findings if f.rule_id == "sixty_four_bit_block_cipher_in_esp"]
        assert len(findings) == 1

    def test_mixed_rule_counts_as_found_and_does_not_also_report_a_pass(self, rules):
        # A rule with one triggering claim and one clean claim (e.g. two
        # ESP tunnels, only one using a weak cipher) counts entirely under
        # "found" for the headline — the clean tunnel's claim isn't also
        # surfaced as a separate PassedCheck for the same rule. Disclosed
        # simplification (see engine.py's own amendment note); no real
        # capture available to this project has produced this mix yet.
        ledger = ClaimLedger.from_claims(
            _claim("esp.granularity", 8, tier=Tier.INFERRED_SIDE_CHANNEL, evidence=(1,)),
            _claim("esp.granularity", 16, tier=Tier.INFERRED_SIDE_CHANNEL, evidence=(2,)),
        )
        result = evaluate_rules(ledger, rules)
        assert any(f.rule_id == "sixty_four_bit_block_cipher_in_esp" for f in result.findings)
        assert not any(p.rule_id == "sixty_four_bit_block_cipher_in_esp" for p in result.passes)


class TestPassedCheck:
    """Item 2 of the Phase 6b review: a rule that's assessable and whose
    condition evaluates false for every qualifying claim is a third,
    positive outcome — PassedCheck — not silence.
    """

    def test_clean_capture_reports_passes_not_an_empty_findings_table(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim("ike_sa.dh_group", 19),  # strong group — passes weak_dh_group_negotiated
            _claim("ike.version", 2),  # IKEv2 — passes ikev1_in_use
        )
        result = evaluate_rules(ledger, rules)
        pass_ids = {p.rule_id for p in result.passes}
        assert "weak_dh_group_negotiated" in pass_ids
        assert "ikev1_in_use" in pass_ids
        assert result.findings == ()

    def test_passed_check_carries_tier_and_evidence(self, rules):
        ledger = ClaimLedger.from_claims(_claim("ike.version", 2, evidence=(5, 6)))
        result = evaluate_rules(ledger, rules)
        passed = next(p for p in result.passes if p.rule_id == "ikev1_in_use")
        assert passed.tier is Tier.OBSERVED
        assert passed.evidence == (5, 6)
        assert passed.scope == (5, 6)
        assert passed.title  # non-empty

    def test_found_plus_passed_plus_gap_equals_total(self, rules):
        ledger = ClaimLedger.from_claims(
            _claim("ike_sa.dh_group", 2),  # weak — a finding
            _claim("ike.version", 2),  # a pass
        )
        result = evaluate_rules(ledger, rules)
        assert result.checks_found + result.checks_passed + result.checks_gap == result.checks_total
        assert result.checks_found == 1
        assert result.checks_passed == 1
        assert result.checks_gap == 13


class TestRealCaptureIntegration:
    """Confirms the engine runs against claims actually produced by
    real captures in Phase 4's pipeline, not just hand-built fixtures.
    """

    def test_aes128ccm12_capture_yields_no_weak_findings(self):
        from pathlib import Path

        from ipsec_analyzer.protocol.ike_parse import extract_ike_sa_init_claims, parse_ike_messages

        captures = Path(__file__).resolve().parent.parent.parent / "captures"
        parsed = parse_ike_messages(str(captures / "ikev2-decrypt-aes256gcm16.pcap"))
        claims = extract_ike_sa_init_claims(parsed)
        ledger = ClaimLedger.from_claims(claims)
        result = evaluate_rules(ledger, load_default_rules())
        assert not any(f.rule_id in ("weak_ike_sa_cipher", "weak_ike_sa_integrity") for f in result.findings)

    def test_3des_capture_yields_weak_cipher_finding(self):
        from pathlib import Path

        from ipsec_analyzer.protocol.ike_parse import extract_ike_sa_init_claims, parse_ike_messages

        captures = Path(__file__).resolve().parent.parent.parent / "captures"
        parsed = parse_ike_messages(str(captures / "ikev2-decrypt-3des-sha1_160.pcap"))
        claims = extract_ike_sa_init_claims(parsed)
        ledger = ClaimLedger.from_claims(claims)
        result = evaluate_rules(ledger, load_default_rules())
        finding_ids = {f.rule_id for f in result.findings}
        assert "weak_ike_sa_cipher" in finding_ids
        assert "weak_ike_sa_integrity" in finding_ids  # SHA1
