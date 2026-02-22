"""AIOreAgent - AI俺：通知価値判定エージェント"""

from typing import Literal
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from workflows.news_workflow.state import (
    NewsWorkflowState,
    ApprovedDigest,
    RevisionRequest,
    NoNotifyReason,
    NewsCandidate,
)


# ===== 構造化出力スキーマ =====

class JudgmentOutput(BaseModel):
    """AI俺の判定出力（3分岐）"""
    decision: Literal["approve", "revise", "notify_suppress"] = Field(
        description="判定結果: approve=通知, revise=改善再試行, notify_suppress=通知しない"
    )
    reason: str = Field(description="判定理由（自然文）")
    evidence_urls: list[str] = Field(description="根拠URL（最低1つ）")
    
    # decision別の詳細
    digest_text: str = Field(default="", description="approve時のダイジェスト本文")
    improvement_hints: list[str] = Field(default_factory=list, description="revise時の改善ヒント")
    missing_topics: list[str] = Field(default_factory=list, description="不足している観点")
    query_improvement_hint: str = Field(default="", description="notify_suppress時の次週改善案")


class AIOreAgent:
    """
    AI俺エージェント: ユーザの分身として通知価値を判定
    
    再利用性:
        - ペルソナ・評価軸を差し替えれば意思決定ゲートとして汎用化可能
        - 判定基準をドメイン別にカスタマイズ
    """
    
    def __init__(
        self,
        model: BaseChatModel,
    ):
        self.model = model
        self.parser = JsonOutputParser(pydantic_object=JudgmentOutput)
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """通知価値を判定"""
        
        prompt_bundle = state.get("prompt_bundle")
        news_candidates = state.get("news_candidates", [])
        memory_context = state["memory_context"]
        feedback_context = state["feedback_context"]
        
        if not prompt_bundle or not news_candidates:
            # 候補がない場合は通知抑制
            return self._no_candidates_result()
        
        # 判定実行
        judgment = self._judge(
            judge_prompt=prompt_bundle.judge,
            candidates=news_candidates,
            memory_context=memory_context,
            feedback_context=feedback_context,
        )
        
        # 判定結果に応じて出力を整形
        return self._format_result(judgment, news_candidates)
    
    def _judge(
        self,
        judge_prompt: str,
        candidates: list[NewsCandidate],
        memory_context,
        feedback_context,
    ) -> JudgmentOutput:
        """判定実行"""
        
        # 候補をテキスト化
        candidates_text = self._format_candidates(candidates)
        
        # 過去記事情報
        past_articles_text = self._format_past_articles(
            memory_context.past_articles[-10:]  # 直近10件
        )
        
        # 判定クエリ構築
        query = f"""{judge_prompt}

【収集されたニュース候補】
{candidates_text}

【過去4週の採用記事】
{past_articles_text}

【判定指示】
以下のJSON形式で判定結果を返してください:

{{
  "decision": "approve" or "revise" or "notify_suppress",
  "reason": "判定理由（自然文で詳しく）",
  "evidence_urls": ["根拠URL1", "根拠URL2", ...],
  
  // decision = "approve" の場合
  "digest_text": "今週のニュースダイジェスト本文（Markdown形式）",
  
  // decision = "revise" の場合
  "improvement_hints": ["改善ヒント1", "改善ヒント2", ...],
  "missing_topics": ["不足トピック1", "不足トピック2", ...],
  
  // decision = "notify_suppress" の場合
  "query_improvement_hint": "次週の収集クエリ改善案"
}}

【判定基準の再確認】
- approve: 通知して喜ぶ価値がある
- revise: 方向性は良いが物足りない（収集を改善すれば通知できそう）
- notify_suppress: 価値不足で通知不要（次週の改善案だけ残す）
"""
        
        try:
            # LLMで判定
            response = self.model.invoke([HumanMessage(content=query)])
            
            # JSON解析
            judgment = self.parser.parse(response.content)
            return judgment
            
        except Exception as e:
            print(f"判定エラー: {e}")
            # フォールバック: reviseを返す
            return JudgmentOutput(
                decision="revise",
                reason=f"判定処理でエラーが発生しました: {str(e)}",
                evidence_urls=[],
                improvement_hints=["エラー回復のため再収集してください"],
            )
    
    def _format_candidates(self, candidates: list[NewsCandidate]) -> str:
        """候補をテキスト形式に整形"""
        if not candidates:
            return "（候補なし）"
        
        lines = []
        for i, c in enumerate(candidates, 1):
            lines.append(f"{i}. {c.title}")
            lines.append(f"   URL: {c.url}")
            lines.append(f"   公開: {c.published_at} | ソース: {c.source}")
            lines.append(f"   要約: {c.summary}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_past_articles(self, past: list[NewsCandidate]) -> str:
        """過去記事をテキスト形式に整形"""
        if not past:
            return "（過去記事なし）"
        
        lines = []
        for c in past:
            lines.append(f"- {c.title} ({c.published_at})")
        
        return "\n".join(lines)
    
    def _format_result(
        self,
        judgment: JudgmentOutput,
        candidates: list[NewsCandidate],
    ) -> dict:
        """判定結果をState更新用に整形"""
        
        result = {
            "decision": judgment.decision,
        }
        
        if judgment.decision == "approve":
            result["approved_digest"] = ApprovedDigest(
                candidates=candidates,
                digest_text=judgment.digest_text,
                reason=judgment.reason,
                evidence_urls=judgment.evidence_urls,
            )
            result["revision_request"] = None
            result["no_notify_reason"] = None
            
        elif judgment.decision == "revise":
            result["revision_request"] = RevisionRequest(
                reason=judgment.reason,
                improvement_hints=judgment.improvement_hints,
                missing_topics=judgment.missing_topics,
            )
            result["approved_digest"] = None
            result["no_notify_reason"] = None
            
        elif judgment.decision == "notify_suppress":
            result["no_notify_reason"] = NoNotifyReason(
                reason=judgment.reason,
                missing_topics=judgment.missing_topics,
                query_improvement_hint=judgment.query_improvement_hint,
            )
            result["approved_digest"] = None
            result["revision_request"] = None
        
        return result
    
    def _no_candidates_result(self) -> dict:
        """候補なし時のデフォルト結果"""
        return {
            "decision": "notify_suppress",
            "no_notify_reason": NoNotifyReason(
                reason="収集されたニュース候補がありませんでした",
                missing_topics=[],
                query_improvement_hint="収集クエリを見直してください",
            ),
            "approved_digest": None,
            "revision_request": None,
        }
