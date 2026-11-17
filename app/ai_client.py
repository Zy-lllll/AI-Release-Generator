"""调用大模型生成三个视角的发版说明（兼容 OpenAI Chat Completions 协议）。"""
from __future__ import annotations

import re
import time
from typing import Any

import requests

from . import config

PROMPT_TEMPLATE = """你是一位资深软件发布经理。请阅读下面的 GitHub 更新记录，输出三个版本的中文发版说明。

1. DEV（面向开发者）：保留技术细节、模块名、接口变化、破坏性变更。
2. PM（面向产品经理）：侧重功能变化、业务价值、影响范围。
3. USER（面向普通用户）：用大白话讲清使用体验的提升，不要出现代码、函数、PR 之类的词汇。

【严格要求】
- 全程使用简体中文，不要输出任何英文段落。
- 每段开头自行拟定一个合理的版本号，格式为：**版本号：v1.2.0**
- 正文必须用 Markdown 表格整理，表头固定为：| 更新类型 | 具体说明 | 关联 Issue/PR |
- 如果没有关联 Issue，写“—”。

【输出格式】（必须严格使用这三个分隔标记）
### DEV
**版本号：v1.2.0**
| 更新类型 | 具体说明 | 关联 Issue/PR |
|---|---|---|
| 修复 | ... | #123 |
### PM
**版本号：v1.2.0**
| 更新类型 | 具体说明 | 关联 Issue/PR |
|---|---|---|
| 功能 | ... | #123 |
### USER
**版本号：v1.2.0**
| 更新类型 | 具体说明 | 关联 Issue/PR |
|---|---|---|
| 体验提升 | ... | #123 |

更新记录如下：
{commits}
"""


class AIError(Exception):
    pass


def _build_commit_text(commits: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {c.get('message', '')} (作者: {c.get('author', '')}, 时间: {c.get('date', '')[:10]})"
        for c in commits
    )


def _split_sections(text: str) -> dict[str, str]:
    patterns = {
        "dev": r"###\s*DEV\s*(.*?)(?=###\s*PM|###\s*USER|$)",
        "pm": r"###\s*PM\s*(.*?)(?=###\s*USER|###\s*DEV|$)",
        "user": r"###\s*USER\s*(.*)$",
    }
    result: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        result[key] = match.group(1).strip() if match else ""

    # 模型没按格式输出时兜底：把全文放进开发者版，其它两版给出提示
    if not any(result.values()):
        result["dev"] = text.strip()
        result["pm"] = "模型本次未按格式返回，请点击「重新生成」再试一次。"
        result["user"] = "模型本次未按格式返回，请点击「重新生成」再试一次。"
    else:
        for key, value in result.items():
            if not value:
                result[key] = "本次未生成该视角的内容，请点击「重新生成」再试一次。"
    return result


def _call_model(payload: dict[str, Any]) -> dict[str, Any]:
    """带重试的调用：免费档常报「访问量过大」，推理模型可能不支持 thinking 参数。"""
    url = f"{config.AI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.AI_API_KEY}",
        "Content-Type": "application/json",
    }
    thinking_off = payload.pop("thinking", None) is not None
    last_error = ""

    for attempt in range(max(0, config.AI_RETRY) + 1):
        if thinking_off and attempt == 0:
            payload["thinking"] = {"type": "disabled"}   # 只发一次，失败再去掉
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=config.AI_TIMEOUT)
        except requests.Timeout:
            raise AIError("大模型响应超时，请稍后重试或减少提交条数。")
        except requests.RequestException:
            raise AIError("无法连接大模型服务，请检查服务器网络或 AI_BASE_URL 配置。")

        body = resp.text or ""
        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 401:
            raise AIError("大模型密钥无效，请检查 .env 中的 AI_API_KEY。")
        if resp.status_code == 402:
            raise AIError("大模型账户余额不足，请充值后重试。")

        busy = resp.status_code == 429 or "1305" in body or "访问量过大" in body
        if busy and attempt < config.AI_RETRY:
            payload.pop("thinking", None)
            last_error = "模型当前访问量过大"
            time.sleep(2 + attempt * 2)
            continue

        if resp.status_code == 400 and "thinking" in payload:
            payload.pop("thinking", None)     # 该模型不认这个参数，去掉重发
            last_error = body[:200]
            continue

        if busy:
            raise AIError("免费模型当前访问量过大，请等几秒再点「重新生成」。")
        raise AIError(f"大模型接口报错（HTTP {resp.status_code}）：{body[:200]}")

    raise AIError(f"大模型调用失败：{last_error or '请稍后重试'}")


def generate_release_notes(commits: list[dict[str, Any]], repo_name: str = "") -> dict[str, str]:
    if not config.AI_API_KEY:
        raise AIError("服务端未配置 AI_API_KEY，请在 .env 中填入大模型密钥。")
    if not commits:
        raise AIError("没有可总结的更新记录。")

    prompt = PROMPT_TEMPLATE.format(commits=_build_commit_text(commits))
    if repo_name:
        prompt = f"仓库：{repo_name}\n\n{prompt}"

    payload: dict[str, Any] = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": "你是严谨的中文技术文档作者，只输出要求的 Markdown 内容。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "stream": False,
    }
    # 推理类模型（glm-4.5/4.6/4.7 系列）关掉思考，既快又不吃满 token
    if config.AI_DISABLE_THINKING and config.AI_PROVIDER.startswith("zhipu"):
        payload["thinking"] = {"type": "disabled"}

    data = _call_model(payload)
    try:
        message = data["choices"][0]["message"]
        content = (message.get("content") or "").strip()
    except (KeyError, IndexError, AttributeError):
        raise AIError("大模型返回内容解析失败，请重试。")

    if not content:
        reasoning = (message.get("reasoning_content") or "").strip()
        if reasoning:
            raise AIError("模型把 token 全用在思考上了，请点「重新生成」再试一次。")
        raise AIError("模型返回了空内容，请点「重新生成」再试一次。")

    return _split_sections(content)
