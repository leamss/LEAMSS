import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ClipboardList, Briefcase, Users, TrendingUp, ArrowRight,
  Sparkles, AlertCircle, CheckCircle, UserCheck, Package, DollarSign, Shield
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

const ActionCard = ({ icon: Icon, title, count, description, cta, color, onClick, testId, highlight }) => (
  <Card
    className={`p-5 border-0 shadow-lg bg-gradient-to-br ${color} text-white cursor-pointer transition-all hover:shadow-xl hover:-translate-y-0.5 ${highlight ? 'ring-2 ring-pink-300 ring-offset-2 animate-pulse' : ''}`}
    onClick={onClick}
    data-testid={testId}
  >
    <div className="flex items-start justify-between">
      <div>
        <Icon className="h-8 w-8 opacity-80 mb-3" />
        <p className="text-4xl font-bold tabular-nums">{count}</p>
        <p className="text-sm font-semibold mt-1">{title}</p>
        <p className="text-xs opacity-80 mt-1 leading-relaxed">{description}</p>
      </div>
      <ArrowRight className="h-5 w-5 opacity-60" />
    </div>
    <div className="flex items-center gap-1 text-xs font-semibold mt-3 pt-3 border-t border-white/20">
      {cta} <ArrowRight className="h-3 w-3" />
    </div>
  </Card>
);

