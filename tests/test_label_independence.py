import json
from pathlib import Path

from match_eval.dataset import load_dataset
from match_eval.filters import build_filter_context, hard_filter_reason
from match_eval.scoring import FEATURE_KEYS, Weights, features_for, rank_demand
from scripts.weight_grid import dominance_witnesses, enumerate_grid

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _load():
    dataset = load_dataset(DATA)
    annotations = json.loads((DATA / "annotations.json").read_text(encoding="utf-8"))["demands"]
    context = build_filter_context(dataset)
    labels = {record["demand_id"]: list(record["should_recommend"]) for record in annotations}
    return dataset, annotations, context, labels


def test_d052_has_an_unlabeled_dominating_candidate():
    dataset, annotations, context, labels = _load()
    positives = labels["d052"]
    assert len(positives) == 6
    assert "c006" not in positives
    assert "c022" in positives

    witnesses = dominance_witnesses(dataset, context, annotations)
    assert len(witnesses) == 1, witnesses
    witness = witnesses[0]
    assert witness["demand_id"] == "d052"
    assert witness["unlabeled_candidate"] == "c006"
    assert witness["dominated_positive"] == "c022"

    companies = dataset.company_map()
    demand = dataset.demand_map()["d052"]
    candidate = companies["c006"]
    dominated = companies["c022"]
    assert hard_filter_reason(context, demand, candidate) is None
    candidate_features = features_for(context, demand, candidate)
    dominated_features = features_for(context, demand, dominated)
    assert all(candidate_features[key] >= dominated_features[key] for key in FEATURE_KEYS)
    assert any(candidate_features[key] > dominated_features[key] for key in FEATURE_KEYS)


def test_no_four_feature_weight_can_cover_all_six_d052_positives():
    dataset, _annotations, context, labels = _load()
    demand = dataset.demand_map()["d052"]
    positives = set(labels["d052"])
    for vector in enumerate_grid():
        weights = Weights(name="grid", description="grid", values=vector)
        ranked = rank_demand(dataset, demand, weights, top_k=6, context=context)
        top6 = {row["company_id"] for row in ranked}
        assert not positives <= top6, vector
