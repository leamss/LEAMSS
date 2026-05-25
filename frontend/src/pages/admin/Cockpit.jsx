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
  Clock, Mail, Loader2, RefreshCw,
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

  const headers = useMemo(() => {
    const t = localStorage.getItem('token');
    return t ? { Authorization: `Bearer ${t}` } : {};
  }, []);

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
              { icon: Users,      label: 'Leads',             to: '/admin/leads' },
              { icon: FileText,   label: 'Assessments',       to: '/sales/assessments' },
              { icon: FileBadge,  label: 'Pre-Assessments',   to: '/admin/pre-assessments' },
              { icon: Briefcase,  label: 'Active Cases',      to: '/admin/cases' },
              { icon: Shield,     label: 'Verification Hub',  to: '/admin/verification-hub' },
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
                sortMode === 'recent'     ? 'Recent First' :
                sortMode === 'oldest'     ? 'Oldest First' :
                sortMode === 'score_desc' ? 'Highest Score' : 'Lowest Score'
              }
              onClick={() => {
                const order = ['recent', 'oldest', 'score_desc', 'score_asc'];
                setSortMode(order[(order.indexOf(sortMode) + 1) % order.length]);
              }}
              testid="cockpit-filter-sort"
            />
            <div className="relative">
              <Search className="h-3 w-3 absolute left-2 top-1/2 -translate-y-1/2" style={{ color: C.muted }} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name..."
                className="pl-7 pr-3 py-1.5 rounded-md border text-xs outline-none"
                style={{ background: C.card, borderColor: C.border, color: C.ink, width: '200px' }}
                data-testid="cockpit-search-input"
              />
            </div>
          </div>
          <p className="text-xs" style={{ color: C.muted }}>
            Showing <strong style={{ color: C.ink }}>{cards.length}</strong>
          </p>
        </div>

        {/* CARD GRID */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="cockpit-pipeline-grid">
            {cards.map(card => (
              <PipelineCard
                key={`${card.type}-${card.id}`}
                card={card}
                onClick={() => setSelectedCard(card)}
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
                { icon: Sparkles,      label: 'Draft Proposal',   desc: 'Auto-write fee proposal',      to: '/admin/pre-assessments' },
                { icon: FileText,      label: 'Generate Report',  desc: 'Branded PDF in 30 sec',        to: '/sales/assessments' },
                { icon: MessageSquare, label: 'WhatsApp Share',   desc: 'Send proposal link',           to: '/admin/share-links' },
                { icon: Shield,        label: 'Verification Hub', desc: `${brief?.counts?.pending_verify ?? 0} items pending`, to: '/admin/verification-hub' },
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
                    }}
                    className="px-3 py-2 rounded-md font-bold text-xs flex items-center justify-center gap-2 shadow-sm"
                    style={{ background: C.teal, color: '#fff' }}
                    data-testid="cockpit-drill-openfull-btn"
                  >
                    <FileText className="h-3.5 w-3.5" />Open Full View
                  </button>
                  <button
                    className="px-3 py-2 rounded-md font-bold text-xs flex items-center justify-center gap-2 border"
                    style={{ borderColor: C.border, color: C.body, background: '#fff' }}
                    data-testid="cockpit-drill-whatsapp-btn"
                  >
                    <MessageSquare className="h-3.5 w-3.5" />Send WhatsApp
                  </button>
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
                { label: 'Open Verification Hub',               to: '/admin/verification-hub' },
                { label: 'Open Country Templates',              to: '/admin/country-templates' },
                { label: 'Open Pre-Assessments',                to: '/admin/pre-assessments' },
                { label: 'Open Leads',                          to: '/admin/leads' },
                { label: 'Open Active Cases',                   to: '/admin/cases' },
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

function PipelineCard({ card, onClick }) {
  const ringColor = URGENCY_RING[card.urgency] || C.teal;
  const flags = (card.countries || []).map(c => COUNTRY_FLAG[c] || c).join(' ');
  return (
    <div
      onClick={onClick}
      className="bg-white p-4 rounded-xl border shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col gap-3 group"
      style={{ borderColor: C.border }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.teal)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}
      data-testid={`cockpit-card-${card.type}-${card.id}`}
    >
      {/* Header */}
      <div className="flex justify-between items-start">
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
        {card.score !== null && card.score !== undefined ? (
          <span
            className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-md border whitespace-nowrap"
            style={{ color: C.orangeDeep, background: C.goldWash, borderColor: C.goldLight }}
          >
            <Sparkles className="h-3 w-3" />{card.score}
          </span>
        ) : (
          <span className="text-[10px] font-bold uppercase px-2 py-1 rounded-md whitespace-nowrap"
                style={{ background: C.borderSoft, color: C.muted }}>
            {card.type === 'lead' ? 'New' : '—'}
          </span>
        )}
      </div>

      {/* Score label */}
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
            {(card.owner?.name || '—').slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-[10px] font-bold leading-none truncate" style={{ color: C.ink }}>{card.owner?.name || '—'}</p>
            <p className="text-[10px] leading-none mt-0.5" style={{ color: C.muted }}>{card.updated_at_human}</p>
          </div>
        </div>
        <span
          className="text-[10px] font-bold flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5"
          style={{ color: ringColor, background: `${ringColor}15` }}
        >
          ● {card.urgency}
        </span>
      </div>

      {/* Next action CTA */}
      <button
        className="text-xs font-bold flex items-center justify-between w-full pt-1 transition-colors"
        style={{ color: C.teal }}
        onClick={(e) => { e.stopPropagation(); onClick(); }}
      >
        <span>{card.next_action}</span>
        <ChevronRight className="h-3 w-3" />
      </button>
    </div>
  );
}
