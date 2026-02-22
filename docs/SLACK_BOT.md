# Slack Bot（Slack連絡係）

Slackからメンション付きで話しかけると、AIエージェントが応答するボットです。
直接回答・ワークフロー実行・サブエージェント起動を自動で判断します。

## アーキテクチャ

```
Slack (メンション)
  │
  ▼
FastAPI webhook (/slack/events)        ← slack_bot/app.py
  │
  ├─ URL Verification (初回設定時)
  ├─ 署名検証 / 重複排除
  │
  ▼
Event Handler (バックグラウンドスレッド)  ← slack_bot/event_handler.py
  │
  ▼
Slack Agent (LangGraph ReAct)           ← agents/slack_agent.py
  │
  ├─ 直接回答（LLMの知識で回答）
  ├─ run_workflow ツール → ワークフロー実行
  └─ launch_subagent ツール → サブエージェント起動
  │
  ▼
Slack に返信（同スレッド内）
```

## セットアップ

### 1. Slack App の作成と設定

1. [Slack API](https://api.slack.com/apps) で新しいアプリを作成
2. **OAuth & Permissions** で以下のスコープを追加:

| Scope | 説明 |
|-------|------|
| `app_mentions:read` | メンションイベントの受信 |
| `chat:write` | メッセージの送信 |
| `channels:history` | パブリックチャンネルでスレッド履歴を取得（スレッド丸ごと認識に必要） |
| `groups:history` | プライベートチャンネルでスレッド履歴を取得（プライベートでスレッド認識する場合） |

3. **Event Subscriptions** を有効化:
   - Request URL: `https://<your-domain>/slack/events`
   - Subscribe to bot events: `app_mention`

4. ワークスペースにインストール

### 2. 環境変数

`.env` に以下を追加:

```env
# 既存の設定
SLACK_BOT_TOKEN=xoxb-...

# 追加する設定
SLACK_SIGNING_SECRET=<Slack App の Basic Information > Signing Secret>

# Slack Bot 用の LLM（Vertex AI）※必須
# 下記のほか、gcloud auth application-default login で ADC を設定
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_MODEL=gemini-1.5-flash

# オプション: ポート・ホスト・HTTPS（このPCをサーバーにする場合）
# SLACK_BOT_HOST=0.0.0.0
# SLACK_BOT_PORT=3000
# SLACK_BOT_SSL_CERT=C:\path\to\fullchain.pem
# SLACK_BOT_SSL_KEY=C:\path\to\privkey.pem

# オプション: エラー時にSlackに詳細を表示（デバッグ用）
# SLACK_BOT_SHOW_ERROR=1
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 起動

```bash
python run_slack_bot.py
```

デフォルトでポート 3000 で起動します。  
**「ポートが使用中」(WinError 10048) が出る場合**: 既に別プロセスが 3000 を使っています。`.env` に `SLACK_BOT_PORT=3001` を追加するか、既存の `run_slack_bot.py` を終了してから再起動してください。

### 5. 外部公開の設定方法

Slack Events API は **インターネットから HTTPS でアクセス可能な URL** が必須です。  
ローカルで動かしているだけでは Slack から届かないため、以下のいずれかで公開します。

---

#### 方法A: ngrok（ローカル開発向け・手軽）

1. [ngrok](https://ngrok.com/) に登録し、[ダウンロード](https://ngrok.com/download)してインストール
2. 認証トークンを設定（ダッシュボードで取得）:
   ```bash
   ngrok config add-authtoken <your-token>
   ```
3. ボットを起動した状態で、**別のターミナル**でトンネルを張る:
   ```bash
   ngrok http 3000
   ```
4. 表示される **Forwarding** の URL（例: `https://abc123.ngrok-free.app`）をコピー
5. Slack App の **Event Subscriptions** → **Request URL** に次を入力:
   ```
   https://abc123.ngrok-free.app/slack/events
   ```
   「Save」後、**Verified** と表示されればOK

**注意**: 無料プランでは ngrok を起動するたびに URL が変わります。URL が変わったら Slack の Request URL を再設定してください。

---

#### 方法B: Cloud Run（本番・常時稼働向け）

Google Cloud で常時稼働させる場合の例です。

1. プロジェクトで Cloud Run の API を有効化
2. Dockerfile を作成し、`run_slack_bot.py` と依存関係をビルド
3. デプロイ例:
   ```bash
   gcloud run deploy slack-bot --source . --region asia-northeast1 --allow-unauthenticated
   ```
4. デプロイ後に表示される URL（例: `https://slack-bot-xxxxx-an.a.run.app`）を Slack の Request URL に設定:
   ```
   https://slack-bot-xxxxx-an.a.run.app/slack/events
   ```

※ 認証が必要な場合は `--no-allow-unauthenticated` にし、Slack のリクエストのみを通す設定（例: IAP や Cloud Endpoints）を検討してください。

---

#### 方法C: VPS・自宅サーバー（ポート開放）

サーバーをすでに持っている場合:

1. サーバー上で `python run_slack_bot.py` を起動（または systemd / supervisord で常駐化）
2. ルーターで **TCP 3000**（または利用するポート）をサーバーにポートフォワード
3. ドメインと SSL が必要です:
   - **Let's Encrypt + nginx/caddy** でリバースプロキシを立て、`/slack/events` を `http://localhost:3000` に転送
   - 例（nginx）:
     ```nginx
     location /slack/events {
         proxy_pass http://127.0.0.1:3000;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
     }
     ```
4. 公開URL（例: `https://your-domain.com/slack/events`）を Slack の Request URL に設定

---

#### このPCをサーバーとして外部公開する（自宅・オフィス）

このPCをサーバーにして、Slack から直接アクセスさせる手順です。

**前提**: Slack は **HTTPS** が必須です。以下の ① または ② のどちらかで HTTPS を用意してください。

**① 推奨: Cloudflare Tunnel（ドメイン不要・証明書不要）**

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) にログインし、**Networks** → **Tunnels** でトンネルを作成
2. **cloudflared** をこのPCにインストールし、トンネル用のトークンで接続
3. パブリックホスト名を設定（例: `slack-bot.your-domain.com` → `http://localhost:3000`）
4. Slack の Request URL に `https://slack-bot.your-domain.com/slack/events` を設定

