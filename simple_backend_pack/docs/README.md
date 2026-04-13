# 最小后端打包文档

## 1. 目录结构

```
simple_backend/
├── main.py           # 主入口
├── loader.py         # 加载profile/rules
├── queries.py       # 查询生成（垂直目录+种子公司）
├── searcher.py       # 搜索（串行/并行）
├── normalizer.py     # 归一化
├── scorer.py         # 两阶段评分
├── enrich.py         # 二次搜索补全联系人
├── actions.py        # LLM生成邮件草稿
├── output.py         # 飞书字段 + JSON输出
├── config.py        # 配置
└── data/output/    # JSON输出目录
```

## 2. .env 配置

```bash
# 搜索API（Serper）
SEARCH_PROVIDER=serper
SERPER_API_KEY=xxx

# LLM（阿里百炼）
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=xxx
OPENAI_MODEL=qwen3.5-plus

# 飞书
FEISHU_APP_ID=cli_a9401b8a57f8dbc6
FEISHU_APP_SECRET=xxx
FEISHU_BITABLE_APP_TOKEN=NCzxbo6k2ahRLFsCjM8c5rehn9b
FEISHU_BITABLE_TABLE_ID=tbld2KqdBRbR6vgG
```

## 3. 运行命令

```bash
# 基础搜索（无LLM）
cd /home/kkk/Project/project-root/simple_backend
python main.py --max-leads 10 --no-llm-actions

# 完整流程（搜索+二次搜索+LLM邮件）
cd /home/kkk/Project/project-root/simple_backend
python main.py --max-leads 20
```

## 4. 14个飞书字段（当前v20）

| 序号 | 字段 | 说明 |
|------|------|------|
| 1 | 公司名称 | |
| 2 | 官网 | |
| 3 | 国家 | |
| 4 | 客户类型 | 推断 |
| 5 | 客户等级 | A/B/C/D |
| 6 | 客户符合度分 | 30-100 |
| 7 | 分级原因 | 业务词库生成 |
| 8 | 关键判断信号 | 市场/类型/需求/风险 |
| 9 | 推荐联系人 | 二次搜索 |
| 10 | 联系方式线索 | 邮箱/电话/LinkedIn |
| 11 | 邮件草稿 | LLM生成 |
| 12 | 搜索处理状态 | 5种枚举 |
| 13 | 下一步动作 | 规则映射 |
| 14 | 备注 | |

## 5. 核心函数接口

```python
# loader.py
load_data(profile_path, rules_path) -> (profile, rules)

# queries.py
build_lead_queries(profile, max_queries) -> List[str]

# searcher.py
search_leads(queries, profile, concurrency, result_per_query, max_results) -> List[Dict]

# normalizer.py
normalize_leads(results, max_leads) -> List[Dict]

# scorer.py
score_leads(profile, rules, leads, max_leads, include_all_grades) -> List[Dict]
# 输出: customer_grade, customer_value_score, grading_reason, key_signals

# enrich.py
enrich_contacts(leads, profile, concurrency, max_queries_per_lead, max_leads) -> List[Dict]
# 输出: decision_makers, emails, contacts, linkedin_urls

# actions.py (需LLM)
enrich_with_email(profile, leads, llm) -> List[Dict]
# 输出: email_draft

# output.py
_format_for_feishu(lead) -> Dict  # 14字段
FEISHU_FIELDS  # 字段定义
write_json(leads, output_path) -> str  # 本地JSON
write_feishu(leads, table_id) -> dict  # 飞书
```

## 6. 搜索处理状态（5种）

| 状态 | 条件 | 下一步动作 |
|------|------|-----------|
| 已补全可跟进 | 有联系人+邮箱 | 立即跟进 |
| 高符合度，需第三次搜索 | A/B级无联系方式 | 第三次搜索 |
| 高符合度，需人工搜索 | A/B级线索不完整 | 人工搜索 |
| 信息不足，继续背调 | C级 | 继续背调 |
| 暂不优先 | D级 | 暂不优先 |

## 7. 业务词库（分级原因/关键信号用）

**市场**：英国首选市场、澳洲重点市场、美国培育市场、德国需认证、中东避坑

**类型**：英澳礼品买手、英澳零售商、美国宠物电商、儿童礼品专营店、大宗批发商

**需求**：多材质主题配套、DTF快样、小批量测款、OEM定制

**风险**：缺EN71认证、缺LFGB认证、只比价、小单散客、服务成本过高

## 8. 评分等级

| 等级 | 分数 | 说明 |
|------|------|------|
| A | 80-100 | 种子客户，目标市场 |
| B | 65-79 | 高匹配 |
| C | 50-64 | 待培育 |
| D | <50 | 暂不优先 |

## 9. 飞书表格版本

- v20: table_id = tblMyX67ad91Fk4b