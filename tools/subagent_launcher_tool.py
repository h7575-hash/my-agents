"""LangGraphエージェント用: 汎用サブエージェント起動ツール."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class SubAgentLaunchInput(BaseModel):
    """サブエージェント起動ツールの入力スキーマ."""

    role: str = Field(
        description="サブエージェントの役割。例: Pythonレビュアー、要約担当、設計相談役",
        min_length=1,
    )
    task: str = Field(
        description="サブエージェントに実行させる具体的なタスク指示",
        min_length=1,
    )
    context: str = Field(
        default="",
        description="補足コンテキスト。対象コード断片、前提条件、制約など",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="追加制約の配列。例: ['箇条書きで出力', '英語禁止']",
    )
    output_format: str = Field(
        default="markdown",
        description="期待する出力形式。text / markdown / json のいずれか",
    )
    max_output_chars: int = Field(
        default=4000,
        ge=200,
        le=20000,
        description="返却する最大文字数。長い場合は末尾を省略して返す",
    )


def _to_text(content: Any) -> str:
    """LLMレスポンスを文字列に正規化."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(parts).strip()

    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)

    return str(content)


def create_subagent_launcher_tool(model: BaseChatModel):
    """サブエージェント起動用のLangChain Toolを生成."""

    @tool("launch_subagent", args_schema=SubAgentLaunchInput)
    def launch_subagent(
        role: str,
        task: str,
        context: str = "",
        constraints: list[str] | None = None,
        output_format: str = "markdown",
        max_output_chars: int = 4000,
    ) -> str:
        """
        任意ロールのサブエージェントを起動し、指定タスクの結果を返す。

        このツールは、LangGraphエージェントが必要に応じて専門ロールを立ち上げるための
        汎用ディスパッチャとして使えます。
        """
        constraint_lines = constraints or []
        formatted_constraints = (
            "\n".join(f"- {line}" for line in constraint_lines)
            if constraint_lines
            else "- なし"
        )

        system_prompt = (
            "あなたは指定された役割を厳密に実行するサブエージェントです。\n"
            f"役割: {role}\n"
            f"出力形式: {output_format}\n"
            "事実と推論を分けて簡潔に回答してください。"
        )

        user_prompt = (
            "以下のタスクを実行してください。\n\n"
            f"## タスク\n{task}\n\n"
            f"## コンテキスト\n{context or '（なし）'}\n\n"
            f"## 制約\n{formatted_constraints}\n"
        )

        response = model.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        text = _to_text(response.content).strip()
        if len(text) > max_output_chars:
            clipped = text[:max_output_chars].rstrip()
            return (
                f"{clipped}\n\n"
                f"[truncated: 元の出力は {len(text)} 文字、上限 {max_output_chars} 文字]"
            )
        return text

    return launch_subagent

