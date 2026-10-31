import requests


def get_recent_commits(owner, repo, count=5):
    # 1. 拼接 GitHub 的 API 地址
    # 格式：https://api.github.com/repos/用户名/仓库名/commits
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    # 2. 设置请求头（Headers）
    headers = {
        "Accept": "application/vnd.github+json",
        # ⚠️ 把下面引号里的内容替换成你刚才申请的 Token（注意保留开头的 ghp_）
        # 带上 Token 的好处是：GitHub 知道是你，每分钟允许你请求 60 次（不带只能请求极少数）
        "Authorization": "Bearer ght_faketoken",
         }

    # 3. 设置参数（告诉 GitHub 我只要最近的 5 条）
    params = {
        "per_page": count
    }

    print(f"正在拉取 {owner}/{repo} 的最近 {count} 条 commit...\n")

    # 4. 发送 GET 请求
    response = requests.get(url, headers=headers, params=params)

    # 5. 判断是否请求成功（状态码 200 代表成功）
    if response.status_code == 200:
        # 把返回的 JSON 数据转换成 Python 的字典/列表
        commits = response.json()

        # 6. 遍历并打印结果
        for i, commit_data in enumerate(commits, 1):
            # 提取我们需要的信息
            commit_info = commit_data["commit"]
            author = commit_info["author"]["name"]
            date = commit_info["author"]["date"]
            message = commit_info["message"].split("\n")[0]  # 只取提交信息的第一行，防止太长
            sha = commit_data["sha"][:7]  # 取哈希值的前7位作为编号

            print(f"【第 {i} 条】")
            print(f"提交人: {author}")
            print(f"时  间: {date}")
            print(f"编  号: {sha}")
            print(f"内  容: {message}")
            print("-" * 40)
    else:
        print(f"获取失败，状态码: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    # 调用函数：拉取 tiangolo/fastapi 项目的最近 5 条 commit
    get_recent_commits("tiangolo", "fastapi", 5)
