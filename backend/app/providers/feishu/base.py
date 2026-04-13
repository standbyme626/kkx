from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseFeishuProvider(ABC):
    """飞书提供者基类"""
    
    @abstractmethod
    async def write_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """写入记录
        
        Args:
            records: 记录列表
        
        Returns:
            写入结果
        """
        raise NotImplementedError

    async def list_fields(self) -> List[Dict[str, Any]]:
        """列出当前数据表字段（可选能力，默认空）。"""
        return []

    async def ensure_fields(self, field_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """确保字段存在（可选能力，默认不创建）。"""
        return {"created": [], "existing": [], "failed": []}

    def supports_upsert(self) -> bool:
        """是否支持按业务键更新记录。"""
        return False

    async def list_records(self, page_size: int = 500) -> List[Dict[str, Any]]:
        """列出记录（可选能力，默认空）。"""
        return []

    async def update_record(
        self, record_id: str, fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新单条记录（可选能力，默认失败）。"""
        return {"record_id": record_id, "success": False}
