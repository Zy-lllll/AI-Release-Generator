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

# --- 大模型（兼容 OpenAI 协议，可换 DeepSeek / 智谱 / 通义 等）---
AI_API_KEY = _env("AI_API_KEY")

# 预设：只填 AI_PROVIDER 就能切换供应商，AI_BASE_URL / AI_MODEL 可单独覆盖
PROVIDER_PRESETS: dict[str, tuple[str, str]] = {
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
    "zhipu": ("https://open.bigmodel.cn/api/paas/v4", "glm-4.5-flash"),      # 免费
    "zhipu-pro": ("https://open.bigmodel.cn/api/paas/v4", "glm-4.6"),
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
}

AI_PROVIDER = _env("AI_PROVIDER", "deepseek").lower()
_default_base, _default_model = PROVIDER_PRESETS.get(
    AI_PROVIDER, PROVIDER_PRESETS["deepseek"]
)
AI_BASE_URL = (_env("AI_BASE_URL") or _default_base).rstrip("/")
AI_MODEL = _env("AI_MODEL") or _default_model
AI_TIMEOUT = int(_env("AI_TIMEOUT", "90"))

# --- 业务参数 ---
DEFAULT_LIMIT = int(_env("DEFAULT_LIMIT", "8"))
MAX_LIMIT = int(_env("MAX_LIMIT", "30"))
CACHE_TTL = int(_env("CACHE_TTL", "300"))          # 提交列表缓存秒数
AI_RATE_LIMIT = int(_env("AI_RATE_LIMIT", "20"))   # 每个 IP 每小时 AI 生成次数
