# 验收对照报告

- 生成时间：2026-11-21T07:27:57Z
- 结论：全部通过
- 运行目录：.

## 对照表

| 编号 | 验收项 | 结果 | 证据 |
| --- | --- | --- | --- |
| AC1 | 评测集需求条数 >= 50，统计脚本输出覆盖需求类型数 | PASS | demands=60; demand_type_count=8 |
| AC2 | 每个指标函数都有单元测试 | PASS | 14 passed in 0.08s |
| AC3 | 硬过滤违规数 > 0 时退出码非 0 | PASS | exit=2; hard_filter_violations=222 |
| AC4 | 两个权重版本的对比示例报告 | PASS | report=artifacts/report-compare.md; verdict=pass |
| AC5 | 正式评测硬过滤违规为 0，理由可追溯率为 1.0 | PASS | v1 violations=0, trace=1.0; v2 violations=0, trace=1.0 |
| AC6 | 全量单元测试通过 | PASS | 66 passed in 1.30s |

## 数据哈希（sha256）

| 文件 | sha256 |
| --- | --- |
| data/companies.json | fafade43c7142f2ed1a1e91d4565f2e75a5afb390540ed5dea8d0c6e18c2a07d |
| data/supplies.json | 1e51c471d11058cb7c34a1da263d7cb1499675ea503bf23af3f71b621c87ec31 |
| data/demands.json | 15637e438652ea574bef71db66429f311a4f400345c46b722e31b92fd2c26d6f |
| data/annotations.json | c42a743699c38cf77942279c52ecefb506b39c8ecec6a8603bdbe1700ed8d1ce |
| data/editorial-signals.json | e77329acc3e157e625e87876eaadc3aa23cadd079f71bb7e6a887565b0960dd1 |

## 命令与退出码

### AC1

- 命令：python -m match_eval stats
- 期望退出码：0；实际退出码：0
- 结果：PASS

### AC2

- 命令：python -m pytest tests/test_metric_hit_at_5.py tests/test_metric_ndcg_at_10.py tests/test_metric_filter_violations.py tests/test_metric_rationale_trace.py tests/test_metric_top5_concentration.py
- 期望退出码：0；实际退出码：0
- 结果：PASS

### AC3

- 命令：python -m match_eval evaluate --weights v2 --no-hard-filter --report artifacts/diagnostic-no-filter.md
- 期望退出码：2；实际退出码：2
- 结果：PASS

### AC4

- 命令：python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
- 期望退出码：0；实际退出码：0
- 结果：PASS

### AC5

- 命令：python -m match_eval evaluate --weights v1 --report artifacts/report-v1.md
- 期望退出码：0；实际退出码：0
- 命令：python -m match_eval evaluate --weights v2 --report artifacts/report-v2.md
- 期望退出码：0；实际退出码：0
- 结果：PASS

### AC6

- 命令：python -m pytest tests
- 期望退出码：0；实际退出码：0
- 结果：PASS

## 说明

- AC3 的 no-filter 运行只用于证明违规时退出码非 0；它不是对外推荐结果。
- 所有数据均为合成数据，不含真实联系人、金额或生产队列。
