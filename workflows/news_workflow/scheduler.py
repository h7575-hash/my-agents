"""週次スケジューラ - 週次ニュースワークフローの定期実行"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from langchain_core.language_models import BaseChatModel

from .state import (
    NewsWorkflowState,
    UserProfile,
    TimeWindow,
    MemoryContext,
    FeedbackContext,
)
from .graph import create_news_workflow_graph
from .stores import MemoryStore, FeedbackStore


class WeeklyNewsScheduler:
    """
    週次ニュースエージェントのスケジューラ
    
    運用:
        - cron / Airflow / Cloud Scheduler等で定期実行
        - 失敗時の再実行ロジック
        - 監視メトリクス出力
    """
    
    def __init__(
        self,
        model: BaseChatModel,
        memory_store: Optional[MemoryStore] = None,
        feedback_store: Optional[FeedbackStore] = None,
        max_retries: int = 2,
    ):
        self.model = model
        self.memory_store = memory_store or MemoryStore()
        self.feedback_store = feedback_store or FeedbackStore()
        self.max_retries = max_retries
    
    def run_weekly(
        self,
        user_id: str,
        topics: list[str],
        exclude_keywords: Optional[list[str]] = None,
        lookback_days: int = 7,
    ) -> dict:
        """週次実行のエントリーポイント"""
        
        run_id = str(uuid.uuid4())[:8]
        
        print(f"[{run_id}] 週次ニュース収集開始")
        print(f"  ユーザ: {user_id}")
        print(f"  トピック: {', '.join(topics)}")
        
        try:
            # 初期状態構築
            initial_state = self._build_initial_state(
                run_id=run_id,
                user_id=user_id,
                topics=topics,
                exclude_keywords=exclude_keywords or [],
                lookback_days=lookback_days,
            )
            
            # グラフ実行
            graph = create_news_workflow_graph(
                model=self.model,
                memory_store=self.memory_store,
                feedback_store=self.feedback_store,
                max_retries=self.max_retries,
            )
            
            result = graph.invoke(initial_state)
            
            # 結果処理
            self._process_result(user_id, result)
            
            print(f"[{run_id}] 完了: {result.get('notification_status')}")
            
            return {
                "run_id": run_id,
                "status": "success",
                "notification_status": result.get("notification_status"),
                "report_path": result.get("final_report_path"),
            }
            
        except Exception as e:
            print(f"[{run_id}] エラー: {e}")
            
            # 失敗原因を記憶
            self.memory_store.add_failure(user_id, str(e))
            
            return {
                "run_id": run_id,
                "status": "error",
                "error": str(e),
            }
    
    def _build_initial_state(
        self,
        run_id: str,
        user_id: str,
        topics: list[str],
        exclude_keywords: list[str],
        lookback_days: int,
    ) -> NewsWorkflowState:
        """初期状態を構築"""
        
        # 期間設定
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        time_window = TimeWindow(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        
        # ユーザプロファイル
        user_profile = UserProfile(
            topics=topics,
            exclude_keywords=exclude_keywords,
        )
        
        # 記憶・FBロード
        memory_context = self.memory_store.load_memory(user_id)
        feedback_context = self.feedback_store.load_feedback(user_id)
        
        return NewsWorkflowState(
            run_id=run_id,
            user_profile=user_profile,
            time_window=time_window,
            memory_context=memory_context,
            feedback_context=feedback_context,
            news_candidates=[],
            decision="notify_suppress",  # デフォルト
            approved_digest=None,
            revision_request=None,
            no_notify_reason=None,
            prompt_bundle=None,
            final_report_path=None,
            notification_status=None,
            retry_count=0,
            max_retries=self.max_retries,
        )
    
    def _process_result(self, user_id: str, result: NewsWorkflowState) -> None:
        """結果を処理して記憶・FBストアを更新"""
        
        # approve時: 採用記事を記憶に保存
        if result.get("approved_digest"):
            for candidate in result["approved_digest"].candidates:
                self.memory_store.add_article(user_id, candidate)
        
        # notify_suppress時: 改善ヒントを記憶に保存
        elif result.get("no_notify_reason"):
            reason = result["no_notify_reason"]
            if reason.query_improvement_hint:
                self.memory_store.add_failure(
                    user_id,
                    f"改善案: {reason.query_improvement_hint}"
                )
        
        # メモリ保存
        self.memory_store.save_memory(user_id, result["memory_context"])
    
    def add_user_feedback(
        self,
        user_id: str,
        article_url: str,
        liked: bool,
        reason: str,
    ) -> None:
        """ユーザFBを追加（手動呼び出し）"""
        
        self.feedback_store.add_feedback(
            user_id=user_id,
            liked=liked,
            reason=reason,
            article_url=article_url,
        )
        
        print(f"FB追加: {user_id} - {'👍' if liked else '👎'} {reason}")


# ===== 監視メトリクス =====

class WorkflowMetrics:
    """ワークフロー監視メトリクス"""
    
    @staticmethod
    def log_metrics(run_id: str, result: dict) -> None:
        """メトリクスをログ出力（将来的にはPrometheus等へ）"""
        
        print(f"[Metrics] run_id={run_id}")
        print(f"  status={result.get('status')}")
        print(f"  notification_status={result.get('notification_status')}")
        print(f"  report_path={result.get('report_path')}")
        
        # TODO: Prometheus、CloudWatch等へメトリクス送信
