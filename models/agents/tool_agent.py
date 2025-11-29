# backend.py

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3
from PIL import Image
import os 
import re
import json
import io
from google import genai
import requests

load_dotenv()
google_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=google_api_key)

@tool
def upload_report(title: str, file_bytes: bytes, filename: str) -> str:
    """
    Upload a PDF report to Django API as multipart/form-data.
    Params:
        title: Title of the report
        file_bytes: Raw PDF file bytes
        filename: Name of the uploaded file (example: 'report.pdf')
    """

    url = "http://django-backend:8000/api/reports/report"

    try:
        # Multipart form-data
        files = {
            "file": (filename, file_bytes, "application/pdf")
        }

        data = {
            "title": title
        }

        response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            return f"Report Uploaded Successfully 🎉\n\nResponse: {response.json()}"
        else:
            return f"Upload Failed ❌: {response.text}"

    except Exception as e:
        return f"Server error 🔥: {str(e)}"


# -------------------
# 1. LLM
# -------------------
llm = ChatOpenAI()

# -------------------
# 2. Tools
# -------------------
# Tools
tools = [ upload_report]

llm_with_tools = llm.bind_tools(tools)

# -------------------
# 3. State
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# -------------------
# 4. Nodes
# -------------------
def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call."""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

# -------------------
# 5. Checkpointer
# -------------------
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# -------------------
# 6. Graph
# -------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")

graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge('tools', 'chat_node')

chatbot = graph.compile(checkpointer=checkpointer)

# -------------------
# 7. Helper
# -------------------
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)