"""
HTML Template
朝の整理レポートを豪華 HTML メールに整形する
"""
from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo


WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]


def format_date_jp(dt: datetime) -> str:
    """2026年5月2日（土）形式に整形"""
    return f"{dt.year}年{dt.month}月{dt.day}日（{WEEKDAY_JP[dt.weekday()]}）"


def format_due_jp(due: str | None) -> str:
    """2026-05-04 → 5月4日 のように整形"""
    if not due:
        return ""
    try:
        d = datetime.strptime(due, "%Y-%m-%d")
        return f"{d.month}月{d.day}日"
    except (ValueError, TypeError):
        return due


def render_priority_badge(priority: str | None) -> str:
    """Priorityバッジ HTML を返す（None の場合は空文字）"""
    if not priority:
        return ""
    if "High" in priority:
        css_class = "badge-priority-high"
    elif "Mid" in priority:
        css_class = "badge-priority-mid"
    else:
        css_class = "badge-priority-low"
    return f'<span class="badge {css_class}">{priority}</span>'


def render_due_badge(due: str | None) -> str:
    if not due:
        return ""
    return f'<span class="badge badge-due">📅 {format_due_jp(due)}</span>'


def render_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    return "".join(f'<span class="item-tag">#{t}</span>' for t in tags)


def render_item(
    title: str,
    type_value: str,
    tags: list[str],
    priority: str | None,
    due: str | None,
    notion_url: str,
    is_remained: bool = False,
    reason: str = "",
) -> str:
    """1アイテムのHTMLブロックを生成"""
    badge_type_class = "badge-type-gray" if is_remained else "badge-type"
    priority_html = render_priority_badge(priority)
    due_html = render_due_badge(due)
    tags_html = render_tags(tags)
    reason_html = f'<div class="item-reason">💭 {reason}</div>' if (is_remained and reason) else ""

    return f"""
<div class="item">
  <div class="item-header">
    <span class="badge {badge_type_class}">{type_value}</span>
    {priority_html}
    {due_html}
  </div>
  <div class="item-title">{title}</div>
  {f'<div class="item-tags">{tags_html}</div>' if tags_html else ""}
  {reason_html}
  <a href="{notion_url}" class="item-link">Notion で開く →</a>
</div>
"""


