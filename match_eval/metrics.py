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


def rationale_traceability(
    ranked_items: Sequence[dict[str, Any]],
    *,
    context: Any | None = None,
    demand: Any | None = None,
    companies: dict[str, Any] | None = None,
) -> float:
    """Share of rankings whose rationale matches the candidate's actual features.

    With only ranked_items this is a field-completeness check.  When context,
    demand and companies are supplied (the evaluation path), every rationale
    value is recomputed from the dataset: matched capabilities must be a subset
    of the candidate's effective capabilities and of the request, the three
    boolean feature claims must match features_for(), and active_supply_ids must
    equal the candidate's active supplies.  A fabricated or stale rationale
    therefore counts as untraceable.
    """
    if not ranked_items:
        return 0.0
    semantic = context is not None and demand is not None and companies is not None
    traceable = 0
    for item in ranked_items:
        rationale = item.get("rationale")
        if not isinstance(rationale, dict):
            continue
        if not (all(key in rationale for key in RATIONALE_KEYS) and isinstance(rationale.get("summary"), str) and rationale["summary"]):
            continue
        if not semantic:
            traceable += 1
            continue
        company = companies.get(str(item.get("company_id")))
        if company is None:
            continue
        from .scoring import features_for

        features = features_for(context, demand, company)
        supplies = context.active_supplies.get(company.id, ())
        if list(rationale.get("active_supply_ids", [])) != [supply.id for supply in supplies]:
            continue
        if bool(rationale.get("industry_match")) != bool(features["industry"]):
            continue
        if bool(rationale.get("region_match")) != bool(features["region"]):
            continue
        if bool(rationale.get("capacity_fit")) != bool(features["capacity"]):
            continue
        matched = rationale.get("matched_capabilities")
        if not isinstance(matched, list) or not all(isinstance(value, str) for value in matched):
            continue
        if set(matched) - set(demand.required_capabilities):
            continue
        effective = set(company.capabilities)
        for supply in supplies:
            effective.update(supply.capabilities)
        if set(matched) - effective:
            continue
        if features["capability"] > 0 and not matched:
            continue
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
