# 🚀 AI 发版说明书生成器

基于 FastAPI 和大模型打造的实用工具，一键把 GitHub 的英文 Commit 记录，生成面向开发者、产品经理和普通用户的中文发版说明。

## 如何使用
1. 配置 `.env` 文件（参考 `.env.example`），填入 GitHub Token 和 AI Key。
2. 安装依赖：`pip install fastapi uvicorn requests python-dotenv`
3. 启动服务：`python -m uvicorn main:app --reload`
4. 打开 `http://127.0.0.1:8000` 体验！
