# 评测边界与标签口径（#2050，交付 v3）

本文件说明四件容易被误读的事：标签不是人工标注；标签与 v1/v2 的独立性是有限度的；+0.075025 不是“v2 更好”的泛化证据；top6 精确一致不是标签质量的证明。

## 1. 标签是规则生成的编辑式合成标签，不是人工标注

- 规模：40 家企业、30 条供给（27 active）、60 条需求、190 个正例、240 个负例。
- 每个需求由六个编辑槽位各选至多一个正例：capability_lead、case_strength、responsiveness、industry_fit、regional_fit、capacity_fit。槽位可以弃权，因此每条需求 1–6 个正例（分布见下）。
- 负例：2 个 rejected + 1 个 not_accepting +（有冲突对象时）1 个 conflict，否则第二个 not_accepting。合计 rejected 120、not_accepting 104、conflict 16；44/60 条需求没有 conflict。
- 规则源码是 `scripts/labeling.py`，唯一规则源；`scripts/build_annotations.py` 读取手写企业 fixture 和 `data/editorial-signals.json`，输出冻结的 `data/annotations.json`；`scripts/generate_dataset.py` 只套用，不重新计算。
- `scripts/manual_review.py` 逐条重放六槽位和四负例，生成 `docs/MANUAL-REVIEW.md`、`artifacts/manual-review.json`、`artifacts/manual-review.csv`：60 条需求、190 个正例、240 个负例、0 个标签缺陷、0 个重放不一致。
- 复核包当前状态是 **pending-human-signoff**：没有人类复核人姓名、签字或时间。签字前只能称“已完成可复算的合成标签 + 机器复核包”，不能称“人工标注已完成”。
- 任务原文要求“每条需求人工标注”。本项目没有用真实人工逐条标注，选择的是**可复算的编辑式规则 + 待人工签字的复核包**，并在 README、REWORK、ACCEPTANCE 中如实披露。平台若坚持人工性，这是已知交付风险，不应被文档措辞掩盖。

## 2. 独立性的准确含义

第 2 轮审核的 blocker 是“标签由与 v2 相同的加权公式生成，排序器在评自己”。本轮已消除这一具体问题，但不能扩大解释：

- **不读权重**：`scripts/build_annotations.py`、`scripts/labeling.py`、`scripts/fixture_spec.py` 不导入 `match_eval`，也不读取 `weights/v1.json` 或 `weights/v2.json`。测试用 AST 静态检查和“改权重后重跑、四个数据文件逐字节不变”的行为检查双重验证。
- **无加权和**：六个槽位都是词典序，不存在 0.40/0.20/0.20/0.20 或 0.55/0.25/0.10/0.10 的合成分。
- **只有两个真正的新信号**：`data/editorial-signals.json` 的 `verified_cases`、`response_days`、`max_response_days` 不在 `match_eval` 的读取路径中，分别支撑 case_strength 与 responsiveness。行业、区域、产能三个槽位是对评测器也使用的业务事实的不同编辑口径，不声称是独立信号。
- **共享业务事实，但 top6 集合不可由四特征权重复现**：标签仍然使用企业能力、行业、区域、容量这些评测器也使用的字段。`scripts/weight_grid.py` 枚举 0.05 步长、四权重非负且和为 1 的 **1771** 组权重；网格内最好的权重也只能让 **58/60** 条需求的 top6 覆盖全部正例（capability 0.65 / industry 0.00 / region 0.15 / capacity 0.20；正例召回 188/190），best NDCG@10=0.996243。

  这不是网格密度问题。d052 有 6 个正例，其中 c022 的四特征是 capability 2/3、industry 0、region 0、capacity 1；未标注但硬过滤合格的 c006 是 capability 3/3、industry 0、region 0、capacity 1。c006 在 capability 上严格更高、其余三项相同，因此**任何非负四特征权重**都会把 c006 排在 c022 之前；若 c022 进入 top6，c006 也必然进入，再加另外 5 个正例需要 7 个位置。所以没有任何非负四特征权重能让每条需求的 top6 覆盖全部 190 个正例。`tests/test_label_independence.py` 穷举 1771 组权重断言这一点，`artifacts/weight-grid.json` 的 `dominance_witnesses` 记录该反例。

  因此能声称的是“标签不由 v1/v2 权重生成，且 top6 标签集合不能被任何非负四特征权重完整复现”；不能声称“与业务事实无关”。
- **案例数的边界**：`case_strength` 的 `verified_cases` 是公司级案例数，没有按能力或行业拆分。它表示“该公司有交付记录”，不表示“该公司在本次 required capabilities 上有记录”。

## 3. +0.075025 不是 v2 更好的证明

v1 NDCG@10=0.890098，v2=0.965123，v2−v1=+0.075025；compare 的“退步（左−右）”= -0.075025，未超过 0.02，verdict=pass，退出码 0。

这个差值必须和随机化基线一起读。固定负例、硬过滤和排序，按每条需求的实际正例数随机替换正例，跑 500 个种子：

