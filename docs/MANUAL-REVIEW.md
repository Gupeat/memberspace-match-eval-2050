# 人工复核记录 · #2050 匹配排序评测集

> 本文件由 scripts/manual_review.py 生成。它逐条核对 60 条需求、360 个正例、240 个负例；当前状态为**待人类复核人签字**，签字前不得称为人工标注。

## 复核范围与方法

- 对象：data/demands.json 中全部 60 条需求、600 个标签。
- 正例检查：6 个/条；不是需求方；不在排除集合（self / not_accepting / rejected / conflict / no_active_supply）；至少命中一个 required capability。
- 负例检查：4 个/条；原因必须是 rejected / not_accepting / conflict 之一，且对应条件确实成立、硬过滤确实会排除。
- 一致性检查：正负例不重叠；前十名理由字段完整。v2 top6 与标签是否一致只作为观察项：标签强制至少命中一个 required capability，而 v2 评分没有该门槛，因此不一致是模型与标签规则的差异，不是标签缺陷。
- 复核结果：见下表与 artifacts/manual-review.csv / artifacts/manual-review.json。

## 汇总

| 项 | 值 |
| --- | ---: |
| 需求数 | 60 |
| 正例标签 | 360 |
| 负例标签 | 240 |
| 有问题的需求 | 0 |
| 标签失败检查项 | 0 |
| v2 top6 与标签一致（观察项） | 47/60 |

## 逐条结果

| 需求 | 类型 | 正例 | 负例 | 原因 | v2 top6 | 结果 |
| --- | --- | ---: | ---: | --- | --- | --- |
| d001 | event | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d002 | marketing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d003 | hiring | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d004 | legal | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d005 | finance | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d006 | it | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d007 | training | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d008 | sourcing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d009 | event | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d010 | marketing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d011 | hiring | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d012 | legal | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d013 | finance | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d014 | it | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d015 | training | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d016 | sourcing | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d017 | event | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d018 | marketing | 6 | 4 | conflict,not_accepting,rejected | 不一致 | PASS |
| d019 | hiring | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d020 | legal | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d021 | finance | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d022 | it | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d023 | training | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d024 | sourcing | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d025 | event | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d026 | marketing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d027 | hiring | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d028 | legal | 6 | 4 | conflict,not_accepting,rejected | 不一致 | PASS |
| d029 | finance | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d030 | it | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d031 | training | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d032 | sourcing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d033 | event | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d034 | marketing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d035 | hiring | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d036 | legal | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d037 | finance | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d038 | it | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d039 | training | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d040 | sourcing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d041 | event | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d042 | marketing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d043 | hiring | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d044 | legal | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d045 | finance | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d046 | it | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d047 | training | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d048 | sourcing | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d049 | event | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d050 | marketing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d051 | hiring | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d052 | legal | 6 | 4 | conflict,not_accepting,rejected | 不一致 | PASS |
| d053 | finance | 6 | 4 | not_accepting,rejected | 不一致 | PASS |
| d054 | it | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d055 | training | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d056 | sourcing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d057 | event | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d058 | marketing | 6 | 4 | not_accepting,rejected | 一致 | PASS |
| d059 | hiring | 6 | 4 | conflict,not_accepting,rejected | 一致 | PASS |
| d060 | legal | 6 | 4 | not_accepting,rejected | 一致 | PASS |

## 复核人签字

- 复核人：________________（待填写）
- 复核时间：________________（待填写）
- 结论：________________

签字前，本仓库只能声明“已完成可复核的合成标注 + 复核包”，不能声明“人工标注已完成”。
