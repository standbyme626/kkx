import httpx
import re
from typing import Dict, Any, List
from app.core.config import settings
from app.core.logging import get_logger
from .base import BaseSearchProvider

logger = get_logger("bocha_search")

# 需要过滤的中文域名关键词
CHINESE_DOMAINS = [
    ".cn",
    ".com.cn",
    ".gov.cn",
    "bidcenter",
    "jianyu",
    "caigou",
    "zhaobiao",
    "21cnjy",
    "51sole",
    "tradesns",
    "sohu.com",
    "sina.com",
    "qq.com",
    "taobao",
    "tmall",
    "jd.com",
    "baidu",
    "alibaba",
    "1688",
    "china.com",
    "people.com.cn",
]

# 需要过滤的中文标题关键词
CHINESE_TITLE_KEYWORDS = [
    "招标",
    "采购",
    "中标",
    "公告",
    "供应",
    "求购",
    "批发",
    "公司",
    "有限公司",
    "股份",
    "中国",
    "广东",
    "浙江",
    "江苏",
    "山东",
]


class BochaSearchProvider(BaseSearchProvider):
    """博查AI 搜索提供者"""

    def __init__(self):
        if not settings.BOCHA_API_KEY:
            raise ValueError("BOCHA_API_KEY 未配置")
        self.api_key = settings.BOCHA_API_KEY
        self.base_url = "https://api.bochaai.com/v1"

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """搜索

        Args:
            query: 搜索词
            count: 返回结果数量（默认10）
            freshness: 时间范围（oneDay, oneWeek, oneMonth, oneYear）

        Returns:
            搜索结果列表
        """
        count = kwargs.get("count", 10)
        freshness = kwargs.get("freshness", "oneMonth")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/web-search",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "count": count,
                        "freshness": freshness,
                        "summary": True,
                    },
                )

                response.raise_for_status()
                data = response.json()

                # 解析结果并过滤
                results = []
                if data.get("code") == 200:
                    web_pages = (
                        data.get("data", {}).get("webPages", {}).get("value", [])
                    )
                    for item in web_pages:
                        url = item.get("url", "")
                        title = item.get("name", "")

                        # 跳过中文域名
                        if any(domain in url.lower() for domain in CHINESE_DOMAINS):
                            continue

                        # 跳过中文标题
                        if any(keyword in title for keyword in CHINESE_TITLE_KEYWORDS):
                            # 但允许英文标题包含这些词的情况
                            if re.search(r"[a-zA-Z]", title):
                                pass  # 有英文就保留
                            else:
                                continue

                        results.append(
                            {
                                "title": item.get("name", ""),
                                "url": url,
                                "snippet": item.get("snippet", ""),
                                "siteName": item.get("siteName", ""),
                            }
                        )

                logger.info(
                    f"博查AI 搜索 `{query}` 返回 {len(results)} 条结果（过滤后）"
                )
                return results

        except Exception as e:
            logger.error(f"博查AI 搜索失败: {str(e)}")
            raise
