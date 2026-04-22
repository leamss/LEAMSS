import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle2, Upload, FileText, Clock, Loader2, Sparkles, Scan,
  AlertTriangle, XCircle, CreditCard, ShieldCheck, FileCheck, Send, RefreshCw
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DOC_TYPES = [
  { id: 'passport', label: 'Passport', required: true },
  { id: 'resume', label: 'Resume / CV', required: true },
  { id: 'education_cert', label: 'Education Certificate', required: true },
  { id: 'transcript', label: 'Academic Transcripts', required: false },
  { id: 'ielts', label: 'IELTS / English Test', required: false },
  { id: 'experience_letter', label: 'Work Experience Letter', required: false },
  { id: 'bank_statement', label: 'Bank Statement', required: false },
  { id: 'other', label: 'Other Document', required: false },
];

// 6 pipeline stages the client sees (maps to backend stages)
const STAGE_STEPS = [
  { key: 'paid', label: 'Payment Done', stages: ['payment_received', 'partner_review', 'documents_submitted', 'under_review', 'approved', 'proposal_sent', 'proposal_paid', 'case_created'] },
  { key: 'uploading', label: 'Upload Documents', stages: ['partner_review', 'documents_submitted', 'under_review', 'approved', 'proposal_sent', 'proposal_paid', 'case_created'] },
  { key: 'reviewing', label: 'Under Review', stages: ['documents_submitted', 'under_review', 'approved', 'proposal_sent', 'proposal_paid', 'case_created'] },
  { key: 'approved', label: 'Approved', stages: ['approved', 'proposal_sent', 'proposal_paid', 'case_created'] },
  { key: 'proposal', label: 'Proposal & Signing', stages: ['proposal_sent', 'proposal_paid', 'case_created'] },
  { key: 'case', label: 'Case Active', stages: ['case_created'] },
];

const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

