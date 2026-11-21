# Rework 逐项证据（#2050，交付 v3）

本文件把平台 rework 要求逐条映射到仓库文件、命令与输出。当前代码、数据、报告、测试和验收已全部切到第 3 轮事实。

## 1. 代码仓库（blocker）

- 仓库：https://github.com/Gupeat/memberspace-match-eval-2050 （public）
- 内容：`match_eval/` 包、`scripts/`、`tests/`、`data/`、`weights/v1.json`、`weights/v2.json`、`artifacts/` 报告与验收记录、`docs/` 复核指南。
- README「快速开始」给出统计、标注生成、评测、对比、测试、验收命令。

## 2. 评测集规模与需求类型（major）

- 数据：`data/companies.json`（40）、`data/supplies.json`（30，27 active）、`data/demands.json`（60）。
- 标注规则：`data/ANNOTATION.md`；冻结标签：`data/annotations.json`（由 `scripts/build_annotations.py` 生成，不读取权重）。
- 统计命令：`python -m match_eval stats`
- 实际输出（完整 JSON）：

```json
{"active_supplies": 27, "companies": 40, "demand_type_count": 8, "demand_types": {"event": 8, "finance": 7, "hiring": 8, "it": 7, "legal": 8, "marketing": 8, "sourcing": 7, "training": 7}, "demands": 60, "negative_labels": 240, "positive_labels": 190, "supplies": 30}
```

- 覆盖类型：event、finance、hiring、it、legal、marketing、sourcing、training（每种 7–8 条）。
- 正例覆盖：3/3=113、2/3=77、1/3=0；每需求正例数 1–6（1:7、2:11、3:21、4:11、5:6、6:4）。
- 负例原因：rejected 120、not_accepting 104、conflict 16；44/60 条需求没有冲突对象。

## 3. 每个指标的专用单元测试（major）

| 指标 | 专用测试文件 |
| --- | --- |
| Hit@5 | `tests/test_metric_hit_at_5.py` |
| NDCG@10 | `tests/test_metric_ndcg_at_10.py` |
| 硬过滤违规数 | `tests/test_metric_filter_violations.py` |
| 理由可追溯率 | `tests/test_metric_rationale_trace.py` |
| 前 5 名集中度 | `tests/test_metric_top5_concentration.py` |

命令：

```bash
python -m pytest tests/test_metric_hit_at_5.py tests/test_metric_ndcg_at_10.py tests/test_metric_filter_violations.py tests/test_metric_rationale_trace.py tests/test_metric_top5_concentration.py
```

输出：`14 passed`。全量：`python -m pytest tests` → `68 passed`。`tests/test_metrics.py` 保留综合覆盖，`tests/test_label_independence.py` 覆盖支配反例。

## 4. 违规/退步时退出码非 0（major）

- 违规：

```bash
python -m match_eval evaluate --weights v2 --no-hard-filter --report artifacts/diagnostic-no-filter.md
```

输出：`hard_filter_violations=222`、`ndcg_at_10=0.808071`、退出码 **2**。

- 退步：`tests/test_cli.py::test_cli_compare_regression_exit_nonzero` 使用只按 region 打分的坏权重，断言 NDCG@10 退步超过 2 个百分点时退出码 3。
- 正常对比：

```bash
python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
```

输出：`ndcg_regression=-0.075025`、`verdict=pass`、退出码 0。

- 说明：正式评测的违规数恒为 0，因此 AC3 的“违规时非 0”证据来自 `--no-hard-filter` 诊断运行；不要把诊断 NDCG 当作交付成绩。

## 5. 两个权重版本对比报告（major）

- 文件：`artifacts/report-compare.md`（已提交到仓库）。
- 结果（六槽标签下）：
  - Hit@5：1.000000 / 1.000000
  - NDCG@10：0.890098 / 0.965123（右−左 **+0.075025**；左−右退步 -0.075025）
  - 硬过滤违规：0 / 0
  - 理由可追溯率：1.000000 / 1.000000
  - HHI：0.051467 / 0.053333；top1：0.083333 / 0.096667；覆盖公司 23 / 23
  - 退步未超过 0.02，判定 pass，退出码 0。
