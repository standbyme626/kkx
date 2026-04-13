"""最小异常定义"""


class AppError(Exception):
    """应用基础异常"""
    pass


class FeishuError(AppError):
    """飞书操作异常"""
    pass


class LLMError(AppError):
    """LLM 调用异常"""
    pass


class SearchError(AppError):
    """搜索调用异常"""
    pass
