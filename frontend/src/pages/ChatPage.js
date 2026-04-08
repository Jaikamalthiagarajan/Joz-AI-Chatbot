import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export default function ChatPage({ user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(
        `${API_URL}/chat/query`,
        { question: input },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer || response.data.response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h2 className="section-title">Policy Q&A Chat</h2>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-message assistant">
              <div className="chat-bubble">
                Hello! I'm your AI HR Assistant. Ask me anything about leave policies, HR procedures, or company information.
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.role}`}>
              <div className="chat-bubble">{msg.content}</div>
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant">
              <div className="chat-bubble">Thinking...</div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form className="chat-input-area" onSubmit={handleSendMessage}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            disabled={loading}
          />
          <button type="submit" disabled={loading} className="secondary">
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
