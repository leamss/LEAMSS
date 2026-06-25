import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import {
  ArrowLeft, TicketCheck, Plus, AlertCircle, Clock, CheckCircle2,
  Bug, Sparkles, RefreshCw, Star, MessageSquare, EyeOff, History, Link2,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DEPARTMENTS = [
  { key: 'it', label: 'IT' },
  { key: 'hr', label: 'HR' },
  { key: 'finance', label: 'Finance' },
  { key: 'marketing', label: 'Marketing' },
  { key: 'ops', label: 'Operations' },
];

const STATUSES = [
  { key: 'open', label: 'Open', color: 'bg-amber-100 text-amber-700 border-amber-300' },
  { key: 'in_progress', label: 'In Progress', color: 'bg-leamss-teal-100 text-leamss-teal-700 border-leamss-teal-300' },
  { key: 'waiting', label: 'Waiting', color: 'bg-sky-100 text-sky-700 border-sky-300' },
  { key: 'resolved', label: 'Resolved', color: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  { key: 'closed', label: 'Closed', color: 'bg-slate-100 text-slate-700 border-slate-300' },
];

const PRIORITY_CHIP = {
  P0: 'bg-leamss-red-100 text-leamss-red-700 border-leamss-red-300',
  P1: 'bg-leamss-orange-100 text-leamss-orange-700 border-leamss-orange-300',
  P2: 'bg-leamss-teal-100 text-leamss-teal-700 border-leamss-teal-300',
  P3: 'bg-sky-100 text-sky-700 border-sky-300',
};

const statusObj = (k) => STATUSES.find(s => s.key === k) || STATUSES[0];

export default function TicketsHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({ total: 0, by_status: {}, past_sla: 0, resolved_this_week: 0 });
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ department: '', status: '', priority: '', mine_only: false });
  const [me, setMe] = useState(null);

  const [newOpen, setNewOpen] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', department: 'it', priority: 'P2', category: '', tags: '',
  });

  const [detail, setDetail] = useState(null);
  const [comment, setComment] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [rateOpen, setRateOpen] = useState(false);
  const [rating, setRating] = useState({ stars: 5, comment: '' });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.department) params.department = filters.department;
      if (filters.status) params.status = filters.status;
      if (filters.priority) params.priority = filters.priority;
      if (filters.mine_only) params.mine_only = true;
      const [list, st, meRes] = await Promise.all([
        axios.get(`${API}/support-tickets`, { ...auth, params }),
        axios.get(`${API}/support-tickets/stats`, auth),
        axios.get(`${API}/auth/me`, auth),
      ]);
      setTickets(list.data);
      setStats(st.data);
      setMe(meRes.data);
    } catch (e) {
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line
  }, [filters]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (!token) { navigate('/'); return; } load(); }, [filters]);

  const isAdmin = (me?.rbac_role || me?.role || '').match(/admin/i);

  const createTicket = async () => {
    if (!form.title.trim() || !form.department) { toast.error('Title aur department zaroori hai'); return; }
    try {
      const payload = {
        title: form.title.trim(),
        description: form.description.trim(),
        department: form.department,
        priority: form.priority,
        category: form.category.trim() || null,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      };
      const { data } = await axios.post(`${API}/support-tickets`, payload, auth);
      toast.success(`Ticket ${data.ticket_number} raised ✓`);
      if (data.linked_dev_item_id) {
        toast.info(`Auto-linked to Dev Tracker (bug detected)`);
      }
      setNewOpen(false);
      setForm({ title: '', description: '', department: 'it', priority: 'P2', category: '', tags: '' });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Create failed');
    }
  };

  const openDetail = async (t) => {
    try {
      const { data } = await axios.get(`${API}/support-tickets/${t.id}`, auth);
      setDetail(data);
    } catch { toast.error('Failed to open ticket'); }
  };

  const refreshDetail = async () => {
    if (!detail) return;
    const { data } = await axios.get(`${API}/support-tickets/${detail.id}`, auth);
    setDetail(data);
  };

  const addComment = async () => {
    if (!comment.trim()) return;
    try {
      await axios.post(`${API}/support-tickets/${detail.id}/comments`, { body: comment.trim(), is_internal: isInternal }, auth);
      setComment(''); setIsInternal(false);
      refreshDetail();
      toast.success('Comment added');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Comment failed');
    }
  };

  const setStatus = async (status) => {
    try {
      await axios.patch(`${API}/support-tickets/${detail.id}`, { status }, auth);
      refreshDetail(); load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Update failed'); }
  };

  const resolveTicket = async () => {
    try { await axios.post(`${API}/support-tickets/${detail.id}/resolve`, {}, auth); refreshDetail(); load(); toast.success('Resolved'); }
    catch (e) { toast.error(e.response?.data?.detail || 'Resolve failed'); }
  };

  const reopen = async () => {
    try { await axios.post(`${API}/support-tickets/${detail.id}/reopen`, {}, auth); refreshDetail(); load(); toast.success('Re-opened'); }
    catch (e) { toast.error(e.response?.data?.detail || 'Reopen failed'); }
  };

  const submitRating = async () => {
    try {
      await axios.post(`${API}/support-tickets/${detail.id}/rate`, rating, auth);
      setRateOpen(false);
      refreshDetail();
      toast.success('Thanks for rating ⭐');
    } catch (e) { toast.error(e.response?.data?.detail || 'Rate failed'); }
  };

  const isPastSLA = (t) => t.sla_target_at && new Date(t.sla_target_at) < new Date()
    && ['open', 'in_progress', 'waiting'].includes(t.status);

  return (
    <div className="min-h-screen bg-slate-50" data-testid="tickets-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="tickets-back">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div className="flex items-center gap-2">
              <TicketCheck className="h-5 w-5 text-leamss-orange-600" />
              <div>
                <h1 className="text-lg font-bold text-slate-900">Tickets</h1>
                <p className="text-xs text-slate-500">Internal helpdesk — HR · IT · Finance · Marketing · Ops</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={load} data-testid="tickets-refresh"><RefreshCw className="h-3.5 w-3.5" /></Button>
            <Button size="sm" onClick={() => setNewOpen(true)} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="tickets-new-btn">
              <Plus className="h-4 w-4 mr-1" /> Raise ticket
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-5 space-y-4">
        {/* KPI tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="tickets-kpis">
          <Card className="p-4">
            <p className="text-[10px] uppercase text-slate-500">Open</p>
            <p className="text-2xl font-bold text-amber-700">{stats.by_status?.open || 0}</p>
          </Card>
          <Card className="p-4">
            <p className="text-[10px] uppercase text-slate-500">In Progress</p>
            <p className="text-2xl font-bold text-leamss-teal-700">{stats.by_status?.in_progress || 0}</p>
          </Card>
          <Card className={`p-4 ${stats.past_sla > 0 ? 'bg-leamss-red-50 border-leamss-red-200' : ''}`}>
            <p className="text-[10px] uppercase text-slate-500 inline-flex items-center gap-1">
              {stats.past_sla > 0 && <AlertCircle className="h-3 w-3 text-leamss-red-600" />} Past SLA
            </p>
            <p className={`text-2xl font-bold ${stats.past_sla > 0 ? 'text-leamss-red-700' : 'text-slate-600'}`}>{stats.past_sla}</p>
          </Card>
          <Card className="p-4">
            <p className="text-[10px] uppercase text-slate-500">Resolved this week</p>
            <p className="text-2xl font-bold text-emerald-700">{stats.resolved_this_week}</p>
          </Card>
        </div>

        {/* Filters */}
        <Card className="p-3 flex items-center gap-2 flex-wrap">
          <Select value={filters.department || 'all'} onValueChange={v => setFilters({ ...filters, department: v === 'all' ? '' : v })}>
            <SelectTrigger className="w-32 h-9" data-testid="tickets-filter-dept"><SelectValue placeholder="Dept" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All depts</SelectItem>
              {DEPARTMENTS.map(d => <SelectItem key={d.key} value={d.key}>{d.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={filters.status || 'all'} onValueChange={v => setFilters({ ...filters, status: v === 'all' ? '' : v })}>
            <SelectTrigger className="w-32 h-9" data-testid="tickets-filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              {STATUSES.map(s => <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={filters.priority || 'all'} onValueChange={v => setFilters({ ...filters, priority: v === 'all' ? '' : v })}>
            <SelectTrigger className="w-24 h-9" data-testid="tickets-filter-priority"><SelectValue placeholder="Pri" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="P0">P0</SelectItem>
              <SelectItem value="P1">P1</SelectItem>
              <SelectItem value="P2">P2</SelectItem>
              <SelectItem value="P3">P3</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center gap-2 ml-2">
            <Switch checked={filters.mine_only} onCheckedChange={v => setFilters({ ...filters, mine_only: v })} data-testid="tickets-mine-only" />
            <Label className="text-xs cursor-pointer">Only mine</Label>
          </div>
        </Card>

        {/* List */}
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {!loading && tickets.length === 0 && (
          <Card className="p-10 text-center" data-testid="tickets-empty">
            <TicketCheck className="h-10 w-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500 italic">Koi ticket abhi tak nahi hai.</p>
            <p className="text-xs text-slate-400 mt-1">Right top ke "Raise ticket" se shuru kijiye.</p>
          </Card>
        )}
        <div className="space-y-2">
          {tickets.map(t => {
            const s = statusObj(t.status);
            const past = isPastSLA(t);
            return (
              <Card
                key={t.id}
                onClick={() => openDetail(t)}
                className={`p-3 cursor-pointer hover:shadow-md transition-all ${past ? 'border-leamss-red-300 bg-leamss-red-50/50' : ''}`}
                data-testid={`ticket-${t.id}`}
              >
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <code className="text-[10px] font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">{t.ticket_number}</code>
                      <Badge className={`text-[10px] ${PRIORITY_CHIP[t.priority]} border`}>{t.priority}</Badge>
                      <Badge className={`text-[10px] border ${s.color}`}>{s.label}</Badge>
                      <Badge variant="outline" className="text-[10px] uppercase">{t.department}</Badge>
                      {t.linked_dev_item_id && (
                        <Badge className="text-[10px] bg-leamss-red-100 text-leamss-red-700 border border-leamss-red-300 inline-flex items-center gap-1" data-testid={`ticket-dev-link-${t.id}`}>
                          <Link2 className="h-2.5 w-2.5" /> Dev Tracker
                        </Badge>
                      )}
                      {past && (
                        <Badge className="text-[10px] bg-leamss-red-600 text-white inline-flex items-center gap-1" data-testid={`ticket-past-sla-${t.id}`}>
                          <AlertCircle className="h-2.5 w-2.5" /> Past SLA
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm font-medium text-slate-800 line-clamp-1">{t.title}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5 inline-flex items-center gap-1">
                      <Clock className="h-3 w-3" /> Raised by {t.raised_by_name} · {new Date(t.created_at).toLocaleString()}
                      {t.assignee_name && <span> · assignee: {t.assignee_name}</span>}
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* New ticket dialog */}
      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent className="max-w-lg" data-testid="ticket-new-dialog">
          <DialogHeader><DialogTitle>Raise a new ticket</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Title</Label>
              <Input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="e.g., Laptop request" data-testid="ticket-title-input" />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={4} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Detailed context, steps, links…" data-testid="ticket-desc-input" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <Label>Department</Label>
                <Select value={form.department} onValueChange={v => setForm({ ...form, department: v })}>
                  <SelectTrigger data-testid="ticket-dept-input"><SelectValue /></SelectTrigger>
                  <SelectContent>{DEPARTMENTS.map(d => <SelectItem key={d.key} value={d.key}>{d.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label>Priority</Label>
                <Select value={form.priority} onValueChange={v => setForm({ ...form, priority: v })}>
                  <SelectTrigger data-testid="ticket-priority-input"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="P0">P0 — blocker (4h)</SelectItem>
                    <SelectItem value="P1">P1 — high (8h)</SelectItem>
                    <SelectItem value="P2">P2 — normal (24h)</SelectItem>
                    <SelectItem value="P3">P3 — low (72h)</SelectItem>
                  </SelectContent>
                </Select>
                {!isAdmin && form.priority !== 'P3' && (
                  <p className="text-[10px] text-leamss-orange-600 mt-0.5">Non-admin requests default to P3</p>
                )}
              </div>
              <div>
                <Label>Category (optional)</Label>
                <Input value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} placeholder="e.g., hardware" data-testid="ticket-category-input" />
              </div>
            </div>
            <div>
              <Label>Tags (comma-separated)</Label>
              <Input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} placeholder="bug, urgent, mobile" data-testid="ticket-tags-input" />
              <p className="text-[10px] text-slate-400 mt-0.5">Tip: tag "bug" on IT/Marketing tickets auto-creates a Dev Tracker item</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)} data-testid="ticket-cancel-btn">Cancel</Button>
            <Button onClick={createTicket} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="ticket-submit-btn">Submit</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail dialog */}
      <Dialog open={!!detail} onOpenChange={(o) => { if (!o) setDetail(null); }}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="ticket-detail-dialog">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 flex-wrap">
                  <code className="text-xs font-mono bg-slate-100 px-1.5 py-0.5 rounded">{detail.ticket_number}</code>
                  <Badge className={`text-[10px] ${PRIORITY_CHIP[detail.priority]} border`}>{detail.priority}</Badge>
                  <Badge className={`text-[10px] border ${statusObj(detail.status).color}`}>{statusObj(detail.status).label}</Badge>
                  <span className="text-base">{detail.title}</span>
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <Card className="p-3 bg-slate-50">
                  <p className="text-sm text-slate-800 whitespace-pre-wrap">{detail.description || <span className="italic text-slate-400">No description</span>}</p>
                </Card>

                {/* Linked dev tracker */}
                {detail.linked_dev_item_id && (
                  <Card className="p-2.5 bg-leamss-red-50 border-leamss-red-200" data-testid="ticket-dev-linked-card">
                    <p className="text-xs flex items-center gap-1.5 text-leamss-red-700">
                      <Bug className="h-3.5 w-3.5" />
                      Auto-linked to Dev Tracker item
                      <button
                        onClick={() => navigate(`/portal/it/dev-tracker`)}
                        className="font-mono text-[10px] bg-white px-1.5 py-0.5 rounded hover:bg-leamss-red-100"
                        data-testid="ticket-open-dev-link"
                      >
                        {detail.linked_dev_item_id.slice(0, 8)}
                      </button>
                    </p>
                  </Card>
                )}

                {/* Meta */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  <div><p className="text-slate-400 uppercase text-[9px]">Department</p><p className="capitalize">{detail.department}</p></div>
                  <div><p className="text-slate-400 uppercase text-[9px]">Raised by</p><p>{detail.raised_by_name}</p></div>
                  <div><p className="text-slate-400 uppercase text-[9px]">Assignee</p><p>{detail.assignee_name || 'Unassigned'}</p></div>
                  <div>
                    <p className="text-slate-400 uppercase text-[9px]">SLA target</p>
                    <p className={isPastSLA(detail) ? 'text-leamss-red-700 font-semibold' : ''}>
                      {detail.sla_target_at ? new Date(detail.sla_target_at).toLocaleString() : '—'}
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 flex-wrap" data-testid="ticket-actions">
                  {detail.status !== 'resolved' && detail.status !== 'closed' && (
                    <>
                      {detail.status === 'open' && (
                        <Button size="sm" variant="outline" onClick={() => setStatus('in_progress')} data-testid="ticket-start">Start work</Button>
                      )}
                      {detail.status === 'in_progress' && (
                        <Button size="sm" variant="outline" onClick={() => setStatus('waiting')} data-testid="ticket-waiting">Mark waiting</Button>
                      )}
                      <Button size="sm" onClick={resolveTicket} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="ticket-resolve">
                        <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Resolve
                      </Button>
                    </>
                  )}
                  {(detail.status === 'resolved' || detail.status === 'closed') && detail.raised_by_id === me?.id && (
                    <>
                      <Button size="sm" variant="outline" onClick={reopen} data-testid="ticket-reopen">Reopen</Button>
                      {!detail.satisfaction_rating && (
                        <Button size="sm" onClick={() => setRateOpen(true)} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="ticket-rate-btn">
                          <Star className="h-3.5 w-3.5 mr-1" /> Rate
                        </Button>
                      )}
                    </>
                  )}
                </div>
                {detail.satisfaction_rating && (
                  <Card className="p-2 bg-emerald-50 border-emerald-200">
                    <p className="text-xs text-emerald-800">
                      ⭐ {detail.satisfaction_rating.stars}/5 — {detail.satisfaction_rating.comment || 'No comment'}
                    </p>
                  </Card>
                )}

                {/* Comments */}
                <div data-testid="ticket-comments-section">
                  <h4 className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
                    <MessageSquare className="h-3.5 w-3.5" /> Comments ({(detail.comments || []).length})
                  </h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {(detail.comments || []).map(c => (
                      <Card key={c.comment_id} className={`p-2.5 text-xs ${c.is_internal ? 'bg-leamss-orange-50 border-leamss-orange-200' : 'bg-slate-50'}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-slate-800 inline-flex items-center gap-1">
                            {c.is_internal && <EyeOff className="h-3 w-3 text-leamss-orange-600" />}
                            {c.author_name}
                            {c.is_internal && <span className="text-[9px] text-leamss-orange-700">(internal note)</span>}
                          </span>
                          <span className="text-[10px] text-slate-400">{new Date(c.created_at).toLocaleString()}</span>
                        </div>
                        <p className="text-slate-700 whitespace-pre-wrap">{c.body}</p>
                      </Card>
                    ))}
                    {(detail.comments || []).length === 0 && <p className="text-[11px] text-slate-400 italic">No comments yet</p>}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Textarea
                      rows={2}
                      value={comment}
                      onChange={e => setComment(e.target.value)}
                      placeholder="Add a comment…"
                      data-testid="ticket-comment-input"
                    />
                    <div className="flex flex-col gap-1">
                      <Button onClick={addComment} size="sm" className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="ticket-comment-submit">Post</Button>
                      {isAdmin && (
                        <label className="text-[10px] flex items-center gap-1 cursor-pointer">
                          <Switch checked={isInternal} onCheckedChange={setIsInternal} data-testid="ticket-internal-toggle" />
                          Internal
                        </label>
                      )}
                    </div>
                  </div>
                </div>

                {/* Audit log */}
                <details className="border-t border-slate-200 pt-2">
                  <summary className="text-xs font-semibold text-slate-700 cursor-pointer inline-flex items-center gap-1.5">
                    <History className="h-3.5 w-3.5" /> Audit log ({(detail.audit_log || []).length})
                  </summary>
                  <div className="mt-2 space-y-1">
                    {(detail.audit_log || []).map((e, i) => (
                      <div key={i} className="text-[11px] flex items-start gap-2 p-1.5 bg-slate-50 rounded">
                        <div className="mt-0.5 h-1.5 w-1.5 rounded-full bg-leamss-orange-500" />
                        <div className="flex-1">
                          <span className="font-medium capitalize">{e.action.replace(/_/g, ' ')}</span>
                          {' by '}<span className="text-slate-600">{e.actor_name}</span>
                          {e.from !== undefined && <span className="text-slate-400 ml-1">({String(e.from)} → {String(e.to)})</span>}
                          <p className="text-[10px] text-slate-400">{new Date(e.timestamp).toLocaleString()}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Rate dialog */}
      <Dialog open={rateOpen} onOpenChange={setRateOpen}>
        <DialogContent className="max-w-md" data-testid="ticket-rate-dialog">
          <DialogHeader><DialogTitle>Rate this resolution</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="flex justify-center gap-1">
              {[1, 2, 3, 4, 5].map(s => (
                <button
                  key={s}
                  onClick={() => setRating({ ...rating, stars: s })}
                  className="hover:scale-110 transition"
                  data-testid={`rate-star-${s}`}
                >
                  <Star className={`h-7 w-7 ${s <= rating.stars ? 'fill-leamss-orange-500 text-leamss-orange-500' : 'text-slate-300'}`} />
                </button>
              ))}
            </div>
            <Textarea
              rows={3}
              value={rating.comment}
              onChange={e => setRating({ ...rating, comment: e.target.value })}
              placeholder="Optional comment about the resolution…"
              data-testid="rate-comment-input"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRateOpen(false)}>Cancel</Button>
            <Button onClick={submitRating} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="rate-submit-btn">Submit rating</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
