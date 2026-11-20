"""Dedicated unit tests for top-5 concentration (rework item 3)."""

import pytest

from match_eval.metrics import top5_concentration


def test_top5_concentration_counts_and_hhi():
    result = top5_concentration(
        [
            ["a", "b", "c", "d", "e"],
            ["a", "b", "f", "g", "h"],
        ]
    )
    assert result["slots"] == 10
    assert result["unique_companies"] == 8
    assert result["top1_share"] == pytest.approx(0.2)
    assert result["hhi"] == pytest.approx(0.14)


def test_top5_concentration_empty_input():
    assert top5_concentration([]) == {"top1_share": 0.0, "hhi": 0.0, "unique_companies": 0, "slots": 0}
