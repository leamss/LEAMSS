import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Link2, RefreshCw, Search, Shield, ShieldAlert, ShieldCheck,
  Eye, X, Clock, CheckCircle2, AlertTriangle, Copy, ExternalLink, Ban
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_STYLES = {
  active: { c: 'bg-emerald-50 border-emerald-200 text-emerald-700', label: 'Active', icon: ShieldCheck },
  expired: { c: 'bg-amber-50 border-amber-200 text-amber-700', label: 'Expired', icon: Clock },
  revoked: { c: 'bg-rose-50 border-rose-200 text-rose-700', label: 'Revoked', icon: Ban },
  consumed: { c: 'bg-slate-50 border-slate-200 text-slate-600', label: 'Used', icon: CheckCircle2 },
  deactivated: { c: 'bg-slate-50 border-slate-200 text-slate-600', label: 'Inactive', icon: X },
};

export default function ShareLinksDashboard() {
  const [data, setData] = useState({ items: [], stats: {}, count: 0 });
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [confirmRevoke, setConfirmRevoke] = useState(null);
  const [revokeReason, setRevokeReason] = useState('');

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set('status', statusFilter);
      if (typeFilter) params.set('link_type', typeFilter);
      if (search) params.set('search', search);
      const r = await axios.get(`${API}/share-links/?${params.toString()}`, auth());
      setData(r.data);
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to load'); }
    setLoading(false);
  }, [statusFilter, typeFilter, search]);

  useEffect(() => { load(); }, [load]);

  const doRevoke = async () => {
    if (!confirmRevoke) return;
    try {
      await axios.post(`${API}/share-links/revoke`, {
        type: confirmRevoke.type,
        token: confirmRevoke.token,
        reason: revokeReason || null,
      }, auth());
      toast.success('Link revoked — client can no longer access this URL');
      setConfirmRevoke(null);
      setRevokeReason('');
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Revoke failed'); }
  };

  const fullUrl = (item) => {
    const base = window.location.origin;
    if (item.type === 'public_pa_fee') return `${base}/pre-assess/${item.token}`;
    if (item.type === 'sales_report') return `${base}/sales/report/${item.token}`;
    return `${base}/magic/${item.token}`;
  };

  const copyLink = (item) => {
    navigator.clipboard.writeText(fullUrl(item));
    toast.success('Link copied');
  };

  const fmtDate = (iso) => {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }); }
    catch { return iso; }
  };

  return (
    <Card className="p-5 border-l-4 border-l-indigo-500" data-testid="share-links-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-4 flex-wrap">
        <div className="flex items-center gap-2.5">
          <Link2 className="h-5 w-5 text-indigo-600" />
          <div>
            <p className="font-semibold text-slate-800">Active Share Links</p>
            <p className="text-[11px] text-slate-500">Audit, monitor, and revoke any client-facing link</p>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading} data-testid="sl-refresh">
          <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-4">
        {['active', 'expired', 'consumed', 'revoked', 'deactivated'].map(k => {
          const s = STATUS_STYLES[k];
          const Ic = s.icon;
          const count = data.stats[k] || 0;
          return (
            <button key={k}
              onClick={() => setStatusFilter(statusFilter === k ? '' : k)}
              className={`p-2 rounded border text-left transition ${s.c} ${statusFilter === k ? 'ring-2 ring-offset-1 ring-indigo-400' : ''}`}
              data-testid={`sl-stat-${k}`}>
              <div className="flex items-center gap-1.5">
                <Ic className="h-3.5 w-3.5" />
                <p className="text-[10px] uppercase font-semibold tracking-wide">{s.label}</p>
              </div>
              <p className="text-xl font-bold mt-1">{count}</p>
            </button>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search PA / client / email…" className="pl-8 h-8 text-xs" data-testid="sl-search" />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="border border-slate-200 rounded-md px-2 py-1 text-xs h-8 bg-white" data-testid="sl-type-filter">
          <option value="">All Types</option>
          <option value="public_pa_fee">Public · PA Fee</option>
          <option value="magic_portal">Magic · Portal</option>
          <option value="sales_report">Sales · Report</option>
        </select>
        {(statusFilter || typeFilter || search) && (
          <Button size="sm" variant="ghost" onClick={() => { setStatusFilter(''); setTypeFilter(''); setSearch(''); }} className="h-8 text-xs">
            Clear
          </Button>
        )}
      </div>

      {/* Table */}
      {data.items.length === 0 ? (
        <p className="text-center py-8 text-sm text-slate-400">{loading ? 'Loading…' : 'No share links match the filter.'}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="bg-slate-50 text-slate-600 sticky top-0">
              <tr>
                <th className="px-2 py-2 text-left">Status</th>
                <th className="px-2 py-2 text-left">PA / Client</th>
                <th className="px-2 py-2 text-left">Type · Purpose</th>
                <th className="px-2 py-2 text-left">Token</th>
                <th className="px-2 py-2 text-left">Issued</th>
                <th className="px-2 py-2 text-left">Expires</th>
                <th className="px-2 py-2 text-center">Clicks</th>
                <th className="px-2 py-2 text-left">Last Access</th>
                <th className="px-2 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map(item => {
                const s = STATUS_STYLES[item.status] || STATUS_STYLES.active;
                const Ic = s.icon;
                return (
                  <tr key={item.token} className={`hover:bg-slate-50 ${item.suspicious ? 'bg-amber-50/50' : ''}`} data-testid={`sl-row-${item.token.slice(0,10)}`}>
                    <td className="px-2 py-2">
                      <Badge className={`${s.c} border text-[10px]`}><Ic className="h-3 w-3 mr-0.5" /> {s.label}</Badge>
                      {item.suspicious && <Badge className="ml-1 bg-amber-100 text-amber-800 border-amber-300 text-[10px]"><AlertTriangle className="h-3 w-3 mr-0.5" />Suspect</Badge>}
                    </td>
                    <td className="px-2 py-2">
                      <p className="font-mono text-[10px] text-slate-500">{item.pa_number || '—'}</p>
                      <p className="font-semibold text-slate-800">{item.client_name || '—'}</p>
                      <p className="text-[10px] text-slate-500">{item.client_email || ''}</p>
                    </td>
                    <td className="px-2 py-2">
                      <p className="font-semibold text-slate-700">
                        {item.type === 'public_pa_fee' && '📨 Public'}
                        {item.type === 'magic_portal' && '🔑 Magic'}
                        {item.type === 'sales_report' && '📊 Sales Report'}
                      </p>
                      <p className="text-[10px] text-slate-500 capitalize">{item.purpose.replace(/_/g, ' ')}</p>
                      <p className="text-[10px] font-semibold text-emerald-700">{item.amount_label}</p>
                    </td>
                    <td className="px-2 py-2 font-mono text-[10px] text-slate-600">{item.token_prefix}</td>
                    <td className="px-2 py-2 text-[11px] text-slate-600">{fmtDate(item.issued_at)}</td>
                    <td className="px-2 py-2 text-[11px] text-slate-600">{item.expires_at ? fmtDate(item.expires_at) : <span className="text-rose-700 font-semibold">Never</span>}</td>
                    <td className="px-2 py-2 text-center font-bold text-slate-800">{item.access_count || 0}</td>
                    <td className="px-2 py-2 text-[10px] text-slate-500">
                      {item.last_accessed_at ? (
                        <>
                          <p>{fmtDate(item.last_accessed_at)}</p>
                          {item.last_accessed_ip && <p className="font-mono">{item.last_accessed_ip}</p>}
                        </>
                      ) : '—'}
                    </td>
                    <td className="px-2 py-2 text-right">
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="ghost" onClick={() => copyLink(item)} title="Copy URL" className="h-7 w-7 p-0">
                          <Copy className="h-3 w-3" />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => window.open(fullUrl(item), '_blank')} title="Open" className="h-7 w-7 p-0">
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                        {item.status === 'active' && (
                          <Button size="sm" variant="ghost" onClick={() => setConfirmRevoke(item)} title="Revoke" className="h-7 w-7 p-0 text-rose-600 hover:bg-rose-50" data-testid={`sl-revoke-${item.token.slice(0,10)}`}>
                            <Ban className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Revoke Confirm Dialog */}
      {confirmRevoke && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setConfirmRevoke(null)} data-testid="sl-revoke-dialog">
          <div className="bg-white rounded-xl max-w-md w-full overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b bg-rose-50 flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-rose-600" />
              <p className="font-bold text-rose-900">Revoke Share Link</p>
            </div>
            <div className="p-5 space-y-3">
              <div className="bg-slate-50 border rounded p-3 text-xs">
                <p className="font-semibold text-slate-700 mb-0.5">{confirmRevoke.client_name}</p>
                <p className="text-slate-500">{confirmRevoke.pa_number} · {confirmRevoke.amount_label}</p>
                <p className="font-mono text-[10px] text-slate-400 mt-1">{confirmRevoke.token_prefix}</p>
              </div>
              <p className="text-xs text-slate-600">
                Once revoked, the client will see <strong>"Link Unavailable"</strong> when accessing this URL.
                This action is logged in the audit trail and <strong>cannot be undone</strong>.
              </p>
              <div>
                <label className="text-xs font-medium text-slate-600 block mb-1">Reason (recommended)</label>
                <Input value={revokeReason} onChange={e => setRevokeReason(e.target.value)} placeholder="e.g. Suspicious access pattern · Client requested · Fraud suspicion" data-testid="sl-revoke-reason" />
              </div>
            </div>
            <div className="p-4 border-t bg-slate-50 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setConfirmRevoke(null)}>Cancel</Button>
              <Button onClick={doRevoke} className="bg-rose-600 hover:bg-rose-700 text-white" data-testid="sl-confirm-revoke">
                <Ban className="h-4 w-4 mr-1" /> Revoke Permanently
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
