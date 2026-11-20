import math

import pytest

from match_eval.metrics import (
    hard_filter_violations,
    hit_at_k,
    mean,
    ndcg_at_k,
    rationale_traceability,
    top5_concentration,
)


def test_hit_at_k():
    assert hit_at_k(["a", "b", "c"], {"c"}, k=3) == 1.0
    assert hit_at_k(["a", "b", "c"], {"c"}, k=2) == 0.0
    assert hit_at_k([], {"a"}, k=5) == 0.0


def test_ndcg_at_k_known_value():
    expected = (1.0 + 1.0 / math.log2(4)) / (1.0 + 1.0 / math.log2(3))
    assert ndcg_at_k(["a", "b", "c"], {"a", "c"}, k=3) == pytest.approx(expected)
    assert ndcg_at_k(["a", "b", "c"], {"a", "b", "c"}, k=3) == pytest.approx(1.0)
    assert ndcg_at_k([], {"a"}, k=10) == 0.0


def test_ndcg_binary_relevance_ignores_unlabeled():
    assert ndcg_at_k(["x", "a"], {"a"}, k=2) == pytest.approx(1.0 / math.log2(3))
    assert ndcg_at_k(["a", "x"], {"a"}, k=2) == pytest.approx(1.0)


def test_hard_filter_violations():
    assert hard_filter_violations(["a", "b", "c"], {"b"}) == 1
    assert hard_filter_violations(["a", "b"], {"x"}) == 0


def _item(company_id, summary="capabilities=design; industry=yes"):
    return {
        "company_id": company_id,
        "rationale": {
            "matched_capabilities": ["design"],
            "industry_match": True,
            "region_match": False,
            "capacity_fit": True,
            "active_supply_ids": ["s1"],
            "summary": summary,
        },
    }


def test_rationale_traceability():
    assert rationale_traceability([_item("a"), _item("b")]) == 1.0
    assert rationale_traceability([_item("a"), {"company_id": "b", "rationale": {}}]) == 0.5
    assert rationale_traceability([_item("a", summary="")]) == 0.0
    assert rationale_traceability([]) == 0.0


def test_top5_concentration():
    result = top5_concentration(
        [
            ["a", "b", "c", "d", "e"],
            ["a", "b", "f", "g", "h"],
        ]
    )
    assert result["slots"] == 10
    assert result["unique_companies"] == 8
    assert result["top1_share"] == pytest.approx(0.2)
    assert result["hhi"] == pytest.approx(4 / 100 + 4 / 100 + 6 / 100)
    assert top5_concentration([])["slots"] == 0


def test_mean():
    assert mean([1.0, 0.0]) == 0.5
    assert mean([]) == 0.0
