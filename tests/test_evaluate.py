from match_eval.evaluate import evaluate


def test_full_v2_evaluation(dataset, weights_v2):
    result = evaluate(dataset, weights_v2)
    metrics = result.metrics
    assert metrics["demand_count"] == 60
    assert metrics["demand_type_count"] == 8
    assert metrics["hit_at_5"] == 1.0
    assert metrics["ndcg_at_10"] >= 0.95
    assert metrics["hard_filter_violations"] == 0
    assert metrics["rationale_traceability"] == 1.0
    assert metrics["top5_concentration"]["slots"] == 300
    assert len(result.per_demand) == 60
    assert set(result.per_demand) == {demand.id for demand in dataset.demands}
    assert "demand_types" in result.to_dict()["dataset"]


def test_unfiltered_evaluation_reports_violations(dataset, weights_v2):
    result = evaluate(dataset, weights_v2, apply_hard_filters=False)
    assert result.metrics["hard_filter_violations"] > 0


def test_full_v1_evaluation_still_safe(dataset, weights_v1):
    result = evaluate(dataset, weights_v1)
    assert result.metrics["hard_filter_violations"] == 0
    assert result.metrics["rationale_traceability"] == 1.0
    assert result.metrics["hit_at_5"] == 1.0
