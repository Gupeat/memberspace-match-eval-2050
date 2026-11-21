import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from scripts import labeling

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

GOLDEN = {
    "companies.json": "a508c4942d3311e8e987b1afd70463bdca5962a29431c5785cb7bc79eb954b47",
    "supplies.json": "c29391996dc5d3692761e451f621ac6886e9c3834aaa84c4071d2c76550738fe",
    "demands.json": "956da350a2f20501b1e0af3fc4b519da287ab34407ee57c7e9ceceb2b714aa31",
    "annotations.json": "4694fac72d7fc9691a0df6e19c341e05a4f2b8d2f795fd01110b94405a35ef88",
    "editorial-signals.json": "bf8491c6ef1d20e1fe21e0343e98c429c629526718cd5c43e1ec426d7276d032",
}


def _load_plain():
    companies = json.loads((DATA / "companies.json").read_text(encoding="utf-8"))["companies"]
    supplies = json.loads((DATA / "supplies.json").read_text(encoding="utf-8"))["supplies"]
    demands = json.loads((DATA / "demands.json").read_text(encoding="utf-8"))["demands"]
    signals = json.loads((DATA / "editorial-signals.json").read_text(encoding="utf-8"))
    annotations = json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))["demands"]
    return companies, supplies, demands, signals, annotations


def test_frozen_data_hashes():
    for name, digest in GOLDEN.items():
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == digest, name


def test_positive_floor_and_slot_qualification():
    companies, supplies, demands, signals, _ = _load_plain()
    counts = set()
    for demand in demands:
        rows = labeling.select_positive_slots(demand, companies, supplies, signals)
        counts.add(len(rows))
        assert 1 <= len(rows) <= len(labeling.SLOT_ORDER)
        assert len({row["slot"] for row in rows}) == len(rows)
        assert len({row["company_id"] for row in rows}) == len(rows)
        views = {
            view["company_id"]: view
            for view in labeling.build_views(demand, companies, supplies, signals)
        }
        for row in rows:
            view = views[row["company_id"]]
            assert view["coverage"] >= labeling.POSITIVE_MIN_COVERAGE
            assert labeling.slot_qualifies(row["slot"], view), (demand["id"], row)
    assert 1 in counts
    assert any(count < 6 for count in counts)


def test_every_label_replays_from_the_six_editor_rules():
    companies, supplies, demands, signals, annotations = _load_plain()
    records = {row["demand_id"]: row for row in annotations}
    for demand in demands:
        positives = labeling.select_positive_slots(demand, companies, supplies, signals)
        assert [(row["slot"], row["company_id"]) for row in positives] == [
            (row["slot"], row["company_id"]) for row in records[demand["id"]]["positive_slots"]
        ]
        negative_rows = labeling.select_negative_rows(
            demand, companies, supplies, [row["company_id"] for row in positives]
        )
        assert [(row["company_id"], row["reason"]) for row in negative_rows] == [
            (row["company_id"], row["reason"]) for row in demand["should_not_recommend"]
        ]


def test_builder_and_generator_ignore_weight_files(tmp_path):
    shutil.copytree(ROOT / "scripts", tmp_path / "scripts")
    (tmp_path / "data").mkdir()
    shutil.copy(DATA / "editorial-signals.json", tmp_path / "data" / "editorial-signals.json")
    (tmp_path / "weights").mkdir()
    changed = {"capability": 0.123, "industry": 0.456, "region": 0.789, "capacity": 0.321}
    for name in ("v1.json", "v2.json"):
        (tmp_path / "weights" / name).write_text(
            json.dumps({"version": name[:2], "weights": changed}), encoding="utf-8"
        )
    subprocess.run(
        [sys.executable, "scripts/build_annotations.py"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, "scripts/generate_dataset.py"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    for name in ("companies.json", "supplies.json", "demands.json", "annotations.json"):
        assert (tmp_path / "data" / name).read_bytes() == (DATA / name).read_bytes(), name
