# 验收复核指南（#2050，交付 v3）

本文件给评审者一条最短核对路径：每条验收标准对应一个命令、一个期望结果和一个可检查的证据文件。所有命令在 repo 根目录执行，Python 3.11+，无网络依赖。

> 本机若没有裸 `python`，把命令里的 `python` 换成实际解释器路径即可；仓库内不写死本机绝对路径。

## 一页结论

| 项 | 当前值 |
| --- | ---: |
| 企业 / 供给 / 需求 | 40 / 30（27 active）/ 60 |
| 需求类型数 | 8 |
| 正例 / 负例 | 190 / 240 |
| v1 NDCG@10 | 0.890098 |
| v2 NDCG@10 | 0.965123 |
| v2−v1 | +0.075025 |
| compare 退步（左−右） | -0.075025，阈值 0.02，verdict=pass |
| 正式评测违规 | 0 / 0 |
| 理由可追溯率 | 1.0 / 1.0 |
| 诊断（关闭硬过滤）违规 | 222，exit 2 |
| 全量测试 | 68 passed |
| 标签复核 | 0 缺陷、0 重放不一致、pending-human-signoff |
| v2 top6 与标签集合 | 精确 2/4（仅 6 正例需求），覆盖全部标签 51/60，交集 180/190 |

## AC1：需求条数 ≥ 50，且统计脚本输出类型数

```bash
python -m match_eval stats
```

期望：退出码 0；输出包含 `"demands": 60`、`"demand_type_count": 8`，以及 companies 40、supplies 30、active_supplies 27、positive_labels 190、negative_labels 240。

证据：`artifacts/ACCEPTANCE.md` 的 AC1 行；`data/demands.json` 应有 60 条记录。

## AC2：每个指标函数都有专用单元测试

```bash
python -m pytest tests/test_metric_hit_at_5.py tests/test_metric_ndcg_at_10.py tests/test_metric_filter_violations.py tests/test_metric_rationale_trace.py tests/test_metric_top5_concentration.py
```

期望：退出码 0；`14 passed`。

五个文件分别覆盖 Hit@5、NDCG@10、硬过滤违规、理由可追溯率、前 5 名集中度。测试使用真实函数和显式期望值，不是“函数存在”式断言。

## AC3：违规 > 0 时退出码非 0

```bash
python -m match_eval evaluate --weights v2 --no-hard-filter --report artifacts/diagnostic-no-filter.md
```

期望：退出码 **2**；输出 `"hard_filter_violations": 222`、`"ndcg_at_10": 0.808071`。

说明：`--no-hard-filter` 故意关闭硬过滤，用来制造违规并验证退出码；这是诊断运行，不是对外推荐结果，不能引用它的 NDCG 作为成绩。

证据：`artifacts/diagnostic-no-filter.md`，其中复现命令必须包含 `--no-hard-filter` 和真实的 `--report` 路径。

## AC4：两权重版本对比报告

```bash
python -m match_eval compare --weights-a v1 --weights-b v2 --report artifacts/report-compare.md
```

期望：退出码 0；输出 `"ndcg_regression": -0.075025`、`"verdict": "pass"`。

证据：`artifacts/report-compare.md`，含 v1/v2 并排指标、差值（右−左）、退步（左−右）、阈值说明和可复现命令。

## AC5：正式评测零违规、理由可追溯率 1.0

```bash
python -m match_eval evaluate --weights v1 --report artifacts/report-v1.md
python -m match_eval evaluate --weights v2 --report artifacts/report-v2.md
```

期望：两条命令均退出码 0；各自 `"hard_filter_violations": 0`、`"rationale_traceability": 1.0`。

证据：`artifacts/report-v1.md`、`artifacts/report-v2.md` 的指标表；`artifacts/ACCEPTANCE.md` AC5 的命令区包含两条命令。

## AC6：全量测试

```bash
python -m pytest tests
```

期望：退出码 0；`68 passed`。

