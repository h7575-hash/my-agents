# Slack Bot を公開する（手順）

## 1. ボットを起動

**ターミナル1** で:

```powershell
cd c:\Users\koyas\work\Langgraph
python run_slack_bot.py
```

`Uvicorn running on http://0.0.0.0:3001` と出ればOK（ポートは .env の `SLACK_BOT_PORT` に従います）。

## 2. ngrok で HTTPS 公開

**ターミナル2** で（ボットを止めずに）:

```powershell
ngrok http 3001
```

※ ポートは `.env` の `SLACK_BOT_PORT` と同じにしてください。

表示される **Forwarding** の URL をコピーします（例: `https://abc123.ngrok-free.app`）。

## 3. Slack の Request URL を設定

1. [Slack API](https://api.slack.com/apps) → 対象アプリ → **Event Subscriptions**
2. **Request URL** に次を入力して **Save**:
   ```
   https://<ngrokのURL>/slack/events
   ```
   例: `https://abc123.ngrok-free.app/slack/events`
3. **Verified** と表示されれば公開完了です。

## 注意

- ngrok を終了すると URL は使えません。無料プランでは再起動で URL が変わるため、その都度 Slack の Request URL を更新してください。
- ボットを止めたら、同じ手順で再度「1. 起動」→「2. ngrok」からやり直してください。
