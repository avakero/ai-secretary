"""
AI Organizer
Straico の OpenAI互換 API (/v2) を呼び出して、Inbox ページのメタデータを推論する
"""
import json
import os
import re
from typing import Any
from openai import OpenAI
from datetime import datetime
from zoneinfo import ZoneInfo


STRAICO_BASE_URL = "https://api.straico.com/v2"


SYSTEM_PROMPT = """あなたは、Notion の「📋 AI 秘書」データベースに溜まった未整理メモ（Status=Inbox）を読み、適切なメタデータ（Type / Tags / Priority / Due / Status）を推論する整理担当の AI 秘書です。

以下のルールに厳密に従って、JSON 形式で結果を返してください。

# Type 推論ルール（必ずいずれか1つを選ぶ）
- "Memo": 雑なメモ・気づき・独り言・着想
- "Meeting": 商談・打ち合わせ・会議の議事録や予定
- "Task": やることリスト・期限のある作業・ToDo
- "Knowledge": ノウハウ・調べ物・記事クリップ・学んだこと
- "Person": 人物に関する情報・連絡先・関係メモ
- "SNS Post": X / Threads / Instagram など SNS 投稿の下書きや原稿
- "Blog Post": note やブログ記事の下書き・構成案

# Tags 推論ルール
- 本文から関連キーワードを 1〜5 個抽出する
- 既存タグ（プロンプトに渡される候補リスト）を最優先で再利用する
- 新規タグ追加は、既存に近いものが本当に無い場合のみ
- 命名は短く（例: "HP制作", "A社", "AI", "Pickaxe"）
- ハッシュタグの "#" は付けない（Notion 側で表示時に整形される）

# Priority 推論ルール（Type=Task の場合のみ）
- "🔥 High": 期限が3日以内 / 売上・収益に直結 / クライアント対応
- "🟡 Mid": 1週間以内 / 重要だが緊急ではない / 自社の改善
- "⚪ Low": 期限なし / アイデア段階 / いつかやる
- Type が Task 以外の場合は null

# Due 推論ルール（Type=Task の場合のみ）
- 本文に「●月●日まで」「来週金曜」「期限: ●●」などの言及があれば ISO-8601（YYYY-MM-DD）に変換
- 言及がない場合は null
- 相対表現は、ページの created_time（プロンプトで渡される）を起点に解釈

# Status 推論ルール
- 高確度で推論完了 → "Active"
- 本文が極端に短く曖昧 / Type 判別不能 → "Inbox"（人手判断にゆだねる）

# 判別が曖昧なケース
- 複数候補がある場合は、具体的な行動を促す方を優先（Task > SNS Post > Blog Post > Meeting > Memo）
- 完全に判別不能なら Type="Memo" / Status="Inbox" を返し、reason に「要・人手判断」と書く

# 出力フォーマット（JSON のみ。前後に説明文を書かない）
{
  "type": "Memo" | "Meeting" | "Task" | "Knowledge" | "Person" | "SNS Post" | "Blog Post",
  "tags": ["タグ1", "タグ2"],
  "priority": "🔥 High" | "🟡 Mid" | "⚪ Low" | null,
  "due_date": "YYYY-MM-DD" | null,
  "status": "Active" | "Inbox",
  "reason": "推論の根拠を1〜2文で簡潔に"
}
"""


class AIOrganizer:
    """Straico (OpenAI互換 v2) を使ってメタデータを推論する"""

    def __init__(self, api_key: str, model: str = "anthropic/claude-opus-4-7"):
        self.client = OpenAI(api_key=api_key, base_url=STRAICO_BASE_URL)
        self.model = model

    def organize_page(
        self,
        title: str,
        body: str,
        created_time: str,
        existing_tags: list[str],
    ) -> dict[str, Any]:
        """1ページ分のメタデータを推論する"""
        existing_tags_str = ", ".join(existing_tags) if existing_tags else "（既存タグなし）"

        user_prompt = f"""以下のページを分析して、JSON で結果を返してください。

# ページ情報
- タイトル: {title}
- 作成日時 (ISO-8601): {created_time}
- 既存タグ候補: {existing_tags_str}

# 本文
{body if body else "（本文なし）"}

JSON 形式のみで返してください。"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        text = response.choices[0].message.content or ""
        return self._parse_json_response(text)

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        """LLM の出力から JSON 部分を抽出してパース"""
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                raise ValueError(f"JSON が見つかりません: {text[:200]}")

        return json.loads(json_str)
