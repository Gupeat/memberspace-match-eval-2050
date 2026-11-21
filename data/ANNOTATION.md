# 标注说明（合成夹具 · 六编辑槽位 v2）

本目录是 ClawHunt #2050 的离线评测夹具。所有企业、供给、需求和标注均为虚构，仅用于验证匹配排序指标、退出码和可复现流程；不是线上人工样本，不能用来估计线上效果。

## 规模

| 项 | 值 |
| --- | ---: |
| 企业 | 40（c001–c040，逐家手写） |
| 供给 | 30（s001–s030；27 条 active，3 条 paused：s009/s018/s028） |
| 需求 | 60（d001–d060，按 8 类型确定性派生） |
| 需求类型 | 8（event/marketing/hiring/legal 各 8；finance/it/training/sourcing 各 7） |
| 正例合计 | 186 |
| 负例合计 | 240 |
| 每需求正例数 | 1 条=7；2 条=8；3 条=27；4 条=9；5 条=8；6 条=1 |
| 正例覆盖 | 3/3 = 57；2/3 = 129；1/3 = 0 |

可推荐底线是“至少覆盖两个 required capability”。这条底线是业务口径，不读取 v1/v2 权重；它会影响指标，因此在 README、`docs/EVALUATION-LIMITS.md` 和 `docs/LABEL-BASELINE.md` 中单独披露。

## 为什么第 3 轮重做

第 2 轮审核指出两个实质问题：

1. 上一版标签由 `annotation_score = 0.55 * capability + 0.25 * industry + 0.10 * region + 0.10 * capacity` 生成，与 `weights/v2.json` 的系数完全相同；排序器在评自己。
2. 上一版数据由索引循环生成，企业名与能力卡不符；required capability 恒为 3 个，而企业最多覆盖 2 个，因此不可能出现 3/3；`catering`、`legal` 等能力在数据中从未出现。

本轮同时重写夹具与标签：

- `scripts/fixture_spec.py`：手写 40 家企业及其能力卡、行业、区域、容量、冲突关系；30 条供给与 60 条需求由该规格确定性派生（供给取企业能力卡前两个能力；需求按类型/变体取模）。
- `data/editorial-signals.json`：只给标注用的 `verified_cases`、`response_days`、`max_response_days`，评测器永不读取。
- `scripts/labeling.py`：六个编辑槽位，纯词典序，没有加权和。
- `scripts/build_annotations.py`：从 fixture + signals 生成并冻结 `data/annotations.json`。
- `scripts/generate_dataset.py`：只套用冻结标签，不计算标签、不读权重，也不读生成后的 `data/demands.json`，避免“builder 依赖 generator 产物”的循环。

## 六个编辑槽位

每个槽位最多选一个尚未入选的企业；槽位可以弃权。槽位内的排序键是词典序，不是加权和：

| 槽位 | 资格 | 主信号 | 同分时的短 tie-break | 评测器是否使用 |
| --- | --- | --- | --- | --- |
| capability_lead | 覆盖 ≥2 | 匹配能力的平均 IDF 稀缺度密度 | 覆盖数、响应天数、company_id | 评测器用覆盖比例，不用 IDF |
| case_strength | 覆盖 ≥2 且有案例 | 公司级已核实交付案例数 `verified_cases` | IDF 密度、覆盖数、company_id | 否 |
| responsiveness | 覆盖 ≥2 且不超时 | `response_days <= max_response_days`，再按响应天数 | IDF 密度、覆盖数、company_id | 否 |
| industry_fit | 覆盖 ≥2 且命中行业 | 命中 preferred industries 的个数 | IDF 密度、案例数、company_id | 评测器用 0/1 命中标志 |
| regional_fit | 覆盖 ≥2 且同区/邻区 | 同区 0、邻区 1、远区 2 | IDF 密度、案例数、company_id | 评测器只区分同区/不同区 |
| capacity_fit | 覆盖 ≥2 且容量达标 | 先看容量是否达到需求，再看最小够用余量 | IDF 密度、company_id | 评测器用达到/未达到阈值 |

选择顺序：

1. 先过滤出合格候选：active supply、非需求方、`accepting=true`、无冲突、不在 `rejected_company_ids`、至少命中一个 required capability；
2. 只保留覆盖 ≥2 的候选；
3. 为每个槽位建立“满足该槽位资格”的候选池；
4. 按池大小升序处理槽位（稀缺优先），同池大小按 `SLOT_ORDER`；
5. 每个槽位从“尚未入选”的合格候选中取词典序最小者；若没有剩余候选，弃权；
6. 最终按 `SLOT_ORDER` 输出 1–6 条正例。

