import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import DashboardShell from '@/components/DashboardShell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboard, Users, Building2, Network, UserPlus, UsersRound,
  Settings as SettingsIcon, Calendar, FileText, ShieldCheck, History,
  Megaphone, Target, Mail, Gift, Trophy, BarChart3,
  Server, Globe, Search,
  User, CheckSquare, Coffee, Receipt, BookOpen,
  ArrowRight, Sparkles, Clock,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ─────────────────────────────────────────────────────────────
// Card group definitions (cards shown in main area per group)
// ─────────────────────────────────────────────────────────────
const GROUP_CARDS = {
  employees: {
    label: 'Employees',
    accent: 'leamss-teal',
    icon: UsersRound,
    description: 'Manage internal workforce, departments, and org structure.',
    cards: [
      { id: 'emp-dashboard', icon: LayoutDashboard, title: 'Dashboard', desc: 'Workforce overview & stats', route: '/admin/employees' },
      { id: 'emp-list', icon: Users, title: 'All Employees', desc: 'Search, filter, manage', route: '/admin/employees' },
      { id: 'emp-org', icon: Network, title: 'Org Chart', desc: 'Reports-to hierarchy', route: '/admin/employees' },
      { id: 'emp-departments', icon: Building2, title: 'Departments', desc: 'Eight departments + heads', route: '/admin/employees' },
      { id: 'emp-add', icon: UserPlus, title: 'Add Employee', desc: 'Three-step onboarding form', route: '/admin/employees' },
    ],
  },
  hr: {
    label: 'HR',
    accent: 'sky',
    icon: ShieldCheck,
    description: 'Attendance rules, leave policies, holidays, approvers, audit.',
    cards: [
      { id: 'hr-settings', icon: SettingsIcon, title: 'Attendance Settings', desc: 'Office hours, late marks, sandwich', route: '/admin/hr/settings' },
      { id: 'hr-holidays', icon: Calendar, title: 'Holiday Calendar', desc: 'Manage public + optional', route: '/admin/hr/holidays' },
      { id: 'hr-leave-types', icon: FileText, title: 'Leave Types', desc: 'Policies, quotas, carry-forward', route: '/admin/hr/leave-types' },
      { id: 'hr-approvers', icon: Users, title: 'Approver Config', desc: 'L1, Final, Department-wise', route: '/admin/hr/approvers' },
      { id: 'hr-audit', icon: History, title: 'Audit Log', desc: 'Policy changes trail', route: '/admin/hr/audit' },
    ],
  },
  marketing: {
    label: 'Marketing',
    accent: 'leamss-orange',
    icon: Megaphone,
    description: 'Leads, campaigns, testimonials, promotions, scorecards.',
    cards: [
      { id: 'mkt-overview', icon: BarChart3, title: 'Dashboard', desc: 'Pipeline & funnel overview', route: '/admin/marketing' },
      { id: 'mkt-leads', icon: Target, title: 'Lead CRM', desc: 'Capture, qualify, follow-up', route: '/admin/marketing' },
      { id: 'mkt-campaigns', icon: Mail, title: 'Campaigns', desc: 'Email blasts, drip flows', route: '/admin/marketing' },
      { id: 'mkt-promos', icon: Gift, title: 'Promo Codes', desc: 'Discounts & coupons', route: '/admin/marketing' },
      { id: 'mkt-scorecards', icon: FileText, title: 'Scorecards', desc: 'Eligibility quiz leads', route: '/admin/marketing' },
    ],
  },
  it: {
    label: 'IT',
    accent: 'slate',
    icon: Server,
    description: 'Website audit, SEO monitor, dev tasks (Slice 4 — coming soon).',
    cards: [
      { id: 'it-site-audit', icon: Globe, title: 'Website Audit', desc: 'Broken links, missing alt, perf', route: null, soon: true },
      { id: 'it-seo-health', icon: Search, title: 'SEO Health Monitor', desc: 'Lighthouse + AEO/GEO scoring', route: null, soon: true },
      { id: 'it-dev-tasks', icon: CheckSquare, title: 'Dev Task Tracker', desc: 'Engineering kanban', route: null, soon: true },
    ],
  },
  me: {
    label: 'Me',
    accent: 'emerald',
    icon: User,
    description: 'Your personal workspace — profile, tasks, leave, payslips.',
    cards: [
      { id: 'me-profile', icon: User, title: 'My Profile', desc: 'Personal, bank, emergency contact', route: '/portal/my-profile' },
      { id: 'me-tasks', icon: CheckSquare, title: 'My Tasks', desc: 'Kanban board of assigned work', route: '/portal/my-tasks' },
      { id: 'me-attendance', icon: Clock, title: 'My Attendance', desc: 'Punch in/out, monthly calendar', route: '/portal/attendance' },
      { id: 'me-leaves', icon: Coffee, title: 'My Leaves', desc: 'Apply, balance, history', route: '/portal/leaves' },
      { id: 'me-payslips', icon: Receipt, title: 'My Payslips', desc: 'Salary history (Slice 2)', route: null, soon: true },
      { id: 'me-policies', icon: BookOpen, title: 'Policies', desc: 'Read & acknowledge handbook', route: '/portal/policies' },
    ],
  },
};

