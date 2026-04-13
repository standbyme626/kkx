import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.core.exceptions import FeishuError
from app.core.logging import get_logger
from .base import BaseFeishuProvider

logger = get_logger("feishu_bitable")

# 字段名映射：代码使用的英文名 -> 表格的中文名
FIELD_MAPPING = {
    "company_name": "公司名称",
    "tier": "分级",
    "score": "分数",
    "tier_reason": "分级原因",
    "next_action": "下一步动作",
    "country": "国家",
    "industry": "行业",
    "website": "官网",
    "decision_maker": "决策人",
    "contact": "联系方式",
    "source_channel": "来源渠道",
    "customer_grade": "客户等级",
    "icp_score": "ICP分数",
    "key_signals": "关键判断信号",
    "recommended_script": "推荐话术",
    "review_status": "审核状态",
    "review_notes": "审核备注",
    "needs_human_review": "是否需人工接管",
    "二次_search_status": "二次搜索状态",
    "contact_evidence": "联系人证据",
}


class FeishuBitableProvider(BaseFeishuProvider):
    """飞书多维表格提供者"""

    def __init__(self, app_token: str | None = None, table_id: str | None = None):
        self.app_id = settings.FEISHU_APP_ID
        self.app_secret = settings.FEISHU_APP_SECRET
        self.app_token = app_token or settings.FEISHU_BITABLE_APP_TOKEN
        self.table_id = table_id or settings.FEISHU_BITABLE_TABLE_ID

        if not all([self.app_id, self.app_secret, self.app_token]):
            raise FeishuError("飞书配置不完整")

        self.access_token = None

    async def create_table(
        self, table_name: str, field_specs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建新的数据表并设置字段。"""
        try:
            token = await self._get_or_refresh_token()
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=15.0, read=60.0)
            ) as client:
                fields = []
                for spec in field_specs:
                    field = {
                        "field_name": spec.get("field_name"),
                        "type": int(spec.get("type", 1)),
                    }
                    if spec.get("options"):
                        field["options"] = spec["options"]
                    fields.append(field)

                payload = {"table": {"name": table_name, "fields": fields}}
                logger.info(f"创建表格请求: {payload}")
                response = await client.post(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                logger.info(f"创建表格响应: {response.text}")
                response.raise_for_status()
                result = response.json()
                if result.get("code") != 0:
                    raise FeishuError(
                        f"创建飞书表格失败 code={result.get('code')} msg={result.get('msg')}"
                    )
                return result.get("data", {})
        except Exception as e:
            logger.error(f"创建飞书表格失败: {str(e)}")
            raise FeishuError(f"创建飞书表格失败: {str(e)}")

    async def _get_access_token(self) -> str:
        """获取访问令牌（需要 tenant_access_token）"""
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0, read=30.0)
            ) as client:
                response = await client.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": self.app_id, "app_secret": self.app_secret},
                )

                response.raise_for_status()
                data = response.json()
                if data.get("code") != 0:
                    raise FeishuError(
                        f"获取 token 失败 code={data.get('code')} msg={data.get('msg')}"
                    )
                return data["tenant_access_token"]
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:800] if e.response is not None else str(e)
            logger.error(f"获取飞书访问令牌 HTTP 错误: {detail}")
            raise FeishuError(f"获取飞书访问令牌 HTTP 错误: {detail}")
        except httpx.TimeoutException as e:
            logger.error(f"获取飞书访问令牌超时: {repr(e)}")
            raise FeishuError("获取飞书访问令牌超时")
        except Exception as e:
            logger.error(f"获取飞书访问令牌失败: {str(e)}")
            raise FeishuError(f"获取飞书访问令牌失败: {str(e)}")

    async def _get_or_refresh_token(self) -> str:
        if not self.access_token:
            self.access_token = await self._get_access_token()
        return self.access_token

    async def list_fields(self) -> List[Dict[str, Any]]:
        """读取当前数据表字段列表。"""
        try:
            token = await self._get_or_refresh_token()
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0, read=30.0)
            ) as client:
                response = await client.get(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                result = response.json()
                if result.get("code") != 0:
                    raise FeishuError(
                        f"飞书字段读取失败 code={result.get('code')} msg={result.get('msg')}"
                    )
                return result.get("data", {}).get("items", [])
        except Exception as e:
            logger.error(f"读取飞书字段失败: {str(e)}")
            raise FeishuError(f"读取飞书字段失败: {str(e)}")

    async def ensure_fields(self, field_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按字段规格自动补齐缺失字段。"""
        created: List[str] = []
        existing: List[str] = []
        failed: List[Dict[str, Any]] = []
        try:
            token = await self._get_or_refresh_token()
            current_fields = await self.list_fields()
            current_names = {
                str(item.get("field_name")).strip()
                for item in current_fields
                if str(item.get("field_name", "")).strip()
            }

            create_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0, read=30.0)
            ) as client:
                for spec in field_specs or []:
                    name = str(spec.get("field_name", "")).strip()
                    if not name:
                        continue
                    if name in current_names:
                        existing.append(name)
                        continue

                    payload: Dict[str, Any] = {
                        "field_name": name,
                        "type": int(spec.get("type", 1)),
                    }
                    options = spec.get("options")
                    if options:
                        payload["options"] = options

                    try:
                        response = await client.post(
                            create_url, headers=headers, json=payload
                        )
                        response.raise_for_status()
                        data = response.json()
                        if data.get("code") != 0:
                            failed.append(
                                {
                                    "field_name": name,
                                    "error": (
                                        f"code={data.get('code')} msg={data.get('msg')}"
                                    ),
                                }
                            )
                            continue
                        created.append(name)
                        current_names.add(name)
                    except Exception as e:
                        failed.append({"field_name": name, "error": str(e)})

            return {"created": created, "existing": existing, "failed": failed}
        except Exception as e:
            logger.error(f"自动补齐飞书字段失败: {str(e)}")
            raise FeishuError(f"自动补齐飞书字段失败: {str(e)}")

    def supports_upsert(self) -> bool:
        return True

    async def list_records(self, page_size: int = 500) -> List[Dict[str, Any]]:
        """读取当前数据表记录（单页）。"""
        try:
            token = await self._get_or_refresh_token()
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0, read=30.0)
            ) as client:
                response = await client.get(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"page_size": max(1, min(500, int(page_size)))},
                )
                response.raise_for_status()
                result = response.json()
                if result.get("code") != 0:
                    raise FeishuError(
                        f"飞书记录读取失败 code={result.get('code')} msg={result.get('msg')}"
                    )
                return result.get("data", {}).get("items", [])
        except Exception as e:
            logger.error(f"读取飞书记录失败: {str(e)}")
            raise FeishuError(f"读取飞书记录失败: {str(e)}")

    async def update_record(
        self, record_id: str, fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新单条记录。"""
        try:
            token = await self._get_or_refresh_token()
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0, read=30.0)
            ) as client:
                response = await client.put(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{record_id}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"fields": fields},
                )
                response.raise_for_status()
                result = response.json()
                if result.get("code") != 0:
                    raise FeishuError(
                        f"飞书记录更新失败 code={result.get('code')} msg={result.get('msg')}"
                    )
                return {"record_id": record_id, "success": True}
        except Exception as e:
            logger.error(f"更新飞书记录失败: {str(e)}")
            return {"record_id": record_id, "success": False, "error": str(e)}

    def _map_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """将英文字段名映射到中文
        注意：数字字段（如客户符合度分）必须保持数字类型，不能转字符串
        """
        mapped = {}
        # 已知需要保持数字类型的字段
        number_fields = {"客户符合度分"}
        for key, value in record.items():
            mapped_key = FIELD_MAPPING.get(key, key)
            if value is None:
                mapped[mapped_key] = ""
            elif mapped_key in number_fields and isinstance(value, (int, float)):
                # 数字字段保持数字类型
                mapped[mapped_key] = float(value)
            elif isinstance(value, (int, float)):
                mapped[mapped_key] = value
            else:
                mapped[mapped_key] = value
        return mapped

    async def write_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """写入记录"""
        try:
            # 获取访问令牌
            token = await self._get_or_refresh_token()

            # 准备请求数据，映射字段名
            mapped_records = [self._map_fields(r) for r in records]
            data = {"records": [{"fields": record} for record in mapped_records]}

            # 发送请求
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=15.0, read=30.0)
            ) as client:
                response = await client.post(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=data,
                )

                response.raise_for_status()
                result = response.json()

                if result.get("code") != 0:
                    raise FeishuError(
                        f"飞书 API 返回错误 code={result.get('code')} msg={result.get('msg')}"
                    )

                # 处理返回结果
                success_count = len(result.get("data", {}).get("records", []))
                return {
                    "success": success_count == len(records),
                    "total": len(records),
                    "success_count": success_count,
                    "failed_count": len(records) - success_count,
                    "failed_records": [],
                    "records": [
                        {"record_id": record.get("record_id"), "success": True}
                        for record in result.get("data", {}).get("records", [])
                    ],
                }
        except Exception as e:
            logger.error(f"飞书写入失败: {str(e)}")
            raise FeishuError(f"飞书写入失败: {str(e)}")

    async def create_view(
        self, view_name: str, view_type: str = "grid", field_ids: List[str] = None
    ) -> Dict[str, Any]:
        """创建视图

        Args:
            view_name: 视图名称
            view_type: 视图类型 (grid/kanban/gallery/gantt/form)，默认grid
            field_ids: 要显示的字段ID列表，None表示显示所有字段
        """
        try:
            token = await self._get_or_refresh_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 构建请求体
                payload = {"view_name": view_name, "view_type": view_type}
                if field_ids:
                    payload["field_ids"] = field_ids
                logger.info(f"创建视图请求: {payload}")
                response = await client.post(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                result = response.json()
                logger.info(f"创建视图响应: {result}")
                if result.get("code") != 0:
                    raise FeishuError(
                        f"创建视图失败: code={result.get('code')} msg={result.get('msg')}"
                    )
                return result.get("data", {})
        except Exception as e:
            logger.error(f"创建视图失败: {str(e)}")
            raise FeishuError(f"创建视图失败: {str(e)}")

    async def list_views(self) -> List[Dict[str, Any]]:
        """读取当前表格的视图列表。"""
        try:
            token = await self._get_or_refresh_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                result = response.json()
                if result.get("code") != 0:
                    raise FeishuError(
                        f"读取视图失败: code={result.get('code')} msg={result.get('msg')}"
                    )
                return result.get("data", {}).get("items", [])
        except Exception as e:
            logger.error(f"读取视图失败: {str(e)}")
            raise FeishuError(f"读取视图失败: {str(e)}")

    async def delete_view(self, view_id: str) -> Dict[str, Any]:
        """删除视图"""
        try:
            token = await self._get_or_refresh_token()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views/{view_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                result = response.json()
                if result.get("code") != 0:
                    raise FeishuError(
                        f"删除视图失败: code={result.get('code')} msg={result.get('msg')}"
                    )
                return result.get("data", {})
        except Exception as e:
            logger.error(f"删除视图失败: {str(e)}")
            raise FeishuError(f"删除视图失败: {str(e)}")
