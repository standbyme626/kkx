"""
动作建议模块 - 只用 LLM 生成邮件草稿
其他字段由 scorer.py 规则生成

邮件草稿触发条件（必须全部满足）：
1. 对象是允许的 page_type (company_detail, exhibitor_detail, brand_profile, company_site)
2. 已确认是真实客户公司（公司名不是假的）
3. 客户等级不是 D
4. 至少有一个真实联系方式线索（邮箱/电话/LinkedIn个人页）
   或至少有一个真实联系人线索（决策人姓名）

否则不生成邮件草稿，不再对错误页面标题套模板
"""

import asyncio
from typing import Dict, Any, List


EMAIL_PROMPT = """你是一个外贸获客专家。为客户生成英文开发信草稿。

## 我司信息
{my_info}

## 客户信息
- 公司名: {company_name}
- 决策人: {decision_maker}
- 行业: {industry}
- 国家: {country}

## 等级
{grade}级客户

请生成一封专业开发信（JSON格式）：
{{
    "email_draft": "英文邮件内容..."
}}

只输出 JSON。
"""

# 允许的 page_type
ALLOWED_PAGE_TYPES_FOR_EMAIL = {
    "company_detail",
    "exhibitor_detail",
    "brand_profile",
    "company_site",
}

# 禁止的公司名
FAKE_COMPANY_NAMES = {
    "exhibitor directory", "marketing kit", "why exhibit",
    "show sector", "exhibitor resources", "business builder",
    "exhibitor resource", "steps to success", "unknown",
}


def _join(values: Any, default: str = "") -> str:
    if isinstance(values, list):
        return ", ".join([str(v).strip() for v in values if str(v).strip()])
    return default


def _should_generate_email(lead: Dict[str, Any]) -> bool:
    """判断是否应该为该 lead 生成邮件草稿

    必须全部满足以下条件：
    1. 允许的 page_type
    2. 真实客户公司名
    3. 等级不是 D
    4. 至少有一个真实联系方式或联系人
    """
    # 1. 检查 page_type
    page_type = lead.get("page_type", "unknown")
    if page_type not in ALLOWED_PAGE_TYPES_FOR_EMAIL:
        return False

    # 2. 检查公司名
    company_name = str(lead.get("company_name", "")).strip().lower()
    if not company_name or company_name in FAKE_COMPANY_NAMES:
        return False

    # 3. 检查等级
    grade = str(lead.get("grade", lead.get("final_grade", lead.get("customer_grade", "D")))).upper()
    if grade == "D":
        return False

    # 4. 检查是否有真实联系方式或联系人
    has_email = bool(lead.get("emails"))
    has_phone = bool(lead.get("phones") or lead.get("contacts"))
    has_linkedin_personal = any(
        "/in/" in str(li) for li in (lead.get("linkedin_urls") or [])
    )
    has_decision_maker = bool(lead.get("decision_makers"))
    has_real_contact_page = lead.get("has_real_contact_page", False)

    has_contact_info = has_email or has_phone or has_linkedin_personal
    has_contact_person = has_decision_maker

    if not (has_contact_info or has_contact_person or has_real_contact_page):
        return False

    return True


