"""NotifyAssistantAgent - なんでも通知アシスタント"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests

from workflows.news_workflow.state import (
    NewsWorkflowState,
    ApprovedDigest,
)


class NotifyAssistantAgent:
    """
    なんでも通知アシスタント: Markdown生成・保存・Pushover通知
    
    再利用性:
        - 通知チャンネルアダプタ追加でSlack/Emailにも拡張可能
        - 出力フォーマットを差し替え可能（MD / HTML / PDF）
    """
    
    def __init__(
        self,
        reports_dir: str = "reports",
        pushover_token: Optional[str] = None,
        pushover_user: Optional[str] = None,
    ):
        self.reports_dir = Path(reports_dir)
        self.pushover_token = pushover_token or os.getenv("PUSHOVER_TOKEN")
        self.pushover_user = pushover_user or os.getenv("PUSHOVER_USER")
    
    def __call__(self, state: NewsWorkflowState) -> dict:
        """Markdown保存とPushover通知を実行"""
        
        approved_digest = state.get("approved_digest")
        user_profile = state["user_profile"]
        time_window = state["time_window"]
        
        if not approved_digest:
            return {
                "final_report_path": None,
                "notification_status": "no_digest",
            }
        
        # Markdown生成
        markdown_content = self._generate_markdown(
            digest=approved_digest,
            user_profile=user_profile,
            time_window=time_window,
        )
        
        # 保存
        report_path = self._save_report(markdown_content, time_window)
        
        # Pushover通知
        notification_status = self._send_pushover(
            digest=approved_digest,
            report_path=report_path,
            topics=user_profile.topics,
        )
        
        return {
            "final_report_path": str(report_path),
            "notification_status": notification_status,
        }
    
    def _generate_markdown(
        self,
        digest: ApprovedDigest,
        user_profile,
        time_window,
    ) -> str:
        """Markdown生成"""
        
        lines = []
        
        # ヘッダー
        lines.append(f"# 今週の{user_profile.topics[0]}ニュース")
        lines.append(f"")
        lines.append(f"**期間**: {time_window.start_date} 〜 {time_window.end_date}  ")
        lines.append(f"**生成日時**: {datetime.now().isoformat()}  ")
        lines.append(f"")
        
        # ダイジェスト本文（AI俺が生成）
        lines.append("## 今週のまとめ")
        lines.append("")
        lines.append(digest.digest_text)
        lines.append("")
        
        # 記事一覧
        lines.append("## 記事一覧")
        lines.append("")
        for i, candidate in enumerate(digest.candidates, 1):
            lines.append(f"### {i}. {candidate.title}")
            lines.append(f"")
            lines.append(f"- **公開日**: {candidate.published_at}")
            lines.append(f"- **ソース**: {candidate.source}")
            lines.append(f"- **URL**: {candidate.url}")
            lines.append(f"")
            lines.append(f"{candidate.summary}")
            lines.append(f"")
        
        # 根拠URL
        lines.append("## 参考リンク")
        lines.append("")
        for url in digest.evidence_urls:
            lines.append(f"- {url}")
        lines.append("")
        
        # 判定理由
        lines.append("---")
        lines.append(f"**判定理由**: {digest.reason}")
        lines.append("")
        
        return "\n".join(lines)
    
    def _save_report(self, content: str, time_window) -> Path:
        """Markdownをファイル保存"""
        
        # ディレクトリ作成（YYYY/）
        start_date = datetime.fromisoformat(time_window.start_date)
        year_dir = self.reports_dir / str(start_date.year)
        year_dir.mkdir(parents=True, exist_ok=True)
        
        # ファイル名（weekly_YYYY-MM-DD.md）
        filename = f"weekly_{start_date.strftime('%Y-%m-%d')}.md"
        filepath = year_dir / filename
        
        # 保存
        filepath.write_text(content, encoding="utf-8")
        
        return filepath
    
    def _send_pushover(
        self,
        digest: ApprovedDigest,
        report_path: Path,
        topics: list[str],
    ) -> str:
        """Pushover通知送信"""
        
        if not self.pushover_token or not self.pushover_user:
            return "pushover_not_configured"
        
        # 通知タイトル（40文字以内）
        title = f"今週の{topics[0]}ニュース"
        if len(title) > 40:
            title = title[:37] + "..."
        
        # 通知本文（主要トピック3件の要約）
        message_lines = []
        for i, candidate in enumerate(digest.candidates[:3], 1):
            message_lines.append(f"{i}. {candidate.title}")
        
        message_lines.append(f"\n📄 保存先: {report_path}")
        message = "\n".join(message_lines)
        
        # Pushover API呼び出し
        try:
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": self.pushover_token,
                    "user": self.pushover_user,
                    "title": title,
                    "message": message,
                    "url": str(report_path),
                    "url_title": "レポートを開く",
                },
                timeout=10,
            )
            
            if response.status_code == 200:
                return "sent"
            else:
                return f"error_{response.status_code}"
                
        except Exception as e:
            print(f"Pushover送信エラー: {e}")
            return f"error: {str(e)}"
