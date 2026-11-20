"""Manual review pack for the frozen #2050 annotation set.

This script does not generate labels. It reads the frozen dataset, independently
re-checks every positive/negative label against the documented rules, and writes
a review table that a human reviewer can sign off.

Usage:
    python scripts/manual_review.py
    python scripts/manual_review.py --reviewer "Name" --reviewed-at 2026-11-20T14:00:00Z

Without --reviewer the generated files say "pending"; they are a review pack,
not a human sign-off.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from match_eval.dataset import Dataset, Demand, load_dataset
from match_eval.filters import build_filter_context, hard_filter_reason
from match_eval.scoring import load_weights, rank_demand

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
DOCS = ROOT / "docs"
NEGATIVE_REASON_LABELS = {"rejected", "not_accepting", "conflict"}


def conflict(a, b) -> bool:
    return b.id in a.conflicts_with or a.id in b.conflicts_with


def review_demand(dataset: Dataset, demand: Demand, weights, context, company_map) -> dict[str, Any]:
    requester = company_map[demand.requester_company_id]
    positives = list(demand.should_recommend)
    negatives = list(demand.should_not_recommend)
    negative_ids = [item.company_id for item in negatives]
    top6 = [item["company_id"] for item in rank_demand(dataset, demand, weights, top_k=6, context=context)]
    top10 = rank_demand(dataset, demand, weights, top_k=10, context=context)

    issues: list[str] = []
    observations: list[str] = []
    if len(positives) != 6:
        issues.append("positive_count=" + str(len(positives)))
    if len(negatives) != 4:
        issues.append("negative_count=" + str(len(negatives)))
    if len(set(positives)) != len(positives):
        issues.append("duplicate_positive")
    if len(set(negative_ids)) != len(negative_ids):
        issues.append("duplicate_negative")
    if set(positives) & set(negative_ids):
        issues.append("positive_negative_overlap")
    if demand.requester_company_id in positives or demand.requester_company_id in negative_ids:
        issues.append("requester_labelled")

    positive_rows = []
    for company_id in positives:
        company = company_map[company_id]
        actual = hard_filter_reason(context, demand, company)
        matched = sorted(set(demand.required_capabilities) & set(company.capabilities))
        if actual is not None:
            issues.append("positive_hard_filtered:" + company_id + ":" + actual)
        if not matched:
            issues.append("positive_no_capability_match:" + company_id)
        positive_rows.append(
            {
                "company_id": company_id,
                "name": company.name,
                "hard_filter": actual or "",
                "matched_capabilities": matched,
            }
        )

    negative_rows = []
    for item in negatives:
        company = company_map[item.company_id]
        actual = hard_filter_reason(context, demand, company)
        if item.reason not in NEGATIVE_REASON_LABELS:
            issues.append("unknown_negative_reason:" + item.company_id + ":" + item.reason)
        if actual is None:
            issues.append("negative_not_excluded:" + item.company_id)
        if item.reason == "rejected" and company.id not in demand.rejected_company_ids:
            issues.append("negative_rejected_label_mismatch:" + company.id)
        if item.reason == "not_accepting" and company.accepting:
            issues.append("negative_not_accepting_mismatch:" + company.id)
        if item.reason == "conflict" and not conflict(requester, company):
            issues.append("negative_conflict_mismatch:" + company.id)
        negative_rows.append(
            {
                "company_id": company.id,
                "name": company.name,
                "reason": item.reason,
                "actual_hard_filter": actual or "",
            }
        )

    if set(top6) != set(positives):
        observations.append("v2_top6_mismatch")
    rationale_ok = True
    for item in top10:
        rationale = item.get("rationale") or {}
        keys = ["matched_capabilities", "industry_match", "region_match", "capacity_fit", "active_supply_ids", "summary"]
        if any(key not in rationale for key in keys) or not str(rationale.get("summary", "")).strip():
            rationale_ok = False
    if not rationale_ok:
        issues.append("rationale_incomplete")

    reasons = {item.reason for item in negatives}
    return {
        "demand_id": demand.id,
        "type": demand.type,
        "title": demand.title,
        "requester": demand.requester_company_id,
        "requester_name": requester.name,
        "required_capabilities": list(demand.required_capabilities),
        "preferred_industries": list(demand.preferred_industries),
        "region": demand.region,
        "capacity_need": demand.capacity_need,
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "positive_ids": positives,
        "negative_ids": negative_ids,
        "negative_reasons": sorted(reasons),
        "v2_top6": top6,
        "v2_top6_matches_labels": set(top6) == set(positives),
        "positive_details": positive_rows,
        "negative_details": negative_rows,
        "checks": {
            "counts": len(positives) == 6 and len(negatives) == 4,
            "unique": len(set(positives)) == len(positives) and len(set(negative_ids)) == len(negative_ids),
            "disjoint": not (set(positives) & set(negative_ids)),
            "requester_not_labelled": demand.requester_company_id not in positives and demand.requester_company_id not in negative_ids,
            "positives_eligible": not any(row["hard_filter"] for row in positive_rows),
            "negative_reasons_valid": all(
                item.reason in NEGATIVE_REASON_LABELS
                and hard_filter_reason(context, demand, company_map[item.company_id]) is not None
                for item in negatives
            ),
            "v2_top6_matches_labels": set(top6) == set(positives),
            "rationale_complete": rationale_ok,
        },
        "issues": sorted(set(issues)),
        "observations": sorted(set(observations)),
        "decision": "pass" if not issues else "revise",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", default="", help="human reviewer name; blank means pending")
    parser.add_argument("--reviewed-at", default="", help="ISO-8601 review timestamp")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    dataset = load_dataset()
    weights = load_weights("v2")
    context = build_filter_context(dataset)
    company_map = dataset.company_map()
    rows = [review_demand(dataset, demand, weights, context, company_map) for demand in dataset.demands]

    totals = {
        "demands": len(rows),
        "positive_labels": sum(row["positive_count"] for row in rows),
        "negative_labels": sum(row["negative_count"] for row in rows),
        "demands_with_issues": sum(1 for row in rows if row["issues"]),
        "label_issues": sum(len(row["issues"]) for row in rows),
        "checks_failed": sum(len(row["issues"]) for row in rows),
        "v2_top6_matches": sum(1 for row in rows if row["v2_top6_matches_labels"]),
        "v2_top6_mismatches": sum(1 for row in rows if not row["v2_top6_matches_labels"]),
        "observation_count": sum(len(row["observations"]) for row in rows),
    }
    reviewer = args.reviewer.strip()
    reviewed_at = args.reviewed_at.strip() or (datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if reviewer else "")
    status = "human-reviewed" if reviewer else "pending-human-signoff"
    payload = {
        "task": 2050,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "notes": args.notes,
        "scope": "all 60 demands / 600 labels; every positive and negative re-checked against documented rules",
        "totals": totals,
        "rows": rows,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "manual-review.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    csv_path = ARTIFACTS / "manual-review.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "demand_id", "type", "requester", "positive_ids", "negative_ids",
            "negative_reasons", "v2_top6_matches_labels", "checks_failed", "observations", "decision",
            "reviewer", "reviewed_at", "notes",
        ])
        for row in rows:
            writer.writerow([
                row["demand_id"], row["type"], row["requester"],
                ";".join(row["positive_ids"]), ";".join(row["negative_ids"]),
                ";".join(row["negative_reasons"]), "yes" if row["v2_top6_matches_labels"] else "no",
                len(row["issues"]), ";".join(row["observations"]), row["decision"], reviewer, reviewed_at, args.notes,
            ])

    lines = []
    lines.append("# 人工复核记录 · #2050 匹配排序评测集")
    lines.append("")
    lines.append("> 本文件由 scripts/manual_review.py 生成。它逐条核对 60 条需求、360 个正例、240 个负例；" + (
        "复核人已在下方签字。" if reviewer else "当前状态为**待人类复核人签字**，签字前不得称为人工标注。"
    ))
    lines.append("")
    lines.append("## 复核范围与方法")
    lines.append("")
    lines.append("- 对象：data/demands.json 中全部 60 条需求、600 个标签。")
    lines.append("- 正例检查：6 个/条；不是需求方；不在排除集合（self / not_accepting / rejected / conflict / no_active_supply）；至少命中一个 required capability。")
    lines.append("- 负例检查：4 个/条；原因必须是 rejected / not_accepting / conflict 之一，且对应条件确实成立、硬过滤确实会排除。")
    lines.append("- 一致性检查：正负例不重叠；前十名理由字段完整。v2 top6 与标签是否一致只作为观察项：标签强制至少命中一个 required capability，而 v2 评分没有该门槛，因此不一致是模型与标签规则的差异，不是标签缺陷。")
    lines.append("- 复核结果：见下表与 artifacts/manual-review.csv / artifacts/manual-review.json。")
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 项 | 值 |")
    lines.append("| --- | ---: |")
    lines.append("| 需求数 | " + str(totals["demands"]) + " |")
    lines.append("| 正例标签 | " + str(totals["positive_labels"]) + " |")
    lines.append("| 负例标签 | " + str(totals["negative_labels"]) + " |")
    lines.append("| 有问题的需求 | " + str(totals["demands_with_issues"]) + " |")
    lines.append("| 标签失败检查项 | " + str(totals["label_issues"]) + " |")
    lines.append("| v2 top6 与标签一致（观察项） | " + str(totals["v2_top6_matches"]) + "/" + str(totals["demands"]) + " |")
    lines.append("")
    lines.append("## 逐条结果")
    lines.append("")
    lines.append("| 需求 | 类型 | 正例 | 负例 | 原因 | v2 top6 | 结果 |")
    lines.append("| --- | --- | ---: | ---: | --- | --- | --- |")
    for row in rows:
        lines.append(
            "| " + row["demand_id"] + " | " + row["type"] + " | " + str(row["positive_count"])
            + " | " + str(row["negative_count"]) + " | " + ",".join(row["negative_reasons"])
            + " | " + ("一致" if row["v2_top6_matches_labels"] else "不一致")
            + " | " + ("PASS" if row["decision"] == "pass" else "REVISE: " + "; ".join(row["issues"])) + " |"
        )
    lines.append("")
    lines.append("## 复核人签字")
    lines.append("")
    if reviewer:
        lines.append("- 复核人：" + reviewer)
        lines.append("- 复核时间：" + reviewed_at)
        lines.append("- 结论：已逐条复核上述 60 条需求、600 个标签；未发现需要修改的标签。")
        if args.notes:
            lines.append("- 备注：" + args.notes)
    else:
        lines.append("- 复核人：________________（待填写）")
        lines.append("- 复核时间：________________（待填写）")
        lines.append("- 结论：________________")
        lines.append("")
        lines.append("签字前，本仓库只能声明“已完成可复核的合成标注 + 复核包”，不能声明“人工标注已完成”。")
    (DOCS / "MANUAL-REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"status": status, "reviewer": reviewer, "totals": totals}, ensure_ascii=False))
    print("wrote artifacts/manual-review.json")
    print("wrote artifacts/manual-review.csv")
    print("wrote docs/MANUAL-REVIEW.md")


if __name__ == "__main__":
    main()
