import json
from typing import Dict, Any


def load_json(path: str) -> Dict[str, Any]:
    """加载 JSON 文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_profile(path: str) -> Dict[str, Any]:
    """加载公司画像"""
    return load_json(path)


def load_grading_rules(path: str) -> Dict[str, Any]:
    """加载评分规则"""
    return load_json(path)


def load_data(
    profile_path: str, rules_path: str
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """加载画像和规则"""
    profile = load_profile(profile_path)
    rules = load_grading_rules(rules_path)
    return profile, rules
