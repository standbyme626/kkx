"""
A/B 级客户二次搜索联系人
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
    if ":" in raw:
        return raw.split(":")[0].strip()
    if " - " in raw:
        parts = [p.strip() for p in raw.split(" - ") if p.strip()]
        return parts[-1]
    return raw


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
    lead: Dict[str, Any], profile: Dict[str, Any], max_queries: int = 10
) -> List[str]:
    """二次搜索查询 - 域名优先 + contact/about/team页面优先"""
    company = str(lead.get("company_name") or lead.get("name") or "").strip()
    website = str(lead.get("website") or "").strip()
    domain = _extract_domain(website)

    contact_roles = [
        "Category Buyer",
        "Product Development Manager",
        "Procurement Manager",
        "Sourcing Manager",
        "Buyer",
        "Head of Buying",
    ]

    queries: List[str] = []

    # 1. 官网站内优先
    if domain:
        queries.extend(
            [
                f'site:{domain} (buyer OR procurement OR sourcing OR "category manager")',
                f'site:{domain} ("about us" OR team OR contact OR careers)',
                f"site:{domain} email",
                f'site:{domain} phone OR telephone OR "contact us"',
            ]
        )

    # 2. 公司名 + 职位
    for role in contact_roles[:4]:
        queries.append(f'"{company}" "{role}"')
        queries.append(f'"{company}" "{role}" LinkedIn')

    # 3. LinkedIn 个人页/公司页
    queries.append(f'site:linkedin.com/in "{company}" buyer')
    queries.append(f'site:linkedin.com/in "{company}" "product development manager"')
    queries.append(f'site:linkedin.com/company "{company}"')

    # 4. 推进信号
    queries.append(f'"{company}" hiring buyer')
    queries.append(f'"{company}" "new collection"')
    queries.append(f'"{company}" expansion')

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
    """从搜索文本提取人名和职位"""
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
                    if any(
                        r in title_lower
                        for r in ["buyer", "manager", "sourcing", "procurement", "head"]
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
    import re

    candidates = []
    for m in _get_phone_re().findall(text or ""):
        cleaned = " ".join(m.split())
        if len(re.sub(r"\D", "", cleaned)) >= 8:
            candidates.append(cleaned)
    return list(set(candidates))


def _rank_contact_name(name: str, title: str) -> int:
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


async def enrich_contacts(
    leads: List[Dict[str, Any]],
    profile: Dict[str, Any],
    concurrency: int = 3,
    max_queries_per_lead: int = 8,
    max_leads: int = 5,
) -> List[Dict[str, Any]]:
    """二次搜索联系人 - 关闭mock + 电话抽取 + 联系人排序"""
    from app.providers.search import create_search_provider

    search = create_search_provider(use_mock_if_env_missing=False)
    sem = asyncio.Semaphore(concurrency)

    async def _search_contact(query: str) -> List[Dict]:
        try:
            async with sem:
                return await search.search(query, limit=3)
        except Exception:
            return []

    async def _enrich_one(lead: Dict[str, Any]) -> Dict[str, Any]:
        company = str(lead.get("company_name") or "").strip()
        domain = _extract_domain(str(lead.get("website", "")))
        queries = _build_contact_queries(
            lead, profile, max_queries=max_queries_per_lead
        )

        all_emails, all_phones = [], []
        all_linkedin = []
        all_decision_makers, all_titles = [], []
        query_hits = []

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

                # 域名优先：保留官网相关命中
                if domain and domain in url:
                    query_hits.append({"query": query, "url": url, "title": title})

                for e in _get_email_re().findall(text):
                    if e not in all_emails:
                        all_emails.append(e)

                for p in _extract_phones(text):
                    if p not in all_phones:
                        all_phones.append(p)

                for li in _extract_linkedin(text):
                    if li not in all_linkedin:
                        all_linkedin.append(li)

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
        result["decision_maker"] = best.get("name")
        result["job_title"] = best.get("title")
        result["emails"] = all_emails
        result["email"] = all_emails[0] if all_emails else None
        result["phones"] = all_phones
        result["phone"] = all_phones[0] if all_phones else None
        result["linkedin_profiles"] = all_linkedin
        result["linkedin_url"] = all_linkedin[0] if all_linkedin else None
        result["query_hits"] = query_hits
        result["secondary_search_ran"] = True

        if result.get("decision_maker") and (
            result.get("email") or result.get("linkedin_url")
        ):
            result["second_search_status"] = "已补全可跟进"
        elif (
            result.get("decision_maker")
            or result.get("email")
            or result.get("linkedin_url")
        ):
            result["second_search_status"] = "信息不足待补充"
        else:
            result["second_search_status"] = "无有效联系人"

        return result

    selected = leads[:max_leads]
    enriched = await asyncio.gather(*[_enrich_one(l) for l in selected])
    return enriched
