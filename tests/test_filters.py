import pytest

from match_eval.filters import (
    HARD_FILTER_REASONS,
    build_filter_context,
    excluded_map,
    hard_filter_reason,
    reason_counts,
)
from match_eval.scoring import rank_demand


def test_filter_context_and_reason_set(dataset):
    context = build_filter_context(dataset)
    assert len(context.companies) == 40
    assert "c001" in context.active_supplies
    assert "c031" not in context.active_supplies
    demand = dataset.demands[0]
    reasons = excluded_map(context, demand)
    assert set(reasons.values()) <= set(HARD_FILTER_REASONS)
    assert "no_active_supply" in reasons.values()
    assert "self" in reasons.values()
    assert reason_counts(reasons)["self"] == 1


def test_rule_priority_not_accepting_and_no_supply(dataset):
    context = build_filter_context(dataset)
    demand = dataset.demands[0]
    assert hard_filter_reason(context, demand, context.companies["c005"]) == "not_accepting"
    assert hard_filter_reason(context, demand, context.companies["c031"]) == "no_active_supply"
    assert hard_filter_reason(context, demand, context.companies[demand.requester_company_id]) == "self"


def test_rejected_and_conflict_are_excluded(dataset):
    context = build_filter_context(dataset)
    for demand in dataset.demands:
        reasons = excluded_map(context, demand)
        for company_id in demand.rejected_company_ids:
            assert reasons[company_id] == "rejected"
        for negative in demand.should_not_recommend:
            assert negative.company_id in reasons
            assert reasons[negative.company_id] in {"not_accepting", "rejected", "conflict"}
        requester = context.companies[demand.requester_company_id]
        for other in requester.conflicts_with:
            assert reasons[other] == "conflict"


def test_ranked_results_never_contain_hard_excluded(dataset, weights_v2):
    context = build_filter_context(dataset)
    for demand in dataset.demands:
        ranked = rank_demand(dataset, demand, weights_v2, top_k=10, context=context)
        ranked_ids = [item["company_id"] for item in ranked]
        excluded = excluded_map(context, demand)
        assert not set(ranked_ids) & set(excluded)
        negative_ids = {negative.company_id for negative in demand.should_not_recommend}
        assert not set(ranked_ids) & negative_ids
        assert len(ranked) == 10


def test_positive_labels_are_eligible(dataset):
    context = build_filter_context(dataset)
    for demand in dataset.demands:
        reasons = excluded_map(context, demand)
        assert not set(demand.should_recommend) & set(reasons)
