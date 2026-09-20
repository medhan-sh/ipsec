from ipsec_analyzer.core.constants import (
    ADDITIONAL_KEY_EXCHANGE,
    IKE_SA_INIT_FULL_TRANSCRIPT_AUTH,
    PPK_IDENTITY_KEY,
    PPK_SUPPORT,
    SUITE_FRAMINGS,
    SuiteFraming,
)


def test_at_least_35_suites():
    assert len(SUITE_FRAMINGS) >= 35


def test_every_suite_has_an_rfc_reference():
    for suite_id, framing in SUITE_FRAMINGS.items():
        assert framing.rfc.strip(), f"{suite_id} has no RFC reference"


def test_suite_ids_are_unique_and_match_keys():
    for suite_id, framing in SUITE_FRAMINGS.items():
        assert framing.suite_id == suite_id


def test_family_is_cbc_or_counter():
    for suite_id, framing in SUITE_FRAMINGS.items():
        assert framing.family in ("cbc", "counter"), f"{suite_id} has unknown family {framing.family!r}"


def test_cbc_suites_have_matching_iv_and_pad_granularity():
    for suite_id, framing in SUITE_FRAMINGS.items():
        if framing.family == "cbc":
            assert framing.explicit_iv == framing.pad_granularity, (
                f"{suite_id}: CBC explicit_iv should equal block size (pad_granularity)"
            )
            assert framing.explicit_iv in (8, 16), f"{suite_id}: unexpected CBC block size"


def test_counter_suites_have_4_byte_pad_granularity():
    for suite_id, framing in SUITE_FRAMINGS.items():
        if framing.family == "counter":
            assert framing.pad_granularity == 4, f"{suite_id}: counter family should pad to 4 bytes"


def test_all_icv_lens_positive():
    for suite_id, framing in SUITE_FRAMINGS.items():
        assert framing.icv_len > 0, f"{suite_id} has non-positive icv_len"


def test_suiteframing_is_frozen():
    s = next(iter(SUITE_FRAMINGS.values()))
    try:
        s.icv_len = 999
        assert False, "SuiteFraming should be immutable"
    except AttributeError:
        pass


def test_notify_type_constants_are_distinct_positive_ints():
    notify_types = {
        IKE_SA_INIT_FULL_TRANSCRIPT_AUTH,
        ADDITIONAL_KEY_EXCHANGE,
        PPK_SUPPORT,
        PPK_IDENTITY_KEY,
    }
    assert len(notify_types) == 4, "notify type constants must be distinct"
    assert all(isinstance(n, int) and n > 0 for n in notify_types)
