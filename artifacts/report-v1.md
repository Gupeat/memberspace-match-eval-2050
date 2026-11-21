# 匹配排序离线评测报告（v1）

本报告由 match-eval 从冻结的合成数据生成；数据与标注不含真实企业、真实联系人或生产数据。

## 数据规模

| 项目 | 数量 |
| --- | ---: |
| 虚构企业 | 40 |
| 供给条目 | 30 |
| 其中活跃供给 | 27 |
| 需求条目 | 60 |
| 应推荐标注数 | 190 |
| 不应推荐标注数 | 240 |

## 权重版本

| 特征 | 权重 |
| --- | ---: |
| capability | 0.45 |
| industry | 0.25 |
| region | 0.20 |
| capacity | 0.10 |

权重文件：v1；描述：基础版：能力 45%，区域 20%，强调本地供给，容量只占 10%。

## 指标

| 指标 | 值 | 目标/说明 |
| --- | ---: | --- |
| 需求条数 | 60 | 至少 50 |
| 覆盖需求类型数 | 8 | 统计脚本输出 |
| Hit@5 | 1.000000 | 有至少一个应推荐进入前 5 的需求占比 |
| NDCG@10 | 0.890098 | 二值相关性，应推荐=1 |
| 硬过滤违规数 | 0 | 目标 0；大于 0 时退出码非 0 |
| 理由可追溯率 | 1.000000 | 目标 1.000000 |
| 前 5 名集中度 HHI | 0.051467 | 所有需求前 5 名公司分布 |
| 前 5 名最高公司占比 | 0.083333 | 观察值，不设硬门槛 |
| 前 5 名覆盖公司数 | 23 | 观察值 |

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
| not_accepting | 240 |
| rejected | 120 |
| self | 60 |

## 排序样例

以下展示前 3 个需求的前 5 名；应推荐标注以 * 标记。

### d001 · 活动执行需求 01

类型：event；需求方：c001；可推荐标注：c025, c014, c032

| 排名 | 公司 | 分数 | 理由摘要 | 标注 |
| ---: | --- | ---: | --- | --- |
| 1 | c032 | 1.0000 | capabilities=catering,event_planning,venue; industry=yes; region=yes; capacity=yes; supplies=s030 | 应推荐 * |
| 2 | c025 | 0.6500 | capabilities=event_planning,venue; industry=yes; region=no; capacity=yes; supplies=s025 | 应推荐 * |
| 3 | c014 | 0.5500 | capabilities=catering,event_planning,venue; industry=no; region=no; capacity=yes; supplies=s014 | 应推荐 * |
| 4 | c019 | 0.5000 | capabilities=event_planning; industry=yes; region=no; capacity=yes; supplies=s019 | 未标注 |
| 5 | c002 | 0.4500 | capabilities=none; industry=yes; region=yes; capacity=no; supplies=s002 | 未标注 |

### d002 · 品牌营销需求 02

类型：marketing；需求方：c002；可推荐标注：c020, c019, c012, c015

| 排名 | 公司 | 分数 | 理由摘要 | 标注 |
| ---: | --- | ---: | --- | --- |
| 1 | c019 | 0.7500 | capabilities=design,media; industry=yes; region=yes; capacity=no; supplies=s019 | 应推荐 * |
| 2 | c015 | 0.5500 | capabilities=marketing,media; industry=yes; region=no; capacity=no; supplies=s015 | 应推荐 * |
| 3 | c010 | 0.4000 | capabilities=media; industry=yes; region=no; capacity=no; supplies=s010 | 未标注 |
| 4 | c011 | 0.4000 | capabilities=marketing; industry=yes; region=no; capacity=no; supplies=s011 | 未标注 |
| 5 | c012 | 0.3000 | capabilities=design,media; industry=no; region=no; capacity=no; supplies=s012 | 应推荐 * |

### d003 · 人才招聘需求 03

类型：hiring；需求方：c003；可推荐标注：c008, c017, c006

| 排名 | 公司 | 分数 | 理由摘要 | 标注 |
| ---: | --- | ---: | --- | --- |
| 1 | c006 | 0.6000 | capabilities=consulting,hr; industry=no; region=yes; capacity=yes; supplies=s006 | 应推荐 * |
| 2 | c008 | 0.5500 | capabilities=consulting,hr,training; industry=no; region=no; capacity=yes; supplies=s008 | 应推荐 * |
| 3 | c017 | 0.5500 | capabilities=consulting,hr,training; industry=no; region=no; capacity=yes; supplies=s017 | 应推荐 * |
| 4 | c013 | 0.5000 | capabilities=consulting; industry=yes; region=no; capacity=yes; supplies=s013 | 未标注 |
| 5 | c011 | 0.4500 | capabilities=consulting; industry=no; region=yes; capacity=yes; supplies=s011 | 未标注 |

## 结论

硬过滤违规目标为 0；理由可追溯率目标为 1.0000；本报告只用于离线评测，不写入生产 AI 队列、不触发对外联系、不涉及金额。

复现命令：python -m match_eval evaluate --weights v1 --report artifacts/report-v1.md
