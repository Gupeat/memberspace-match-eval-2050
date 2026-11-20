"""Dedicated unit tests for Hit@5 (rework item 3)."""

from match_eval.metrics import hit_at_k


def test_hit_at_5_true_when_relevant_in_top_five():
    assert hit_at_k(["a", "b", "c", "d", "e"], {"e"}, k=5) == 1.0


def test_hit_at_5_false_when_relevant_below_top_five():
    assert hit_at_k(["a", "b", "c", "d", "e", "f"], {"f"}, k=5) == 0.0


def test_hit_at_5_handles_empty_ranking():
    assert hit_at_k([], {"a"}, k=5) == 0.0
