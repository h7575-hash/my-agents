# Slack メッセージ送信ツール

`tools/slack_notifier_tool.py` の利用手順と、メッセージの読み書きに必要な OAuth スコープです。

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `SLACK_BOT_TOKEN` | Slack App の Bot User OAuth Token（`xoxb-...`） |
| `SLACK_MENTION_TARGETS` | メンション先（カンマ区切り）。例: `U01ABCDEF,here` |

## メッセージの読み書きに必要な Token Scope

Slack App の **OAuth & Permissions** で、用途に応じて以下のスコープを追加してください。

### 書き込み（送信）のみ

| Scope | 説明 |
|-------|------|
| **`chat:write`** | メッセージの送信・更新・削除。`chat.postMessage` に必須。 |

※ 本ツール（送信のみ）では **`chat:write`** だけで動作します。

### 読み取り（履歴取得）

会話タイプごとに次のスコープが必要です。

| 会話タイプ | 必要なスコープ | 主な API |
|------------|----------------|----------|
| **パブリックチャンネル** | `channels:read`<br>`channels:history` | `conversations.list`<br>`conversations.history` |
| **プライベートチャンネル** | `groups:read`<br>`groups:history` | 同上（プライベート用） |
| **DM** | `im:read`<br>`im:history` | 同上（DM用） |
| **マルチDM** | `mpim:read`<br>`mpim:history` | 同上（マルチDM用） |

スレッドの返信を取得する `conversations.replies` も、対象会話の **history** スコープがあれば利用できます。

### 画像・ファイルの参照

メッセージに添付された画像やファイルの**メタ情報の取得**と**実体のダウンロード**には、次のスコープが必要です。

| Scope | 説明 |
|-------|------|
| **`files:read`** | ワークスペースにアップロードされたファイルの情報取得（`files.info`, `files.list`）およびファイルのダウンロード。 |

- 履歴取得（`conversations.history` など）で得られるメッセージには、添付ファイルの参照（`files` 配列）が含まれることがあります。
- 実際の画像バイナリを取得するには、そのファイルの `url_private` に Bot Token を付けて `GET` する必要があり、**`files:read`** があればダウンロード可能です。
- 画像を Vision API などに渡して「見る」処理をする場合は、**履歴用スコープ（例: `channels:history`）+ `files:read`** を付けてください。

### まとめ（よく使う組み合わせ）

- **送信だけ（本ツールの最小構成）**: `chat:write`
- **送信 + パブリックチャンネルの履歴読み取り**: `chat:write`, `channels:read`, `channels:history`
- **送信 + 全タイプの履歴読み取り**: `chat:write`, `channels:read`, `channels:history`, `groups:read`, `groups:history`, `im:read`, `im:history`, `mpim:read`, `mpim:history`
- **履歴 + 画像・ファイルの参照**: 上記の履歴スコープに加えて **`files:read`**

## 設定手順（送信のみ）

1. [Slack API](https://api.slack.com/apps) でアプリを作成
2. **OAuth & Permissions** → **Scopes** → **Bot Token Scopes** に `chat:write` を追加
3. **Install to Workspace**（または **Reinstall**）でワークスペースにインストール
4. 発行された **Bot User OAuth Token** を `.env` の `SLACK_BOT_TOKEN` に設定