export default function PreAssessmentMiniPortal({ pa, onRefresh, onOpenScanner }) {
  const [docs, setDocs] = useState([]);
  const [access, setAccess] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState('passport');
  const [submitting, setSubmitting] = useState(false);
  const [paying, setPaying] = useState(false);
  const [accepting, setAccepting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, a] = await Promise.all([
        axios.get(`${API}/pre-assessment/${pa.id}/documents`, getAuth()),
        axios.get(`${API}/pre-assess-portal/client/portal-access/${pa.id}`, getAuth()),
      ]);
      setDocs(d.data || []);
      setAccess(a.data);
    } catch (e) { console.error(e); }
  }, [pa.id]);

  useEffect(() => { load(); }, [load]);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('document_type', docType);
      fd.append('file', file);
      await axios.post(`${API}/pre-assessment/${pa.id}/upload-document`, fd, {
        ...getAuth(),
        headers: { ...getAuth().headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`${file.name} uploaded`);
      e.target.value = '';
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleSubmitForReview = async () => {
    setSubmitting(true);
    try {
      await axios.post(`${API}/pre-assess-portal/client/submit/${pa.id}`, {}, getAuth());
      toast.success('Submitted! Your partner will review and forward to admin.');
      await load();
      onRefresh?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Submit failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAccept = async () => {
    setAccepting(true);
    try {
      await axios.post(`${API}/pre-assess-portal/client/accept-proposal/${pa.id}`, {}, getAuth());
      toast.success('Proposal accepted!');
      await load();
      onRefresh?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed');
    } finally {
      setAccepting(false);
    }
  };

  const handlePayProposal = async () => {
    setPaying(true);
    try {
      await axios.post(`${API}/pre-assess-portal/client/mock-pay-proposal/${pa.id}`, {}, getAuth());
      toast.success('Main fee paid (MOCK). Admin will activate your case shortly.');
      await load();
      onRefresh?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Payment failed');
    } finally {
      setPaying(false);
    }
  };

  const stage = pa.stage;
  const currentStepIdx = STAGE_STEPS.findIndex(s => !s.stages.includes(stage));
  const activeIdx = currentStepIdx === -1 ? STAGE_STEPS.length - 1 : currentStepIdx - 1;
  const progressPct = ((activeIdx + 1) / STAGE_STEPS.length) * 100;
  const isRejected = ['rejected', 'refund_initiated', 'refunded'].includes(stage);

  return (
    <div className="space-y-6" data-testid="pa-mini-portal">
      {/* HERO — Welcome + stage pipeline */}
      <Card className="overflow-hidden border-0 shadow-xl bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] text-white">
        <div className="p-6 sm:p-8">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <Badge className="bg-white/20 text-white border-white/30 mb-2">
                <ShieldCheck className="h-3 w-3 mr-1" /> Pre-Assessment Active
              </Badge>
              <h2 className="text-2xl sm:text-3xl font-bold">Welcome, {pa.client_name}!</h2>
              <p className="text-sm opacity-80 mt-1">
                Your <span className="font-semibold">{pa.service_type}</span> journey to <span className="font-semibold">{pa.country}</span> has begun.
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-3 px-4 text-right">
              <p className="text-xs opacity-70">Pre-assessment #</p>
              <p className="font-mono text-sm font-semibold">{pa.pa_number}</p>
            </div>
          </div>
          {/* Pipeline */}
          <div className="mt-7">
            <div className="flex items-center justify-between text-[11px] uppercase tracking-wider font-semibold opacity-80 mb-2 gap-2 overflow-x-auto">
              {STAGE_STEPS.map((s, i) => (
                <span key={s.key} className={`whitespace-nowrap ${i <= activeIdx ? 'text-white' : 'opacity-50'}`}>
                  {i + 1}. {s.label}
                </span>
              ))}
            </div>
            <Progress value={progressPct} className="h-2 bg-white/20" />
            <p className="text-xs opacity-75 mt-2">
              {isRejected
                ? 'Your application was not approved. Refund has been initiated.'
                : `Stage ${activeIdx + 1} of ${STAGE_STEPS.length}: ${STAGE_STEPS[Math.max(0, activeIdx)]?.label}`}
            </p>
          </div>
        </div>
      </Card>

      {isRejected && (
        <Card className="p-5 bg-red-50 border-red-200 flex gap-3 items-start">
          <XCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-red-700">Application Not Approved</h4>
            <p className="text-sm text-red-600 mt-1">
              {pa.admin_reason || 'Please contact your partner for details. Refund will be processed within 5-7 business days.'}
            </p>
          </div>
        </Card>
      )}

      {/* STAGE: Upload documents (payment_received) */}
      {stage === 'payment_received' && (
        <>
          <Card className="p-5 border-slate-200">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-[#f7620b] to-[#e55a09] rounded-lg flex items-center justify-center shrink-0">
                <Upload className="h-5 w-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800">Upload Your Documents</h3>
                <p className="text-sm text-slate-500">Upload the documents below so our team can assess your eligibility.</p>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap items-center bg-slate-50 border border-slate-200 rounded-lg p-3">
              <select value={docType} onChange={e => setDocType(e.target.value)}
                className="text-sm border border-slate-300 rounded px-2 py-1.5 bg-white" data-testid="mini-doc-type">
                {DOC_TYPES.map(d => <option key={d.id} value={d.id}>{d.label}{d.required ? ' *' : ''}</option>)}
              </select>
              <label className="cursor-pointer">
                <input type="file" className="hidden" onChange={handleFile} disabled={uploading} data-testid="mini-upload-input" />
                <span className="inline-flex items-center gap-1.5 bg-[#2a777a] hover:bg-[#236466] text-white text-sm font-medium px-3 py-1.5 rounded transition">
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  {uploading ? 'Uploading…' : 'Upload Document'}
                </span>
              </label>
              <Button variant="outline" size="sm" onClick={onOpenScanner} className="text-xs" data-testid="mini-scanner-btn">
                <Scan className="h-3.5 w-3.5 mr-1" /> AI Scan a document first
              </Button>
            </div>

            {docs.length > 0 ? (
              <div className="mt-4 space-y-2">
                <p className="text-xs uppercase tracking-wider font-semibold text-slate-500">Uploaded ({docs.length})</p>
                {docs.map((d) => (
                  <div key={d.id} className="flex items-center gap-3 p-2.5 bg-emerald-50 border border-emerald-100 rounded">
                    <FileCheck className="h-4 w-4 text-emerald-600" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-700 truncate">{d.file_name}</p>
                      <p className="text-xs text-slate-500">{d.document_type} · {(d.file_size / 1024).toFixed(1)} KB</p>
                    </div>
                    <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">Uploaded</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-xs text-slate-400 italic">No documents uploaded yet.</p>
            )}
          </Card>

          <Card className="p-5 bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-slate-800">Ready to submit?</h3>
                <p className="text-sm text-slate-600 mt-1">
                  Once you've uploaded all required documents, click Submit for Review. Your partner will verify and send to admin for approval (usually 1-2 business days).
                </p>
                <Button onClick={handleSubmitForReview} disabled={submitting || docs.length === 0}
                  className="mt-3 bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="mini-submit-review">
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                  Submit for Review
                </Button>
              </div>
            </div>
          </Card>
        </>
      )}

      {/* STAGE: Partner reviewing client's submission */}
      {stage === 'partner_review' && (
        <Card className="p-6 bg-gradient-to-br from-pink-50 to-white border-pink-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-pink-100 rounded-full flex items-center justify-center shrink-0">
              <Clock className="h-6 w-6 text-pink-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-lg">Documents with your Partner</h3>
              <p className="text-sm text-slate-600 mt-1">
                Thank you for submitting! Your partner is reviewing your documents before forwarding to our eligibility team. You'll hear back within 1 business day.
              </p>
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                <FileCheck className="h-3.5 w-3.5" />
                <span>{docs.length} document(s) submitted</span>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* STAGE: In review */}
      {['documents_submitted', 'under_review'].includes(stage) && (
        <Card className="p-6 bg-gradient-to-br from-amber-50 to-white border-amber-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center shrink-0">
              <Clock className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-lg">Under Review</h3>
              <p className="text-sm text-slate-600 mt-1">
                Your documents are being reviewed by our expert team. We'll notify you as soon as the eligibility assessment is ready (usually within 1-2 business days).
              </p>
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                <RefreshCw className="h-3.5 w-3.5" />
                <span>{docs.length} document(s) submitted · Refresh this page for updates</span>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* STAGE: Approved — waiting for proposal */}
      {stage === 'approved' && (
        <Card className="p-6 bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center shrink-0">
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-lg">Congratulations — You're Eligible!</h3>
              <p className="text-sm text-slate-600 mt-1">
                Your partner is preparing a personalised proposal with fees, timeline and next steps. You'll receive it shortly.
              </p>
              {pa.admin_reason && (
                <p className="text-xs text-emerald-700 mt-2 bg-white rounded p-2 border border-emerald-100">
                  <span className="font-semibold">Admin note:</span> {pa.admin_reason}
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* STAGE: Proposal received — accept + pay */}
      {stage === 'proposal_sent' && (
        <Card className="p-6 bg-gradient-to-br from-[#f7620b]/5 to-[#2a777a]/5 border-[#2a777a]/20">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-[#f7620b] rounded-full flex items-center justify-center shrink-0">
              <FileText className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <Badge className="bg-[#f7620b] text-white mb-2">Proposal Ready</Badge>
              <h3 className="font-bold text-slate-800 text-lg">Your Service Proposal</h3>
              <div className="mt-3 bg-white rounded-lg p-4 border border-slate-200">
                <div className="flex justify-between text-sm py-1.5">
                  <span className="text-slate-500">Service fee</span>
                  <span className="font-bold text-2xl text-slate-800">₹{(pa.proposal_fee || 0).toLocaleString('en-IN')}</span>
                </div>
                {pa.notes && <p className="text-xs text-slate-600 mt-2 italic">"{pa.notes}"</p>}
              </div>
              <div className="mt-4 flex gap-2 flex-wrap">
                {pa.proposal_status !== 'accepted' ? (
                  <Button onClick={handleAccept} disabled={accepting}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="mini-accept-proposal">
                    {accepting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
                    Accept Proposal
                  </Button>
                ) : (
                  <Button onClick={handlePayProposal} disabled={paying}
                    className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="mini-pay-proposal">
                    {paying ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CreditCard className="h-4 w-4 mr-2" />}
                    Pay ₹{(pa.proposal_fee || 0).toLocaleString('en-IN')} (MOCK)
                  </Button>
                )}
              </div>
              <p className="text-[10px] text-slate-400 mt-2">🔒 MOCK payment mode. Real Razorpay/Stripe coming soon.</p>
            </div>
          </div>
        </Card>
      )}

      {/* STAGE: proposal_paid — awaiting admin final approval */}
      {stage === 'proposal_paid' && (
        <Card className="p-6 bg-gradient-to-br from-blue-50 to-white border-blue-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center shrink-0">
              <Clock className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-lg">Payment Received — Activating Your Case</h3>
              <p className="text-sm text-slate-600 mt-1">
                Thank you! Your main fee payment has been received. Our admin team is creating your case now and will assign a dedicated case manager shortly.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Access level hint */}
      {access && (
        <p className="text-center text-xs text-slate-400">
          Portal access level: <span className="font-semibold text-slate-500 capitalize">{access.access_level}</span>
          {' · '}Current stage: <span className="font-semibold text-slate-500">{stage.replace(/_/g, ' ')}</span>
        </p>
      )}
    </div>
  );
}
