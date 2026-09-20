from ipsec_analyzer.core.claims import Claim, Tier
from ipsec_analyzer.core.ledger import ClaimLedger


def _claim(field, value=1, tier=Tier.OBSERVED, confidence=1.0, evidence=(1,)):
    return Claim(field=field, value=value, tier=tier, confidence=confidence, method="test", evidence=evidence)


class TestGet:
    def test_returns_matching_claim(self):
        c = _claim("esp.granularity", value=4)
        ledger = ClaimLedger(claims=(c,))
        assert ledger.get("esp.granularity") is c

    def test_returns_none_when_absent(self):
        ledger = ClaimLedger(claims=())
        assert ledger.get("esp.granularity") is None

    def test_returns_first_match_when_multiple_claims_share_a_field(self):
        c1 = _claim("esp.granularity", value=4, evidence=(1,))
        c2 = _claim("esp.granularity", value=8, evidence=(2,))
        ledger = ClaimLedger(claims=(c1, c2))
        assert ledger.get("esp.granularity") is c1


class TestGetAll:
    def test_returns_every_matching_claim(self):
        c1 = _claim("esp.granularity", value=4, evidence=(1,))
        c2 = _claim("esp.granularity", value=8, evidence=(2,))
        other = _claim("ike_sa.dh_group", value=14)
        ledger = ClaimLedger(claims=(c1, c2, other))
        assert ledger.get_all("esp.granularity") == (c1, c2)

    def test_returns_empty_tuple_when_absent(self):
        ledger = ClaimLedger(claims=())
        assert ledger.get_all("esp.granularity") == ()


class TestHasField:
    def test_true_when_present(self):
        ledger = ClaimLedger(claims=(_claim("ike.version"),))
        assert ledger.has_field("ike.version") is True

    def test_false_when_absent(self):
        ledger = ClaimLedger(claims=())
        assert ledger.has_field("ike.version") is False


class TestFromClaims:
    def test_flattens_single_claims_and_lists_and_drops_none(self):
        single = _claim("a")
        grouped = [_claim("b"), _claim("c")]
        ledger = ClaimLedger.from_claims(single, None, grouped, None)
        assert set(c.field for c in ledger.claims) == {"a", "b", "c"}

    def test_empty_input_yields_empty_ledger(self):
        ledger = ClaimLedger.from_claims(None, [], None)
        assert ledger.claims == ()
