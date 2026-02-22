"""Slack Bot エントリーポイント."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

import uvicorn

from slack_bot.app import app

if __name__ == "__main__":
    host = os.environ.get("SLACK_BOT_HOST", "0.0.0.0")
    # Cloud Run は PORT を注入するため、PORT を優先する
    port = int(os.environ.get("PORT", os.environ.get("SLACK_BOT_PORT", "3000")))
    ssl_certfile = os.environ.get("SLACK_BOT_SSL_CERT", "")
    ssl_keyfile = os.environ.get("SLACK_BOT_SSL_KEY", "")

    kwargs = {"host": host, "port": port, "log_level": "info"}
    if ssl_certfile and ssl_keyfile:
        kwargs["ssl_certfile"] = ssl_certfile
        kwargs["ssl_keyfile"] = ssl_keyfile

    uvicorn.run(app, **kwargs)
