# KKX — 外贸获客智能体

一个基于 AI 的 B2B 客户发现与线索分级系统，为礼品制造企业（SWSAGE/WELP）自动搜索、评分、丰富联系人生成邮件草稿并同步到飞书多维表格。

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                        Web 前端 (Next.js)                      │
│  Next.js 16 + React 19 + TypeScript + Tailwind CSS + shadcn/ui │
│  http://localhost:3000                                        │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   API Server (FastAPI)                        │
│  Python FastAPI + Uvicorn · http://localhost:8001             │
│  端点: /api/run  /api/runs  /api/runs/{id}  /api/health       │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    9 步流水线引擎                              │
│                                                              │
│  1. 加载数据 (loader)    → 公司画像 + 评分规则 JSON            │
│  2. 构建搜索词 (queries)  → 英文查询模板 (UK/AU/US)            │
│  3. 搜索客户 (searcher)  → Serper Google Search API          │
│  4. 归一化 (normalizer)  → page_type 分类 + 严格过滤          │
│  5. 客户匹配评分 (scorer)→ 两层评分: 匹配分 + 就绪分          │
│  6. 联系人补全 (enrich)  → 二次搜索: 邮箱/电话/LinkedIn       │
│  7. 最终分级            → 合并评分结果                        │
│  8. 邮件草稿 (actions)  → LLM 生成英文开发信                  │
│  9. 输出 (output)       → 本地 JSON + 飞书多维表格            │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌─────────────┐
        │  JSON    │ │  飞书    │ │  Provider   │
        │  文件    │ │  多维表  │ │  插件层      │
        └──────────┘ └──────────┘ └─────────────┘
```

## 核心功能

### 搜索系统

| 特性 | 说明 |
|------|------|
| **主搜索引擎** | Serper Google Search API（2500 次/月免费） |
| **查询语言** | 纯英文，按市场分组（UK > AU > US） |
| **国家定位** | Serper `gl`/`hl` 参数 + 页面内容提取（不从 TLD 硬猜） |
| **备用 Provider** | Tavily / SERP API / DuckDuckGo / Mock |

### 两层评分系统

**第一层 — 客户匹配分**（决定 A/B/C/D 等级，与联系人信息无关）：

| 维度 | 分值范围 | 说明 |
|------|---------|------|
| 市场匹配 | 0-30 | UK=30, AU=30, US=20 |
| 客户类型 | 0-30 | 礼品零售买手=30, 连锁=25, 相关=15 |
| 产品场景 | 0-25 | mug/tumbler/homeware 等关键词匹配 |
| 风险项 | 0-15 | 无风险=15, 中风险=5, 高风险=0 |

**等级阈值**：A ≥ 70 · B = 55-69 · C = 40-54 · D < 40 · < 25 自动排除

**第二层 — 推进就绪分**（决定下一步动作）：

| 维度 | 分值范围 | 说明 |
|------|---------|------|
| 官网 | 0-10 | 有官网=10 |
| 联系人 | 0-30 | 关键决策人=30, 采购角色=25, 普通=15 |
| 联系方式 | 0-25 | 邮箱=25, 电话=15, LinkedIn个人=15 |
| 证据完整度 | 0-20 | 真实联系页=20, 有官网=15, 仅搜索=5 |

### 页面类型过滤

只有以下 page_type 允许进入最终 lead 表：

| 允许入表 | 禁止入表 |
|---------|---------|
| `company_detail` | `directory_root` |
| `exhibitor_detail` | `event_resource` |
| `brand_profile` | `sector_page` |
| `company_site` | `blog_news` |
| | `generic_event_contact` |
| | `unknown` |

### 飞书集成

- 每次运行在同一个 Base App 下**自动创建新表**
- 表名格式：`客户表_MM-DD_HH-mm-ss`（带秒，避免重名冲突）
- 重名自动重试：`_2` / `_3` / `_4` ...
- 15 个业务字段自动创建，中文名称

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- Serper API Key（[serper.dev](https://serper.dev)）
- 飞书开放平台应用（App ID + App Secret + App Token）
- DashScope / OpenAI 兼容 API Key

### 1. 后端配置

编辑 `simple_backend_project_root/.env`：

```bash
# LLM 配置
LLM_PROVIDER=dashscope
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=your-dashscope-api-key
OPENAI_MODEL=qwen3.5-plus

# 搜索配置
SEARCH_PROVIDER=serper
SERPER_API_KEY=your-serper-api-key

