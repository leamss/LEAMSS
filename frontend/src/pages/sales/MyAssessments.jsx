/**
 * Smart Sales Helper — Phase 6.8.2
 * My Saved Assessments — list view of `sales_assessments` collection.
 *
 * Route: /sales/my-assessments
 *
 * Admin → sees all assessments (across users)
 * Sales/Partner → sees only their own (filtered by created_by)
 *
 * Status pills:
 *   • Linked-PA → already converted to a Pre-Assessment
 *   • Shared    → public share link is active
 *   • Saved     → assessment created but no PA / share yet
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  ArrowLeft, Search, FileText, Sparkles, Trash2, Briefcase, Share2,
  CheckCircle2, Loader2, AlertTriangle, ExternalLink, RefreshCw, Play,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;


export default function MyAssessments() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const me = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  }, []);
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);
  const isAdmin = ['admin', 'admin_owner'].includes(me.rbac_role || me.role);

  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [status, setStatus] = useState('all');
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [partners, setPartners] = useState([]);
  const [paPickerFor, setPaPickerFor] = useState(null);
  const [selectedPartner, setSelectedPartner] = useState('');

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 250);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (debounced) params.append('search', debounced);
      params.append('limit', '100');
      const r = await axios.get(`${API}/sales/assessments?${params}`, { headers });
      setItems(r.data.items || []);
      setCount(r.data.count || 0);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load assessments'));
    } finally {
      setLoading(false);
    }
  }, [debounced, headers]);

  useEffect(() => { load(); }, [load]);

  // Load partners once for admin's PA picker
  useEffect(() => {
    if (!isAdmin) return;
    axios.get(`${API}/sales/assessments/partner-options`, { headers })
      .then(r => setPartners(r.data.items || []))
      .catch(() => setPartners([]));
  }, [isAdmin, headers]);

  const filtered = useMemo(() => {
    if (status === 'all') return items;
    if (status === 'linked') return items.filter(i => !!i.linked_pa_id);
    if (status === 'shared') return items.filter(i => i.share_active && i.share_token);
    if (status === 'saved') return items.filter(i => !i.linked_pa_id && !(i.share_active && i.share_token));
    return items;
  }, [items, status]);

  const onDelete = async (id) => {
    if (!window.confirm('Delete this saved assessment? This cannot be undone.')) return;
    setBusyId(id);
    try {
      await axios.delete(`${API}/sales/assessments/${id}`, { headers });
      toast.success('Assessment deleted');
      setItems(prev => prev.filter(p => p.id !== id));
    } catch (e) {
      toast.error(formatApiError(e, 'Delete failed'));
    } finally {
      setBusyId(null);
    }
  };

  const onCreatePA = (assessmentId) => {
    if (isAdmin) {
      setSelectedPartner('');
      setPaPickerFor(assessmentId);
    } else {
      doCreatePA(assessmentId, null);
    }
  };

  const onContinue = async (assessmentId) => {
    setBusyId(assessmentId);
    try {
      const r = await axios.get(`${API}/sales/assessments/${assessmentId}`, { headers });
      sessionStorage.setItem('resume_assessment', JSON.stringify(r.data));
      navigate('/sales/client-assessment');
    } catch (e) {
      toast.error(formatApiError(e, 'Could not load assessment'));
    } finally {
      setBusyId(null);
    }
  };

  const doCreatePA = async (assessmentId, partnerId) => {
    setBusyId(assessmentId);
    try {
      const body = { lead_source: 'smart_sales_helper' };
      if (partnerId) body.partner_id = partnerId;
      const r = await axios.post(`${API}/sales/assessments/${assessmentId}/create-pa`, body, { headers });
      toast.success(`Pre-Assessment created: ${r.data.pa_number || r.data.pa_id}`, { duration: 6000 });
      setPaPickerFor(null);
      load();
    } catch (e) {
      toast.error(formatApiError(e, 'PA creation failed'));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="my-assessments-page">
      <div className="max-w-6xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate(-1)} data-testid="back-btn">
              <ArrowLeft className="h-4 w-4 mr-1" />Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <FileText className="h-7 w-7 text-indigo-600" />
                {isAdmin ? 'All Saved Assessments' : 'My Saved Assessments'}
              </h1>
              <p className="text-sm text-slate-500">
                {isAdmin ? 'All sales assessments across users' : 'Your saved Smart Sales Helper assessments'}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn">
              <RefreshCw className="h-4 w-4 mr-1" />Refresh
            </Button>
            <Button size="sm" onClick={() => navigate('/sales/client-assessment')} className="bg-indigo-600" data-testid="new-assessment-btn">
              <Sparkles className="h-4 w-4 mr-1" />New Assessment
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card className="p-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search by client name…"
                className="pl-9 h-9"
                data-testid="search-input"
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-44 h-9" data-testid="status-filter"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All ({items.length})</SelectItem>
                <SelectItem value="saved">Saved only</SelectItem>
                <SelectItem value="linked">Linked to PA</SelectItem>
                <SelectItem value="shared">Has shared link</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-slate-500">
              <strong>{filtered.length}</strong> of <strong>{count}</strong> {count === 1 ? 'assessment' : 'assessments'}
            </p>
          </div>
        </Card>

        {/* List */}
        {loading ? (
          <Card className="p-10 text-center text-slate-400" data-testid="loading-state">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
            <p className="text-sm">Loading…</p>
          </Card>
        ) : filtered.length === 0 ? (
          <Card className="p-10 text-center text-slate-400" data-testid="empty-state">
            <FileText className="h-10 w-10 mx-auto mb-2 opacity-40" />
            <p className="font-medium">No assessments yet</p>
            <p className="text-xs mt-1">
              {debounced
                ? 'No matches for your search.'
                : 'Click "New Assessment" to start your first Smart Sales Helper workflow.'}
            </p>
          </Card>
        ) : (
          <div className="space-y-2" data-testid="assessments-list">
            {filtered.map(a => <AssessmentRow
              key={a.id}
              item={a}
              isAdmin={isAdmin}
              busy={busyId === a.id}
              onDelete={onDelete}
              onCreatePA={onCreatePA}
              onContinue={onContinue}
            />)}
          </div>
        )}

        {/* Partner picker modal (Admin only) */}
        {paPickerFor && (
          <PartnerPickerModal
            partners={partners}
            selected={selectedPartner}
            setSelected={setSelectedPartner}
            onCancel={() => setPaPickerFor(null)}
            onConfirm={() => {
              if (!selectedPartner) { toast.error('Pick a partner first'); return; }
              doCreatePA(paPickerFor, selectedPartner);
            }}
          />
        )}
      </div>
    </div>
  );
}


