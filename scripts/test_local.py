"""
ローカルテスト用スクリプト
メール送信はせず、Notion 取得 → 推論まで動作確認する
"""
import os
import sys
import json

# src ディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notion_secretary import NotionSecretaryClient
from ai_organizer import AIOrganizer


def main():
    notion = NotionSecretaryClient(
        api_key=os.environ["NOTION_API_KEY"],
        database_id=os.environ["NOTION_DATABASE_ID"],
    )
    organizer = AIOrganizer(
        api_key=os.environ["STRAICO_API_KEY"],
        model=os.environ.get("STRAICO_MODEL", "anthropic/claude-opus-4-7"),
    )

    print("Inbox を取得中...")
    pages = notion.fetch_inbox_pages()
    print(f"  {len(pages)} 件取得")

    existing_tags = notion.fetch_existing_tags()
    print(f"既存タグ: {existing_tags}")

    for page in pages:
        title = NotionSecretaryClient.get_page_title(page)
        page_id = NotionSecretaryClient.get_page_id(page)
        body = notion.fetch_page_content(page_id)
        created_time = NotionSecretaryClient.get_created_time(page)

        print(f"\n--- {title} ---")
        result = organizer.organize_page(
            title=title,
            body=body,
            created_time=created_time,
            existing_tags=existing_tags,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
