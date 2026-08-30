import { useState, useRef, useEffect } from 'react';
import Message from './Message';
import LoadingIndicator from './LoadingIndicator';
import SuggestedQuestions from './SuggestedQuestions';
import { sendMessage } from '../services/api';

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `# Welcome to Skylark BI Agent 👋\n\nI am your AI-powered Business Intelligence Assistant for **monday.com**. I analyze live data from your **Deals Board** and **Work Order Tracker Board** using deterministic calculations to deliver reliable executive insights.\n\nAsk me anything about sales pipelines, revenue projections, operational bottlenecks, risks, or ask for a leadership update!`,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const query = textToSend || input;
    if (!query.trim() || loading) return;

    setInput('');
    const userMsg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await sendMessage(query);
      const assistantMsg = {
        role: 'assistant',
        content: res.answer,
        metrics: res.metrics,
        dataQualityNotes: res.data_quality_notes,
        assumptions: res.assumptions,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `❌ **Error:** ${err.message || 'Failed to connect to the backend server.'}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-surface-950/80 backdrop-blur-xl rounded-2xl border border-surface-800 shadow-2xl overflow-hidden">
      {/* Scrollable Message History Container */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
        {messages.map((msg, index) => (
          <Message key={index} message={msg} />
        ))}
        {loading && <LoadingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions Pill bar */}
      {messages.length <= 2 && !loading && (
        <div className="py-4 border-t border-surface-800/60 bg-surface-900/40 px-4 md:px-8">
          <p className="text-xs text-surface-400 font-bold mb-3 uppercase tracking-wider">
            Quick Executive Queries
          </p>
          <SuggestedQuestions onSelect={(q) => handleSend(q)} disabled={loading} />
        </div>
      )}

      {/* Input Box Footer */}
      <div className="p-4 md:p-6 border-t border-surface-800 bg-surface-900/95 flex-shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-3 max-w-7xl mx-auto"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about sales pipeline, work order delays, operational risks, leadership summary..."
            disabled={loading}
            className="flex-1 bg-surface-800/90 text-surface-100 placeholder-surface-400 rounded-xl px-5 py-4
                       border border-surface-700/70 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30
                       transition-all text-sm disabled:opacity-50 shadow-inner"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-gradient-to-r from-primary-600 via-primary-500 to-accent text-white px-7 py-4 rounded-xl font-bold text-sm
                       hover:from-primary-500 hover:to-accent focus:outline-none focus:ring-2 focus:ring-primary-500/40
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2 cursor-pointer shadow-lg shadow-primary-600/30 flex-shrink-0"
          >
            <span>Send</span>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
