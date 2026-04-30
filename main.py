"""個人新聞儀表板 — Web 版主程式

啟動後自動在瀏覽器中開啟 HTML 儀表板。

鍵盤快捷鍵（瀏覽器中）
-----------------------
  R    立即刷新
  F    聚焦篩選框
  Esc  清除篩選

啟動範例
--------
  python main.py
  python main.py --keyword "AI"
  python main.py --refresh 120 --max 10 --port 8080
"""
from __future__ import annotations

import argparse
import json
import logging
import socket
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from typing import Optional

from flask import Flask, Response, jsonify

from config import ENGLISH_CATEGORIES, MAX_ARTICLES_ENGLISH, MAX_ARTICLES_PER_CATEGORY, REFRESH_INTERVAL, RSS_FEEDS
from fetcher import fetch_all

# ── 關閉 Werkzeug 請求日誌 ───────────────────────
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# ── Flask App ────────────────────────────────────
app = Flask(__name__)
_dashboard: Optional["NewsDashboard"] = None

# ── HTML 模板 ─────────────────────────────────────
_HTML = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>📰 個人新聞儀表板</title>
  <link rel="manifest" href="/manifest.json">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="新聞儀表板">
  <meta name="theme-color" content="#161b22">
  <style>
    :root {
      --bg:       #0d1117;
      --surface:  #161b22;
      --surface2: #21262d;
      --border:   #30363d;
      --text:     #e6edf3;
      --muted:    #8b949e;
      --accent:   #58a6ff;
      --green:    #3fb950;
      --yellow:   #e3b341;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      min-height: 100vh;
    }

    /* ── Header ── */
    header {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 0 20px;
      height: 52px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .logo { font-size: 17px; font-weight: 700; letter-spacing: -0.2px; }
    .header-right { display: flex; align-items: center; gap: 16px; }
    #meta   { color: var(--muted); font-size: 12px; }
    #status { color: var(--yellow); font-size: 12px; min-width: 110px; text-align: right; }

    /* ── Controls ── */
    .controls {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 8px 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .search-wrap { position: relative; display: flex; align-items: center; }
    #keyword {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
      font-size: 13px;
      padding: 5px 28px 5px 12px;
      width: 260px;
      outline: none;
      transition: border-color 0.15s;
    }
    #keyword:focus { border-color: var(--accent); }
    #keyword::placeholder { color: var(--muted); }
    .clear-btn {
      position: absolute; right: 6px;
      background: none; border: none;
      color: var(--muted); cursor: pointer;
      font-size: 12px; padding: 2px 4px;
      display: none;
    }
    .clear-btn:hover { color: var(--text); }
    .btn {
      border: none; border-radius: 6px; cursor: pointer;
      font-size: 13px; font-weight: 500;
      padding: 5px 14px; transition: opacity 0.15s;
    }
    .btn:hover { opacity: 0.8; }
    .btn-primary { background: var(--accent); color: #0d1117; }
    #countdown { color: var(--muted); font-size: 12px; margin-left: 4px; }

    /* ── Grid ── */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(460px, 1fr));
      gap: 16px;
      padding: 16px 20px 24px;
    }

    /* ── Card ── */
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .card-header {
      padding: 9px 14px;
      font-size: 13px; font-weight: 600;
      color: var(--accent);
      background: var(--surface2);
      border-bottom: 1px solid var(--border);
      display: flex; align-items: center; justify-content: space-between;
    }
    .card-count { color: var(--muted); font-size: 11px; font-weight: 400; }

    /* ── Article ── */
    .article-list { list-style: none; flex: 1; }
    .article-item {
      display: grid;
      grid-template-columns: 20px 72px 1fr auto;
      gap: 8px;
      align-items: start;
      padding: 7px 14px;
      border-bottom: 1px solid rgba(48,54,61,0.6);
      transition: background 0.1s;
    }
    .article-item.no-thumb {
      grid-template-columns: 20px 1fr auto;
    }
    .article-item:last-child { border-bottom: none; }
    .article-item:hover { background: var(--surface2); }
    .article-num { color: var(--muted); font-size: 11px; padding-top: 2px; text-align: right; }
    .article-thumb {
      width: 72px; height: 48px;
      object-fit: cover;
      border-radius: 4px;
      background: var(--surface2);
      flex-shrink: 0;
      display: block;
    }
    .article-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .article-title {
      color: var(--text); text-decoration: none;
      font-size: 13px; line-height: 1.45; word-break: break-word;
    }
    .article-title:hover { color: var(--accent); }
    .article-title mark {
      background: rgba(227,179,65,0.2);
      color: var(--yellow);
      border-radius: 2px; padding: 0 2px;
    }
    .article-meta {
      display: flex; flex-direction: column;
      align-items: flex-end; gap: 2px;
      min-width: 90px; max-width: 90px;
    }
    .source {
      color: var(--green); font-size: 11px;
      white-space: nowrap; overflow: hidden;
      text-overflow: ellipsis; max-width: 90px; text-align: right;
    }
    .pub-time { color: var(--muted); font-size: 11px; }

    /* ── Empty / Loading ── */
    .empty-msg {
      padding: 16px 14px; color: var(--muted);
      font-style: italic; font-size: 13px;
    }
    .loading-state {
      grid-column: 1 / -1;
      display: flex; align-items: center; justify-content: center;
      gap: 12px; padding: 60px 20px; color: var(--muted);
    }
    .spinner {
      width: 20px; height: 20px;
      border: 2px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ── Bottom tab bar ── */
    #tabs {
      position: sticky;
      bottom: 0;
      z-index: 100;
      background: var(--surface);
      border-top: 1px solid var(--border);
      display: flex;
      align-items: stretch;
      overflow-x: auto;
      scrollbar-width: none;
    }
    #tabs::-webkit-scrollbar { display: none; }
    .tab-checkbox {
      display: none;
    }
    .tab-btn {
      position: relative;
      flex: 0 0 auto;
      background: none;
      border: none;
      border-top: 2px solid transparent;
      color: var(--muted);
      cursor: pointer;
      font-size: 13px;
      padding: 10px 18px 10px 32px;
      white-space: nowrap;
      transition: color 0.15s, border-color 0.15s;
      user-select: none;
    }
    .tab-btn input[type=checkbox] {
      position: absolute;
      left: 8px; top: 50%;
      transform: translateY(-50%);
      width: 16px; height: 16px;
      accent-color: var(--accent);
      margin: 0;
      cursor: pointer;
    }
    .tab-btn.active {
      color: var(--accent);
      border-top-color: var(--accent);
      font-weight: bold;
    }
    .tab-btn.all {
      font-weight: bold;
      color: var(--accent);
      border-top-color: var(--accent);
    }
    kbd {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 3px; padding: 1px 6px;
      font-family: ui-monospace, monospace; font-size: 11px;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--muted); }
  </style>
