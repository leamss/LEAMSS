/**
 * Phase 7.5 — Pipeline Cockpit (PRODUCTION)
 *
 * Live, LEAMSS-branded single-pane cockpit for Sales/Admin.
 * Wires to /api/cockpit/{funnel,cards,brief,card/...} with 30-sec auto-refresh.
 *
 * Brand palette (NO blue/indigo):
 *   Teal  #0F766E   Orange  #EA7C2E   Red  #D32F2F   Gold  #D4A017
 *
 * Route: /admin/cockpit
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Plus, Search, Command, Globe2, FileText, Users, Briefcase, CheckCircle2,
  Filter, ArrowDownUp, ChevronRight, Wand2, Sparkles, Send, Bot, Zap,
  Home, Bell, Inbox, Shield, FileBadge, MessageSquare, X, AlertCircle,
  Clock, Mail, Loader2, RefreshCw, CheckSquare, Square, UserPlus, ExternalLink, Download,
} from 'lucide-react';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetClose,
} from '@/components/ui/sheet';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ─── LEAMSS brand tokens (mirrors PDF v2 palette) ────────────────────────────
const C = {
  bg:          '#FAFAF9',           // cream
  card:        '#FFFFFF',
  border:      '#E5E7EB',
  borderSoft:  '#F1F5F9',
  ink:         '#1F2937',           // charcoal
  body:        '#475569',
  muted:       '#94A3B8',
  // brand
  teal:        '#0F766E',
  tealDeep:    '#115E59',
  tealDark:    '#134E4A',
  tealWash:    '#F0FDFA',
  tealWash2:   '#CCFBF1',
  orange:      '#EA7C2E',
  orangeDeep:  '#C2410C',
  orangeWash:  '#FFF7ED',
  orangeWash2: '#FFEDD5',
  red:         '#D32F2F',
  redWash:     '#FEE2E2',
  gold:        '#D4A017',
  goldLight:   '#FBBF24',
  goldWash:    '#FEF3C7',
};

const FUNNEL_DEF = [
  { key: 'leads',       label: 'Leads',           icon: Inbox },
  { key: 'assessments', label: 'Assessments',     icon: FileText },
  { key: 'pa',          label: 'Pre-Assessments', icon: FileBadge },
  { key: 'proposals',   label: 'Proposals',       icon: Send },
  { key: 'cases',       label: 'Active Cases',    icon: Briefcase },
  { key: 'closed',      label: 'Closed',          icon: CheckCircle2 },
];

const COUNTRY_FLAG = {
  AU: '🇦🇺', CA: '🇨🇦', NZ: '🇳🇿', UK: '🇬🇧', US: '🇺🇸', USA: '🇺🇸',
};

const URGENCY_RING = {
  high:   C.red,
  medium: C.orange,
  low:    C.teal,
};

const BRIEF_ICONS = { alert: AlertCircle, clock: Clock, mail: Mail, shield: Shield };

// ─── Component ───────────────────────────────────────────────────────────────
export default function Cockpit() {
  const navigate = useNavigate();
  const [funnel, setFunnel] = useState(null);
  const [cards, setCards] = useState([]);
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeStage, setActiveStage] = useState('all');
  const [search, setSearch] = useState('');
  const [ownerFilter, setOwnerFilter] = useState('all'); // 'me' | 'all'
  const [sortMode, setSortMode] = useState('recent');
  const [selectedCard, setSelectedCard] = useState(null);
  const [cardDetail, setCardDetail] = useState(null);
  const [showCmdK, setShowCmdK] = useState(false);
  const [cmdQuery, setCmdQuery] = useState('');

  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedLeadIds, setSelectedLeadIds] = useState([]);
  const [convertingPA, setConvertingPA] = useState(false);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [bulkAssignTarget, setBulkAssignTarget] = useState('');
  const [bulkAssignRole, setBulkAssignRole] = useState('agent'); // 'agent' | 'partner' | 'case_manager'

  const headers = useMemo(() => {
    const t = localStorage.getItem('token');
    return t ? { Authorization: `Bearer ${t}` } : {};
  }, []);

  // Fetch team members for assignment
  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/users`, { headers });
        if (Array.isArray(r.data)) {
          // Filter all active staff (partners, case managers, sales executives, admins)
          setTeamMembers(r.data.filter(u => u.role !== 'client' && u.status !== 'inactive'));
        }
      } catch (e) {
        console.error('Failed to load team members for lead assignment', e);
      }
    })();
  }, [headers]);

  const handleConvertToPA = async (leadId) => {
    try {
      setConvertingPA(true);
      const res = await axios.post(`${API}/leads/${leadId}/convert-to-pa`, {}, { headers });
      setConvertingPA(false);
      fetchAll();
      if (res.data?.pa_id) {
        navigate(`/admin?tab=pre-assessments&pa_id=${res.data.pa_id}`);
      }
    } catch (e) {
      setConvertingPA(false);
      alert(e.response?.data?.detail || 'Failed to convert lead to Pre-Assessment');
    }
  };

  const handleBulkConvertToPA = async () => {
    if (!selectedLeadIds.length) return;
    try {
      setBulkActionLoading(true);
      const res = await axios.post(`${API}/leads/bulk-create-pa`, { lead_ids: selectedLeadIds }, { headers });
      setBulkActionLoading(false);
      setSelectedLeadIds([]);
      fetchAll();
      alert(`Successfully created ${res.data?.created_count || selectedLeadIds.length} Pre-Assessments!`);
      navigate('/admin?tab=pre-assessments');
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Bulk Pre-Assessment creation failed');
    }
  };

  const handleSendToBulkAssessment = async (leadIds = [], paidOnly = false) => {
    try {
      setBulkActionLoading(true);
      const res = await axios.post(`${API}/bulk-assessments/from-leads`, {
        lead_ids: leadIds.length ? leadIds : undefined,
        paid_only: paidOnly,
        batch_name: paidOnly
          ? `Paid Registrations (${new Date().toLocaleDateString('en-GB')})`
          : `Website Registrations (${new Date().toLocaleDateString('en-GB')})`,
      }, { headers });
      setBulkActionLoading(false);
      setSelectedLeadIds([]);
      navigate('/sales/bulk-assessment');
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Failed to create bulk assessment batch');
    }
  };

  const selectSequence = (mode) => {
    const leadCards = cards.filter(c => c.type === 'lead');
    if (mode === 'all') {
      setSelectedLeadIds(leadCards.map(c => c.id));
    } else if (mode === 'paid') {
      const paid = leadCards.filter(c =>
        c.payment_status === 'success' || c.payment_status === 'paid' || (c.payment_amount && c.payment_amount > 0)
      );
      setSelectedLeadIds(paid.map(c => c.id));
    } else if (mode === 'unassigned') {
      const unassigned = leadCards.filter(c => !c.owner?.id || c.owner?.name === 'Unassigned');
      setSelectedLeadIds(unassigned.map(c => c.id));
    } else if (mode === 'clear') {
      setSelectedLeadIds([]);
    } else if (Number(mode) > 0) {
      setSelectedLeadIds(leadCards.slice(0, Number(mode)).map(c => c.id));
    }
  };

  const handleStartClientAssessment = (rec = {}) => {
    const params = new URLSearchParams();
    if (rec.name || selectedCard?.name) params.set('name', rec.name || selectedCard?.name || '');
    if (rec.email) params.set('email', rec.email);
    if (rec.phone || rec.mobile) params.set('phone', rec.phone || rec.mobile);
    if (rec.latest_qualification || rec.qualification) params.set('qualification', rec.latest_qualification || rec.qualification);
    if (rec.total_work_experience || rec.experience) params.set('experience', rec.total_work_experience || rec.experience);
    if (rec.date_of_birth || rec.dob) params.set('dob', rec.date_of_birth || rec.dob);
    if (rec.marital_status) params.set('marital', rec.marital_status);
    if (rec.resume_url || rec.resume_path) params.set('resume_url', rec.resume_url || rec.resume_path);
    if (selectedCard?.id) params.set('lead_id', selectedCard.id);

    navigate(`/sales/client-assessment?${params.toString()}`);
  };

  const handleAssignLead = async (leadId, targetId, targetName, assignmentType = 'agent') => {
    try {
      await axios.put(`${API}/leads/${leadId}/assign`, {
        assigned_to: targetId,
        assigned_to_name: targetName,
        assignment_type: assignmentType,
      }, { headers });
      fetchAll();
      if (cardDetail?.record) {
        const updated = { ...cardDetail.record };
        if (assignmentType === 'partner') {
          updated.partner_id = targetId;
          updated.partner_name = targetName;
        } else if (assignmentType === 'case_manager') {
          updated.case_manager_id = targetId;
          updated.case_manager_name = targetName;
        } else {
          updated.assigned_to = targetId;
          updated.assigned_to_name = targetName;
        }
        setCardDetail({
          ...cardDetail,
          record: updated,
        });
      }
    } catch (e) {
      alert(e.response?.data?.detail || 'Failed to assign lead');
    }
  };

  const handleBulkAssign = async () => {
    if (!selectedLeadIds.length || !bulkAssignTarget) return;
    const targetUser = teamMembers.find(u => u.id === bulkAssignTarget);
    const targetName = targetUser?.name || 'Assigned Member';
    try {
      setBulkActionLoading(true);
      await axios.post(`${API}/leads/bulk-assign`, {
        lead_ids: selectedLeadIds,
        assigned_to: bulkAssignTarget,
        assigned_to_name: targetName,
        assignment_type: bulkAssignRole,
      }, { headers });
      setBulkActionLoading(false);
      setSelectedLeadIds([]);
      fetchAll();
      alert(`Successfully assigned ${selectedLeadIds.length} leads to ${targetName} (${bulkAssignRole.replace('_', ' ')})`);
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Bulk assign failed');
    }
  };

  const toggleLeadSelection = (leadId, e) => {
    if (e) e.stopPropagation();
    setSelectedLeadIds(prev =>
      prev.includes(leadId) ? prev.filter(id => id !== leadId) : [...prev, leadId]
    );
  };


  // ─── Data fetchers ─────────────────────────────────────────────────────────
  const fetchFunnel = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/cockpit/funnel`, { headers });
      setFunnel(r.data);
    } catch (e) { console.error('funnel', e); }
  }, [headers]);

  const fetchCards = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (activeStage !== 'all') params.set('stage', activeStage);
      if (search) params.set('search', search);
      if (ownerFilter !== 'all') params.set('owner', ownerFilter);
      params.set('sort', sortMode);
      params.set('limit', '60');
      const r = await axios.get(`${API}/cockpit/cards?${params}`, { headers });
      setCards(r.data.items || []);
    } catch (e) { console.error('cards', e); }
  }, [headers, activeStage, search, ownerFilter, sortMode]);

  const fetchBrief = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/cockpit/brief`, { headers });
      setBrief(r.data);
    } catch (e) { console.error('brief', e); }
  }, [headers]);

  const fetchAll = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([fetchFunnel(), fetchCards(), fetchBrief()]);
    setRefreshing(false);
    setLoading(false);
  }, [fetchFunnel, fetchCards, fetchBrief]);

  // Initial + filter-change fetch
  useEffect(() => { fetchAll(); }, [fetchAll]);

  // 30-sec auto-refresh polling (lightweight — just funnel + cards, not brief)
  useEffect(() => {
    const id = setInterval(() => {
      fetchFunnel();
      fetchCards();
    }, 30000);
    return () => clearInterval(id);
  }, [fetchFunnel, fetchCards]);

  // Drill-in detail fetch when a card is selected
  useEffect(() => {
    if (!selectedCard) { setCardDetail(null); return; }
    (async () => {
      try {
        const r = await axios.get(
          `${API}/cockpit/card/${selectedCard.type}/${selectedCard.id}`,
          { headers }
        );
        setCardDetail(r.data);
      } catch (e) { console.error('drill', e); }
    })();
  }, [selectedCard, headers]);

  // Cmd-K keyboard shortcut
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowCmdK(true);
      } else if (e.key === 'Escape') {
        setShowCmdK(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const totalActive = funnel?.total_active ?? 0;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: C.bg }}>
        <Loader2 className="h-8 w-8 animate-spin" style={{ color: C.teal }} />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex"
      style={{ background: C.bg, fontFamily: "'Manrope', sans-serif" }}
      data-testid="cockpit-root"
    >
      {/* ───────── LEFT SIDEBAR ───────── */}
      <aside
        className="w-16 md:w-60 border-r flex flex-col justify-between shrink-0 transition-all"
        style={{ background: C.card, borderColor: C.border }}
      >
        <div>
          <div className="px-4 py-5 border-b" style={{ borderColor: C.border }}>
            <div className="flex items-center gap-2">
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center shadow-sm"
                style={{ background: C.teal, color: '#fff' }}
              >
                <Globe2 className="h-5 w-5" />
              </div>
              <div className="hidden md:block">
                <h1 className="font-bold text-base leading-tight" style={{ color: C.tealDark }}>LEAMSS</h1>
                <p className="text-[10px] tracking-wide uppercase" style={{ color: C.muted, letterSpacing: '0.06em' }}>
                  Cockpit
                </p>
              </div>
            </div>
          </div>
          <nav className="px-3 py-4 space-y-1">
            {[
              { icon: Home,       label: 'Dashboard',         to: '/admin' },
              { icon: Zap,        label: 'Pipeline Cockpit',  to: '/admin/cockpit', active: true },
              { icon: Globe2,     label: 'Migration Atlas',   to: '/admin/atlas/search' },
              { icon: FileText,   label: 'Assessments',       to: '/sales/my-assessments' },
              { icon: FileBadge,  label: 'Pre-Assessments',   to: '/admin?tab=pre-assessments' },
              { icon: Briefcase,  label: 'Active Cases',      to: '/admin?tab=cases' },
              { icon: Shield,     label: 'Verification Hub',  to: '/admin/verify-hub' },
              { icon: Users,      label: 'Smart Sales Helper', to: '/sales/client-assessment' },
            ].map(item => (
              <button
                key={item.label}
                onClick={() => item.to && navigate(item.to)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors"
                style={{
                  background: item.active ? C.tealWash : 'transparent',
                  color:      item.active ? C.tealDark : C.body,
                  fontWeight: item.active ? 700 : 500,
                  border:     item.active ? `1px solid ${C.tealWash2}` : '1px solid transparent',
                }}
                data-testid={`cockpit-nav-${item.label.replace(/\s+/g, '-').toLowerCase()}`}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <span className="hidden md:inline">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
        <div className="p-4 border-t hidden md:block" style={{ borderColor: C.border }}>
          <div className="flex items-center gap-2 text-[10px]" style={{ color: C.muted }}>
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: C.teal }}/>
            Live · auto-refresh 30s
          </div>
        </div>
      </aside>

      {/* ───────── MAIN CONTENT ───────── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* TOP BAR */}
        <header
          className="h-16 border-b flex items-center justify-between px-6 shrink-0"
          style={{ background: C.card, borderColor: C.border }}
          data-testid="cockpit-topbar"
        >
          <div>
            <h2 className="font-bold text-xl tracking-tight" style={{ color: C.tealDark }}>
              Pipeline Cockpit
            </h2>
            <p className="text-xs" style={{ color: C.muted }}>
              <strong style={{ color: C.ink, fontFamily: 'monospace' }}>{totalActive}</strong> active records
              {refreshing && (
                <span className="ml-2 inline-flex items-center gap-1" style={{ color: C.teal }}>
                  <Loader2 className="h-3 w-3 animate-spin" /> refreshing
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCmdK(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-md border text-sm transition-colors hover:bg-slate-50"
              style={{ background: C.bg, borderColor: C.border, color: C.muted }}
              data-testid="cockpit-cmdk-trigger"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Quick search...</span>
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
                   style={{ borderColor: C.border, background: C.card }}>⌘K</kbd>
            </button>
            <button
              onClick={fetchAll}
              disabled={refreshing}
              className="p-2 rounded-md transition-colors hover:bg-slate-100"
              data-testid="cockpit-refresh-btn"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} style={{ color: C.body }}/>
            </button>
            <button
              className="relative p-2 rounded-md transition-colors hover:bg-slate-100"
              data-testid="cockpit-notifications-btn"
            >
              <Bell className="h-5 w-5" style={{ color: C.body }} />
              {brief?.insights?.length > 0 && (
                <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full" style={{ background: C.orange }}/>
              )}
            </button>
            <button
              onClick={() => navigate('/sales/client-assessment')}
              className="px-4 py-2 rounded-md font-bold text-sm shadow-sm transition-all hover:shadow-md flex items-center gap-2"
              style={{ background: C.teal, color: '#fff' }}
              data-testid="cockpit-new-client-btn"
            >
              <Plus className="h-4 w-4" />New Client
            </button>
          </div>
        </header>

        {/* FUNNEL BAR */}
        <div
          className="px-6 py-4 border-b shrink-0"
          style={{ background: C.card, borderColor: C.border }}
          data-testid="cockpit-funnel-bar"
        >
          <div className="flex gap-2 overflow-x-auto pb-1">
            <FunnelChip
              label="All"
              count={totalActive}
              icon={Zap}
              active={activeStage === 'all'}
              onClick={() => setActiveStage('all')}
              testid="cockpit-funnel-all"
            />
            {FUNNEL_DEF.map((f, idx) => (
              <div key={f.key} className="flex items-center gap-2">
                <FunnelChip
                  label={f.label}
                  count={funnel?.[f.key] ?? 0}
                  icon={f.icon}
                  active={activeStage === f.key}
                  onClick={() => setActiveStage(f.key)}
                  testid={`cockpit-funnel-${f.key}`}
                />
                {idx < FUNNEL_DEF.length - 1 && (
                  <ChevronRight className="h-4 w-4" style={{ color: C.muted }} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* FILTER ROW */}
        <div
          className="px-6 py-3 flex items-center justify-between border-b shrink-0"
          style={{ background: C.bg, borderColor: C.borderSoft }}
        >
          <div className="flex items-center gap-2 flex-wrap">
            <FilterButton
              icon={Users}
              label={ownerFilter === 'me' ? 'Owner: Me' : 'Owner: All'}
              onClick={() => setOwnerFilter(ownerFilter === 'me' ? 'all' : 'me')}
              active={ownerFilter === 'me'}
              testid="cockpit-filter-owner"
            />
            <FilterButton
              icon={ArrowDownUp}
              label={
                sortMode === 'recent'     ? 'Newest First' :
                sortMode === 'oldest'     ? 'Oldest First (FIFO)' :
                sortMode === 'paid_first' ? '💰 Paid First' :
                sortMode === 'score_desc' ? 'Highest Score' : 'Lowest Score'
              }
              onClick={() => {
                const order = ['recent', 'oldest', 'paid_first', 'score_desc', 'score_asc'];
                setSortMode(order[(order.indexOf(sortMode) + 1) % order.length]);
              }}
              testid="cockpit-filter-sort"
            />

            {/* Sequential Batch Select Dropdown */}
            <select
              onChange={(e) => { selectSequence(e.target.value); e.target.value = ''; }}
              className="text-xs px-2.5 py-1.5 rounded-md border font-semibold outline-none cursor-pointer"
              style={{ borderColor: C.border, background: C.card, color: C.ink }}
            >
              <option value="">⚡ Select in Sequence...</option>
              <option value="5">Select First 5 (Sequential)</option>
              <option value="10">Select First 10 (Sequential)</option>
              <option value="20">Select First 20 (Sequential)</option>
              <option value="all">Select All Leads</option>
              <option value="paid">Select Paid Only (Payment Success)</option>
              <option value="unassigned">Select Unassigned Only</option>
              <option value="clear">Deselect All</option>
            </select>

            <div className="relative">
              <Search className="h-3 w-3 absolute left-2 top-1/2 -translate-y-1/2" style={{ color: C.muted }} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name..."
                className="pl-7 pr-3 py-1.5 rounded-md border text-xs outline-none"
                style={{ background: C.card, borderColor: C.border, color: C.ink, width: '180px' }}
                data-testid="cockpit-search-input"
              />
            </div>

            {/* Paid-Only Bulk Pre-Assessment */}
            <button
              onClick={() => handleSendToBulkAssessment([], true)}
              className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm hover:opacity-90"
              style={{ borderColor: C.teal, background: C.tealWash, color: C.tealDark }}
              title="Process all Payment Success registrations in Bulk Pre-Assessment"
            >
              <Zap className="h-3.5 w-3.5" /> 💰 Process Paid Only
            </button>

            <button
              onClick={() => handleSendToBulkAssessment(selectedLeadIds, false)}
              className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm hover:opacity-90"
              style={{ borderColor: C.gold, background: C.goldWash, color: C.orangeDeep }}
              title="Open Bulk Pre-Assessment with website registrations"
            >
              <Sparkles className="h-3.5 w-3.5" /> Bulk Assessment (All)
            </button>
          </div>
          <p className="text-xs" style={{ color: C.muted }}>
            Showing <strong style={{ color: C.ink }}>{cards.length}</strong>
          </p>
        </div>

        {/* CARD GRID */}
        <div className="flex-1 overflow-y-auto p-6 relative">
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="cockpit-pipeline-grid">
            {cards.map(card => (
              <PipelineCard
                key={`${card.type}-${card.id}`}
                card={card}
                onClick={() => setSelectedCard(card)}
                isSelected={selectedLeadIds.includes(card.id)}
                onToggleSelect={card.type === 'lead' ? (e) => toggleLeadSelection(card.id, e) : null}
                onConvertToPA={card.type === 'lead' ? (e) => { e.stopPropagation(); handleConvertToPA(card.id); } : null}
              />
            ))}
          </div>
          {cards.length === 0 && (
            <div className="text-center py-16">
              <Inbox className="h-12 w-12 mx-auto mb-3" style={{ color: C.muted }} />
              <p className="text-sm" style={{ color: C.body }}>
                No records in this view. Try clearing filters or click <strong>+ New Client</strong>.
              </p>
            </div>
          )}

          {/* FLOATING BULK ACTIONS TOOLBAR */}
          {selectedLeadIds.length > 0 && (
            <div
              className="sticky bottom-4 left-0 right-0 mx-auto max-w-3xl bg-white border rounded-xl shadow-2xl p-3.5 z-40 flex items-center justify-between gap-3 animate-in fade-in slide-in-from-bottom-4"
              style={{ borderColor: C.teal, background: '#FFFFFF', boxShadow: '0 10px 25px -5px rgba(15, 118, 110, 0.2), 0 8px 10px -6px rgba(15, 118, 110, 0.2)' }}
            >
              <div className="flex items-center gap-2 shrink-0">
                <span className="w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs" style={{ background: C.tealWash, color: C.tealDark }}>
                  {selectedLeadIds.length}
                </span>
                <p className="text-xs font-bold" style={{ color: C.ink }}>
                  Selected
                </p>
              </div>

              <div className="flex items-center gap-2 flex-wrap justify-end">
                {/* Assignment Role Selector */}
                <select
                  value={bulkAssignRole}
                  onChange={(e) => setBulkAssignRole(e.target.value)}
                  className="text-xs px-2.5 py-1.5 rounded-lg border outline-none font-bold cursor-pointer"
                  style={{ borderColor: C.teal, background: C.tealWash, color: C.tealDark }}
                  title="Choose assignment target role"
                >
                  <option value="agent">Role: Lead Owner</option>
                  <option value="partner">Role: Partner</option>
                  <option value="case_manager">Role: Case Manager</option>
                </select>

                {/* Target User Dropdown */}
                <select
                  value={bulkAssignTarget}
                  onChange={(e) => setBulkAssignTarget(e.target.value)}
                  className="text-xs px-2.5 py-1.5 rounded-lg border outline-none font-medium max-w-[190px] cursor-pointer"
                  style={{ borderColor: C.border, background: C.bg, color: C.ink }}
                >
                  <option value="">Select Member / User...</option>
                  {renderUserOptions(teamMembers)}
                </select>

                <button
                  onClick={handleBulkAssign}
                  disabled={!bulkAssignTarget || bulkActionLoading}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-colors disabled:opacity-50 shadow-sm"
                  style={{ background: C.teal }}
                >
                  Assign
                </button>

                {/* Bulk Create PA */}
                <button
                  onClick={handleBulkConvertToPA}
                  disabled={bulkActionLoading}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 disabled:opacity-50"
                  style={{ background: C.tealDark }}
                >
                  <Zap className={`h-3.5 w-3.5 ${bulkActionLoading ? 'animate-spin' : ''}`} />
                  {bulkActionLoading ? 'Creating...' : 'Bulk PA'}
                </button>

                {/* Bulk Assessment Reports */}
                <button
                  onClick={() => handleSendToBulkAssessment(selectedLeadIds)}
                  disabled={bulkActionLoading}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 disabled:opacity-50"
                  style={{ background: C.orange }}
                >
                  <Sparkles className={`h-3.5 w-3.5 ${bulkActionLoading ? 'animate-spin' : ''}`} />
                  {bulkActionLoading ? 'Processing...' : 'Bulk Reports'}
                </button>

                <button
                  onClick={() => setSelectedLeadIds([])}
                  className="p-1.5 rounded-lg text-xs font-bold hover:bg-slate-100"
                  style={{ color: C.muted }}
                  title="Clear Selection"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ───────── RIGHT AI SIDEBAR ───────── */}
      <aside
        className="w-80 border-l hidden lg:flex flex-col shrink-0 sticky top-0 h-screen overflow-y-auto"
        style={{ background: C.bg, borderColor: C.border }}
        data-testid="cockpit-ai-sidebar"
      >
        <div className="p-5 border-b" style={{ borderColor: C.border, background: C.card }}>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: C.teal, color: '#fff' }}>
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold" style={{ color: C.tealDark }}>AI Co-Pilot</h3>
              <p className="text-[10px]" style={{ color: C.muted }}>Live insights · auto-refresh</p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-5 flex-1">
          {/* CMD-K HINT */}
          <button
            onClick={() => setShowCmdK(true)}
            className="w-full flex items-center justify-between p-3 rounded-lg border shadow-sm text-left transition-all hover:shadow-md"
            style={{ borderColor: C.border, background: C.card }}
            data-testid="cockpit-cmdk-hint"
          >
            <span className="text-xs font-bold flex items-center gap-2" style={{ color: C.body }}>
              <Command className="h-3.5 w-3.5" style={{ color: C.teal }} />
              Quick Commands
            </span>
            <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border" style={{ borderColor: C.border }}>⌘K</kbd>
          </button>

          {/* QUICK ACTIONS */}
          <div>
            <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: C.muted, letterSpacing: '0.06em' }}>
              Quick Actions
            </p>
            <div className="space-y-2">
              {[
                { icon: Wand2,         label: 'AI Suggester',     desc: 'Suggest best country + visa',  to: '/sales/client-assessment' },
                { icon: Sparkles,      label: 'Draft Proposal',   desc: 'Auto-write fee proposal',      to: '/admin?tab=pre-assessments' },
                { icon: FileText,      label: 'Generate Report',  desc: 'Branded PDF in 30 sec',        to: '/sales/my-assessments' },
                { icon: MessageSquare, label: 'WhatsApp Share',   desc: 'Send proposal link',           to: '/admin?tab=pre-assessments' },
                { icon: Shield,        label: 'Verification Hub', desc: `${brief?.counts?.pending_verify ?? 0} items pending`, to: '/admin/verify-hub' },
              ].map(item => (
                <button
                  key={item.label}
                  onClick={() => item.to && navigate(item.to)}
                  className="w-full text-left px-3 py-2.5 rounded-lg border hover:shadow-sm transition-all flex items-start gap-3 group"
                  style={{ borderColor: C.border, background: C.card }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.teal)}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}
                  data-testid={`cockpit-ai-action-${item.label.replace(/\s+/g, '-').toLowerCase()}`}
                >
                  <item.icon className="h-4 w-4 mt-0.5 shrink-0" style={{ color: C.teal }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold leading-tight" style={{ color: C.ink }}>{item.label}</p>
                    <p className="text-[10px] mt-0.5 leading-tight" style={{ color: C.muted }}>{item.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* TODAY'S BRIEF — live from /cockpit/brief */}
          <div className="p-4 rounded-lg" style={{ background: C.tealDark, color: '#fff' }}>
            <p className="text-[10px] uppercase tracking-wider font-bold mb-3" style={{ color: C.goldLight, letterSpacing: '0.08em' }}>
              ✨ Today's AI Brief
            </p>
            {brief?.insights?.length ? (
              <div className="space-y-3">
                {brief.insights.map((ins, idx) => {
                  const Icon = BRIEF_ICONS[ins.icon] || AlertCircle;
                  return (
                    <button
                      key={idx}
                      onClick={() => navigate(ins.cta_link)}
                      className="w-full text-left flex items-start gap-2 p-2 rounded-md transition-colors hover:bg-white/10"
                      data-testid={`cockpit-brief-insight-${idx}`}
                    >
                      <Icon className="h-3.5 w-3.5 mt-0.5 shrink-0" style={{ color: C.goldLight }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-bold leading-snug" style={{ color: '#fff' }}>{ins.title}</p>
                        <p className="text-[10px] mt-0.5" style={{ color: C.goldLight }}>
                          {ins.cta_label} <ChevronRight className="h-2.5 w-2.5 inline" />
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.75)' }}>All clear — no urgent items.</p>
            )}
          </div>
        </div>
      </aside>

      {/* DRILL-IN DRAWER */}
      <Sheet open={!!selectedCard} onOpenChange={(open) => !open && setSelectedCard(null)}>
        <SheetContent className="w-full sm:max-w-lg p-0" style={{ background: C.card }} data-testid="cockpit-drill-drawer">
          {selectedCard && (
            <>
              <SheetHeader className="px-6 py-4 border-b" style={{ borderColor: C.border }}>
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <SheetTitle className="text-lg font-bold tracking-tight" style={{ color: C.tealDark }}>
                      {selectedCard.name}
                    </SheetTitle>
                    <SheetDescription className="text-xs mt-1" style={{ color: C.muted }}>
                      {selectedCard.countries.map(c => COUNTRY_FLAG[c] || c).join(' ')} · {selectedCard.score_label}
                    </SheetDescription>
                  </div>
                  <SheetClose className="p-1 rounded hover:bg-slate-100">
                    <X className="h-5 w-5" style={{ color: C.body }} />
                  </SheetClose>
                </div>
              </SheetHeader>
              <div className="p-6 space-y-5">
                {/* Lead-specific Profile Card if type is lead */}
                {selectedCard.type === 'lead' && cardDetail?.record && (
                  <div className="rounded-xl border p-4 space-y-4 shadow-sm" style={{ background: C.bg, borderColor: C.border }}>
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{
                        background: cardDetail.record.payment_status === 'success' ? C.tealWash2 : C.goldWash,
                        color: cardDetail.record.payment_status === 'success' ? C.tealDark : C.orangeDeep,
                      }}>
                        {cardDetail.record.payment_status === 'success' ? '✓ Payment Success' : (cardDetail.record.payment_status || 'Payment Pending')}
                      </span>
                      {cardDetail.record.unique_id && (
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded border" style={{ color: C.ink, borderColor: C.border, background: C.card }}>
                          {cardDetail.record.unique_id}
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Mobile</p>
                        <p className="font-semibold text-sm" style={{ color: C.ink }}>{cardDetail.record.phone || '—'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Email</p>
                        <p className="font-semibold truncate text-sm" style={{ color: C.ink }}>{cardDetail.record.email || '—'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Qualification</p>
                        <p className="font-semibold" style={{ color: C.ink }}>{cardDetail.record.latest_qualification || '—'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Experience</p>
                        <p className="font-semibold" style={{ color: C.ink }}>{cardDetail.record.total_work_experience ? `${cardDetail.record.total_work_experience} yrs` : '—'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>DOB</p>
                        <p className="font-semibold" style={{ color: C.ink }}>{cardDetail.record.date_of_birth || '—'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Marital Status</p>
                        <p className="font-semibold" style={{ color: C.ink }}>{cardDetail.record.marital_status || '—'}</p>
                      </div>
                    </div>

                    {/* Prominent Uploaded Resume Box */}
                    {cardDetail.record.resume_url ? (
                      <div className="p-3 rounded-lg border flex items-center justify-between" style={{ background: C.tealWash, borderColor: C.tealWash2 }}>
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="h-5 w-5 shrink-0" style={{ color: C.teal }} />
                          <div className="min-w-0">
                            <p className="text-xs font-bold truncate" style={{ color: C.tealDark }}>Uploaded Resume</p>
                            <p className="text-[10px] truncate" style={{ color: C.body }}>Ready for evaluation</p>
                          </div>
                        </div>
                        <a
                          href={cardDetail.record.resume_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-1.5 rounded-md text-xs font-bold flex items-center gap-1.5 shadow-sm text-white transition-all hover:opacity-90"
                          style={{ background: C.teal }}
                        >
                          <Download className="h-3.5 w-3.5" /> View / Download
                        </a>
                      </div>
                    ) : (
                      <div className="p-2.5 rounded-lg border text-xs text-center" style={{ background: C.card, borderColor: C.border, color: C.muted }}>
                        No resume uploaded with this registration
                      </div>
                    )}

                    {/* Multi-Role Staff & Partner Assignment */}
                    <div className="pt-3 border-t space-y-3" style={{ borderColor: C.border }}>
                      <p className="text-[10px] uppercase font-bold tracking-wider flex items-center gap-1" style={{ color: C.tealDark }}>
                        <Users className="h-3.5 w-3.5" /> Staff & Partner Assignment
                      </p>

                      <div className="space-y-2.5">
                        {/* Lead Owner / Agent */}
                        <div>
                          <div className="flex items-center justify-between text-[10px] uppercase font-bold mb-1" style={{ color: C.muted }}>
                            <span className="flex items-center gap-1"><UserPlus className="h-3 w-3" /> Lead Owner (Agent)</span>
                            {cardDetail.record.assigned_to_name && cardDetail.record.assigned_to_name !== 'Unassigned' && (
                              <span className="font-semibold capitalize" style={{ color: C.tealDeep }}>{cardDetail.record.assigned_to_name}</span>
                            )}
                          </div>
                          <select
                            value={cardDetail.record.assigned_to || ''}
                            onChange={(e) => {
                              const uId = e.target.value;
                              const user = teamMembers.find(u => u.id === uId);
                              handleAssignLead(selectedCard.id, uId, user?.name || 'Assigned Agent', 'agent');
                            }}
                            className="w-full text-xs px-2.5 py-1.5 rounded-lg border font-medium outline-none cursor-pointer"
                            style={{ borderColor: C.border, background: C.card, color: C.ink }}
                          >
                            <option value="">Select Lead Owner / Agent...</option>
                            {renderUserOptions(teamMembers)}
                          </select>
                        </div>

                        {/* Assigned Partner */}
                        <div>
                          <div className="flex items-center justify-between text-[10px] uppercase font-bold mb-1" style={{ color: C.muted }}>
                            <span className="flex items-center gap-1">🤝 Assigned Partner</span>
                            {cardDetail.record.partner_name && (
                              <span className="font-semibold capitalize" style={{ color: C.orangeDeep }}>{cardDetail.record.partner_name}</span>
                            )}
                          </div>
                          <select
                            value={cardDetail.record.partner_id || ''}
                            onChange={(e) => {
                              const uId = e.target.value;
                              const user = teamMembers.find(u => u.id === uId);
                              handleAssignLead(selectedCard.id, uId, user?.name || 'Assigned Partner', 'partner');
                            }}
                            className="w-full text-xs px-2.5 py-1.5 rounded-lg border font-medium outline-none cursor-pointer"
                            style={{ borderColor: C.border, background: C.card, color: C.ink }}
                          >
                            <option value="">Select Partner...</option>
                            {renderUserOptions(teamMembers)}
                          </select>
                        </div>

                        {/* Assigned Case Manager */}
                        <div>
                          <div className="flex items-center justify-between text-[10px] uppercase font-bold mb-1" style={{ color: C.muted }}>
                            <span className="flex items-center gap-1">📋 Assigned Case Manager</span>
                            {cardDetail.record.case_manager_name && (
                              <span className="font-semibold capitalize" style={{ color: C.tealDark }}>{cardDetail.record.case_manager_name}</span>
                            )}
                          </div>
                          <select
                            value={cardDetail.record.case_manager_id || ''}
                            onChange={(e) => {
                              const uId = e.target.value;
                              const user = teamMembers.find(u => u.id === uId);
                              handleAssignLead(selectedCard.id, uId, user?.name || 'Case Manager', 'case_manager');
                            }}
                            className="w-full text-xs px-2.5 py-1.5 rounded-lg border font-medium outline-none cursor-pointer"
                            style={{ borderColor: C.border, background: C.card, color: C.ink }}
                          >
                            <option value="">Select Case Manager...</option>
                            {renderUserOptions(teamMembers)}
                          </select>
                        </div>
                      </div>
                    </div>

                    {/* Payment transaction details */}
                    {cardDetail.record.razorpay_payment_id && (
                      <div className="pt-2 border-t text-[11px] flex justify-between" style={{ borderColor: C.border }}>
                        <span className="font-mono text-[10px]" style={{ color: C.muted }}>
                          Razorpay ID: {cardDetail.record.razorpay_payment_id}
                        </span>
                        {cardDetail.record.payment_amount && (
                          <span className="font-bold text-[11px]" style={{ color: C.tealDeep }}>
                            ₹{cardDetail.record.payment_amount}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* 1-Click Pre-Assessment & Client Assessment Action Banner */}
                {selectedCard.type === 'lead' && (
                  <div className="p-4 rounded-xl border shadow-sm space-y-3" style={{ background: '#FFFFFF', borderColor: C.gold }}>
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5" style={{ color: C.orangeDeep }}>
                        <Zap className="h-4 w-4" /> Assessment Actions
                      </p>
                      {cardDetail?.record?.converted_pa_number && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded" style={{ background: C.tealWash, color: C.tealDark }}>
                          Converted: {cardDetail.record.converted_pa_number}
                        </span>
                      )}
                    </div>
                    <p className="text-xs" style={{ color: C.body }}>
                      Create an official record, launch full report calculation with attached resume, or process in bulk.
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => handleConvertToPA(selectedCard.id)}
                        disabled={convertingPA}
                        className="w-full py-2.5 px-3 rounded-lg font-bold text-xs text-white flex items-center justify-center gap-1.5 shadow-sm transition-all hover:opacity-95 disabled:opacity-50"
                        style={{ background: C.orange }}
                      >
                        <Zap className={`h-3.5 w-3.5 ${convertingPA ? 'animate-spin' : ''}`} />
                        {convertingPA ? 'Creating...' : '⚡ Create PA'}
                      </button>

                      <button
                        onClick={() => handleStartClientAssessment(cardDetail?.record || {})}
                        className="w-full py-2.5 px-3 rounded-lg font-bold text-xs text-white flex items-center justify-center gap-1.5 shadow-sm transition-all hover:opacity-95"
                        style={{ background: C.teal }}
                      >
                        <Wand2 className="h-3.5 w-3.5" /> Client Assessment
                      </button>
                    </div>

                    <button
                      onClick={() => handleSendToBulkAssessment([selectedCard.id])}
                      disabled={bulkActionLoading}
                      className="w-full py-2 px-3 rounded-lg font-semibold text-xs border flex items-center justify-center gap-1.5 transition-all hover:bg-slate-50 disabled:opacity-50"
                      style={{ borderColor: C.border, color: C.body, background: '#FAFAFA' }}
                    >
                      <Sparkles className="h-3.5 w-3.5 text-amber-500" /> Send to Bulk Pre-Assessment Queue
                    </button>
                  </div>
                )}

                {/* 7-step Lifecycle */}
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider mb-3" style={{ color: C.muted, letterSpacing: '0.08em' }}>
                    Client Journey
                  </p>
                  <div className="space-y-2">
                    {[
                      'Created', 'Eligibility Calculated', 'Report Generated',
                      'Pre-Assessment Created', 'PA Fee Paid', 'Main Fee Paid', 'Case Active'
                    ].map((step, i) => {
                      const done = i < selectedCard.lifecycle;
                      const cur  = i === selectedCard.lifecycle;
                      return (
                        <div key={step} className="flex items-center gap-3" data-testid={`cockpit-lifecycle-step-${i}`}>
                          <div
                            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                            style={{
                              background: done ? C.teal : cur ? C.goldWash : C.borderSoft,
                              color:      done ? '#fff' : cur ? C.orangeDeep : C.muted,
                              border:     cur ? `2px solid ${C.gold}` : 'none',
                            }}
                          >
                            {done ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
                          </div>
                          <p className="text-sm" style={{ color: done ? C.ink : cur ? C.ink : C.muted, fontWeight: done || cur ? 600 : 400 }}>
                            {step}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Next Action banner */}
                <div className="p-4 rounded-lg" style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }}>
                  <p className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: C.tealDeep, letterSpacing: '0.08em' }}>
                    Next Action
                  </p>
                  <p className="text-base font-bold tracking-tight" style={{ color: C.ink }}>
                    {selectedCard.next_action}
                  </p>
                </div>

                {/* Quick CTAs */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      const link = cardDetail?.deep_link;
                      if (link) navigate(link);
                      else navigate(`/sales/client-assessment?name=${encodeURIComponent(selectedCard.name || '')}`);
                    }}
                    className="px-3 py-2 rounded-md font-bold text-xs flex items-center justify-center gap-2 shadow-sm"
                    style={{ background: C.teal, color: '#fff' }}
                    data-testid="cockpit-drill-openfull-btn"
                  >
                    <FileText className="h-3.5 w-3.5" />{selectedCard.type === 'lead' ? 'Start Assessment Wizard' : 'Open Full View'}
                  </button>
                  <a
                    href={
                      cardDetail?.record?.phone
                        ? `https://wa.me/${cardDetail.record.phone.replace(/[^0-9]/g, '')}?text=${encodeURIComponent(`Hi ${selectedCard.name}, thank you for registering with LEAMSS for our Navratri Special Offer!`)}`
                        : '#'
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-2 rounded-md font-bold text-xs flex items-center justify-center gap-2 border"
                    style={{ borderColor: C.border, color: C.body, background: '#fff' }}
                    data-testid="cockpit-drill-whatsapp-btn"
                  >
                    <MessageSquare className="h-3.5 w-3.5" style={{ color: '#25D366' }} />Send WhatsApp
                  </a>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* CMD-K MODAL — functional search */}
      {showCmdK && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/40"
          onClick={() => setShowCmdK(false)}
          data-testid="cockpit-cmdk-modal"
        >
          <div
            className="w-full max-w-xl rounded-xl shadow-2xl overflow-hidden"
            style={{ background: C.card }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: C.border }}>
              <Command className="h-4 w-4" style={{ color: C.teal }} />
              <input
                autoFocus
                value={cmdQuery}
                onChange={(e) => setCmdQuery(e.target.value)}
                placeholder="Type a command or search..."
                className="flex-1 outline-none text-sm bg-transparent"
                style={{ color: C.ink }}
                data-testid="cockpit-cmdk-input"
              />
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border" style={{ borderColor: C.border }}>esc</kbd>
            </div>
            <div className="p-2 max-h-96 overflow-y-auto">
              <p className="text-[10px] font-bold uppercase tracking-wider px-3 py-2" style={{ color: C.muted }}>
                Quick Actions
              </p>
              {[
                { label: 'Create new client',                   to: '/sales/client-assessment' },
                { label: 'Open Verification Hub',               to: '/admin/verify-hub' },
                { label: 'Open Country Templates',              to: '/admin/kb/occupation-master' },
                { label: 'Open Pre-Assessments',                to: '/admin?tab=pre-assessments' },
                { label: 'Open Active Cases',                   to: '/admin?tab=cases' },
                { label: 'Open My Assessments',                 to: '/sales/my-assessments' },
              ].filter(c => !cmdQuery || c.label.toLowerCase().includes(cmdQuery.toLowerCase()))
                .map(c => (
                  <button
                    key={c.label}
                    onClick={() => { setShowCmdK(false); navigate(c.to); }}
                    className="w-full text-left px-3 py-2 rounded text-sm cursor-pointer transition-colors hover:bg-slate-50"
                    style={{ color: C.body }}
                    data-testid={`cockpit-cmdk-item-${c.label.replace(/\s+/g, '-').toLowerCase()}`}
                  >
                    {c.label}
                  </button>
                ))}
              {/* Search matching cards inline */}
              {cmdQuery && (
                <>
                  <p className="text-[10px] font-bold uppercase tracking-wider px-3 py-2 mt-2" style={{ color: C.muted }}>
                    Matching records
                  </p>
                  {cards.filter(c => c.name.toLowerCase().includes(cmdQuery.toLowerCase())).slice(0, 5).map(c => (
                    <button
                      key={`${c.type}-${c.id}`}
                      onClick={() => { setShowCmdK(false); setSelectedCard(c); }}
                      className="w-full text-left px-3 py-2 rounded text-sm cursor-pointer transition-colors hover:bg-slate-50 flex items-center justify-between"
                    >
                      <span style={{ color: C.ink }}>{c.name}</span>
                      <span className="text-[10px]" style={{ color: C.muted }}>{c.stage}</span>
                    </button>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Subcomponents ──────────────────────────────────────────────────────────
function renderUserOptions(members = []) {
  const partners = members.filter(u => u.role === 'partner');
  const caseManagers = members.filter(u => u.role === 'case_manager');
  const salesTeam = members.filter(u => ['sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head'].includes(u.role));
  const admins = members.filter(u => ['admin', 'admin_owner'].includes(u.role));
  const others = members.filter(u => !['partner', 'case_manager', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_head', 'admin', 'admin_owner', 'client'].includes(u.role));

  return (
    <>
      {partners.length > 0 && (
        <optgroup label="🤝 Partners">
          {partners.map(u => (
            <option key={u.id} value={u.id}>{u.name} (Partner)</option>
          ))}
        </optgroup>
      )}
      {caseManagers.length > 0 && (
        <optgroup label="📋 Case Managers">
          {caseManagers.map(u => (
            <option key={u.id} value={u.id}>{u.name} (Case Manager)</option>
          ))}
        </optgroup>
      )}
      {salesTeam.length > 0 && (
        <optgroup label="💼 Sales Executives & Agents">
          {salesTeam.map(u => (
            <option key={u.id} value={u.id}>{u.name} ({u.role?.replace(/_/g, ' ')})</option>
          ))}
        </optgroup>
      )}
      {admins.length > 0 && (
        <optgroup label="🛡️ Administrators">
          {admins.map(u => (
            <option key={u.id} value={u.id}>{u.name} (Admin)</option>
          ))}
        </optgroup>
      )}
      {others.length > 0 && (
        <optgroup label="👤 Staff">
          {others.map(u => (
            <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
          ))}
        </optgroup>
      )}
    </>
  );
}

function FunnelChip({ label, count, icon: Icon, active, onClick, testid }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-lg border text-sm font-semibold flex items-center gap-2 cursor-pointer whitespace-nowrap transition-all"
      style={{
        background:  active ? C.tealWash : C.card,
        borderColor: active ? C.teal     : C.border,
        color:       active ? C.tealDeep : C.body,
        boxShadow:   active ? `0 0 0 3px ${C.tealWash2}` : 'none',
      }}
      data-testid={testid}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
      <span
        className="px-2 py-0.5 rounded-full text-xs font-bold"
        style={{
          background: active ? C.tealWash2 : C.borderSoft,
          color:      active ? C.tealDeep  : C.body,
        }}
      >
        {count}
      </span>
    </button>
  );
}

function FilterButton({ icon: Icon, label, onClick, active, testid }) {
  return (
    <button
      onClick={onClick}
      className="px-3 py-1.5 rounded-md border text-xs font-medium flex items-center gap-1.5 transition-colors"
      style={{
        background:  active ? C.tealWash : C.card,
        borderColor: active ? C.teal     : C.border,
        color:       active ? C.tealDeep : C.body,
      }}
      data-testid={testid}
    >
      <Icon className="h-3 w-3" />{label}
    </button>
  );
}

function PipelineCard({ card, onClick, isSelected, onToggleSelect, onConvertToPA }) {
  const ringColor = URGENCY_RING[card.urgency] || C.teal;
  const flags = (card.countries || []).map(c => COUNTRY_FLAG[c] || c).join(' ');
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-xl border shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col gap-3 group relative"
      style={{
        borderColor: isSelected ? C.teal : C.border,
        background:  isSelected ? C.tealWash : '#FFFFFF',
        boxShadow:   isSelected ? '0 0 0 2px rgba(15, 118, 110, 0.25)' : undefined,
      }}
      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.borderColor = C.teal; }}
      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.borderColor = C.border; }}
      data-testid={`cockpit-card-${card.type}-${card.id}`}
    >
      {/* Header */}
      <div className="flex justify-between items-start gap-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          {onToggleSelect && (
            <button
              type="button"
              onClick={onToggleSelect}
              className="mt-0.5 p-0.5 rounded hover:bg-black/5 transition-colors shrink-0"
              title={isSelected ? 'Deselect lead' : 'Select lead'}
            >
              {isSelected ? (
                <CheckSquare className="h-4 w-4" style={{ color: C.teal }} />
              ) : (
                <Square className="h-4 w-4" style={{ color: C.muted }} />
              )}
            </button>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-bold leading-tight tracking-tight truncate" style={{ color: C.ink }}>
              {card.name}
            </h3>
            <p className="text-xs mt-0.5 flex items-center gap-1" style={{ color: C.body }}>
              {flags && <span>{flags}</span>}
              <span style={{ color: C.muted }}>·</span>
              <span className="font-mono text-[10px] truncate">{card.id?.slice(0, 16)}</span>
            </p>
          </div>
        </div>
        {card.score !== null && card.score !== undefined ? (
          <span
            className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-md border whitespace-nowrap shrink-0"
            style={{ color: C.orangeDeep, background: C.goldWash, borderColor: C.goldLight }}
          >
            <Sparkles className="h-3 w-3" />{card.score}
          </span>
        ) : (
          <span
            className="text-[10px] font-bold uppercase px-2 py-1 rounded-md whitespace-nowrap shrink-0"
            style={{
              background: card.payment_status === 'success' ? C.tealWash2 : C.borderSoft,
              color: card.payment_status === 'success' ? C.tealDark : C.muted
            }}
          >
            {card.type === 'lead' ? (card.payment_status === 'success' ? '✓ Paid' : 'New') : '—'}
          </span>
        )}
      </div>

      {/* Score / Service label */}
      <p className="text-xs truncate" style={{ color: C.body }}>
        <strong>{card.score_label}</strong>
      </p>

      {/* 7-step lifecycle bar */}
      <div className="flex gap-1 w-full pt-1">
        {Array.from({ length: 7 }).map((_, i) => {
          const done = i < card.lifecycle;
          const cur  = i === card.lifecycle;
          return (
            <div
              key={i}
              className="h-1.5 flex-1 rounded-full"
              style={{
                background: done ? C.teal : cur ? C.orange : C.borderSoft,
                animation:  cur ? 'pulse 2s infinite' : 'none',
              }}
            />
          );
        })}
      </div>

      {/* Footer */}
      <div className="flex justify-between items-center pt-3 border-t" style={{ borderColor: C.borderSoft }}>
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
               style={{ background: C.tealWash, color: C.tealDeep, border: `1px solid ${C.tealWash2}` }}>
            {(card.owner?.name || card.partner?.name || '—').slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-bold leading-none truncate" style={{ color: C.ink }}>
              {card.owner?.name || card.partner?.name || 'Unassigned'}
            </p>
            <p className="text-[10px] leading-none mt-0.5" style={{ color: C.muted }}>{card.updated_at_human}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {card.partner?.name && card.partner?.name !== 'Unassigned' && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: C.goldWash, color: C.orangeDeep }} title={`Assigned Partner: ${card.partner.name}`}>
              Partner
            </span>
          )}
          {card.case_manager?.name && card.case_manager?.name !== 'Unassigned' && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: C.tealWash2, color: C.tealDark }} title={`Case Manager: ${card.case_manager.name}`}>
              CM
            </span>
          )}
          <span
            className="text-[10px] font-bold flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5"
            style={{ color: ringColor, background: `${ringColor}15` }}
          >
            ● {card.urgency}
          </span>
        </div>
      </div>

      {/* Next action CTA */}
      <div className="flex items-center justify-between pt-1">
        <button
          className="text-xs font-bold flex items-center gap-1 transition-colors"
          style={{ color: C.teal }}
          onClick={(e) => { e.stopPropagation(); onClick(); }}
        >
          <span>{card.next_action}</span>
          <ChevronRight className="h-3 w-3" />
        </button>
        {onConvertToPA && (
          <button
            onClick={onConvertToPA}
            className="text-[10px] font-bold px-2 py-1 rounded shadow-sm flex items-center gap-1 text-white hover:opacity-90"
            style={{ background: C.orange }}
            title="Convert to Pre-Assessment in 1-click"
          >
            <Zap className="h-2.5 w-2.5" /> PA
          </button>
        )}
      </div>
    </div>
  );
}
