"""
输出模块 - JSON + 飞书
15 个业务字段（含邮件草稿、创建时间）
业务词库生成关键判断信号和分级原因
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime


# ========== 业务词库 ==========

# 市场词库
MARKET_WORDS = {
    "UK": "英国首选市场",
    "AU": "澳洲重点市场",
    "US": "美国培育市场",
    "DE": "德国需认证",
    "OTHER": "非目标市场",
}

# 客户类型词库
TYPE_WORDS = {
    "retail": "英澳礼品买手",
    "chain": "英澳零售商",
    "pet": "美国宠物电商",
    "kids": "儿童礼品专营店",
    "wholesale": "大宗批发商",
    "blank": "空白素坯采购商",
    "supermarket": "超市直采",
}

# 需求词库
NEED_WORDS = {
    "multi": "多材质主题配套",
    "dtf": "DTF快样",
    "sample": "小批量测款",
    "oem": "OEM定制",
    "seasonal": "节日主题快速响应",
}

# 信号词库
SIGNAL_WORDS = {
    "hiring": "招聘品类经理",
    "fair": "参加Reed Gift Fairs",
    "new": "新品上架",
    "funding": "融资",
    "inquiry": "平台询盘",
}

# 风险词库
RISK_WORDS = {
    "en71": "缺EN71认证",
    "lfgb": "缺LFGB认证",
    "price": "只比价",
    "small": "小单散客",
    "cost": "服务成本过高",
}


def _generate_key_signals_business(
    lead: Dict[str, Any], grade: str, country: str, industry: str
) -> str:
    """用业务词库生成关键判断信号"""
    parts = []

    # 市场
    market_word = MARKET_WORDS.get(
        country.upper()[:2] if country else "OTHER", "非目标市场"
    )
    parts.append(f"市场：{market_word}")

    # 类型
    ind = (industry or "").lower()
    if "retail" in ind or "gift" in ind:
        parts.append("类型：英澳礼品买手")
    elif "chain" in ind or "department" in ind:
        parts.append("类型：英澳零售商")
    elif "pet" in ind:
        parts.append("类型：美国宠物电商")
    elif "kids" in ind or "child" in ind:
        parts.append("类型：儿童礼品专营店")
    elif "wholesale" in ind or "distributor" in ind:
        parts.append("类型：大宗批发商")

    # 需求 - 从 business_scope 推断
    scope = (lead.get("business_scope") or "").lower()
    if "oem" in scope or "custom" in scope:
        parts.append("需求：OEM定制")
    elif "dtf" in scope:
        parts.append("需求：DTF快样")
    elif "seasonal" in scope or "christmas" in scope:
        parts.append("需求：节日主题快速响应")

    # 风险 - D级专用
    if grade == "D":
        if "wholesale" in ind or "distributor" in ind:
            parts.append("风险：只比价")
        elif "blank" in ind:
            parts.append("风险：小单散客")
        elif "germany" in country.lower() or "german" in scope:
            parts.append("风险：缺LFGB认证")

    return " / ".join(parts) if parts else "市场：非目标市场"


def _generate_grade_reason_business(
    lead: Dict[str, Any], grade: str, country: str, industry: str
) -> str:
    """用业务话术生成分级原因"""
    ind = (industry or "").lower()
    scope = (lead.get("business_scope") or "").lower()

    if grade == "A":
        if country.upper() in ["UK", "AU"]:
            if "retail" in ind or "gift" in ind:
                return "英国礼品买手，主营家居/礼品，匹配我司首选市场"
            return "英澳零售商家，匹配重点市场"
        return "礼品零售买手，匹配目标市场"

    elif grade == "B":
        if "pet" in ind:
            return "美国宠物电商卖家，主营相关品类，匹配DTF快样优势"
        if "kids" in ind or "child" in ind:
            return "英国儿童礼品专营店，有套装需求，需先确认EN71认证"
        return "市场对/类型对，有合作潜力"

    elif grade == "C":
        if "germany" in country.lower():
            return "德国零售商，但缺少LFGB认证，需先核实"
        if "wholesale" in ind:
            return "大宗批发商，价格敏感，匹配度低"
        return "边缘匹配，信息待完善"

    elif grade == "D":
        if "wholesale" in ind:
            return "小单散客，服务成本过高，暂不优先"
        if "blank" in ind:
            return "只买空白素坯，绕过我司最强印花能力"
        return "非目标客户，暂不优先"

    return ""


def write_json(leads: List[Dict[str, Any]], output_path: str = None) -> str:
    """生成本地 JSON"""
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/output/leads_{timestamp}.json"
        if not os.path.isabs(output_path):
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), output_path
            )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamped: List[Dict[str, Any]] = []
    for lead in leads:
        row = dict(lead)
        if not row.get("record_created_at"):
            row["record_created_at"] = now
        stamped.append(row)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stamped, f, ensure_ascii=False, indent=2)

    return output_path


def _join_list(values: Any) -> str:
    """列表转字符串"""
    if isinstance(values, list):
        return ", ".join([str(v).strip() for v in values if str(v).strip()])
    return ""


def _normalize_grade(value: str) -> str:
    """标准化等级"""
    raw = str(value or "").upper()
    return raw if raw in ["A", "B", "C", "D"] else "C"


def _derive_search_status(lead: Dict[str, Any]) -> tuple[str, str]:
    """推导搜索处理状态和备注

    Returns:
        (status, remark)
    """
    grade = _normalize_grade(
        lead.get("final_grade")
        or lead.get("customer_grade")
        or lead.get("grade")
        or "D"
    )
    score = lead.get("customer_value_score") or lead.get("total_score") or 0
    has_name = bool(lead.get("decision_makers") or lead.get("decision_maker"))
    has_email = bool(lead.get("emails"))
    has_phone = bool(lead.get("contacts"))
    has_linkedin = bool(lead.get("linkedin_urls"))
    has_linkedin_personal = any(
        "/in/" in str(li) for li in (lead.get("linkedin_urls") or [])
    )

    # A. 已补全可跟进（有联系人+联系方式）
    if has_name and (has_email or has_phone or has_linkedin_personal):
        return "已补全可跟进", ""

    # B. 高符合度，需第三次搜索（高等级但无任何联系方式）
    if (grade in ["A", "B"] or score >= 65) and not (
        has_email or has_phone or has_linkedin_personal
    ):
        remark = "缺联系人方式，仅有官网"
        return "高符合度，需第三次搜索", remark

    # C. 高符合度，需人工搜索（有线索但不完整）
    if grade in ["A", "B"] or score >= 65:
        clues = []
        if has_linkedin and not has_linkedin_personal:
            clues.append("仅LinkedIn公司页")
        if has_name and not (has_email or has_phone):
            clues.append("有人名无联系方式")
        if clues:
            return "高符合度，需人工搜索", "，".join(clues)

    # D. 信息不足，继续背调（C级）
    if grade == "C":
        return "信息不足，继续背调", "需进一步背调"

    # E. 暂不优先（D级或默认）
    return "暂不优先", "低匹配"


def _format_contact_clues(lead: Dict[str, Any]) -> str:
    """合并联系方式线索"""
    parts = []

    # 1. 真实邮箱
    emails = lead.get("emails", [])
    if emails:
        parts.extend(emails[:2])

    # 2. 电话
    phones = lead.get("contacts", [])
    if phones:
        parts.extend(phones[:2])

    # 3. LinkedIn 个人页
    linkedins = lead.get("linkedin_urls", [])
    for li in linkedins[:2]:
        if "/in/" in li:
            parts.append(li)

    # 4. 官网 contact 页面线索（如果没有其他）
    if not parts and lead.get("website"):
        website = lead.get("website", "")
        if website:
            parts.append(f"{website.rstrip('/')}/contact")

    return " | ".join(parts)


def _format_recommended_contact(lead: Dict[str, Any]) -> str:
    """格式化推荐联系人"""
    names = lead.get("decision_makers", [])
    titles = lead.get("decision_maker_titles", [])
    if not names:
        return ""

    # 合并 name + title
    contacts = []
    for i, name in enumerate(names[:3]):
        title = titles[i] if i < len(titles) else ""
        if title:
            contacts.append(f"{name} ({title})")
        else:
            contacts.append(name)

    return " / ".join(contacts)


def _format_for_feishu(lead: Dict[str, Any]) -> Dict[str, Any]:
    """格式化飞书数据 - 15 个字段（含创建时间）"""

    # 获取基础字段
    company_name = lead.get("company_name", "")
    website = lead.get("website", "")
    country = lead.get("country", "")
    industry = lead.get("industry", "")

    # 客户等级
    grade = _normalize_grade(
        lead.get("final_grade")
        or lead.get("customer_grade")
        or lead.get("grade")
        or "D"
    )

    # 客户符合度分
    score = int(lead.get("customer_value_score") or lead.get("total_score") or 0)

    # 分级原因 - 业务词库生成
    reason = _generate_grade_reason_business(lead, grade, country, industry)

    # 关键判断信号 - 业务词库生成
    key_signals = _generate_key_signals_business(lead, grade, country, industry)

    # 推荐联系人
    recommended_contact = _format_recommended_contact(lead)

    # 联系方式线索
    contact_clues = _format_contact_clues(lead)

    # 搜索处理状态 + 备注
    search_status, remark = _derive_search_status(lead)

    # 下一步动作（基于状态）
    status_to_action = {
        "已补全可跟进": "立即跟进",
        "高符合度，需第三次搜索": "第三次搜索",
        "高符合度，需人工搜索": "人工搜索",
        "信息不足，继续背调": "继续背调",
        "暂不优先": "暂不优先",
    }
    next_action = status_to_action.get(search_status, "待处理")

    created_at = str(
        lead.get("record_created_at")
        or lead.get("created_at")
        or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    return {
        "公司名称": company_name,
        "官网": website,
        "国家": country,
        "客户类型": industry,
        "客户等级": grade,
        "客户符合度分": float(score),
        "分级原因": reason,
        "关键判断信号": key_signals,
        "推荐联系人": recommended_contact,
        "联系方式线索": contact_clues,
        "邮件草稿": lead.get("email_draft", ""),
        "搜索处理状态": search_status,
        "下一步动作": next_action,
        "备注": remark,
        "创建时间": created_at,
    }


# 飞书字段定义 - 15 个（含邮件草稿、创建时间）
FEISHU_FIELDS = [
    {"field_name": "公司名称", "type": 1},
    {"field_name": "官网", "type": 1},
    {"field_name": "国家", "type": 1},
    {"field_name": "客户类型", "type": 1},
    {"field_name": "客户等级", "type": 1},
    {"field_name": "客户符合度分", "type": 1},
    {"field_name": "分级原因", "type": 1},
    {"field_name": "关键判断信号", "type": 1},
    {"field_name": "推荐联系人", "type": 1},
    {"field_name": "联系方式线索", "type": 1},
    {"field_name": "邮件草稿", "type": 1},  # LLM生成
    {"field_name": "搜索处理状态", "type": 1},
    {"field_name": "下一步动作", "type": 1},
    {"field_name": "备注", "type": 1},
    {"field_name": "创建时间", "type": 1},
]


async def create_feishu_table(
    app_token: str = None, table_name: str = "外贸获客结果v17"
) -> dict:
    """创建飞书多维表"""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

    from app.providers.feishu import create_feishu_provider

    if not app_token:
        app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN", "")

    if not app_token:
        return {"error": "未配置 FEISHU_BITABLE_APP_TOKEN"}

    feishu = create_feishu_provider()

    try:
        result = await feishu.create_table(table_name, FEISHU_FIELDS)
        return result
    except Exception as e:
        return {"error": str(e)}


async def write_feishu(leads: List[Dict[str, Any]], table_id: str = None) -> dict:
    """写入飞书多维表"""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

    from app.providers.feishu import create_feishu_provider

    if not table_id:
        table_id = os.getenv("FEISHU_BITABLE_TABLE_ID", "")

    if not table_id:
        return {"error": "未配置 FEISHU_BITABLE_TABLE_ID"}

    feishu = create_feishu_provider(table_id_override=table_id)
    records = [_format_for_feishu(lead) for lead in leads]

    try:
        result = await feishu.write_records(records)
        return result
    except Exception as e:
        return {"error": str(e)}


# ========== 演示 ==========
if __name__ == "__main__":
    # 演示数据
    demo_records = [
        {
            "company_name": "The Range",
            "website": "https://www.therange.co.uk/",
            "country": "UK",
            "industry": "Retail",
            "final_grade": "A",
            "customer_value_score": 85,
            "grading_reason": "目标种子客户，英国市场",
            "key_signals": ["目标市场匹配", "种子客户"],
            "decision_makers": ["John Smith"],
            "decision_maker_titles": ["Category Buyer"],
            "emails": ["buyer@therange.co.uk"],
            "contacts": [],
            "linkedin_urls": [],
        },
        {
            "company_name": "Dunelm",
            "website": "https://www.dunelm.com/",
            "country": "UK",
            "industry": "Retail",
            "final_grade": "B",
            "customer_value_score": 75,
            "grading_reason": "英国零售",
            "key_signals": ["目标市场"],
            "decision_makers": [],
            "emails": [],
            "contacts": [],
            "linkedin_urls": ["https://linkedin.com/company/dunelm"],
        },
        {
            "company_name": "Small Shop",
            "website": "https://smallshop.co.uk/",
            "country": "UK",
            "industry": "Retail",
            "final_grade": "D",
            "customer_value_score": 30,
            "grading_reason": "低匹配",
            "key_signals": [],
            "decision_makers": [],
            "emails": [],
            "contacts": [],
            "linkedin_urls": [],
        },
    ]

    print("=== 演示新飞书格式 ===")
    for rec in demo_records:
        result = _format_for_feishu(rec)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("---")
