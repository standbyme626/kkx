"""
查询生成模块 - 严格按照 1.md 搜索规范
一次搜索：找真实客户公司页 / exhibitor detail 页 / brand profile 页
二次搜索：只补真实联系人，不再乱拼 /contact
"""

from typing import Dict, Any, List


def _to_english_market(label: str) -> str:
    """转换市场标签到英文"""
    src = (label or "").strip()
    if not src:
        return ""
    mapping = {
        "uk": "UK",
        "united kingdom": "UK",
        "英国": "UK",
        "australia": "Australia",
        "澳洲": "Australia",
        "澳大利亚": "Australia",
        "usa": "USA",
        "united states": "USA",
        "美国": "USA",
    }
    lower = src.lower()
    for k, v in mapping.items():
        if k in lower:
            return v
    return src


# ============================================================
# 一次搜索最终版（来自 1.md）
# ============================================================

# A. 直接公司搜索 - 基础组
COMPANY_QUERIES_BASE = [
    '"ceramic mug gift retailer uk"',
    '"giftware wholesaler australia"',
    '"homeware wholesaler australia"',
    '"tabletop gift retailer uk"',
    '"seasonal giftware wholesaler uk"',
    '"gift and homewares wholesaler australia"',
    '"mug and tumbler retailer uk"',
    '"giftware brand australia wholesale"',
    '"home decor gift retailer uk"',
    '"tabletop homeware retailer australia"',
]

# B. 更贴近 SWSAGE 产品组合的搜索
COMPANY_QUERIES_COMBO = [
    '"ceramic mug stainless tumbler giftware retailer uk"',
    '"cross material giftware wholesaler australia"',
    '"themed giftware homeware retailer uk"',
    '"kids melamine gift retailer australia"',
    '"placemat coaster homeware wholesaler uk"',
]

# C. 展会目录下钻搜索
EXHIBITOR_QUERIES = [
    'site:autumnfair.com/exhibitors giftware',
    'site:autumnfair.com/exhibitors homeware',
    'site:autumnfair.com/exhibitors mug',
    'site:reedgiftfairs.com.au "exhibitor details" gift',
    'site:reedgiftfairs.com.au "brand directory" tabletop',
]

# D. detail page 特征搜索
DETAIL_QUERIES = [
    'site:autumnfair.com/exhibitors "Overview" "Products"',
    'site:autumnfair.com/exhibitors "Stand:"',
    'site:reedgiftfairs.com.au "contact details" "brands" "products"',
]

# ============================================================
# 一次搜索负向过滤词（来自 1.md）
# ============================================================

NEGATIVE_KEYWORDS = [
    # 展会资源页
    "marketing kit",
    "exhibiting 101",
    "why exhibit",
    "exhibit",
    "show sector",
    "exhibitor directory",
    "brand directory",
    "business builder",
    "event guide",
    "retail therapy",
    "getting there",
    "exhibitor resources",
    "exhibitor portal",
    "exhibitor registration",
    "book a stand",
    "become an exhibitor",
    "exhibition guide",
    "exhibitor information",
    "exhibitor manual",
    # 目录/栏目页
    "directory",
    "browse exhibitors",
    "see all exhibitors",
    "full exhibitor list",
    "complete list of",
    # 新闻/博客
    "blog",
    "news",
    "feature",
    "press release",
    "event news",
    "show blog",
    # 其他
    "contact us",
    "faq",
    "resources",
    "manual",
    "event contact",
    "show contact",
    "general enquiry",
    "event organiser",
    # 文章/博客特征
    "best independent",
    "list of",
    "stores reveal",
    "big spenders",
    "review of",
    # 评论/Yelp
    "yelp",
    "tripadvisor",
]

# ============================================================
# 二次搜索最终版（来自 1.md）
# ============================================================

CONTACT_WEBSITE_TEMPLATES = [
    '"{company}" contact',
    '"{company}" contact us',
    '"{company}" about us',
    '"{company}" team',
    '"{company}" wholesale contact',
]

