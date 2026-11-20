"""Hard filters applied before ranking."""

from __future__ import annotations

from dataclasses import dataclass

from .dataset import Company, Dataset, Demand, Supply

HARD_FILTER_REASONS = (
    "self",
    "not_accepting",
    "rejected",
    "conflict",
    "no_active_supply",
)


@dataclass(frozen=True)
class FilterContext:
    companies: dict[str, Company]
    active_supplies: dict[str, tuple[Supply, ...]]


def build_filter_context(dataset: Dataset) -> FilterContext:
    return FilterContext(
        companies=dataset.company_map(),
        active_supplies=dataset.active_supplies_by_company(),
    )


def hard_filter_reason(
    context: FilterContext,
    demand: Demand,
    company: Company,
) -> str | None:
    if company.id == demand.requester_company_id:
        return "self"
    if not company.accepting:
        return "not_accepting"
    if company.id in demand.rejected_company_ids:
        return "rejected"
    requester = context.companies[demand.requester_company_id]
    if company.id in requester.conflicts_with or requester.id in company.conflicts_with:
        return "conflict"
    if not context.active_supplies.get(company.id):
        return "no_active_supply"
    return None


def excluded_map(
    context: FilterContext,
    demand: Demand,
    companies: tuple[Company, ...] | None = None,
) -> dict[str, str]:
    source = companies if companies is not None else tuple(context.companies.values())
    result: dict[str, str] = {}
    for company in source:
        reason = hard_filter_reason(context, demand, company)
        if reason is not None:
            result[company.id] = reason
    return result


def reason_counts(reasons: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reason in reasons.values():
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))
