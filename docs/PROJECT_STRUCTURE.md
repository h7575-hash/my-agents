# プロジェクト構造

```
Langgraph/
│
├── agents/                          # 再利用可能な4エージェント
│   ├── __init__.py
│   ├── prompt_master_agent.py       # プロンプト管理・FB反映
│   ├── news_collector_agent.py      # Gemini検索グラウンディング収集
│   ├── ai_ore_agent.py              # 通知価値判定（3分岐）
│   └── notify_assistant_agent.py    # MD保存 + Pushover通知
│
├── workflows/                       # ワークフロー定義
│   ├── run.py                       # workflows統合実行ランナー
│   ├── README.md                    # workflows一覧
│   └── news_workflow/
│       ├── __init__.py
│       ├── state.py                 # LangGraph State定義
│       ├── contracts.py             # エージェント契約（Protocol）
│       ├── stores.py                # 記憶・FBストア
│       ├── graph.py                 # LangGraphワークフロー
│       ├── scheduler.py             # 週次スケジューラ
│       ├── run.py                   # 実行エントリーポイント
│       └── README.md                # ワークフロー説明
│
├── prompts/                         # プロンプトテンプレート
│   └── news_workflow/
│       ├── collector.txt            # 収集エージェント用
│       ├── judge.txt                # AI俺用
│       ├── notify.txt               # 通知アシスタント用
│       └── prompt_master.txt        # プロンプトマスター用
│
├── data/                            # 設定データ
│   ├── user_profiles.json           # ユーザプロファイル・トピック設定
│   └── README.md                    # データ設定ガイド
│
├── utils/                           # ユーティリティ
│   ├── __init__.py
│   ├── model_helper.py              # モデルビルダー
│   ├── loaders.py                   # プロンプト・データローダー
│   └── single_agent_graph.py        # シンプルエージェント（サンプル）
│
├── tools/                           # LangGraphエージェント用ツール
│   ├── __init__.py
│   └── subagent_launcher_tool.py    # 汎用サブエージェント起動ツール
│
├── docs/
│   ├── AI_AGENT_ARCHITECTURE.md     # アーキテクチャドキュメント
│   ├── PROJECT_STRUCTURE.md         # このファイル
│   ├── CONFIGURATION_EXTERNALIZATION.md  # 設定外部化ガイド
│   ├── SUBAGENT_TOOL.md             # サブエージェントツール利用ガイド
│   └── ほしいもの                    # エージェント要望リスト
│
├── reports/                         # 生成されたレポート（実行時作成）
├── memory/                          # 記憶ストア（実行時作成）
├── feedback/                        # FBストア（実行時作成）
│
├── .env                             # 環境変数
├── .gitignore                       # Git除外設定
├── requirements.txt                 # 依存パッケージ
└── README.md                        # プロジェクトREADME
```

## 設計思想

### 責務分離
- **agents/**: ドメインに依存しない再利用可能なエージェント
- **workflows/**: 特定ユースケースのワークフロー定義
- **prompts/**: プロンプトテンプレート（ハードコードしない）
- **data/**: 設定データ（トピック、ユーザプロファイル等）
- **tools/**: LangGraphエージェントが利用するツール群
- **utils/**: 汎用ユーティリティ

### 設定の外部化
- **プロンプト**: `prompts/` フォルダで管理
- **データ**: `data/` フォルダで管理
- コードはロジックに集中、設定は外部ファイルで柔軟に変更可能

### 今後の拡張
`ほしいもの` リストの他エージェントも同じ構造で追加可能:
- `agents/smart_home_agent.py`
- `workflows/smart_home_workflow/`
- `prompts/smart_home_workflow/`
- `data/smart_home_config.json`

各エージェントは独立しており、異なるワークフローで組み合わせて使用できる。