export default function AdminHome({ user, onNavigate }) {
  const [data, setData] = useState({
    first_approval_pending: 0,
    second_approval_pending: 0,
    unassigned_cases: 0,
    active_cases: 0,
    total_users: 0,
    total_partners: 0,
    total_revenue: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [queueRes, casesRes, usersRes] = await Promise.all([
          axios.get(`${API}/pre-assessment/admin/queue`, getAuth()).catch(() => ({ data: [] })),
          axios.get(`${API}/cases`, getAuth()).catch(() => ({ data: [] })),
          axios.get(`${API}/users`, getAuth()).catch(() => ({ data: [] })),
        ]);
        const queue = queueRes.data || [];
        const cases = casesRes.data || [];
        const users = usersRes.data || [];
        const first_approval_pending = queue.filter(p => ['documents_submitted', 'under_review'].includes(p.stage)).length;
        const second_approval_pending = queue.filter(p => p.stage === 'proposal_paid').length;
        const unassigned_cases = cases.filter(c => !c.case_manager_id).length;
        const active_cases = cases.filter(c => c.status === 'active').length;
        const total_partners = users.filter(u => u.role === 'partner').length;
        setData({
          first_approval_pending, second_approval_pending, unassigned_cases,
          active_cases, total_users: users.length, total_partners, total_revenue: 0,
        });
      } catch (e) { /* graceful */ }
      setLoading(false);
    })();
  }, []);

  const greeting = (() => {
    const h = new Date().getHours();
    return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
  })();
  const totalActions = data.first_approval_pending + data.second_approval_pending + data.unassigned_cases;

  return (
    <div className="space-y-6" data-testid="admin-home">
      {/* Greeting */}
      <div className="bg-gradient-to-r from-[#2a777a] to-[#1f5c5f] rounded-2xl p-6 text-white shadow-xl">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <p className="text-sm opacity-80">{greeting}, Admin 🛡️</p>
            <h1 className="text-3xl font-bold mt-1">{user?.name?.split(' ')[0] || 'there'}!</h1>
            <p className="text-sm opacity-90 mt-2">
              {totalActions > 0
                ? <>You have <span className="font-bold text-[#f7620b] bg-white px-1.5 py-0.5 rounded">{totalActions}</span> items requiring your approval.</>
                : <>All clear. System is operating smoothly.</>
              }
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => onNavigate?.('users')} variant="outline" className="border-white/30 text-white hover:bg-white/10">
              <Users className="h-4 w-4 mr-1.5" /> Users
            </Button>
            <Button onClick={() => onNavigate?.('dashboard')} className="bg-[#f7620b] hover:bg-[#e55a09] shadow-lg">
              <TrendingUp className="h-4 w-4 mr-1.5" /> Classic Dashboard
            </Button>
          </div>
        </div>
      </div>

      {/* Action cards */}
      <div>
        <h2 className="text-lg font-bold text-slate-800 mb-3 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[#f7620b]" /> Pending approvals
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.first_approval_pending > 0 && (
            <ActionCard
              icon={ClipboardList}
              title="1st Approval needed"
              count={data.first_approval_pending}
              description="Pre-Assessments awaiting eligibility review."
              cta="Review queue"
              color="from-purple-500 to-purple-600"
              onClick={() => onNavigate?.('pre-assessments')}
              testId="action-first-approval"
              highlight
            />
          )}
          {data.second_approval_pending > 0 && (
            <ActionCard
              icon={CheckCircle}
              title="2nd Approval needed"
              count={data.second_approval_pending}
              description="Main fee received — activate case & assign CM."
              cta="Activate cases"
              color="from-[#f7620b] to-orange-600"
              onClick={() => onNavigate?.('pre-assessments')}
              testId="action-second-approval"
              highlight
            />
          )}
          {data.unassigned_cases > 0 && (
            <ActionCard
              icon={UserCheck}
              title="Cases unassigned"
              count={data.unassigned_cases}
              description="Active cases without a Case Manager yet."
              cta="Assign CM"
              color="from-blue-500 to-blue-600"
              onClick={() => onNavigate?.('cases')}
              testId="action-unassigned"
            />
          )}
          {totalActions === 0 && !loading && (
            <Card className="md:col-span-4 p-8 text-center bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
              <CheckCircle className="h-12 w-12 text-emerald-500 mx-auto mb-2" />
              <h3 className="font-bold text-slate-800">All caught up! 🎉</h3>
              <p className="text-sm text-slate-500 mt-1">No pending approvals at the moment.</p>
            </Card>
          )}
        </div>
      </div>

      {/* Org snapshot */}
      <div>
        <h2 className="text-lg font-bold text-slate-800 mb-3">Organisation snapshot</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { icon: Briefcase, label: 'Active Cases', value: data.active_cases, color: 'text-emerald-600 bg-emerald-50' },
            { icon: Users, label: 'Total Users', value: data.total_users, color: 'text-blue-600 bg-blue-50' },
            { icon: Shield, label: 'Partners', value: data.total_partners, color: 'text-[#2a777a] bg-[#2a777a]/10' },
            { icon: AlertCircle, label: 'Needs Action', value: totalActions, color: 'text-[#f7620b] bg-[#f7620b]/10' },
          ].map(s => (
            <Card key={s.label} className="p-4 border-slate-200">
              <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${s.color} mb-2`}>
                <s.icon className="h-5 w-5" />
              </div>
              <p className="text-2xl font-bold text-slate-800 tabular-nums">{s.value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
            </Card>
          ))}
        </div>
      </div>

      {/* Quick access */}
      <div>
        <h2 className="text-lg font-bold text-slate-800 mb-3">Quick access</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { icon: ClipboardList, label: 'Pre-Assessments', tab: 'pre-assessments' },
            { icon: Briefcase, label: 'All Cases', tab: 'cases' },
            { icon: Users, label: 'Users', tab: 'users' },
            { icon: Package, label: 'Upsell Bundles', tab: 'upsell-bundles' },
            { icon: DollarSign, label: 'Marketing', tab: 'marketing' },
            { icon: TrendingUp, label: 'Reports', tab: 'report-builder' },
          ].map(x => (
            <Card
              key={x.tab}
              onClick={() => onNavigate?.(x.tab)}
              className="p-4 cursor-pointer hover:shadow-md hover:border-[#2a777a]/30 transition-all border-slate-200"
              data-testid={`quick-${x.tab}`}
            >
              <x.icon className="h-5 w-5 text-[#2a777a] mb-2" />
              <p className="text-sm font-semibold text-slate-800">{x.label}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
