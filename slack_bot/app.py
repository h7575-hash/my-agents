"""Slack Bot - Slack Events API を受け取る FastAPI webhook サーバー."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time

from fastapi import FastAPI, Request, Response

from slack_bot.event_handler import dispatch_event

logger = logging.getLogger(__name__)

app = FastAPI(title="Slack Agent Bot")

_processed_events: dict[str, float] = {}
_MAX_CACHE_SIZE = 1000


@app.get("/")
async def root():
    """Slack の Request URL は /slack/events を指定してください。"""
    return {
        "ok": True,
        "message": "Slack Bot is running. Use https://<this-host>/slack/events as Request URL.",
    }


@app.get("/slack/events")
async def slack_events_get():
    """Slack は POST でチャレンジを送るため、GET では検証できません。"""
    return {"ok": False, "error": "Use POST to this URL for Slack Event Subscriptions."}


def _verify_signature(body_bytes: bytes, timestamp: str, signature: str) -> bool:
    """Slack リクエスト署名を検証."""
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        logger.warning("SLACK_SIGNING_SECRET 未設定 - 署名検証をスキップします")
        return True

    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body_bytes.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


def _is_duplicate(event_id: str) -> bool:
    """イベントIDの重複チェック."""
    if event_id in _processed_events:
        return True

    if len(_processed_events) > _MAX_CACHE_SIZE:
        cutoff = time.time() - 300
        expired = [k for k, v in _processed_events.items() if v < cutoff]
        for k in expired:
            del _processed_events[k]

    _processed_events[event_id] = time.time()
    return False


@app.post("/slack/events")
async def slack_events(request: Request):
    """Slack Events API のエンドポイント."""
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response(status_code=400, content="Invalid JSON")

    # URL Verification Challenge（署名検証より先に処理。Slack の検証時は challenge をそのまま返す）
    if body.get("type") == "url_verification":
        challenge = body.get("challenge")
        if challenge is not None:
            return {"challenge": challenge}
        return Response(status_code=400, content="Missing challenge")

    # 署名検証
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    signature = request.headers.get("X-Slack-Signature", "")
    if not _verify_signature(body_bytes, timestamp, signature):
        return Response(status_code=403)

    if body.get("type") == "event_callback":
        event_id = body.get("event_id", "")

        # Slack のリトライは無視
        retry_num = request.headers.get("X-Slack-Retry-Num")
        if retry_num:
            logger.info("Slack retry ignored: %s", retry_num)
            return {"ok": True}

        if _is_duplicate(event_id):
            return {"ok": True}

        event = body.get("event", {})
        if event.get("type") == "app_mention" and not event.get("bot_id"):
            dispatch_event(event)

    return {"ok": True}
