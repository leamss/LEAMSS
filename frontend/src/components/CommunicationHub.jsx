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
  MessageSquare, Send, Loader2, User, ArrowLeft, FileText,
  Bell, Clock
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CommunicationHub = ({ token, cases }) => {
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [messages, setMessages] = useState([]);
  const [caseInfo, setCaseInfo] = useState({});
  const [newMessage, setNewMessage] = useState('');
  const [msgType, setMsgType] = useState('text');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef(null);

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const loadUnread = async () => {
      try {
        const res = await axios.get(`${API}/cm-tools/communications/unread-count`, { headers });
        setUnreadCount(res.data.count || 0);
      } catch (e) { /* ignore */ }
    };
    loadUnread();
  }, []);

  const loadMessages = async (caseId) => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/cm-tools/communications/${caseId}`, { headers });
      setMessages(res.data.messages || []);
      setCaseInfo({ case_id: res.data.case_id, client_name: res.data.client_name, client_email: res.data.client_email });
      // Mark as read
      await axios.put(`${API}/cm-tools/communications/${caseId}/mark-read`, {}, { headers });
    } catch (e) {
      toast.error('Failed to load messages');
    }
    setLoading(false);
  };

  useEffect(() => {
    if (selectedCaseId) loadMessages(selectedCaseId);
  }, [selectedCaseId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!newMessage.trim() || !selectedCaseId) return;
    const caseData = (cases || []).find(c => c.id === selectedCaseId);
    setSending(true);
    try {
      await axios.post(`${API}/cm-tools/communications/send`, {
        case_id: selectedCaseId,
        client_id: caseData?.client_id || '',
        message: newMessage.trim(),
        message_type: msgType,
      }, { headers });
      setNewMessage('');
      loadMessages(selectedCaseId);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to send');
    }
    setSending(false);
  };

  const quickTemplates = [
    { label: 'Document Reminder', msg: 'Please upload the required documents at your earliest convenience. You can do this from your client portal.' },
    { label: 'Step Complete', msg: 'Great news! Your current step has been completed. Please check your portal for the next steps.' },
    { label: 'Payment Reminder', msg: 'This is a gentle reminder regarding your pending payment. Please complete the payment to continue your application process.' },
    { label: 'Information Request', msg: 'We need some additional information from you. Please update your Information Sheet in the client portal.' },
  ];

  return (
    <div className="space-y-4" data-testid="communication-hub">
      {/* Case Selector */}
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <MessageSquare className="h-5 w-5 text-[#2a777a]" />
          <Select value={selectedCaseId} onValueChange={setSelectedCaseId}>
            <SelectTrigger className="flex-1" data-testid="comm-case-select">
              <SelectValue placeholder="Select a case to communicate..." />
            </SelectTrigger>
            <SelectContent>
              {(cases || []).filter(c => c.status === 'active' || c.status === 'in_progress').map(c => (
                <SelectItem key={c.id} value={c.id}>{c.case_id} - {c.client_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {unreadCount > 0 && (
            <Badge className="bg-red-500 text-white">{unreadCount} unread</Badge>
          )}
        </div>
      </Card>

      {!selectedCaseId && (
        <Card className="p-12 text-center">
          <MessageSquare className="h-12 w-12 text-slate-300 mx-auto mb-4" />
          <p className="text-slate-500">Select a case to start communicating with the client</p>
        </Card>
      )}

      {selectedCaseId && (
        <>
          {/* Case Info Bar */}
          <Card className="p-3 bg-slate-50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-slate-500" />
                <span className="font-medium text-slate-800">{caseInfo.client_name}</span>
                <span className="text-sm text-slate-500">{caseInfo.client_email}</span>
                <Badge variant="outline">{caseInfo.case_id}</Badge>
              </div>
              <Button variant="outline" size="sm" onClick={() => setSelectedCaseId('')}><ArrowLeft className="h-4 w-4 mr-1" />Back</Button>
            </div>
          </Card>

          {/* Messages */}
          <Card className="p-4">
            <div className="h-[350px] overflow-y-auto space-y-3 mb-4" data-testid="messages-container">
              {loading ? (
                <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-[#2a777a]" /></div>
              ) : messages.length === 0 ? (
                <div className="text-center py-12 text-slate-400">
                  <MessageSquare className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                  <p>No messages yet. Start the conversation!</p>
                </div>
              ) : (
                messages.map((m, idx) => (
                  <div key={m.id || idx} className={`flex ${m.sender_role === 'case_manager' || m.sender_role === 'admin' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] rounded-lg p-3 ${
                      m.sender_role === 'case_manager' || m.sender_role === 'admin'
                        ? 'bg-[#2a777a] text-white'
                        : 'bg-slate-100 text-slate-800'
                    }`} data-testid={`msg-${idx}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium opacity-80">{m.sender_name}</span>
                        {m.message_type !== 'text' && (
                          <Badge className="text-xs bg-white/20">{m.message_type === 'document_request' ? 'Doc Request' : m.message_type === 'reminder' ? 'Reminder' : m.message_type}</Badge>
                        )}
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{m.message}</p>
                      <p className="text-xs opacity-60 mt-1">{m.created_at ? new Date(m.created_at).toLocaleString() : ''}</p>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Templates */}
            <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
              {quickTemplates.map((t, idx) => (
                <Button key={idx} variant="outline" size="sm" className="whitespace-nowrap text-xs" onClick={() => setNewMessage(t.msg)} data-testid={`template-${idx}`}>
                  {t.label}
                </Button>
              ))}
            </div>

            {/* Input */}
            <div className="flex gap-2">
              <Select value={msgType} onValueChange={setMsgType}>
                <SelectTrigger className="w-[120px]" data-testid="msg-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="text">Message</SelectItem>
                  <SelectItem value="update">Update</SelectItem>
                  <SelectItem value="reminder">Reminder</SelectItem>
                  <SelectItem value="document_request">Doc Request</SelectItem>
                </SelectContent>
              </Select>
              <Textarea value={newMessage} onChange={(e) => setNewMessage(e.target.value)} placeholder="Type your message..."
                className="flex-1" rows={2} data-testid="comm-message-input"
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              />
              <Button onClick={handleSend} disabled={sending || !newMessage.trim()} className="bg-[#2a777a] hover:bg-[#236466] text-white self-end" data-testid="comm-send-btn">
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  );
};

export default CommunicationHub;
