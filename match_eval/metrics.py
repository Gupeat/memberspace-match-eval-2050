"""Metric functions used by the evaluation report and unit tests."""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

RATIONALE_KEYS = (
    "matched_capabilities",
    "industry_match",
    "region_match",
    "capacity_fit",
    "active_supply_ids",
    "summary",
)


def hit_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int = 5) -> float:
    relevant = set(relevant_ids)
    return 1.0 if any(company_id in relevant for company_id in ranked_ids[:k]) else 0.0


def ndcg_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int = 10) -> float:
    relevant = set(relevant_ids)
    dcg = 0.0
    for position, company_id in enumerate(ranked_ids[:k], start=1):
        if company_id in relevant:
            dcg += 1.0 / math.log2(position + 1)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(position + 1) for position in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def hard_filter_violations(ranked_ids: Sequence[str], excluded_ids: Iterable[str]) -> int:
    excluded = set(excluded_ids)
    return sum(1 for company_id in ranked_ids if company_id in excluded)


def rationale_traceability(ranked_items: Sequence[dict[str, Any]]) -> float:
    if not ranked_items:
        return 0.0
    traceable = 0
    for item in ranked_items:
        rationale = item.get("rationale")
        if not isinstance(rationale, dict):
            continue
        if all(key in rationale for key in RATIONALE_KEYS) and isinstance(rationale.get("summary"), str) and rationale["summary"]:
            traceable += 1
    return traceable / len(ranked_items)


def top5_concentration(ranked_lists: Iterable[Sequence[str]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    total = 0
    for ranked in ranked_lists:
        for company_id in ranked[:5]:
            counts[company_id] = counts.get(company_id, 0) + 1
            total += 1
    if total == 0:
        return {"top1_share": 0.0, "hhi": 0.0, "unique_companies": 0, "slots": 0}
    shares = [count / total for count in counts.values()]
    return {
        "top1_share": round(max(shares), 6),
        "hhi": round(sum(share * share for share in shares), 6),
        "unique_companies": len(counts),
        "slots": total,
        "counts": dict(sorted(counts.items())),
    }


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
