"""Command line entry point: python -m match_eval ..."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dataset import DEFAULT_DATA_DIR, dataset_stats, load_dataset
from .evaluate import evaluate
from .report import render_compare, render_evaluation
from .scoring import load_weights

REGRESSION_LIMIT = 0.02


def _write_report(path: str, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    return target


def _summary(result) -> dict:
    metrics = result.metrics
    return {
        "weights": result.weights.name,
        "demand_count": metrics["demand_count"],
        "demand_type_count": metrics["demand_type_count"],
        "hit_at_5": metrics["hit_at_5"],
        "ndcg_at_10": metrics["ndcg_at_10"],
        "hard_filter_violations": metrics["hard_filter_violations"],
        "rationale_traceability": metrics["rationale_traceability"],
        "top5_concentration": metrics["top5_concentration"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="match-eval", description="离线匹配排序评测")
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate", help="运行单个权重版本的评测")
    evaluate_parser.add_argument("--data", default=str(DEFAULT_DATA_DIR))
    evaluate_parser.add_argument("--weights", default="v2")
    evaluate_parser.add_argument("--report", default="artifacts/report.md")
    evaluate_parser.add_argument("--no-hard-filter", action="store_true", help="仅用于验证退出码；关闭硬过滤")
    evaluate_parser.add_argument("--top-k", type=int, default=10)

    compare_parser = sub.add_parser("compare", help="比较两个权重版本")
    compare_parser.add_argument("--data", default=str(DEFAULT_DATA_DIR))
    compare_parser.add_argument("--weights-a", default="v1")
    compare_parser.add_argument("--weights-b", default="v2")
    compare_parser.add_argument("--report", default="artifacts/report-compare.md")
    compare_parser.add_argument("--top-k", type=int, default=10)

    stats_parser = sub.add_parser("stats", help="输出数据集规模与需求类型覆盖")
    stats_parser.add_argument("--data", default=str(DEFAULT_DATA_DIR))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.data)
        if args.command == "stats":
            print(json.dumps(dataset_stats(dataset), ensure_ascii=False, sort_keys=True))
            return 0
        if args.command == "evaluate":
            weights = load_weights(args.weights)
            result = evaluate(
                dataset,
                weights,
                apply_hard_filters=not args.no_hard_filter,
                top_k=args.top_k,
            )
            report = render_evaluation(
                result,
                dataset,
                report_path=args.report,
                apply_hard_filters=not args.no_hard_filter,
            )
            target = _write_report(args.report, report)
            print(json.dumps({"report": str(target), **_summary(result)}, ensure_ascii=False, sort_keys=True))
            return 2 if result.metrics["hard_filter_violations"] > 0 else 0
        if args.command == "compare":
            left_weights = load_weights(args.weights_a)
            right_weights = load_weights(args.weights_b)
            left = evaluate(dataset, left_weights, top_k=args.top_k)
            right = evaluate(dataset, right_weights, top_k=args.top_k)
            report = render_compare(left, right, dataset, report_path=args.report)
            target = _write_report(args.report, report)
            regression = left.metrics["ndcg_at_10"] - right.metrics["ndcg_at_10"]
            payload = {
                "report": str(target),
                "left": _summary(left),
                "right": _summary(right),
                "ndcg_regression": round(regression, 6),
                "regression_limit": REGRESSION_LIMIT,
            }
            if left.metrics["hard_filter_violations"] > 0 or right.metrics["hard_filter_violations"] > 0:
                payload["verdict"] = "hard_filter_violation"
                print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                return 2
            if regression > REGRESSION_LIMIT:
                payload["verdict"] = "ndcg_regression"
                print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                return 3
            payload["verdict"] = "pass"
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0
    except (FileNotFoundError, ValueError) as exc:
        print("match-eval: " + str(exc), file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())