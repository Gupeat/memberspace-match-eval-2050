# match-eval：会员空间匹配排序离线评测

本项目是 ClawHunt 任务 #2050（【S3-MATCH-030】匹配排序评测集与离线评测脚本）的交付实现。

目标：用 40 家虚构企业、30 条供给和 60 条需求构造可重复运行的离线匹配排序夹具；按指定权重计算 Hit@5、NDCG@10、硬过滤违规数、理由可追溯率和前 5 名企业集中度；支持两个权重版本对比，并在违规或 NDCG@10 退步超过 2 个百分点时返回非 0 退出码。

本仓库只做离线评测：不写生产 AI 队列、不触发对外联系、不涉及金额、不包含真实企业或真实联系人。

## 快速开始

在 repo 根目录执行（Python 3.11+）：

```bash
python scripts/build_annotations.py
python scripts/generate_dataset.py
python -m match_eval stats
python -m match_eval evaluate --weights v1 --report artifacts/report-v1.md
python -m match_eval evaluate --weights v2 --report artifacts/report-v2.md
python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
python -m pytest tests
python scripts/run_acceptance.py
python scripts/manual_review.py
python scripts/label_sensitivity.py
```

`build_annotations.py` 先读 `scripts/fixture_spec.py` 的手写企业规格和 `data/editorial-signals.json` 生成冻结标签；`generate_dataset.py` 再把标签套到数据上。这两步只在重建标签时运行；日常评测从 `stats` 开始，权重网格证据用 `python scripts/weight_grid.py`。

## 第 3 轮改了什么

第 2 轮审核的 blocker 是“标签由 v2 同系数公式生成，排序器在评自己”。本轮不是改文档措辞，而是重写夹具与标注，并修掉数据层缺陷：

1. **手写企业、确定性派生供给与需求**：40 家企业的名称、能力卡、行业、区域、容量、冲突关系由 `scripts/fixture_spec.py` 逐家手写，能力卡与名称语义一致（青石法务=legal/finance/consulting，松间餐饮=catering/venue/event_planning 等），16 个能力全部出现；30 条供给由企业列表派生（覆盖 c001–c029 + c032，s009/s018/s028 为 paused）；60 条需求按 8 种类型和 2–3 个能力变体确定性生成。每需求 required 2–3 个，preferred 1–2 个；本数据可出现 3/3 覆盖（113 条正例），不再是上一版“最多 2/3”。
2. **六编辑槽位**：`scripts/labeling.py` 的 capability_lead / case_strength / responsiveness / industry_fit / regional_fit / capacity_fit 各用主信号词典序选人；全程无加权和。槽位可以弃权，因此每条需求 1–6 个正例，而不是强行凑满 6 个。
3. **两个真正的新信号**：`data/editorial-signals.json` 的 `verified_cases`、`response_days`、`max_response_days` 只给标注用，评测器从不读取；capability_lead 用 IDF 稀缺度密度，不是评测器的覆盖比例。行业、区域、产能三个槽位是对评测器也使用的业务事实的**另一种编辑口径**，不声称是独立信号。
4. **可复算、可复现**：`scripts/manual_review.py` 用同一 `labeling` 逐条重放六槽位与四负例；`tests/test_labeling.py` 做 golden hash、逐条重放、任意权重重跑后数据逐字节不变；`scripts/label_sensitivity.py` 做随机化基线；`scripts/weight_grid.py` 枚举 1771 组四特征权重；`docs/LABEL-BASELINE.md` 披露结果。

详细规则见 `data/ANNOTATION.md`，验收对照见 `docs/REVIEW-GUIDE.md`。

## 目录

