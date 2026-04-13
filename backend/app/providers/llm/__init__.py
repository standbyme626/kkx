from app.core.config import settings
from .base import BaseLLMProvider
from .openai_compatible import OpenAICompatibleLLMProvider
from .mock_llm import MockLLMProvider


def create_llm_provider() -> BaseLLMProvider:
    """创建 LLM 提供者
    
    Returns:
        LLM 提供者实例
    """
    provider = settings.LLM_PROVIDER
    
    if provider in ("openai", "dashscope"):
        return OpenAICompatibleLLMProvider()
    else:
        # 默认使用 Mock LLM
        return MockLLMProvider()