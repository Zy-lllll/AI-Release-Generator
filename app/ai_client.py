"""调用大模型生成三个视角的发版说明（兼容 OpenAI Chat Completions 协议）。"""
from __future__ import annotations

import re
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


def generate_release_notes(commits: list[dict[str, Any]], repo_name: str = "") -> dict[str, str]:
    if not config.AI_API_KEY:
        raise AIError("服务端未配置 AI_API_KEY，请在 .env 中填入大模型密钥。")
    if not commits:
        raise AIError("没有可总结的更新记录。")

    prompt = PROMPT_TEMPLATE.format(commits=_build_commit_text(commits))
    if repo_name:
        prompt = f"仓库：{repo_name}\n\n{prompt}"

    payload = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": "你是严谨的中文技术文档作者，只输出要求的 Markdown 内容。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "stream": False,
    }

    try:
        resp = requests.post(
            f"{config.AI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=config.AI_TIMEOUT,
        )
    except requests.Timeout:
        raise AIError("大模型响应超时，请稍后重试或减少提交条数。")
    except requests.RequestException:
        raise AIError("无法连接大模型服务，请检查服务器网络或 AI_BASE_URL 配置。")

    if resp.status_code == 401:
        raise AIError("大模型密钥无效，请检查 .env 中的 AI_API_KEY。")
    if resp.status_code == 402:
        raise AIError("大模型账户余额不足，请充值后重试。")
    if resp.status_code == 429:
        raise AIError("大模型调用过于频繁，请稍后再试。")
    if resp.status_code != 200:
        raise AIError(f"大模型接口报错（HTTP {resp.status_code}）：{resp.text[:200]}")

    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        raise AIError("大模型返回内容解析失败，请重试。")

    return _split_sections(content)
