"""FastAPI 入口：网页 + 接口一体化，可直接部署为单端口服务。"""
from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import ai_client, config, github_client

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "templates" / "index.html"

app = FastAPI(title="发版说明生成器", version="3.0.0", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=800)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---- 简易限流：防止公开部署后密钥被刷 ----
_hits: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(request: Request, limit: int, window: int = 3600) -> None:
    ip = (request.client.host if request.client else "unknown") or "unknown"
    now = time.time()
    hits = [t for t in _hits[ip] if now - t < window]
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试。")
    hits.append(now)
    _hits[ip] = hits


class SummaryRequest(BaseModel):
    owner: str = Field(default="", max_length=80)
    repo: str = Field(default="", max_length=120)
    limit: int = Field(default=config.DEFAULT_LIMIT, ge=1, le=config.MAX_LIMIT)
    commits: list[dict] | None = None

    @field_validator("owner", "repo")
    @classmethod
    def _clean(cls, value: str) -> str:
        return value.strip().strip("/")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(INDEX_FILE, media_type="text/html; charset=utf-8")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    # Service Worker 必须位于根路径才能控制全站
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "github_token": bool(config.GITHUB_TOKEN),
        "ai_key": bool(config.AI_API_KEY),
        "ai_model": config.AI_MODEL,
    }


@app.get("/api/commits")
def get_commits(
    owner: str = "tiangolo",
    repo: str = "fastapi",
    limit: int = config.DEFAULT_LIMIT,
):
    owner, repo = owner.strip().strip("/"), repo.strip().strip("/")
    if not owner or not repo:
        raise HTTPException(status_code=400, detail="请填写用户名和仓库名。")
    limit = max(1, min(limit, config.MAX_LIMIT))

    try:
        info = github_client.fetch_repo_info(owner, repo)
        commits = github_client.fetch_commits(owner, repo, limit)
    except github_client.GitHubError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"repo": info, "commits": commits}


@app.post("/api/summary")
def summary(payload: SummaryRequest, request: Request):
    _check_rate_limit(request, config.AI_RATE_LIMIT)

    commits = payload.commits
    repo_name = f"{payload.owner}/{payload.repo}".strip("/")
    if not commits:
        if not payload.owner or not payload.repo:
            raise HTTPException(status_code=400, detail="请先选择仓库并获取更新记录。")
        try:
            commits = github_client.fetch_commits(payload.owner, payload.repo, payload.limit)
        except github_client.GitHubError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    if len(commits) > config.MAX_LIMIT:
        commits = commits[: config.MAX_LIMIT]

    try:
        sections = ai_client.generate_release_notes(commits, repo_name)
    except ai_client.AIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"repo": repo_name, "count": len(commits), **sections}


@app.exception_handler(HTTPException)
def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
