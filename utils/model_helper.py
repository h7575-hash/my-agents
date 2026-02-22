import os
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_vertexai import ChatVertexAI

# プロジェクトルートのサービスアカウントキーを常に使用
_CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / "news-for-problem-2fe0d80c17d1.json"


def build_model() -> ChatVertexAI:
    """Vertex AI のチャットモデルを構築。GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION を使用。"""
    if _CREDENTIALS_FILE.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_CREDENTIALS_FILE)

    model_name = os.getenv("VERTEX_MODEL", "gemini-1.5-flash")
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    return ChatVertexAI(
        model=model_name,
        project=project,
        location=location,
        temperature=0.2,
    )


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str) and text:
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)
    return str(content)


def invoke_with_chat_model(
    model: BaseChatModel, messages: list[HumanMessage | AIMessage]
) -> str:
    """任意の LangChain チャットモデルでメッセージを実行し、テキストを返す。"""
    answer = model.invoke(messages)
    return _extract_text_content(answer.content)
