/**
 * Phase 4B — Sales executive's "My Targets" page.
 *
 * Allows individual salespersons to track and monitor their own performance across:
 *   - Today (Daily)
 *   - This Week (Weekly)
 *   - Current Month (Monthly)
 *   - Current Quarter (Quarterly)
 *   - History (Past 12 Months)
 *
 * Displays Target vs Actual, Pending targets, Achievement %, Pace Insights for:
 *   - Leads
 *   - Calls
 *   - Follow-ups
 *   - Conversions
 *   - Revenue
 *   - Closed Deals
 *
 * Read-only for sales executives.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Target,
  TrendingUp,
  Calendar,
  Clock,
  ArrowLeft,
  IndianRupee,
  Hash,
  Flame,
  AlertTriangle,
  Trophy,
  Sparkles,
  PhoneCall,
  UserCheck,
  CheckCircle2,
  CalendarDays
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(1)}K`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const statusColors = {
  active: 'bg-blue-100 text-blue-800 border-blue-300',
  completed: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  exceeded: 'bg-amber-100 text-amber-800 border-amber-300',
  missed: 'bg-rose-100 text-rose-800 border-rose-300',
};

const pctColor = (p) => {
  if (p >= 150) return {
    bar: 'bg-gradient-to-r from-amber-400 via-yellow-500 to-amber-600',
    text: 'text-amber-800',
    bg: 'bg-amber-50/70',
    border: 'border-amber-300',
    badge: 'bg-amber-100 text-amber-900 border-amber-300',
  };
  if (p >= 100) return {
    bar: 'bg-gradient-to-r from-emerald-500 to-green-600',
    text: 'text-emerald-800',
    bg: 'bg-emerald-50/70',
    border: 'border-emerald-300',
    badge: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  };
  if (p >= 75) return {
    bar: 'bg-gradient-to-r from-blue-500 to-leamss-teal-600',
    text: 'text-blue-800',
    bg: 'bg-blue-50/70',
    border: 'border-blue-300',
    badge: 'bg-blue-100 text-blue-900 border-blue-300',
  };
  if (p >= 50) return {
    bar: 'bg-gradient-to-r from-orange-400 to-amber-500',
    text: 'text-orange-800',
    bg: 'bg-orange-50/70',
    border: 'border-orange-300',
    badge: 'bg-orange-100 text-orange-900 border-orange-300',
  };
  return {
    bar: 'bg-gradient-to-r from-rose-500 to-red-600',
    text: 'text-rose-800',
    bg: 'bg-rose-50/70',
    border: 'border-rose-300',
    badge: 'bg-rose-100 text-rose-900 border-rose-300',
  };
};

const ProgressBar = ({ pct }) => {
  const colors = pctColor(pct);
  const w = Math.min(100, Math.max(0, pct));
  return (
    <div className="h-2.5 w-full bg-slate-200 rounded-full overflow-hidden" data-testid="progress-bar">
      <div className={`h-full ${colors.bar} transition-all duration-700 rounded-full`} style={{ width: `${w}%` }} />
    </div>
  );
};

const MetricCard = ({
  icon: Icon,
  label,
  current = 0,
  target = 0,
  pending = 0,
  percent = 0,
  daysLeft = 0,
  unit = '',
  formatter = (v) => v,
  testId,
  targetStatus = 'active',
  periodType = 'monthly',
}) => {
  const colors = pctColor(percent);
  const calcPending = pending != null ? pending : Math.max(0, target - current);
  const dailyRequired = daysLeft > 0 && calcPending > 0 ? calcPending / daysLeft : 0;
  const isPeriodEnded = targetStatus === 'missed' || (targetStatus !== 'active' && daysLeft <= 0);

  return (
    <Card className={`p-4 border-2 ${colors.border} ${colors.bg} shadow-sm`} data-testid={testId}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-white ring-1 ring-slate-200 flex items-center justify-center">
            <Icon className={`h-4 w-4 ${colors.text}`} />
          </div>
          <p className="text-sm font-bold text-slate-800">{label}</p>
        </div>
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-black border shadow-xs ${colors.badge}`}
          data-testid="metric-percent-badge"
        >
          {percent.toFixed(0)}%
        </span>
      </div>

      <div className="flex items-baseline justify-between mb-2">
        <div className="flex items-baseline gap-1.5">
          <span className={`text-2xl font-black ${colors.text}`}>{formatter(current)}</span>
          <span className="text-slate-500 text-xs">/ {formatter(target)}{unit}</span>
        </div>
        <span className="text-xs text-rose-600 font-semibold">
          {calcPending > 0 ? `Pending: ${formatter(calcPending)}` : 'Completed'}
        </span>
      </div>

      <ProgressBar pct={percent} />

      <div className="mt-2.5 flex items-center justify-between text-[11px]">
        {calcPending <= 0 ? (
          <span className="text-emerald-700 font-bold flex items-center gap-1">
            <Trophy className="h-3 w-3" /> Target achieved!
          </span>
        ) : isPeriodEnded ? (
          <span className={`${colors.text} font-medium flex items-center gap-1`}>
            <AlertTriangle className="h-3 w-3" /> Period ended
          </span>
        ) : periodType === 'daily' || daysLeft <= 1 ? (
          <span className="text-slate-700 font-medium flex items-center gap-1">
            <Flame className="h-3 w-3 text-orange-500" />
            Need {formatter(Math.ceil(calcPending))}{unit} today
          </span>
        ) : (
          <span className="text-slate-700 font-medium flex items-center gap-1">
            <Flame className="h-3 w-3 text-orange-500" />
            Need {formatter(Math.ceil(dailyRequired))}{unit}/day
          </span>
        )}
        <span className="text-slate-500">
          {isPeriodEnded ? '0 days left' : periodType === 'daily' ? 'Ends today' : `${daysLeft} day${daysLeft !== 1 ? 's' : ''} left`}
        </span>
      </div>
    </Card>
  );
};

const TargetPanel = ({ title, target, periodLabel }) => {
  if (!target) {
    return (
      <Card className="p-12 text-center border-dashed border-2 border-slate-300" data-testid={`no-target-${title.toLowerCase().replace(/\s/g, '-')}`}>
        <Target className="h-12 w-12 text-slate-300 mx-auto mb-3" />
        <p className="text-slate-600 font-semibold text-base">No {title} Configured</p>
        <p className="text-sm text-slate-400 mt-1">Your manager or admin has not set targets for this period yet.</p>
      </Card>
    );
  }

  const tg = target.targets || {};
  const ach = target.achievement || {};
  const pnd = ach.pending || {};
  const daysLeft = target.days_remaining || 0;
  const overallColors = pctColor(ach.overall_percentage || 0);

  return (
    <Card className={`p-6 border-2 ${overallColors.border} bg-white shadow-sm space-y-6`} data-testid={`target-panel-${title.toLowerCase().replace(/\s/g, '-')}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b">
        <div>
          <Badge variant="outline" className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
            {title}
          </Badge>
          <h2 className="text-2xl font-black text-slate-800">{periodLabel}</h2>
          {target.notes && <p className="text-sm text-slate-500 mt-1">{target.notes}</p>}
        </div>

        <div className="flex items-center gap-4 sm:text-right">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500 font-bold">Overall Achievement</p>
            <p className={`text-3xl font-black ${overallColors.text}`}>
              {(ach.overall_percentage || 0).toFixed(0)}%
            </p>
          </div>
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border shadow-xs ${statusColors[target.status] || 'bg-slate-100 text-slate-700 border-slate-300'}`}
            data-testid="target-status-badge"
          >
            {target.status}
          </span>
        </div>
      </div>

      {/* Grid of metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Leads */}
        <MetricCard
          icon={UserCheck}
          label="Leads Target"
          current={ach.leads || 0}
          target={tg.leads || 0}
          pending={pnd.leads}
          percent={ach.leads_percentage || 0}
          daysLeft={daysLeft}
          formatter={(v) => Math.round(v).toString()}
          testId="metric-leads"
          targetStatus={target.status}
          periodType={target.period_type}
        />

        {/* Calls */}
        <MetricCard
          icon={PhoneCall}
          label="Calls Target"
          current={ach.calls || 0}
          target={tg.calls || 0}
          pending={pnd.calls}
          percent={ach.calls_percentage || 0}
          daysLeft={daysLeft}
          formatter={(v) => Math.round(v).toString()}
          testId="metric-calls"
          targetStatus={target.status}
          periodType={target.period_type}
        />

        {/* Follow-ups */}
        <MetricCard
          icon={Clock}
          label="Follow-ups Target"
          current={ach.follow_ups || 0}
          target={tg.follow_ups || 0}
          pending={pnd.follow_ups}
          percent={ach.follow_ups_percentage || 0}
          daysLeft={daysLeft}
          formatter={(v) => Math.round(v).toString()}
          testId="metric-follow-ups"
          targetStatus={target.status}
          periodType={target.period_type}
        />

        {/* Conversions */}
        <MetricCard
          icon={CheckCircle2}
          label="Conversions Target"
          current={ach.conversions || 0}
          target={tg.conversions || 0}
          pending={pnd.conversions}
          percent={ach.conversions_percentage || 0}
          daysLeft={daysLeft}
          formatter={(v) => Math.round(v).toString()}
          testId="metric-conversions"
          targetStatus={target.status}
          periodType={target.period_type}
        />

        {/* Revenue */}
        <MetricCard
          icon={IndianRupee}
          label="Revenue Target"
          current={ach.revenue || 0}
          target={tg.revenue || 0}
          pending={pnd.revenue}
          percent={ach.revenue_percentage || 0}
          daysLeft={daysLeft}
          formatter={formatINR}
          testId="metric-revenue"
          targetStatus={target.status}
          periodType={target.period_type}
        />

        {/* Closed Deals / PAs */}
        <MetricCard
          icon={Hash}
          label="Closed Deals Target"
          current={ach.pa_count || 0}
          target={tg.pa_count || 0}
          pending={pnd.pa_count}
          percent={ach.pa_count_percentage || 0}
          daysLeft={daysLeft}
          formatter={(v) => Math.round(v).toString()}
          unit=" deals"
          testId="metric-pa-count"
          targetStatus={target.status}
          periodType={target.period_type}
        />
      </div>
    </Card>
  );
};

