import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Target,
  IndianRupee,
  Trophy,
  PhoneCall,
  UserCheck,
  CheckCircle2,
  Clock,
  ArrowRight,
  Sparkles,
  Flame,
  Calendar,
  Layers,
  ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(1)}L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(0)}K`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'completed':
      return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    case 'exceeded':
      return 'bg-amber-100 text-amber-800 border-amber-300';
    case 'active':
      return 'bg-blue-100 text-blue-800 border-blue-300';
    case 'missed':
      return 'bg-rose-100 text-rose-800 border-rose-300';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-300';
  }
};

const getPctColor = (pct) => {
  if (pct >= 100) return {
    bar: 'bg-emerald-500',
    text: 'text-emerald-700',
    badge: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  };
  if (pct >= 75) return {
    bar: 'bg-blue-500',
    text: 'text-blue-700',
    badge: 'bg-blue-100 text-blue-900 border-blue-300',
  };
  if (pct >= 50) return {
    bar: 'bg-amber-500',
    text: 'text-amber-700',
    badge: 'bg-amber-100 text-amber-900 border-amber-300',
  };
  return {
    bar: 'bg-rose-500',
    text: 'text-rose-700',
    badge: 'bg-rose-100 text-rose-900 border-rose-300',
  };
};

function PeriodCard({ title, subtitle, icon: Icon, periodKey, target, onNavigate }) {
  const ach = target?.achievement || {};
  const tg = target?.targets || {};
  const pnd = ach.pending || {};
  const overallPct = ach.overall_percentage || 0;
  const colors = getPctColor(overallPct);
  const daysLeft = target?.days_remaining != null ? target.days_remaining : 0;
  const isDaily = periodKey === 'daily';
  const hasTarget = Boolean(target && (tg.revenue || tg.leads || tg.calls || tg.follow_ups || tg.pa_count || tg.conversions));

  return (
    <Card
      className="p-4 border border-slate-200/80 bg-white hover:shadow-md transition cursor-pointer flex flex-col justify-between group"
      onClick={() => onNavigate(periodKey)}
    >
      <div>
        {/* Card Header */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-slate-100 group-hover:bg-teal-50 group-hover:text-teal-600 flex items-center justify-center transition">
              <Icon className="h-4 w-4 text-slate-600 group-hover:text-teal-600" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-700">{title}</p>
              <p className="text-[11px] text-slate-400 font-medium">{target?.period_label || subtitle}</p>
            </div>
          </div>
          {hasTarget ? (
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-black border shadow-2xs ${colors.badge}`}>
              {overallPct.toFixed(0)}%
            </span>
          ) : (
            <Badge variant="outline" className="text-[10px] text-slate-400 font-semibold">
              Not Set
            </Badge>
          )}
        </div>

        {/* Progress Bar */}
        <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden mb-3">
          <div
            className={`h-full ${colors.bar} transition-all duration-700 rounded-full`}
            style={{ width: `${Math.min(100, Math.max(0, overallPct))}%` }}
          />
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs mb-3 bg-slate-50/70 p-2.5 rounded-lg border border-slate-100">
          <div className="flex items-center justify-between">
            <span className="text-slate-500 flex items-center gap-1">
              <PhoneCall className="h-3 w-3 text-slate-400" /> Calls
            </span>
            <span className="font-bold text-slate-800">
              {ach.calls || 0}<span className="text-slate-400 font-normal">/{tg.calls || 0}</span>
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500 flex items-center gap-1">
              <Clock className="h-3 w-3 text-slate-400" /> Follow-ups
            </span>
            <span className="font-bold text-slate-800">
              {ach.follow_ups || 0}<span className="text-slate-400 font-normal">/{tg.follow_ups || 0}</span>
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500 flex items-center gap-1">
              <UserCheck className="h-3 w-3 text-slate-400" /> Leads
            </span>
            <span className="font-bold text-slate-800">
              {ach.leads || 0}<span className="text-slate-400 font-normal">/{tg.leads || 0}</span>
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-slate-400" /> Deals
            </span>
            <span className="font-bold text-slate-800">
              {ach.pa_count || 0}<span className="text-slate-400 font-normal">/{tg.pa_count || 0}</span>
            </span>
          </div>
        </div>

        {/* Revenue Progress */}
        <div className="flex items-center justify-between text-xs px-1 mb-2">
          <span className="text-slate-500 flex items-center gap-1">
            <IndianRupee className="h-3 w-3 text-slate-400" /> Revenue
          </span>
          <span className="font-black text-slate-800">
            {formatINR(ach.revenue || 0)}
            <span className="text-slate-400 font-normal text-[11px]"> / {formatINR(tg.revenue || 0)}</span>
          </span>
        </div>
      </div>

      {/* Card Footer */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
        <span className="flex items-center gap-1 font-medium">
          {overallPct >= 100 ? (
            <span className="text-emerald-700 font-bold flex items-center gap-1">
              <Trophy className="h-3 w-3 text-emerald-600" /> Goal Achieved!
            </span>
          ) : isDaily ? (
            <span className="text-amber-700 font-medium flex items-center gap-1">
              <Clock className="h-3 w-3 text-amber-500" /> Ends today
            </span>
          ) : daysLeft > 0 ? (
            <span className="text-slate-600 flex items-center gap-1">
              <Clock className="h-3 w-3 text-slate-400" /> {daysLeft} days left
            </span>
          ) : (
            <span className="text-slate-400">Period ended</span>
          )}
        </span>
        <span className="text-teal-600 font-semibold group-hover:translate-x-0.5 transition flex items-center gap-0.5">
          Details <ChevronRight className="h-3 w-3" />
        </span>
      </div>
    </Card>
  );
}

