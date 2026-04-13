from typing import List, Dict, Any
from app.core.logging import get_logger
from .base import BaseSearchProvider

logger = get_logger("mock_search")


class MockSearchProvider(BaseSearchProvider):
    """Mock 搜索提供者"""
    
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """执行搜索"""
        logger.info(f"Mock 搜索: {query}")
        
        # 返回 Mock 搜索结果
        return [
            {
                "title": "Apple Inc. - 官方网站",
                "url": "https://www.apple.com",
                "content": "Apple 是一家全球知名的科技公司，专注于设计和制造电子产品。",
                "company": "Apple Inc.",
                "country": "美国"
            },
            {
                "title": "Samsung Electronics - 官方网站",
                "url": "https://www.samsung.com",
                "content": "Samsung 是一家全球知名的电子产品制造商，总部位于韩国。",
                "company": "Samsung Electronics",
                "country": "韩国"
            },
            {
                "title": "Microsoft Corporation - 官方网站",
                "url": "https://www.microsoft.com",
                "content": "Microsoft 是一家全球知名的软件公司，总部位于美国。",
                "company": "Microsoft Corporation",
                "country": "美国"
            },
            {
                "title": "Google LLC - 官方网站",
                "url": "https://www.google.com",
                "content": "Google 是一家全球知名的互联网公司，总部位于美国。",
                "company": "Google LLC",
                "country": "美国"
            },
            {
                "title": "Amazon.com Inc. - 官方网站",
                "url": "https://www.amazon.com",
                "content": "Amazon 是一家全球知名的电子商务公司，总部位于美国。",
                "company": "Amazon.com Inc.",
                "country": "美国"
            }
        ][:limit]