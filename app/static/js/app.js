/* 发版说明生成器 - 前端交互 */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const state = {
    repo: null,
    commits: [],
    ai: { dev: "", pm: "", user: "" },
    tab: "dev",
    limit: 8,
  };

  const el = {
    owner: $("ownerInput"),
    repo: $("repoInput"),
    fetchBtn: $("fetchBtn"),
    generateBtn: $("generateBtn"),
    guideCard: $("guideCard"),
    repoCard: $("repoCard"),
    repoAvatar: $("repoAvatar"),
    repoName: $("repoName"),
    repoDesc: $("repoDesc"),
    repoStats: $("repoStats"),
    commitsCard: $("commitsCard"),
    commitCount: $("commitCount"),
    commitList: $("commitList"),
    toggleCommits: $("toggleCommits"),
    resultCard: $("resultCard"),
    aiContent: $("aiContent"),
    copyBtn: $("copyBtn"),
    shareBtn: $("shareBtn"),
    regenBtn: $("regenBtn"),
    installBtn: $("installBtn"),
    toast: $("toast"),
    loading: $("loading"),
    loadingText: $("loadingText"),
  };

  /* ------------------ 工具 ------------------ */
  let toastTimer = null;
  function toast(message, isError) {
    el.toast.textContent = message;
    el.toast.classList.toggle("error", !!isError);
    el.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.toast.hidden = true; }, 2600);
  }

  function showLoading(text) {
    el.loadingText.textContent = text || "正在处理…";
    el.loading.hidden = false;
  }
  function hideLoading() { el.loading.hidden = true; }

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  async function api(path, options) {
    const res = await fetch(path, options);
    let data = null;
    try { data = await res.json(); } catch (e) { /* ignore */ }
    if (!res.ok) {
      throw new Error((data && data.detail) || "请求失败，请稍后重试。");
    }
    return data;
  }

  /* ------------------ 提交信息汉化 ------------------ */
  const WORD_DICT = [
    ["Fixes", "修复"], ["Fixed", "修复"], ["Fix", "修复"],
    ["Adds", "新增"], ["Added", "新增"], ["Add", "新增"],
    ["Updates", "更新"], ["Updated", "更新"], ["Update", "更新"],
    ["Removes", "移除"], ["Removed", "移除"], ["Remove", "移除"],
    ["Supports", "支持"], ["Support", "支持"],
    ["Improves", "优化"], ["Improve", "优化"], ["Improved", "优化"],
    ["Refactor", "重构"], ["Refactored", "重构"],
    ["Drop", "弃用"], ["Drops", "弃用"], ["Bump", "升级"], ["Bumps", "升级"],
    ["Require", "要求"], ["Requires", "要求"], ["Use", "使用"], ["Uses", "使用"],
    ["Allow", "允许"], ["Allows", "允许"], ["Migrate", "迁移"], ["Makes", "使"],
    ["Restore", "恢复"], ["Apply", "应用"], ["Default", "默认"],
    ["obsolete", "过时的"], ["deprecated", "已废弃的"], ["docs", "文档"],
  ];

  function localizeMessage(msg) {
    let out = msg;
    for (const [en, zh] of WORD_DICT) {
      out = out.replace(new RegExp("\\b" + en + "\\b", "gi"), zh);
    }
    return out.replace(/\s{2,}/g, " ").trim();
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso.slice(0, 10);
    const p = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) +
      " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }

  /* ------------------ 获取更新 ------------------ */
  async function fetchCommits() {
    const owner = el.owner.value.trim().replace(/^\/+|\/+$/g, "");
    let repo = el.repo.value.trim().replace(/^\/+|\/+$/g, "");
    if (repo.indexOf("/") > -1) {           // 支持直接粘贴 "owner/repo"
      const parts = repo.split("/");
      el.owner.value = owner || parts[0];
      repo = parts[1] || "";
      el.repo.value = repo;
    }
    if (!owner || !repo) { toast("请填写用户名和仓库名", true); return; }

    el.fetchBtn.disabled = true;
    showLoading("正在从 GitHub 拉取更新记录…");
    try {
      const data = await api("/api/commits?owner=" + encodeURIComponent(el.owner.value.trim()) +
        "&repo=" + encodeURIComponent(repo) + "&limit=" + state.limit);

      state.repo = data.repo;
      state.commits = data.commits || [];
      state.ai = { dev: "", pm: "", user: "" };
      el.guideCard.hidden = true;
      renderRepo();
      renderCommits();
      el.resultCard.hidden = true;
      el.generateBtn.hidden = state.commits.length === 0;

      if (state.commits.length === 0) {
        toast("没有找到有效的人工提交记录", true);
      } else {
        toast("已获取 " + state.commits.length + " 条更新");
      }
      localStorage.setItem("rn_owner", el.owner.value.trim());
      localStorage.setItem("rn_repo", repo);
      localStorage.setItem("rn_limit", String(state.limit));
      el.generateBtn.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) {
      toast(err.message, true);
    } finally {
      el.fetchBtn.disabled = false;
      hideLoading();
    }
  }

  function renderRepo() {
    const r = state.repo;
    if (!r) return;
    el.repoCard.hidden = false;
    el.repoAvatar.src = r.avatar || "";
    el.repoAvatar.alt = r.full_name;
    el.repoName.textContent = r.full_name;
    el.repoDesc.textContent = r.description || "这个仓库还没有简介";
    el.repoStats.innerHTML =
      "<span>⭐ " + (r.stars || 0).toLocaleString() + "</span>" +
      (r.language ? "<span>🧩 " + escapeHtml(r.language) + "</span>" : "");
  }

  function renderCommits() {
    if (!state.commits.length) { el.commitsCard.hidden = true; return; }
    el.commitsCard.hidden = false;
    el.commitCount.textContent = String(state.commits.length);
    el.commitList.innerHTML = state.commits.map(function (c) {
      return '<div class="commit-item">' +
        '<div class="who"><b>' + escapeHtml(c.author || "未知") + "</b>" +
        '<span class="sha">' + escapeHtml(c.sha || "") + "</span>" +
        "<span>" + formatDate(c.date) + "</span></div>" +
        '<div class="msg">' + escapeHtml(localizeMessage(c.message || "")) + "</div>" +
        "</div>";
    }).join("");
  }

  /* ------------------ 生成发版说明 ------------------ */
  async function generate() {
    if (!state.commits.length) { toast("请先获取更新记录", true); return; }
    el.generateBtn.disabled = true;
    el.generateBtn.textContent = "AI 正在撰写三种版本…";
    el.resultCard.hidden = false;
    el.aiContent.innerHTML = '<p class="placeholder">AI 正在从开发者、产品经理、普通用户三个视角分析这次更新…</p>';
    el.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });

    try {
      const data = await api("/api/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          owner: el.owner.value.trim(),
          repo: el.repo.value.trim(),
          limit: state.limit,
          commits: state.commits,
        }),
      });
      state.ai = { dev: data.dev, pm: data.pm, user: data.user };
      state.tab = "dev";
      renderTabs();
      renderMarkdown();
      toast("发版说明已生成");
    } catch (err) {
      el.aiContent.innerHTML = '<p class="placeholder" style="color:#b91c1c">' +
        escapeHtml(err.message) + "</p>";
      toast(err.message, true);
    } finally {
      el.generateBtn.disabled = false;
      el.generateBtn.textContent = "✨ 重新生成三种发版说明";
    }
  }

  /* ------------------ 渲染 ------------------ */
  function renderTabs() {
    document.querySelectorAll(".tab").forEach(function (btn) {
      btn.classList.toggle("active", btn.dataset.key === state.tab);
    });
  }

  function renderMarkdown() {
    const text = state.ai[state.tab] || "";
    if (!text) {
      el.aiContent.innerHTML = '<p class="placeholder">暂无内容</p>';
      return;
    }
    if (window.marked && !window.__markedFailed) {
      try {
        el.aiContent.innerHTML = window.marked.parse(text);
        return;
      } catch (e) { /* 落到下面的纯文本模式 */ }
    }
    el.aiContent.innerHTML = "<p>" +
      escapeHtml(text).replace(/\n/g, "<br>") + "</p>";
  }

  /* ------------------ 复制 / 分享 ------------------ */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy") ? resolve() : reject(new Error("copy failed"));
      } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  async function copyCurrent() {
    const text = state.ai[state.tab] || "";
    if (!text) { toast("还没有可复制的内容", true); return; }
    try {
      await copyText(text);
      el.copyBtn.textContent = "已复制 ✓";
      el.copyBtn.classList.add("done");
      setTimeout(function () {
        el.copyBtn.textContent = "复制";
        el.copyBtn.classList.remove("done");
      }, 1800);
    } catch (e) {
      toast("复制失败，请长按文字手动选择", true);
    }
  }

  async function shareCurrent() {
    const text = state.ai[state.tab] || "";
    if (!text) { toast("还没有可分享的内容", true); return; }
    const title = "发版说明 · " + ((state.repo && state.repo.full_name) || "");
    if (navigator.share) {
      try { await navigator.share({ title: title, text: text }); return; }
      catch (e) { if (e && e.name === "AbortError") return; }
    }
    try {
      await copyText(text);
      toast("已复制，可直接粘贴发给同事");
    } catch (e) { toast("分享失败，请手动复制", true); }
  }

  /* ------------------ 事件绑定 ------------------ */
  el.fetchBtn.addEventListener("click", fetchCommits);
  el.generateBtn.addEventListener("click", generate);
  el.copyBtn.addEventListener("click", copyCurrent);
  el.shareBtn.addEventListener("click", shareCurrent);
  el.regenBtn.addEventListener("click", generate);

  el.owner.addEventListener("keydown", function (e) {
    if (e.key === "Enter") el.repo.focus();
  });
  el.repo.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); fetchCommits(); }
  });

  el.toggleCommits.addEventListener("click", function () {
    const hidden = el.commitList.hidden;
    el.commitList.hidden = !hidden;
    el.toggleCommits.textContent = hidden ? "收起" : "展开";
  });

  document.querySelectorAll("#presets .chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      el.owner.value = chip.dataset.owner;
      el.repo.value = chip.dataset.repo;
      document.querySelectorAll("#presets .chip").forEach(function (c) {
        c.classList.toggle("active", c === chip);
      });
      fetchCommits();
    });
  });

  document.querySelectorAll("#limitSeg .seg-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.limit = Number(btn.dataset.limit);
      document.querySelectorAll("#limitSeg .seg-btn").forEach(function (b) {
        b.classList.toggle("active", b === btn);
      });
      if (state.commits.length) fetchCommits();
    });
  });

  document.querySelectorAll(".tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.tab = btn.dataset.key;
      renderTabs();
      renderMarkdown();
    });
  });

  /* ------------------ PWA：注册 SW + 安装提示 ------------------ */
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () { /* 忽略 */ });
    });
  }

  let deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    el.installBtn.hidden = false;
  });

  el.installBtn.addEventListener("click", async function () {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    el.installBtn.hidden = true;
  });

  window.addEventListener("appinstalled", function () { el.installBtn.hidden = true; });

  /* ------------------ 恢复上次选择 ------------------ */
  (function restore() {
    const owner = localStorage.getItem("rn_owner");
    const repo = localStorage.getItem("rn_repo");
    const limit = Number(localStorage.getItem("rn_limit") || 8);
    if (owner) el.owner.value = owner;
    if (repo) el.repo.value = repo;
    if ([8, 15, 30].indexOf(limit) > -1) {
      state.limit = limit;
      document.querySelectorAll("#limitSeg .seg-btn").forEach(function (b) {
        b.classList.toggle("active", Number(b.dataset.limit) === limit);
      });
    }
  })();
})();
