# 评测边界与标签口径（#2050）

本文件把交付中最容易被误读的两点写清楚，避免把夹具结果当成线上效果或人工标注。

## 1. 标签是规则生成的合成标签，不是人工逐条标注

- `data/ANNOTATION.md` 已写明：60 条需求、360 正例、240 负例，均由固定规则生成后冻结。
- `scripts/manual_review.py` 已逐条重放规则，生成 60 条需求、600 个标签的复核包（`docs/MANUAL-REVIEW.md`、`artifacts/manual-review.json`、`artifacts/manual-review.csv`）：0 个标签缺陷，13 条 v2 top6 与标签不一致仅作为模型观察项。
- 复核包当前状态是 **pending-human-signoff**：没有人类复核人姓名、签字或复核时间。签字前只能称“已完成可复核的合成标注 + 复核包”，不能称“人工标注已完成”。
- 任务原文使用“人工标注”时，若客户把人工标注作为硬性验收项，需要复核人签字或客户书面接受合成标签，不能把本数据称为人工样本。

## 2. v2 的 NDCG@10=0.992774 不是泛化证据

- 标注公式：`0.55 * capability + 0.25 * industry + 0.10 * region + 0.10 * capacity`。
- v2 权重：`0.55 / 0.25 / 0.10 / 0.10`，与标注公式相同；但标签生成多了一道门槛：正例必须至少命中一个 required capability，而 v2 评分没有这道门槛。
- 生成器里的 `supply.capabilities` 是 `company.capabilities[:2]` 的子集，所以评测阶段合并供给能力不会改变分数。
- 结果：v2 的 top6 与标注 47/60 一致，NDCG@10=0.992774；它不是 1.0，但仍然是同一批合成标签上的排序一致度。
- v1 权重为 `0.45 / 0.25 / 0.20 / 0.10`，NDCG@10=0.970951；该数字只能说明“换权重会改变与同一批规则标签的一致度”。
- 本仓库没有独立留出集、人工标注集或线上反馈，因此不能用这两个数字证明 v2 在真实数据上更好。

## 3. 复现与核对

```
python -m match_eval stats
python -m match_eval evaluate --weights v1
python -m match_eval evaluate --weights v2
python -m match_eval compare --weights-a v1 --weights-b v2
python -m pytest tests
python scripts/manual_review.py
```

任何对外报告都应同时引用本文件；只引用单一高分、不说明标签口径与能力门槛，会构成误导。
