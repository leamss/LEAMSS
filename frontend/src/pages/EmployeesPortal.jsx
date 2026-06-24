import { useState, useEffect, lazy, Suspense, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import DashboardShell from '@/components/DashboardShell';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboard, Building2, UsersRound, Network, UserPlus, ArrowLeft,
  Home, Sparkles, Settings as SettingsIcon, Calendar, FileText, ShieldCheck, History,
  Megaphone, Target, Mail, Gift, BarChart3,
  Server, Globe, Search,
  User, CheckSquare, Coffee, Receipt, BookOpen, Clock, ArrowRight,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Lazy-loaded existing employee modules
const EmployeesDashboard = lazy(() => import('@/components/employees/EmployeesDashboard'));
const DepartmentsPage = lazy(() => import('@/components/employees/DepartmentsPage'));
const EmployeesList = lazy(() => import('@/components/employees/EmployeesList'));
const AddEmployeeForm = lazy(() => import('@/components/employees/AddEmployeeForm'));
const OrgChart = lazy(() => import('@/components/employees/OrgChart'));

const PAGE_TITLES = {
  'hub-home': 'Portal Hub',
  'emp-dashboard': 'Employees Dashboard',
  'emp-departments': 'Departments',
  'emp-list': 'All Employees',
  'emp-add': 'Add Employee',
  'emp-org-chart': 'Org Chart',
};

const Fallback = () => <div className="p-12 text-center text-slate-400">Loading…</div>;

// ─────────────────── Group definitions (cards on Hub Home) ───────────────────
const GROUP_CARDS = {
  employees: {
    label: 'Employees',
    accent: 'leamss-teal',
    icon: UsersRound,
    description: 'Manage internal workforce, departments, and org structure.',
    cards: [
      { id: 'emp-dashboard', icon: LayoutDashboard, title: 'Dashboard', desc: 'Workforce overview & stats', internal: true },
      { id: 'emp-list', icon: UsersRound, title: 'All Employees', desc: 'Search, filter, manage', internal: true },
      { id: 'emp-org-chart', icon: Network, title: 'Org Chart', desc: 'Reports-to hierarchy', internal: true },
      { id: 'emp-departments', icon: Building2, title: 'Departments', desc: 'Eight departments + heads', internal: true },
      { id: 'emp-add', icon: UserPlus, title: 'Add Employee', desc: 'Three-step onboarding form', internal: true },
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
      { id: 'hr-approvers', icon: UsersRound, title: 'Approver Config', desc: 'L1, Final, department-wise', route: '/admin/hr/approvers' },
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
      { id: 'it-site-audit', icon: Globe, title: 'Website Audit', desc: 'Broken links, missing alt, perf', soon: true },
      { id: 'it-seo-health', icon: Search, title: 'SEO Health Monitor', desc: 'Lighthouse + AEO/GEO scoring', soon: true },
      { id: 'it-dev-tasks', icon: CheckSquare, title: 'Dev Task Tracker', desc: 'Engineering kanban', soon: true },
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
      { id: 'me-announcements', icon: Megaphone, title: 'Announcements', desc: 'Company news feed', route: '/portal/announcements' },
      { id: 'me-policies', icon: BookOpen, title: 'Policies', desc: 'Read & acknowledge handbook', route: '/portal/policies' },
      { id: 'me-payslips', icon: Receipt, title: 'My Payslips', desc: 'Salary history (Slice 2)', soon: true },
    ],
  },
};

const ACCENT_MAP = {
  'leamss-teal': { ring: 'ring-leamss-teal-200', bg: 'bg-leamss-teal-50', text: 'text-leamss-teal-700', border: 'border-leamss-teal-300', solid: 'bg-leamss-teal-600', hover: 'hover:border-leamss-teal-400' },
  'leamss-orange': { ring: 'ring-leamss-orange-200', bg: 'bg-leamss-orange-50', text: 'text-leamss-orange-700', border: 'border-leamss-orange-300', solid: 'bg-leamss-orange-600', hover: 'hover:border-leamss-orange-400' },
  sky: { ring: 'ring-sky-200', bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-300', solid: 'bg-sky-600', hover: 'hover:border-sky-400' },
  slate: { ring: 'ring-slate-200', bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-300', solid: 'bg-slate-600', hover: 'hover:border-slate-400' },
  emerald: { ring: 'ring-emerald-200', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300', solid: 'bg-emerald-600', hover: 'hover:border-emerald-400' },
};

// ─────────────────── Hub Home view component ───────────────────
function HubHome({ user, stats, activeGroup, setActiveGroup, onSelectInternal }) {
  const navigate = useNavigate();
  const group = GROUP_CARDS[activeGroup];
  const accent = ACCENT_MAP[group.accent];

  const counts = useMemo(() => stats ? {
    employees: stats.employees.active,
    hr: stats.hr.pending_leaves + stats.hr.pending_regularizations,
    marketing: stats.marketing.active_campaigns + stats.marketing.draft_campaigns,
    it: stats.it.open_incidents,
    me: stats.me.my_tasks + (stats.me.unread_announcements || 0),
  } : { employees: 0, hr: 0, marketing: 0, it: 0, me: 0 }, [stats]);

  return (
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
              One place for Employees, HR, Marketing, IT and your personal workspace. Pick a section below or use the sidebar.
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

      {/* Group selector chips */}
      <div className="flex gap-2 overflow-x-auto pb-2" data-testid="portal-hub-chips">
        {Object.entries(GROUP_CARDS).map(([key, g]) => {
          const a = ACCENT_MAP[g.accent];
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
          const isDisabled = card.soon || (!card.route && !card.internal);
          const handleClick = () => {
            if (isDisabled) return;
            if (card.internal) onSelectInternal(card.id);
            else navigate(card.route);
          };
          return (
            <Card
              key={card.id}
              onClick={handleClick}
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
            <strong>Tip:</strong> Your old shortcuts still work — <code className="px-1 bg-white rounded text-leamss-teal-700">/admin/marketing</code>,
            {' '}<code className="px-1 bg-white rounded text-leamss-teal-700">/admin/hr/settings</code>, and others remain available. This hub is just the unified front door.
          </span>
        </p>
      </Card>
    </div>
  );
}

// ─────────────────── Main page ───────────────────
export default function EmployeesPortal() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'hub-home');
  const [activeGroup, setActiveGroup] = useState('employees');
  const [empListFilter, setEmpListFilter] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    const auth = { headers: { Authorization: `Bearer ${token}` } };
    Promise.all([
      axios.get(`${API}/auth/me`, auth),
      axios.get(`${API}/admin/portal-hub/stats`, auth).catch(() => ({ data: null })),
    ]).then(([me, st]) => {
      setUser(me.data);
      setStats(st.data);
    }).catch(() => navigate('/'));
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  // Sidebar: Hub Home as first group, Employees tabs as second group, jump-out shortcuts as 3rd
  const navGroups = [
    {
      groupLabel: 'Portal Hub',
      defaultOpen: true,
      items: [
        { id: 'hub-home', icon: Home, label: 'Hub Home', onClick: () => { setActiveTab('hub-home'); setEmpListFilter(null); } },
      ],
    },
    {
      groupLabel: 'Employees',
      defaultOpen: true,
      items: [
        { id: 'emp-dashboard', icon: LayoutDashboard, label: 'Dashboard', onClick: () => { setActiveTab('emp-dashboard'); setEmpListFilter(null); } },
        { id: 'emp-departments', icon: Building2, label: 'Departments', onClick: () => { setActiveTab('emp-departments'); setEmpListFilter(null); } },
        { id: 'emp-list', icon: UsersRound, label: 'All Employees', onClick: () => { setActiveTab('emp-list'); setEmpListFilter(null); } },
        { id: 'emp-org-chart', icon: Network, label: 'Org Chart', onClick: () => { setActiveTab('emp-org-chart'); } },
        { id: 'emp-add', icon: UserPlus, label: 'Add Employee', onClick: () => { setActiveTab('emp-add'); } },
      ],
    },
    {
      groupLabel: 'Jump To',
      defaultOpen: false,
      items: [
        { id: 'nav-hr', icon: ShieldCheck, label: 'HR Settings', onClick: () => navigate('/admin/hr/settings') },
        { id: 'nav-marketing', icon: Megaphone, label: 'Marketing', onClick: () => navigate('/admin/marketing') },
        { id: 'nav-my-profile', icon: User, label: 'My Profile', onClick: () => navigate('/portal/my-profile') },
        { id: 'nav-my-tasks', icon: CheckSquare, label: 'My Tasks', onClick: () => navigate('/portal/my-tasks') },
        { id: 'nav-announcements', icon: Megaphone, label: 'Announcements', onClick: () => navigate('/portal/announcements') },
        { id: 'nav-policies', icon: BookOpen, label: 'Policies', onClick: () => navigate('/portal/policies') },
      ],
    },
    {
      groupLabel: 'Back to Main',
      defaultOpen: false,
      items: [
        { id: 'back-admin', icon: ArrowLeft, label: 'Admin Dashboard', onClick: () => navigate('/admin') },
      ],
    },
  ];

  const onNavigateInternal = (tab, filter) => {
    if (filter) setEmpListFilter(filter);
    setActiveTab(tab);
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'hub-home':
        return (
          <HubHome
            user={user}
            stats={stats}
            activeGroup={activeGroup}
            setActiveGroup={setActiveGroup}
            onSelectInternal={(id) => { setEmpListFilter(null); setActiveTab(id); }}
          />
        );
      case 'emp-dashboard':
        return <EmployeesDashboard onNavigate={onNavigateInternal} />;
      case 'emp-departments':
        return <DepartmentsPage onNavigate={onNavigateInternal} />;
      case 'emp-list':
        return <EmployeesList initialFilter={empListFilter} onNavigate={(t) => setActiveTab(t)} />;
      case 'emp-add':
        return <AddEmployeeForm onNavigate={(t) => { setEmpListFilter(null); setActiveTab(t); }} />;
      case 'emp-org-chart':
        return <OrgChart onSelect={(id) => { setEmpListFilter({ employeeId: id }); setActiveTab('emp-list'); }} />;
      default:
        return null;
    }
  };

  if (!user) return <div className="flex items-center justify-center h-screen text-slate-500">Loading...</div>;

  return (
    <DashboardShell
      user={user}
      roleLabel="Portal Hub"
      navGroups={navGroups}
      activeTab={activeTab}
      pageTitle={PAGE_TITLES[activeTab] || 'Portal Hub'}
      onLogout={handleLogout}
    >
      <Suspense fallback={<Fallback />}>
        {renderActiveTab()}
      </Suspense>
    </DashboardShell>
  );
}
