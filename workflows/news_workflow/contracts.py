"""4エージェントノードのI/O契約と責務境界

各ノードは独立したモジュールとして再利用可能
"""

from typing import Protocol
from workflows.news_workflow.state import (
    NewsWorkflowState,
    UserProfile,
    PromptBundle,
    NewsCandidate,
    ApprovedDigest,
    RevisionRequest,
    NoNotifyReason,
    MemoryContext,
    FeedbackContext,
)


# ===== PromptMasterAgent =====

class PromptMasterAgentProtocol(Protocol):
    """プロンプトマスターエージェント契約"""
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """
        役割: プロンプト収集・管理・更新、FB反映、各エージェントへのプロンプト配布
        
        入力:
            - user_profile: ユーザプロファイル
            - feedback_context: FB記憶
            - memory_context: 過去実行記憶
            - retry_count: 現在の再試行回数
        
        出力:
            - prompt_bundle: 各エージェント向けプロンプト集
        
        再利用ポイント:
            - ドメインごとにテンプレート差し替え可能（ニュース/PC管理/連絡管理）
            - FBの反映ルールをカスタマイズ可能
        """
        ...


# ===== NewsCollectorAgent =====

class NewsCollectorAgentProtocol(Protocol):
    """ニュース収集エージェント契約"""
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """
        役割: Gemini検索グラウンディングでニュース収集、正規化、重複除去
        
        入力:
            - prompt_bundle.collector: 収集指示プロンプト
            - time_window: 収集期間
            - user_profile.topics: 監視トピック
            - user_profile.exclude_keywords: 除外キーワード
            - memory_context: 重複判定用の過去記事
        
        出力:
            - news_candidates: 収集したニュース候補リスト
        
        再利用ポイント:
            - 「収集対象」を変えれば他領域クローラとして転用可能
            - 検索ソースをRSS/API等に差し替え可能
        """
        ...


# ===== AIOreAgent =====

class AIOreAgentProtocol(Protocol):
    """AI俺エージェント契約"""
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """
        役割: あなたの分身として「通知されてうれしいか」を判定し、改善指示を返す
        
        入力:
            - news_candidates: 収集されたニュース候補
            - prompt_bundle.judge: 判定基準プロンプト
            - memory_context: 過去採用記事
            - feedback_context: ユーザ嗜好記憶
        
        出力:
            - decision: "approve" / "revise" / "notify_suppress"
            - approved_digest: (approve時) 承認ダイジェスト
            - revision_request: (revise時) 再生成要求
            - no_notify_reason: (notify_suppress時) 通知抑制理由
        
        再利用ポイント:
            - ペルソナ・評価軸を差し替えれば意思決定ゲートとして汎用化可能
            - 判定基準をドメイン別にカスタマイズ
        """
        ...


# ===== NotifyAssistantAgent =====

class NotifyAssistantAgentProtocol(Protocol):
    """なんでも通知アシスタントエージェント契約"""
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """
        役割: Markdown生成、保存、Pushover通知を実行
        
        入力:
            - approved_digest: 承認されたダイジェスト
            - user_profile: 通知先情報
            - time_window: レポート期間
        
        出力:
            - final_report_path: 保存先パス
            - notification_status: 通知ステータス
        
        再利用ポイント:
            - 通知チャンネルアダプタ追加でSlack/Emailにも拡張可能
            - 出力フォーマットを差し替え可能（MD / HTML / PDF）
        """
        ...


# ===== ストアプロトコル =====

class MemoryStoreProtocol(Protocol):
    """記憶ストア契約"""
    
    def load_memory(self, user_id: str, lookback_weeks: int = 4) -> MemoryContext:
        """過去記憶をロード"""
        ...
    
    def save_memory(self, user_id: str, context: MemoryContext) -> None:
        """記憶を保存"""
        ...
    
    def add_article(self, user_id: str, candidate: NewsCandidate) -> None:
        """採用記事を追加"""
        ...


class FeedbackStoreProtocol(Protocol):
    """フィードバックストア契約"""
    
    def load_feedback(self, user_id: str) -> FeedbackContext:
        """FBをロード"""
        ...
    
    def save_feedback(self, user_id: str, context: FeedbackContext) -> None:
        """FBを保存"""
        ...
    
    def add_feedback(
        self,
        user_id: str,
        liked: bool,
        reason: str,
        article_url: str,
    ) -> None:
        """ユーザFBを追加"""
        ...
