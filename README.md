# 🚀 AI 发版说明书生成器

这是一个基于 FastAPI 和大语言模型（LLM）打造的全栈自动化工具，专治开发团队在写 Release Notes 时的“多角色翻译”痛点。针对 GitHub 上充满技术黑话且夹杂着大量机器人（如 `dependabot[bot]`）无效更新的 Commit 记录，本项目在后端内置了智能数据清洗滤网，只将人类开发者的核心代码改动精准提取出来，并利用结构化 Prompt，一键生成面向“开发者、产品经理、普通用户”三种视角的中文 Markdown 表格发版说明。前端零框架依赖，使用原生 JS 配合 `marked.js` 实时渲染，自带多视角 Tab 切换和一键复制功能。在安全方面，项目严格遵循工程化标准，所有的 API 密钥均通过 `.env` 文件进行隔离读取，确保开源代码绝对纯净。

## 快速启动

如果你想在本地跑起来，只需三步：

1. 安装依赖：`pip install fastapi uvicorn requests python-dotenv`
2. 配置密钥：在根目录新建 `.env` 文件，填入 `GITHUB_TOKEN` 和 `AI_API_KEY`
3. 启动服务：`python -m uvicorn main:app --reload`

打开浏览器访问 `http://127.0.0.1:8000` 即可体验！欢迎 Star 🌟 交流探讨。
