# 验收对照报告

- 生成时间：2026-11-21T10:50:58Z
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
| AC6 | 全量单元测试通过 | PASS | 68 passed in 1.76s |

## 数据哈希（sha256）

| 文件 | sha256 |
| --- | --- |
| data/companies.json | a508c4942d3311e8e987b1afd70463bdca5962a29431c5785cb7bc79eb954b47 |
| data/supplies.json | c29391996dc5d3692761e451f621ac6886e9c3834aaa84c4071d2c76550738fe |
| data/demands.json | 956da350a2f20501b1e0af3fc4b519da287ab34407ee57c7e9ceceb2b714aa31 |
| data/annotations.json | 4694fac72d7fc9691a0df6e19c341e05a4f2b8d2f795fd01110b94405a35ef88 |
| data/editorial-signals.json | bf8491c6ef1d20e1fe21e0343e98c429c629526718cd5c43e1ec426d7276d032 |

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