CONTACT_ROLE_TEMPLATES = [
    '"{company}" buyer',
    '"{company}" category manager',
    '"{company}" purchasing manager',
    '"{company}" founder',
    '"{company}" owner',
]

CONTACT_LINKEDIN_TEMPLATES = [
    '"{company}" linkedin',
    '"{company}" buyer linkedin',
    '"{company}" category manager linkedin',
    '"{company}" purchasing manager linkedin',
]

CONTACT_EMAIL_TEMPLATES = [
    '"{company}" email',
    '"{company}" buyer email',
    '"{company}" wholesale email',
    '"{company}" phone',
    '"{company}" head office phone',
    '"{company}" contact email',
]

CONTACT_ENHANCED_TEMPLATES = [
    '"{company}" gift buyer email',
    '"{company}" wholesale enquiries',
]


def _build_company_queries(profile: Dict[str, Any], max_queries: int = 50) -> List[str]:
    """一次搜索：公司级搜索（英文）

    严格按照 1.md 最终版 query 清单
    """
    queries = []

    # A. 直接公司搜索 - 基础组
    queries.extend(COMPANY_QUERIES_BASE)

    # B. 更贴近 SWSAGE 产品组合
    queries.extend(COMPANY_QUERIES_COMBO)

    # C. 展会目录下钻
    queries.extend(EXHIBITOR_QUERIES)

    # D. detail page 特征搜索
    queries.extend(DETAIL_QUERIES)

    # 去重
    deduped = []
    seen = set()
    for q in queries:
        q_norm = " ".join(q.split()).strip()
        if q_norm and q_norm not in seen:
            deduped.append(q_norm)
            seen.add(q_norm)

    return deduped[:max_queries]


def _build_exhibitor_queries(profile: Dict[str, Any], max_queries: int = 15) -> List[str]:
    """展会目录下钻搜索（已合并到 _build_company_queries）"""
    return []


def build_contact_queries(company_name: str, max_queries: int = 22) -> List[str]:
    """二次搜索：联系人补全

    严格按照 1.md 最终版 query 清单
    只对已确认的真实公司名做搜索，不再乱拼 /contact
    """
    queries = []

    # 官网 / 联系页类
    for template in CONTACT_WEBSITE_TEMPLATES:
        queries.append(template.format(company=company_name))

    # 职位 / 人名类
    for template in CONTACT_ROLE_TEMPLATES:
        queries.append(template.format(company=company_name))

    # LinkedIn 类
    for template in CONTACT_LINKEDIN_TEMPLATES:
        queries.append(template.format(company=company_name))

    # 邮箱 / 电话类
    for template in CONTACT_EMAIL_TEMPLATES:
        queries.append(template.format(company=company_name))

    # 组合增强模板
    for template in CONTACT_ENHANCED_TEMPLATES:
        queries.append(template.format(company=company_name))

    # 去重
    deduped = []
    seen = set()
    for q in queries:
        q_norm = " ".join(q.split()).strip()
        if q_norm and q_norm not in seen:
            deduped.append(q_norm)
            seen.add(q_norm)

    return deduped[:max_queries]


def build_lead_queries(profile: Dict[str, Any], max_queries: int = 50) -> List[str]:
    """构建完整查询列表

    一次搜索分三组：
    1. 直接公司搜索
    2. 展会目录下钻搜索
    3. detail page 特征搜索
    """
    company_qs = _build_company_queries(profile, max_queries=max_queries)
    exhibitor_qs = _build_exhibitor_queries(profile)

    all_queries = company_qs + exhibitor_qs

    # 去重
    deduped = []
    seen = set()
    for q in all_queries:
        q_norm = " ".join(q.split()).strip()
        if q_norm and q_norm not in seen:
            deduped.append(q_norm)
            seen.add(q_norm)

    return deduped[:max_queries]
