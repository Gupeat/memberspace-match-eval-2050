# 标注说明（合成夹具）

本目录的数据是 ClawHunt #2050 的离线评测夹具。所有企业、供给、需求和标注均为虚构，仅用于验证匹配排序指标与流程；不是线上人工标注样本，不能用来估计线上效果。

## 规模

- 企业：40（c001–c040）
- 供给：30（s001–s030；27 条 active，3 条 paused）
- 需求：60（d001–d060）
- 需求类型：8 种
  - event 8、marketing 8、hiring 8、legal 8、finance 7、it 7、training 7、sourcing 7
- 每条需求标注：6 个应推荐、4 个不应推荐
- 合计：360 个正标注、240 个负标注

## 标注生成规则（冻结前）

先按需求类型确定 required_capabilities，再从企业能力与供给能力计算四个信号：

- capability：需求必需能力中被企业能力覆盖的比例。注意：生成器只使用企业能力，不使用供给能力；评测打分阶段才把 active 供给的能力合并进来，两处口径不同，文档与代码必须分开看；
- industry：企业行业是否命中 preferred_industries；
- region：企业区域是否等于需求区域；
- capacity：企业容量档是否大于等于需求容量档。

annotation_score = 0.55 * capability + 0.25 * industry + 0.10 * region + 0.10 * capacity。

候选必须满足：有 active 供给、不是需求方、accepting=true、不在冲突关系中。按 annotation_score 降序取前 6 个作为 should_recommend；从剩余的合格候选中取前 2 个作为 rejected（已拒绝组合），再从“有 active 供给但 not_accepting 或与需求方冲突”的企业中按 annotation_score 取最多 2 个作为负例，合计 4 个 should_not_recommend。因此数据集整体覆盖 rejected、not_accepting、conflict 三类原因；单条需求不一定同时出现三类（当前 13/60 条需求同时有三类，其余 47 条为 rejected + not_accepting）。

标注写入 demands.json 后冻结。评测运行时不再读取 annotation_score，也不根据评测权重反推标签；权重变化只影响排序结果，不会改变标注。

## 负例原因

| 原因 | 含义 |
| --- | --- |
| rejected | 需求方已拒绝的组合；进入硬过滤 |
| not_accepting | 企业暂不接受对接；进入硬过滤 |
| conflict | 企业与需求方存在双向冲突；进入硬过滤 |

## 复核方式

1. 运行 python -m match_eval stats，核对 40/30/60、8 种类型、360/240 标注。
2. 运行测试 tests/test_dataset.py，核对每条需求 6 正 4 负、负例原因覆盖、冲突对称、无手机号/邮箱等 PII 模式。
3. 运行 python -m match_eval evaluate --weights v1 或 v2，核对正式评测违规为 0、理由可追溯率为 1.0。
4. 运行 scripts/run_acceptance.py，生成 artifacts/ACCEPTANCE.md。

## 限制

- 规则生成的标注是“显式、冻结、可复核”的合成标注，不是人工逐条审核的线上样本。
- 规模 60 条需求适合回归测试，不足以覆盖真实业务的长尾分布。
- 若接入真实数据，应保留 should_recommend、should_not_recommend、rejected_company_ids、annotation_note 字段，替换 JSON 后重跑同一套指标与测试。