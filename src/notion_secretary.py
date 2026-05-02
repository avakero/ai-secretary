"""
Notion API クライアント
📋 AI 秘書 データベースの読み書きを担当
"""
import os
from typing import Any
from notion_client import Client


class NotionSecretaryClient:
    """📋 AI 秘書 データベース専用クライアント"""

    def __init__(self, api_key: str, database_id: str):
        self.client = Client(auth=api_key)
        self.database_id = database_id
        # データソースIDをキャッシュ（DB初回アクセス時に取得）
        self._data_source_id: str | None = None

    def _get_data_source_id(self) -> str:
        """DBの最初のデータソースIDを取得（Notion APIの仕様変更対応）"""
        if self._data_source_id:
            return self._data_source_id
        db = self.client.databases.retrieve(database_id=self.database_id)
        # 新APIでは data_sources、旧APIでは database_id 自体がそのまま使える
        data_sources = db.get("data_sources", [])
        if data_sources:
            self._data_source_id = data_sources[0]["id"]
        else:
            # フォールバック：データベースIDをそのまま使う
            self._data_source_id = self.database_id
        return self._data_source_id

    def fetch_inbox_pages(self) -> list[dict[str, Any]]:
        """Status=Inbox のページを全件取得（ページネーション対応）"""
        results = []
        next_cursor = None
        while True:
            kwargs = {
                "database_id": self.database_id,
                "filter": {
                    "property": "Status",
                    "select": {"equals": "Inbox"},
                },
                "page_size": 100,
            }
            if next_cursor:
                kwargs["start_cursor"] = next_cursor
            response = self.client.databases.query(**kwargs)
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            next_cursor = response.get("next_cursor")
        return results

    def fetch_page_content(self, page_id: str) -> str:
        """ページの本文（Markdown相当）を取得"""
        blocks = []
        next_cursor = None
        while True:
            kwargs = {"block_id": page_id, "page_size": 100}
            if next_cursor:
                kwargs["start_cursor"] = next_cursor
            response = self.client.blocks.children.list(**kwargs)
            blocks.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            next_cursor = response.get("next_cursor")

        return self._blocks_to_markdown(blocks)

    def _blocks_to_markdown(self, blocks: list[dict]) -> str:
        """Notion ブロックを Markdown 文字列に変換"""
        lines = []
        for block in blocks:
            block_type = block.get("type", "")
            data = block.get(block_type, {})
            text = self._rich_text_to_plain(data.get("rich_text", []))

            if block_type == "heading_1":
                lines.append(f"# {text}")
            elif block_type == "heading_2":
                lines.append(f"## {text}")
            elif block_type == "heading_3":
                lines.append(f"### {text}")
            elif block_type == "bulleted_list_item":
                lines.append(f"- {text}")
            elif block_type == "numbered_list_item":
                lines.append(f"1. {text}")
            elif block_type == "to_do":
                checked = "x" if data.get("checked") else " "
                lines.append(f"- [{checked}] {text}")
            elif block_type == "quote":
                lines.append(f"> {text}")
            elif block_type == "code":
                lang = data.get("language", "")
                lines.append(f"```{lang}\n{text}\n```")
            elif block_type == "paragraph":
                lines.append(text)
            elif block_type == "divider":
                lines.append("---")
            else:
                if text:
                    lines.append(text)
        return "\n\n".join(line for line in lines if line)

    @staticmethod
    def _rich_text_to_plain(rich_text: list[dict]) -> str:
        """rich_text 配列をプレーンテキストに変換"""
        return "".join(rt.get("plain_text", "") for rt in rich_text)

    def fetch_existing_tags(self) -> list[str]:
        """既存の Tags マルチセレクト選択肢一覧を取得"""
        db = self.client.databases.retrieve(database_id=self.database_id)
        tags_property = db.get("properties", {}).get("Tags", {})
        options = tags_property.get("multi_select", {}).get("options", [])
        return [opt.get("name", "") for opt in options if opt.get("name")]

    def update_page_properties(
        self,
        page_id: str,
        type_value: str | None = None,
        tags: list[str] | None = None,
        priority: str | None = None,
        due_date: str | None = None,
        status: str | None = None,
    ) -> dict:
        """ページのプロパティを一括更新"""
        properties: dict[str, Any] = {}

        if type_value is not None:
            properties["Type"] = {"select": {"name": type_value}}

        if tags is not None:
            properties["Tags"] = {
                "multi_select": [{"name": t} for t in tags if t]
            }

        if priority is not None:
            # 空文字なら何もしない、値があればセット
            if priority:
                properties["Priority"] = {"select": {"name": priority}}

        if due_date is not None:
            if due_date:
                properties["Due"] = {"date": {"start": due_date}}

        if status is not None:
            properties["Status"] = {"select": {"name": status}}

        if not properties:
            return {}

        return self.client.pages.update(page_id=page_id, properties=properties)

    @staticmethod
    def get_page_title(page: dict) -> str:
        """ページから Title プロパティ値を抽出"""
        title_prop = page.get("properties", {}).get("Title", {})
        title_array = title_prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in title_array)

    @staticmethod
    def get_page_url(page: dict) -> str:
        """ページのURLを取得"""
        return page.get("url", "")

    @staticmethod
    def get_page_id(page: dict) -> str:
        return page.get("id", "")

    @staticmethod
    def get_created_time(page: dict) -> str:
        return page.get("created_time", "")
