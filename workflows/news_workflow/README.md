# 週次ニュースエージェント

LangGraphを使った週次ニュース収集・評価・通知エージェント（4ノード再利用型アーキテクチャ）

## アーキテクチャ

プランの詳細は [docs/AI_AGENT_ARCHITECTURE.md](docs/AI_AGENT_ARCHITECTURE.md) を参照

### 4つの再利用可能エージェント

1. **PromptMasterAgent**: プロンプト管理・FB反映
2. **NewsCollectorAgent**: Gemini検索グラウンディングで収集
3. **AIOreAgent**: 「通知してうれしいか」を判定（3分岐）
4. **NotifyAssistantAgent**: MD保存 + Pushover通知

### 判定フロー（3分岐）

- `approve`: 通知価値あり → 通知実行
- `revise`: 物足りない → 収集を改善して再試行
- `notify_suppress`: 価値不足 → 通知せず終了

## セットアップ

### 1. 依存パッケージインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数設定

`.env` ファイルを作成:

```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
VERTEX_MODEL=gemini-3-flash-preview

# Pushover通知（オプション）
PUSHOVER_TOKEN=your-pushover-token
PUSHOVER_USER=your-pushover-user
```

### 3. 実行

```bash
# 統合ランナー経由（推奨）
python workflows/run.py news

# 個別実行
python workflows/news_workflow/run.py
```

## ディレクトリ構造

```
.
├── agents/                       # 再利用可能な4エージェント
│   ├── prompt_master_agent.py    # プロンプトマスターエージェント
│   ├── news_collector_agent.py   # ニュース収集エージェント
│   ├── ai_ore_agent.py           # AI俺エージェント
│   └── notify_assistant_agent.py # なんでも通知アシスタント
├── workflows/                    # ワークフロー定義
│   ├── run.py                    # 統合ランナー
│   └── news_workflow/
│       ├── run.py                # 個別実行エントリーポイント
│       ├── state.py              # LangGraph State定義
│       ├── contracts.py          # エージェント契約
│       ├── stores.py             # 記憶・FBストア
│       ├── graph.py              # LangGraphワークフロー
│       └── scheduler.py          # 週次スケジューラ
├── prompts/                      # プロンプトテンプレート
│   └── news_workflow/
│       ├── collector.txt         # 収集エージェント用
│       ├── judge.txt             # AI俺用
│       └── notify.txt            # 通知アシスタント用
├── data/                         # 設定データ
│   ├── user_profiles.json        # ユーザプロファイル・トピック設定
│   └── README.md                 # データ設定ガイド
├── tools/                        # LangGraphエージェント用ツール
│   ├── __init__.py
│   └── subagent_launcher_tool.py # 汎用サブエージェント起動
├── utils/                        # ユーティリティ
│   ├── model_helper.py           # モデルビルダー
│   ├── loaders.py                # プロンプト・データローダー
│   └── single_agent_graph.py    # シンプルエージェント
├── docs/
│   └── AI_AGENT_ARCHITECTURE.md  # アーキテクチャドキュメント
├── reports/                      # 生成されたレポート保存先
├── memory/                       # 記憶ストア保存先
├── feedback/                     # FBストア保存先
├── requirements.txt
└── .env
```

## カスタマイズ

### トピックを変更

`data/user_profiles.json` を編集:

```json
{
  "user_profiles": {
    "default_user": {
      "topics": ["あなたの興味トピック"],
      "exclude_keywords": ["除外キーワード"],
      "language": "ja",
      "region": "JP"
    }
  }
}
```

### プロンプトをカスタマイズ

#### 方法1: テンプレートを直接編集（推奨）

`prompts/news_workflow/` 内のテンプレートを編集:

- `collector.txt`: ニュース収集の指示
- `judge.txt`: 判定基準
- `notify.txt`: 通知フォーマット
- `prompt_master.txt`: プロンプトマスター用（動的生成時）

例:
```
# prompts/news_workflow/collector.txt
あなたは技術ニュース収集の専門家です。
以下のトピックに関連する記事を、技術的な深さを重視して収集してください:
{topics}
...
```

#### 方法2: LLMによる動的生成（実験的）

プロンプトマスターにLLMを使わせて、FBから自動でプロンプトを改善:

```python
from agents import PromptMasterAgent

# 動的生成を有効化
prompt_master = PromptMasterAgent(
    model=model,
    use_dynamic_generation=True,  # LLMでプロンプト生成
)
```

この場合、`prompts/news_workflow/prompt_master.txt` の指示に従ってLLMが各エージェント用のプロンプトを生成します。

`data/user_profiles.json` の `workflow_config` を編集:

```json
{
  "workflow_config": {
    "lookback_days": 7,
    "max_retries": 3,
    "max_candidates": 20
  }
}
```

### 通知先を追加

`agents/notify_assistant_agent.py` に新しいアダプタを追加（Slack、Email等）

### サブエージェントツールを使う

`tools/subagent_launcher_tool.py` を使うと、LangGraphエージェントから任意ロールのサブエージェントを起動できます。詳細は `docs/SUBAGENT_TOOL.md` を参照してください。

## ユーザFBの追加

通知後、手動でFBを追加:

```python
from workflows.news_workflow.scheduler import WeeklyNewsScheduler

scheduler = WeeklyNewsScheduler(model)
scheduler.add_user_feedback(
    user_id="default_user",
    article_url="https://example.com/article",
    liked=True,
    reason="この視点が参考になった",
)
```

## 定期実行

### cron（Linux/Mac）

```bash
0 8 * * MON cd /path/to/Langgraph && python workflows/run.py news
```

### Windows タスクスケジューラ

毎週月曜8:00にスクリプトを実行するタスクを作成

### Cloud Scheduler（GCP）

```bash
gcloud scheduler jobs create http weekly-news \
  --schedule="0 8 * * MON" \
  --uri="https://your-cloud-run-url/run" \
  --http-method=POST
```

## ライセンス

MIT
