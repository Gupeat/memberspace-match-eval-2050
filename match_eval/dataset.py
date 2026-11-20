"""Dataset loading and structural validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PACKAGE_ROOT / "data"
CAPACITIES = {"small", "medium", "large"}
NEGATIVE_REASONS = {"rejected", "not_accepting", "conflict"}


@dataclass(frozen=True)
class Company:
    id: str
    name: str
    summary: str
    capabilities: tuple[str, ...]
    industries: tuple[str, ...]
    region: str
    capacity: str
    accepting: bool
    conflicts_with: tuple[str, ...]


@dataclass(frozen=True)
class Supply:
    id: str
    company_id: str
    title: str
    summary: str
    capabilities: tuple[str, ...]
    industries: tuple[str, ...]
    region: str
    capacity: str
    status: str


@dataclass(frozen=True)
class Negative:
    company_id: str
    reason: str


@dataclass(frozen=True)
class Demand:
    id: str
    type: str
    title: str
    summary: str
    requester_company_id: str
    required_capabilities: tuple[str, ...]
    preferred_industries: tuple[str, ...]
    region: str
    capacity_need: str
    rejected_company_ids: tuple[str, ...]
    should_recommend: tuple[str, ...]
    should_not_recommend: tuple[Negative, ...]
    annotation_note: str


@dataclass(frozen=True)
class Dataset:
    companies: tuple[Company, ...]
    supplies: tuple[Supply, ...]
    demands: tuple[Demand, ...]

    def company_map(self) -> dict[str, Company]:
        return {company.id: company for company in self.companies}

    def demand_map(self) -> dict[str, Demand]:
        return {demand.id: demand for demand in self.demands}

    def active_supplies_by_company(self) -> dict[str, tuple[Supply, ...]]:
        result: dict[str, list[Supply]] = {}
        for supply in self.supplies:
            if supply.status != "active":
                continue
            result.setdefault(supply.company_id, []).append(supply)
        return {key: tuple(value) for key, value in result.items()}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError("dataset file not found: " + str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON in " + str(path) + ": " + str(exc)) from exc
    if not isinstance(payload, dict):
        raise ValueError("dataset root must be an object: " + str(path))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported schema_version in " + str(path))
    return payload


def _require_string(item: dict[str, Any], key: str, where: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(where + " requires a non-empty string field " + key)
    return value


def _require_string_list(item: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = item.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(entry, str) and entry for entry in value):
        raise ValueError(where + " requires a non-empty string array field " + key)
    return tuple(value)


def _optional_string_list(item: dict[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = item.get(key, [])
    if not isinstance(value, list) or not all(isinstance(entry, str) and entry for entry in value):
        raise ValueError(where + " requires a string array field " + key)
    return tuple(value)


def _require_bool(item: dict[str, Any], key: str, where: str) -> bool:
    value = item.get(key)
    if not isinstance(value, bool):
        raise ValueError(where + " requires a boolean field " + key)
    return value


def _unique_ids(items: list[Any], label: str) -> None:
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate " + label + " id")
    if not ids:
        raise ValueError("no " + label + " entries")


def load_dataset(data_dir: str | Path = DEFAULT_DATA_DIR) -> Dataset:
    root = Path(data_dir)
    companies_payload = _read_json(root / "companies.json")
    supplies_payload = _read_json(root / "supplies.json")
    demands_payload = _read_json(root / "demands.json")

    companies: list[Company] = []
    for raw in companies_payload.get("companies", []):
        if not isinstance(raw, dict):
            raise ValueError("company entry must be an object")
        company_id = _require_string(raw, "id", "company")
        companies.append(
            Company(
                id=company_id,
                name=_require_string(raw, "name", company_id),
                summary=_require_string(raw, "summary", company_id),
                capabilities=_require_string_list(raw, "capabilities", company_id),
                industries=_require_string_list(raw, "industries", company_id),
                region=_require_string(raw, "region", company_id),
                capacity=_require_string(raw, "capacity", company_id),
                accepting=_require_bool(raw, "accepting", company_id),
                conflicts_with=_optional_string_list(raw, "conflicts_with", company_id),
            )
        )
    _unique_ids(companies, "company")

    supplies: list[Supply] = []
    for raw in supplies_payload.get("supplies", []):
        if not isinstance(raw, dict):
            raise ValueError("supply entry must be an object")
        supply_id = _require_string(raw, "id", "supply")
        supplies.append(
            Supply(
                id=supply_id,
                company_id=_require_string(raw, "company_id", supply_id),
                title=_require_string(raw, "title", supply_id),
                summary=_require_string(raw, "summary", supply_id),
                capabilities=_require_string_list(raw, "capabilities", supply_id),
                industries=_require_string_list(raw, "industries", supply_id),
                region=_require_string(raw, "region", supply_id),
                capacity=_require_string(raw, "capacity", supply_id),
                status=_require_string(raw, "status", supply_id),
            )
        )
    _unique_ids(supplies, "supply")

    demands: list[Demand] = []
    for raw in demands_payload.get("demands", []):
        if not isinstance(raw, dict):
            raise ValueError("demand entry must be an object")
        demand_id = _require_string(raw, "id", "demand")
        negatives_raw = raw.get("should_not_recommend")
        if not isinstance(negatives_raw, list):
            raise ValueError(demand_id + " requires should_not_recommend array")
        negatives = tuple(
            Negative(
                company_id=_require_string(entry, "company_id", demand_id),
                reason=_require_string(entry, "reason", demand_id),
            )
            for entry in negatives_raw
        )
        demands.append(
            Demand(
                id=demand_id,
                type=_require_string(raw, "type", demand_id),
                title=_require_string(raw, "title", demand_id),
                summary=_require_string(raw, "summary", demand_id),
                requester_company_id=_require_string(raw, "requester_company_id", demand_id),
                required_capabilities=_require_string_list(raw, "required_capabilities", demand_id),
                preferred_industries=_require_string_list(raw, "preferred_industries", demand_id),
                region=_require_string(raw, "region", demand_id),
                capacity_need=_require_string(raw, "capacity_need", demand_id),
                rejected_company_ids=_optional_string_list(raw, "rejected_company_ids", demand_id),
                should_recommend=_optional_string_list(raw, "should_recommend", demand_id),
                should_not_recommend=negatives,
                annotation_note=str(raw.get("annotation_note", "")),
            )
        )
    _unique_ids(demands, "demand")

    dataset = Dataset(tuple(companies), tuple(supplies), tuple(demands))
    validate_dataset(dataset)
    return dataset


def validate_dataset(dataset: Dataset) -> None:
    companies = dataset.company_map()
    company_ids = set(companies)
    if not dataset.supplies:
        raise ValueError("dataset needs supplies")
    for company in dataset.companies:
        if company.capacity not in CAPACITIES:
            raise ValueError("company " + company.id + " has unknown capacity")
        if company.id in company.conflicts_with:
            raise ValueError("company " + company.id + " cannot conflict with itself")
    for supply in dataset.supplies:
        if supply.company_id not in company_ids:
            raise ValueError("supply " + supply.id + " references unknown company")
        if supply.status not in {"active", "paused"}:
            raise ValueError("supply " + supply.id + " has unknown status")
        if supply.capacity not in CAPACITIES:
            raise ValueError("supply " + supply.id + " has unknown capacity")
    for demand in dataset.demands:
        where = "demand " + demand.id
        if demand.requester_company_id not in company_ids:
            raise ValueError(where + " references unknown requester")
        if demand.capacity_need not in CAPACITIES:
            raise ValueError(where + " has unknown capacity_need")
        if len(demand.should_recommend) != len(set(demand.should_recommend)):
            raise ValueError(where + " has duplicate positive labels")
        if len(demand.rejected_company_ids) != len(set(demand.rejected_company_ids)):
            raise ValueError(where + " has duplicate rejected ids")
        for company_id in demand.rejected_company_ids:
            if company_id not in company_ids:
                raise ValueError(where + " rejected id is unknown")
        for company_id in demand.should_recommend:
            if company_id not in company_ids:
                raise ValueError(where + " positive id is unknown")
        for negative in demand.should_not_recommend:
            if negative.company_id not in company_ids:
                raise ValueError(where + " negative id is unknown")
            if negative.reason not in NEGATIVE_REASONS:
                raise ValueError(where + " has unknown negative reason " + negative.reason)
        if len({negative.company_id for negative in demand.should_not_recommend}) != len(demand.should_not_recommend):
            raise ValueError(where + " has duplicate negative labels")
        positives = set(demand.should_recommend)
        negatives = {negative.company_id for negative in demand.should_not_recommend}
        if not positives:
            raise ValueError(where + " needs at least one should_recommend id")
        if positives & negatives:
            raise ValueError(where + " positive and negative labels overlap")
        if set(demand.rejected_company_ids) - negatives:
            raise ValueError(where + " rejected ids must appear in should_not_recommend")
    for company in dataset.companies:
        for other in company.conflicts_with:
            if other not in company_ids:
                raise ValueError("company " + company.id + " conflicts with unknown id")
            if company.id not in companies[other].conflicts_with:
                raise ValueError("conflict relation is not symmetric: " + company.id + " / " + other)


def dataset_stats(dataset: Dataset) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    for demand in dataset.demands:
        type_counts[demand.type] = type_counts.get(demand.type, 0) + 1
    return {
        "companies": len(dataset.companies),
        "supplies": len(dataset.supplies),
        "active_supplies": sum(1 for supply in dataset.supplies if supply.status == "active"),
        "demands": len(dataset.demands),
        "demand_types": dict(sorted(type_counts.items())),
        "demand_type_count": len(type_counts),
        "positive_labels": sum(len(demand.should_recommend) for demand in dataset.demands),
        "negative_labels": sum(len(demand.should_not_recommend) for demand in dataset.demands),
    }