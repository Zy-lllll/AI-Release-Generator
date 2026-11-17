"""集中管理配置：所有密钥只从环境变量读取，绝不下发给前端。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


# --- GitHub ---
GITHUB_TOKEN = _env("GITHUB_TOKEN")
GITHUB_API = _env("GITHUB_API", "https://api.github.com").rstrip("/")

# --- 大模型（兼容 OpenAI 协议，可换 DeepSeek / 通义 / 智谱 / Kimi 等）---
AI_API_KEY = _env("AI_API_KEY")
AI_BASE_URL = _env("AI_BASE_URL", "https://api.deepseek.com").rstrip("/")
AI_MODEL = _env("AI_MODEL", "deepseek-chat")
AI_TIMEOUT = int(_env("AI_TIMEOUT", "90"))

# --- 业务参数 ---
DEFAULT_LIMIT = int(_env("DEFAULT_LIMIT", "8"))
MAX_LIMIT = int(_env("MAX_LIMIT", "30"))
CACHE_TTL = int(_env("CACHE_TTL", "300"))          # 提交列表缓存秒数
AI_RATE_LIMIT = int(_env("AI_RATE_LIMIT", "20"))   # 每个 IP 每小时 AI 生成次数
