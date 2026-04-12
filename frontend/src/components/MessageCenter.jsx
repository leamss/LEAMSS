import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Send, MessageSquare, User, Clock, Paperclip, Smile, Search } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MessageCenter = ({ caseId, currentUser }) => {
  const [conversations, setConversations] = useState([]);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef(null);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (activeConv) loadMessages(activeConv.id);
  }, [activeConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversations = async () => {
    try {
      const res = await axios.get(`${API}/chat/conversations`, getAuthHeader());
      setConversations(res.data || []);
      if (res.data?.length > 0 && !activeConv) setActiveConv(res.data[0]);
    } catch (e) {
      console.error('Failed to load conversations');
    }
  };

  const loadMessages = async (convId) => {
    try {
      const res = await axios.get(`${API}/chat/conversations/${convId}/messages`, getAuthHeader());
      setMessages(res.data || []);
    } catch (e) {
      console.error('Failed to load messages');
    }
  };

  const handleSend = async () => {
    if (!newMessage.trim() || !activeConv) return;
    setSending(true);
    try {
      await axios.post(`${API}/chat/conversations/${activeConv.id}/messages`, {
        content: newMessage.trim()
      }, getAuthHeader());
      setNewMessage('');
      loadMessages(activeConv.id);
    } catch (e) {
      toast.error('Failed to send message');
    }
    setSending(false);
  };

  const startNewConversation = async () => {
    if (!caseId) {
      toast.error('No active case for conversation');
      return;
    }
    try {
      const res = await axios.post(`${API}/chat/conversations`, {
        case_id: caseId,
        subject: `Query about my case`
      }, getAuthHeader());
      await loadConversations();
      setActiveConv(res.data);
      toast.success('New conversation started!');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to start conversation');
    }
  };

  const filteredConvs = conversations.filter(c =>
    !searchQuery || (c.subject || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff/60000)}m ago`;
    if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString();
  };

  return (
    <div data-testid="message-center">
      <Card className="bg-white shadow-xl border-0 overflow-hidden" style={{ height: 'calc(100vh - 250px)', minHeight: '500px' }}>
        <div className="flex h-full">
          {/* Conversation List */}
          <div className="w-80 border-r border-slate-200 flex flex-col bg-slate-50/50">
            <div className="p-4 border-b border-slate-200">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-slate-800 flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-[#2a777a]" /> Messages
                </h3>
                <Button size="sm" onClick={startNewConversation} className="bg-[#2a777a] hover:bg-[#236466] h-8 text-xs" data-testid="new-conversation-btn">
                  New
                </Button>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input placeholder="Search conversations..." value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-9 h-9 text-sm bg-white" data-testid="search-conversations" />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {filteredConvs.length === 0 ? (
                <div className="p-6 text-center">
                  <MessageSquare className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-500">No conversations yet</p>
                  <Button size="sm" onClick={startNewConversation} variant="outline" className="mt-2 text-xs" data-testid="start-first-convo">
                    Start a conversation
                  </Button>
                </div>
              ) : (
                filteredConvs.map(conv => (
                  <button key={conv.id} onClick={() => setActiveConv(conv)}
                    className={`w-full text-left p-4 border-b border-slate-100 hover:bg-white transition-colors ${
                      activeConv?.id === conv.id ? 'bg-white border-l-2 border-l-[#2a777a]' : ''
                    }`} data-testid={`conv-${conv.id}`}>
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                        {(conv.participants?.[0]?.name || 'CM')[0]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-center">
                          <p className="font-semibold text-sm text-slate-800 truncate">{conv.subject || 'Case Discussion'}</p>
                          <span className="text-xs text-slate-400 flex-shrink-0 ml-2">{formatTime(conv.last_message_at || conv.created_at)}</span>
                        </div>
                        <p className="text-xs text-slate-500 truncate mt-0.5">{conv.last_message || 'No messages yet'}</p>
                        {conv.unread_count > 0 && (
                          <Badge className="bg-[#f7620b] text-white text-xs mt-1 h-5 px-1.5">{conv.unread_count} new</Badge>
                        )}
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Message Area */}
          <div className="flex-1 flex flex-col">
            {activeConv ? (
              <>
                {/* Chat Header */}
                <div className="px-6 py-4 border-b border-slate-200 bg-white">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-slate-800">{activeConv.subject || 'Case Discussion'}</h4>
                      <p className="text-xs text-slate-500">
                        {activeConv.case_display_id || activeConv.case_id?.substring(0, 8)}
                        {activeConv.status && <Badge className="ml-2 bg-emerald-100 text-emerald-700 text-xs capitalize">{activeConv.status}</Badge>}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gradient-to-b from-slate-50 to-white">
                  {messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <MessageSquare className="h-12 w-12 text-slate-200 mx-auto mb-3" />
                        <p className="text-slate-400 text-sm">No messages yet. Start the conversation!</p>
                      </div>
                    </div>
                  ) : (
                    messages.map((msg, idx) => {
                      const isMe = msg.sender_id === currentUser?.id;
                      return (
                        <div key={msg.id || idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`} data-testid={`message-${idx}`}>
                          <div className={`max-w-[70%] ${isMe ? 'order-2' : 'order-1'}`}>
                            {!isMe && (
                              <p className="text-xs text-slate-500 mb-1 flex items-center gap-1">
                                <User className="h-3 w-3" /> {msg.sender_name || 'Case Manager'}
                              </p>
                            )}
                            <div className={`rounded-2xl px-4 py-3 shadow-sm ${
                              isMe ? 'bg-[#2a777a] text-white rounded-br-md' : 'bg-white text-slate-800 border border-slate-200 rounded-bl-md'
                            }`}>
                              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                            </div>
                            <p className={`text-xs mt-1 ${isMe ? 'text-right text-slate-400' : 'text-slate-400'}`}>
                              {formatTime(msg.created_at)}
                            </p>
                          </div>
                        </div>
                      );
                    })
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Message Input */}
                <div className="px-6 py-4 border-t border-slate-200 bg-white">
                  <div className="flex items-center gap-3">
                    <Input
                      value={newMessage}
                      onChange={e => setNewMessage(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                      placeholder="Type your message..."
                      className="flex-1"
                      data-testid="message-input"
                    />
                    <Button onClick={handleSend} disabled={sending || !newMessage.trim()}
                      className="bg-[#2a777a] hover:bg-[#236466] px-6" data-testid="send-message-btn">
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <MessageSquare className="h-16 w-16 text-slate-200 mx-auto mb-4" />
                  <p className="text-slate-500 font-medium">Select a conversation to start messaging</p>
                  <Button onClick={startNewConversation} className="mt-4 bg-[#2a777a] hover:bg-[#236466]" data-testid="start-conversation-btn">
                    Start New Conversation
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default MessageCenter;