export default function SalesTargetsOverviewHub() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({ daily: null, weekly: null, monthly: null, yearly: null });

  useEffect(() => {
    let cancelled = false;
    const fetchTargets = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await axios.get(`${API}/sales/targets/my`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!cancelled && res.data) {
          setData(res.data);
        }
      } catch (err) {
        // Silently catch if targets not accessible
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchTargets();
    return () => { cancelled = true; };
  }, []);

  const handleNavigate = (periodTab) => {
    navigate('/sales/my-targets');
  };

  if (loading) {
    return (
      <Card className="p-5 mb-6 border border-slate-200 bg-white">
        <div className="flex items-center gap-2 text-slate-400 text-xs animate-pulse">
          <Sparkles className="h-4 w-4 text-teal-500" />
          <span>Loading targets & performance for Daily, Weekly, Monthly, and Yearly…</span>
        </div>
      </Card>
    );
  }

  return (
    <div className="mb-6 space-y-3" data-testid="all-targets-performance-hub">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-teal-600 to-emerald-500 text-white flex items-center justify-center shadow-xs">
            <Target className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-black text-slate-800">
              Targets & Performance Hub
            </h3>
            <p className="text-xs text-slate-500">
              Real-time tracking of your Daily, Weekly, Monthly, and Yearly sales goals
            </p>
          </div>
        </div>

        <button
          onClick={() => navigate('/sales/my-targets')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-teal-700 bg-teal-50 hover:bg-teal-100 transition border border-teal-200 self-start sm:self-auto shadow-2xs"
          data-testid="link-view-all-targets"
        >
          <span>Open Full Performance Hub</span>
          <ArrowRight className="h-3 w-3" />
        </button>
      </div>

      {/* 4 Cards Grid for Daily, Weekly, Monthly, and Yearly */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <PeriodCard
          title="Daily Target"
          subtitle="Today's goals"
          icon={Flame}
          periodKey="daily"
          target={data.daily}
          onNavigate={handleNavigate}
        />
        <PeriodCard
          title="Weekly Target"
          subtitle="This week"
          icon={Calendar}
          periodKey="weekly"
          target={data.weekly}
          onNavigate={handleNavigate}
        />
        <PeriodCard
          title="Monthly Target"
          subtitle="Current month"
          icon={Target}
          periodKey="monthly"
          target={data.monthly}
          onNavigate={handleNavigate}
        />
        <PeriodCard
          title="Yearly Target"
          subtitle="Annual goals"
          icon={Trophy}
          periodKey="yearly"
          target={data.yearly}
          onNavigate={handleNavigate}
        />
      </div>
    </div>
  );
}
