"""Markdown reports for one weight version and for a two-version comparison."""

from __future__ import annotations

from typing import Any

from .dataset import Dataset
from .evaluate import EvaluationResult


def _metric_rows(result: EvaluationResult) -> list[str]:
    metrics = result.metrics
    concentration = metrics["top5_concentration"]
    return [
        "| 指标 | 值 | 目标/说明 |",
        "| --- | ---: | --- |",
        "| 需求条数 | " + str(metrics["demand_count"]) + " | 至少 50 |",
        "| 覆盖需求类型数 | " + str(metrics["demand_type_count"]) + " | 统计脚本输出 |",
        "| Hit@5 | " + f"{metrics['hit_at_5']:.4f}" + " | 有至少一个应推荐进入前 5 的需求占比 |",
        "| NDCG@10 | " + f"{metrics['ndcg_at_10']:.4f}" + " | 二值相关性，应推荐=1 |",
        "| 硬过滤违规数 | " + str(metrics["hard_filter_violations"]) + " | 目标 0；大于 0 时退出码非 0 |",
        "| 理由可追溯率 | " + f"{metrics['rationale_traceability']:.4f}" + " | 目标 1.0000 |",
        "| 前 5 名集中度 HHI | " + f"{concentration['hhi']:.4f}" + " | 所有需求前 5 名公司分布 |",
        "| 前 5 名最高公司占比 | " + f"{concentration['top1_share']:.4f}" + " | 观察值，不设硬门槛 |",
        "| 前 5 名覆盖公司数 | " + str(concentration["unique_companies"]) + " | 观察值 |",
    ]


def render_evaluation(result: EvaluationResult, dataset: Dataset) -> str:
    stats = result.dataset_stats
    lines = [
        "# 匹配排序离线评测报告（" + result.weights.name + "）",
        "",
        "本报告由 match-eval 从冻结的合成数据生成；数据与标注不含真实企业、真实联系人或生产数据。",
        "",
        "## 数据规模",
        "",
        "| 项目 | 数量 |",
        "| --- | ---: |",
        "| 虚构企业 | " + str(stats["companies"]) + " |",
        "| 供给条目 | " + str(stats["supplies"]) + " |",
        "| 其中活跃供给 | " + str(stats["active_supplies"]) + " |",
        "| 需求条目 | " + str(stats["demands"]) + " |",
        "| 应推荐标注数 | " + str(stats["positive_labels"]) + " |",
        "| 不应推荐标注数 | " + str(stats["negative_labels"]) + " |",
        "",
        "## 权重版本",
        "",
        "| 特征 | 权重 |",
        "| --- | ---: |",
    ]
    for key, value in result.weights.values.items():
        lines.append("| " + key + " | " + f"{value:.2f}" + " |")
    lines.extend(
        [
            "",
            "权重文件：" + result.weights.name + "；描述：" + (result.weights.description or "（未填写）"),
            "",
            "## 指标",
            "",
            *_metric_rows(result),
            "",
            "## 需求类型覆盖",
            "",
            "| 类型 | 需求数 |",
            "| --- | ---: |",
        ]
    )
    for demand_type, count in result.metrics["demand_types"].items():
        lines.append("| " + demand_type + " | " + str(count) + " |")
    lines.extend(
        [
            "",
            "## 硬过滤排除统计",
            "",
            "统计每个需求被排除的候选企业次数，按原因汇总：",
            "",
            "| 原因 | 次数 |",
            "| --- | ---: |",
        ]
    )
    if result.hard_filter_reason_counts:
        for reason, count in result.hard_filter_reason_counts.items():
            lines.append("| " + reason + " | " + str(count) + " |")
    else:
        lines.append("| 无 | 0 |")
    lines.extend(
        [
            "",
            "## 排序样例",
            "",
            "以下展示前 3 个需求的前 5 名；应推荐标注以 * 标记。",
            "",
        ]
    )
    for demand in dataset.demands[:3]:
        positives = set(demand.should_recommend)
        per = result.per_demand[demand.id]
        lines.append("### " + demand.id + " · " + demand.title)
        lines.append("")
        lines.append("类型：" + demand.type + "；需求方：" + demand.requester_company_id + "；可推荐标注：" + ", ".join(demand.should_recommend))
        lines.append("")
        lines.append("| 排名 | 公司 | 分数 | 理由摘要 | 标注 |")
        lines.append("| ---: | --- | ---: | --- | --- |")
        for position, item in enumerate(result.rankings[demand.id][:5], start=1):
            mark = "应推荐 *" if item["company_id"] in positives else "未标注"
            lines.append(
                "| " + str(position)
                + " | " + item["company_id"]
                + " | " + f"{item['score']:.4f}"
                + " | " + item["rationale"]["summary"]
                + " | " + mark + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## 结论",
            "",
            "硬过滤违规目标为 0；理由可追溯率目标为 1.0000；"
            "本报告只用于离线评测，不写入生产 AI 队列、不触发对外联系、不涉及金额。",
            "",
            "复现命令：python -m match_eval evaluate --weights " + result.weights.name
            + " --report artifacts/report-" + result.weights.name + ".md",
            "",
        ]
    )
    return "\n".join(lines)


