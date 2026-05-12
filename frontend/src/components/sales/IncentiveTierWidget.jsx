import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Trophy, TrendingUp, Target, Award, IndianRupee } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TIER_GRADIENT = {
  Bronze: 'from-amber-600 to-yellow-700',
  Silver: 'from-slate-400 to-slate-600',
  Gold: 'from-yellow-400 to-amber-500',
};
const TIER_ICON_COLOR = {
  Bronze: 'text-amber-100',
  Silver: 'text-slate-100',
  Gold: 'text-yellow-100',
};

/**
 * IncentiveTierWidget — visible only to employment_type='employee' partners/reps.
 * Shows current month revenue, tier, projected payout, and progress to next tier.
 */
export default function IncentiveTierWidget() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/sales-team/my-incentive`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      setData(r.data);
      setErr(null);
    } catch (e) {
      setErr(e.response?.status === 403 ? 'employee_only' : (e.response?.data?.detail || 'Failed'));
      setData(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  // Silently hide for non-employees — admin sees Sales Manager view instead
  if (err === 'employee_only') return null;
  if (loading || !data) return null;

  const tier = data.current_tier || {};
  const grad = TIER_GRADIENT[tier.label] || 'from-emerald-500 to-teal-600';
  const iconC = TIER_ICON_COLOR[tier.label] || 'text-emerald-100';
  const progress = data.next_tier ? Math.min(100, (data.revenue / data.next_tier.min_revenue) * 100) : 100;

  return (
    <Card className="overflow-hidden border-0 shadow-md" data-testid="incentive-widget">
      {/* Top gradient banner */}
      <div className={`bg-gradient-to-r ${grad} text-white p-5`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className={`${iconC} text-xs uppercase tracking-wide font-semibold opacity-90`}>Current Tier · {data.month}</p>
            <div className="flex items-center gap-2 mt-1">
              <Trophy className={`h-7 w-7 ${iconC}`} />
              <h3 className="text-2xl font-bold">{tier.label || 'Bronze'}</h3>
              <span className="text-xs px-2 py-0.5 bg-white/20 rounded-full font-mono">{tier.rate_pct}%</span>
            </div>
          </div>
          <div className="text-right">
            <p className={`${iconC} text-xs opacity-80`}>Projected Payout</p>
            <p className="text-2xl font-bold">₹{(data.base_payout || 0).toLocaleString('en-IN')}</p>
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 divide-x border-b">
        <div className="p-3 text-center">
          <IndianRupee className="h-4 w-4 mx-auto text-emerald-600 mb-0.5" />
          <p className="text-[10px] text-slate-500 uppercase">Revenue</p>
          <p className="font-bold text-slate-800">₹{(data.revenue || 0).toLocaleString('en-IN')}</p>
        </div>
        <div className="p-3 text-center">
          <Award className="h-4 w-4 mx-auto text-blue-600 mb-0.5" />
          <p className="text-[10px] text-slate-500 uppercase">Deals Closed</p>
          <p className="font-bold text-slate-800">{data.deal_count || 0}</p>
        </div>
        <div className="p-3 text-center">
          <TrendingUp className="h-4 w-4 mx-auto text-purple-600 mb-0.5" />
          <p className="text-[10px] text-slate-500 uppercase">Commission</p>
          <p className="font-bold text-slate-800">{tier.rate_pct}%</p>
        </div>
      </div>

      {/* Progress to next tier */}
      <div className="p-4">
        {data.next_tier ? (
          <>
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-600 flex items-center gap-1"><Target className="h-3 w-3" /> Next: <strong className="text-slate-800">{data.next_tier.label}</strong> @ {data.next_tier.rate_pct}%</span>
              <span className="font-semibold text-emerald-700">₹{(data.revenue_to_next_tier || 0).toLocaleString('en-IN')} more</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden" data-testid="incentive-progress">
              <div className={`h-full bg-gradient-to-r ${grad} transition-all`} style={{ width: `${progress}%` }} />
            </div>
            <p className="text-[10px] text-slate-500 mt-1.5">
              Close ₹{(data.revenue_to_next_tier || 0).toLocaleString('en-IN')} more to bump your commission rate from {tier.rate_pct}% to {data.next_tier.rate_pct}%.
            </p>
          </>
        ) : (
          <p className="text-xs text-emerald-700 font-semibold text-center">🎉 You're at the top tier — max commission rate active!</p>
        )}
      </div>
    </Card>
  );
}
