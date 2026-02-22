"""LangGraph State定義 - 週次ニュースワークフロー"""

from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# ===== データモデル =====

class UserProfile(BaseModel):
    """ユーザプロファイル"""
    topics: list[str] = Field(description="監視トピック")
    exclude_keywords: list[str] = Field(default_factory=list, description="除外キーワード")
    language: str = Field(default="ja", description="言語")
    region: str = Field(default="JP", description="地域")


class TimeWindow(BaseModel):
    """収集期間"""
    start_date: str = Field(description="開始日時 (ISO 8601)")
    end_date: str = Field(description="終了日時 (ISO 8601)")


class PromptBundle(BaseModel):
    """各エージェントへ配布するプロンプト集"""
    collector: str = Field(description="NewsCollectorAgent用プロンプト")
    judge: str = Field(description="AIOreAgent用プロンプト")
    notify: str = Field(description="NotifyAssistantAgent用プロンプト")


class NewsCandidate(BaseModel):
    """収集したニュース候補"""
    title: str
    url: str
    published_at: str
    source: str
    summary: str
    relevance_score: float = Field(default=0.0)


class ApprovedDigest(BaseModel):
    """承認されたニュースダイジェスト"""
    candidates: list[NewsCandidate]
    digest_text: str = Field(description="最終レポート本文")
    reason: str = Field(description="approve理由")
    evidence_urls: list[str] = Field(description="根拠URL")


class RevisionRequest(BaseModel):
    """再生成要求"""
    reason: str = Field(description="revise理由")
    improvement_hints: list[str] = Field(description="改善ヒント")
    missing_topics: list[str] = Field(default_factory=list, description="不足している観点")


class NoNotifyReason(BaseModel):
    """通知しない理由"""
    reason: str = Field(description="通知抑制理由")
    missing_topics: list[str] = Field(default_factory=list)
    query_improvement_hint: str = Field(default="", description="次週の収集改善案")


class MemoryContext(BaseModel):
    """記憶コンテキスト"""
    past_articles: list[NewsCandidate] = Field(default_factory=list, description="過去採用記事")
    topic_trends: dict[str, float] = Field(default_factory=dict, description="トピック推移")
    failure_reasons: list[str] = Field(default_factory=list, description="失敗原因")


class FeedbackContext(BaseModel):
    """フィードバックコンテキスト"""
    liked_reasons: list[str] = Field(default_factory=list, description="高評価理由")
    disliked_reasons: list[str] = Field(default_factory=list, description="低評価理由")
    topic_priorities: dict[str, float] = Field(default_factory=dict, description="トピック優先度")


# ===== LangGraph State =====

class NewsWorkflowState(TypedDict):
    """週次ニュースワークフローの状態"""
    
    # 入力
    user_profile: UserProfile
    time_window: TimeWindow
    
    # プロンプト管理
    prompt_bundle: Optional[PromptBundle]
    
    # 収集結果
    news_candidates: list[NewsCandidate]
    
    # 判定結果
    decision: Literal["approve", "revise", "notify_suppress"]
    approved_digest: Optional[ApprovedDigest]
    revision_request: Optional[RevisionRequest]
    no_notify_reason: Optional[NoNotifyReason]
    
    # 記憶・FB
    memory_context: MemoryContext
    feedback_context: FeedbackContext
    
    # 出力
    final_report_path: Optional[str]
    notification_status: Optional[str]
    
    # メタ
    run_id: str
    retry_count: int
    max_retries: int
