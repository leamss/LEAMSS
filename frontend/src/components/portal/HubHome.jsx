import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles, ArrowRight } from 'lucide-react';

/**
 * Phase 21 Slice 3 Sub-Slice A — HubHome extracted from EmployeesPortal.
 * Pure presentational component; receives all data + config via props
 * so EmployeesPortal keeps owning GROUP_CARDS / ACCENT_MAP and routing state.
 */
export default function HubHome({
  user,
  stats,
  activeGroup,
  setActiveGroup,
  onSelectInternal,
  groupCards,
  accentMap,
}) {
  const navigate = useNavigate();
  const group = groupCards[activeGroup];
  const accent = accentMap[group.accent];

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
        {Object.entries(groupCards).map(([key, g]) => {
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
