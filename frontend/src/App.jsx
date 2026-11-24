import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    const text = input.trim();

    if (!text || loading) return;

    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
    ]);

    setLoading(true);

    try {
      const body = {
        session_id: sessionId,
        message: text,
      };

      if (systemPrompt.trim()) {
        body.system_prompt = systemPrompt.trim();
      }

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Request failed");
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          metadata: data.metadata,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          content: `Error: ${error.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app">
      <header>
        <div>
          <h1>Lyftr AI</h1>
          <p>Resilient LLM Chat</p>
        </div>

        <span className="status">● Online</span>
      </header>

      <main>
        <div className="system-box">
          <label htmlFor="systemPrompt">
            System prompt <span>optional</span>
          </label>

          <input
            id="systemPrompt"
            data-testid="system-prompt-input"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="e.g. Answer concisely and clearly"
          />
        </div>

        <div className="chat">
          {messages.length === 0 && (
            <div className="welcome">
              <div className="logo">AI</div>
              <h2>How can I help?</h2>
              <p>
                Start a conversation with the resilient
                LiteLLM-powered assistant.
              </p>
            </div>
          )}

          {messages.map((message, index) => {
            if (message.role === "user") {
              return (
                <div className="message-row user-row" key={index}>
                  <div className="user-message">
                    {message.content}
                  </div>
                </div>
              );
            }

            if (message.role === "error") {
              return (
                <div className="error-message" key={index}>
                  {message.content}
                </div>
              );
            }

            return (
              <div
                className="assistant-message"
                data-testid="assistant-message"
                key={index}
              >
                <div className="assistant-label">Lyftr AI</div>

                <div className="reply">
                  <ReactMarkdown>
                    {message.content}
                  </ReactMarkdown>
                </div>

                <div className="metadata">
                  <span
                    className={
                      message.metadata.resolution_source ===
                      "LLM_CACHE"
                        ? "cache-badge"
                        : "live-badge"
                    }
                    data-testid="meta-source"
                  >
                    {message.metadata.resolution_source}
                  </span>

                  <span data-testid="meta-model">
                    {message.metadata.model}
                  </span>

                  <span data-testid="meta-latency">
                    {message.metadata.latency_ms} ms
                  </span>

                  <span>
                    Input:{" "}
                    <strong data-testid="meta-input-tokens">
                      {message.metadata.input_tokens}
                    </strong>
                  </span>

                  <span>
                    Output:{" "}
                    <strong data-testid="meta-output-tokens">
                      {message.metadata.output_tokens}
                    </strong>
                  </span>
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="thinking">
              <span></span>
              <span></span>
              <span></span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="composer">
          <textarea
            data-testid="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message Lyftr AI..."
            rows="1"
          />

          <button
            data-testid="send-button"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            {loading ? "..." : "Send"}
          </button>
        </div>

        <div className="session">
          Session: {sessionId.slice(0, 8)}
        </div>
      </main>
    </div>
  );
}

export default App;