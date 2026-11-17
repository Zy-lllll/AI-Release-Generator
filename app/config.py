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
    "zhipu": ("https://open.bigmodel.cn/api/paas/v4", "glm-4.7-flash"),      # 免费，200K
    "zhipu-lite": ("https://open.bigmodel.cn/api/paas/v4", "glm-4.5-flash"), # 免费，128K
    "zhipu-pro": ("https://open.bigmodel.cn/api/paas/v4", "glm-4.6"),
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
}

# 选供应商：写一行 AI_PROVIDER 就用该家预设的接口+模型（旧的 AI_MODEL 不会再干扰）；
# 一行都不写则默认智谱免费档；要接非预设的服务，手写 AI_BASE_URL + AI_MODEL。
_provider = _env("AI_PROVIDER").lower()
if _provider in PROVIDER_PRESETS:
    AI_PROVIDER = _provider
    AI_BASE_URL, AI_MODEL = PROVIDER_PRESETS[_provider]
else:
    AI_PROVIDER = _provider or ("custom" if (_env("AI_BASE_URL") or _env("AI_MODEL")) else "zhipu")
    AI_BASE_URL = (_env("AI_BASE_URL") or PROVIDER_PRESETS["zhipu"][0]).rstrip("/")
    AI_MODEL = _env("AI_MODEL") or PROVIDER_PRESETS["zhipu"][1]
AI_TIMEOUT = int(_env("AI_TIMEOUT", "120"))
AI_RETRY = int(_env("AI_RETRY", "2"))                    # 免费档偶发「访问量过大」时重试
AI_DISABLE_THINKING = _env("AI_DISABLE_THINKING", "1") not in ("0", "false", "False", "")

# --- 业务参数 ---
DEFAULT_LIMIT = int(_env("DEFAULT_LIMIT", "8"))
MAX_LIMIT = int(_env("MAX_LIMIT", "30"))
CACHE_TTL = int(_env("CACHE_TTL", "300"))          # 提交列表缓存秒数
AI_RATE_LIMIT = int(_env("AI_RATE_LIMIT", "20"))   # 每个 IP 每小时 AI 生成次数