# 飞书配置
FEISHU_PROVIDER=feishu
FEISHU_APP_ID=your-feishu-app-id
FEISHU_APP_SECRET=your-feishu-app-secret
FEISHU_BITABLE_APP_TOKEN=your-feishu-bitable-app-token
FEISHU_BITABLE_TABLE_ID=default-table-id
```

### 2. 启动 API 服务器

```bash
cd simple_backend_project_root
pip install -r requirements.txt  # 如需安装依赖
python -m uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload
```

### 3. 启动前端

```bash
cd web
npm install
npm run dev
```

访问 http://localhost:3000 打开工作台界面。

### 4. CLI 直接运行

```bash
cd simple_backend_project_root
python main.py --feishu --max-leads 10
```

## 项目结构

```
kkx/
├── simple_backend_project_root/     # 核心流水线引擎
│   ├── main.py                      # 9 步流水线编排器
│   ├── queries.py                   # 搜索查询构建器（一次/二次搜索）
│   ├── searcher.py                  # 搜索执行 + 负向过滤
│   ├── normalizer.py               # page_type 分类 + 公司名规范化
│   ├── scorer.py                   # 两层评分系统
│   ├── enrich.py                   # 联系人二次搜索
│   ├── actions.py                  # LLM 邮件草稿生成
│   ├── output.py                   # JSON 输出 + 飞书写入
│   ├── api_server.py               # FastAPI REST API 服务器
│   ├── config.py                   # 环境变量配置
│   ├── run_naming.py               # 表名命名规则
│   └── loader.py                   # JSON 数据加载
│
├── backend/app/                     # Provider 插件层
│   ├── core/
│   │   ├── config.py               # 最小配置类
│   │   ├── exceptions.py           # 自定义异常
│   │   └── logging.py              # 日志工具
│   └── providers/
│       ├── search/                  # 搜索 Provider
│       │   ├── serper_provider.py  # Serper（主）
│       │   ├── tavily_provider.py  # Tavily
│       │   ├── serpapi_provider.py # SERP API
│       │   ├── duckduckgo_provider.py # DuckDuckGo
│       │   └── mock_search.py      # Mock
│       ├── llm/                     # LLM Provider
│       │   ├── openai_compatible.py # DashScope/Qwen
│       │   └── mock_llm.py         # Mock
│       └── feishu/                  # 飞书 Provider
│           ├── feishu_bitable.py   # 飞书多维表格 API
│           └── mock_feishu.py      # Mock
│
├── web/                             # 前端工作台
│   ├── app/page.tsx                # 主页面
│   ├── lib/                        # API 客户端 + 类型定义
│   └── components/                 # 14 个 React 组件
│
├── data/profiles/                   # 业务数据
│   ├── swsage_company_profile_v3.json   # 公司画像
│   └── swsage_grading_rules_v3.json     # 评分规则
│
└── data/output/                     # 输出目录
    ├── leads_*.json                 # 每次运行的 JSON 结果
    └── runs_index.json              # 运行记录索引
```

## API 端点

### POST /api/run — 启动一次流水线运行

```json
{
  "max_leads": 10,
  "use_llm_queries": false,
  "use_llm_actions": true,
  "output_feishu": true
}
```

返回：

```json
{
  "run_id": "abc123",
  "run_name": "客户表_04-13_10-28-18",
  "feishu_table_name": "客户表_04-13_10-28-18",
  "feishu_sync_status": "已创建",
  "status": "running",
  "feishu_table_id": "tblXXXX",
  "feishu_table_url": "https://www.feishu.cn/base/...?table=tblXXXX"
}
```

### GET /api/runs — 列出所有运行记录

### GET /api/runs/{run_id} — 获取运行详情（含 leads 数据）

### GET /api/health — 健康检查

### GET /api/feishu/test-create-table — 独立飞书建表测试

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12, FastAPI, Uvicorn, httpx, asyncio |
| 前端 | Next.js 16, React 19, TypeScript 5, Tailwind CSS v4, shadcn/ui |
| 搜索 | Serper（主）, Tavily, SERP API, DuckDuckGo |
| LLM | DashScope qwen3.5-plus（OpenAI 兼容 API） |
| 集成 | 飞书开放平台 API（tenant_access_token 认证） |
| 构建 | npm/Turbopack（前端）, pip（后端） |

## 关键设计原则

1. **一次搜索只找真实公司页** — 目录页/资源页/栏目页绝不入表
2. **两层评分分离** — 客户匹配分（业务适配）≠ 推进就绪分（信息完整度）
3. **不伪造联系方式** — 二次搜索只记录真实找到的邮箱/电话/LinkedIn
4. **国家从内容提取** — 不从域名 TLD 硬猜，从页面正文/地址/公司简介提取
5. **英文搜索为主** — 所有查询使用英文，按市场传 `gl`/`hl` 参数
6. **表名自动去重** — 带秒 + 重试机制，不会因为重名阻断流程

## 搜索查询模板

### 一次搜索（找公司）

```
"ceramic mug gift retailer uk"
"giftware wholesaler australia"
"homeware wholesaler australia"
site:autumnfair.com/exhibitors giftware
site:autumnfair.com/exhibitors "Overview" "Products"
site:reedgiftfairs.com.au "exhibitor details" gift
```

### 二次搜索（找联系人）

```
"[company name] contact"
"[company name] buyer email"
"[company name] category manager linkedin"
site:[domain] buyer
site:[domain] "about us"
```

## 许可证

内部项目，仅供团队使用。
