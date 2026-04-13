"""
简化版外贸获客智能体 - 主入口
使用两阶段评分系统
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加 backend 到路径，以便复用 provider
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import config
from loader import load_data
from searcher import search_leads
from normalizer import normalize_leads
from scorer import score_leads
from enrich import enrich_contacts
from output import write_json, write_feishu


async def run_workflow(
    profile_path: str = None,
    rules_path: str = None,
    use_llm_for_queries: bool = False,
    use_llm_for_actions: bool = True,
    max_leads: int = 10,
    output_json: bool = True,
    output_feishu: bool = False,
):
    """运行工作流 - 两阶段评分"""

    # 1. 加载数据
    print("=" * 50)
    print("步骤1: 加载数据")
    print("=" * 50)

    if not profile_path:
        profile_path = config.PROFILE_PATH
    if not rules_path:
        rules_path = config.RULES_PATH

    profile, rules = load_data(profile_path, rules_path)
    print(f"公司: {profile.get('company_name')}")
    print(f"产品: {profile.get('product_category')}")
    print(f"目标市场: {profile.get('target_markets')}")

    # 2. 构建搜索词 - 使用新的垂直目录/展会查询
    print("\n" + "=" * 50)
    print("步骤2: 构建搜索词")
    print("=" * 50)

    from queries import build_lead_queries

    queries = build_lead_queries(profile, max_queries=max_leads * 3)
    print(f"生成搜索词 {len(queries)} 条")
    for q in queries[:8]:
        print(f"  - {q}")
    if len(queries) > 8:
        print(f"  ... 共 {len(queries)} 条")

    # 3. 搜索客户
    print("\n" + "=" * 50)
    print("步骤3: 搜索客户")
    print("=" * 50)

    raw_results = await search_leads(
        queries,
        profile,
        concurrency=config.SEARCH_CONCURRENCY,
        result_per_query=config.SEARCH_RESULT_PER_QUERY,
        max_results=max_leads * 3,
    )
    print(f"搜索结果 {len(raw_results)} 条")

    # 4. 归一化
    print("\n" + "=" * 50)
    print("步骤4: 归一化")
    print("=" * 50)

    normalized = normalize_leads(raw_results, max_leads=max_leads * 3)
    print(f"归一化后 {len(normalized)} 条")

    # 5. 第一阶段评分
    print("\n" + "=" * 50)
    print("步骤5: 第一阶段评分（客户价值分）")
    print("=" * 50)

    scored = score_leads(
        profile, rules, normalized, max_leads=max_leads, include_all_grades=True
    )

    # 统计分级
    grade_dist = {}
    for l in scored:
        g = l.get("customer_grade", "D")
        grade_dist[g] = grade_dist.get(g, 0) + 1

    print(
        f"全部客户: {len(scored)} 条 "
        f"(A:{grade_dist.get('A', 0)} B:{grade_dist.get('B', 0)} "
        f"C:{grade_dist.get('C', 0)} D:{grade_dist.get('D', 0)})"
    )

    # 显示第一阶段高分候选
    stage1_candidates = [l for l in scored if l.get("customer_grade") in ["A", "B"]]
    print(f"第一阶段 A/B 级候选: {len(stage1_candidates)} 条")

    for lead in stage1_candidates[:5]:
        grade = lead.get("customer_grade", "?")
        score = lead.get("customer_value_score", 0)
        name = lead.get("company_name", "?")
        country = lead.get("country", "")
        print(f"  [{grade}] {score}分 - {name} ({country})")

    # 6. 第二阶段评分（对高优候选）
    print("\n" + "=" * 50)
    print("步骤6: 第二阶段评分（推进就绪分）")
    print("=" * 50)

    # 只对第一阶段 A/B 级进行二次搜索
    target_leads = [l for l in scored if l.get("customer_grade") in ["A", "B"]]

    if target_leads:
        print(f"高优客户 {len(target_leads)} 条，执行二次搜索...")

        enriched_targets = await enrich_contacts(
            target_leads,
            profile,
            concurrency=3,
            max_queries_per_lead=12,
            max_leads=len(target_leads),
        )

        # 按 company_name merge
        by_name = {
            str(l.get("company_name", "")).strip().lower(): l for l in enriched_targets
        }

        merged = []
        for lead in scored:
            key = str(lead.get("company_name", "")).strip().lower()
            if key in by_name:
                updated = {**lead, **by_name[key]}
                merged.append(updated)
            else:
                merged.append(lead)

        # 重新评分（含第二阶段）
        scored = score_leads(
            profile, rules, merged, max_leads=max_leads, include_all_grades=True
        )

        # 显示有联系人信息的候选
        has_contact = [
            l
            for l in scored
            if l.get("decision_makers") or l.get("emails") or l.get("linkedin_urls")
        ]
        print(f"二次搜索后有联系人: {len(has_contact)} 条")

        for lead in has_contact[:3]:
            dms = lead.get("decision_makers", [])
            emails = lead.get("emails", [])
            linkedin = lead.get("linkedin_urls", [])
            print(f"  - {lead.get('company_name')}")
            print(f"    决策人: {dms[:2]}")
            print(f"    邮箱: {emails[:2]}")
            print(f"    LinkedIn: {linkedin[:1]}")
    else:
        print("无高优客户，跳过二次搜索")

    # 7. 最终分级输出
    print("\n" + "=" * 50)
    print("步骤7: 最终分级")
    print("=" * 50)

    final_grade_dist = {}
    for l in scored:
        g = l.get("final_grade", l.get("customer_grade", "D"))
        final_grade_dist[g] = final_grade_dist.get(g, 0) + 1

    print(
        f"最终客户: {len(scored)} 条 "
        f"(A:{final_grade_dist.get('A', 0)} B:{final_grade_dist.get('B', 0)} "
        f"C:{final_grade_dist.get('C', 0)} D:{final_grade_dist.get('D', 0)})"
    )

    # 显示 Top 候选
    top_candidates = sorted(
        scored, key=lambda x: x.get("customer_value_score", 0), reverse=True
    )[:5]

    for lead in top_candidates:
        grade = lead.get("final_grade", lead.get("customer_grade", "?"))
        score = lead.get("customer_value_score", 0)
        name = lead.get("company_name", "?")
        stage2 = lead.get("data_completeness_score", 0)
        status = lead.get("second_search_status", "待二次搜索")

        print(f"  [{grade}] {score}分 | {name}")
        print(f"       二阶段: {stage2}分 | {status}")

    # 8. 生成邮件草稿
    print("\n" + "=" * 50)
    print("步骤8: 生成邮件草稿")
    print("=" * 50)

    if use_llm_for_actions:
        from app.providers.llm import create_llm_provider
        from actions import enrich_with_email

        llm = create_llm_provider()
        scored = await enrich_with_email(profile, scored, llm)
        print(f"LLM邮件草稿已生成")
    else:
        from actions import _fallback_email

        for lead in scored:
            lead.update(_fallback_email(lead))

    print(f"完成 {len(scored)} 条客户处理")

    # 9. 输出
    print("\n" + "=" * 50)
    print("步骤9: 输出")
    print("=" * 50)

    if output_json:
        output_path = write_json(scored)
        print(f"JSON: {output_path}")

    if output_feishu:
        result = await write_feishu(scored)
        print(f"飞书: {result}")

    return scored


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="简化版外贸获客智能体")
    parser.add_argument("--profile", help="公司画像路径")
    parser.add_argument("--rules", help="评分规则路径")
    parser.add_argument("--max-leads", type=int, default=10, help="最大客户数")
    parser.add_argument("--no-llm-queries", action="store_true", help="搜索词不用 LLM")
    parser.add_argument(
        "--no-llm-actions", action="store_true", help="动作建议不用 LLM"
    )
    parser.add_argument("--json", action="store_true", default=True, help="输出 JSON")
    parser.add_argument("--feishu", action="store_true", help="写入飞书")

    args = parser.parse_args()

    asyncio.run(
        run_workflow(
            profile_path=args.profile,
            rules_path=args.rules,
            use_llm_for_queries=not args.no_llm_queries,
            use_llm_for_actions=not args.no_llm_actions,
            max_leads=args.max_leads,
            output_json=args.json,
            output_feishu=args.feishu,
        )
    )


if __name__ == "__main__":
    main()
