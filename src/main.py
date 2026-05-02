"""
📋 AI 秘書 - メインエントリポイント

GitHub Actions から daily-organize.yml で呼び出される。
処理フロー:
  1. Notion から Status=Inbox のページを取得
  2. 各ページを Straico (OpenAI互換) 経由で推論
  3. Notion のプロパティを更新
  4. 整理結果を HTML メールで送信
"""
import os
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from notion_secretary import NotionSecretaryClient
from ai_organizer import AIOrganizer
from email_sender import EmailSender
from html_template import build_html_email, build_empty_email, format_date_jp


JST = ZoneInfo("Asia/Tokyo")


def get_env(name: str, required: bool = True, default: str = "") -> str:
    """環境変数を取得。required=True で未設定なら異常終了"""
    value = os.environ.get(name, default)
    if required and not value:
        print(f"❌ ERROR: 環境変数 {name} が設定されていません")
        sys.exit(1)
    return value


def main() -> None:
    print("=" * 60)
    print("📋 AI 秘書 - 開始")
    print("=" * 60)

    # 環境変数の取得
    straico_api_key = get_env("STRAICO_API_KEY")
    notion_api_key = get_env("NOTION_API_KEY")
    notion_database_id = get_env("NOTION_DATABASE_ID")
    gmail_user = get_env("GMAIL_USER")
    gmail_app_password = get_env("GMAIL_APP_PASSWORD")
    recipient_email = get_env("RECIPIENT_EMAIL")
    straico_model = get_env("STRAICO_MODEL", required=False, default="anthropic/claude-opus-4-7")

    recipients = [r.strip() for r in recipient_email.split(",") if r.strip()]
    today = datetime.now(JST)
    date_str = format_date_jp(today)
    notion_db_url = f"https://www.notion.so/{notion_database_id.replace('-', '')}"

    print(f"📅 実行日時: {today.isoformat()}")
    print(f"📧 送信先: {', '.join(recipients)}")
    print(f"🤖 モデル: {straico_model} (via Straico)")
    print()

    # クライアント初期化
    notion = NotionSecretaryClient(notion_api_key, notion_database_id)
    organizer = AIOrganizer(straico_api_key, model=straico_model)
    sender = EmailSender(gmail_user, gmail_app_password)

    # ========== STEP 1: Inbox ページ取得 ==========
    print("STEP 1: Notion から Inbox ページを取得中...")
    try:
        inbox_pages = notion.fetch_inbox_pages()
    except Exception as e:
        print(f"❌ Notion 取得エラー: {e}")
        traceback.print_exc()
        sys.exit(1)
    print(f"  → {len(inbox_pages)} 件取得")

    # 0件の場合は空メールを送って終了
    if not inbox_pages:
        print("\nInbox は空です。空メールを送信します。")
        html = build_empty_email(today, notion_db_url)
        subject = f"📋 AI 秘書 朝の整理レポート — {date_str}"
        try:
            sender.send_html(recipients, subject, html)
            print("✅ メール送信完了")
        except Exception as e:
            print(f"❌ メール送信エラー: {e}")
            traceback.print_exc()
            sys.exit(1)
        print("\n=== 完了 ===")
        return

    # 既存タグ一覧を取得（LLM のヒントとして使う）
    print("\n既存タグを取得中...")
    try:
        existing_tags = notion.fetch_existing_tags()
        print(f"  → {len(existing_tags)} 件: {existing_tags}")
    except Exception as e:
        print(f"⚠️ 既存タグ取得失敗（処理続行）: {e}")
        existing_tags = []

    # ========== STEP 2-3: 推論 + Notion 更新 ==========
    print(f"\nSTEP 2-3: 各ページを推論し、Notion を更新中...")
    activated_items = []
    remained_items = []
    failed_count = 0

    for idx, page in enumerate(inbox_pages, 1):
        page_id = NotionSecretaryClient.get_page_id(page)
        title = NotionSecretaryClient.get_page_title(page)
        url = NotionSecretaryClient.get_page_url(page)
        created_time = NotionSecretaryClient.get_created_time(page)

        print(f"\n[{idx}/{len(inbox_pages)}] {title}")

        # 本文を取得
        try:
            body = notion.fetch_page_content(page_id)
        except Exception as e:
            print(f"  ⚠️ 本文取得失敗: {e}")
            body = ""

        # Straico (LLM) で推論
        try:
            result = organizer.organize_page(
                title=title,
                body=body,
                created_time=created_time,
                existing_tags=existing_tags,
            )
            print(f"  → Type={result.get('type')} / Tags={result.get('tags')} / "
                  f"Priority={result.get('priority')} / Due={result.get('due_date')} / "
                  f"Status={result.get('status')}")
        except Exception as e:
            print(f"  ❌ 推論エラー: {e}")
            failed_count += 1
            remained_items.append({
                "title": title,
                "url": url,
                "type": "Memo",
                "tags": [],
                "priority": None,
                "due_date": None,
                "reason": f"推論エラー: {str(e)[:80]}",
            })
            continue

        # Notion 更新
        try:
            notion.update_page_properties(
                page_id=page_id,
                type_value=result.get("type"),
                tags=result.get("tags", []),
                priority=result.get("priority"),
                due_date=result.get("due_date"),
                status=result.get("status"),
            )
            print(f"  ✅ Notion 更新完了")
        except Exception as e:
            print(f"  ⚠️ Notion 更新失敗: {e}")
            failed_count += 1

        # 結果リストに追加
        item = {
            "title": title,
            "url": url,
            "type": result.get("type", "Memo"),
            "tags": result.get("tags", []),
            "priority": result.get("priority"),
            "due_date": result.get("due_date"),
            "reason": result.get("reason", ""),
        }
        if result.get("status") == "Active":
            activated_items.append(item)
        else:
            remained_items.append(item)

    # ========== STEP 4: HTML メール送信 ==========
    print(f"\nSTEP 4: HTML メールを送信中...")
    print(f"  整理完了: {len(activated_items)} 件")
    print(f"  要・人手判断: {len(remained_items)} 件")
    print(f"  失敗: {failed_count} 件")

    html = build_html_email(
        today=today,
        activated_items=activated_items,
        remained_items=remained_items,
        notion_db_url=notion_db_url,
        failed_count=failed_count,
    )
    subject = f"📋 AI 秘書 朝の整理レポート — {date_str}"

    try:
        sender.send_html(recipients, subject, html)
        print("✅ メール送信完了")
    except Exception as e:
        print(f"❌ メール送信エラー: {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 全処理完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
