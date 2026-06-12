/**
 * Phase 18.7 — Client Errors Admin Dashboard.
 *
 * Route: /admin/client-errors (admin/admin_owner only).
 * Lives next to VerificationHub. Shows:
 *   - 4 KPI counter pills (open / resolved / 24h / critical)
 *   - Filter bar (scope / status / window / search)
 *   - Sortable table (route, message, occurrences, last seen, scope)
 *   - Side drawer with stack trace + Mark Resolved + Notes
 *   - "Channels" tab with notification channel CRUD + test send
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import {
  AlertTriangle, ArrowLeft, BellRing, CheckCircle2, Clock, Copy, Loader2,
  Plus, RefreshCw, Search, ShieldCheck, Slack, Trash2, X, AlertCircle, Mail,
  Activity, Filter, ChevronRight, Send,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const BRAND = {
  forest: '#1F4D44',
  forestDark: '#173B34',
  burnt: '#D4633F',
  warm: '#FAFAF7',
  cream: '#F5F2EC',
};

function relTime(iso) {
  if (!iso) return '—';
  try {
    const t = new Date(iso).getTime();
    if (!t) return '—';
    const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  } catch { return '—'; }
}

const SCOPE_COLOR = {
  sales: 'bg-amber-100 text-amber-800',
  admin: 'bg-violet-100 text-violet-800',
  workspace: 'bg-cyan-100 text-cyan-800',
  partner: 'bg-emerald-100 text-emerald-800',
  portal: 'bg-blue-100 text-blue-800',
  public: 'bg-slate-100 text-slate-700',
  unknown: 'bg-slate-100 text-slate-500',
};

export default function ClientErrorsDashboard() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [tab, setTab] = useState('errors');
  const [summary, setSummary] = useState({ open: 0, resolved: 0, last_24h: 0, critical: 0 });
  const [items, setItems] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [loading, setLoading] = useState(false);
  const [filterScope, setFilterScope] = useState('all');
  const [filterStatus, setFilterStatus] = useState('open');
  const [filterWindow, setFilterWindow] = useState('7d');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerUsers, setDrawerUsers] = useState([]);
  const [notes, setNotes] = useState('');

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(t);
  }, [search]);

  const sinceFromWindow = () => {
    const now = new Date();
    if (filterWindow === '24h') return new Date(now - 24 * 3600 * 1000).toISOString();
    if (filterWindow === '7d') return new Date(now - 7 * 86400 * 1000).toISOString();
    if (filterWindow === '30d') return new Date(now - 30 * 86400 * 1000).toISOString();
    return null;
  };

  const loadAll = async () => {
    setLoading(true);
    try {
      const params = { page, page_size: pageSize };
      if (filterScope !== 'all') params.scope = filterScope;
      if (filterStatus === 'open') params.resolved = false;
      else if (filterStatus === 'resolved') params.resolved = true;
      const since = sinceFromWindow();
      if (since) params.since = since;
      if (debouncedSearch) params.search = debouncedSearch;

      const [sRes, lRes] = await Promise.all([
        axios.get(`${API}/client-errors/summary`, { headers }),
        axios.get(`${API}/client-errors`, { headers, params }),
      ]);
      setSummary(sRes.data);
      setItems(lRes.data.items || []);
      setTotalCount(lRes.data.total_count || 0);
    } catch (e) {
      toast.error('Failed to load client errors');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [page, filterScope, filterStatus, filterWindow, debouncedSearch]);

  // Auto-open drawer when ?id=… in URL
  useEffect(() => {
    const id = searchParams.get('id');
    if (id && !selected) {
      const found = items.find((it) => it.id === id);
      if (found) openDrawer(found);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  const openDrawer = async (it) => {
    setSelected(it);
    setNotes(it.resolution_notes || '');
    setDrawerLoading(true);
    setDrawerUsers([]);
    setSearchParams((p) => { p.set('id', it.id); return p; });
    try {
      const r = await axios.get(`${API}/client-errors/${it.id}/users`, { headers });
      setDrawerUsers(r.data.items || []);
    } catch { /* ignore */ } finally { setDrawerLoading(false); }
  };

  const closeDrawer = () => {
    setSelected(null);
    setNotes('');
    setSearchParams((p) => { p.delete('id'); return p; });
  };

  const markResolved = async (resolved) => {
    if (!selected) return;
    try {
      const r = await axios.patch(`${API}/client-errors/${selected.id}`, { resolved, notes }, { headers });
      toast.success(resolved ? 'Marked resolved' : 'Reopened');
      setSelected(r.data);
      loadAll();
    } catch (e) {
      toast.error('Update failed');
    }
  };

  return (
    <div className="min-h-screen" style={{ background: BRAND.warm }} data-testid="client-errors-dashboard">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between flex-wrap gap-2">
          <div>
            <button onClick={() => navigate('/admin/verify-hub')} className="text-sm text-slate-600 hover:text-slate-900 inline-flex items-center gap-1 mb-1" data-testid="cer-back-btn">
              <ArrowLeft className="h-4 w-4" />Admin Hub
            </button>
            <h1 className="text-xl font-bold flex items-center gap-2" style={{ color: BRAND.forestDark, fontFamily: 'Georgia, serif' }}>
              <Activity className="h-5 w-5" style={{ color: BRAND.burnt }} />
              Client Errors
            </h1>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={loadAll} disabled={loading} data-testid="cer-refresh-btn">
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Counter pills */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <CounterPill label="Open" value={summary.open} testid="error-counter-open" tone={summary.open === 0 ? 'emerald' : summary.open > 10 ? 'rose' : 'amber'} icon={AlertCircle} />
          <CounterPill label="Resolved" value={summary.resolved} testid="error-counter-resolved" tone="slate" icon={CheckCircle2} />
          <CounterPill label="Last 24h" value={summary.last_24h} testid="error-counter-24h" tone="burnt" icon={Clock} />
          <CounterPill label="Critical" value={summary.critical} testid="error-counter-critical" tone="rose" icon={AlertTriangle} />
        </div>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="mb-4" data-testid="cer-tabs">
            <TabsTrigger value="errors" data-testid="cer-tab-errors"><Activity className="h-3.5 w-3.5 mr-1" />Errors</TabsTrigger>
            <TabsTrigger value="channels" data-testid="cer-tab-channels"><BellRing className="h-3.5 w-3.5 mr-1" />Channels</TabsTrigger>
          </TabsList>

          <TabsContent value="errors">
            {/* Filter bar */}
            <Card className="p-3 mb-3 flex flex-wrap items-center gap-2" data-testid="error-filter-bar">
              <Filter className="h-4 w-4 text-slate-400" />
              <Select value={filterScope} onValueChange={setFilterScope}>
                <SelectTrigger className="h-8 w-32 text-[12px]" data-testid="error-filter-scope"><SelectValue placeholder="Scope" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All scopes</SelectItem>
                  <SelectItem value="sales">sales</SelectItem>
                  <SelectItem value="admin">admin</SelectItem>
                  <SelectItem value="workspace">workspace</SelectItem>
                  <SelectItem value="partner">partner</SelectItem>
                  <SelectItem value="portal">portal</SelectItem>
                  <SelectItem value="public">public</SelectItem>
                  <SelectItem value="unknown">unknown</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="h-8 w-32 text-[12px]" data-testid="error-filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="all">All</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterWindow} onValueChange={setFilterWindow}>
                <SelectTrigger className="h-8 w-32 text-[12px]" data-testid="error-filter-date"><SelectValue placeholder="Window" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="24h">Last 24h</SelectItem>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                  <SelectItem value="all">All time</SelectItem>
                </SelectContent>
              </Select>
              <div className="relative flex-1 min-w-[180px]">
                <Search className="h-3.5 w-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input placeholder="Search message…" value={search} onChange={(e) => setSearch(e.target.value)} className="h-8 pl-7 text-[12px]" data-testid="error-filter-search" />
              </div>
              <span className="text-[11px] text-slate-500 ml-auto">{totalCount} result{totalCount !== 1 ? 's' : ''}</span>
            </Card>

            {/* Table */}
            <Card className="overflow-x-auto" data-testid="error-table-card">
              {loading && items.length === 0 ? (
                <div className="p-8 text-center text-slate-500"><Loader2 className="h-5 w-5 mx-auto animate-spin mb-2" />Loading…</div>
              ) : items.length === 0 ? (
                <div className="p-10 text-center" data-testid="error-empty-state">
                  <ShieldCheck className="h-8 w-8 mx-auto text-emerald-400 mb-2" />
                  <p className="text-sm font-semibold text-slate-700">No client errors match your filters</p>
                  <p className="text-[12px] text-slate-500 mt-1">Either the app is healthy or the window is too narrow.</p>
                </div>
              ) : (
                <table className="w-full text-[12px]">
                  <thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="text-left py-2 px-3">Scope</th>
                      <th className="text-left py-2 px-3">Route</th>
                      <th className="text-left py-2 px-3">Message</th>
                      <th className="text-center py-2 px-3">Occ.</th>
                      <th className="text-left py-2 px-3">Last seen</th>
                      <th className="text-left py-2 px-3">Status</th>
                      <th className="py-2 px-3"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it) => (
                      <tr key={it.id} className="border-t border-slate-100 hover:bg-amber-50/40 cursor-pointer" onClick={() => openDrawer(it)} data-testid="error-row">
                        <td className="py-2 px-3"><Badge className={`text-[9px] ${SCOPE_COLOR[it.scope] || SCOPE_COLOR.unknown}`}>{it.scope || 'unknown'}</Badge></td>
                        <td className="py-2 px-3 font-mono text-[11px] text-slate-700 max-w-[14rem] truncate" title={it.route}>{it.route || '—'}</td>
                        <td className="py-2 px-3 max-w-[24rem] truncate text-slate-800" title={it.message}>{it.message}</td>
                        <td className="py-2 px-3 text-center"><Badge className={`text-[10px] ${it.occurrence_count > 10 ? 'bg-rose-500 text-white' : 'bg-slate-200 text-slate-700'}`}>{it.occurrence_count}</Badge></td>
                        <td className="py-2 px-3 text-slate-500">{relTime(it.received_at)}</td>
                        <td className="py-2 px-3">
                          {it.resolved
                            ? <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">Resolved</Badge>
                            : <Badge className="bg-rose-100 text-rose-700 text-[9px]">Open</Badge>}
                        </td>
                        <td className="py-2 px-3"><ChevronRight className="h-3 w-3 text-slate-400" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>

            {/* Pagination */}
            {totalCount > pageSize && (
              <div className="flex items-center justify-between mt-3 text-[11px] text-slate-500" data-testid="error-pagination">
                <span>Page {page} of {Math.max(1, Math.ceil(totalCount / pageSize))}</span>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)} data-testid="error-pagination-prev">Prev</Button>
                  <Button variant="outline" size="sm" disabled={page * pageSize >= totalCount} onClick={() => setPage(p => p + 1)} data-testid="error-pagination-next">Next</Button>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="channels">
            <ChannelsTab headers={headers} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Drawer */}
      {selected && (
        <ErrorDrawer
          err={selected}
          onClose={closeDrawer}
          markResolved={markResolved}
          notes={notes}
          setNotes={setNotes}
          users={drawerUsers}
          loading={drawerLoading}
        />
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Counter Pill
   ════════════════════════════════════════════════════════════════ */
function CounterPill({ label, value, testid, tone, icon: Icon }) {
  const TONES = {
    emerald: { bg: 'bg-emerald-50', border: 'border-l-emerald-500', text: 'text-emerald-700' },
    amber:   { bg: 'bg-amber-50',   border: 'border-l-amber-500',   text: 'text-amber-700' },
    rose:    { bg: 'bg-rose-50',    border: 'border-l-rose-500',    text: 'text-rose-700' },
    burnt:   { bg: 'bg-orange-50',  border: 'border-l-orange-500',  text: 'text-orange-700' },
    slate:   { bg: 'bg-slate-50',   border: 'border-l-slate-400',   text: 'text-slate-700' },
  };
  const t = TONES[tone] || TONES.slate;
  return (
    <Card className={`p-3 border-l-4 ${t.bg} ${t.border}`} data-testid={testid}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500">{label}</p>
          <p className={`text-2xl font-bold ${t.text}`}>{value}</p>
        </div>
        <Icon className={`h-7 w-7 ${t.text} opacity-60`} />
      </div>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════
   Drawer
   ════════════════════════════════════════════════════════════════ */
function ErrorDrawer({ err, onClose, markResolved, notes, setNotes, users, loading }) {
  const copy = () => {
    try {
      navigator.clipboard.writeText(`Message: ${err.message}\nRoute: ${err.route}\nStack:\n${err.stack}\n\nComponent Stack:\n${err.componentStack || ''}`);
      toast.success('Stack copied to clipboard');
    } catch { toast.error('Copy failed'); }
  };
  return (
    <div className="fixed inset-0 z-50 flex" data-testid="error-drawer">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <div className="w-full max-w-xl bg-white shadow-2xl overflow-y-auto" style={{ background: BRAND.cream }}>
        <div className="sticky top-0 z-10 px-4 py-3 border-b border-slate-200 bg-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge className={`text-[9px] ${SCOPE_COLOR[err.scope] || SCOPE_COLOR.unknown}`}>{err.scope || 'unknown'}</Badge>
            <h2 className="font-semibold text-slate-800 text-[14px]" style={{ fontFamily: 'Georgia, serif' }}>Error Detail</h2>
          </div>
          <button onClick={onClose} className="rounded-full p-1 hover:bg-slate-100" data-testid="error-drawer-close" aria-label="Close"><X className="h-4 w-4" /></button>
        </div>
        <div className="p-4 space-y-4">
          {/* Message */}
          <Card className="p-3">
            <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">Message</p>
            <p className="text-[13px] font-mono break-all" data-testid="error-drawer-message">{err.message}</p>
          </Card>

          {/* Route + occurrence + last seen */}
          <div className="grid grid-cols-3 gap-2 text-[11px]">
            <div className="bg-white p-2 rounded border border-slate-100"><p className="text-slate-500">Route</p><p className="font-mono truncate" title={err.route}>{err.route || '—'}</p></div>
            <div className="bg-white p-2 rounded border border-slate-100"><p className="text-slate-500">Occurrences</p><p className="font-bold">{err.occurrence_count}</p></div>
            <div className="bg-white p-2 rounded border border-slate-100"><p className="text-slate-500">Last seen</p><p>{relTime(err.received_at)}</p></div>
          </div>

          {/* Stack */}
          <Card className="p-3">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Stack trace</p>
              <button onClick={copy} className="text-[10px] text-slate-500 hover:text-slate-800 inline-flex items-center gap-1" data-testid="error-drawer-copy"><Copy className="h-3 w-3" />Copy</button>
            </div>
            <pre className="text-[10px] font-mono whitespace-pre-wrap break-all bg-slate-50 p-2 rounded max-h-44 overflow-y-auto" data-testid="error-drawer-stack">{err.stack || '—'}</pre>
          </Card>

          {/* Component stack */}
          {err.componentStack && (
            <Card className="p-3">
              <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">Component stack</p>
              <pre className="text-[10px] font-mono whitespace-pre-wrap break-all bg-slate-50 p-2 rounded max-h-32 overflow-y-auto" data-testid="error-drawer-component-stack">{err.componentStack}</pre>
            </Card>
          )}

          {/* Affected users */}
          <Card className="p-3">
            <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-2">Affected users ({users.length})</p>
            {loading ? <Loader2 className="h-4 w-4 animate-spin text-slate-400" /> :
             users.length === 0 ? <p className="text-[11px] text-slate-400">—</p> :
             <div className="space-y-1 max-h-32 overflow-y-auto" data-testid="error-drawer-users">
               {users.map((u) => (
                 <div key={u.user_id} className="text-[11px] flex items-center justify-between bg-white px-2 py-1 rounded">
                   <span>{u.user_email || u.user_id} <span className="text-slate-400">({u.user_role})</span></span>
                   <span className="text-slate-400">{u.occurrences}x</span>
                 </div>
               ))}
             </div>}
          </Card>

          {/* Notes */}
          <Card className="p-3">
            <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">Resolution notes</p>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Root cause, fix PR link, etc."
              rows={3}
              className="text-[12px]"
              data-testid="error-notes-input"
            />
          </Card>

          {/* Actions */}
          <div className="flex gap-2 sticky bottom-0 bg-white -mx-4 -mb-4 p-3 border-t border-slate-200">
            {err.resolved ? (
              <Button variant="outline" onClick={() => markResolved(false)} className="text-rose-700 border-rose-300" data-testid="error-drawer-unresolve-btn">
                Reopen
              </Button>
            ) : (
              <Button onClick={() => markResolved(true)} className="text-white" style={{ background: BRAND.forest }} data-testid="error-drawer-resolve-btn">
                <CheckCircle2 className="h-4 w-4 mr-1.5" />Mark Resolved
              </Button>
            )}
            <Button variant="outline" onClick={onClose} className="ml-auto">Close</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════
   Channels Tab (Phase 18.7 — notification channels CRUD)
   ════════════════════════════════════════════════════════════════ */
function ChannelsTab({ headers }) {
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ type: 'slack', name: '', target: '', threshold_count: 5, threshold_window_hours: 1, scopes: '' });

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/notification-channels`, { headers });
      setChannels(r.data.items || []);
    } catch { toast.error('Failed to load channels'); } finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const create = async () => {
    if (!form.name.trim() || !form.target.trim()) {
      toast.error('Name + target required');
      return;
    }
    try {
      await axios.post(`${API}/notification-channels`, {
        type: form.type,
        name: form.name.trim(),
        target: form.target.trim(),
        enabled: true,
        threshold_count: Number(form.threshold_count) || 5,
        threshold_window_hours: Number(form.threshold_window_hours) || 1,
        scopes: form.scopes.split(',').map(s => s.trim()).filter(Boolean),
      }, { headers });
      toast.success('Channel created');
      setAdding(false);
      setForm({ type: 'slack', name: '', target: '', threshold_count: 5, threshold_window_hours: 1, scopes: '' });
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Create failed');
    }
  };

  const remove = async (cid) => {
    if (!window.confirm('Delete this channel?')) return;
    try {
      await axios.delete(`${API}/notification-channels/${cid}`, { headers });
      toast.success('Channel deleted');
      load();
    } catch { toast.error('Delete failed'); }
  };

  const toggle = async (ch) => {
    try {
      await axios.patch(`${API}/notification-channels/${ch.id}`, { enabled: !ch.enabled }, { headers });
      load();
    } catch { toast.error('Toggle failed'); }
  };

  const test = async (cid) => {
    try {
      const r = await axios.post(`${API}/notification-channels/${cid}/test`, {}, { headers });
      toast.success(`Test send: ${r.data?.result?.ok ? 'OK' : 'failed'}`);
      load();
    } catch { toast.error('Test send failed'); }
  };

  const runDigest = async () => {
    try {
      const r = await axios.post(`${API}/notification-channels/run-digest-now`, {}, { headers });
      toast.success(`Digest sweep done — sent ${r.data?.alerts_sent ?? 0}, failures ${r.data?.failures ?? 0}`);
    } catch { toast.error('Digest run failed'); }
  };

  return (
    <Card className="p-4" data-testid="channels-tab">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold text-slate-800 text-[15px]" style={{ fontFamily: 'Georgia, serif' }}>Notification channels</h2>
          <p className="text-[11px] text-slate-500 mt-0.5">Slack / Email digest when an error crosses your threshold. Runs every 30 min via APScheduler.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={runDigest} data-testid="channels-run-digest-btn"><Send className="h-3.5 w-3.5 mr-1" />Run digest now</Button>
          <Button size="sm" onClick={() => setAdding(true)} className="text-white" style={{ background: BRAND.burnt }} data-testid="error-add-channel-btn">
            <Plus className="h-3.5 w-3.5 mr-1" />Add channel
          </Button>
        </div>
      </div>

      {/* Add form */}
      {adding && (
        <Card className="p-3 mb-3 border-l-4 border-l-orange-400 bg-orange-50/30" data-testid="channels-add-form">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
              <SelectTrigger className="h-9 text-[12px]" data-testid="channel-form-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="slack">Slack webhook</SelectItem>
                <SelectItem value="email">Email</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Name (e.g. Ops Alerts)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="h-9 text-[12px]" data-testid="channel-form-name" />
            <Input placeholder={form.type === 'slack' ? 'https://hooks.slack.com/services/...' : 'admin@leamss.com,ops@leamss.com'} value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} className="h-9 text-[12px] col-span-2" data-testid="channel-form-target" />
            <Input type="number" min={1} placeholder="Threshold count" value={form.threshold_count} onChange={(e) => setForm({ ...form, threshold_count: e.target.value })} className="h-9 text-[12px]" data-testid="channel-form-threshold-count" />
            <Input type="number" min={1} placeholder="Window (hours)" value={form.threshold_window_hours} onChange={(e) => setForm({ ...form, threshold_window_hours: e.target.value })} className="h-9 text-[12px]" data-testid="channel-form-window-hours" />
            <Input placeholder="Scopes (comma) e.g. sales,admin" value={form.scopes} onChange={(e) => setForm({ ...form, scopes: e.target.value })} className="h-9 text-[12px] col-span-2" data-testid="channel-form-scopes" />
          </div>
          <div className="flex gap-2 mt-2">
            <Button size="sm" onClick={create} className="text-white" style={{ background: BRAND.forest }} data-testid="channel-form-submit">Create</Button>
            <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {/* List */}
      {loading ? (
        <div className="p-6 text-center text-slate-500"><Loader2 className="h-5 w-5 mx-auto animate-spin" /></div>
      ) : channels.length === 0 ? (
        <div className="p-6 text-center text-[12px] text-slate-500" data-testid="channels-empty">No channels yet. Add one to start receiving alerts.</div>
      ) : (
        <div className="space-y-2" data-testid="channels-list">
          {channels.map((ch) => (
            <div key={ch.id} className="flex items-center gap-2 bg-white border border-slate-200 rounded p-2" data-testid={`channel-row-${ch.id}`}>
              {ch.type === 'slack' ? <Slack className="h-4 w-4 text-violet-600" /> : <Mail className="h-4 w-4 text-blue-600" />}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-[13px]">{ch.name}</span>
                  <Badge className={`text-[9px] ${ch.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-500'}`}>{ch.enabled ? 'enabled' : 'disabled'}</Badge>
                </div>
                <p className="text-[10px] text-slate-500 truncate font-mono" title={ch.target}>{ch.target}</p>
                <p className="text-[10px] text-slate-400">threshold ≥ {ch.threshold_count} in {ch.threshold_window_hours}h{ch.scopes?.length ? ` · scopes: ${ch.scopes.join(', ')}` : ''}{ch.last_test_result ? ` · last test: ${ch.last_test_result}` : ''}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => test(ch.id)} className="text-[11px]" data-testid={`channel-test-${ch.id}`}><Send className="h-3 w-3 mr-1" />Test</Button>
              <Button variant="outline" size="sm" onClick={() => toggle(ch)} className="text-[11px]">{ch.enabled ? 'Disable' : 'Enable'}</Button>
              <Button variant="ghost" size="sm" onClick={() => remove(ch.id)} className="text-rose-600"><Trash2 className="h-3.5 w-3.5" /></Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
