/**
 * Phase 4C.7 — Payout Queue & Workflow (Admin).
 * Bulk approve, bulk mark-paid, NEFT CSV export.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Download, CheckCircle, Banknote, Filter } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const STATUS_BADGE = {
  unassigned: 'bg-slate-100 text-slate-700',
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-indigo-100 text-indigo-700',
  paid: 'bg-emerald-100 text-emerald-700',
  disputed: 'bg-rose-100 text-rose-700',
};


export default function PayoutQueue() {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState(null);
  const [statusFilter, setStatusFilter] = useState('approved');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const params = new URLSearchParams();
      if (statusFilter) params.set('status', statusFilter);
      if (fromDate) params.set('from_date', fromDate);
      if (toDate) params.set('to_date', toDate);
      const [qRes, sRes] = await Promise.all([
        axios.get(`${API}/payouts/queue?${params.toString()}`, { headers }),
        axios.get(`${API}/payouts/stats`, { headers }),
      ]);
      setRows(qRes.data.rows || []);
      setStats(sRes.data);
      setSelected({});
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed to load queue'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [statusFilter]);

  const filtered = useMemo(() => {
    if (!search) return rows;
    const s = search.toLowerCase();
    return rows.filter(r => (r.vendor_name || '').toLowerCase().includes(s) ||
      (r.client_name || '').toLowerCase().includes(s) ||
      (r.pa_number || '').toLowerCase().includes(s));
  }, [rows, search]);

  // Only `pending` and `approved` rows can be bulk-actioned. Paid/disputed/reversed are terminal/locked.
  const actionableFiltered = useMemo(() => filtered.filter(r => r.status === 'pending' || r.status === 'approved'), [filtered]);

  const selectedRows = filtered.filter(r => selected[`${r.pa_id}|${r.allocation_id}`]);
  const selectedTotal = selectedRows.reduce((s, r) => s + (r.amount || 0), 0);
  const canBulkApprove = selectedRows.length > 0 && selectedRows.every(r => r.status === 'pending');
  const canBulkPay = selectedRows.length > 0 && selectedRows.every(r => r.status === 'pending' || r.status === 'approved');

  const toggle = (r) => {
    // Lock terminal-state rows from being selected
    if (r.status === 'paid' || r.status === 'reversed' || r.status === 'disputed') {
      toast.error(`Cannot select ${r.status} rows for bulk actions`);
      return;
    }
    const k = `${r.pa_id}|${r.allocation_id}`;
    setSelected(prev => ({ ...prev, [k]: !prev[k] }));
  };
  const toggleAll = () => {
    if (selectedRows.length === actionableFiltered.length && actionableFiltered.length > 0) setSelected({});
    else {
      const next = {};
      actionableFiltered.forEach(r => { next[`${r.pa_id}|${r.allocation_id}`] = true; });
      setSelected(next);
    }
  };

  const disputeRow = async (r) => {
    const reason = prompt(`Reason for marking "${r.label}" as disputed (vendor refused / wrong amount / payment failed / etc.):`);
    if (reason === null) return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/payouts/${r.pa_id}/allocations/${r.allocation_id}/dispute`, { reason }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Marked as disputed');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Dispute failed'); }
  };

  const resolveDispute = async (r) => {
    if (!window.confirm(`Resolve dispute on "${r.label}" and move back to ${r.vendor_id || r.vendor_master_id ? 'approved' : 'pending'}?`)) return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/payouts/${r.pa_id}/allocations/${r.allocation_id}/resolve-dispute`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Dispute resolved');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Resolve failed'); }
  };

  const bulkApprove = async () => {
    if (selectedRows.length === 0) { toast.error('Select at least one row'); return; }
    setBusy(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/payouts/bulk-approve`,
        { items: selectedRows.map(x => ({ pa_id: x.pa_id, allocation_id: x.allocation_id })) },
        { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Approved: ${r.data.approved} | Failed: ${r.data.failed}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Bulk approve failed'); }
    finally { setBusy(false); }
  };

  const bulkPay = async () => {
    if (selectedRows.length === 0) { toast.error('Select at least one row'); return; }
    const ref = prompt(`Payment reference for ${selectedRows.length} payouts (NEFT batch ID, UTR, etc.):`);
    if (ref === null) return;
    setBusy(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/payouts/bulk-mark-paid`,
        { items: selectedRows.map(x => ({ pa_id: x.pa_id, allocation_id: x.allocation_id })), payment_reference: ref || '' },
        { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`Paid: ${r.data.paid} | Failed: ${r.data.failed} | Ref: ${r.data.payment_reference}`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Bulk pay failed'); }
    finally { setBusy(false); }
  };

  const downloadCsv = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      params.set('status', statusFilter || 'approved');
      if (fromDate) params.set('from_date', fromDate);
      if (toDate) params.set('to_date', toDate);
      const r = await axios.get(`${API}/payouts/neft-csv?${params.toString()}`,
        { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `NEFT_payouts_${statusFilter}_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('CSV downloaded');
    } catch (e) { toast.error('Download failed'); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="payout-queue-page">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-to-admin"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Banknote className="h-7 w-7 text-emerald-600" />Payout Queue</h1>
              <p className="text-sm text-slate-500 mt-1">Bulk approve · Mark paid · Download NEFT CSV</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-5 gap-3 mb-6">
            <Card className="p-4 bg-amber-50/60 border-amber-200" data-testid="stat-pending">
              <p className="text-[10px] font-bold uppercase text-amber-700">Pending</p>
              <p className="text-xl font-extrabold text-amber-800 mt-1">{formatINR(stats.totals.pending)}</p>
              <p className="text-[10px] text-amber-600">{stats.counts.pending} items</p>
            </Card>
            <Card className="p-4 bg-indigo-50/60 border-indigo-200" data-testid="stat-approved">
              <p className="text-[10px] font-bold uppercase text-indigo-700">Approved · Ready to Pay</p>
              <p className="text-xl font-extrabold text-indigo-800 mt-1">{formatINR(stats.totals.approved)}</p>
              <p className="text-[10px] text-indigo-600">{stats.counts.approved} items</p>
            </Card>
            <Card className="p-4 bg-emerald-50/60 border-emerald-200" data-testid="stat-paid">
              <p className="text-[10px] font-bold uppercase text-emerald-700">Paid</p>
              <p className="text-xl font-extrabold text-emerald-800 mt-1">{formatINR(stats.totals.paid)}</p>
              <p className="text-[10px] text-emerald-600">{stats.counts.paid} items</p>
            </Card>
            <Card className="p-4 bg-rose-50/60 border-rose-200" data-testid="stat-disputed">
              <p className="text-[10px] font-bold uppercase text-rose-700">Disputed</p>
              <p className="text-xl font-extrabold text-rose-800 mt-1">{formatINR(stats.totals.disputed)}</p>
              <p className="text-[10px] text-rose-600">{stats.counts.disputed} items</p>
            </Card>
            <Card className="p-4 bg-gradient-to-br from-slate-100 to-slate-200" data-testid="stat-outstanding">
              <p className="text-[10px] font-bold uppercase text-slate-600">Outstanding</p>
              <p className="text-xl font-extrabold text-slate-900 mt-1">{formatINR(stats.outstanding)}</p>
              <p className="text-[10px] text-slate-500">pending + approved</p>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card className="p-4 mb-4 flex flex-wrap items-end gap-3" data-testid="filters">
          <div>
            <label className="text-[10px] font-bold uppercase text-slate-500">Status</label>
            <div className="flex gap-1.5 mt-1">
              {['pending', 'approved', 'paid', 'disputed', ''].map(s => (
                <button key={s || 'all'} onClick={() => setStatusFilter(s)}
                  className={`px-2.5 py-1 rounded text-xs ${statusFilter === s ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'}`}
                  data-testid={`filter-${s || 'all'}`}>{s || 'All'}</button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase text-slate-500">From</label>
            <Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} className="h-9 w-40" data-testid="from-date" />
          </div>
          <div>
            <label className="text-[10px] font-bold uppercase text-slate-500">To</label>
            <Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} className="h-9 w-40" data-testid="to-date" />
          </div>
          <div className="flex-1 min-w-48">
            <label className="text-[10px] font-bold uppercase text-slate-500">Search</label>
            <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Vendor / Client / PA #" className="h-9" data-testid="search-input" />
          </div>
          <Button variant="outline" onClick={load} data-testid="apply-filters"><Filter className="h-4 w-4 mr-1" />Apply</Button>
          <Button variant="outline" onClick={downloadCsv} data-testid="download-csv"><Download className="h-4 w-4 mr-1" />NEFT CSV</Button>
        </Card>

        {/* Bulk actions bar */}
        {selectedRows.length > 0 && (
          <Card className="p-3 mb-3 bg-indigo-50 border-indigo-200 flex items-center justify-between" data-testid="bulk-bar">
            <div className="text-sm">
              <strong>{selectedRows.length}</strong> selected · Total: <strong className="text-indigo-700">{formatINR(selectedTotal)}</strong>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setSelected({})}>Clear</Button>
              <Button size="sm" onClick={bulkApprove} disabled={busy || !canBulkApprove} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50" data-testid="bulk-approve-btn" title={!canBulkApprove ? 'Bulk Approve only works on pending rows' : ''}>Bulk Approve</Button>
              <Button size="sm" onClick={bulkPay} disabled={busy || !canBulkPay} className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50" data-testid="bulk-pay-btn" title={!canBulkPay ? 'Bulk Pay only works on pending/approved rows' : ''}><CheckCircle className="h-3.5 w-3.5 mr-1" />Bulk Mark Paid</Button>
            </div>
          </Card>
        )}

        {/* Status flow info card */}
        <Card className="p-3 mb-3 bg-slate-50 border-slate-200" data-testid="status-info">
          <p className="text-[11px] text-slate-600">
            <strong>Status flow:</strong> <Badge className={`${STATUS_BADGE.pending} text-[10px] mx-1`}>pending</Badge>→
            <Badge className={`${STATUS_BADGE.approved} text-[10px] mx-1`}>approved</Badge>→
            <Badge className={`${STATUS_BADGE.paid} text-[10px] mx-1`}>paid</Badge>
            (terminal). At any time you can mark a row as
            <Badge className={`${STATUS_BADGE.disputed} text-[10px] mx-1`}>disputed</Badge>
            — use this when vendor refuses payment, wrong amount, payment failure, or any issue requiring resolution. Disputed rows are paused from payout; resolve them to put them back into the flow.
          </p>
        </Card>

        {/* Table */}
        <Card className="p-0 overflow-hidden" data-testid="queue-table">
          {loading ? <div className="p-12 text-center text-slate-500">Loading…</div> :
            filtered.length === 0 ? <div className="p-12 text-center text-slate-400 italic">No payouts match current filters.</div> :
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-100">
                  <tr className="text-[10px] uppercase text-slate-500">
                    <th className="px-3 py-2 text-left"><input type="checkbox" checked={actionableFiltered.length > 0 && selectedRows.length === actionableFiltered.length} onChange={toggleAll} data-testid="select-all" /></th>
                    <th className="px-3 py-2 text-left">PA / Client</th>
                    <th className="px-3 py-2 text-left">Vendor</th>
                    <th className="px-3 py-2 text-left">Category</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                    <th className="px-3 py-2 text-center">Status</th>
                    <th className="px-3 py-2 text-left">Reference</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => {
                    const k = `${r.pa_id}|${r.allocation_id}`;
                    const isSel = !!selected[k];
                    const isTerminal = r.status === 'paid' || r.status === 'reversed';
                    const isDisputed = r.status === 'disputed';
                    return (
                      <tr key={k} className={`border-t hover:bg-slate-50 ${isSel ? 'bg-indigo-50/40' : ''} ${isTerminal ? 'opacity-60' : ''}`} data-testid={`row-${i}`}>
                        <td className="px-3 py-2">
                          {isTerminal || isDisputed ? (
                            <span className="text-slate-300 text-[10px] italic" title="Terminal status — cannot bulk action">—</span>
                          ) : (
                            <input type="checkbox" checked={isSel} onChange={() => toggle(r)} data-testid={`row-check-${i}`} />
                          )}
                        </td>
                        <td className="px-3 py-2"><p className="font-medium">{r.client_name}</p><p className="text-[10px] text-slate-500">{r.pa_number}</p></td>
                        <td className="px-3 py-2"><p className="text-xs">{r.vendor_name || <span className="italic text-slate-400">unassigned</span>}</p><p className="text-[10px] text-slate-500">{r.vendor_type || ''}</p></td>
                        <td className="px-3 py-2 text-xs">{r.label}<p className="text-[10px] text-slate-400">{r.vendor_category}</p></td>
                        <td className="px-3 py-2 text-right font-bold">{formatINR(r.amount)}</td>
                        <td className="px-3 py-2 text-center"><Badge className={`${STATUS_BADGE[r.status]} text-[10px]`}>{r.status}</Badge></td>
                        <td className="px-3 py-2 text-[11px] font-mono text-slate-500">{r.payment_reference || '—'}</td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex gap-1 justify-end">
                            {/* Dispute action: only show when actionable */}
                            {(r.status === 'pending' || r.status === 'approved') && (
                              <Button size="sm" variant="ghost" className="h-6 text-[10px] px-2 text-rose-600 hover:bg-rose-50" onClick={() => disputeRow(r)} data-testid={`dispute-${i}`} title="Mark as Disputed">⚠️ Dispute</Button>
                            )}
                            {/* Resolve dispute action */}
                            {isDisputed && (
                              <Button size="sm" variant="outline" className="h-6 text-[10px] px-2" onClick={() => resolveDispute(r)} data-testid={`resolve-${i}`}>Resolve</Button>
                            )}
                            {/* Locked indicator for terminal states */}
                            {isTerminal && (
                              <span className="text-[10px] text-slate-400 italic px-2" title={`This row is ${r.status} and cannot be modified`}>🔒 locked</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          }
        </Card>
      </div>
    </div>
  );
}
