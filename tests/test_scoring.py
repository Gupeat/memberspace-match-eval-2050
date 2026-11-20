import json

import pytest

from match_eval.filters import build_filter_context
from match_eval.scoring import (
    FEATURE_KEYS,
    Weights,
    features_for,
    load_weights,
    rank_demand,
    score_company,
)


def test_weights_files_load(dataset, weights_v1, weights_v2):
    assert weights_v1.name == "v1"
    assert weights_v2.name == "v2"
    assert set(weights_v1.values) == set(FEATURE_KEYS)
    assert weights_v1.total == pytest.approx(1.0)
    assert weights_v2.total == pytest.approx(1.0)


def test_rank_demand_is_sorted_and_explainable(dataset, weights_v2):
    context = build_filter_context(dataset)
    demand = dataset.demands[0]
    ranked = rank_demand(dataset, demand, weights_v2, context=context, top_k=10)
    assert len(ranked) == 10
    scores = [item["score"] for item in ranked]
    assert scores == sorted(scores, reverse=True)
    for item in ranked:
        assert item["company_id"]
        assert 0.0 <= item["score"] <= 1.0
        rationale = item["rationale"]
        assert rationale["summary"]
        assert rationale["matched_capabilities"] == sorted(rationale["matched_capabilities"])
        assert isinstance(rationale["industry_match"], bool)
        assert isinstance(rationale["region_match"], bool)
        assert isinstance(rationale["capacity_fit"], bool)
        assert isinstance(rationale["active_supply_ids"], list)


def test_features_are_bounded(dataset):
    context = build_filter_context(dataset)
    demand = dataset.demands[0]
    for company in dataset.companies:
        features = features_for(context, demand, company)
        assert set(features) == set(FEATURE_KEYS)
        assert all(0.0 <= value <= 1.0 for value in features.values())


def test_hard_filter_can_be_disabled_for_diagnostics(dataset, weights_v2):
    demand = dataset.demands[0]
    filtered = rank_demand(dataset, demand, weights_v2, apply_hard_filters=True, top_k=10)
    unfiltered = rank_demand(dataset, demand, weights_v2, apply_hard_filters=False, top_k=10)
    assert filtered != unfiltered


def test_weights_validation(tmp_path):
    def write(payload):
        path = tmp_path / "w.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    with pytest.raises(ValueError):
        load_weights(write({"version": "bad", "weights": {"capability": -1, "industry": 0, "region": 0, "capacity": 0}}))
    with pytest.raises(ValueError):
        load_weights(write({"version": "bad", "weights": {"capability": 1, "industry": 0, "region": 0, "capacity": 0, "extra": 1}}))
    with pytest.raises(ValueError):
        load_weights(write({"version": "bad", "weights": {"capability": 0, "industry": 0, "region": 0, "capacity": 0}}))
    with pytest.raises(ValueError):
        load_weights(write({"version": "bad", "weights": {"capability": 0.5, "industry": 0.2, "region": 0.2, "capacity": 0.05}}))


def test_score_company_uses_weights(dataset):
    context = build_filter_context(dataset)
    demand = dataset.demands[0]
    company = dataset.companies[0]
    a = Weights("a", "", {"capability": 0.25, "industry": 0.25, "region": 0.25, "capacity": 0.25})
    b = Weights("b", "", {"capability": 1.0, "industry": 0.0, "region": 0.0, "capacity": 0.0})
    score_a, _ = score_company(context, demand, company, a)
    score_b, _ = score_company(context, demand, company, b)
    assert 0.0 <= score_a <= 1.0
    assert 0.0 <= score_b <= 1.0
    assert score_a != score_b