"""Hand-authored fixture specification for the #2050 match-ranking dataset.

Everything here is fictional and deterministic.  The specification is the single
source of truth for companies, supplies and demand metadata; labels are produced
separately by scripts/build_annotations.py from scripts/labeling.py plus
data/editorial-signals.json.

Keeping the fixture in code (instead of generating capabilities by cycling an
index) lets every company's capability card match its name and lets every
demand type carry required capabilities that actually exist in the data.
"""

from __future__ import annotations

CAPABILITIES = [
    "event_planning",
    "venue",
    "catering",
    "av",
    "marketing",
    "design",
    "media",
    "photography",
    "hr",
    "training",
    "consulting",
    "legal",
    "finance",
    "it",
    "translation",
    "logistics",
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

CAPABILITY_LABELS = {
    "event_planning": "活动策划",
    "venue": "场地运营",
    "catering": "餐饮服务",
    "av": "视听技术",
    "marketing": "品牌营销",
    "design": "视觉设计",
    "media": "媒体传播",
    "photography": "摄影记录",
    "hr": "人才招聘",
    "training": "企业培训",
    "consulting": "管理咨询",
    "legal": "法律服务",
    "finance": "财务顾问",
    "it": "软件与数据",
    "translation": "语言翻译",
    "logistics": "会务物流",
}

INDUSTRY_LABELS = {
    "tech": "科技",
    "finance": "金融",
    "manufacturing": "制造",
    "education": "教育",
    "healthcare": "医疗健康",
    "culture": "文创",
    "retail": "零售",
    "energy": "能源",
    "logistics": "物流",
    "real_estate": "地产",
}

REGION_LABELS = {
    "east": "华东",
    "south": "华南",
    "north": "华北",
    "west": "西部",
    "central": "华中",
}

CAPACITY_LABELS = {"small": "小型", "medium": "中型", "large": "大型"}

# (id, name, capabilities, industries, region, capacity, accepting)
COMPANY_ROWS = [
    ("c001", "晨星会务", ["event_planning", "venue", "catering"], ["culture"], "east", "medium", True),
    ("c002", "云杉品牌", ["marketing", "design", "media"], ["retail"], "south", "small", True),
    ("c003", "青石法务", ["legal", "finance", "consulting"], ["finance"], "north", "large", True),
    ("c004", "远帆财务", ["finance", "legal", "it"], ["finance"], "west", "medium", True),
    ("c005", "拾光影像", ["photography", "media", "design"], ["culture"], "central", "small", False),
    ("c006", "栖梧咨询", ["legal", "finance", "consulting", "hr"], ["education"], "east", "large", True),
    ("c007", "澜图科技", ["it", "consulting", "design"], ["tech"], "south", "large", True),
    ("c008", "禾木培训", ["training", "consulting", "hr"], ["education"], "north", "small", True),
    ("c009", "南北物流", ["logistics", "translation", "event_planning"], ["logistics"], "west", "medium", True),
    ("c010", "译林翻译", ["translation", "media", "consulting"], ["culture"], "central", "small", True),
    ("c011", "山海策划", ["event_planning", "consulting", "marketing"], ["culture"], "east", "medium", True),
    ("c012", "沐光设计", ["design", "media", "photography"], ["retail"], "south", "small", True),
    ("c013", "澄明咨询", ["consulting", "finance", "legal"], ["finance"], "north", "large", True),
    ("c014", "松间餐饮", ["catering", "venue", "event_planning"], ["healthcare"], "west", "medium", True),
    ("c015", "海盐传播", ["media", "marketing", "event_planning"], ["culture"], "central", "small", True),
    ("c016", "白露公关", ["marketing", "event_planning", "media"], ["retail"], "east", "medium", False),
    ("c017", "苍梧教育", ["training", "consulting", "hr"], ["education"], "south", "large", True),
    ("c018", "星野健康", ["event_planning", "catering", "venue"], ["healthcare"], "north", "small", True),
    ("c019", "溪谷文化", ["design", "event_planning", "media"], ["culture"], "west", "medium", True),
    ("c020", "暮山零售", ["marketing", "logistics", "design"], ["retail"], "central", "small", True),
    ("c021", "长风能源", ["consulting", "finance", "legal"], ["energy"], "east", "large", True),
    ("c022", "元野地产", ["design", "finance", "consulting"], ["real_estate"], "south", "medium", True),
    ("c023", "清越制造", ["logistics", "it", "consulting"], ["manufacturing"], "north", "large", True),
    ("c024", "知微数据", ["it", "consulting", "finance"], ["tech"], "west", "small", True),
    ("c025", "半山活动", ["event_planning", "venue", "av"], ["culture"], "central", "medium", True),
    ("c026", "竹影视觉", ["photography", "design", "media"], ["culture"], "east", "small", False),
    ("c027", "安澜保险", ["finance", "legal", "consulting"], ["finance"], "south", "large", False),
    ("c028", "一苇咨询", ["consulting", "training", "hr"], ["finance"], "north", "medium", True),
    ("c029", "南枝旅行", ["event_planning", "translation", "logistics"], ["logistics"], "west", "small", True),
    ("c030", "西窗印刷", ["media", "design", "marketing"], ["manufacturing"], "central", "medium", True),
    ("c031", "东篱安保", ["event_planning", "logistics", "consulting"], ["real_estate"], "east", "medium", True),
    ("c032", "北岸会展", ["event_planning", "venue", "catering"], ["retail"], "south", "large", True),
    ("c033", "林间茶事", ["catering", "venue", "event_planning"], ["healthcare"], "north", "small", True),
    ("c034", "云上软件", ["it", "design", "consulting"], ["tech"], "west", "large", True),
    ("c035", "石桥广告", ["marketing", "media", "design"], ["manufacturing"], "central", "small", True),
    ("c036", "江畔摄影", ["photography", "media", "design"], ["culture"], "east", "small", True),
    ("c037", "花间礼仪", ["event_planning", "catering", "venue"], ["real_estate"], "south", "medium", True),
    ("c038", "木铎学院", ["training", "consulting", "hr"], ["education"], "north", "large", True),
    ("c039", "风铃翻译", ["translation", "media", "consulting"], ["culture"], "west", "small", True),
    ("c040", "月湖康养", ["catering", "event_planning", "venue"], ["healthcare"], "central", "medium", True),
]

CONFLICT_PAIRS = [
    ("c001", "c011"),
    ("c004", "c022"),
    ("c008", "c034"),
    ("c013", "c029"),
    ("c019", "c037"),
]

# Thirty supply entries cover c001-c029 plus c032; c030 has no supply.  Three
# supplies are paused and three companies with an active supply are not accepting.
SUPPLY_COMPANY_IDS = [f"c{index:03d}" for index in range(1, 30)] + ["c032"]
PAUSED_SUPPLY_COMPANY_IDS = {"c009", "c018", "c028"}

DEMAND_TYPE_LABELS = {
    "event": "活动执行",
    "marketing": "品牌营销",
    "hiring": "人才招聘",
    "legal": "法律合规",
    "finance": "财税服务",
    "it": "数字化建设",
    "training": "企业培训",
    "sourcing": "资源采购",
}

DEMAND_TYPE_VARIANTS = {
    "event": [
        ["event_planning", "venue", "catering"],
        ["event_planning", "venue", "av"],
        ["event_planning", "catering"],
    ],
    "marketing": [
        ["marketing", "design", "media"],
        ["marketing", "design", "photography"],
        ["marketing", "media"],
    ],
    "hiring": [
        ["hr", "training", "consulting"],
        ["hr", "consulting"],
    ],
    "legal": [
        ["legal", "finance", "consulting"],
        ["legal", "consulting"],
    ],
    "finance": [
        ["finance", "legal", "it"],
        ["finance", "it"],
    ],
    "it": [
        ["it", "consulting", "design"],
        ["it", "consulting"],
    ],
    "training": [
        ["training", "consulting", "hr"],
        ["training", "consulting"],
    ],
    "sourcing": [
        ["logistics", "event_planning", "translation"],
        ["logistics", "event_planning"],
    ],
}

DEMAND_INDUSTRIES = {
    "event": ["culture", "retail", "healthcare"],
    "marketing": ["retail", "culture", "manufacturing"],
    "hiring": ["education", "tech", "finance"],
    "legal": ["finance", "real_estate", "manufacturing"],
    "finance": ["finance", "manufacturing", "retail"],
    "it": ["tech", "logistics", "education"],
    "training": ["education", "finance", "healthcare"],
    "sourcing": ["logistics", "manufacturing", "retail"],
}


def conflict(a: dict, b: dict) -> bool:
    return b["id"] in a["conflicts_with"] or a["id"] in b["conflicts_with"]


def build_companies() -> list[dict]:
    conflicts = {row[0]: [] for row in COMPANY_ROWS}
    for left, right in CONFLICT_PAIRS:
        conflicts[left].append(right)
        conflicts[right].append(left)
    companies = []
    for company_id, name, capabilities, industries, region, capacity, accepting in COMPANY_ROWS:
        capability_text = "、".join(CAPABILITY_LABELS[item] for item in capabilities)
        industry_text = "、".join(INDUSTRY_LABELS[item] for item in industries)
        companies.append(
            {
                "id": company_id,
                "name": name,
                "summary": (
                    f"{name}是虚构的{industry_text}领域会员企业，位于{REGION_LABELS[region]}，"
                    f"提供{capability_text}服务；仅用于离线评测。"
                ),
                "capabilities": list(capabilities),
                "industries": list(industries),
                "region": region,
                "capacity": capacity,
                "accepting": accepting,
                "conflicts_with": sorted(conflicts[company_id]),
            }
        )
    return companies


def build_supplies(companies: list[dict]) -> list[dict]:
    by_id = {company["id"]: company for company in companies}
    supplies = []
    for position, company_id in enumerate(SUPPLY_COMPANY_IDS, start=1):
        company = by_id[company_id]
        status = "paused" if company_id in PAUSED_SUPPLY_COMPANY_IDS else "active"
        capability_text = "、".join(CAPABILITY_LABELS[item] for item in company["capabilities"][:2])
        supplies.append(
            {
                "id": f"s{position:03d}",
                "company_id": company_id,
                "title": company["name"] + " · 标准服务包",
                "summary": (
                    f"{company['name']}提供的{capability_text}服务包，"
                    + ("当前暂停对接。" if status == "paused" else "当前开放对接。")
                    + "虚构供给，仅用于离线评测。"
                ),
                "capabilities": list(company["capabilities"][:2]),
                "industries": list(company["industries"]),
                "region": company["region"],
                "capacity": company["capacity"],
                "status": status,
            }
        )
    return supplies


def eligible_pool(companies: list[dict], supplies: list[dict], requester_id: str) -> list[str]:
    by_id = {company["id"]: company for company in companies}
    requester = by_id[requester_id]
    active_ids = {supply["company_id"] for supply in supplies if supply["status"] == "active"}
    return sorted(
        company["id"]
        for company in companies
        if company["id"] in active_ids
        and company["id"] != requester_id
        and company["accepting"]
        and not conflict(requester, company)
    )


def covered_ids(
    companies: list[dict], supplies: list[dict], demand: dict, pool: list[str]
) -> set[str]:
    by_id = {company["id"]: company for company in companies}
    supply_caps: dict[str, set[str]] = {}
    for supply in supplies:
        if supply["status"] == "active":
            supply_caps.setdefault(supply["company_id"], set()).update(supply["capabilities"])
    required = set(demand["required_capabilities"])
    return {
        company_id
        for company_id in pool
        if required
        & (set(by_id[company_id]["capabilities"]) | supply_caps.get(company_id, set()))
    }


def _pick_rejected(pool: list[str], covered: set[str], index: int) -> list[str]:
    """Deterministic synthetic "previously declined" pairs.

    Prefer companies outside the capability-covered set so the two rejected
    relations do not silently shrink the pool of legitimate candidates.  This
    is a fixture choice, not a label: every rejected company is still eligible
    under the business filters and is disclosed as a synthetic relation.
    """
    if len(pool) < 2:
        raise RuntimeError("eligible pool is too small to pick rejected companies")
    candidates = [company_id for company_id in pool if company_id not in covered]
    if len(candidates) < 2:
        candidates = list(pool)
    first = candidates[(index * 7 + 3) % len(candidates)]
    second = candidates[(index * 7 + 3 + 5) % len(candidates)]
    if second == first:
        second = candidates[(index * 7 + 3 + 1) % len(candidates)]
    return [first, second]


def build_demands(companies: list[dict], supplies: list[dict]) -> list[dict]:
    by_id = {company["id"]: company for company in companies}
    active_ids = {supply["company_id"] for supply in supplies if supply["status"] == "active"}
    accepting_pool = sorted(
        company_id
        for company_id in active_ids
        if by_id[company_id]["accepting"]
    )
    type_names = list(DEMAND_TYPE_LABELS)
    demands = []
    for index in range(60):
        demand_type = type_names[index % len(type_names)]
        variants = DEMAND_TYPE_VARIANTS[demand_type]
        required = list(variants[(index // len(type_names)) % len(variants)])
        requester = by_id[accepting_pool[index % len(accepting_pool)]]
        industry_options = DEMAND_INDUSTRIES[demand_type]
        preferred = [industry_options[index % len(industry_options)]]
        if index % 4 == 0:
            preferred.append(industry_options[(index + 1) % len(industry_options)])
        demand = {
            "id": f"d{index + 1:03d}",
            "type": demand_type,
            "title": f"{DEMAND_TYPE_LABELS[demand_type]}需求 {index + 1:02d}",
            "summary": (
                f"虚拟会员企业寻找{DEMAND_TYPE_LABELS[demand_type]}合作方；"
                "需求、企业、标注均为合成数据，仅用于离线评测。"
            ),
            "requester_company_id": requester["id"],
            "required_capabilities": required,
            "preferred_industries": sorted(set(preferred)),
            "region": REGIONS[(index * 2 + 1) % len(REGIONS)],
            "capacity_need": CAPACITIES[(index + 1) % len(CAPACITIES)],
            "rejected_company_ids": [],
            "should_recommend": [],
            "should_not_recommend": [],
            "annotation_note": (
                "synthetic fixture; six-editor-panel labels; see data/ANNOTATION.md"
            ),
        }
        pool = eligible_pool(companies, supplies, requester["id"])
        demand["rejected_company_ids"] = _pick_rejected(
            pool,
            covered_ids(companies, supplies, demand, pool),
            index,
        )
        demands.append(demand)
    return demands


def build_fixture() -> tuple[list[dict], list[dict], list[dict]]:
    companies = build_companies()
    supplies = build_supplies(companies)
    demands = build_demands(companies, supplies)
    return companies, supplies, demands
