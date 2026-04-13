"""最小日志"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("app")

def get_logger(name: str) -> logging.Logger:
    return logger.getChild(name)