```text
match_eval/
  dataset.py      数据类、JSON 加载、结构校验
  filters.py      硬过滤规则
  scoring.py      特征、权重加载、排序与理由
  metrics.py      Hit@5、NDCG@10、违规、可追溯率、集中度
  evaluate.py     端到端评测编排
  report.py       Markdown 报告（含可复现命令）
  cli.py          命令行与退出码
data/
  ANNOTATION.md           标注规则、独立性边界、基线、限制
  annotations.json        冻结标签（六槽位 + 逐条理由）
  editorial-signals.json  仅标注用信号（案例数/响应天数）
  companies.json          40 家虚构企业
  supplies.json           30 条虚构供给（27 条 active）
  demands.json            60 条虚构需求（标签由 annotations.json 套用）
weights/
  v1.json  基础版权重（0.45/0.25/0.20/0.10）
  v2.json  能力增强版（0.55/0.25/0.10/0.10）
scripts/
  fixture_spec.py        手写企业规格；供给/需求确定性派生
  labeling.py            六编辑槽位规则（唯一标签规则源）
  build_annotations.py   生成 data/annotations.json
  generate_dataset.py    套用冻结标签，生成 data/*.json
  manual_review.py       机器复核包（默认待人工签字）
  label_sensitivity.py   标签随机化基线
  weight_grid.py         1771 组四特征权重枚举
  run_acceptance.py      AC1–AC6 验收对照
tests/                   68 个单元/集成测试
docs/                    评测边界、复核指南、rework 证据
artifacts/               报告、验收、复核包；history/ 为历史存档
```

## 数据契约

### 企业（40）

字段：id、name、summary、capabilities、industries、region、capacity、accepting、conflicts_with。

- capabilities：16 个能力标签，全部在数据中出现。
- industries：10 个行业标签；region：east、south、north、west、central；capacity：small、medium、large。
- accepting=false 表示暂不接受对接（c005、c016、c026）；conflicts_with 是双向冲突关系，加载时强制校验对称性。

### 供给（30）

字段：id、company_id、title、summary、capabilities、industries、region、capacity、status。

27 条 status=active；3 条 paused（s009、s018、s028，对应企业 c009、c018、c028）。供给覆盖 c001–c029 + c032；其余 10 家企业（c030、c031、c033–c040）没有供给，不进入候选池。供给能力取所属企业能力卡的前两个。

### 需求（60）

字段：id、type、title、summary、requester_company_id、required_capabilities、preferred_industries、region、capacity_need、rejected_company_ids、should_recommend、should_not_recommend、annotation_note。

- 8 种类型：event、marketing、hiring、legal、finance、it、training、sourcing；每种 7 或 8 条。
- 每条需求 1–6 个应推荐、4 个不应推荐；正例数按六个编辑槽位的合格候选决定，不强行补足。
- 负例组成：2 个 rejected；1 个 not_accepting；有冲突对象时再取 1 个 conflict，否则取第二个 not_accepting。本数据合计 rejected 120、not_accepting 104、conflict 16（44/60 条需求没有 conflict）。
- 标签由六编辑槽位生成后冻结在 `data/annotations.json`；`scripts/generate_dataset.py` 只套用，不计算标签、不读权重。

### 标注覆盖

| 项 | 值 |
| --- | ---: |
| 应推荐正例 | 190 |
| 不应推荐负例 | 240 |
| 正例覆盖 | 3/3 = 113；2/3 = 77；1/3 = 0 |
| 每需求正例数 | 1 条=7；2 条=11；3 条=21；4 条=11；5 条=6；6 条=4 |

可推荐底线是“至少覆盖两个 required capability”。这既是业务口径，也是本轮对上一版“只命中一个能力也算正例”的修正；它不读取 v1/v2 权重，但会系统性影响指标，详见 `docs/EVALUATION-LIMITS.md`。

## 标注与硬过滤

硬过滤在任何打分之前执行。原因与优先级：

| 优先级 | 原因 | 条件 |
| --- | --- | --- |
| 1 | self | 候选企业就是需求方 |
| 2 | not_accepting | 企业 accepting=false |
| 3 | rejected | 企业在该需求的 rejected_company_ids 中 |
| 4 | conflict | 企业与需求方存在双向冲突 |
| 5 | no_active_supply | 企业没有 active 供给 |

硬过滤违规数统计返回的前 10 名中仍然命中上述排除集合的条目数。正式评测目标为 0；大于 0 时 evaluate 返回退出码 2。

## 指标

- Hit@5：前 5 名中至少有一个应推荐企业的需求占比。
- NDCG@10：二值相关性，应推荐=1，不应推荐和未标注=0；按每个需求的理想 DCG 归一后取平均。
- 硬过滤违规数：所有需求前 10 名的违规条目总数。
- 理由可追溯率：前 10 名中理由字段完整，且能力命中、行业、区域、容量、活跃供给、摘要可由数据集回算的条目占比，目标 1.0。
- 前 5 名企业集中度：所有需求前 5 名共 300 个槽位的公司分布，报告 HHI、最高公司占比和覆盖公司数；观察指标，不设硬门槛。

