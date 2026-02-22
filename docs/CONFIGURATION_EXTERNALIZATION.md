# 設定の外部化 - プロンプト＆データ分離

## 概要

プロンプトとデータをコードからハードコードせず、外部ファイルで管理する構成に変更しました。

## 変更内容

### 新規追加フォルダ

#### 1. `prompts/` - プロンプトテンプレート
```
prompts/
└── news_workflow/
    ├── collector.txt        # NewsCollectorAgent用
    ├── judge.txt            # AIOreAgent用
    ├── notify.txt           # NotifyAssistantAgent用
    └── prompt_master.txt    # PromptMasterAgent用（動的生成時）
```

**特徴:**
- プロンプトをテンプレート化（`{変数名}` で変数埋め込み）
- ワークフロー別にディレクトリ分離
- コード修正なしでプロンプトを調整可能

**例（`collector.txt`）:**
```
あなたはニュース収集エージェントです。
以下のトピックに関連するニュースを収集してください:
{topics}

除外キーワード: {exclude_keywords}
...
```

#### 2. `data/` - 設定データ
```
data/
├── user_profiles.json   # ユーザプロファイル・トピック設定
└── README.md            # データ設定ガイド
```

**特徴:**
- ユーザプロファイル（トピック、除外キーワード等）をJSON管理
- ワークフロー設定（再試行回数、収集日数等）を一元管理
- 複数ユーザ対応可能

**例（`user_profiles.json`）:**
```json
{
  "user_profiles": {
    "default_user": {
      "topics": ["AI", "LangGraph", "Vertex AI"],
      "exclude_keywords": ["広告", "PR"],
      "language": "ja",
      "region": "JP"
    }
  },
  "workflow_config": {
    "lookback_days": 7,
    "max_retries": 2,
    "max_candidates": 20
  }
}
```

### 新規ユーティリティ

#### `utils/loaders.py`

**PromptLoader:**
- プロンプトテンプレートを読み込み
- 変数埋め込み（`format()`）

**DataLoader:**
- ユーザプロファイルを読み込み
- ワークフロー設定を取得

### 修正したファイル

#### 1. `agents/prompt_master_agent.py`
**変更前:** プロンプトをハードコード
```python
base = f"""あなたはニュース収集エージェントです。
以下のトピックに関連するニュースを収集してください:
{', '.join(profile.topics)}
...
"""
```

**変更後:** テンプレート読み込み
```python
template = self.prompt_loader.load(self.workflow, "collector")
return self.prompt_loader.format(
    template,
    topics=", ".join(profile.topics),
    exclude_keywords=", ".join(profile.exclude_keywords),
    ...
)
```

#### 2. `run_weekly_news.py`
**変更前:** トピックをハードコード
```python
result = scheduler.run_weekly(
    user_id="default_user",
    topics=["AI", "LangGraph", "Vertex AI"],
    exclude_keywords=["広告", "PR"],
)
```

**変更後:** データファイルから読み込み
```python
data_loader = DataLoader()
user_profile = data_loader.get_user_profile("default_user")
workflow_config = data_loader.get_workflow_config()

result = scheduler.run_weekly(
    user_id="default_user",
    topics=user_profile["topics"],
    exclude_keywords=user_profile.get("exclude_keywords", []),
    lookback_days=workflow_config.get("lookback_days", 7),
)
```

## メリット

### 1. 柔軟な設定変更
- コード修正不要でトピック・プロンプトを変更可能
- 環境ごとに異なる設定を適用しやすい

### 2. 保守性向上
- プロンプトが一箇所に集約
- バージョン管理しやすい

### 3. 再利用性向上
- 同じエージェントコードで異なるワークフロー対応
- ワークフロー別にプロンプトフォルダを追加するだけ

### 4. 複数ユーザ対応
- `user_profiles.json` に複数プロファイルを追加可能
- ユーザごとに異なるトピック・嗜好を管理

## 使用例

### トピックを変更

`data/user_profiles.json` を編集:
```json
{
  "user_profiles": {
    "default_user": {
      "topics": ["Python", "FastAPI", "PostgreSQL"],
      "exclude_keywords": ["広告"]
    }
  }
}
```

### プロンプトを調整

#### 方法1: テンプレート直接編集（推奨）

`prompts/news_workflow/collector.txt` を編集:
```
あなたは技術ニュース収集の専門家です。
以下のトピックに関連する記事を、技術的な深さを重視して収集してください:
{topics}
...
```

#### 方法2: LLMによる動的生成（実験的）

`prompt_master.txt` を編集してプロンプトマスターの挙動を調整:
```
あなたはプロンプト最適化の専門家です。
以下のフィードバックを分析し、より効果的なプロンプトを生成してください:

## 過去の高評価理由
{liked_reasons}

## 過去の低評価理由
{disliked_reasons}

目標: ユーザが「通知されてうれしい」と感じるニュースを収集できるプロンプトを作成
...
```

コードで動的生成を有効化:
```python
prompt_master = PromptMasterAgent(
    model=model,
    use_dynamic_generation=True,
)
```

### 新しいユーザを追加

`data/user_profiles.json` に追加:
```json
{
  "user_profiles": {
    "default_user": { ... },
    "user_business": {
      "topics": ["スタートアップ", "資金調達"],
      "exclude_keywords": ["PR", "広告"],
      "language": "ja",
      "region": "JP"
    }
  }
}
```

実行時にユーザIDを指定:
```python
result = scheduler.run_weekly(user_id="user_business", ...)
```

## 今後の拡張

他のワークフロー追加時も同じパターンで実装:

```
prompts/
├── news_workflow/
│   ├── collector.txt
│   ├── judge.txt
│   └── notify.txt
└── smart_home_workflow/
    ├── sensor.txt
    ├── controller.txt
    └── alert.txt

data/
├── user_profiles.json
└── smart_home_config.json
```
