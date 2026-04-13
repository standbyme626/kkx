import httpx
import json
from typing import Dict, Any
from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from .base import BaseLLMProvider

logger = get_logger("openai_llm")


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    """OpenAI 兼容的 LLM 提供者"""

    def __init__(self):
        # DashScope（阿里百炼）兼容模式：可用 DASHSCOPE_* 或复用 OPENAI_*
        self.base_url = (
            settings.DASHSCOPE_BASE_URL
            if settings.LLM_PROVIDER == "dashscope"
            else (
                settings.OPENAI_BASE_URL
                or settings.DASHSCOPE_BASE_URL
                or "https://api.openai.com/v1"
            )
        )
        self.api_key = settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL

        if not self.api_key:
            raise LLMError("OpenAI API key 未配置")

    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(180.0, connect=60.0, read=180.0)
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        **kwargs,
                    },
                )

                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:800] if e.response is not None else str(e)
            logger.error(f"LLM HTTP 错误: {detail}")
            raise LLMError(f"LLM HTTP 错误: {detail}")
        except httpx.TimeoutException as e:
            logger.error(f"LLM 请求超时: {repr(e)}")
            raise LLMError("LLM 请求超时")
        except Exception as e:
            logger.error(f"LLM 生成失败: {str(e)}")
            raise LLMError(f"LLM 生成失败: {str(e)}")

    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成 JSON"""
        # 添加 JSON 格式要求
        prompt += "\n\n请严格以 JSON 格式返回结果，不要包含任何其他文本。"

        # 最多重试 1 次
        for i in range(2):
            try:
                result = await self.generate(prompt, **kwargs)
                # 清理结果
                result = result.strip()
                if result.startswith("```json"):
                    result = result[7:].strip()
                if result.endswith("```"):
                    result = result[:-3].strip()
                # 解析 JSON
                return json.loads(result)
            except json.JSONDecodeError as e:
                if i == 0:
                    logger.warning(f"JSON 解析失败，重试一次: {str(e)}")
                    continue
                else:
                    logger.error(f"JSON 解析失败: {str(e)}")
                    raise LLMError(f"JSON 解析失败: {str(e)}")
            except Exception as e:
                raise LLMError(f"LLM 生成失败: {str(e)}")