## 权重版本

v1（基础版）：capability 0.45、industry 0.25、region 0.20、capacity 0.10，更强调本地供给。

v2（能力增强版）：capability 0.55、industry 0.25、region 0.10、capacity 0.10，更强调能力覆盖，是默认评测版本。

两个版本都通过同一套数据、同一套硬过滤和同一套指标代码运行，只有权重不同。标签不读取这两个文件。

## 当前冻结结果

| 指标 | v1 | v2 |
| --- | ---: | ---: |
| 需求条数 | 60 | 60 |
| 覆盖需求类型数 | 8 | 8 |
| Hit@5 | 1.000000 | 1.000000 |
| NDCG@10 | 0.890098 | 0.965123 |
| 硬过滤违规数 | 0 | 0 |
| 理由可追溯率 | 1.000000 | 1.000000 |
| 前 5 名 HHI | 0.051467 | 0.053333 |
| 前 5 名最高公司占比 | 0.083333 | 0.096667 |
| 覆盖公司数 | 23 | 23 |

对比结论：v2 − v1 = **+0.075025**；compare 报告的“退步（左−右）”= -0.075025，未超过 0.02 的退步阈值；两个版本违规均为 0；退出码为 0。逐需求看，v2 在 31 条上更好、28 条持平、1 条更差，最大提升 +0.5。详见 `artifacts/report-compare.md`。

这些数字是合成夹具上的回归结果，不是线上效果估计。

## 标签敏感度：+0.075025 不是“v2 更好”的证明

固定负例、硬过滤和排序，按每条需求实际正例数随机替换，跑 500 个种子：

| 抽样池 | 中位 v2−v1 | v2>v1 | 实际标签百分位 |
| --- | ---: | ---: | ---: |
| qualified（覆盖 ≥2，与正式标签同底线） | +0.075438 | 500/500 | 41.0 |
| covered（覆盖 ≥1） | +0.023730 | 484/500 | 100.0 |
| 全部 eligible（无底线） | -0.000253 | 247/500 | 100.0 |

保留“覆盖 ≥2”时，随机标签几乎都会让 v2 略高；实际标签的 +0.075025 位于第 41.0 百分位，说明本标签集没有被调成偏向 v2。去掉底线后优势基本消失（247/500），所以这个差值不能解释成 v2 的泛化优势。完整方法、数字和限制见 `docs/LABEL-BASELINE.md`；复现命令 `python scripts/label_sensitivity.py`。

## 权重网格：独立性边界

`scripts/weight_grid.py` 枚举 0.05 步长、四权重非负且和为 1 的全部 1771 组权重。结果：网格内最好的权重也只能让 **58/60** 条需求的 top6 覆盖全部正例（capability 0.65 / industry 0.00 / region 0.15 / capacity 0.20；正例召回 188/190）；best NDCG@10=0.996243。v1/v2 的 top6 正例召回分别为 169/190、180/190。

这不是“网格不够密”，而是结构性的：d052 有 6 个正例，其中 c022 的特征是 capability 2/3、industry 0、region 0、capacity 1；未标注但硬过滤合格的 c006 是 capability 3/3、industry 0、region 0、capacity 1。c006 在 capability 上严格更高、其余三项相同，因此**任何非负四特征权重**都会把 c006 排在 c022 之前。若 c022 进入 top6，c006 也必然进入 top6，再加上另外 5 个正例就是 7 个候选，6 个槽位装不下。所以没有任何非负四特征权重能让每条需求的 top6 覆盖全部 190 个正例；`tests/test_label_independence.py` 对全部 1771 组网格做了穷举断言，`scripts/weight_grid.py` 把该支配反例写入 `artifacts/weight-grid.json` 的 `dominance_witnesses` 字段。

标签仍与评测器共享企业能力、行业、区域、容量这些业务事实，因此**不声称与业务事实无关**；能声称的是“标签不由 v1/v2 权重生成，且其 top6 集合不能被任何非负四特征权重完整复现”。

