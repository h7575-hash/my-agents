"""エージェント - 再利用可能なエージェント

循環インポートを避けるため、パッケント直下では遅延インポートのみ行います。
利用時は各モジュールから直接 import してください。
例: from agents.prompt_master_agent import PromptMasterAgent
"""

__all__ = [
    "PromptMasterAgent",
    "NewsCollectorAgent",
    "AIOreAgent",
    "NotifyAssistantAgent",
]


def __getattr__(name: str):
    """遅延インポート（agents パッケント経由で参照されたときのみロード）"""
    if name == "PromptMasterAgent":
        from .prompt_master_agent import PromptMasterAgent
        return PromptMasterAgent
    if name == "NewsCollectorAgent":
        from .news_collector_agent import NewsCollectorAgent
        return NewsCollectorAgent
    if name == "AIOreAgent":
        from .ai_ore_agent import AIOreAgent
        return AIOreAgent
    if name == "NotifyAssistantAgent":
        from .notify_assistant_agent import NotifyAssistantAgent
        return NotifyAssistantAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
