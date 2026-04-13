"""
查询生成模块 - 垂直目录+展会优先
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


def _to_english_customer_type(label: str) -> str:
    """转换客户类型到英文"""
    src = (label or "").strip()
    if not src:
        return "gift distributor"
    mapping = {
        "礼品渠道商": "gift distributor",
        "电商卖家": "e-commerce seller",
        "连锁礼品店": "gift retail chain",
        "中高端礼品采购商": "premium gift buyer",
        "批发": "wholesale",
        "零售": "retail",
    }
    for k, v in mapping.items():
        if k in src:
            return v
    return src


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


# ========== 垂直目录 + 展会查询 ==========


CHANNEL_QUERIES = {
    "UK": [
        # Autumn Fair 参展商
        "site:autumnfair.com exhibitor giftware",
        "site:autumnfair.com buyer gift",
        "site:autumnfair.com retail buyer",
        # Faire 批发平台
        "site:faire.com wholesale gift UK",
        "site:faire.com retailer UK mugs",
        # 其他展会
        "site:homeandgift.com buyer",
        "site:homecollective.com buyer",
    ],
    "Australia": [
        # Reed Gift Fairs
        "site:reedgiftfairs.com.au exhibitor gift",
        "site:reedgiftfairs.com.au buyer homeware",
        "site:reedgiftfairs.com.au retail buyer",
        # Faire AU
        "site:faire.com wholesale gift Australia",
        # 其他渠道
        "site:adairs.com.au buyer",
        "site: rejects.com.au buyer gift",
    ],
    "USA": [
        "site:nynow.com gift buyer",
        "site:asdshow.com gift buyer",
        "site:faire.com wholesale gift USA",
    ],
}


# ========== 目标客户种子公司 ==========


TARGET_RETAILERS = {
    "UK": [
        {"name": "The Range", "domain": "therange.co.uk"},
        {"name": "Dunelm", "domain": "dunelm.com"},
        {"name": "Next Home", "domain": "next.co.uk"},
        {"name": "John Lewis", "domain": "johnlewis.com"},
        {"name": "Marks & Spencer", "domain": "marksandspencer.com"},
        {"name": "Fenwick", "domain": "fenwick.com"},
        {"name": "HomeSense", "domain": "homesense.co.uk"},
        {"name": "Hobbycraft", "domain": "hobbycraft.co.uk"},
        {"name": "Wilko", "domain": "wilko.com"},
        {"name": "Poundland", "domain": "poundland.co.uk"},
    ],
    "Australia": [
        {"name": "Big W", "domain": "bigw.com.au"},
        {"name": "Kmart", "domain": "kmart.com.au"},
        {"name": "Target", "domain": "target.com.au"},
        {"name": "Myer", "domain": "myer.com.au"},
        {"name": "David Jones", "domain": "davidjones.com.au"},
        {"name": "Harvey Norman", "domain": "harveynorman.com.au"},
        {"name": "Adairs", "domain": "adairs.com.au"},
        {"name": "Reject Shop", "domain": "rejectshop.com.au"},
        {"name": "Spotlight", "domain": "spotlight.com.au"},
        {"name": "Miniso", "domain": "miniso.com.au"},
    ],
    "USA": [
        {"name": "Target", "domain": "target.com"},
        {"name": "Walmart", "domain": "walmart.com"},
        {"name": "Costco", "domain": "costco.com"},
        {"name": "Bed Bath & Beyond", "domain": "bedbathandbeyond.com"},
        {"name": "HomeGoods", "domain": "homegoods.com"},
        {"name": "Michaels", "domain": "michaels.com"},
    ],
}


# ========== 需排除的客户类型 ==========


EXCLUDE_PATTERNS = [
    "wholesale distributor",
    "bulk supplier",
    "manufacturer only",
    "factory direct",
    "alibaba supplier",
    "1688.com",
    "made-in-china",
    "promotional products",
    "giveaway",
    "branded merchandise",
]


def _build_channel_queries(profile: Dict[str, Any], max_queries: int = 20) -> List[str]:
    """生成垂直目录/展会查询"""
    markets = [_to_english_market(str(m)) for m in profile.get("target_markets", [])]
    if not markets:
        markets = ["UK", "Australia"]

    queries = []
    for market in markets:
        queries.extend(CHANNEL_QUERIES.get(market, []))

    return queries[:max_queries]


def _build_seed_company_queries(
    profile: Dict[str, Any], max_queries: int = 30
) -> List[str]:
    """生成目标客户种子公司 site 查询"""
    markets = [_to_english_market(str(m)) for m in profile.get("target_markets", [])]
    if not markets:
        markets = ["UK", "Australia"]

    queries = []
    seen = set()

    for market in markets:
        retailers = TARGET_RETAILERS.get(market, [])
        for r in retailers[:8]:
            name = r["name"]
            domain = r["domain"]

            # 官网定向查询
            q1 = f'site:{domain} "{name}"'
            if q1 not in seen:
                seen.add(q1)
                queries.append(q1)

            # 礼品买手查询
            q2 = f"site:{domain} gift buyer"
            if q2 not in seen:
                seen.add(q2)
                queries.append(q2)

            # category buyer
            q3 = f'site:{domain} "category buyer"'
            if q3 not in seen:
                seen.add(q3)
                queries.append(q3)

            # product development
            q4 = f'site:{domain} "product development"'
            if q4 not in seen:
                seen.add(q4)
                queries.append(q4)

            # procurement
            q5 = f"site:{domain} procurement"
            if q5 not in seen:
                seen.add(q5)
                queries.append(q5)

            if len(queries) >= max_queries:
                break

    return queries[:max_queries]


def _build_retailer_verification_queries(
    profile: Dict[str, Any], max_queries: int = 20
) -> List[str]:
    """生成零售商验证查询"""
    markets = [_to_english_market(str(m)) for m in profile.get("target_markets", [])]
    if not markets:
        markets = ["UK", "Australia"]

    product = str(profile.get("product_category", "giftware"))
    product_parts = product.split()
    main_product = product_parts[0] if product_parts else "giftware"

    queries = []
    seen = set()

    for market in markets:
        retailers = TARGET_RETAILERS.get(market, [])

        for r in retailers[:5]:
            name = r["name"]
            domain = r["domain"]

            # 验证是零售商
            keywords = ["retailer", "store", "chain", "shop", "outlet"]
            for kw in keywords:
                q = f"{name} {kw} {market} {main_product}"
                if q not in seen:
                    seen.add(q)
                    queries.append(q)

        # 泛搜 + 类别确认
        for kw in ["gift buyer", "category buyer", "homeware buyer"]:
            q = f'"{kw}" {market} {main_product}'
            if q not in seen:
                seen.add(q)
                queries.append(q)

            if len(queries) >= max_queries:
                break

    return queries[:max_queries]


def build_lead_queries(profile: Dict[str, Any], max_queries: int = 50) -> List[str]:
    """构建完整查询列表 - 垂直目录/展会优先"""
    # 优先级1: 垂直目录/展会
    channel_queries = _build_channel_queries(
        profile, max_queries=max(10, max_queries // 3)
    )

    # 优先级2: 种子公司 site 查询
    seed_queries = _build_seed_company_queries(
        profile, max_queries=max(15, max_queries // 2)
    )

    # 优先级3: 零售商验证
    verify_queries = _build_retailer_verification_queries(
        profile, max_queries=max(10, max_queries // 3)
    )

    # 合并
    all_queries = channel_queries + seed_queries + verify_queries

    # 去重
    deduped = []
    seen = set()
    for q in all_queries:
        q_norm = " ".join(q.split()).strip()
        if q_norm and q_norm not in seen:
            deduped.append(q_norm)
            seen.add(q_norm)

    return deduped[:max_queries]


def _build_company_queries(
    companies: Dict[str, List[str]], max_queries: int = 12
) -> List[str]:
    """从目标公司生成 site:domain 查询 - 兼容旧接口"""
    queries = []
    domain_map = {
        "the range": "therange.co.uk",
        "dunelm": "dunelm.com",
        "next home": "next.co.uk",
        "big w": "bigw.com.au",
        "kmart": "kmart.com.au",
        "ashdene": "ashdene.com.au",
        "petsmart": "petsmart.com",
        "gopromotional": "gopromotional.co.uk",
        "puckator": "puckator.co.uk",
    }
    for country, companies_list in companies.items():
        for name in companies_list:
            key = name.lower().strip()
            domain = domain_map.get(key, "")
            if domain:
                queries.append(f'site:{domain} "{name}" gifts')
                queries.append(f'site:{domain} "{name}" supplier')
            else:
                queries.append(f'"{name}" official website')
                queries.append(f'"{name}" giftware retailer')
            if len(queries) >= max_queries:
                return queries[:max_queries]
    return queries


def _build_template_queries(
    profile: Dict[str, Any], max_queries: int = 16
) -> List[str]:
    """画像驱动查询 - 兼容旧接口"""
    return build_lead_queries(profile, max_queries)


def _build_broad_queries(profile: Dict[str, Any], max_queries: int = 30) -> List[str]:
    """宽泛市场查询 - 兼容旧接口"""
    return build_lead_queries(profile, max_queries)


PROMPT_TEMPLATE = """你是一个外贸获客专家。根据以下公司画像，生成精准的英文搜索词，用于寻找目标客户。

## 公司画像
- 公司名: {company_name}
- 产品类别: {product_category}
- 目标市场: {target_markets}
- 目标客户类型: {target_customer_types}
- 目标决策人: {target_decision_makers}
- 竞争优势: {competitive_advantages}
- 典型客户例子: {example_companies}

## 要求
"""


# 兼容旧接口
def generate_search_queries(
    profile: Dict[str, Any], max_queries: int = 30
) -> List[str]:
    """生成搜索查询 - 统一入口"""
    return build_lead_queries(profile, max_queries)
