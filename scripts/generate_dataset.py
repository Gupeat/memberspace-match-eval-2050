"""Generate the synthetic match-ranking evaluation fixture.

The fixture is deterministic: same script -> same JSON bytes. It contains only
fictional companies, fictional people-free text, and no production data.

The annotations are curated by the fixed relevance rules in this file and then
frozen into demands.json; they are not derived from the evaluator weights at
runtime. Evaluator weights live in weights/*.json and are intentionally separate
from the annotation score.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CAPABILITY_GROUPS = [
    ["event_planning", "venue", "catering", "av"],
    ["marketing", "design", "media", "photography"],
    ["legal", "finance", "hr", "it"],
    ["training", "consulting", "logistics", "translation"],
]
INDUSTRIES = [
    "tech",
    "finance",
    "manufacturing",
    "education",
    "healthcare",
    "culture",
    "retail",
    "energy",
    "logistics",
    "real_estate",
]
REGIONS = ["east", "south", "north", "west", "central"]
CAPACITIES = ["small", "medium", "large"]
CAPACITY_RANK = {value: index for index, value in enumerate(CAPACITIES)}

COMPANY_NAMES = [
    "晨星会务", "云杉品牌", "青石法务", "远帆财务", "拾光影像", "栖梧人力",
    "澜图科技", "禾木培训", "南北物流", "译林翻译", "山海策划", "沐光设计",
    "澄明咨询", "松间餐饮", "海盐传播", "白露公关", "苍梧教育", "星野健康",
    "溪谷文化", "暮山零售", "长风能源", "元野地产", "清越制造", "知微数据",
    "半山活动", "竹影视觉", "安澜保险", "一苇咨询", "南枝旅行", "西窗印刷",
    "东篱安保", "北岸会展", "林间茶事", "云上软件", "石桥广告", "江畔摄影",
    "花间礼仪", "木铎学院", "风铃翻译", "月湖康养",
]

DEMAND_TYPES = {
    "event": ("活动执行", ["event_planning", "venue", "catering"]),
    "marketing": ("品牌营销", ["marketing", "design", "media"]),
    "hiring": ("人才招聘", ["hr", "training", "consulting"]),
    "legal": ("法律合规", ["legal", "finance", "consulting"]),
    "finance": ("财税服务", ["finance", "legal", "it"]),
    "it": ("数字化建设", ["it", "consulting", "translation"]),
    "training": ("企业培训", ["training", "consulting", "hr"]),
    "sourcing": ("资源采购", ["logistics", "translation", "event_planning"]),
}

# Symmetric conflict pairs; an excluded company is a hard-filter case, not a
# training label for the scorer.
CONFLICT_PAIRS = [(0, 10), (3, 21), (7, 33), (12, 28), (18, 36)]
NOT_ACCEPTING = {4, 17, 27}
PAUSED_SUPPLY = {9, 19, 29}

# These nine member companies are also consulting providers.  The extra
# capability keeps every demand type supplied with at least six eligible
# companies that match at least one required capability; without it the legal
# demands have only four or five capability-matched candidates.
CONSULTING_COMPANIES = {1, 2, 5, 10, 13, 18, 21, 25, 26}


def capabilities_for(index: int) -> list[str]:
    primary = index % len(CAPABILITY_GROUPS)
    secondary = (primary + 1) % len(CAPABILITY_GROUPS)
    first = CAPABILITY_GROUPS[primary][index % len(CAPABILITY_GROUPS[primary])]
    second = CAPABILITY_GROUPS[primary][(index + 1) % len(CAPABILITY_GROUPS[primary])]
    third = CAPABILITY_GROUPS[secondary][index % len(CAPABILITY_GROUPS[secondary])]
    return sorted({first, second, third})


def build_companies() -> list[dict]:
    conflicts: dict[int, set[int]] = {index: set() for index in range(40)}
    for left, right in CONFLICT_PAIRS:
        conflicts[left].add(right)
        conflicts[right].add(left)
    companies = []
    for index, name in enumerate(COMPANY_NAMES):
        capabilities = capabilities_for(index)
        if index in CONSULTING_COMPANIES:
            capabilities = sorted(set(capabilities) | {"consulting"})
        companies.append(
            {
                "id": f"c{index + 1:03d}",
                "name": name,
                "summary": f"虚构会员企业，提供{name}相关服务。",
                "capabilities": capabilities,
                "industries": [INDUSTRIES[index % len(INDUSTRIES)]],
                "region": REGIONS[index % len(REGIONS)],
                "capacity": CAPACITIES[index % len(CAPACITIES)],
                "accepting": index not in NOT_ACCEPTING,
                "conflicts_with": [f"c{other + 1:03d}" for other in sorted(conflicts[index])],
            }
        )
    return companies


def build_supplies(companies: list[dict]) -> list[dict]:
    supplies = []
    for index in range(30):
        company = companies[index]
        status = "paused" if index in PAUSED_SUPPLY else "active"
        supplies.append(
            {
                "id": f"s{index + 1:03d}",
                "company_id": company["id"],
                "title": company["name"] + " · 标准服务包",
                "summary": "虚构供给条目，仅用于离线评测。",
                "capabilities": company["capabilities"][:2],
                "industries": company["industries"],
                "region": company["region"],
                "capacity": company["capacity"],
                "status": status,
            }
        )
    return supplies


def annotation_score(demand: dict, company: dict) -> float:
    required = set(demand["required_capabilities"])
    capabilities = set(company["capabilities"])
    capability = len(required & capabilities) / len(required)
    industry = 1.0 if set(demand["preferred_industries"]) & set(company["industries"]) else 0.0
    region = 1.0 if demand["region"] == company["region"] else 0.0
    capacity = 1.0 if CAPACITY_RANK[company["capacity"]] >= CAPACITY_RANK[demand["capacity_need"]] else 0.0
    return 0.55 * capability + 0.25 * industry + 0.10 * region + 0.10 * capacity


def conflict(a: dict, b: dict) -> bool:
    return b["id"] in a["conflicts_with"] or a["id"] in b["conflicts_with"]


def build_demands(companies: list[dict], supplies: list[dict]) -> list[dict]:
    by_id = {company["id"]: company for company in companies}
    active_supply_companies = [
        by_id[supply["company_id"]]
        for supply in supplies
        if supply["status"] == "active"
    ]
    accepting_pool = [company for company in active_supply_companies if company["accepting"]]
    type_names = list(DEMAND_TYPES)
    demands = []
    for index in range(60):
        demand_type = type_names[index % len(type_names)]
        label, required = DEMAND_TYPES[demand_type]
        requester = accepting_pool[index % len(accepting_pool)]
        preferred = [INDUSTRIES[(index * 3 + index % 3) % len(INDUSTRIES)]]
        if index % 4 == 0:
            preferred.append(INDUSTRIES[(index * 3 + 4) % len(INDUSTRIES)])
        demand = {
            "id": f"d{index + 1:03d}",
            "type": demand_type,
            "title": f"{label}需求 {index + 1:02d}",
            "summary": f"虚构会员企业寻找{label}合作方；仅用于离线评测。",
            "requester_company_id": requester["id"],
            "required_capabilities": required,
            "preferred_industries": sorted(set(preferred)),
            "region": REGIONS[index % len(REGIONS)],
            "capacity_need": CAPACITIES[index % len(CAPACITIES)],
            "rejected_company_ids": [],
            "should_recommend": [],
            "should_not_recommend": [],
            "annotation_note": "synthetic fixture; fixed relevance rules; see README",
        }
        candidate_pool = [
            company
            for company in active_supply_companies
            if company["id"] != requester["id"]
            and company["accepting"]
            and not conflict(requester, company)
        ]
        eligible = [
            company
            for company in candidate_pool
            if set(required) & set(company["capabilities"])
        ]
        if len(eligible) < 6:
            raise RuntimeError(
                f"{demand['id']}: only {len(eligible)} eligible capability-matched companies"
            )
        eligible.sort(key=lambda company: (-annotation_score(demand, company), company["id"]))
        should = eligible[:6]
        should_ids = {company["id"] for company in should}
        rejected_pool = [
            company for company in candidate_pool if company["id"] not in should_ids
        ]
        rejected = rejected_pool[:2]
        demand["should_recommend"] = [company["id"] for company in should]
        demand["rejected_company_ids"] = [company["id"] for company in rejected]
        negatives = [
            {"company_id": company["id"], "reason": "rejected"}
            for company in rejected
        ]
        excluded = [
            company
            for company in active_supply_companies
            if company not in should
            and company["id"] not in demand["rejected_company_ids"]
            and (not company["accepting"] or conflict(requester, company))
        ]
        excluded.sort(key=lambda company: (-annotation_score(demand, company), company["id"]))
        for company in excluded[:2]:
            reason = "not_accepting" if not company["accepting"] else "conflict"
            negatives.append({"company_id": company["id"], "reason": reason})
        demand["should_not_recommend"] = negatives
        demands.append(demand)
    return demands


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    companies = build_companies()
    supplies = build_supplies(companies)
    demands = build_demands(companies, supplies)
    files = {
        "companies.json": {"schema_version": 1, "companies": companies},
        "supplies.json": {"schema_version": 1, "supplies": supplies},
        "demands.json": {"schema_version": 1, "demands": demands},
    }
    for filename, payload in files.items():
        path = DATA / filename
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("wrote", path.relative_to(ROOT), "bytes", path.stat().st_size)


if __name__ == "__main__":
    main()
