import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.core.exceptions import SearchError
from app.core.logging import get_logger
from .base import BaseSearchProvider

logger = get_logger("serpapi_search")


class SerpApiSearchProvider(BaseSearchProvider):
    """SerpApi 搜索提供者（作为可替换的真实 Provider）

    说明：
    - 只调用 SerpApi 的搜索接口，不做爬虫。
    - 输出字段与 Mock/Tavily 保持一致：title/url/content。
    """

    def __init__(self):
        self.api_key = settings.SERPAPI_API_KEY
        if not self.api_key:
            raise SearchError("SerpApi API key 未配置")

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": min(limit, 10),
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get("https://serpapi.com/search.json", params=params)
                resp.raise_for_status()
                data = resp.json()

            organic = data.get("organic_results", []) or []
            results: List[Dict[str, Any]] = []
            for item in organic[:limit]:
                results.append(
                    {
                        "title": item.get("title"),
                        "url": item.get("link"),
                        "content": item.get("snippet"),
                        "company": item.get("title"),
                        "country": "",
                    }
                )

            return results
        except Exception as e:
            logger.error(f"SerpApi 搜索失败: {str(e)}")
            raise SearchError(f"SerpApi 搜索失败: {str(e)}")

