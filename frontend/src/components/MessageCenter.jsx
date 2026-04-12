import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Send, MessageSquare, User, Clock, Search, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MessageCenter = ({ currentUser }) => {
  const [conversations, setConversations] = useState([]);
  const [activeCase, setActiveCase] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef(null);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  useEffect(() => { loadConversations(); }, []);

  useEffect(() => {
    if (activeCase) loadMessages(activeCase.case_id);
  }, [activeCase]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversations = async () => {
    try {
      const res = await axios.get(`${API}/cm-tools/client-messages`, getAuthHeader());
      setConversations(res.data || []);
      if (res.data?.length > 0 && !activeCase) setActiveCase(res.data[0]);
    } catch (e) {
      console.error('Failed to load conversations');
    }
    setLoading(false);
  };

  const loadMessages = async (caseId) => {
    try {
      const res = await axios.get(`${API}/cm-tools/communications/${caseId}`, getAuthHeader());
      setMessages(res.data.messages || []);
      // Mark as read
      await axios.put(`${API}/cm-tools/communications/${caseId}/mark-read`, {}, getAuthHeader());
    } catch (e) {
      console.error('Failed to load messages');
    }
  };

  const handleSend = async () => {
    if (!newMessage.trim() || !activeCase) return;
    setSending(true);
    try {
      await axios.post(`${API}/cm-tools/client-messages/send`, {
        case_id: activeCase.case_id,
        message: newMessage.trim(),
      }, getAuthHeader());
      setNewMessage('');
      loadMessages(activeCase.case_id);
      loadConversations();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to send message');
    }
    setSending(false);
  };

  const filteredConvos = conversations.filter(c =>
    !searchQuery || c.case_display_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.case_manager_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  return (
    <div data-testid="message-center">
      <div className="flex h-[600px] bg-white dark:bg-slate-900 rounded-xl border overflow-hidden">
        {/* Left sidebar - conversation list */}
        <div className="w-[300px] border-r flex flex-col">
          <div className="p-3 border-b">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-1.5">
                <MessageSquare className="h-4 w-4" />Messages
              </h3>
            </div>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <Input placeholder="Search conversations..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-8 h-8 text-sm" data-testid="msg-search" />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {filteredConvos.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-400">No conversations yet</div>
            ) : (
              filteredConvos.map((conv, idx) => (
                <div key={conv.case_id}
                  className={`p-3 cursor-pointer border-b hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${activeCase?.case_id === conv.case_id ? 'bg-[#2a777a]/10 border-l-4 border-l-[#2a777a]' : ''}`}
                  onClick={() => setActiveCase(conv)}
                  data-testid={`conv-${idx}`}
                >
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-full bg-[#2a777a]/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[#2a777a] font-bold text-xs">{conv.case_manager_name?.charAt(0) || 'C'}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-sm text-slate-800 dark:text-white truncate">{conv.case_display_id}</p>
                        {conv.last_message_at && (
                          <span className="text-[10px] text-slate-400">{new Date(conv.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 truncate">{conv.last_message || 'No messages yet'}</p>
                    </div>
                    {conv.unread_count > 0 && <Badge className="bg-[#2a777a] text-white text-[10px] h-5 w-5 flex items-center justify-center rounded-full p-0">{conv.unread_count}</Badge>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right side - messages */}
        <div className="flex-1 flex flex-col">
          {!activeCase ? (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 text-slate-300" />
                <p>Select a conversation</p>
              </div>
            </div>
          ) : (
            <>
              {/* Chat header */}
              <div className="p-3 border-b bg-slate-50 dark:bg-slate-800">
                <h4 className="font-semibold text-slate-800 dark:text-white">{activeCase.case_display_id}</h4>
                <p className="text-xs text-slate-500">CM: {activeCase.case_manager_name} | {activeCase.product_name}</p>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="messages-area">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    <div className="text-center">
                      <MessageSquare className="h-10 w-10 mx-auto mb-2 text-slate-300" />
                      <p className="text-sm">No messages yet. Start the conversation!</p>
                    </div>
                  </div>
                ) : (
                  messages.map((m, idx) => {
                    const isMe = m.sender_id === currentUser?.id;
                    return (
                      <div key={m.id || idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${
                          isMe ? 'bg-[#2a777a] text-white rounded-br-md' : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white rounded-bl-md'
                        }`} data-testid={`msg-${idx}`}>
                          {!isMe && <p className="text-xs font-medium opacity-70 mb-0.5">{m.sender_name}</p>}
                          <p className="text-sm whitespace-pre-wrap">{m.message}</p>
                          <p className="text-[10px] opacity-50 mt-1 text-right">{m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</p>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-3 border-t bg-white dark:bg-slate-900">
                <div className="flex gap-2">
                  <Textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 resize-none"
                    rows={1}
                    data-testid="msg-input"
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  />
                  <Button onClick={handleSend} disabled={sending || !newMessage.trim()} className="bg-[#2a777a] hover:bg-[#236466] text-white self-end" data-testid="send-msg-btn">
                    {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageCenter;
