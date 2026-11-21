from match_eval.evaluate import evaluate
from match_eval.report import render_compare, render_evaluation


def test_evaluation_report_contains_required_sections(dataset, weights_v1):
    result = evaluate(dataset, weights_v1)
    report = render_evaluation(result, dataset)
    assert "# 匹配排序离线评测报告" in report
    assert "覆盖需求类型数" in report
    assert "硬过滤违规数" in report
    assert "理由可追溯率" in report
    assert "前 5 名集中度" in report
    assert "排序样例" in report
    for demand_type in result.metrics["demand_types"]:
        assert demand_type in report


def test_compare_report_has_both_versions_and_verdict(dataset, weights_v1, weights_v2):
    left = evaluate(dataset, weights_v1)
    right = evaluate(dataset, weights_v2)
    report = render_compare(left, right, dataset)
    assert "权重版本对比报告" in report
    assert "判定" in report
    assert "NDCG@10" in report
    assert "v1" in report and "v2" in report


def test_diagnostic_report_reproduces_its_own_command(dataset, weights_v2):
    result = evaluate(dataset, weights_v2, apply_hard_filters=False)
    report = render_evaluation(
        result,
        dataset,
        report_path="artifacts/diagnostic-no-filter.md",
        apply_hard_filters=False,
    )
    assert "--no-hard-filter" in report
    assert "--report artifacts/diagnostic-no-filter.md" in report
    assert "artifacts/report-v2.md" not in report


def test_render_is_deterministic(dataset, weights_v2):
    result = evaluate(dataset, weights_v2)
    first = render_evaluation(result, dataset)
    second = render_evaluation(result, dataset)
    assert first == second
    assert len(first.encode("utf-8")) > 1000