async def generate_email_draft(
    profile: Dict[str, Any], lead: Dict[str, Any], llm
) -> Dict[str, Any]:
    """只为符合条件的 lead 生成邮件草稿"""
    my_info = f"""Company: {profile.get("company_name", "SWSAGE/WELP")}
Products: giftware, ceramic mugs, stainless steel cups, cork coasters, melamine tableware
Advantages: cross-material consistency, DTF sampling, OEM/ODM, themed ranges"""

    company_name = lead.get("company_name", "")
    decision_maker = _join(lead.get("decision_makers", []), "Team")
    industry = lead.get("industry", "")
    country = lead.get("country", "")
    grade = lead.get("grade", lead.get("final_grade", "B"))

    prompt = EMAIL_PROMPT.format(
        my_info=my_info,
        company_name=company_name,
        decision_maker=decision_maker,
        industry=industry,
        country=country,
        grade=grade,
    )

    try:
        result = await llm.generate_json(prompt)
        email_draft = result.get("email_draft", "")
    except Exception:
        email_draft = ""

    # 如果LLM失败，生成简单邮件
    if not email_draft:
        email_draft = f"""Subject: Premium Custom Giftware Solutions for {company_name}

Dear {decision_maker},

We specialize in cross-material giftware (ceramic mugs, stainless steel tumblers, cork coasters, melamine tableware) with our in-house DTF sampling capability. Our themed ranges help UK/AU retailers increase repeat orders by 40%.

Key advantages:
- 15-day sampling lead time
- 50K-unit monthly capacity
- Consistent artwork across materials (ceramic, stainless steel, cork, melamine)
- Licensed & themed collections available

Could we schedule a call to discuss your needs?

Best regards"""

    return {"email_draft": email_draft}


async def enrich_with_email(
    profile: Dict[str, Any], leads: List[Dict[str, Any]], llm
) -> List[Dict[str, Any]]:
    """只为符合条件的 lead 生成邮件草稿（并行）

    必须满足：
    1. 允许的 page_type
    2. 真实客户公司名
    3. 等级不是 D
    4. 有真实联系方式或联系人
    """
    # 筛选符合条件的 lead
    targets = [l for l in leads if _should_generate_email(l)]
    others = [l for l in leads if not _should_generate_email(l)]

    # 给不符合条件的 lead 标记空邮件
    for lead in others:
        if "email_draft" not in lead:
            lead["email_draft"] = ""
            lead["email_eligible"] = False
            lead["email_ineligible_reason"] = _get_ineligible_reason(lead)

    if not targets:
        return leads

    print(f"[邮件] 符合条件 {len(targets)} 条，不符合 {len(others)} 条")

    tasks = [generate_email_draft(profile, lead, llm) for lead in targets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            targets[i]["email_draft"] = ""
            print(f"[邮件] 生成失败: {targets[i].get('company_name', '?')} - {result}")
        else:
            targets[i].update(result)
            targets[i]["email_eligible"] = True
            print(f"[邮件] 已生成: {targets[i].get('company_name', '?')}")

    return targets + others


def _fallback_email(lead: Dict[str, Any]) -> Dict[str, Any]:
    """降级邮件 - 只在符合条件时调用"""
    if not _should_generate_email(lead):
        return {"email_draft": "", "email_eligible": False,
                "email_ineligible_reason": _get_ineligible_reason(lead)}

    company = lead.get("company_name", "there")
    decision_maker = _join(lead.get("decision_makers", []), "Team")
    return {
        "email_draft": f"""Subject: Custom Giftware Solutions for {company}

Dear {decision_maker},

We offer cross-material giftware (ceramic/stainless/cork) with fast sampling. Our themed ranges help UK/AU retailers increase repeat orders by 40%.

Could we schedule a call?

Best regards""",
        "email_eligible": True,
    }


def _get_ineligible_reason(lead: Dict[str, Any]) -> str:
    """获取不符合邮件生成条件的原因"""
    page_type = lead.get("page_type", "unknown")
    if page_type not in ALLOWED_PAGE_TYPES_FOR_EMAIL:
        return f"page_type '{page_type}' 不允许生成邮件"

    company_name = str(lead.get("company_name", "")).strip().lower()
    if not company_name or company_name in FAKE_COMPANY_NAMES:
        return "公司名无效"

    grade = str(lead.get("grade", lead.get("final_grade", lead.get("customer_grade", "D")))).upper()
    if grade == "D":
        return "D级客户不生成邮件"

    has_email = bool(lead.get("emails"))
    has_phone = bool(lead.get("phones") or lead.get("contacts"))
    has_linkedin_personal = any("/in/" in str(li) for li in (lead.get("linkedin_urls") or []))
    has_decision_maker = bool(lead.get("decision_makers"))

    if not (has_email or has_phone or has_linkedin_personal or has_decision_maker):
        return "无联系方式或联系人"

    return "未知原因"