※ Cloudflare の無料ドメイン（例: `xxx.trycloudflare.com`）を使う場合は、Tunnel の種類によってはそのURLをそのまま Request URL に設定できます。

**② ルーターでポート開放 + このPCで HTTPS**

1. **このPCのポートを決める**  
   例: 3000。既に 3000 が使われている場合は `.env` に `SLACK_BOT_PORT=3001` を追加
2. **このPCのローカルIPを確認**  
   `ipconfig` で「IPv4 アドレス」（例: 192.168.1.10）を控える
3. **ルーターでポートフォワード**  
   - 外部ポート: **443**（HTTPS）  
   - 内部IP: 上記のローカルIP（192.168.1.10）  
   - 内部ポート: 3000（または `SLACK_BOT_PORT` の値）
4. **Windowsファイアウォール**  
   「セキュリティが強化された Windows Defender ファイアウォール」→「受信の規則」で、該当ポート（3000 など）の TCP を許可
5. **HTTPS を用意**  
   - **ドメイン**がこのPCのグローバルIP（または DDNS）を指していること  
   - **証明書**: Let's Encrypt 等で取得し、`.env` に設定:
     ```env
     SLACK_BOT_SSL_CERT=C:\path\to\fullchain.pem
     SLACK_BOT_SSL_KEY=C:\path\to\privkey.pem
     SLACK_BOT_PORT=443
     ```
   - ポート 443 で待ち受ける場合、管理者権限で `python run_slack_bot.py` を実行するか、リバースプロキシ（IIS / nginx / Caddy）で 443 を受け、内部で 3000 に転送する方法もあります
6. Slack の Request URL に `https://<あなたのドメインまたはグローバルIP>/slack/events` を設定

**常時起動する場合**  
- タスクスケジューラで「ログオン時」や「起動時」に `python run_slack_bot.py` を実行  
- または [NSSM](https://nssm.cc/) で Windows サービス化

---

#### Slack 側の共通手順

1. [Slack API](https://api.slack.com/apps) → 対象アプリ → **Event Subscriptions**
2. **Enable Events** を ON
3. **Request URL** に `https://<あなたの公開URL>/slack/events` を入力
4. Slack が GET で URL にアクセスし、**Verified** と出れば設定完了
5. **Subscribe to bot events** で `app_mention` を追加して保存

**Verified にならない場合**:
- サーバーが起動しているか
- ファイアウォールで 443（HTTPS）が開いているか
- URL の末尾が `/slack/events` になっているか  
を確認してください。

## 使い方

Slack でボットにメンション付きでメッセージを送信します:

| メッセージ例 | 動作 |
|-------------|------|
| `@bot こんにちは` | 直接回答（挨拶） |
| `@bot AIの最新トレンドは？` | 直接回答（LLMの知識で回答） |
| `@bot ニュースを集めて` | news ワークフローを実行 |
| `@bot この文章を要約して: ...` | サブエージェントで要約 |

## ファイル構成

```
slack_bot/
├── __init__.py
├── app.py              # FastAPI webhook サーバー
└── event_handler.py    # イベント処理 + エージェント呼び出し

agents/
└── slack_agent.py      # LangGraph ReAct エージェント

tools/
└── workflow_runner_tool.py  # ワークフロー実行ツール

prompts/
└── slack_agent/
    └── system.txt      # システムプロンプト

run_slack_bot.py        # エントリーポイント
```

## ワークフローの追加

新しいワークフローを Slack から実行可能にするには:

1. `tools/workflow_runner_tool.py` の `WORKFLOW_DESCRIPTIONS` と `_WORKFLOW_RUNNERS` に登録
2. `prompts/slack_agent/system.txt` のワークフロー一覧に追記

```python
# workflow_runner_tool.py

WORKFLOW_DESCRIPTIONS = {
    "news": "...",
    "my_workflow": "新しいワークフローの説明",
}

def _run_my_workflow(model, parameters):
    # ワークフロー実行ロジック
    return "結果テキスト"

_WORKFLOW_RUNNERS = {
    "news": _run_news_workflow,
    "my_workflow": _run_my_workflow,
}
```
