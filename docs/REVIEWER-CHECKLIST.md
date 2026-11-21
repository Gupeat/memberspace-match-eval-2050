# Reviewer checklist - delivery v3

Repository: https://github.com/Gupeat/memberspace-match-eval-2050

This checklist maps each review item to a committed artifact. Run all commands from the
repository root with Python 3.11+; there are no network or third-party runtime dependencies.

## 1. Public code repository (blocker)

- Source: `match_eval/` (dataset, filters, scoring, metrics, evaluate, report, cli).
- Data: `data/companies.json` (40), `data/supplies.json` (30, 27 active),
  `data/demands.json` (60, 8 types), `data/annotations.json` (frozen labels),
  `data/editorial-signals.json` (label-only signals), `data/ANNOTATION.md`.
- Label rules: `scripts/labeling.py` (six editorial slots); builder:
  `scripts/build_annotations.py`; applier: `scripts/generate_dataset.py`.
- Run/test instructions: `README.md`, `docs/REVIEW-GUIDE.md`.

## 2. Dataset, annotation and stats (major)

- 60 demands, 8 types, 190 positives, 240 negatives. Each demand has 1-6 positives and
  exactly 4 negatives: 2 rejected, at least 1 not_accepting, plus 1 conflict when a
  conflicting company exists, otherwise a second not_accepting. Actual totals: rejected 120,
  not_accepting 104, conflict 16; 44/60 demands have no conflict.
- Required capabilities are 2-3 per demand; all 16 capabilities appear in company cards.
  Company capability cards are hand-written to match company names; supplies and demand
  metadata are deterministically derived, not all hand-written.
- Positives cover 3/3=113, 2/3=77, 1/3=0. The "at least two required capabilities" floor is
  a disclosed business rule. It cannot be raised to 3/3 without changing the fixture: only
  113 positives reach 3/3.
- Command: `python -m match_eval stats`
- Expected: companies 40, supplies 30 (active 27), demands 60, demand_type_count 8,
  positive_labels 190, negative_labels 240.

## 3. Metric unit tests (major)

- Dedicated files: `tests/test_metric_hit_at_5.py`, `test_metric_ndcg_at_10.py`,
  `test_metric_filter_violations.py`, `test_metric_rationale_trace.py`,
  `test_metric_top5_concentration.py` (14 passed total).
- Supporting suites: `tests/test_metrics.py`, `test_filters.py`, `test_scoring.py`,
  `test_evaluate.py`, `test_cli.py`, `test_dataset.py`, `test_labeling.py`,
  `test_report.py`.
- Full suite: `python -m pytest tests` -> 68 passed.
- Acceptance record: `artifacts/ACCEPTANCE.md`.

## 4. Non-zero exit code on violations or regression (major)

- `tests/test_cli.py` asserts exit 2 for hard-filter violations and exit 3 when
  NDCG@10 regresses by more than 0.02.
- Real diagnostic run:
  `python -m match_eval evaluate --weights v2 --no-hard-filter --report artifacts/diagnostic-no-filter.md`
  -> 222 violations, NDCG@10 0.808071, exit 2.
- The diagnostic report's embedded reproduction command includes `--no-hard-filter` and its
  real output path; `tests/test_report.py` asserts this.
- Normal run: exit 0 when violations are zero. The exit-2 evidence intentionally comes from
  the no-filter diagnostic; formal evaluation has zero violations.

## 5. v1/v2 comparison report (major)

- Committed report: `artifacts/report-compare.md`, linked from `README.md`.
- Command: `python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md`
- v1 NDCG@10=0.890098; v2=0.965123; v2-v1=+0.075025; compare left-minus-right
  regression=-0.075025, below the 0.02 threshold; verdict=pass, exit 0.
- Formal builds: v1/v2 Hit@5 1.000000/1.000000, violations 0/0, traceability 1.0/1.0,
  HHI 0.051467/0.053333, top1 0.083333/0.096667, 23 companies each.
