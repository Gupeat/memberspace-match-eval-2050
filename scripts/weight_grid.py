"""Reproduce the four-weight sensitivity grid quoted in LABEL-BASELINE.

The grid enumerates every non-negative weight vector on a 0.05 step whose four
components sum to 1.0.  That is C(23, 3) = 1771 vectors, not 1330 (1330 is
C(21, 3), the count for a sum of 0.90).  For each vector the script evaluates
the same frozen dataset and reports how closely the resulting top-6 matches the
editorial label set.  It is a diagnostic, not part of the acceptance path.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match_eval.dataset import load_dataset
from match_eval.filters import build_filter_context, hard_filter_reason
from match_eval.metrics import ndcg_at_k
from match_eval.scoring import FEATURE_KEYS, Weights, features_for, load_weights, rank_demand

STEP = 20


def enumerate_grid() -> list[dict[str, float]]:
    vectors = []
    for capability in range(STEP + 1):
        for industry in range(STEP + 1 - capability):
            for region in range(STEP + 1 - capability - industry):
                capacity = STEP - capability - industry - region
                vectors.append(
                    {
                        "capability": capability / STEP,
                        "industry": industry / STEP,
                        "region": region / STEP,
                        "capacity": capacity / STEP,
                    }
                )
    return vectors


def measure(dataset, context, labels, weights: Weights) -> dict:
    exact = 0
    exact_denominator = 0
    covers_all = 0
    overlap = 0
    positive_total = 0
    ndcg = 0.0
    for demand in dataset.demands:
        ranked = rank_demand(dataset, demand, weights, top_k=10, context=context)
        ids = [row["company_id"] for row in ranked]
        positive = set(labels[demand.id])
        top6 = set(ids[:6])
        positive_total += len(positive)
        overlap += len(top6 & positive)
        covers_all += 1 if positive <= top6 else 0
        if len(positive) == 6:
            exact_denominator += 1
            exact += 1 if top6 == positive else 0
        ndcg += ndcg_at_k(ids, positive, k=10)
    return {
        "ndcg_at_10": round(ndcg / len(dataset.demands), 6),
        "top6_exact": exact,
        "top6_exact_denominator": exact_denominator,
        "top6_covers_all": covers_all,
        "positive_total": positive_total,
        "overlap_total": overlap,
        "positive_recall": round(overlap / positive_total, 6) if positive_total else 0.0,
    }


def dominance_witnesses(dataset, context, annotations) -> list[dict]:
    """Find unlabeled qualified candidates that strictly dominate a positive.

    A dominance witness on a six-positive demand proves that no non-negative
    four-feature weight vector can put all six positives in a top-6: the
    unlabeled candidate outranks the dominated positive on every feature, so it
    must also appear in any top-6 that contains that positive, leaving seven
    candidates for six slots.
    """
    labels = {record["demand_id"]: list(record["should_recommend"]) for record in annotations}
    companies = dataset.company_map()
    witnesses = []
    for demand in dataset.demands:
        positives = labels[demand.id]
        if len(positives) != 6:
            continue
        positive_set = set(positives)
        for company in dataset.companies:
            if company.id in positive_set:
                continue
            if hard_filter_reason(context, demand, company) is not None:
                continue
            candidate_features = features_for(context, demand, company)
            for positive_id in positives:
                positive_features = features_for(context, demand, companies[positive_id])
                if all(candidate_features[key] >= positive_features[key] for key in FEATURE_KEYS) and any(
                    candidate_features[key] > positive_features[key] for key in FEATURE_KEYS
                ):
                    witnesses.append(
                        {
                            "demand_id": demand.id,
                            "unlabeled_candidate": company.id,
                            "dominated_positive": positive_id,
                            "candidate_features": candidate_features,
                            "positive_features": positive_features,
                        }
                    )
    return witnesses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset = load_dataset(ROOT / "data")
    annotations = json.loads((ROOT / "data" / "annotations.json").read_text(encoding="utf-8"))["demands"]
    labels = {record["demand_id"]: list(record["should_recommend"]) for record in annotations}
    context = build_filter_context(dataset)

    vectors = enumerate_grid()
    best = None
    best_recall = None
    best_ndcg = None
    for vector in vectors:
        weights = Weights(name="grid", description="grid", values=vector)
        result = measure(dataset, context, labels, weights)
        row = {"weights": vector, **result}
        if best is None or (result["top6_covers_all"], result["overlap_total"]) > (
            best["top6_covers_all"],
            best["overlap_total"],
        ):
            best = row
        if best_recall is None or result["positive_recall"] > best_recall["positive_recall"]:
            best_recall = row
        if best_ndcg is None or result["ndcg_at_10"] > best_ndcg["ndcg_at_10"]:
            best_ndcg = row

    named = {}
    for name in ("v1", "v2"):
        named[name] = measure(dataset, context, labels, load_weights(name))

    payload = {
        "step": 1 / STEP,
        "grid_size": len(vectors),
        "grid_size_expected": 1771,
        "best_top6_covers_all": best,
        "best_positive_recall": best_recall,
        "best_ndcg": best_ndcg,
        "named_weights": named,
        "dominance_witnesses": dominance_witnesses(dataset, context, annotations),
    }
    out = ROOT / "artifacts" / "weight-grid.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("grid_size", len(vectors))
        print("best_top6_covers_all", best["top6_covers_all"], best["weights"])
        print("best_positive_recall", best_recall["positive_recall"], best_recall["weights"])
        print("best_ndcg", best_ndcg["ndcg_at_10"], best_ndcg["weights"])
        print("dominance_witnesses", len(payload["dominance_witnesses"]))
        for name, row in named.items():
            print(name, row)
        print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