def render_compare(
    left: EvaluationResult,
    right: EvaluationResult,
    dataset: Dataset,
) -> str:
    left_metrics = left.metrics
    right_metrics = right.metrics
    regression = round(left_metrics["ndcg_at_10"] - right_metrics["ndcg_at_10"], 6)
    lines = [
        "# 匹配排序权重版本对比报告",
        "",
        "本报告比较两个权重版本的离线评测结果；数据、标注和排序流程相同，仅权重不同。",
        "",
        "## 版本",
        "",
        "| 版本 | capability | industry | region | capacity |",
        "| --- | ---: | ---: | ---: | ---: |",
        "| " + left.weights.name + " | " + f"{left.weights.values['capability']:.2f}" + " | "
        + f"{left.weights.values['industry']:.2f}" + " | " + f"{left.weights.values['region']:.2f}" + " | "
        + f"{left.weights.values['capacity']:.2f}" + " |",
        "| " + right.weights.name + " | " + f"{right.weights.values['capability']:.2f}" + " | "
        + f"{right.weights.values['industry']:.2f}" + " | " + f"{right.weights.values['region']:.2f}" + " | "
        + f"{right.weights.values['capacity']:.2f}" + " |",
        "",
        "## 指标对比",
        "",
        "| 指标 | " + left.weights.name + " | " + right.weights.name + " | 差值（右-左） |",
        "| --- | ---: | ---: | ---: |",
        "| Hit@5 | " + f"{left_metrics['hit_at_5']:.4f}" + " | " + f"{right_metrics['hit_at_5']:.4f}"
        + " | " + f"{right_metrics['hit_at_5'] - left_metrics['hit_at_5']:+.4f}" + " |",
        "| NDCG@10 | " + f"{left_metrics['ndcg_at_10']:.4f}" + " | " + f"{right_metrics['ndcg_at_10']:.4f}"
        + " | " + f"{right_metrics['ndcg_at_10'] - left_metrics['ndcg_at_10']:+.4f}" + " |",
        "| 硬过滤违规数 | " + str(left_metrics["hard_filter_violations"]) + " | "
        + str(right_metrics["hard_filter_violations"]) + " | "
        + str(right_metrics["hard_filter_violations"] - left_metrics["hard_filter_violations"]) + " |",
        "| 理由可追溯率 | " + f"{left_metrics['rationale_traceability']:.4f}" + " | "
        + f"{right_metrics['rationale_traceability']:.4f}" + " | "
        + f"{right_metrics['rationale_traceability'] - left_metrics['rationale_traceability']:+.4f}" + " |",
        "",
        "## 判定",
        "",
        "- NDCG@10 退步（左-右）：" + f"{regression:+.4f}" + "；允许退步上限 0.0200。",
        "- 硬过滤违规：" + str(left_metrics["hard_filter_violations"]) + " / " + str(right_metrics["hard_filter_violations"]) + "；目标均为 0。",
    ]
    if right_metrics["hard_filter_violations"] > 0:
        lines.append("- 结论：不通过，右侧版本存在硬过滤违规，退出码 2。")
    elif regression > 0.02:
        lines.append("- 结论：不通过，右侧版本 NDCG@10 退步超过 2 个百分点，退出码 3。")
    else:
        lines.append("- 结论：通过，右侧版本无硬过滤违规且 NDCG@10 未出现超过 2 个百分点的退步，退出码 0。")
    lines.extend(
        [
            "",
            "## 需求类型覆盖",
            "",
            "| 类型 | 需求数 |",
            "| --- | ---: |",
        ]
    )
    for demand_type, count in left_metrics["demand_types"].items():
        lines.append("| " + demand_type + " | " + str(count) + " |")
    lines.append("")
    lines.append("对比命令：python -m match_eval compare --weights-a " + left.weights.name
                 + " --weights-b " + right.weights.name + " --report artifacts/report-compare.md")
    lines.append("")
    return "\n".join(lines)
