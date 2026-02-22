# LangGraph Agents

LangGraphを使った再利用可能なAIエージェント基盤です。

## クイックスタート

```bash
pip install -r requirements.txt
```

ワークフロー実行（統合ランナー）:

```bash
python workflows/run.py news
```

個別ワークフロー実行:

```bash
python workflows/news_workflow/run.py
```

## 構成

- `agents/`: 再利用可能エージェント
- `workflows/`: ワークフロー定義と統合実行ランナー
- `prompts/`: プロンプトテンプレート
- `data/`: 設定データ
- `tools/`: LangGraphエージェント用ツール
- `utils/`: 共通ユーティリティ
- `docs/`: 設計・運用ドキュメント

## Slack Bot（エージェント連絡係）

メンションで話しかけると、直接回答・ワークフロー実行・サブエージェント起動を行うボットです。

```bash
python run_slack_bot.py
```

- ローカル・ngrok: `docs/SLACK_BOT.md`
- **Cloud Run へデプロイ**: `docs/DEPLOY_CLOUD_RUN.md`

## 主要ドキュメント

- `workflows/news_workflow/README.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/CONFIGURATION_EXTERNALIZATION.md`
- `docs/AI_AGENT_ARCHITECTURE.md`
- `docs/SUBAGENT_TOOL.md`
- `docs/SLACK_TOOL.md`（Slack ツール・Token Scope）
- `docs/SLACK_BOT.md`（Slack Bot セットアップ）
- `docs/DEPLOY_CLOUD_RUN.md`（Cloud Run デプロイ）

## ライセンス

MIT
