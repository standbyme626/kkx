import asyncio
import re
from typing import Dict, Any, List
from urllib.parse import urlparse


def _extract_domain(url: str) -> str:
    """提取域名"""
    try:
        netloc = urlparse(url).netloc.lower().strip()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


BLOCKED_DOMAINS = {
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "monster.com",
}

# Marketplace / 电商平台 - 不把这些当客户公司
BLOCKED_MARKETPLACES = [
    "etsy.com",
    "ebay.co.uk",
    "ebay.com",
    "amazon.co.uk",
    "amazon.com",
    "pinterest.com",
    "pinterest.co.uk",
    "issuu.com",
    "europages.co.uk",
    "faire.com",
    "alibaba.com",
    "aliexpress.com",
    "dhgate.com",
    "made-in-china.com",
    "global sources.com",
]

# 负向关键词 - 禁止这些页面进入最终 lead
# 严格按照 1.md 最终版
# 注意：不用单个 "exhibit"（会误杀 exhibitor detail 页）
NEGATIVE_KEYWORDS = [
    # 展会资源页
    "marketing kit",
    "exhibiting 101",
    "why exhibit",
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
    "browse exhibitors",
    "see all exhibitors",
    "full exhibitor list",
    "complete list of",
    # 新闻/博客
    "press release",
    "event news",
    "show blog",
    # 其他
    "faq",
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


def _should_drop_result(result: Dict[str, Any]) -> bool:
    """判断是否应该丢弃搜索结果"""
    url = str(result.get("url") or "").strip()
    title = str(result.get("title") or "")
    content = str(result.get("content") or "")

    if not url:
        return True

    domain = _extract_domain(url)
    lower_url = url.lower()
    blob = f"{title} {content} {url}".lower()

    # 已知禁止域名
    if any(d in domain for d in BLOCKED_DOMAINS):
        return True

    # Marketplace / 电商平台
    for mp in BLOCKED_MARKETPLACES:
        if mp in domain:
            return True

    # 禁止 URL 模式
    blocked_url_kw = ["/jobs", "/job/", "careers", "salary", "recruitment"]
    if any(k in lower_url for k in blocked_url_kw):
        return True

    # 招聘页面
    if any(k in blob for k in [" job ", "jobs", "hiring", "resume", "internship"]):
        return True

    # 负向关键词过滤
    for kw in NEGATIVE_KEYWORDS:
        if kw.lower() in blob:
            return True

    return False


def _infer_country(title: str, content: str, url: str) -> str:
    """推断国家 - 从页面内容提取，不从域名硬猜

    优先从页面正文、地址、公司简介、展商资料中提取国家。
    不要从站点主域名硬猜国家。
    """
    text = f"{title} {content}".lower()
    url_lower = (url or "").lower()

    # 已知零售商映射（仅用于确认，不是主逻辑）
    known_retailers = {
        "therange.co.uk": "UK",
        "dunelm.com": "UK",
        "next.co.uk": "UK",
        "johnlewis.com": "UK",
        "marksandspencer.com": "UK",
        "fenwick.com": "UK",
        "homesense.co.uk": "UK",
        "hobbycraft.co.uk": "UK",
        "argos.co.uk": "UK",
        "very.co.uk": "UK",
        "bigw.com.au": "AU",
        "kmart.com.au": "AU",
        "target.com.au": "AU",
        "myer.com.au": "AU",
        "davidjones.com.au": "AU",
        "harveynorman.com.au": "AU",
        "adairs.com.au": "AU",
        "rejectshop.com.au": "AU",
        "spotlight.com.au": "AU",
    }
    domain = _extract_domain(url)
    for known, country in known_retailers.items():
        if known in domain:
            return country

    # 从页面内容提取国家 - 使用明确的地理标识
    # UK 标识
    uk_patterns = [
        "united kingdom", " england", " scotland", " wales",
        " great britain", "london, uk", "manchester, uk",
        "birmingham, uk", "liverpool, uk", "leeds, uk",
        ", uk", " uk ", "britain", "england,", "scotland,",
        "uk registered", "uk company", "registered in england",
        "vat gb", "company number england",
    ]
    for pattern in uk_patterns:
        if pattern.lower() in text:
            return "UK"

    # AU 标识
    au_patterns = [
        " australia", " melbourne", " sydney", "brisbane",
        "perth, au", "adelaide", "australian", "australia ",
        ", australia", "victoria, australia", "nsw, australia",
        "abn ", "acn ", "gst registered australia",
    ]
    for pattern in au_patterns:
        if pattern.lower() in text:
            return "AU"

    # US 标识
    us_patterns = [
        " united states", " usa ", " new york, ny",
        " los angeles", "chicago, il", "american",
        "houston, tx", ", usa", " usa,", "inc.", "llc",
        "delaware corporation", "registered in delaware",
    ]
    for pattern in us_patterns:
        if pattern.lower() in text:
            return "US"

    # URL 中的国家线索（谨慎使用，仅作为最后手段）
    if "/uk/" in url_lower or "/united-kingdom/" in url_lower:
        return "UK"
    if "/au/" in url_lower or "/australia/" in url_lower:
        return "AU"
    if "/us/" in url_lower or "/united-states/" in url_lower:
        return "US"

    return ""


def _infer_industry(title: str, content: str) -> str:
    """推断行业"""
    text = f"{title} {content}".lower()
    if "promotional" in text:
        return "Promotional"
    if "wholesale" in text or "distributor" in text:
        return "Wholesale"
    if "retail" in text or "department store" in text or "homeware" in text:
        return "Retail"
    if "e-commerce" in text or "amazon" in text or "etsy" in text or "shopify" in text:
        return "E-commerce"
    if "gift" in text:
        return "Giftware"
    return ""


def _pre_score_result(
    result: Dict[str, Any], profile: Dict[str, Any], seed_companies: List[str]
) -> float:
    """预排序分数"""
    title = str(result.get("title") or "")
    content = str(result.get("content") or "")
    url = str(result.get("url") or "")
    blob = f"{title} {content} {url}".lower()

    score = 0.0

    # 市场匹配
    target_markets = {
        _to_english_market(str(m)).lower()
        for m in (profile.get("target_markets") or [])
    }
    country = _infer_country(title, content, url)
    if "uk" in target_markets and country == "UK":
        score += 3.0
    if "australia" in target_markets and country == "AU":
        score += 3.0
    if ("usa" in target_markets or "us" in target_markets) and country == "US":
        score += 1.0

    # 业务信号
    business_signals = ["gift", "giftware", "homeware", "retail", "home decor", "tabletop"]
    for keyword in business_signals:
        if keyword in blob:
            score += 0.6

    # 低信号
    low_signals = ["trend", "insight", "blog", "news", "directory", "yelp"]
    for keyword in low_signals:
        if keyword in blob:
            score -= 0.8

    # 种子公司匹配
    for name in seed_companies:
        if name.lower() in blob:
            score += 4.0
            break

    # 官网权重
    parsed = urlparse(url)
    if parsed.path in {"", "/"}:
        score += 0.5

    return round(score, 2)


def _to_english_market(label: str) -> str:
    """转换市场标签"""
    src = (label or "").strip().lower()
    mapping = {
        "uk": "UK",
        "united kingdom": "UK",
        "australia": "Australia",
        "usa": "USA",
    }
    for k, v in mapping.items():
        if k in src:
            return v
    return label.upper() if label else ""


async def search_leads(
    queries: List[str],
    profile: Dict[str, Any],
    concurrency: int = 6,
    result_per_query: int = 5,
    max_results: int = 30,
) -> List[Dict[str, Any]]:
    """搜索客户（核心函数）

    Args:
        queries: 搜索词列表
        profile: 公司画像
        concurrency: 并发数
        result_per_query: 每词返回结果数
        max_results: 最大结果数

    Returns:
        候选客户列表
    """
    from app.providers.search import create_search_provider

    search = create_search_provider(use_mock_if_env_missing=False)
    sem = asyncio.Semaphore(concurrency)

    async def _search_one(query: str) -> Dict[str, Any]:
        try:
            async with sem:
                # Serper 支持国家/语言参数，这里默认英文
                # 如果 query 中已包含国家词（UK/Australia），Serper 的 gl/hl 参数会辅助定位
                results = await search.search(query, limit=result_per_query, language="en")
            return {"query": query, "results": results, "error": ""}
        except Exception as e:
            return {"query": query, "results": [], "error": str(e)}

    # 并行搜索
    outcomes = await asyncio.gather(
        *[_search_one(q) for q in queries], return_exceptions=True
    )

    # 收集结果
    all_results = []
    for outcome in outcomes:
        if isinstance(outcome, Exception):
            continue
        for r in outcome.get("results", []):
            if isinstance(r, dict):
                r["search_query"] = outcome.get("query", "")
                all_results.append(r)

    # 过滤 + 去重
    merged = {}
    dropped = 0
    print(f"[搜索] 原始结果 {len(all_results)} 条")
    for result in all_results:
        if _should_drop_result(result):
            dropped += 1
            continue

        url = str(result.get("url") or "").strip().lower()
        if not url:
            dropped += 1
            continue

        if url not in merged:
            merged[url] = result
        else:
            # 保留信息更丰富的
            existing = merged[url]
            if len(str(result.get("content") or "")) > len(
                str(existing.get("content") or "")
            ):
                merged[url] = result

    # 预排序
    seed_companies = []
    for companies in profile.get("example_target_companies", {}).values():
        seed_companies.extend(companies)

    ranked = list(merged.values())
    for r in ranked:
        r["_pre_score"] = _pre_score_result(r, profile, seed_companies)
        if not r.get("country"):
            r["country"] = _infer_country(
                r.get("title", ""), r.get("content", ""), r.get("url", "")
            )

    ranked.sort(key=lambda x: x.get("_pre_score", 0), reverse=True)

    # 清理内部字段
    cleaned = []
    for r in ranked[:max_results]:
        cleaned.append({k: v for k, v in r.items() if not str(k).startswith("_")})

    print(f"[搜索] 过滤后去重: {len(merged)} 条, 丢弃: {dropped} 条, 返回: {len(cleaned)} 条")
    return cleaned
