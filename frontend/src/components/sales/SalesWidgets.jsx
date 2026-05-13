import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';
import { Target, IndianRupee, Trophy, PhoneCall, ArrowRight } from 'lucide-react';

/**
 * Internal-only widgets shown ABOVE the PA pipeline on /sales/dashboard.
 * Each widget is a "Coming in Phase 4X" placeholder — wired up later.
 */

const PHASE_BADGE = (phase) => (
  <Badge className="bg-amber-100 text-amber-800 text-[10px] font-bold uppercase tracking-wide">
    Coming in Phase {phase}
  </Badge>
);


export function TargetWidget() {
  const navigate = useNavigate();
  return (
    <Card className="p-4 border-t-4 border-t-indigo-500 hover:shadow-md transition" data-testid="widget-target">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
            <Target className="h-4 w-4 text-indigo-600" />
          </div>
          <p className="text-sm font-bold text-slate-800">Monthly Target</p>
        </div>
        {PHASE_BADGE('4B')}
      </div>
      <p className="text-xs text-slate-500 mt-1">Setup pending</p>
      <p className="text-xs text-slate-400">Your targets will appear here</p>
      <button
        onClick={() => navigate('/sales/coming-soon?feature=targets')}
        className="mt-2 text-xs text-indigo-600 hover:underline flex items-center gap-1"
        data-testid="link-targets"
      >
        View target structure <ArrowRight className="h-3 w-3" />
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
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" data-testid="sales-widgets-row">
      <TargetWidget />
      <CommissionWidget />
      <TeamRankWidget />
      <FollowupsWidget />
    </div>
  );
}
