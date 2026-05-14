import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { 
  Plus, Send, CheckCircle, Clock, XCircle, FileText, Upload, 
  CreditCard, Eye, ChevronDown, ChevronUp, Search,
  Edit3,
  AlertTriangle, RefreshCw, Filter, Bell
} from 'lucide-react';
import FunnelProgress from '@/components/FunnelProgress';
import PaymentHistoryTimeline from '@/components/PaymentHistoryTimeline';
import SmartDocChecklist from '@/components/SmartDocChecklist';
import RiskScoreBadge from '@/components/RiskScoreBadge';
import PaFinancialSummary from '@/components/pa/PaFinancialSummary';
import PaCreateForm from '@/components/pa/PaCreateForm';
import PaProposalForm from '@/components/pa/PaProposalForm';
import PaDocumentsList from '@/components/pa/PaDocumentsList';
import PaFinalSubmitForm from '@/components/pa/PaFinalSubmitForm';
import PaForwardForm from '@/components/pa/PaForwardForm';
import PaStageProgress from '@/components/pa/PaStageProgress';
import PaActionBar from '@/components/pa/PaActionBar';
import PaEditDetailsModal from '@/components/pa/PaEditDetailsModal';
import AgreementGenerator from '@/components/AgreementGenerator';
import AgreementViewerModal from '@/components/AgreementViewerModal';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STAGE_CONFIG = {
  new: { label: 'New Lead', color: 'bg-slate-500', textColor: 'text-slate-700', bgColor: 'bg-slate-50', icon: Plus },
  payment_pending: { label: 'Payment Pending', color: 'bg-amber-500', textColor: 'text-amber-700', bgColor: 'bg-amber-50', icon: Clock },
  payment_received: { label: 'Payment Received', color: 'bg-blue-500', textColor: 'text-blue-700', bgColor: 'bg-blue-50', icon: CreditCard },
  partner_review: { label: 'Awaiting Your Review', color: 'bg-pink-500', textColor: 'text-pink-700', bgColor: 'bg-pink-50', icon: Eye },
  documents_submitted: { label: 'Sent to Admin', color: 'bg-indigo-500', textColor: 'text-indigo-700', bgColor: 'bg-indigo-50', icon: FileText },
  under_review: { label: 'Under Review', color: 'bg-purple-500', textColor: 'text-purple-700', bgColor: 'bg-purple-50', icon: Eye },
  approved: { label: 'Approved', color: 'bg-emerald-500', textColor: 'text-emerald-700', bgColor: 'bg-emerald-50', icon: CheckCircle },
  rejected: { label: 'Rejected', color: 'bg-red-500', textColor: 'text-red-700', bgColor: 'bg-red-50', icon: XCircle },
  proposal_sent: { label: 'Waiting for Client Payment', color: 'bg-amber-500', textColor: 'text-amber-700', bgColor: 'bg-amber-50', icon: Clock },
  proposal_paid: { label: 'Action: Upload Receipt + Agreement', color: 'bg-[#f7620b]', textColor: 'text-orange-700', bgColor: 'bg-orange-50', icon: Upload },
  awaiting_final_approval: { label: 'Awaiting Admin Final Approval', color: 'bg-indigo-600', textColor: 'text-indigo-700', bgColor: 'bg-indigo-50', icon: Clock },
  case_created: { label: 'Case Created', color: 'bg-green-600', textColor: 'text-green-800', bgColor: 'bg-green-50', icon: CheckCircle },
  refund_initiated: { label: 'Refund Initiated', color: 'bg-orange-500', textColor: 'text-orange-700', bgColor: 'bg-orange-50', icon: RefreshCw },
  refunded: { label: 'Refunded', color: 'bg-gray-500', textColor: 'text-gray-700', bgColor: 'bg-gray-50', icon: RefreshCw },
};