</head>
<body>

<header>
  <span class="logo">📰 個人新聞儀表板</span>
  <div class="header-right">
    <span id="meta">載入中...</span>
    <span id="status"></span>
  </div>
</header>

<div class="controls">
  <div class="search-wrap">
    <input type="text" id="keyword" placeholder="🔍 關鍵字篩選…" autocomplete="off">
    <button class="clear-btn" id="clearBtn" onclick="clearKeyword()" title="清除篩選 (Esc)">✕</button>
  </div>
  <button class="btn btn-primary" onclick="refreshNow()" title="立即刷新 (R)">⟳ 立即刷新</button>
  <span id="countdown"></span>
</div>

<main class="grid" id="grid">
  <div class="loading-state">
    <div class="spinner"></div>
    <span>📡 正在抓取新聞，請稍候…</span>
  </div>
</main>

<nav id="tabs">
  <!-- 由 JS 動態產生 -->
  <div class="tab-hints">
    <span><kbd>R</kbd> 刷新</span>
    <span><kbd>F</kbd> 篩選</span>
    <span><kbd>Esc</kbd> 清除</span>
  </div>
</nav>

<script>
  const REFRESH_INTERVAL = __REFRESH_INTERVAL__;
  const INITIAL_KEYWORD  = __INITIAL_KEYWORD__;

  let allData        = { categories: {}, last_updated: null, status: '' };
  let selectedCats  = new Set(); // 多選分類
  let catsList      = [];
  let countdownVal   = REFRESH_INTERVAL;
  let countdownTimer = null;
  let firstLoad      = true;

  /* ── Fetch news ── */
  async function fetchNews() {
    try {
      const res = await fetch('/api/news');
      if (!res.ok) throw new Error(res.statusText);
      allData = await res.json();
      catsList = Object.keys(allData.categories || {});
      
      // 修正點 1：如果是第一次載入且尚未選擇，則預設全選
      if (selectedCats.size === 0) {
        catsList.forEach(cat => selectedCats.add(cat));
      }
      
      if (firstLoad && INITIAL_KEYWORD) {
        document.getElementById('keyword').value = INITIAL_KEYWORD;
        firstLoad = false;
      }

      // 修正點 2：必須呼叫 renderTabs 才能顯示底部的按鈕
      renderTabs(catsList);
      render();
      resetCountdown();
    } catch (e) {
      document.getElementById('status').textContent = '⚠ 連線失敗';
    }
  }

  /* ── Manual refresh ── */
  async function refreshNow() {
    document.getElementById('status').textContent = '⏳ 正在刷新…';
    try {
      await fetch('/api/refresh', { method: 'POST' });
      await fetchNews();
    } catch (e) {
      document.getElementById('status').textContent = '⚠ 刷新失敗';
    }
  }

  /* ── Clear keyword ── */
  function clearKeyword() {
    document.getElementById('keyword').value = '';
    document.getElementById('clearBtn').style.display = 'none';
    render();
  }

  /* ── Render ── */
  function render() {
    const keyword  = document.getElementById('keyword').value.trim();
    const grid     = document.getElementById('grid');
    const meta     = document.getElementById('meta');
    const statusEl = document.getElementById('status');

    document.getElementById('clearBtn').style.display = keyword ? 'block' : 'none';

    if (allData.last_updated) meta.textContent = `上次更新：${allData.last_updated}`;
    statusEl.textContent = allData.status || '';

    const visibleCats = catsList.filter(cat => selectedCats.has(cat));
    grid.innerHTML = visibleCats.length
      ? visibleCats.map(cat => renderCategory(cat, allData.categories[cat] || [], keyword)).join('')
      : '<div class="loading-state"><span>（請選擇要顯示的分類）</span></div>';
  }

  /* ── Render tab bar ── */
  function renderTabs(cats) {
    const nav = document.getElementById('tabs');
    const hints = nav.querySelector('.tab-hints');
    nav.querySelectorAll('.tab-btn').forEach(el => el.remove());
    // 全部 tab
    const allBtn = document.createElement('button');
    allBtn.className = 'tab-btn all';
    allBtn.innerHTML = `<input type="checkbox" ${selectedCats.size === cats.length ? 'checked' : ''} onclick="event.stopPropagation();toggleAllCats()">📋 全部`;
    allBtn.onclick = () => toggleAllCats();
    nav.insertBefore(allBtn, hints);
    // 各分類 tab
    cats.forEach(cat => {
      const btn = document.createElement('button');
      btn.className = 'tab-btn' + (selectedCats.has(cat) ? ' active' : '');
      btn.innerHTML = `<input type="checkbox" ${selectedCats.has(cat) ? 'checked' : ''} onclick="event.stopPropagation();toggleCat('${cat.replace(/'/g, "\\'")}')">${cat}`;
      btn.onclick = () => toggleCat(cat);
      nav.insertBefore(btn, hints);
    });
  }

  window.toggleCat = function(cat) {
    if (selectedCats.has(cat)) {
      selectedCats.delete(cat);
    } else {
      selectedCats.add(cat);
    }
    renderTabs(catsList); // 重新渲染 Tab 以更新 checkbox 狀態與顏色
    render();
  }

  window.toggleAllCats = function() {
    if (selectedCats.size === catsList.length) {
      selectedCats.clear();
    } else {
      catsList.forEach(cat => selectedCats.add(cat));
    }
    renderTabs(catsList);
    render();
  }

  /* ── Render one category card ── */
  function renderCategory(cat, articles, keyword) {
    const kw = keyword.toLowerCase();
    const filtered = kw
      ? articles.filter(a =>
          a.title.toLowerCase().includes(kw) || a.summary.toLowerCase().includes(kw))
      : articles;

    let body;
    if (filtered.length === 0) {
      const msg = articles.length === 0
        ? '（尚無文章，請稍候…）'
        : `（無符合「${esc(keyword)}」的文章）`;
      body = `<li class="empty-msg">${msg}</li>`;
    } else {
      body = filtered.map((a, i) => {
        const titleInner = highlight(esc(a.title), keyword);
        const titleEl = a.url
          ? `<a class="article-title" href="${esc(a.url)}" target="_blank" rel="noopener noreferrer">${titleInner}</a>`
          : `<span class="article-title">${titleInner}</span>`;
        const thumbEl = a.image
          ? `<img class="article-thumb" src="${esc(a.image)}" alt="" loading="lazy" onerror="this.parentElement.classList.add('no-thumb');this.remove()">`
          : '';
        return `
          <li class="article-item${a.image ? '' : ' no-thumb'}">
            <span class="article-num">${i + 1}</span>
            ${thumbEl}
            <div class="article-body">${titleEl}</div>
            <div class="article-meta">
              <span class="source" title="${esc(a.source)}">${esc(a.source)}</span>
              <span class="pub-time">${esc(a.time || '—')}</span>
            </div>
          </li>`;
      }).join('');
    }

    return `
      <div class="card">
        <div class="card-header">
          <span>${esc(cat)}</span>
          <span class="card-count">${filtered.length} 篇</span>
        </div>
        <ul class="article-list">${body}</ul>
      </div>`;
  }

  /* ── Highlight keyword in already-escaped HTML ── */
  function highlight(html, keyword) {
    if (!keyword) return html;
    try {
      const pat = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return html.replace(new RegExp(pat, 'gi'), m => `<mark>${m}</mark>`);
    } catch (_) { return html; }
  }

  /* ── HTML escape ── */
  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ── Countdown ── */
  function resetCountdown() {
    clearInterval(countdownTimer);
    countdownVal = REFRESH_INTERVAL;
    tick();
    countdownTimer = setInterval(() => { countdownVal--; tick(); if (countdownVal <= 0) fetchNews(); }, 1000);
  }
  function tick() {
    const m = Math.floor(countdownVal / 60), s = countdownVal % 60;
    document.getElementById('countdown').textContent =
      m > 0 ? `${m} 分 ${s} 秒後自動刷新` : `${s} 秒後自動刷新`;
  }

  /* ── Keyboard shortcuts ── */
  document.addEventListener('keydown', e => {
    const isInput = document.activeElement.tagName === 'INPUT';
    if (e.key === 'Escape') { clearKeyword(); document.activeElement.blur(); return; }
    if (isInput) { if (e.key === 'Enter') render(); return; }
    if (e.key === 'r' || e.key === 'R') { e.preventDefault(); refreshNow(); }
    if (e.key === 'f' || e.key === 'F') { e.preventDefault(); document.getElementById('keyword').focus(); }
  });

  /* ── Live filter on input ── */
  document.getElementById('keyword').addEventListener('input', render);

  /* ── Init ── */
  fetchNews();

