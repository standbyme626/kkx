"""
归一化模块 - 带 page_type 分类与严格过滤
只允许真实公司实体页入池
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse


# ============================================================
# 页面类型识别
# ============================================================

# 展会/活动资源禁止词 - 这些页面绝对不能入 lead 表
EVENT_RESOURCE_KEYWORDS = [
    # 展会资源页
    "marketing kit",
    "marketing-kit",
    "exhibitor information",
    "exhibitor resources",
    "exhibitor manual",
    "exhibitor portal",
    # 展会主办方页面
    "why exhibit",
    "why-exhibit",
    "become an exhibitor",
    "book a stand",
    "exhibition space",
    "exhibitor enquiry",
    "exhibitor registration",
    "exhibitor login",
    "exhibiting 101",
    "steps to success",
    # 展会行业/类别页
    "show sector",
    "sector guide",
    "product category",
    "show features",
    "event highlights",
    "what's on show",
    # 展会新闻/博客
    "press release",
    "news release",
    "event news",
    "show blog",
    "event feature",
    "show highlights",
    # 展会联系页
    "event contact",
    "show contact",
    "general enquiry",
    "event organiser",
    # 其他
    "business builder",
    "stand awards",
    "getting there",
    "event guide",
    "retail therapy",
]

# 目录根页特征词
DIRECTORY_ROOT_KEYWORDS = [
    "exhibitor directory",
    "exhibitor list",
    "full exhibitor list",
    "brand directory",
    "complete list of",
    "see all exhibitors",
    "browse exhibitors",
    "all exhibitors",
    "exhibitors a-z",
]

# 允许入池的页面类型
# 只有 company_detail, exhibitor_detail, brand_profile, company_site 允许进入
ALLOWED_PAGE_TYPES = {
    "company_detail",
    "exhibitor_detail",
    "brand_profile",
    "company_site",
}


def _extract_domain(url: str) -> str:
    """提取域名"""
    try:
        netloc = urlparse(url).netloc.lower().strip()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


# 展会域名列表 - 用于特殊处理
EXHIBITION_DOMAINS = {
    "autumnfair.com",
    "springfair.com",
    "reedgiftfairs.com.au",
    "homeandgift.com",
    "homecollective.com",
    "nynow.com",
    "asdshow.com",
    "topdrawer.com",
    "giftwareassociation.org",
}


def classify_page(url: str, title: str, content: str) -> str:
    """页面类型分类

    Returns:
        page_type: company_detail | exhibitor_detail | brand_profile | company_site |
                   directory_root | event_resource | sector_page | blog_news | generic_event_contact | unknown
    """
    url_lower = (url or "").lower()
    title_lower = (title or "").lower()
    content_lower = (content or "").lower()
    blob = f"{title_lower} {content_lower}"
    domain = _extract_domain(url)

    # --- 第一步：检查是否是目录根页 ---
    for kw in DIRECTORY_ROOT_KEYWORDS:
        if kw.lower() in blob or kw.lower() in url_lower:
            return "directory_root"

    # URL 路径特征：如果路径只有 /exhibitors 或 /exhibitor-list 且内容很短
    if any(p in url_lower for p in ["/exhibitors", "/exhibitor-list", "/brand-directory"]):
        path_depth = url_lower.count("/")
        if path_depth <= 3 and len(content or "") < 500:
            return "directory_root"

    # --- 第二步：检查是否是展会资源页 ---
    for kw in EVENT_RESOURCE_KEYWORDS:
        if kw.lower() in blob or kw.lower() in url_lower:
            return "event_resource"

    # --- 第三步：检查域名是否是展会域名 ---
    is_exhibition_domain = any(d in domain for d in EXHIBITION_DOMAINS)

    if is_exhibition_domain:
        # 展会域名下，需要进一步判断是 exhibitor detail 页还是资源页
        # 关键：检查是否有公司名/品牌名/展位号等 exhibitor detail 特征

        # exhibitor detail 页通常包含：
        # - "Stand:" / "Booth:" / "Company:" / "Brand:" / "Overview" / "Products"
        # - 具体的产品描述
        # - 公司地址/联系方式

        has_exhibitor_detail_signals = any(kw in blob for kw in [
            "stand:", "booth:", "hall:",
            "overview", "products", "product range",
            "company:", "brand:", "about us",
            "contact us", "enquiry",
            "established", "founded",
            "specialis", "manufacturer", "supplier",
        ])

        # 有具体的产品列表或公司描述
        has_company_content = (
            len(content or "") > 300
            and any(kw in blob for kw in [
                "product", "range", "collection", "brand",
                "company", "specialis", "manufacture", "design",
                "quality", "since", "year",
            ])
        )

        if has_exhibitor_detail_signals or has_company_content:
            return "exhibitor_detail"
        else:
            # 展会域名下但不符合 detail 特征 → 资源页
            return "event_resource"

    # --- 第四步：检查博客/新闻 ---
    if any(p in url_lower for p in ["/blog/", "/news/", "/press/", "/article", "/feature/"]):
        return "blog_news"

    # --- 第五步：检查公司详情页信号 ---
    # 先排除文章/博客/列表页特征
    article_signals = [
        "best independent", "best ", "top ", "list of",
        "stores reveal", "big spenders", "review of",
        "nik nak", "niknak", "shops uk (for",
        # URL 路径中的文章特征
        "/blog/", "/news/", "/article/", "/feature/",
    ]
    # URL 路径直接判断
    if any(p in url_lower for p in ["/blog/", "/news/", "/article/", "/feature/"]):
        return "blog_news"
    # 标题/内容判断
    is_article = any(kw in blob for kw in article_signals)
    if is_article:
        return "blog_news"

    has_about = any(kw in blob for kw in [
        "about us", "about our company", "about our",
        "our story", "our brand", "our team",
    ])
    has_company_words = any(kw in blob for kw in [
        "our company", "our brand", "established", "headquartered",
        "founded in", "since ", "specialis in",
    ])
    has_retail = any(kw in blob for kw in [
        "online store", "shop now", "free delivery",
        "our collections", "our ranges", "add to cart",
    ])
    has_product_info = any(kw in blob for kw in [
        "our products", "product range", "collections",
        "catalogue", "product categories",
    ])

    if has_about or has_company_words or has_retail or has_product_info:
        # 进一步区分
        if "/exhibitor" in url_lower:
            return "exhibitor_detail"
        if "brand" in blob or "brand profile" in blob:
            return "brand_profile"
        if has_retail or "online store" in blob:
            return "company_site"
        return "company_detail"

    # --- 第六步：品牌/公司官网信号 ---
    # 检查页面标题是否像公司官网
    if any(kw in title_lower for kw in [
        "official", "official website",
        " | ", " - ",  # 公司名 | 描述 格式
    ]):
        # 确保不是资源页
        if not any(kw.lower() in blob for kw in EVENT_RESOURCE_KEYWORDS):
            return "company_site"

    return "unknown"


def _should_accept_page(page_type: str, url: str, title: str, content: str) -> bool:
    """判断是否允许入池

    只允许 company_detail, exhibitor_detail, brand_profile, company_site
    """
    if page_type not in ALLOWED_PAGE_TYPES:
        return False

    # 二次检查：即使分类通过了，再检查硬特征
    blob = f"{title} {content}".lower()

    # 绝对禁止的硬关键词
    hard_block = [
        "marketing kit", "marketing-kit",
        "exhibitor directory", "exhibitor list",
        "full exhibitor list", "brand directory",
        "browse exhibitors", "see all exhibitors",
        "why exhibit", "why-exhibit",
        "become an exhibitor", "book a stand",
        "show sector",
        "exhibitor resources", "exhibitor portal",
        "exhibitor registration", "exhibitor manual",
        "business builder", "stand awards",
        "getting there", "event guide", "retail therapy",
        "exhibiting 101", "steps to success",
    ]
    for kw in hard_block:
        if kw.lower() in blob:
            return False

    # 公司名不能是这些假名称
    fake_names = [
        "exhibitor directory", "marketing kit", "why exhibit",
        "show sector", "exhibitor resources", "business builder",
        "unknown",
    ]
    title_first_part = title.split("|")[0].split("-")[0].strip().lower()
    if title_first_part in fake_names:
        return False

    # Marketplace / 电商平台域名 - 不作为客户公司
    marketplace_domains = [
        "etsy.com", "ebay.co.uk", "ebay.com", "amazon.co.uk",
        "amazon.com", "pinterest.com", "issuu.com", "europages.co.uk",
    ]
    domain = _extract_domain(url)
    for mp in marketplace_domains:
        if mp in domain:
            return False

    return True


# ============================================================
# 国家推断
# ============================================================

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

# 国家关键词 - 从页面内容提取
COUNTRY_KEYWORDS = {
    "UK": [
        "united kingdom", " england", " scotland", " wales",
        " great britain", "london, uk", "manchester, uk",
        "birmingham, uk", "liverpool, uk", ", uk", " uk ",
        "britain", "uk registered", "registered in england",
        "vat gb",
    ],
    "AU": [
        " australia", " melbourne", " sydney", "brisbane",
        "perth, au", "adelaide", "australian", ", australia",
        "victoria, australia", "nsw, australia", "abn ",
    ],
    "US": [
        " united states", " usa ", " new york, ny",
        " los angeles", "chicago, il", "american",
        "houston, tx", ", usa", "inc.", "llc",
    ],
}


def _infer_country(title: str, content: str, url: str) -> str:
    """推断国家 - 从页面内容提取，不从域名硬猜

    优先顺序：
    1. 已知零售商映射
    2. 页面正文中的国家关键词
    3. URL 中的国家线索
    """
    domain = _extract_domain(url)
    text = f"{title} {content}".lower()
    url_lower = (url or "").lower()

    # 1. 已知零售商映射优先
    for known, country in KNOWN_RETAILERS.items():
        if known in domain:
            return country

    # 2. 从页面内容提取国家（不从 TLD 硬猜）
    for country, keywords in COUNTRY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return country

    # 3. URL 中的国家线索（谨慎使用）
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
    """规范化公司名

    禁止使用 "Exhibitor Directory""Marketing Kit""Why Exhibit" 等作为公司名
    """
    # 假名称列表
    fake_names = {
        "exhibitor directory", "marketing kit", "why exhibit",
        "show sector", "exhibitor resources", "business builder",
        "exhibitor resource", "steps to success", "exhibitor list",
        "brand directory", "unknown",
        # 页面标题不是公司名
        "about us", "about", "contact us", "contact", "home",
        "our story", "our team", "our brand", "our products",
        "welcome", "homepage", "official website", "welcome to",
        # 展会通用标题不是公司名
        "exhibitor details", "exhibitor profile", "exhibitor info",
        "sydney exhibitor details", "melbourne exhibitor details",
    }

    # 提取标题的第一部分
    if ":" in title:
        name = title.split(":")[0].strip()
        if 2 <= len(name.split()) <= 5:
            if name.lower() not in fake_names:
                return name

    if " - " in title:
        parts = [p.strip() for p in title.split(" - ") if p.strip()]
        for p in parts:
            if p.lower() not in {"official", "website", "about", "contact", "home"}:
                if p.lower() not in fake_names:
                    return p
        # 如果所有部分都是假的，取最后一部分
        return parts[-1] if parts and parts[-1].lower() not in fake_names else "Unknown"

    if "|" in title:
        name = title.split("|")[0].strip()
        if name.lower() not in fake_names:
            return name

    # 如果提取的名称是假的，尝试从 URL 提取
    if website:
        domain = _extract_domain(website)
        # 去掉 TLD 和 www
        parts = domain.replace("www.", "").split(".")
        if parts and parts[0].lower() not in fake_names and len(parts[0]) > 2:
            return parts[0].capitalize()

    name = title.split("|")[0].split("-")[0].strip()
    if name.lower() in fake_names:
        return "Unknown"
    return name if name else "Unknown"


def normalize_leads(
    results: List[Dict[str, Any]], max_leads: int = 20
) -> List[Dict[str, Any]]:
    """归一化客户信息 - 带 page_type 过滤"""

    normalized = []
    seen = set()
    dropped_by_type = {}
    total_dropped = 0

    for r in results:
        url = str(r.get("url") or "").strip()
        title = str(r.get("title") or "").strip()
        content = str(r.get("content") or "").strip()

        key = url or ""
        if not key or key in seen:
            continue
        seen.add(key)

        # 页面类型分类
        page_type = classify_page(url, title, content)

        # 严格过滤
        if not _should_accept_page(page_type, url, title, content):
            dropped_by_type[page_type] = dropped_by_type.get(page_type, 0) + 1
            total_dropped += 1
            continue

        company_name = _normalize_company_name(title, url)

        # 如果公司名是假的，丢弃
        fake_names = {
            "exhibitor directory", "marketing kit", "why exhibit",
            "show sector", "exhibitor resources", "business builder",
            "exhibitor resource", "steps to success", "unknown",
            "about us", "about", "contact us", "contact", "home",
            "our story", "our team", "our brand", "our products",
            "welcome", "homepage", "official website", "welcome to",
            "exhibitor details", "exhibitor profile", "exhibitor info",
        }
        if company_name.lower() in fake_names:
            dropped_by_type["fake_company_name"] = dropped_by_type.get("fake_company_name", 0) + 1
            total_dropped += 1
            continue

        country = _infer_country(title, content, url)
        industry = _infer_industry(title, content)

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
                "page_type": page_type,
            }
        )

        if len(normalized) >= max_leads:
            break

    print(f"[归一化] 输入 {len(results)} 条, 通过 {len(normalized)} 条, 过滤 {total_dropped} 条")
    print(f"[归一化] 过滤分布: {dict(dropped_by_type)}")
    return normalized
