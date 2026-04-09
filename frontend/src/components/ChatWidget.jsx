import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Send, ArrowLeft, User, Clock, Check, CheckCheck, Loader2 } from 'lucide-react';

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

const ChatWidget = ({ caseId, caseDisplayId, currentUser }) => {
  const [conversations, setConversations] = useState([]);
  const [activeConvo, setActiveConvo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const pollRef = useRef(null);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const fetchConversations = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/chat/conversations`, getAuthHeader());
      setConversations(res.data);
      const totalUnread = res.data.reduce((sum, c) => sum + (c.unread_count || 0), 0);
      setUnreadCount(totalUnread);
    } catch (err) { /* silent */ }
  }, []);

  const fetchMessages = useCallback(async (convoId) => {
    try {
      const res = await axios.get(`${API}/chat/messages/${convoId}?limit=50`, getAuthHeader());
      setMessages(res.data);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch (err) { /* silent */ }
  }, []);

  useEffect(() => {
    fetchConversations();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (isOpen && activeConvo) {
      fetchMessages(activeConvo.id);
      pollRef.current = setInterval(() => fetchMessages(activeConvo.id), 5000);
    } else if (isOpen) {
      pollRef.current = setInterval(fetchConversations, 8000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [isOpen, activeConvo]);

  const startConversation = async () => {
    if (!caseId) return;
    try {
      const res = await axios.post(`${API}/chat/conversations`, { case_id: caseId }, getAuthHeader());
      setActiveConvo(res.data);
      fetchMessages(res.data.id);
    } catch (err) {
      toast.error('Failed to start conversation');
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !activeConvo || sending) return;
    setSending(true);
    try {
      await axios.post(`${API}/chat/messages`, {
        conversation_id: activeConvo.id,
        message: newMessage.trim()
      }, getAuthHeader());
      setNewMessage('');
      fetchMessages(activeConvo.id);
    } catch (err) {
      toast.error('Failed to send message');
    }
    setSending(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  // Floating button
  if (!isOpen) {
    return (
      <button
        onClick={() => { setIsOpen(true); fetchConversations(); setLoading(false); }}
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
    <div className="fixed bottom-6 right-6 z-50 w-[380px] h-[520px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden" data-testid="chat-widget">
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
            {activeConvo ? activeConvo.subject || 'Chat' : 'Messages'}
          </p>
          {activeConvo && <p className="text-xs opacity-80 truncate">{activeConvo.case_manager_name || activeConvo.client_name}</p>}
        </div>
        <button onClick={() => setIsOpen(false)} className="text-white/80 hover:text-white text-lg font-bold" data-testid="chat-close-btn">&times;</button>
      </div>

      {/* Conversation List */}
      {!activeConvo && (
        <div className="flex-1 overflow-y-auto">
          {conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full p-6 text-center">
              <MessageSquare className="h-12 w-12 text-gray-300 mb-3" />
              <p className="text-sm text-gray-500">No conversations yet</p>
              {caseId && (
                <Button onClick={startConversation} size="sm" className="mt-3 bg-[#2a777a] hover:bg-[#236466]" data-testid="start-chat-btn">
                  Start Conversation
                </Button>
              )}
            </div>
          ) : (
            <div>
              {caseId && !conversations.find(c => c.case_id === caseId) && (
                <div className="p-3 border-b">
                  <Button onClick={startConversation} size="sm" className="w-full bg-[#2a777a] hover:bg-[#236466]" data-testid="start-chat-btn">
                    <MessageSquare className="h-4 w-4 mr-2" /> New Chat for This Case
                  </Button>
                </div>
              )}
              {conversations.map((convo) => (
                <div key={convo.id}
                     className="flex items-center gap-3 p-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors"
                     onClick={() => { setActiveConvo(convo); fetchMessages(convo.id); }}
                     data-testid={`conversation-${convo.id}`}
                >
                  <div className="h-10 w-10 rounded-full bg-[#2a777a]/10 flex items-center justify-center flex-shrink-0">
                    <User className="h-5 w-5 text-[#2a777a]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-gray-900 truncate">{convo.client_name || convo.case_manager_name}</p>
                      <span className="text-[10px] text-gray-400">{formatTime(convo.updated_at)}</span>
                    </div>
                    <p className="text-xs text-gray-500 truncate">{convo.last_message || 'No messages yet'}</p>
                    <p className="text-[10px] text-gray-400">{convo.case_display_id} - {convo.product_name}</p>
                  </div>
                  {convo.unread_count > 0 && (
                    <Badge className="bg-[#f7620b] text-white text-[10px] px-1.5">{convo.unread_count}</Badge>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      {activeConvo && (
        <>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-gray-50">
            {messages.length === 0 && (
              <div className="text-center text-xs text-gray-400 mt-8">No messages yet. Say hello!</div>
            )}
            {messages.map((msg) => {
              const isMe = msg.sender_id === currentUser?.id;
              return (
                <div key={msg.id} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] rounded-2xl px-3.5 py-2 ${isMe ? 'bg-[#2a777a] text-white rounded-br-md' : 'bg-white text-gray-800 border border-gray-200 rounded-bl-md'}`}>
                    {!isMe && <p className="text-[10px] font-semibold mb-0.5 text-[#2a777a]">{msg.sender_name}</p>}
                    <p className="text-sm whitespace-pre-wrap break-words">{msg.message}</p>
                    <div className={`flex items-center justify-end gap-1 mt-0.5 ${isMe ? 'text-white/60' : 'text-gray-400'}`}>
                      <span className="text-[10px]">{formatTime(msg.created_at)}</span>
                      {isMe && (msg.read ? <CheckCheck className="h-3 w-3" /> : <Check className="h-3 w-3" />)}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-gray-200 bg-white">
            <div className="flex items-center gap-2">
              <Input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Type a message..."
                className="flex-1 text-sm rounded-full"
                data-testid="chat-input"
              />
              <Button
                onClick={sendMessage}
                disabled={!newMessage.trim() || sending}
                className="h-9 w-9 p-0 rounded-full bg-[#2a777a] hover:bg-[#236466]"
                data-testid="chat-send-btn"
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatWidget;
