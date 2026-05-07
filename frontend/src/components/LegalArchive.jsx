import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Search, FileText, Pen, Receipt, Shield, Download, Eye,
  Calendar, X, RefreshCw, IndianRupee, ShieldCheck, ShieldAlert
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TYPE_META = {
  consent: { icon: Shield, label: 'Consent', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  signature: { icon: Pen, label: 'E-Signature', color: 'bg-amber-100 text-amber-700 border-amber-200' },
  invoice: { icon: Receipt, label: 'Invoice', color: 'bg-blue-100 text-blue-700 border-blue-200' },
};

export default function LegalArchive() {
  const [stats, setStats] = useState({ total: 0, consents: 0, signatures: 0, invoices: 0 });
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState({ q: '', record_type: 'all', start_date: '', end_date: '' });
  const [selected, setSelected] = useState(null);
  const [integrity, setIntegrity] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const verifyAll = useCallback(async () => {
    setVerifying(true);
    try {
      const r = await axios.get(`${API}/legal-archive/integrity/verify-all`, getAuth());
      setIntegrity(r.data);
      if (r.data.tampered > 0) {
        toast.error(`⚠️ ${r.data.tampered} tampered record(s) detected!`);
      } else if (r.data.unverified > 0) {
        toast.warning(`${r.data.unverified} legacy record(s) without hash. Run Backfill.`);
      } else {
        toast.success(`All ${r.data.verified} records verified — chain intact ✓`);
      }
    } catch (e) { toast.error(e.response?.data?.detail || 'Verification failed'); }
    setVerifying(false);
  }, []);

  const backfillHashes = useCallback(async () => {
    try {
      const r = await axios.post(`${API}/legal-archive/integrity/backfill`, {}, getAuth());
      toast.success(`Backfilled ${r.data.total} record(s) — ${r.data.consent} consent, ${r.data.signature} sig, ${r.data.invoice} invoice`);
      verifyAll();
    } catch (e) { toast.error(e.response?.data?.detail || 'Backfill failed'); }
  }, [verifyAll]);

  const loadStats = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/legal-archive/stats`, getAuth());
      setStats(r.data);
    } catch (e) { /* silent */ }
  }, []);

  const search = useCallback(async (overrides = {}) => {
    setLoading(true);
    try {
      const f = { ...filter, ...overrides };
      const params = new URLSearchParams();
      if (f.q) params.set('q', f.q);
      if (f.record_type) params.set('record_type', f.record_type);
      if (f.start_date) params.set('start_date', f.start_date);
      if (f.end_date) params.set('end_date', f.end_date);
      const r = await axios.get(`${API}/legal-archive/search?${params.toString()}`, getAuth());
      setItems(r.data.items || []);
    } catch (e) { toast.error(e.response?.data?.detail || 'Search failed'); }
    setLoading(false);
  }, [filter]);

  useEffect(() => { loadStats(); search(); verifyAll(); }, [loadStats, search, verifyAll]);

  const downloadDoc = async (paId, kind, refId) => {
    try {
      const r = await fetch(`${API}/proposal-docs/${paId}/${kind}.pdf`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const u = URL.createObjectURL(blob);
      window.open(u, '_blank');
      setTimeout(() => URL.revokeObjectURL(u), 60000);
    } catch { toast.error('Download failed'); }
  };

  const exportCsv = () => {
    if (items.length === 0) { toast.error('Nothing to export'); return; }
    const header = 'Type,Reference ID,PA Number,Client Name,Client Email,Partner,Country,Service,Amount,Timestamp,Mode\n';
    const rows = items.map(i => [
      i.type, i.reference_id || '', i.pa_number || '',
      `"${(i.client_name || '').replace(/"/g, '""')}"`,
      i.client_email || '', `"${(i.partner_name || '').replace(/"/g, '""')}"`,
      i.country || '', i.service_type || '',
      i.amount || '', i.timestamp || '', i.mode || '',
    ].join(',')).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const u = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = u; a.download = `legal-archive-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(u), 60000);
  };

  return (
    <div className="space-y-5" data-testid="legal-archive">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Shield className="h-6 w-6 text-[#2a777a]" /> Legal Archive
          </h1>
          <p className="text-sm text-slate-500 mt-1">Searchable compliance dashboard — every consent, signature & invoice with reference IDs.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={verifyAll} disabled={verifying} className="border-indigo-300 text-indigo-700 hover:bg-indigo-50" data-testid="verify-all-btn">
            <ShieldCheck className={`h-4 w-4 mr-2 ${verifying ? 'animate-pulse' : ''}`} /> {verifying ? 'Verifying…' : 'Verify Integrity'}
          </Button>
          <Button variant="outline" onClick={exportCsv} className="border-slate-300" data-testid="export-csv-btn">
            <Download className="h-4 w-4 mr-2" /> Export CSV
          </Button>
        </div>
      </div>

      {/* Stats Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="p-4 border-l-4 border-l-slate-400">
          <p className="text-xs text-slate-500">Total Records</p>
          <p className="text-2xl font-bold text-slate-800">{stats.total}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-emerald-500">
          <p className="text-xs text-emerald-600 flex items-center gap-1"><Shield className="h-3 w-3" /> Consents</p>
          <p className="text-2xl font-bold text-emerald-800">{stats.consents}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-amber-500">
          <p className="text-xs text-amber-600 flex items-center gap-1"><Pen className="h-3 w-3" /> E-Signatures</p>
          <p className="text-2xl font-bold text-amber-800">{stats.signatures}</p>
        </Card>
        <Card className="p-4 border-l-4 border-l-blue-500">
          <p className="text-xs text-blue-600 flex items-center gap-1"><Receipt className="h-3 w-3" /> Invoices</p>
          <p className="text-2xl font-bold text-blue-800">{stats.invoices}</p>
        </Card>
      </div>

      {/* Integrity Banner */}
      {integrity && (
        <Card className={`p-3 border-l-4 ${integrity.tampered > 0 ? 'border-l-red-500 bg-red-50' : integrity.unverified > 0 ? 'border-l-amber-500 bg-amber-50' : 'border-l-emerald-500 bg-emerald-50'}`} data-testid="integrity-banner">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2.5">
              {integrity.tampered > 0
                ? <ShieldAlert className="h-5 w-5 text-red-600" />
                : <ShieldCheck className={`h-5 w-5 ${integrity.unverified > 0 ? 'text-amber-600' : 'text-emerald-600'}`} />}
              <div>
                <p className="text-sm font-semibold text-slate-800">
                  SHA-256 Integrity:&nbsp;
                  <span className="text-emerald-700">{integrity.verified} verified</span>
                  {integrity.tampered > 0 && <> · <span className="text-red-700">{integrity.tampered} tampered</span></>}
                  {integrity.unverified > 0 && <> · <span className="text-amber-700">{integrity.unverified} unverified</span></>}
                </p>
                <p className="text-[11px] text-slate-500">Scanned at {new Date(integrity.scanned_at).toLocaleString()}</p>
              </div>
            </div>
            {integrity.unverified > 0 && (
              <Button size="sm" variant="outline" onClick={backfillHashes} className="border-amber-300 text-amber-700 hover:bg-amber-100" data-testid="backfill-btn">
                Backfill Legacy Hashes
              </Button>
            )}
          </div>
          {integrity.tampered > 0 && (
            <div className="mt-2 pt-2 border-t border-red-200 text-[11px] text-red-700">
              <p className="font-semibold mb-1">Tampered records:</p>
              <ul className="space-y-0.5 font-mono">
                {integrity.tampered_records.map((t, idx) => (
                  <li key={idx}>· [{t.type}] <strong>{t.reference_id || t.id}</strong> — expected {t.expected} · actual {t.actual}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}
      <Card className="p-4 border-slate-200">
        <div className="flex gap-2 mb-3 flex-wrap">
          <div className="flex-1 min-w-[220px] relative">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input
              placeholder="Search by reference ID, client name, email, PA number…"
              value={filter.q}
              onChange={e => setFilter({ ...filter, q: e.target.value })}
              onKeyDown={e => e.key === 'Enter' && search()}
              className="pl-9"
              data-testid="legal-search-input"
            />
          </div>
          <Button onClick={() => search()} disabled={loading} className="bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="legal-search-btn">
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4 mr-1" />} Search
          </Button>
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <div className="flex bg-slate-100 rounded-lg p-1 gap-1">
            {[
              { k: 'all', l: 'All' },
              { k: 'consent', l: 'Consents' },
              { k: 'signature', l: 'Signatures' },
              { k: 'invoice', l: 'Invoices' },
            ].map(t => (
              <button key={t.k} onClick={() => { setFilter({ ...filter, record_type: t.k }); search({ record_type: t.k }); }}
                className={`px-3 py-1 rounded-md text-xs font-medium transition ${filter.record_type === t.k ? 'bg-white text-[#2a777a] shadow-sm' : 'text-slate-600 hover:text-slate-800'}`}
                data-testid={`filter-${t.k}`}>
                {t.l}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Calendar className="h-3.5 w-3.5" />
            <Input type="date" value={filter.start_date} onChange={e => setFilter({ ...filter, start_date: e.target.value })} className="h-8 text-xs w-36" data-testid="filter-start-date" />
            <span>→</span>
            <Input type="date" value={filter.end_date} onChange={e => setFilter({ ...filter, end_date: e.target.value })} className="h-8 text-xs w-36" data-testid="filter-end-date" />
            {(filter.start_date || filter.end_date) && (
              <button onClick={() => { setFilter({ ...filter, start_date: '', end_date: '' }); search({ start_date: '', end_date: '' }); }}
                className="text-slate-400 hover:text-red-500" title="Clear dates">
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Results */}
      <Card className="border-slate-200 overflow-hidden">
        <div className="p-4 border-b bg-slate-50 flex items-center justify-between">
          <p className="text-sm font-semibold text-slate-700">{items.length} record{items.length !== 1 ? 's' : ''}</p>
          <Button variant="ghost" size="sm" onClick={() => search()} className="h-7 text-xs" data-testid="legal-refresh-btn">
            <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
        {items.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <Shield className="h-10 w-10 mx-auto mb-2 text-slate-300" />
            <p className="text-sm">No records match your filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-600">
                <tr>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Reference ID</th>
                  <th className="px-3 py-2 text-left">Integrity</th>
                  <th className="px-3 py-2 text-left">Client</th>
                  <th className="px-3 py-2 text-left">Country / Service</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((i, idx) => {
                  const meta = TYPE_META[i.type] || { icon: FileText, label: i.type, color: 'bg-slate-100 text-slate-700' };
                  const Icon = meta.icon;
                  return (
                    <tr key={`${i.type}-${i.id}-${idx}`} className="hover:bg-slate-50" data-testid={`legal-row-${i.type}-${i.id}`}>
                      <td className="px-3 py-2.5">
                        <Badge className={`${meta.color} border h-5 text-[11px]`}>
                          <Icon className="h-3 w-3 mr-1" /> {meta.label}
                        </Badge>
                      </td>
                      <td className="px-3 py-2.5 font-mono text-xs text-slate-700">{i.reference_id || '—'}</td>
                      <td className="px-3 py-2.5">
                        {i.integrity_status === 'verified' ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded" title={`Hash: ${i.integrity_hash}…`} data-testid={`integrity-${i.id}`}>
                            <ShieldCheck className="h-3 w-3" /> {i.integrity_hash}…
                          </span>
                        ) : i.integrity_status === 'tampered' ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium text-red-700 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded animate-pulse" data-testid={`integrity-${i.id}`}>
                            <ShieldAlert className="h-3 w-3" /> Tampered
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded" data-testid={`integrity-${i.id}`}>
                            <Shield className="h-3 w-3" /> Legacy
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        <p className="font-medium text-slate-800">{i.client_name || '—'}</p>
                        <p className="text-[11px] text-slate-500">{i.client_email || ''}</p>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-600">
                        <p>{i.country || '—'}</p>
                        <p className="text-[10px] text-slate-400">{i.service_type || ''}</p>
                      </td>
                      <td className="px-3 py-2.5 text-right text-xs text-slate-700">
                        {i.amount > 0 ? <span className="font-semibold flex items-center justify-end"><IndianRupee className="h-3 w-3" />{i.amount.toLocaleString('en-IN')}</span> : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-500">{i.timestamp ? new Date(i.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}</td>
                      <td className="px-3 py-2.5 text-right">
                        <Button size="sm" variant="ghost" onClick={() => setSelected(i)} className="h-7 text-xs" data-testid={`legal-view-${i.id}`}>
                          <Eye className="h-3 w-3 mr-1" /> View
                        </Button>
                        {i.type === 'invoice' && (
                          <Button size="sm" variant="ghost" onClick={() => downloadDoc(i.pa_id, 'invoice', i.reference_id)} className="h-7 text-xs" data-testid={`legal-dl-invoice-${i.id}`}>
                            <Download className="h-3 w-3" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setSelected(null)} data-testid="legal-detail-modal">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b flex items-center justify-between sticky top-0 bg-white">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wide">{TYPE_META[selected.type]?.label || selected.type}</p>
                <h3 className="text-lg font-bold text-slate-800 font-mono">{selected.reference_id}</h3>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelected(null)} className="h-8 w-8 p-0"><X className="h-4 w-4" /></Button>
            </div>
            <div className="p-5 space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><p className="text-xs text-slate-500">Client</p><p className="font-medium">{selected.client_name}</p><p className="text-[11px] text-slate-500">{selected.client_email}</p></div>
                <div><p className="text-xs text-slate-500">Partner</p><p className="font-medium">{selected.partner_name || '—'}</p></div>
                <div><p className="text-xs text-slate-500">Country / Service</p><p className="font-medium">{selected.country || '—'}</p><p className="text-[11px] text-slate-500">{selected.service_type || ''}</p></div>
                <div><p className="text-xs text-slate-500">Timestamp</p><p className="font-medium">{selected.timestamp ? new Date(selected.timestamp).toLocaleString() : '—'}</p></div>
                {selected.amount > 0 && (
                  <div className="col-span-2"><p className="text-xs text-slate-500">Amount</p><p className="font-bold text-emerald-700 text-lg">₹{selected.amount.toLocaleString('en-IN')}</p></div>
                )}
              </div>
              {/* Type-specific previews */}
              {selected.type === 'consent' && selected.preview && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs">
                  <p className="font-semibold text-emerald-900 mb-2">Consent Snapshot</p>
                  <div className="space-y-1">
                    <div className="flex justify-between"><span>Base Fee:</span> <span>₹{(selected.preview.base_fee || 0).toLocaleString('en-IN')}</span></div>
                    {selected.preview.promo_code && <div className="flex justify-between text-red-600"><span>Promo {selected.preview.promo_code}:</span> <span>- ₹{(selected.preview.promo_discount || 0).toLocaleString('en-IN')}</span></div>}
                    {selected.preview.custom_discount > 0 && <div className="flex justify-between text-red-600"><span>Custom Discount:</span> <span>- ₹{selected.preview.custom_discount.toLocaleString('en-IN')}</span></div>}
                    {selected.preview.upsell_total > 0 && <div className="flex justify-between text-indigo-600"><span>Upsells ({(selected.preview.upsells || []).length}):</span> <span>+ ₹{selected.preview.upsell_total.toLocaleString('en-IN')}</span></div>}
                    <div className="flex justify-between font-bold border-t border-dashed border-emerald-300 pt-1"><span>Final Amount:</span> <span>₹{(selected.preview.final_amount || 0).toLocaleString('en-IN')}</span></div>
                  </div>
                </div>
              )}
              {selected.type === 'signature' && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs">
                  <p className="font-semibold text-amber-900 mb-2">Signature Metadata</p>
                  <div className="space-y-1">
                    <div className="flex justify-between"><span>IP Address:</span> <span className="font-mono">{selected.ip_address || '—'}</span></div>
                    <div className="flex justify-between"><span>File Size:</span> <span>{selected.file_size ? `${(selected.file_size / 1024).toFixed(1)} KB` : '—'}</span></div>
                    <p className="text-slate-500 mt-1 break-all">UA: {selected.user_agent}</p>
                  </div>
                </div>
              )}
              <div className="flex gap-2 pt-2 border-t">
                {selected.type === 'invoice' && (
                  <Button size="sm" onClick={() => downloadDoc(selected.pa_id, 'invoice', selected.reference_id)} className="bg-[#2a777a] hover:bg-[#206063] text-white">
                    <Download className="h-3.5 w-3.5 mr-1" /> Download Invoice PDF
                  </Button>
                )}
                {selected.type === 'consent' && (
                  <Button size="sm" onClick={() => downloadDoc(selected.pa_id, 'proposal', selected.reference_id)} className="bg-[#2a777a] hover:bg-[#206063] text-white">
                    <Download className="h-3.5 w-3.5 mr-1" /> Download Proposal PDF
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
