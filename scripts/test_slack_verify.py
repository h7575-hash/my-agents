"""Slack URL Verification のレスポンスをテストする。

使い方:
  # ローカル (ポート 3001 で起動している場合)
  python scripts/test_slack_verify.py http://localhost:3001/slack/events

  # Cloud Run
  python scripts/test_slack_verify.py https://my-agents-1072071838370.asia-northeast1.run.app/slack/events
"""

import json
import sys
import urllib.request

CHALLENGE_VALUE = "test_challenge_12345"
PAYLOAD = {"type": "url_verification", "challenge": CHALLENGE_VALUE}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_slack_verify.py <URL>")
        print("  Example: python scripts/test_slack_verify.py https://xxx.run.app/slack/events")
        return 1

    url = sys.argv[1].rstrip("/")
    if not url.endswith("/slack/events"):
        url = f"{url}/slack/events" if not url.endswith("/") else f"{url}slack/events"

    body = json.dumps(PAYLOAD).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"POST {url}")
    print(f"Body: {PAYLOAD}")
    print()

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
            code = resp.getcode()
            print(f"Status: {code}")
            print(f"Response: {data[:500]}{'...' if len(data) > 500 else ''}")
            if "placeholder" in data.lower() or "just a placeholder" in data.lower():
                print()
                print("NG: Cloud Run がプレースホルダーページを返しています。")
                print("    → コードがまだデプロイされていません。Cloud Run のビルド・デプロイを完了してください。")
                return 1
            try:
                out = json.loads(data)
                if out.get("challenge") == CHALLENGE_VALUE:
                    print()
                    print("OK: challenge が正しく返っています。Slack の Verify は通る想定です。")
                    return 0
                else:
                    print()
                    print("NG: レスポンスに challenge が含まれていないか、値が一致しません。")
                    return 1
            except json.JSONDecodeError:
                print()
                print("NG: レスポンスが JSON ではありません。")
                return 1
    except urllib.error.HTTPError as e:
        print(f"Status: {e.code}")
        print(e.read().decode("utf-8", errors="replace"))
        print()
        print("NG: HTTP エラーです。")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
