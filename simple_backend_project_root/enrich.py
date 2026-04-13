"""
A/B 级客户二次搜索联系人
只对已确认的真实公司名做搜索，不再乱拼 /contact
只记录真实存在的联系方式线索
"""

import re
import asyncio
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


def _canonical_company_name(lead: Dict[str, Any]) -> str:
    """规范化公司名"""
    raw = str(lead.get("company_name") or "").strip()
    # 禁止的假名称
    fake_names = {
        "exhibitor directory", "marketing kit", "why exhibit",
        "show sector", "exhibitor resources", "business builder",
        "exhibitor resource", "steps to success", "unknown",
    }
    if raw.lower() in fake_names:
        return ""
    if ":" in raw:
        return raw.split(":")[0].strip()
    if " - " in raw:
        parts = [p.strip() for p in raw.split(" - ") if p.strip()]
        return parts[-1]
    return raw


# 二次搜索查询模板 - 英文
CONTACT_ROLES = [
    "Category Buyer",
    "Buyer",
    "Product Development Manager",
    "Sourcing Manager",
    "Procurement Manager",
    "Purchasing Manager",
    "Merchandise Manager",
    "Head of Buying",
    "Gift Buyer",
    "Home Buyer",
]


def _build_contact_queries(
    lead: Dict[str, Any], profile: Dict[str, Any], max_queries: int = 12
) -> List[str]:
    """二次搜索查询 - 只对真实公司名搜索，不再自动拼接 /contact

    查询分类：
    1. 官网 / 联系页类
    2. LinkedIn / 人名类
    3. 邮箱 / 电话类
    """
    company = _canonical_company_name(lead)
    if not company:
        return []

    website = str(lead.get("website") or "").strip()
    domain = _extract_domain(website)

    queries: List[str] = []

    # 1. 官网 / 联系页类
    contact_website = [
        f'"{company}" contact',
        f'"{company}" contact us',
        f'"{company}" about us',
        f'"{company}" team',
        f'"{company}" buyers',
        f'"{company}" wholesale contact',
    ]
    queries.extend(contact_website)

    # 2. LinkedIn / 人名类
    contact_linkedin = [
        f'"{company}" linkedin',
        f'"{company}" buyer linkedin',
        f'"{company}" category manager linkedin',
        f'"{company}" purchasing manager linkedin',
        f'"{company}" product manager linkedin',
    ]
    queries.extend(contact_linkedin)

    # 3. 邮箱 / 电话类
    contact_email = [
        f'"{company}" email',
        f'"{company}" buyer email',
        f'"{company}" wholesale email',
        f'"{company}" phone',
        f'"{company}" head office phone',
    ]
    queries.extend(contact_email)

    # 4. 如果有官网域名，优先站内搜索
    if domain:
        site_queries = [
            f'site:{domain} buyer',
            f'site:{domain} "about us"',
            f'site:{domain} contact',
            f'site:{domain} team',
        ]
        # 插入到最前面，优先级最高
        queries = site_queries + queries

    # 去重
    deduped = []
    seen = set()
    for q in queries:
        q = " ".join(q.split()).strip()
        if q and q not in seen:
            deduped.append(q)
            seen.add(q)

    return deduped[:max_queries]


def _extract_emails(text: str) -> List[str]:
    """提取邮箱"""
    emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    return list(set(e.lower() for e in emails))


def _extract_linkedin(text: str) -> List[str]:
    """提取 LinkedIn URL"""
    urls = re.findall(r"https?://[^\s)\]>\"']+", text)
    return [u for u in urls if "linkedin.com" in u.lower() and "/in/" in u.lower()]


def _extract_name_from_linkedin(url: str) -> str:
    """从 LinkedIn URL 提取姓名"""
    try:
        path = urlparse(url).path
        if "/in/" not in path.lower():
            return ""
        slug = path.split("/in/", 1)[1].strip("/").split("/")[0]
        slug = re.sub(r"[^a-zA-Z\- ]+", " ", slug)
        parts = [p.capitalize() for p in slug.split() if p and len(p) >= 2]
        return " ".join(parts[:2])
    except Exception:
        return ""


