"""
评分系统 - 两层分离
1. 客户匹配分：决定 A/B/C/D 等级（与联系人信息无关）
2. 推进就绪分：决定下一步动作（背调/三搜/人工/跟进）

阈值：
- A >= 70
- B = 55-69
- C = 40-54
- D < 40
- < 25 自动排除
"""

from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse


def _to_english_market(label: str) -> str:
    src = (label or "").strip().lower()
    mapping = {
        "uk": "UK", "united kingdom": "UK", "英国": "UK",
        "australia": "AU", "澳洲": "AU", "澳大利亚": "AU",
        "usa": "US", "united states": "US", "美国": "US",
    }
    for k, v in mapping.items():
        if k in src:
            return v
    return label.upper() if label else ""


def _extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower().strip()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


KNOWN_RETAILERS = {
    "therange.co.uk": "UK", "dunelm.com": "UK", "next.co.uk": "UK",
    "johnlewis.com": "UK", "marksandspencer.com": "UK", "fenwick.com": "UK",
    "houseoffraser.co.uk": "UK", "argos.co.uk": "UK", "very.co.uk": "UK",
    "homesense.co.uk": "UK", "hobbycraft.co.uk": "UK",
    "bigw.com.au": "AU", "kmart.com.au": "AU", "target.com.au": "AU",
    "myer.com.au": "AU", "davidjones.com.au": "AU", "harveynorman.com.au": "AU",
    "rejectshop.com.au": "AU", "spotlight.com.au": "AU", "adairs.com.au": "AU",
}

# 国家关键词 - 从页面内容提取（不从 TLD 硬猜）
COUNTRY_CONTENT_KEYWORDS = {
    "UK": [
        "united kingdom", "london, uk", "manchester, uk", "birmingham, uk",
        "liverpool, uk", ", uk", " uk ", "britain", "england,", "scotland,",
        "registered in england", "uk company", "uk registered", "vat gb",
    ],
    "AU": [
        " australia", " melbourne", " sydney", "brisbane", "adelaide",
        "australian", ", australia", "victoria, australia", "nsw, australia",
        "abn ", "acn ",
    ],
    "US": [
        " united states", " usa ", " new york, ny", " los angeles",
        "chicago, il", "american", ", usa", "inc.", "llc",
    ],
}


def _infer_country(lead: Dict[str, Any]) -> str:
    """国家推断：优先从页面内容提取，不从 TLD 硬猜"""
    website = str(lead.get("website", ""))
    title = str(lead.get("company_name", "") or "")
    content = str(lead.get("business_scope", "") or "")
    domain = _extract_domain(website)

    # 1. 已知零售商映射优先
    for known, country in KNOWN_RETAILERS.items():
        if known in domain:
            return country

    # 2. 从页面内容提取国家
    text = f"{title} {content}".lower()
    for country, keywords in COUNTRY_CONTENT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return country

    # 3. lead 里已有的 country 字段（来自 normalizer）
    existing = lead.get("country", "").strip().upper()
    if existing in ("UK", "AU", "US"):
        return existing

    # 4. URL 路径中的国家线索（谨慎使用）
    url_lower = website.lower()
    if "/uk/" in url_lower or "/united-kingdom/" in url_lower:
        return "UK"
    if "/au/" in url_lower or "/australia/" in url_lower:
        return "AU"

    return ""


# ============================================================
# 第一层：客户匹配分（决定 A/B/C/D 等级）
# ============================================================

def _score_market_match(lead: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, str]:
    """市场匹配 (0-30分)

    优先从页面内容提取国家，不从域名 TLD 硬猜。
    """
    country = _infer_country(lead)
    target_markets = {
        _to_english_market(str(m)).upper()
        for m in (profile.get("target_markets") or [])
    }
    if not target_markets:
        target_markets = {"UK", "AU"}

    if country == "UK" and "UK" in target_markets:
        return 30, "英国首选市场"
    if country == "AU" and "AU" in target_markets:
        return 30, "澳洲重点市场"
    if country == "US" and "US" in target_markets:
        return 20, "美国培育市场"
    if country in ("UK", "AU", "US"):
        return 10, "非目标英语市场"
    return 0, "国家未识别/非目标市场"


def _score_customer_type(lead: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, str]:
    """客户类型匹配 (0-30分)"""
    industry = str(lead.get("industry", "")).lower()
    business_scope = str(lead.get("business_scope", "")).lower()
    company_name = str(lead.get("company_name", "")).lower()
    text = f"{industry} {business_scope} {company_name}"

    # 高优先：礼品零售买手 / 百货 / homeware
    if any(k in text for k in [
        "gift retail", "gift shop", "gift retailer", "gift wholesaler",
        "homeware retailer", "homeware wholesaler", "department store",
        "seasonal gift", "home and gift", "giftware retailer",
        "home retailer", "tabletop", "boutique gift",
    ]):
        return 30, "礼品零售买手"

    # 中优先：连锁 / 大型零售
    if any(k in text for k in ["chain", "supermarket", "lifestyle retailer"]):
        return 25, "连锁/大型零售"

    # 边缘：礼品相关
    if "gift" in text or "homeware" in text or "tableware" in text:
        return 15, "礼品/家居相关"

    return 5, "类型不明确"


