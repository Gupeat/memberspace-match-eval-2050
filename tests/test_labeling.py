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
    "companies.json": "fafade43c7142f2ed1a1e91d4565f2e75a5afb390540ed5dea8d0c6e18c2a07d",
    "supplies.json": "1e51c471d11058cb7c34a1da263d7cb1499675ea503bf23af3f71b621c87ec31",
    "demands.json": "15637e438652ea574bef71db66429f311a4f400345c46b722e31b92fd2c26d6f",
    "annotations.json": "c42a743699c38cf77942279c52ecefb506b39c8ecec6a8603bdbe1700ed8d1ce",
    "editorial-signals.json": "e77329acc3e157e625e87876eaadc3aa23cadd079f71bb7e6a887565b0960dd1",
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
