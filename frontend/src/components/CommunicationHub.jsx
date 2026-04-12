import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  MessageSquare, Send, Loader2, User, Search, Clock
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CommunicationHub = ({ token }) => {
  const [conversations, setConversations] = useState([]);
  const [activeCase, setActiveCase] = useState(null);
  const [messages, setMessages] = useState([]);
  const [caseInfo, setCaseInfo] = useState({});
  const [newMessage, setNewMessage] = useState('');
  const [msgType, setMsgType] = useState('text');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef(null);

  const headers = { Authorization: `Bearer ${token}` };

  // Load all conversations (cases with message info)
  const loadConversations = async () => {
    try {
      // Get all CM's cases
      const casesRes = await axios.get(`${API}/cm-tools/my-cases-summary`, { headers });
      const allCases = casesRes.data || [];

      // For each case, get last message and unread count
      const enriched = await Promise.all(allCases.map(async (c) => {
        try {
          const commRes = await axios.get(`${API}/cm-tools/communications/${c.id}`, { headers });
          const msgs = commRes.data.messages || [];
          const lastMsg = msgs.length > 0 ? msgs[msgs.length - 1] : null;
          const unread = msgs.filter(m => m.sender_role !== 'case_manager' && m.sender_role !== 'admin' && !m.read).length;
          // Get client name from comm response
          const clientName = commRes.data.client_name || c.client_name || 'Unknown Client';

          return {
            ...c,
            client_name: clientName,
            client_email: commRes.data.client_email || '',
            last_message: lastMsg?.message?.slice(0, 80) || '',
            last_message_at: lastMsg?.created_at || '',
            last_sender: lastMsg?.sender_role || '',
            unread_count: unread,
            message_count: msgs.length,
          };
        } catch {
          return { ...c, client_name: c.client_name || 'Unknown', last_message: '', unread_count: 0, message_count: 0 };
        }
      }));

      // Sort: unread first, then by last message time
      enriched.sort((a, b) => {
        if (a.unread_count > 0 && b.unread_count === 0) return -1;
        if (a.unread_count === 0 && b.unread_count > 0) return 1;
        return (b.last_message_at || '').localeCompare(a.last_message_at || '');
      });

      setConversations(enriched);
      // Auto-select first if none selected
      if (!activeCase && enriched.length > 0) {
        setActiveCase(enriched[0]);
        loadMessages(enriched[0].id, enriched[0].client_id);
      }
    } catch (e) {
      console.error('Failed to load conversations');
    }
    setLoading(false);
  };

  const loadMessages = async (caseId, clientId) => {
    try {
      const res = await axios.get(`${API}/cm-tools/communications/${caseId}`, { headers });
      setMessages(res.data.messages || []);
      setCaseInfo({
        case_id: res.data.case_id,
        client_name: res.data.client_name,
        client_email: res.data.client_email,
        client_id: clientId,
      });
      // Mark as read
      await axios.put(`${API}/cm-tools/communications/${caseId}/mark-read`, {}, { headers });
    } catch (e) {
      setMessages([]);
    }
  };

  useEffect(() => { loadConversations(); }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSelectCase = (conv) => {
    setActiveCase(conv);
    loadMessages(conv.id, conv.client_id);
  };

  const handleSend = async () => {
    if (!newMessage.trim() || !activeCase) return;
    setSending(true);
    try {
      await axios.post(`${API}/cm-tools/communications/send`, {
        case_id: activeCase.id,
        client_id: activeCase.client_id || caseInfo.client_id || '',
        message: newMessage.trim(),
        message_type: msgType,
      }, { headers });
      setNewMessage('');
      loadMessages(activeCase.id, activeCase.client_id);
      // Refresh conversation list for updated last message
      loadConversations();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to send');
    }
    setSending(false);
  };

  const quickTemplates = [
    { label: 'Doc Reminder', msg: 'Please upload the required documents at your earliest convenience.' },
    { label: 'Step Done', msg: 'Your current step has been completed. Check your portal for next steps.' },
    { label: 'Payment', msg: 'This is a gentle reminder regarding your pending payment.' },
    { label: 'Info Needed', msg: 'We need additional information from you. Please update your Info Sheet.' },
  ];

  const filteredConvos = conversations.filter(c =>
    !searchQuery ||
    c.case_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.client_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.product_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  return (
    <div data-testid="communication-hub">
      <div className="flex h-[600px] bg-white dark:bg-slate-900 rounded-xl border overflow-hidden">
        {/* Left sidebar - conversation list */}
        <div className="w-[300px] border-r flex flex-col">
          <div className="p-3 border-b">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-1.5">
                <MessageSquare className="h-4 w-4 text-[#2a777a]" />Clients ({conversations.length})
              </h3>
              {conversations.reduce((sum, c) => sum + c.unread_count, 0) > 0 && (
                <Badge className="bg-red-500 text-white">{conversations.reduce((sum, c) => sum + c.unread_count, 0)} unread</Badge>
              )}
            </div>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <Input placeholder="Search cases/clients..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-8 h-8 text-sm" data-testid="comm-search" />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {filteredConvos.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-400">No cases found</div>
            ) : (
              filteredConvos.map((conv, idx) => (
                <div key={conv.id}
                  className={`p-3 cursor-pointer border-b hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${activeCase?.id === conv.id ? 'bg-[#2a777a]/10 border-l-4 border-l-[#2a777a]' : ''}`}
                  onClick={() => handleSelectCase(conv)}
                  data-testid={`conv-${idx}`}
                >
                  <div className="flex items-center gap-2">
                    <div className="h-9 w-9 rounded-full bg-[#2a777a]/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[#2a777a] dark:text-[#4db8bb] font-bold text-xs">{(conv.client_name || '?').charAt(0)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-sm text-slate-800 dark:text-white truncate">{conv.client_name || conv.case_id}</p>
                        {conv.last_message_at && (
                          <span className="text-[10px] text-slate-400 flex-shrink-0 ml-1">{new Date(conv.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 truncate">{conv.case_id} — {conv.product_name}</p>
                      <p className="text-xs text-slate-400 truncate">{conv.last_message || 'No messages yet'}</p>
                    </div>
                    {conv.unread_count > 0 && <Badge className="bg-[#2a777a] text-white text-[10px] h-5 w-5 flex items-center justify-center rounded-full p-0 flex-shrink-0">{conv.unread_count}</Badge>}
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
                <p>Select a client to start communicating</p>
              </div>
            </div>
          ) : (
            <>
              {/* Chat header */}
              <div className="p-3 border-b bg-slate-50 dark:bg-slate-800">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-full bg-[#2a777a]/10 flex items-center justify-center">
                    <span className="text-[#2a777a] font-bold text-sm">{(caseInfo.client_name || activeCase.client_name || '?').charAt(0)}</span>
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-800 dark:text-white">{caseInfo.client_name || activeCase.client_name}</h4>
                    <p className="text-xs text-slate-500">{caseInfo.case_id || activeCase.case_id} | {caseInfo.client_email || activeCase.client_email}</p>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="messages-container">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-slate-400">
                    <div className="text-center">
                      <MessageSquare className="h-10 w-10 mx-auto mb-2 text-slate-300" />
                      <p className="text-sm">No messages yet. Send the first message!</p>
                    </div>
                  </div>
                ) : (
                  messages.map((m, idx) => {
                    const isMe = m.sender_role === 'case_manager' || m.sender_role === 'admin';
                    return (
                      <div key={m.id || idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${
                          isMe ? 'bg-[#2a777a] text-white rounded-br-md' : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white rounded-bl-md'
                        }`} data-testid={`msg-${idx}`}>
                          {!isMe && <p className="text-xs font-medium opacity-70 mb-0.5">{m.sender_name}</p>}
                          {m.message_type && m.message_type !== 'text' && (
                            <Badge className="mb-1 text-[10px] bg-white/20">{m.message_type === 'document_request' ? 'Doc Request' : m.message_type}</Badge>
                          )}
                          <p className="text-sm whitespace-pre-wrap">{m.message}</p>
                          <p className="text-[10px] opacity-50 mt-1 text-right">{m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</p>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick templates */}
              <div className="px-3 pt-2 flex gap-1.5 overflow-x-auto">
                {quickTemplates.map((t, idx) => (
                  <Button key={idx} variant="outline" size="sm" className="whitespace-nowrap text-[11px] h-7 px-2" onClick={() => setNewMessage(t.msg)} data-testid={`template-${idx}`}>
                    {t.label}
                  </Button>
                ))}
              </div>

              {/* Input */}
              <div className="p-3 border-t bg-white dark:bg-slate-900">
                <div className="flex gap-2">
                  <Select value={msgType} onValueChange={setMsgType}>
                    <SelectTrigger className="w-[100px] h-9 text-xs" data-testid="msg-type"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="text">Message</SelectItem>
                      <SelectItem value="update">Update</SelectItem>
                      <SelectItem value="reminder">Reminder</SelectItem>
                      <SelectItem value="document_request">Doc Request</SelectItem>
                    </SelectContent>
                  </Select>
                  <Textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type a message..."
                    className="flex-1 resize-none"
                    rows={1}
                    data-testid="comm-message-input"
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  />
                  <Button onClick={handleSend} disabled={sending || !newMessage.trim()} className="bg-[#2a777a] hover:bg-[#236466] text-white self-end" data-testid="comm-send-btn">
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

export default CommunicationHub;
