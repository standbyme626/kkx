"""
两阶段评分系统
- 第一阶段：客户价值分（值不值得进池子）
- 第二阶段：推进就绪分（现在能不能推给销售）
"""

from typing import Dict, Any, List, Tuple


def _to_english_market(label: str) -> str:
    src = (label or "").strip().lower()
    mapping = {"uk": "UK", "united kingdom": "UK", "australia": "AU", "usa": "US"}
    for k, v in mapping.items():
        if k in src:
            return v
    return label.upper() if label else ""


def _extract_domain(url: str) -> str:
    """提取域名"""
    from urllib.parse import urlparse

    try:
        netloc = urlparse(url).netloc.lower().strip()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


KNOWN_UK_RETAILERS = {
    "therange.co.uk": "UK",
    "dunelm.com": "UK",
    "next.co.uk": "UK",
    "johnlewis.com": "UK",
    "marksandspencer.com": "UK",
    "fenwick.com": "UK",
    "houseoffraser.co.uk": "UK",
    "argos.co.uk": "UK",
    "very.co.uk": "UK",
    "homesense.co.uk": "UK",
    "kiddicare.com": "UK",
}

KNOWN_AU_RETAILERS = {
    "bigw.com.au": "AU",
    "kmart.com.au": "AU",
    "target.com.au": "AU",
    "myer.com.au": "AU",
    "davidjones.com.au": "AU",
    "harveynorman.com.au": "AU",
    "rejectshop.com.au": "AU",
    "spotlight.com.au": "AU",
    "adairs.com.au": "AU",
    "miniso.com.au": "AU",
}


# 种子公司名称（用于识别）
SEED_COMPANY_NAMES = {
    "the range",
    "therange",
    "therange.co.uk",
    "dunelm",
    "dunelm.com",
    "next home",
    "next",
    "next.co.uk",
    "john lewis",
    "johnlewis",
    "johnlewis.com",
    "marks and spencer",
    "marks & spencer",
    "marksandspencer",
    "m&s",
    "fenwick",
    "fenwick.com",
    "homesense",
    "homesense.co.uk",
    "hobbycraft",
    "hobbycraft.co.uk",
    "big w",
    "bigw",
    "bigw.com.au",
    "kmart",
    "kmart.com.au",
    "target",
    "target.com.au",
    "myer",
    "myer.com.au",
    "david jones",
    "davidjones",
    "harvey norman",
    "harveynorman",
    "adairs",
    "adairs.com.au",
    "spotlight",
    "spotlight.com.au",
}


def _infer_country(lead: Dict[str, Any]) -> str:
    """统一 country 推断"""
    website = str(lead.get("website", ""))
    domain = _extract_domain(website)

    if domain.endswith(".co.uk") or domain.endswith(".uk"):
        return "UK"
    if domain.endswith(".com.au") or domain.endswith(".au"):
        return "AU"
    if domain.endswith(".com"):
        country = lead.get("country", "")
        if country:
            return _to_english_market(country)

    for known, c in KNOWN_UK_RETAILERS.items():
        if known in domain:
            return "UK"
    for known, c in KNOWN_AU_RETAILERS.items():
        if known in domain:
            return "AU"

    text = f"{lead.get('company_name', '')} {lead.get('business_scope', '')}".lower()
    if "united kingdom" in text or " uk " in text or "britain" in text:
        return "UK"
    if "australia" in text or " au " in text:
        return "AU"

    return ""


# ========== 第一阶段：客户价值分 ==========


