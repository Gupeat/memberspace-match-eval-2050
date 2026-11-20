"""End-to-end evaluation over the frozen synthetic dataset."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .dataset import Dataset, dataset_stats
from .filters import build_filter_context, excluded_map, reason_counts
from .metrics import (
    hard_filter_violations,
    hit_at_k,
    mean,
    ndcg_at_k,
    rationale_traceability,
    top5_concentration,
)
from .scoring import Weights, rank_demand


@dataclass(frozen=True)
class EvaluationResult:
    weights: Weights
    dataset_stats: dict[str, Any]
    metrics: dict[str, Any]
    hard_filter_reason_counts: dict[str, int]
    rankings: dict[str, list[dict[str, Any]]]
    per_demand: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": {
                "version": self.weights.name,
                "values": self.weights.values,
            },
            "dataset": self.dataset_stats,
            "metrics": self.metrics,
            "hard_filter_reason_counts": self.hard_filter_reason_counts,
        }


def evaluate(
    dataset: Dataset,
    weights: Weights,
    apply_hard_filters: bool = True,
    top_k: int = 10,
) -> EvaluationResult:
    if top_k < 10:
        raise ValueError("top_k must be at least 10 for NDCG@10")
    context = build_filter_context(dataset)
    stats = dataset_stats(dataset)
    rankings: dict[str, list[dict[str, Any]]] = {}
    per_demand: dict[str, dict[str, Any]] = {}
    hit_scores: list[float] = []
    ndcg_scores: list[float] = []
    trace_scores: list[float] = []
    total_violations = 0
    reason_totals: dict[str, int] = {}

    for demand in dataset.demands:
        ranked = rank_demand(
            dataset,
            demand,
            weights,
            apply_hard_filters=apply_hard_filters,
            top_k=top_k,
            context=context,
        )
        ranked_ids = [item["company_id"] for item in ranked]
        excluded = excluded_map(context, demand)
        for reason, count in reason_counts(excluded).items():
            reason_totals[reason] = reason_totals.get(reason, 0) + count
        violations = hard_filter_violations(ranked_ids, excluded)
        total_violations += violations
        hit = hit_at_k(ranked_ids, demand.should_recommend, k=5)
        ndcg = ndcg_at_k(ranked_ids, demand.should_recommend, k=10)
        trace = rationale_traceability(ranked)
        hit_scores.append(hit)
        ndcg_scores.append(ndcg)
        trace_scores.append(trace)
        rankings[demand.id] = ranked
        per_demand[demand.id] = {
            "type": demand.type,
            "title": demand.title,
            "hit_at_5": hit,
            "ndcg_at_10": round(ndcg, 6),
            "hard_filter_violations": violations,
            "rationale_traceability": round(trace, 6),
            "top5": ranked_ids[:5],
        }

    concentration = top5_concentration(
        [item["company_id"] for item in rankings[demand.id]]
        for demand in dataset.demands
    )
    metrics = {
        "demand_count": len(dataset.demands),
        "demand_type_count": stats["demand_type_count"],
        "demand_types": stats["demand_types"],
        "hit_at_5": round(mean(hit_scores), 6),
        "ndcg_at_10": round(mean(ndcg_scores), 6),
        "hard_filter_violations": total_violations,
        "rationale_traceability": round(mean(trace_scores), 6),
        "top5_concentration": concentration,
        "evaluated_ranking_size": top_k,
    }
    return EvaluationResult(
        weights=weights,
        dataset_stats=stats,
        metrics=metrics,
        hard_filter_reason_counts=dict(sorted(reason_totals.items())),
        rankings=rankings,
        per_demand=per_demand,
    )
