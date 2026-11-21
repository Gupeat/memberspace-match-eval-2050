"""Acceptance runner for the match-ranking evaluation task.

It intentionally executes the real CLI, including the diagnostic run with hard
filters disabled, because the acceptance criterion is about the process exit
code, not only a unit-level return value.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
REPORT = ARTIFACTS / "ACCEPTANCE.md"


def display_command(command: list[str]) -> str:
    """Render a portable command for the evidence report.

    The interpreter is always sys.executable; the report must not leak the
    absolute local path, so show the portable prefix "python" instead.
    """
    return "python " + " ".join(command[1:])


def run(command: list[str], expected: int) -> dict:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    passed = result.returncode == expected
    return {
        "command": display_command(command),
        "expected": expected,
        "actual": result.returncode,
        "passed": passed,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def parse_last_json(stdout: str) -> dict:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {}


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []

    stats = run([sys.executable, "-m", "match_eval", "stats"], expected=0)
    stats_payload = parse_last_json(stats["stdout"])
    checks.append(
        {
            "id": "AC1",
            "title": "评测集需求条数 >= 50，统计脚本输出覆盖需求类型数",
            "passed": stats["passed"] and stats_payload.get("demands", 0) >= 50 and stats_payload.get("demand_type_count", 0) > 0,
            "evidence": "demands=" + str(stats_payload.get("demands")) + "; demand_type_count=" + str(stats_payload.get("demand_type_count")),
            "command": stats,
        }
    )

    metric_tests = run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_metric_hit_at_5.py",
            "tests/test_metric_ndcg_at_10.py",
            "tests/test_metric_filter_violations.py",
            "tests/test_metric_rationale_trace.py",
            "tests/test_metric_top5_concentration.py",
        ],
        expected=0,
    )
    checks.append(
        {
            "id": "AC2",
            "title": "每个指标函数都有单元测试",
            "passed": metric_tests["passed"],
            "evidence": metric_tests["stdout"].strip().splitlines()[-1] if metric_tests["stdout"].strip() else "no output",
            "command": metric_tests,
        }
    )

    diagnostic = run(
        [
            sys.executable,
            "-m",
            "match_eval",
            "evaluate",
            "--weights",
            "v2",
            "--no-hard-filter",
            "--report",
            "artifacts/diagnostic-no-filter.md",
        ],
        expected=2,
    )
    diagnostic_payload = parse_last_json(diagnostic["stdout"])
    checks.append(
        {
            "id": "AC3",
            "title": "硬过滤违规数 > 0 时退出码非 0",
            "passed": diagnostic["passed"] and diagnostic_payload.get("hard_filter_violations", 0) > 0,
            "evidence": "exit=" + str(diagnostic["actual"]) + "; hard_filter_violations=" + str(diagnostic_payload.get("hard_filter_violations")),
            "command": diagnostic,
        }
    )

    compare = run(
        [
            sys.executable,
            "-m",
            "match_eval",
            "compare",
            "--weights-a",
            "v1",
            "--weights-b",
            "v2",
            "--report",
            "artifacts/report-compare.md",
        ],
        expected=0,
    )
    compare_payload = parse_last_json(compare["stdout"])
    compare_path = ARTIFACTS / "report-compare.md"
    checks.append(
        {
            "id": "AC4",
            "title": "两个权重版本的对比示例报告",
            "passed": compare["passed"] and compare_path.is_file() and compare_payload.get("verdict") == "pass",
            "evidence": "report=artifacts/report-compare.md; verdict=" + str(compare_payload.get("verdict")),
            "command": compare,
        }
    )

    v1 = run(
        [sys.executable, "-m", "match_eval", "evaluate", "--weights", "v1", "--report", "artifacts/report-v1.md"],
        expected=0,
    )
    v2 = run(
        [sys.executable, "-m", "match_eval", "evaluate", "--weights", "v2", "--report", "artifacts/report-v2.md"],
        expected=0,
    )
    v1_payload = parse_last_json(v1["stdout"])
    v2_payload = parse_last_json(v2["stdout"])
    safe = (
        v1["passed"]
        and v2["passed"]
        and v1_payload.get("hard_filter_violations") == 0
        and v2_payload.get("hard_filter_violations") == 0
        and v1_payload.get("rationale_traceability") == 1.0
        and v2_payload.get("rationale_traceability") == 1.0
    )
    checks.append(
        {
            "id": "AC5",
            "title": "正式评测硬过滤违规为 0，理由可追溯率为 1.0",
            "passed": safe,
            "evidence": "v1 violations=" + str(v1_payload.get("hard_filter_violations"))
            + ", trace=" + str(v1_payload.get("rationale_traceability"))
            + "; v2 violations=" + str(v2_payload.get("hard_filter_violations"))
            + ", trace=" + str(v2_payload.get("rationale_traceability")),
            "commands": [v1, v2],
        }
    )

    full_tests = run([sys.executable, "-m", "pytest", "tests"], expected=0)
    checks.append(
        {
            "id": "AC6",
            "title": "全量单元测试通过",
            "passed": full_tests["passed"],
            "evidence": full_tests["stdout"].strip().splitlines()[-1] if full_tests["stdout"].strip() else "no output",
            "command": full_tests,
        }
    )

    all_passed = all(check["passed"] for check in checks)
    data_hashes = {
        name: hashlib.sha256((ROOT / "data" / name).read_bytes()).hexdigest()
        for name in (
            "companies.json",
            "supplies.json",
            "demands.json",
            "annotations.json",
            "editorial-signals.json",
        )
    }
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# 验收对照报告",
        "",
        "- 生成时间：" + timestamp,
        "- 结论：" + ("全部通过" if all_passed else "存在失败项"),
        "- 运行目录：.",
        "",
        "## 对照表",
        "",
        "| 编号 | 验收项 | 结果 | 证据 |",
        "| --- | --- | --- | --- |",
    ]
    for check in checks:
        lines.append(
            "| " + check["id"] + " | " + check["title"] + " | "
            + ("PASS" if check["passed"] else "FAIL") + " | " + check["evidence"] + " |"
        )
    lines.extend(["", "## 数据哈希（sha256）", ""])
    lines.append("| 文件 | sha256 |")
    lines.append("| --- | --- |")
    for name, digest in data_hashes.items():
        lines.append("| data/" + name + " | " + digest + " |")
    lines.extend(["", "## 命令与退出码", ""])
    for check in checks:
        lines.append("### " + check["id"])
        lines.append("")
        commands = check.get("commands")
        if commands is None:
            commands = [check["command"]]
        for command in commands:
            lines.append("- 命令：" + command["command"])
            lines.append("- 期望退出码：" + str(command["expected"]) + "；实际退出码：" + str(command["actual"]))
            if command["stderr"].strip():
                lines.append("- stderr 摘要：" + command["stderr"].strip().splitlines()[-1])
        lines.append("- 结果：" + ("PASS" if check["passed"] else "FAIL"))
        lines.append("")
    lines.extend(
        [
            "## 说明",
            "",
            "- AC3 的 no-filter 运行只用于证明违规时退出码非 0；它不是对外推荐结果。",
            "- 所有数据均为合成数据，不含真实联系人、金额或生产队列。",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("wrote", REPORT.relative_to(ROOT).as_posix())
    print("all_passed", all_passed)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())