def _score_type_stage1(
    lead: Dict[str, Any], profile: Dict[str, Any]
) -> Tuple[int, str]:
    """公司类型匹配度 (0-30分) - 修正 Promotional + 种子公司识别"""
    industry = str(lead.get("industry", "")).lower()
    business_scope = str(lead.get("business_scope", "")).lower()
    company_name = str(lead.get("company_name", "")).lower()
    website = str(lead.get("website", "")).lower()
    text = f"{industry} {business_scope} {company_name} {website}"

    # 种子公司识别（最高优先级）
    website_domain = _extract_domain(website)
    for seed in SEED_COMPANY_NAMES:
        # 检查域名或公司名是否包含种子
        if website_domain and seed.replace(" ", "").replace(
            ".", ""
        ) in website_domain.replace(".", ""):
            return 30, "目标种子客户"
        if seed in company_name or seed.replace(" ", "") in company_name.replace(
            " ", ""
        ):
            return 30, "目标种子客户"

    # 高优先级：礼品零售买手 / 百货买手 / 节日礼品零售
    if any(
        k in text
        for k in [
            "gift retail",
            "gift shop",
            "department store",
            "homeware retailer",
            "seasonal gift",
            "home and gift",
            "giftware retailer",
            "home retailer",
            "chain store",
            "retail chain",
        ]
    ):
        return 30, "礼品零售买手"

    # 中优先级：连锁店采购
    if any(k in text for k in ["chain", "supermarket", "hypermarket"]):
        return 25, "连锁零售"

    # 修正：Promotional 降为低分
    if any(
        k in text
        for k in ["promotional", "giveaway", "branded merchandise", "promo item"]
    ):
        return 8, "促销品公司（低优先）"

    # 边缘：礼品相关
    if "gift" in text or "homeware" in text:
        return 15, "礼品相关"

    return 5, "待确认"


def _score_market_stage1(
    lead: Dict[str, Any], profile: Dict[str, Any]
) -> Tuple[int, str]:
    """市场匹配度 (0-25分)"""
    country = _infer_country(lead)
    target_markets = {
        _to_english_market(str(m)).upper()
        for m in (profile.get("target_markets") or [])
    }

    if country == "UK" and "UK" in target_markets:
        return 25, "英国目标市场"
    if country == "AU" and "AU" in target_markets:
        return 25, "澳洲目标市场"
    if country == "US" and "US" in target_markets:
        return 15, "美国培育市场"
    if country in {"UK", "AU", "US"}:
        return 10, "其他市场"
    return 5, "非目标市场"


def _score_product_scene(
    lead: Dict[str, Any], profile: Dict[str, Any]
) -> Tuple[int, str]:
    """产品/场景匹配度 (0-20分)"""
    business_scope = str(lead.get("business_scope", "")).lower()
    website = str(lead.get("website", "")).lower()
    company_name = str(lead.get("company_name", "")).lower()
    text = f"{business_scope} {website}"

    # 种子公司直接给产品分
    for seed in SEED_COMPANY_NAMES:
        if seed in company_name or (website and seed in website):
            return 15, "目标客户产品线"

    product_keywords = [
        "mug",
        "cup",
        "bottle",
        "tumbler",
        "placemat",
        "tray",
        "melamine",
        "ceramic",
        "glass",
        "homeware",
        "giftware",
        "kitchen",
        "dining",
        "seasonal",
        "christmas",
        "easter",
        "gift set",
        "cookware",
    ]

    matches = sum(1 for kw in product_keywords if kw in text)

    if matches >= 4:
        return 20, "产品高度匹配"
    elif matches >= 2:
        return 15, "产品匹配"
    elif matches >= 1:
        return 10, "产品相关"
    return 5, "产品待确认"


def _score_risk_stage1(
    lead: Dict[str, Any], profile: Dict[str, Any]
) -> Tuple[int, str]:
    """风险项 (0-10分，扣分制）"""
    business_scope = str(lead.get("business_scope", "")).lower()
    website = str(lead.get("website", "")).lower()
    company_name = str(lead.get("company_name", "")).lower()
    text = f"{business_scope} {website} {company_name}"

    risk_keywords = [
        "wholesale distributor",
        "bulk supplier",
        "manufacturer only",
        "factory direct",
        "china supplier",
        "alibaba",
        "1688",
        "private label",
        "odm",
        "oem only",
    ]

    risk_count = sum(1 for kw in risk_keywords if kw in text)

    if risk_count >= 2:
        return -10, "高风险：纯制作商"
    elif risk_count >= 1:
        return -5, "中风险：可能需要转售"
    return 0, "无明显风险"


