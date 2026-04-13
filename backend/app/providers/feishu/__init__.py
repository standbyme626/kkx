from app.core.config import settings
from .base import BaseFeishuProvider
from .mock_feishu import MockFeishuProvider
from .feishu_bitable import FeishuBitableProvider


def create_feishu_provider(
    provider_override: str | None = None,
    app_token_override: str | None = None,
    table_id_override: str | None = None,
    use_mock_if_env_missing: bool = True,
) -> BaseFeishuProvider:
    """创建飞书提供者
    
    Returns:
        飞书提供者实例
    """
    provider = provider_override or settings.FEISHU_PROVIDER
    
    if provider == "feishu":
        try:
            return FeishuBitableProvider(
                app_token=app_token_override,
                table_id=table_id_override,
            )
        except Exception:
            # 如果配置不完整，返回 Mock 提供者
            if use_mock_if_env_missing:
                return MockFeishuProvider()
            raise
    else:
        # 默认使用 Mock 飞书
        return MockFeishuProvider()
