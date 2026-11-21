"""Label-sensitivity baseline for the #2050 fixture (read-only).

Question: is the observed v2-v1 NDCG@10 gap simply what any label set of the
same size drawn from the same candidate pool would produce?

The script keeps the frozen negatives, hard filters and rankings fixed and
replaces every demand's positives with a random draw of the same size as the
frozen label.  Three pools are tested: the two-capability qualified pool used by
the editorial floor, the one-capability covered pool, and the full eligible pool
without any capability floor.  The actual label set is compared with the
resulting distribution.

Usage:
    python scripts/label_sensitivity.py
    python scripts/label_sensitivity.py --seeds 500 --json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match_eval.dataset import load_dataset
from match_eval.scoring import load_weights, rank_demand
from scripts import labeling


def ndcg_at_10(relevant: set[str], ranking: list[str]) -> float:
    dcg = sum(
        1.0 / math.log2(position + 2)
        for position, company_id in enumerate(ranking[:10])
        if company_id in relevant
    )
    ideal = sum(1.0 / math.log2(position + 2) for position in range(min(len(relevant), 10)))
    return dcg / ideal if ideal else 0.0


def mean_ndcg(rankings: dict[str, list[str]], labels: dict[str, list[str]]) -> float:
    return sum(ndcg_at_10(set(labels[demand_id]), ranking) for demand_id, ranking in rankings.items()) / len(rankings)


def percentile_at_or_below(values: list[float], actual: float) -> float:
    return 100.0 * sum(1 for value in values if value <= actual) / len(values)


def summarize(values: list[float], actual: float) -> dict:
    ordered = sorted(values)
    return {
        "seeds": len(ordered),
        "min": ordered[0],
        "p05": ordered[round(0.05 * (len(ordered) - 1))],
        "median": ordered[len(ordered) // 2],
        "p95": ordered[round(0.95 * (len(ordered) - 1))],
        "max": ordered[-1],
        "v2_wins": sum(1 for value in ordered if value > 0),
        "actual_percentile": percentile_at_or_below(ordered, actual),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--seed-base", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dataset = load_dataset(ROOT / "data")
    companies = [company.__dict__ for company in dataset.companies]
    supplies = [supply.__dict__ for supply in dataset.supplies]
    signals = json.loads((ROOT / "data" / "editorial-signals.json").read_text(encoding="utf-8"))
    annotations = json.loads((ROOT / "data" / "annotations.json").read_text(encoding="utf-8"))["demands"]
    by_demand = {record["demand_id"]: record for record in annotations}

    rankings = {}
    for name in ("v1", "v2"):
        weights = load_weights(name)
        rankings[name] = {
            demand.id: [row["company_id"] for row in rank_demand(dataset, demand, weights, top_k=10)]
            for demand in dataset.demands
        }

    actual = {record["demand_id"]: list(record["should_recommend"]) for record in annotations}
    actual_v1 = mean_ndcg(rankings["v1"], actual)
    actual_v2 = mean_ndcg(rankings["v2"], actual)
    actual_diff = actual_v2 - actual_v1

    by_id = {company["id"]: company for company in companies}
    supply_ids = labeling.active_supply_ids(supplies)
    qualified_pools: dict[str, list[str]] = {}
    covered_pools: dict[str, list[str]] = {}
    eligible_pools: dict[str, list[str]] = {}
    actual_counts = {demand.id: len(actual[demand.id]) for demand in dataset.demands}
    for demand in dataset.demands:
        plain = demand.__dict__
        views = labeling.build_views(plain, companies, supplies, signals)
        qualified_pools[demand.id] = [
            view["company_id"]
            for view in views
            if view["coverage"] >= labeling.POSITIVE_MIN_COVERAGE
        ]
        covered_pools[demand.id] = [view["company_id"] for view in views]
        requester = by_id[demand.requester_company_id]
        rejected = set(demand.rejected_company_ids)
        eligible_pools[demand.id] = [
            company["id"]
            for company in companies
            if company["id"] in supply_ids
            and company["id"] != requester["id"]
            and company["accepting"]
            and company["id"] not in rejected
            and not labeling.conflict(requester, company)
        ]

    results = {}
    for pool_name, pools in (
        ("qualified", qualified_pools),
        ("covered", covered_pools),
        ("eligible", eligible_pools),
    ):
        diffs = []
        for seed in range(args.seed_base, args.seed_base + args.seeds):
            rng = random.Random(seed)
            labels = {
                demand.id: rng.sample(
                    pools[demand.id],
                    min(actual_counts[demand.id], len(pools[demand.id])),
                )
                for demand in dataset.demands
            }
            diffs.append(mean_ndcg(rankings["v2"], labels) - mean_ndcg(rankings["v1"], labels))
        results[pool_name] = summarize(diffs, actual_diff)

    payload = {
        "actual": {
            "v1_ndcg_at_10": actual_v1,
            "v2_ndcg_at_10": actual_v2,
            "v2_minus_v1": actual_diff,
        },
        "baselines": results,
    }
    out = ROOT / "artifacts" / "label-sensitivity.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("actual v1=%.6f v2=%.6f diff=%+.6f" % (actual_v1, actual_v2, actual_diff))
        print("pool      seeds  min        p05        median     p95        max        v2>v1   actual_pct")
        for name, row in results.items():
            print(
                "%-9s %5d  %+0.6f  %+0.6f  %+0.6f  %+0.6f  %+0.6f  %5d  %6.1f"
                % (
                    name,
                    row["seeds"],
                    row["min"],
                    row["p05"],
                    row["median"],
                    row["p95"],
                    row["max"],
                    row["v2_wins"],
                    row["actual_percentile"],
                )
            )
        print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
