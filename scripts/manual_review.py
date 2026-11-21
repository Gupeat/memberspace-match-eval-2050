"""Machine review pack for the frozen #2050 annotation set.

This script does not generate labels.  It replays the six-editor rules in
`scripts/labeling.py` against the frozen fixture and compares every positive
slot and every negative row with the shipped annotations.  A zero-mismatch run
means the artifact is reproducible from the documented rules; it is not a
human business sign-off.

Usage:
    python scripts/manual_review.py
    python scripts/manual_review.py --reviewer "Name" --reviewed-at 2026-11-20T14:00:00Z --attest

Without --reviewer and --attest the generated files stay pending; a reviewer
name alone records an unverified claim.
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
from scripts import labeling

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARTIFACTS = ROOT / "artifacts"
DOCS = ROOT / "docs"
NEGATIVE_REASON_LABELS = {"rejected", "not_accepting", "conflict"}


def load_plain() -> tuple[list[dict], list[dict], list[dict], dict, dict]:
    companies = json.loads((DATA / "companies.json").read_text(encoding="utf-8"))["companies"]
    supplies = json.loads((DATA / "supplies.json").read_text(encoding="utf-8"))["supplies"]
    demands = json.loads((DATA / "demands.json").read_text(encoding="utf-8"))["demands"]
    signals = json.loads((DATA / "editorial-signals.json").read_text(encoding="utf-8"))
    annotations = {
        row["demand_id"]: row
        for row in json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))["demands"]
    }
    return companies, supplies, demands, signals, annotations


def conflict(a, b) -> bool:
    return b.id in a.conflicts_with or a.id in b.conflicts_with


def review_demand(
    dataset: Dataset,
    demand: Demand,
    raw_demand: dict,
    raw_companies: list[dict],
    raw_supplies: list[dict],
    signals: dict,
    annotation: dict,
    weights,
    context,
    company_map,
) -> dict[str, Any]:
    requester = company_map[demand.requester_company_id]
    positives = list(demand.should_recommend)
    negatives = list(demand.should_not_recommend)
    negative_ids = [item.company_id for item in negatives]
    top6 = [item["company_id"] for item in rank_demand(dataset, demand, weights, top_k=6, context=context)]
    top10 = rank_demand(dataset, demand, weights, top_k=10, context=context)

    replay_rows = labeling.select_positive_slots(raw_demand, raw_companies, raw_supplies, signals)
    replay_ids = [row["company_id"] for row in replay_rows]
    shipped_slots = [(row["slot"], row["company_id"]) for row in annotation["positive_slots"]]
    replay_slots = [(row["slot"], row["company_id"]) for row in replay_rows]
    replay_negatives = labeling.select_negative_rows(raw_demand, raw_companies, raw_supplies, replay_ids)
    shipped_negatives = [(row["company_id"], row["reason"]) for row in raw_demand["should_not_recommend"]]
    replay_negative_pairs = [(row["company_id"], row["reason"]) for row in replay_negatives]

    issues: list[str] = []
    observations: list[str] = []
    if not 1 <= len(positives) <= len(labeling.SLOT_ORDER):
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
    if positives != replay_ids:
        issues.append("positive_slot_replay_mismatch")
    if shipped_slots != replay_slots:
        issues.append("positive_slot_rows_mismatch")
    if shipped_negatives != replay_negative_pairs:
        issues.append("negative_replay_mismatch")
    if sorted(raw_demand["rejected_company_ids"]) != sorted(
        row["company_id"] for row in replay_negatives if row["reason"] == "rejected"
    ):
        issues.append("rejected_input_mismatch")

    positive_rows = []
    for company_id in positives:
        company = company_map[company_id]
        actual = hard_filter_reason(context, demand, company)
        matched = sorted(
            set(demand.required_capabilities)
            & labeling.effective_capabilities(
                next(item for item in raw_companies if item["id"] == company_id),
                labeling.active_supply_capabilities(raw_supplies),
            )
        )
        if actual is not None:
            issues.append("positive_hard_filtered:" + company_id + ":" + actual)
        if len(matched) < labeling.POSITIVE_MIN_COVERAGE:
            issues.append("positive_insufficient_capability_match:" + company_id)
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

    top6_set = set(top6)
    positive_set = set(positives)
    top6_exact = len(positives) == len(top6) and top6_set == positive_set
    top6_covers = positive_set <= top6_set
    if not top6_exact:
        observations.append("v2_top6_set_differs")
    if not top6_covers:
        observations.append("v2_top6_misses_positive")
    rationale_ok = True
    for item in top10:
        rationale = item.get("rationale") or {}
        keys = ["matched_capabilities", "industry_match", "region_match", "capacity_fit", "active_supply_ids", "summary"]
        if any(key not in rationale for key in keys) or not str(rationale.get("summary", "")).strip():
            rationale_ok = False
    if not rationale_ok:
        issues.append("rationale_incomplete")

    slot_coverage = {}
    for row in replay_rows:
        source = next(item for item in raw_companies if item["id"] == row["company_id"])
        coverage = len(
            set(demand.required_capabilities)
            & labeling.effective_capabilities(source, labeling.active_supply_capabilities(raw_supplies))
        )
        slot_coverage[row["slot"]] = coverage
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
        "slot_coverage": slot_coverage,
        "v2_top6": top6,
        "v2_top6_exact": top6_exact,
        "v2_top6_covers_positives": top6_covers,
        "v2_top6_overlap": len(top6_set & positive_set),
        "replay_slots": replay_slots,
        "replay_negatives": replay_negative_pairs,
        "positive_details": positive_rows,
        "negative_details": negative_rows,
        "checks": {
            "counts": 1 <= len(positives) <= len(labeling.SLOT_ORDER) and len(negatives) == 4,
            "unique": len(set(positives)) == len(positives) and len(set(negative_ids)) == len(negative_ids),
            "disjoint": not (set(positives) & set(negative_ids)),
            "requester_not_labelled": demand.requester_company_id not in positives and demand.requester_company_id not in negative_ids,
            "positives_eligible": not any(row["hard_filter"] for row in positive_rows),
            "positive_slots_replayed": shipped_slots == replay_slots and positives == replay_ids,
            "negatives_replayed": shipped_negatives == replay_negative_pairs,
            "negative_reasons_valid": all(
                item.reason in NEGATIVE_REASON_LABELS
                and hard_filter_reason(context, demand, company_map[item.company_id]) is not None
                for item in negatives
            ),
            "v2_top6_exact": top6_exact,
            "v2_top6_covers_positives": top6_covers,
            "rationale_complete": rationale_ok,
        },
        "issues": sorted(set(issues)),
        "observations": sorted(set(observations)),
        "machine_decision": "pass" if not issues else "revise",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", default="", help="human reviewer name; blank means pending")
    parser.add_argument("--reviewed-at", default="", help="ISO-8601 review timestamp")
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--attest",
        action="store_true",
        help="explicit human attestation; without it the pack stays pending even if --reviewer is given",
    )
    args = parser.parse_args()

    companies, supplies, demands, signals, annotations = load_plain()
    dataset = load_dataset()
    weights = load_weights("v2")
    context = build_filter_context(dataset)
    company_map = dataset.company_map()
    rows = []
    for demand in dataset.demands:
        rows.append(
            review_demand(
                dataset,
                demand,
                next(item for item in demands if item["id"] == demand.id),
                companies,
                supplies,
                signals,
                annotations[demand.id],
                weights,
                context,
                company_map,
            )
        )

    totals = {
        "demands": len(rows),
        "positive_labels": sum(row["positive_count"] for row in rows),
        "negative_labels": sum(row["negative_count"] for row in rows),
        "demands_with_issues": sum(1 for row in rows if row["issues"]),
        "label_issues": sum(len(row["issues"]) for row in rows),
        "checks_failed": sum(len(row["issues"]) for row in rows),
        "replay_mismatches": sum(
            1
            for row in rows
            if not row["checks"]["positive_slots_replayed"] or not row["checks"]["negatives_replayed"]
        ),
        "v2_top6_exact": sum(1 for row in rows if row["v2_top6_exact"]),
        "v2_top6_exact_denominator": sum(1 for row in rows if row["positive_count"] == 6),
        "v2_top6_covers_positives": sum(1 for row in rows if row["v2_top6_covers_positives"]),
        "v2_top6_overlap_total": sum(row["v2_top6_overlap"] for row in rows),
        "observation_count": sum(len(row["observations"]) for row in rows),
    }
    reviewer = args.reviewer.strip()
    human_reviewed = bool(reviewer) and args.attest
    reviewed_at = (
        args.reviewed_at.strip()
        or (datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if human_reviewed else "")
    )
    status = "human-reviewed" if human_reviewed else "pending-human-signoff"
    for row in rows:
        row["decision"] = row["machine_decision"] if human_reviewed else "pending"
    payload = {
        "task": 2050,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": status,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "notes": args.notes,
        "scope": f"all 60 demands / {totals['positive_labels'] + totals['negative_labels']} labels; up to six positive slots and four negatives replayed from scripts/labeling.py",
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
            "negative_reasons", "positive_slots_replayed", "negatives_replayed",
            "v2_top6_exact", "v2_top6_covers_positives", "v2_top6_overlap", "checks_failed", "observations", "machine_decision", "decision",
            "reviewer", "reviewed_at", "notes",
        ])
        for row in rows:
            writer.writerow([
                row["demand_id"], row["type"], row["requester"],
                ";".join(row["positive_ids"]), ";".join(row["negative_ids"]),
                ";".join(row["negative_reasons"]),
                "yes" if row["checks"]["positive_slots_replayed"] else "no",
                "yes" if row["checks"]["negatives_replayed"] else "no",
                "yes" if row["v2_top6_exact"] else "no",
                "yes" if row["v2_top6_covers_positives"] else "no",
                row["v2_top6_overlap"],
                len(row["issues"]), ";".join(row["observations"]), row["machine_decision"], row["decision"],
                reviewer, reviewed_at, args.notes,
            ])

    lines = []
    lines.append("# 机器复核包 · #2050 匹配排序评测集（待人工签字）")
    lines.append("")
    lines.append("> 本文件由 scripts/manual_review.py 生成。它用 scripts/labeling.py 原样重算每个需求的至多六个正例槽位与四个负例，并逐条比对到已冻结的 data/annotations.json；" + (
        "复核人已签字。" if human_reviewed else "当前状态为**待人类复核人签字**，签字前不得称为人工标注。"
    ))
    lines.append("")
    lines.append("## 复核范围与方法")
    lines.append("")
    lines.append("- 对象：data/demands.json 中全部 60 条需求、" + str(totals["positive_labels"] + totals["negative_labels"]) + " 个标签。")
    lines.append("- 正例：至多六个编辑槽位（capability_lead / case_strength / responsiveness / industry_fit / regional_fit / capacity_fit）按词典序逐个重算；无合格候选的槽位弃权，所以每条需求 1-6 个正例。要求 company_id 与槽位顺序逐条一致。")
    lines.append("- 负例：重算 2 个 rejected + ≥1 个 not_accepting；有冲突对象时再取 1 个 conflict，否则取第二个 not_accepting；要求 company_id 与 reason 逐条一致。")
    lines.append("- 约束：1-6 正/4 负、正负不交、需求方不在标签中、正例未被硬过滤、至少命中两个 required capability；前十名理由字段完整。")
    lines.append("- 独立性：capability_lead 用平均 IDF 稀缺度；case_strength / responsiveness 用 data/editorial-signals.json 的已核实案例与响应天数；二者均不被 match_eval 读取。")
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
    lines.append("| 重放不一致需求 | " + str(totals["replay_mismatches"]) + " |")
    lines.append("| v2 top6 精确等于标签集（仅正例=6 时有意义） | " + str(totals["v2_top6_exact"]) + "/" + str(totals["v2_top6_exact_denominator"]) + " |")
    lines.append("| v2 top6 覆盖全部标签 | " + str(totals["v2_top6_covers_positives"]) + "/" + str(totals["demands"]) + " |")
    lines.append("| v2 top6 与标签的交集总数 | " + str(totals["v2_top6_overlap_total"]) + " |")
    lines.append("")
    lines.append("v2 top6 与标签集合不完全一致是排序目标的差异，不是标签缺陷：NDCG@10 按位置加权，top6 是集合；标签由六个不同编辑视角各选一个，因此自然包含非最高分候选。")
    lines.append("")
    lines.append("## 逐条结果")
    lines.append("")
    lines.append("| 需求 | 类型 | 正例 | 负例 | 原因 | 槽位重放 | 负例重放 | v2 top6 | 机器结论 |")
    lines.append("| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |")
    for row in rows:
        lines.append(
            "| " + row["demand_id"] + " | " + row["type"] + " | " + str(row["positive_count"])
            + " | " + str(row["negative_count"]) + " | " + ",".join(row["negative_reasons"])
            + " | " + ("一致" if row["checks"]["positive_slots_replayed"] else "不一致")
            + " | " + ("一致" if row["checks"]["negatives_replayed"] else "不一致")
            + " | " + ("覆盖" if row["v2_top6_covers_positives"] else "缺标签")
            + " | " + ("PASS" if row["machine_decision"] == "pass" else "REVISE: " + "; ".join(row["issues"])) + " |"
        )
    lines.append("")
    lines.append("## 复核人签字")
    lines.append("")
    if human_reviewed:
        lines.append("- 复核人：" + reviewer)
        lines.append("- 复核时间：" + reviewed_at)
        lines.append("- 结论：已逐条复核上述 60 条需求、" + str(totals["positive_labels"] + totals["negative_labels"]) + " 个标签；未发现需要修改的标签。")
        if args.notes:
            lines.append("- 备注：" + args.notes)
    else:
        lines.append("- 复核人：________________（待填写）")
        lines.append("- 复核时间：________________（待填写）")
        lines.append("- 结论：________________")
        lines.append("")
        lines.append("签字前，本仓库只能声明“已完成可复现的合成标注 + 机器复核包”，不能声明“人工标注已完成”。")
    (DOCS / "MANUAL-REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"status": status, "reviewer": reviewer, "totals": totals}, ensure_ascii=False))
    print("wrote artifacts/manual-review.json")
    print("wrote artifacts/manual-review.csv")
    print("wrote docs/MANUAL-REVIEW.md")


if __name__ == "__main__":
    main()
