"""LangGraphワークフローグラフ - 週次ニュースエージェント"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.language_models import BaseChatModel

from .state import NewsWorkflowState
from agents.prompt_master_agent import PromptMasterAgent
from agents.news_collector_agent import NewsCollectorAgent
from agents.ai_ore_agent import AIOreAgent
from agents.notify_assistant_agent import NotifyAssistantAgent
from .stores import MemoryStore, FeedbackStore


def create_news_workflow_graph(
    model: BaseChatModel,
    memory_store: MemoryStore,
    feedback_store: FeedbackStore,
    max_retries: int = 2,
) -> StateGraph:
    """週次ニュースワークフローグラフを構築"""
    
    # エージェント初期化
    prompt_master = PromptMasterAgent(model)
    news_collector = NewsCollectorAgent(model)
    ai_ore = AIOreAgent(model)
    notify_assistant = NotifyAssistantAgent()
    
    # グラフ構築
    workflow = StateGraph(NewsWorkflowState)
    
    # ノード定義
    workflow.add_node("prompt_master", prompt_master)
    workflow.add_node("news_collector", news_collector)
    workflow.add_node("ai_ore", ai_ore)
    workflow.add_node("notify_assistant", notify_assistant)
    workflow.add_node("no_notify_exit", _no_notify_exit_node)
    workflow.add_node("increment_retry", _increment_retry_node)
    
    # エントリーポイント
    workflow.set_entry_point("prompt_master")
    
    # フロー定義
    workflow.add_edge("prompt_master", "news_collector")
    workflow.add_edge("news_collector", "ai_ore")
    
    # AI俺の3分岐判定
    workflow.add_conditional_edges(
        "ai_ore",
        _decision_router,
        {
            "approve": "notify_assistant",
            "revise": "increment_retry",
            "notify_suppress": "no_notify_exit",
        }
    )
    
    # 再試行ループ
    workflow.add_conditional_edges(
        "increment_retry",
        _should_retry(max_retries),
        {
            "retry": "prompt_master",
            "max_retries_reached": "no_notify_exit",
        }
    )
    
    # 終了
    workflow.add_edge("notify_assistant", END)
    workflow.add_edge("no_notify_exit", END)
    
    return workflow.compile()


def _decision_router(state: NewsWorkflowState) -> Literal["approve", "revise", "notify_suppress"]:
    """AI俺の判定結果でルーティング"""
    return state["decision"]


def _should_retry(max_retries: int):
    """再試行すべきか判定"""
    def router(state: NewsWorkflowState) -> Literal["retry", "max_retries_reached"]:
        if state["retry_count"] < max_retries:
            return "retry"
        else:
            return "max_retries_reached"
    return router


def _increment_retry_node(state: NewsWorkflowState) -> dict:
    """再試行カウンタをインクリメント"""
    return {
        "retry_count": state["retry_count"] + 1,
    }


def _no_notify_exit_node(state: NewsWorkflowState) -> dict:
    """通知しない終了ノード（記憶だけ保存）"""
    # NOTE: 実際の運用では、ここでno_notify_reasonをMemoryStoreに保存
    return {
        "final_report_path": None,
        "notification_status": "suppressed",
    }
