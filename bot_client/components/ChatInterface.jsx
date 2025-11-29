"use client";

import { useEffect, useRef, useState } from "react";

export default function ChatBot({ wsUrl = "ws://localhost:8001/ws/chat" }) {
  const [connected, setConnected] = useState(false);
  const [socket, setSocket] = useState(null);
  const [threadId, setThreadId] = useState(null);
  const [threads, setThreads] = useState([]);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const currentAssistantRef = useRef("");

  // -------------------------------------------------------
  // INIT WEBSOCKET
  // -------------------------------------------------------
  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    setSocket(ws);

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ type: "get_threads" }));
    };

    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);

      switch (data.type) {
        case "session_create":
          setThreadId(data.thread_id);
          setMessages([]);
          break;

        case "threads_list":
          setThreads(data.threads);
          break;

        case "thread_set":
          setThreadId(data.thread_id);
          break;

        case "thread_messages":
          setMessages(
            data.messages.map((m) => ({
              role: m.role === "tool" ? "system" : m.role,
              content: m.content,
              tool: m.tool,
              inProgress: false,
            }))
          );
          break;

        case "user_ack":
          setMessages((prev) => [
            ...prev,
            { role: "user", content: data.content, inProgress: false },
          ]);
          break;

        case "tool_message":
          setMessages((prev) => [
            ...prev,
            {
              role: "system",
              content: data.content,
              tool: data.tool,
              inProgress: false,
            },
          ]);
          break;

        case "assistant_chunk":
          currentAssistantRef.current += data.content;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === "assistant" && last.inProgress) {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...last,
                content: currentAssistantRef.current,
              };
              return updated;
            } else {
              return [
                ...prev,
                {
                  role: "assistant",
                  content: currentAssistantRef.current,
                  inProgress: true,
                },
              ];
            }
          });
          break;

        case "assistant_final":
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.role === "assistant" && last.inProgress) {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...last,
                content: data.content,
                inProgress: false,
              };
              return updated;
            } else {
              return [
                ...prev,
                {
                  role: "assistant",
                  content: data.content,
                  inProgress: false,
                },
              ];
            }
          });
          currentAssistantRef.current = "";
          break;

        // 📄 PDF Upload Response
        case "report_uploaded":
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: data.content,
              inProgress: false,
            },
          ]);
          break;

        // Image Upload ACK
        case "upload_ack":
          setMessages((prev) => [
            ...prev,
            {
              role: "system",
              content: data.message || "Image received, analyzing...",
              inProgress: false,
            },
          ]);
          break;

        case "error":
          setMessages((prev) => [
            ...prev,
            {
              role: "system",
              content: `Error: ${data.message}`,
              inProgress: false,
              isError: true,
            },
          ]);
          break;

        default:
          console.log("Unhandled:", data);
      }
    };

    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, [wsUrl]);

  // -------------------------------------------------------
  // FORMATTER
  // -------------------------------------------------------
  const formatMessageContent = (content) => {
    if (!content) return [];
    return [{ type: "text", content }];
  };

  const renderFormattedContent = (elements) => {
    return elements.map((el, i) => (
      <div key={i} dangerouslySetInnerHTML={{ __html: el.content }} />
    ));
  };

  const renderMessageContent = (msg) =>
    renderFormattedContent(formatMessageContent(msg.content));

  // -------------------------------------------------------
  // SEND NORMAL MESSAGE
  // -------------------------------------------------------
  const sendMessage = () => {
    if (!input.trim()) return;
    currentAssistantRef.current = "";
    socket.send(JSON.stringify({ type: "user_message", content: input }));
    setInput("");
  };

  // -------------------------------------------------------
  // 🔥 PDF UPLOAD HANDLER
  // -------------------------------------------------------
  const handlePDFUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file || !socket) return;

    if (file.type !== "application/pdf") {
      alert("Upload only PDF!");
      return;
    }

    // Show message in UI
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: `📄 PDF Uploaded: ${file.name}`,
        inProgress: false,
      },
    ]);

    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result.replace("data:application/pdf;base64,", "");
      socket.send(
        JSON.stringify({
          type: "upload_report_direct",
          filename: file.name,
          title: file.name.replace(".pdf", ""),
          file_base64: base64,
        })
      );
    };

    reader.readAsDataURL(file);
  };

  // -------------------------------------------------------
  // IMAGE UPLOAD (unchanged)
  // -------------------------------------------------------
  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file || !socket) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: "📷 Image uploaded", imagePreview: URL.createObjectURL(file) },
    ]);

    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result.replace(/^data:image\/[a-z]+;base64,/, "");
      socket.send(
        JSON.stringify({
          type: "uploading_file",
          file: base64,
        })
      );
    };

    reader.readAsDataURL(file);
  };

  // -------------------------------------------------------
  // NEW THREAD
  // -------------------------------------------------------
  const newChat = () => {
    setMessages([]);
    socket.send(JSON.stringify({ type: "set_thread", thread_id: null }));
  };

  // -------------------------------------------------------
  // SWITCH THREAD
  // -------------------------------------------------------
  const switchThread = (id) => {
    socket.send(JSON.stringify({ type: "set_thread", thread_id: id }));
  };

  // AUTOSCROLL
  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // -------------------------------------------------------
  // RENDER UI
  // -------------------------------------------------------
  return (
    <div style={{ height: "100vh", display: "flex", background: "#0f0f0f" }}>
      {/* Sidebar */}
      <div style={{ width: 280, background: "#1a1a1a", padding: 20 }}>
        <h3 style={{ color: "#667ee0" }}>LangGraph Chat</h3>
        <button onClick={newChat} style={{ marginBottom: 20 }}>
          🆕 New Chat
        </button>

        <h4>Chat History</h4>
        {threads.map((t) => (
          <button
            key={t}
            onClick={() => switchThread(t)}
            style={{
              display: "block",
              marginBottom: 8,
              background: t === threadId ? "#667ee033" : "#2d2d2d",
              padding: 10,
              borderRadius: 6,
              color: "#ddd",
            }}
          >
            💬 {t.slice(0, 18)}...
          </button>
        ))}
      </div>

      {/* Chat Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Messages */}
        <div style={{ flex: 1, padding: 20, overflowY: "auto" }}>
          {messages.map((m, i) => (
            <div key={i} style={{ marginBottom: 20 }}>
              <b>{m.role === "assistant" ? "🤖" : m.role === "user" ? "🧑" : "🛠️"}</b>
              <div>{renderMessageContent(m)}</div>
              {m.imagePreview && (
                <img
                  src={m.imagePreview}
                  style={{ marginTop: 10, maxWidth: "40%" }}
                />
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <div style={{ padding: 20, display: "flex", gap: 10 }}>
          {/* Hidden upload inputs */}
          <input type="file" accept="application/pdf" id="pdfUpload" style={{ display: "none" }} onChange={handlePDFUpload} />
          <input type="file" accept="image/*" id="imageUpload" style={{ display: "none" }} onChange={handleImageUpload} />

          {/* Buttons */}
          <label htmlFor="pdfUpload" style={{ padding: 10, background: "#333", color: "#fff", borderRadius: 8 }}>
            📄 PDF
          </label>

          <label htmlFor="imageUpload" style={{ padding: 10, background: "#333", color: "#fff", borderRadius: 8 }}>
            📷 Image
          </label>

          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Type a message"
            style={{ flex: 1, padding: 12 }}
          />

          <button onClick={sendMessage} style={{ padding: "12px 20px", background: "#667ee0", color: "#fff" }}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
