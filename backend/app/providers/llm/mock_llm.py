import json
from typing import Dict, Any
from app.core.logging import get_logger
from .base import BaseLLMProvider

logger = get_logger("mock_llm")


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM 提供者"""
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        logger.info(f"Mock LLM 生成: {prompt[:100]}...")
        return "这是一个 Mock 响应"
    
    async def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成 JSON"""
        logger.info(f"Mock LLM 生成 JSON: {prompt[:100]}...")
        
        # 根据提示词返回不同的 Mock 数据
        if "公司画像" in prompt:
            return {
                "company_name": "示例公司",
                "product_category": "电子产品",
                "target_markets": ["美国", "欧洲", "日本"],
                "target_customer_types": ["大型企业", "中型企业"],
                "preferred_company_sizes": ["100-500人", "500-1000人"],
                "target_decision_makers": ["CEO", "CTO", "采购经理"],
                "competitive_advantages": ["价格优势", "技术领先", "服务周到"],
                "key_selection_signals": ["近期有采购计划", "正在寻找供应商", "对我们的产品有兴趣"]
            }
        elif "分级规则" in prompt:
            return {
                "grade_system": ["S", "A", "B", "C"],
                "dimensions": [
                    {
                        "name": "market_match",
                        "description": "市场匹配度",
                        "weight": 20,
                        "scoring_rule": "目标市场匹配度"
                    },
                    {
                        "name": "customer_type_match",
                        "description": "客户类型匹配度",
                        "weight": 20,
                        "scoring_rule": "客户类型匹配度"
                    },
                    {
                        "name": "company_size_match",
                        "description": "公司规模匹配度",
                        "weight": 15,
                        "scoring_rule": "公司规模匹配度"
                    },
                    {
                        "name": "decision_maker_completeness",
                        "description": "决策人信息完整度",
                        "weight": 15,
                        "scoring_rule": "决策人信息完整度"
                    },
                    {
                        "name": "contact_completeness",
                        "description": "联系方式完整度",
                        "weight": 10,
                        "scoring_rule": "联系方式完整度"
                    },
                    {
                        "name": "demand_signal",
                        "description": "需求信号",
                        "weight": 10,
                        "scoring_rule": "需求信号强度"
                    },
                    {
                        "name": "product_fit",
                        "description": "产品适配度",
                        "weight": 10,
                        "scoring_rule": "产品适配度"
                    }
                ],
                "thresholds": {
                    "S": "85",
                    "A": "70",
                    "B": "50",
                    "C": "0"
                }
            }
        elif "搜索 query" in prompt:
            return {
                "queries": [
                    "美国电子产品大型企业采购",
                    "欧洲电子产品供应商寻找",
                    "日本电子产品中型企业采购计划"
                ]
            }
        elif "归一化" in prompt:
            return {
                "leads": [
                    {
                        "company_name": "Apple Inc.",
                        "website": "https://www.apple.com",
                        "country": "美国",
                        "industry": "科技",
                        "company_size_signal": "10000+人",
                        "contacts": ["contact@apple.com"],
                        "decision_makers": ["Tim Cook"],
                        "evidence_urls": ["https://www.apple.com/about/"],
                        "raw_summary": "Apple 是一家全球知名的科技公司"
                    },
                    {
                        "company_name": "Samsung Electronics",
                        "website": "https://www.samsung.com",
                        "country": "韩国",
                        "industry": "科技",
                        "company_size_signal": "10000+人",
                        "contacts": ["contact@samsung.com"],
                        "decision_makers": ["Lee Jae-yong"],
                        "evidence_urls": ["https://www.samsung.com/global/about-us/"],
                        "raw_summary": "Samsung 是一家全球知名的电子产品制造商"
                    }
                ]
            }
        elif "分级原因" in prompt:
            return {
                "grade_reason": "该客户在市场匹配度、客户类型匹配度等多个维度表现优秀",
                "key_signals": ["目标市场匹配", "客户类型匹配", "公司规模适合"],
                "risk_notes": ["联系方式不够完整", "需求信号不够强烈"],
                "next_action": "立即重点跟进",
                "priority": "high",
                "email_draft": "尊敬的客户，您好！我们是一家专业的电子产品供应商..."
            }
        else:
            return {"message": "Mock 响应"}