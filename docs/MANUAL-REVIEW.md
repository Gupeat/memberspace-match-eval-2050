# 机器复核包 · #2050 匹配排序评测集（待人工签字）

> 本文件由 scripts/manual_review.py 生成。它用 scripts/labeling.py 原样重算每个需求的至多六个正例槽位与四个负例，并逐条比对到已冻结的 data/annotations.json；当前状态为**待人类复核人签字**，签字前不得称为人工标注。

## 复核范围与方法

- 对象：data/demands.json 中全部 60 条需求、426 个标签。
- 正例：至多六个编辑槽位（capability_lead / case_strength / responsiveness / industry_fit / regional_fit / capacity_fit）按词典序逐个重算；无合格候选的槽位弃权，所以每条需求 1-6 个正例。要求 company_id 与槽位顺序逐条一致。
- 负例：重算 2 个 rejected + ≥1 个 not_accepting；有冲突对象时再取 1 个 conflict，否则取第二个 not_accepting；要求 company_id 与 reason 逐条一致。
- 约束：1-6 正/4 负、正负不交、需求方不在标签中、正例未被硬过滤、至少命中两个 required capability；前十名理由字段完整。
- 独立性：capability_lead 用平均 IDF 稀缺度；case_strength / responsiveness 用 data/editorial-signals.json 的已核实案例与响应天数；二者均不被 match_eval 读取。
- 复核结果：见下表与 artifacts/manual-review.csv / artifacts/manual-review.json。

## 汇总

| 项 | 值 |
| --- | ---: |
| 需求数 | 60 |
| 正例标签 | 186 |
| 负例标签 | 240 |
| 有问题的需求 | 0 |
| 标签失败检查项 | 0 |
| 重放不一致需求 | 0 |
| v2 top6 精确等于标签集（仅正例=6 时有意义） | 1/1 |
| v2 top6 覆盖全部标签 | 54/60 |
| v2 top6 与标签的交集总数 | 180 |

v2 top6 与标签集合不完全一致是排序目标的差异，不是标签缺陷：NDCG@10 按位置加权，top6 是集合；标签由六个不同编辑视角各选一个，因此自然包含非最高分候选。

## 逐条结果

| 需求 | 类型 | 正例 | 负例 | 原因 | 槽位重放 | 负例重放 | v2 top6 | 机器结论 |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| d001 | event | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d002 | marketing | 4 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d003 | hiring | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d004 | legal | 4 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d005 | finance | 5 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d006 | it | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d007 | training | 2 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d008 | sourcing | 1 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d009 | event | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d010 | marketing | 2 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d011 | hiring | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d012 | legal | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d013 | finance | 2 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d014 | it | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d015 | training | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d016 | sourcing | 1 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d017 | event | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d018 | marketing | 2 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d019 | hiring | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d020 | legal | 5 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d021 | finance | 5 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d022 | it | 4 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d023 | training | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d024 | sourcing | 1 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d025 | event | 4 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d026 | marketing | 5 | 4 | not_accepting,rejected | 一致 | 一致 | 缺标签 | PASS |
| d027 | hiring | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d028 | legal | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d029 | finance | 2 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d030 | it | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d031 | training | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d032 | sourcing | 1 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d033 | event | 4 | 4 | not_accepting,rejected | 一致 | 一致 | 缺标签 | PASS |
| d034 | marketing | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d035 | hiring | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d036 | legal | 5 | 4 | not_accepting,rejected | 一致 | 一致 | 缺标签 | PASS |
| d037 | finance | 5 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d038 | it | 4 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d039 | training | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d040 | sourcing | 1 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d041 | event | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d042 | marketing | 2 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d043 | hiring | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d044 | legal | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d045 | finance | 2 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d046 | it | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d047 | training | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d048 | sourcing | 1 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d049 | event | 4 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d050 | marketing | 5 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 缺标签 | PASS |
| d051 | hiring | 2 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d052 | legal | 6 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d053 | finance | 5 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d054 | it | 4 | 4 | not_accepting,rejected | 一致 | 一致 | 缺标签 | PASS |
| d055 | training | 3 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d056 | sourcing | 1 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d057 | event | 4 | 4 | conflict,not_accepting,rejected | 一致 | 一致 | 缺标签 | PASS |
| d058 | marketing | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d059 | hiring | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |
| d060 | legal | 3 | 4 | not_accepting,rejected | 一致 | 一致 | 覆盖 | PASS |

## 复核人签字

- 复核人：________________（待填写）
- 复核时间：________________（待填写）
- 结论：________________

签字前，本仓库只能声明“已完成可复现的合成标注 + 机器复核包”，不能声明“人工标注已完成”。