## 独立性证据与边界

- **静态**：`tests/test_dataset.py` 用 AST 检查 generator、builder、labeling、fixture 不导入 `match_eval` 或 `weights`。
- **行为**：`tests/test_labeling.py` 在临时目录写入任意 v1/v2 权重，重跑 builder + generator，四个 `data/*.json` 与基线逐字节相同。
- **支配反例**：`tests/test_label_independence.py` 对 d052 的 c006→c022 做逐特征断言，并穷举 1771 组权重证明 d052 的 6 个正例不可能全部进入 top6。
- **新信号**：案例数与响应天数只存在于 `data/editorial-signals.json`，评测器从不读取；只有这两个槽位是评测器没有的信号，其余三个槽位（行业、区域、产能）是同一业务事实的不同编辑口径。

## 退出码

| 退出码 | 含义 |
| --- | ---: |
| 0 | 成功；正式 evaluate 违规为 0；compare 无违规且无超过 2 个百分点的 NDCG@10 退步 |
| 1 | 数据/权重/参数错误 |
| 2 | 正式评测或对比评测出现硬过滤违规 |
| 3 | compare 中右侧版本 NDCG@10 退步超过 0.02 |

`--no-hard-filter` 只用于验证“违规时退出码非 0”这一验收点，生成的是诊断报告，不是对外推荐结果。任务 AC3 的退出码 2 也由这个诊断模式证明；正式评测的违规数恒为 0。

## 验收

`artifacts/ACCEPTANCE.md` 记录 AC1–AC6 的命令、退出码、证据和五个数据文件的 sha256。当前全量测试 **68 passed**；验收运行 `all_passed True`。

| AC | 证据 |
| --- | --- |
| AC1 | 60 条需求、8 种类型；`python -m match_eval stats` |
| AC2 | 每个指标一个专用测试文件；5 个文件共 14 passed |
| AC3 | `--no-hard-filter` 诊断 222 个违规，退出码 2 |
| AC4 | `artifacts/report-compare.md`，v1/v2 对比，verdict=pass |
| AC5 | 正式评测违规 0、理由可追溯率 1.0（v1 与 v2 均跑） |
| AC6 | 全量测试 68 passed |

逐条命令与期望输出见 `docs/REVIEW-GUIDE.md`。历史轮次存档在 `artifacts/history/`，数字已过期，不要引用。

## 人工复核状态

`scripts/manual_review.py` 用同一 `labeling` 重放六槽位和四负例，生成 `artifacts/manual-review.json`、`artifacts/manual-review.csv`、`docs/MANUAL-REVIEW.md`：60 条需求 / 190 个正例 / 240 个负例，0 个标签缺陷、0 个检查失败、0 个重放不一致。默认状态是 **pending-human-signoff**；只有同时传 `--reviewer` 与 `--attest` 才写 `human-reviewed`。签字前不能称为“人工标注已完成”。

v2 top6 精确等于标签集只在“该需求恰好 6 个正例”时有意义：本数据有 4 条这样的需求，因此是 2/4；v2 top6 覆盖全部标签为 51/60，交集总数 180/190。190 个正例全部落在 v2 全量排名前 10 内（中位第 2，最差第 8），所以 NDCG 与 top6 集合的差异来自位置权重与集合口径，不是标签缺陷。

## 限制

- 合成数据规模有限，标注是规则生成的编辑式合成标签，不代表真实业务分布；复核包尚无人类签字。
- 标签不由 v1/v2 权重生成，但仍与企业能力/行业/区域/容量这些业务事实相关；不能据此声称 v2 在真实数据上更好。
- 保留“覆盖 ≥2”的业务底线会系统性抬高 v2；去掉底线后 v2 在随机 eligible 标签中只赢 247/500，差值中位 -0.000253。该限制已在 README、`docs/EVALUATION-LIMITS.md`、`docs/LABEL-BASELINE.md` 中披露。
- 没有真实企业库、联系人、金额和线上反馈；不接入生产 AI 队列。
- 只支持单机离线 JSON；没有数据库、网络和外部服务依赖。
- 集中度是观察指标，当前 v2 的 HHI 略高，不代表线上一定更集中。
- 正式提交前需要用户明确批准；仓库内不会自动提交。
