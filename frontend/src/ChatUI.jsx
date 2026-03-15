import React, { useState, useRef, useEffect } from 'react';
import './ChatUI.css';

/** Strip <think>...</think> blocks so internal reasoning is never shown (safety net if backend misses any). */
function cleanResponse(text) {
  if (!text || typeof text !== 'string') return text;
  return text.replace(/<think>[\s\S]*?<\/think>/gi, '').replace(/\s*<\/?think>\s*/gi, '').trim() || text.trim();
}

function ChatUI() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sources, setSources] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [confidence, setConfidence] = useState(null);
  const [confidenceScore, setConfidenceScore] = useState(null);
  const [retrievedContext, setRetrievedContext] = useState([]);
  const [showContext, setShowContext] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (text) => {
    const trimmed = (text || input).trim();
    if (!trimmed || loading) return;

    setError(null);
    setSources([]);
    setFollowUps([]);
    setConfidence(null);
    setConfidenceScore(null);
    setRetrievedContext([]);

    const userMsg = { role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const chatHistory = messages.map((m) => ({ role: m.role, content: m.content }));
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: trimmed,
          history: chatHistory,
        }),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody.detail || `Request failed: ${response.status}`);
      }

      const data = await response.json();
      const answer = cleanResponse(data.answer ?? '');
      setMessages((prev) => [...prev, { role: 'assistant', content: answer }]);
      setSources(data.sources || []);
      setFollowUps(data.follow_up_suggestions || []);
      setConfidence(data.confidence || null);
      setConfidenceScore(data.confidence_score != null ? data.confidence_score : null);
      setRetrievedContext(data.retrieved_context || []);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
      setMessages((prev) => [...prev, { role: 'assistant', content: null, isError: true }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleFollowUp = (suggestion) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  return (
    <div className="chat-ui">
      <div className="chat-window">
        {messages.length === 0 && (
          <div className="chat-welcome">
            <p>Ask anything about GitLab's handbook or direction.</p>
            <ul className="example-queries">
              <li><button type="button" onClick={() => handleFollowUp("What is GitLab's product strategy?")}>What is GitLab's product strategy?</button></li>
              <li><button type="button" onClick={() => handleFollowUp("How does GitLab handle remote work?")}>How does GitLab handle remote work?</button></li>
              <li><button type="button" onClick={() => handleFollowUp("What is GitLab's engineering culture?")}>What is GitLab's engineering culture?</button></li>
            </ul>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message message-${msg.role}`}>
            <div className="message-avatar" aria-hidden>
              {msg.role === 'user' ? 'You' : '◇'}
            </div>
            <div className="message-body">
              {msg.isError ? (
                <p className="message-error">{error}</p>
              ) : (
                <div className="message-content">{msg.content}</div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message message-assistant">
            <div className="message-avatar" aria-hidden>◇</div>
            <div className="message-body">
              <div className="loading-dots" aria-label="Loading">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {(sources.length > 0 || followUps.length > 0 || confidence || retrievedContext.length > 0) && (
        <div className="chat-meta">
          {(confidence || confidenceScore != null) && (
            <p className="confidence">
              Confidence:{' '}
              {confidenceScore != null ? (
                <span className={`confidence-value confidence-${confidence}`}>{confidenceScore}%</span>
              ) : (
                <span className={`confidence-${confidence}`}>{confidence}</span>
              )}
            </p>
          )}
          {sources.length > 0 && (
            <div className="sources-panel">
              <strong>Sources</strong>
              <ul className="sources-list">
                {sources.map((s, j) => (
                  <li key={j} className="source-item">
                    <span className="source-title">{s.title || 'GitLab Handbook'}</span>
                    <a href={s.url} target="_blank" rel="noopener noreferrer" className="source-url-link">{s.url}</a>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {retrievedContext.length > 0 && (
            <div className="retrieved-context-panel">
              <button
                type="button"
                className="context-toggle"
                onClick={() => setShowContext(!showContext)}
                aria-expanded={showContext}
              >
                {showContext ? '▼' : '▶'} Retrieved context ({retrievedContext.length} doc{retrievedContext.length !== 1 ? 's' : ''} used)
              </button>
              {showContext && (
                <div className="context-snippets">
                  {retrievedContext.map((ctx, j) => (
                    <div key={j} className="context-snippet">
                      <strong>{ctx.title}</strong>
                      <a href={ctx.url} target="_blank" rel="noopener noreferrer" className="context-link">{ctx.url}</a>
                      <p className="context-preview">{ctx.snippet}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {followUps.length > 0 && (
            <div className="follow-ups">
              <strong>You may also ask</strong>
              <div className="follow-up-buttons">
                {followUps.map((s, j) => (
                  <button key={j} type="button" className="follow-up-btn" onClick={() => handleFollowUp(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <form className="chat-input-wrap" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          placeholder="Ask about GitLab handbook or direction..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          aria-label="Message"
        />
        <button type="submit" className="chat-send" disabled={loading || !input.trim()} aria-label="Send">
          Send
        </button>
      </form>
    </div>
  );
}

export default ChatUI;
