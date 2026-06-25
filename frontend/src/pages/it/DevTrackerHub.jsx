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
import {
  ArrowLeft, Plus, KanbanSquare, MessageSquare, Bug, Sparkles, Wrench,
  ChevronLeft, ChevronRight, Search, History,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUSES = [
  { key: 'backlog', label: 'Backlog', accent: 'slate' },
  { key: 'in_progress', label: 'In Progress', accent: 'leamss-teal' },
  { key: 'in_review', label: 'In Review', accent: 'leamss-orange' },
  { key: 'done', label: 'Done', accent: 'emerald' },
];

const STATUS_BG = {
  slate: 'bg-slate-100 text-slate-700 border-slate-300',
  'leamss-teal': 'bg-leamss-teal-100 text-leamss-teal-700 border-leamss-teal-300',
  'leamss-orange': 'bg-leamss-orange-100 text-leamss-orange-700 border-leamss-orange-300',
  emerald: 'bg-emerald-100 text-emerald-700 border-emerald-300',
};

const PRIORITY_CHIP = {
  P0: 'bg-leamss-red-100 text-leamss-red-700 border border-leamss-red-300',
  P1: 'bg-leamss-orange-100 text-leamss-orange-700 border border-leamss-orange-300',
  P2: 'bg-leamss-teal-100 text-leamss-teal-700 border border-leamss-teal-300',
  P3: 'bg-sky-100 text-sky-700 border border-sky-300',
};

const TYPE_ICON = { bug: Bug, feature: Sparkles, chore: Wrench };

/**
 * Phase 21 Slice 4 Sub-Slice A.2 — Dev Tracker kanban.
 * Click-to-move buttons on each card (no DnD lib) — works perfectly on mobile.
 */
export default function DevTrackerHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ q: '', type: '', priority: '' });
  // Mobile-only: which kanban column is currently visible on <md viewports
  const [mobileStatus, setMobileStatus] = useState('backlog');
  const [newOpen, setNewOpen] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', type: 'bug', priority: 'P2', labels: '',
  });
  const [detail, setDetail] = useState(null);
  const [comment, setComment] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.q) params.q = filters.q;
      if (filters.type) params.type = filters.type;
      if (filters.priority) params.priority = filters.priority;
      const { data } = await axios.get(`${API}/dev-tracker/items`, { ...auth, params });
      setItems(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load items');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line
  }, [filters]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (!token) { navigate('/'); return; } load(); }, [filters]);

  const createItem = async () => {
    if (!form.title.trim()) { toast.error('Title required'); return; }
    try {
      const payload = {
        title: form.title.trim(),
        description: form.description.trim(),
        type: form.type,
        priority: form.priority,
        status: 'backlog',
        labels: form.labels.split(',').map(s => s.trim()).filter(Boolean),
      };
      await axios.post(`${API}/dev-tracker/items`, payload, auth);
      toast.success('Item created ✓');
      setNewOpen(false);
      setForm({ title: '', description: '', type: 'bug', priority: 'P2', labels: '' });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Create failed');
    }
  };

  const moveItem = async (item, direction) => {
    const idx = STATUSES.findIndex(s => s.key === item.status);
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= STATUSES.length) return;
    try {
      await axios.patch(`${API}/dev-tracker/items/${item.id}`, { status: STATUSES[newIdx].key }, auth);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Move failed');
    }
  };

  const openDetail = async (item) => {
    try {
      const { data } = await axios.get(`${API}/dev-tracker/items/${item.id}`, auth);
      setDetail(data);
    } catch {
      toast.error('Failed to load detail');
    }
  };

  const addComment = async () => {
    if (!comment.trim() || !detail) return;
    try {
      await axios.post(`${API}/dev-tracker/items/${detail.id}/comments`, { body: comment.trim() }, auth);
      setComment('');
      openDetail(detail);
      load();
      toast.success('Comment added');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Comment failed');
    }
  };

  const byStatus = (s) => items.filter(i => i.status === s);

  return (
    <div className="min-h-screen bg-slate-50" data-testid="dev-tracker-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="dev-back">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div className="flex items-center gap-2">
              <KanbanSquare className="h-5 w-5 text-leamss-teal-600" />
              <div>
                <h1 className="text-lg font-bold text-slate-900">Dev Tracker</h1>
                <p className="text-xs text-slate-500">Bugs · features · chores — internal kanban</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search…"
                value={filters.q}
                onChange={e => setFilters({ ...filters, q: e.target.value })}
                className="pl-7 h-9 w-48"
                data-testid="dev-search"
              />
            </div>
            <Select value={filters.type || 'all'} onValueChange={v => setFilters({ ...filters, type: v === 'all' ? '' : v })}>
              <SelectTrigger className="w-28 h-9" data-testid="dev-filter-type"><SelectValue placeholder="Type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                <SelectItem value="bug">Bug</SelectItem>
                <SelectItem value="feature">Feature</SelectItem>
                <SelectItem value="chore">Chore</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.priority || 'all'} onValueChange={v => setFilters({ ...filters, priority: v === 'all' ? '' : v })}>
              <SelectTrigger className="w-24 h-9" data-testid="dev-filter-priority"><SelectValue placeholder="Pri" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="P0">P0</SelectItem>
                <SelectItem value="P1">P1</SelectItem>
                <SelectItem value="P2">P2</SelectItem>
                <SelectItem value="P3">P3</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" onClick={() => setNewOpen(true)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="dev-new-btn">
              <Plus className="h-4 w-4 mr-1" /> New
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-5">
        {loading && <p className="text-sm text-slate-500">Loading…</p>}
        {/* Mobile-only status switcher — pick which kanban column to view at <md */}
        <div className="md:hidden flex gap-1.5 overflow-x-auto pb-2 mb-3" data-testid="kanban-column-switcher-row">
          {STATUSES.map(s => {
            const count = byStatus(s.key).length;
            const isActive = mobileStatus === s.key;
            return (
              <button
                key={s.key}
                onClick={() => setMobileStatus(s.key)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap border transition-all ${
                  isActive
                    ? `${STATUS_BG[s.accent]} border-current shadow-sm`
                    : 'bg-white text-slate-500 border-slate-200'
                }`}
                data-testid={`kanban-column-switcher-${s.key}`}
              >
                {s.label} <span className="ml-1 text-[10px] opacity-70">({count})</span>
              </button>
            );
          })}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3" data-testid="dev-kanban">
          {STATUSES.map(s => {
            const cards = byStatus(s.key);
            // On mobile, only render the selected column
            const mobileVisible = mobileStatus === s.key;
            return (
              <div key={s.key} className={`flex-col ${mobileVisible ? 'flex' : 'hidden md:flex'}`}>
                <div className={`px-3 py-2 rounded-t-lg border-b-2 ${STATUS_BG[s.accent]}`} data-testid={`dev-col-${s.key}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs">{s.label}</span>
                    <Badge variant="outline" className="text-[10px] bg-white">{cards.length}</Badge>
                  </div>
                </div>
                <div className="bg-white border border-t-0 border-slate-200 rounded-b-lg p-2 space-y-2 min-h-[200px]" data-testid={`dev-col-body-${s.key}`}>
                  {cards.length === 0 && <p className="text-[11px] text-slate-400 italic text-center py-4">Empty</p>}
                  {cards.map(it => {
                    const TypeIcon = TYPE_ICON[it.type] || Bug;
                    const idx = STATUSES.findIndex(x => x.key === it.status);
                    return (
                      <Card key={it.id} className="p-2.5 hover:shadow-md transition-all" data-testid={`dev-card-${it.id}`}>
                        <div className="flex items-start justify-between gap-1 mb-1.5">
                          <div className="flex items-center gap-1.5">
                            <TypeIcon className="h-3 w-3 text-slate-400" />
                            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${PRIORITY_CHIP[it.priority]}`}>{it.priority}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            {it.comment_count > 0 && (
                              <span className="text-[10px] text-slate-400 inline-flex items-center gap-0.5">
                                <MessageSquare className="h-3 w-3" /> {it.comment_count}
                              </span>
                            )}
                          </div>
                        </div>
                        <p
                          className="text-sm font-medium text-slate-800 cursor-pointer hover:text-leamss-teal-700 line-clamp-2 mb-1"
                          onClick={() => openDetail(it)}
                          data-testid={`dev-card-title-${it.id}`}
                        >
                          {it.title}
                        </p>
                        {(it.labels || []).length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-1">
                            {it.labels.slice(0, 3).map((l, i) => (
                              <Badge key={i} variant="outline" className="text-[9px] bg-sky-50 text-sky-700 border-sky-200">{l}</Badge>
                            ))}
                          </div>
                        )}
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-[10px] text-slate-400 truncate max-w-[80px]" title={it.assignee_name || 'unassigned'}>
                            {it.assignee_name || 'Unassigned'}
                          </span>
                          <div className="flex gap-0.5">
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-6 w-6"
                              disabled={idx === 0}
                              onClick={() => moveItem(it, -1)}
                              title="Move left"
                              data-testid={`dev-move-left-${it.id}`}
                            >
                              <ChevronLeft className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-6 w-6"
                              disabled={idx === STATUSES.length - 1}
                              onClick={() => moveItem(it, +1)}
                              title="Move right"
                              data-testid={`dev-move-right-${it.id}`}
                            >
                              <ChevronRight className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* New item dialog */}
      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent className="max-w-lg" data-testid="dev-new-dialog">
          <DialogHeader><DialogTitle>New tracker item</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Title</Label>
              <Input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Brief problem statement" data-testid="dev-title-input" />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea rows={4} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Steps, expected/actual, links…" data-testid="dev-desc-input" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>Type</Label>
                <Select value={form.type} onValueChange={v => setForm({ ...form, type: v })}>
                  <SelectTrigger data-testid="dev-type-input"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bug">Bug</SelectItem>
                    <SelectItem value="feature">Feature</SelectItem>
                    <SelectItem value="chore">Chore</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Priority</Label>
                <Select value={form.priority} onValueChange={v => setForm({ ...form, priority: v })}>
                  <SelectTrigger data-testid="dev-priority-input"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="P0">P0 — blocker</SelectItem>
                    <SelectItem value="P1">P1 — high</SelectItem>
                    <SelectItem value="P2">P2 — normal</SelectItem>
                    <SelectItem value="P3">P3 — low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Labels (comma-separated)</Label>
              <Input value={form.labels} onChange={e => setForm({ ...form, labels: e.target.value })} placeholder="frontend, ui, urgent" data-testid="dev-labels-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNewOpen(false)} data-testid="dev-cancel-btn">Cancel</Button>
            <Button onClick={createItem} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="dev-create-btn">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail dialog */}
      <Dialog open={!!detail} onOpenChange={(o) => { if (!o) setDetail(null); }}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="dev-detail-dialog">
          {detail && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2 flex-wrap">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${PRIORITY_CHIP[detail.priority]}`}>{detail.priority}</span>
                  <Badge variant="outline" className="capitalize text-[10px]">{detail.type}</Badge>
                  <Badge className={STATUS_BG[STATUSES.find(s => s.key === detail.status)?.accent || 'slate']}>{detail.status.replace('_', ' ')}</Badge>
                  <span>{detail.title}</span>
                </DialogTitle>
                <p className="text-[10px] text-slate-400 font-mono mt-1">{detail.id}</p>
              </DialogHeader>
              <div className="space-y-3">
                <Card className="p-3 bg-slate-50">
                  <h4 className="text-xs font-semibold text-slate-600 mb-1">Description</h4>
                  <p className="text-sm text-slate-800 whitespace-pre-wrap" data-testid="dev-detail-desc">
                    {detail.description || <span className="italic text-slate-400">No description</span>}
                  </p>
                </Card>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <p className="text-slate-400 uppercase text-[9px]">Reporter</p>
                    <p className="text-slate-700">{detail.reporter_name}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 uppercase text-[9px]">Assignee</p>
                    <p className="text-slate-700">{detail.assignee_name || 'Unassigned'}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 uppercase text-[9px]">Created</p>
                    <p className="text-slate-700">{new Date(detail.created_at).toLocaleString()}</p>
                  </div>
                </div>

                {/* Comments */}
                <div data-testid="dev-comments-section">
                  <h4 className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
                    <MessageSquare className="h-3.5 w-3.5" /> Comments ({detail.comments?.length || 0})
                  </h4>
                  <div className="space-y-2">
                    {(detail.comments || []).map(c => (
                      <Card key={c.comment_id} className="p-2.5 text-xs bg-slate-50">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-slate-800">{c.author_name}</span>
                          <span className="text-[10px] text-slate-400">{new Date(c.created_at).toLocaleString()}</span>
                        </div>
                        <p className="text-slate-700 whitespace-pre-wrap">{c.body}</p>
                      </Card>
                    ))}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Input
                      value={comment}
                      onChange={e => setComment(e.target.value)}
                      placeholder="Add a comment…"
                      onKeyDown={e => e.key === 'Enter' && addComment()}
                      data-testid="dev-comment-input"
                    />
                    <Button onClick={addComment} size="sm" className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="dev-comment-submit">
                      Post
                    </Button>
                  </div>
                </div>

                {/* Audit log */}
                <details className="border-t border-slate-200 pt-2">
                  <summary className="text-xs font-semibold text-slate-700 cursor-pointer flex items-center gap-1.5">
                    <History className="h-3.5 w-3.5" /> Audit log ({detail.audit_log?.length || 0})
                  </summary>
                  <div className="mt-2 space-y-1">
                    {(detail.audit_log || []).map((e, i) => (
                      <div key={i} className="text-[11px] flex items-start gap-2 p-1.5 bg-slate-50 rounded">
                        <div className="mt-0.5 h-1.5 w-1.5 rounded-full bg-leamss-teal-500" />
                        <div className="flex-1">
                          <span className="font-medium capitalize">{e.action.replace('_', ' ')}</span>
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
    </div>
  );
}
