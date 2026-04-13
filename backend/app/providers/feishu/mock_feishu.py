import hashlib
from typing import List, Dict, Any
from app.core.logging import get_logger
from .base import BaseFeishuProvider

logger = get_logger("mock_feishu")


class MockFeishuProvider(BaseFeishuProvider):
    """Mock 飞书提供者"""

    async def create_table(
        self, table_name: str, field_specs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """本地/测试：模拟在同一 Base 下建新表。"""
        h = hashlib.md5(table_name.encode("utf-8")).hexdigest()[:10]
        tid = f"mock_{h}"
        logger.info(f"Mock 飞书建表: {table_name} -> {tid} ({len(field_specs or [])} 字段)")
        return {"table_id": tid}

    def supports_upsert(self) -> bool:
        return True

    async def list_records(self, page_size: int = 500) -> List[Dict[str, Any]]:
        return []

    async def update_record(
        self, record_id: str, fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"record_id": record_id, "success": True}
    
    async def write_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """写入记录"""
        logger.info(f"Mock 飞书写入: {len(records)} 条记录")
        
        # 返回 Mock 结果
        return {
            "success": True,
            "total": len(records),
            "success_count": len(records),
            "failed_count": 0,
            "failed_records": [],
            "records": [
                {
                    "record_id": f"mock_record_{i}",
                    "success": True
                }
                for i in range(len(records))
            ]
        }