覆盖：数据规模与正负例约束、六槽位重放、AST import 独立性、golden hash、权重重跑不变性、支配反例、理由语义回算、报告复现命令、CLI 退出码。

## 全量验收

```bash
python scripts/run_acceptance.py
```

期望：输出 `all_passed True`，退出码 0；重写 `artifacts/ACCEPTANCE.md`（AC1–AC6、命令、退出码、数据 sha256）。

## 标签与独立性（本轮重点）

```bash
python scripts/build_annotations.py
python scripts/generate_dataset.py
python scripts/manual_review.py
python scripts/label_sensitivity.py
python scripts/weight_grid.py
python -m pytest tests/test_dataset.py tests/test_labeling.py tests/test_label_independence.py
```

核对点：

1. `scripts/build_annotations.py`、`scripts/labeling.py`、`scripts/fixture_spec.py` 不导入 `match_eval`，不读 `weights/`；
2. 六槽位是词典序，没有 0.40/0.20/0.20/0.20 或 0.55/0.25/0.10/0.10 加权和；
3. `data/editorial-signals.json` 的案例数/响应天数不被 `match_eval` 读取；
4. `tests/test_labeling.py` 在临时目录改写 v1/v2 权重后重跑 builder+generator，四个数据文件逐字节不变；
5. `scripts/manual_review.py` 用同一 `labeling` 重放六槽位，覆盖 60 条需求 / 430 个标签，输出 0 缺陷、0 重放不一致、pending-human-signoff；
6. `scripts/label_sensitivity.py` 的随机化基线：与正式标签同一“覆盖 ≥2”底线时，随机标签中位 +0.075438、v2 胜 500/500，实际标签在第 41.0 百分位；覆盖 ≥1 时中位 +0.023730、484/500；去掉底线时中位 -0.000253、v2 仅 247/500。实际 +0.075025 因此不是泛化证据。
7. `scripts/weight_grid.py` 枚举 1771 组四特征权重；网格内最好的权重也只能让 58/60 条需求的 top6 覆盖全部正例。失败的两条是 d052 和 d036：d052 的未标注候选 c006 逐特征支配正例 c022；d036 的 5 个正例被 c003/c006/c013/c021（capability=1）与 c022/c023（region/industry 领先）或 company_id 平局挤出。`tests/test_label_independence.py` 对两条穷举断言；`artifacts/weight-grid.json` 的 `failed_demands` 记录 best_covered/missing/extra。能声称“top6 标签集合不能被任何非负四特征权重完整复现”，但不声称与业务事实正交。

完整口径见 `data/ANNOTATION.md` 与 `docs/LABEL-BASELINE.md`。

## 常见误读

- “2/4”不是全部 60 条都精确一致：只有 4 条需求恰有 6 个正例，精确集合比较只在 6 正例时有意义；其余用“top6 覆盖全部标签 51/60、交集 180/190”衡量。
- “190 个正例都在前 10”与“top6 只覆盖 51/60”不矛盾：NDCG 按位置加权，top6 是集合；190 个正例全量排名中位第 2、最差第 8，但第 7–10 名不计入 top6。v2 在 31 条需求上更好、28 条持平、1 条更差。
- “+0.075025”不是泛化证据：与正式标签同底线时随机标签几乎都会让 v2 略高；去掉底线后 v2 仅 247/500。详见 `docs/EVALUATION-LIMITS.md`。
- “人工标注”尚未完成：复核包是机器可复算的合成标签，等待人类签字；签字前不得称人工标注。
- “0.965123”是 60 条合成需求的回归结果，不是线上效果或模型优劣结论。
- 标签覆盖：113 个完全覆盖 required（52 个 3/3、61 个 2/2）、77 个覆盖 2/3、没有低于底线的项；如果评审要求 3/3 全覆盖，只有 52 条满足，需改数据与标签，不能只改文档。

## 历史文件

`artifacts/history/` 是第 1/2 轮历史存档，数字已过期，不能作为当前结果引用。当前结果以 README、`artifacts/ACCEPTANCE.md` 和本文件为准。
