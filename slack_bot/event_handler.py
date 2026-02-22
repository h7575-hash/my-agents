"""Slack イベントハンドラ - イベントを受け取りエージェントへディスパッチ."""

from __future__ import annotations

import logging
import os
import re
import threading

import requests

from agents.slack_agent import run_slack_agent

logger = logging.getLogger(__name__)


def dispatch_event(event: dict) -> None:
    """Slack イベントをバックグラウンドスレッドで処理."""
    thread = threading.Thread(target=_process_event, args=(event,), daemon=True)
    thread.start()


def _process_event(event: dict) -> None:
    """1件の Slack イベントを処理."""
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts") or event.get("ts")

    try:
        text = event.get("text", "")
        user_id = event.get("user", "")

        clean_text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()
        if not clean_text:
            clean_text = "こんにちは"

        logger.info("Processing message from %s: %s", user_id, clean_text[:100])

        response = run_slack_agent(
            user_message=clean_text,
            user_id=user_id,
        )

        _send_reply(channel, response, thread_ts)

    except Exception as e:
        logger.exception("Failed to process Slack event")
        if channel:
            msg = (
                "申し訳ございません、処理中にエラーが発生しました。"
                "しばらくしてからお試しください。"
            )
            if os.environ.get("SLACK_BOT_SHOW_ERROR"):
                err_text = str(e).strip()[:200]
                msg += f"\n\n（詳細）{err_text}"
            _send_reply(channel, msg, thread_ts)


def _send_reply(channel: str, text: str, thread_ts: str | None = None) -> None:
    """Slack にメッセージを返信."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.error("SLACK_BOT_TOKEN not set")
        return

    payload: dict = {"channel": channel, "text": text}
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

    data = resp.json()
    if not data.get("ok"):
        logger.error("Slack reply failed: %s", data.get("error"))