// Tailwind accent → text/border/badge class helper
const accentMap = {
  'leamss-teal': { ring: 'ring-leamss-teal-200', bg: 'bg-leamss-teal-50', text: 'text-leamss-teal-700', border: 'border-leamss-teal-300', solid: 'bg-leamss-teal-600', hover: 'hover:border-leamss-teal-400' },
  'leamss-orange': { ring: 'ring-leamss-orange-200', bg: 'bg-leamss-orange-50', text: 'text-leamss-orange-700', border: 'border-leamss-orange-300', solid: 'bg-leamss-orange-600', hover: 'hover:border-leamss-orange-400' },
  sky: { ring: 'ring-sky-200', bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-300', solid: 'bg-sky-600', hover: 'hover:border-sky-400' },
  slate: { ring: 'ring-slate-200', bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-300', solid: 'bg-slate-600', hover: 'hover:border-slate-400' },
  emerald: { ring: 'ring-emerald-200', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300', solid: 'bg-emerald-600', hover: 'hover:border-emerald-400' },
};

export default function PortalHub() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeGroup, setActiveGroup] = useState('employees');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    (async () => {
      try {
        const [me, st] = await Promise.all([
          axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/admin/portal-hub/stats`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setUser(me.data);
        setStats(st.data);
      } catch (e) {
        navigate('/');
      } finally {
        setLoading(false);
      }
    })();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  // Build counts per group for sidebar badges
  const counts = stats ? {
    employees: stats.employees.active,
    hr: stats.hr.pending_leaves + stats.hr.pending_regularizations,
    marketing: stats.marketing.active_campaigns + stats.marketing.draft_campaigns,
    it: stats.it.open_incidents,
    me: stats.me.my_tasks,
  } : { employees: 0, hr: 0, marketing: 0, it: 0, me: 0 };

  const navGroups = [
    {
      groupLabel: 'Portal Hub',
      defaultOpen: true,
      items: Object.entries(GROUP_CARDS).map(([key, g]) => ({
        id: `hub-${key}`,
        icon: g.icon,
        label: g.label,
        badge: counts[key],
        badgeColor: key === 'me' ? 'bg-emerald-600' : key === 'marketing' ? 'bg-leamss-orange-500' : 'bg-leamss-teal-600',
        onClick: () => setActiveGroup(key),
      })),
    },
  ];

  if (loading || !user) {
    return <div className="flex items-center justify-center h-screen text-slate-500">Loading Portal Hub...</div>;
  }

  const group = GROUP_CARDS[activeGroup];
  const accent = accentMap[group.accent];

  return (
    <DashboardShell
      user={user}
      roleLabel="Portal Hub"
      navGroups={navGroups}
      activeTab={`hub-${activeGroup}`}
      pageTitle="Portal Hub"
      onLogout={handleLogout}
    >
      <div className="space-y-6" data-testid="portal-hub">
        {/* Hero banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-leamss-teal-700 to-leamss-teal-600 p-6 md:p-8 text-white shadow-xl" data-testid="portal-hub-hero">
          <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-leamss-orange-500/20 blur-3xl" />
          <div className="absolute -left-8 -bottom-8 w-40 h-40 rounded-full bg-white/10 blur-2xl" />
          <div className="relative flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 text-leamss-orange-200 text-xs font-semibold uppercase tracking-wider">
                <Sparkles className="h-3.5 w-3.5" /> Unified Workplace
              </div>
              <h1 className="text-3xl md:text-4xl font-bold mt-2">Welcome, {user.name?.split(' ')[0]} 👋</h1>
              <p className="text-sm text-white/80 mt-2 max-w-2xl">
                One place for Employees, HR, Marketing, IT and your personal workspace. Pick a section from the sidebar or jump to a card below.
              </p>
              <div className="flex items-center gap-2 mt-4 flex-wrap">
                <Badge className="bg-white/20 text-white border-white/30">{user.rbac_role || user.role}</Badge>
                {user.department && <Badge className="bg-leamss-orange-500 text-white">{user.department}</Badge>}
                {user.employee_id && <Badge variant="outline" className="border-white/40 text-white font-mono text-xs">{user.employee_id}</Badge>}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-right">
              <div className="px-3 py-2 rounded-lg bg-white/10 backdrop-blur">
                <p className="text-xs text-white/70">Active Employees</p>
                <p className="text-2xl font-bold">{stats?.employees.active ?? '—'}</p>
              </div>
              <div className="px-3 py-2 rounded-lg bg-white/10 backdrop-blur">
                <p className="text-xs text-white/70">My Tasks</p>
                <p className="text-2xl font-bold">{stats?.me.my_tasks ?? 0}</p>
              </div>
              <div className="px-3 py-2 rounded-lg bg-white/10 backdrop-blur">
                <p className="text-xs text-white/70">Pending Leaves</p>
                <p className="text-2xl font-bold">{stats?.hr.pending_leaves ?? 0}</p>
              </div>
              <div className="px-3 py-2 rounded-lg bg-white/10 backdrop-blur">
                <p className="text-xs text-white/70">Active Campaigns</p>
                <p className="text-2xl font-bold">{stats?.marketing.active_campaigns ?? 0}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Group selector chips (mobile-friendly, mirrors sidebar) */}
        <div className="flex gap-2 overflow-x-auto pb-2 md:hidden" data-testid="portal-hub-mobile-chips">
          {Object.entries(GROUP_CARDS).map(([key, g]) => {
            const a = accentMap[g.accent];
            const Icon = g.icon;
            const isActive = activeGroup === key;
            return (
              <button
                key={key}
                onClick={() => setActiveGroup(key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap border transition-all ${
                  isActive ? `${a.solid} text-white border-transparent shadow-md` : `${a.bg} ${a.text} ${a.border}`
                }`}
                data-testid={`portal-hub-chip-${key}`}
              >
                <Icon className="h-3.5 w-3.5" /> {g.label}
                {counts[key] > 0 && (
                  <span className={`ml-1 px-1.5 rounded-full text-[10px] font-bold ${isActive ? 'bg-white/20' : 'bg-white'}`}>
                    {counts[key]}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Active group header */}
        <div className={`p-4 rounded-xl border ${accent.border} ${accent.bg}`} data-testid={`portal-hub-group-${activeGroup}`}>
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-lg ${accent.solid} text-white`}>
              <group.icon className="h-5 w-5" />
            </div>
            <div>
              <h2 className={`text-lg font-bold ${accent.text}`}>{group.label}</h2>
              <p className="text-sm text-slate-600">{group.description}</p>
            </div>
          </div>
        </div>

        {/* Cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid={`portal-hub-cards-${activeGroup}`}>
          {group.cards.map(card => {
            const Icon = card.icon;
            const isDisabled = card.soon || !card.route;
            return (
              <Card
                key={card.id}
                onClick={() => !isDisabled && navigate(card.route)}
                className={`group p-5 transition-all ${
                  isDisabled
                    ? 'opacity-60 cursor-not-allowed'
                    : `cursor-pointer ${accent.hover} hover:shadow-lg hover:-translate-y-0.5`
                } border-slate-200`}
                data-testid={`portal-hub-card-${activeGroup}-${card.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className={`p-2.5 rounded-lg ${accent.bg}`}>
                    <Icon className={`h-5 w-5 ${accent.text}`} />
                  </div>
                  {!isDisabled && (
                    <ArrowRight className={`h-4 w-4 text-slate-300 group-hover:${accent.text} group-hover:translate-x-1 transition-all`} />
                  )}
                  {card.soon && <Badge variant="outline" className="text-xs">Coming Soon</Badge>}
                </div>
                <h3 className="font-semibold text-slate-900 mt-3">{card.title}</h3>
                <p className="text-xs text-slate-500 mt-1">{card.desc}</p>
              </Card>
            );
          })}
        </div>

        {/* Footer hint */}
        <Card className="p-4 bg-slate-50/50 border-dashed border-slate-300">
          <p className="text-xs text-slate-500 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-leamss-orange-500" />
            <span>
              <strong>Tip:</strong> All your old links (<code className="px-1 bg-white rounded text-leamss-teal-700">/admin/employees</code>,
              {' '}<code className="px-1 bg-white rounded text-leamss-teal-700">/admin/marketing</code>,
              {' '}<code className="px-1 bg-white rounded text-leamss-teal-700">/admin/hr/*</code>) still work. The Portal Hub is just a unified front door.
            </span>
          </p>
        </Card>
      </div>
    </DashboardShell>
  );
}
