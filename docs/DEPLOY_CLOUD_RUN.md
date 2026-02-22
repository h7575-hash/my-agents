# Cloud Run へのデプロイ

Slack Bot（エージェントシステム）を Google Cloud Run にデプロイする手順です。

## 前提

- Google Cloud プロジェクトがある
- `gcloud` CLI がインストールされ、対象プロジェクトにログイン済み
- デプロイは `gcloud run deploy --source .` で行うため、ローカルに Docker は不要（Cloud Build でビルド）

## 1. API の有効化

```bash
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

## 2. デプロイ実行

プロジェクトルート（`Dockerfile` があるディレクトリ）で:

```bash
gcloud run deploy slack-bot \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=your-project-id,GOOGLE_CLOUD_LOCATION=us-central1,VERTEX_MODEL=gemini-1.5-flash" \
  --set-secrets "SLACK_BOT_TOKEN=slack-bot-token:latest,SLACK_SIGNING_SECRET=slack-signing-secret:latest"
```

**シークレットをまだ作っていない場合**は、まず環境変数で渡して動作確認してもよいです:

```bash
gcloud run deploy slack-bot \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=your-project-id,GOOGLE_CLOUD_LOCATION=us-central1,VERTEX_MODEL=gemini-1.5-flash,SLACK_BOT_TOKEN=xoxb-...,SLACK_SIGNING_SECRET=your-signing-secret"
```

- `your-project-id` を実際の GCP プロジェクト ID に
- `SLACK_BOT_TOKEN` と `SLACK_SIGNING_SECRET` を Slack App の値に

デプロイ後、表示される **サービス URL**（例: `https://slack-bot-xxxxx-an.a.run.app`）を控えます。

## 3. 環境変数・シークレット一覧

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `GOOGLE_CLOUD_PROJECT` | ○ | GCP プロジェクト ID |
| `GOOGLE_CLOUD_LOCATION` | ○ | Vertex AI のリージョン（例: `us-central1`, `asia-northeast1`） |
| `VERTEX_MODEL` | ○ | モデル名（例: `gemini-1.5-flash`） |
| `SLACK_BOT_TOKEN` | ○ | Slack Bot User OAuth Token（`xoxb-...`） |
| `SLACK_SIGNING_SECRET` | ○ | Slack App の Signing Secret |
| `SLACK_MENTION_TARGETS` | - | メンション先（カンマ区切り）。通知ツール用 |

Vertex AI の認証は **Cloud Run のデフォルトサービスアカウント** が使われます。同一プロジェクトで Vertex AI API が有効なら、多くの場合そのままで動作します。

## 4. Vertex AI の権限（エラーになる場合）

「Permission denied」などが出る場合は、Cloud Run のサービスアカウントに Vertex AI のロールを付けます:

```bash
# デフォルトのサービスアカウント
PROJECT_NUMBER=$(gcloud projects describe your-project-id --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:${SA}" \
  --role="roles/aiplatform.user"
```

## 5. Slack の Request URL を更新

1. [Slack API](https://api.slack.com/apps) → 対象アプリ → **Event Subscriptions**
2. **Request URL** を Cloud Run の URL に変更:
   ```
   https://<サービスURL>/slack/events
   ```
   例: `https://slack-bot-xxxxx-an.a.run.app/slack/events`
3. **Save** して **Verified** になることを確認

## 6. シークレットを利用する場合（推奨）

トークン類を環境変数ではなく Secret Manager で渡す場合:

```bash
# シークレット作成（初回のみ）
echo -n "xoxb-your-token" | gcloud secrets create slack-bot-token --data-file=-
echo -n "your-signing-secret" | gcloud secrets create slack-signing-secret --data-file=-

# Cloud Run のデフォルト SA に Secret Accessor を付与
PROJECT_NUMBER=$(gcloud projects describe your-project-id --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding slack-bot-token --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding slack-signing-secret --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor"
```

デプロイ時に `--set-secrets` で参照:

```bash
gcloud run deploy slack-bot \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=your-project-id,GOOGLE_CLOUD_LOCATION=us-central1,VERTEX_MODEL=gemini-1.5-flash" \
  --set-secrets "SLACK_BOT_TOKEN=slack-bot-token:latest,SLACK_SIGNING_SECRET=slack-signing-secret:latest"
```

## 7. ローカルで Docker イメージを試す場合

```bash
docker build -t slack-bot .
docker run --rm -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  -e GOOGLE_CLOUD_LOCATION=us-central1 \
  -e VERTEX_MODEL=gemini-1.5-flash \
  -e SLACK_BOT_TOKEN=xoxb-... \
  -e SLACK_SIGNING_SECRET=... \
  slack-bot
```

`http://localhost:8080/slack/events` でリクエストを受け付けます（ADC で Vertex に認証）。
