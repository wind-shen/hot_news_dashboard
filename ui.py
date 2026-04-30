"""Rich TUI 渲染模組 — 建立儀表板畫面佈局"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from rich import box
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from fetcher import Article


# ── 文章表格 ────────────────────────────────────
def make_article_table(
    articles: List[Article],
    keyword: str = "",
    max_items: int = 8,
) -> Table:
    """產生單一類別的文章列表 Table"""
    table = Table(
        box=box.SIMPLE_HEAD,
        header_style="bold cyan",
        expand=True,
        padding=(0, 1),
        show_lines=False,
        show_footer=False,
    )
    table.add_column("#",  style="dim",          width=3,  no_wrap=True)
    table.add_column("標題",                      ratio=5,  overflow="fold")
    table.add_column("來源", style="bright_green", ratio=2,  no_wrap=True)
    table.add_column("時間", style="dim",          width=11, no_wrap=True)

    filtered = [a for a in articles if a.matches(keyword)]
    shown    = filtered[:max_items]

    if not shown:
        msg = "（尚無文章，請稍候...）" if not articles else f"（無符合「{keyword}」的文章）"
        table.add_row("—", Text(msg, style="italic dim"), "", "")
        return table

    for i, art in enumerate(shown, 1):
        pub   = art.published.strftime("%m/%d %H:%M") if art.published else "—"
        title = _highlight(art.title, keyword)
        table.add_row(str(i), title, art.source, pub)

    return table


def _highlight(text: str, keyword: str) -> Text:
    """在文字中標亮關鍵字"""
    t = Text(text)
    if keyword:
        t.highlight_words([keyword], style="bold yellow on dark_red", case_sensitive=False)
    return t


# ── 頁首 / 頁尾 ─────────────────────────────────
def _make_header(
    last_updated: Optional[datetime],
    refresh_interval: int,
    keyword: str,
    status: str,
) -> Panel:
    upd  = last_updated.strftime("%H:%M:%S") if last_updated else "等待中..."
    mins = refresh_interval // 60
    secs = refresh_interval % 60
    interval_str = f"{mins} 分鐘" if secs == 0 else f"{refresh_interval} 秒"

    parts: list[str] = [
        f"[bold white]📰  個人新聞儀表板[/]  "
        f"[dim]上次更新：{upd}  │  每 {interval_str} 自動刷新[/dim]"
    ]
    if keyword:
        parts.append(f"   [bold yellow]🔍 篩選：{keyword}[/]")
    if status:
        parts.append(f"   [bold red]{status}[/]")

    return Panel(Text.from_markup("".join(parts)), style="bold blue", height=3)


def _make_footer() -> Panel:
    return Panel(
        Text.from_markup(
            "[dim]  [bold white]R[/] 立即刷新  "
            "[bold white]F[/] 關鍵字篩選  "
            "[bold white]C[/] 清除篩選  "
            "[bold white]Q[/] 退出[/dim]"
        ),
        height=3,
    )


# ── 主佈局 ──────────────────────────────────────
def build_dashboard(
    data: Dict[str, List[Article]],
    keyword: str,
    last_updated: Optional[datetime],
    refresh_interval: int,
    max_articles: int,
    status: str = "",
) -> Layout:
    """組合完整的儀表板 Layout（頁首 + 2欄新聞 + 頁尾）"""
    cats = list(data.keys())

    # ── 根佈局 ──
    root = Layout()
    root.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    root["header"].update(_make_header(last_updated, refresh_interval, keyword, status))
    root["footer"].update(_make_footer())

    # ── 載入中佔位 ──
    if not cats:
        root["body"].update(Panel("[dim]正在載入新聞，請稍候...[/dim]", border_style="dim"))
        return root

    # ── 建立每個類別 Panel ──
    def _cat_layout(cat: str, name: str) -> Layout:
        tbl = make_article_table(data.get(cat, []), keyword, max_articles)
        return Layout(
            Panel(tbl, title=cat, border_style="cyan", padding=(0, 1)),
            name=name,
        )

    # ── 2 欄佈局：左半 / 右半 ──
    mid        = (len(cats) + 1) // 2
    left_cats  = cats[:mid]
    right_cats = cats[mid:]

    left_panels  = [_cat_layout(c, f"l{i}") for i, c in enumerate(left_cats)]
    right_panels = [_cat_layout(c, f"r{i}") for i, c in enumerate(right_cats)]

    if right_panels:
        root["body"].split_row(
            Layout(name="col_l"),
            Layout(name="col_r"),
        )
        root["col_l"].split_column(*left_panels)
        root["col_r"].split_column(*right_panels)
    else:
        # 只有一欄（類別數 <= 1）
        root["body"].split_column(*left_panels)

    return root
