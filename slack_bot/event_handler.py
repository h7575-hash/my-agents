"""Slack イベントハンドラ - イベントを受け取りエージェントへディスパッチ."""

from __future__ import annotations

import logging
import os
import re
import threading

import requests

from agents.slack_agent import run_slack_agent

logger = logging.getLogger(__name__)


def _fetch_thread_replies(channel: str, thread_ts: str) -> list[dict]:
    """スレッド内の全メッセージを conversations.replies で取得する."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return []

    all_messages: list[dict] = []
    cursor: str | None = None

    while True:
        url = "https://slack.com/api/conversations.replies"
        params: dict = {"channel": channel, "ts": thread_ts}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            params=params,
            timeout=10,
        )
        data = resp.json()

        if not data.get("ok"):
            logger.warning(
                "conversations.replies failed: %s", data.get("error", "unknown")
            )
            return all_messages

        messages = data.get("messages", [])
        all_messages.extend(messages)

        if not data.get("has_more"):
            break
        cursor = (data.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            break

    return all_messages


def _format_thread_context(messages: list[dict], current_ts: str | None) -> str:
    """スレッドのメッセージ一覧をエージェント用のテキストに整形する.
    現在のメッセージ（current_ts）は履歴に含めず、直前までの会話とする.
    """
    lines: list[str] = []
    for m in messages:
        ts = m.get("ts", "")
        if current_ts and ts == current_ts:
            continue
        text = (m.get("text") or "").strip()
        text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()
        if not text:
            continue
        if m.get("bot_id"):
            speaker = "Bot"
        else:
            speaker = "ユーザー"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines) if lines else ""


def dispatch_event(event: dict) -> None:
    """Slack イベントをバックグラウンドスレッドで処理."""
    thread = threading.Thread(target=_process_event, args=(event,), daemon=True)
    thread.start()


def _process_event(event: dict) -> None:
    """1件の Slack イベントを処理."""
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts") or event.get("ts")
    current_ts = event.get("ts")

    try:
        text = event.get("text", "")
        user_id = event.get("user", "")

        clean_text = re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()
        if not clean_text:
            clean_text = "こんにちは"

        thread_context = ""
        replies = _fetch_thread_replies(channel, thread_ts)
        if replies:
            thread_context = _format_thread_context(replies, current_ts)

        logger.info("Processing message from %s: %s", user_id, clean_text[:100])

        response = run_slack_agent(
            user_message=clean_text,
            user_id=user_id,
            thread_context=thread_context or None,
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