def _score_product_scene(lead: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, str]:
    """产品/场景匹配 (0-25分)"""
    business_scope = str(lead.get("business_scope", "")).lower()
    website = str(lead.get("website", "")).lower()
    text = f"{business_scope} {website}"

    product_keywords = [
        "mug", "cup", "tumbler", "bottle", "placemat", "tray",
        "melamine", "ceramic", "cork", "glass", "homeware",
        "giftware", "kitchen", "dining", "seasonal", "christmas",
        "gift set", "cookware", "tabletop",
    ]

    matches = sum(1 for kw in product_keywords if kw in text)

    if matches >= 4:
        return 25, "产品高度匹配"
    elif matches >= 2:
        return 20, "产品匹配"
    elif matches >= 1:
        return 12, "产品相关"
    return 5, "产品不明确"


def _score_risk(lead: Dict[str, Any], profile: Dict[str, Any]) -> Tuple[int, str]:
    """风险项 (0-15分，含扣分)"""
    business_scope = str(lead.get("business_scope", "")).lower()
    website = str(lead.get("website", "")).lower()
    company_name = str(lead.get("company_name", "")).lower()
    text = f"{business_scope} {website} {company_name}"

    risk_keywords = [
        "wholesale distributor", "bulk supplier", "manufacturer only",
        "factory direct", "china supplier", "alibaba", "1688",
        "private label", "odm", "oem only",
    ]
    risk_count = sum(1 for kw in risk_keywords if kw in text)

    if risk_count >= 2:
        return 0, "高风险：纯制造商/平台"
    elif risk_count >= 1:
        return 5, "中风险"

    # 无风险，给基础分
    return 15, "无明显风险"


def score_customer_match(
    profile: Dict[str, Any], rules: Dict[str, Any], lead: Dict[str, Any]
) -> Dict[str, Any]:
    """客户匹配分 - 决定 A/B/C/D 等级

    与联系人信息完全无关。
    """
    score_market, market_desc = _score_market_match(lead, profile)
    score_type, type_desc = _score_customer_type(lead, profile)
    score_product, product_desc = _score_product_scene(lead, profile)
    score_risk, risk_desc = _score_risk(lead, profile)

    total = score_market + score_type + score_product + score_risk
    total = min(100, max(0, total))

    # A/B/C/D 只由客户匹配分决定
    if total >= 70:
        grade = "A"
    elif total >= 55:
        grade = "B"
    elif total >= 40:
        grade = "C"
    else:
        grade = "D"

    country = _infer_country(lead)

    result = {
        "customer_value_score": total,
        "customer_grade": grade,
        "customer_match_score": total,  # 显式字段
        "score_breakdown_match": {
            "market": score_market,
            "market_desc": market_desc,
            "customer_type": score_type,
            "customer_type_desc": type_desc,
            "product": score_product,
            "product_desc": product_desc,
            "risk": score_risk,
            "risk_desc": risk_desc,
        },
        "country": country,
    }

    # 分级原因
    reasons = []
    if score_market >= 25:
        reasons.append(f"市场：{market_desc}")
    if score_type >= 25:
        reasons.append(f"类型：{type_desc}")
    if score_product >= 15:
        reasons.append(f"产品：{product_desc}")
    if score_risk <= 5:
        reasons.append(f"风险：{risk_desc}")

    result["grading_reason"] = "；".join(reasons) if reasons else "待完善客户信息"
    result["key_signals"] = reasons if reasons else ["待完善"]

    # 下一步动作（基于匹配分 + 联系人状态）
    has_contact = bool(
        lead.get("decision_makers") or lead.get("emails") or
        lead.get("contacts") or lead.get("linkedin_urls")
    )

    if total < 25:
        result["next_action_stage1"] = "自动排除：匹配度过低"
        result["priority"] = "P4"
    elif grade == "A":
        if has_contact:
            result["next_action_stage1"] = "立即跟进"
            result["priority"] = "P0"
        else:
            result["next_action_stage1"] = "第三次搜索补联系人"
            result["priority"] = "P1"
    elif grade == "B":
        if has_contact:
            result["next_action_stage1"] = "发送开发信"
            result["priority"] = "P1"
        else:
            result["next_action_stage1"] = "继续背调"
            result["priority"] = "P2"
    elif grade == "C":
        result["next_action_stage1"] = "信息不足，继续背调"
        result["priority"] = "P2"
    else:
        result["next_action_stage1"] = "暂不优先"
        result["priority"] = "P3"

    return result


# ============================================================
# 第二层：推进就绪分（决定下一步动作）
# ============================================================

