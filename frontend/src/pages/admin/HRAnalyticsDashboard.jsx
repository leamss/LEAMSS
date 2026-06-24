import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  ArrowLeft, Users, TrendingDown, Calendar, ClipboardCheck, BarChart3, RefreshCw, Download,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#0d9488', '#f97316', '#dc2626', '#0ea5e9', '#10b981', '#a855f7', '#eab308'];

/**
 * Phase 21 Slice 3 Day 2 — HR Analytics Dashboard.
 * KPI tiles + Recharts visualisations of headcount/attrition/leave/attendance/onboarding.
 */
export default function HRAnalyticsDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(365);

  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const load = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/hr-analytics/overview`, auth);
      setData(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (!token) { navigate('/'); return; } load(); /* eslint-disable-next-line */ }, []);

  const exportCSV = () => {
    if (!data) return;
    const rows = [
      ['Metric', 'Value'],
      ['Total headcount', data.headcount.total],
      ['Active', data.headcount.active],
      ['On leave', data.headcount.on_leave],
      ['Terminated', data.headcount.terminated],
      ['Attrition rate %', data.attrition.attrition_rate_pct],
      ['Late marks (30d)', data.attendance.late_marks_count],
      ['Onboarding completion %', data.onboarding.completion_rate_pct],
      [],
      ['Department', 'Total', 'Active'],
      ...data.departments.map(d => [d.department, d.total, d.active]),
      [],
      ['Leave Type', 'Requests', 'Days'],
      ...data.leaves.map(l => [l.leave_type, l.request_count, l.total_days]),
    ];
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `hr-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    toast.success('CSV exported');
  };

  if (loading || !data) return <div className="flex items-center justify-center h-screen text-slate-500">Loading HR analytics…</div>;

  const { headcount, attrition, attendance, onboarding, departments, leaves } = data;
  const statusPieData = [
    { name: 'Active', value: headcount.active },
    { name: 'On leave', value: headcount.on_leave },
    { name: 'Terminated', value: headcount.terminated },
  ];

  return (
    <div className="min-h-screen bg-slate-50" data-testid="hr-analytics-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/employees')} data-testid="hra-back">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-leamss-teal-600" />
              <div>
                <h1 className="text-lg font-bold text-slate-900">HR Analytics</h1>
                <p className="text-xs text-slate-500">Workforce KPIs · attrition · leave · onboarding</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Select value={String(periodDays)} onValueChange={v => setPeriodDays(Number(v))}>
              <SelectTrigger className="w-32 h-9" data-testid="hra-period"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
                <SelectItem value="180">Last 180 days</SelectItem>
                <SelectItem value="365">Last 12 months</SelectItem>
              </SelectContent>
            </Select>
            <Button size="sm" variant="outline" onClick={load} data-testid="hra-refresh"><RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh</Button>
            <Button size="sm" onClick={exportCSV} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="hra-export-csv">
              <Download className="h-3.5 w-3.5 mr-1" /> Export CSV
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-4">
        {/* KPI tiles */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="hra-kpis">
          <KPI title="Total Headcount" value={headcount.total} sub={`${headcount.active} active`} icon={Users} accent="leamss-teal" />
          <KPI title="Attrition (12 mo)" value={`${attrition.attrition_rate_pct}%`} sub={`${attrition.terminated_count} terminated`} icon={TrendingDown} accent="leamss-red" />
          <KPI title="Late Marks (30d)" value={attendance.late_marks_count} sub={`${attendance.total_attendance_logs} logs`} icon={Calendar} accent="leamss-orange" />
          <KPI title="Onboarding Done" value={`${onboarding.completion_rate_pct}%`} sub={`${onboarding.completed}/${onboarding.total_started}`} icon={ClipboardCheck} accent="emerald" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Department breakdown */}
          <Card className="p-4" data-testid="hra-dept-chart">
            <h3 className="font-semibold text-slate-900 text-sm mb-3 flex items-center gap-1.5">
              <Users className="h-4 w-4 text-leamss-teal-600" /> Department Headcount
            </h3>
            {departments.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No data</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={departments}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="department" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="total" fill="#0d9488" name="Total" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="active" fill="#f97316" name="Active" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* Status pie */}
          <Card className="p-4" data-testid="hra-status-pie">
            <h3 className="font-semibold text-slate-900 text-sm mb-3 flex items-center gap-1.5">
              <Users className="h-4 w-4 text-leamss-orange-600" /> Workforce Status
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={statusPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {statusPieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Card>

          {/* Leave patterns */}
          <Card className="p-4 lg:col-span-2" data-testid="hra-leave-chart">
            <h3 className="font-semibold text-slate-900 text-sm mb-3 flex items-center gap-1.5">
              <Calendar className="h-4 w-4 text-leamss-red-600" /> Leave Patterns ({periodDays}d, approved)
            </h3>
            {leaves.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No approved leaves in the period</p>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={leaves}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="leave_type" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="request_count" fill="#0d9488" name="Requests" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="total_days" fill="#dc2626" name="Total days" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </div>

        {/* Raw tables */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-4" data-testid="hra-dept-table">
            <h3 className="font-semibold text-slate-900 text-sm mb-3">Departments</h3>
            <div className="space-y-1.5">
              {departments.map(d => (
                <div key={d.department} className="flex items-center justify-between text-sm py-1.5 border-b border-slate-100">
                  <span className="text-slate-700">{d.department}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">Total {d.total}</Badge>
                    <Badge className="bg-leamss-teal-100 text-leamss-teal-700 text-[10px]">Active {d.active}</Badge>
                  </div>
                </div>
              ))}
              {departments.length === 0 && <p className="text-xs text-slate-400 italic">No departments seeded</p>}
            </div>
          </Card>

          <Card className="p-4" data-testid="hra-attendance-table">
            <h3 className="font-semibold text-slate-900 text-sm mb-3">Attendance Status (30d)</h3>
            <div className="space-y-1.5">
              {Object.keys(attendance.by_status || {}).map(s => (
                <div key={s} className="flex items-center justify-between text-sm py-1.5 border-b border-slate-100">
                  <span className="text-slate-700 capitalize">{s}</span>
                  <Badge variant="outline">{attendance.by_status[s]}</Badge>
                </div>
              ))}
              {Object.keys(attendance.by_status || {}).length === 0 && <p className="text-xs text-slate-400 italic">No attendance logs yet</p>}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function KPI({ title, value, sub, icon: Icon, accent }) {
  const color = {
    'leamss-teal': 'text-leamss-teal-600 bg-leamss-teal-50',
    'leamss-orange': 'text-leamss-orange-600 bg-leamss-orange-50',
    'leamss-red': 'text-leamss-red-600 bg-leamss-red-50',
    'emerald': 'text-emerald-600 bg-emerald-50',
  }[accent] || 'text-slate-600 bg-slate-100';
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{title}</span>
        <div className={`p-1.5 rounded ${color}`}><Icon className="h-3.5 w-3.5" /></div>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-[10px] text-slate-400 mt-1">{sub}</p>}
    </Card>
  );
}
