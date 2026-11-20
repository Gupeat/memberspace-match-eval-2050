"""Dedicated unit tests for hard-filter violation counting (rework item 3)."""

from match_eval.metrics import hard_filter_violations


def test_violations_count_every_excluded_id_in_ranking():
    assert hard_filter_violations(["a", "b", "c", "d"], {"b", "d"}) == 2


def test_violations_zero_when_no_excluded_id_returned():
    assert hard_filter_violations(["a", "b"], {"x", "y"}) == 0


def test_violations_empty_ranking():
    assert hard_filter_violations([], {"a"}) == 0
