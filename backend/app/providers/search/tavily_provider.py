import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.core.exceptions import SearchError
from app.core.logging import get_logger
from .base import BaseSearchProvider

logger = get_logger("tavily_search")


class TavilySearchProvider(BaseSearchProvider):
    """Tavily 搜索提供者"""
    
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        if not self.api_key:
            raise SearchError("Tavily API key 未配置")
    
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """执行搜索"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": limit,
                        "include_answer": False,
                        "include_raw_content": False
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # 转换结果格式
                results = []
                for result in data.get("results", []):
                    results.append({
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "content": result.get("content"),
                        "company": result.get("title").split(" - ")[0] if " - " in result.get("title", "") else result.get("title"),
                        "country": ""
                    })
                
                return results
        except Exception as e:
            logger.error(f"Tavily 搜索失败: {str(e)}")
            raise SearchError(f"Tavily 搜索失败: {str(e)}")