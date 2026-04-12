import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Send, ArrowLeft, X, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatTime = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
};

const ChatWidget = ({ currentUser }) => {
  const [conversations, setConversations] = useState([]);
  const [activeConvo, setActiveConvo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const pollRef = useRef(null);

  const role = currentUser?.role;
  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const fetchConversations = useCallback(async () => {
    try {
      if (role === 'client') {
        const res = await axios.get(`${API}/cm-tools/client-messages`, getAuth());
        const convos = (res.data || []).map(c => ({
          id: c.case_id,
          name: c.case_manager_name || 'Case Manager',
          subtitle: `${c.case_display_id} — ${c.product_name}`,
          last_message: c.last_message,
          last_message_at: c.last_message_at,
          unread_count: c.unread_count,
          client_id: null,
        }));
        setConversations(convos);
        setUnreadCount(convos.reduce((s, c) => s + (c.unread_count || 0), 0));
      } else if (role === 'case_manager' || role === 'admin') {
        // Fast load: just get cases with names, no message enrichment
        const casesRes = await axios.get(`${API}/cm-tools/my-cases-summary`, getAuth());
        const cases = casesRes.data || [];
        const convos = cases.map(c => ({
          id: c.id,
          name: c.client_name || 'Client',
          subtitle: `${c.case_id} — ${c.product_name}`,
          last_message: '',
          last_message_at: '',
          unread_count: 0,
          client_id: c.client_id,
        }));
        setConversations(convos);
        // Enrich in background (unread counts, last messages)
        const unreadRes = await axios.get(`${API}/cm-tools/communications/unread-count`, getAuth()).catch(() => ({ data: { count: 0 } }));
        setUnreadCount(unreadRes.data?.count || 0);
      }
    } catch { /* silent */ }
  }, [role]);

  const fetchMessages = useCallback(async (caseId) => {
    try {
      const res = await axios.get(`${API}/cm-tools/communications/${caseId}`, getAuth());
      setMessages(res.data.messages || []);
      // Mark read
      await axios.put(`${API}/cm-tools/communications/${caseId}/mark-read`, {}, getAuth()).catch(() => {});
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch { setMessages([]); }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Polling for new messages
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (isOpen && activeConvo) {
      fetchMessages(activeConvo.id);
      pollRef.current = setInterval(() => fetchMessages(activeConvo.id), 5000);
    } else if (isOpen) {
      pollRef.current = setInterval(fetchConversations, 8000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [isOpen, activeConvo, fetchMessages, fetchConversations]);

  const sendMsg = async () => {
    if (!newMessage.trim() || !activeConvo || sending) return;
    setSending(true);
    try {
      if (role === 'client') {
        await axios.post(`${API}/cm-tools/client-messages/send`, {
          case_id: activeConvo.id,
          message: newMessage.trim(),
        }, getAuth());
      } else {
        await axios.post(`${API}/cm-tools/communications/send`, {
          case_id: activeConvo.id,
          client_id: activeConvo.client_id || '',
          message: newMessage.trim(),
          message_type: 'text',
        }, getAuth());
      }
      setNewMessage('');
      fetchMessages(activeConvo.id);
    } catch (e) {
      toast.error('Failed to send');
    }
    setSending(false);
  };

  // Floating button
  if (!isOpen) {
    return (
      <button
        onClick={() => { setIsOpen(true); setLoading(true); fetchConversations().then(() => setLoading(false)); }}
        className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full bg-[#2a777a] hover:bg-[#236466] text-white shadow-lg flex items-center justify-center transition-transform hover:scale-105"
        data-testid="chat-toggle-btn"
      >
        <MessageSquare className="h-6 w-6" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 h-5 w-5 bg-[#f7620b] text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[380px] h-[520px] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden" data-testid="chat-widget">
      {/* Header */}
      <div className="bg-[#2a777a] text-white px-4 py-3 flex items-center gap-3">
        {activeConvo && (
          <button onClick={() => { setActiveConvo(null); fetchConversations(); }} className="hover:opacity-80">
            <ArrowLeft className="h-5 w-5" />
          </button>
        )}
        <MessageSquare className="h-5 w-5" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm truncate">
            {activeConvo ? activeConvo.name : (role === 'client' ? 'Messages' : 'Client Messages')}
          </p>
          {activeConvo && <p className="text-[11px] opacity-80 truncate">{activeConvo.subtitle}</p>}
        </div>
        <button onClick={() => { setIsOpen(false); setActiveConvo(null); }} className="hover:opacity-80" data-testid="chat-close-btn">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full"><Loader2 className="h-6 w-6 animate-spin text-[#2a777a]" /></div>
        ) : !activeConvo ? (
          /* Conversation list */
          <div>
            {conversations.length === 0 ? (
              <div className="p-6 text-center text-sm text-slate-400">No conversations yet</div>
            ) : (
              conversations.map((conv, idx) => (
                <div key={conv.id}
                  className="p-3 border-b hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors"
                  onClick={() => { setActiveConvo(conv); fetchMessages(conv.id); }}
                  data-testid={`chat-conv-${idx}`}
                >
                  <div className="flex items-center gap-2.5">
                    <div className="h-9 w-9 rounded-full bg-[#2a777a]/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[#2a777a] font-bold text-xs">{(conv.name || '?').charAt(0)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-sm text-slate-800 dark:text-white truncate">{conv.name}</p>
                        {conv.last_message_at && <span className="text-[10px] text-slate-400 flex-shrink-0">{formatTime(conv.last_message_at)}</span>}
                      </div>
                      <p className="text-[11px] text-slate-500 truncate">{conv.subtitle}</p>
                      <p className="text-xs text-slate-400 truncate">{conv.last_message || 'No messages'}</p>
                    </div>
                    {conv.unread_count > 0 && (
                      <Badge className="bg-[#2a777a] text-white text-[10px] h-5 w-5 flex items-center justify-center rounded-full p-0 flex-shrink-0">{conv.unread_count}</Badge>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Messages */
          <div className="p-3 space-y-2">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-[300px] text-slate-400 text-sm">
                <div className="text-center">
                  <MessageSquare className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                  <p>Start the conversation</p>
                </div>
              </div>
            ) : (
              messages.map((m, idx) => {
                const isMe = (role === 'client' && m.sender_role === 'client') ||
                             (role !== 'client' && (m.sender_role === 'case_manager' || m.sender_role === 'admin'));
                return (
                  <div key={m.id || idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-2xl px-3 py-2 ${
                      isMe ? 'bg-[#2a777a] text-white rounded-br-sm' : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white rounded-bl-sm'
                    }`} data-testid={`chat-msg-${idx}`}>
                      {!isMe && <p className="text-[10px] font-medium opacity-70 mb-0.5">{m.sender_name}</p>}
                      <p className="text-[13px] whitespace-pre-wrap">{m.message}</p>
                      <p className="text-[9px] opacity-50 mt-0.5 text-right">{formatTime(m.created_at)}</p>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input - only when in a conversation */}
      {activeConvo && (
        <div className="p-2 border-t bg-white dark:bg-slate-900">
          <div className="flex gap-2">
            <Input
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 text-sm h-9"
              data-testid="chat-input"
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); } }}
            />
            <Button onClick={sendMsg} disabled={sending || !newMessage.trim()} className="bg-[#2a777a] hover:bg-[#236466] text-white h-9 w-9 p-0" data-testid="chat-send-btn">
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatWidget;
