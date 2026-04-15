import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env（优先共享 /home/test/kkk/.env，其次 backend/.env，再其次本目录 .env）
BASE_DIR = Path(__file__).parent
load_dotenv(Path("/home/test/kkk/.env"))
load_dotenv(BASE_DIR.parent / "backend" / ".env")
load_dotenv(BASE_DIR / ".env")

PROFILE_PATH = BASE_DIR / "../backend/data/profiles/swsage_company_profile_v3.json"
RULES_PATH = BASE_DIR / "../backend/data/profiles/swsage_grading_rules_v3.json"

MAX_LEADS = 10
SEARCH_CONCURRENCY = 6
SEARCH_RESULT_PER_QUERY = 8

# 输出目录 - 绝对路径
OUTPUT_DIR = BASE_DIR / "data" / "output"
RUNS_INDEX_FILE = OUTPUT_DIR / "runs_index.json"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "dashscope")
LLM_MODEL = os.getenv("OPENAI_MODEL", "qwen3.5-plus")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "")

SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_APP_TOKEN = os.getenv("FEISHU_BITABLE_APP_TOKEN", "")  # 表格 token
FEISHU_TABLE_ID = os.getenv("FEISHU_BITABLE_TABLE_ID", "")  # 表格 ID（默认表，API 动态建表时不用）

# 浏览器打开多维表：{base}/{app_token}?table={table_id}
FEISHU_BITABLE_WEB_BASE = os.getenv(
    "FEISHU_BITABLE_WEB_BASE", "https://www.feishu.cn/base"
).rstrip("/")
