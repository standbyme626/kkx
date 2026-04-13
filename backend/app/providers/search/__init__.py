from app.core.config import settings
from .base import BaseSearchProvider
from .mock_search import MockSearchProvider
from .tavily_provider import TavilySearchProvider
from .serpapi_provider import SerpApiSearchProvider
from .bocha_provider import BochaSearchProvider
from .duckduckgo_provider import DuckDuckGoSearchProvider
from .serper_provider import SerperSearchProvider
from app.core.logging import get_logger
import os


logger = get_logger("search_provider_factory")


def create_search_provider(
    provider_override: str | None = None, use_mock_if_env_missing: bool = True
) -> BaseSearchProvider:
    """创建搜索提供者

    Serper 优先，如果 key 缺失则根据 use_mock_if_env_missing 决定 fallback。

    Returns:
        搜索提供者实例
    """
    provider = provider_override or settings.SEARCH_PROVIDER

    # 用户要求：禁用 Bocha，统一走英文查询友好的 Serper
    if provider == "bocha":
        logger.warning("Bocha provider is disabled by policy, falling back to serper.")
        provider = "serper"

    if provider == "serper":
        api_key = os.getenv("SERPER_API_KEY") or settings.SERPER_API_KEY
        if not api_key:
            logger.error(
                "Serper provider 配置错误: SERPER_API_KEY 未设置。"
                "请设置环境变量 SERPER_API_KEY 或检查 .env 文件。"
            )
            if use_mock_if_env_missing:
                logger.warning("Fallback 到 MockSearchProvider（仅用于测试）")
                return MockSearchProvider()
            else:
                raise RuntimeError(
                    "Serper API key 缺失且 use_mock_if_env_missing=False。"
                    "请设置 SERPER_API_KEY 环境变量。"
                )
        try:
            return SerperSearchProvider()
        except Exception as e:
            logger.error(f"SerperSearchProvider 初始化失败: {e}")
            if use_mock_if_env_missing:
                logger.warning("Fallback 到 MockSearchProvider")
                return MockSearchProvider()
            raise

    if provider == "tavily":
        try:
            return TavilySearchProvider()
        except Exception:
            return (
                MockSearchProvider()
                if use_mock_if_env_missing
                else TavilySearchProvider()
            )
    if provider == "serpapi":
        try:
            return SerpApiSearchProvider()
        except Exception:
            return (
                MockSearchProvider()
                if use_mock_if_env_missing
                else SerpApiSearchProvider()
            )
    if provider == "duckduckgo":
        try:
            return DuckDuckGoSearchProvider()
        except Exception:
            return (
                MockSearchProvider()
                if use_mock_if_env_missing
                else DuckDuckGoSearchProvider()
            )

    # 默认使用 Mock 搜索
    logger.warning(f"未知 search provider '{provider}'，使用 MockSearchProvider")
    return MockSearchProvider()
