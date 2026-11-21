import json
from pathlib import Path

from match_eval.dataset import load_dataset
from match_eval.filters import build_filter_context, hard_filter_reason
from match_eval.scoring import FEATURE_KEYS, Weights, features_for, rank_demand
from scripts.weight_grid import coverage_by_demand, dominance_witnesses, enumerate_grid

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


def test_no_four_feature_weight_can_cover_all_structural_failures():
    dataset, _annotations, context, labels = _load()
    demands = dataset.demand_map()
    vectors = enumerate_grid()
    failures = {"d036": 5, "d052": 6}

    for demand_id in failures:
        positive = set(labels[demand_id])
        for vector in vectors:
            weights = Weights(name="grid", description="grid", values=vector)
            ranked = rank_demand(dataset, demands[demand_id], weights, top_k=6, context=context)
            top6 = {row["company_id"] for row in ranked}
            assert not positive <= top6, (demand_id, vector)

    coverage = coverage_by_demand(dataset, context, labels, vectors)
    failed = {row["demand_id"] for row in coverage.values() if row["best_covered"] < row["positive_count"]}
    assert failed == set(failures), failed
    for demand_id, positive_count in failures.items():
        assert coverage[demand_id]["positive_count"] == positive_count
        assert coverage[demand_id]["best_covered"] == positive_count - 1
        assert coverage[demand_id]["missing_positives"]

    # d036 has five positives; c003/c006/c013/c021 dominate the 2/3-capability
    # c004 and c024 on capability, and c022's region lead (or the id tie-break)
    # leaves no six-slot arrangement that contains all five positives.
    positives = set(labels["d036"])
    assert positives == {"c003", "c004", "c013", "c022", "c024"}
    companies = dataset.company_map()
    demand = demands["d036"]
    for candidate_id in ("c003", "c006", "c013", "c021"):
        candidate = features_for(context, demand, companies[candidate_id])
        for positive_id in ("c004", "c024"):
            positive = features_for(context, demand, companies[positive_id])
            assert candidate["capability"] > positive["capability"]
            assert candidate["industry"] == positive["industry"] == 0
            assert candidate["region"] == positive["region"] == 0
            assert candidate["capacity"] == positive["capacity"] == 1