</script>
</body>
</html>"""

# ── PWA Manifest ──────────────────────────────────
_MANIFEST = json.dumps({
    "name":             "📰 個人新聞儀表板",
    "short_name":       "新聞儀表板",
    "start_url":        "/",
    "display":          "standalone",
    "background_color": "#0d1117",
    "theme_color":      "#161b22",
    "orientation":      "portrait",
    "icons": [
        {"src": "/icon.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/icon.png", "sizes": "512x512", "type": "image/png"},
    ],
}, ensure_ascii=False)


# ── 主控制器 ─────────────────────────────────────
class NewsDashboard:
    """管理新聞資料與背景自動刷新"""

    def __init__(self, refresh_interval: int, max_articles: int) -> None:
        self.refresh_interval = refresh_interval
        self.max_articles     = max_articles
        self.initial_keyword  = ""
        self.data             = {cat: [] for cat in RSS_FEEDS}
        self.last_updated: Optional[datetime] = None
        self.status           = ""
        self._lock            = threading.Lock()
        self._quit            = False
        self._trigger         = threading.Event()

    def _do_fetch(self) -> None:
        with self._lock:
            self.status = "⏳ 正在刷新..."
        try:
            new_data = fetch_all(RSS_FEEDS)
            with self._lock:
                self.data         = new_data
                self.last_updated = datetime.now()
                self.status       = ""
        except Exception as exc:
            with self._lock:
                self.status = f"⚠ 刷新失敗：{exc}"

    def _refresh_worker(self) -> None:
        while not self._quit:
            self._trigger.wait(timeout=self.refresh_interval)
            if self._quit:
                break
            self._trigger.clear()
            self._do_fetch()

    def stop(self) -> None:
        self._quit = True
        self._trigger.set()


# ── Flask 路由 ────────────────────────────────────
@app.route("/manifest.json")
def pwa_manifest() -> Response:
    return Response(_MANIFEST, content_type="application/manifest+json")


@app.route("/icon.png")
def pwa_icon() -> Response:
    # 192x192 深色圖示（SVG 轉 PNG，直接用 1像素 PNG base64 占位符）
    import base64
    # 1像素黑色 PNG，勝於回傳 404
    _1px = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    return Response(_1px, content_type="image/png")


@app.route("/")
def index() -> Response:
    assert _dashboard is not None
    html = (_HTML
            .replace("__REFRESH_INTERVAL__", str(_dashboard.refresh_interval))
            .replace("__INITIAL_KEYWORD__",  json.dumps(_dashboard.initial_keyword)))
    return Response(html, content_type="text/html; charset=utf-8")


@app.route("/api/news")
def api_news() -> Response:
    assert _dashboard is not None
    with _dashboard._lock:
        data         = _dashboard.data
        last_updated = _dashboard.last_updated
        status       = _dashboard.status
        max_articles = _dashboard.max_articles

    categories: dict = {}
    for cat, articles in data.items():
        limit = MAX_ARTICLES_ENGLISH if cat in ENGLISH_CATEGORIES else max_articles
        categories[cat] = [
            {
                "title":   a.title,
                "url":     a.url,
                "source":  a.source,
                "time":    a.published.strftime("%m/%d %H:%M") if a.published else "",
                "summary": a.summary,
                "image":   a.image,
            }
            for a in articles[:limit]
        ]

    return jsonify({
        "categories":   categories,
        "last_updated": last_updated.strftime("%H:%M:%S") if last_updated else None,
        "status":       status,
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh() -> Response:
    assert _dashboard is not None
    _dashboard._trigger.set()
    return jsonify({"ok": True})


# ── 取得區域網路 IP ────────────────────────────────
def _local_ip() -> str:
    """取得本機在區域網路中的 IP 位址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── 開啟瀏覽器 ────────────────────────────────────