def _score_readiness(lead: Dict[str, Any]) -> Dict[str, Any]:
    """推进就绪分 - 与 A/B/C/D 无关，只决定下一步动作"""
    emails = lead.get("emails", [])
    contacts = lead.get("contacts", [])
    linkedin_urls = lead.get("linkedin_urls", [])
    decision_makers = lead.get("decision_makers", [])
    decision_maker_titles = lead.get("decision_maker_titles", [])
    website = str(lead.get("website", "") or "")
    has_real_contact_page = lead.get("has_real_contact_page", False)

    # 官网
    website_score = 10 if website else 0
    website_desc = "有官网" if website else "无官网"

    # 联系人
    contact_score = 0
    if decision_makers:
        # 检查是否有真实角色
        title_text = " ".join(str(t).lower() for t in decision_maker_titles)
        if any(r in title_text for r in [
            "category buyer", "gift buyer", "home buyer",
            "product development", "purchasing manager",
        ]):
            contact_score = 30
            contact_desc = f"关键决策人：{decision_maker_titles[0] if decision_maker_titles else decision_makers[0]}"
        elif any(r in title_text for r in [
            "buyer", "procurement", "sourcing", "merchandise",
            "manager", "director", "owner", "founder",
        ]):
            contact_score = 25
            contact_desc = f"采购角色：{decision_maker_titles[0] if decision_maker_titles else ''}"
        else:
            contact_score = 15
            contact_desc = f"联系人：{decision_makers[0]}"
    else:
        contact_desc = "无联系人"

    # 联系方式
    method_score = 0
    method_items = []
    if emails:
        method_score += 25
        method_items.append("邮箱")
    if contacts:
        method_score += 15
        method_items.append("电话")
    if any("/in/" in str(li) for li in linkedin_urls):
        method_score += 15
        method_items.append("LinkedIn个人")
    elif linkedin_urls:
        method_score += 5
        method_items.append("LinkedIn公司页")
    method_desc = f"已获取{', '.join(method_items)}" if method_items else "无联系方式"

    # 证据完整度
    evidence_score = 0
    if website and has_real_contact_page:
        evidence_score = 20
        evidence_desc = "真实联系页验证"
    elif website:
        evidence_score = 15
        evidence_desc = "有官网验证"
    else:
        evidence_score = 5
        evidence_desc = "仅搜索结果"

    total = website_score + contact_score + method_score + evidence_score
    total = min(100, max(0, total))

    # 推进状态
    if total >= 70:
        status = "已补全可跟进"
        action = "立即跟进"
    elif total >= 50:
        status = "部分补全"
        action = "发送开发信"
    elif total >= 30:
        status = "信息不足，继续背调"
        action = "继续背调"
    else:
        status = "信息严重不足"
        action = "第三次搜索或人工搜索"

    return {
        "readiness_score": total,
        "readiness_breakdown": {
            "website": website_score,
            "website_desc": website_desc,
            "contact": contact_score,
            "contact_desc": contact_desc,
            "method": method_score,
            "method_desc": method_desc,
            "evidence": evidence_score,
            "evidence_desc": evidence_desc,
        },
        "second_search_status": status,
        "next_action_stage2": action,
    }


# ============================================================
# 合并评分
# ============================================================

def score_lead(
    profile: Dict[str, Any], rules: Dict[str, Any], lead: Dict[str, Any]
) -> Dict[str, Any]:
    """完整评分 - 客户匹配分 + 推进就绪分"""
    # 第一层：客户匹配分（决定 A/B/C/D）
    match_result = score_customer_match(profile, rules, lead)

    result = {**lead, **match_result}

    # 第二层：推进就绪分（决定下一步动作）
    readiness_result = _score_readiness(lead)
    result = {**result, **readiness_result}

    # 兼容旧字段
    result["total_score"] = result.get("customer_value_score", 0)
    result["grade"] = result.get("customer_grade", "D")
    result["final_grade"] = result.get("customer_grade", "D")
    result["data_completeness_score"] = result.get("readiness_score", 0)

    return result


def _normalize_company_key(lead: Dict[str, Any]) -> str:
    name = str(lead.get("company_name", "")).lower().strip()
    for suffix in [" ltd", " ltd.", " limited", " uk", " co", " co."]:
        name = name.replace(suffix, "")
    return name.strip()


def score_leads(
    profile: Dict[str, Any],
    rules: Dict[str, Any],
    leads: List[Dict[str, Any]],
    max_leads: int = 10,
    include_all_grades: bool = True,
) -> List[Dict[str, Any]]:
    scored = []
    for lead in leads:
        result = score_lead(profile, rules, lead)
        scored.append(result)

    # 过滤 < 25 的自动排除
    if include_all_grades:
        scored = [s for s in scored if s.get("customer_value_score", 0) >= 25]

    # 去重
    seen = {}
    for lead in scored:
        key = _normalize_company_key(lead)
        if key not in seen or lead.get("customer_value_score", 0) > seen[key].get(
            "customer_value_score", 0
        ):
            seen[key] = lead

    unique = list(seen.values())
    unique.sort(key=lambda x: x.get("customer_value_score", 0), reverse=True)

    if include_all_grades:
        return unique
    return unique[:max_leads]