def build_html_email(
    today: datetime,
    activated_items: list[dict[str, Any]],
    remained_items: list[dict[str, Any]],
    notion_db_url: str,
    failed_count: int = 0,
) -> str:
    """完成した HTML メール本文を返す"""
    total = len(activated_items) + len(remained_items)
    activated_count = len(activated_items)
    remained_count = len(remained_items)
    tasks_count = sum(1 for i in activated_items if i.get("type") == "Task")

    activated_html = "".join(
        render_item(
            title=i["title"],
            type_value=i["type"],
            tags=i.get("tags", []),
            priority=i.get("priority"),
            due=i.get("due_date"),
            notion_url=i["url"],
            is_remained=False,
        )
        for i in activated_items
    )
    if not activated_items:
        activated_html = '<div class="empty">整理完了アイテムはありません</div>'

    remained_html = "".join(
        render_item(
            title=i["title"],
            type_value=i.get("type", "Memo"),
            tags=i.get("tags", []),
            priority=i.get("priority"),
            due=i.get("due_date"),
            notion_url=i["url"],
            is_remained=True,
            reason=i.get("reason", ""),
        )
        for i in remained_items
    )
    if not remained_items:
        remained_html = '<div class="empty">すべて整理されています ✨</div>'

    failed_block = ""
    if failed_count > 0:
        failed_block = f"""
<div class="warning">
  <strong>⚠️ 注意:</strong> {failed_count} 件のページで Notion 更新に失敗しました。
  詳細は GitHub Actions の実行ログを確認してください。
</div>
"""

    date_str = format_date_jp(today)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ margin: 0; padding: 0; background-color: #0a0a14; font-family: 'Helvetica Neue', Arial, sans-serif; }}
  .wrapper {{ max-width: 1200px; margin: 0 auto; background: #ffffff; }}
  .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%); padding: 56px 20px; text-align: center; position: relative; overflow: hidden; }}
  .header-icon {{ font-size: 64px; margin-bottom: 14px; position: relative; }}
  .header-title {{ color: #fff; font-size: 38px; font-weight: 800; margin: 0 0 10px; letter-spacing: -0.5px; position: relative; line-height: 1.3; }}
  .header-subtitle {{ color: rgba(255,255,255,0.85); font-size: 16px; margin: 0; position: relative; }}
  .header-date {{ display: inline-block; margin-top: 20px; background: rgba(255,255,255,0.18); color: #fff; font-size: 14px; padding: 10px 22px; border-radius: 24px; position: relative; }}
  .stats {{ display: flex; padding: 0; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
  .stat {{ flex: 1; padding: 28px 12px; text-align: center; border-right: 1px solid #e2e8f0; }}
  .stat:last-child {{ border-right: none; }}
  .stat-num {{ font-size: 36px; font-weight: 800; color: #6366f1; }}
  .stat-label {{ font-size: 12px; font-weight: 700; letter-spacing: 1.5px; color: #64748b; text-transform: uppercase; margin-top: 6px; }}
  .content {{ padding: 40px 12px; }}
  .section-label {{ font-size: 20px; font-weight: 800; letter-spacing: 0.5px; color: #6366f1; margin-bottom: 24px; padding-left: 14px; border-left: 4px solid #6366f1; }}
  .item {{ border: 1px solid #e2e8f0; border-radius: 14px; padding: 24px 26px; margin-bottom: 18px; position: relative; overflow: hidden; }}
  .item::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, #6366f1, #8b5cf6, #ec4899); }}
  .item-header {{ margin-bottom: 10px; }}
  .badge {{ display: inline-block; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px; letter-spacing: 0.5px; margin-right: 6px; }}
  .badge-type {{ background: #ede9fe; color: #6d28d9; }}
  .badge-type-gray {{ background: #f1f5f9; color: #64748b; }}
  .badge-priority-high {{ background: #fee2e2; color: #dc2626; }}
  .badge-priority-mid {{ background: #fef3c7; color: #d97706; }}
  .badge-priority-low {{ background: #f1f5f9; color: #64748b; }}
  .badge-due {{ background: #dbeafe; color: #2563eb; }}
  .item-title {{ font-size: 21px; font-weight: 700; color: #0f172a; line-height: 1.45; margin: 10px 0 14px; }}
  .item-tags {{ font-size: 12px; color: #64748b; margin-bottom: 10px; }}
  .item-tag {{ display: inline-block; background: #f1f5f9; padding: 3px 8px; border-radius: 4px; margin-right: 4px; }}
  .item-reason {{ font-size: 12px; color: #92400e; background: #fef3c7; padding: 6px 10px; border-radius: 6px; margin-bottom: 10px; }}
  .item-link {{ display: inline-block; color: #6366f1; text-decoration: none; font-size: 13px; font-weight: 600; margin-top: 4px; }}
  .empty {{ background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 14px; padding: 40px; text-align: center; color: #64748b; font-size: 14px; }}
  .warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px; padding: 16px 20px; margin-top: 24px; font-size: 13px; color: #92400e; line-height: 1.6; }}
  .warning strong {{ color: #78350f; }}
  .footer {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 32px; text-align: center; }}
  .footer-title {{ color: #fff; font-weight: 700; font-size: 16px; margin-bottom: 8px; }}
  .footer-text {{ color: #94a3b8; font-size: 13px; line-height: 1.6; }}
  .footer-link {{ display: inline-block; margin-top: 16px; background: linear-gradient(135deg, #6366f1, #ec4899); color: #fff; text-decoration: none; padding: 10px 24px; border-radius: 8px; font-size: 13px; font-weight: 700; }}
</style></head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="header-icon">📋</div>
    <h1 class="header-title">AI 秘書 朝の整理レポート</h1>
    <p class="header-subtitle">昨日のあなたの思考を整え、今日のあなたへ届けます</p>
    <span class="header-date">📅 {date_str}</span>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-num">{total}</div><div class="stat-label">処理件数</div></div>
    <div class="stat"><div class="stat-num">{activated_count}</div><div class="stat-label">整理完了</div></div>
    <div class="stat"><div class="stat-num">{remained_count}</div><div class="stat-label">要・人手判断</div></div>
    <div class="stat"><div class="stat-num">{tasks_count}</div><div class="stat-label">新規タスク</div></div>
  </div>

  <div class="content">
    <div class="section-label">✨ 整理完了アイテム</div>
    {activated_html}

    <div class="section-label" style="margin-top: 36px;">🤔 要・人手判断アイテム</div>
    {remained_html}

    {failed_block}
  </div>

  <div class="footer">
    <div class="footer-title">📋 AI 秘書</div>
    <div class="footer-text">
      昨日の自分から、今日の自分へのバトン。<br>
      未整理アイテムは Notion で確認・修正してください。
    </div>
    <a href="{notion_db_url}" class="footer-link">Notion で開く →</a>
  </div>
</div>
</body>
</html>
"""


def build_empty_email(today: datetime, notion_db_url: str) -> str:
    """Inbox 0件時の簡易メール"""
    date_str = format_date_jp(today)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ margin: 0; padding: 40px; background: #f8fafc; font-family: 'Helvetica Neue', Arial, sans-serif; text-align: center; }}
  .wrapper {{ max-width: 480px; margin: 0 auto; background: #fff; padding: 48px 32px; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .icon {{ font-size: 64px; margin-bottom: 16px; }}
  .title {{ font-size: 22px; font-weight: 800; color: #0f172a; margin-bottom: 8px; }}
  .date {{ color: #64748b; font-size: 13px; margin-bottom: 24px; }}
  .message {{ color: #475569; font-size: 14px; line-height: 1.7; margin-bottom: 24px; }}
  .link {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #ec4899); color: #fff; text-decoration: none; padding: 10px 24px; border-radius: 8px; font-size: 13px; font-weight: 700; }}
</style></head>
<body><div class="wrapper">
  <div class="icon">✨</div>
  <div class="title">整理対象なし</div>
  <div class="date">{date_str}</div>
  <div class="message">AI 秘書 の Inbox は空っぽです。<br>気持ちのいい朝ですね。</div>
  <a href="{notion_db_url}" class="link">AI 秘書 を開く →</a>
</div></body></html>
"""
