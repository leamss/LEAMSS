/**
 * Phase 6.11 — Unified Pipeline Cockpit MOCKUP (Visual Preview Only)
 *
 * This is a STATIC visual mockup for Sir to approve the design BEFORE
 * the production wire-up. Uses /app/design_guidelines.json tokens.
 *
 * Route: /admin/cockpit-mockup
 *
 * No backend calls — all data is hand-curated for visual clarity.
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Plus, Search, Command, Sparkles, Globe2, FileText, Users, Briefcase, CheckCircle2,
  Filter, ArrowDownUp, MoreHorizontal, ChevronRight, Wand2, Bot, Zap, Send,
  Home, Settings, Bell, Inbox, Shield, FileBadge, MessageSquare, X,
} from 'lucide-react';

import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetClose,
} from '@/components/ui/sheet';

// ─────────────────────────────────────────────────────────────────────────────
// Design tokens (mirrored from /app/design_guidelines.json)
// ─────────────────────────────────────────────────────────────────────────────
const C = {
  bg: '#F8FAFC',
  card: '#FFFFFF',
  border: '#E2E8F0',
  borderSoft: '#F1F5F9',
  ink: '#1E1B4B',
  body: '#475569',
  muted: '#94A3B8',
  blue: '#2563EB',
  blueDeep: '#1E40FF',
  indigo: '#312E81',
  indigoDark: '#1E1B4B',
  gold: '#F59E0B',
  goldLight: '#FBBF24',
  blueWash: '#EFF6FF',
  blueWash2: '#DBEAFE',
  goldWash: '#FEF3C7',
  goldBorder: '#FDE68A',
  emeraldWash: '#ECFDF5',
};

// ─────────────────────────────────────────────────────────────────────────────
// Mock pipeline data
// ─────────────────────────────────────────────────────────────────────────────
const FUNNEL = [
  { key: 'leads', label: 'Leads', count: 12, icon: Inbox },
  { key: 'assessments', label: 'Assessments', count: 18, icon: FileText },
  { key: 'pa', label: 'Pre-Assessments', count: 8, icon: FileBadge },
  { key: 'proposals', label: 'Proposals', count: 5, icon: Send },
  { key: 'cases', label: 'Active Cases', count: 9, icon: Briefcase },
  { key: 'closed', label: 'Closed', count: 24, icon: CheckCircle2 },
];

const PIPELINE_CARDS = [
  {
    id: 'C-001', name: 'Ravi Kumar Sharma', stage: 'assessments',
    countries: ['🇦🇺', '🇨🇦'], score: 80, scoreLabel: 'AU 80 · CA 372',
    lifecycle: 2,  // 7-step (0..6)
    nextAction: 'Generate Report', urgency: 'high',
    owner: { name: 'Rohit P', avatar: 'https://images.unsplash.com/photo-1560250097-0b93528c311a?w=64&q=80' },
    updatedAt: '12 min ago', daysInStage: 0,
  },
  {
    id: 'C-002', name: 'Priya Mehta', stage: 'pa',
    countries: ['🇦🇺'], score: 75, scoreLabel: 'AU 75',
    lifecycle: 4,
    nextAction: 'Awaiting Main Fee Payment', urgency: 'medium',
    owner: { name: 'Anita G', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&q=80' },
    updatedAt: '2 hr ago', daysInStage: 3,
  },
  {
    id: 'C-003', name: 'Arjun Singh', stage: 'proposals',
    countries: ['🇨🇦', '🇳🇿'], score: 412, scoreLabel: 'CA 412 · NZ 188',
    lifecycle: 4,
    nextAction: 'Send Proposal PDF', urgency: 'high',
    owner: { name: 'Rohit P', avatar: 'https://images.unsplash.com/photo-1560250097-0b93528c311a?w=64&q=80' },
    updatedAt: '1 day ago', daysInStage: 1,
  },
  {
    id: 'C-004', name: 'Kavya Iyer', stage: 'assessments',
    countries: ['🇬🇧'], score: 68, scoreLabel: 'UK Skilled Worker',
    lifecycle: 1,
    nextAction: 'Run Calculator', urgency: 'low',
    owner: { name: 'Vikram L', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=64&q=80' },
    updatedAt: '4 hr ago', daysInStage: 0,
  },
  {
    id: 'C-005', name: 'Suresh Reddy', stage: 'cases',
    countries: ['🇦🇺'], score: 90, scoreLabel: 'AU 90 · Case #LE-2026-014',
    lifecycle: 6,
    nextAction: 'Document Verification', urgency: 'medium',
    owner: { name: 'Anita G', avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=64&q=80' },
    updatedAt: '30 min ago', daysInStage: 12,
  },
  {
    id: 'C-006', name: 'Nikhil Joshi', stage: 'leads',
    countries: ['🇺🇸', '🇨🇦'], score: null, scoreLabel: 'New Lead · No score yet',
    lifecycle: 0,
    nextAction: 'Start Eligibility Wizard', urgency: 'medium',
    owner: { name: 'Vikram L', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=64&q=80' },
    updatedAt: '8 hr ago', daysInStage: 0,
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────
export default function CockpitMockup() {
  const navigate = useNavigate();
  const [activeStage, setActiveStage] = useState('all');
  const [selectedCard, setSelectedCard] = useState(null);
  const [showCmdK, setShowCmdK] = useState(false);

  const filteredCards = activeStage === 'all'
    ? PIPELINE_CARDS
    : PIPELINE_CARDS.filter(c => c.stage === activeStage);

  return (
    <div
      className="min-h-screen flex"
      style={{ background: C.bg, fontFamily: "'Public Sans', sans-serif" }}
      data-testid="cockpit-mockup"
    >
      {/* ───────── LEFT SIDEBAR ───────── */}
      <aside
        className="w-16 md:w-64 border-r flex flex-col justify-between shrink-0 transition-all"
        style={{ background: C.card, borderColor: C.border }}
      >
        <div>
          <div className="px-4 py-5 border-b" style={{ borderColor: C.border }}>
            <div className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: C.indigo, color: '#fff' }}>
                <Globe2 className="h-5 w-5" />
              </div>
              <div className="hidden md:block">
                <h1 className="font-bold text-base leading-tight" style={{ fontFamily: "'Manrope', sans-serif", color: C.ink }}>LEAMSS</h1>
                <p className="text-[10px] tracking-wide uppercase" style={{ color: C.muted }}>We Value Emotions</p>
              </div>
            </div>
          </div>
          <nav className="px-3 py-4 space-y-1">
            {[
              { icon: Home, label: 'Dashboard', active: false },
              { icon: Zap, label: 'Pipeline Cockpit', active: true },
              { icon: Users, label: 'Clients & Leads' },
              { icon: FileBadge, label: 'Pre-Assessments' },
              { icon: Briefcase, label: 'Active Cases' },
              { icon: Shield, label: 'Verification Hub' },
              { icon: Settings, label: 'Settings' },
            ].map(item => (
              <button
                key={item.label}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors"
                style={{
                  background: item.active ? C.blueWash : 'transparent',
                  color: item.active ? C.blueDeep : C.body,
                  fontWeight: item.active ? 700 : 500,
                  border: item.active ? `1px solid ${C.blueWash2}` : '1px solid transparent',
                }}
                data-testid={`nav-${item.label.replace(/\s+/g, '-').toLowerCase()}`}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <span className="hidden md:inline">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
        <div className="p-4 border-t hidden md:block" style={{ borderColor: C.border }}>
          <div className="flex items-center gap-3">
            <img src="https://images.unsplash.com/photo-1560250097-0b93528c311a?w=64&q=80" alt="me" className="w-9 h-9 rounded-full object-cover border" style={{ borderColor: C.border }} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold truncate" style={{ color: C.ink }}>Rohit Pawar</p>
              <p className="text-[10px]" style={{ color: C.muted }}>Admin · Owner</p>
            </div>
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
            <h2 className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Manrope', sans-serif", color: C.ink }}>
              Pipeline Cockpit
            </h2>
            <p className="text-xs" style={{ color: C.muted }}>
              <span className="font-mono">{PIPELINE_CARDS.length}</span> active records · auto-refresh every 30s
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCmdK(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-md border text-sm transition-colors"
              style={{ background: C.bg, borderColor: C.border, color: C.muted }}
              data-testid="cmdk-trigger"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Quick search...</span>
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border" style={{ borderColor: C.border, background: C.card }}>⌘K</kbd>
            </button>
            <button
              className="relative p-2 rounded-md transition-colors hover:bg-slate-100"
              data-testid="notifications-btn"
            >
              <Bell className="h-5 w-5" style={{ color: C.body }} />
              <span
                className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full"
                style={{ background: C.gold }}
              />
            </button>
            <button
              className="px-4 py-2 rounded-md font-bold text-sm shadow-sm transition-colors flex items-center gap-2"
              style={{ background: C.blue, color: '#fff', fontFamily: "'Manrope', sans-serif" }}
              data-testid="new-client-btn"
            >
              <Plus className="h-4 w-4" />New Client
            </button>
          </div>
        </header>

        {/* FUNNEL BAR */}
        <div
          className="px-6 py-4 border-b shrink-0"
          style={{ background: C.card, borderColor: C.border }}
          data-testid="funnel-bar"
        >
          <div className="flex gap-2 overflow-x-auto pb-1">
            <FunnelChip
              label="All"
              count={PIPELINE_CARDS.length}
              icon={Zap}
              active={activeStage === 'all'}
              onClick={() => setActiveStage('all')}
              testid="funnel-all"
            />
            {FUNNEL.map((f, idx) => (
              <>
                <FunnelChip
                  key={f.key}
                  label={f.label}
                  count={f.count}
                  icon={f.icon}
                  active={activeStage === f.key}
                  onClick={() => setActiveStage(f.key)}
                  testid={`funnel-${f.key}`}
                />
                {idx < FUNNEL.length - 1 && (
                  <div className="flex items-center" key={`sep-${idx}`}>
                    <ChevronRight className="h-4 w-4" style={{ color: C.muted }} />
                  </div>
                )}
              </>
            ))}
          </div>
        </div>

        {/* FILTER ROW */}
        <div
          className="px-6 py-3 flex items-center justify-between border-b shrink-0"
          style={{ background: C.bg, borderColor: C.borderSoft }}
        >
          <div className="flex items-center gap-2">
            <FilterButton icon={Users} label="Owner: Me" />
            <FilterButton icon={Filter} label="All Stages" />
            <FilterButton icon={ArrowDownUp} label="Recent First" />
          </div>
          <p className="text-xs" style={{ color: C.muted }}>
            Showing <strong style={{ color: C.ink }}>{filteredCards.length}</strong> of {PIPELINE_CARDS.length}
          </p>
        </div>

        {/* CARD GRID */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4" data-testid="pipeline-grid">
            {filteredCards.map(card => (
              <PipelineCard
                key={card.id}
                card={card}
                onClick={() => setSelectedCard(card)}
              />
            ))}
          </div>
          {filteredCards.length === 0 && (
            <div className="text-center py-16">
              <Inbox className="h-12 w-12 mx-auto mb-3" style={{ color: C.muted }} />
              <p className="text-sm" style={{ color: C.body }}>
                No records in this stage. Click <strong>+ New Client</strong> to get started.
              </p>
            </div>
          )}
        </div>
      </main>

      {/* ───────── RIGHT AI SIDEBAR ───────── */}
      <aside
        className="w-80 border-l hidden lg:flex flex-col shrink-0 sticky top-0 h-screen overflow-y-auto"
        style={{ background: C.bg, borderColor: C.border }}
        data-testid="ai-sidebar"
      >
        <div className="p-5 border-b" style={{ borderColor: C.border }}>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: C.indigo, color: '#fff' }}>
              <Bot className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-base font-bold" style={{ fontFamily: "'Manrope', sans-serif", color: C.ink }}>AI Co-Pilot</h3>
              <p className="text-[10px]" style={{ color: C.muted }}>Claude Sonnet 4.6 · always ready</p>
            </div>
          </div>
        </div>

        <div className="p-5 space-y-5 flex-1">
          {/* CMD-K HINT */}
          <button
            onClick={() => setShowCmdK(true)}
            className="w-full flex items-center justify-between p-3 rounded-lg border bg-white shadow-sm text-left transition-all hover:shadow-md"
            style={{ borderColor: C.border }}
          >
            <span className="text-xs font-bold flex items-center gap-2" style={{ color: C.body }}>
              <Command className="h-3.5 w-3.5" style={{ color: C.blue }} />
              Quick Commands
            </span>
            <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border" style={{ borderColor: C.border, background: C.bg }}>⌘K</kbd>
          </button>

          {/* QUICK ACTIONS */}
          <div>
            <p className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: C.muted, letterSpacing: '0.05em' }}>
              Quick Actions
            </p>
            <div className="space-y-2">
              {[
                { icon: Wand2, label: 'AI Suggester', desc: 'Suggest best country + visa' },
                { icon: Sparkles, label: 'Draft Proposal', desc: 'Auto-write fee proposal' },
                { icon: FileText, label: 'Generate Report', desc: 'Branded PDF in 30 sec' },
                { icon: MessageSquare, label: 'WhatsApp Share', desc: 'Send proposal link' },
                { icon: Shield, label: 'Verify Hub', desc: '3 items pending' },
              ].map(item => (
                <button
                  key={item.label}
                  className="w-full text-left px-3 py-2.5 rounded-lg border bg-white hover:shadow-sm hover:border-blue-500 transition-all flex items-start gap-3 group"
                  style={{ borderColor: C.border }}
                  data-testid={`ai-action-${item.label.replace(/\s+/g, '-').toLowerCase()}`}
                >
                  <item.icon className="h-4 w-4 mt-0.5 shrink-0 transition-colors group-hover:text-[#2563EB]" style={{ color: C.body }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold leading-tight" style={{ color: C.ink }}>{item.label}</p>
                    <p className="text-[10px] mt-0.5 leading-tight" style={{ color: C.muted }}>{item.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* TODAY'S BRIEF */}
          <div className="p-4 rounded-lg" style={{ background: C.indigoDark, color: '#fff' }}>
            <p className="text-[10px] uppercase tracking-wider font-bold mb-2" style={{ color: C.goldLight, letterSpacing: '0.08em' }}>
              ✨ Today's AI Brief
            </p>
            <p className="text-xs leading-relaxed mb-3" style={{ color: '#E0E7FF' }}>
              <strong>5 leads</strong> haven't been contacted in 48hr.
              <strong className="text-amber-300"> Priya Mehta</strong>'s fee
              window closes tomorrow.
            </p>
            <button className="text-[10px] font-bold flex items-center gap-1" style={{ color: C.goldLight }}>
              Review now <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      </aside>

      {/* DRILL-IN DRAWER (mock) */}
      <Sheet open={!!selectedCard} onOpenChange={(open) => !open && setSelectedCard(null)}>
        <SheetContent className="w-full sm:max-w-lg p-0" style={{ background: C.card }}>
          {selectedCard && (
            <>
              <SheetHeader className="px-6 py-4 border-b" style={{ borderColor: C.border }}>
                <div className="flex items-start justify-between">
                  <div>
                    <SheetTitle className="text-lg font-bold tracking-tight" style={{ fontFamily: "'Manrope', sans-serif", color: C.ink }}>
                      {selectedCard.name}
                    </SheetTitle>
                    <SheetDescription className="text-xs mt-1" style={{ color: C.muted }}>
                      {selectedCard.countries.join(' ')} · {selectedCard.scoreLabel}
                    </SheetDescription>
                  </div>
                  <SheetClose className="p-1 rounded hover:bg-slate-100">
                    <X className="h-5 w-5" style={{ color: C.body }} />
                  </SheetClose>
                </div>
              </SheetHeader>
              <div className="p-6 space-y-5">
                {/* Lifecycle */}
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider mb-3" style={{ color: C.muted, letterSpacing: '0.08em' }}>
                    Client Journey
                  </p>
                  <div className="space-y-2">
                    {['Created', 'Eligibility Calculated', 'Report Generated', 'Pre-Assessment Created', 'PA Fee Paid', 'Main Fee Paid', 'Case Active'].map((step, i) => {
                      const done = i < selectedCard.lifecycle;
                      const cur = i === selectedCard.lifecycle;
                      return (
                        <div key={step} className="flex items-center gap-3">
                          <div
                            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                            style={{
                              background: done ? C.blue : cur ? C.goldWash : C.borderSoft,
                              color: done ? '#fff' : cur ? C.gold : C.muted,
                              border: cur ? `2px solid ${C.gold}` : 'none',
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
                {/* Next Action */}
                <div className="p-4 rounded-lg" style={{ background: C.blueWash, border: `1px solid ${C.blueWash2}` }}>
                  <p className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: C.blueDeep, letterSpacing: '0.08em' }}>
                    Next Action
                  </p>
                  <p className="text-base font-bold tracking-tight" style={{ fontFamily: "'Manrope', sans-serif", color: C.ink }}>
                    {selectedCard.nextAction}
                  </p>
                </div>
                {/* Quick actions */}
                <div className="grid grid-cols-2 gap-2">
                  <button className="px-3 py-2 rounded-md font-bold text-xs flex items-center justify-center gap-2"
                          style={{ background: C.blue, color: '#fff' }}>
                    <FileText className="h-3.5 w-3.5" />Open Full View
                  </button>
                  <button className="px-3 py-2 rounded-md font-bold text-xs flex items-center justify-center gap-2 border"
                          style={{ borderColor: C.border, color: C.body, background: '#fff' }}>
                    <MessageSquare className="h-3.5 w-3.5" />Send WhatsApp
                  </button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* CMD-K MODAL (mock) */}
      {showCmdK && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/40"
          onClick={() => setShowCmdK(false)}
          data-testid="cmdk-modal"
        >
          <div
            className="w-full max-w-xl rounded-xl shadow-2xl overflow-hidden"
            style={{ background: C.card }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: C.border }}>
              <Command className="h-4 w-4" style={{ color: C.blue }} />
              <input
                autoFocus
                placeholder="Type a command or search..."
                className="flex-1 outline-none text-sm"
                style={{ color: C.ink }}
              />
              <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded border" style={{ borderColor: C.border }}>esc</kbd>
            </div>
            <div className="p-2">
              <p className="text-[10px] font-bold uppercase tracking-wider px-3 py-2" style={{ color: C.muted }}>Quick Actions</p>
              {[
                'Create new client',
                'Generate latest assessment report',
                'Go to Verification Hub',
                'Open Country Templates',
                'Toggle dark mode (coming soon)',
              ].map(c => (
                <div key={c} className="px-3 py-2 rounded text-sm hover:bg-slate-50 cursor-pointer" style={{ color: C.body }}>
                  {c}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Subcomponents
// ─────────────────────────────────────────────────────────────────────────────
function FunnelChip({ label, count, icon: Icon, active, onClick, testid }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-lg border text-sm font-semibold flex items-center gap-2 cursor-pointer whitespace-nowrap transition-all"
      style={{
        background: active ? C.blueWash : C.card,
        borderColor: active ? C.blue : C.border,
        color: active ? C.blueDeep : C.body,
        boxShadow: active ? `0 0 0 3px ${C.blueWash2}` : 'none',
      }}
      data-testid={testid}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
      <span
        className="px-2 py-0.5 rounded-full text-xs font-bold"
        style={{
          background: active ? C.blueWash2 : C.borderSoft,
          color: active ? C.blueDeep : C.body,
        }}
      >
        {count}
      </span>
    </button>
  );
}

function FilterButton({ icon: Icon, label }) {
  return (
    <button
      className="px-3 py-1.5 rounded-md border text-xs font-medium flex items-center gap-1.5 hover:bg-white transition-colors"
      style={{ background: C.card, borderColor: C.border, color: C.body }}
    >
      <Icon className="h-3 w-3" />{label}
    </button>
  );
}

function PipelineCard({ card, onClick }) {
  return (
    <div
      onClick={onClick}
      className="bg-white p-4 rounded-xl border shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col gap-3 group"
      style={{ borderColor: C.border }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.blue)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}
      data-testid={`pipeline-card-${card.id}`}
    >
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-bold leading-tight tracking-tight truncate" style={{ fontFamily: "'Manrope', sans-serif", color: C.ink }}>
            {card.name}
          </h3>
          <p className="text-xs mt-0.5 flex items-center gap-1" style={{ color: C.body }}>
            <span>{card.countries.join(' ')}</span>
            <span style={{ color: C.muted }}>·</span>
            <span className="font-mono text-[10px]">{card.id}</span>
          </p>
        </div>
        {card.score !== null ? (
          <span
            className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-md border"
            style={{ color: '#D97706', background: C.goldWash, borderColor: C.goldBorder }}
          >
            <Sparkles className="h-3 w-3" />{card.score}
          </span>
        ) : (
          <span className="text-[10px] font-bold uppercase px-2 py-1 rounded-md" style={{ background: C.borderSoft, color: C.muted }}>
            New
          </span>
        )}
      </div>

      {/* Score Label */}
      <p className="text-xs" style={{ color: C.body }}>
        <strong>{card.scoreLabel}</strong>
      </p>

      {/* 7-step Lifecycle Tracker */}
      <div className="flex gap-1 w-full pt-1">
        {Array.from({ length: 7 }).map((_, i) => {
          const done = i < card.lifecycle;
          const cur = i === card.lifecycle;
          return (
            <div
              key={i}
              className="h-1.5 flex-1 rounded-full"
              style={{
                background: done ? C.blue : cur ? C.gold : C.borderSoft,
                animation: cur ? 'pulse 2s infinite' : 'none',
              }}
            />
          );
        })}
      </div>

      {/* Footer */}
      <div
        className="flex justify-between items-center pt-3 border-t"
        style={{ borderColor: C.borderSoft }}
      >
        <div className="flex items-center gap-2">
          <img
            src={card.owner.avatar}
            alt={card.owner.name}
            className="w-6 h-6 rounded-full object-cover border"
            style={{ borderColor: C.border }}
          />
          <div>
            <p className="text-[10px] font-bold leading-none" style={{ color: C.ink }}>{card.owner.name}</p>
            <p className="text-[10px] leading-none mt-0.5" style={{ color: C.muted }}>{card.updatedAt}</p>
          </div>
        </div>
        <button
          className="text-xs font-bold flex items-center gap-1"
          style={{ color: C.blue }}
        >
          {card.nextAction} <ChevronRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
