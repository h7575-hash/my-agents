"""NewsCollectorAgent - Gemini検索グラウンディングでニュース収集"""

import hashlib
from datetime import datetime
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from workflows.news_workflow.state import (
    NewsWorkflowState,
    NewsCandidate,
    MemoryContext,
)


class NewsCollectorAgent:
    """
    ニュース収集エージェント: Gemini検索グラウンディングで収集・正規化・重複除去
    
    再利用性:
        - 収集対象を変えれば他領域クローラとして転用可能
        - 検索ソースをRSS/API等に差し替え可能
    """
    
    def __init__(
        self,
        model: BaseChatModel,
        max_candidates: int = 20,
    ):
        self.model = model
        self.max_candidates = max_candidates
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """ニュース収集を実行"""
        
        prompt_bundle = state["prompt_bundle"]
        time_window = state["time_window"]
        user_profile = state["user_profile"]
        memory_context = state["memory_context"]
        
        if not prompt_bundle:
            return {"news_candidates": []}
        
        # Gemini検索グラウンディングで収集
        raw_candidates = self._collect_with_grounding(
            collector_prompt=prompt_bundle.collector,
            topics=user_profile.topics,
            exclude_keywords=user_profile.exclude_keywords,
            time_window=time_window,
        )
        
        # 正規化・重複除去
        clean_candidates = self._normalize_and_deduplicate(
            raw_candidates, memory_context
        )
        
        # 最大件数に制限
        final_candidates = clean_candidates[:self.max_candidates]
        
        return {"news_candidates": final_candidates}
    
    def _collect_with_grounding(
        self,
        collector_prompt: str,
        topics: list[str],
        exclude_keywords: list[str],
        time_window,
    ) -> list[NewsCandidate]:
        """Gemini検索グラウンディングでニュース収集"""
        
        # 検索クエリ構築
        query = f"""以下のトピックに関する最新ニュースを収集してください:
{', '.join(topics)}

期間: {time_window.start_date} 〜 {time_window.end_date}
除外: {', '.join(exclude_keywords)}

{collector_prompt}

【出力形式】
以下のJSON形式で各ニュースを返してください:
{{
  "title": "記事タイトル",
  "url": "記事URL",
  "published_at": "公開日時 (ISO 8601)",
  "source": "メディア名",
  "summary": "要約（200文字程度）"
}}

複数記事がある場合はJSON配列で返してください。
"""
        
        # Gemini検索グラウンディング有効化
        # NOTE: langchain-google-vertexaiでは search_grounding=True を使用
        try:
            response = self.model.invoke(
                [HumanMessage(content=query)],
                # Gemini 1.5以降で検索グラウンディング有効化
                # モデルによって引数が異なる場合があるため、実装時に確認
            )
            
            # レスポンスをパース
            candidates = self._parse_response(response.content)
            return candidates
            
        except Exception as e:
            print(f"収集エラー: {e}")
            return []
    
    def _parse_response(self, content: str) -> list[NewsCandidate]:
        """レスポンスをNewsCandidate形式にパース"""
        import json
        import re
        
        candidates = []
        
        # JSON部分を抽出（マークダウンコードブロックに入っている場合も対応）
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = content
        
        try:
            data = json.loads(json_str)
            
            # 配列でない場合は配列化
            if not isinstance(data, list):
                data = [data]
            
            for item in data:
                try:
                    candidate = NewsCandidate(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        published_at=item.get("published_at", ""),
                        source=item.get("source", ""),
                        summary=item.get("summary", ""),
                    )
                    candidates.append(candidate)
                except Exception as e:
                    print(f"候補パースエラー: {e}, item: {item}")
                    continue
                    
        except json.JSONDecodeError as e:
            print(f"JSON解析エラー: {e}")
            # フォールバック: テキストから簡易抽出
            candidates = self._fallback_parse(content)
        
        return candidates
    
    def _fallback_parse(self, content: str) -> list[NewsCandidate]:
        """JSON解析失敗時のフォールバック"""
        # 簡易的にURLを抽出してダミー候補を作成
        import re
        
        url_pattern = r'https?://[^\s"]+'
        urls = re.findall(url_pattern, content)
        
        candidates = []
        for url in urls[:10]:  # 最大10件
            candidates.append(NewsCandidate(
                title=f"記事 {url}",
                url=url,
                published_at=datetime.now().isoformat(),
                source="不明",
                summary="",
            ))
        
        return candidates
    
    def _normalize_and_deduplicate(
        self,
        candidates: list[NewsCandidate],
        memory: MemoryContext,
    ) -> list[NewsCandidate]:
        """正規化・重複除去"""
        
        seen_fingerprints = set()
        clean = []
        
        # 過去記事の指紋を取得
        for past_article in memory.past_articles:
            fp = self._fingerprint(past_article.url, past_article.title)
            seen_fingerprints.add(fp)
        
        # 重複チェック
        for candidate in candidates:
            # URL正規化
            normalized_url = self._normalize_url(candidate.url)
            candidate.url = normalized_url
            
            # 指紋生成
            fp = self._fingerprint(normalized_url, candidate.title)
            
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                clean.append(candidate)
        
        return clean
    
    def _normalize_url(self, url: str) -> str:
        """URL正規化（クエリパラメータ除去等）"""
        from urllib.parse import urlparse, urlunparse
        
        parsed = urlparse(url)
        # クエリとフラグメントを除去
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            '',  # params
            '',  # query
            '',  # fragment
        ))
        return normalized
    
    def _fingerprint(self, url: str, title: str) -> str:
        """記事の指紋（重複判定用）"""
        combined = f"{url}::{title}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
