import { useState, useRef, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { MessageSquare, Send, X, Loader2, Bot, User, Minimize2 } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const AIChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: 'Hello! I\'m your LEAMSS AI Assistant. I can help you with:\n\n- Visa & immigration queries\n- Document requirements\n- Case status updates\n- Process explanations\n\nHow can I help you today?'
      }]);
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await axios.post(`${API}/ai-intel/chat`, {
        message: userMsg,
        session_id: sessionId
      }, getAuthHeader());
      setSessionId(res.data.session_id);
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-[#2a777a] hover:bg-[#236466] text-white rounded-full shadow-xl flex items-center justify-center transition-all hover:scale-110"
        data-testid="ai-chat-trigger"
      >
        <MessageSquare className="h-6 w-6" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[380px] h-[520px] flex flex-col shadow-2xl rounded-2xl overflow-hidden border border-slate-200" data-testid="ai-chat-widget">
      {/* Header */}
      <div className="bg-[#2a777a] text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          <div>
            <p className="font-semibold text-sm">LEAMSS AI Assistant</p>
            <p className="text-xs text-white/70">Powered by GPT-5.2</p>
          </div>
        </div>
        <div className="flex gap-1">
          <button onClick={() => setIsOpen(false)} className="p-1 hover:bg-white/20 rounded">
            <Minimize2 className="h-4 w-4" />
          </button>
          <button onClick={() => { setIsOpen(false); setMessages([]); setSessionId(null); }} className="p-1 hover:bg-white/20 rounded">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto bg-slate-50 p-3 space-y-3">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-[#2a777a] flex items-center justify-center shrink-0 mt-1">
                <Bot className="h-4 w-4 text-white" />
              </div>
            )}
            <div className={`max-w-[280px] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'bg-[#2a777a] text-white rounded-br-sm'
                : 'bg-white text-slate-700 border border-slate-200 rounded-bl-sm shadow-sm'
            }`}>
              {msg.content}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-full bg-[#f7620b] flex items-center justify-center shrink-0 mt-1">
                <User className="h-4 w-4 text-white" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-2 justify-start">
            <div className="w-7 h-7 rounded-full bg-[#2a777a] flex items-center justify-center shrink-0">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm">
              <Loader2 className="h-4 w-4 animate-spin text-[#2a777a]" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t px-3 py-2">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask anything..."
            className="flex-1 text-sm"
            disabled={loading}
            data-testid="ai-chat-input"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            size="sm"
            className="bg-[#2a777a] hover:bg-[#236466] text-white px-3"
            data-testid="ai-chat-send"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AIChatWidget;