- Per demand, v2 is better on 31, equal on 28 and worse on 1. All 190 positives fall inside
  v2's full top 10 (median rank 2, worst 8).

## 6. Label independence (this round's blocker)

- `scripts/build_annotations.py`, `scripts/labeling.py` and `scripts/fixture_spec.py` do
  not import `match_eval` and do not read `weights/v1.json` or `weights/v2.json`; checked by
  AST in `tests/test_dataset.py`.
- Labels are frozen in `data/annotations.json`; `scripts/generate_dataset.py` only applies
  them and contains no `annotation_score`.
- `tests/test_labeling.py`: golden SHA-256, replay of all 60 demands, and a behavioural test
  that rewrites weights to arbitrary values, reruns both scripts, and asserts all four data
  files are byte-identical.
- `scripts/manual_review.py` replays the six slots and four negatives with the same
  `labeling` module; 60 demands / 430 labels, 0 defects, 0 replay mismatches, default status
  pending-human-signoff.
- The six slots are lexicographic, with no weighted sum, and a slot abstains when no
  qualified candidate remains (hence 1-6 positives). Only `case_strength` (company-level
  verified cases) and `responsiveness` (curated response days) are wholly new signals;
  industry, region and capacity are different editorial aggregations of facts the evaluator
  also uses. Do not claim full orthogonality.
- `scripts/weight_grid.py` enumerates all 1771 non-negative four-feature weights at 0.05
  steps. The best weight in the grid covers 58/60 demands (capability 0.65 / industry 0.00 /
  region 0.15 / capacity 0.20; positive recall 188/190), best NDCG@10=0.996243. This is not a
  grid-resolution issue: in d052 the unlabelled but eligible c006 has features
  capability 1.0 / industry 0 / region 0 / capacity 1, while the labelled c022 has
  capability 2/3 / industry 0 / region 0 / capacity 1. c006 strictly dominates c022, so any
  non-negative four-feature weight ranks c006 above c022; if c022 enters top6, c006 must too,
  and six positives plus c006 need seven slots. `tests/test_label_independence.py` asserts
  this over all 1771 grid weights and `artifacts/weight-grid.json` records the witness.
  Therefore the claim is "no non-negative four-feature weight can reproduce every demand's
  top6 label set", not full orthogonality with the business facts.
- v2 top6 exact agreement is 2/4 (only demands with six positives can be exact),
  51/60 demands fully covered, 180/190 positive ids in top6. The gap is a ranking-target
  difference (NDCG is position-weighted; top6 is a set), not a label defect and not proof of
  independence.

## 7. Label-sensitivity baseline

- `scripts/label_sensitivity.py` (500 seeds, deterministic) replaces only the positives,
  preserving each demand's actual positive count.
- With the production floor (coverage >= 2): median v2-v1=+0.075438, v2 wins 500/500; the
  actual labels are at the 41.0st percentile, i.e. not tuned to favour v2.
- With coverage >= 1: median +0.023730, 484/500.
- Without the floor: median -0.000253, v2 wins 247/500, 95% range crosses zero.
- Therefore +0.075025 is not evidence that v2 generalizes better; see
  `docs/LABEL-BASELINE.md` and `docs/EVALUATION-LIMITS.md`.

## 8. Honest limits

- Labels are rule-generated synthetic editorial fixtures, not human annotations; the review
  pack is pending human sign-off.
- NDCG@10=0.965123 is a consistency result on 60 synthetic demands, not a production-quality
  estimate.
- 77/190 positives cover 2/3 required capabilities; 113 cover 3/3; none cover 1/3. The
  rationale is documented per label in `data/annotations.json` and in
  `docs/EVALUATION-LIMITS.md`.
- `case_strength` verified-case counts are company-level, not split by capability.
- Data contains no real companies, contacts, API keys, PII or monetary values.
- Historical round-1/round-2 logs under `artifacts/history/` are superseded; do not cite
  their numbers.
