import json

from match_eval.cli import main


def test_cli_evaluate_writes_report(tmp_path):
    report = tmp_path / "report.md"
    assert main(["evaluate", "--weights", "v1", "--report", str(report)]) == 0
    assert report.is_file()
    assert "匹配排序离线评测报告" in report.read_text(encoding="utf-8")


def test_cli_stats_has_type_count(capsys):
    assert main(["stats"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["demands"] == 60
    assert output["demand_type_count"] == 8


def test_cli_violations_exit_nonzero(tmp_path):
    report = tmp_path / "nofilter.md"
    assert main(["evaluate", "--weights", "v2", "--no-hard-filter", "--report", str(report)]) == 2
    assert "硬过滤违规数" in report.read_text(encoding="utf-8")


def test_cli_compare_pass_and_report(tmp_path):
    report = tmp_path / "compare.md"
    assert main(["compare", "--weights-a", "v1", "--weights-b", "v2", "--report", str(report)]) == 0
    assert "判定" in report.read_text(encoding="utf-8")


def test_cli_compare_regression_exit_nonzero(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "version": "bad",
                "description": "only region, expected regression",
                "weights": {"capability": 0.0, "industry": 0.0, "region": 1.0, "capacity": 0.0},
            }
        ),
        encoding="utf-8",
    )
    report = tmp_path / "regress.md"
    assert main(["compare", "--weights-a", "v1", "--weights-b", str(bad), "--report", str(report)]) == 3
    assert "退步" in report.read_text(encoding="utf-8")


def test_cli_missing_weights_returns_error(tmp_path):
    assert main(["evaluate", "--weights", "missing-version", "--report", str(tmp_path / "x.md")]) == 1
