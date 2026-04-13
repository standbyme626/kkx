from typing import List, Dict, Any
from app.core.logging import get_logger
from .base import BaseSearchProvider

logger = get_logger("duckduckgo")


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """DuckDuckGo 搜索提供者 (免费)"""

    def __init__(self):
        try:
            from duckduckgo_search import DDGS

            self._ddgs = DDGS()
        except ImportError:
            logger.warning("duckduckgo-search 未安装，请运行: pip install ddgs")
            self._ddgs = None

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """执行搜索

        Args:
            query: 搜索查询
            limit: 返回结果数量限制

        Returns:
            搜索结果列表
        """
        if not self._ddgs:
            logger.error("duckduckgo-search 未安装")
            return []

        logger.info(f"DuckDuckGo 搜索: {query}")

        try:
            results = self._ddgs.text(query, max_results=limit)

            search_results = []
            for r in results:
                search_results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "content": r.get("body", ""),
                        "company": r.get("title", "").split("|")[0].strip(),
                        "source": "duckduckgo",
                    }
                )

            logger.info(f"找到 {len(search_results)} 条结果")
            return search_results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