def _open_browser(url: str) -> None:
    """優先嘗試 Chrome，否則使用系統預設瀏覽器"""
    if sys.platform == "win32":
        try:
            subprocess.Popen(f'start chrome "{url}"', shell=True)
            return
        except Exception:
            pass
    webbrowser.open(url)


# ── 進入點 ────────────────────────────────────────
def main() -> None:
    global _dashboard

    parser = argparse.ArgumentParser(
        prog="news_dashboard",
        description="📰 個人新聞儀表板 — Web 版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--keyword", "-k", default="", metavar="關鍵字",
                        help="啟動時設定篩選關鍵字")
    parser.add_argument("--refresh", "-r", type=int, default=REFRESH_INTERVAL,
                        metavar="秒", help=f"自動刷新間隔，單位秒（預設 {REFRESH_INTERVAL}）")
    parser.add_argument("--max", "-m", type=int, default=MAX_ARTICLES_PER_CATEGORY,
                        metavar="篇數", help=f"每類別最多顯示篇數（預設 {MAX_ARTICLES_PER_CATEGORY}）")
    parser.add_argument("--port", "-p", type=int, default=5555,
              metavar="埠號", help="Web 伺服器埠號（預設 5555）")
    args = parser.parse_args()

    _dashboard                 = NewsDashboard(args.refresh, args.max)
    _dashboard.initial_keyword = args.keyword

    print("📡 正在抓取新聞，請稍候...")
    _dashboard._do_fetch()

    worker = threading.Thread(target=_dashboard._refresh_worker, daemon=True)
    worker.start()

    local_ip = _local_ip()
    url_local = f"http://127.0.0.1:{args.port}"
    url_lan   = f"http://{local_ip}:{args.port}"
    print(f"\u2705 新聞抓取完成，啟動 Web 伺服器")
    print(f"   本機： {url_local}")
    print(f"   iPhone（同一 WiFi）： {url_lan}")
    print("   iPhone 步驟：Safari 開啟上方網址 → 分享按鈕 → 加入主畫面")
    print("   （Ctrl+C 停止伺服器）\n")

    threading.Timer(1.0, _open_browser, args=(url_local,)).start()

    try:
        app.run(host="0.0.0.0", port=args.port,
                threaded=True, use_reloader=False, debug=False)
    except KeyboardInterrupt:
        pass
    finally:
        _dashboard.stop()
        print("\n已停止伺服器。")


if __name__ == "__main__":
    main()
