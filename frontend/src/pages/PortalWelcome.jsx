import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  LogOut, User, KeyRound, Bell, Calendar, CheckSquare, Sparkles,
  Building2, Briefcase, Shield, TrendingUp, Megaphone, Users, Receipt,
  Server, ScrollText, ChevronRight, Clock, Database,
} from 'lucide-react';
import PunchWidget from '@/components/attendance/PunchWidget';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DEPT_THEMES = {
  admin:       { color: '#7c3aed', tint: 'bg-leamss-red-50',   text: 'text-leamss-red-700',  icon: Shield },
  sales:       { color: '#16a34a', tint: 'bg-emerald-50',  text: 'text-emerald-700', icon: TrendingUp },
  marketing:   { color: '#ea580c', tint: 'bg-orange-50',   text: 'text-orange-700',  icon: Megaphone },
  operations:  { color: '#0891b2', tint: 'bg-cyan-50',     text: 'text-cyan-700',    icon: Briefcase },
  hr:          { color: '#db2777', tint: 'bg-pink-50',     text: 'text-pink-700',    icon: Users },
  accounts:    { color: '#0d9488', tint: 'bg-teal-50',     text: 'text-teal-700',    icon: Receipt },
  it:          { color: '#475569', tint: 'bg-slate-50',    text: 'text-slate-700',   icon: Server },
  compliance:  { color: '#b91c1c', tint: 'bg-rose-50',     text: 'text-rose-700',    icon: ScrollText },
};

