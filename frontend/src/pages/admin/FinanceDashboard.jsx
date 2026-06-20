/**
 * Phase 4D — Unified Finance Dashboard
 *
 * ONE screen for all money flows:
 *   - Sales Commissions  (sales_commission)
 *   - CM Earnings        (cm-earnings)
 *   - Vendor Payouts     (payouts)
 *   - Slabs Config       (link to slabs manager)
 *
 * Common filters: period, date range, status. CSV download per tab.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ArrowLeft, IndianRupee, TrendingUp, Trophy, Banknote, Download,
  Calendar, Crown, AlertCircle, Sparkles, Settings, CheckCircle, Trash2,
} from 'lucide-react';

import CustomCommissionsPanel from '@/components/finance/CustomCommissionsPanel';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const currentPeriod = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

const STATUS_BADGE = {
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-leamss-teal-100 text-leamss-teal-700',
  paid: 'bg-emerald-100 text-emerald-700',
  reversed: 'bg-rose-100 text-rose-700',
  disputed: 'bg-rose-100 text-rose-700',
  unassigned: 'bg-slate-100 text-slate-700',
};


function downloadCSV(rows, filename, headers) {
  const escape = (v) => {
    const s = v == null ? '' : String(v);
    return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [
    headers.map(h => h.label).join(','),
    ...rows.map(r => headers.map(h => escape(typeof h.value === 'function' ? h.value(r) : r[h.key])).join(',')),
  ].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}


// ═══════════════════════════════════════════════════════════════════════
export default function FinanceDashboard() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('overview');
  const [period, setPeriod] = useState(currentPeriod());
  const [statusFilter, setStatusFilter] = useState('');

  const [salesCommissions, setSalesCommissions] = useState({ entries: [], leaderboard: [], total_revenue: 0, total_commission: 0 });
  const [vendorPayouts, setVendorPayouts] = useState({ rows: [], totals: {}, ready_to_pay: 0, outstanding: 0 });
  const [cmEarningsAll, setCmEarningsAll] = useState({ rows: [], total: 0 });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [scR, lbR, vqR, vsR] = await Promise.all([
        axios.get(`${API}/sales-commission/all?period=${period}${statusFilter ? `&status=${statusFilter}` : ''}`, { headers }),
        axios.get(`${API}/sales-commission/leaderboard?period=${period}`, { headers }),
        axios.get(`${API}/payouts/queue${statusFilter ? `?status=${statusFilter}` : ''}`, { headers }),
        axios.get(`${API}/payouts/stats`, { headers }),
      ]);
      setSalesCommissions({
        entries: scR.data.entries || [],
        leaderboard: lbR.data.leaderboard || [],
        total_revenue: scR.data.total_revenue || 0,
        total_commission: scR.data.total_commission || 0,
      });
      setVendorPayouts({
        rows: vqR.data.rows || [],
        totals: vsR.data.totals || {},
        ready_to_pay: vsR.data.ready_to_pay || 0,
        outstanding: vsR.data.outstanding || 0,
      });
      // Aggregate CM earnings from vendor payouts where category=case_manager
      const cmRows = (vqR.data.rows || []).filter(r => r.vendor_category === 'case_manager');
      const cmTotal = cmRows.reduce((s, r) => s + (r.amount || 0), 0);
      setCmEarningsAll({ rows: cmRows, total: cmTotal });
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed to load finance data'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [period, statusFilter]);

  const grandPayoutTotal = useMemo(() =>
    salesCommissions.total_commission + (vendorPayouts.totals.paid || 0) + (vendorPayouts.totals.approved || 0),
  [salesCommissions, vendorPayouts]);

  const commissionAction = async (entryId, type, payload = {}) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/sales-commission/entries/${entryId}/${type}`, payload, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`${type} done`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || `${type} failed`); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="finance-dashboard">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-btn"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><IndianRupee className="h-7 w-7 text-emerald-600" />Finance Center</h1>
              <p className="text-sm text-slate-500 mt-1">All commissions, payouts, and earnings in one place.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Input type="month" value={period} onChange={e => setPeriod(e.target.value)} className="w-44" data-testid="period-picker" />
            <Button variant="outline" onClick={() => navigate('/admin/sales/commission-slabs')} data-testid="slabs-link">
              <Trophy className="h-4 w-4 mr-1.5" />Manage Slabs
            </Button>
          </div>
        </div>

        {/* Top KPIs */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <Card className="p-4 bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-300" data-testid="kpi-revenue">
            <p className="text-[10px] uppercase font-bold text-emerald-800">Total Revenue ({period})</p>
            <p className="text-2xl font-extrabold text-emerald-900 mt-1">{formatINR(salesCommissions.total_revenue)}</p>
            <p className="text-[10px] text-emerald-700">{salesCommissions.entries.length} deals</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-leamss-teal-50 to-leamss-teal-100 border-leamss-teal-300" data-testid="kpi-commission">
            <p className="text-[10px] uppercase font-bold text-leamss-teal-800">Sales Commission</p>
            <p className="text-2xl font-extrabold text-leamss-teal-900 mt-1">{formatINR(salesCommissions.total_commission)}</p>
            <p className="text-[10px] text-leamss-teal-700">{salesCommissions.total_revenue > 0 ? `${((salesCommissions.total_commission / salesCommissions.total_revenue) * 100).toFixed(1)}% avg` : '—'}</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-300" data-testid="kpi-payouts">
            <p className="text-[10px] uppercase font-bold text-amber-800">Vendor Payouts Outstanding</p>
            <p className="text-2xl font-extrabold text-amber-900 mt-1">{formatINR(vendorPayouts.outstanding)}</p>
            <p className="text-[10px] text-amber-700">Ready to pay: {formatINR(vendorPayouts.ready_to_pay)}</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-slate-100 to-slate-200 border-slate-300" data-testid="kpi-grand">
            <p className="text-[10px] uppercase font-bold text-slate-700">Total Money Movement</p>
            <p className="text-2xl font-extrabold text-slate-900 mt-1">{formatINR(grandPayoutTotal)}</p>
            <p className="text-[10px] text-slate-600">commission + paid + approved</p>
          </Card>
        </div>

        {/* Filter */}
        <Card className="p-3 mb-4 flex items-center gap-2 flex-wrap" data-testid="filters">
          <Calendar className="h-4 w-4 text-slate-400" />
          <span className="text-xs text-slate-600">Status filter:</span>
          {['', 'pending', 'approved', 'paid', 'disputed', 'reversed'].map(s => (
            <button key={s || 'all'} onClick={() => setStatusFilter(s)}
              className={`px-2.5 py-1 rounded text-xs ${statusFilter === s ? 'bg-leamss-teal-600 text-white' : 'bg-slate-100 text-slate-600'}`}
              data-testid={`filter-${s || 'all'}`}>{s || 'All'}</button>
          ))}
        </Card>

        {/* Tabs */}
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid grid-cols-5 mb-4">
            <TabsTrigger value="overview" data-testid="tab-overview"><Sparkles className="h-3.5 w-3.5 mr-1" />Overview</TabsTrigger>
            <TabsTrigger value="commissions" data-testid="tab-commissions"><TrendingUp className="h-3.5 w-3.5 mr-1" />Sales ({salesCommissions.entries.length})</TabsTrigger>
            <TabsTrigger value="cm" data-testid="tab-cm"><IndianRupee className="h-3.5 w-3.5 mr-1" />CM ({cmEarningsAll.rows.length})</TabsTrigger>
            <TabsTrigger value="vendors" data-testid="tab-vendors"><Banknote className="h-3.5 w-3.5 mr-1" />Vendors ({vendorPayouts.rows.length})</TabsTrigger>
            <TabsTrigger value="custom-rates" data-testid="tab-custom-rates"><Settings className="h-3.5 w-3.5 mr-1" />Custom Rates</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="p-5" data-testid="overview-leaderboard">
                <h2 className="font-bold flex items-center gap-2 mb-3"><Crown className="h-5 w-5 text-amber-500" />Top Sales Performers</h2>
                {salesCommissions.leaderboard.length === 0 ? <p className="text-sm italic text-slate-400">No data for {period}</p> :
                  <div className="space-y-2">
                    {salesCommissions.leaderboard.slice(0, 5).map((l, i) => (
                      <div key={l.user_id} className="flex items-center gap-3 p-2 bg-slate-50 rounded">
                        <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-amber-500 text-white' : 'bg-slate-200'}`}>{i + 1}</span>
                        <div className="flex-1"><p className="font-medium text-sm">{l.user_name || l.user_email}</p><p className="text-[10px] text-slate-500">{l.deal_count} deals</p></div>
                        <div className="text-right"><p className="text-sm font-bold text-emerald-700">{formatINR(l.total_revenue)}</p><p className="text-[11px] text-leamss-teal-600">{formatINR(l.total_commission)} earned</p></div>
                      </div>
                    ))}
                  </div>
                }
              </Card>
              <Card className="p-5" data-testid="overview-payout-summary">
                <h2 className="font-bold flex items-center gap-2 mb-3"><Banknote className="h-5 w-5 text-emerald-500" />Vendor Payout Health</h2>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between p-2 bg-amber-50 rounded"><span>Pending</span><strong>{formatINR(vendorPayouts.totals.pending)}</strong></div>
                  <div className="flex justify-between p-2 bg-leamss-teal-50 rounded"><span>Approved (Ready)</span><strong>{formatINR(vendorPayouts.totals.approved)}</strong></div>
                  <div className="flex justify-between p-2 bg-emerald-50 rounded"><span>Paid</span><strong>{formatINR(vendorPayouts.totals.paid)}</strong></div>
                  {vendorPayouts.totals.disputed > 0 && <div className="flex justify-between p-2 bg-rose-50 rounded"><span className="flex items-center gap-1"><AlertCircle className="h-3.5 w-3.5" />Disputed</span><strong>{formatINR(vendorPayouts.totals.disputed)}</strong></div>}
                </div>
                <Button onClick={() => navigate('/admin/payouts')} variant="outline" className="w-full mt-3" data-testid="goto-payouts">Go to Payout Queue →</Button>
              </Card>
            </div>
          </TabsContent>

          {/* Sales Commissions Tab */}
          <TabsContent value="commissions">
            <Card className="p-4">
              <div className="flex justify-between mb-3">
                <h2 className="font-bold">Sales Commission Entries</h2>
                <Button size="sm" variant="outline" onClick={() => downloadCSV(salesCommissions.entries, `sales_commissions_${period}.csv`, [
                  { label: 'Rep', key: 'user_name' },
                  { label: 'Email', key: 'user_email' },
                  { label: 'PA#', key: 'pa_number' },
                  { label: 'Client', key: 'client_name' },
                  { label: 'Revenue', key: 'revenue' },
                  { label: 'Slab', key: 'slab_name' },
                  { label: 'Rate%', key: 'rate_pct' },
                  { label: 'Commission', key: 'commission_amount' },
                  { label: 'Status', key: 'status' },
                  { label: 'Period', key: 'period' },
                ])} disabled={salesCommissions.entries.length === 0} data-testid="dl-commissions">
                  <Download className="h-3.5 w-3.5 mr-1" />Download CSV
                </Button>
              </div>
              {loading ? <p className="text-sm text-slate-500 text-center py-6">Loading…</p> :
                salesCommissions.entries.length === 0 ? <p className="text-sm italic text-slate-400 text-center py-8">No commissions for {period}</p> :
                <table className="w-full text-sm">
                  <thead><tr className="border-b text-[10px] uppercase text-slate-500"><th className="text-left py-2">Rep</th><th className="text-left py-2">Client / PA</th><th className="text-right py-2">Revenue</th><th className="text-center py-2">Slab</th><th className="text-right py-2">Commission</th><th className="text-center py-2">Status</th><th className="text-right py-2">Action</th></tr></thead>
                  <tbody>
                    {salesCommissions.entries.map(e => (
                      <tr key={e.id} className="border-b hover:bg-slate-50" data-testid={`commission-row-${e.id}`}>
                        <td className="py-2">{e.user_name}<br /><span className="text-[10px] text-slate-500">{e.user_email}</span></td>
                        <td className="py-2 text-xs">{e.client_name}<br /><span className="text-[10px] text-slate-500">{e.pa_number}</span></td>
                        <td className="py-2 text-right font-medium">{formatINR(e.revenue)}</td>
                        <td className="py-2 text-center"><Badge className="bg-amber-100 text-amber-700 text-[10px]">{e.slab_name} ({e.rate_pct}%)</Badge></td>
                        <td className="py-2 text-right font-bold text-emerald-700">{formatINR(e.commission_amount)}</td>
                        <td className="py-2 text-center"><Badge className={`${STATUS_BADGE[e.status] || ''} text-[10px]`}>{e.status}</Badge></td>
                        <td className="py-2 text-right">
                          <div className="flex gap-1 justify-end">
                            {e.status === 'pending' && (
                              <Button size="sm" variant="outline" className="h-6 text-[10px] px-2" onClick={() => commissionAction(e.id, 'approve')} data-testid={`approve-${e.id}`}>
                                Approve
                              </Button>
                            )}
                            {(e.status === 'pending' || e.status === 'approved') && (
                              <Button size="sm" className="h-6 text-[10px] px-2 bg-emerald-600 hover:bg-emerald-700" onClick={() => commissionAction(e.id, 'mark-paid', { payment_reference: window.prompt('Payment reference (NEFT/UPI):') || '' })} data-testid={`pay-${e.id}`}>
                                <CheckCircle className="h-3 w-3 mr-0.5" />Pay
                              </Button>
                            )}
                            {e.status !== 'reversed' && (
                              <Button size="sm" variant="ghost" className="h-6 px-2 text-rose-600" title="Reverse" onClick={() => { if (window.confirm('Reverse this commission entry?')) commissionAction(e.id, 'reverse'); }} data-testid={`reverse-${e.id}`}>
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            </Card>
          </TabsContent>

          {/* CM Earnings Tab */}
          <TabsContent value="cm">
            <Card className="p-4">
              <div className="flex justify-between mb-3">
                <h2 className="font-bold">Case Manager Earnings</h2>
                <Button size="sm" variant="outline" onClick={() => downloadCSV(cmEarningsAll.rows, `cm_earnings_${period}.csv`, [
                  { label: 'CM', key: 'vendor_name' },
                  { label: 'PA#', key: 'pa_number' },
                  { label: 'Client', key: 'client_name' },
                  { label: 'Fee', key: 'amount' },
                  { label: 'Status', key: 'status' },
                  { label: 'Paid On', key: 'paid_at' },
                  { label: 'Reference', key: 'payment_reference' },
                ])} disabled={cmEarningsAll.rows.length === 0} data-testid="dl-cm">
                  <Download className="h-3.5 w-3.5 mr-1" />Download CSV
                </Button>
              </div>
              {cmEarningsAll.rows.length === 0 ? <p className="text-sm italic text-slate-400 text-center py-8">No CM earnings recorded</p> :
                <>
                  <p className="text-sm mb-3"><strong>Total CM Earnings:</strong> <span className="text-emerald-700 font-bold">{formatINR(cmEarningsAll.total)}</span></p>
                  <table className="w-full text-sm">
                    <thead><tr className="border-b text-[10px] uppercase text-slate-500"><th className="text-left py-2">Case Manager</th><th className="text-left py-2">Client / PA</th><th className="text-right py-2">Fee</th><th className="text-center py-2">Status</th><th className="text-left py-2">Paid On</th></tr></thead>
                    <tbody>
                      {cmEarningsAll.rows.map((r, i) => (
                        <tr key={i} className="border-b hover:bg-slate-50">
                          <td className="py-2">{r.vendor_name || <span className="italic text-slate-400">unassigned</span>}</td>
                          <td className="py-2 text-xs">{r.client_name}<br /><span className="text-[10px] text-slate-500">{r.pa_number}</span></td>
                          <td className="py-2 text-right font-bold text-emerald-700">{formatINR(r.amount)}</td>
                          <td className="py-2 text-center"><Badge className={`${STATUS_BADGE[r.status] || ''} text-[10px]`}>{r.status}</Badge></td>
                          <td className="py-2 text-[11px] text-slate-500">{r.paid_at ? new Date(r.paid_at).toLocaleDateString() : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              }
            </Card>
          </TabsContent>

          {/* Vendor Payouts Tab */}
          <TabsContent value="vendors">
            <Card className="p-4">
              <div className="flex justify-between mb-3">
                <h2 className="font-bold">Vendor Payouts</h2>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => downloadCSV(vendorPayouts.rows, `vendor_payouts_${period}.csv`, [
                    { label: 'Vendor', key: 'vendor_name' },
                    { label: 'Type', key: 'vendor_type' },
                    { label: 'Category', key: 'vendor_category' },
                    { label: 'PA#', key: 'pa_number' },
                    { label: 'Client', key: 'client_name' },
                    { label: 'Amount', key: 'amount' },
                    { label: 'Status', key: 'status' },
                    { label: 'Paid On', key: 'paid_at' },
                    { label: 'Reference', key: 'payment_reference' },
                  ])} disabled={vendorPayouts.rows.length === 0} data-testid="dl-vendors">
                    <Download className="h-3.5 w-3.5 mr-1" />Download CSV
                  </Button>
                  <Button size="sm" onClick={() => navigate('/admin/payouts')} className="bg-leamss-teal-600 hover:bg-leamss-teal-700">Manage →</Button>
                </div>
              </div>
              {vendorPayouts.rows.length === 0 ? <p className="text-sm italic text-slate-400 text-center py-8">No payouts match filter</p> :
                <table className="w-full text-sm">
                  <thead><tr className="border-b text-[10px] uppercase text-slate-500"><th className="text-left py-2">Vendor</th><th className="text-left py-2">Category</th><th className="text-left py-2">Client / PA</th><th className="text-right py-2">Amount</th><th className="text-center py-2">Status</th><th className="text-left py-2">Reference</th></tr></thead>
                  <tbody>
                    {vendorPayouts.rows.slice(0, 100).map((r, i) => (
                      <tr key={i} className="border-b hover:bg-slate-50">
                        <td className="py-2">{r.vendor_name || <span className="italic text-slate-400">unassigned</span>}<br /><span className="text-[10px] text-slate-500">{r.vendor_type}</span></td>
                        <td className="py-2 text-xs">{r.vendor_category}</td>
                        <td className="py-2 text-xs">{r.client_name}<br /><span className="text-[10px] text-slate-500">{r.pa_number}</span></td>
                        <td className="py-2 text-right font-bold">{formatINR(r.amount)}</td>
                        <td className="py-2 text-center"><Badge className={`${STATUS_BADGE[r.status] || ''} text-[10px]`}>{r.status}</Badge></td>
                        <td className="py-2 text-[11px] font-mono text-slate-500">{r.payment_reference || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              }
            </Card>
          </TabsContent>

          {/* Custom Rates Tab */}
          <TabsContent value="custom-rates">
            <CustomCommissionsPanel />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
