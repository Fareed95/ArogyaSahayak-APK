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

load_dotenv()
google_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=google_api_key)
@tool
def login(username: str, password: str) -> str:
    """
    A dummy login tool that simulates user authentication.
    """
    # In a real application, you would verify the username and password.
    if username == "user" and password == "pass":
        return "Login successful!"
    else:
        return "Invalid username or password."
@tool
def describe_image(image_path: str, prompt: str = "Describe the image") -> str:
    """
    Analyze the image using Gemini Vision + return rich markdown output
    including headings, bullets, prompt-specific details & structured formatting.
    """

    # Load & convert image
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        return "❌ Image could not be opened. Please upload a valid PNG/JPG image."

    # Convert to bytes
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    image_bytes = buffer.getvalue()

    # Send to Gemini
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "text": f"""
You must analyze this image **in detail**.

### Required Response Format
- Use Markdown only
- Include a Title
- Use bullet points, sub-headings
- Include a section: **🧠 Prompt-Specific Insight** based on:
**"{prompt}"**

### Avoid
- Do not repeat general statements unnecessarily
- Do not ask questions
"""
                },
                {"inline_data": {"mime_type": "image/jpeg", "data": image_bytes}}
            ],
        )

        # Force markdown semantics
        return f"""# 🖼️ Image Analysis

{response.text}

---
📌 **Prompt Used:** `{prompt}`
"""

    except Exception as e:
        return f"⚠️ Vision API Error: {str(e)}"

# -------------------
# 1. LLM
# -------------------
llm = ChatOpenAI()

# -------------------
# 2. Tools
# -------------------
# Tools
tools = [ login, describe_image ]

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