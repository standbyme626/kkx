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
# 排除批发商关键词
EXCLUDE_RETAIL_KEYWORDS = [
    "wholesale",
    "distributor",
    "supplier",
    "bulk",
    "wholesaler",
    "distribution",
    "b2b",
    "trade only",
    "manufacturer",
    "factory",
    "china supplier",
]
# 确认零售商关键词
RETAIL_CONFIRM_KEYWORDS = [
    "shop",
    "store",
    "retailer",
    "boutique",
    "department store",
    "chain store",
    "ecommerce",
]
BLOCKED_URL_KEYWORDS = {"/jobs", "/job/", "careers", "salary", "recruitment"}
LOW_SIGNAL_KEYWORDS = {
    "trend",
    "insight",
    "blog",
    "news",
    "directory",
    "yelp",
    "wedding",
}
BUSINESS_SIGNAL_KEYWORDS = {
    "gift",
    "giftware",
    "homeware",
    "retail",
    "wholesale",
    "promotional",
    "distributor",
    "supplier",
}


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

    if any(d in domain for d in BLOCKED_DOMAINS):
        return True
    if any(k in lower_url for k in BLOCKED_URL_KEYWORDS):
        return True
    if any(k in blob for k in [" job ", "jobs", "hiring", "resume", "internship"]):
        return True

    # 过滤批发商
    if any(k in blob for k in EXCLUDE_RETAIL_KEYWORDS):
        return True

    return False


def is_retail_candidate(result: Dict[str, Any]) -> bool:
    """判断是否是零售商候选"""
    title = str(result.get("title") or "")
    content = str(result.get("content") or "")
    blob = (title + " " + content).lower()

    # 有确认关键词
    if any(k in blob for k in RETAIL_CONFIRM_KEYWORDS):
        return True
    # 无批发商关键词
    if not any(k in blob for k in EXCLUDE_RETAIL_KEYWORDS):
        return True
    return False


def _infer_country(title: str, content: str, url: str) -> str:
    """推断国家"""
    text = f"{title} {content} {url}".lower()
    domain = _extract_domain(url)

    if domain.endswith(".co.uk") or domain.endswith(".uk"):
        return "UK"
    if domain.endswith(".com.au") or domain.endswith(".au"):
        return "AU"
    if domain.endswith(".com") and "us" in text:
        return "US"
    if (
        " united kingdom" in text
        or " uk " in text
        or "britain" in text
        or "england" in text
    ):
        return "UK"
    if " australia" in text or " aussie" in text:
        return "AU"
    if " united states" in text or " usa " in text:
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
    for keyword in BUSINESS_SIGNAL_KEYWORDS:
        if keyword in blob:
            score += 0.6

    # 低信号
    for keyword in LOW_SIGNAL_KEYWORDS:
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
                results = await search.search(query, limit=result_per_query)
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

    return cleaned
