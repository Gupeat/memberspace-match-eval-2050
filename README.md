# match-eval：会员空间匹配排序离线评测

本项目是 ClawHunt 任务 #2050（【S3-MATCH-030】匹配排序评测集与离线评测脚本）的交付实现。

目标：用 40 家虚构企业、30 条供给和 60 条需求构造一个可重复运行的离线匹配排序评测夹具；按指定权重计算 Hit@5、NDCG@10、硬过滤违规数、理由可追溯率和前 5 名企业集中度；支持两个权重版本对比，并在违规或 NDCG@10 退步超过 2 个百分点时返回非 0 退出码。

本仓库只做离线评测：不写生产 AI 队列、不触发对外联系、不涉及金额、不包含真实企业或真实联系人。

## 快速开始

在 repo 根目录执行（Python 3.11+）：

    python -m match_eval stats
    python -m match_eval evaluate --weights v1 --report artifacts/report-v1.md
    python -m match_eval evaluate --weights v2 --report artifacts/report-v2.md
    python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
    python -m pytest tests
    python scripts/run_acceptance.py
    python scripts/manual_review.py

重新生成冻结数据（可选）：

    python scripts/generate_dataset.py

生成器是确定性的；同一版本脚本会得到逐字节相同的 data/*.json 文件。正式评测只读取生成后的 JSON，不读取生成器运行时的随机状态。

## 目录

    match_eval/
      dataset.py      数据类、JSON 加载、结构校验
      filters.py      硬过滤规则
      scoring.py      特征、权重加载、排序与理由
      metrics.py      Hit@5、NDCG@10、违规、可追溯率、集中度
      evaluate.py     端到端评测编排
      report.py       Markdown 报告
      cli.py         命令行与退出码
      __main__.py     python -m match_eval 入口
    data/
      ANNOTATION.md   标注规则、规模与限制
      companies.json  40 家虚构企业
      supplies.json   30 条虚构供给（27 条活跃）
      demands.json    60 条虚构需求与冻结标注
    weights/
      v1.json         基础版权重
      v2.json         能力增强版权重
    scripts/
      generate_dataset.py  确定性数据生成器
      run_acceptance.py    验收对照运行器
      manual_review.py     60 条需求 / 600 个标签的复核包生成器
    tests/           55 个单元/集成测试（含 5 个指标各自的专用测试文件）
    artifacts/       报告、验收报告、两轮日志、变异演练日志、manual-review.json/csv

## 数据契约

### 企业（40）

字段：id、name、summary、capabilities、industries、region、capacity、accepting、conflicts_with。

- capabilities：能力标签，来自 event_planning、venue、catering、av、marketing、design、media、photography、legal、finance、hr、it、training、consulting、logistics、translation 等。
- industries：行业标签；region：east、south、north、west、central；capacity：small、medium、large。
- accepting=false 表示暂不接受对接。
- conflicts_with 是双向冲突关系，加载时强制校验对称性。

### 供给（30）

字段：id、company_id、title、summary、capabilities、industries、region、capacity、status。

27 条 status=active；3 条 paused。没有活跃供给的企业不进入候选池。

### 需求（60）

字段：id、type、title、summary、requester_company_id、required_capabilities、preferred_industries、region、capacity_need、rejected_company_ids、should_recommend、should_not_recommend、annotation_note。

- 8 种类型：event、marketing、hiring、legal、finance、it、training、sourcing；每种 7 或 8 条。
- 每条需求固定 6 个应推荐企业、4 个不应推荐标注。
- 不应推荐原因覆盖 rejected（已拒绝组合）、not_accepting（暂不接受对接）、conflict（冲突关系）。
- 标注文件是冻结的合成夹具标注：由固定相关性规则生成后写入 demands.json，不从运行时权重反向生成。它是可复核的合成标注，不是线上人工标注样本，不能用来估计线上效果。scripts/manual_review.py 会逐条重放规则并生成待签字复核包；签字前不得称为“人工标注”。

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
- 理由可追溯率：前 10 名中理由字段完整（能力命中、行业、区域、容量、活跃供给、摘要）的条目占比，目标 1.0。
- 前 5 名企业集中度：所有需求前 5 名共 300 个槽位的公司分布，报告 HHI、最高公司占比和覆盖公司数；这是观察指标，不设硬门槛。

## 权重版本

v1（基础版）：capability 0.45、industry 0.25、region 0.20、capacity 0.10。更强调本地供给。

v2（能力增强版）：capability 0.55、industry 0.25、region 0.10、capacity 0.10。更强调能力覆盖，是默认评测版本。

两个版本都通过同一套数据、同一套硬过滤和同一套指标代码运行，只有权重不同。

## 方法论警示：v2 的 0.9928 不是泛化结果

v2 的权重（0.55/0.25/0.10/0.10）与标签生成公式相同，但标签生成多了一道“正例至少命中一个 required capability”的门槛，而 v2 评分没有这道门槛。因此 v2 的 top6 与标签 47/60 一致、NDCG@10=0.992774，不是构造性的 1.0；它仍然只是同一批合成标签上的排序一致度，不代表在独立数据或线上更好。v1 的 0.970951 也只表示另一组权重与同一批标签的一致度。完整说明见 docs/EVALUATION-LIMITS.md。

## 当前冻结结果

| 指标 | v1 | v2 |
| --- | ---: | ---: |
| 需求条数 | 60 | 60 |
| 覆盖需求类型数 | 8 | 8 |
| Hit@5 | 1.0000 | 1.0000 |
| NDCG@10 | 0.970951 | 0.992774 |
| 硬过滤违规数 | 0 | 0 |
| 理由可追溯率 | 1.0000 | 1.0000 |
| 前 5 名 HHI | 0.050689 | 0.058578 |
| 前 5 名最高公司占比 | 0.080000 | 0.103333 |

对比结论：以 v1 为左、v2 为右，NDCG@10 变化为 -0.021823（即 v2 高 2.18 个百分点），没有超过 2 个百分点的退步阈值；两个版本硬过滤违规均为 0；对比退出码为 0。详见 artifacts/report-compare.md。

这些数字是合成夹具上的回归结果，不是线上效果估计。标签是规则生成的合成标签，不是人工逐条标注；scripts/manual_review.py 已生成 60 条需求、600 个标签的复核包，0 个标签缺陷；复核人签字前仍是 pending-human-signoff。若客户把“人工标注”作为硬性验收项，需要复核人签字或客户书面接受合成标签。详见 docs/EVALUATION-LIMITS.md 和 docs/MANUAL-REVIEW.md。

## 退出码

| 退出码 | 含义 |
| --- | ---: |
| 0 | 成功；正式 evaluate 违规为 0；compare 无违规且无超过 2 个百分点的 NDCG@10 退步 |
| 1 | 数据/权重/参数错误 |
| 2 | 正式评测或对比评测出现硬过滤违规 |
| 3 | compare 中右侧版本 NDCG@10 退步超过 0.02 |

--no-hard-filter 只用于验证“违规时退出码非 0”这一验收点，生成的是诊断报告，不是对外推荐结果。

## 验收

artifacts/ACCEPTANCE.md 记录 AC1–AC6 的命令、退出码和结果。当前全量测试 55 passed；验收运行 all_passed True。

- AC1：60 条需求，8 种类型；统计命令 python -m match_eval stats。
- AC2：每个指标一个专用测试文件：tests/test_metric_hit_at_5.py、test_metric_ndcg_at_10.py、test_metric_filter_violations.py、test_metric_rationale_trace.py、test_metric_top5_concentration.py；tests/test_metrics.py 保留综合覆盖。
- AC3：--no-hard-filter 诊断运行产生 206 个违规，进程退出码 2。
- AC4：artifacts/report-compare.md 为 v1/v2 对比示例报告。
- AC5：正式评测硬过滤违规 0，理由可追溯率 1.0。
- AC6：全量测试 55 passed（含 5 个指标专用文件 14 passed）。

两轮从零演练日志：artifacts/ac-round1.log、ac-round2.log。变异演练日志：artifacts/reverse-drill.log。人工复核包：artifacts/manual-review.json、artifacts/manual-review.csv、docs/MANUAL-REVIEW.md。

## 限制

- 合成数据规模有限，标注由固定规则生成，不代表真实业务分布；复核包已生成但尚无人类复核人签字。
- v2 权重与标注公式相同、标签还多了 capability 门槛，NDCG@10=0.992774 只是同一批合成标签上的一致度，不能当作泛化或线上效果证据。
- 没有真实企业库、真实联系人、金额和线上反馈；不接入生产 AI 队列。
- 只支持单机离线 JSON 数据；没有数据库、网络和外部服务依赖。
- 集中度是观察指标，当前数据下 v2 的 HHI 略高于 v1，不代表线上一定更集中。
- 正式提交前需要用户明确批准；仓库内不会自动提交。