def _score_size_stage1(
    lead: Dict[str, Any], profile: Dict[str, Any]
) -> Tuple[int, str]:
    """规模粗匹配 (0-15分)"""
    business_scope = str(lead.get("business_scope", "")).lower()
    company_name = str(lead.get("company_name", "")).lower()
    website = str(lead.get("website", "")).lower()
    text = f"{business_scope} {company_name} {website}"

    # 种子公司直接给大型连锁分
    for seed in SEED_COMPANY_NAMES:
        if seed in company_name or (website and seed in website):
            return 15, "知名连锁"

    if any(k in text for k in ["department store", "1000+ stores", "500+ stores"]):
        return 15, "大型连锁"
    if any(k in text for k in ["100+ stores", "50+ stores", "chain"]):
        return 12, "中型连锁"
    if "wholesale" in text or "distributor" in text:
        return 8, "批发商"
    return 5, "规模待确认"


def score_lead_stage1(
    profile: Dict[str, Any], rules: Dict[str, Any], lead: Dict[str, Any]
) -> Dict[str, Any]:
    """第一阶段评分：客户价值分（不含联系人信息）"""
    # 1. 公司类型 (0-30分)
    score_type_val, type_desc = _score_type_stage1(lead, profile)

    # 2. 市场匹配 (0-25分)
    score_market_val, market_desc = _score_market_stage1(lead, profile)

    # 3. 产品/场景 (0-20分)
    score_product_val, product_desc = _score_product_scene(lead, profile)

    # 4. 风险项 (0--10分)
    score_risk_val, risk_desc = _score_risk_stage1(lead, profile)

    # 5. 规模粗匹配 (0-15分)
    score_size_val, size_desc = _score_size_stage1(lead, profile)

    # 总分
    total = round(
        score_type_val
        + score_market_val
        + score_product_val
        + score_risk_val
        + score_size_val,
        1,
    )
    total = min(100, max(0, total))

    # 分级阈值
    if total >= 80:
        grade = "A"
    elif total >= 65:
        grade = "B"
    elif total >= 50:
        grade = "C"
    else:
        grade = "D"

    country = _infer_country(lead)

    # 第一阶段输出
    result = {
        "customer_value_score": total,
        "customer_grade": grade,
        "score_breakdown_stage1": {
            "type": score_type_val,
            "type_desc": type_desc,
            "market": score_market_val,
            "market_desc": market_desc,
            "product": score_product_val,
            "product_desc": product_desc,
            "risk": score_risk_val,
            "risk_desc": risk_desc,
            "size": score_size_val,
            "size_desc": size_desc,
        },
        "country": country,
    }

    # 第一阶段原因
    reasons = []
    if score_type_val >= 20:
        reasons.append(f"类型匹配：{type_desc}")
    if score_market_val >= 20:
        reasons.append(f"市场：{market_desc}")
    if score_product_val >= 15:
        reasons.append(f"产品：{product_desc}")
    if score_risk_val < 0:
        reasons.append(risk_desc)

    result["grading_reason"] = "；".join(reasons) if reasons else "待完善客户信息"
    result["key_signals"] = [r for r in reasons] if reasons else ["待完善"]

    # 第一阶段动作
    if grade == "A":
        result["next_action_stage1"] = "进入第二阶段：二次搜索补全联系人"
        result["priority"] = "P0"
    elif grade == "B":
        result["next_action_stage1"] = "进入第二阶段：二次搜索补全联系人"
        result["priority"] = "P1"
    elif grade == "C":
        result["next_action_stage1"] = "待培育，观察信号"
        result["priority"] = "P2"
    else:
        result["next_action_stage1"] = "暂不进入线索池"
        result["priority"] = "P3"

    return result


# ========== 第二阶段：推进就绪分 ==========


