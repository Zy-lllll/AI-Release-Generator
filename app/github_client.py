"""GitHub 提交记录拉取：过滤机器人提交、内存缓存、友好错误提示。"""
from __future__ import annotations

import threading
import time
from typing import Any

import requests

from . import config

_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_cache_lock = threading.Lock()

# 过滤规则：这些提交对"写发版说明"没有价值
SKIP_KEYWORDS = (
    "[bot]",
    "update release notes",
    "bump ",
    "chore(deps)",
    "dependabot",
    "merge branch",
    "merge pull request",
    "release ",
)


class GitHubError(Exception):
    """带中文提示的业务异常。"""


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ReleaseNoteStudio/1.0",
    }
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return headers


def _friendly_error(status: int, owner: str, repo: str) -> str:
    if status == 404:
        return f"找不到仓库 {owner}/{repo}，请检查用户名和仓库名是否正确（私有仓库需要配置令牌）。"
    if status == 403:
        return "GitHub 接口调用次数已用尽或被限制，请稍后再试，或在服务端配置 GITHUB_TOKEN。"
    if status == 401:
        return "GitHub 令牌无效，请检查服务端 .env 里的 GITHUB_TOKEN。"
    if status >= 500:
        return "GitHub 服务暂时不可用，请稍后重试。"
    return f"GitHub 接口返回异常（HTTP {status}）。"


def fetch_repo_info(owner: str, repo: str) -> dict[str, Any]:
    try:
        resp = requests.get(
            f"{config.GITHUB_API}/repos/{owner}/{repo}",
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException:
        raise GitHubError("连接 GitHub 失败，请检查服务器网络（国内服务器可能需要代理）。")

    if resp.status_code != 200:
        raise GitHubError(_friendly_error(resp.status_code, owner, repo))

    data = resp.json()
    return {
        "full_name": data.get("full_name", f"{owner}/{repo}"),
        "description": data.get("description") or "",
        "stars": data.get("stargazers_count", 0),
        "language": data.get("language") or "",
        "avatar": (data.get("owner") or {}).get("avatar_url", ""),
    }


def fetch_commits(owner: str, repo: str, limit: int = 8) -> list[dict[str, Any]]:
    """翻页抓取，直到攒够 limit 条人工提交（有些仓库前几十条全是机器人）。"""
    key = f"{owner.lower()}/{repo.lower()}/{limit}"
    now = time.time()

    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < config.CACHE_TTL:
            return hit[1]

    commits: list[dict[str, Any]] = []
    per_page = 100
    max_pages = 3

    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                f"{config.GITHUB_API}/repos/{owner}/{repo}/commits",
                headers=_headers(),
                params={"per_page": per_page, "page": page},
                timeout=20,
            )
        except requests.RequestException:
            raise GitHubError("连接 GitHub 失败，请检查服务器网络（国内服务器可能需要代理）。")

        if resp.status_code != 200:
            raise GitHubError(_friendly_error(resp.status_code, owner, repo))

        batch = resp.json()
        if not isinstance(batch, list) or not batch:
            break

        for item in batch:
            commit = item.get("commit") or {}
            message = (commit.get("message") or "").split("\n")[0].strip()
            author_name = ((commit.get("author") or {}).get("name") or "").strip()
            login = ((item.get("author") or {}).get("login") or "").strip()
            haystack = f"{author_name} {login} {message}".lower()

            if not message:
                continue
            if any(word in haystack for word in SKIP_KEYWORDS):
                continue

            commits.append(
                {
                    "author": login or author_name or "未知作者",
                    "date": (commit.get("author") or {}).get("date", ""),
                    "message": message,
                    "url": item.get("html_url", ""),
                    "sha": (item.get("sha") or "")[:7],
                }
            )
            if len(commits) >= limit:
                break

        if len(commits) >= limit or len(batch) < per_page:
            break

    commits = commits[:limit]

    with _cache_lock:
        _cache[key] = (now, commits)
        if len(_cache) > 200:
            _cache.clear()

    return commits
