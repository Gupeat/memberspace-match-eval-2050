"""Six-editor labeling rules for the #2050 synthetic fixture.

The evaluator sees four weighted features (capability ratio, industry flag,
exact-region flag, capacity threshold).  This module deliberately does not
compute a weighted score.  Six "editors" each use one primary signal and a
short lexicographic tie-break chain:

  1. capability_lead   - IDF rarity density of the matched capabilities
  2. case_strength     - curated verified delivery cases
  3. responsiveness    - curated response time against the request tolerance
  4. industry_fit      - number of preferred industries matched
  5. regional_fit      - same / adjacent / distant region band
  6. capacity_fit      - whether capacity meets the need, then excess capacity

Signals 2 and 3 (verified_cases / response_days / max_response_days) live in
data/editorial-signals.json and are never read by match_eval.  Signal 1 uses
average corpus-level IDF per matched capability, not the evaluator's raw ratio;
adding a common capability can lower it.  There is no weighted sum, no
0.40/0.20 style blend, and no tie-break chain borrowed from the evaluator's
coefficient order.

A positive label must cover at least two required capabilities.  That is a
business floor ("recommend a company that can deliver at least two of the
requested workstreams"), not a scoring weight; it is stated explicitly in
data/ANNOTATION.md.  A slot with no qualified candidate is skipped rather than
filled with a candidate that fails the slot's own condition.

The module is pure: it takes plain dicts and returns plain dicts, so both the
builder and the manual-review replay use exactly the same code path.
"""

from __future__ import annotations

import math

CAPACITY_RANK = {"small": 0, "medium": 1, "large": 2}
CAPACITY_LABELS = {"small": "小型", "medium": "中型", "large": "大型"}
REGION_LABELS = {"east": "华东", "south": "华南", "north": "华北", "west": "西部", "central": "华中"}
REGION_NEIGHBOURS = {
    "east": {"south", "north"},
    "south": {"east", "west"},
    "north": {"east", "west"},
    "west": {"south", "north", "central"},
    "central": {"west"},
}

SLOT_ORDER = (
    "capability_lead",
    "case_strength",
    "responsiveness",
    "industry_fit",
    "regional_fit",
    "capacity_fit",
)

# A company must be able to deliver at least two of the requested workstreams.
# This is the positive-label floor; one-of-three matches are kept in build_views
# for pool diagnostics but are never promoted to should_recommend.
POSITIVE_MIN_COVERAGE = 2

SLOT_NOTES = {
    "capability_lead": "average IDF rarity per matched capability, then coverage",
    "case_strength": "curated verified_cases; capability coverage is only a tie-break",
    "responsiveness": "curated response_days against max_response_days; capability coverage is only a tie-break",
    "industry_fit": "count of preferred industries matched",
    "regional_fit": "same=0, adjacent=1, distant=2 band",
    "capacity_fit": "capacity meets the need first, then smallest sufficient excess",
}


def active_supply_ids(supplies: list[dict]) -> set[str]:
    return {supply["company_id"] for supply in supplies if supply["status"] == "active"}


