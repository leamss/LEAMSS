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
  Copy, Check, CreditCard, Flame, FileSpreadsheet,
} from 'lucide-react';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetClose,
} from '@/components/ui/sheet';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const getResumeHref = (url) => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('blob:') || url.startsWith('data:')) return url;
  if (url.startsWith('/api')) return `${BACKEND_URL}${url}`;
  if (url.startsWith('/')) return `${BACKEND_URL}/api${url}`;
  return `${BACKEND_URL}/api/${url}`;
};


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
  { key: 'navratri',    label: '✨ Navratri Offer', icon: Flame, isSpecial: true },
  { key: 'leads',       label: 'Leads',             icon: Inbox },
  { key: 'assessments', label: 'Assessments',       icon: FileText },
  { key: 'pa',          label: 'Pre-Assessments',   icon: FileBadge },
  { key: 'proposals',   label: 'Proposals',         icon: Send },
  { key: 'cases',       label: 'Active Cases',      icon: Briefcase },
  { key: 'closed',      label: 'Closed',            icon: CheckCircle2 },
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
  const [navratriStatusFilter, setNavratriStatusFilter] = useState('all'); // 'all' | 'paid_resume_received' | 'paid_resume_pending' | 'unpaid'
  const [search, setSearch] = useState('');
  const [ownerFilter, setOwnerFilter] = useState('all'); // 'me' | 'all'
  const [reportPendingOnly, setReportPendingOnly] = useState(false);
  const [hasResumeOnly, setHasResumeOnly] = useState(false);
  const [sortMode, setSortMode] = useState('recent');
  const [selectedCard, setSelectedCard] = useState(null);
  const [cardDetail, setCardDetail] = useState(null);
  const [showCmdK, setShowCmdK] = useState(false);
  const [cmdQuery, setCmdQuery] = useState('');
  const [copiedId, setCopiedId] = useState(null);


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

  const handleSendToBulkAssessment = async (leadIds = [], paidOnly = true, reportPendingOnly = true) => {
    try {
      setBulkActionLoading(true);
      const res = await axios.post(`${API}/bulk-assessments/from-leads`, {
        lead_ids: leadIds.length ? leadIds : undefined,
        paid_only: paidOnly,
        report_pending_only: reportPendingOnly,
        batch_name: paidOnly
          ? `Paid Batch (${new Date().toLocaleDateString('en-GB')} ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})})`
          : `Website Registrations (${new Date().toLocaleDateString('en-GB')} ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})})`,
      }, { headers });
      setBulkActionLoading(false);
      setSelectedLeadIds([]);
      const targetBatchId = res.data?.batch_id;
      if (targetBatchId) {
        navigate(`/sales/bulk-assessment?batch_id=${targetBatchId}`);
      } else {
        navigate('/sales/bulk-assessment');
      }
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Failed to create bulk assessment batch');
    }
  };

  const selectSequence = (mode) => {
    const leadCards = cards.filter(c => c.type === 'lead');
    const isPaid = (c) => c.payment_status === 'success' || c.payment_status === 'paid' || (c.payment_amount && c.payment_amount > 0);
    const isUnassigned = (c) => !c.owner?.id || c.owner?.name === 'Unassigned' || !c.owner?.name;
    const isReportPending = (c) => !c.report_generated;
    const hasResume = (c) => Boolean(c.has_resume);

    if (mode === 'all') {
      setSelectedLeadIds(leadCards.map(c => c.id));
    } else if (mode === 'paid') {
      setSelectedLeadIds(leadCards.filter(isPaid).map(c => c.id));
    } else if (mode === 'paid_pending') {
      setSelectedLeadIds(leadCards.filter(c => isPaid(c) && isReportPending(c)).map(c => c.id));
    } else if (mode === 'with_resume') {
      setSelectedLeadIds(leadCards.filter(hasResume).map(c => c.id));
    } else if (mode === 'with_resume_5') {
      setSelectedLeadIds(leadCards.filter(hasResume).slice(0, 5).map(c => c.id));
    } else if (mode === 'with_resume_10') {
      setSelectedLeadIds(leadCards.filter(hasResume).slice(0, 10).map(c => c.id));
    } else if (mode === 'with_resume_20') {
      setSelectedLeadIds(leadCards.filter(hasResume).slice(0, 20).map(c => c.id));
    } else if (mode === 'without_resume') {
      setSelectedLeadIds(leadCards.filter(c => !hasResume(c)).map(c => c.id));
    } else if (mode === 'unassigned') {
      setSelectedLeadIds(leadCards.filter(isUnassigned).map(c => c.id));
    } else if (mode === 'unassigned_1') {
      setSelectedLeadIds(leadCards.filter(isUnassigned).slice(0, 1).map(c => c.id));
    } else if (mode === 'unassigned_5') {
      setSelectedLeadIds(leadCards.filter(isUnassigned).slice(0, 5).map(c => c.id));
    } else if (mode === 'unassigned_10') {
      setSelectedLeadIds(leadCards.filter(isUnassigned).slice(0, 10).map(c => c.id));
    } else if (mode === 'unassigned_20') {
      setSelectedLeadIds(leadCards.filter(isUnassigned).slice(0, 20).map(c => c.id));
    } else if (mode === 'unassigned_50') {
      setSelectedLeadIds(leadCards.filter(isUnassigned).slice(0, 50).map(c => c.id));
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


  const handleSendResumeRequest = async (leadIds) => {
    const ids = Array.isArray(leadIds) ? leadIds : [leadIds];
    if (!ids.length) return;
    try {
      setBulkActionLoading(true);
      const res = await axios.post(`${API}/cockpit/navratri/send-resume-request`, { lead_ids: ids }, { headers });
      setBulkActionLoading(false);
      fetchAll();
      alert(`Sent Resume Upload Link to ${res.data?.dispatched_count || ids.length} lead(s) via Email & WhatsApp!`);
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Failed to dispatch resume requests');
    }
  };

  const handleSendPaymentLink = async (leadIds) => {
    const ids = Array.isArray(leadIds) ? leadIds : [leadIds];
    if (!ids.length) return;
    try {
      setBulkActionLoading(true);
      const res = await axios.post(`${API}/cockpit/navratri/send-payment-link`, { lead_ids: ids }, { headers });
      setBulkActionLoading(false);
      fetchAll();
      alert(`Sent Navratri Offer Payment Link to ${res.data?.dispatched_count || ids.length} lead(s) via Email & WhatsApp!`);
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Failed to dispatch payment links');
    }
  };

  const handleMarkPaid = async (leadId) => {
    if (!leadId) return;
    try {
      setBulkActionLoading(true);
      const res = await axios.post(`${API}/cockpit/navratri/mark-paid`, { lead_id: leadId }, { headers });
      setBulkActionLoading(false);
      fetchAll();
      if (res.data?.has_resume) {
        alert('Payment confirmed! Lead is updated as Paid with resume and ready for Bulk Pre-Assessment.');
      } else {
        alert('Payment confirmed! Lead is updated as Paid and Resume Upload Link was auto-dispatched via Email & WhatsApp.');
      }
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Failed to mark lead as paid');
    }
  };

  const handleNavratriBulkPreAssessment = async (leadIds = []) => {
    try {
      setBulkActionLoading(true);
      const res = await axios.post(`${API}/cockpit/navratri/bulk-process-pre-assessment`, {
        lead_ids: leadIds.length ? leadIds : undefined,
        report_pending_only: true,
      }, { headers });
      setBulkActionLoading(false);
      setSelectedLeadIds([]);
      fetchAll();
      const targetBatchId = res.data?.batch_id || res.data?.batch_info?.batch_id;
      alert(`Created fresh batch with ${res.data?.leads_queued_count || 'all'} Paid Navratri leads pending reports!`);
      if (targetBatchId) {
        navigate(`/sales/bulk-assessment?batch_id=${targetBatchId}`);
      } else {
        navigate('/sales/bulk-assessment');
      }
    } catch (e) {
      setBulkActionLoading(false);
      alert(e.response?.data?.detail || 'Failed to process Navratri Bulk Pre-Assessment');
    }
  };

  const handleCopyLink = (url, id) => {
    if (!url) return;
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const [syncingMySQL, setSyncingMySQL] = useState(false);

  const handleSyncMySQL = async () => {
    try {
      setSyncingMySQL(true);
      const res = await axios.post(`${API}/leads/sync-mysql`, {}, { headers });
      try { await axios.post(`${API}/leads/reconcile-navratri`, {}, { headers }); } catch (_) {}
      setSyncingMySQL(false);
      fetchAll();
      alert(`Synced! Found ${res.data?.total_rows_found || 0} rows. (New: ${res.data?.new_leads_created || 0}, Updated: ${res.data?.existing_leads_updated || 0})`);
    } catch (e) {
      try {
        const rec = await axios.post(`${API}/leads/reconcile-navratri`, {}, { headers });
        fetchAll();
        setSyncingMySQL(false);
        alert(`Reconciled ${rec.data?.reconciled_leads_count || 0} website leads in Cockpit!`);
        return;
      } catch (_) {}
      setSyncingMySQL(false);
      alert(e.response?.data?.detail || 'Direct MySQL connection timed out. You can use the phpMyAdmin JSON/CSV import button or visit https://leamss.com/sync-crm-now');
    }
  };

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const content = event.target.result;
          let records = [];
          if (file.name.endsWith('.json')) {
            const parsed = JSON.parse(content);
            records = Array.isArray(parsed) ? parsed : (parsed.data || parsed.rows || [parsed]);
          } else if (file.name.endsWith('.csv')) {
            const lines = content.split('\n').map(l => l.trim()).filter(Boolean);
            if (lines.length > 1) {
              const csvHeaders = lines[0].split(',').map(h => h.replace(/["']/g, '').trim());
              for (let i = 1; i < lines.length; i++) {
                const vals = lines[i].split(',').map(v => v.replace(/["']/g, '').trim());
                const row = {};
                csvHeaders.forEach((h, idx) => { row[h] = vals[idx]; });
                records.push(row);
              }
            }
          }
          if (!records.length) {
            alert('No valid records found in file');
            return;
          }
          setBulkActionLoading(true);
          const res = await axios.post(`${API}/leads/bulk-import-navratri`, records, { headers });
          setBulkActionLoading(false);
          fetchAll();
          alert(`Successfully imported ${res.data?.total_processed || records.length} records! (New: ${res.data?.created}, Updated: ${res.data?.updated})`);
        } catch (err) {
          setBulkActionLoading(false);
          alert('Failed to parse file: ' + err.message);
        }
      };
      reader.readAsText(file);
    } catch (err) {
      alert('File read error: ' + err.message);
    }
    e.target.value = '';
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
      if (activeStage === 'navratri' && navratriStatusFilter !== 'all') {
        params.set('navratri_status', navratriStatusFilter);
      }
      if (search) params.set('search', search);
      if (ownerFilter !== 'all') params.set('owner', ownerFilter);
      if (reportPendingOnly) params.set('filter', 'paid_report_pending');
      if (hasResumeOnly) params.set('has_resume', 'true');
      params.set('sort', sortMode);
      params.set('limit', '500');
      const r = await axios.get(`${API}/cockpit/cards?${params}`, { headers });
      setCards(r.data.items || []);
    } catch (e) { console.error('cards', e); }
  }, [headers, activeStage, navratriStatusFilter, search, ownerFilter, reportPendingOnly, hasResumeOnly, sortMode]);


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
                  isSpecial={f.isSpecial}
                  onClick={() => {
                    setActiveStage(f.key);
                    if (f.key !== 'navratri') setNavratriStatusFilter('all');
                  }}
                  testid={`cockpit-funnel-${f.key}`}
                />
                {idx < FUNNEL_DEF.length - 1 && (
                  <ChevronRight className="h-4 w-4" style={{ color: C.muted }} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* NAVRATRI CAMPAIGN CONTROL & SEGREGATION BAR */}
        {activeStage === 'navratri' && (
          <div
            className="px-6 py-3 border-b flex flex-wrap items-center justify-between gap-3 animate-in fade-in slide-in-from-top-2"
            style={{ background: 'linear-gradient(to right, #FFF7ED, #FEF3C7)', borderColor: '#FED7AA' }}
          >
            <div className="flex items-center gap-2.5">
              <span className="w-8 h-8 rounded-lg flex items-center justify-center shadow-sm text-white" style={{ background: '#EA7C2E' }}>
                <Sparkles className="h-4 w-4" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-black tracking-wide uppercase" style={{ color: '#9A3412' }}>
                    Navratri Festive Campaign
                  </h4>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-orange-200 text-orange-900 border border-orange-300">
                    Live Sync
                  </span>
                </div>
                <p className="text-[11px]" style={{ color: '#B45309' }}>
                  Integrated Website Form Registrations · Automated Pipeline
                </p>
              </div>
            </div>

            {/* Segregation Filter Buttons */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => setNavratriStatusFilter('all')}
                className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-sm"
                style={{
                  background: navratriStatusFilter === 'all' ? '#134E4A' : '#FFFFFF',
                  color: navratriStatusFilter === 'all' ? '#FFFFFF' : '#334155',
                  border: '1px solid',
                  borderColor: navratriStatusFilter === 'all' ? '#134E4A' : '#CBD5E1',
                }}
              >
                All Navratri ({funnel?.navratri || cards.length})
              </button>

              <button
                type="button"
                onClick={() => setNavratriStatusFilter('paid_resume_received')}
                className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-sm flex items-center gap-1.5"
                style={{
                  background: navratriStatusFilter === 'paid_resume_received' ? '#047857' : '#ECFDF5',
                  color: navratriStatusFilter === 'paid_resume_received' ? '#FFFFFF' : '#065F46',
                  border: '1px solid #6EE7B7',
                }}
                title="Paid leads with resume attached (Ready for Bulk Pre-Assessment)"
              >
                <span>🟢 Paid · Resume Received</span>
              </button>

              <button
                type="button"
                onClick={() => setNavratriStatusFilter('paid_resume_pending')}
                className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-sm flex items-center gap-1.5"
                style={{
                  background: navratriStatusFilter === 'paid_resume_pending' ? '#D97706' : '#FFFBEB',
                  color: navratriStatusFilter === 'paid_resume_pending' ? '#FFFFFF' : '#92400E',
                  border: '1px solid #FCD34D',
                }}
                title="Paid leads awaiting resume upload (Click to send upload link)"
              >
                <span>🟡 Paid · Resume Pending</span>
              </button>

              <button
                type="button"
                onClick={() => setNavratriStatusFilter('unpaid')}
                className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-sm flex items-center gap-1.5"
                style={{
                  background: navratriStatusFilter === 'unpaid' ? '#DC2626' : '#FEF2F2',
                  color: navratriStatusFilter === 'unpaid' ? '#FFFFFF' : '#991B1B',
                  border: '1px solid #FCA5A5',
                }}
                title="Unpaid leads (Click to send payment link)"
              >
                <span>🔴 Unpaid / Payment Pending</span>
              </button>
            </div>

            {/* Top Quick Action Buttons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSyncMySQL}
                disabled={syncingMySQL}
                className="px-3 py-1.5 rounded-lg text-xs font-bold border transition-all shadow-sm flex items-center gap-1.5 hover:opacity-90 cursor-pointer"
                style={{ borderColor: '#F59E0B', background: '#FEF3C7', color: '#92400E' }}
                title="Sync all entries directly from cPanel MySQL hosldwuh_staging database"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${syncingMySQL ? 'animate-spin' : ''}`} />
                {syncingMySQL ? 'Syncing...' : 'Sync Database'}
              </button>

              <label
                className="px-3 py-1.5 rounded-lg text-xs font-bold border transition-all shadow-sm flex items-center gap-1.5 hover:opacity-90 cursor-pointer"
                style={{ borderColor: '#CBD5E1', background: '#FFFFFF', color: '#334155' }}
                title="Import phpMyAdmin exported JSON/CSV file with all historical registrations and payments"
              >
                <Download className="h-3.5 w-3.5 rotate-180" /> Import phpMyAdmin
                <input
                  type="file"
                  accept=".json,.csv"
                  className="hidden"
                  onChange={handleImportFile}
                />
              </label>

              <button
                onClick={() => handleNavratriBulkPreAssessment([])}
                className="px-3.5 py-1.5 rounded-lg text-xs font-extrabold text-white shadow-md flex items-center gap-1.5 transition-all hover:opacity-90 cursor-pointer"
                style={{ background: '#0F766E' }}
                title="Enqueue all Paid leads with Resumes into Bulk Pre-Assessment"
              >
                <Zap className="h-3.5 w-3.5" /> ⚡ Bulk Pre-Assessment (Ready)
              </button>

              <button
                onClick={() => navigate('/sales/bulk-assessment')}
                className="px-3 py-1.5 rounded-lg text-xs font-bold border border-teal-300 bg-white text-teal-800 shadow-sm flex items-center gap-1.5 transition-all hover:bg-teal-50 cursor-pointer"
                title="Open Bulk Pre-Assessment workspace and all generated batches"
              >
                <FileSpreadsheet className="h-3.5 w-3.5 text-teal-600" /> 📊 All Batches
              </button>
            </div>
          </div>
        )}

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
              icon={Zap}
              label={reportPendingOnly ? '⚡ Paid (Report Pending: ON)' : '⚡ Paid (Report Pending)'}
              onClick={() => setReportPendingOnly(!reportPendingOnly)}
              active={reportPendingOnly}
              testid="cockpit-filter-paid-pending"
            />
            <FilterButton
              icon={FileText}
              label={hasResumeOnly ? '📄 Has Resume (ON)' : '📄 Has Resume'}
              onClick={() => setHasResumeOnly(!hasResumeOnly)}
              active={hasResumeOnly}
              testid="cockpit-filter-has-resume"
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
              className="text-xs px-2.5 py-1.5 rounded-md border font-semibold outline-none cursor-pointer shadow-sm"
              style={{ borderColor: C.border, background: C.card, color: C.ink }}
            >
              <option value="">⚡ Select in Sequence...</option>
              <optgroup label="📄 Resume Filter">
                <option value="with_resume">Select With Resume (All)</option>
                <option value="with_resume_5">Select First 5 With Resume</option>
                <option value="with_resume_10">Select First 10 With Resume</option>
                <option value="with_resume_20">Select First 20 With Resume</option>
                <option value="without_resume">Select Without Resume</option>
              </optgroup>
              <optgroup label="📋 Select Unassigned">
                <option value="unassigned_1">Select 1 Unassigned</option>
                <option value="unassigned_5">Select 5 Unassigned</option>
                <option value="unassigned_10">Select 10 Unassigned</option>
                <option value="unassigned_20">Select 20 Unassigned</option>
                <option value="unassigned_50">Select 50 Unassigned</option>
                <option value="unassigned">Select All Unassigned</option>
              </optgroup>
              <optgroup label="🔢 Sequential (First N)">
                <option value="1">Select First 1 (Sequential)</option>
                <option value="5">Select First 5 (Sequential)</option>
                <option value="10">Select First 10 (Sequential)</option>
                <option value="20">Select First 20 (Sequential)</option>
                <option value="50">Select First 50 (Sequential)</option>
                <option value="all">Select All Leads</option>
              </optgroup>
              <optgroup label="💰 Paid & Reports">
                <option value="paid_pending">Select Paid (Report Pending Only)</option>
                <option value="paid">Select Paid Only (All)</option>
              </optgroup>
              <option value="clear">✕ Deselect All</option>
            </select>


            <div className="relative">
              <Search className="h-3 w-3 absolute left-2 top-1/2 -translate-y-1/2" style={{ color: C.muted }} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or unique ID..."
                className="pl-7 pr-3 py-1.5 rounded-md border text-xs outline-none"
                style={{ background: C.card, borderColor: C.border, color: C.ink, width: '190px' }}
                data-testid="cockpit-search-input"
              />
            </div>

            {/* Paid (Report Pending) Bulk Pre-Assessment */}
            <button
              onClick={() => handleSendToBulkAssessment([], true, true)}
              className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm hover:opacity-90"
              style={{ borderColor: C.teal, background: C.tealWash, color: C.tealDark }}
              title="Process Paid registrations whose Client Assessment Report is not yet generated"
            >
              <Zap className="h-3.5 w-3.5" /> 💰 Process Paid (Report Pending)
            </button>

            <button
              onClick={() => handleSendToBulkAssessment(selectedLeadIds, false, false)}
              className="px-3 py-1.5 rounded-md border text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm hover:opacity-90"
              style={{ borderColor: C.gold, background: C.goldWash, color: C.orangeDeep }}
              title="Add selected or all registrations to current Bulk Pre-Assessment queue"
            >
              <Sparkles className="h-3.5 w-3.5" /> Bulk Assessment (Queue)
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
                onSendResumeRequest={(leadId) => handleSendResumeRequest(leadId)}
                onSendPaymentLink={(leadId) => handleSendPaymentLink(leadId)}
                onMarkPaid={(leadId) => handleMarkPaid(leadId)}
                onCopyLink={(url, id) => handleCopyLink(url, id)}
                copiedId={copiedId}
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
              className="sticky bottom-4 left-0 right-0 mx-auto max-w-4xl bg-white border rounded-xl shadow-2xl p-3.5 z-40 flex items-center justify-between gap-3 animate-in fade-in slide-in-from-bottom-4"
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
                  className="text-xs px-2.5 py-1.5 rounded-lg border outline-none font-medium max-w-[170px] cursor-pointer"
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

                {/* Send Bulk Resume Upload Links (Email + WhatsApp) */}
                <button
                  onClick={() => handleSendResumeRequest(selectedLeadIds)}
                  disabled={bulkActionLoading}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 disabled:opacity-50 transition-all hover:opacity-90"
                  style={{ background: '#D97706' }}
                  title="Send Resume Upload Link via Email & WhatsApp to selected leads"
                >
                  <Mail className="h-3.5 w-3.5" /> Resume Link (Email+WA)
                </button>

                {/* Send Bulk Payment Links (Email + WhatsApp) */}
                <button
                  onClick={() => handleSendPaymentLink(selectedLeadIds)}
                  disabled={bulkActionLoading}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 disabled:opacity-50 transition-all hover:opacity-90"
                  style={{ background: '#DC2626' }}
                  title="Send Navratri Offer Payment Link via Email & WhatsApp to selected leads"
                >
                  <CreditCard className="h-3.5 w-3.5" /> Payment Link (Email+WA)
                </button>

                {/* Bulk Create PA */}
                <button
                  onClick={handleBulkConvertToPA}
                  disabled={bulkActionLoading}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 disabled:opacity-50"
                  style={{ background: C.tealDark }}
                >
                  <Zap className={`h-3.5 w-3.5 ${bulkActionLoading ? 'animate-spin' : ''}`} />
                  {bulkActionLoading ? 'Creating...' : 'Bulk PA'}
                </button>

                {/* Bulk Assessment Reports */}
                <button
                  onClick={() => handleSendToBulkAssessment(selectedLeadIds)}
                  disabled={bulkActionLoading}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 disabled:opacity-50"
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
        <SheetContent className="w-full sm:max-w-lg p-0 flex flex-col h-full overflow-hidden" style={{ background: C.card }} data-testid="cockpit-drill-drawer">
          {selectedCard && (
            <>
              <SheetHeader className="px-6 py-4 border-b shrink-0" style={{ borderColor: C.border }}>
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
              <div className="p-6 space-y-5 flex-1 overflow-y-auto min-h-0">
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
                    {(cardDetail.record.resume_url || cardDetail.record.resume_file_id || selectedCard.resume_url) ? (
                      <div className="p-3 rounded-lg border flex items-center justify-between" style={{ background: C.tealWash, borderColor: C.tealWash2 }}>
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="h-5 w-5 shrink-0" style={{ color: C.teal }} />
                          <div className="min-w-0">
                            <p className="text-xs font-bold truncate" style={{ color: C.tealDark }}>
                              {cardDetail.record.resume_filename || selectedCard.resume_filename || 'Uploaded Resume'}
                            </p>
                            <p className="text-[10px] truncate" style={{ color: C.body }}>Ready for evaluation</p>
                          </div>
                        </div>
                        <a
                          href={getResumeHref(cardDetail.record.resume_url || (cardDetail.record.resume_file_id ? `/cockpit/resume/${cardDetail.record.resume_file_id}` : '') || selectedCard.resume_url)}
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

                {/* Non-lead card details (Assessment or PA) */}
                {selectedCard.type !== 'lead' && (
                  <div className="rounded-xl border p-4 space-y-3 shadow-sm" style={{ background: C.bg, borderColor: C.border }}>
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <span className="text-xs font-bold px-2.5 py-1 rounded-full uppercase" style={{ background: C.tealWash2, color: C.tealDark }}>
                        {selectedCard.type === 'pa' ? 'Pre-Assessment' : 'Client Assessment'}
                      </span>
                      {selectedCard.score !== null && selectedCard.score !== undefined && (
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded border" style={{ color: C.orangeDeep, borderColor: C.gold, background: C.goldWash }}>
                          Score: {selectedCard.score} pts
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Client</p>
                        <p className="font-semibold text-sm" style={{ color: C.ink }}>{selectedCard.name || '—'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Stage</p>
                        <p className="font-semibold capitalize text-sm" style={{ color: C.ink }}>{selectedCard.stage || '—'}</p>
                      </div>
                      {cardDetail?.email && (
                        <div>
                          <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Email</p>
                          <p className="font-semibold truncate text-xs" style={{ color: C.ink }}>{cardDetail.email}</p>
                        </div>
                      )}
                      {cardDetail?.phone && (
                        <div>
                          <p className="text-[10px] uppercase font-bold" style={{ color: C.muted }}>Phone</p>
                          <p className="font-semibold text-xs" style={{ color: C.ink }}>{cardDetail.phone}</p>
                        </div>
                      )}
                    </div>

                    {/* Resume download box for assessment / PA */}
                    {(cardDetail?.has_resume || cardDetail?.resume_url || selectedCard.has_resume || selectedCard.resume_url) ? (
                      <div className="p-3 rounded-lg border flex items-center justify-between" style={{ background: C.tealWash, borderColor: C.tealWash2 }}>
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="h-5 w-5 shrink-0" style={{ color: C.teal }} />
                          <div className="min-w-0">
                            <p className="text-xs font-bold truncate" style={{ color: C.tealDark }}>
                              {cardDetail?.resume_filename || selectedCard.resume_filename || 'Uploaded Resume'}
                            </p>
                            <p className="text-[10px] truncate" style={{ color: C.body }}>Candidate Resume / CV</p>
                          </div>
                        </div>
                        <a
                          href={getResumeHref(cardDetail?.resume_url || selectedCard.resume_url)}
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
                        No resume uploaded with this record
                      </div>
                    )}
                  </div>
                )}


                {/* Dedicated Navratri Campaign Hub inside Drawer */}
                {(selectedCard.is_navratri || cardDetail?.card?.is_navratri || cardDetail?.record?.source?.includes('Navratri') || cardDetail?.record?.unique_id?.startsWith('NN')) && (
                  <div className="p-4 rounded-xl border shadow-sm space-y-3" style={{ background: '#FFFBEB', borderColor: '#FDE68A' }}>
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-extrabold uppercase tracking-wider flex items-center gap-1.5" style={{ color: '#92400E' }}>
                        <Flame className="h-4 w-4 text-amber-600" /> Navratri Offer Automation
                      </p>
                      <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full border shadow-sm"
                        style={{
                          background: (selectedCard.navratri_category === 'paid_resume_received' || (selectedCard.is_paid && selectedCard.has_resume)) ? '#ECFDF5' : (selectedCard.is_paid || cardDetail?.record?.payment_status === 'success') ? '#FFFBEB' : '#FEF2F2',
                          borderColor: (selectedCard.navratri_category === 'paid_resume_received' || (selectedCard.is_paid && selectedCard.has_resume)) ? '#A7F3D0' : (selectedCard.is_paid || cardDetail?.record?.payment_status === 'success') ? '#FDE68A' : '#FECACA',
                          color: (selectedCard.navratri_category === 'paid_resume_received' || (selectedCard.is_paid && selectedCard.has_resume)) ? '#065F46' : (selectedCard.is_paid || cardDetail?.record?.payment_status === 'success') ? '#92400E' : '#991B1B',
                        }}
                      >
                        {(selectedCard.navratri_category === 'paid_resume_received' || (selectedCard.is_paid && selectedCard.has_resume))
                          ? '🟢 Paid · Resume Received'
                          : (selectedCard.is_paid || cardDetail?.record?.payment_status === 'success')
                          ? '🟡 Paid · Resume Pending'
                          : '🔴 Unpaid / Payment Pending'}
                      </span>
                    </div>

                    {/* Details / Action according to status */}
                    {(!selectedCard.is_paid && cardDetail?.record?.payment_status !== 'success') ? (
                      <div className="space-y-2 pt-1">
                        <p className="text-xs text-slate-700">
                          Client has registered for the ₹499 Navratri Offer. Send the festive payment link via Email & WhatsApp.
                        </p>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleSendPaymentLink(selectedCard.id)}
                            disabled={bulkActionLoading}
                            className="flex-1 py-2 px-3 rounded-lg font-bold text-xs text-white shadow-sm flex items-center justify-center gap-1.5 transition-all hover:opacity-95"
                            style={{ background: '#DC2626' }}
                          >
                            <CreditCard className="h-3.5 w-3.5" /> Send Payment Link (Email + WA)
                          </button>
                          <button
                            onClick={() => handleMarkPaid(selectedCard.id)}
                            disabled={bulkActionLoading}
                            className="py-2 px-3 rounded-lg font-bold text-xs border transition-all shadow-sm hover:opacity-90 flex items-center gap-1"
                            style={{ borderColor: '#059669', background: '#ECFDF5', color: '#047857' }}
                          >
                            <Check className="h-3.5 w-3.5" /> Mark Paid
                          </button>
                        </div>
                        {selectedCard.payment_link && (
                          <div className="flex items-center justify-between text-[11px] p-2 rounded border bg-white" style={{ borderColor: '#E2E8F0' }}>
                            <span className="truncate text-slate-600 font-mono text-[10px]">{selectedCard.payment_link}</span>
                            <button
                              onClick={() => handleCopyLink(selectedCard.payment_link, `pay-drawer-${selectedCard.id}`)}
                              className="ml-2 px-2 py-1 rounded border text-[10px] font-bold text-slate-700 hover:bg-slate-50 flex items-center gap-1 shrink-0"
                            >
                              {copiedId === `pay-drawer-${selectedCard.id}` ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3 text-slate-500" />}
                              {copiedId === `pay-drawer-${selectedCard.id}` ? 'Copied' : 'Copy'}
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (!selectedCard.has_resume && !cardDetail?.record?.resume_url && !cardDetail?.record?.resume_file_id) ? (
                      <div className="space-y-2 pt-1">
                        <p className="text-xs text-slate-700">
                          Payment received (₹499). Client has not yet uploaded their resume. Dispatch the secure 1-click upload link via Email and WhatsApp.
                        </p>
                        <button
                          onClick={() => handleSendResumeRequest(selectedCard.id)}
                          disabled={bulkActionLoading}
                          className="w-full py-2 px-3 rounded-lg font-bold text-xs text-white shadow-sm flex items-center justify-center gap-1.5 transition-all hover:opacity-95"
                          style={{ background: '#D97706' }}
                        >
                          <Mail className="h-3.5 w-3.5" /> Request Resume Upload (Email + WhatsApp)
                        </button>
                        {selectedCard.resume_upload_url && (
                          <div className="flex items-center justify-between text-[11px] p-2 rounded border bg-white" style={{ borderColor: '#E2E8F0' }}>
                            <span className="truncate text-slate-600 font-mono text-[10px]">{selectedCard.resume_upload_url}</span>
                            <button
                              onClick={() => handleCopyLink(selectedCard.resume_upload_url, `resume-drawer-${selectedCard.id}`)}
                              className="ml-2 px-2 py-1 rounded border text-[10px] font-bold text-slate-700 hover:bg-slate-50 flex items-center gap-1 shrink-0"
                            >
                              {copiedId === `resume-drawer-${selectedCard.id}` ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3 text-slate-500" />}
                              {copiedId === `resume-drawer-${selectedCard.id}` ? 'Copied' : 'Copy'}
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (selectedCard.report_generated || cardDetail?.record?.report_generated) ? (
                      <div className="space-y-2 pt-1">
                        <p className="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                          <Check className="h-4 w-4 text-emerald-600 shrink-0" />
                          Pre-Assessment Report Generated Successfully!
                        </p>
                        <button
                          onClick={() => {
                            const bId = selectedCard.bulk_batch_id || cardDetail?.record?.bulk_batch_id;
                            if (bId) {
                              navigate(`/sales/bulk-assessment?batch_id=${bId}`);
                            } else {
                              navigate('/sales/bulk-assessment');
                            }
                          }}
                          className="w-full py-2 px-3 rounded-lg font-black text-xs text-white shadow-md flex items-center justify-center gap-1.5 transition-all hover:opacity-95 cursor-pointer"
                          style={{ background: '#0F766E' }}
                        >
                          <FileSpreadsheet className="h-4 w-4 text-white shrink-0" />
                          View in Bulk Batch {(selectedCard.bulk_batch_id || cardDetail?.record?.bulk_batch_id) ? `(${selectedCard.bulk_batch_id || cardDetail?.record?.bulk_batch_id})` : ''}
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2 pt-1">
                        <p className="text-xs font-semibold text-emerald-800">
                          ✓ Payment confirmed and Resume attached. This lead is ready for Bulk Pre-Assessment calculation and Report Generation!
                        </p>
                        <button
                          onClick={() => handleNavratriBulkPreAssessment([selectedCard.id])}
                          disabled={bulkActionLoading}
                          className="w-full py-2 px-3 rounded-lg font-extrabold text-xs text-white shadow-md flex items-center justify-center gap-1.5 transition-all hover:opacity-95 cursor-pointer"
                          style={{ background: '#0F766E' }}
                        >
                          <Zap className="h-3.5 w-3.5" /> ⚡ Process Bulk Pre-Assessment
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Generated Batch Banner if Report is Generated */}
                {selectedCard.report_generated && (selectedCard.bulk_batch_id || cardDetail?.record?.bulk_batch_id) && (
                  <div className="p-3.5 rounded-xl border border-teal-200 bg-teal-50/70 shadow-xs flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-[10px] font-extrabold uppercase tracking-wider text-teal-800 flex items-center gap-1">
                        <Check className="h-3.5 w-3.5 text-teal-600" /> Report Generated in Batch
                      </p>
                      <p className="text-xs font-mono font-bold text-slate-800 truncate mt-0.5">
                        {selectedCard.bulk_batch_id || cardDetail?.record?.bulk_batch_id}
                      </p>
                    </div>
                    <button
                      onClick={() => navigate(`/sales/bulk-assessment?batch_id=${selectedCard.bulk_batch_id || cardDetail?.record?.bulk_batch_id}`)}
                      className="px-3 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 transition-all hover:opacity-90 shrink-0 cursor-pointer"
                      style={{ background: '#0F766E' }}
                    >
                      <FileSpreadsheet className="h-3.5 w-3.5" /> View in Batch
                    </button>
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

function FunnelChip({ label, count, icon: Icon, active, isSpecial, onClick, testid }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-lg border text-sm font-semibold flex items-center gap-2 cursor-pointer whitespace-nowrap transition-all"
      style={{
        background:  active ? (isSpecial ? '#FFEDD5' : C.tealWash) : (isSpecial ? '#FFFBEB' : C.card),
        borderColor: active ? (isSpecial ? '#EA7C2E' : C.teal) : (isSpecial ? '#FCD34D' : C.border),
        color:       active ? (isSpecial ? '#9A3412' : C.tealDeep) : (isSpecial ? '#B45309' : C.body),
        boxShadow:   active ? (isSpecial ? '0 0 0 3px rgba(234, 124, 46, 0.2)' : `0 0 0 3px ${C.tealWash2}`) : 'none',
        fontWeight:  isSpecial ? 700 : 600,
      }}
      data-testid={testid}
    >
      <Icon className={`h-4 w-4 ${isSpecial ? 'text-amber-600' : ''}`} />
      <span>{label}</span>
      <span
        className="px-2 py-0.5 rounded-full text-xs font-bold"
        style={{
          background: active ? (isSpecial ? '#FDBA74' : C.tealWash2) : (isSpecial ? '#FEF3C7' : C.borderSoft),
          color:      active ? (isSpecial ? '#7C2D12' : C.tealDeep) : (isSpecial ? '#92400E' : C.body),
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

function PipelineCard({
  card,
  onClick,
  isSelected,
  onToggleSelect,
  onConvertToPA,
  onSendResumeRequest,
  onSendPaymentLink,
  onMarkPaid,
  onCopyLink,
  copiedId,
}) {
  const ringColor = URGENCY_RING[card.urgency] || C.teal;
  const flags = (card.countries || []).map(c => COUNTRY_FLAG[c] || c).join(' ');
  const isNavratri = card.is_navratri;
  const navCategory = card.navratri_category;

  return (
    <div
      onClick={onClick}
      className="p-4 rounded-xl border shadow-sm hover:shadow-md transition-all cursor-pointer flex flex-col gap-3 group relative"
      style={{
        borderColor: isSelected ? C.teal : isNavratri ? '#FDE68A' : C.border,
        background:  isSelected ? C.tealWash : '#FFFFFF',
        boxShadow:   isSelected ? '0 0 0 2px rgba(15, 118, 110, 0.25)' : undefined,
      }}
      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.borderColor = C.teal; }}
      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.borderColor = isNavratri ? '#FDE68A' : C.border; }}
      data-testid={`cockpit-card-${card.type}-${card.id}`}
    >
      {/* Optional Navratri Campaign Top Strip */}
      {isNavratri && (
        <div className="flex items-center justify-between px-2.5 py-1 rounded-lg border text-[11px] font-bold"
             style={{
               background: navCategory === 'paid_resume_received' ? '#ECFDF5' : navCategory === 'paid_resume_pending' ? '#FFFBEB' : '#FEF2F2',
               borderColor: navCategory === 'paid_resume_received' ? '#A7F3D0' : navCategory === 'paid_resume_pending' ? '#FDE68A' : '#FECACA',
               color: navCategory === 'paid_resume_received' ? '#065F46' : navCategory === 'paid_resume_pending' ? '#92400E' : '#991B1B'
             }}>
          <span className="flex items-center gap-1">
            <Flame className="h-3.5 w-3.5 text-amber-600" />
            Navratri Offer
          </span>
          <span>
            {navCategory === 'paid_resume_received' && '🟢 Paid · Resume Ready'}
            {navCategory === 'paid_resume_pending' && '🟡 Paid · Resume Pending'}
            {navCategory === 'unpaid' && '🔴 Unpaid / Pending'}
          </span>
        </div>
      )}

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
          <div className="flex flex-col items-end gap-1 shrink-0">
            <span
              className="flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-md border whitespace-nowrap"
              style={{ color: C.orangeDeep, background: C.goldWash, borderColor: C.goldLight }}
            >
              <Sparkles className="h-3 w-3" />{card.score}
            </span>
            {card.report_generated && card.bulk_batch_id && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/sales/bulk-assessment?batch_id=${card.bulk_batch_id}`);
                }}
                className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-100 hover:bg-teal-50 text-slate-700 hover:text-teal-800 border border-slate-200 hover:border-teal-300 flex items-center gap-1 cursor-pointer transition-all shadow-xs"
                title={`Click to view this client in Batch: ${card.bulk_batch_id}`}
              >
                <FileSpreadsheet className="h-2.5 w-2.5 text-teal-600" />
                <span>Batch: {card.bulk_batch_id.replace('BATCH-', '')}</span>
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-end gap-1 shrink-0">
            {card.report_generated ? (
              <div className="flex flex-col items-end gap-1">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md whitespace-nowrap bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 shadow-sm">
                  ✓ Report Generated
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (card.bulk_batch_id) {
                      navigate(`/sales/bulk-assessment?batch_id=${card.bulk_batch_id}`);
                    } else {
                      navigate('/sales/bulk-assessment');
                    }
                  }}
                  className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-300 flex items-center gap-1 cursor-pointer transition-all shadow-xs"
                  title={card.bulk_batch_id ? `Click to view this client in Batch: ${card.bulk_batch_id}` : 'Click to view in Bulk Assessment Batch'}
                >
                  <FileSpreadsheet className="h-2.5 w-2.5 text-teal-600" />
                  <span>{card.bulk_batch_id ? `Batch: ${card.bulk_batch_id.replace('BATCH-', '')}` : 'View in Batch'}</span>
                </button>
              </div>
            ) : (card.payment_status === 'success' || (card.payment_amount && card.payment_amount > 0)) ? (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md whitespace-nowrap bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1 shadow-sm">
                ⚡ Paid · Report Pending
              </span>
            ) : (
              <span
                className="text-[10px] font-bold uppercase px-2 py-1 rounded-md whitespace-nowrap"
                style={{
                  background: C.borderSoft,
                  color: C.muted
                }}
              >
                {card.type === 'lead' ? 'New' : '—'}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Score / Service label */}
      <p className="text-xs truncate" style={{ color: C.body }}>
        <strong>{card.score_label}</strong>
      </p>

      {/* Resume badge & quick view/download button */}
      {card.has_resume && (
        <div
          className="flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-xs"
          style={{ background: C.tealWash, borderColor: C.tealWash2 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center gap-1.5 min-w-0">
            <FileText className="h-3.5 w-3.5 shrink-0" style={{ color: C.teal }} />
            <span className="font-semibold truncate text-[11px]" style={{ color: C.tealDark }} title={card.resume_filename || 'Resume'}>
              {card.resume_filename || 'Resume.pdf'}
            </span>
          </div>
          {card.resume_url && (
            <a
              href={getResumeHref(card.resume_url)}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2 py-0.5 rounded text-[10px] font-bold text-white shrink-0 flex items-center gap-1 transition-all hover:opacity-90 shadow-sm"
              style={{ background: C.teal }}
              title="View / Download Resume"
            >
              <Download className="h-2.5 w-2.5" /> View
            </a>
          )}
        </div>
      )}

      {/* Dedicated 1-Click Action Buttons on Card */}
      <div className="pt-1 flex flex-col gap-1.5" onClick={(e) => e.stopPropagation()}>
        {(card.report_generated || card.bulk_batch_id || card.assessment_report_id) ? (
          <button
            type="button"
            onClick={() => {
              if (card.bulk_batch_id) {
                navigate(`/sales/bulk-assessment?batch_id=${encodeURIComponent(card.bulk_batch_id)}&search=${encodeURIComponent(card.name || '')}`);
              } else {
                navigate(`/sales/bulk-assessment?search=${encodeURIComponent(card.name || card.email || '')}`);
              }
            }}
            className="w-full py-2 px-2.5 rounded-lg text-xs font-black border-2 border-teal-500 bg-teal-50 hover:bg-teal-100 text-teal-900 flex items-center justify-center gap-1.5 transition-all shadow-sm hover:shadow-md cursor-pointer active:scale-98"
            title={`Open this client's generated report in Batch: ${card.bulk_batch_id || 'Bulk Pre-Assessment'}`}
          >
            <FileSpreadsheet className="h-4 w-4 text-teal-600 shrink-0" />
            <span className="truncate font-extrabold">View in Bulk Batch {card.bulk_batch_id ? `(${card.bulk_batch_id})` : ''}</span>
          </button>
        ) : isNavratri && card.type === 'lead' ? (
          <>
            {navCategory === 'paid_resume_pending' && (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => onSendResumeRequest && onSendResumeRequest(card.id)}
                  className="flex-1 py-1.5 px-2 rounded-md text-[11px] font-bold text-white shadow-sm flex items-center justify-center gap-1 transition-all hover:opacity-90 cursor-pointer"
                  style={{ background: '#D97706' }}
                  title="Send Resume Upload link via Email and WhatsApp"
                >
                  <Mail className="h-3 w-3" /> Request Resume (Email+WA)
                </button>
                {card.resume_upload_url && (
                  <button
                    type="button"
                    onClick={() => onCopyLink && onCopyLink(card.resume_upload_url, `resume-${card.id}`)}
                    className="px-2 py-1.5 rounded-md border text-[10px] font-semibold flex items-center gap-1 transition-colors hover:bg-slate-50 cursor-pointer"
                    style={{ borderColor: C.border, color: C.body, background: '#FFF' }}
                    title="Copy direct Resume Upload Link"
                  >
                    {copiedId === `resume-${card.id}` ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3 text-slate-500" />}
                    {copiedId === `resume-${card.id}` ? 'Copied' : 'Link'}
                  </button>
                )}
              </div>
            )}

            {navCategory === 'unpaid' && (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => onSendPaymentLink && onSendPaymentLink(card.id)}
                  className="flex-1 py-1.5 px-2 rounded-md text-[11px] font-bold text-white shadow-sm flex items-center justify-center gap-1 transition-all hover:opacity-90 cursor-pointer"
                  style={{ background: '#DC2626' }}
                  title="Send Navratri Offer payment link via Email and WhatsApp"
                >
                  <CreditCard className="h-3 w-3" /> Send Payment Link
                </button>
                <button
                  type="button"
                  onClick={() => onMarkPaid && onMarkPaid(card.id)}
                  className="px-2 py-1.5 rounded-md border text-[10px] font-bold transition-all shadow-sm hover:opacity-90 flex items-center gap-1 cursor-pointer"
                  style={{ borderColor: '#059669', background: '#ECFDF5', color: '#047857' }}
                  title="Manually verify & mark lead as Paid"
                >
                  <Check className="h-3 w-3" /> Mark Paid
                </button>
              </div>
            )}

            {navCategory === 'paid_resume_received' && (
              <div className="px-2.5 py-1 rounded-md text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 flex items-center justify-between">
                <span>✓ Ready for Bulk Pre-Assessment</span>
                <Zap className="h-3 w-3 text-emerald-600" />
              </div>
            )}
          </>
        ) : null}
      </div>

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
