import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { askAssistant, getCustomerAnalysis } from "../services/api";
import { pct, riskBadge } from "../components/ui";

const PORTFOLIO_SUGGESTIONS = [
  "Summarize the portfolio.",
  "How many customers are high risk?",
  "What is the average predicted churn probability?",
  "What are the most important model drivers?",
  "Show me the highest-risk customers.",
];

const CUSTOMER_SUGGESTIONS = [
  "Why is this customer at high risk?",
  "What are the main factors influencing the prediction?",
  "What should we do to retain this customer?",
  "What happens if we change the contract?",
  "Give me a retention plan.",
];

function Message({ role, text }) {
  return (
    <div className={`chat-msg ${role === "user" ? "user" : ""}`}>
      <div className={`chat-avatar ${role === "user" ? "user" : "ai"}`}>
        {role === "user" ? "You" : "AI"}
      </div>
      <div className="chat-bubble" style={{ whiteSpace: "pre-wrap" }}>{text}</div>
    </div>
  );
}

function loadNewFeatures() {
  try {
    const raw = sessionStorage.getItem("retensa_new_customer_features");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function loadNewAnalysis() {
  try {
    const raw = sessionStorage.getItem("retensa_new_customer_analysis");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function Assistant() {
  const [params, setParams] = useSearchParams();
  const customerParam = params.get("customer") || "";
  const modeNew = params.get("mode") === "new";
  const [customerIndex, setCustomerIndex] = useState(customerParam);
  const [newFeatures, setNewFeatures] = useState(modeNew ? loadNewFeatures() : null);
  const [context, setContext] = useState(null);
  const [contextError, setContextError] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Ask about the portfolio, an existing dataset customer, or a newly analyzed customer.",
    },
  ]);
  const scrollRef = useRef(null);
  const isNewMode = Boolean(newFeatures);

  useEffect(() => {
    setCustomerIndex(customerParam);
    if (modeNew) {
      setNewFeatures(loadNewFeatures());
      const saved = loadNewAnalysis();
      if (saved) setContext(saved);
    }
  }, [customerParam, modeNew]);

  useEffect(() => {
    if (isNewMode) {
      const saved = loadNewAnalysis();
      if (saved) setContext(saved);
      setContextError(newFeatures ? "" : "Analyze a new customer first.");
      return;
    }
    if (!customerIndex || !/^\d+$/.test(String(customerIndex))) {
      setContext(null);
      setContextError("");
      return;
    }
    let cancelled = false;
    setContextError("");
    getCustomerAnalysis(customerIndex)
      .then((payload) => {
        if (!cancelled) setContext(payload);
      })
      .catch((err) => {
        if (!cancelled) {
          setContext(null);
          setContextError(err.message);
        }
      });
    return () => { cancelled = true; };
  }, [customerIndex, isNewMode, newFeatures]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, loading]);

  async function send(text) {
    const message = (text ?? input).trim();
    if (!message || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setLoading(true);
    try {
      const idx = !isNewMode && customerIndex && /^\d+$/.test(String(customerIndex))
        ? Number(customerIndex)
        : null;
      const reply = await askAssistant(message, idx, isNewMode ? newFeatures : null);
      setMessages((prev) => [...prev, { role: "assistant", text: reply.answer, meta: reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: err.message || "Unable to reach the RETENSA assistant." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const suggestions = context || isNewMode ? CUSTOMER_SUGGESTIONS : PORTFOLIO_SUGGESTIONS;

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>RETENSA AI Assistant</h1>
          <p>Portfolio, existing customers, and new-customer analysis — always grounded in live evidence.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="flex gap-8" style={{ flexWrap: "wrap", alignItems: "center" }}>
          <label className="card-sub" style={{ margin: 0 }}>Context</label>
          <input
            className="filter-input"
            style={{ maxWidth: 160 }}
            value={isNewMode ? "" : customerIndex}
            placeholder="Dataset index"
            disabled={isNewMode}
            onChange={(e) => setCustomerIndex(e.target.value)}
            onBlur={() => {
              if (isNewMode) return;
              const value = customerIndex.trim();
              if (value && /^\d+$/.test(value)) setParams({ customer: value });
              else setParams({});
            }}
          />
          <button
            className="btn btn-sm"
            type="button"
            disabled={isNewMode}
            onClick={() => {
              const value = customerIndex.trim();
              if (value && /^\d+$/.test(value)) setParams({ customer: value });
              else setParams({});
            }}
          >
            Apply dataset ID
          </button>
          <button
            className={`btn btn-sm ${isNewMode ? "btn-primary" : ""}`}
            type="button"
            onClick={() => {
              const feats = loadNewFeatures();
              if (!feats) {
                setContextError("Analyze a new customer first on Analyze New Customer.");
                return;
              }
              setNewFeatures(feats);
              setParams({ mode: "new" });
            }}
          >
            New customer mode
          </button>
          <button
            className="btn btn-sm"
            type="button"
            onClick={() => {
              setNewFeatures(null);
              setCustomerIndex("");
              setContext(null);
              setParams({});
            }}
          >
            Portfolio mode
          </button>
          {isNewMode && context && (
            <span className="flex gap-8" style={{ alignItems: "center" }}>
              New Customer · {riskBadge(context.risk.level)} · {pct(context.risk.probability)}
              <Link className="btn btn-sm" to="/new-customer">Open analysis</Link>
            </span>
          )}
          {!isNewMode && context && customerIndex && (
            <span className="flex gap-8" style={{ alignItems: "center" }}>
              Customer #{customerIndex} · {riskBadge(context.risk.level)} · {pct(context.risk.probability)}
              <Link className="btn btn-sm" to={`/customers/${customerIndex}`}>Open Action Center</Link>
            </span>
          )}
        </div>
        {contextError && <div className="page-status error" style={{ marginTop: 10 }}>{contextError}</div>}
      </div>

      <div className="card chat-shell">
        <div className="chat-scroll" ref={scrollRef}>
          {messages.map((msg, idx) => (
            <Message key={`${msg.role}-${idx}`} role={msg.role} text={msg.text} />
          ))}
          {loading && (
            <div className="chat-msg">
              <div className="chat-avatar ai">AI</div>
              <div className="chat-bubble">Thinking with RETENSA evidence…</div>
            </div>
          )}
        </div>
        <div className="suggestion-row" style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
          {suggestions.map((q) => (
            <button key={q} className="toggle-pill" type="button" onClick={() => send(q)} disabled={loading}>
              {q}
            </button>
          ))}
        </div>
        <form
          className="chat-input-row"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              isNewMode
                ? "Ask about the new customer…"
                : context
                  ? `Ask about customer #${customerIndex}…`
                  : "Ask RETENSA AI about the portfolio…"
            }
            aria-label="Assistant message"
          />
          <button className="btn btn-primary" type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </main>
  );
}