// Maps a ui_module key to a friendly label + icon. Anything unmapped gets a default.
const MODULE_META = {
  // Self-service (everyone)
  attendance_self:      { label: 'My Attendance',       icon: Clock },
  leave_self:           { label: 'My Leave',            icon: Calendar },
  profile_self:         { label: 'My Profile',          icon: User },
  notifications:        { label: 'Notifications',       icon: Bell },
  my_tasks:             { label: 'My Tasks',            icon: CheckSquare },
  // Sales
  sales_dashboard:      { label: 'Sales Dashboard',     icon: TrendingUp },
  pa_pipeline_own:      { label: 'My PA Pipeline',      icon: Briefcase },
  my_crm:                { label: 'My CRM',              icon: Database },
  pa_pipeline_team:     { label: 'Team PA Pipeline',    icon: Briefcase },
  pa_pipeline_all:      { label: 'All PA Pipeline',     icon: Briefcase },
  lead_pool:            { label: 'Lead Pool',           icon: Sparkles },
  my_targets:           { label: 'My Targets',          icon: TrendingUp },
  team_targets:         { label: 'Team Targets',        icon: TrendingUp },
  my_incentives:        { label: 'My Incentives',       icon: Sparkles },
  team_incentives:      { label: 'Team Incentives',     icon: Sparkles },
  my_commissions:       { label: 'My Commissions',      icon: Receipt },
  team_commissions:     { label: 'Team Commissions',    icon: Receipt },
  call_log:             { label: 'Call Log',            icon: Bell },
  call_logs:            { label: 'Team Call Logs',      icon: Bell },
  leaderboard:          { label: 'Leaderboard',         icon: TrendingUp },
  discount_inbox:       { label: 'Discount Approvals',  icon: CheckSquare },
  sales_analytics:      { label: 'Sales Analytics',     icon: TrendingUp },
  team_management:      { label: 'Team Management',     icon: Users },
  // Marketing
  marketing_dashboard:  { label: 'Marketing Dashboard', icon: Megaphone },
  campaigns_all:        { label: 'All Campaigns',       icon: Megaphone },
  my_campaigns:         { label: 'My Campaigns',        icon: Megaphone },
  content_library:      { label: 'Content Library',     icon: ScrollText },
  content_calendar:     { label: 'Content Calendar',    icon: Calendar },
  email_campaigns_all:  { label: 'Email Campaigns',     icon: Bell },
  email_drafts:         { label: 'Email Drafts',        icon: Bell },
  public_pages:         { label: 'Public Pages',        icon: ScrollText },
  public_pages_view:    { label: 'Public Pages',        icon: ScrollText },
  lead_analytics:       { label: 'Lead Analytics',      icon: TrendingUp },
  // Operations
  ops_dashboard:        { label: 'Operations Home',     icon: Briefcase },
  pa_l2_approval:       { label: 'PA L2 Approvals',     icon: CheckSquare },
  cases_all:            { label: 'All Cases',           icon: Briefcase },
  my_cases:             { label: 'My Cases',            icon: Briefcase },
  doc_verification_queue:{ label: 'Doc Verification',   icon: ScrollText },
  ocr_review:           { label: 'OCR Review',          icon: ScrollText },
  cm_workload:          { label: 'CM Workload',         icon: Users },
  cm_dashboard:         { label: 'Case Manager Home',   icon: Briefcase },
  support_tickets:      { label: 'Support Tickets',     icon: Bell },
  // HR
  hr_dashboard:         { label: 'HR Dashboard',        icon: Users },
  employee_directory:   { label: 'Employee Directory',  icon: Users },
  attendance_admin:     { label: 'Attendance Admin',    icon: Clock },
  attendance_view:      { label: 'Attendance',          icon: Clock },
  leave_admin:          { label: 'Leave Admin',         icon: Calendar },
  leave_approvals:      { label: 'Leave Approvals',     icon: CheckSquare },
  payroll:              { label: 'Payroll',             icon: Receipt },
  onboarding:           { label: 'Onboarding',          icon: User },
  offboarding:          { label: 'Offboarding',         icon: User },
  performance_cycles:   { label: 'Performance Reviews', icon: TrendingUp },
  training_mgmt:        { label: 'Training',            icon: Sparkles },
  // Accounts
  accounts_dashboard:   { label: 'Accounts Home',       icon: Receipt },
  invoices_all:         { label: 'All Invoices',        icon: Receipt },
  invoices_process:     { label: 'Invoice Processing',  icon: Receipt },
  refunds:              { label: 'Refunds',             icon: Receipt },
  commissions:          { label: 'Commissions',         icon: Receipt },
  commissions_view:     { label: 'Commissions',         icon: Receipt },
  gst:                  { label: 'GST',                 icon: Receipt },
  gst_view:             { label: 'GST',                 icon: Receipt },
  vendors:              { label: 'Vendors',             icon: Briefcase },
  vendors_view:         { label: 'Vendors',             icon: Briefcase },
  expenses:             { label: 'Expenses',            icon: Receipt },
  expenses_view:        { label: 'Expenses',            icon: Receipt },
  revenue_pnl:          { label: 'Revenue & P&L',       icon: TrendingUp },
  // IT
  it_dashboard:         { label: 'IT Dashboard',        icon: Server },
  user_access:          { label: 'User Access',         icon: User },
  system_config:        { label: 'System Config',       icon: Server },
  api_keys:             { label: 'API Keys',            icon: KeyRound },
  backups:              { label: 'Backups',             icon: Server },
  assets:               { label: 'Assets',              icon: Briefcase },
  support_tickets_admin:{ label: 'Support Admin',       icon: Bell },
  security_logs:        { label: 'Security Logs',       icon: Shield },
  // Compliance
  legal_archive:        { label: 'Legal Archive',       icon: ScrollText },
  audit_log:            { label: 'Audit Logs',          icon: ScrollText },
  compliance_reports:   { label: 'Compliance Reports',  icon: ScrollText },
  activity_log:         { label: 'Activity Log',        icon: ScrollText },
};

