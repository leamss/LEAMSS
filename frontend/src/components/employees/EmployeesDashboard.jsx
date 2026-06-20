import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Users, UserCheck, Coffee, UserPlus, TrendingUp, Building2, Network, Plus, ArrowRight } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const StatCard = ({ icon: Icon, label, value, color, accent, testid }) => (
  <Card className={`p-5 border-l-4 ${color} hover:shadow-md transition-shadow`} data-testid={testid}>
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs uppercase tracking-wider text-slate-500 font-medium">{label}</p>
        <p className={`text-3xl font-bold mt-2 ${accent}`}>{value}</p>
      </div>
      <div className={`p-3 rounded-xl bg-slate-50`}>
        <Icon className={`h-6 w-6 ${accent}`} />
      </div>
    </div>
  </Card>
);

const DeptBar = ({ name, count, total, color }) => {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-sm">
        <span className="font-medium text-slate-700 capitalize">{name}</span>
        <span className="text-slate-500 text-xs tabular-nums">{count} {count === 1 ? 'person' : 'people'}</span>
      </div>
      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color || '#0891b2' }} />
      </div>
    </div>
  );
};

const DEPT_COLORS = {
  admin: '#7c3aed', sales: '#16a34a', marketing: '#ea580c', operations: '#0891b2',
  hr: '#db2777', accounts: '#0d9488', it: '#475569', compliance: '#b91c1c',
};

export default function EmployeesDashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token');

  useEffect(() => {
    const load = async () => {
      try {
        const [s, r] = await Promise.all([
          axios.get(`${API}/employees/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/employees/recent?limit=5`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setStats(s.data);
        setRecent(r.data);
      } catch (e) {
        console.error('Failed to load dashboard:', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Card key={i} className="p-5 h-28 animate-pulse bg-slate-50" />)}
        </div>
      </div>
    );
  }

  if (!stats) return <Card className="p-6">No data available</Card>;

  return (
    <div className="space-y-6 p-6" data-testid="employees-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Employees Dashboard</h1>
          <p className="text-slate-500 mt-1 text-sm">Manage your internal workforce across {stats.department_breakdown.length} active departments</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => onNavigate('emp-departments')} variant="outline" data-testid="quick-departments-btn">
            <Building2 className="h-4 w-4 mr-2" /> Departments
          </Button>
          <Button onClick={() => onNavigate('emp-org-chart')} variant="outline" data-testid="quick-org-btn">
            <Network className="h-4 w-4 mr-2" /> Org Chart
          </Button>
          <Button onClick={() => onNavigate('emp-add')} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="quick-add-employee-btn">
            <Plus className="h-4 w-4 mr-2" /> Add Employee
          </Button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Total Employees" value={stats.total} color="border-l-leamss-teal-500" accent="text-leamss-teal-600" testid="stat-total" />
        <StatCard icon={UserCheck} label="Active" value={stats.active} color="border-l-emerald-500" accent="text-emerald-600" testid="stat-active" />
        <StatCard icon={Coffee} label="On Leave" value={stats.on_leave} color="border-l-amber-500" accent="text-amber-600" testid="stat-onleave" />
        <StatCard icon={UserPlus} label="New This Month" value={stats.new_this_month} color="border-l-leamss-red-500" accent="text-leamss-red-600" testid="stat-new" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Department breakdown */}
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-teal-700" /> Department Breakdown
            </h3>
            <button onClick={() => onNavigate('emp-departments')} className="text-xs text-teal-700 hover:underline flex items-center gap-1">
              See all <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          {stats.department_breakdown.length === 0 ? (
            <p className="text-slate-500 text-sm">No departments populated yet</p>
          ) : (
            <div className="space-y-4">
              {stats.department_breakdown.map(d => (
                <DeptBar key={d.department || 'unknown'} name={d.department || 'Unassigned'} count={d.count} total={stats.total} color={DEPT_COLORS[d.department] || '#64748b'} />
              ))}
            </div>
          )}
        </Card>

        {/* Recent joiners */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2 mb-4">
            <UserPlus className="h-5 w-5 text-teal-700" /> Recently Joined
          </h3>
          {recent.length === 0 ? (
            <p className="text-slate-500 text-sm">No recent joiners</p>
          ) : (
            <div className="space-y-3">
              {recent.map(u => (
                <div key={u.id} className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded-md cursor-pointer" onClick={() => onNavigate('emp-list', { employeeId: u.id })} data-testid={`recent-emp-${u.id}`}>
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-500 to-leamss-teal-600 flex items-center justify-center text-white font-semibold text-sm">
                    {(u.name || '?').charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 text-sm truncate">{u.name}</p>
                    <p className="text-xs text-slate-500 truncate">{u.designation || u.rbac_role || '—'} · {u.department || '—'}</p>
                  </div>
                  <Badge variant="outline" className="text-xs">{u.employee_id || '—'}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
