/**
 * WhatsApp Marketing & Live Chat Inbox
 * Multi-thread conversation dashboard with WhatsApp Web-style chat box,
 * Admin partner assignment, canned responses, internal notes, and lead inspection.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  MessageSquare, Send, Search, UserCheck, UserPlus, Phone, Mail, Clock,
  CheckCheck, Paperclip, Sparkles, RefreshCw, ChevronRight, User, ShieldAlert,
  FileText, ExternalLink, PlusCircle, StickyNote, Filter, CheckCircle2,
  AlertCircle, ChevronDown, ArrowLeft, Bot, PhoneCall
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_CONFIG = {
  open: { label: 'Open', color: 'bg-emerald-100 text-emerald-800 border-emerald-300' },
  in_progress: { label: 'In Progress', color: 'bg-amber-100 text-amber-800 border-amber-300' },
  qualified: { label: 'Qualified', color: 'bg-blue-100 text-blue-800 border-blue-300' },
  closed: { label: 'Closed', color: 'bg-slate-100 text-slate-700 border-slate-300' },
};

export default function WhatsAppChatInbox() {
  const navigate = useNavigate();
  const location = useLocation();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  // Current logged in user profile
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('user') || '{}');
    } catch {
      return {};
    }
  });

  const isAdmin = useMemo(() => {
    const role = currentUser?.rbac_role || currentUser?.role || '';
    return ['admin', 'admin_owner', 'super_admin'].includes(role);
  }, [currentUser]);

  // State
  const [conversations, setConversations] = useState([]);
  const [stats, setStats] = useState({ total_all: 0, total_open: 0, total_unassigned: 0, total_mine: 0 });
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [selectedConvId, setSelectedConvId] = useState(null);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  // Filters & Search
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'mine' | 'unassigned'
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Messaging state
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);

  // Directory & Canned templates
  const [assignableUsers, setAssignableUsers] = useState([]);
  const [cannedTemplates, setCannedTemplates] = useState([]);
  const [showTemplatesDropdown, setShowTemplatesDropdown] = useState(false);

  // Dialogs
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [assignTargetUserId, setAssignTargetUserId] = useState('');
  const [assigning, setAssigning] = useState(false);

  const [showSimulateDialog, setShowSimulateDialog] = useState(false);
  const [simPhone, setSimPhone] = useState('');
  const [simName, setSimName] = useState('');
  const [simText, setSimText] = useState('');
  const [simulating, setSimulating] = useState(false);

  const [showNewChatDialog, setShowNewChatDialog] = useState(false);
  const [newChatPhone, setNewChatPhone] = useState('');
  const [newChatName, setNewChatName] = useState('');
  const [newChatInitial, setNewChatInitial] = useState('');
  const [creatingChat, setCreatingChat] = useState(false);

  // Staff note state
  const [noteText, setNoteText] = useState('');
  const [addingNote, setAddingNote] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 1. Fetch assignable users and canned templates
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const [usersRes, tmplRes] = await Promise.all([
          axios.get(`${API}/whatsapp-chat/assignable-users`, { headers }),
          axios.get(`${API}/whatsapp-chat/canned-templates`, { headers }),
        ]);
        setAssignableUsers(usersRes.data?.users || []);
        setCannedTemplates(tmplRes.data?.templates || []);
      } catch (err) {
        console.warn('Metadata fetch error:', err);
      }
    };
    if (token) fetchMetadata();
  }, [token, headers]);

  // 2. Fetch conversations
  const fetchConversations = useCallback(async (quiet = false) => {
    if (!token) return;
    if (!quiet) setLoadingConvs(true);
    try {
      const params = {
        tab: activeTab,
        status: statusFilter,
        search: searchQuery.trim() || undefined,
      };
      const res = await axios.get(`${API}/whatsapp-chat/conversations`, { headers, params });
      setConversations(res.data?.conversations || []);
      setStats(res.data?.stats || { total_all: 0, total_open: 0, total_unassigned: 0, total_mine: 0 });

      // Auto-select first conversation if none selected
      if (!selectedConvId && res.data?.conversations?.length > 0) {
        setSelectedConvId(res.data.conversations[0].id);
      }
    } catch (err) {
      if (!quiet) toast.error(formatApiError(err, 'Failed to load conversations'));
    } finally {
      if (!quiet) setLoadingConvs(false);
    }
  }, [token, headers, activeTab, statusFilter, searchQuery, selectedConvId]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Periodic polling for new messages / live sync (every 5s)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchConversations(true);
      if (selectedConvId) {
        fetchMessages(selectedConvId, true);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [selectedConvId, fetchConversations]);

  // 3. Fetch messages for active conversation
  const fetchMessages = async (convId, quiet = false) => {
    if (!convId || !token) return;
    if (!quiet) setLoadingMessages(true);
    try {
      const [convRes, msgRes] = await Promise.all([
        axios.get(`${API}/whatsapp-chat/conversations/${convId}`, { headers }),
        axios.get(`${API}/whatsapp-chat/conversations/${convId}/messages`, { headers }),
      ]);
      setActiveConv(convRes.data);
      setMessages(msgRes.data?.messages || []);
      if (!quiet) setTimeout(scrollToBottom, 100);
    } catch (err) {
      if (!quiet) toast.error(formatApiError(err, 'Failed to load messages'));
    } finally {
      if (!quiet) setLoadingMessages(false);
    }
  };

  useEffect(() => {
    if (selectedConvId) {
      fetchMessages(selectedConvId);
    }
  }, [selectedConvId]);

  // Handle send message
  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!inputText.trim() || !selectedConvId || sending) return;

    setSending(true);
    try {
      const res = await axios.post(
        `${API}/whatsapp-chat/conversations/${selectedConvId}/send`,
        { text: inputText.trim() },
        { headers }
      );

      if (res.data?.is_simulated) {
        toast.info('Message logged to thread (Simulated - WhatsApp API not configured in live mode)');
      } else if (res.data?.api_error) {
        toast.warning(`Message saved, but WhatsApp API responded: ${res.data.api_error}`);
      } else {
        toast.success('Message dispatched successfully');
      }

      setInputText('');
      fetchMessages(selectedConvId, true);
      fetchConversations(true);
    } catch (err) {
      toast.error(formatApiError(err, 'Failed to send WhatsApp message'));
    } finally {
      setSending(false);
    }
  };

  // Insert template into chat input
  const handleInsertTemplate = (tmpl) => {
    if (!tmpl?.body) return;
    let text = tmpl.body;
    if (activeConv) {
      text = text
        .replace(/{name}/g, activeConv.client_name || 'Client')
        .replace(/{client_name}/g, activeConv.client_name || 'Client')
        .replace(/{phone}/g, activeConv.phone || '')
        .replace(/{consultant_name}/g, currentUser?.name || 'LEAMSS Migration Team')
        .replace(/{company}/g, 'LEAMSS');
    }
    setInputText(text);
    setShowTemplatesDropdown(false);
  };

  // Handle Assign conversation
  const handleAssign = async () => {
    if (!selectedConvId || assigning) return;
    setAssigning(true);
    try {
      const selectedUserObj = assignableUsers.find((u) => u.id === assignTargetUserId);
      await axios.post(
        `${API}/whatsapp-chat/conversations/${selectedConvId}/assign`,
        {
          user_id: assignTargetUserId || null,
          user_name: selectedUserObj?.name || (assignTargetUserId ? selectedUserObj?.email : null),
        },
        { headers }
      );
      toast.success(assignTargetUserId ? `Assigned to ${selectedUserObj?.name || 'team member'}` : 'Chat unassigned');
      setShowAssignDialog(false);
      fetchMessages(selectedConvId, true);
      fetchConversations(true);
    } catch (err) {
      toast.error(formatApiError(err, 'Failed to assign conversation'));
    } finally {
      setAssigning(false);
    }
  };

  // Handle Update Status
  const handleStatusChange = async (newStatus) => {
    if (!selectedConvId) return;
    try {
      await axios.post(
        `${API}/whatsapp-chat/conversations/${selectedConvId}/status`,
        { status: newStatus },
        { headers }
      );
      toast.success(`Status changed to ${STATUS_CONFIG[newStatus]?.label || newStatus}`);
      setActiveConv((prev) => (prev ? { ...prev, status: newStatus } : null));
      fetchConversations(true);
    } catch (err) {
      toast.error(formatApiError(err, 'Failed to update status'));
    }
  };

  // Handle Add Internal Note
  const handleAddNote = async (e) => {
    e.preventDefault();
    if (!noteText.trim() || !selectedConvId || addingNote) return;
    setAddingNote(true);
    try {
      const res = await axios.post(
        `${API}/whatsapp-chat/conversations/${selectedConvId}/notes`,
        { text: noteText.trim() },
        { headers }
      );
      toast.success('Internal note added');
      setNoteText('');
      if (res.data?.note) {
        setActiveConv((prev) => (prev ? { ...prev, notes: [...(prev.notes || []), res.data.note] } : null));
      }
    } catch (err) {
      toast.error(formatApiError(err, 'Failed to add note'));
    } finally {
      setAddingNote(false);
    }
  };

  // Handle Simulate Inbound Message
  const handleSimulateInbound = async () => {
    if (!simPhone.trim() || !simText.trim() || simulating) return;
    setSimulating(true);
    try {
      await axios.post(
        `${API}/whatsapp-chat/simulate-inbound`,
        {
          phone: simPhone.trim(),
          client_name: simName.trim() || 'Applicant',
          text: simText.trim(),
        },
        { headers }
      );
      toast.success('Simulated incoming message received!');
      setShowSimulateDialog(false);
      setSimText('');
      fetchConversations();
    } catch (err) {
      toast.error(formatApiError(err, 'Failed to simulate incoming message'));
    } finally {
      setSimulating(false);
    }
  };

  // Handle Start New Chat
  const handleCreateChat = async () => {
    if (!newChatPhone.trim() || creatingChat) return;
    setCreatingChat(true);
    try {
      const res = await axios.post(
        `${API}/whatsapp-chat/conversations/create-or-get`,
        {
          phone: newChatPhone.trim(),
          client_name: newChatName.trim() || 'Applicant',
          initial_message: newChatInitial.trim() || undefined,
        },
        { headers }
      );
      toast.success(res.data?.is_new ? 'New WhatsApp conversation opened' : 'Existing conversation loaded');
      setShowNewChatDialog(false);
      setNewChatPhone('');
      setNewChatName('');
      setNewChatInitial('');
      await fetchConversations();
      if (res.data?.conversation?.id) {
        setSelectedConvId(res.data.conversation.id);
      }
    } catch (err) {
      toast.error(formatApiError(err, 'Failed to open conversation'));
    } finally {
      setCreatingChat(false);
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-slate-100 dark:bg-slate-950 font-sans overflow-hidden">
      {/* ── Top Header Bar ── */}
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-2.5 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-slate-500 hover:text-slate-900"
            onClick={() => navigate(isAdmin ? '/admin' : '/partner')}
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
          </Button>
          <div className="h-4 w-px bg-slate-200 dark:bg-slate-700" />
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white shadow-sm">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                WhatsApp Live Chat & Marketing Inbox
                <Badge className="bg-emerald-100 text-emerald-800 text-[10px] font-semibold">2-Way Live</Badge>
              </h1>
              <p className="text-[11px] text-slate-500">
                Assigned team conversations, instant templates & assessment intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions & Simulator */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50"
            onClick={() => {
              if (activeConv) {
                setSimPhone(activeConv.phone);
                setSimName(activeConv.client_name);
              }
              setShowSimulateDialog(true);
            }}
          >
            <Bot className="w-3.5 h-3.5 mr-1" /> Simulate Client Reply
          </Button>

          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            onClick={() => navigate('/sales/whatsapp-templates')}
          >
            <FileText className="w-3.5 h-3.5 mr-1" /> Template Manager
          </Button>

          <Button
            size="sm"
            className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={() => setShowNewChatDialog(true)}
          >
            <PlusCircle className="w-3.5 h-3.5 mr-1" /> Start New Chat
          </Button>
        </div>
      </div>

      {/* ── Main Split View ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Left Pane: Conversation List ── */}
        <div className="w-80 md:w-96 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col flex-shrink-0">
          {/* Tabs */}
          <div className="p-2.5 border-b border-slate-200 dark:border-slate-800 space-y-2">
            <div className="flex rounded-md bg-slate-100 dark:bg-slate-800 p-0.5 text-xs font-medium">
              <button
                className={`flex-1 py-1 px-2 rounded text-center transition-all ${
                  activeTab === 'all' ? 'bg-white dark:bg-slate-900 text-emerald-700 shadow-sm font-bold' : 'text-slate-600'
                }`}
                onClick={() => setActiveTab('all')}
              >
                All ({stats.total_all || 0})
              </button>
              <button
                className={`flex-1 py-1 px-2 rounded text-center transition-all ${
                  activeTab === 'mine' ? 'bg-white dark:bg-slate-900 text-emerald-700 shadow-sm font-bold' : 'text-slate-600'
                }`}
                onClick={() => setActiveTab('mine')}
              >
                Assigned to Me ({stats.total_mine || 0})
              </button>
              <button
                className={`flex-1 py-1 px-2 rounded text-center transition-all ${
                  activeTab === 'unassigned' ? 'bg-white dark:bg-slate-900 text-amber-700 shadow-sm font-bold' : 'text-slate-600'
                }`}
                onClick={() => setActiveTab('unassigned')}
              >
                Unassigned ({stats.total_unassigned || 0})
              </button>
            </div>

            {/* Search and Status filter */}
            <div className="flex gap-1.5 items-center">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="Search name, phone..."
                  className="h-8 pl-8 text-xs bg-slate-50 dark:bg-slate-800"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-8 w-28 text-xs bg-slate-50 dark:bg-slate-800">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="qualified">Qualified</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Conversations Scroll Area */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800/60">
            {loadingConvs ? (
              <div className="p-8 text-center text-xs text-slate-400">Loading conversations...</div>
            ) : conversations.length === 0 ? (
              <div className="p-8 text-center space-y-2">
                <MessageSquare className="w-8 h-8 mx-auto text-slate-300" />
                <p className="text-xs text-slate-500 font-medium">No conversations found</p>
                <p className="text-[11px] text-slate-400">Click &quot;Start New Chat&quot; or &quot;Simulate Client Reply&quot; to begin</p>
              </div>
            ) : (
              conversations.map((conv) => {
                const isSelected = conv.id === selectedConvId;
                const statusCfg = STATUS_CONFIG[conv.status] || STATUS_CONFIG.open;
                return (
                  <div
                    key={conv.id}
                    onClick={() => setSelectedConvId(conv.id)}
                    className={`p-3 cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40 relative ${
                      isSelected ? 'bg-emerald-50/60 dark:bg-emerald-950/20 border-l-4 border-emerald-600' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center font-bold text-xs text-slate-700 dark:text-slate-200 flex-shrink-0">
                          {conv.client_name ? conv.client_name.substring(0, 2).toUpperCase() : 'WA'}
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                            {conv.client_name || 'Applicant'}
                          </h4>
                          <p className="text-[11px] text-slate-500 font-mono">+{conv.phone}</p>
                        </div>
                      </div>

                      <div className="text-right flex-shrink-0 space-y-1">
                        <span className="text-[10px] text-slate-400">
                          {conv.last_message_at
                            ? new Date(conv.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                            : ''}
                        </span>
                        {conv.unread_count > 0 && (
                          <div>
                            <span className="inline-block px-1.5 py-0.5 bg-emerald-600 text-white rounded-full text-[10px] font-bold">
                              {conv.unread_count}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-600 dark:text-slate-300 truncate line-clamp-1 mb-1.5">
                      {conv.last_message_direction === 'outbound' && <span className="text-slate-400">You: </span>}
                      {conv.last_message || 'No messages yet'}
                    </p>

                    <div className="flex items-center justify-between text-[10px]">
                      <Badge className={`text-[9px] px-1.5 py-0 border ${statusCfg.color}`}>
                        {statusCfg.label}
                      </Badge>

                      {conv.assigned_to_name ? (
                        <span className="text-slate-500 font-medium flex items-center gap-1">
                          <UserCheck className="w-3 h-3 text-emerald-600" /> {conv.assigned_to_name}
                        </span>
                      ) : (
                        <span className="text-amber-600 font-medium flex items-center gap-1">
                          <UserPlus className="w-3 h-3" /> Unassigned
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ── Center Pane: Chat Window ── */}
        <div className="flex-1 flex flex-col bg-slate-50/50 dark:bg-slate-900/40 relative">
          {activeConv ? (
            <>
              {/* Active Conversation Header */}
              <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-2.5 flex items-center justify-between shadow-xs">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-emerald-700 text-white flex items-center justify-center font-bold text-xs">
                    {activeConv.client_name ? activeConv.client_name.substring(0, 2).toUpperCase() : 'WA'}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                        {activeConv.client_name || 'Applicant'}
                      </h2>
                      <Badge className={`text-[10px] px-1.5 py-0 border ${STATUS_CONFIG[activeConv.status]?.color}`}>
                        {STATUS_CONFIG[activeConv.status]?.label || activeConv.status}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-500 flex items-center gap-3">
                      <span>📱 +{activeConv.phone}</span>
                      {activeConv.client_email && <span>✉️ {activeConv.client_email}</span>}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Status Dropdown */}
                  <Select value={activeConv.status || 'open'} onValueChange={handleStatusChange}>
                    <SelectTrigger className="h-8 text-xs w-32 bg-slate-50">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="qualified">Qualified</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                    </SelectContent>
                  </Select>

                  {/* Partner Assignment Button */}
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                    onClick={() => {
                      setAssignTargetUserId(activeConv.assigned_to || '');
                      setShowAssignDialog(true);
                    }}
                  >
                    <UserCheck className="w-3.5 h-3.5 mr-1 text-indigo-600" />
                    {activeConv.assigned_to_name ? `Assigned: ${activeConv.assigned_to_name}` : 'Assign to Partner'}
                  </Button>

                  {/* Toggle Sidebar */}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 px-2 text-slate-500"
                    onClick={() => setShowSidebar(!showSidebar)}
                    title="Toggle Lead Info Sidebar"
                  >
                    <FileText className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* Messages Timeline (WhatsApp bubble style) */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#e5ddd5]/30 dark:bg-slate-950/60">
                {loadingMessages ? (
                  <div className="text-center py-12 text-xs text-slate-400">Loading conversation history...</div>
                ) : messages.length === 0 ? (
                  <div className="text-center py-12 space-y-2">
                    <p className="text-xs text-slate-500">No message history yet for this contact.</p>
                    <p className="text-[11px] text-slate-400">Type a message below or pick a template to start chatting.</p>
                  </div>
                ) : (
                  messages.map((m) => {
                    const isOutbound = m.direction === 'outbound';
                    return (
                      <div
                        key={m.id}
                        className={`flex flex-col ${isOutbound ? 'items-end' : 'items-start'}`}
                      >
                        <div
                          className={`max-w-[75%] rounded-lg px-3.5 py-2 shadow-xs text-xs relative ${
                            isOutbound
                              ? 'bg-emerald-600 text-white rounded-tr-none'
                              : 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-tl-none border border-slate-200 dark:border-slate-700'
                          }`}
                        >
                          {/* Sender name for group/staff clarification */}
                          <div
                            className={`text-[10px] font-bold mb-1 ${
                              isOutbound ? 'text-emerald-100' : 'text-emerald-700 dark:text-emerald-400'
                            }`}
                          >
                            {m.sender_name || (isOutbound ? 'LEAMSS Staff' : 'Client')}
                          </div>

                          {/* Message Body */}
                          <div className="whitespace-pre-wrap leading-relaxed text-xs">
                            {m.body}
                          </div>

                          {/* Media attachments */}
                          {m.media_filename && (
                            <div className="mt-2 p-1.5 rounded bg-black/10 flex items-center gap-2 text-[11px]">
                              <Paperclip className="w-3.5 h-3.5" />
                              <span className="truncate">{m.media_filename}</span>
                            </div>
                          )}

                          {/* Timestamp & Delivery status */}
                          <div
                            className={`flex items-center justify-end gap-1 mt-1 text-[9px] ${
                              isOutbound ? 'text-emerald-200' : 'text-slate-400'
                            }`}
                          >
                            <span>
                              {m.created_at
                                ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                : ''}
                            </span>
                            {isOutbound && (
                              <CheckCheck className={`w-3 h-3 ${m.status === 'read' ? 'text-cyan-300' : ''}`} />
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Message Input & Canned Template Picker */}
              <div className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-3 space-y-2">
                {/* Template Toolbar */}
                <div className="flex items-center justify-between text-xs">
                  <div className="relative">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 text-[11px] bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100"
                      onClick={() => setShowTemplatesDropdown(!showTemplatesDropdown)}
                    >
                      <Sparkles className="w-3 h-3 mr-1 text-emerald-600" /> Insert Canned Template
                      <ChevronDown className="w-3 h-3 ml-1" />
                    </Button>

                    {showTemplatesDropdown && (
                      <div className="absolute bottom-9 left-0 w-80 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 p-2 z-50 max-h-64 overflow-y-auto">
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2 py-1">
                          Saved WhatsApp Templates
                        </div>
                        {cannedTemplates.length === 0 ? (
                          <div className="p-3 text-center text-slate-400 text-xs">No templates found</div>
                        ) : (
                          cannedTemplates.map((t) => (
                            <button
                              key={t.id || t.name}
                              type="button"
                              onClick={() => handleInsertTemplate(t)}
                              className="w-full text-left p-2 rounded hover:bg-emerald-50 dark:hover:bg-slate-700 transition-colors"
                            >
                              <div className="font-semibold text-xs text-slate-800 dark:text-slate-200">{t.name}</div>
                              <div className="text-[10px] text-slate-500 truncate">{t.body}</div>
                            </button>
                          ))
                        )}
                      </div>
                    )}
                  </div>

                  <span className="text-[10px] text-slate-400">
                    Press <kbd className="px-1 py-0.5 bg-slate-100 rounded border">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-slate-100 rounded border">Shift+Enter</kbd> for newline
                  </span>
                </div>

                {/* Composer Form */}
                <form onSubmit={handleSendMessage} className="flex gap-2 items-end">
                  <textarea
                    rows={2}
                    placeholder="Type WhatsApp response to client..."
                    className="flex-1 text-xs p-2.5 rounded-md border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 resize-none focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                  />
                  <Button
                    type="submit"
                    disabled={!inputText.trim() || sending}
                    className="h-14 px-4 bg-emerald-600 hover:bg-emerald-700 text-white flex-shrink-0"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 space-y-3">
              <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                <MessageSquare className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">No Conversation Selected</h3>
              <p className="text-xs text-slate-500 max-w-sm">
                Select a WhatsApp lead from the left pane to view messages, assign partners, and send replies.
              </p>
            </div>
          )}
        </div>

        {/* ── Right Pane: Lead Profile & Internal Notes ── */}
        {activeConv && showSidebar && (
          <div className="w-72 md:w-80 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 flex flex-col flex-shrink-0 overflow-y-auto p-4 space-y-4">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Lead & Case Profile</h3>
              <Card className="p-3 bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 space-y-2 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 block">Full Name</span>
                  <span className="font-bold text-slate-800 dark:text-slate-100">{activeConv.client_name || 'Applicant'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Phone</span>
                  <span className="font-mono text-slate-700 dark:text-slate-300">+{activeConv.phone}</span>
                </div>
                {activeConv.client_email && (
                  <div>
                    <span className="text-[10px] text-slate-400 block">Email</span>
                    <span className="text-slate-700 dark:text-slate-300">{activeConv.client_email}</span>
                  </div>
                )}
                <div>
                  <span className="text-[10px] text-slate-400 block">Assigned Partner / Consultant</span>
                  <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                    {activeConv.assigned_to_name || 'Unassigned'}
                  </span>
                </div>
              </Card>
            </div>

            {/* Linked Pre-Assessment Information */}
            {activeConv.linked_assessment && (
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Pre-Assessment Outcome</h3>
                <Card className="p-3 bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800 space-y-2 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] text-slate-500">Total Points Score</span>
                    <Badge className="bg-emerald-600 text-white font-bold">
                      {activeConv.linked_assessment.best_total || 0} pts
                    </Badge>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Occupation</span>
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {activeConv.linked_assessment.occupation?.title || 'Professional'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Target Country</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {activeConv.linked_assessment.best_country_code || 'AU'}
                    </span>
                  </div>

                  {activeConv.linked_assessment.share_token && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full mt-2 h-7 text-[11px] border-emerald-300 text-emerald-700"
                      onClick={() => window.open(`/sales/report/${activeConv.linked_assessment.share_token}`, '_blank')}
                    >
                      <ExternalLink className="w-3 h-3 mr-1" /> View Full 23-Page Report
                    </Button>
                  )}
                </Card>
              </div>
            )}

            {/* Internal Staff Notes */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <StickyNote className="w-3.5 h-3.5 text-amber-500" /> Internal Staff Notes
              </h3>

              {/* Note Input */}
              <form onSubmit={handleAddNote} className="space-y-1.5">
                <textarea
                  rows={2}
                  placeholder="Add private staff note..."
                  className="w-full text-xs p-2 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 resize-none focus:outline-none focus:ring-1 focus:ring-amber-500"
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={!noteText.trim() || addingNote}
                  className="w-full h-7 text-[11px] bg-slate-800 hover:bg-slate-900 text-white"
                >
                  Save Note
                </Button>
              </form>

              {/* Notes List */}
              <div className="space-y-2 mt-2">
                {(activeConv.notes || []).length === 0 ? (
                  <p className="text-[11px] text-slate-400 italic">No notes added yet.</p>
                ) : (
                  activeConv.notes.map((n) => (
                    <div key={n.id} className="p-2 rounded bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 text-xs">
                      <div className="flex justify-between text-[10px] text-amber-900/70 dark:text-amber-300 font-semibold mb-1">
                        <span>{n.author_name}</span>
                        <span>{n.created_at ? new Date(n.created_at).toLocaleDateString() : ''}</span>
                      </div>
                      <p className="text-slate-700 dark:text-slate-300 text-[11px]">{n.text}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Dialog 1: Assign Partner / Consultant ── */}
      <Dialog open={showAssignDialog} onOpenChange={setShowAssignDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-emerald-600" /> Assign WhatsApp Conversation
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <p className="text-slate-600">
              Assign conversation for <strong>{activeConv?.client_name}</strong> (+{activeConv?.phone}) to a dedicated partner or sales executive:
            </p>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">Select Team Member / Partner</label>
              <Select value={assignTargetUserId} onValueChange={setAssignTargetUserId}>
                <SelectTrigger className="w-full text-xs">
                  <SelectValue placeholder="Choose partner / executive..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">-- Unassign (Public Pool) --</SelectItem>
                  {assignableUsers.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.name || u.email} ({u.role || u.rbac_role || 'Staff'})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button size="sm" variant="ghost" onClick={() => setShowAssignDialog(false)}>
              Cancel
            </Button>
            <Button size="sm" className="bg-emerald-600 text-white" disabled={assigning} onClick={handleAssign}>
              {assigning ? 'Assigning...' : 'Save Assignment'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Dialog 2: Simulate Inbound Client Reply ── */}
      <Dialog open={showSimulateDialog} onOpenChange={setShowSimulateDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <Bot className="w-4 h-4 text-emerald-600" /> Test Inbound WhatsApp Message
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <p className="text-slate-600 text-[11px]">
              Simulate a WhatsApp message sent by a customer directly into LEAMSS Inbox for testing two-way communication.
            </p>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">Sender Phone Number (with Country Code)</label>
              <Input
                placeholder="e.g. 919876543210"
                value={simPhone}
                onChange={(e) => setSimPhone(e.target.value)}
                className="text-xs font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">Client Name</label>
              <Input
                placeholder="e.g. Rahul Sharma"
                value={simName}
                onChange={(e) => setSimName(e.target.value)}
                className="text-xs"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">Client Message Body</label>
              <textarea
                rows={3}
                placeholder="e.g. Hi, I received my Australia assessment report. Can we schedule a call tomorrow?"
                className="w-full text-xs p-2 rounded border border-slate-300 dark:border-slate-700"
                value={simText}
                onChange={(e) => setSimText(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button size="sm" variant="ghost" onClick={() => setShowSimulateDialog(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-emerald-600 text-white"
              disabled={!simPhone.trim() || !simText.trim() || simulating}
              onClick={handleSimulateInbound}
            >
              {simulating ? 'Receiving...' : 'Simulate Inbound Message'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Dialog 3: Start New WhatsApp Chat ── */}
      <Dialog open={showNewChatDialog} onOpenChange={setShowNewChatDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <PlusCircle className="w-4 h-4 text-emerald-600" /> Start New WhatsApp Chat
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">Client Phone Number</label>
              <Input
                placeholder="e.g. 919876543210"
                value={newChatPhone}
                onChange={(e) => setNewChatPhone(e.target.value)}
                className="text-xs font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">Client Name</label>
              <Input
                placeholder="e.g. John Doe"
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                className="text-xs"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1">Initial Welcome Message (Optional)</label>
              <textarea
                rows={2}
                placeholder="Hello! Welcome to LEAMSS Immigration Consulting..."
                className="w-full text-xs p-2 rounded border border-slate-300"
                value={newChatInitial}
                onChange={(e) => setNewChatInitial(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button size="sm" variant="ghost" onClick={() => setShowNewChatDialog(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              className="bg-emerald-600 text-white"
              disabled={!newChatPhone.trim() || creatingChat}
              onClick={handleCreateChat}
            >
              {creatingChat ? 'Opening...' : 'Start Conversation'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
