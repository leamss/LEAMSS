import { useState, useEffect, lazy, Suspense, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import DashboardShell from '@/components/DashboardShell';
import HubHome from '@/components/portal/HubHome';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboard, Building2, UsersRound, Network, UserPlus, ArrowLeft,
  Home, Sparkles, Settings as SettingsIcon, Calendar, FileText, ShieldCheck, History,
  Megaphone, Target, Mail, Gift, BarChart3, MessageCircleQuestion, Bot,
  Server, Globe, Search,
  User, CheckSquare, Coffee, Receipt, BookOpen, Clock, ArrowRight, Wallet,
  MessageCircle, TicketCheck,
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
  communication: {
    label: 'Communication',
    accent: 'leamss-red',
    icon: MessageCircle,
    description: 'Internal team chat aur cross-department helpdesk tickets — daily high-frequency tools.',
    cards: [
      { id: 'comm-chat', icon: MessageCircle, title: 'Chat', desc: 'DMs aur group threads with employees', route: '/portal/chat' },
      { id: 'comm-tickets', icon: TicketCheck, title: 'Tickets', desc: 'Raise / track HR · IT · Finance · Marketing · Ops requests', route: '/portal/tickets' },
    ],
  },
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
      { id: 'hr-analytics', icon: BarChart3, title: 'HR Analytics', desc: 'Headcount, attrition, leave KPIs', route: '/admin/hr/analytics' },
      { id: 'hr-settings', icon: SettingsIcon, title: 'Attendance Settings', desc: 'Office hours, late marks, sandwich', route: '/admin/hr/settings' },
      { id: 'hr-holidays', icon: Calendar, title: 'Holiday Calendar', desc: 'Manage public + optional', route: '/admin/hr/holidays' },
      { id: 'hr-leave-types', icon: FileText, title: 'Leave Types', desc: 'Policies, quotas, carry-forward', route: '/admin/hr/leave-types' },
      { id: 'hr-approvers', icon: UsersRound, title: 'Approver Config', desc: 'L1, Final, department-wise', route: '/admin/hr/approvers' },
      { id: 'hr-reimbursements', icon: Receipt, title: 'Reimbursements (HR)', desc: 'Approve & merge into payslip', route: '/admin/reimbursements/all' },
      { id: 'hr-audit', icon: History, title: 'Audit Log', desc: 'Policy changes trail', route: '/admin/hr/audit' },
    ],
  },
  marketing: {
    label: 'Marketing',
    accent: 'leamss-orange',
    icon: Megaphone,
    description: 'Leads, campaigns, content studio, SEO/AEO/GEO AI tools.',
    cards: [
      { id: 'mkt-overview', icon: BarChart3, title: 'Marketing Dashboard', desc: 'Pipeline & funnel overview', route: '/admin/marketing' },
      { id: 'mkt-content-studio', icon: Sparkles, title: 'Content Studio', desc: 'AI emails/blogs/ads (Claude 4.5)', route: '/portal/marketing/content-studio' },
      { id: 'mkt-seo', icon: Search, title: 'SEO Tools', desc: 'Keyword research, meta optimisation', route: '/portal/marketing/seo' },
      { id: 'mkt-aeo', icon: MessageCircleQuestion, title: 'AEO Tools', desc: 'FAQ schema, voice search, snippets', route: '/portal/marketing/aeo' },
      { id: 'mkt-geo', icon: Bot, title: 'GEO Tools (NEW)', desc: 'LLM citation optimiser — quotable by ChatGPT/Claude', route: '/portal/marketing/geo' },
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
    description: 'Website audit, dev tracker, internal engineering tools.',
    cards: [
      { id: 'it-site-audit', icon: Globe, title: 'Site Audit', desc: 'Meta · JSON-LD · H-hierarchy · alt · link health', route: '/portal/it/site-audit' },
      { id: 'it-dev-tracker', icon: CheckSquare, title: 'Dev Tracker', desc: 'Bugs · features · chores kanban', route: '/portal/it/dev-tracker' },
      { id: 'it-seo-health', icon: Search, title: 'SEO Health Monitor', desc: 'Lighthouse + AEO/GEO scoring', soon: true },
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
      { id: 'me-payslips', icon: Receipt, title: 'My Payslips', desc: 'Monthly salary statements + PDF', route: '/portal/my-payslips' },
      { id: 'me-documents', icon: FileText, title: 'My Documents', desc: 'ID, education, bank docs vault', route: '/portal/my-documents' },
      { id: 'me-assets', icon: BookOpen, title: 'My Assets', desc: 'Laptop, phone, access cards', route: '/portal/my-assets' },
      { id: 'me-onboarding', icon: CheckSquare, title: 'My Onboarding', desc: 'Checklist & evidence upload', route: '/portal/my-onboarding' },
      { id: 'me-reimbursements', icon: Wallet, title: 'My Reimbursements', desc: 'Submit & track expense claims', route: '/portal/my-reimbursements' },
      { id: 'me-team-reimb', icon: Wallet, title: 'Team Reimbursements', desc: 'Approve direct reports (manager)', route: '/admin/reimbursements/pending' },
      { id: 'me-announcements', icon: Megaphone, title: 'Announcements', desc: 'Company news feed', route: '/portal/announcements' },
      { id: 'me-policies', icon: BookOpen, title: 'Policies', desc: 'Read & acknowledge handbook', route: '/portal/policies' },
    ],
  },
};

const ACCENT_MAP = {
  'leamss-teal': { ring: 'ring-leamss-teal-200', bg: 'bg-leamss-teal-50', text: 'text-leamss-teal-700', border: 'border-leamss-teal-300', solid: 'bg-leamss-teal-600', hover: 'hover:border-leamss-teal-400' },
  'leamss-orange': { ring: 'ring-leamss-orange-200', bg: 'bg-leamss-orange-50', text: 'text-leamss-orange-700', border: 'border-leamss-orange-300', solid: 'bg-leamss-orange-600', hover: 'hover:border-leamss-orange-400' },
  'leamss-red': { ring: 'ring-leamss-red-200', bg: 'bg-leamss-red-50', text: 'text-leamss-red-700', border: 'border-leamss-red-300', solid: 'bg-leamss-red-600', hover: 'hover:border-leamss-red-400' },
  sky: { ring: 'ring-sky-200', bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-300', solid: 'bg-sky-600', hover: 'hover:border-sky-400' },
  slate: { ring: 'ring-slate-200', bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-300', solid: 'bg-slate-600', hover: 'hover:border-slate-400' },
  emerald: { ring: 'ring-emerald-200', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300', solid: 'bg-emerald-600', hover: 'hover:border-emerald-400' },
};

// ─────────────────── HubHome moved to /app/frontend/src/components/portal/HubHome.jsx ───────────────────

// ─────────────────── Main page ───────────────────
export default function EmployeesPortal() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'hub-home');
  // Phase 22 Slice 22.1 — default to "me" group so user lands on personal workspace
  // (includes My Payslips, My Tasks, My Profile, etc.) instead of communication-only chat/tickets.
  const [activeGroup, setActiveGroup] = useState('me');
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
            groupCards={GROUP_CARDS}
            accentMap={ACCENT_MAP}
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
