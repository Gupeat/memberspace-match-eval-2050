"""Deterministic weighted scorer and rationale generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .dataset import Company, Dataset, Demand
from .filters import FilterContext, build_filter_context, hard_filter_reason

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS_DIR = PACKAGE_ROOT / "weights"
FEATURE_KEYS = ("capability", "industry", "region", "capacity")
CAPACITY_RANK = {"small": 0, "medium": 1, "large": 2}


@dataclass(frozen=True)
class Weights:
    name: str
    description: str
    values: dict[str, float]

    @property
    def total(self) -> float:
        return sum(self.values.values())


def load_weights(source: str | Path, base_dir: str | Path | None = None) -> Weights:
    root = Path(base_dir) if base_dir is not None else DEFAULT_WEIGHTS_DIR
    candidate = Path(source)
    if not candidate.is_file():
        candidate = root / str(source)
        if candidate.suffix != ".json":
            candidate = candidate.with_suffix(".json")
    if not candidate.is_file():
        raise FileNotFoundError("weights file not found: " + str(source))
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    name = str(payload.get("version") or candidate.stem)
    description = str(payload.get("description", ""))
    raw = payload.get("weights")
    if not isinstance(raw, dict):
        raise ValueError("weights file must contain a weights object")
    values: dict[str, float] = {}
    for key in FEATURE_KEYS:
        value = raw.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError("weight " + key + " must be a non-negative number")
        values[key] = float(value)
    unknown = set(raw) - set(FEATURE_KEYS)
    if unknown:
        raise ValueError("unknown weight keys: " + ", ".join(sorted(unknown)))
    total = sum(values.values())
    if total <= 0:
        raise ValueError("weights must have a positive sum")
    if abs(total - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1.0 (got " + str(total) + ")")
    return Weights(name=name, description=description, values=values)


def _active_supplies_for(
    context: FilterContext,
    company: Company,
) -> tuple:
    return context.active_supplies.get(company.id, ())


def features_for(
    context: FilterContext,
    demand: Demand,
    company: Company,
) -> dict[str, float]:
    supplies = _active_supplies_for(context, company)
    capabilities = set(company.capabilities)
    industries = set(company.industries)
    for supply in supplies:
        capabilities.update(supply.capabilities)
        industries.update(supply.industries)
    required = set(demand.required_capabilities)
    capability = len(required & capabilities) / len(required)
    industry = 1.0 if set(demand.preferred_industries) & industries else 0.0
    region = 1.0 if company.region == demand.region else 0.0
    capacity = 1.0 if CAPACITY_RANK[company.capacity] >= CAPACITY_RANK[demand.capacity_need] else 0.0
    return {
        "capability": capability,
        "industry": industry,
        "region": region,
        "capacity": capacity,
    }


def score_company(
    context: FilterContext,
    demand: Demand,
    company: Company,
    weights: Weights,
) -> tuple[float, dict[str, Any]]:
    features = features_for(context, demand, company)
    score = sum(weights.values[key] * features[key] for key in FEATURE_KEYS) / weights.total
    supplies = _active_supplies_for(context, company)
    matched = sorted(set(demand.required_capabilities) & set(company.capabilities))
    if not matched:
        for supply in supplies:
            matched.extend(sorted(set(demand.required_capabilities) & set(supply.capabilities)))
    matched = sorted(set(matched))
    rationale = {
        "matched_capabilities": matched,
        "industry_match": bool(features["industry"]),
        "region_match": bool(features["region"]),
        "capacity_fit": bool(features["capacity"]),
        "active_supply_ids": [supply.id for supply in supplies],
        "summary": (
            "capabilities=" + (",".join(matched) if matched else "none")
            + "; industry=" + ("yes" if features["industry"] else "no")
            + "; region=" + ("yes" if features["region"] else "no")
            + "; capacity=" + ("yes" if features["capacity"] else "no")
            + "; supplies=" + (",".join(supply.id for supply in supplies) if supplies else "none")
        ),
    }
    return round(score, 6), rationale


def rank_demand(
    dataset: Dataset,
    demand: Demand,
    weights: Weights,
    apply_hard_filters: bool = True,
    top_k: int = 10,
    context: FilterContext | None = None,
) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    context = context or build_filter_context(dataset)
    ranked: list[dict[str, Any]] = []
    for company in dataset.companies:
        if apply_hard_filters and hard_filter_reason(context, demand, company) is not None:
            continue
        score, rationale = score_company(context, demand, company, weights)
        ranked.append(
            {
                "company_id": company.id,
                "score": score,
                "rationale": rationale,
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["company_id"]))
    return ranked[:top_k]