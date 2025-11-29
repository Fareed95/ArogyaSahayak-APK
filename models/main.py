import json
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query,UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
from agents.tool_agent import chatbot, retrieve_all_threads, upload_report
import base64
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from starlette.websockets import WebSocketState

UPLOAD_DIR = "uploaded_images" 
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------- Utilities ----------
def generate_thread_id():
    return str(uuid.uuid4())

executor = ThreadPoolExecutor(max_workers=2)  # For running synchronous stream

# ---------- FastAPI App ----------
app = FastAPI()

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"path": file_path}

# ---------- Stream Helper ----------
async def send_chunk(ws: WebSocket, chunk):
    """Send a single chunk/message to WebSocket safely"""
    if ws.application_state != WebSocketState.CONNECTED:
        return

    if isinstance(chunk, ToolMessage):
        await safe_send(ws, json.dumps({
            "type": "tool_message",
            "tool": getattr(chunk, "name", "tool"),
            "content": chunk.content
        }))
    elif isinstance(chunk, AIMessage):
        await safe_send(ws, json.dumps({
            "type": "assistant_chunk",
            "content": chunk.content
        }))


async def safe_send(ws, msg):
    if ws.application_state == WebSocketState.CONNECTED:
        try:
            await ws.send_text(msg)
        except:
            pass  # ignore if already closed


async def stream_to_ws(websocket: WebSocket, user_input: str, thread_id: str):
    """Run LangGraph stream in executor and push chunks to WebSocket"""
    loop = asyncio.get_event_loop()

    def run_stream():
        for msg_chunk, metadata in chatbot.stream(
            {"messages": [HumanMessage(content=user_input)]},
            config={
                "configurable": {"thread_id": thread_id},
                "metadata": {"thread_id": thread_id},
                "run_name": "chat_turn",
            },
            stream_mode="messages",
        ):
            asyncio.run_coroutine_threadsafe(send_chunk(websocket, msg_chunk), loop)

    # Run synchronous stream in thread
    await loop.run_in_executor(executor, run_stream)

    # Send final message
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", [])
    final_msg = next((m.content for m in reversed(messages) if isinstance(m, AIMessage)), "")
    await safe_send(websocket,json.dumps({"type": "assistant_final", "content": final_msg}))

def serialize_messages(messages):
    """Serialize messages for frontend"""
    serialized = []
    for m in messages:
        if isinstance(m, HumanMessage):
            serialized.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            serialized.append({"role": "assistant", "content": m.content})
        elif isinstance(m, ToolMessage):
            serialized.append({"role": "tool", "content": m.content, "tool": getattr(m, "name", "tool")})
    return serialized

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket, thread_id: Optional[str] = Query(None)):
    await websocket.accept()

    if not thread_id:
        thread_id = generate_thread_id()
        await safe_send(websocket,json.dumps({"type": "session_create", "thread_id": thread_id}))
    else:
        # Send existing thread messages when connecting to existing thread
        try:
            state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
            messages = state.values.get("messages", [])
            await safe_send(websocket,json.dumps({
                "type": "thread_messages",
                "thread_id": thread_id,
                "messages": serialize_messages(messages)
            }))
        except Exception as e:
            print(f"Error loading thread {thread_id}: {e}")
            # If thread doesn't exist, create new one
            thread_id = generate_thread_id()
            await safe_send(websocket,json.dumps({"type": "session_create", "thread_id": thread_id}))

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            msg_type = data.get("type")

            if msg_type == "user_message":
                content = data.get("content", "")
                await safe_send(websocket,json.dumps({"type": "user_ack", "content": content}))
                await stream_to_ws(websocket, content, thread_id)

            elif msg_type == "get_threads":
                threads = retrieve_all_threads()
                await safe_send(websocket,json.dumps({"type": "threads_list", "threads": threads}))

            elif msg_type == "set_thread":
                new_thread_id = data.get("thread_id")
                if not new_thread_id:
                    # Create new thread
                    new_thread_id = generate_thread_id()
                    thread_id = new_thread_id
                    await safe_send(websocket,json.dumps({
                        "type": "session_create", 
                        "thread_id": thread_id
                    }))
                    # Clear messages for new thread
                    await safe_send(websocket,json.dumps({
                        "type": "thread_messages",
                        "thread_id": thread_id,
                        "messages": []
                    }))
                else:
                    # Switch to existing thread
                    thread_id = new_thread_id
                    try:
                        state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
                        messages = state.values.get("messages", [])
                        await safe_send(websocket,json.dumps({
                            "type": "thread_set", 
                            "thread_id": thread_id
                        }))
                        await safe_send(websocket,json.dumps({
                            "type": "thread_messages",
                            "thread_id": thread_id,
                            "messages": serialize_messages(messages)
                        }))
                    except Exception as e:
                        await safe_send(websocket,json.dumps({
                            "type": "error", 
                            "message": f"Thread not found: {e}"
                        }))

            elif msg_type == "fetch_thread":
                requested_thread = data.get("thread_id")
                try:
                    state = chatbot.get_state(config={"configurable": {"thread_id": requested_thread}})
                    messages = state.values.get("messages", [])
                    await safe_send(websocket,json.dumps({
                        "type": "thread_messages",
                        "thread_id": requested_thread,
                        "messages": serialize_messages(messages)
                    }))
                except Exception as e:
                    await safe_send(websocket,json.dumps({
                        "type": "error", 
                        "message": f"Error fetching thread: {e}"
                    }))

            elif msg_type == "upload_report_direct":
                base64_pdf = data["file_base64"]
                filename = data.get("filename", "report.pdf")
                title = data.get("title", "Untitled Report")

                pdf_bytes = base64.b64decode(base64_pdf)

                # --- DIRECT TOOL INVOCATION ---
                result = upload_report.invoke({
                    "title": title,
                    "file_bytes": pdf_bytes,
                    "filename": filename
                })

                await safe_send(websocket, json.dumps({
                    "type": "report_uploaded",
                    "content": result
                }))

        
    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        await safe_send(websocket,json.dumps({"type": "error", "message": str(e)}))

# ---------- Run ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)