槽位计数：capability_lead 57、case_strength 30、responsiveness 22、industry_fit 22、regional_fit 33、capacity_fit 22。capability_lead 在 3 条需求上没有剩余候选而弃权（其他更稀缺槽位先选走了所有覆盖 ≥2 的候选），不是“整个需求没有合格候选”。

关键点：

- **没有任何槽位使用 0.40/0.20/0.20/0.20 或 0.55/0.25/0.10/0.10 加权和**；每个槽位只按自己的主信号排序。
- `capability_lead` 使用语料级 IDF 密度（`sum(IDF)/coverage`），不是评测器的 `|required ∩ capabilities| / |required|`；覆盖数只在密度相同时作 tie-break。这里不声称两者正交，只声称计算方式不同。
- `case_strength` 与 `responsiveness` 依赖 `data/editorial-signals.json`；该文件不在 `match_eval` 的读取路径中。
- `verified_cases` 是**公司级**案例数，没有按能力或行业拆分；因此 `case_strength` 只表示“该公司有交付记录”，不表示“该公司在本次 required capabilities 上有记录”。这是本轮的已知简化，已在限制中披露。
- 六个槽位的 tie-break 会复用其他编辑信号（例如案例槽在案例数相同时看 IDF），这是为了确定性，不是给评测器加权；审计时可逐条复算。

## 候选池与负例

候选池 = 有 active 供给、不是需求方、`accepting=true`、与需求方无冲突、且不在该需求已声明的 `rejected_company_ids` 中。正例还必须覆盖至少两个 required capability（业务底线）。

负例：

- 2 个 `rejected`：由 `scripts/fixture_spec.py` 的 `_pick_rejected` 在候选池中确定性选取，优先选不在 capability-covered 集合中的企业；这是夹具声明，不是标签；
- 1 个 `not_accepting`：有 active 供给但 `accepting=false`；
- 1 个 `conflict`：与需求方存在双向冲突；若该需求方没有冲突对象，则用第二个 `not_accepting`。

本数据负例原因合计：`rejected` 120、`not_accepting` 104、`conflict` 16。只有 16/60 条需求有 conflict，所以“固定 2+1+1”只对负例总数成立，不应对每条需求都这样宣称。

## 独立性证据与边界

1. **静态**：`tests/test_dataset.py` 用 AST 检查 `generate_dataset.py`、`build_annotations.py`、`labeling.py`、`fixture_spec.py` 不导入 `match_eval` 或 `weights`；`tests/test_labeling.py` 断言 builder 产物中没有 `annotation_score`。
2. **行为**：`tests/test_labeling.py` 在临时目录写入任意 v1/v2 权重（0.123/0.456/0.789/0.321），重跑 builder + generator，四个 `data/*.json` 与基线逐字节相同。权重变化不会改变标签。
3. **新信号**：案例数与响应天数只存在于 `data/editorial-signals.json`，评测器从不读取；它们直接影响两个槽位和多个 tie-break。行业、区域、产能三个槽位是对评测器也使用的业务事实的不同编辑口径，不是新信号。
4. **网格披露**：`scripts/weight_grid.py` 枚举 0.05 步长、四权重非负且和为 1 的全部 **1771** 组权重。存在一组权重（0.60/0.10/0.15/0.15）使每需求 top6 覆盖全部 186 个正例；best NDCG@10=0.999187。因此不能声称“标签与任何四特征加权和不等价”；能声称的只有“标签不由 v1/v2 权重生成”。

## 标签敏感度（随机化基线）

固定负例、硬过滤和排序，按每条需求的实际正例数随机替换正例，跑 500 个种子：

| 抽样池 | min | p05 | median | p95 | max | v2>v1 | 实际标签百分位 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| qualified（覆盖 ≥2，与正式标签同底线） | +0.074426 | +0.074426 | +0.076281 | +0.079730 | +0.079730 | 500/500 | 47.2 |
| covered（覆盖 ≥1） | -0.015229 | +0.006834 | +0.026651 | +0.046156 | +0.061762 | 491/500 | 100.0 |
| eligible（无底线） | -0.030290 | -0.018102 | +0.000717 | +0.021024 | +0.039774 | 256/500 | 100.0 |

解读：

