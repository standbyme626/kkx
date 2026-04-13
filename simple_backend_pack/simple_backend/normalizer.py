"""
归一化模块 - 与 scorer 统一的 country 推断
"""

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


# 已知零售商映射
KNOWN_RETAILERS = {
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


def _infer_country_from_text(title: str, content: str, url: str) -> str:
    """推断国家 - 统一逻辑"""
    text = f"{title} {content} {url}".lower()
    domain = _extract_domain(url)

    # 域名后缀优先
    if domain.endswith(".co.uk") or domain.endswith(".uk"):
        return "UK"
    if domain.endswith(".com.au") or domain.endswith(".au"):
        return "AU"
    if domain.endswith(".com"):
        # 检查已知零售商
        for known, c in KNOWN_RETAILERS.items():
            if known in domain:
                return c

    # 页面文本
    if " united kingdom" in text or " uk " in text or " britain" in text:
        return "UK"
    if " australia" in text or " aussie" in text:
        return "AU"
    if " united states" in text or " usa " in text:
        return "US"

    return ""


def _infer_industry(title: str, content: str) -> str:
    """推断行业"""
    text = f"{title} {content}".lower()

    # 高优先级
    if "promotional" in text or "giveaway" in text or "branded merchandise" in text:
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


def _normalize_company_name(title: str, website: str) -> str:
    """规范化公司名"""
    # 从 title 提取
    if ":" in title:
        name = title.split(":")[0].strip()
        if len(name.split()) <= 4:
            return name
    if " - " in title:
        parts = [p.strip() for p in title.split(" - ") if p.strip()]
        for p in parts:
            if p.lower() not in {"official", "website", "about", "contact", "home"}:
                return p
        return parts[-1] if parts else "Unknown"
    return title.split("|")[0].strip() or "Unknown"


def _is_product_page(url: str, title: str) -> bool:
    """判断是否是产品/目录页面"""
    url_lower = url.lower()
    title_lower = title.lower()

    product_patterns = [
        "/product",
        "/products",
        "/collection",
        "/collections",
        "/shop",
        "/store",
        "/buy",
        "/category",
        "/catalog",
        "shop",
        "buy",
    ]

    for pattern in product_patterns:
        if pattern in url_lower or pattern in title_lower:
            return True

    return False


def _is_career_job_page(url: str, title: str, content: str) -> bool:
    """判断是否是招聘/job页面"""
    text = f"{url} {title} {content}".lower()

    job_patterns = [
        "/jobs",
        "/job",
        "/careers",
        "/career",
        "/hiring",
        "/vacancy",
        "apply now",
        "join our team",
    ]

    for pattern in job_patterns:
        if pattern in text:
            return True

    return False


def _is_store_locator(url: str) -> bool:
    """判断是否是门店 locator"""
    url_lower = url.lower()

    locator_patterns = [
        "/store-locator",
        "/stores",
        "/find-a-store",
        "/store-finder",
        "/locations",
    ]

    for pattern in locator_patterns:
        if pattern in url_lower:
            return True

    return False


def normalize_leads(
    results: List[Dict[str, Any]], max_leads: int = 20
) -> List[Dict[str, Any]]:
    """归一化客户信息 - 增强过滤"""

    normalized = []
    seen = set()

    for r in results:
        url = str(r.get("url") or "").strip()
        title = str(r.get("title") or "").strip()
        content = str(r.get("content") or "").strip()

        key = url or ""
        if not key or key in seen:
            continue
        seen.add(key)

        # 过滤产品/目录页面
        if _is_product_page(url, title):
            continue

        # 过滤 job/career 页面
        if _is_career_job_page(url, title, content):
            continue

        # 过滤 store locator
        if _is_store_locator(url):
            continue

        company_name = _normalize_company_name(title, url)
        country = r.get("country") or _infer_country_from_text(title, content, url)
        industry = r.get("industry") or _infer_industry(title, content)

        # 补充从 website 提取 country
        if not country:
            domain = _extract_domain(url)
            country = KNOWN_RETAILERS.get(domain, "")

        normalized.append(
            {
                "company_name": company_name,
                "website": url,
                "country": country,
                "industry": industry,
                "business_scope": content[:200] if content else "",
                "evidence_urls": [url] if url else [],
                "decision_makers": [],
                "decision_maker_titles": [],
                "contacts": [],
                "emails": [],
                "linkedin_urls": [],
            }
        )

        if len(normalized) >= max_leads:
            break

    return normalized
