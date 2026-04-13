"""
动作建议模块 - 只用 LLM 生成邮件草稿
其他字段由 scorer.py 规则生成
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

## 等级
{grade}级客户

请生成一封专业开发信（JSON格式）：
{{
    "email_draft": "英文邮件内容..."
}}

只输出 JSON。
"""


def _join(values: Any, default: str = "") -> str:
    if isinstance(values, list):
        return ", ".join([str(v).strip() for v in values if str(v).strip()])
    return default


async def generate_email_draft(
    profile: Dict[str, Any], lead: Dict[str, Any], llm
) -> Dict[str, Any]:
    """只生成邮件草稿"""
    my_info = f"""Company: {profile.get("company_name", "SWSAGE/WELP")}
Products: giftware, ceramic mugs, stainless steel cups
Advantages: cross-material consistency, DTF sampling, OEM/ODM"""

    company_name = lead.get("company_name", "")
    decision_maker = _join(lead.get("decision_makers", []), "Team")
    industry = lead.get("industry", "")
    grade = lead.get("grade", "B")

    prompt = EMAIL_PROMPT.format(
        my_info=my_info,
        company_name=company_name,
        decision_maker=decision_maker,
        industry=industry,
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

We specialize in cross-material giftware (ceramic/stainless/cork) with our in-house DTF sampling capability. Our themed ranges help UK retailers increase repeat orders by 40%.

Key advantages:
- 15-day sampling lead time
- 50K-unit monthly capacity
- Consistent artwork across materials

Could we schedule a call to discuss your needs?

Best regards"""

    return {"email_draft": email_draft}


async def enrich_with_email(
    profile: Dict[str, Any], leads: List[Dict[str, Any]], llm
) -> List[Dict[str, Any]]:
    """为所有客户生成邮件草稿（并行）"""
    # 只对 A/B 级生成
    targets = [l for l in leads if l.get("grade", "C") in ["A", "B"]]
    others = [l for l in leads if l.get("grade", "C") not in ["A", "B"]]

    if not targets:
        return leads

    tasks = [generate_email_draft(profile, lead, llm) for lead in targets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            targets[i]["email_draft"] = ""
        else:
            targets[i].update(result)

    return targets + others


def _fallback_email(lead: Dict[str, Any]) -> Dict[str, Any]:
    """降级邮件"""
    company = lead.get("company_name", "there")
    return {
        "email_draft": f"""Subject: Custom Giftware Solutions for {company}

Dear Team,

We offer cross-material giftware (ceramic/stainless/cork) with fast sampling. Our themed ranges help UK retailers increase repeat orders by 40%.

Could we schedule a call?

Best regards"""
    }
