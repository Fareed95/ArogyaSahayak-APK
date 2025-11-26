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

  // --- Initialize WebSocket ---
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

        // 🔥 NEW: image upload ack
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
          console.error("WebSocket Error:", data.message);
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
    ws.onerror = (err) => console.error(err);

    return () => ws.close();
  }, [wsUrl]);

  // --- Format message content with markdown and code blocks ---
  const formatMessageContent = (content) => {
    if (!content) return [];

    const elements = [];
    const lines = content.split("\n");
    let currentBlock = [];
    let inCodeBlock = false;
    let currentLanguage = "";

    const flushTextBlock = () => {
      if (currentBlock.length > 0) {
        elements.push({
          type: "text",
          content: currentBlock.join("\n"),
        });
        currentBlock = [];
      }
    };

    const flushCodeBlock = () => {
      if (currentBlock.length > 0) {
        elements.push({
          type: "code",
          content: currentBlock.join("\n"),
          language: currentLanguage,
        });
        currentBlock = [];
        inCodeBlock = false;
        currentLanguage = "";
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Check for code block start
      const codeBlockMatch = line.match(/^```(\w*)/);
      if (codeBlockMatch && !inCodeBlock) {
        flushTextBlock();
        inCodeBlock = true;
        currentLanguage = codeBlockMatch[1] || "text";
        continue;
      }

      // Check for code block end
      if (inCodeBlock && line.trim() === "```") {
        flushCodeBlock();
        continue;
      }

      if (inCodeBlock) {
        currentBlock.push(line);
      } else {
        // Handle inline code and other markdown in text blocks
        let processedLine = line;

        // Convert **bold** to styled text
        processedLine = processedLine.replace(
          /\*\*(.*?)\*\*/g,
          "<strong>$1</strong>"
        );

        // Convert *italic* to styled text
        processedLine = processedLine.replace(
          /\*(.*?)\*/g,
          "<em>$1</em>"
        );

        // Convert `code` to inline code
        processedLine = processedLine.replace(
          /`([^`]+)`/g,
          '<code class="inline-code">$1</code>'
        );

        currentBlock.push(processedLine);
      }
    }

    // Flush any remaining content
    if (inCodeBlock) {
      flushCodeBlock();
    } else {
      flushTextBlock();
    }

    return elements;
  };

  // --- Render formatted message content ---
  const renderFormattedContent = (formattedElements) => {
    return formattedElements.map((element, index) => {
      if (element.type === "text") {
        return (
          <div
            key={index}
            style={{
              marginBottom: 12,
              lineHeight: 1.6,
              fontSize: "14px",
            }}
            dangerouslySetInnerHTML={{ __html: element.content }}
          />
        );
      } else if (element.type === "code") {
        return (
          <div key={index} style={{ marginBottom: 12 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                backgroundColor: "rgba(0, 0, 0, 0.3)",
                padding: "8px 12px",
                borderTopLeftRadius: 8,
                borderTopRightRadius: 8,
                borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
              }}
            >
              <span
                style={{
                  fontSize: "12px",
                  color: "#888",
                  fontWeight: 600,
                  textTransform: "uppercase",
                }}
              >
                {element.language || "code"}
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(element.content);
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#888",
                  cursor: "pointer",
                  fontSize: "12px",
                  padding: "4px 8px",
                  borderRadius: 4,
                }}
                onMouseOver={(e) =>
                  (e.target.style.backgroundColor =
                    "rgba(255, 255, 255, 0.1)")
                }
                onMouseOut={(e) =>
                  (e.target.style.backgroundColor = "transparent")
                }
              >
                📋 Copy
              </button>
            </div>
            <pre
              style={{
                margin: 0,
                padding: "16px",
                backgroundColor: "rgba(0, 0, 0, 0.4)",
                borderRadius: "0 0 8px 8px",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderTop: "none",
                overflowX: "auto",
                fontSize: "13px",
                lineHeight: 1.4,
                fontFamily:
                  '"Fira Code", "Monaco", "Cascadia Code", monospace',
                color: "#e0e0e0",
              }}
            >
              <code>{element.content}</code>
            </pre>
          </div>
        );
      }
      return null;
    });
  };

  // --- Render message content ---
  const renderMessageContent = (message) => {
    if (message.role === "system") {
      return (
        <div style={{ lineHeight: 1.6 }}>
          {message.tool && (
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                backgroundColor: "rgba(245, 158, 11, 0.2)",
                padding: "4px 8px",
                borderRadius: 6,
                marginBottom: 8,
                fontSize: "12px",
                fontWeight: 600,
                color: "#f59e0b",
              }}
            >
              🛠️ Using: {message.tool}
            </div>
          )}
          <div style={{ color: message.isError ? "#ef4444" : "#d1d5db" }}>
            {message.content}
          </div>
        </div>
      );
    }

    const formattedElements = formatMessageContent(message.content);
    return renderFormattedContent(formattedElements);
  };

  // --- Send user message ---
  const sendMessage = () => {
    if (!input.trim() || !socket || socket.readyState !== WebSocket.OPEN)
      return;
    currentAssistantRef.current = "";
    socket.send(JSON.stringify({ type: "user_message", content: input }));
    setInput("");
  };

  // --- NEW: Handle Image Upload ---
  const handleImageUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file || !socket || socket.readyState !== WebSocket.OPEN) return;

    // Show preview as user message
    const previewUrl = URL.createObjectURL(file);
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: "📷 Image uploaded",
        imagePreview: previewUrl,
        inProgress: false,
      },
    ]);

    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result;
// remove "data:image/...;base64,"

      socket.send(
        JSON.stringify({
          type: "uploading_file",
          file: base64,
        })
      );
    };

    reader.readAsDataURL(file);
  };

  // --- New Chat ---
  const newChat = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      setMessages([]);
      socket.send(JSON.stringify({ type: "set_thread", thread_id: null }));
    }
  };

  // --- Switch Thread ---
  const switchThread = (id) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "set_thread", thread_id: id }));
    }
  };

  // --- Auto scroll ---
  const chatEndRef = useRef(null);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        backgroundColor: "#0f0f0f",
        color: "#e0e0e0",
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          width: 280,
          backgroundColor: "#1a1a1a",
          padding: "20px 16px",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid #333",
        }}
      >
        <div style={{ marginBottom: 24 }}>
          <h3
            style={{
              margin: "0 0 8px 0",
              fontSize: "20px",
              background:
                "linear-gradient(135deg, #667ee0 0%, #764ba2 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              fontWeight: 700,
            }}
          >
            🤖 LangGraph Chat
          </h3>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              fontSize: "12px",
              color: connected ? "#10b981" : "#ef4444",
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: connected ? "#10b981" : "#ef4444",
                marginRight: 6,
              }}
            />
            {connected ? "Connected" : "Disconnected"}
          </div>
        </div>

        <button
          onClick={newChat}
          style={{
            marginBottom: 20,
            padding: "12px 16px",
            background:
              "linear-gradient(135deg, #667ee0 0%, #764ba2 100%)",
            color: "white",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "14px",
            transition: "all 0.2s ease",
          }}
          onMouseOver={(e) =>
            (e.target.style.transform = "translateY(-1px)")
          }
          onMouseOut={(e) =>
            (e.target.style.transform = "translateY(0)")
          }
        >
          🆕 New Chat
        </button>

        <div>
          <h4
            style={{
              margin: "0 0 12px 0",
              fontSize: "14px",
              color: "#888",
              fontWeight: 600,
            }}
          >
            Chat History
          </h4>
          <div style={{ maxHeight: "60vh", overflowY: "auto" }}>
            {threads.map((t) => (
              <button
                key={t}
                onClick={() => switchThread(t)}
                style={{
                  display: "block",
                  marginBottom: 8,
                  backgroundColor:
                    t === threadId
                      ? "rgba(102, 126, 224, 0.2)"
                      : "#2d2d2d",
                  color: t === threadId ? "#fff" : "#ccc",
                  width: "100%",
                  textAlign: "left",
                  padding: "10px 12px",
                  border:
                    t === threadId
                      ? "1px solid #667ee0"
                      : "1px solid #333",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: "13px",
                  transition: "all 0.2s ease",
                  wordBreak: "break-all",
                }}
                onMouseOver={(e) => {
                  if (t !== threadId) {
                    e.target.style.backgroundColor = "#3d3d3d";
                  }
                }}
                onMouseOut={(e) => {
                  if (t !== threadId) {
                    e.target.style.backgroundColor = "#2d2d2d";
                  }
                }}
              >
                💬 {t.slice(0, 20)}...
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#0f0f0f",
        }}
      >
        {/* Chat Header */}
        <div
          style={{
            padding: "16px 24px",
            borderBottom: "1px solid #333",
            backgroundColor: "#1a1a1a",
          }}
        >
          <div style={{ fontSize: "14px", color: "#888" }}>
            Current Thread:{" "}
            <span
              style={{ color: "#667ee0", fontFamily: "monospace" }}
            >
              {threadId || "New Chat"}
            </span>
          </div>
        </div>

        {/* Messages Area */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "24px",
            background:
              "linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%)",
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                color: "#666",
                marginTop: "40%",
                fontSize: "16px",
              }}
            >
              Start a new conversation or select a previous chat
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} style={{ marginBottom: 24 }}>
                {/* System Messages (Tool calls / acks) */}
                {message.role === "system" && (
                  <div
                    style={{
                      padding: "16px",
                      borderRadius: 12,
                      background: "rgba(255, 255, 255, 0.05)",
                      backdropFilter: "blur(10px)",
                      border:
                        "1px solid rgba(255, 255, 255, 0.1)",
                      boxShadow:
                        "0 4px 6px rgba(0, 0, 0, 0.1)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 12,
                      }}
                    >
                      <div
                        style={{
                          width: 32,
                          height: 32,
                          borderRadius: "50%",
                          backgroundColor: message.isError
                            ? "#ef4444"
                            : "#f59e0b",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "14px",
                          fontWeight: "bold",
                          color: "white",
                          flexShrink: 0,
                        }}
                      >
                        {message.isError ? "⚠️" : "🛠️"}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div
                          style={{
                            fontWeight: 600,
                            color: message.isError
                              ? "#ef4444"
                              : "#f59e0b",
                            marginBottom: 8,
                            fontSize: "14px",
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                          }}
                        >
                          {message.isError ? "Error" : "System"}
                          {message.tool && (
                            <span
                              style={{
                                backgroundColor:
                                  "rgba(245, 158, 11, 0.2)",
                                padding: "2px 8px",
                                borderRadius: 4,
                                fontSize: "12px",
                                fontWeight: 500,
                              }}
                            >
                              {message.tool}
                            </span>
                          )}
                        </div>
                        {renderMessageContent(message)}
                      </div>
                    </div>
                  </div>
                )}

                {/* User Messages */}
                {message.role === "user" && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                    }}
                  >
                    <div
                      style={{
                        maxWidth: "70%",
                        padding: "16px 20px",
                        borderRadius: 18,
                        background:
                          "linear-gradient(135deg, #667ee0 0%, #764ba2 100%)",
                        color: "white",
                        border:
                          "1px solid rgba(102, 126, 224, 0.3)",
                      }}
                    >
                      <div style={{ lineHeight: 1.5 }}>
                        {message.content}
                      </div>
                      {message.imagePreview && (
                        <img
                          src={message.imagePreview}
                          alt="Uploaded"
                          style={{
                            marginTop: 10,
                            maxWidth: "100%",
                            borderRadius: 10,
                            border:
                              "1px solid rgba(255,255,255,0.2)",
                          }}
                        />
                      )}
                    </div>
                  </div>
                )}

                {/* Assistant Messages */}
                {message.role === "assistant" && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-start",
                    }}
                  >
                    <div
                      style={{
                        maxWidth: "70%",
                        padding: "20px",
                        borderRadius: 12,
                        backgroundColor:
                          "rgba(255, 255, 255, 0.05)",
                        border:
                          "1px solid rgba(255, 255, 255, 0.1)",
                        backdropFilter: "blur(10px)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 12,
                        }}
                      >
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: "50%",
                            backgroundColor: "#10b981",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "14px",
                            fontWeight: "bold",
                            color: "white",
                            flexShrink: 0,
                          }}
                        >
                          🤖
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              fontWeight: 600,
                              color: "#10b981",
                              marginBottom: 12,
                              fontSize: "14px",
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            Assistant
                            {message.inProgress && (
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 4,
                                  fontSize: "12px",
                                  fontWeight: 400,
                                  color: "#6b7280",
                                }}
                              >
                                <div
                                  style={{
                                    width: 12,
                                    height: 12,
                                    border:
                                      "2px solid #10b981",
                                    borderTop:
                                      "2px solid transparent",
                                    borderRadius: "50%",
                                    animation:
                                      "spin 1s linear infinite",
                                  }}
                                />
                                Thinking...
                              </div>
                            )}
                          </div>
                          <div
                            style={{
                              color: "#e0e0e0",
                              lineHeight: 1.6,
                            }}
                          >
                            {renderMessageContent(message)}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Area */}
        <div
          style={{
            padding: "20px 24px",
            backgroundColor: "#1a1a1a",
            borderTop: "1px solid #333",
          }}
        >
          <div
            style={{
              display: "flex",
              gap: 12,
              alignItems: "center",
            }}
          >
            {/* Hidden file input for image upload */}
            <input
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              id="imageUpload"
              onChange={handleImageUpload}
            />

            {/* Upload button */}
            <label
              htmlFor="imageUpload"
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                background: "#333",
                color: "#fff",
                cursor: "pointer",
                fontWeight: 600,
                fontSize: "14px",
                border: "1px solid #444",
                display: "flex",
                alignItems: "center",
                gap: 6,
                whiteSpace: "nowrap",
              }}
            >
              📷 Upload
            </label>

            {/* Text input */}
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Type your message..."
              style={{
                flex: 1,
                padding: "14px 16px",
                borderRadius: 12,
                border: "1px solid #333",
                backgroundColor: "#2d2d2d",
                color: "#e0e0e0",
                fontSize: "14px",
                transition: "all 0.2s ease",
                outline: "none",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#667ee0")}
              onBlur={(e) => (e.target.style.borderColor = "#333")}
            />

            {/* Send button */}
            <button
              onClick={sendMessage}
              disabled={!input.trim()}
              style={{
                padding: "14px 24px",
                borderRadius: 12,
                border: "none",
                background: input.trim()
                  ? "linear-gradient(135deg, #667ee0 0%, #764ba2 100%)"
                  : "#333",
                color: "#fff",
                cursor: input.trim() ? "pointer" : "not-allowed",
                fontWeight: 600,
                fontSize: "14px",
                transition: "all 0.2s ease",
                opacity: input.trim() ? 1 : 0.6,
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* CSS Styles */}
      <style jsx>{`
        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }

        .inline-code {
          background: rgba(0, 0, 0, 0.4);
          padding: 2px 6px;
          border-radius: 4px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          font-family: "Fira Code", Monaco, "Cascadia Code", monospace;
          font-size: 0.9em;
          color: #e0e0e0;
        }

        strong {
          font-weight: 600;
          color: #fff;
        }

        em {
          font-style: italic;
          color: #ccc;
        }
      `}</style>
    </div>
  );
}