- 逐需求：v2 更好 31 条、持平 28 条、更差 1 条。
- 标签独立性：本版标签由 `scripts/labeling.py` 的六个编辑槽位生成，纯词典序、无加权和，不读 v1/v2；capability_lead 用 IDF 稀缺密度，案例/响应信号只存在于 `data/editorial-signals.json`。
- v2 top6 与标签集合：精确一致 **2/4**（只有 4 条需求恰有 6 个正例），覆盖全部标签 **51/60**，交集 **180/190**；190 个正例全部落在 v2 全量前 10（中位 2、最差 8）。NDCG 按位置加权、top6 是集合，二者不矛盾。
- 独立性边界：`scripts/weight_grid.py` 枚举 1771 组四特征权重；网格内最好的权重也只能让 **58/60** 条需求的 top6 覆盖全部正例（capability 0.65 / industry 0.00 / region 0.15 / capacity 0.20；正例召回 188/190），best NDCG@10=0.996243（0.80/0.05/0.00/0.15）。这是结构性的：d052 的未标注、硬过滤合格候选 c006（capability 1.0 / industry 0 / region 0 / capacity 1）严格支配正例 c022（capability 2/3 / industry 0 / region 0 / capacity 1）；任何非负权重都会把 c006 排在 c022 前，若 c022 进 top6 则 c006 也进，再加另外 5 个正例需要 7 个位置。因此能声称“top6 标签集合不能被任何非负四特征权重完整复现”，但不声称与业务事实正交。`tests/test_label_independence.py` 穷举 1771 组权重断言，`artifacts/weight-grid.json` 的 `dominance_witnesses` 记录该反例。
- `+0.075025` 必须与随机化基线一起读：与正式标签同底线（覆盖 ≥2）时随机标签中位 +0.075438、v2 胜 500/500，实际标签第 41.0 百分位；覆盖 ≥1 时中位 +0.023730、484/500；去掉底线时中位 -0.000253、v2 仅胜 247/500。详见 `docs/LABEL-BASELINE.md`。

## 6. 复核与验收

- `python scripts/run_acceptance.py` → `all_passed True`；`artifacts/ACCEPTANCE.md` 记录 AC1–AC6、命令、退出码和五个数据文件 sha256。
- `python scripts/manual_review.py` → 60 条需求、430 个标签（190 正 + 240 负）、0 缺陷、0 重放不一致；默认 `pending-human-signoff`，只有 `--reviewer` 与 `--attest` 同时给才写 `human-reviewed`。
- `python scripts/label_sensitivity.py` → 三个候选池各 500 seeds，输出与 `docs/LABEL-BASELINE.md` 一致。
- `python scripts/weight_grid.py` → 1771 组；输出 `artifacts/weight-grid.json`。

## 复现

```bash
python scripts/build_annotations.py
python scripts/generate_dataset.py
python -m match_eval stats
python -m match_eval evaluate --weights v1 --report artifacts/report-v1.md
python -m match_eval evaluate --weights v2 --report artifacts/report-v2.md
python -m match_eval evaluate --weights v2 --no-hard-filter --report artifacts/diagnostic-no-filter.md
python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
python -m pytest tests
python scripts/run_acceptance.py
python scripts/manual_review.py
python scripts/label_sensitivity.py
python scripts/weight_grid.py
```

## 限制

人工标注仍是未完成项：复核包待人类签字，签字前不得称为人工标注。0.965123 是 60 条合成需求上的回归结果，不是泛化或线上效果结论。77 个正例覆盖 2/3 required capabilities，113 个覆盖 3/3，没有 1/3；理由已逐条写入标注。标签与评测器共享能力、行业、区域、产能事实；独立性指“不由 v1/v2 权重生成，且 top6 集合不能被任何非负四特征权重完整复现”，不是“与业务事实无关”。所有数据均为合成数据，不含真实企业、联系人、金额或 PII。