def _score_contact_role(lead: Dict[str, Any]) -> Tuple[int, str]:
    """联系人角色匹配 (0-25分)"""
    decision_makers = lead.get("decision_makers", [])
    decision_maker_titles = lead.get("decision_maker_titles", [])

    if not decision_makers:
        return 5, "待挖掘联系人"

    best_title = ""
    for idx, title in enumerate(decision_maker_titles):
        if idx < len(decision_makers) and decision_makers[idx]:
            best_title = str(title).lower()
            break

    if not best_title:
        return 10, "已找到联系人"

    # 高优先级角色
    high_roles = [
        "category buyer",
        "gift buyer",
        "home buyer",
        "product development manager",
    ]
    mid_roles = ["buyer", "procurement", "sourcing", "merchandise"]

    if any(r in best_title for r in high_roles):
        return 25, f"关键决策人：{best_title}"
    if any(r in best_title for r in mid_roles):
        return 20, f"采购角色：{best_title}"
    return 15, f"已找到{best_title}"


def _score_contact_info(lead: Dict[str, Any]) -> Tuple[int, str]:
    """联系方式完整度 (0-25分)"""
    emails = lead.get("emails", [])
    contacts = lead.get("contacts", [])
    linkedin_urls = lead.get("linkedin_urls", [])

    score = 0
    items = []

    if emails:
        score += 10
        items.append("邮箱")
    if contacts:
        score += 10
        items.append("电话")
    if linkedin_urls:
        score += 5
        items.append("LinkedIn")

    if score >= 20:
        return score, f"已获取{', '.join(items)}"
    elif score >= 10:
        return score, f"部分联系方式"
    return score, "待补全联系方式"


def _score_evidence(lead: Dict[str, Any]) -> Tuple[int, str]:
    """证据可信度 (0-15分)"""
    website = str(lead.get("website", ""))
    query_hits = lead.get("query_hits", [])

    # 有官网且有查询命中
    if website and query_hits:
        return 15, "多来源验证"
    if website:
        return 10, "有官网验证"
    return 5, "仅搜索结果"


def _score_progress_signal(lead: Dict[str, Any]) -> Tuple[int, str]:
    """推进信号 (0-15分)"""
    business_scope = str(lead.get("business_scope", "")).lower()

    signals = []
    if "sourcing" in business_scope or "procurement" in business_scope:
        signals.append("正在招聘采购")
    if "new collection" in business_scope or "new range" in business_scope:
        signals.append("新品推出")
    if "expansion" in business_scope or "growing" in business_scope:
        signals.append("业务扩张")
    if "gift fair" in business_scope or "exhibitor" in business_scope:
        signals.append("展会参与")

    if len(signals) >= 2:
        return 15, f"多个信号：{', '.join(signals)}"
    elif signals:
        return 10, signals[0]
    return 5, "无明显信号"


def _score_risk_compensate(lead: Dict[str, Any]) -> Tuple[int, str]:
    """风险补正 (0-20分，可正可负)"""
    # 如果第一阶段有风险，用第二阶段补全的信息来补正
    stage1_risk = lead.get("score_breakdown_stage1", {}).get("risk", 0)
    decision_makers = lead.get("decision_makers", [])
    emails = lead.get("emails", [])

    # 高质量联系人可补正风险
    if stage1_risk < 0:
        if decision_makers and emails:
            return 10, "有决策人联系方式，可补正"
        if decision_makers:
            return 5, "有联系人，部分补正"
        return 0, "风险未补正"

    return 0, "无风险需补正"


