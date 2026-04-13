from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseLLMProvider(ABC):
    """LLM 提供者基类"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数
        
        Returns:
            生成的文本
        """
        pass
    
    @abstractmethod
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成 JSON
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数
        
        Returns:
            生成的 JSON 字典
        """
        pass