function AssessmentRow({ item, isAdmin, busy, onDelete, onCreatePA, onContinue }) {
  const navigate = useNavigate();
  const linked = !!item.linked_pa_id;
  const shared = !!(item.share_active && item.share_token);
  const total = item.best_total;
  const country = item.best_country_code;
  const dateStr = item.created_at
    ? new Date(item.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    : '—';

  return (
    <Card className="p-3 hover:shadow-md transition" data-testid={`assessment-row-${item.id}`}>
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="flex-1 min-w-[260px]">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-bold text-slate-900" data-testid={`client-name-${item.id}`}>
              {item.client_name || 'Unnamed client'}
            </p>
            {linked && (
              <Badge className="bg-emerald-100 text-emerald-700 text-[9px]" data-testid={`badge-linked-${item.id}`}>
                <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" />Linked-PA
              </Badge>
            )}
            {shared && (
              <Badge className="bg-blue-100 text-blue-700 text-[9px]" data-testid={`badge-shared-${item.id}`}>
                <Share2 className="h-2.5 w-2.5 mr-0.5" />Shared
              </Badge>
            )}
            {!linked && !shared && (
              <Badge className="bg-slate-100 text-slate-600 text-[9px]" data-testid={`badge-saved-${item.id}`}>Saved</Badge>
            )}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5 truncate">
            {item.client_email || '—'} · {item.client_phone || '—'}
          </p>
          {isAdmin && item.created_by_name && (
            <p className="text-[10px] text-slate-400 mt-0.5 italic">
              by {item.created_by_name}
            </p>
          )}
          <p className="text-[10px] text-slate-400 mt-0.5">{dateStr} · {item.id}</p>
        </div>

        {/* Score */}
        <div className="text-center">
          <p className="text-[9px] uppercase font-bold text-slate-500">Best</p>
          <p className="text-2xl font-bold text-indigo-700" data-testid={`score-${item.id}`}>{total ?? '—'}</p>
          <p className="text-[10px] text-slate-500">{country || '—'}</p>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-1">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] border-indigo-300 text-indigo-700 hover:bg-indigo-50"
            disabled={busy}
            onClick={() => onContinue(item.id)}
            data-testid={`continue-${item.id}`}
          >
            {busy ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Play className="h-3 w-3 mr-1" />}
            Continue
          </Button>
          {shared && (
            <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => window.open(`/sales/report/${item.share_token}`, '_blank')} data-testid={`view-shared-${item.id}`}>
              <ExternalLink className="h-3 w-3 mr-1" />Public link
            </Button>
          )}
          {!linked && (
            <Button
              size="sm"
              className="h-7 text-[10px] bg-indigo-600 hover:bg-indigo-700"
              disabled={busy}
              onClick={() => onCreatePA(item.id)}
              data-testid={`create-pa-${item.id}`}
            >
              {busy ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Briefcase className="h-3 w-3 mr-1" />}
              Create PA
            </Button>
          )}
          {linked && (
            <Badge className="bg-emerald-50 text-emerald-700 text-[9px] justify-center">PA: {item.linked_pa_id?.slice(0, 8)}…</Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] text-rose-700 hover:bg-rose-50"
            disabled={busy}
            onClick={() => onDelete(item.id)}
            data-testid={`delete-${item.id}`}
          >
            <Trash2 className="h-3 w-3 mr-1" />Delete
          </Button>
        </div>
      </div>
    </Card>
  );
}


function PartnerPickerModal({ partners, selected, setSelected, onCancel, onConfirm }) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="partner-picker-modal">
      <Card className="bg-white p-5 max-w-md w-full">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <h3 className="text-base font-bold">Assign to Partner / Sales</h3>
        </div>
        <p className="text-xs text-slate-600 mb-3">
          Admin-initiated PAs must be assigned to a Partner or Sales person so they appear in their pipeline.
        </p>
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger data-testid="partner-select"><SelectValue placeholder="Pick a partner…" /></SelectTrigger>
          <SelectContent className="max-h-64 overflow-y-auto">
            {partners.map(p => (
              <SelectItem key={p.id} value={p.id}>
                {p.name || p.email} <span className="text-[10px] text-slate-400 ml-1">· {p.role}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex gap-2 mt-4">
          <Button variant="outline" onClick={onCancel} className="flex-1" data-testid="picker-cancel">Cancel</Button>
          <Button onClick={onConfirm} disabled={!selected} className="flex-1 bg-indigo-600" data-testid="picker-confirm">Create PA</Button>
        </div>
      </Card>
    </div>
  );
}