const HistoryRow = ({ entry }) => {
  const ach = entry.achievement || {};
  const tg = entry.targets || {};
  const pnd = ach.pending || {};
  const overallColors = pctColor(ach.overall_percentage || 0);

  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50 transition text-xs" data-testid={`history-row-${entry.id}`}>
      <td className="p-3 font-semibold text-slate-800">
        {entry.period_label || `${entry.period_type} (${entry.period_year})`}
      </td>
      <td className="p-3">
        <Badge variant="outline" className="text-[10px] uppercase font-bold">{entry.period_type}</Badge>
      </td>
      <td className="p-3 text-slate-700">
        Leads: {ach.leads || 0}/{tg.leads || 0} · Calls: {ach.calls || 0}/{tg.calls || 0}
        <br />
        F-ups: {ach.follow_ups || 0}/{tg.follow_ups || 0} · Conv: {ach.conversions || 0}/{tg.conversions || 0}
      </td>
      <td className="p-3 text-slate-700 font-medium">
        {formatINR(ach.revenue || 0)} <span className="text-slate-400">/ {formatINR(tg.revenue || 0)}</span>
      </td>
      <td className={`p-3 font-black text-sm ${overallColors.text}`}>
        {(ach.overall_percentage || 0).toFixed(0)}%
      </td>
      <td className="p-3">
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full uppercase text-[10px] font-bold border ${statusColors[entry.status] || 'bg-slate-100 text-slate-700 border-slate-300'}`}
          data-testid="history-status-badge"
        >
          {entry.status}
        </span>
      </td>
    </tr>
  );
};

export default function MyTargets() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [daily, setDaily] = useState(null);
  const [weekly, setWeekly] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [quarterly, setQuarterly] = useState(null);
  const [yearly, setYearly] = useState(null);
  const [history, setHistory] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [my, hist] = await Promise.all([
        axios.get(`${API}/sales/targets/my`, { headers }),
        axios.get(`${API}/sales/targets/my/history?months=12`, { headers }),
      ]);
      setDaily(my.data.daily);
      setWeekly(my.data.weekly);
      setMonthly(my.data.monthly);
      setQuarterly(my.data.quarterly);
      setYearly(my.data.yearly);
      setHistory(hist.data.history || []);
    } catch (e) {
      toast.error('Failed to load targets');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      const role = localStorage.getItem('role') || '';
      if (role.includes('admin') || role === 'sales_manager') {
        navigate('/admin/sales/targets');
      } else {
        navigate('/sales/my-crm');
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="my-targets-page">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBack}
              className="p-2 rounded-lg hover:bg-slate-200 transition text-slate-700"
              title="Go Back"
              data-testid="back-to-dashboard"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <Target className="h-7 w-7 text-leamss-teal-600" /> My Targets & Performance
              </h1>
              <p className="text-sm text-slate-500 mt-1">
                Real-time tracking of your daily, weekly, monthly and quarterly sales activity targets
              </p>
            </div>
          </div>
        </div>

        {loading ? (
          <Card className="p-12 text-center">
            <Sparkles className="h-8 w-8 text-leamss-teal-300 mx-auto animate-pulse mb-2" />
            <p className="text-slate-500">Loading your targets and activity performance…</p>
          </Card>
        ) : (
          <Tabs defaultValue={daily ? "daily" : "monthly"} className="space-y-4" data-testid="targets-tabs">
            <TabsList className="grid w-full grid-cols-6 max-w-3xl bg-slate-200/70 p-1" data-testid="period-tabs">
              <TabsTrigger value="daily" data-testid="tab-daily">Today (Daily)</TabsTrigger>
              <TabsTrigger value="weekly" data-testid="tab-weekly">This Week</TabsTrigger>
              <TabsTrigger value="monthly" data-testid="tab-monthly">Current Month</TabsTrigger>
              <TabsTrigger value="quarterly" data-testid="tab-quarterly">Quarterly</TabsTrigger>
              <TabsTrigger value="yearly" data-testid="tab-yearly">Yearly (Annual)</TabsTrigger>
              <TabsTrigger value="history" data-testid="tab-history">History</TabsTrigger>
            </TabsList>

            <TabsContent value="daily">
              <TargetPanel
                title="Daily Target"
                target={daily}
                periodLabel={daily?.period_label || 'Today'}
              />
            </TabsContent>

            <TabsContent value="weekly">
              <TargetPanel
                title="Weekly Target"
                target={weekly}
                periodLabel={weekly?.period_label || 'This Week'}
              />
            </TabsContent>

            <TabsContent value="monthly">
              <TargetPanel
                title="Monthly Target"
                target={monthly}
                periodLabel={monthly?.period_label || 'This Month'}
              />
            </TabsContent>

            <TabsContent value="quarterly">
              <TargetPanel
                title="Quarterly Target"
                target={quarterly}
                periodLabel={quarterly?.period_label || 'This Quarter'}
              />
            </TabsContent>

            <TabsContent value="yearly">
              <TargetPanel
                title="Yearly Target"
                target={yearly}
                periodLabel={yearly?.period_label || 'Current Year'}
              />
            </TabsContent>

            <TabsContent value="history">
              <Card className="p-0 overflow-hidden shadow-sm" data-testid="history-table-card">
                <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                  <h3 className="font-bold text-slate-800 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-slate-600" /> Target History (Past 12 Months)
                  </h3>
                  <Badge variant="outline" className="text-xs">{history.length} records</Badge>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead className="bg-slate-100/70 border-b text-[11px] uppercase tracking-wider text-slate-600 font-bold">
                      <tr>
                        <th className="p-3">Period</th>
                        <th className="p-3">Type</th>
                        <th className="p-3">Activity Targets (Achieved/Target)</th>
                        <th className="p-3">Revenue</th>
                        <th className="p-3">Overall %</th>
                        <th className="p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {history.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-slate-400">
                            No past target history recorded yet.
                          </td>
                        </tr>
                      ) : (
                        history.map((entry) => <HistoryRow key={entry.id} entry={entry} />)
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}
