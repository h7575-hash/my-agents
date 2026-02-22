"""Slack連絡係 - LangGraph ReAct Agent for Slack interactions."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from tools.subagent_launcher_tool import create_subagent_launcher_tool
from tools.workflow_runner_tool import create_workflow_runner_tool
from utils.loaders import PromptLoader
from utils.model_helper import build_model

logger = logging.getLogger(__name__)


class SlackAgentState(TypedDict):
    messages: Annotated[list, add_messages]


def _extract_text(content: Any) -> str:
    """LLMレスポンスからテキストを抽出."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts) if parts else str(content)
    return str(content)


def create_slack_agent_graph(model, tools):
    """Slack連絡係のReActエージェントグラフを構築."""
    model_with_tools = model.bind_tools(tools)

    def agent_node(state: SlackAgentState) -> dict:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: SlackAgentState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(tools)

    builder = StateGraph(SlackAgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    builder.add_edge("tools", "agent")

    return builder.compile()


def run_slack_agent(
    user_message: str,
    user_id: str = "",
    thread_context: str | None = None,
) -> str:
    """Slackエージェントを実行し、応答テキストを返す.

    Args:
        user_message: ユーザーのメッセージ（ボットメンション除去済み）
        user_id: 送信者のSlackユーザーID
        thread_context: このスレッドの会話履歴（直前まで）。省略時は単発メッセージとして扱う

    Returns:
        Slackに送り返す応答テキスト
    """
    model = build_model()

    tools = [
        create_workflow_runner_tool(model),
        create_subagent_launcher_tool(model),
    ]

    graph = create_slack_agent_graph(model, tools)

    prompt_loader = PromptLoader()
    system_prompt = prompt_loader.load("slack_agent", "system")

    if user_id:
        system_prompt += f"\n\n現在の対話相手のSlackユーザーID: {user_id}"

    if thread_context:
        system_prompt += (
            "\n\n## このスレッドの会話履歴（直前に至るまで）\n"
            "以下を踏まえ、最後のユーザーメッセージに応答してください。\n\n"
            "---\n"
            f"{thread_context}\n"
            "---"
        )

    result = graph.invoke(
        {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]
        }
    )

    final_message = result["messages"][-1]
    return _extract_text(final_message.content)
