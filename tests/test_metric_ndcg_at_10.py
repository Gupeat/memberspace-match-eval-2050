"""Dedicated unit tests for NDCG@10 (rework item 3)."""

import math

import pytest

from match_eval.metrics import ndcg_at_k


def test_ndcg_at_10_perfect_ranking_is_one():
    assert ndcg_at_k([f"c{i}" for i in range(10)], {f"c{i}" for i in range(10)}, k=10) == pytest.approx(1.0)


def test_ndcg_at_10_known_partial_value():
    expected = (1.0 + 1.0 / math.log2(4)) / (1.0 + 1.0 / math.log2(3))
    assert ndcg_at_k(["a", "b", "c"], {"a", "c"}, k=3) == pytest.approx(expected)


def test_ndcg_at_10_penalises_relevant_item_below_cutoff():
    assert ndcg_at_k([f"x{i}" for i in range(10)] + ["a"], {"a"}, k=10) == 0.0
