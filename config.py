"""個人新聞儀表板 — 設定檔"""

# ──────────────────────────────────────────────
#  RSS 來源設定（按類別分組，可自由新增或刪除）
# ──────────────────────────────────────────────
RSS_FEEDS: dict[str, list[str]] = {
    "📰 即時新聞": [
        "https://www.cna.com.tw/rss/aall.aspx",          # 中央社即時
        "https://news.ltn.com.tw/rss/all.xml",            # 自由時報即時
        "https://udn.com/rssfeed/news/2/BREAKINGNEWS",    # 聯合新聞網即時
    ],
    "🤖 科技 / AI（中文）": [
        "https://www.ithome.com.tw/rss",                  # iThome
        "https://www.bnext.com.tw/rss",                   # 數位時代
        "https://technews.tw/rss/",                       # TechNews 科技新聞
    ],
    "🔬 Tech / AI（EN）": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",  # TechCrunch AI
        "https://feeds.arstechnica.com/arstechnica/ai",   # Ars Technica AI
        "https://www.theverge.com/rss/index.xml",         # The Verge
        "https://hnrss.org/frontpage",                    # Hacker News 頭版
    ],
    "💰 財經": [
        "https://news.cnyes.com/rss/tw/index.xml",        # 鉅亨網台股
        "https://tw.news.yahoo.com/rss/finance",          # Yahoo奇摩財經
        "https://udn.com/rssfeed/news/2/FIN",             # 聯合財經
    ],
    "🌏 國際中文": [
        "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml", # BBC 中文（繁體）
        "https://www.rfa.org/cantonese/rss2.xml",         # 自由亞洲粵語
        "https://www.voachinese.com/api/zmgqo-emq_tpe",   # 美國之音中文
    ],
    "🌍 World News（EN）": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",    # BBC World
        "https://feeds.reuters.com/reuters/topNews",      # Reuters Top News
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT World
        "https://feeds.skynews.com/feeds/rss/world.xml",  # Sky News World
    ],
    "🏠 生活": [
        "https://www.cna.com.tw/rss/alife.aspx",          # 中央社生活
        "https://news.ltn.com.tw/rss/life.xml",           # 自由時報生活
        "https://udn.com/rssfeed/news/2/LIFE",            # 聯合生活
    ],
    "⚽ 體育": [
        "https://www.cna.com.tw/rss/aspt.aspx",           # 中央社體育
        "https://news.ltn.com.tw/rss/sports.xml",         # 自由時報體育
        "https://udn.com/rssfeed/news/2/SPT",             # 聯合體育
    ],
}

# ──────────────────────────────────────────────
#  顯示設定
# ──────────────────────────────────────────────

# 每個類別最多顯示幾篇文章
MAX_ARTICLES_PER_CATEGORY: int = 8

# 英文類別只取 Top 10
ENGLISH_CATEGORIES: set[str] = {"🔬 Tech / AI（EN）", "🌍 World News（EN）"}
MAX_ARTICLES_ENGLISH: int = 10

# 自動刷新間隔（秒），預設 5 分鐘
REFRESH_INTERVAL: int = 300

# HTTP 請求逾時（秒）
REQUEST_TIMEOUT: int = 10
