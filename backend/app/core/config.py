"""最小配置 - 供所有 provider 使用"""
import os


class _Settings:
    """简单配置，直接从环境变量读取"""

    # 搜索
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
    BOCHA_API_KEY = os.getenv("BOCHA_API_KEY", "")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

    # LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "dashscope")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
    DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "")
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

    # 飞书
    FEISHU_PROVIDER = os.getenv("FEISHU_PROVIDER", "feishu")
    FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
    FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
    FEISHU_BITABLE_APP_TOKEN = os.getenv("FEISHU_BITABLE_APP_TOKEN", "")
    FEISHU_BITABLE_TABLE_ID = os.getenv("FEISHU_BITABLE_TABLE_ID", "")


settings = _Settings()
