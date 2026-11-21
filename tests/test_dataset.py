import ast
import json
import re
import shutil
from pathlib import Path

import pytest

from match_eval.dataset import dataset_stats, load_dataset

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def test_dataset_scale_and_types(dataset):
    stats = dataset_stats(dataset)
    assert stats["companies"] == 40
    assert stats["supplies"] == 30
    assert stats["active_supplies"] == 27
    assert stats["demands"] == 60
    assert stats["demands"] >= 50
    assert stats["demand_type_count"] == 8
    assert set(stats["demand_types"]) == {
        "event",
        "marketing",
        "hiring",
        "legal",
        "finance",
        "it",
        "training",
        "sourcing",
    }


def test_every_demand_has_positive_and_negative_annotations(dataset):
    for demand in dataset.demands:
        assert 1 <= len(demand.should_recommend) <= 6, demand.id
        assert len(demand.should_not_recommend) == 4, demand.id
        positives = set(demand.should_recommend)
        negatives = {negative.company_id for negative in demand.should_not_recommend}
        assert positives
        assert len(positives) == len(demand.should_recommend)
        assert positives.isdisjoint(negatives), demand.id
        assert set(demand.rejected_company_ids).issubset(negatives)
        assert len(demand.rejected_company_ids) == 2
        reasons = {negative.reason for negative in demand.should_not_recommend}
        assert reasons
        assert reasons <= {"rejected", "not_accepting", "conflict"}


def test_negative_reason_coverage(dataset):
    reasons = {
        negative.reason
        for demand in dataset.demands
        for negative in demand.should_not_recommend
    }
    assert reasons == {"rejected", "not_accepting", "conflict"}


def test_all_annotation_ids_exist(dataset):
    ids = {company.id for company in dataset.companies}
    for demand in dataset.demands:
        assert demand.requester_company_id in ids
        assert set(demand.should_recommend) <= ids
        assert set(demand.rejected_company_ids) <= ids
        assert {negative.company_id for negative in demand.should_not_recommend} <= ids


def test_conflicts_are_symmetric(dataset):
    companies = dataset.company_map()
    for company in dataset.companies:
        for other in company.conflicts_with:
            assert company.id in companies[other].conflicts_with


def test_fixture_has_no_pii_like_strings():
    text = ""
    for path in sorted((ROOT / "data").glob("*.json")):
        text += path.read_text(encoding="utf-8")
    assert not re.search(r"1[3-9]\d{9}", text)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    assert "@" not in text


def _copy_dataset(tmp_path: Path) -> Path:
    for name in ("companies.json", "supplies.json", "demands.json"):
        shutil.copy(DATA / name, tmp_path / name)
    return tmp_path


@pytest.mark.parametrize(
    ("filename", "container", "field", "value", "message"),
    [
        ("companies.json", "companies", "accepting", "false", "boolean field accepting"),
        ("companies.json", "companies", "conflicts_with", "c002", "string array field conflicts_with"),
        ("demands.json", "demands", "rejected_company_ids", "c002", "string array field rejected_company_ids"),
        ("demands.json", "demands", "should_recommend", "c001", "string array field should_recommend"),
    ],
)
def test_loader_rejects_wrong_optional_types(tmp_path, filename, container, field, value, message):
    root = _copy_dataset(tmp_path)
    path = root / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[container][0][field] = value
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_dataset(root)


def test_schema_version_and_frozen_annotation_note(dataset):
    for path in sorted((ROOT / "data").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == 1
    for demand in dataset.demands:
        assert "synthetic fixture" in demand.annotation_note


def test_frozen_annotations_match_dataset(dataset):
    payload = json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))
    assert payload["method"] == "six-editor-panel-v2"
    assert payload["independent_of_weights"] == ["v1", "v2"]
    records = {record["demand_id"]: record for record in payload["demands"]}
    assert set(records) == {demand.id for demand in dataset.demands}
    for demand in dataset.demands:
        record = records[demand.id]
        assert demand.should_recommend == tuple(record["should_recommend"])
        assert demand.rejected_company_ids == tuple(record["rejected_company_ids"])
        actual_negatives = [(row.company_id, row.reason) for row in demand.should_not_recommend]
        frozen_negatives = [
            (row["company_id"], row["reason"]) for row in record["should_not_recommend"]
        ]
        assert actual_negatives == frozen_negatives


def test_annotation_slots_are_complete(dataset):
    payload = json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))
    records = {record["demand_id"]: record for record in payload["demands"]}
    for demand in dataset.demands:
        slots = records[demand.id]["positive_slots"]
        assert 1 <= len(slots) <= 6
        assert len({slot["slot"] for slot in slots}) == len(slots)
        assert {slot["slot"] for slot in slots} <= {
            "capability_lead",
            "case_strength",
            "responsiveness",
            "industry_fit",
            "regional_fit",
            "capacity_fit",
        }
        slot_ids = [slot["company_id"] for slot in slots]
        assert len(set(slot_ids)) == len(slot_ids)
        assert set(slot_ids) == set(records[demand.id]["should_recommend"])
        assert all(slot["reason"].strip() for slot in slots)


def test_every_positive_covers_at_least_two_required_capabilities(dataset):
    supplies = json.loads((DATA / "supplies.json").read_text(encoding="utf-8"))["supplies"]
    supply_caps = {}
    for supply in supplies:
        if supply["status"] == "active":
            supply_caps.setdefault(supply["company_id"], set()).update(supply["capabilities"])
    companies = dataset.company_map()
    for demand in dataset.demands:
        required = set(demand.required_capabilities)
        for company_id in demand.should_recommend:
            company = companies[company_id]
            effective = set(company.capabilities) | supply_caps.get(company_id, set())
            assert len(required & effective) >= 2, (demand.id, company_id)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_generator_does_not_compute_labels():
    generator = ROOT / "scripts" / "generate_dataset.py"
    builder = ROOT / "scripts" / "build_annotations.py"
    labeling = ROOT / "scripts" / "labeling.py"
    fixture = ROOT / "scripts" / "fixture_spec.py"
    generator_source = generator.read_text(encoding="utf-8")
    assert "annotation_score" not in generator_source
    assert "load_annotations" in generator_source
    assert "data/annotations.json" in generator_source
    for path in (generator, builder, labeling, fixture):
        modules = _imported_modules(path)
        assert "match_eval" not in modules, path
        assert "weights" not in modules, path
    assert "annotation_score" not in builder.read_text(encoding="utf-8")
