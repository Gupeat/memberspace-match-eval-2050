# 匹配排序离线评测报告（v2）

本报告由 match-eval 从冻结的合成数据生成；数据与标注不含真实企业、真实联系人或生产数据。

## 数据规模

| 项目 | 数量 |
| --- | ---: |
| 虚构企业 | 40 |
| 供给条目 | 30 |
| 其中活跃供给 | 27 |
| 需求条目 | 60 |
| 应推荐标注数 | 360 |
| 不应推荐标注数 | 240 |

## 权重版本

| 特征 | 权重 |
| --- | ---: |
| capability | 0.55 |
| industry | 0.25 |
| region | 0.10 |
| capacity | 0.10 |

权重文件：v2；描述：能力增强版：能力 55%，区域 10%，降低容量权重，优先覆盖需求能力。

## 指标

| 指标 | 值 | 目标/说明 |
| --- | ---: | --- |
| 需求条数 | 60 | 至少 50 |
| 覆盖需求类型数 | 8 | 统计脚本输出 |
| Hit@5 | 1.0000 | 有至少一个应推荐进入前 5 的需求占比 |
| NDCG@10 | 1.0000 | 二值相关性，应推荐=1 |
| 硬过滤违规数 | 0 | 目标 0；大于 0 时退出码非 0 |
| 理由可追溯率 | 1.0000 | 目标 1.0000 |
| 前 5 名集中度 HHI | 0.0480 | 所有需求前 5 名公司分布 |
| 前 5 名最高公司占比 | 0.0833 | 观察值，不设硬门槛 |
| 前 5 名覆盖公司数 | 24 | 观察值 |

## 需求类型覆盖

| 类型 | 需求数 |
| --- | ---: |
| event | 8 |
| finance | 7 |
| hiring | 8 |
| it | 7 |
| legal | 8 |
| marketing | 8 |
| sourcing | 7 |
| training | 7 |

## 硬过滤排除统计

统计每个需求被排除的候选企业次数，按原因汇总：

| 原因 | 次数 |
| --- | ---: |
| conflict | 21 |
| no_active_supply | 775 |
| not_accepting | 180 |
| rejected | 120 |
| self | 60 |

## 排序样例

以下展示前 3 个需求的前 5 名；应推荐标注以 * 标记。

### d001 · 活动执行需求 01

类型：event；需求方：c001；可推荐标注：c021, c025, c009, c013, c017, c029

| 排名 | 公司 | 分数 | 理由摘要 | 标注 |
| ---: | --- | ---: | --- | --- |
| 1 | c021 | 0.8167 | capabilities=event_planning,venue; industry=yes; region=yes; capacity=yes; supplies=s021 | 应推荐 * |
| 2 | c025 | 0.7167 | capabilities=event_planning,venue; industry=yes; region=no; capacity=yes; supplies=s025 | 应推荐 * |
| 3 | c009 | 0.4667 | capabilities=event_planning,venue; industry=no; region=no; capacity=yes; supplies=s009 | 应推荐 * |
| 4 | c013 | 0.4667 | capabilities=event_planning,venue; industry=no; region=no; capacity=yes; supplies=s013 | 应推荐 * |
| 5 | c017 | 0.4667 | capabilities=event_planning,venue; industry=no; region=no; capacity=yes; supplies=s017 | 应推荐 * |

### d002 · 品牌营销需求 02

类型：marketing；需求方：c002；可推荐标注：c006, c014, c022, c026, c025, c017

| 排名 | 公司 | 分数 | 理由摘要 | 标注 |
| ---: | --- | ---: | --- | --- |
| 1 | c006 | 0.4667 | capabilities=design,media; industry=no; region=no; capacity=yes; supplies=s006 | 应推荐 * |
| 2 | c014 | 0.4667 | capabilities=design,media; industry=no; region=no; capacity=yes; supplies=s014 | 应推荐 * |
| 3 | c022 | 0.4667 | capabilities=design,media; industry=no; region=yes; capacity=no; supplies=s022 | 应推荐 * |
| 4 | c026 | 0.4667 | capabilities=design,media; industry=no; region=no; capacity=yes; supplies=s026 | 应推荐 * |
| 5 | c025 | 0.4333 | capabilities=marketing; industry=yes; region=no; capacity=no; supplies=s025 | 应推荐 * |

### d003 · 人才招聘需求 03

类型：hiring；需求方：c003；可推荐标注：c019, c009, c008, c012, c015, c023

| 排名 | 公司 | 分数 | 理由摘要 | 标注 |
| ---: | --- | ---: | --- | --- |
| 1 | c019 | 0.4333 | capabilities=hr; industry=yes; region=no; capacity=no; supplies=s019 | 应推荐 * |
| 2 | c009 | 0.3500 | capabilities=none; industry=yes; region=no; capacity=yes; supplies=s009 | 应推荐 * |
| 3 | c008 | 0.2833 | capabilities=training; industry=no; region=yes; capacity=no; supplies=s008 | 应推荐 * |
| 4 | c012 | 0.2833 | capabilities=training; industry=no; region=no; capacity=yes; supplies=s012 | 应推荐 * |
| 5 | c015 | 0.2833 | capabilities=hr; industry=no; region=no; capacity=yes; supplies=s015 | 应推荐 * |

## 结论

硬过滤违规目标为 0；理由可追溯率目标为 1.0000；本报告只用于离线评测，不写入生产 AI 队列、不触发对外联系、不涉及金额。

复现命令：python -m match_eval evaluate --weights v2 --report artifacts/report-v2.md
