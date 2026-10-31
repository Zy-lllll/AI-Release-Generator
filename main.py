from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import os
import re
from dotenv import load_dotenv

# 加载 .env 文件里的密钥
load_dotenv()

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="utf-8">
        <title>GitHub AI 发版工具 v2.0</title>
        <!-- 引入国内 CDN 加速的 Markdown 渲染库，防止报错 -->
        <script src="https://cdn.bootcdn.net/ajax/libs/marked/4.3.0/marked.min.js"></script>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9; margin: 0; padding: 40px 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2b6cb0; margin-bottom: 10px; display: flex; justify-content: center; align-items: center; gap: 10px;}
            /* 版本号标签样式 */
            .version-badge { font-size: 14px; background-color: #e2e8f0; color: #4a5568; padding: 4px 10px; border-radius: 20px; font-weight: normal; vertical-align: middle; }

            .search-box { display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; }
            input { padding: 10px 15px; font-size: 16px; border: 1px solid #cbd5e0; border-radius: 6px; outline: none; width: 200px;}
            input:focus { border-color: #4299e1; box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.2); }
            button { padding: 10px 20px; font-size: 16px; cursor: pointer; border: none; border-radius: 6px; font-weight: bold; transition: 0.2s; }
            .btn-primary { background-color: #2b6cb0; color: white; }
            .btn-primary:hover { background-color: #2c5282; }
            .btn-ai { background-color: #805ad5; color: white; margin: 20px 0; width: 100%; padding: 15px; font-size: 18px; display: none;}
            .btn-ai:hover { background-color: #6b46c1; }
            .btn-ai:disabled { background-color: #a0aec0; cursor: not-allowed; }

            .container { max-width: 900px; margin: 0 auto; }

            details { background: white; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }
            summary { font-weight: bold; color: #4a5568; cursor: pointer; outline: none; user-select: none;}
            summary:hover { color: #2b6cb0; }
            .commit-list { margin-top: 15px; border-top: 1px solid #edf2f7; padding-top: 15px;}
            .commit-item { padding: 10px; border-bottom: 1px solid #edf2f7; font-size: 14px;}
            .commit-item:last-child { border-bottom: none; }

            .tabs { display: none; margin-bottom: -1px; gap: 5px; }
            .tab-btn { background: #e2e8f0; color: #4a5568; border-radius: 8px 8px 0 0; padding: 12px 24px; font-size: 16px; }
            .tab-btn.active { background: white; color: #2b6cb0; border-top: 3px solid #2b6cb0; font-weight: bold; }

            .ai-panel { display: none; background: white; border-radius: 0 8px 8px 8px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); position: relative; }
            /* ... 前面的样式保持不变 ... */

            /* 修改 AI 文本容器样式：宋体、靠左 */
            #ai-content { 
                line-height: 1.8; 
                color: #2d3748; 
                min-height: 150px;
                font-family: 'SimSun', '宋体', 'Songti SC', serif; /* 强制设置宋体 */
                text-align: left; /* 文本靠左 */
            }
            #ai-content h3 { color: #2b6cb0; margin-top: 0; font-size: 18px; border-bottom: 1px solid #edf2f7; padding-bottom: 8px;}
            
            /* 专门为 AI 生成的表格设置样式 */
            #ai-content table {
                width: 100%;
                border-collapse: collapse; /* 合并边框 */
                margin: 15px 0;
                font-size: 15px;
            }
            #ai-content th, #ai-content td {
                border: 1px solid #cbd5e0; /* 表格边框 */
                padding: 12px; /* 内边距 */
                text-align: left; /* 表格内容靠左 */
            }
            #ai-content th {
                background-color: #f7fafc; /* 表头背景色 */
                color: #2d3748;
                font-weight: bold;
            }

            /* ... 后面的样式保持不变 ... */

            .btn-copy { position: absolute; top: 20px; right: 20px; background-color: #edf2f7; color: #4a5568; padding: 8px 12px; font-size: 14px; border-radius: 4px;}
            .btn-copy:hover { background-color: #e2e8f0; }
            .btn-copy.copied { background-color: #48bb78; color: white; }

            .loading { text-align: center; color: #718096; padding: 20px; font-style: italic;}
        </style>
    </head>
    <body>
        <div class="header">
            <!-- 升级：加入系统版本号 -->
            <h1>🚀 AI 发版说明书生成器 <span class="version-badge">系统版本 v2.0.0</span></h1>
            <p style="color:#718096;">输入 GitHub 仓库，一键生成面向不同人群的中文发版说明</p>
        </div>

        <div class="search-box">
            <input type="text" id="ownerInput" value="tiangolo" placeholder="用户名">
            <input type="text" id="repoInput" value="fastapi" placeholder="仓库名">
            <button class="btn-primary" onclick="getCommits()">获取最新更新</button>
        </div>

        <div class="container">
            <button id="generateBtn" class="btn-ai" onclick="askAI()">✨ 一键生成 AI 发版说明</button>

            <details id="commitDetails" style="display:none;">
                <summary>查看已过滤的原始更新记录（去除了机器人）</summary>
                <div class="commit-list" id="commitList"></div>
            </details>

            <div id="aiTabs" class="tabs">
                <button class="tab-btn active" onclick="switchTab('dev', this)">👨‍💻 开发者版</button>
                <button class="tab-btn" onclick="switchTab('pm', this)">📊 产品经理版</button>
                <button class="tab-btn" onclick="switchTab('user', this)">👴 普通用户版</button>
            </div>

            <div id="aiPanel" class="ai-panel">
                <button class="btn-copy" id="copyBtn" onclick="copyContent()">📋 复制文本</button>
                <div id="ai-content" class="loading">等待生成...</div>
            </div>
        </div>

        <script>
            let currentCommits = [];
            let aiData = { dev: "", pm: "", user: "" };

            async function getCommits() {
                const generateBtn = document.getElementById('generateBtn');
                const details = document.getElementById('commitDetails');
                const commitList = document.getElementById('commitList');
                const aiTabs = document.getElementById('aiTabs');
                const aiPanel = document.getElementById('aiPanel');

                commitList.innerHTML = '<p class="loading">正在拉取并过滤数据...</p>';
                aiTabs.style.display = 'none';
                aiPanel.style.display = 'none';
                generateBtn.style.display = 'none';
                details.style.display = 'block';
                details.open = false;

                const owner = document.getElementById('ownerInput').value;
                const repo = document.getElementById('repoInput').value;

                try {
                    const res = await fetch(`/api/commits?owner=${owner}&repo=${repo}`);
                    if (!res.ok) {
                        const errorData = await res.json();
                        throw new Error(errorData.detail || '请求失败');
                    }
                    const data = await res.json();
                    currentCommits = data;

                    if(data.length === 0) {
                        commitList.innerHTML = '<p class="loading" style="color:red;">没有找到人类开发者的更新记录。</p>';
                        return;
                    }

                                        commitList.innerHTML = '';
                    data.forEach(commit => {
                        // 1. 机器人名字汉化
                        let displayAuthor = commit.author;
                        if (displayAuthor.toLowerCase().includes("bot")) {
                            displayAuthor = "🤖 自动更新机器人";
                        }

                        // 2. 原始提交信息汉化（简单词典替换）
                        let displayMsg = commit.message;
                        const gitDict = {
                            "Fix ": "修复 ",
                            "Add ": "新增 ",
                            "Update ": "更新 ",
                            "Remove ": "移除 ",
                            "Support ": "支持 ",
                            "Restore ": "恢复 ",
                            "Apply ": "应用 ",
                            "Default ": "默认 ",
                            "Omitted ": "省略的 "
                        };
                        // 遍历字典进行替换
                        for (const [en, zh] of Object.entries(gitDict)) {
                            // 使用正则且忽略大小写进行替换
                            displayMsg = displayMsg.replace(new RegExp(en, "gi"), zh);
                        }

                        // 3. 时间汉化
                        const dateObj = new Date(commit.date);
                        const zhTime = `${dateObj.getFullYear()}年${dateObj.getMonth()+1}月${dateObj.getDate()}日 ${dateObj.getHours()}:${dateObj.getMinutes().toString().padStart(2, '0')}`;
                        
                        commitList.innerHTML += `
                            <div class="commit-item">
                                <strong>👤 ${displayAuthor}</strong> <span style="color:#a0aec0; font-size:12px;">🕒 ${zhTime}</span><br>
                                <!-- 这里用的是替换后的 displayMsg -->
                                <span style="color:#4a5568;">💬 ${displayMsg}</span>
                            </div>
                        `;
                    });

                    generateBtn.style.display = 'block';

                } catch (error) {
                    commitList.innerHTML = `<p style="color:red;">出错了：${error.message}</p>`;
                }
            }

            async function askAI() {
                const generateBtn = document.getElementById('generateBtn');
                const aiTabs = document.getElementById('aiTabs');
                const aiPanel = document.getElementById('aiPanel');
                const aiContent = document.getElementById('ai-content');

                generateBtn.disabled = true;
                generateBtn.innerText = "🤖 AI 正在疯狂码字中，请稍候...";

                aiTabs.style.display = 'flex';
                aiPanel.style.display = 'block';
                aiContent.innerHTML = '<div class="loading">AI 正在从三个视角分析这些更新...</div>';

                try {
                    const res = await fetch('/api/ai_summary', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ commits: currentCommits })
                    });

                    if (!res.ok) throw new Error("AI 服务请求失败");

                    const data = await res.json();
                    aiData = data;

                    switchTab('dev', document.querySelector('.tab-btn'));

                } catch (error) {
                    aiContent.innerHTML = `<span style="color:red;">出错了：${error.message}</span>`;
                } finally {
                    generateBtn.disabled = false;
                    generateBtn.innerText = "✨ 重新生成";
                }
            }

            function switchTab(type, btn) {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const aiContent = document.getElementById('ai-content');
                const text = aiData[type] || "暂无该版本的说明。";

                // 使用 try-catch 兜底，防止 marked 加载失败导致白屏
                try {
                    aiContent.innerHTML = marked.parse(text);
                } catch(e) {
                    aiContent.innerHTML = text.replace(/\\n/g, '<br>');
                }

                const copyBtn = document.getElementById('copyBtn');
                copyBtn.innerText = "📋 复制文本";
                copyBtn.classList.remove('copied');
            }

            function copyContent() {
                const activeTabText = document.querySelector('.tab-btn.active').innerText;
                let textToCopy = "";

                if (activeTabText.includes("开发者")) textToCopy = aiData.dev;
                else if (activeTabText.includes("产品")) textToCopy = aiData.pm;
                else textToCopy = aiData.user;

                navigator.clipboard.writeText(textToCopy).then(() => {
                    const copyBtn = document.getElementById('copyBtn');
                    copyBtn.innerText = "✅ 复制成功！";
                    copyBtn.classList.add('copied');
                    setTimeout(() => {
                        copyBtn.innerText = "📋 复制文本";
                        copyBtn.classList.remove('copied');
                    }, 2000);
                });
            }
        </script>
    </body>
    </html>
    """


@app.get("/api/commits")
def get_github_commits(owner: str = "tiangolo", repo: str = "fastapi"):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    github_token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {github_token}"}
    response = requests.get(url, headers=headers, params={"per_page": 30})

    if response.status_code == 200:
        clean_data = []
        for c in response.json():
            author_info = c.get("author")
            login_name = author_info.get("login", "") if author_info else ""
            commit_msg = c["commit"]["message"].split("\n")[0]
            commit_author_name = c["commit"]["author"]["name"]

            if "[bot]" in login_name.lower() or "[bot]" in commit_author_name.lower() or "Update release notes" in commit_msg or "Bump " in commit_msg:
                continue

            clean_data.append({
                "author": commit_author_name,
                "date": c["commit"]["author"]["date"],
                "message": commit_msg
            })
            if len(clean_data) == 5:
                break
        return clean_data
    else:
        return {"detail": f"GitHub API 报错: {response.status_code}"}


@app.post("/api/ai_summary")
def ai_summary(data: dict):
    commits = data.get("commits", [])
    if not commits:
        return {"detail": "没有数据可以总结"}

    commits_text = "\n".join([f"- {c['message']} (作者: {c['author']})" for c in commits])

    ai_api_key = os.getenv("AI_API_KEY", "")
    ai_url = "https://api.deepseek.com/chat/completions"
    ai_headers = {"Authorization": f"Bearer {ai_api_key}", "Content-Type": "application/json"}

    # 💡 核心升级：强制中文输出 + 增加版本号逻辑
    # 💡 核心升级：要求 AI 用 Markdown 表格输出，并强制中文
    prompt = f"""
    你是一个资深的软件发布经理。请阅读以下 GitHub 更新记录，生成三个版本的纯中文发版说明：
    1. 面向开发者：保留技术细节和专业术语。
    2. 面向产品经理：侧重于功能变化和业务影响。
    3. 面向普通用户：用大白话说明使用体验的提升，不要出现代码词汇。

    【严格要求】
    - 必须全程使用**简体中文**。
    - 请在每段说明的最开头，自己拟定一个合理的发版版本号（例如：**版本号：v1.2.0**）。
    - **请将具体的更新内容严格整理成 Markdown 表格的形式。**
    - 表格的表头统一为：`| 更新类型 | 具体说明 | 关联 Issue/PR |`。

    【输出格式要求】
    请严格按以下 Markdown 格式输出，用 "###" 作为分隔：
    ### DEV
    **版本号：v1.2.0**
    | 更新类型 | 具体说明 | 关联 Issue/PR |
    |---|---|---|
    | 修复 | 修复了... | #123 |
    ### PM
    **版本号：v1.2.0**
    | 更新类型 | 具体说明 | 关联 Issue/PR |
    |---|---|---|
    | 功能 | 增加了... | #123 |
    ### USER
    **版本号：v1.2.0**
    | 更新类型 | 具体说明 | 关联 Issue/PR |
    |---|---|---|
    | 体验提升 | 现在您可以... | #123 |

    更新记录如下：
    {commits_text}
    """

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(ai_url, headers=ai_headers, json=payload, timeout=30)
        if response.status_code == 200:
            ai_reply = response.json()["choices"][0]["message"]["content"]

            dev_text, pm_text, user_text = "提取失败", "提取失败", "提取失败"
            try:
                dev_match = re.search(r'### DEV\s*(.*?)\s*### PM', ai_reply, re.DOTALL | re.IGNORECASE)
                pm_match = re.search(r'### PM\s*(.*?)\s*### USER', ai_reply, re.DOTALL | re.IGNORECASE)
                user_match = re.search(r'### USER\s*(.*)', ai_reply, re.DOTALL | re.IGNORECASE)

                if dev_match: dev_text = dev_match.group(1).strip()
                if pm_match: pm_text = pm_match.group(1).strip()
                if user_match: user_text = user_match.group(1).strip()
            except Exception as e:
                print(f"解析 AI 格式失败: {e}")

            return {"dev": dev_text, "pm": pm_text, "user": user_text}
        else:
            return {"detail": f"AI 接口报错: {response.status_code}"}
    except Exception as e:
        return {"detail": f"请求 AI 发生异常: {str(e)}"}