export default function PortalWelcome() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [notifCount, setNotifCount] = useState(0);
  const [taskCount, setTaskCount] = useState(null);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    const auth = { headers: { Authorization: `Bearer ${token}` } };
    axios.get(`${API}/auth/me`, auth)
      .then(r => setUser(r.data))
      .catch(() => navigate('/'));

    axios.get(`${API}/notifications`, auth)
      .then(r => {
        const items = Array.isArray(r.data) ? r.data : (r.data?.items || []);
        setNotifCount(items.filter(n => !n.read).length);
      })
      .catch(() => setNotifCount(0));

    // Phase 22 hotfix — fetch real task count for "My Tasks" tile
    axios.get(`${API}/tasks?mode=me`, auth)
      .then(r => {
        const items = Array.isArray(r.data) ? r.data : (r.data?.items || []);
        setTaskCount(items.filter(t => t.status !== 'done' && t.status !== 'completed').length);
      })
      .catch(() => setTaskCount(0));

    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  const handleModuleClick = (moduleKey) => {
    // Feb 26 hotfix v2 — RBAC v2 stores ui_modules as URL paths (e.g. "/admin/payroll").
    // If moduleKey already looks like a path, navigate to it directly.
    if (typeof moduleKey === 'string' && moduleKey.startsWith('/')) {
      navigate(moduleKey);
      return;
    }
    // Phase 22 hotfix — comprehensive routing for all built Phase 21+22 features (legacy snake_case)
    const routes = {
      pa_pipeline_own: '/sales/dashboard?tab=lead-pipeline',
      // Self-service (everyone)
      attendance_self: '/portal/attendance',
      attendance_view: '/portal/attendance',
      attendance_admin: '/portal/attendance',
      leave_self: '/portal/leaves',
      leave_approvals: '/portal/leave-approvals',
      leave_admin: '/portal/leave-approvals',
      profile_self: '/portal/my-profile',
      notifications: '/notifications',
      my_tasks: '/portal/my-tasks',
      // Phase 21 Slice 4 + 22
      support_tickets: '/portal/tickets',
      support_tickets_admin: '/portal/tickets',
      // HR
      hr_dashboard: '/admin/employees',
      employee_directory: '/admin/employees?tab=all',
      payroll: '/admin/payroll',
      onboarding: '/portal/my-onboarding',
      // Sales
      sales_dashboard: '/sales/dashboard',
      my_targets: '/sales/my-targets',
      my_incentives: '/sales/my-commission',
      my_commissions: '/sales/my-commission',
      leaderboard: '/sales/leaderboard',
      my_crm: '/sales/my-crm',
      lead_pool: '/admin/marketing',
      // Marketing
      marketing_dashboard: '/admin/marketing',
      campaigns_all: '/admin/marketing',
      my_campaigns: '/admin/marketing',
      content_library: '/portal/marketing/content-studio',
      public_pages: '/admin/public-pages',
      public_pages_view: '/admin/public-pages',
      // Operations
      ops_dashboard: '/case-manager',
      cases_all: '/admin/employees',
      my_cases: '/case-manager',
      cm_dashboard: '/case-manager',
      // IT
      it_dashboard: '/portal/it/site-audit',
      // Accounts
      accounts_dashboard: '/admin/payroll',
      commissions: '/admin/sales/commissions',
      commissions_view: '/admin/sales/commissions',
      // Compliance
      audit_log: '/admin/hr/audit',
      activity_log: '/admin/activity',
    };
    const target = routes[moduleKey];
    if (target) { navigate(target); return; }
    toast.info(`Ye module abhi roadmap me hai — agle phase me aayega: "${MODULE_META[moduleKey]?.label || moduleKey}"`);
  };

  if (!user) {
    return <div className="flex items-center justify-center h-screen text-slate-500">Loading...</div>;
  }

  const theme = DEPT_THEMES[user.department] || DEPT_THEMES.it;
  const DeptIcon = theme.icon;
  const modules = user.ui_modules || [];

  return (
    <div className="min-h-screen bg-slate-50" data-testid="portal-welcome">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: theme.color }}>
            <DeptIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-slate-900">LEAMSS Portal</h1>
            <p className="text-xs text-slate-500">{user.designation || user.rbac_role}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs">{user.employee_id || user.partner_code || '—'}</Badge>
          <Button variant="outline" size="sm" onClick={() => navigate('/portal/my-profile')} data-testid="profile-btn">
            <User className="h-4 w-4 mr-1.5" /> Profile
          </Button>
          <Button variant="outline" size="sm" onClick={() => navigate('/portal/my-profile?tab=security')} data-testid="pwd-btn">
            <KeyRound className="h-4 w-4 mr-1.5" /> Password
          </Button>
          <Button variant="outline" size="sm" onClick={handleLogout} className="text-rose-600 border-rose-200" data-testid="logout-btn">
            <LogOut className="h-4 w-4 mr-1.5" /> Logout
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Welcome banner */}
        <Card className={`p-6 ${theme.tint} border-l-4`} style={{ borderLeftColor: theme.color }} data-testid="welcome-banner">
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h2 className="text-3xl font-bold text-slate-900">Welcome, {user.name?.split(' ')[0] || 'there'}!</h2>
              <div className="flex items-center gap-3 mt-3 flex-wrap">
                <Badge className="text-xs" style={{ background: theme.color, color: 'white' }}>
                  <DeptIcon className="h-3 w-3 mr-1" />
                  {(user.department || 'no-dept').toUpperCase()}
                </Badge>
                <span className={`text-sm font-medium ${theme.text}`}>{user.designation || user.rbac_role}</span>
                <span className="text-slate-400">·</span>
                <span className="text-sm text-slate-600">{user.employee_id || user.partner_code || '—'}</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 uppercase tracking-wider">{now.toLocaleDateString(undefined, { weekday: 'long' })}</p>
              <p className="text-2xl font-bold text-slate-900 tabular-nums">{now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</p>
              <p className="text-xs text-slate-500">{now.toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}</p>
            </div>
          </div>
        </Card>

        {/* Punch widget */}
        {user.user_type === 'internal' && <PunchWidget />}

        {/* Stats cards (Phase 22 hotfix — wired to real data + clickable) */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <button onClick={() => navigate('/portal/my-tasks')} className="text-left hover:scale-[1.02] transition-transform" data-testid="stat-tasks-link">
            <StatCard icon={CheckSquare} label="My Tasks" value={taskCount === null ? '—' : taskCount} hint={taskCount > 0 ? 'open tasks' : 'all done!'} color="text-leamss-teal-600" testid="stat-tasks" />
          </button>
          <button onClick={() => navigate('/notifications')} className="text-left hover:scale-[1.02] transition-transform" data-testid="stat-notifs-link">
            <StatCard icon={Bell} label="Notifications" value={notifCount} hint={notifCount > 0 ? 'unread' : 'all caught up'} color="text-amber-600" testid="stat-notifs" />
          </button>
          <button onClick={() => navigate('/portal/attendance')} className="text-left hover:scale-[1.02] transition-transform" data-testid="stat-attendance-link">
            <StatCard icon={Clock} label="Attendance" value="View" hint="Punch & monthly" color="text-emerald-600" testid="stat-attendance" />
          </button>
          <StatCard icon={Sparkles} label="Modules" value={`${modules.length}`} hint="available to you" color="text-leamss-red-600" testid="stat-modules" />
        </div>

        {/* Your Access */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <Sparkles className={`h-5 w-5 ${theme.text}`} /> Your Access
              </h3>
              <p className="text-xs text-slate-500">{modules.filter((m) => m !== 'my_incentives' && m !== 'call_log').concat(modules.includes('my_crm') ? [] : ['my_crm']).length} module{modules.length === 1 ? '' : 's'} granted via your role</p>
            </div>
          </div>

          {modules.length === 0 ? (
            <p className="text-slate-500 text-sm italic">No modules assigned yet. Contact your admin.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {modules
                .filter((m) => m !== 'my_incentives' && m !== 'call_log')
                .concat(modules.includes('my_crm') ? [] : ['my_crm'])
                .map((m) => {
                // Feb 26 hotfix v2 — derive friendly label for URL-path style RBAC v2 ui_modules
                let metaFromPath = null;
                if (typeof m === 'string' && m.startsWith('/')) {
                  const last = m.split('/').filter(Boolean).pop() || m;
                  metaFromPath = {
                    label: last.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
                    icon: ChevronRight,
                  };
                }
                const meta = MODULE_META[m] || metaFromPath || { label: m.replace(/_/g, ' '), icon: ChevronRight };
                const Icon = meta.icon;
                return (
                  <button
                    key={m}
                    onClick={() => handleModuleClick(m)}
                    className="p-4 bg-white border border-slate-200 rounded-lg hover:border-slate-400 hover:shadow-md transition-all text-left group"
                    data-testid={`module-${m}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-md" style={{ background: `${theme.color}15` }}>
                        <Icon className="h-4 w-4" style={{ color: theme.color }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`font-medium text-slate-800 text-sm capitalize truncate ${m === 'pa_pipeline_own' ? 'underline' : ''}`}>{meta.label}</p>
                        <p className="text-[10px] text-slate-400 truncate font-mono">{m}</p>
                      </div>
                      <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-500 transition-colors flex-shrink-0" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        {/* Footer note */}
        <Card className="p-4 bg-slate-100 border-slate-200">
          <p className="text-xs text-slate-600 text-center">
            🚧 This is a placeholder dashboard. Your department-specific dashboard with full features will be built in upcoming phases.
          </p>
        </Card>
      </main>
    </div>
  );
}

const StatCard = ({ icon: Icon, label, value, hint, color, testid }) => (
  <Card className="p-4 hover:shadow-md transition-shadow" data-testid={testid}>
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs uppercase tracking-wider text-slate-500 font-medium">{label}</p>
        <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
        <p className="text-[10px] text-slate-400 mt-0.5">{hint}</p>
      </div>
      <Icon className={`h-5 w-5 ${color}`} />
    </div>
  </Card>
);