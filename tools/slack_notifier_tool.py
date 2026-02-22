"""LangGraphエージェント用: Slack メッセージ送信ツール."""

from __future__ import annotations

import os
from typing import Optional

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class SlackNotifyInput(BaseModel):
    """Slack通知ツールの入力スキーマ."""

    channel: str = Field(
        description="送信先のSlackチャンネル名(例: '#general')またはチャンネルID",
        min_length=1,
    )
    text: str = Field(
        description="送信するメッセージ本文",
        min_length=1,
    )
    mention_enabled: bool = Field(
        default=False,
        description=(
            "Trueの場合、環境変数 SLACK_MENTION_TARGETS で指定された"
            "ユーザー/グループにメンションを付与する"
        ),
    )
    thread_ts: Optional[str] = Field(
        default=None,
        description="スレッドに返信する場合の親メッセージのタイムスタンプ(ts)",
    )


def _build_mention_prefix(targets: list[str]) -> str:
    """メンション対象リストからSlack記法のプレフィックスを組み立てる."""
    if not targets:
        return ""

    special_keywords = {"here", "channel", "everyone"}
    parts: list[str] = []
    for target in targets:
        cleaned = target.strip().lstrip("@")
        if cleaned.lower() in special_keywords:
            parts.append(f"<!{cleaned.lower()}>")
        else:
            parts.append(f"<@{cleaned}>")
    return " ".join(parts)


def _resolve_token() -> str:
    """環境変数からSlack Bot Tokenを取得."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError(
            "環境変数 SLACK_BOT_TOKEN が設定されていません。"
            "Slack App の Bot User OAuth Token を設定してください。"
        )
    return token


def _resolve_mention_targets() -> list[str]:
    """環境変数からデフォルトのメンション対象を取得.

    SLACK_MENTION_TARGETS にカンマ区切りで指定する。
    例: "U01ABCDEF,U02GHIJKL,here"
    """
    raw = os.environ.get("SLACK_MENTION_TARGETS", "")
    if not raw.strip():
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def create_slack_notifier_tool():
    """Slack通知用のLangChain Toolを生成."""

    @tool("send_slack_message", args_schema=SlackNotifyInput)
    def send_slack_message(
        channel: str,
        text: str,
        mention_enabled: bool = False,
        thread_ts: str | None = None,
    ) -> str:
        """
        Slackチャンネルにメッセージを送信する。

        mention_enabled=True の場合、環境変数 SLACK_MENTION_TARGETS に
        設定されたユーザー/グループへのメンションをメッセージ先頭に付与する。
        """
        token = _resolve_token()
        targets = _resolve_mention_targets()

        body = text
        if mention_enabled and targets:
            prefix = _build_mention_prefix(targets)
            body = f"{prefix}\n{text}"

        payload: dict = {
            "channel": channel,
            "text": body,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts

        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("ok"):
            error = data.get("error", "unknown_error")
            return f"Slack送信失敗: {error}"

        ts = data.get("ts", "")
        ch = data.get("channel", channel)
        return f"Slack送信成功: channel={ch}, ts={ts}"

    return send_slack_message
