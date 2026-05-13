import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Target, IndianRupee, Trophy, PhoneCall, ArrowRight, Sparkles, Flame, Clock, Zap } from 'lucide-react';

/**
 * Internal-only widgets shown ABOVE the PA pipeline on /sales/dashboard.
 * TargetWidget is LIVE (Phase 4B). Others are still placeholders.
 */
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PHASE_BADGE = (phase) => (
  <Badge className="bg-amber-100 text-amber-800 text-[10px] font-bold uppercase tracking-wide">
    Coming in Phase {phase}
  </Badge>
);

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(1)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(0)}K`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const pctBarColor = (p) => {
  if (p >= 150) return 'bg-gradient-to-r from-amber-400 to-amber-600';
  if (p >= 100) return 'bg-gradient-to-r from-emerald-500 to-green-600';
  if (p >= 75) return 'bg-gradient-to-r from-blue-500 to-indigo-600';
  if (p >= 50) return 'bg-gradient-to-r from-yellow-400 to-orange-500';
  return 'bg-gradient-to-r from-rose-500 to-red-600';
};


export function TargetWidget() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [monthly, setMonthly] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/sales/targets/my`, { headers: { Authorization: `Bearer ${token}` } });
        if (!cancelled) setMonthly(r.data.monthly);
      } catch (e) {
        // Silently fail — user may not have access
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  // Loading state
  if (loading) {
    return (
      <Card className="p-4 border-t-4 border-t-indigo-500" data-testid="widget-target-loading">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center"><Target className="h-4 w-4 text-indigo-600 animate-pulse" /></div>
          <p className="text-sm font-bold text-slate-800">Monthly Target</p>
        </div>
        <p className="text-xs text-slate-400">Loading…</p>
      </Card>
    );
  }

  // No target set — keep placeholder behavior
  if (!monthly) {
    return (
      <Card className="p-4 border-t-4 border-t-indigo-500 hover:shadow-md transition" data-testid="widget-target">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
              <Target className="h-4 w-4 text-indigo-600" />
            </div>
            <p className="text-sm font-bold text-slate-800">Monthly Target</p>
          </div>
          <Badge className="bg-slate-100 text-slate-600 text-[10px] font-bold uppercase">Not set</Badge>
        </div>
        <p className="text-xs text-slate-500 mt-1">No target assigned yet</p>
        <p className="text-xs text-slate-400">Your manager will set it soon</p>
        <button
          onClick={() => navigate('/sales/my-targets')}
          className="mt-2 text-xs text-indigo-600 hover:underline flex items-center gap-1"
          data-testid="link-targets"
        >
          View targets page <ArrowRight className="h-3 w-3" />
        </button>
      </Card>
    );
  }

  // Live target data
  const ach = monthly.achievement || {};
  const revPct = ach.revenue_percentage || 0;
  const overallPct = ach.overall_percentage || 0;
  const targetRev = monthly.targets?.revenue || 0;
  const currentRev = ach.revenue || 0;
  const targetPa = monthly.targets?.pa_count || 0;
  const currentPa = ach.pa_count || 0;
  const daysLeft = monthly.days_remaining || 0;
  const gap = Math.max(0, targetRev - currentRev);
  const dailyReq = daysLeft > 0 && gap > 0 ? gap / daysLeft : 0;

  return (
    <Card className="p-4 border-t-4 border-t-indigo-500 hover:shadow-md transition cursor-pointer" data-testid="widget-target" onClick={() => navigate('/sales/my-targets')}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
            <Target className="h-4 w-4 text-indigo-600" />
          </div>
          <p className="text-sm font-bold text-slate-800">Monthly Target</p>
        </div>
        <Badge className="bg-indigo-600 text-white text-[10px] font-bold uppercase">{overallPct.toFixed(0)}%</Badge>
      </div>
      <p className="text-lg font-extrabold text-indigo-700 mt-1" data-testid="widget-target-amounts">
        {formatINR(currentRev)} <span className="text-slate-400 text-sm font-normal">/ {formatINR(targetRev)}</span>
      </p>
      <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden mt-1.5" data-testid="widget-target-progress">
        <div className={`h-full ${pctBarColor(revPct)} transition-all`} style={{ width: `${Math.min(100, revPct)}%` }} />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px]">
        <span className="text-slate-600 flex items-center gap-1">
          <span>{currentPa}/{targetPa} PAs</span>
        </span>
        <span className="text-slate-500 flex items-center gap-1"><Clock className="h-3 w-3" />{daysLeft}d left</span>
      </div>
      {dailyReq > 0 && (
        <p className="mt-1.5 text-[11px] text-orange-700 font-medium flex items-center gap-1" data-testid="widget-target-pace">
          <Flame className="h-3 w-3" /> Need {formatINR(Math.ceil(dailyReq))}/day
        </p>
      )}
      <button
        onClick={(e) => { e.stopPropagation(); navigate('/sales/my-targets'); }}
        className="mt-2 text-xs text-indigo-600 hover:underline flex items-center gap-1"
        data-testid="link-targets"
      >
        View details <ArrowRight className="h-3 w-3" />
      </button>
    </Card>
  );
}


