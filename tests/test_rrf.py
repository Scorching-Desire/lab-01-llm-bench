import pytest

from bench.rrf import rrf


def test_one_based_ranks():
    assert rrf([["a", "b"]]) == [("a", 1 / 61), ("b", 1 / 62)]


def test_deterministic_ties_and_single_ranking_candidates():
    assert rrf([["a"], ["b"]]) == rrf([["b"], ["a"]])
    assert {key for key, _ in rrf([["a", "b"], ["a", "c"]])} == {"a", "b", "c"}
    with pytest.raises(ValueError):
        rrf([["a", "a"]])
