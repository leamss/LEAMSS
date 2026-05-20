import { useEffect, useState, useCallback, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Link2, RefreshCw, Search, Shield, ShieldAlert, ShieldCheck,
  Eye, X, Clock, CheckCircle2, AlertTriangle, Copy, ExternalLink, Ban,
  History, Send, Bot, Loader2, Download, Flame,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_STYLES = {
  active: { c: 'bg-emerald-50 border-emerald-200 text-emerald-700', label: 'Active', icon: ShieldCheck },
  expired: { c: 'bg-amber-50 border-amber-200 text-amber-700', label: 'Expired', icon: Clock },
  revoked: { c: 'bg-rose-50 border-rose-200 text-rose-700', label: 'Revoked', icon: Ban },
  consumed: { c: 'bg-slate-50 border-slate-200 text-slate-600', label: 'Used', icon: CheckCircle2 },
  deactivated: { c: 'bg-slate-50 border-slate-200 text-slate-600', label: 'Inactive', icon: X },
};

const EVENT_STYLES = {
  share_generated: { label: 'Link Generated', icon: Send, dot: 'bg-emerald-100 border-emerald-500 text-emerald-700', card: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-800' },
  share_accessed: { label: 'Public Access', icon: Eye, dot: 'bg-indigo-100 border-indigo-500 text-indigo-700', card: 'bg-indigo-50 border-indigo-200', text: 'text-indigo-800' },
  share_revoked: { label: 'Link Revoked', icon: Ban, dot: 'bg-rose-100 border-rose-500 text-rose-700', card: 'bg-rose-50 border-rose-200', text: 'text-rose-800' },
  share_emailed: { label: 'Emailed to Client', icon: Bot, dot: 'bg-amber-100 border-amber-500 text-amber-700', card: 'bg-amber-50 border-amber-200', text: 'text-amber-800' },
  default: { label: 'Event', icon: AlertTriangle, dot: 'bg-slate-100 border-slate-500 text-slate-700', card: 'bg-slate-50 border-slate-200', text: 'text-slate-700' },
};

export default function ShareLinksDashboard() {
  const [data, setData] = useState({ items: [], stats: {}, count: 0 });
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [confirmRevoke, setConfirmRevoke] = useState(null);
  const [revokeReason, setRevokeReason] = useState('');
  // Audit trail modal state
  const [auditModalItem, setAuditModalItem] = useState(null);
  const [auditEvents, setAuditEvents] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);
  // Anomaly summary (auto-loads with main dashboard)
  const [anomalyData, setAnomalyData] = useState(null);
  const [showAnomalyPanel, setShowAnomalyPanel] = useState(false);

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const openAuditTrail = async (item) => {
    setAuditModalItem(item);
    setAuditEvents(null);
    setAuditLoading(true);
    try {
      const r = await axios.get(`${API}/share-links/${item.token}/audit-trail`, auth());
      setAuditEvents(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load audit trail');
      setAuditModalItem(null);
    } finally { setAuditLoading(false); }
  };

  const downloadAuditPdf = async (token) => {
    try {
      const r = await axios.get(`${API}/share-links/${token}/audit-trail.pdf`, {
        ...auth(),
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_${token.slice(0, 10)}_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Audit report downloaded');
    } catch {
      toast.error('PDF generation failed');
    }
  };

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

  // Load anomaly summary in parallel — admin-level health indicator
  useEffect(() => {
    axios.get(`${API}/share-links/anomalies?since_hours=24`, auth())
      .then(r => setAnomalyData(r.data))
      .catch(() => setAnomalyData(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Map share_token → top anomaly severity for per-row indicator
  const anomalyByToken = useMemo(() => {
    if (!anomalyData?.anomalies) return {};
    return anomalyData.anomalies.reduce((acc, a) => {
      acc[a.share_token] = a;
      return acc;
    }, {});
  }, [anomalyData]);

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

      {/* Anomaly Alert Banner */}
      {anomalyData && (anomalyData.summary.high + anomalyData.summary.medium) > 0 && (
        <div className={`mb-4 p-3 rounded border-l-4 ${
          anomalyData.summary.high > 0 ? 'bg-rose-50 border-l-rose-500' : 'bg-amber-50 border-l-amber-500'
        }`} data-testid="anomaly-banner">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Flame className={`h-4 w-4 ${anomalyData.summary.high > 0 ? 'text-rose-600' : 'text-amber-600'}`} />
              <p className="text-xs font-bold">
                {anomalyData.summary.high > 0 && `🔥 ${anomalyData.summary.high} HIGH severity · `}
                {anomalyData.summary.medium > 0 && `${anomalyData.summary.medium} medium · `}
                {anomalyData.summary.low > 0 && `${anomalyData.summary.low} low · `}
                anomalies detected in the last 24 hours
              </p>
            </div>
            <Button size="sm" variant="outline" onClick={() => setShowAnomalyPanel(v => !v)} className="text-[11px] h-7" data-testid="toggle-anomaly-panel">
              {showAnomalyPanel ? 'Hide Details' : 'View Details'}
            </Button>
          </div>
          {showAnomalyPanel && (
            <div className="mt-3 space-y-1.5">
              {anomalyData.anomalies.slice(0, 10).map(a => (
                <div key={a.share_token} className="bg-white/70 rounded p-2 text-[11px] flex items-center justify-between gap-2" data-testid={`anomaly-row-${a.share_token.slice(0,10)}`}>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-700 truncate">
                      <span className={a.severity === 'high' ? 'text-rose-700' : 'text-amber-700'}>[{a.severity.toUpperCase()}]</span>
                      {' '}{a.client_name || '—'} · <code className="font-mono">{a.token_prefix}</code>
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {a.flags.map(f => f.type.replace(/_/g, ' ')).join(' · ')}
                    </p>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => {
                    const item = data.items.find(it => it.token === a.share_token);
                    if (item) openAuditTrail(item);
                  }} className="h-6 text-[10px] px-2" data-testid={`investigate-${a.share_token.slice(0,10)}`}>
                    Investigate
                  </Button>
                </div>
              ))}
              {anomalyData.anomalies.length > 10 && (
                <p className="text-[10px] text-slate-500 italic text-center">+ {anomalyData.anomalies.length - 10} more</p>
              )}
            </div>
          )}
        </div>
      )}

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
                      <div className="flex items-center gap-1">
                        <p className="font-mono text-[10px] text-slate-500">{item.pa_number || '—'}</p>
                        {anomalyByToken[item.token] && (
                          <Badge className={`text-[9px] py-0 px-1 ${
                            anomalyByToken[item.token].severity === 'high' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'
                          }`} title={`${anomalyByToken[item.token].flags.length} anomaly flag(s)`} data-testid={`anomaly-flag-${item.token.slice(0,10)}`}>
                            <Flame className="h-2.5 w-2.5 mr-0.5" />{anomalyByToken[item.token].severity}
                          </Badge>
                        )}
                      </div>
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
                        <Button size="sm" variant="ghost" onClick={() => openAuditTrail(item)} title="Audit Trail" className="h-7 w-7 p-0 text-indigo-600 hover:bg-indigo-50" data-testid={`sl-audit-${item.token.slice(0,10)}`}>
                          <History className="h-3 w-3" />
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

      {/* Audit Trail Modal */}
      {auditModalItem && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setAuditModalItem(null)} data-testid="sl-audit-modal">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b bg-indigo-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-indigo-600" />
                <div>
                  <p className="font-bold text-indigo-900">Audit Trail</p>
                  <p className="text-[10px] text-slate-600 font-mono">{auditModalItem.token_prefix}</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Button variant="outline" size="sm" onClick={() => downloadAuditPdf(auditModalItem.token)} className="h-7 text-[11px]" data-testid="audit-pdf-btn">
                  <Download className="h-3 w-3 mr-1" />Export PDF
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setAuditModalItem(null)} className="h-7 w-7 p-0">
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="p-4 overflow-y-auto flex-1">
              <div className="bg-slate-50 border rounded p-3 mb-3 text-xs">
                <p className="font-semibold text-slate-700 mb-0.5">{auditModalItem.client_name}</p>
                <p className="text-slate-500">{auditModalItem.pa_number || auditModalItem.sales_assessment_id} · {auditModalItem.amount_label}</p>
              </div>

              {auditLoading ? (
                <div className="flex items-center justify-center py-12 text-slate-400">
                  <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading audit trail…
                </div>
              ) : auditEvents && auditEvents.events.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-xs italic">
                  No audit events recorded for this token yet.
                </div>
              ) : auditEvents ? (
                <>
                  <div className="grid grid-cols-3 gap-2 mb-4 text-center">
                    <div className="bg-emerald-50 border border-emerald-200 rounded p-2">
                      <p className="text-[9px] uppercase font-bold text-emerald-700">Total Events</p>
                      <p className="text-lg font-bold text-emerald-900">{auditEvents.count}</p>
                    </div>
                    <div className="bg-indigo-50 border border-indigo-200 rounded p-2">
                      <p className="text-[9px] uppercase font-bold text-indigo-700">Public Accesses</p>
                      <p className="text-lg font-bold text-indigo-900">{auditEvents.access_count}</p>
                    </div>
                    <div className={`${auditEvents.revoked ? 'bg-rose-50 border-rose-200' : 'bg-slate-50 border-slate-200'} border rounded p-2`}>
                      <p className={`text-[9px] uppercase font-bold ${auditEvents.revoked ? 'text-rose-700' : 'text-slate-500'}`}>Status</p>
                      <p className={`text-lg font-bold ${auditEvents.revoked ? 'text-rose-900' : 'text-slate-700'}`}>{auditEvents.revoked ? 'Revoked' : 'Active'}</p>
                    </div>
                  </div>

                  {/* Anomaly section — only if flagged */}
                  {auditEvents.anomalies && auditEvents.anomalies.length > 0 && (
                    <div className={`mb-4 p-3 rounded border-l-4 ${
                      auditEvents.anomaly_severity === 'high' ? 'bg-rose-50 border-l-rose-500'
                      : auditEvents.anomaly_severity === 'medium' ? 'bg-amber-50 border-l-amber-500'
                      : 'bg-yellow-50 border-l-yellow-400'
                    }`} data-testid="audit-anomalies">
                      <div className="flex items-center gap-2 mb-2">
                        <Flame className={`h-4 w-4 ${auditEvents.anomaly_severity === 'high' ? 'text-rose-600' : 'text-amber-600'}`} />
                        <p className="text-xs font-bold uppercase">
                          Anomalies Detected · Severity: <span className={auditEvents.anomaly_severity === 'high' ? 'text-rose-700' : 'text-amber-700'}>{auditEvents.anomaly_severity}</span>
                        </p>
                      </div>
                      <div className="space-y-1.5">
                        {auditEvents.anomalies.map((flag, i) => (
                          <div key={`${flag.type}-${i}`} className="text-[11px] bg-white/60 rounded p-2" data-testid={`anomaly-${flag.type}`}>
                            <p className="font-semibold text-slate-700">
                              {flag.type === 'rapid_burst' && `🔥 Rapid Burst: ${flag.count} accesses in ${flag.window_hours} hour(s)`}
                              {flag.type === 'multiple_ips' && `🌐 Multiple IPs: ${flag.count} distinct IPs in ${flag.window_minutes} min`}
                              {flag.type === 'post_revoke_scrape' && `🚫 Post-Revoke Scraping: ${flag.count} denied attempts after revoke`}
                              {flag.type === 'expired_hammering' && `⏰ Expired Hammering: ${flag.count} hits on expired link`}
                              {flag.type === 'bot_pattern' && `🤖 Bot Pattern: same UA across ${flag.distinct_tokens} tokens`}
                            </p>
                            {flag.ips_sample && flag.ips_sample.length > 0 && (
                              <p className="text-[10px] text-slate-500 mt-0.5 font-mono">IPs: {flag.ips_sample.slice(0, 4).join(', ')}</p>
                            )}
                            {flag.user_agent && (
                              <p className="text-[10px] text-slate-500 mt-0.5 font-mono break-all">{flag.user_agent}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">Timeline</p>
                  <div className="relative pl-5 border-l-2 border-slate-200 space-y-3" data-testid="audit-timeline">
                    {auditEvents.events.map(ev => {
                      const styles = EVENT_STYLES[ev.event_type] || EVENT_STYLES.default;
                      const Icon = styles.icon;
                      return (
                        <div key={ev.id} className="relative" data-testid={`audit-event-${ev.event_type}`}>
                          <div className={`absolute -left-7 top-0 h-5 w-5 rounded-full border-2 flex items-center justify-center ${styles.dot}`}>
                            <Icon className="h-3 w-3" />
                          </div>
                          <div className={`rounded border p-2 text-xs ${styles.card}`}>
                            <div className="flex items-center justify-between mb-1">
                              <p className={`font-bold ${styles.text}`}>{styles.label}</p>
                              <div className="flex items-center gap-1">
                                <Badge className={ev.integrity_status === 'verified' ? 'bg-emerald-100 text-emerald-700 text-[9px]' : 'bg-rose-100 text-rose-700 text-[9px]'}>
                                  {ev.integrity_status === 'verified' ? <ShieldCheck className="h-2.5 w-2.5 inline mr-0.5" /> : <ShieldAlert className="h-2.5 w-2.5 inline mr-0.5" />}
                                  {ev.integrity_status}
                                </Badge>
                                <code className="text-[9px] text-slate-400 font-mono">{ev.integrity_hash}</code>
                              </div>
                            </div>
                            <p className="text-[10px] text-slate-500">{new Date(ev.created_at).toLocaleString()}</p>
                            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-1.5 text-[10px]">
                              {ev.actor_email && <p><span className="text-slate-400">Actor:</span> {ev.actor_email} ({ev.actor_role})</p>}
                              {!ev.actor_email && ev.actor_role === 'anonymous' && <p><span className="text-slate-400">Actor:</span> <span className="italic">anonymous</span></p>}
                              {ev.ip_address && <p><span className="text-slate-400">IP:</span> {ev.ip_address}</p>}
                              {ev.user_agent && <p className="col-span-2"><span className="text-slate-400">UA:</span> <span className="font-mono text-[9px]">{ev.user_agent}</span></p>}
                              {ev.details?.click_count !== undefined && <p><span className="text-slate-400">Click #:</span> {ev.details.click_count}</p>}
                              {ev.details?.expires_in_days !== undefined && <p><span className="text-slate-400">Expiry:</span> {ev.details.expires_in_days === 0 ? 'Never' : `${ev.details.expires_in_days} days`}</p>}
                              {ev.details?.reason && <p className="col-span-2"><span className="text-slate-400">Reason:</span> {ev.details.reason}</p>}
                              {ev.details?.source && <p><span className="text-slate-400">Source:</span> {ev.details.source.replace(/_/g, ' ')}</p>}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              ) : null}
            </div>

            <div className="p-3 border-t bg-slate-50 text-[10px] text-slate-500 text-center">
              All events SHA-256 chained · Stored in Legal Archive (record_type=share_event)
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