def _is_valid_person_name(name: str) -> bool:
    """判断是否有效人名"""
    if not name or len(name.split()) < 2:
        return False
    stops = {"official", "website", "contact", "about", "buyer", "manager", "team"}
    return not any(s in name.lower() for s in stops)


def _extract_names_from_text(text: str, names: List, titles: List):
    """从搜索文本提取人名和职位

    只提取真实出现的角色名，不伪造
    """
    # 模式: "John Smith - Buyer" 或 "Buyer: John Smith"
    patterns = [
        r"([A-Z][a-z]+ [A-Z][a-z]+)\s*[-–]\s*(\w+\s*\w*)",
        r"(\w+\s*\w*):\s*([A-Z][a-z]+ [A-Z][a-z]+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            parts = match.groups()
            if len(parts) == 2:
                name, title = parts
                if _is_valid_person_name(name.strip()):
                    title_lower = title.lower().strip()
                    # 只接受真实的角色
                    if any(
                        r in title_lower
                        for r in ["buyer", "manager", "sourcing", "procurement", "head",
                                 "director", "owner", "founder", "ceo", "president"]
                    ):
                        if name.strip() not in names:
                            names.append(name.strip())
                            titles.append(title.strip()[:30])


EMAIL_RE = None
PHONE_RE = None


def _get_email_re():
    global EMAIL_RE
    if EMAIL_RE is None:
        import re
        EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    return EMAIL_RE


def _get_phone_re():
    global PHONE_RE
    if PHONE_RE is None:
        import re
        PHONE_RE = re.compile(r"(\+?\d[\d\-\s\(\)]{7,}\d)")
    return PHONE_RE


def _extract_phones(text: str) -> List[str]:
    candidates = []
    for m in _get_phone_re().findall(text or ""):
        cleaned = " ".join(m.split())
        if len(re.sub(r"\D", "", cleaned)) >= 8:
            candidates.append(cleaned)
    return list(set(candidates))


def _rank_contact_name(name: str, title: str) -> int:
    """联系人排序 - 只有页面里出现真实角色时才填"""
    t = (title or "").lower()
    if "category buyer" in t:
        return 100
    if "product development" in t:
        return 90
    if "procurement" in t or "sourcing" in t:
        return 80
    if "buyer" in t:
        return 70
    if "owner" in t or "founder" in t:
        return 60
    return 10


def _is_real_contact_page(url: str, title: str, content: str) -> bool:
    """判断是否是真实的联系方式页面

    只允许来自：
    - 官网 contact 页
    - 官网 about/team 页
    - 真实 LinkedIn 公司页 / 人员页
    - 真实 email / phone 抽取结果

    不再自动拼接 /contact
    """
    url_lower = (url or "").lower()
    title_lower = (title or "").lower()
    content_lower = (content or "").lower()
    blob = f"{title_lower} {content_lower}"

    # LinkedIn 个人页 - 真实
    if "linkedin.com/in/" in url_lower:
        return True

    # LinkedIn 公司页 - 真实
    if "linkedin.com/company/" in url_lower:
        return True

    # 官网 contact/about/team 页
    if any(p in url_lower for p in ["/contact", "/contact-us", "/about", "/team", "/about-us"]):
        # 确保页面有实际内容
        if len(content or "") > 100:
            return True

    # 搜索结果中包含邮箱或电话
    email_found = bool(re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", blob))
    phone_found = bool(_get_phone_re().findall(blob))
    if email_found or phone_found:
        return True

    # 搜索结果中明确提到 buyer/contact/manager 角色
    role_signals = [
        "category buyer", "buyer", "procurement", "sourcing",
        "purchasing manager", "head of buying", "merchandise manager",
        "product development", "contact person", "key contact",
    ]
    for signal in role_signals:
        if signal in blob:
            return True

    return False


async def enrich_contacts(
    leads: List[Dict[str, Any]],
    profile: Dict[str, Any],
    concurrency: int = 3,
    max_queries_per_lead: int = 12,
    max_leads: int = 5,
) -> List[Dict[str, Any]]:
    """二次搜索联系人

    - 关闭 mock，只用真实搜索
    - 电话抽取
    - 联系人排序
    - 只记录真实联系方式，不再拼假链接
    """
    from app.providers.search import create_search_provider

    search = create_search_provider(use_mock_if_env_missing=False)
    sem = asyncio.Semaphore(concurrency)

    async def _search_contact(query: str) -> List[Dict]:
        try:
            async with sem:
                return await search.search(query, limit=3, language="en")
        except Exception:
            return []

    async def _enrich_one(lead: Dict[str, Any]) -> Dict[str, Any]:
        company = _canonical_company_name(lead)
        if not company:
            # 假公司名，跳过
            result = dict(lead)
            result["contacts"] = []
            result["decision_makers"] = []
            result["decision_maker_titles"] = []
            result["emails"] = []
            result["phones"] = []
            result["linkedin_urls"] = []
            result["secondary_search_ran"] = False
            result["second_search_status"] = "无效公司名，跳过"
            return result

        domain = _extract_domain(str(lead.get("website", "")))
        queries = _build_contact_queries(
            lead, profile, max_queries=max_queries_per_lead
        )

        all_emails, all_phones = [], []
        all_linkedin = []
        all_decision_makers, all_titles = [], []
        query_hits = []
        has_real_contact_page = False

        for query in queries:
            try:
                results = await _search_contact(query)
            except Exception:
                continue

            for r in results:
                title = str(r.get("title", ""))
                content = str(r.get("content", ""))
                url = str(r.get("url", ""))
                text = f"{title} {content} {url}"

                # 判断是否是真实的联系页面
                if _is_real_contact_page(url, title, content):
                    has_real_contact_page = True

                    # 域名优先：保留官网相关命中
                    if domain and domain in url:
                        query_hits.append({"query": query, "url": url, "title": title})

                    # 提取邮箱
                    for e in _get_email_re().findall(text):
                        if e not in all_emails:
                            all_emails.append(e)

                    # 提取电话
                    for p in _extract_phones(text):
                        if p not in all_phones:
                            all_phones.append(p)

                    # 提取 LinkedIn
                    for li in _extract_linkedin(text):
                        if li not in all_linkedin:
                            all_linkedin.append(li)

                    # 提取人名和职位
                    _extract_names_from_text(text, all_decision_makers, all_titles)

        # 联系人排序
        contacts = []
        for idx, name in enumerate(all_decision_makers):
            title = all_titles[idx] if idx < len(all_titles) else ""
            contacts.append(
                {
                    "name": name,
                    "title": title,
                    "rank": _rank_contact_name(name, title),
                }
            )

        contacts.sort(key=lambda x: x["rank"], reverse=True)
        best = contacts[0] if contacts else {}

        result = dict(lead)
        result["contacts"] = contacts
        result["decision_maker"] = best.get("name", "")
        result["decision_makers"] = [c["name"] for c in contacts[:3]] if contacts else []
        result["decision_maker_titles"] = [c["title"] for c in contacts[:3]] if contacts else []
        result["job_title"] = best.get("title", "")
        result["emails"] = all_emails
        result["email"] = all_emails[0] if all_emails else ""
        result["phones"] = all_phones
        result["phone"] = all_phones[0] if all_phones else ""
        result["linkedin_profiles"] = all_linkedin
        result["linkedin_urls"] = all_linkedin  # 兼容下游字段名
        result["linkedin_url"] = all_linkedin[0] if all_linkedin else ""
        result["query_hits"] = query_hits
        result["secondary_search_ran"] = True
        result["has_real_contact_page"] = has_real_contact_page

        # 状态判断
        has_name = bool(result.get("decision_makers"))
        has_email = bool(all_emails)
        has_phone = bool(all_phones)
        has_linkedin_personal = any("/in/" in li for li in all_linkedin)

        if has_name and (has_email or has_phone or has_linkedin_personal):
            result["second_search_status"] = "已补全可跟进"
        elif has_name or has_email or has_phone or has_linkedin_personal:
            result["second_search_status"] = "信息不足待补充"
        elif has_real_contact_page:
            result["second_search_status"] = "有联系页但无具体信息"
        else:
            result["second_search_status"] = "无有效联系人"

        return result

    selected = leads[:max_leads]
    enriched = await asyncio.gather(*[_enrich_one(l) for l in selected])
    return enriched
