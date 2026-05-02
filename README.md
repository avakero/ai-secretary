# 🧠 AI Brain Organizer

Notion の「🧠 AI Brain」DB に溜まった未整理メモを、毎朝 LLM が読み解いて
**Type / Tags / Priority / Due / Status** を自動で整理し、整理結果を豪華 HTML メールで通知します。

**完全無料・サーバー不要・GitHub Actions で動作。**

---

## できること

- 毎朝 7:00 JST に自動実行（時刻は変更可能）
- Notion の `Status=Inbox` ページを全件取得
- LLM でメタデータを推論（Type, Tags, Priority, Due, Status）
- 推論結果を Notion に書き戻す
- 整理レポートを Gmail SMTP で送信

---

## アーキテクチャ

```
GitHub Actions（cron: 毎朝 22:00 UTC = 7:00 JST）
    ↓
1. Notion API で Status=Inbox を全件取得
    ↓
2. Straico (OpenAI互換 v2 API) で各ページを LLM 推論
    ↓
3. Notion API でプロパティ更新
    ↓
4. SMTP（Gmail アプリパスワード）でレポートメール送信
```

LLM プロバイダーは [Straico](https://straico.com/) を経由するため、
Anthropic / OpenAI / Google Gemini など複数のモデルを `STRAICO_MODEL` 変数1つで切り替えられます。

---

## 必要なもの

| サービス | 用途 | 費用目安 |
|---|---|---|
| GitHub | リポジトリ + Actions の cron 実行 | 無料（Public/Private どちらも） |
| Notion | 「🧠 AI Brain」DB の置き場 | 無料プランでOK |
| Straico | LLM API ゲートウェイ | 従量課金（数百円〜/月） |
| Gmail | レポートメール送信 | 無料 |

---

## セットアップ手順

### STEP 1: Notion 側を準備

#### 1-A. 「🧠 AI Brain」DB を作成

**🚀 一番ラクな方法：テンプレートを複製する**

[**📋 AI Brain DB テンプレートをワンクリック複製**](https://sulfuric-queen-bc2.notion.site/09a34a51a4b44d0ab6abafa05fd02443)

リンク先で右上の **「Duplicate」** ボタンを押すと、自分のワークスペースに完全な構成でDBがコピーされます。
プロパティ名・型・選択肢・色まで完全再現されているので、以降の手順がスムーズです。

**手動で作る場合**

新しいデータベースを作り、以下のプロパティを揃えてください：

| プロパティ名 | 型 | 必須の選択肢 |
|---|---|---|
| `Title` | Title | — |
| `Type` | Select | `Memo` / `Meeting` / `Task` / `Knowledge` / `Person` / `SNS Post` / `Blog Post` |
| `Tags` | Multi-select | （育てていく） |
| `Priority` | Select | `🔥 High` / `🟡 Mid` / `⚪ Low` |
| `Due` | Date | — |
| `Status` | Select | `Inbox` / `Active` / `Archive` |

> **プロパティ名と選択肢の名前は完全一致が必要**です（コードからこの値を直接参照しているため）。

#### 1-B. インテグレーションを作成

1. <https://www.notion.so/profile/integrations> →「+ New integration」
2. Type: `Internal`、ワークスペースを選択して作成
3. 「Configure」→「Internal Integration Secret」をコピー（`secret_...` または `ntn_...`）

#### 1-C. インテグレーションを DB に接続（最重要）

1. 上で作った「🧠 AI Brain」DB を開く
2. 右上「**...**」→「**Connections**」→「**Connect to**」
3. 作成したインテグレーションを選択 → Confirm

> ⚠️ これを忘れると `object_not_found` エラーになります。

#### 1-D. データベース ID を控える

DB の URL から ID を抜き出します：

```
https://www.notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx?v=...
                       ↑この32文字がID
```

### STEP 2: Straico API キーを取得

1. <https://platform.straico.com/> でアカウント作成（クレジット購入）
2. 「User Settings」→ API Key をコピー

利用可能なモデル一覧は `scripts/list_straico_models.py` 相当のスクリプトで取得可能。
無難な選択：

| 用途 | モデル |
|---|---|
| 高品質（推奨） | `anthropic/claude-sonnet-4.5` |
| 安価 | `openai/gpt-4o-mini` |
| バランス | `openai/gpt-4o` |

### STEP 3: Gmail アプリパスワードを取得

1. <https://myaccount.google.com/security> で「2 段階認証プロセス」を有効化
2. <https://myaccount.google.com/apppasswords> で新規発行
3. アプリ名は `AI Brain Organizer` など、表示された 16 文字をコピー

### STEP 4: GitHub リポジトリを作成

このリポジトリを Fork するか、Template から作成。Public/Private どちらでも動作します（個人運用なら Private 推奨）。

### STEP 5: GitHub Secrets を登録

リポジトリの **Settings → Secrets and variables → Actions** で「New repository secret」：

| Name | 値 |
|:---|:---|
| `STRAICO_API_KEY` | Straico の API キー |
| `NOTION_API_KEY` | `secret_...` または `ntn_...` |
| `NOTION_DATABASE_ID` | STEP 1-D で控えた32文字 |
| `GMAIL_USER` | 送信元 Gmail アドレス |
| `GMAIL_APP_PASSWORD` | 16文字のアプリパスワード |
| `RECIPIENT_EMAIL` | 受信先（カンマ区切りで複数指定可） |

オプション（**Variables** タブ、Secret ではなく Variable）：

| Name | 値 | デフォルト |
|:---|:---|:---|
| `STRAICO_MODEL` | 例: `anthropic/claude-sonnet-4.5` | `anthropic/claude-opus-4-7` |

> 💡 `gh` CLI を使えば1行で登録できます：
> ```bash
> gh secret set STRAICO_API_KEY --repo OWNER/REPO
> gh variable set STRAICO_MODEL --body "anthropic/claude-sonnet-4.5" --repo OWNER/REPO
> ```

### STEP 6: 動作確認

1. リポジトリの **Actions** タブを開く
2. 「🧠 AI Brain Daily Organize」ワークフローを選択
3. 「Run workflow」→「Run workflow」で手動実行
4. 緑のチェック ✅ が出れば OK、Gmail を確認

翌朝 7:00 JST から自動実行されます。

---

## ローカル動作確認

```bash
# 環境変数を設定
export STRAICO_API_KEY="..."
export STRAICO_MODEL="anthropic/claude-sonnet-4.5"  # 任意
export NOTION_API_KEY="secret_..."
export NOTION_DATABASE_ID="..."

# 依存ライブラリをインストール
pip install -r requirements.txt

# 推論のみテスト（メール送信なし）
python scripts/test_local.py

# フル実行（メール送信あり）
export GMAIL_USER="..."
export GMAIL_APP_PASSWORD="..."
export RECIPIENT_EMAIL="..."
python src/main.py
```

---

## ファイル構成

```
ai-brain-organizer/
├── .github/workflows/
│   └── daily-organize.yml       # 毎朝の自動実行
├── scripts/
│   └── test_local.py            # ローカル推論テスト
├── src/
│   ├── main.py                  # エントリポイント
│   ├── notion_brain.py          # Notion API ラッパー
│   ├── ai_organizer.py          # Straico (OpenAI互換) で推論
│   ├── email_sender.py          # Gmail SMTP 送信
│   └── html_template.py         # 豪華 HTML メール
├── requirements.txt
└── README.md
```

---

## カスタマイズ

### 実行時刻を変更する

`.github/workflows/daily-organize.yml` の cron を編集：

```yaml
schedule:
  - cron: '0 22 * * *'  # 22:00 UTC = 7:00 JST
```

JST = UTC + 9 なので：

| 希望時刻 (JST) | cron |
|:---|:---|
| 朝 6:00 | `0 21 * * *` |
| 朝 7:00 | `0 22 * * *` |
| 朝 8:00 | `0 23 * * *` |
| 夜 22:00 | `0 13 * * *` |

### モデルを切り替える

```bash
gh variable set STRAICO_MODEL --body "openai/gpt-4o" --repo OWNER/REPO
```

次回の実行から反映されます。

### Type の選択肢を追加・変更する

1. `src/ai_organizer.py` の `SYSTEM_PROMPT` 内の Type 選択肢を更新
2. Notion DB の `Type` プロパティの選択肢を同じ名前で追加
3. commit & push

両方の同期が必須です。

### 一時停止

```bash
gh workflow disable "🧠 AI Brain Daily Organize" --repo OWNER/REPO
# 再開:
gh workflow enable "🧠 AI Brain Daily Organize" --repo OWNER/REPO
```

---

## トラブルシューティング

### `Notion 取得エラー: object_not_found`

→ STEP 1-C のインテグレーション接続を忘れている可能性大。
DB を開いて右上「...」→「Connections」を確認。

### `Model not found: ...`

→ Straico がそのモデルを提供していない、または ID の表記揺れ。
`gh variable set STRAICO_MODEL --body "openai/gpt-4o-mini"` などに切り替え。

### `'DatabasesEndpoint' object has no attribute 'query'`

→ `notion-client` のバージョン非互換。`requirements.txt` に
`notion-client==2.2.1` とピン留めしてあるはずなので、ピンが外れていないか確認。

### メールが届かない

→ Gmail のアプリパスワードを再発行 / 「迷惑メール」フォルダを確認 /
`RECIPIENT_EMAIL` が正しいか確認。

### `推論エラー: ...`

→ Straico の API キーや残高を確認。
`max_tokens` を上げる必要があれば `src/ai_organizer.py` の値を調整。

---

## ライセンス

MIT License

---

*Powered by [Straico](https://straico.com/) / [Notion API](https://developers.notion.com)*
