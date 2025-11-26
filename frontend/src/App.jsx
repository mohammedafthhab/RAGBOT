import FloatingWords from "./components/FloatingWords";
import seedDance from "./seeddance.gif";

import LetterGlitch from "./components/LetterGlitch";
import React, { useState, useEffect, useRef } from "react";
import LightRays from "./LightRays";
import "./App.css";
import "./LightRays.css";

// Loading UI
import Handscan from "./components/Handscan";
import SearchingAnimation from "./components/SearchingAnimation";
import TypingIndicator from "./components/TypingIndicator";

const API_BASE = "http://127.0.0.1:5000";

async function postJSON(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [fullHistory, setFullHistory] = useState([]);


  // Gesture mode state
  const [gestureMode, setGestureMode] = useState(false);
  const sseRef = useRef(null);

  const chatEndRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // -----------------------------------------
  // Load localStorage history on first load
  // -----------------------------------------
  useEffect(() => {
    const saved = localStorage.getItem("seed_chat_history");
    if (saved) {
      setMessages(JSON.parse(saved));
    }
  }, []);

  // -----------------------------------------
  // Auto-save messages to localStorage
  // -----------------------------------------
  useEffect(() => {
    localStorage.setItem("seed_chat_history", JSON.stringify(messages));
  }, [messages]);

  // -----------------------------------------
  // Sync with backend MongoDB history
  // -----------------------------------------
  async function syncHistory() {
    try {
      const res = await fetch(`${API_BASE}/history`);
      const server = await res.json();

      const formatted = server.map((h) => ({
        role: h.role,
        text: h.message,
        time: h.time,
      }));

      if (formatted.length > messages.length) {
        setMessages(formatted);
        localStorage.setItem("seed_chat_history", JSON.stringify(formatted));
      }
    } catch (err) {
      console.error("History sync failed:", err);
    }
  }

  useEffect(() => {
    syncHistory();
  }, []);

  async function loadFullHistory() {
  try {
    const res = await fetch(`${API_BASE}/full-history`);
    const data = await res.json();
    setFullHistory(data);
    setShowHistory(true);
  } catch (err) {
    console.error("Failed to load history:", err);
  }
}


  // -----------------------------------------
  // Send message
  // -----------------------------------------
  async function doSend(text) {
    if (!text.trim()) return;

    setMessages((prev) => [...prev, { role: "user", text }]);

    setInput("");
    setLoading(true);

    try {
      const data = await postJSON(`${API_BASE}/chat`, { query: text });

      setMessages((prev) => [
        ...prev,
        { role: "bot", text: data.answer || "🤖 No response from chatbot." },
      ]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "⚠️ Unable to reach the server. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const sendMessage = async (e) => {
    e.preventDefault();
    await doSend(input);
  };

  // -----------------------------------------
  // Gesture Mode Handlers
  // -----------------------------------------
  async function startGesture() {
    try {
      await postJSON(`${API_BASE}/gesture/start`, {});

      const es = new EventSource(`${API_BASE}/gesture/stream`);
      sseRef.current = es;

      es.onmessage = (ev) => {
        if (!ev.data) return;
        const msg = JSON.parse(ev.data);

        if (msg.type === "sentence") {
          setInput(msg.value || "");
        }

        if (msg.type === "undo") {
          setInput((prev) => {
            const parts = prev.trim().split(" ");
            parts.pop();
            return parts.join(" ");
          });
        }

        if (msg.type === "clear") setInput("");

        if (msg.type === "close") {
          setGestureMode(false);
          if (sseRef.current) sseRef.current.stop();
          stopGesture();
        }

        if (msg.type === "send") {
          const sentence = (msg.value || "").trim();
          if (sentence) {
            doSend(sentence);
            setInput("");
          }
        }
      };

      es.onerror = () => {
        console.error("Gesture SSE error");
        stopGesture();
      };
    } catch (e) {
      console.error(e);
      setGestureMode(false);
    }
  }

  async function stopGesture() {
    try {
      await postJSON(`${API_BASE}/gesture/stop`, {});
    } catch {}

    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  }

  useEffect(() => {
    return () => {
      if (sseRef.current) sseRef.current.close();
    };
  }, []);

  // -----------------------------------------
  // FRONT PAGE
  // -----------------------------------------
  if (!started) {
    return (
      <div className="front-page">
        <div className="glitch-wrapper">
          <FloatingWords
            words={[
              "Done is better than perfect.",
              "startup",
              "Stay consistent",
              "growth",
              "success",
              "revenue",
              "money",
              "funding",
              "motivation",
              "innovate",
              "vision",
              "product",
              "market",
              "leadership",
              "scaling",
              "strategy",
              "creativity",
              "impact",
              "If you dont start, someone else will",
              "brand",
              "team",
              "idea",
              "Your idea deserves a chance",
              "hustle",
              "win",
              "value",
              "profit",
              "mindset",
              "opportunity",
              "focus",
            ]}
            count={22}
            speed={0.5}
          />
        </div>

        <div className="hero-container">
          <div className="seed-logo-wrapper">
            <img src="/logo.png" className="seed-logo-static" alt="Seed Static" />
            <img src="/seed.gif" className="seed-logo-wiggle" alt="Seed Wiggle" />
          </div>
          
          <h1 className="hero-text">
            With seed you begin to grow.<br />
            Your next step starts right here.
          </h1>

          <div className="hero-buttons">
            <button className="btn-primary" onClick={() => setStarted(true)}>
              Ask me
            </button>
          </div>
        </div>
      </div>
    );
  }

  // -----------------------------------------
  // MAIN CHAT UI
  // -----------------------------------------
  return (
    <div className="app-wrapper">
      {showHistory && (
      <div className="history-panel">
        <div className="history-header">
          <h3>Chat history ..</h3>
          <button className="close-history" onClick={() => setShowHistory(false)}>x</button>
        </div>

        <div className="history-content">
          {fullHistory.length === 0 ? (
            <p>No history found.</p>
          ) : (
            fullHistory.map((msg, i) => (
              <div key={i} className={`history-item ${msg.role}`}>
                <strong>{msg.role === "user" ? "You:" : "Bot:"}</strong>
                <p>{msg.message}</p>
              </div>
            ))
          )}
        </div>
      </div>
    )}
      <img
        src="/logo.png"
        alt="SEED Logo"
        className="chat-corner-logo"
        onClick={() => setStarted(false)}
        style={{ cursor: "pointer", zIndex: 9999 }}
      />
       <button
          className="history-btn"
          onClick={loadFullHistory}
        >
        History
        </button>
      <div className="light-layer">
        <LightRays
          raysOrigin="top-center"
          raysColor="#00ffff"
          raysSpeed={1.2}
          lightSpread={0.8}
          rayLength={1.3}
          followMouse
          mouseInfluence={0.2}
          noiseAmount={0.1}
          distortion={0.05}
        />
      </div>

      <div className="chat-wrapper">
       <div className="chat-header">
         <h1 className="chat-title">Study</h1>
      </div>


        <div className="chat-box">
          {messages.map((msg, i) => (
  <div
    key={i}
    className={`chat-message ${msg.role === "user" ? "user" : "bot"}`}
  >
    {msg.text.split("\n").map((line, index) => (
      <p key={index}>{line}</p>
    ))}
  </div>
))}

          <div ref={chatEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={sendMessage}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="chat-input"
            disabled={loading}
          />

          <button
            type="button"
            className={`chat-gesture-btn ${gestureMode ? "on" : ""}`}
            onClick={async () => {
              if (!gestureMode) {
                setGestureMode(true);
                await startGesture();
              } else {
                setGestureMode(false);
                await stopGesture();
              }
            }}
          >
            {gestureMode ? (
              <SearchingAnimation size={19.5} scale={2.7} />
            ) : (
              "Gesture"
            )}
          </button>

          <button type="submit" className="chat-send-btn" disabled={loading} aria-busy={loading}>
            {!loading ? (
              "ask"
            ) : (
              <img
                src={seedDance}
                alt="loading"
                style={{ width: "80px", height: "80px", objectFit: "contain" }}
              />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
