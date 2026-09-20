import inspect

from ipsec_analyzer.core.candidates import CandidateSet, eliminate, rank


class TestCandidateSetEliminate:
    def _universe(self):
        ids = frozenset({"A", "B", "C", "D"})
        return CandidateSet(universe=ids, surviving=ids, eliminated_by=())

    def test_eliminate_removes_candidates(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A", "B"}, "framing arithmetic ruled out A, B")
        assert cs2.surviving == frozenset({"C", "D"})

    def test_eliminate_records_human_readable_derivation(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A"}, "gcd(g)=16 excludes counter-mode A")
        assert ("A", "gcd(g)=16 excludes counter-mode A") in cs2.eliminated_by

    def test_eliminate_does_not_resurrect_previously_eliminated(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A"}, "reason 1")
        cs3 = eliminate(cs2, {"B"}, "reason 2")
        assert cs3.surviving == frozenset({"C", "D"})
        assert len(cs3.eliminated_by) == 2

    def test_eliminate_returns_new_candidateset_not_mutating_original(self):
        cs = self._universe()
        cs2 = eliminate(cs, {"A"}, "reason")
        assert cs.surviving == frozenset({"A", "B", "C", "D"})
        assert cs2 is not cs


class TestRank:
    def _universe(self):
        ids = frozenset({"A", "B", "C"})
        return CandidateSet(universe=ids, surviving=frozenset({"A", "B"}), eliminated_by=())

    def test_rank_returns_a_list(self):
        cs = self._universe()
        result = rank(cs, {"A": 0.9, "B": 0.1})
        assert isinstance(result, list)

    def test_rank_drops_scores_outside_surviving(self):
        cs = self._universe()
        result = rank(cs, {"A": 0.9, "B": 0.1, "C": 0.99})
        assert {suite for suite, _ in result} == {"A", "B"}

    def test_rank_orders_descending_by_score(self):
        cs = self._universe()
        result = rank(cs, {"A": 0.1, "B": 0.9})
        assert result == [("B", 0.9), ("A", 0.1)]

    def test_rank_never_constructs_a_candidateset(self):
        source = inspect.getsource(rank)
        assert "CandidateSet(" not in source
