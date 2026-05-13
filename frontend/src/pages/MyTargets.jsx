/**
 * Phase 4B — Sales executive's "My Targets" page.
 *
 * Shows current month + current quarter targets with:
 *   - Big progress card per metric (Revenue + PA Count)
 *   - Days remaining + daily run-rate insights
 *   - History tab with last 6-12 months
 *
 * Read-only for sales executives. Admin/Manager set targets elsewhere.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Target, TrendingUp, Calendar, Clock, ArrowLeft, IndianRupee, Hash, Flame, AlertTriangle, Trophy, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(1)}K`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const pctColor = (p) => {
  if (p >= 150) return { bar: 'bg-gradient-to-r from-amber-400 via-yellow-500 to-amber-600', text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-300' };
  if (p >= 100) return { bar: 'bg-gradient-to-r from-emerald-500 to-green-600', text: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-300' };
  if (p >= 75) return { bar: 'bg-gradient-to-r from-blue-500 to-indigo-600', text: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-300' };
  if (p >= 50) return { bar: 'bg-gradient-to-r from-yellow-400 to-orange-500', text: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-300' };
  return { bar: 'bg-gradient-to-r from-rose-500 to-red-600', text: 'text-rose-700', bg: 'bg-rose-50', border: 'border-rose-300' };
};

const ProgressBar = ({ pct }) => {
  const colors = pctColor(pct);
  const w = Math.min(100, Math.max(0, pct));
  return (
    <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden" data-testid="progress-bar">
      <div className={`h-full ${colors.bar} transition-all duration-700 rounded-full`} style={{ width: `${w}%` }} />
    </div>
  );
};

const MetricCard = ({ icon: Icon, label, current, target, percent, daysLeft, unit = '', formatter = (v) => v, testId }) => {
  const colors = pctColor(percent);
  const gap = Math.max(0, target - current);
  const dailyRequired = daysLeft > 0 && gap > 0 ? gap / daysLeft : 0;
  return (
    <Card className={`p-5 border-2 ${colors.border} ${colors.bg}`} data-testid={testId}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-9 h-9 rounded-lg ${colors.bg} ring-2 ring-white flex items-center justify-center`}>
            <Icon className={`h-5 w-5 ${colors.text}`} />
          </div>
          <p className="text-sm font-bold text-slate-800">{label}</p>
        </div>
        <Badge className={`${colors.text} bg-white border ${colors.border} text-sm font-bold`}>
          {percent.toFixed(0)}%
        </Badge>
      </div>
      <div className="flex items-baseline gap-2 mb-2">
        <span className={`text-3xl font-extrabold ${colors.text}`}>{formatter(current)}</span>
        <span className="text-slate-500 text-sm">/ {formatter(target)}{unit}</span>
      </div>
      <ProgressBar pct={percent} />
      <div className="mt-3 flex items-center justify-between text-xs">
        {gap > 0 && daysLeft > 0 ? (
          <span className="text-slate-700 font-medium flex items-center gap-1">
            <Flame className="h-3.5 w-3.5 text-orange-500" />
            Need {formatter(Math.ceil(dailyRequired))}{unit}/day to hit target
          </span>
        ) : gap > 0 ? (
          <span className={`${colors.text} font-medium flex items-center gap-1`}>
            <AlertTriangle className="h-3.5 w-3.5" /> Period ended — {formatter(gap)}{unit} short
          </span>
        ) : (
          <span className="text-emerald-700 font-bold flex items-center gap-1">
            <Trophy className="h-3.5 w-3.5" /> Target achieved!
          </span>
        )}
        <span className="text-slate-500">{daysLeft} day{daysLeft !== 1 ? 's' : ''} left</span>
      </div>
    </Card>
  );
};

const TargetPanel = ({ title, target, periodLabel }) => {
  if (!target) {
    return (
      <Card className="p-10 text-center border-dashed border-2 border-slate-300" data-testid={`no-target-${title.toLowerCase().replace(/\s/g, '-')}`}>
        <Target className="h-12 w-12 text-slate-300 mx-auto mb-3" />
        <p className="text-slate-600 font-semibold">No {title} Set</p>
        <p className="text-sm text-slate-400 mt-1">Your manager or admin will assign a target soon.</p>
      </Card>
    );
  }
  const ach = target.achievement || {};
  const targetRev = target.targets?.revenue || 0;
  const targetPa = target.targets?.pa_count || 0;
  const daysLeft = target.days_remaining || 0;
  const overallColors = pctColor(ach.overall_percentage || 0);
  return (
    <Card className={`p-6 border-2 ${overallColors.border}`} data-testid={`target-panel-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold">{title}</p>
          <h2 className="text-2xl font-extrabold text-slate-800 mt-1">{periodLabel}</h2>
          {target.notes && <p className="text-sm text-slate-500 mt-1">{target.notes}</p>}
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wider text-slate-500 font-bold">Overall</p>
          <p className={`text-3xl font-extrabold ${overallColors.text}`}>{(ach.overall_percentage || 0).toFixed(0)}%</p>
          <Badge className={`${overallColors.text} bg-white border ${overallColors.border} mt-1 uppercase font-bold`}>
            {target.status}
          </Badge>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MetricCard
          icon={IndianRupee}
          label="Revenue Target"
          current={ach.revenue || 0}
          target={targetRev}
          percent={ach.revenue_percentage || 0}
          daysLeft={daysLeft}
          formatter={formatINR}
          testId="metric-revenue"
        />
        <MetricCard
          icon={Hash}
          label="PA Count Target"
          current={ach.pa_count || 0}
          target={targetPa}
          percent={ach.pa_count_percentage || 0}
          daysLeft={daysLeft}
          formatter={(v) => Math.round(v).toString()}
          unit=" PA"
          testId="metric-pa-count"
        />
      </div>
    </Card>
  );
};

const HistoryRow = ({ entry }) => {
  const ach = entry.achievement || {};
  const overallColors = pctColor(ach.overall_percentage || 0);
  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50" data-testid={`history-row-${entry.id}`}>
      <td className="p-3 text-sm font-medium text-slate-800">
        {(() => {
          const m = entry.period_month;
          const names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
          return `${names[m]} ${entry.period_year}`;
        })()}
      </td>
      <td className="p-3 text-sm text-slate-700">{formatINR(entry.targets?.revenue || 0)} / {entry.targets?.pa_count || 0} PAs</td>
      <td className="p-3 text-sm text-slate-700">{formatINR(ach.revenue || 0)} / {ach.pa_count || 0} PAs</td>
      <td className={`p-3 text-sm font-bold ${overallColors.text}`}>{(ach.overall_percentage || 0).toFixed(0)}%</td>
      <td className="p-3"><Badge className={`${overallColors.text} bg-white border ${overallColors.border} uppercase text-[10px]`}>{entry.status}</Badge></td>
    </tr>
  );
};

export default function MyTargets() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [monthly, setMonthly] = useState(null);
  const [quarterly, setQuarterly] = useState(null);
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
      setMonthly(my.data.monthly);
      setQuarterly(my.data.quarterly);
      setHistory(hist.data.history || []);
    } catch (e) {
      toast.error('Failed to load targets');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="my-targets-page">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/sales/dashboard')} className="p-2 rounded-lg hover:bg-slate-200 transition" data-testid="back-to-dashboard">
              <ArrowLeft className="h-5 w-5 text-slate-700" />
            </button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2">
                <Target className="h-7 w-7 text-indigo-600" /> My Targets
              </h1>
              <p className="text-sm text-slate-500 mt-1">Track your monthly & quarterly progress</p>
            </div>
          </div>
        </div>

        {loading ? (
          <Card className="p-12 text-center">
            <Sparkles className="h-8 w-8 text-indigo-300 mx-auto animate-pulse mb-2" />
            <p className="text-slate-500">Loading your targets…</p>
          </Card>
        ) : (
          <Tabs defaultValue="monthly" className="space-y-4" data-testid="targets-tabs">
            <TabsList className="grid w-full grid-cols-3 max-w-md" data-testid="period-tabs">
              <TabsTrigger value="monthly" data-testid="tab-monthly">Current Month</TabsTrigger>
              <TabsTrigger value="quarterly" data-testid="tab-quarterly">Current Quarter</TabsTrigger>
              <TabsTrigger value="history" data-testid="tab-history">History</TabsTrigger>
            </TabsList>

            <TabsContent value="monthly">
              <TargetPanel
                title="Monthly Target"
                target={monthly}
                periodLabel={monthly?.period_label || '—'}
              />
            </TabsContent>

            <TabsContent value="quarterly">
              <TargetPanel
                title="Quarterly Target"
                target={quarterly}
                periodLabel={quarterly?.period_label || '—'}
              />
            </TabsContent>

            <TabsContent value="history">
              <Card className="p-0 overflow-hidden" data-testid="history-table-card">
                <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                  <h3 className="font-bold text-slate-800 flex items-center gap-2">
                    <Calendar className="h-4 w-4" /> Last 12 Months
                  </h3>
                  <Badge variant="outline" className="text-slate-600">{history.length} entries</Badge>
                </div>
                {history.length === 0 ? (
                  <div className="p-10 text-center text-slate-400">No historical targets yet.</div>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200">
                        <th className="p-3 text-left text-xs uppercase tracking-wider text-slate-500 font-bold">Period</th>
                        <th className="p-3 text-left text-xs uppercase tracking-wider text-slate-500 font-bold">Target</th>
                        <th className="p-3 text-left text-xs uppercase tracking-wider text-slate-500 font-bold">Achieved</th>
                        <th className="p-3 text-left text-xs uppercase tracking-wider text-slate-500 font-bold">%</th>
                        <th className="p-3 text-left text-xs uppercase tracking-wider text-slate-500 font-bold">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((h) => <HistoryRow key={h.id} entry={h} />)}
                    </tbody>
                  </table>
                )}
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}