const PreAssessmentPipeline = ({ initialFilter = null }) => {
  const [assessments, setAssessments] = useState([]);
  const [stats, setStats] = useState({});
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [editingPa, setEditingPa] = useState(null);
  const [filterStage, setFilterStage] = useState('all');
  const [search, setSearch] = useState('');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Apply initial filter when provided
  useEffect(() => {
    if (initialFilter) setFilterStage(initialFilter);
  }, [initialFilter]);

  // Create form state
  const [form, setForm] = useState({
    client_name: '', client_email: '', client_mobile: '', country: '',
    service_type: '', product_id: '', notes: '', client_age: 0,
    education: '', work_experience: '',
    lead_source: null, lead_source_detail: '',
    // Phase 4B Part 2 — Express Sale fields
    sale_type: 'standard',
    express_sale_reason: null,
    express_sale_justification: '',
  });
  // Phase 4B Part 2 — Express usage (loaded from /api/express/my-usage)
  const [expressUsage, setExpressUsage] = useState(null);
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${API}/express/my-usage`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setExpressUsage(d); })
      .catch(() => {});
  }, []);
  const [proposalForm, setProposalForm] = useState({ fee_amount: '', notes: '', promo_code: '', promo_applied: null, additional_discount: '', upsell_ids: [], ai_text: '' });
  const [showProposal, setShowProposal] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [upsellCatalog, setUpsellCatalog] = useState([]);
  const [paDocs, setPaDocs] = useState({}); // { pa_id: [docs] }
  const [paActivity, setPaActivity] = useState({}); // { pa_id: [activity] }
  const [paBundle, setPaBundle] = useState({}); // { pa_id: { payment_history, checklist, risk } }
  const [forwardingId, setForwardingId] = useState(null);
  const [forwardRemarks, setForwardRemarks] = useState('');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [validatingPromo, setValidatingPromo] = useState(false);
  const [finalSubmittingId, setFinalSubmittingId] = useState(null);
  const [finalNotes, setFinalNotes] = useState('');
  // Explicit upload staging: { [paId]: { file, docType } }
  const [pendingUpload, setPendingUpload] = useState({});
  const [sendingInvoice, setSendingInvoice] = useState(null);
  const [generatingAgreementFor, setGeneratingAgreementFor] = useState(null);
  const [viewingAgreementFor, setViewingAgreementFor] = useState(null);

  const downloadPdf = async (paId, kind) => {
    try {
      const url = `${API}/proposal-docs/${paId}/${kind}.pdf`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
      if (!r.ok) throw new Error('Fetch failed');
      const blob = await r.blob();
      const objUrl = URL.createObjectURL(blob);
      window.open(objUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(objUrl), 60000);
    } catch (e) { toast.error(`${kind} PDF failed`); }
  };

  const sendInvoiceNow = async (paId) => {
    setSendingInvoice(paId);
    try {
      const r = await axios.post(`${API}/proposal-docs/${paId}/send-invoice`, { channel: 'email' }, getAuthHeader());
      toast.success(`Invoice sent · Ref ${r.data.reference_id}`);
    } catch (e) { toast.error(e.response?.data?.detail || 'Send failed'); }
    setSendingInvoice(null);
  };

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadData = useCallback(async () => {
    try {
      const [aRes, sRes, pRes] = await Promise.all([
        axios.get(`${API}/pre-assessment/my-assessments`, getAuthHeader()),
        axios.get(`${API}/pre-assessment/stats/overview`, getAuthHeader()),
        axios.get(`${API}/products`, getAuthHeader()),
      ]);
      setAssessments(aRes.data || []);
      setStats(sRes.data || {});
      setProducts(pRes.data || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    if (!form.client_name || !form.client_email || !form.country || !form.service_type) {
      toast.error('Please fill required fields'); return;
    }
    if (form.sale_type === 'express') {
      if (!form.express_sale_reason) { toast.error('Please select a reason for Express Sale'); return; }
      if ((form.express_sale_justification || '').length < 30) { toast.error('Express justification must be at least 30 characters'); return; }
    }
    try {
      const res = await axios.post(`${API}/pre-assessment/create`, {
        ...form, client_age: parseInt(form.client_age) || 0
      }, getAuthHeader());
      toast.success(res.data.message || 'Pre-assessment created!');
      setShowCreate(false);
      setForm({ client_name: '', client_email: '', client_mobile: '', country: '', service_type: '', product_id: '', notes: '', client_age: 0, education: '', work_experience: '', lead_source: null, lead_source_detail: '', sale_type: 'standard', express_sale_reason: null, express_sale_justification: '' });
      // Refresh express usage after creating an express PA
      if (form.sale_type === 'express') {
        try {
          const u = await axios.get(`${API}/express/my-usage`, getAuthHeader());
          setExpressUsage(u.data);
        } catch (_) {}
      }
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed to create'); }
  };

  const handleSendPayment = async (paId) => {
    try {
      // Generate public share-token link (new client-facing flow)
      const res = await axios.post(`${API}/pre-assess-portal/generate-public-link`, { pa_id: paId }, getAuthHeader());
      const publicUrl = res.data.public_url?.startsWith('http') ? res.data.public_url : `${window.location.origin}${res.data.public_url}`;
      try { await navigator.clipboard.writeText(publicUrl); } catch (_) { /* ignore */ }
      toast.success('Public payment link generated & copied to clipboard');
      window.open(publicUrl, '_blank');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to generate link');
    }
  };

  const handleCopyPublicLink = async (paId) => {
    try {
      const res = await axios.post(`${API}/pre-assess-portal/generate-public-link`, { pa_id: paId }, getAuthHeader());
      const publicUrl = res.data.public_url?.startsWith('http') ? res.data.public_url : `${window.location.origin}${res.data.public_url}`;
      await navigator.clipboard.writeText(publicUrl);
      toast.success('Public payment link copied — share via WhatsApp/Email');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
  };

  const handlePreviewAsClient = async (paId) => {
    try {
      const pa = assessments.find(a => a.id === paId);
      if (!pa) return;
      // If client hasn't paid yet → open public payment page
      if (['new', 'payment_pending'].includes(pa.stage) || pa.fee_payment_status !== 'paid') {
        const res = await axios.post(`${API}/pre-assess-portal/generate-public-link`, { pa_id: paId }, getAuthHeader());
        const url = res.data.public_url?.startsWith('http') ? res.data.public_url : `${window.location.origin}${res.data.public_url}`;
        window.open(url, '_blank');
        toast.success('Opening public payment page (what client sees before paying)');
        return;
      }
      // Else generate a fresh magic link for the client & open the MiniPortal
      const res = await axios.post(`${API}/pre-assess-portal/partner/preview-magic/${paId}`, {}, getAuthHeader());
      if (res.data.portal_url) {
        const url = res.data.portal_url.startsWith('http') ? res.data.portal_url : `${window.location.origin}${res.data.portal_url}`;
        window.open(url, '_blank');
        toast.success('Opening client portal preview in new tab');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Preview failed');
    }
  };

  const handleConfirmPayment = async (paId) => {
    try {
      await axios.post(`${API}/pre-assessment/${paId}/confirm-payment`, {}, getAuthHeader());
      toast.success('Payment confirmed!');
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const handleSubmitDocs = async (paId) => {
    try {
      const formData = new FormData();
      formData.append('remarks', 'Documents ready for review');
      await axios.post(`${API}/pre-assessment/${paId}/submit-documents`, formData, getAuthHeader());
      toast.success('Submitted to admin for review!');
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
  };

  const handleUploadDoc = async (paId, file, docType) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('document_type', docType);
      await axios.post(`${API}/pre-assessment/${paId}/upload-document`, fd, getAuthHeader());
      toast.success('Document uploaded!');
      loadData();
    } catch (e) { toast.error('Upload failed'); }
    setUploading(false);
  };

  // Stage a file for upload (explicit two-step flow)
  const stageFile = (paId, file, docType) => {
    if (!file) return;
    setPendingUpload(prev => ({ ...prev, [paId]: { file, docType } }));
  };

  const clearPendingFile = (paId) => {
    setPendingUpload(prev => {
      const n = { ...prev };
      delete n[paId];
      return n;
    });
  };

  const confirmUpload = async (paId) => {
    const entry = pendingUpload[paId];
    if (!entry || !entry.file) { toast.error('Select a file first'); return; }
    await handleUploadDoc(paId, entry.file, entry.docType);
    clearPendingFile(paId);
    await loadDocsAndActivity(paId);
  };

  const handleSendProposal = async (paId) => {
    if (!proposalForm.fee_amount || parseFloat(proposalForm.fee_amount) <= 0) {
      toast.error('Enter valid fee amount'); return;
    }
    // Optimistic UI: immediately move stage to proposal_sent + close form
    const snapshot = [...assessments];
    setAssessments(p => p.map(x => x.id === paId ? { ...x, stage: 'proposal_sent', proposal_status: 'sent', proposal_fee: parseFloat(proposalForm.fee_amount) } : x));
    setShowProposal(null);
    const formCopy = { ...proposalForm };
    setProposalForm({ fee_amount: '', notes: '', promo_code: '', promo_applied: null, additional_discount: '', upsell_ids: [], ai_text: '' });
    try {
      const res = await axios.post(`${API}/pre-assessment/${paId}/send-proposal`, {
        fee_amount: parseFloat(formCopy.fee_amount),
        payment_method: 'online',
        notes: formCopy.notes,
        currency: 'INR',
        promo_code: formCopy.promo_code || null,
        additional_discount: parseFloat(formCopy.additional_discount) || 0,
        upsell_bundle_ids: formCopy.upsell_ids || [],
        ai_proposal_text: formCopy.ai_text || null,
      }, getAuthHeader());
      toast.success(`${res.data.message} — Final ₹${res.data.breakdown?.final_amount?.toLocaleString('en-IN')}`);
      loadData();
    } catch (e) {
      // Rollback on failure
      setAssessments(snapshot);
      const status = e.response?.status;
      const detail = e.response?.data?.detail || 'Failed to send proposal';
      if (status === 401) {
        toast.error('Session expired. Please log in again.');
      } else {
        toast.error(`${detail}${status ? ` (HTTP ${status})` : ''} — reverted`);
      }
      console.error('Send proposal failed:', status, detail);
    }
  };

  const openProposalForm = async (pa) => {
    setShowProposal(pa.id);
    // Phase 4C — Lock proposal fee to product's service_price if PA is linked to a product
    let lockedPrice = '';
    let productName = '';
    if (pa.product_id) {
      try {
        const pr = await axios.get(`${API}/products/${pa.product_id}`, getAuthHeader());
        const sp = pr.data?.service_price || pr.data?.base_fee || 0;
        if (sp > 0) {
          lockedPrice = String(sp);
          productName = pr.data?.name || '';
        }
      } catch (e) { /* fallback to free input */ }
    }
    setProposalForm({
      fee_amount: lockedPrice,
      product_locked_price: lockedPrice,
      product_name: productName,
      price_overridden: false,
      notes: '', promo_code: '', promo_applied: null, additional_discount: '', upsell_ids: [], ai_text: '',
    });
    if (upsellCatalog.length === 0) {
      try {
        const r = await axios.get(`${API}/upsell-bundles`, getAuthHeader());
        setUpsellCatalog(r.data || []);
      } catch (e) { /* ignore */ }
    }
  };

  const openForwardForm = (paId) => {
    setForwardingId(paId);
    setForwardRemarks('');
    loadDocsAndActivity(paId);
  };

  const openFinalForm = (paId) => {
    setFinalSubmittingId(paId);
    setFinalNotes('');
    loadDocsAndActivity(paId);
  };

  const handleSubmitFinal = async (paId) => {
    // Optimistic: stage → awaiting_final_approval
    const snapshot = [...assessments];
    setAssessments(p => p.map(x => x.id === paId ? { ...x, stage: 'awaiting_final_approval' } : x));
    setFinalSubmittingId(null);
    const notes = finalNotes;
    setFinalNotes('');
    try {
      await axios.post(`${API}/pre-assess-portal/partner/submit-final/${paId}`,
        { notes }, getAuthHeader());
      toast.success('Submitted to Admin for Final Approval');
      loadData();
    } catch (e) {
      setAssessments(snapshot);
      toast.error((e.response?.data?.detail || 'Failed') + ' — reverted');
    }
  };

  const handleForwardToAdmin = async (paId) => {
    // Optimistic: stage → under_review
    const snapshot = [...assessments];
    setAssessments(p => p.map(x => x.id === paId ? { ...x, stage: 'under_review' } : x));
    setForwardingId(null);
    const remarks = forwardRemarks;
    setForwardRemarks('');
    try {
      await axios.post(`${API}/pre-assess-portal/partner/forward-to-admin/${paId}`,
        { remarks }, getAuthHeader());
      toast.success('Forwarded to Admin for 1st approval');
      loadData();
    } catch (e) {
      setAssessments(snapshot);
      toast.error((e.response?.data?.detail || 'Failed') + ' — reverted');
    }
  };

  const loadDocsAndActivity = async (paId) => {
    // Single bundled call — replaces 2+ parallel calls (docs + activity)
    // AND pre-fills payment_history / checklist / risk so sub-components skip their own fetches.
    try {
      const r = await axios.get(`${API}/pre-assessment/${paId}/bundle`, getAuthHeader());
      const b = r.data || {};
      setPaDocs(p => ({ ...p, [paId]: b.documents || [] }));
      setPaActivity(p => ({ ...p, [paId]: b.activity || [] }));
      setPaBundle(p => ({ ...p, [paId]: { payment_history: b.payment_history, checklist: b.checklist, risk: b.risk } }));
    } catch (e) { /* ignore */ }
  };

  const handleValidatePromo = async () => {
    const code = proposalForm.promo_code?.trim();
    if (!code) return;
    setValidatingPromo(true);
    try {
      const r = await axios.post(`${API}/marketing/promo/validate`, { code }, getAuthHeader());
      setProposalForm(p => ({ ...p, promo_applied: r.data }));
      toast.success(`Promo ${r.data.code} valid — ${r.data.discount_type === 'percentage' ? r.data.discount_value + '% off' : '₹' + r.data.discount_value + ' off'}`);
    } catch (e) {
      setProposalForm(p => ({ ...p, promo_applied: null }));
      toast.error(e.response?.data?.detail || 'Invalid promo code');
    } finally {
      setValidatingPromo(false);
    }
  };

  const handleGenerateAI = async (paId, premium = false) => {
    setAiGenerating(premium ? 'premium' : 'std');
    try {
      const r = await axios.post(`${API}/ai-proposal/generate`,
        { pa_id: paId, tone: 'professional', premium }, getAuthHeader());
      setProposalForm(p => ({ ...p, ai_text: r.data.proposal_text }));
      toast.success(`${premium ? '✨ Premium' : 'AI'} draft ready · ${r.data.word_count} words · ${r.data.model.replace('anthropic/', '')}`);
    } catch (e) {
      const status = e.response?.status;
      const detail = e.response?.data?.detail || 'AI generation failed';
      if (status === 401) {
        toast.error('Session expired. Please log in again.');
      } else {
        toast.error(`${detail}${status ? ` (${status})` : ''}`);
      }
      console.error('AI generate failed:', status, detail);
    }
    setAiGenerating(false);
  };

  const computeBreakdown = () => {
    const base = parseFloat(proposalForm.fee_amount) || 0;
    let promoDiscount = 0;
    if (proposalForm.promo_applied && base > 0) {
      promoDiscount = proposalForm.promo_applied.discount_type === 'percentage'
        ? (base * proposalForm.promo_applied.discount_value) / 100
        : proposalForm.promo_applied.discount_value;
    }
    const addDisc = parseFloat(proposalForm.additional_discount) || 0;
    const upsellTotal = upsellCatalog
      .filter(b => proposalForm.upsell_ids.includes(b.id))
      .reduce((s, b) => s + (b.amount || 0), 0);
    const final = Math.max(0, base - promoDiscount - addDisc + upsellTotal);
    return { base, promoDiscount, addDisc, upsellTotal, final };
  };

  const filtered = assessments.filter(a =>
    (filterStage === 'all' || a.stage === filterStage) &&
    (!search || a.client_name?.toLowerCase().includes(search.toLowerCase()) || a.pa_number?.toLowerCase().includes(search.toLowerCase()))
  );

  const getStageInfo = (stage) => STAGE_CONFIG[stage] || STAGE_CONFIG.new;

  const getNextAction = (pa) => {
    switch (pa.stage) {
      case 'new': return { label: 'Send Payment Link (₹5,100)', action: () => handleSendPayment(pa.id), color: 'bg-amber-500 hover:bg-amber-600' };
      case 'payment_pending': return { label: 'Confirm Payment Received', action: () => handleConfirmPayment(pa.id), color: 'bg-blue-500 hover:bg-blue-600' };
      case 'payment_received': return { label: 'Waiting for client to upload', action: null, color: 'bg-slate-400 cursor-not-allowed' };
      case 'partner_review': return { label: 'Review Docs & Forward to Admin', action: () => openForwardForm(pa.id), color: 'bg-pink-500 hover:bg-pink-600' };
      case 'proposal_sent': return { label: 'Waiting for client payment…', action: null, color: 'bg-slate-400 cursor-not-allowed' };
      case 'approved': return { label: 'Send Proposal to Client', action: () => openProposalForm(pa), color: 'bg-emerald-500 hover:bg-emerald-600' };
      case 'proposal_paid': return { label: 'Upload Receipt + Submit Final', action: () => openFinalForm(pa.id), color: 'bg-[#f7620b] hover:bg-[#e55a09]' };
      default: return null;
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><RefreshCw className="h-8 w-8 text-[#2a777a] animate-spin" /></div>;

  return (
    <div className="space-y-6" data-testid="pre-assessment-pipeline">
      {/* Filter context banner */}
      {filterStage !== 'all' && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-center justify-between">
          <p className="text-sm text-amber-800">
            <span className="font-semibold">Filter active:</span> Showing only <span className="font-semibold capitalize">{filterStage.replace(/_/g, ' ')}</span> items
          </p>
          <Button variant="ghost" size="sm" onClick={() => setFilterStage('all')} data-testid="clear-filter-partner">
            <XCircle className="h-4 w-4 mr-1" /> Clear filter
          </Button>
        </div>
      )}

      {/* Stats Bar — clickable */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: 'Total', value: stats.total || 0, color: 'from-slate-500 to-slate-600', click: () => setFilterStage('all') },
          { label: 'Needs Your Review', value: assessments.filter(a => a.stage === 'partner_review').length, color: 'from-pink-500 to-pink-600', highlight: true, click: () => setFilterStage('partner_review') },
          { label: 'Admin Review', value: stats.under_review || 0, color: 'from-purple-500 to-purple-600', click: () => setFilterStage('under_review') },
          { label: 'Approved', value: stats.approved || 0, color: 'from-emerald-500 to-emerald-600', click: () => setFilterStage('approved') },
          { label: 'Proposals Sent', value: stats.proposal_sent || 0, color: 'from-teal-500 to-teal-600', click: () => setFilterStage('proposal_sent') },
          { label: 'Conversion', value: `${stats.conversion_rate || 0}%`, color: 'from-[#2a777a] to-[#236466]' },
        ].map((s, i) => (
          <Card key={i} onClick={s.click} className={`bg-gradient-to-br ${s.color} text-white p-4 border-0 shadow-lg ${s.highlight && s.value > 0 ? 'ring-2 ring-pink-300 ring-offset-2 animate-pulse' : ''} ${s.click ? 'cursor-pointer hover:shadow-xl hover:-translate-y-0.5 transition-all' : ''}`}>
            <p className="text-2xl font-bold">{s.value}</p>
            <p className="text-xs text-white/80">{s.label}</p>
          </Card>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => setShowCreate(true)} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="create-pa-btn">
          <Plus className="h-4 w-4 mr-2" /> New Pre-Assessment
        </Button>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input placeholder="Search by name or PA number..." value={search}
            onChange={e => setSearch(e.target.value)} className="pl-9" data-testid="search-pa" />
        </div>
        <select value={filterStage} onChange={e => setFilterStage(e.target.value)}
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white" data-testid="filter-stage">
          <option value="all">All Stages</option>
          {Object.entries(STAGE_CONFIG).map(([key, val]) => (
            <option key={key} value={key}>{val.label}</option>
          ))}
        </select>
      </div>

      {/* Create Form Modal */}
      {showCreate && (
        <PaCreateForm
          form={form}
          setForm={setForm}
          products={products}
          expressUsage={expressUsage}
          onCancel={() => setShowCreate(false)}
          onSubmit={handleCreate}
        />
      )}

      {/* Pipeline Cards */}
      {filtered.length === 0 ? (
        <Card className="p-12 text-center bg-white border-0 shadow-md">
          <FileText className="h-12 w-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">No pre-assessments found</p>
          <Button onClick={() => setShowCreate(true)} className="mt-3 bg-[#2a777a] hover:bg-[#236466]">Create First Pre-Assessment</Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map(pa => {
            const stageInfo = getStageInfo(pa.stage);
            const StageIcon = stageInfo.icon;
            const isExpanded = expandedId === pa.id;
            const nextAction = getNextAction(pa);

            return (
              <Card key={pa.id} className="bg-white border-0 shadow-md overflow-hidden hover:shadow-lg transition-shadow" data-testid={`pa-card-${pa.id}`}>
                <div className="flex items-center gap-4 p-4 cursor-pointer" onClick={() => {
                  const newExpanded = isExpanded ? null : pa.id;
                  setExpandedId(newExpanded);
                  if (newExpanded && paDocs[pa.id] === undefined) loadDocsAndActivity(pa.id);
                }}>
                  <div className={`w-10 h-10 ${stageInfo.color} rounded-full flex items-center justify-center flex-shrink-0`}>
                    <StageIcon className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-bold text-slate-800">{pa.client_name}</p>
                      <Badge className="bg-slate-100 text-slate-600 text-xs">{pa.pa_number}</Badge>
                      {pa.sale_type === 'express' && (
                        <Badge className="bg-amber-100 text-amber-700 border border-amber-300 text-[10px] font-bold uppercase" data-testid={`express-badge-${pa.id}`}>
                          ⚡ Express
                        </Badge>
                      )}
                      {pa.sale_type === 'express' && pa.express_sale_approval_status === 'pending' && (
                        <Badge className="bg-orange-100 text-orange-700 border border-orange-300 text-[10px] font-bold uppercase">
                          Awaiting Approval
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-slate-500">{pa.country} — {pa.service_type} {pa.product_name ? `(${pa.product_name})` : ''}</p>
                  </div>
                  <Badge className={`${stageInfo.bgColor} ${stageInfo.textColor} border-0`}>{stageInfo.label}</Badge>
                  <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); handlePreviewAsClient(pa.id); }}
                    className="hidden md:inline-flex border-[#f7620b]/40 text-[#f7620b] hover:bg-[#f7620b]/5"
                    data-testid={`preview-client-header-${pa.id}`} title="Open client's portal view in a new tab">
                    <Eye className="h-4 w-4 mr-1" /> Preview as Client
                  </Button>
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setEditingPa(pa); }}
                    className="text-indigo-600 hover:bg-indigo-50"
                    data-testid={`edit-pa-${pa.id}`} title="Edit client details (name, email, mobile, etc.)">
                    <Edit3 className="h-4 w-4" />
                  </Button>
                  <p className="text-xs text-slate-400 hidden lg:block">{pa.created_at ? new Date(pa.created_at).toLocaleDateString() : ''}</p>
                  {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                </div>

                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-slate-100 pt-4 space-y-4">
                    {/* Funnel Progress */}
                    <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                      <FunnelProgress stage={pa.stage} />
                    </div>

                    {/* Client Info */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div><span className="text-slate-500">Email:</span> <span className="font-medium">{pa.client_email}</span></div>
                      <div><span className="text-slate-500">Mobile:</span> <span className="font-medium">{pa.client_mobile || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Age:</span> <span className="font-medium">{pa.client_age || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Education:</span> <span className="font-medium">{pa.education || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Experience:</span> <span className="font-medium">{pa.work_experience || 'N/A'}</span></div>
                      <div><span className="text-slate-500">Payment:</span> <Badge className={pa.fee_payment_status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>{pa.fee_payment_status === 'paid' ? '₹5,100 Paid' : 'Unpaid'}</Badge></div>
                      <div><span className="text-slate-500">Docs:</span> <span className="font-medium">{pa.documents_count || 0} uploaded</span></div>
                      {pa.admin_decision && (
                        <div><span className="text-slate-500">Decision:</span> <Badge className={pa.admin_decision === 'approved' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{pa.admin_decision}</Badge></div>
                      )}
                    </div>

                    {pa.admin_reason && (
                      <div className="bg-slate-50 rounded-lg p-3">
                        <p className="text-xs font-semibold text-slate-600 mb-1">Admin Review Notes:</p>
                        <p className="text-sm text-slate-700">{pa.admin_reason}</p>
                      </div>
                    )}

                    {/* Document Upload (when payment_received) — Optional: Partner can upload on behalf of client */}
                    {pa.stage === 'payment_received' && (
                      <div className="bg-blue-50 rounded-lg p-4">
                        <p className="text-sm font-semibold text-blue-800 mb-2 flex items-center gap-2">
                          <Upload className="h-4 w-4" /> Client is uploading documents
                        </p>
                        <p className="text-xs text-blue-600 mb-2">Client will review and submit from their portal. You can also upload on their behalf:</p>
                        <div className="flex items-center gap-3 flex-wrap">
                          <select id={`docType-${pa.id}`} className="border border-blue-200 rounded-md px-3 py-2 text-sm bg-white" data-testid={`doc-type-${pa.id}`}>
                            <option value="passport">Passport</option>
                            <option value="ielts">IELTS/Language Test</option>
                            <option value="education">Education Certificate</option>
                            <option value="experience">Work Experience Letter</option>
                            <option value="financial">Financial Documents</option>
                            <option value="other">Other</option>
                          </select>
                          <Input type="file" className="flex-1 min-w-[200px]" id={`fileInput-${pa.id}`}
                            onChange={(e) => {
                              const file = e.target.files[0];
                              if (file) {
                                const docType = document.getElementById(`docType-${pa.id}`).value;
                                stageFile(pa.id, file, docType);
                              }
                            }} data-testid={`file-input-${pa.id}`} />
                        </div>
                        {pendingUpload[pa.id] && (
                          <div className="mt-3 flex items-center gap-2 bg-white rounded-md p-2 border border-blue-200">
                            <FileText className="h-4 w-4 text-blue-500 shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium text-slate-700 truncate">{pendingUpload[pa.id].file.name}</p>
                              <p className="text-[10px] text-slate-500 capitalize">{pendingUpload[pa.id].docType} · {(pendingUpload[pa.id].file.size / 1024).toFixed(1)} KB</p>
                            </div>
                            <Button size="sm" onClick={() => confirmUpload(pa.id)} disabled={uploading}
                              className="h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white" data-testid={`upload-btn-${pa.id}`}>
                              <Upload className="h-3 w-3 mr-1" /> {uploading ? 'Uploading...' : 'Upload'}
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => { clearPendingFile(pa.id); const el = document.getElementById(`fileInput-${pa.id}`); if (el) el.value = ''; }}
                              className="h-7 text-xs" data-testid={`cancel-upload-${pa.id}`}>
                              Cancel
                            </Button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Uploaded Docs + Activity (always visible when expanded) */}
                    {['payment_received', 'partner_review', 'documents_submitted', 'under_review', 'approved', 'proposal_sent', 'proposal_paid', 'case_created'].includes(pa.stage) && (
                      <div className="grid md:grid-cols-2 gap-3">
                        <PaDocumentsList
                          pa={pa}
                          docs={paDocs[pa.id]}
                          onRefresh={() => loadDocsAndActivity(pa.id)}
                          getAuthHeader={getAuthHeader}
                        />
                        <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                          <p className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> Client Activity</p>
                          {(paActivity[pa.id] === undefined) ? (
                            <Button variant="link" size="sm" onClick={() => loadDocsAndActivity(pa.id)} className="text-xs h-auto p-0">Click to load activity</Button>
                          ) : paActivity[pa.id].length === 0 ? (
                            <p className="text-xs text-slate-400 italic">No activity logged</p>
                          ) : (
                            <div className="space-y-1.5 max-h-36 overflow-y-auto">
                              {paActivity[pa.id].map((a, i) => (
                                <div key={i} className="text-xs">
                                  <span className="font-medium text-slate-700 capitalize">{a.action.replace(/_/g, ' ')}</span>
                                  <span className="text-slate-400 ml-2">{a.created_at ? new Date(a.created_at).toLocaleString() : ''}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Waiting banner for proposal_sent stage */}
                    {pa.stage === 'proposal_sent' && (
                      <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3 animate-pulse">
                        <div className="h-10 w-10 bg-amber-500 rounded-full flex items-center justify-center shrink-0">
                          <Bell className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold text-amber-900">Waiting for Client Payment</p>
                          <p className="text-xs text-amber-700 mt-0.5">Proposal of ₹{(pa.proposal_fee || 0).toLocaleString('en-IN')} sent to {pa.client_name}. Notify them via WhatsApp/Email to speed things up.</p>
                        </div>
                      </div>
                    )}

                    {/* Waiting banner for awaiting_final_approval stage */}
                    {pa.stage === 'awaiting_final_approval' && (
                      <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 rounded-lg p-4 flex items-center gap-3">
                        <div className="h-10 w-10 bg-indigo-500 rounded-full flex items-center justify-center shrink-0">
                          <Clock className="h-5 w-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold text-indigo-900">Submitted to Admin · Awaiting Final Approval</p>
                          <p className="text-xs text-indigo-700 mt-0.5">Admin will verify receipt + signed agreement and activate the case by assigning a Case Manager. Aapka role iske baad complete ho jayega.</p>
                        </div>
                      </div>
                    )}

                    {/* Financial Summary — visible for proposal_paid / awaiting_final_approval / case_created */}
                    <PaFinancialSummary
                      pa={pa}
                      onDownload={downloadPdf}
                      onSendInvoice={sendInvoiceNow}
                      onGenerateAgreement={(p) => {
                        if (p.active_agreement_id) {
                          setViewingAgreementFor(p);
                        } else {
                          setGeneratingAgreementFor(p);
                        }
                      }}
                      sendingInvoice={sendingInvoice}
                    />

                    {/* Payment History Timeline + Risk + Checklist (visible once fee_payment_status is paid) */}
                    {pa.fee_payment_status === 'paid' && paBundle[pa.id] && (
                      <div className="grid md:grid-cols-2 gap-3">
                        <div className="bg-white rounded-lg p-3 border border-slate-200">
                          <p className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> Payment Timeline</p>
                          <PaymentHistoryTimeline scope="pa" id={pa.id} compact initialData={paBundle[pa.id].payment_history} />
                        </div>
                        <div className="bg-white rounded-lg p-3 border border-slate-200 space-y-3">
                          <RiskScoreBadge paId={pa.id} showFactors initialData={paBundle[pa.id].risk} />
                          <SmartDocChecklist paId={pa.id} initialData={{...paBundle[pa.id].checklist, country: pa.country, service_type: pa.service_type}} />
                        </div>
                      </div>
                    )}

                    {/* Final-Submit UI (proposal_paid → awaiting_final_approval) */}
                    {finalSubmittingId === pa.id && (
                      <PaFinalSubmitForm
                        pa={pa}
                        pendingUpload={pendingUpload[pa.id]}
                        uploading={uploading}
                        stageFile={stageFile}
                        confirmUpload={confirmUpload}
                        clearPendingFile={clearPendingFile}
                        finalNotes={finalNotes}
                        setFinalNotes={setFinalNotes}
                        handleSubmitFinal={handleSubmitFinal}
                        onCancel={() => setFinalSubmittingId(null)}
                      />
                    )}

                    {/* Forward-to-Admin Form (partner_review stage) */}
                    {forwardingId === pa.id && (
                      <PaForwardForm
                        pa={pa}
                        forwardRemarks={forwardRemarks}
                        setForwardRemarks={setForwardRemarks}
                        handleForwardToAdmin={handleForwardToAdmin}
                        onCancel={() => setForwardingId(null)}
                      />
                    )}

                    {/* Proposal Form (when approved) — Enhanced with promo + discount + upsells + AI */}
                    {showProposal === pa.id && (
                      <PaProposalForm
                        pa={pa}
                        proposalForm={proposalForm}
                        setProposalForm={setProposalForm}
                        upsellCatalog={upsellCatalog}
                        validatingPromo={validatingPromo}
                        handleValidatePromo={handleValidatePromo}
                        aiGenerating={aiGenerating}
                        handleGenerateAI={handleGenerateAI}
                        handleSendProposal={handleSendProposal}
                        breakdown={computeBreakdown()}
                        onCancel={() => setShowProposal(null)}
                        currentUserRole={(JSON.parse(localStorage.getItem('user') || '{}')).role}
                      />
                    )}

                    {/* Action Buttons — always show Copy Link + Preview as Client, show nextAction if exists */}
                    {showProposal !== pa.id && forwardingId !== pa.id && finalSubmittingId !== pa.id && (
                      <PaActionBar
                        pa={pa}
                        nextAction={nextAction}
                        handleCopyPublicLink={handleCopyPublicLink}
                        handlePreviewAsClient={handlePreviewAsClient}
                      />
                    )}

                    {/* Stage Progress Indicator */}
                    <PaStageProgress stage={pa.stage} />
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* Agreement Generator Modal */}
      {generatingAgreementFor && (
        <AgreementGenerator
          pa={generatingAgreementFor}
          onClose={() => setGeneratingAgreementFor(null)}
          onGenerated={() => { loadData(); setGeneratingAgreementFor(null); }}
        />
      )}

      {/* Agreement Viewer Modal (existing agreement) */}
      {viewingAgreementFor && (
        <AgreementViewerModal
          pa={viewingAgreementFor}
          onClose={() => setViewingAgreementFor(null)}
          onRegenerate={() => { setViewingAgreementFor(null); setGeneratingAgreementFor(viewingAgreementFor); }}
        />
      )}

      {/* Edit PA Details Modal */}
      <PaEditDetailsModal
        pa={editingPa}
        open={!!editingPa}
        onClose={() => setEditingPa(null)}
        onSaved={(payload) => {
          setAssessments(prev => prev.map(x => x.id === editingPa.id ? { ...x, ...payload } : x));
          loadData();
        }}
      />
    </div>
  );
};

export default PreAssessmentPipeline;
