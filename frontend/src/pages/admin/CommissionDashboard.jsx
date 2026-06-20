/**
 * Phase 4C.4 — Admin Commission Dashboard.
 * Leaderboard + entries + approve/pay actions across all sales reps.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Trophy, CheckCircle, IndianRupee, Crown, TrendingUp, Trash2 } from 'lucide-react';

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

const STATUS_COLOR = {
  pending: 'bg-amber-100 text-amber-700',
  approved: 'bg-leamss-teal-100 text-leamss-teal-700',
  paid: 'bg-emerald-100 text-emerald-700',
  reversed: 'bg-rose-100 text-rose-700',
};


export default function CommissionDashboard() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState(currentPeriod());
  const [entries, setEntries] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [stats, setStats] = useState({ total_revenue: 0, total_commission: 0 });
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [eRes, lRes] = await Promise.all([
        axios.get(`${API}/sales-commission/all?period=${period}${statusFilter ? `&status=${statusFilter}` : ''}`, { headers }),
        axios.get(`${API}/sales-commission/leaderboard?period=${period}`, { headers }),
      ]);
      setEntries(eRes.data.entries || []);
      setLeaderboard(lRes.data.leaderboard || []);
      setStats({ total_revenue: eRes.data.total_revenue || 0, total_commission: eRes.data.total_commission || 0 });
    } catch (e) { toast.error('Failed to load'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [period, statusFilter]);

  const action = async (entryId, type, payload = {}) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/sales-commission/entries/${entryId}/${type}`, payload, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(`${type} done`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || `${type} failed`); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="commission-dashboard-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-to-admin"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><IndianRupee className="h-7 w-7 text-emerald-600" />Sales Commission</h1>
              <p className="text-sm text-slate-500 mt-1">All entries + leaderboard for the selected period.</p>
            </div>
          </div>
          <div className="flex gap-2 items-center">
            <Input type="month" value={period} onChange={e => setPeriod(e.target.value)} className="w-44" data-testid="period-picker" />
            <Button variant="outline" onClick={() => navigate('/admin/sales/commission-slabs')} data-testid="manage-slabs-btn"><Trophy className="h-4 w-4 mr-1.5" />Manage Slabs</Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <Card className="p-4 bg-gradient-to-br from-emerald-50 to-emerald-100 border-emerald-300">
            <p className="text-xs font-bold uppercase text-emerald-800">Total Revenue</p>
            <p className="text-2xl font-extrabold text-emerald-900 mt-1" data-testid="total-revenue">{formatINR(stats.total_revenue)}</p>
            <p className="text-[10px] text-emerald-700 mt-1">{period}</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-leamss-teal-50 to-leamss-teal-100 border-leamss-teal-300">
            <p className="text-xs font-bold uppercase text-leamss-teal-800">Total Commission</p>
            <p className="text-2xl font-extrabold text-leamss-teal-900 mt-1" data-testid="total-commission">{formatINR(stats.total_commission)}</p>
            <p className="text-[10px] text-leamss-teal-700 mt-1">{entries.length} entries</p>
          </Card>
          <Card className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 border-amber-300">
            <p className="text-xs font-bold uppercase text-amber-800">Avg Rate</p>
            <p className="text-2xl font-extrabold text-amber-900 mt-1">{stats.total_revenue > 0 ? `${((stats.total_commission / stats.total_revenue) * 100).toFixed(1)}%` : '—'}</p>
            <p className="text-[10px] text-amber-700 mt-1">company-wide</p>
          </Card>
        </div>

        {/* Leaderboard */}
        <Card className="p-5 mb-6" data-testid="leaderboard-card">
          <h2 className="font-bold flex items-center gap-2 mb-4"><Crown className="h-5 w-5 text-amber-500" />Top Performers</h2>
          {leaderboard.length === 0 ? (
            <p className="text-sm text-slate-400 italic text-center py-4">No data for {period}</p>
          ) : (
            <div className="space-y-2">
              {leaderboard.slice(0, 10).map((l, i) => (
                <div key={l.user_id} className="flex items-center gap-3 p-2 bg-slate-50 rounded" data-testid={`lb-row-${i}`}>
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-amber-500 text-white' : i === 1 ? 'bg-slate-400 text-white' : i === 2 ? 'bg-orange-500 text-white' : 'bg-slate-200'}`}>{i + 1}</span>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{l.user_name || l.user_email}</p>
                    <p className="text-[11px] text-slate-500">{l.deal_count} deal{l.deal_count !== 1 ? 's' : ''}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-emerald-700">{formatINR(l.total_revenue)}</p>
                    <p className="text-[11px] text-leamss-teal-600"><TrendingUp className="h-3 w-3 inline" /> {formatINR(l.total_commission)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Entries Table */}
        <Card className="p-5" data-testid="entries-card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold">Commission Entries</h2>
            <div className="flex gap-1.5 text-xs">
              {['', 'pending', 'approved', 'paid', 'reversed'].map(s => (
                <button key={s} onClick={() => setStatusFilter(s)}
                  className={`px-2.5 py-1 rounded ${statusFilter === s ? 'bg-leamss-teal-600 text-white' : 'bg-slate-100 text-slate-600'}`}
                  data-testid={`filter-${s || 'all'}`}>{s || 'All'}</button>
              ))}
            </div>
          </div>
          {loading ? <p className="text-sm text-slate-500 text-center py-6">Loading…</p> :
            entries.length === 0 ? <p className="text-sm text-slate-400 italic text-center py-6">No entries for {period}</p> :
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-[10px] uppercase text-slate-500">
                    <th className="text-left py-2">Rep</th>
                    <th className="text-left py-2">PA / Client</th>
                    <th className="text-right py-2">Revenue</th>
                    <th className="text-center py-2">Slab</th>
                    <th className="text-right py-2">Commission</th>
                    <th className="text-center py-2">Status</th>
                    <th className="text-right py-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map(e => (
                    <tr key={e.id} className="border-b last:border-b-0 hover:bg-slate-50" data-testid={`entry-${e.id}`}>
                      <td className="py-2"><p className="font-medium">{e.user_name}</p><p className="text-[10px] text-slate-500">{e.user_email}</p></td>
                      <td className="py-2"><p className="text-xs">{e.client_name}</p><p className="text-[10px] text-slate-500">{e.pa_number}</p></td>
                      <td className="py-2 text-right font-medium">{formatINR(e.revenue)}</td>
                      <td className="py-2 text-center"><Badge className="bg-amber-100 text-amber-700 text-[10px]">{e.slab_name} ({e.rate_pct}%)</Badge></td>
                      <td className="py-2 text-right font-bold text-emerald-700">{formatINR(e.commission_amount)}</td>
                      <td className="py-2 text-center"><Badge className={`${STATUS_COLOR[e.status] || ''} text-[10px]`}>{e.status}</Badge></td>
                      <td className="py-2 text-right">
                        <div className="flex gap-1 justify-end">
                          {e.status === 'pending' && <Button size="sm" variant="outline" className="h-6 text-[10px] px-2" onClick={() => action(e.id, 'approve')} data-testid={`approve-${e.id}`}>Approve</Button>}
                          {(e.status === 'pending' || e.status === 'approved') && <Button size="sm" className="h-6 text-[10px] px-2 bg-emerald-600 hover:bg-emerald-700" onClick={() => action(e.id, 'mark-paid', { payment_reference: prompt('Reference (NEFT/UPI):') || '' })} data-testid={`pay-${e.id}`}><CheckCircle className="h-3 w-3 mr-0.5" />Pay</Button>}
                          {e.status !== 'reversed' && <Button size="sm" variant="ghost" className="h-6 text-rose-600 px-2" title="Reverse" onClick={() => { if (window.confirm('Reverse this commission entry?')) action(e.id, 'reverse'); }} data-testid={`reverse-${e.id}`}><Trash2 className="h-3 w-3" /></Button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          }
        </Card>
      </div>
    </div>
  );
}
