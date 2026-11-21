"""Generate the synthetic match-ranking evaluation fixture.

The fixture is deterministic: same specification -> same JSON bytes.  Company,
supply and demand metadata come from scripts/fixture_spec.py.  Labels are
frozen in data/annotations.json by scripts/build_annotations.py this generator
only validates and applies those frozen labels; it does not select labels and
does not read any evaluator weight file.
"""

from __future__ import annotations

import json
from pathlib import Path

import fixture_spec
import labeling

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_annotations() -> dict[str, dict]:
    path = DATA / "annotations.json"
    if not path.is_file():
        raise RuntimeError(
            "data/annotations.json is missing; run scripts/build_annotations.py first"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError("data/annotations.json has an unsupported schema_version")
    if payload.get("method") != "six-editor-panel-v2":
        raise RuntimeError("data/annotations.json has an unexpected method")
    records = payload.get("demands")
    if not isinstance(records, list) or not records:
        raise RuntimeError("data/annotations.json has no demand records")
    result: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError("annotation record is not an object")
        demand_id = record.get("demand_id")
        if not isinstance(demand_id, str) or not demand_id:
            raise RuntimeError("annotation record has no demand_id")
        if demand_id in result:
            raise RuntimeError("duplicate annotation record: " + demand_id)
        result[demand_id] = record
    return result


def validate_annotation_record(
    demand: dict,
    record: dict,
    companies: list[dict],
    supplies: list[dict],
    eligible_ids: set[str],
) -> None:
    by_id = {company["id"]: company for company in companies}
    requester = by_id[demand["requester_company_id"]]
    supply_caps = labeling.active_supply_capabilities(supplies)
    required = set(demand["required_capabilities"])
    should_ids = record.get("should_recommend")
    rejected_ids = record.get("rejected_company_ids")
    negatives = record.get("should_not_recommend")
    slots = record.get("positive_slots")
    if (
        not isinstance(should_ids, list)
        or not 1 <= len(should_ids) <= len(labeling.SLOT_ORDER)
        or len(set(should_ids)) != len(should_ids)
    ):
        raise RuntimeError(demand["id"] + ": should_recommend must have 1-6 unique ids")
    if not isinstance(rejected_ids, list) or len(rejected_ids) != 2 or len(set(rejected_ids)) != 2:
        raise RuntimeError(demand["id"] + ": rejected_company_ids must have two unique ids")
    if not isinstance(negatives, list) or len(negatives) != 4:
        raise RuntimeError(demand["id"] + ": should_not_recommend must have four rows")
    if not isinstance(slots, list) or not 1 <= len(slots) <= len(labeling.SLOT_ORDER):
        raise RuntimeError(demand["id"] + ": positive_slots must have 1-6 rows")
    if not set(should_ids) <= eligible_ids:
        raise RuntimeError(demand["id"] + ": frozen positive id is not in the eligible pool")
    if not set(rejected_ids) <= eligible_ids:
        raise RuntimeError(demand["id"] + ": frozen rejected id is not in the eligible pool")
    if set(rejected_ids) & set(should_ids):
        raise RuntimeError(demand["id"] + ": frozen rejected id overlaps positives")
    slot_ids = [row.get("company_id") for row in slots]
    slot_names = [row.get("slot") for row in slots]
    if set(slot_ids) != set(should_ids):
        raise RuntimeError(demand["id"] + ": positive slots do not match should_recommend")
    if len(set(slot_names)) != len(slot_names) or not set(slot_names) <= set(labeling.SLOT_ORDER):
        raise RuntimeError(demand["id"] + ": positive slot names are invalid or duplicated")
    for row in slots:
        company_id = row.get("company_id")
        if not isinstance(row.get("slot"), str) or not row["slot"]:
            raise RuntimeError(demand["id"] + ": positive slot has no slot name")
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            raise RuntimeError(demand["id"] + ": positive slot has no reason")
        company = by_id[company_id]
        coverage = len(required & labeling.effective_capabilities(company, supply_caps))
        if coverage < labeling.POSITIVE_MIN_COVERAGE:
            raise RuntimeError(
                demand["id"] + ": positive covers fewer than two required capabilities: " + company_id
            )

    negative_ids = [row.get("company_id") for row in negatives]
    if len(set(negative_ids)) != 4:
        raise RuntimeError(demand["id"] + ": frozen negatives must have four unique ids")
    if set(should_ids) & set(negative_ids):
        raise RuntimeError(demand["id"] + ": frozen positives and negatives overlap")
    rejected_negative_ids = {
        row["company_id"] for row in negatives if row.get("reason") == "rejected"
    }
    if rejected_negative_ids != set(rejected_ids):
        raise RuntimeError(demand["id"] + ": rejected_company_ids does not match rejected negatives")
    for row in negatives:
        company_id = row.get("company_id")
        reason = row.get("reason")
        if company_id not in by_id:
            raise RuntimeError(demand["id"] + ": frozen negative id is unknown")
        if reason not in {"rejected", "not_accepting", "conflict"}:
            raise RuntimeError(demand["id"] + ": frozen negative reason is invalid")
        if reason == "not_accepting" and by_id[company_id]["accepting"]:
            raise RuntimeError(demand["id"] + ": not_accepting label is wrong for " + company_id)
        if reason == "conflict" and not fixture_spec.conflict(requester, by_id[company_id]):
            raise RuntimeError(demand["id"] + ": conflict label is wrong for " + company_id)


def build_demands(
    companies: list[dict], supplies: list[dict], annotations: dict[str, dict]
) -> list[dict]:
    _, _, base_demands = fixture_spec.build_fixture()
    demands = []
    for demand in base_demands:
        record = annotations.get(demand["id"])
        if record is None:
            raise RuntimeError("no frozen annotation for " + demand["id"])
        eligible_ids = set(
            fixture_spec.eligible_pool(
                companies, supplies, demand["requester_company_id"]
            )
        )
        validate_annotation_record(demand, record, companies, supplies, eligible_ids)
        demand = dict(demand)
        demand["should_recommend"] = list(record["should_recommend"])
        demand["rejected_company_ids"] = list(record["rejected_company_ids"])
        demand["should_not_recommend"] = [dict(row) for row in record["should_not_recommend"]]
        demands.append(demand)
    return demands


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    companies, supplies, _ = fixture_spec.build_fixture()
    annotations = load_annotations()
    demands = build_demands(companies, supplies, annotations)
    files = {
        "companies.json": {"schema_version": 1, "companies": companies},
        "supplies.json": {"schema_version": 1, "supplies": supplies},
        "demands.json": {"schema_version": 1, "demands": demands},
    }
    for filename, payload in files.items():
        path = DATA / filename
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("wrote", path.relative_to(ROOT), "bytes", path.stat().st_size)


if __name__ == "__main__":
    main()