def active_supply_capabilities(supplies: list[dict]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for supply in supplies:
        if supply["status"] == "active":
            result.setdefault(supply["company_id"], set()).update(supply["capabilities"])
    return result


def effective_capabilities(company: dict, supply_caps: dict[str, set[str]]) -> set[str]:
    return set(company["capabilities"]) | supply_caps.get(company["id"], set())


def idf_by_capability(companies: list[dict], supplies: list[dict]) -> dict[str, float]:
    """Corpus-level rarity; never derived from evaluator weights."""
    supply_caps = active_supply_capabilities(supplies)
    document_frequency: dict[str, int] = {}
    for company in companies:
        for capability in effective_capabilities(company, supply_caps):
            document_frequency[capability] = document_frequency.get(capability, 0) + 1
    total = len(companies)
    return {
        capability: math.log((total + 1) / (frequency + 0.5)) + 1.0
        for capability, frequency in document_frequency.items()
    }


def conflict(a: dict, b: dict) -> bool:
    return b["id"] in a["conflicts_with"] or a["id"] in b["conflicts_with"]


def region_band(demand_region: str, company_region: str) -> int:
    if company_region == demand_region:
        return 0
    if company_region in REGION_NEIGHBOURS.get(demand_region, set()):
        return 1
    return 2


def signal_row(signals: dict, section: str, key: str, field: str, default: int) -> int:
    row = signals.get(section, {}).get(key)
    if not isinstance(row, dict):
        return default
    value = row.get(field)
    return default if value is None else int(value)


def build_views(
    demand: dict,
    companies: list[dict],
    supplies: list[dict],
    signals: dict,
) -> list[dict]:
    """All eligible, covered candidates with every editorial signal resolved."""
    by_id = {company["id"]: company for company in companies}
    requester = by_id[demand["requester_company_id"]]
    supply_ids = active_supply_ids(supplies)
    supply_caps = active_supply_capabilities(supplies)
    idf = idf_by_capability(companies, supplies)
    rejected = set(demand.get("rejected_company_ids", []))
    required = set(demand["required_capabilities"])
    preferred = set(demand["preferred_industries"])
    max_response_days = signal_row(signals, "demands", demand["id"], "max_response_days", 5)
    need_rank = CAPACITY_RANK[demand["capacity_need"]]

    views = []
    for company in companies:
        if company["id"] not in supply_ids:
            continue
        if company["id"] == requester["id"]:
            continue
        if not company["accepting"]:
            continue
        if conflict(requester, company):
            continue
        if company["id"] in rejected:
            continue
        capabilities = effective_capabilities(company, supply_caps)
        matched = sorted(required & capabilities)
        if not matched:
            continue
        coverage = len(matched)
        rarity = round(sum(idf.get(capability, 1.0) for capability in matched), 6)
        industry_matches = len(preferred & set(company["industries"]))
        band = region_band(demand["region"], company["region"])
        capacity_rank = CAPACITY_RANK[company["capacity"]]
        capacity_ok = capacity_rank >= need_rank
        views.append(
            {
                "company_id": company["id"],
                "name": company["name"],
                "coverage": coverage,
                "required_count": len(required),
                "rarity": rarity,
                "rarity_density": round(rarity / coverage, 6),
                "verified_cases": signal_row(signals, "companies", company["id"], "verified_cases", 0),
                "response_days": signal_row(signals, "companies", company["id"], "response_days", 5),
                "max_response_days": max_response_days,
                "industry_matches": industry_matches,
                "preferred_count": len(preferred),
                "region_band": band,
                "region_label": "同区" if band == 0 else ("邻区" if band == 1 else "远区"),
                "capacity_rank": capacity_rank,
                "need_rank": need_rank,
                "capacity_ok": capacity_ok,
                "capacity_gap": capacity_rank - need_rank,
                "capacity_slack": abs(capacity_rank - need_rank),
                "company_capacity": company["capacity"],
            }
        )
    return views


def slot_key(slot: str, view: dict) -> tuple:
    """Lexicographic key for one editor; no feature is multiplied by a weight."""
    if slot == "capability_lead":
        return (
            -view["rarity_density"],
            -view["coverage"],
            view["response_days"],
            view["company_id"],
        )
    if slot == "case_strength":
        return (
            -view["verified_cases"],
            -view["rarity_density"],
            -view["coverage"],
            view["company_id"],
        )
    if slot == "responsiveness":
        return (
            0 if view["response_days"] <= view["max_response_days"] else 1,
            view["response_days"],
            -view["rarity_density"],
            -view["coverage"],
            view["company_id"],
        )
    if slot == "industry_fit":
        return (
            -view["industry_matches"],
            -view["rarity_density"],
            -view["verified_cases"],
            view["company_id"],
        )
    if slot == "regional_fit":
        return (
            view["region_band"],
            -view["rarity_density"],
            -view["verified_cases"],
            view["company_id"],
        )
    if slot == "capacity_fit":
        return (
            0 if view["capacity_ok"] else 1,
            view["capacity_slack"],
            -view["rarity_density"],
            view["company_id"],
        )
    raise ValueError("unknown editorial slot: " + slot)


def slot_qualifies(slot: str, view: dict) -> bool:
    """True when the candidate satisfies the slot's own editorial condition.

    A missing qualified candidate means the editor abstains for this demand; it
    is never filled with a candidate whose primary condition failed.
    """
    if view["coverage"] < POSITIVE_MIN_COVERAGE:
        return False
    if slot == "capability_lead":
        return True
    if slot == "case_strength":
        return view["verified_cases"] > 0
    if slot == "responsiveness":
        return view["response_days"] <= view["max_response_days"]
    if slot == "industry_fit":
        return view["industry_matches"] > 0
    if slot == "regional_fit":
        return view["region_band"] <= 1
    if slot == "capacity_fit":
        return view["capacity_ok"]
    raise ValueError("unknown editorial slot: " + slot)


def slot_reason(slot: str, view: dict) -> str:
    coverage = f"覆盖 {view['coverage']}/{view['required_count']} 项必需能力"
    if slot == "capability_lead":
        return (
            "能力匹配（主槽位）：" + coverage
            + f"，平均 IDF 稀缺度 {view['rarity_density']:.2f}；公司级已核实案例 {view['verified_cases']} 个。"
        )
    if slot == "case_strength":
        return (
            "交付记录（主槽位）："
            + f"{view['verified_cases']} 个公司级已核实案例（不按能力拆分）；"
            + coverage + "。"
        )
    if slot == "responsiveness":
        return (
            "响应时效（主槽位）："
            + f"{view['response_days']} 天响应，需求上限 {view['max_response_days']} 天；"
            + coverage + "。"
        )
    if slot == "industry_fit":
        return (
            "行业匹配（主槽位）："
            + f"命中 {view['industry_matches']}/{view['preferred_count']} 个偏好行业；"
            + coverage + "。"
        )
    if slot == "regional_fit":
        return "区域可达（主槽位）：" + view["region_label"] + "；" + coverage + "。"
    if slot == "capacity_fit":
        return (
            "产能匹配（主槽位）："
            + CAPACITY_LABELS[view["company_capacity"]]
            + "容量，"
            + ("满足" if view["capacity_ok"] else "不足")
            + "需求；"
            + coverage
            + "。"
        )
    raise ValueError("unknown editorial slot: " + slot)


def select_positive_slots(
    demand: dict,
    companies: list[dict],
    supplies: list[dict],
    signals: dict,
) -> list[dict]:
    """Pick at most one distinct company per slot; abstain when a slot has no qualified candidate.

    Slots are processed from the scarcest qualified pool to the richest so a
    niche dimension cannot be drained by a broad one.  The returned rows are
    sorted in canonical SLOT_ORDER.
    """
    views = [
        view
        for view in build_views(demand, companies, supplies, signals)
        if view["coverage"] >= POSITIVE_MIN_COVERAGE
    ]
    if not views:
        raise ValueError(
            f"{demand['id']}: no candidate covers at least "
            f"{POSITIVE_MIN_COVERAGE} required capabilities"
        )

    slot_pools = {
        slot: [view for view in views if slot_qualifies(slot, view)]
        for slot in SLOT_ORDER
    }
    if not slot_pools["capability_lead"]:
        raise ValueError(f"{demand['id']}: no qualified capability_lead candidate")

    order = sorted(
        SLOT_ORDER,
        key=lambda slot: (len(slot_pools[slot]), SLOT_ORDER.index(slot)),
    )
    chosen: set[str] = set()
    rows: list[dict] = []
    for slot in order:
        remaining = [
            view
            for view in slot_pools[slot]
            if view["company_id"] not in chosen
        ]
        if not remaining:
            continue
        selected = min(remaining, key=lambda view: slot_key(slot, view))
        chosen.add(selected["company_id"])
        rows.append(
            {
                "slot": slot,
                "company_id": selected["company_id"],
                "reason": slot_reason(slot, selected),
            }
        )
    rows.sort(key=lambda row: SLOT_ORDER.index(row["slot"]))
    return rows


def eligible_positive_ids(
    demand: dict,
    companies: list[dict],
    supplies: list[dict],
    signals: dict,
) -> set[str]:
    """Company ids that clear the positive coverage floor for this demand."""
    return {
        view["company_id"]
        for view in build_views(demand, companies, supplies, signals)
        if view["coverage"] >= POSITIVE_MIN_COVERAGE
    }


def select_negative_rows(
    demand: dict,
    companies: list[dict],
    supplies: list[dict],
    positive_ids: list[str],
) -> list[dict]:
    """Two rejected + one not-accepting + one conflict (or a second not-accepting)."""
    by_id = {company["id"]: company for company in companies}
    requester = by_id[demand["requester_company_id"]]
    supply_ids = active_supply_ids(supplies)
    chosen = set(positive_ids)
    rejected = list(demand.get("rejected_company_ids", []))
    if len(rejected) != 2:
        raise ValueError(f"{demand['id']}: expected two rejected_company_ids")
    rows = [{"company_id": company_id, "reason": "rejected"} for company_id in rejected]
    chosen.update(rejected)

    not_accepting = sorted(
        company["id"]
        for company in companies
        if company["id"] in supply_ids
        and not company["accepting"]
        and company["id"] != requester["id"]
        and company["id"] not in chosen
    )
    if not not_accepting:
        raise ValueError(f"{demand['id']}: no not-accepting company available")
    rows.append({"company_id": not_accepting[0], "reason": "not_accepting"})
    chosen.add(not_accepting[0])

    conflicts = sorted(
        company["id"]
        for company in companies
        if company["id"] in supply_ids
        and company["id"] != requester["id"]
        and company["id"] not in chosen
        and conflict(requester, company)
    )
    if conflicts:
        rows.append({"company_id": conflicts[0], "reason": "conflict"})
    else:
        remaining = [company_id for company_id in not_accepting if company_id not in chosen]
        if not remaining:
            raise ValueError(f"{demand['id']}: no second not-accepting company available")
        rows.append({"company_id": remaining[0], "reason": "not_accepting"})
    return rows
