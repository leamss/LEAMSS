/**
 * Phase 4C.4 — Sales Rep "My Commission" page.
 * Shows current month: revenue, slab tier, commission, gap to next slab + entries history.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowLeft, Trophy, IndianRupee, TrendingUp, Target, Crown, Sparkles } from 'lucide-react';

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
  approved: 'bg-indigo-100 text-indigo-700',
  paid: 'bg-emerald-100 text-emerald-700',
  reversed: 'bg-rose-100 text-rose-700',
};


export default function MyCommission() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState(currentPeriod());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/sales-commission/my?period=${period}`, { headers: { Authorization: `Bearer ${token}` } });
        setData(r.data);
      } catch (e) { toast.error(e?.response?.data?.detail || 'Failed to load'); }
      finally { setLoading(false); }
    })();
  }, [period]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><Sparkles className="h-10 w-10 text-indigo-400 animate-pulse" /></div>;
  }
  if (!data) return null;

  const progressPct = data.next_slab && data.next_slab.min_revenue > 0
    ? Math.min(100, (data.total_revenue / data.next_slab.min_revenue) * 100)
    : 100;

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="my-commission-page">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate(-1)} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-btn"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><IndianRupee className="h-7 w-7 text-emerald-600" />My Commission</h1>
              <p className="text-sm text-slate-500 mt-1">Track your earnings and progress to the next slab.</p>
            </div>
          </div>
          <Input type="month" value={period} onChange={e => setPeriod(e.target.value)} className="w-44" data-testid="period-picker" />
        </div>

        {/* Current slab + commission */}
        <Card className="p-6 mb-6 bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 border-amber-300" data-testid="current-slab-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-amber-700 font-bold mb-1">Current Tier</p>
              <h2 className="text-4xl font-extrabold text-amber-900 flex items-center gap-2">
                <Crown className="h-8 w-8 text-amber-600" />
                {data.current_slab?.name || '—'}
              </h2>
              <p className="text-sm text-amber-700 mt-1">{data.current_slab?.rate_pct}% commission on every deal</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-wider text-emerald-700 font-bold mb-1">Total Commission ({period})</p>
              <p className="text-4xl font-extrabold text-emerald-700" data-testid="total-commission">{formatINR(data.total_commission)}</p>
              <p className="text-sm text-emerald-600 mt-1">from {data.deal_count} deal{data.deal_count !== 1 ? 's' : ''}</p>
            </div>
          </div>

          {/* Progress to next slab */}
          {data.next_slab && (
            <div className="mt-6 bg-white/60 rounded-lg p-4" data-testid="next-slab-progress">
              <div className="flex justify-between items-center mb-2 text-xs">
                <span><strong>Revenue Achieved:</strong> {formatINR(data.total_revenue)}</span>
                <span><strong>Next: {data.next_slab.name}</strong> @ {data.next_slab.rate_pct}% — needs {formatINR(data.next_slab.min_revenue)}</span>
              </div>
              <div className="w-full bg-amber-100 rounded-full h-3 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-amber-500 to-emerald-500 transition-all" style={{ width: `${progressPct}%` }} data-testid="slab-progress-bar" />
              </div>
              <p className="text-xs text-amber-700 mt-2 text-center">
                <Target className="h-3 w-3 inline mr-1" />
                <strong>{formatINR(data.gap_to_next_slab)}</strong> more revenue to unlock <strong>{data.next_slab.name}</strong> tier (+{(data.next_slab.rate_pct - (data.current_slab?.rate_pct || 0)).toFixed(1)}%)
              </p>
            </div>
          )}
        </Card>

        {/* Breakdown stats */}
        <div className="grid grid-cols-4 gap-3 mb-6">
          <Card className="p-4">
            <p className="text-xs font-bold uppercase text-slate-500">Revenue</p>
            <p className="text-xl font-extrabold text-slate-800 mt-1">{formatINR(data.total_revenue)}</p>
          </Card>
          <Card className="p-4 bg-amber-50/50 border-amber-200">
            <p className="text-xs font-bold uppercase text-amber-700">Pending</p>
            <p className="text-xl font-extrabold text-amber-800 mt-1" data-testid="pending-amount">{formatINR(data.pending)}</p>
          </Card>
          <Card className="p-4 bg-indigo-50/50 border-indigo-200">
            <p className="text-xs font-bold uppercase text-indigo-700">Approved</p>
            <p className="text-xl font-extrabold text-indigo-800 mt-1" data-testid="approved-amount">{formatINR(data.approved)}</p>
          </Card>
          <Card className="p-4 bg-emerald-50/50 border-emerald-200">
            <p className="text-xs font-bold uppercase text-emerald-700">Paid</p>
            <p className="text-xl font-extrabold text-emerald-800 mt-1" data-testid="paid-amount">{formatINR(data.paid)}</p>
          </Card>
        </div>

        {/* Entries */}
        <Card className="p-5" data-testid="entries-card">
          <h2 className="font-bold flex items-center gap-2 mb-3"><Trophy className="h-5 w-5 text-amber-500" />My Deals This Period</h2>
          {data.entries.length === 0 ? (
            <div className="text-center py-8">
              <TrendingUp className="h-10 w-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No deals closed in {period} yet. Close a case to earn commission!</p>
              <Button onClick={() => navigate('/sales/dashboard')} variant="outline" className="mt-3" data-testid="go-to-pipeline">Go to Pipeline</Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-[10px] uppercase text-slate-500">
                    <th className="text-left py-2">Client / PA</th>
                    <th className="text-left py-2">Country</th>
                    <th className="text-right py-2">Revenue</th>
                    <th className="text-center py-2">Slab</th>
                    <th className="text-right py-2">Commission</th>
                    <th className="text-center py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.entries.map(e => (
                    <tr key={e.id} className="border-b last:border-b-0 hover:bg-slate-50" data-testid={`entry-${e.id}`}>
                      <td className="py-2"><p className="font-medium">{e.client_name}</p><p className="text-[10px] text-slate-500">{e.pa_number}</p></td>
                      <td className="py-2 text-xs">{e.country}<br /><span className="text-slate-500">{e.service_type}</span></td>
                      <td className="py-2 text-right font-medium">{formatINR(e.revenue)}</td>
                      <td className="py-2 text-center"><Badge className="bg-amber-100 text-amber-700 text-[10px]">{e.slab_name} ({e.rate_pct}%)</Badge></td>
                      <td className="py-2 text-right font-bold text-emerald-700">{formatINR(e.commission_amount)}</td>
                      <td className="py-2 text-center"><Badge className={`${STATUS_COLOR[e.status]} text-[10px]`}>{e.status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