- 与正式标签同底线（覆盖 ≥2）时，随机标签集几乎都会让 v2 略高；实际标签 +0.076120 位于第 47.2 百分位，**没有**被调成让 v2 赢更多。
- covered 池（覆盖 ≥1）中位 +0.026651，实际标签差值高于全部 500 个随机集（百分位 100），说明“覆盖 ≥2”这条底线本身显著放大了 v2 的优势。
- eligible 池（无底线）中位 +0.000717，v2 只赢 256/500，95% 区间跨 0。因此 +0.076120 不能脱离业务底线被解释成 v2 的泛化优势。
- 复现：`python scripts/label_sensitivity.py`（默认 500 seeds，结果确定性可复现，同时写 `artifacts/label-sensitivity.json`）。

## 当前数字（本轮冻结）

| 指标 | v1 | v2 |
| --- | ---: | ---: |
| Hit@5 | 1.000000 | 1.000000 |
| NDCG@10 | 0.894126 | 0.970246 |
| 硬过滤违规数 | 0 | 0 |
| 理由可追溯率 | 1.000000 | 1.000000 |
| 前 5 名 HHI | 0.049556 | 0.050844 |
| 前 5 名最高公司占比 | 0.080000 | 0.083333 |
| 覆盖公司数 | 23 | 23 |

v2 − v1 = **+0.076120**；compare 的“退步（左−右）”= -0.076120，未超过 0.02，verdict=pass，退出码 0。v2 在 31 条需求上更好、29 条持平、0 条更差。v2 top6 精确等于标签集只在“该需求恰好 6 个正例”时有意义：本数据只有 1 条，所以是 1/1；top6 覆盖全部标签 54/60，交集 180/186。186 个正例全部落在 v2 全量前 10（中位第 2、最差第 8），NDCG 与 top6 集合不是同一个量。

## 复现

在本目录的上一级（repo 根目录）执行：

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
```

Python 3.11+；本机没有裸 `python` 时，把命令里的 `python` 换成你的解释器路径。

## 复核方式

1. `python -m match_eval stats`：核对 40/30/60、8 种类型、186/240 标注。
2. `python -m pytest tests`：66 个测试，覆盖数据规模、正负例约束、槽位资格、逐条重放、AST import、golden hash、权重扰动不变性、报告复现命令。
3. `python scripts/manual_review.py`：生成 60 条需求 / 426 个标签的复核包；默认 `pending-human-signoff`，只有同时传 `--reviewer` 与 `--attest` 才写 `human-reviewed`。
4. `python scripts/label_sensitivity.py`：重跑随机化基线。
5. `python scripts/weight_grid.py`：重跑 1771 组网格。
6. `python scripts/run_acceptance.py`：生成 `artifacts/ACCEPTANCE.md`（AC1–AC6、数据哈希）。

## 数据哈希（sha256）

| 文件 | sha256 |
| --- | --- |
| data/companies.json | fafade43c7142f2ed1a1e91d4565f2e75a5afb390540ed5dea8d0c6e18c2a07d |
| data/supplies.json | 1e51c471d11058cb7c34a1da263d7cb1499675ea503bf23af3f71b621c87ec31 |
| data/demands.json | 15637e438652ea574bef71db66429f311a4f400345c46b722e31b92fd2c26d6f |
| data/annotations.json | c42a743699c38cf77942279c52ecefb506b39c8ecec6a8603bdbe1700ed8d1ce |
| data/editorial-signals.json | e77329acc3e157e625e87876eaadc3aa23cadd079f71bb7e6a887565b0960dd1 |

## 限制

- 这是**规则生成的编辑式合成标注**，不是人工逐条标注；`scripts/manual_review.py` 的复核包在人类签字前不能称为“人工标注”。
- 正例底线是覆盖 ≥2，不是全覆盖；本数据 2/3 覆盖 129 条、3/3 覆盖 57 条。若客户要求 3/3 全覆盖，需要重做数据与标签。
- `case_strength` 的案例数是公司级的，不按 required capabilities 拆分；它不能证明该公司在本需求的能力上有交付记录。
- 评测器与标签共享企业能力、行业、区域、容量这些业务事实；独立性只到“不由 v1/v2 权重生成”，不是“与业务事实无关”，也不是“与任何四特征加权和不等价”。
- 60 条适合回归测试，不足以覆盖真实长尾；0.970246 不是线上效果估计。
- 若接入真实数据，应保留 `should_recommend`、`should_not_recommend`、`rejected_company_ids`、`annotation_note` 字段，替换 JSON 后重跑同一套指标与测试。
