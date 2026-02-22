"""Vertex AI 呼び出しテスト."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage

from utils.model_helper import build_model, invoke_with_chat_model


def main() -> int:
    print("Vertex AI 呼び出しテストを開始します...")
    print()

    try:
        model = build_model()
        print("モデル構築 OK:", type(model).__name__)

        messages = [HumanMessage(content="「Vertex AI」を一言で説明してください。")]
        response = invoke_with_chat_model(model, messages)

        print("応答:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        print()
        print("テスト完了: 成功")
        return 0
    except Exception as e:
        print("エラー:", e)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
