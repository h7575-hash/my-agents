"""LangGraphエージェント用: ワークフロー実行ツール."""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

WORKFLOW_DESCRIPTIONS = {
    "news": "AI/LangGraph/Vertex AI関連の最新ニュースを収集・判定・通知する週次ニュースワークフロー",
}


class WorkflowRunInput(BaseModel):
    """ワークフロー実行ツールの入力スキーマ."""

    workflow_name: str = Field(
        description=(
            "実行するワークフロー名。"
            f"利用可能: {', '.join(WORKFLOW_DESCRIPTIONS.keys())}"
        ),
        min_length=1,
    )
    parameters: Optional[dict] = Field(
        default=None,
        description="ワークフローに渡す追加パラメータ（topics, lookback_days など）",
    )


def _run_news_workflow(model: BaseChatModel, parameters: dict | None) -> str:
    """ニュースワークフローを実行して結果を返す."""
    from utils.loaders import DataLoader
    from workflows.news_workflow.scheduler import WeeklyNewsScheduler

    data_loader = DataLoader()
    user_profile = data_loader.get_user_profile("default_user")
    workflow_config = data_loader.get_workflow_config()

    if not user_profile:
        return "エラー: ユーザプロファイルが見つかりませんでした。"

    scheduler = WeeklyNewsScheduler(
        model=model,
        max_retries=workflow_config.get("max_retries", 2),
    )

    topics = user_profile.get("topics", ["AI"])
    if parameters and "topics" in parameters:
        topics = parameters["topics"]

    lookback_days = workflow_config.get("lookback_days", 7)
    if parameters and "lookback_days" in parameters:
        lookback_days = parameters["lookback_days"]

    result = scheduler.run_weekly(
        user_id="default_user",
        topics=topics,
        exclude_keywords=user_profile.get("exclude_keywords", []),
        lookback_days=lookback_days,
    )

    status = result.get("status", "unknown")
    if status == "success":
        notification_status = result.get("notification_status", "不明")
        report_path = result.get("report_path")
        summary = (
            f"ワークフロー実行完了\n"
            f"• ステータス: {status}\n"
            f"• 通知: {notification_status}"
        )
        if report_path:
            summary += f"\n• レポート: {report_path}"
        return summary

    error = result.get("error", "不明なエラー")
    return f"ワークフロー実行失敗\n• ステータス: {status}\n• エラー: {error}"


_WORKFLOW_RUNNERS = {
    "news": _run_news_workflow,
}


def create_workflow_runner_tool(model: BaseChatModel):
    """ワークフロー実行用のLangChain Toolを生成."""

    @tool("run_workflow", args_schema=WorkflowRunInput)
    def run_workflow(
        workflow_name: str,
        parameters: dict | None = None,
    ) -> str:
        """
        登録済みワークフローを名前で実行し、結果を返す。

        利用可能なワークフロー:
        - news: AI/LangGraph/Vertex AI関連の最新ニュースを収集・判定・通知
        """
        runner = _WORKFLOW_RUNNERS.get(workflow_name)
        if not runner:
            available = ", ".join(_WORKFLOW_RUNNERS.keys())
            return f"未対応のワークフロー: {workflow_name}\n利用可能: {available}"

        try:
            logger.info("Running workflow: %s", workflow_name)
            return runner(model, parameters)
        except Exception as e:
            logger.exception("Workflow %s failed", workflow_name)
            return f"ワークフロー '{workflow_name}' の実行中にエラーが発生しました: {e}"

    return run_workflow