| 抽样池 | 中位 v2−v1 | v2>v1 的种子数 | 实际标签百分位 |
| --- | ---: | ---: | ---: |
| qualified（覆盖 ≥2，与正式标签同底线） | +0.075438 | 500/500 | 41.0 |
| covered（覆盖 ≥1） | +0.023730 | 484/500 | 100.0 |
| eligible（无底线） | -0.000253 | 247/500 | 100.0 |

- 与正式标签同底线时，几乎任何随机标签集都会让 v2 略高；实际标签的 +0.075025 位于第 41.0 百分位，说明它没有被调成偏向 v2。
- covered 池中实际标签差值是 500 个随机集的最高值（百分位 100），说明“覆盖 ≥2”底线本身显著放大了 v2 的优势。
- 去掉底线后，v2 只在 247/500 个随机集中胜出，中位 -0.000253，95% 区间跨 0。因此 +0.075025 是夹具上的具体一致性结果，不是泛化结论。
- 完整方法与复现：`docs/LABEL-BASELINE.md`、`python scripts/label_sensitivity.py`、`artifacts/label-sensitivity.json`。

## 4. 正例口径：2/3 与 3/3，没有 1/3

- 190 个正例中，3/3 覆盖 113 个、2/3 覆盖 77 个、1/3 覆盖 0 个。可推荐底线是“至少覆盖两个 required capability”，这是业务口径，不是评测权重。
- 每条需求正例数：1 条=7、2 条=11、3 条=21、4 条=11、5 条=6、6 条=4。槽位弃权产生这些差异，不是强行凑满六条。
- 槽位计数：capability_lead 54、case_strength 30、responsiveness 27、industry_fit 22、regional_fit 34、capacity_fit 23。弃权发生在更稀缺槽位先选完候选之后。
- 不能把底线提高到 3/3：本数据只有 113 个正例达到 3/3；若客户要求“正例必须完全覆盖 required capabilities”，需要改数据生成规则、重做标注并重跑全部指标，不能只改文档。
- 逐条理由写在 `data/annotations.json` 的 `positive_slots` 中，评审可以按理由反驳某一条；这比只给一个总分更可审计。

## 5. NDCG、top6 与集中度

- NDCG@10 是二值相关性：应推荐=1，不应推荐和未标注=0；按每个需求的理想 DCG 归一后取平均。
- v2 在 31 条需求上更好、28 条持平、1 条更差；逐需求 NDCG 最低 0.644784、最高 1.0。
- 190 个正例全部落在 v2 全量排名前 10 内（中位第 2、最差第 8）。因此 NDCG 与 top6 集合的差异主要来自位置权重与集合口径，不是“正例被排到 10 名之外”。
- v2 top6 精确等于标签集只在“该需求恰好 6 个正例”时有意义：本数据有 4 条，所以是 2/4；top6 覆盖全部标签 51/60，交集 180/190。精确集合一致要求六个位置全对，不能用它单独判断标签质量。
- Hit@5 为 1.000000/1.000000 是因为每条需求至少 1 个正例，而 Hit@5 只要求前 5 名至少一个正例；这个指标在当前夹具上区分力有限，仍按任务要求报告。
- 硬过滤违规数为 0，理由可追溯率为 1.0；这两项是当前夹具的回归基线，不是线上保证。
- 前 5 名 HHI 为 0.051467/0.053333，top1 为 0.083333/0.096667，覆盖 23 家公司；这是观察指标，没有硬门槛。v2 的集中度略高，不构成“更好”或“更差”。

## 6. 复现与核对

```bash
python scripts/build_annotations.py
python scripts/generate_dataset.py
python -m match_eval stats
python -m match_eval evaluate --weights v1 --report artifacts/report-v1.md
python -m match_eval evaluate --weights v2 --report artifacts/report-v2.md
python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
python -m pytest tests
python scripts/manual_review.py
python scripts/label_sensitivity.py
python scripts/weight_grid.py
python scripts/run_acceptance.py
```

核对入口：

- 标签独立性：`tests/test_dataset.py`（AST import）、`tests/test_labeling.py`（golden hash、重放、权重扰动）、`tests/test_label_independence.py`（支配反例与 1771 组网格穷举）。
- 冻结标签：`data/annotations.json` 是标注产物，`data/demands.json` 只是套用结果。
- 随机化基线与网格：`docs/LABEL-BASELINE.md`、`scripts/label_sensitivity.py`、`scripts/weight_grid.py`、`artifacts/label-sensitivity.json`、`artifacts/weight-grid.json`。
- 数字与报告：`artifacts/report-v1.md`、`artifacts/report-v2.md`、`artifacts/report-compare.md`、`artifacts/ACCEPTANCE.md`。
- 人工复核：`docs/MANUAL-REVIEW.md`；签字前状态为 pending-human-signoff。

任何对外报告都应同时引用本文件；只引用单一高分、不说明标签口径，会构成误导。
