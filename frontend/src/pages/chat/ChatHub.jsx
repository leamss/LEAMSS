import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  ArrowLeft, MessageCircle, Send, Plus, Search, Users, Smile,
  Edit2, Trash2, Check, X, MoreHorizontal,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const EMOJIS = ['👍', '❤️', '😂', '🎉', '👀', '✅'];

/**
 * Phase 21 Slice 4 Sub-Slice B.1 — Internal Chat.
 * Two-pane: left=threads, right=active thread messages + composer.
 * Polling: 8s for thread list, 4s for active messages.
 */
export default function ChatHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [me, setMe] = useState(null);
  const [threads, setThreads] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [newOpen, setNewOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editBody, setEditBody] = useState('');
  const [directory, setDirectory] = useState([]);
  const [dirQ, setDirQ] = useState('');
  const [picked, setPicked] = useState([]);
  const [groupTitle, setGroupTitle] = useState('');
  const msgListRef = useRef(null);

  const loadMe = useCallback(async () => {
    try { const r = await axios.get(`${API}/auth/me`, auth); setMe(r.data); }
    catch { navigate('/'); }
    // eslint-disable-next-line
  }, []);

  const loadThreads = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/internal-chat/threads`, auth);
      setThreads(data);
    } catch (e) {
      // silent
    }
    // eslint-disable-next-line
  }, []);

  const loadMessages = useCallback(async () => {
    if (!active) return;
    try {
      const { data } = await axios.get(`${API}/internal-chat/threads/${active.id}/messages?limit=100`, auth);
      setMessages(data);
      // mark read
      axios.post(`${API}/internal-chat/threads/${active.id}/read`, {}, auth).catch(() => {});
    } catch (e) { /* silent */ }
    // eslint-disable-next-line
  }, [active]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (!token) { navigate('/'); return; } loadMe(); loadThreads(); }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadMessages(); }, [active]);

  // Polling
  useEffect(() => {
    const tid = setInterval(loadThreads, 8000);
    return () => clearInterval(tid);
  }, [loadThreads]);
  useEffect(() => {
    if (!active) return;
    const mid = setInterval(loadMessages, 4000);
    return () => clearInterval(mid);
  }, [active, loadMessages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (msgListRef.current) {
      msgListRef.current.scrollTop = msgListRef.current.scrollHeight;
    }
  }, [messages]);

  const loadDirectory = async (q = '') => {
    try { const { data } = await axios.get(`${API}/internal-chat/directory${q ? `?q=${encodeURIComponent(q)}` : ''}`, auth); setDirectory(data); }
    catch {}
  };

  const openNew = () => {
    setPicked([]);
    setGroupTitle('');
    setDirQ('');
    loadDirectory();
    setNewOpen(true);
  };

  const createThread = async () => {
    if (picked.length === 0) { toast.error('Pick at least 1 member'); return; }
    try {
      const type = picked.length === 1 ? 'dm' : 'group';
      const payload = { type, member_ids: picked.map(p => p.id) };
      if (type === 'group' && groupTitle.trim()) payload.title = groupTitle.trim();
      const { data } = await axios.post(`${API}/internal-chat/threads`, payload, auth);
      toast.success('Thread ready');
      setNewOpen(false);
      await loadThreads();
      setActive(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create thread');
    }
  };

  const sendMessage = async () => {
    const body = draft.trim();
    if (!body || !active) return;
    setDraft('');
    try {
      await axios.post(`${API}/internal-chat/threads/${active.id}/messages`, { body }, auth);
      loadMessages();
      loadThreads();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Send failed');
      setDraft(body);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleReact = async (msgId, emoji) => {
    try {
      await axios.post(`${API}/internal-chat/messages/${msgId}/reactions`, { emoji }, auth);
      loadMessages();
    } catch (e) {
      toast.error('Reaction failed');
    }
  };

  const startEdit = (m) => { setEditingId(m.id); setEditBody(m.body); };
  const saveEdit = async () => {
    if (!editBody.trim()) return;
    try {
      await axios.patch(`${API}/internal-chat/messages/${editingId}`, { body: editBody.trim() }, auth);
      setEditingId(null);
      loadMessages();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Edit failed');
    }
  };

  const delMessage = async (msgId) => {
    try {
      await axios.delete(`${API}/internal-chat/messages/${msgId}`, auth);
      loadMessages();
    } catch {
      toast.error('Delete failed');
    }
  };

  const threadLabel = (t) => {
    if (t.type === 'group') return t.title || 'Group';
    const peer = (t.members || []).find(m => m.id !== me?.id);
    return peer?.name || 'DM';
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="chat-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="chat-back">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5 text-leamss-teal-600" />
              <div>
                <h1 className="text-lg font-bold text-slate-900">Chat</h1>
                <p className="text-xs text-slate-500">Internal team conversations</p>
              </div>
            </div>
          </div>
          <Button size="sm" onClick={openNew} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="chat-new-btn">
            <Plus className="h-4 w-4 mr-1" /> New chat
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-4">
        <div className="grid grid-cols-1 md:grid-cols-[300px_1fr] gap-3 h-[calc(100vh-160px)]">
          {/* Thread list */}
          <Card className="overflow-y-auto" data-testid="chat-threads-list">
            {threads.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-500 italic">
                Aap pehli baat shuru karein 🙏
              </div>
            )}
            {threads.map(t => {
              const unread = (t.unread_counts || {})[me?.id] || 0;
              const isActive = active?.id === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setActive(t)}
                  className={`w-full text-left p-3 border-b border-slate-100 hover:bg-slate-50 transition-all ${isActive ? 'bg-leamss-teal-50 border-l-2 border-l-leamss-teal-600' : ''}`}
                  data-testid={`chat-thread-${t.id}`}
                >
                  <div className="flex items-center justify-between gap-1.5">
                    <div className="flex items-center gap-1.5 min-w-0">
                      {t.type === 'group' ? <Users className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" /> : <MessageCircle className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />}
                      <span className="font-medium text-sm text-slate-800 truncate">{threadLabel(t)}</span>
                    </div>
                    {unread > 0 && (
                      <Badge className="bg-leamss-red-500 text-white text-[10px] h-5 px-1.5" data-testid={`chat-unread-${t.id}`}>{unread}</Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1 truncate">{t.last_message_preview || <span className="italic">No messages</span>}</p>
                </button>
              );
            })}
          </Card>

          {/* Active thread */}
          <Card className="flex flex-col overflow-hidden" data-testid="chat-active-panel">
            {!active && (
              <div className="flex-1 flex items-center justify-center text-slate-400 text-sm italic">
                Left side se ek thread chuniye, ya 'New chat' se shuru kijiye
              </div>
            )}
            {active && (
              <>
                <div className="px-4 py-2 border-b border-slate-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {active.type === 'group' ? <Users className="h-4 w-4 text-leamss-teal-600" /> : <MessageCircle className="h-4 w-4 text-leamss-teal-600" />}
                    <span className="font-semibold text-sm text-slate-800">{threadLabel(active)}</span>
                    <span className="text-[10px] text-slate-400">· {(active.member_ids || []).length} members</span>
                  </div>
                </div>
                <div ref={msgListRef} className="flex-1 overflow-y-auto p-4 space-y-2" data-testid="chat-messages">
                  {messages.length === 0 && <p className="text-xs text-slate-400 italic text-center">Conversation shuru kijiye 🙏</p>}
                  {messages.map((m, i) => {
                    const isMine = m.sender_id === me?.id;
                    const prev = messages[i - 1];
                    const groupWithPrev = prev && prev.sender_id === m.sender_id
                      && (new Date(m.created_at) - new Date(prev.created_at)) < 5 * 60 * 1000;
                    const created = new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    return (
                      <div key={m.id} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`} data-testid={`chat-msg-${m.id}`}>
                        <div className={`max-w-[70%] ${isMine ? 'items-end' : 'items-start'} flex flex-col`}>
                          {!groupWithPrev && (
                            <span className="text-[10px] text-slate-400 mb-0.5 px-1">{m.sender_name} · {created}</span>
                          )}
                          <div className={`relative group rounded-2xl px-3 py-1.5 ${isMine ? 'bg-leamss-teal-600 text-white' : 'bg-slate-100 text-slate-800'} ${m.is_deleted ? 'italic opacity-60' : ''}`}>
                            {editingId === m.id ? (
                              <div className="flex items-center gap-1">
                                <Input
                                  value={editBody}
                                  onChange={e => setEditBody(e.target.value)}
                                  onKeyDown={e => e.key === 'Enter' && saveEdit()}
                                  className="h-7 text-xs bg-white text-slate-800"
                                  data-testid={`chat-edit-input-${m.id}`}
                                />
                                <Button size="icon" variant="ghost" className="h-6 w-6 text-white hover:bg-white/20" onClick={saveEdit} data-testid={`chat-edit-save-${m.id}`}><Check className="h-3.5 w-3.5" /></Button>
                                <Button size="icon" variant="ghost" className="h-6 w-6 text-white hover:bg-white/20" onClick={() => setEditingId(null)}><X className="h-3.5 w-3.5" /></Button>
                              </div>
                            ) : (
                              <p className="text-sm whitespace-pre-wrap break-words">{m.body}</p>
                            )}
                            {m.edited_at && !m.is_deleted && <span className="text-[9px] opacity-70 ml-1">(edited)</span>}

                            {/* Action menu — only on own non-deleted messages */}
                            {isMine && !m.is_deleted && editingId !== m.id && (
                              <div className="absolute -top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex bg-white border rounded-full shadow px-1 gap-0.5">
                                <Popover>
                                  <PopoverTrigger asChild>
                                    <Button size="icon" variant="ghost" className="h-5 w-5 text-slate-500"><Smile className="h-3 w-3" /></Button>
                                  </PopoverTrigger>
                                  <PopoverContent className="w-auto p-1 flex gap-0.5">
                                    {EMOJIS.map(e => (
                                      <button key={e} onClick={() => toggleReact(m.id, e)} className="text-lg hover:scale-125 transition px-1" data-testid={`chat-react-${m.id}-${e}`}>{e}</button>
                                    ))}
                                  </PopoverContent>
                                </Popover>
                                <Button size="icon" variant="ghost" className="h-5 w-5 text-slate-500" onClick={() => startEdit(m)} data-testid={`chat-edit-btn-${m.id}`}><Edit2 className="h-3 w-3" /></Button>
                                <Button size="icon" variant="ghost" className="h-5 w-5 text-leamss-red-500" onClick={() => delMessage(m.id)} data-testid={`chat-del-btn-${m.id}`}><Trash2 className="h-3 w-3" /></Button>
                              </div>
                            )}
                            {/* Reactions only for others on others' messages */}
                            {!isMine && !m.is_deleted && (
                              <Popover>
                                <PopoverTrigger asChild>
                                  <button className="absolute -top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-white border rounded-full shadow p-0.5" data-testid={`chat-react-btn-${m.id}`}>
                                    <Smile className="h-3 w-3 text-slate-500" />
                                  </button>
                                </PopoverTrigger>
                                <PopoverContent className="w-auto p-1 flex gap-0.5">
                                  {EMOJIS.map(e => (
                                    <button key={e} onClick={() => toggleReact(m.id, e)} className="text-lg hover:scale-125 transition px-1" data-testid={`chat-react-other-${m.id}-${e}`}>{e}</button>
                                  ))}
                                </PopoverContent>
                              </Popover>
                            )}
                          </div>
                          {(m.reactions || []).length > 0 && (
                            <div className="flex gap-0.5 mt-1 px-1">
                              {m.reactions.map(r => (
                                <span key={r.emoji} className="text-xs bg-white border border-slate-200 rounded-full px-1.5 py-0.5 inline-flex items-center gap-0.5">
                                  {r.emoji} <span className="text-[9px] text-slate-500">{r.user_ids?.length || 0}</span>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="border-t border-slate-200 p-2 flex gap-2">
                  <Textarea
                    value={draft}
                    onChange={e => setDraft(e.target.value)}
                    onKeyDown={onKeyDown}
                    placeholder="Type a message… (Enter = send, Shift+Enter = newline)"
                    rows={1}
                    className="resize-none min-h-[40px] max-h-32"
                    data-testid="chat-composer-input"
                  />
                  <Button onClick={sendMessage} disabled={!draft.trim()} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="chat-send-btn">
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </>
            )}
          </Card>
        </div>
      </div>

      {/* New chat dialog */}
      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent className="max-w-md" data-testid="chat-new-dialog">
          <DialogHeader>
            <DialogTitle>New chat</DialogTitle>
            <p className="text-xs text-slate-500">Pick 1 person for DM, or 2+ for a group.</p>
          </DialogHeader>
          <div className="space-y-2">
            <div className="relative">
              <Search className="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input
                value={dirQ}
                onChange={e => { setDirQ(e.target.value); loadDirectory(e.target.value); }}
                placeholder="Search employees…"
                className="pl-7"
                data-testid="chat-directory-search"
              />
            </div>
            {picked.length >= 2 && (
              <Input
                value={groupTitle}
                onChange={e => setGroupTitle(e.target.value)}
                placeholder="Group title (optional)"
                data-testid="chat-group-title"
              />
            )}
            {picked.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {picked.map(p => (
                  <Badge key={p.id} className="bg-leamss-teal-100 text-leamss-teal-700">
                    {p.name}
                    <button onClick={() => setPicked(picked.filter(x => x.id !== p.id))} className="ml-1"><X className="h-2.5 w-2.5" /></button>
                  </Badge>
                ))}
              </div>
            )}
            <div className="max-h-48 overflow-y-auto border rounded">
              {directory.filter(u => !picked.find(p => p.id === u.id)).map(u => (
                <button
                  key={u.id}
                  onClick={() => setPicked([...picked, u])}
                  className="w-full text-left px-3 py-1.5 hover:bg-slate-50 text-sm border-b border-slate-100"
                  data-testid={`chat-directory-${u.id}`}
                >
                  <span className="text-slate-800">{u.name}</span>
                  <span className="text-[10px] text-slate-400 ml-2">{u.department || u.designation || ''}</span>
                </button>
              ))}
              {directory.length === 0 && <p className="text-xs text-slate-400 italic p-3 text-center">No matches</p>}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)}>Cancel</Button>
            <Button onClick={createThread} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="chat-create-thread-btn">
              Start chat
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
