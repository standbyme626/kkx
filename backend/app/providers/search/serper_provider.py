from typing import List, Dict, Any, Optional
import httpx
import os
from app.core.config import settings
from app.core.logging import get_logger
from .base import BaseSearchProvider

logger = get_logger("serper")


class SerperSearchProvider(BaseSearchProvider):
    """Serper 搜索提供者 (免费 2500次/月)

    支持国家和语言参数，默认英文搜索。
    """

    def __init__(self):
        # 优先从环境变量读取，fallback 到 settings
        self.api_key = os.getenv("SERPER_API_KEY") or settings.SERPER_API_KEY
        self.base_url = "https://google.serper.dev"

    async def search(
        self,
        query: str,
        limit: int = 5,
        country: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """执行搜索

        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            country: 国家代码 (e.g., 'uk', 'au', 'us')
            language: 语言代码 (e.g., 'en')

        Returns:
            搜索结果列表

        Raises:
            RuntimeError: 当 API key 缺失时
        """
        if not self.api_key:
            logger.error("SERPER_API_KEY 未设置")
            raise RuntimeError(
                "Serper API key 缺失：请设置环境变量 SERPER_API_KEY。"
                "如需 fallback 到备用 provider，请确保 SEARCH_PROVIDER 不是 serper。"
            )

        logger.info(f"Serper 搜索: {query} (country={country}, lang={language})")

        try:
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": query, "num": limit}

            # Serper 支持 gl (地理定位) 和 hl (语言)
            # https://serper.dev/playground
            if country:
                payload["gl"] = country.lower()
            if language:
                payload["hl"] = language.lower()
            else:
                # 默认英文
                payload["hl"] = "en"

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(20.0, connect=10.0, read=20.0)
            ) as client:
                response = await client.post(
                    f"{self.base_url}/search", headers=headers, json=payload
                )

            if response.status_code != 200:
                logger.error(
                    f"Serper API 错误: {response.status_code} - {response.text[:500]}"
                )
                return []

            data = response.json()
            results = data.get("organic", [])[:limit]

            search_results = []
            for r in results:
                title = r.get("title", "")
                link = r.get("link", "")
                snippet = r.get("snippet", "")

                search_results.append(
                    {
                        "title": title,
                        "url": link,
                        "content": snippet,
                        "company": title.split("|")[0].strip()
                        if "|" in title
                        else title,
                        "source": "serper",
                    }
                )

            logger.info(f"找到 {len(search_results)} 条结果")
            return search_results

        except httpx.TimeoutException as e:
            logger.error(f"搜索超时: {e}")
            return []
        except httpx.HTTPError as e:
            logger.error(f"搜索 HTTP 失败: {e}")
            return []
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
