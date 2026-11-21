"""Build the frozen annotation set for #2050.

The labels are produced by six independent editorial lenses from
scripts/labeling.py.  This script reads the hand-authored fixture
(scripts/fixture_spec.py) and the label-only signals
(data/editorial-signals.json).  It never imports or reads weights/v1.json,
weights/v2.json or match_eval.scoring.

Usage:
    python scripts/build_annotations.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fixture_spec
import labeling

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SIGNALS_FILE = DATA / "editorial-signals.json"
OUTPUT_FILE = DATA / "annotations.json"


def load_signals() -> tuple[dict, str]:
    raw = SIGNALS_FILE.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("schema_version") != 1:
        raise RuntimeError("data/editorial-signals.json has an unsupported schema_version")
    for section in ("companies", "demands"):
        if not isinstance(payload.get(section), dict) or not payload[section]:
            raise RuntimeError("data/editorial-signals.json is missing " + section)
    digest = hashlib.sha256(raw).hexdigest()
    return payload, digest


def validate_signals(
    signals: dict, companies: list[dict], demands: list[dict]
) -> None:
    company_ids = {company["id"] for company in companies}
    demand_ids = {demand["id"] for demand in demands}
    if set(signals["companies"]) != company_ids:
        raise RuntimeError("editorial company signals do not match the fixture")
    if set(signals["demands"]) != demand_ids:
        raise RuntimeError("editorial demand signals do not match the fixture")
    for company_id, row in signals["companies"].items():
        cases = row.get("verified_cases")
        days = row.get("response_days")
        if not isinstance(cases, int) or not 0 <= cases <= 100:
            raise RuntimeError(company_id + ": verified_cases must be an integer 0..100")
        if not isinstance(days, int) or not 1 <= days <= 30:
            raise RuntimeError(company_id + ": response_days must be an integer 1..30")
    for demand_id, row in signals["demands"].items():
        limit = row.get("max_response_days")
        if not isinstance(limit, int) or not 1 <= limit <= 30:
            raise RuntimeError(demand_id + ": max_response_days must be an integer 1..30")


def build_record(
    demand: dict, companies: list[dict], supplies: list[dict], signals: dict
) -> dict:
    slots = labeling.select_positive_slots(demand, companies, supplies, signals)
    positive_ids = [row["company_id"] for row in slots]
    if not 1 <= len(positive_ids) <= len(labeling.SLOT_ORDER):
        raise RuntimeError(demand["id"] + ": positive slots must select 1-6 companies")
    if len(set(positive_ids)) != len(positive_ids):
        raise RuntimeError(demand["id"] + ": positive slots must be distinct")
    if set(positive_ids) - labeling.eligible_positive_ids(demand, companies, supplies, signals):
        raise RuntimeError(demand["id"] + ": positive slot outside the qualified pool")
    negatives = labeling.select_negative_rows(demand, companies, supplies, positive_ids)
    rejected_ids = [row["company_id"] for row in negatives if row["reason"] == "rejected"]
    if rejected_ids != list(demand["rejected_company_ids"]):
        raise RuntimeError(demand["id"] + ": rejected negatives do not match the fixture")
    if set(positive_ids) & {row["company_id"] for row in negatives}:
        raise RuntimeError(demand["id"] + ": positive and negative labels overlap")
    return {
        "demand_id": demand["id"],
        "should_recommend": positive_ids,
        "rejected_company_ids": list(demand["rejected_company_ids"]),
        "should_not_recommend": negatives,
        "positive_slots": slots,
        "annotation_note": (
            "six editor lenses, each may abstain; positive floor is at least two of the "
            "required capabilities; signals 2-3 are label-only; no evaluator weights are read"
        ),
    }


def main() -> None:
    companies, supplies, demands = fixture_spec.build_fixture()
    signals, signals_digest = load_signals()
    validate_signals(signals, companies, demands)
    records = [build_record(demand, companies, supplies, signals) for demand in demands]
    slot_counts: dict[str, int] = {}
    reason_counts: dict[str, int] = {}
    covered_counts: dict[int, int] = {}
    for record, demand in zip(records, demands):
        for row in record["positive_slots"]:
            slot_counts[row["slot"]] = slot_counts.get(row["slot"], 0) + 1
        for row in record["should_not_recommend"]:
            reason_counts[row["reason"]] = reason_counts.get(row["reason"], 0) + 1
        covered_counts[len(record["should_recommend"])] = (
            covered_counts.get(len(record["should_recommend"]), 0) + 1
        )
        # Coverage floor: every positive covers at least two required capabilities.
        by_id = {company["id"]: company for company in companies}
        supply_caps = labeling.active_supply_capabilities(supplies)
        required = set(demand["required_capabilities"])
        for company_id in record["should_recommend"]:
            capabilities = labeling.effective_capabilities(by_id[company_id], supply_caps)
            if len(required & capabilities) < labeling.POSITIVE_MIN_COVERAGE:
                raise RuntimeError(
                    demand["id"] + ": positive covers fewer than two required capabilities"
                )
    payload = {
        "schema_version": 1,
        "method": "six-editor-panel-v2",
        "independent_of_weights": ["v1", "v2"],
        "generated_by": "scripts/build_annotations.py",
        "fixture_source": "scripts/fixture_spec.py",
        "signal_source": "data/editorial-signals.json",
        "signal_source_sha256": signals_digest,
        "feature_notes": {
            "capability_lead": "average IDF rarity density of matched capabilities; no evaluator weights",
            "case_strength": "verified_cases from data/editorial-signals.json",
            "responsiveness": "response_days vs max_response_days from data/editorial-signals.json",
            "industry_fit": "count of preferred industries matched",
            "regional_fit": "same / adjacent / distant region band",
            "capacity_fit": "capacity meets need first, then smallest sufficient excess",
            "capability_floor": "each positive covers at least two required capabilities",
            "positive_count": "1-6; a slot abstains when no remaining candidate meets its condition",
            "aggregation": "one lexicographic key per slot; no weighted sum anywhere",
        },
        "slot_order": list(labeling.SLOT_ORDER),
        "slot_notes": dict(labeling.SLOT_NOTES),
        "demands": records,
    }
    OUTPUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("wrote", OUTPUT_FILE.relative_to(ROOT), "demands", len(records))
    print("slots", json.dumps(slot_counts, sort_keys=True))
    print("negative_reasons", json.dumps(reason_counts, sort_keys=True))
    print("positives_per_demand", json.dumps(covered_counts, sort_keys=True))
    print("signals_sha256", signals_digest)


if __name__ == "__main__":
    main()