def score_lead_stage2(
    profile: Dict[str, Any], rules: Dict[str, Any], lead: Dict[str, Any]
) -> Dict[str, Any]:
    """第二阶段评分：推进就绪分"""
    # 1. 联系人角色 (0-25分)
    score_role_val, role_desc = _score_contact_role(lead)

    # 2. 联系方式 (0-25分)
    score_contact_val, contact_desc = _score_contact_info(lead)

    # 3. 证据可信度 (0-15分)
    score_evidence_val, evidence_desc = _score_evidence(lead)

    # 4. 推进信号 (0-15分)
    score_signal_val, signal_desc = _score_progress_signal(lead)

    # 5. 风险补正 (0-20分)
    score_risk_val, risk_desc = _score_risk_compensate(lead)

    # 总分
    total = round(
        score_role_val
        + score_contact_val
        + score_evidence_val
        + score_signal_val
        + score_risk_val,
        1,
    )
    total = min(100, max(0, total))

    # 第二阶段状态
    if total >= 70:
        status = "已补全可跟进"
        needs_manual = False
    elif total >= 50:
        status = "部分补全"
        needs_manual = False
    else:
        status = "信息不足需补正"
        needs_manual = True

    # 生成推荐开口
    if score_role_val >= 20 and score_contact_val >= 20:
        opening = f"尊敬的{lead.get('decision_makers', ['采购负责人'])[0]}，我司专注跨材质礼品定制"
    elif score_contact_val >= 10:
        opening = "您好，关于贵司礼品采购需求"
    else:
        opening = "您好，关注贵司礼品业务"

    result = {
        "data_completeness_score": total,
        "second_search_status": status,
        "needs_manual_takeover": needs_manual,
        "recommended_opening": opening,
        "score_breakdown_stage2": {
            "contact_role": score_role_val,
            "contact_role_desc": role_desc,
            "contact_info": score_contact_val,
            "contact_info_desc": contact_desc,
            "evidence": score_evidence_val,
            "evidence_desc": evidence_desc,
            "progress_signal": score_signal_val,
            "progress_signal_desc": signal_desc,
            "risk_compensate": score_risk_val,
            "risk_compensate_desc": risk_desc,
        },
    }

    # 第二阶段动作
    if status == "已补全可跟进":
        result["next_action_stage2"] = "推荐销售直接联系"
    elif status == "部分补全":
        result["next_action_stage2"] = "发送开发信，等待回复"
    else:
        result["next_action_stage2"] = "需人工补全信息"

    return result


# ========== 合并两阶段评分 ==========


def score_lead(
    profile: Dict[str, Any], rules: Dict[str, Any], lead: Dict[str, Any]
) -> Dict[str, Any]:
    """完整评分 - 自动执行两阶段"""
    # 第一阶段
    stage1_result = score_lead_stage1(profile, rules, lead)

    # 如果是第一阶段结果（含所有字段），合并
    result = {**lead, **stage1_result}

    # 检查是否需要执行第二阶段
    grade = result.get("customer_grade", "D")
    needs_stage2 = grade in ["A", "B"] or result.get("customer_value_score", 0) >= 70

    if needs_stage2 and any(
        [
            lead.get("decision_makers"),
            lead.get("emails"),
            lead.get("contacts"),
            lead.get("linkedin_urls"),
            lead.get("query_hits"),
        ]
    ):
        stage2_result = score_lead_stage2(profile, rules, lead)
        result = {**result, **stage2_result}

        # 计算最终总分和等级
        stage1_score = result.get("customer_value_score", 0)
        stage2_score = result.get("data_completeness_score", 0)

        # 根据第二阶段调整最终等级
        if stage2_score >= 70:
            final_grade = result.get("customer_grade", "C")
        elif stage2_score >= 50 and result.get("customer_grade") in ["A", "B"]:
            final_grade = "B" if result.get("customer_grade") == "A" else "C"
        else:
            final_grade = "C" if result.get("customer_grade") in ["A", "B"] else "D"

        result["final_grade"] = final_grade
    else:
        result["final_grade"] = result.get("customer_grade", "D")
        result["data_completeness_score"] = 0
        result["second_search_status"] = "待二次搜索补全"
        result["needs_manual_takeover"] = True

    # 兼容旧字段
    result["total_score"] = result.get("customer_value_score", 0)
    result["grade"] = result.get("final_grade", result.get("customer_grade", "D"))

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
