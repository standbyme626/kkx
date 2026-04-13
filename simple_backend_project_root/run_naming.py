"""Demo 运行 / 飞书表业务命名（业务员可读）"""

from datetime import datetime


def make_demo_run_table_name(now: datetime | None = None) -> str:
    """
    统一格式：客户表_MM-DD_HH-mm-ss
    例如：客户表_04-13_10-30-45
    加秒避免同一分钟内重复运行导致 TableNameDuplicated
    """
    dt = now or datetime.now()
    return dt.strftime("客户表_%m-%d_%H-%M-%S")


def make_demo_run_table_name_with_retry(
    attempt: int = 0, now: datetime | None = None
) -> str:
    """
    重试时生成不冲突的表名。
    attempt=0 → 客户表_MM-DD_HH-mm-ss
    attempt>=1 → 客户表_MM-DD_HH-mm-ss_2 / _3 / _4
    """
    base = make_demo_run_table_name(now)
    if attempt > 0:
        return f"{base}_{attempt + 1}"
    return base
