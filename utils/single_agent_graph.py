from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from utils.model_helper import invoke_with_chat_model


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


def create_graph(model: BaseChatModel):
    def call_model(state: ChatState) -> ChatState:
        response_text = invoke_with_chat_model(model, state["messages"])
        return {"messages": [AIMessage(content=response_text)]}

    builder = StateGraph(ChatState)
    builder.add_node("call_model", call_model)
    builder.add_edge(START, "call_model")
    builder.add_edge("call_model", END)
    return builder.compile()
