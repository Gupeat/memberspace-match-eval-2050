"""Dedicated unit tests for rationale traceability (rework item 3)."""

from match_eval.metrics import rationale_traceability


def item(summary="capabilities=design; industry=yes"):
    return {
        "company_id": "c1",
        "rationale": {
            "matched_capabilities": ["design"],
            "industry_match": True,
            "region_match": False,
            "capacity_fit": True,
            "active_supply_ids": ["s1"],
            "summary": summary,
        },
    }


def test_traceability_all_complete_is_one():
    assert rationale_traceability([item(), item()]) == 1.0


def test_traceability_missing_fields_is_zero():
    assert rationale_traceability([{"company_id": "c1", "rationale": {}}]) == 0.0


def test_traceability_empty_summary_is_zero():
    assert rationale_traceability([item("")]) == 0.0
