# エージェントシステム（Slack Bot）を Cloud Run で動かすためのイメージ
FROM python:3.11-slim

WORKDIR /app

# 依存関係のみ先にインストール（レイヤーキャッシュのため）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY agents/ agents/
COPY tools/ tools/
COPY utils/ utils/
COPY workflows/ workflows/
COPY prompts/ prompts/
COPY data/ data/
COPY slack_bot/ slack_bot/
COPY run_slack_bot.py .

# Cloud Run は PORT を注入。run_slack_bot.py が PORT を参照する
ENV SLACK_BOT_HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "run_slack_bot.py"]
