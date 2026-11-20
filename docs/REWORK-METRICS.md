# Rework 逐项证据（#2050）

本文件把平台 rework 要求逐条映射到仓库文件、命令与输出。

## 1. 代码仓库（blocker）

- 仓库：https://github.com/Gupeat/memberspace-match-eval-2050 （public）
- 内容：match_eval 包、scripts/、tests/、data/（companies 40、supplies 30、demands 60）、weights/v1.json、weights/v2.json、artifacts/ 报告与验收日志。
- README「快速开始」给出统计、评测、对比、测试、验收命令。

## 2. 评测集规模与需求类型（major）

- 数据：data/companies.json（40）、data/supplies.json（30，27 active）、data/demands.json（60）。
- 标注规则：data/ANNOTATION.md。
- 统计命令：python -m match_eval stats
- 实际输出：{"companies": 40, "supplies": 30, "active_supplies": 27, "demands": 60, "demand_type_count": 8}
- 覆盖类型：event、finance、hiring、it、legal、marketing、sourcing、training（每种 7–8 条）。

## 3. 每个指标的专用单元测试（major）

| 指标 | 专用测试文件 |
| --- | --- |
| Hit@5 | tests/test_metric_hit_at_5.py |
| NDCG@10 | tests/test_metric_ndcg_at_10.py |
| 硬过滤违规数 | tests/test_metric_filter_violations.py |
| 理由可追溯率 | tests/test_metric_rationale_trace.py |
| 前 5 名集中度 | tests/test_metric_top5_concentration.py |

命令：python -m pytest tests/test_metric_hit_at_5.py tests/test_metric_ndcg_at_10.py tests/test_metric_filter_violations.py tests/test_metric_rationale_trace.py tests/test_metric_top5_concentration.py
输出：14 passed。全量：python -m pytest tests → 55 passed。tests/test_metrics.py 保留综合覆盖。

## 4. 违规/退步时退出码非 0（major）

- 违规：python -m match_eval evaluate --weights v2 --no-hard-filter --report artifacts/diagnostic-no-filter.md → 硬过滤违规数 206，退出码 2。
- 退步：tests/test_cli.py::test_cli_compare_regression_exit_nonzero 使用只按 region 打分的坏权重，断言 NDCG@10 退步超过 2 个百分点时退出码 3。
- 正常对比：python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md → 退出码 0。

## 5. 两个权重版本对比报告（major）

- 文件：artifacts/report-compare.md（已提交到仓库，并在 PR 正文中引用）。
- 结果：Hit@5 1.0000/1.0000；NDCG@10 0.9710/0.9928（右-左 +0.0218）；硬过滤违规 0/0；理由可追溯率 1.0/1.0；退步 -0.0218 < 0.02，判定通过。
- 标签生成增加了“正例至少命中一个 required capability”的门槛，v2 评分没有该门槛，因此 v2 的 top6 与标签只有 47/60 一致，NDCG@10=0.992774，不再是构造性的 1.0。
- 命令：python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md

## 复现

    python -m match_eval stats
    python -m pytest tests/test_metric_hit_at_5.py tests/test_metric_ndcg_at_10.py tests/test_metric_filter_violations.py tests/test_metric_rationale_trace.py tests/test_metric_top5_concentration.py
    python -m pytest tests
    python -m match_eval evaluate --weights v2 --no-hard-filter --report artifacts/diagnostic-no-filter.md
    python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
    python scripts/run_acceptance.py
    python scripts/manual_review.py

人工复核：scripts/manual_review.py 逐条重放规则并生成 60 条需求、600 个标签的复核包（docs/MANUAL-REVIEW.md），0 个标签缺陷，当前 pending-human-signoff；签字前不得称为人工标注。

所有数据均为合成数据，不含真实企业、联系人、金额或 PII。
