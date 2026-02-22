# サブエージェント起動ツール

`tools/subagent_launcher_tool.py` に、LangGraphエージェントから任意のサブエージェントを起動するためのツールを追加しました。

## 目的

- メインエージェントが必要に応じて専門ロールを都度起動する
- タスク内容・制約・出力形式を実行時に柔軟に切り替える
- 1つの汎用ツールで複数ユースケースに対応する

## 提供API

- `create_subagent_launcher_tool(model)`
  - 引数: `BaseChatModel`
  - 戻り値: `launch_subagent` ツール（LangChain Tool）

## ツール引数

- `role`: サブエージェントの役割
- `task`: 実行タスク
- `context`: 補足情報（任意）
- `constraints`: 制約配列（任意）
- `output_format`: `text` / `markdown` / `json`
- `max_output_chars`: 返却文字数上限

## 使い方（LangGraph）

```python
from langgraph.prebuilt import create_react_agent
from tools import create_subagent_launcher_tool
from utils.model_helper import build_model

model = build_model()
subagent_tool = create_subagent_launcher_tool(model)

agent = create_react_agent(
    model=model,
    tools=[subagent_tool],
)
```

## 実行イメージ

`launch_subagent` を呼び出すと、内部で `SystemMessage` と `HumanMessage` を組み立ててモデルを実行し、結果文字列を返します。  
出力が長すぎる場合は `max_output_chars` で切り詰め、末尾に `truncated` 情報を付与します。

## 注意点

- 現在の実装は「同一モデルを使った軽量サブエージェント実行」です。
- 役割分離をさらに強化したい場合は、将来的に `role` ごとのモデル切り替えや、ワーカー用グラフ分岐を追加してください。

