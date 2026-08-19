/**
 * Bulk Pre-Assessment — Australia PR (189 / 190 / 491).
 *
 * Phase A: upload Excel → validate → background-generate draft reports.
 * Phase B: review dashboard, per-client edit (code / english / experience / marital) + regenerate.
 * Export: ZIP of all PDFs + summary Excel.
 *
 * Route: /sales/bulk-assessment
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import EmailSettingsDialog from './EmailSettingsDialog';
import { EmailPreviewDialog, EmailSummaryDialog } from './EmailSendDialogs';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from '@/components/ui/select';
import {
  Tooltip, TooltipTrigger, TooltipContent, TooltipProvider,
} from '@/components/ui/tooltip';
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuSub, DropdownMenuSubTrigger,
  DropdownMenuSubContent, DropdownMenuPortal,
} from '@/components/ui/dropdown-menu';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  ArrowLeft, Upload, Download, FileSpreadsheet, Loader2, RefreshCw, Play,
  CheckCircle2, XCircle, AlertTriangle, Edit3, FileText, Users, Package, Sparkles,
  Info, Check, ClipboardCheck, FileUser, ExternalLink, Search, Star, Mail, Send,
  MoreVertical, Ban, RotateCcw, LayoutTemplate,
} from 'lucide-react';

// Open a client's resume link (from the uploaded Excel) in a new tab
const openResume = (url) => {
  if (!url) { toast.error('No resume link provided for this client'); return; }
  const href = /^https?:\/\//i.test(url) ? url : `https://${url}`;
  window.open(href, '_blank', 'noopener,noreferrer');
};
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const QUALS = ['doctorate', 'master', 'bachelor', 'diploma', 'trade', 'high_school'];
const COST_CATEGORIES = [
  'Government Fees', 'Skill Assessment', 'English Test',
  'Medical Tests', 'Police Clearance', 'Translation',
  'LEAMSS Professional Fees', 'Protection Policy Coverage', 'Other',
];

// Package Total is always derived from the breakdown so it stays consistent with the PDF
// (which prints Professional Fee, Discount and GST separately). Falls back to the stored
// total only when no breakdown fields exist.
const pkgTotal = (p) => {
  if (p.professional_fee == null && p.discount == null && p.gst == null) return Number(p.total) || 0;
  return Math.max(0, (Number(p.professional_fee) || 0) - (Number(p.discount) || 0) + (Number(p.gst) || 0));
};

const money = (tbc) => Object.entries(tbc || {}).map(([c, v]) => `${c === 'INR' ? '₹' : c + ' '}${(Number(v) || 0).toLocaleString('en-IN')}`).join(' + ') || '—';

export default function BulkPreAssessment() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [batches, setBatches] = useState([]);
  const [batch, setBatch] = useState(null);
  const [rows, setRows] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [editRow, setEditRow] = useState(null);
  const [showDefaults, setShowDefaults] = useState(false);
  const [showAiReview, setShowAiReview] = useState(false);
  const [rowFilter, setRowFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [emailCfg, setEmailCfg] = useState(null);
  const [emailingRow, setEmailingRow] = useState(null);
  const [showMailAccounts, setShowMailAccounts] = useState(false);
  const [showEmailSettings, setShowEmailSettings] = useState(false);
  const [showEmailPreview, setShowEmailPreview] = useState(false);
  const [showEmailSummary, setShowEmailSummary] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [markRow, setMarkRow] = useState(null);
  const fileRef = useRef(null);
  const pollRef = useRef(null);

  const loadTemplates = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/email-templates`, { headers });
      setTemplates(r.data.templates || []);
    } catch (e) { /* silent */ }
  }, [headers]);
  useEffect(() => { loadTemplates(); }, [loadTemplates]);

  const loadBatches = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/bulk-assessments`, { headers });
      setBatches(r.data.batches || []);
    } catch (e) { /* silent */ }
  }, [headers]);

  const loadBatch = useCallback(async (id) => {
    try {
      const r = await axios.get(`${API}/bulk-assessments/${id}`, { headers });
      setBatch(r.data.batch);
      setRows(r.data.rows || []);
      return r.data.batch;
    } catch (e) { toast.error(formatApiError(e, 'Failed to load batch')); }
  }, [headers]);

  useEffect(() => { loadBatches(); }, [loadBatches]);

  const refreshEmailCfg = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/bulk-assessments/email-config`, { headers });
      setEmailCfg(r.data);
    } catch (e) { /* silent */ }
  }, [headers]);
  useEffect(() => { refreshEmailCfg(); }, [refreshEmailCfg]);

  // Poll while generating, AI-enriching, or emailing
  useEffect(() => {
    if (batch?.status === 'generating' || batch?.status === 'enriching' || batch?.email_status === 'sending') {
      pollRef.current = setInterval(async () => {
        const b = await loadBatch(batch.id);
        if (b && b.status !== 'generating' && b.status !== 'enriching' && b.email_status !== 'sending') {
          clearInterval(pollRef.current); setGenerating(false);
        }
      }, 2500);
      return () => clearInterval(pollRef.current);
    }
  }, [batch?.status, batch?.email_status, batch?.id, loadBatch]);

  const runAiEnrich = async () => {
    if (!batch) return;
    try {
      const r = await axios.post(`${API}/bulk-assessments/${batch.id}/ai-enrich`, {}, { headers });
      toast.success(r.data.resumed
        ? `Resuming AI detection for ${r.data.enriching} remaining resume(s)…`
        : `AI reading ${r.data.enriching} resume(s) to detect ANZSCO codes…`);
      await loadBatch(batch.id);
    } catch (e) {
      toast.error(formatApiError(e, 'Could not start AI detection'));
    }
  };

  const downloadTemplate = async () => {
    try {
      const r = await axios.get(`${API}/bulk-assessments/template`, { headers, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url; a.download = 'bulk_preassessment_template.xlsx'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error('Template download failed'); }
  };

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append('file', file);
      const r = await axios.post(`${API}/bulk-assessments/validate`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`Validated: ${r.data.valid} ready, ${r.data.invalid} need fixing`);
      await loadBatch(r.data.batch_id);
      await loadBatches();
    } catch (e) {
      toast.error(formatApiError(e, 'Validation failed'));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const startGenerate = async () => {
    if (!batch) return;
    setGenerating(true);
    try {
      await axios.post(`${API}/bulk-assessments/${batch.id}/generate`, {}, { headers });
      toast.success('Generation started');
      await loadBatch(batch.id);
    } catch (e) {
      setGenerating(false);
      toast.error(formatApiError(e, 'Could not start generation'));
    }
  };

  const emailCategory = async (kind) => {
    if (!batch) return;
    if (!emailCfg?.configured) { toast.error('Email not set up yet — see the setup banner'); return; }
    const ep = kind === 'not_eligible' ? 'email-not-eligible' : 'email-resume-request';
    const label = kind === 'not_eligible' ? 'Not-Eligible reports' : 'resume-upload requests';
    try {
      const r = await axios.post(`${API}/bulk-assessments/${batch.id}/${ep}`, { bcc_self: true }, { headers });
      toast.success(`Queued ${r.data.queued} ${label}`);
      await loadBatch(batch.id);
    } catch (e) { toast.error(formatApiError(e, `Could not send ${label}`)); }
  };

  const sendReminders = async () => {
    if (!batch) return;
    if (!emailCfg?.configured) { toast.error('Email not set up yet — see the setup banner'); return; }
    if (!window.confirm(`Send a follow-up reminder (with the offer) to ${reminderCount} client(s) who already received their report?`)) return;
    try {
      const r = await axios.post(`${API}/bulk-assessments/${batch.id}/email-reminder`, { bcc_self: true }, { headers });
      toast.success(`Queued ${r.data.queued} reminder email(s)`);
      await loadBatch(batch.id);
    } catch (e) { toast.error(formatApiError(e, 'Could not send reminders')); }
  };

  const exportZip = async () => {
    try {
      toast.info('Preparing ZIP…');
      const r = await axios.get(`${API}/bulk-assessments/${batch.id}/export`, { headers, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url; a.download = `${batch.id}_reports.zip`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(formatApiError(e, 'Export failed')); }
  };

  const viewPdf = async (row) => {
    try {
      const r = await axios.get(`${API}/bulk-assessments/row/${row.id}/pdf`, { headers, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      window.open(url, '_blank');
    } catch (e) { toast.error(formatApiError(e, 'Could not open PDF')); }
  };

  const emailRow = async (row, templateId = null) => {
    if (!emailCfg?.configured) { toast.error('Email not set up yet — see the setup banner'); return; }
    if (!row.parsed?.email) { toast.error(`${row.parsed?.name || 'This client'} has no email address`); return; }
    setEmailingRow(row.id);
    try {
      const body = { bcc_self: true };
      if (templateId) body.template_id = templateId;
      const r = await axios.post(`${API}/bulk-assessments/row/${row.id}/email`, body, { headers });
      const kindLabel = { eligible: 'Report', improvable: 'Not-Eligible report', ineligible: 'Not-Eligible report', needs_resume: 'Resume-upload request' }[r.data.kind] || 'Email';
      toast.success(`${kindLabel} emailed to ${r.data.sent_to}`);
      await loadBatch(batch.id);
    } catch (e) { toast.error(formatApiError(e, 'Could not send email')); }
    finally { setEmailingRow(null); }
  };

  const markEligibility = async (row, kind, reason = null) => {
    try {
      const r = await axios.post(`${API}/bulk-assessments/row/${row.id}/set-eligibility`, { kind, reason }, { headers });
      const msg = kind === 'auto' ? 'Reset to automatic eligibility'
        : kind === 'improvable' ? 'Marked Not-Eligible (future possible)' : 'Marked Not-Eligible (permanent)';
      toast.success(`${msg}${r.data.regenerated ? ' — report regenerated' : ''}`);
      await loadBatch(batch.id);
    } catch (e) { toast.error(formatApiError(e, 'Could not update eligibility')); }
  };

  const assignConsultant = async (rowIds, email) => {
    try {
      const body = { consultant_email: email || '' };
      if (rowIds) body.row_ids = rowIds;
      const r = await axios.post(`${API}/bulk-assessments/${batch.id}/assign-consultant`, body, { headers });
      toast.success(email ? `Assigned ${r.data.updated} client(s) → ${email}` : `Cleared consultant on ${r.data.updated} client(s)`);
      await loadBatch(batch.id);
    } catch (e) { toast.error(formatApiError(e, 'Could not assign consultant')); }
  };

  const progressPct = batch && batch.valid ? Math.round(((batch.generated + batch.failed) / batch.valid) * 100) : 0;
  const enrichStalled = !!batch && batch.status === 'enriching' && (() => {
    const hb = batch.ai_heartbeat;
    if (!hb) return true;
    const t = new Date(hb).getTime();
    if (Number.isNaN(t)) return true;
    return (Date.now() - t) > 95000;  // no progress for ~95s → background run likely died
  })();
  const rowBucket = (r) => {
    if (r.status === 'needs_ai' || r.status === 'error') return 'needs_resume';
    const v = r.eligibility?.verdict;
    if (v === 'improvable') return 'improvable';
    if (v === 'ineligible_age') return 'ineligible';
    return 'eligible';
  };
  const displayRows = rows.filter((r) => {
    const p = r.parsed || {};
    const q = search.trim().toLowerCase();
    if (q) {
      const hay = [p.name, p.email, p.phone, p.anzsco_code, p.occupation_title, p.consultant_email, p.consultant_name]
        .filter(Boolean).join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (rowFilter === 'all') return true;
    if (rowFilter === 'review') return r.parsed?.anzsco_source === 'ai' && !r.parsed?.ai_reviewed;
    if (rowFilter === 'ai') return r.parsed?.anzsco_source === 'ai';
    if (['eligible', 'improvable', 'ineligible', 'needs_resume'].includes(rowFilter)) return rowBucket(r) === rowFilter;
    return r.status === rowFilter;
  });
  const sendableCount = rows.filter((r) => r.status === 'generated' && r.parsed?.email).length;
  const notEligibleCount = rows.filter((r) => r.status === 'generated' && ['improvable', 'ineligible'].includes(rowBucket(r)) && r.parsed?.email).length;
  const resumeReqCount = rows.filter((r) => (r.status === 'needs_ai' || r.status === 'error') && r.parsed?.email).length;
  const reminderCount = rows.filter((r) => r.status === 'generated' && r.email_status === 'sent' && rowBucket(r) === 'eligible' && r.pdf_file_id && r.parsed?.email).length;
  const activeSenders = (emailCfg?.senders || []).filter((s) => s.active);

  // Categorise why 'needs AI' rows failed, so the user knows what to do (retry vs manual).
  const categorizeAiError = (e) => {
    if (!e) return 'untried';
    const s = String(e).toLowerCase();
    if (s.includes('html page') || s.includes('public') || s.includes('anyone with the link')
      || s.includes('publicly reachable') || s.includes('http 40') || s.includes('http 30')
      || s.includes('dropped the connection')) return 'inaccessible';
    if (s.includes('empty') || s.includes('scanned') || s.includes('unreadable')) return 'scanned';
    if (s.includes('unsupported file')) return 'unsupported';
    if (s.includes('could not match')) return 'nomatch';
    if (s.includes('timed out')) return 'timeout';
    return 'other';
  };
  const AI_FAIL_META = {
    inaccessible: { label: 'Private / unreachable link', tip: 'Set the file to "Anyone with the link" (Viewer) then Retry — or open the resume and set the code manually.' },
    scanned: { label: 'Scanned image resume', tip: 'Now readable via OCR — click "Retry AI" to auto-detect. If it still fails, open the resume and set the code manually.' },
    unsupported: { label: 'Unsupported file type', tip: 'Only PDF, DOCX & TXT can be read. Open the resume and set the code manually.' },
    nomatch: { label: 'AI couldn\'t match a code', tip: 'Resume was read but no clear occupation matched. Open the resume and pick the code manually.' },
    timeout: { label: 'AI timed out', tip: 'A transient slowdown — click Retry to try these again.' },
    other: { label: 'Other error', tip: 'Click Retry, or open the resume and set the code manually.' },
  };
  const needsAiRows = rows.filter((r) => r.status === 'needs_ai' && r.parsed?.resume_link);
  const aiBreakdown = needsAiRows.reduce((acc, r) => {
    const k = categorizeAiError(r.ai_error); acc[k] = (acc[k] || 0) + 1; return acc;
  }, {});
  const aiUntried = aiBreakdown.untried || 0;
  // scanned/unsupported are now retryable too (OCR reads them); private links only if re-shared.
  const aiRetryable = (aiBreakdown.timeout || 0) + (aiBreakdown.inaccessible || 0)
    + (aiBreakdown.other || 0) + (aiBreakdown.scanned || 0) + (aiBreakdown.unsupported || 0);
  const aiTriedFailed = needsAiRows.length - aiUntried;

  const statusBadge = (s) => {
    const map = {
      valid: 'bg-sky-100 text-sky-700', generated: 'bg-emerald-100 text-emerald-700',
      error: 'bg-rose-100 text-rose-700', failed: 'bg-amber-100 text-amber-700',
      needs_ai: 'bg-violet-100 text-violet-700',
    };
    const label = s === 'needs_ai' ? 'needs AI' : s;
    return <Badge className={`${map[s] || 'bg-slate-100'} text-[10px]`}>{label}</Badge>;
  };

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="bulk-assessment-page">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/sales/my-assessments')} data-testid="bulk-back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />Assessments
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Users className="h-7 w-7 text-teal-600" />
              Bulk Pre-Assessment
              <Badge className="bg-teal-600 text-white text-[9px]">AU · 189/190/491</Badge>
            </h1>
            <p className="text-sm text-slate-500">Upload your client list → generate accurate reports for everyone</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate('/sales/fee-master')} className="ml-auto border-teal-300 text-teal-700 hover:bg-teal-50" data-testid="open-fee-master-btn">
            <Package className="h-4 w-4 mr-1" />Fee Master
          </Button>
        </div>

        {/* Upload */}
        <Card className="p-4 space-y-3" data-testid="bulk-upload-card">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-base font-bold flex items-center gap-2"><Upload className="h-4 w-4 text-teal-600" />Step 1 · Upload Client List</h2>
            <Button variant="outline" size="sm" onClick={downloadTemplate} data-testid="download-template-btn">
              <Download className="h-4 w-4 mr-1" />Download Excel Template
            </Button>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" disabled={uploading}
              onChange={(e) => handleUpload(e.target.files?.[0])} className="text-sm" data-testid="bulk-file-input" />
            {uploading && <span className="flex items-center gap-1 text-sm text-teal-700"><Loader2 className="h-4 w-4 animate-spin" />Validating…</span>}
          </div>
          <p className="text-[11px] text-slate-500">
            Required: <strong>Name</strong> + either an <strong>ANZSCO Code</strong> or a public <strong>Resume Link</strong> (AI detects the code & fills missing details).
            Recommended: Date of Birth, Qualification, Work Experience. Optional: Email, Mobile, Gender, Marital Status. English defaults to 8/8/8/8/8 (editable per client).
          </p>
        </Card>

        {/* Batch summary + generate */}
        {batch && (
          <Card className="p-4 space-y-3" data-testid="bulk-batch-card">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h2 className="text-base font-bold">{batch.name}</h2>
                <p className="text-[11px] text-slate-500">{batch.id} · {batch.status}</p>
              </div>
              <div className="flex gap-2 flex-wrap">
                <div className="text-center px-3"><p className="text-lg font-bold text-sky-700">{batch.valid}</p><p className="text-[9px] text-slate-500">READY</p></div>
                {batch.needs_ai > 0 && (
                  <div className="text-center px-3"><p className="text-lg font-bold text-violet-600">{batch.needs_ai}</p><p className="text-[9px] text-slate-500">NEEDS AI</p></div>
                )}
                <div className="text-center px-3"><p className="text-lg font-bold text-rose-600">{batch.invalid}</p><p className="text-[9px] text-slate-500">NEEDS FIX</p></div>
                <div className="text-center px-3"><p className="text-lg font-bold text-emerald-700">{batch.generated}</p><p className="text-[9px] text-slate-500">GENERATED</p></div>
                <div className="flex items-center gap-2 ml-2">
                  <span className="text-[11px] text-slate-600">Show EOI in reports</span>
                  <Switch
                    checked={!!batch.show_eoi_backlog}
                    onCheckedChange={async (v) => {
                      try {
                        await axios.patch(`${API}/bulk-assessments/${batch.id}/settings`, null, {
                          headers, params: { show_eoi_backlog: v },
                        });
                        setBatch({ ...batch, show_eoi_backlog: v });
                        toast.success(v ? 'EOI backlog will show in reports' : 'EOI backlog hidden — re-generate to apply');
                      } catch (e) { toast.error('Could not update setting'); }
                    }}
                    data-testid="bulk-eoi-flag"
                  />
                </div>
              </div>
            </div>

            {emailCfg && !emailCfg.configured && (
              <div className="bg-amber-50 border-l-4 border-amber-400 rounded p-3 text-[12px] text-amber-900 space-y-1" data-testid="email-config-banner">
                <p className="font-semibold flex items-center gap-1"><Mail className="h-4 w-4" />Email setup — send each report from the assigned consultant's @{emailCfg.domain || 'leamss.com'} inbox</p>
                <p>Uses Google Workspace <b>domain-wide delegation</b> (one service account, no per-person passwords). Your Workspace Super Admin needs to:</p>
                <ol className="list-decimal ml-5 space-y-0.5">
                  <li>Create a Google Cloud <b>service account</b> and enable the <b>Gmail API</b>.</li>
                  <li>In <a className="underline text-amber-800" href="https://admin.google.com" target="_blank" rel="noreferrer">admin.google.com</a> → Security → API controls → <b>Domain-wide delegation</b>, authorize the service account Client ID with scope <code>https://www.googleapis.com/auth/gmail.send</code>.</li>
                  <li>Share the service-account <b>JSON key</b> so it can be set as <code>GMAIL_SA_JSON_B64</code> in the backend.</li>
                </ol>
                {emailCfg.sa_client_id && (
                  <p className="text-[11px] mt-1">Service account Client ID to authorize: <code className="bg-amber-100 px-1 rounded">{emailCfg.sa_client_id}</code></p>
                )}
              </div>
            )}
            {emailCfg && emailCfg.configured && (
              <div className="bg-emerald-50 border-l-4 border-emerald-400 rounded p-2 text-[11px] text-emerald-800 flex items-center gap-2" data-testid="email-config-ok">
                <Mail className="h-4 w-4" />Email ready — reports send from each client's assigned consultant (default {emailCfg.default_sender}). {emailCfg.remaining_today} left today per mailbox.
              </div>
            )}

            {batch.needs_ai > 0 && batch.status !== 'enriching' && (
              <div className="bg-violet-50 border-l-4 border-violet-400 rounded p-3 space-y-2" data-testid="ai-enrich-banner">
                <div className="flex items-center gap-3 flex-wrap">
                  <Sparkles className="h-5 w-5 text-violet-600 shrink-0" />
                  <p className="text-[12px] text-violet-900 flex-1 min-w-[240px]">
                    <strong>{needsAiRows.length}</strong> client(s) have a Resume Link but no ANZSCO code.
                    AI can read each resume, find the right ANZSCO code and fill missing details (experience, qualification, DOB).
                    {aiUntried > 0 && <span className="block text-[10px] text-violet-500">Note: resume links must be public ("Anyone with the link").</span>}
                  </p>
                  <Button onClick={runAiEnrich} className="bg-violet-600 hover:bg-violet-700" data-testid="ai-enrich-btn">
                    <Sparkles className="h-4 w-4 mr-1" />
                    {aiTriedFailed > 0 && aiUntried === 0 ? `Retry AI (${aiRetryable ? aiRetryable : needsAiRows.length})` : 'Detect ANZSCO from Resumes'}
                  </Button>
                </div>

                {aiTriedFailed > 0 && (
                  <div className="bg-white/70 rounded border border-violet-200 p-2.5" data-testid="ai-fail-breakdown">
                    <p className="text-[11px] font-semibold text-violet-900 mb-1.5 flex items-center gap-1">
                      <Info className="h-3.5 w-3.5" />Why {aiTriedFailed} couldn't be auto-detected — these need your action:
                    </p>
                    <div className="grid sm:grid-cols-2 gap-1.5">
                      {Object.entries(aiBreakdown).filter(([k]) => k !== 'untried').map(([k, n]) => (
                        <div key={k} className="flex items-start gap-2 text-[11px]" data-testid={`ai-fail-${k}`}>
                          <span className="mt-0.5 inline-flex items-center justify-center min-w-[22px] h-[18px] px-1 rounded-full bg-rose-100 text-rose-700 font-semibold text-[10px]">{n}</span>
                          <span className="text-slate-600"><span className="font-medium text-slate-800">{(AI_FAIL_META[k] || AI_FAIL_META.other).label}.</span> {(AI_FAIL_META[k] || AI_FAIL_META.other).tip}</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-[10px] text-slate-500 mt-2">
                      Tip: use the <FileUser className="h-3 w-3 inline -mt-0.5 text-violet-500" /> resume button on each row to open the CV, then set the code in the editor. Filter by <button className="underline text-violet-600" onClick={() => setRowFilter('needs_ai')} data-testid="jump-needs-ai">Needs AI</button> to see them all.
                    </p>
                  </div>
                )}
              </div>
            )}

            {batch.status === 'enriching' && (
              <div data-testid="bulk-ai-progress">
                <div className="flex justify-between text-[11px] text-violet-700 mb-1">
                  <span className="flex items-center gap-1"><Sparkles className="h-3.5 w-3.5" />AI reading resumes & detecting ANZSCO codes…</span>
                  <span>{batch.ai_done || 0} / {batch.ai_total || batch.needs_ai}</span>
                </div>
                <Progress value={batch.ai_total ? Math.round(((batch.ai_done || 0) / batch.ai_total) * 100) : 0} className="h-2" />
              </div>
            )}

            {batch.status === 'generating' && (
              <div data-testid="bulk-progress">
                <div className="flex justify-between text-[11px] text-slate-600 mb-1">
                  <span>Generating reports…</span>
                  <span>{batch.generated + batch.failed} / {batch.valid}</span>
                </div>
                <Progress value={progressPct} className="h-2" />
              </div>
            )}

            {batch.email_status === 'sending' && (
              <div data-testid="bulk-email-progress">
                <div className="flex justify-between text-[11px] text-indigo-700 mb-1">
                  <span className="flex items-center gap-1"><Send className="h-3.5 w-3.5" />Emailing reports to clients…</span>
                  <span>{(batch.email_done || 0) + (batch.email_failed || 0)} / {batch.email_total || 0}</span>
                </div>
                <Progress value={batch.email_total ? Math.round((((batch.email_done || 0) + (batch.email_failed || 0)) / batch.email_total) * 100) : 0} className="h-2" />
              </div>
            )}
            {batch.email_status === 'done' && (
              <p className="text-[11px] text-slate-600 flex items-center gap-2" data-testid="bulk-email-summary">
                <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5 text-emerald-600" />Emailed {batch.email_done || 0} · {batch.email_failed || 0} failed{batch.email_skipped ? ` · ${batch.email_skipped} skipped (no email)` : ''}</span>
                <button type="button" onClick={() => setShowEmailSummary(true)} className="underline text-indigo-600 hover:text-indigo-700" data-testid="view-email-summary-btn">View full summary</button>
              </p>
            )}

            <div className="flex gap-2 flex-wrap">
              {rows.some((r) => r.parsed?.anzsco_source === 'ai') && batch.status !== 'enriching' && (
                <Button onClick={() => setShowAiReview(true)} variant="outline" className="border-violet-400 text-violet-700 hover:bg-violet-50" data-testid="ai-review-btn">
                  <ClipboardCheck className="h-4 w-4 mr-1" />
                  Review AI ({rows.filter((r) => r.parsed?.anzsco_source === 'ai' && !r.parsed?.ai_reviewed).length})
                </Button>
              )}
              {batch.status !== 'generating' && batch.status !== 'enriching' && (
                <Button onClick={() => setShowDefaults(true)} variant="outline" className="border-amber-400 text-amber-800 hover:bg-amber-50" data-testid="batch-defaults-btn">
                  <Package className="h-4 w-4 mr-1" />Set Batch Cost & Packages
                </Button>
              )}
              {batch.status !== 'generating' && batch.status !== 'enriching' && (
                <Button onClick={startGenerate} disabled={batch.valid === 0} className="bg-teal-600 hover:bg-teal-700" data-testid="bulk-generate-btn">
                  <Play className="h-4 w-4 mr-1" />
                  {batch.generated > 0 ? 'Re-generate All' : `Generate ${batch.valid} Reports`}
                </Button>
              )}
              {batch.status === 'enriching' && (
                <Button disabled className="bg-violet-600"><Loader2 className="h-4 w-4 mr-1 animate-spin" />AI detecting…</Button>
              )}
              {batch.status === 'enriching' && enrichStalled && (
                <Button onClick={runAiEnrich} variant="outline" className="border-amber-500 text-amber-700 hover:bg-amber-50" data-testid="resume-ai-btn">
                  <RefreshCw className="h-4 w-4 mr-1" />Resume AI detection
                </Button>
              )}
              {batch.status === 'generating' && (
                <Button disabled className="bg-teal-600"><Loader2 className="h-4 w-4 mr-1 animate-spin" />Generating…</Button>
              )}
              {batch.generated > 0 && (
                <Button variant="outline" onClick={exportZip} data-testid="bulk-export-btn">
                  <Package className="h-4 w-4 mr-1" />Download ZIP + Summary
                </Button>
              )}
              {batch.generated > 0 && batch.email_status !== 'sending' && (
                <Button onClick={() => { if (!emailCfg?.configured) { toast.error('Email not set up yet — see the setup banner'); return; } setShowEmailPreview(true); }} disabled={sendableCount === 0}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50" data-testid="bulk-email-all-btn"
                  title={sendableCount === 0 ? 'No generated reports have a client email' : `Email ${sendableCount} report(s)`}>
                  <Send className="h-4 w-4 mr-1" />Email All ({sendableCount})
                </Button>
              )}
              {batch.email_status !== 'sending' && reminderCount > 0 && (
                <Button onClick={sendReminders}
                  className="bg-teal-600 hover:bg-teal-700 text-white" data-testid="bulk-email-reminder-btn"
                  title={`Send a follow-up reminder (with offer) to ${reminderCount} client(s) who already got their report`}>
                  <RefreshCw className="h-4 w-4 mr-1" />Send Reminder ({reminderCount})
                </Button>
              )}
              {batch.generated > 0 && batch.email_status !== 'sending' && notEligibleCount > 0 && (
                <Button onClick={() => emailCategory('not_eligible')}
                  className="bg-amber-600 hover:bg-amber-700 text-white" data-testid="bulk-email-not-eligible-btn"
                  title={`Email ${notEligibleCount} Not-Eligible report(s) with reasoning`}>
                  <Send className="h-4 w-4 mr-1" />Email Not-Eligible ({notEligibleCount})
                </Button>
              )}
              {batch.email_status !== 'sending' && resumeReqCount > 0 && (
                <Button onClick={() => emailCategory('resume_request')}
                  className="bg-rose-600 hover:bg-rose-700 text-white" data-testid="bulk-email-resume-btn"
                  title={`Ask ${resumeReqCount} client(s) to upload their resume`}>
                  <Mail className="h-4 w-4 mr-1" />Request Resume ({resumeReqCount})
                </Button>
              )}
              {batch.email_status === 'sending' && (
                <Button disabled className="bg-indigo-600"><Loader2 className="h-4 w-4 mr-1 animate-spin" />Emailing…</Button>
              )}
              <Button variant="outline" onClick={() => loadBatch(batch.id)}><RefreshCw className="h-4 w-4 mr-1" />Refresh</Button>
            </div>
          </Card>
        )}

        {/* Rows table */}
        {batch && rows.length > 0 && (
          <Card className="p-0 overflow-hidden" data-testid="bulk-rows-card">
            <div className="px-3 py-2 border-b bg-slate-50">
              <div className="relative w-full sm:max-w-sm mb-2">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search client by name, email, phone, ANZSCO code…"
                  className="h-8 pl-8 pr-8 text-xs bg-white" data-testid="client-search-input" />
                {search && (
                  <button type="button" onClick={() => setSearch('')} data-testid="client-search-clear"
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                    <XCircle className="h-4 w-4" />
                  </button>
                )}
              </div>
              <div className="flex items-center gap-1.5 flex-wrap" data-testid="row-filters">
              {[
                ['all', `All (${rows.length})`],
                ['review', `Review pending (${rows.filter((r) => r.parsed?.anzsco_source === 'ai' && !r.parsed?.ai_reviewed).length})`],
                ['ai', `AI-detected (${rows.filter((r) => r.parsed?.anzsco_source === 'ai').length})`],
                ['needs_ai', `Needs AI (${rows.filter((r) => r.status === 'needs_ai').length})`],
                ['error', `Needs fix (${rows.filter((r) => r.status === 'error').length})`],
                ['generated', `Generated (${rows.filter((r) => r.status === 'generated').length})`],
                ['eligible', `✓ Eligible (${rows.filter((r) => rowBucket(r) === 'eligible').length})`],
                ['improvable', `⚠ Not-Eligible Yet (${rows.filter((r) => rowBucket(r) === 'improvable').length})`],
                ['ineligible', `✗ Age-Ineligible (${rows.filter((r) => rowBucket(r) === 'ineligible').length})`],
                ['needs_resume', `Resume Needed (${rows.filter((r) => rowBucket(r) === 'needs_resume').length})`],
              ].map(([key, label]) => (
                <button key={key} onClick={() => setRowFilter(key)}
                  className={`text-[11px] px-2.5 py-1 rounded-full border transition-colors ${
                    rowFilter === key ? 'bg-teal-600 text-white border-teal-600' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'}`}
                  data-testid={`row-filter-${key}`}>{label}</button>
              ))}
              <div className="ml-auto flex items-center gap-1.5">
                <span className="text-[10px] text-slate-500">Assign shown to:</span>
                <Select onValueChange={(v) => assignConsultant(displayRows.map((r) => r.id), v === '__default__' ? '' : v)}>
                  <SelectTrigger className="h-7 text-[10px] w-[170px]" data-testid="assign-all-consultant"><SelectValue placeholder="Choose mailbox" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__default__" className="text-[11px]">Default ({emailCfg?.default_sender || 'info@leamss.com'})</SelectItem>
                    {activeSenders.map((s) => <SelectItem key={s.email} value={s.email} className="text-[11px]">{s.name} · {s.email}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={() => setShowMailAccounts(true)} data-testid="open-mail-accounts">
                  <Mail className="h-3 w-3 mr-1" />Mail Accounts
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={() => setShowEmailSettings(true)} data-testid="open-email-settings">
                  <FileText className="h-3 w-3 mr-1" />Email Settings
                </Button>
                <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={() => navigate('/sales/email-templates')} data-testid="open-email-templates">
                  <LayoutTemplate className="h-3 w-3 mr-1" />Templates
                </Button>
              </div>
            </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 text-slate-600">
                  <tr>
                    <th className="p-2 text-left">#</th>
                    <th className="p-2 text-left">Client</th>
                    <th className="p-2 text-left">ANZSCO</th>
                    <th className="p-2">Age</th>
                    <th className="p-2">189</th>
                    <th className="p-2">190</th>
                    <th className="p-2">491</th>
                    <th className="p-2">Status</th>
                    <th className="p-2">Consultant (sends from)</th>
                    <th className="p-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {displayRows.map((r) => (
                    <tr key={r.id} className="border-t hover:bg-slate-50" data-testid={`bulk-row-${r.row_index}`}>
                      <td className="p-2 text-slate-400">{r.row_index}</td>
                      <td className="p-2">
                        <p className="font-semibold">{r.parsed?.name}</p>
                        <p className="text-[10px] text-slate-400">{r.parsed?.email}</p>
                      </td>
                      <td className="p-2">
                        <p className="font-mono">{r.parsed?.anzsco_code || '—'}</p>
                        <p className="text-[10px] text-slate-400">{r.parsed?.occupation_title || ''}</p>
                        {r.parsed?.anzsco_source === 'ai' && (
                          <TooltipProvider delayDuration={100}>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`inline-flex items-center gap-0.5 text-[9px] px-1 py-0.5 rounded mt-0.5 cursor-help ${
                                  r.parsed?.ai_reviewed ? 'bg-emerald-100 text-emerald-700'
                                  : r.parsed?.ai_confidence === 'high' ? 'bg-violet-100 text-violet-700'
                                  : r.parsed?.ai_confidence === 'medium' ? 'bg-amber-100 text-amber-700'
                                  : 'bg-rose-100 text-rose-700'}`} data-testid={`ai-badge-${r.row_index}`}>
                                  {r.parsed?.ai_reviewed
                                    ? <><Check className="h-2.5 w-2.5" />AI · confirmed</>
                                    : <><Sparkles className="h-2.5 w-2.5" />AI · {r.parsed?.ai_confidence || 'low'} · review</>}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs" data-testid={`ai-tooltip-${r.row_index}`}>
                                <p className="text-[11px] font-semibold mb-0.5">Why AI chose {r.parsed?.anzsco_code}</p>
                                <p className="text-[11px]">{r.parsed?.ai_reasoning || 'Matched from the candidate\'s resume.'}</p>
                                {(r.parsed?.ai_alternatives || []).length > 0 && (
                                  <p className="text-[10px] text-slate-300 mt-1">Alternatives: {(r.parsed.ai_alternatives).map((a) => `${a.code} ${a.title || ''}`).join(', ')}</p>
                                )}
                                {(r.parsed?.ai_filled_fields || []).length > 0 && (
                                  <p className="text-[10px] text-slate-300 mt-1">AI-filled: {r.parsed.ai_filled_fields.join(', ')}</p>
                                )}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </td>
                      <td className="p-2 text-center">{r.parsed?.age ?? '—'}</td>
                      <td className="p-2 text-center font-bold">{r.points?.['189'] ?? '—'}</td>
                      <td className="p-2 text-center font-bold text-teal-700">{r.points?.['190'] ?? '—'}</td>
                      <td className="p-2 text-center font-bold text-teal-800">{r.points?.['491'] ?? '—'}</td>
                      <td className="p-2 text-center">
                        {statusBadge(r.status)}
                        {r.status === 'generated' && r.eligibility?.verdict && (
                          <p className={`text-[9px] font-semibold mt-0.5 inline-block px-1.5 py-0.5 rounded ${
                            r.eligibility.verdict === 'eligible' ? 'bg-emerald-100 text-emerald-700'
                            : r.eligibility.verdict === 'improvable' ? 'bg-amber-100 text-amber-700'
                            : 'bg-rose-100 text-rose-700'}`} data-testid={`eligibility-badge-${r.row_index}`}>
                            {r.eligibility.verdict === 'eligible' ? '✓ Eligible'
                              : r.eligibility.verdict === 'improvable' ? '⚠ Not eligible yet'
                              : '✗ Age-ineligible'}
                          </p>
                        )}
                        {r.email_status === 'sent' && (
                          <p className="text-[9px] text-emerald-600 mt-0.5" data-testid={`email-sent-${r.row_index}`}>✓ emailed</p>
                        )}
                        {r.email_status === 'failed' && (
                          <p className="text-[9px] text-rose-500 mt-0.5" title={r.email_error} data-testid={`email-failed-${r.row_index}`}>email failed</p>
                        )}
                        {r.status === 'error' && (
                          <p className="text-[9px] text-rose-500 mt-0.5 max-w-[200px]">{(r.errors || []).join('; ')}</p>
                        )}
                        {r.status === 'needs_ai' && r.ai_error && (
                          <div className="mt-1 max-w-[220px] mx-auto" data-testid={`row-ai-error-${r.row_index}`}>
                            <span className="inline-block text-[9px] font-semibold text-rose-600 bg-rose-50 border border-rose-200 rounded px-1.5 py-0.5">
                              {(AI_FAIL_META[categorizeAiError(r.ai_error)] || AI_FAIL_META.other).label}
                            </span>
                            <p className="text-[9px] text-slate-500 mt-0.5 leading-tight">{r.ai_error}</p>
                          </div>
                        )}
                      </td>
                      <td className="p-2">
                        <Select value={r.parsed?.consultant_email || '__default__'} onValueChange={(v) => assignConsultant([r.id], v === '__default__' ? '' : v)}>
                          <SelectTrigger className="h-7 text-[10px] w-[160px]" data-testid={`consultant-select-${r.row_index}`}><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="__default__" className="text-[11px]">Default ({emailCfg?.default_sender || 'info@leamss.com'})</SelectItem>
                            {activeSenders.map((s) => <SelectItem key={s.email} value={s.email} className="text-[11px]">{s.name} · {s.email}</SelectItem>)}
                            {r.parsed?.consultant_email && !activeSenders.some((s) => s.email === r.parsed.consultant_email) && (
                              <SelectItem value={r.parsed.consultant_email} className="text-[11px]">{r.parsed.consultant_email}</SelectItem>
                            )}
                          </SelectContent>
                        </Select>
                      </td>
                      <td className="p-2">
                        <div className="flex gap-1 justify-center">
                          {r.parsed?.resume_link && (
                            <TooltipProvider delayDuration={100}>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button size="sm" variant="ghost" className="h-7 px-2 text-violet-600 hover:text-violet-700 hover:bg-violet-50"
                                    onClick={() => openResume(r.parsed.resume_link)} data-testid={`view-resume-${r.row_index}`}>
                                    <FileUser className="h-3.5 w-3.5" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent><p className="text-[11px]">View client resume</p></TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => setEditRow(r)} data-testid={`edit-row-${r.row_index}`}>
                            <Edit3 className="h-3.5 w-3.5" />
                          </Button>
                          {r.status === 'generated' && (
                            <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => viewPdf(r)} data-testid={`view-row-${r.row_index}`}>
                              <FileText className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          {r.parsed?.email && (
                            <>
                              <TooltipProvider delayDuration={100}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button size="sm" variant="ghost" className="h-7 px-2 text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 disabled:opacity-40"
                                      disabled={emailingRow === r.id || !emailCfg?.configured}
                                      onClick={() => emailRow(r)} data-testid={`email-row-${r.row_index}`}>
                                      {emailingRow === r.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent><p className="text-[11px]">{emailCfg?.configured
                                    ? `Send ${rowBucket(r) === 'needs_resume' ? 'resume request' : rowBucket(r) === 'eligible' ? 'report' : 'not-eligible report'} to ${r.parsed.email}`
                                    : 'Set up Gmail first (see banner)'}</p></TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button size="sm" variant="ghost" className="h-7 px-1.5" data-testid={`row-actions-${r.row_index}`}>
                                    <MoreVertical className="h-3.5 w-3.5" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-56">
                                  <DropdownMenuLabel className="text-[11px]">Send email</DropdownMenuLabel>
                                  <DropdownMenuItem disabled={!emailCfg?.configured} onClick={() => emailRow(r)} data-testid={`send-auto-${r.row_index}`}>
                                    <Send className="h-3.5 w-3.5 mr-2" />Send (Auto)
                                  </DropdownMenuItem>
                                  {templates.length > 0 && (
                                    <DropdownMenuSub>
                                      <DropdownMenuSubTrigger disabled={!emailCfg?.configured}>
                                        <LayoutTemplate className="h-3.5 w-3.5 mr-2" />Send with template
                                      </DropdownMenuSubTrigger>
                                      <DropdownMenuPortal>
                                        <DropdownMenuSubContent className="w-64">
                                          {templates.map((t) => (
                                            <DropdownMenuItem key={t.id} onClick={() => emailRow(r, t.id)} data-testid={`send-tpl-${t.id}-${r.row_index}`}>
                                              <span className="truncate">{t.name}</span>
                                            </DropdownMenuItem>
                                          ))}
                                        </DropdownMenuSubContent>
                                      </DropdownMenuPortal>
                                    </DropdownMenuSub>
                                  )}
                                  {r.status === 'generated' && (
                                    <>
                                      <DropdownMenuSeparator />
                                      <DropdownMenuLabel className="text-[11px]">Eligibility</DropdownMenuLabel>
                                      <DropdownMenuItem onClick={() => setMarkRow(r)} data-testid={`mark-not-eligible-${r.row_index}`}>
                                        <Ban className="h-3.5 w-3.5 mr-2 text-rose-600" />Mark Not-Eligible…
                                      </DropdownMenuItem>
                                      {r.manual_eligibility && (
                                        <DropdownMenuItem onClick={() => markEligibility(r, 'auto')} data-testid={`reset-eligibility-${r.row_index}`}>
                                          <RotateCcw className="h-3.5 w-3.5 mr-2" />Reset to Auto
                                        </DropdownMenuItem>
                                      )}
                                    </>
                                  )}
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {displayRows.length === 0 && (
                    <tr><td colSpan={10} className="p-6 text-center text-slate-400 text-[11px]">No clients match this filter.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Past batches */}
        {!batch && batches.length > 0 && (
          <Card className="p-4" data-testid="past-batches-card">
            <h2 className="text-base font-bold mb-2">Recent Batches</h2>
            <div className="space-y-1">
              {batches.map((b) => (
                <button key={b.id} onClick={() => loadBatch(b.id)} className="w-full flex items-center justify-between p-2 rounded hover:bg-slate-50 text-left" data-testid={`batch-${b.id}`}>
                  <span className="text-sm font-medium">{b.name}</span>
                  <span className="text-[11px] text-slate-500">{b.generated}/{b.valid} generated · {b.status}</span>
                </button>
              ))}
            </div>
          </Card>
        )}
      </div>

      {editRow && (
        <EditRowDialog row={editRow} headers={headers} senders={activeSenders} defaultSender={emailCfg?.default_sender}
          onClose={() => setEditRow(null)}
          onSaved={async () => { setEditRow(null); await loadBatch(batch.id); }} />
      )}

      {markRow && (
        <MarkNotEligibleDialog row={markRow} onClose={() => setMarkRow(null)}
          onConfirm={async (kind, reason) => { await markEligibility(markRow, kind, reason); setMarkRow(null); }} />
      )}

      {showMailAccounts && (
        <MailAccountsDialog headers={headers} senders={emailCfg?.senders || []} domain={emailCfg?.domain}
          onClose={() => setShowMailAccounts(false)}
          onChanged={refreshEmailCfg} />
      )}

      {showEmailSettings && (
        <EmailSettingsDialog headers={headers} onClose={() => setShowEmailSettings(false)} />
      )}

      {showEmailPreview && (
        <EmailPreviewDialog batchId={batch.id} headers={headers}
          onClose={() => setShowEmailPreview(false)}
          onConfirmed={() => loadBatch(batch.id)} />
      )}

      {showEmailSummary && (
        <EmailSummaryDialog batchId={batch.id} headers={headers}
          onClose={() => setShowEmailSummary(false)} />
      )}

      {showDefaults && batch && (
        <BatchDefaultsDialog
          batch={batch}
          headers={headers}
          onClose={() => setShowDefaults(false)}
          onApplied={async () => {
            setShowDefaults(false);
            setGenerating(true);
            await loadBatch(batch.id);
          }}
        />
      )}

      {showAiReview && batch && (
        <AiReviewDialog
          batch={batch}
          rows={rows}
          headers={headers}
          onClose={() => setShowAiReview(false)}
          onChanged={async () => { await loadBatch(batch.id); }}
          onEdit={(row) => { setShowAiReview(false); setEditRow(row); }}
        />
      )}
    </div>
  );
}

function EditRowDialog({ row, headers, senders = [], defaultSender, onClose, onSaved }) {
  const p = row.parsed || {};
  const [form, setForm] = useState({
    anzsco_code: p.anzsco_code || '',
    occupation_title: p.occupation_title || '',
    age: p.age ?? '',
    qualification: p.qualification || 'bachelor',
    experience_total: p.experience_total ?? '',
    experience_au: p.experience_au ?? 0,
    marital_status: p.marital_status || 'single',
    state_nominated: !!p.state_nominated,
    partner_skill: p.partner_skill || ((p.marital_status === 'married' || p.marital_status === 'de_facto') ? 'english_only' : 'none'),
    au_extras: {
      australian_study_2_years: !!(p.au_extras || {}).australian_study_2_years,
      specialist_education_stem_au: !!(p.au_extras || {}).specialist_education_stem_au,
      professional_year_completed: !!(p.au_extras || {}).professional_year_completed,
      naati_accredited: !!(p.au_extras || {}).naati_accredited,
      regional_study_au: !!(p.au_extras || {}).regional_study_au,
    },
    eng: { ...(p.english || { overall: 8, listening: 8, reading: 8, writing: 8, speaking: 8 }) },
  });
  const [saving, setSaving] = useState(false);
  const [hideEoi, setHideEoi] = useState(!!p.hide_eoi);
  const [consultantEmail, setConsultantEmail] = useState(p.consultant_email || '');
  const [suggestions, setSuggestions] = useState(() => {
    const alts = (p.ai_alternatives || []).map((a) => ({ code: String(a.code), title: a.title, confidence: a.confidence }));
    if (p.anzsco_code && p.anzsco_source === 'ai') {
      return [{ code: String(p.anzsco_code), title: p.occupation_title, confidence: p.ai_confidence, current: true }, ...alts];
    }
    return alts;
  });
  const [suggesting, setSuggesting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [occQuery, setOccQuery] = useState('');
  const [occResults, setOccResults] = useState([]);
  const [occSearching, setOccSearching] = useState(false);
  const [uploadedFileId, setUploadedFileId] = useState(p.resume_file_id || null);
  const [uploadedName, setUploadedName] = useState(p.resume_filename || null);
  const [reportAlts, setReportAlts] = useState(() => {
    if (Array.isArray(p.report_alt_codes)) return p.report_alt_codes.map((a) => ({ code: String(a.code), title: a.title }));
    return (p.ai_alternatives || [])
      .filter((a) => String(a.code) !== String(p.anzsco_code))
      .slice(0, 2).map((a) => ({ code: String(a.code), title: a.title }));
  });
  const fileRef = useRef(null);

  const applyCode = (code, title) => {
    const c = String(code);
    setForm((f) => ({ ...f, anzsco_code: c, occupation_title: title || f.occupation_title }));
    setReportAlts((prev) => prev.filter((a) => a.code !== c));
    toast.success(`Primary code set to ${c}${title ? ' · ' + title : ''}`);
  };

  // Swap: make an existing alternate the new primary; the old primary drops into alternates.
  const makePrimary = (code, title) => {
    const c = String(code);
    const oldCode = String(form.anzsco_code || '');
    const oldTitle = form.occupation_title || '';
    setForm((f) => ({ ...f, anzsco_code: c, occupation_title: title || f.occupation_title }));
    setReportAlts((prev) => {
      const withoutNew = prev.filter((a) => a.code !== c);
      if (oldCode && oldCode !== c && withoutNew.length < 2 && !withoutNew.some((a) => a.code === oldCode)) {
        return [...withoutNew, { code: oldCode, title: oldTitle }];
      }
      return withoutNew;
    });
    toast.success(`Primary set to ${c}${title ? ' · ' + title : ''}`);
  };

  const toggleAlt = (code, title) => {
    const c = String(code);
    if (c === String(form.anzsco_code)) { toast.info('That is the primary code'); return; }
    setReportAlts((prev) => {
      if (prev.some((a) => a.code === c)) return prev.filter((a) => a.code !== c);
      if (prev.length >= 2) { toast.info('Max 2 alternate pathways on the report'); return prev; }
      toast.success(`Added ${c} as an alternate pathway`);
      return [...prev, { code: c, title }];
    });
  };

  const runSuggest = async () => {
    setSuggesting(true);
    try {
      const r = await axios.post(`${API}/bulk-assessments/row/${row.id}/suggest-codes`, {}, { headers });
      setSuggestions(r.data.suggestions || []);
      if (!(r.data.suggestions || []).length) toast.info('No confident code suggestions found');
    } catch (e) {
      toast.error(formatApiError(e, 'Could not get suggestions'));
    } finally { setSuggesting(false); }
  };

  const uploadResume = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/bulk-assessments/row/${row.id}/upload-resume`, fd,
        { headers: { ...headers, 'Content-Type': 'multipart/form-data' } });
      const rp = (r.data.row || {}).parsed || {};
      setUploadedFileId(rp.resume_file_id || null);
      setUploadedName(rp.resume_filename || file.name);
      setSuggestions(r.data.alternatives?.length
        ? [...(r.data.detected_code ? [{ code: String(r.data.detected_code), title: rp.occupation_title, confidence: rp.ai_confidence, current: true }] : []), ...r.data.alternatives.map((a) => ({ code: String(a.code), title: a.title, confidence: a.confidence }))]
        : suggestions);
      // Pull any newly filled fields into the form
      setForm((f) => ({
        ...f,
        anzsco_code: r.data.detected_code ? String(r.data.detected_code) : f.anzsco_code,
        age: rp.age ?? f.age,
        qualification: rp.qualification || f.qualification,
        experience_total: rp.experience_total ?? f.experience_total,
      }));
      if (r.data.ok && r.data.detected_code) toast.success(`Resume read — detected ${r.data.detected_code}`);
      else toast.warning(r.data.ai_error || 'Resume uploaded but no code detected — pick one below');
    } catch (e) {
      toast.error(formatApiError(e, 'Resume upload failed'));
    } finally { setUploading(false); if (fileRef.current) fileRef.current.value = ''; }
  };

  const viewResume = async () => {
    if (uploadedFileId) {
      try {
        const r = await axios.get(`${API}/bulk-assessments/row/${row.id}/resume-file`, { headers, responseType: 'blob' });
        window.open(URL.createObjectURL(r.data), '_blank', 'noopener,noreferrer');
      } catch (e) { toast.error('Could not open uploaded resume'); }
    } else if (p.resume_link) {
      openResume(p.resume_link);
    }
  };

  useEffect(() => {
    const q = occQuery.trim();
    if (q.length < 2) { setOccResults([]); return; }
    const t = setTimeout(async () => {
      setOccSearching(true);
      try {
        const r = await axios.get(`${API}/sales/occupations/search?q=${encodeURIComponent(q)}&country=AU`, { headers });
        setOccResults((r.data.items || []).slice(0, 6));
      } catch (e) { setOccResults([]); } finally { setOccSearching(false); }
    }, 350);
    return () => clearTimeout(t);
  }, [occQuery]);
  const [cost, setCost] = useState(() => {
    const ce = row.cost_estimator || {};
    return {
      items: (ce.items || []).map((i) => ({ ...i })),
      packages: (ce.service_packages || []).map((p) => ({ ...p })),
    };
  });
  const setItem = (i, f, v) => setCost((c) => ({ ...c, items: c.items.map((it, idx) => idx === i ? { ...it, [f]: v } : it) }));
  const addItem = () => setCost((c) => ({ ...c, items: [...c.items, { category: 'Other', label: '', amount: 0, currency: 'INR', is_editable: true }] }));
  const removeItem = (i) => setCost((c) => ({ ...c, items: c.items.filter((_, idx) => idx !== i) }));
  const setPkg = (i, f, v) => setCost((c) => ({
    ...c,
    packages: c.packages.map((p, idx) => {
      if (idx !== i) return p;
      const next = { ...p, [f]: v };
      // Keep the PDF breakdown consistent: Total = Professional Fee − Discount + GST
      if (['professional_fee', 'discount', 'gst'].includes(f)) {
        const fee = parseFloat(f === 'professional_fee' ? v : next.professional_fee) || 0;
        const disc = parseFloat(f === 'discount' ? v : next.discount) || 0;
        const gst = parseFloat(f === 'gst' ? v : next.gst) || 0;
        next.total = Math.max(0, fee - disc + gst);
      }
      return next;
    }),
  }));

  const save = async () => {
    setSaving(true);
    try {
      const tbc = {};
      cost.items.forEach((it) => { const c = it.currency || 'INR'; tbc[c] = (tbc[c] || 0) + (Number(it.amount) || 0); });
      const payload = {
        anzsco_code: form.anzsco_code,
        age: form.age === '' ? null : Number(form.age),
        qualification: form.qualification,
        experience_total: form.experience_total === '' ? null : Number(form.experience_total),
        experience_au: Number(form.experience_au) || 0,
        marital_status: form.marital_status,
        state_nominated: form.state_nominated,
        report_alt_codes: reportAlts.map((a) => a.code),
        hide_eoi: hideEoi,
        consultant_email: consultantEmail,
        partner_skill: (form.marital_status === 'married' || form.marital_status === 'de_facto') ? form.partner_skill : null,
        au_extras: form.au_extras,
        english: Object.fromEntries(Object.entries(form.eng).map(([k, v]) => [k, Number(v)])),
        cost_estimator: {
          currency: 'INR',
          items: cost.items.map((it) => ({ ...it, amount: Number(it.amount) || 0 })),
          service_packages: cost.packages.map((p) => ({
            ...p,
            professional_fee: Number(p.professional_fee) || 0,
            discount: Number(p.discount) || 0,
            gst: Number(p.gst) || 0,
            total: pkgTotal(p),
          })),
          total_by_currency: tbc,
          notes: (row.cost_estimator && row.cost_estimator.notes) || 'Edited per client',
        },
      };
      await axios.patch(`${API}/bulk-assessments/row/${row.id}`, payload, { headers });
      toast.success('Client updated & report regenerated');
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Update failed'));
    } finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[88vh] overflow-y-auto" data-testid="edit-row-dialog">
        <DialogHeader><DialogTitle>Edit · {p.name}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          {/* Resume: view (uploaded or linked) + manual upload */}
          <div className="flex items-stretch gap-2">
            {(p.resume_link || uploadedFileId) ? (
              <button type="button" onClick={viewResume}
                className="flex-1 flex items-center justify-between gap-2 px-3 py-2 rounded-lg border border-violet-200 bg-violet-50 hover:bg-violet-100 transition-colors"
                data-testid="edit-view-resume">
                <span className="flex items-center gap-2 text-[12px] font-semibold text-violet-700">
                  <FileUser className="h-4 w-4" />{uploadedFileId ? (uploadedName || 'Uploaded resume') : "Review client's resume"}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-violet-600">Open <ExternalLink className="h-3.5 w-3.5" /></span>
              </button>
            ) : (
              <div className="flex-1 px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-[11px] text-slate-400 flex items-center gap-2" data-testid="edit-no-resume">
                <FileUser className="h-4 w-4" />No resume link in the Excel — upload one →
              </div>
            )}
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp" className="hidden"
              onChange={(e) => uploadResume(e.target.files?.[0])} data-testid="edit-resume-file-input" />
            <Button type="button" variant="outline" disabled={uploading}
              className="border-violet-300 text-violet-700 hover:bg-violet-50 shrink-0"
              onClick={() => fileRef.current?.click()} data-testid="edit-upload-resume-btn">
              {uploading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}
              {uploading ? 'Reading…' : 'Upload resume'}
            </Button>
          </div>

          {/* ANZSCO Code Helper: AI suggestions, keyword search, alternatives */}
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-2.5 space-y-2" data-testid="code-helper">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold text-slate-700 flex items-center gap-1"><Sparkles className="h-3.5 w-3.5 text-violet-600" />ANZSCO Code Helper — pick the best match</p>
              <Button type="button" size="sm" variant="ghost" disabled={suggesting}
                className="h-6 px-2 text-[11px] text-violet-700 hover:bg-violet-100"
                onClick={runSuggest} data-testid="suggest-codes-btn">
                {suggesting ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Sparkles className="h-3 w-3 mr-1" />}Suggest from resume
              </Button>
            </div>

            {suggestions.length > 0 && (
              <div className="flex flex-wrap gap-1.5" data-testid="code-suggestions">
                {suggestions.map((s, i) => {
                  const isPrimary = String(form.anzsco_code) === String(s.code);
                  const onReport = reportAlts.some((a) => a.code === String(s.code));
                  return (
                    <div key={s.code + i} className={`flex items-center rounded-md border text-[11px] overflow-hidden ${isPrimary ? 'border-violet-500 bg-violet-100' : 'border-slate-200 bg-white'}`}>
                      <button type="button" onClick={() => applyCode(s.code, s.title)}
                        className="text-left px-2 py-1 hover:bg-violet-50" data-testid={`code-suggestion-${s.code}`}>
                        <span className="font-semibold">{s.code}</span> {s.title || ''}
                        {s.confidence && <span className={`ml-1 text-[9px] uppercase ${s.confidence === 'high' ? 'text-emerald-600' : s.confidence === 'medium' ? 'text-amber-600' : 'text-slate-400'}`}>{s.confidence}</span>}
                        {isPrimary && <span className="ml-1 text-[9px] text-violet-600 font-semibold">• PRIMARY</span>}
                      </button>
                      {!isPrimary && (
                        <button type="button" onClick={() => toggleAlt(s.code, s.title)}
                          title={onReport ? 'On report — click to remove' : 'Add to report as alternate'}
                          className={`px-1.5 self-stretch border-l ${onReport ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : 'bg-slate-50 text-slate-400 border-slate-200 hover:text-violet-600'}`}
                          data-testid={`alt-toggle-${s.code}`}>
                          {onReport ? <Check className="h-3 w-3" /> : '+'}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            <div className="relative">
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-md border border-slate-200 bg-white">
                <Search className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                <input value={occQuery} onChange={(e) => setOccQuery(e.target.value)}
                  placeholder="Search another occupation (e.g. ACS, developer, accountant)…"
                  className="flex-1 text-[11px] outline-none bg-transparent" data-testid="occ-search-input" />
                {occSearching && <Loader2 className="h-3 w-3 animate-spin text-slate-400" />}
              </div>
              {occResults.length > 0 && (
                <div className="mt-1 max-h-40 overflow-y-auto rounded-md border border-slate-200 bg-white shadow-sm" data-testid="occ-search-results">
                  {occResults.map((o) => (
                    <div key={o.code} className="flex items-center border-b border-slate-100 last:border-0">
                      <button type="button" onClick={() => { applyCode(o.code, o.title); setOccQuery(''); setOccResults([]); }}
                        className="flex-1 text-left px-2 py-1.5 text-[11px] hover:bg-violet-50" data-testid={`occ-result-${o.code}`}>
                        <span className="font-semibold">{o.code}</span> {o.title}
                        {o.assessing_body && <span className="text-slate-400"> · {o.assessing_body}</span>}
                      </button>
                      <button type="button" onClick={() => toggleAlt(o.code, o.title)}
                        title="Add to report as alternate" className="px-2 py-1.5 text-[11px] text-slate-400 hover:text-violet-600 border-l border-slate-100"
                        data-testid={`occ-alt-toggle-${o.code}`}>+report</button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Report pathways: primary + selected alternates shown on the client's report */}
            <div className="rounded-md bg-white border border-slate-200 p-2" data-testid="report-pathways">
              <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1">On the report — occupation pathways</p>
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-600 text-white text-[10px] font-semibold" data-testid="report-primary">
                  {form.anzsco_code || '—'} <span className="opacity-80">Primary</span>
                </span>
                {reportAlts.map((a) => (
                  <span key={a.code} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[10px]" data-testid={`report-alt-${a.code}`}>
                    {a.code} <span className="text-slate-500">{(a.title || '').slice(0, 22)}</span>
                    <button type="button" onClick={() => makePrimary(a.code, a.title)} title="Make this the primary code"
                      className="text-slate-400 hover:text-violet-600" data-testid={`report-alt-makeprimary-${a.code}`}>
                      <Star className="h-3 w-3" />
                    </button>
                    <button type="button" onClick={() => toggleAlt(a.code, a.title)} title="Remove from report"
                      className="text-slate-400 hover:text-rose-600" data-testid={`report-alt-remove-${a.code}`}>
                      <XCircle className="h-3 w-3" />
                    </button>
                  </span>
                ))}
                {reportAlts.length === 0 && <span className="text-[10px] text-slate-400">No alternates — tap "+" on a code above to add up to 2.</span>}
              </div>
              {reportAlts.length > 0 && (
                <p className="text-[9px] text-slate-400 mt-1 flex items-center gap-1">
                  <Star className="h-2.5 w-2.5" /> = make primary · <XCircle className="h-2.5 w-2.5" /> = remove from report
                </p>
              )}
            </div>
          </div>

          <p className="text-[11px] text-slate-500">Changing the ANZSCO code recomputes points, occupation deep-dive, EOI backlog & eligibility.</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">ANZSCO Code</Label>
              <Input value={form.anzsco_code} onChange={(e) => setForm({ ...form, anzsco_code: e.target.value })} data-testid="edit-anzsco" />
            </div>
            <div>
              <Label className="text-xs">Age</Label>
              <Input type="number" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} data-testid="edit-age" />
            </div>
            <div>
              <Label className="text-xs">Qualification</Label>
              <Select value={form.qualification} onValueChange={(v) => setForm({ ...form, qualification: v })}>
                <SelectTrigger className="h-9" data-testid="edit-qual"><SelectValue /></SelectTrigger>
                <SelectContent>{QUALS.map((q) => <SelectItem key={q} value={q}>{q === 'high_school' ? 'High School' : q.charAt(0).toUpperCase() + q.slice(1)}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Marital Status</Label>
              <Select value={form.marital_status} onValueChange={(v) => setForm({ ...form, marital_status: v })}>
                <SelectTrigger className="h-9" data-testid="edit-marital"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="single">Single</SelectItem><SelectItem value="married">Married</SelectItem><SelectItem value="de_facto">De-facto</SelectItem></SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Total Experience (yrs)</Label>
              <Input type="number" value={form.experience_total} onChange={(e) => setForm({ ...form, experience_total: e.target.value })} data-testid="edit-exp" />
            </div>
            <div>
              <Label className="text-xs">Australian Experience (yrs)</Label>
              <Input type="number" value={form.experience_au} onChange={(e) => setForm({ ...form, experience_au: e.target.value })} data-testid="edit-exp-au" />
            </div>
          </div>
          <div>
            <Label className="text-xs">English (IELTS bands)</Label>
            <div className="grid grid-cols-5 gap-1.5">
              {['overall', 'listening', 'reading', 'writing', 'speaking'].map((b) => (
                <div key={b}>
                  <p className="text-[9px] text-slate-400 uppercase text-center">{b[0]}</p>
                  <Input type="number" step="0.5" value={form.eng[b]}
                    onChange={(e) => setForm({ ...form, eng: { ...form.eng, [b]: e.target.value } })}
                    className="h-8 text-center text-xs" data-testid={`edit-eng-${b}`} />
                </div>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <Switch checked={form.state_nominated} onCheckedChange={(v) => setForm({ ...form, state_nominated: v })} data-testid="edit-state-nom" />
            Has State / Regional Nomination (adds real +5 / +15)
          </label>

          <label className="flex items-center gap-2 text-xs cursor-pointer rounded-md bg-amber-50 border border-amber-200 px-2.5 py-2" data-testid="edit-hide-eoi-label">
            <Switch checked={hideEoi} onCheckedChange={setHideEoi} data-testid="edit-hide-eoi" />
            <span className="flex-1 text-amber-900">Hide EOI backlog tables on <b>this client's</b> report (primary + alternates)</span>
          </label>

          <div className="rounded-md bg-indigo-50 border border-indigo-200 px-2.5 py-2 space-y-1" data-testid="edit-consultant-box">
            <label className="text-xs font-semibold text-indigo-900 flex items-center gap-1"><Mail className="h-3.5 w-3.5" />Email report from (consultant mailbox)</label>
            <Select value={consultantEmail || '__default__'} onValueChange={(v) => setConsultantEmail(v === '__default__' ? '' : v)}>
              <SelectTrigger className="h-8 text-xs bg-white" data-testid="edit-consultant-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__default__" className="text-xs">Default ({defaultSender || 'info@leamss.com'})</SelectItem>
                {senders.map((s) => <SelectItem key={s.email} value={s.email} className="text-xs">{s.name} · {s.email}</SelectItem>)}
                {consultantEmail && !senders.some((s) => s.email === consultantEmail) && (
                  <SelectItem value={consultantEmail} className="text-xs">{consultantEmail}</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Additional Factors — partner skills + AU bonus points (per-client, live recalc on save) */}
          <div className="border-t pt-3 space-y-2.5" data-testid="edit-factors-section">
            <div className="text-sm font-bold text-teal-900 flex items-center gap-2">Additional Factors
              <Badge className="bg-slate-800 text-white text-[9px]">recalc on save</Badge>
            </div>

            {/* Partner skills */}
            {(form.marital_status === 'married' || form.marital_status === 'de_facto') ? (
              <div>
                <Label className="text-xs">Partner Skills</Label>
                <Select value={form.partner_skill} onValueChange={(v) => setForm({ ...form, partner_skill: v })}>
                  <SelectTrigger className="h-9" data-testid="edit-partner-skill"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pr_citizen">Partner is AU PR / Citizen (+10)</SelectItem>
                    <SelectItem value="skilled">Skilled partner — age&lt;45 + competent English (+10)</SelectItem>
                    <SelectItem value="english_only">Competent English only (+5)</SelectItem>
                    <SelectItem value="none">Partner not skilled (0)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div className="text-[11px] text-emerald-700 bg-emerald-50 rounded px-2 py-1.5" data-testid="edit-single-note">
                Single / Divorced / Widowed applicant — <strong>+10 partner-skills bonus</strong> applied automatically (AU rule).
              </div>
            )}

            {/* Experience visibility */}
            <div className="text-[11px] text-slate-500" data-testid="edit-overseas-note">
              Overseas experience (auto): <strong>{Math.max(0, (Number(form.experience_total) || 0) - (Number(form.experience_au) || 0))} yrs</strong>
              {' '}= Total {Number(form.experience_total) || 0} − Australian {Number(form.experience_au) || 0}
            </div>

            {/* AU bonus toggles */}
            <div className="bg-indigo-50/60 rounded-lg p-2.5 space-y-1.5" data-testid="edit-bonus-points">
              <p className="text-[10px] font-bold text-indigo-700 uppercase tracking-wide">Australia · Bonus Points</p>
              {[
                ['australian_study_2_years', 'Australian Study Requirement (2+ yrs AU study)', '+5'],
                ['specialist_education_stem_au', "Specialist Education (STEM Master's/PhD at AU institution)", '+10'],
                ['professional_year_completed', 'Professional Year Programme (PY) completed', '+5'],
                ['naati_accredited', 'NAATI Accredited (Paraprofessional+)', '+5'],
                ['regional_study_au', 'Regional Study (in regional Australia)', '+5'],
              ].map(([key, label, pts]) => (
                <label key={key} className="flex items-center gap-2 text-xs cursor-pointer">
                  <Switch checked={form.au_extras[key]}
                    onCheckedChange={(v) => setForm({ ...form, au_extras: { ...form.au_extras, [key]: v } })}
                    data-testid={`edit-bonus-${key}`} />
                  <span className="flex-1 text-indigo-900">{label}</span>
                  <Badge className="bg-slate-900 text-white text-[9px]">{pts}</Badge>
                </label>
              ))}
            </div>
          </div>

          {/* Cost & Investment editor */}
          <div className="border-t pt-3 space-y-2" data-testid="edit-cost-section">
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-teal-900">Cost & Investment</p>
              <Button size="sm" variant="outline" className="h-7 text-[11px]" onClick={addItem} data-testid="cost-add-item">+ Add line</Button>
            </div>
            <div className="space-y-1.5">
              {cost.items.map((it, i) => (
                <div key={i} className="flex items-center gap-1.5" data-testid={`cost-item-${i}`}>
                  <select value={it.category || 'Other'} onChange={(e) => setItem(i, 'category', e.target.value)} className="h-8 text-[11px] border rounded px-1 w-32" data-testid={`cost-category-${i}`}>
                    {COST_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <Input value={it.label} onChange={(e) => setItem(i, 'label', e.target.value)} placeholder="Label" className="h-8 text-xs flex-1" data-testid={`cost-label-${i}`} />
                  <Input type="number" value={it.amount} onChange={(e) => setItem(i, 'amount', e.target.value)} className="h-8 text-xs w-24" data-testid={`cost-amount-${i}`} />
                  <select value={it.currency || 'INR'} onChange={(e) => setItem(i, 'currency', e.target.value)} className="h-8 text-xs border rounded px-1" data-testid={`cost-ccy-${i}`}>
                    <option>INR</option><option>AUD</option>
                  </select>
                  <button onClick={() => removeItem(i)} className="text-rose-500 px-1" data-testid={`cost-remove-${i}`}>✕</button>
                </div>
              ))}
              {cost.items.length === 0 && <p className="text-[11px] text-slate-400">No cost lines. Click "+ Add line".</p>}
            </div>
          </div>

          {/* LEAMSS Packages editor */}
          {cost.packages.length > 0 && (
            <div className="border-t pt-3 space-y-2" data-testid="edit-packages-section">
              <p className="text-sm font-bold text-teal-900">LEAMSS Service Packages <span className="text-[10px] font-normal text-slate-500">(toggle show + edit fee / discount / GST — Total auto-calculates)</span></p>
              {cost.packages.map((p, i) => (
                <div key={p.key || i} className="bg-slate-50 rounded px-2.5 py-2 space-y-1.5" data-testid={`pkg-edit-${p.key || i}`}>
                  <div className="flex items-center gap-2">
                    <Switch checked={p.show !== false} onCheckedChange={(v) => setPkg(i, 'show', v)} data-testid={`pkg-show-${p.key || i}`} />
                    <span className="text-xs font-semibold flex-1">{p.name}</span>
                    <span className="text-[10px] uppercase tracking-wide text-slate-400">Total</span>
                    <span className="text-sm font-bold text-teal-800 font-mono w-28 text-right" data-testid={`pkg-total-${p.key || i}`}>
                      ₹{pkgTotal(p).toLocaleString()}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-1.5">
                    <div>
                      <p className="text-[9px] text-slate-400 uppercase">Professional Fee</p>
                      <Input type="number" value={p.professional_fee ?? ''} onChange={(e) => setPkg(i, 'professional_fee', e.target.value)} className="h-8 text-xs" data-testid={`pkg-fee-${p.key || i}`} />
                    </div>
                    <div>
                      <p className="text-[9px] text-slate-400 uppercase">Discount</p>
                      <Input type="number" value={p.discount ?? ''} onChange={(e) => setPkg(i, 'discount', e.target.value)} className="h-8 text-xs" data-testid={`pkg-discount-${p.key || i}`} />
                    </div>
                    <div>
                      <p className="text-[9px] text-slate-400 uppercase">GST @18%</p>
                      <Input type="number" value={p.gst ?? ''} onChange={(e) => setPkg(i, 'gst', e.target.value)} className="h-8 text-xs" data-testid={`pkg-gst-${p.key || i}`} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} className="bg-teal-600 hover:bg-teal-700" data-testid="edit-save-btn">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save & Regenerate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function MailAccountsDialog({ headers, senders = [], domain, onClose, onChanged }) {
  const [list, setList] = useState(senders);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [saving, setSaving] = useState(false);

  const reload = async () => {
    try {
      const r = await axios.get(`${API}/bulk-assessments/mail-senders`, { headers });
      setList(r.data);
      if (onChanged) onChanged();
    } catch (e) { /* silent */ }
  };

  const add = async () => {
    if (!name.trim() || !email.trim()) { toast.error('Enter both name and email'); return; }
    setSaving(true);
    try {
      const r = await axios.post(`${API}/bulk-assessments/mail-senders`, { name: name.trim(), email: email.trim() }, { headers });
      if (r.data.domain_warning) toast.warning(`${email.trim()} is not on @${domain} — delegation may not allow sending from it`);
      else toast.success('Mailbox added');
      setName(''); setEmail('');
      await reload();
    } catch (e) { toast.error(formatApiError(e, 'Could not add mailbox')); }
    finally { setSaving(false); }
  };

  const toggleActive = async (s) => {
    try { await axios.patch(`${API}/bulk-assessments/mail-senders/${s.id}`, { active: !s.active }, { headers }); await reload(); }
    catch (e) { toast.error('Could not update'); }
  };

  const remove = async (s) => {
    try { await axios.delete(`${API}/bulk-assessments/mail-senders/${s.id}`, { headers }); toast.success('Removed'); await reload(); }
    catch (e) { toast.error('Could not remove'); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto" data-testid="mail-accounts-dialog">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Mail className="h-4 w-4" />Consultant Mail Accounts</DialogTitle></DialogHeader>
        <DialogDescription className="text-[12px] text-slate-500 -mt-1">Reports are emailed from the consultant assigned to each client. Add each consultant's @{domain || 'leamss.com'} address here, then assign them per client.</DialogDescription>

        <div className="flex gap-2 items-end border rounded-md p-2.5 bg-slate-50">
          <div className="flex-1">
            <Label className="text-[11px]">Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Priya Sharma" className="h-8 text-xs" data-testid="mailbox-name-input" />
          </div>
          <div className="flex-1">
            <Label className="text-[11px]">Email</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder={`priya@${domain || 'leamss.com'}`} className="h-8 text-xs" data-testid="mailbox-email-input" />
          </div>
          <Button onClick={add} disabled={saving} className="h-8 bg-indigo-600 hover:bg-indigo-700" data-testid="mailbox-add-btn">
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Add'}
          </Button>
        </div>

        <div className="space-y-1.5" data-testid="mailbox-list">
          {list.length === 0 && <p className="text-[12px] text-slate-400 text-center py-3">No mailboxes yet. Add your consultants above.</p>}
          {list.map((s) => (
            <div key={s.id} className="flex items-center gap-2 border rounded-md px-2.5 py-1.5" data-testid={`mailbox-item-${s.email}`}>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate">{s.name}</p>
                <p className="text-[10px] text-slate-500 truncate">{s.email}{!s.domain_ok && <span className="text-rose-500"> · not on @{domain}</span>}</p>
              </div>
              <div className="flex items-center gap-1 text-[10px] text-slate-500">
                <Switch checked={s.active} onCheckedChange={() => toggleActive(s)} data-testid={`mailbox-active-${s.email}`} />
                {s.active ? 'active' : 'off'}
              </div>
              <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500 hover:text-rose-600 hover:bg-rose-50" onClick={() => remove(s)} data-testid={`mailbox-delete-${s.email}`}>
                <XCircle className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="mail-accounts-close">Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function BatchDefaultsDialog({ batch, headers, onClose, onApplied }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [items, setItems] = useState([]);
  const [packages, setPackages] = useState([]);
  const [authorities, setAuthorities] = useState([]);
  const [fallback, setFallback] = useState({ amount: '', currency: 'INR' });
  const [notes, setNotes] = useState('');
  const [saveToMaster, setSaveToMaster] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await axios.get(`${API}/bulk-assessments/${batch.id}/cost-defaults-template`, { headers });
        setItems((r.data.common_items || []).map((i) => ({ ...i })));
        setPackages((r.data.service_packages || []).map((p) => ({ ...p })));
        setAuthorities((r.data.authorities || []).map((a) => ({ ...a, newAmount: '', newCurrency: 'INR' })));
        const fb = r.data.fallback_skill_fee || {};
        setFallback({ amount: fb.amount ?? '', currency: fb.currency || 'INR' });
        setNotes(r.data.notes || '');
      } catch (e) {
        toast.error(formatApiError(e, 'Could not load batch defaults'));
      } finally { setLoading(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batch.id]);

  const setItem = (i, f, v) => setItems((arr) => arr.map((it, idx) => idx === i ? { ...it, [f]: v } : it));
  const addItem = () => setItems((arr) => [...arr, { category: 'Other', label: '', amount: 0, currency: 'INR', is_editable: true }]);
  const removeItem = (i) => setItems((arr) => arr.filter((_, idx) => idx !== i));
  const setAuth = (i, f, v) => setAuthorities((arr) => arr.map((a, idx) => idx === i ? { ...a, [f]: v } : a));
  const setPkg = (i, f, v) => setPackages((arr) => arr.map((p, idx) => {
    if (idx !== i) return p;
    const next = { ...p, [f]: v };
    if (['professional_fee', 'discount', 'gst'].includes(f)) {
      const fee = parseFloat(f === 'professional_fee' ? v : next.professional_fee) || 0;
      const disc = parseFloat(f === 'discount' ? v : next.discount) || 0;
      const gst = parseFloat(f === 'gst' ? v : next.gst) || 0;
      next.total = Math.max(0, fee - disc + gst);
    }
    return next;
  }));

  const missingCount = authorities.filter((a) => !a.matched && (a.newAmount === '' || a.newAmount == null)).length;

  const apply = async () => {
    setApplying(true);
    try {
      const skill_fees = {};
      authorities.forEach((a) => {
        if (!a.matched && a.newAmount !== '' && a.newAmount != null && a.key && a.key !== 'unknown') {
          skill_fees[a.key] = {
            authority_name: a.authority_name,
            components: [{ label: 'Skill Assessment Fee', amount: Number(a.newAmount), currency: a.newCurrency || 'INR' }],
          };
        }
      });
      const payload = {
        common_items: items.map((it) => ({ ...it, amount: Number(it.amount) || 0 })),
        service_packages: packages.map((p) => ({
          ...p,
          professional_fee: Number(p.professional_fee) || 0,
          discount: Number(p.discount) || 0,
          gst: Number(p.gst) || 0,
          total: pkgTotal(p),
        })),
        skill_fees,
        fallback_skill_fee: { amount: fallback.amount === '' ? null : Number(fallback.amount), currency: fallback.currency || 'INR' },
        notes,
        save_to_master: saveToMaster,
        regenerate: true,
      };
      const r = await axios.put(`${API}/bulk-assessments/${batch.id}/cost-defaults`, payload, { headers });
      toast.success(r.data.regenerating
        ? `Applied to all clients — regenerating ${batch.valid} reports…`
        : 'Batch defaults saved');
      onApplied();
    } catch (e) {
      toast.error(formatApiError(e, 'Could not apply batch defaults'));
    } finally { setApplying(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="batch-defaults-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Package className="h-5 w-5 text-amber-600" />Set Batch Cost & Packages</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12 text-slate-400"><Loader2 className="h-5 w-5 animate-spin mr-2" />Loading…</div>
        ) : (
          <div className="space-y-5">
            <p className="text-[11px] text-slate-500 bg-amber-50 border-l-4 border-amber-400 p-2 rounded">
              Configure costs & packages <strong>once</strong> — they apply to all <strong>{batch.valid}</strong> clients.
              Each client's <strong>Skill Assessment fee</strong> stays accurate to their own authority. Clients you edited individually keep their edits (only their skill fee updates).
            </p>

            {/* Common cost items */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-teal-900">Common Costs <span className="text-[10px] font-normal text-slate-500">(same for everyone)</span></p>
                <Button size="sm" variant="outline" className="h-7 text-[11px]" onClick={addItem} data-testid="bd-add-item">+ Add line</Button>
              </div>
              {items.map((it, i) => (
                <div key={i} className="flex items-center gap-1.5" data-testid={`bd-item-${i}`}>
                  <select value={it.category || 'Other'} onChange={(e) => setItem(i, 'category', e.target.value)} className="h-8 text-[11px] border rounded px-1 w-32" data-testid={`bd-category-${i}`}>
                    {COST_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <Input value={it.label} onChange={(e) => setItem(i, 'label', e.target.value)} placeholder="Label" className="h-8 text-xs flex-1" data-testid={`bd-label-${i}`} />
                  <Input type="number" value={it.amount} onChange={(e) => setItem(i, 'amount', e.target.value)} className="h-8 text-xs w-24" data-testid={`bd-amount-${i}`} />
                  <select value={it.currency || 'INR'} onChange={(e) => setItem(i, 'currency', e.target.value)} className="h-8 text-xs border rounded px-1" data-testid={`bd-ccy-${i}`}>
                    <option>INR</option><option>AUD</option>
                  </select>
                  <button onClick={() => removeItem(i)} className="text-rose-500 px-1" data-testid={`bd-remove-${i}`}>✕</button>
                </div>
              ))}
            </div>

            {/* Skill Assessment fees per authority in this batch (managed in Fee Master) */}
            <div className="space-y-2 border-t pt-3" data-testid="bd-skill-fees">
              <div className="flex items-center justify-between">
                <div className="text-sm font-bold text-teal-900">Skill Assessment Fees
                  <span className="text-[10px] font-normal text-slate-500"> — {authorities.length} authorit{authorities.length === 1 ? 'y' : 'ies'} in this batch</span>
                  {missingCount > 0 && <Badge className="ml-2 bg-rose-100 text-rose-700 text-[9px]">{missingCount} missing</Badge>}
                </div>
                <button onClick={() => navigate('/sales/fee-master')} className="text-[11px] text-teal-700 hover:underline font-medium" data-testid="bd-open-fee-master">Manage in Fee Master →</button>
              </div>
              <p className="text-[10px] text-slate-400">Fees come from the Fee Master (multi-fee authorities like TRA supported). Missing ones can be quick-filled below.</p>
              {authorities.map((a, i) => (
                <div key={a.key} className="flex items-center gap-2 bg-slate-50 rounded px-2 py-1.5" data-testid={`bd-auth-${a.key}`}>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{a.authority_name}</p>
                    <p className="text-[9px] text-slate-400">{a.count} client{a.count === 1 ? '' : 's'}{a.matched ? ` · ${(a.components || []).length} fee${(a.components || []).length === 1 ? '' : 's'}` : ' · not set'}</p>
                  </div>
                  {a.matched ? (
                    <span className="text-sm font-bold text-teal-800 font-mono" data-testid={`bd-auth-total-${a.key}`}>{money(a.total_by_currency)}</span>
                  ) : (
                    <>
                      <Input type="number" placeholder="Quick-fill" value={a.newAmount}
                        onChange={(e) => setAuth(i, 'newAmount', e.target.value)}
                        className={`h-8 text-xs w-28 ${(a.newAmount === '' || a.newAmount == null) ? 'border-rose-300 bg-rose-50' : ''}`} data-testid={`bd-auth-amount-${a.key}`} />
                      <select value={a.newCurrency || 'INR'} onChange={(e) => setAuth(i, 'newCurrency', e.target.value)} className="h-8 text-xs border rounded px-1" data-testid={`bd-auth-ccy-${a.key}`}>
                        <option>INR</option><option>AUD</option>
                      </select>
                    </>
                  )}
                </div>
              ))}
              <div className="flex items-center gap-2 px-2 pt-1">
                <span className="text-[11px] text-slate-600 flex-1">Fallback fee <span className="text-slate-400">(if an authority still isn't set)</span></span>
                <Input type="number" placeholder="e.g. 60000" value={fallback.amount} onChange={(e) => setFallback({ ...fallback, amount: e.target.value })} className="h-8 text-xs w-28" data-testid="bd-fallback-amount" />
                <select value={fallback.currency} onChange={(e) => setFallback({ ...fallback, currency: e.target.value })} className="h-8 text-xs border rounded px-1" data-testid="bd-fallback-ccy">
                  <option>INR</option><option>AUD</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-[11px] text-slate-600 cursor-pointer px-2">
                <Switch checked={saveToMaster} onCheckedChange={setSaveToMaster} data-testid="bd-save-master" />
                Save quick-filled fees to Fee Master (auto-fill next time)
              </label>
            </div>

            {/* LEAMSS packages */}
            {packages.length > 0 && (
              <div className="space-y-2 border-t pt-3" data-testid="bd-packages">
                <p className="text-sm font-bold text-teal-900">LEAMSS Service Packages <span className="text-[10px] font-normal text-slate-500">(fee / discount / GST — Total auto-calculates)</span></p>
                {packages.map((p, i) => (
                  <div key={p.key || i} className="bg-slate-50 rounded px-2.5 py-2 space-y-1.5" data-testid={`bd-pkg-${p.key || i}`}>
                    <div className="flex items-center gap-2">
                      <Switch checked={p.show !== false} onCheckedChange={(v) => setPkg(i, 'show', v)} data-testid={`bd-pkg-show-${p.key || i}`} />
                      <span className="text-xs font-semibold flex-1">{p.name}</span>
                      <span className="text-[10px] uppercase tracking-wide text-slate-400">Total</span>
                      <span className="text-sm font-bold text-teal-800 font-mono w-28 text-right" data-testid={`bd-pkg-total-${p.key || i}`}>₹{pkgTotal(p).toLocaleString()}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-1.5">
                      <div><p className="text-[9px] text-slate-400 uppercase">Professional Fee</p>
                        <Input type="number" value={p.professional_fee ?? ''} onChange={(e) => setPkg(i, 'professional_fee', e.target.value)} className="h-8 text-xs" data-testid={`bd-pkg-fee-${p.key || i}`} /></div>
                      <div><p className="text-[9px] text-slate-400 uppercase">Discount</p>
                        <Input type="number" value={p.discount ?? ''} onChange={(e) => setPkg(i, 'discount', e.target.value)} className="h-8 text-xs" data-testid={`bd-pkg-discount-${p.key || i}`} /></div>
                      <div><p className="text-[9px] text-slate-400 uppercase">GST @18%</p>
                        <Input type="number" value={p.gst ?? ''} onChange={(e) => setPkg(i, 'gst', e.target.value)} className="h-8 text-xs" data-testid={`bd-pkg-gst-${p.key || i}`} /></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={apply} disabled={applying || loading} className="bg-amber-600 hover:bg-amber-700" data-testid="bd-apply-btn">
            {applying ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
            Apply to all {batch.valid} & Regenerate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AiReviewDialog({ batch, rows, headers, onClose, onChanged, onEdit }) {
  const [busy, setBusy] = useState(null); // row id being acted on

  // AI-detected rows, unreviewed & low-confidence first
  const order = { low: 0, medium: 1, high: 2 };
  const aiRows = rows
    .filter((r) => r.parsed?.anzsco_source === 'ai')
    .sort((a, b) => {
      const rev = (a.parsed?.ai_reviewed ? 1 : 0) - (b.parsed?.ai_reviewed ? 1 : 0);
      if (rev !== 0) return rev;
      return (order[a.parsed?.ai_confidence] ?? 0) - (order[b.parsed?.ai_confidence] ?? 0);
    });

  const confirm = async (row) => {
    setBusy(row.id);
    try {
      await axios.post(`${API}/bulk-assessments/${batch.id}/row/${row.id}/confirm-ai`, {}, { headers });
      toast.success(`Confirmed — ${row.parsed?.name}`);
      await onChanged();
    } catch (e) { toast.error(formatApiError(e, 'Could not confirm')); }
    finally { setBusy(null); }
  };

  const confirmAll = async () => {
    setBusy('all');
    try {
      const r = await axios.post(`${API}/bulk-assessments/${batch.id}/confirm-all-ai`, {}, { headers });
      toast.success(`Marked ${r.data.reviewed} client(s) as reviewed`);
      await onChanged();
    } catch (e) { toast.error(formatApiError(e, 'Could not mark all reviewed')); }
    finally { setBusy(null); }
  };

  const switchToAlternative = async (row, alt) => {
    setBusy(row.id);
    try {
      await axios.patch(`${API}/bulk-assessments/row/${row.id}`, { anzsco_code: alt.code }, { headers });
      toast.success(`Switched ${row.parsed?.name} → ${alt.code} ${alt.title || ''}`);
      await onChanged();
    } catch (e) { toast.error(formatApiError(e, 'Could not switch code')); }
    finally { setBusy(null); }
  };

  const confColor = (c, reviewed) => reviewed ? 'bg-emerald-100 text-emerald-700'
    : c === 'high' ? 'bg-violet-100 text-violet-700'
    : c === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700';

  const pending = aiRows.filter((r) => !r.parsed?.ai_reviewed).length;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="ai-review-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardCheck className="h-5 w-5 text-violet-600" />AI ANZSCO Review
            <Badge className="bg-violet-100 text-violet-700 text-[10px]">{pending} pending</Badge>
          </DialogTitle>
        </DialogHeader>
        <div className="flex items-center justify-between gap-2 bg-violet-50 border-l-4 border-violet-400 p-2 rounded">
          <p className="text-[11px] text-slate-500">
            AI-detected codes, riskiest first. Confirm if correct, pick a better alternative, or open full edit. Low/medium confidence deserve a closer look.
          </p>
          {pending > 0 && (
            <Button size="sm" onClick={confirmAll} disabled={busy === 'all'}
              className="bg-emerald-600 hover:bg-emerald-700 h-7 text-[11px] shrink-0" data-testid="ai-confirm-all-btn">
              {busy === 'all' ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Check className="h-3 w-3 mr-1" />}Mark all {pending} as reviewed
            </Button>
          )}
        </div>

        <div className="space-y-2.5">
          {aiRows.map((r) => {
            const p = r.parsed || {};
            return (
              <div key={r.id} className={`rounded-lg border p-3 ${p.ai_reviewed ? 'border-emerald-200 bg-emerald-50/40' : 'border-slate-200'}`} data-testid={`ai-review-row-${r.row_index}`}>
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <div className="min-w-0">
                    <p className="text-sm font-bold flex items-center gap-2">{p.name}
                      <span className={`text-[9px] px-1.5 py-0.5 rounded ${confColor(p.ai_confidence, p.ai_reviewed)}`}>
                        {p.ai_reviewed ? 'confirmed' : `${p.ai_confidence || 'low'} confidence`}
                      </span>
                    </p>
                    <p className="text-xs text-slate-700 font-mono mt-0.5">{p.anzsco_code} · {p.occupation_title}</p>
                    <p className="text-[11px] text-slate-500 mt-1 flex items-start gap-1"><Info className="h-3 w-3 mt-0.5 shrink-0" />{p.ai_reasoning || 'Matched from resume.'}</p>
                    {(p.ai_filled_fields || []).length > 0 && (
                      <p className="text-[10px] text-slate-400 mt-0.5">AI-filled from resume: {p.ai_filled_fields.join(', ')}</p>
                    )}
                  </div>
                  <div className="flex flex-col gap-1.5 shrink-0">
                    {!p.ai_reviewed && (
                      <Button size="sm" onClick={() => confirm(r)} disabled={busy === r.id} className="bg-emerald-600 hover:bg-emerald-700 h-7 text-[11px]" data-testid={`ai-confirm-${r.row_index}`}>
                        {busy === r.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3 mr-1" />}Confirm
                      </Button>
                    )}
                    <Button size="sm" variant="outline" onClick={() => onEdit(r)} className="h-7 text-[11px]" data-testid={`ai-edit-${r.row_index}`}>
                      <Edit3 className="h-3 w-3 mr-1" />Edit
                    </Button>
                  </div>
                </div>
                {(p.ai_alternatives || []).length > 0 && (
                  <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] text-slate-400">Switch to:</span>
                    {p.ai_alternatives.map((alt) => (
                      <button key={alt.code} onClick={() => switchToAlternative(r, alt)} disabled={busy === r.id}
                        className="text-[10px] px-2 py-0.5 rounded-full border border-violet-200 text-violet-700 hover:bg-violet-100 disabled:opacity-50"
                        data-testid={`ai-alt-${r.row_index}-${alt.code}`}>
                        {alt.code} · {alt.title}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {aiRows.length === 0 && <p className="text-center text-slate-400 py-8 text-sm">No AI-detected rows in this batch.</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="ai-review-close">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}



function MarkNotEligibleDialog({ row, onClose, onConfirm }) {
  const existing = row.manual_eligibility || {};
  const [kind, setKind] = useState(existing.kind || 'improvable');
  const [reason, setReason] = useState(existing.reason || '');
  const [saving, setSaving] = useState(false);
  const name = row.parsed?.name || 'this client';

  const submit = async () => {
    setSaving(true);
    try { await onConfirm(kind, reason.trim()); } finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg" data-testid="mark-not-eligible-dialog">
        <DialogHeader>
          <DialogTitle>Mark as Not-Eligible</DialogTitle>
          <DialogDescription>
            Override the automatic verdict for <b>{name}</b>. The PDF report will be regenerated as a
            Not-Eligible report with your reason, ready to email.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-1">
          <RadioGroup value={kind} onValueChange={setKind}>
            <div className="flex items-start gap-2 rounded-lg border p-3 cursor-pointer hover:bg-amber-50/50" onClick={() => setKind('improvable')}>
              <RadioGroupItem value="improvable" id="k-improvable" className="mt-0.5" data-testid="mark-kind-improvable" />
              <div>
                <Label htmlFor="k-improvable" className="text-sm font-semibold text-amber-700 cursor-pointer">Not-Eligible now — possible in future</Label>
                <p className="text-[11px] text-slate-500">Shows reasons + a "how to become eligible" action plan.</p>
              </div>
            </div>
            <div className="flex items-start gap-2 rounded-lg border p-3 cursor-pointer hover:bg-rose-50/50" onClick={() => setKind('ineligible')}>
              <RadioGroupItem value="ineligible" id="k-ineligible" className="mt-0.5" data-testid="mark-kind-ineligible" />
              <div>
                <Label htmlFor="k-ineligible" className="text-sm font-semibold text-rose-700 cursor-pointer">Not-Eligible — permanent / hard</Label>
                <p className="text-[11px] text-slate-500">Shows reasons + alternative pathways.</p>
              </div>
            </div>
          </RadioGroup>

          <div>
            <Label className="text-xs">Your reason (shown to the client)</Label>
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={4}
              placeholder="e.g. Based on the documents provided, the work experience could not be verified for a positive skills assessment."
              data-testid="mark-reason-input" />
            <p className="text-[10px] text-slate-400 mt-1">Leave blank to use a standard reason.</p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="mark-cancel-btn">Cancel</Button>
          <Button onClick={submit} disabled={saving} className="bg-rose-600 hover:bg-rose-700 text-white" data-testid="mark-confirm-btn">
            {saving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Ban className="h-4 w-4 mr-1" />}
            Mark & Regenerate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
