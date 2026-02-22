"""記憶・フィードバックストア - 過去ニュース記憶とユーザFB記憶"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from workflows.news_workflow.state import (
    NewsCandidate,
    MemoryContext,
    FeedbackContext,
)


class MemoryStore:
    """
    記憶ストア: 過去採用記事、トピック推移、失敗原因を保存
    """
    
    def __init__(self, storage_dir: str = "memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def load_memory(self, user_id: str, lookback_weeks: int = 4) -> MemoryContext:
        """過去記憶をロード"""
        
        memory_file = self.storage_dir / f"{user_id}_memory.json"
        
        if not memory_file.exists():
            return MemoryContext()
        
        try:
            with open(memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 期限切れ記事をフィルタ
            cutoff_date = datetime.now() - timedelta(weeks=lookback_weeks)
            
            past_articles = []
            for article_data in data.get("past_articles", []):
                article = NewsCandidate(**article_data)
                # published_atで期限チェック
                try:
                    pub_date = datetime.fromisoformat(article.published_at)
                    if pub_date >= cutoff_date:
                        past_articles.append(article)
                except Exception:
                    # 日付パースエラーは無視
                    pass
            
            return MemoryContext(
                past_articles=past_articles,
                topic_trends=data.get("topic_trends", {}),
                failure_reasons=data.get("failure_reasons", [])[-10:],  # 最新10件
            )
            
        except Exception as e:
            print(f"記憶ロードエラー: {e}")
            return MemoryContext()
    
    def save_memory(self, user_id: str, context: MemoryContext) -> None:
        """記憶を保存"""
        
        memory_file = self.storage_dir / f"{user_id}_memory.json"
        
        data = {
            "past_articles": [
                article.dict() for article in context.past_articles
            ],
            "topic_trends": context.topic_trends,
            "failure_reasons": context.failure_reasons,
            "updated_at": datetime.now().isoformat(),
        }
        
        try:
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"記憶保存エラー: {e}")
    
    def add_article(self, user_id: str, candidate: NewsCandidate) -> None:
        """採用記事を追加"""
        
        context = self.load_memory(user_id)
        context.past_articles.append(candidate)
        
        # トピック推移を更新（簡易的に記事数をカウント）
        # NOTE: より高度な実装では、トピック抽出とトレンド分析を行う
        
        self.save_memory(user_id, context)
    
    def add_failure(self, user_id: str, reason: str) -> None:
        """失敗原因を追加"""
        
        context = self.load_memory(user_id)
        context.failure_reasons.append(reason)
        self.save_memory(user_id, context)


class FeedbackStore:
    """
    フィードバックストア: ユーザ評価・嗜好を保存
    """
    
    def __init__(self, storage_dir: str = "feedback"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def load_feedback(self, user_id: str) -> FeedbackContext:
        """FBをロード"""
        
        fb_file = self.storage_dir / f"{user_id}_feedback.json"
        
        if not fb_file.exists():
            return FeedbackContext()
        
        try:
            with open(fb_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return FeedbackContext(
                liked_reasons=data.get("liked_reasons", []),
                disliked_reasons=data.get("disliked_reasons", []),
                topic_priorities=data.get("topic_priorities", {}),
            )
            
        except Exception as e:
            print(f"FB読み込みエラー: {e}")
            return FeedbackContext()
    
    def save_feedback(self, user_id: str, context: FeedbackContext) -> None:
        """FBを保存"""
        
        fb_file = self.storage_dir / f"{user_id}_feedback.json"
        
        data = {
            "liked_reasons": context.liked_reasons,
            "disliked_reasons": context.disliked_reasons,
            "topic_priorities": context.topic_priorities,
            "updated_at": datetime.now().isoformat(),
        }
        
        try:
            with open(fb_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"FB保存エラー: {e}")
    
    def add_feedback(
        self,
        user_id: str,
        liked: bool,
        reason: str,
        article_url: str,
    ) -> None:
        """ユーザFBを追加"""
        
        context = self.load_feedback(user_id)
        
        feedback_entry = f"{reason} (URL: {article_url})"
        
        if liked:
            context.liked_reasons.append(feedback_entry)
        else:
            context.disliked_reasons.append(feedback_entry)
        
        self.save_feedback(user_id, context)
    
    def update_topic_priority(
        self,
        user_id: str,
        topic: str,
        delta: float,
    ) -> None:
        """トピック優先度を更新"""
        
        context = self.load_feedback(user_id)
        
        current = context.topic_priorities.get(topic, 0.5)
        new_priority = max(0.0, min(1.0, current + delta))
        context.topic_priorities[topic] = new_priority
        
        self.save_feedback(user_id, context)