export function CommissionWidget() {
  const navigate = useNavigate();
  return (
    <Card className="p-4 border-t-4 border-t-emerald-500 hover:shadow-md transition" data-testid="widget-commission">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
            <IndianRupee className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="text-sm font-bold text-slate-800">Commission Estimate</p>
        </div>
        {PHASE_BADGE('4C')}
      </div>
      <p className="text-xs text-slate-500 mt-1">Auto-calculate disabled</p>
      <p className="text-xs text-slate-400">Earnings update as PAs close</p>
      <button
        onClick={() => navigate('/sales/coming-soon?feature=commission')}
        className="mt-2 text-xs text-emerald-600 hover:underline flex items-center gap-1"
        data-testid="link-commission"
      >
        View commission structure <ArrowRight className="h-3 w-3" />
      </button>
    </Card>
  );
}


export function TeamRankWidget() {
  const navigate = useNavigate();
  return (
    <Card className="p-4 border-t-4 border-t-amber-500 hover:shadow-md transition" data-testid="widget-rank">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
            <Trophy className="h-4 w-4 text-amber-600" />
          </div>
          <p className="text-sm font-bold text-slate-800">Team Rank</p>
        </div>
        {PHASE_BADGE('4E')}
      </div>
      <p className="text-xs text-slate-500 mt-1">Leaderboard pending</p>
      <p className="text-xs text-slate-400">Compete with your team</p>
      <button
        onClick={() => navigate('/sales/coming-soon?feature=leaderboard')}
        className="mt-2 text-xs text-amber-600 hover:underline flex items-center gap-1"
        data-testid="link-leaderboard"
      >
        Leaderboard preview <ArrowRight className="h-3 w-3" />
      </button>
    </Card>
  );
}


export function FollowupsWidget() {
  const navigate = useNavigate();
  return (
    <Card className="p-4 border-t-4 border-t-rose-500 hover:shadow-md transition" data-testid="widget-followups">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center">
            <PhoneCall className="h-4 w-4 text-rose-600" />
          </div>
          <p className="text-sm font-bold text-slate-800">Today's Follow-ups</p>
        </div>
        {PHASE_BADGE('4D')}
      </div>
      <p className="text-xs text-slate-500 mt-1">Call log pending</p>
      <p className="text-xs text-slate-400">Schedule callbacks here</p>
      <button
        onClick={() => navigate('/partner?tab=pipeline')}
        className="mt-2 text-xs text-rose-600 hover:underline flex items-center gap-1"
        data-testid="link-followups"
      >
        Browse PAs needing follow-up <ArrowRight className="h-3 w-3" />
      </button>
    </Card>
  );
}


export default function SalesWidgetsRow() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3" data-testid="sales-widgets-row">
      <TargetWidget />
      <ExpressUsageWidget />
      <CommissionWidget />
      <TeamRankWidget />
      <FollowupsWidget />
    </div>
  );
}


/**
 * Phase 4B Part 2 — Express Usage Widget
 * Shows sales person's monthly Express Sale usage + remaining quota.
 */
export function ExpressUsageWidget() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/express/my-usage`, { headers: { Authorization: `Bearer ${token}` } });
        if (!cancelled) setData(r.data);
      } catch (_) {} finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <Card className="p-4 border-t-4 border-t-amber-500" data-testid="widget-express-loading">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center"><Zap className="h-4 w-4 text-amber-600 animate-pulse" /></div>
          <p className="text-sm font-bold text-slate-800">Express Sales</p>
        </div>
        <p className="text-xs text-slate-400">Loading…</p>
      </Card>
    );
  }
  if (!data) {
    return (
      <Card className="p-4 border-t-4 border-t-amber-500" data-testid="widget-express-error">
        <div className="flex items-center gap-2 mb-2"><Zap className="h-4 w-4 text-amber-600" /><p className="text-sm font-bold text-slate-800">Express Sales</p></div>
        <p className="text-xs text-slate-500">Unavailable</p>
      </Card>
    );
  }

  const used = data.used_this_month;
  const limit = data.limit_per_month;
  const isUnlimited = limit == null;
  const pct = isUnlimited ? 0 : (used / Math.max(1, limit)) * 100;
  const barColor = pct >= 100 ? 'bg-rose-500' : pct >= 80 ? 'bg-orange-500' : 'bg-amber-500';

  return (
    <Card className="p-4 border-t-4 border-t-amber-500 hover:shadow-md transition cursor-pointer" data-testid="widget-express" onClick={() => navigate('/partner?tab=pipeline')}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center">
            <Zap className="h-4 w-4 text-amber-600" />
          </div>
          <p className="text-sm font-bold text-slate-800">Express Sales</p>
        </div>
        {data.allowed
          ? <span className="text-[10px] font-bold uppercase text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-1.5 py-0.5">OK</span>
          : <span className="text-[10px] font-bold uppercase text-rose-700 bg-rose-50 border border-rose-200 rounded px-1.5 py-0.5">Limit</span>
        }
      </div>
      <p className="text-lg font-extrabold text-amber-700 mt-1" data-testid="widget-express-count">
        {used}
        <span className="text-slate-400 text-sm font-normal"> / {isUnlimited ? '∞' : limit}</span>
      </p>
      {!isUnlimited && (
        <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden mt-1.5">
          <div className={`h-full ${barColor} transition-all`} style={{ width: `${Math.min(100, pct)}%` }} />
        </div>
      )}
      <p className="mt-2 text-[11px] text-slate-600">
        {isUnlimited ? 'Unlimited Express quota' : `${data.remaining} remaining this month`}
      </p>
      <p className="text-[11px] text-slate-500 mt-0.5">{data.month_label}</p>
    </Card>
  );
}
