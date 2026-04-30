import feedparser
import webbrowser
import os
from datetime import datetime

# 1. RSS 配置 (範例)
RSS_CONFIG = {
    "📰 即時新聞": "https://www.cna.com.tw/rss/aall.aspx",
    "💰 財經": "https://udn.com/rssfeed/news/2/FIN",
    "🤖 科技": "https://www.ithome.com.tw/rss",
    "🏠 生活": "https://news.ltn.com.tw/rss/life.xml"
}

def fetch_news_data():
    """抓取新聞並過濾髒資料"""
    final_data = {}
    print("正在抓取最新新聞...")
    
    for category, url in RSS_CONFIG.items():
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries:
            # --- 修正點 1：過濾 None 或無效標題 ---
            title = entry.get('title')
            if not title or str(title).strip().lower() in ['none', '']:
                continue
            
            # --- 修正點 2：處理日期並過濾 1970 ---
            pub_date = "最近更新"
            published_parsed = entry.get('published_parsed')
            if published_parsed:
                dt = datetime(*published_parsed[:6])
                if dt.year > 2000: # 排除 1970 年等錯誤日期
                    pub_date = dt.strftime("%m-%d %H:%M")

            articles.append({
                'title': title,
                'link': entry.get('link', '#'),
                'source': category,
                'date': pub_date
            })
            
        final_data[category] = articles[:12] # 每個分類取前 12 則
    return final_data

def generate_html(data_dict):
    """生成包含過濾、更新按鈕、主題切換的 HTML"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 開始組合 HTML 模板
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>個人新聞儀表板</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f0f2f5; font-family: "Microsoft JhengHei", sans-serif; }}
            .header-section {{ background: white; padding: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 25px; }}
            .filter-panel {{ 
                background: #fff; padding: 15px; border-radius: 12px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 30px; 
            }}
            .category-section {{ margin-bottom: 40px; }}
            .category-title {{ border-left: 5px solid #0d6efd; padding-left: 15px; margin-bottom: 20px; font-weight: bold; }}
            .news-card {{ transition: all 0.2s; height: 100%; border: none; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
            .news-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.12); }}
            .news-title {{ font-size: 1rem; font-weight: 600; color: #212529; text-decoration: none; display: block; }}
            .news-title:hover {{ color: #0d6efd; }}
            .source-badge {{ font-size: 0.75rem; background-color: #f1f3f5; color: #495057; padding: 3px 10px; border-radius: 20px; }}
            .update-btn {{ border-radius: 20px; padding: 5px 20px; font-weight: bold; }}
            footer {{ margin-top: 50px; padding: 30px; text-align: center; color: #adb5bd; }}
        </style>
    </head>
    <body>
        <div class="header-section">
            <div class="container">
                <div class="d-flex justify-content-between align-items-center">
                    <h1 class="fw-bold m-0">📰 個人新聞儀表板</h1>
                    <div class="text-end">
                        <div class="text-muted small mb-1">最後更新：{now}</div>
                        <button onclick="location.reload()" class="btn btn-primary btn-sm update-btn">🔄 立即更新</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="container">
            <div class="filter-panel">
                <div class="d-flex align-items-center flex-wrap">
                    <span class="fw-bold me-3">📌 主題篩選：</span>
                    <div class="form-check form-check-inline">
                        <input class="form-check-input" type="checkbox" id="selectAll" checked onclick="toggleAll(this)">
                        <label class="form-check-label fw-bold" for="selectAll">全選</label>
                    </div>
                    <span class="mx-2 text-muted">|</span>
    """

    # 動態產生分類勾選框
    for i, category in enumerate(data_dict.keys()):
        html_template += f"""
                    <div class="form-check form-check-inline">
                        <input class="form-check-input cat-checkbox" type="checkbox" 
                               id="check-{i}" data-target="section-{i}" checked 
                               onclick="updateVisibility()">
                        <label class="form-check-label" for="check-{i}">{category}</label>
                    </div>
        """

    html_template += """
                </div>
            </div>
    """

    # 產生新聞卡片內容
    for i, (category, articles) in enumerate(data_dict.items()):
        if not articles: continue
        
        html_template += f"""
            <div class="category-section" id="section-{i}">
                <h3 class="category-title">{category}</h3>
                <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3">
        """
        
        for art in articles:
            # 這裡再次確保標題不是 "None"
            if str(art['title']).lower() == 'none': continue
            
            html_template += f"""
                    <div class="col">
                        <div class="card news-card">
                            <div class="card-body d-flex flex-column">
                                <a href="{art['link']}" target="_blank" class="news-title mb-3">{art['title']}</a>
                                <div class="mt-auto d-flex justify-content-between align-items-center">
                                    <span class="source-badge">{art['source']}</span>
                                    <small class="text-muted">{art['date']}</small>
                                </div>
                            </div>
                        </div>
                    </div>
            """
        html_template += '</div></div>'

    # 加入 JavaScript 控制邏輯
    html_template += """
            <footer>&copy; 2024 Personal News Dashboard | Python 自动化抓取</footer>
        </div>

        <script>
            // 儲存目前狀態到瀏覽器，下次開啟會記住勾選
            function saveState() {
                const states = {};
                document.querySelectorAll('.cat-checkbox').forEach(cb => {
                    states[cb.id] = cb.checked;
                });
                localStorage.setItem('news_filter_config', JSON.stringify(states));
            }

            function loadState() {
                const saved = localStorage.getItem('news_filter_config');
                if (saved) {
                    const states = JSON.parse(saved);
                    Object.keys(states).forEach(id => {
                        const cb = document.getElementById(id);
                        if (cb) cb.checked = states[id];
                    });
                }
                updateVisibility();
            }

            function updateVisibility() {
                document.querySelectorAll('.cat-checkbox').forEach(cb => {
                    const targetId = cb.getAttribute('data-target');
                    const targetEl = document.getElementById(targetId);
                    if (targetEl) targetEl.style.display = cb.checked ? 'block' : 'none';
                });
                saveState();
            }

            function toggleAll(master) {
                document.querySelectorAll('.cat-checkbox').forEach(cb => {
                    cb.checked = master.checked;
                });
                updateVisibility();
            }

            // 初始化
            window.onload = loadState;
        </script>
    </body>
    </html>
    """
    
    # 寫入檔案
    file_path = os.path.abspath("news.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\n✅ 儀表板已更新！路徑: {file_path}")
    return file_path

if __name__ == "__main__":
    data = fetch_news_data()
    path = generate_html(data)
    
    # 自動開啟瀏覽器
    webbrowser.open("file://" + path.replace("\\", "/"))