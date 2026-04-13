from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseSearchProvider(ABC):
    """搜索提供者基类"""
    
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """执行搜索
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
        
        Returns:
            搜索结果列表
        """
        pass