"""RSS 新聞抓取模組 — 並行抓取、解析、排序"""
from __future__ import annotations

import concurrent.futures
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import feedparser
import requests

from config import REQUEST_TIMEOUT

# ── 預編譯正則 ──────────────────────────────────
_HTML_RE  = re.compile(r"<[^>]+>")
_WS_RE    = re.compile(r"\s+")
_IMG_RE   = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_HEADERS  = {"User-Agent": "PersonalNewsDashboard/1.0"}


# ── 資料模型 ────────────────────────────────────
@dataclass
class Article:
    title:     str
    source:    str
    url:       str
    published: Optional[datetime]
    summary:   str
    image:     str = ""

    def matches(self, keyword: str) -> bool:
        """判斷文章是否包含關鍵字（大小寫不分）"""
        if not keyword:
            return True
        kw = keyword.lower()
        return kw in self.title.lower() or kw in self.summary.lower()


# ── 輔助函式 ────────────────────────────────────
def _clean(text: str) -> str:
    """移除 HTML 標籤並壓縮空白"""
    return _WS_RE.sub(" ", _HTML_RE.sub(" ", text)).strip()


def _extract_image(entry) -> str:
    """從 feedparser entry 擷取縮圖 URL，找不到回傳空字串"""
    # 1. media:thumbnail
    thumbs = getattr(entry, "media_thumbnail", None)
    if thumbs:
        url = thumbs[0].get("url", "")
        if url:
            return url
    # 2. media:content（圖片類型）
    media = getattr(entry, "media_content", None)
    if media:
        for m in media:
            if m.get("medium") == "image" or (m.get("type", "")).startswith("image/"):
                url = m.get("url", "")
                if url:
                    return url
        # 若無明確 type，取第一個有 url 的
        url = media[0].get("url", "")
        if url:
            return url
    # 3. enclosure（image/*）
    for enc in getattr(entry, "enclosures", []):
        if str(enc.get("type", "")).startswith("image/"):
            href = enc.get("href", enc.get("url", ""))
            if href:
                return href
    # 4. 從 content / summary HTML 找第一個 <img>
    for field in ("content", "summary", "description"):
        raw = ""
        val = entry.get(field)
        if isinstance(val, list) and val:
            raw = val[0].get("value", "")
        elif isinstance(val, str):
            raw = val
        m = _IMG_RE.search(raw)
        if m:
            return m.group(1)
    return ""


def _parse_dt(entry) -> Optional[datetime]:
    """從 feedparser entry 解析發布時間"""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6])
            except (TypeError, ValueError):
                pass
    return None


# ── 核心函式 ────────────────────────────────────
def fetch_feed(url: str) -> List[Article]:
    """抓取並解析單一 RSS/Atom feed，失敗時回傳空列表"""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        source = _clean(feed.feed.get("title", url))[:40]

        articles: List[Article] = []
        for entry in feed.entries:
            title = _clean(entry.get("title", ""))
            if not title:
                continue
            summary = _clean(
                entry.get("summary", entry.get("description", ""))
            )[:300]
            articles.append(Article(
                title=title,
                source=source,
                url=entry.get("link", ""),
                published=_parse_dt(entry),
                summary=summary,
                image=_extract_image(entry),
            ))
        return articles

    except Exception:
        return []


def fetch_all(feeds: Dict[str, List[str]]) -> Dict[str, List[Article]]:
    """並行抓取所有分類的 RSS feed，依時間倒序排列"""
    result: Dict[str, List[Article]] = {cat: [] for cat in feeds}
    tasks = [(cat, url) for cat, urls in feeds.items() for url in urls]

    workers = min(len(tasks), 12) if tasks else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(fetch_feed, url): cat for cat, url in tasks}
        for future in concurrent.futures.as_completed(future_map):
            cat = future_map[future]
            result[cat].extend(future.result())

    # 每個分類依時間新到舊排列
    for cat in result:
        result[cat].sort(
            key=lambda a: a.published or datetime.min,
            reverse=True,
        )

    return result
