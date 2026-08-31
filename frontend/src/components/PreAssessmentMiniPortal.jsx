import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle2, Upload, FileText, Clock, Loader2, Sparkles, Scan,
  AlertTriangle, XCircle, CreditCard, ShieldCheck, FileCheck, Send, RefreshCw, Download
} from 'lucide-react';
import SignatureCanvas from '@/components/SignatureCanvas';
import PaymentHistoryTimeline from '@/components/PaymentHistoryTimeline';
import ClientAgreementSigning from '@/components/ClientAgreementSigning';
import ClientOccupationReviewCard from '@/components/ClientOccupationReviewCard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

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
  { key: 'paid', label: 'Payment Done', stages: ['payment_received', 'partner_review', 'documents_submitted', 'under_review', 'approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'uploading', label: 'Upload Documents', stages: ['partner_review', 'documents_submitted', 'under_review', 'approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'reviewing', label: 'Under Review', stages: ['documents_submitted', 'under_review', 'approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'approved', label: 'Approved', stages: ['approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'proposal', label: 'Proposal & Signing', stages: ['awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'case', label: 'Case Active', stages: ['case_created'] },
];

const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

export default function PreAssessmentMiniPortal({ pa, onRefresh, onOpenScanner }) {
  const [localPa, setLocalPa] = useState(null);
  const currentPa = localPa || pa;
  const [docs, setDocs] = useState([]);
  const [access, setAccess] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState('passport');
  const [submitting, setSubmitting] = useState(false);
  const [paying, setPaying] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [givingConsent, setGivingConsent] = useState(false);
  const [consentSummary, setConsentSummary] = useState(null);
  const [esignRec, setEsignRec] = useState(null);
  const [savingSig, setSavingSig] = useState(false);
  const [proposalPayTab, setProposalPayTab] = useState('domestic'); // 'domestic' | 'international'
  const [proposalBankDetails, setProposalBankDetails] = useState(null);
  const [proposalBankLoading, setProposalBankLoading] = useState(false);
  const [proposalTransferRef, setProposalTransferRef] = useState('');
  const [proposalClaiming, setProposalClaiming] = useState(false);
  const [proposalProofFile, setProposalProofFile] = useState(null);
  const [proposalSelectedCountry, setProposalSelectedCountry] = useState('Australia');

  const INTL_COUNTRIES = [
    { code: 'Australia', label: '🇦🇺 AUS' },
    { code: 'Canada', label: '🇨🇦 Canada' },
    { code: 'USA', label: '🇺🇸 USA' },
    { code: 'UK', label: '🇬🇧 UK' },
    { code: 'New Zealand', label: '🇳🇿 NZ' },
  ];

  const load = useCallback(async () => {
    const targetId = pa?.id || pa?.pa_number;
    if (!targetId) return;
    try {
      const [d, a, paDetail] = await Promise.all([
        axios.get(`${API}/pre-assessment/${targetId}/documents`, getAuth()).catch(() => ({ data: [] })),
        axios.get(`${API}/pre-assess-portal/client/portal-access/${targetId}`, getAuth()).catch(() => ({ data: null })),
        axios.get(`${API}/pre-assessment/${targetId}`, getAuth()).catch(() => null),
      ]);
      setDocs(d?.data || []);
      if (a?.data) setAccess(a.data);
      if (paDetail?.data) {
        setLocalPa(paDetail.data);
      }
    } catch (e) { console.error('Error loading PA portal data:', e); }
  }, [pa?.id, pa?.pa_number]);

  useEffect(() => {
    if (pa) setLocalPa(pa);
  }, [pa]);

  useEffect(() => { load(); }, [load]);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const targetId = currentPa?.id || currentPa?.pa_number || pa?.id || pa?.pa_number;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('document_type', docType);
      fd.append('file', file);
      await axios.post(`${API}/pre-assessment/${targetId}/upload-document`, fd, {
        ...getAuth(),
        headers: { ...getAuth().headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`${file.name} uploaded successfully`);
      e.target.value = '';
      await load();
      onRefresh?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleSubmitForReview = async () => {
    const targetId = currentPa?.id || currentPa?.pa_number || pa?.id || pa?.pa_number;
    setSubmitting(true);
    try {
      await axios.post(`${API}/pre-assess-portal/client/submit/${targetId}`, {}, getAuth());
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

  const handleGiveConsent = async () => {
    setGivingConsent(true);
    try {
      const r = await axios.post(`${API}/pre-assess-portal/client/proposal-consent/${pa.id}`, {}, getAuth());
      toast.success(`Consent recorded · Ref ${r.data.reference_id}`);
      setConsentSummary(r.data.summary || null);
      await load();
      onRefresh?.();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
    setGivingConsent(false);
  };

  const loadConsentSummary = useCallback(async () => {
    const targetId = pa?.id || pa?.pa_number;
    if (!targetId) return;
    try {
      const r = await axios.get(`${API}/pre-assess-portal/client/consent-summary/${targetId}`, getAuth());
      if (r.data.exists) setConsentSummary(r.data.record);
    } catch (e) { /* silent */ }
  }, [pa?.id, pa?.pa_number]);

  const loadEsign = useCallback(async () => {
    const targetId = pa?.id || pa?.pa_number;
    if (!targetId) return;
    try {
      const r = await axios.get(`${API}/proposal-docs/${targetId}/esign`, getAuth());
      if (r.data.signed) setEsignRec(r.data.record);
    } catch (e) { /* silent */ }
  }, [pa?.id, pa?.pa_number]);

  useEffect(() => {
    if (pa?.proposal_consent_given) loadConsentSummary();
    if (['proposal_paid', 'awaiting_final_approval', 'case_created'].includes(pa?.stage)) loadEsign();
  }, [pa?.proposal_consent_given, pa?.stage, loadConsentSummary, loadEsign]);

  const handleSaveSignature = async (dataUrl, meta) => {
    const targetId = currentPa?.id || currentPa?.pa_number || pa?.id || pa?.pa_number;
    if (!targetId) return;
    setSavingSig(true);
    try {
      const r = await axios.post(`${API}/proposal-docs/${targetId}/esign`, {
        signature_data_url: dataUrl,
        typed_name: meta.typed_name,
        consent_text: 'I electronically sign this service agreement',
        biometric_packet: meta.biometric_packet || null,
      }, getAuth());
      toast.success('Agreement e-signed · ' + new Date(r.data.signed_at).toLocaleString());
      await loadEsign();
      await load();
      onRefresh?.();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Sign failed'); }
    setSavingSig(false);
  };

  const downloadDoc = async (kind) => {
    const targetId = currentPa?.id || currentPa?.pa_number || pa?.id || pa?.pa_number;
    if (!targetId) return;
    try {
      const r = await fetch(`${API}/proposal-docs/${targetId}/${kind}.pdf`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      });
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const u = URL.createObjectURL(blob);
      window.open(u, '_blank');
      setTimeout(() => URL.revokeObjectURL(u), 60000);
    } catch { toast.error(`${kind} PDF failed`); }
  };

const viewPaDocument = async (docId, inline = true) => {
  try {
    const r = await fetch(`${API}/pre-assessment/${pa.id}/document/${docId}/download?inline=${inline}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    if (!r.ok) throw new Error();
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    toast.error('Could not open document');
  }
};

const downloadPaDocument = async (docId, fileName) => {
  try {
    const r = await fetch(`${API}/pre-assessment/${pa.id}/document/${docId}/download?inline=false`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
    if (!r.ok) throw new Error();
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName || 'document';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch {
    toast.error('Download failed');
  }
};

const [selectingPkg, setSelectingPkg] = useState(null);

  const handleSelectPackage = async (packageId) => {
    const occReviewStatus = currentPa?.client_occupation_review_status || 'pending_client_review';
    const hasOccupation = Boolean(currentPa?.occupation_code || currentPa?.suggested_occupation_code);

    if (hasOccupation && occReviewStatus === 'rejected_by_client') {
      toast.error('You requested an occupation code change. Please wait for partner & admin review before selecting a package.');
      return;
    }
    if (hasOccupation && occReviewStatus !== 'accepted') {
      toast.warning('Please confirm and accept your assigned Occupation Code Profile above first!');
      return;
    }
    setSelectingPkg(packageId);
    try {
      await axios.post(`${API}/pre-assess-portal/client/select-package/${currentPa.id}`, { package_id: packageId }, getAuth());
      toast.success('Package selected! Your partner will set up the payment plan.');
      await load();
      onRefresh?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to select package');
    } finally {
      setSelectingPkg(null);
    }
  };

  const viewPackageDoc = async (documentUrl) => {
    if (!documentUrl) return;
    try {
      const r = await fetch(`${BACKEND_URL}${documentUrl}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch {
      toast.error('Could not open document');
    }
  };

useEffect(() => {
    if (proposalPayTab !== 'international') return;
    setProposalBankLoading(true);
    setProposalBankDetails(null);
    axios.get(`${API}/pre-assess-portal/client/proposal/bank-details/${pa.id}`, {
      ...getAuth(), params: { country: proposalSelectedCountry },
    })
      .then(r => setProposalBankDetails(r.data))
      .catch(e => toast.error(e?.response?.data?.detail || 'Could not load bank details'))
      .finally(() => setProposalBankLoading(false));
  }, [proposalPayTab, proposalSelectedCountry, pa.id]);

  const handlePayProposal = async () => {
    setPaying(true);
    try {
      // Step 1: Backend कडून Razorpay order तयार करून घे
      const orderRes = await axios.post(`${API}/pre-assess-portal/client/proposal/create-order/${pa.id}`, {}, getAuth());
      const { order_id, amount, currency, key_id, client_name, client_email, client_mobile } = orderRes.data;

      // Step 2: Razorpay Checkout Popup उघड
      const options = {
        key: key_id,
        amount: amount,
        currency: currency,
        name: 'LEAMSS Immigration',
        description: 'Service Fee Installment',
        order_id: order_id,
        prefill: { name: client_name || '', email: client_email || '', contact: client_mobile || '' },
        theme: { color: '#f7620b' },
        handler: async function (response) {
          try {
            const verifyRes = await axios.post(`${API}/pre-assess-portal/client/proposal/verify-payment/${pa.id}`, {
              order_id: response.razorpay_order_id,
              payment_id: response.razorpay_payment_id,
              signature: response.razorpay_signature,
            }, getAuth());
            if (verifyRes.data.fully_paid) {
              toast.success('Full payment complete! Admin will activate your case shortly.');
            } else {
              toast.success(`${verifyRes.data.part_paid} paid — ₹${Number(verifyRes.data.amount_paid_now).toLocaleString('en-IN')}. Remaining: ₹${Number(verifyRes.data.amount_pending).toLocaleString('en-IN')}`);
            }
            await load();
            onRefresh?.();
          } catch (e) {
            toast.error(e?.response?.data?.detail || 'Payment verification failed');
          } finally {
            setPaying(false);
          }
        },
        modal: { ondismiss: function () { setPaying(false); } },
      };

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Unable to start payment');
      setPaying(false);
    }
  };

  const handleProposalInternationalClaim = async () => {
    setProposalClaiming(true);
    try {
      const r = await axios.post(`${API}/pre-assess-portal/client/proposal/international-claim/${pa.id}`,
        { reference_note: proposalTransferRef }, getAuth());

      // Upload payment proof file (if attached) using existing document-upload endpoint
      if (proposalProofFile) {
        const fd = new FormData();
        fd.append('document_type', 'payment_proof');
        fd.append('file', proposalProofFile);
        await axios.post(`${API}/pre-assessment/${pa.id}/upload-document`, fd, {
          ...getAuth(), headers: { ...getAuth().headers, 'Content-Type': 'multipart/form-data' },
        });
      }

      toast.success(`${r.data.part_claimed} claim submitted! Your partner will verify and confirm.`);
      setProposalTransferRef('');
      setProposalProofFile(null);
      await load();
      onRefresh?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Something went wrong');
    } finally {
      setProposalClaiming(false);
    }
  };

  const stage = currentPa?.stage || pa?.stage;
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
              <h2 className="text-2xl sm:text-3xl font-bold">Welcome, {currentPa?.client_name || pa?.client_name}!</h2>
              <p className="text-sm opacity-80 mt-1">
                Your <span className="font-semibold">{currentPa?.service_type || pa?.service_type}</span> journey to <span className="font-semibold">{currentPa?.country || pa?.country}</span> has begun.
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-3 px-4 text-right">
              <p className="text-xs opacity-70">Pre-assessment #</p>
              <p className="font-mono text-sm font-semibold">{currentPa?.pa_number || pa?.pa_number}</p>
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

      {/* STAGE: International wire transfer — pending partner verification, but client can upload proof */}
      {stage === 'international_payment_pending' && (
        <>
          <Card className="p-5 bg-blue-50 border-blue-200">
            <div className="flex items-start gap-3">
              <Clock className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-bold text-slate-800">International Payment — Verification Pending</h3>
                <p className="text-sm text-slate-600 mt-1">
                  We've received your transfer claim. Please upload your payment receipt/screenshot below so your partner can verify it (usually within 1-2 business days).
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-5 border-slate-200">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-[#f7620b] to-[#e55a09] rounded-lg flex items-center justify-center shrink-0">
                <Upload className="h-5 w-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800">Upload Payment Proof & Documents</h3>
                <p className="text-sm text-slate-500">Upload your payment receipt/screenshot and eligibility documents.</p>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap items-center bg-slate-50 border border-slate-200 rounded-lg p-3">
              <select value={docType} onChange={e => setDocType(e.target.value)}
                className="text-sm border border-slate-300 rounded px-2 py-1.5 bg-white" data-testid="mini-doc-type-intl">
                <option value="payment_proof">Payment Receipt / Screenshot *</option>
                {DOC_TYPES.map(d => <option key={d.id} value={d.id}>{d.label}{d.required ? ' *' : ''}</option>)}
              </select>
              <label className="cursor-pointer">
                <input type="file" className="hidden" onChange={handleFile} disabled={uploading} data-testid="mini-upload-input-intl" />
                <span className="inline-flex items-center gap-1.5 bg-[#2a777a] hover:bg-[#236466] text-white text-sm font-medium px-3 py-1.5 rounded transition">
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  {uploading ? 'Uploading…' : 'Upload Document'}
                </span>
              </label>
              <Button variant="outline" size="sm" onClick={onOpenScanner} className="text-xs">
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
                  Once you've uploaded your payment proof and documents, click Submit for Review. Your partner will verify your transfer and documents together.
                </p>
                <Button onClick={handleSubmitForReview} disabled={submitting || docs.length === 0}
                  className="mt-3 bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="mini-submit-review-intl">
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                  Submit for Review
                </Button>
              </div>
            </div>
          </Card>
        </>
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

{/* STAGE: Client picks a package */}
      {stage === 'awaiting_package_selection' && (
        <div className="space-y-6">
          <ClientOccupationReviewCard
            caseData={currentPa}
            onUpdated={async () => {
              await load();
              onRefresh?.();
            }}
            getAuthHeader={getAuth}
          />

          <Card className="p-6 border-[#2a777a]/20 space-y-5">
            {/* NEW — Pre-Assessment Report (uploaded by admin/partner) */}
            {docs.filter(d => d.uploaded_by_role === 'admin').length > 0 && (
              <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
                <p className="text-xs font-semibold text-teal-800 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> Your Pre-Assessment Report
                </p>
                <div className="space-y-2">
                  {docs.filter(d => d.uploaded_by_role === 'admin').map(d => (
                    <div
                      key={d.id}
                      className="w-full flex items-center gap-3 p-2.5 bg-white border border-teal-200 rounded-lg"
                      data-testid={`report-row-${d.id}`}
                    >
                      <FileCheck className="h-4 w-4 text-[#2a777a] shrink-0" />
                      <button
                        onClick={() => viewPaDocument(d.id)}
                        className="flex-1 min-w-0 text-left"
                        data-testid={`view-report-${d.id}`}
                      >
                        <p className="text-sm font-medium text-slate-700 truncate">{d.file_name}</p>
                        <p className="text-xs text-slate-500 capitalize">{(d.document_type || '').replace(/_/g, ' ')}</p>
                      </button>
                      <button
                        onClick={() => viewPaDocument(d.id)}
                        className="text-xs text-[#2a777a] font-semibold shrink-0 hover:underline"
                        data-testid={`view-btn-${d.id}`}
                      >
                        View
                      </button>
                      <button
                        onClick={() => downloadPaDocument(d.id, d.file_name)}
                        className="flex items-center gap-1 text-xs text-slate-600 font-semibold shrink-0 border border-slate-300 rounded px-2 py-1 hover:bg-slate-50"
                        data-testid={`download-btn-${d.id}`}
                      >
                        <Download className="h-3 w-3" /> Download
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-[#2a777a] rounded-full flex items-center justify-center shrink-0">
                <FileText className="h-6 w-6 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-lg">Choose Your Package</h3>
                <p className="text-sm text-slate-600 mt-1">
                  Review your pre-assessment report and pick the package that fits you best. Your partner will set up the payment plan once you select.
                </p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {(currentPa?.available_packages_snapshot || pa?.available_packages_snapshot || []).map((pkg) => (
                <Card key={pkg.id} className="p-4 border-2 border-slate-200 hover:border-[#2a777a] transition flex flex-col">
                  <h4 className="font-bold text-slate-800">{pkg.name}</h4>
                  <p className="text-2xl font-bold text-[#2a777a] mt-1">₹{Number(pkg.price || 0).toLocaleString('en-IN')}</p>
                  {pkg.description && <p className="text-xs text-slate-500 mt-2">{pkg.description}</p>}
                  {pkg.info_notes && (
                    <p className="text-xs text-slate-600 mt-2 bg-slate-50 rounded p-2 flex-1">{pkg.info_notes}</p>
                  )}
                  {pkg.document_name && (
                    <button
                      onClick={() => viewPackageDoc(pkg.document_url)}
                      className="text-xs text-[#2a777a] underline mt-2 text-left"
                    >
                      📄 View {pkg.document_name}
                    </button>
                  )}
                  <Button
                    onClick={() => handleSelectPackage(pkg.id)}
                    disabled={selectingPkg === pkg.id}
                    className="mt-4 bg-[#f7620b] hover:bg-[#e55a09] text-white"
                    data-testid={`select-package-${pkg.id}`}
                  >
                    {selectingPkg === pkg.id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                    Select this Package
                  </Button>
                </Card>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* STAGE: Package selected — waiting for partner to set payment method */}
      {stage === 'package_selected' && (
        <div className="space-y-6">
          <ClientOccupationReviewCard
            caseData={currentPa}
            onUpdated={async () => {
              await load();
              onRefresh?.();
            }}
            getAuthHeader={getAuth}
          />
          <Card className="p-6 bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center shrink-0">
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-lg">Package Selected: {currentPa?.selected_package_snapshot?.name || pa?.selected_package_snapshot?.name}</h3>
                <p className="text-sm text-slate-600 mt-1">
                  Your partner is now setting up the payment plan for this package. You'll be able to pay shortly.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* STAGE: Proposal received — full details + consent + pay */}
      {stage === 'proposal_sent' && (
        <div className="space-y-6">
          <ClientOccupationReviewCard
            caseData={currentPa}
            onUpdated={async () => {
              await load();
              onRefresh?.();
            }}
            getAuthHeader={getAuth}
          />
          <Card className="p-6 bg-gradient-to-br from-[#f7620b]/5 to-[#2a777a]/5 border-[#2a777a]/20 space-y-5">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-[#f7620b] rounded-full flex items-center justify-center shrink-0">
                <FileText className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <Badge className="bg-[#f7620b] text-white mb-2">Service Proposal — Please Review Carefully</Badge>
                <h3 className="font-bold text-slate-800 text-xl">Your Personalised Proposal</h3>
                <p className="text-xs text-slate-500 mt-1">Please review the proposal, pricing breakdown and terms before giving consent to pay.</p>
              </div>
            </div>

            {/* AI / partner-written proposal text */}
            {(currentPa?.proposal_ai_text || pa?.proposal_ai_text) && (
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Proposal Details</p>
                <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{currentPa?.proposal_ai_text || pa?.proposal_ai_text}</p>
              </div>
            )}

            {/* Pricing breakdown */}
            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Pricing Breakdown</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-600">Base Service Fee</span>
                <span className="font-semibold text-slate-800">₹{(pa.proposal_base_fee ?? pa.proposal_fee ?? 0).toLocaleString('en-IN')}</span>
              </div>
              {(pa.proposal_coupon_discount_amount || 0) > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Coupon Discount{pa.proposal_coupon_code ? ` (${pa.proposal_coupon_code})` : ''}</span>
                  <span>-₹{(pa.proposal_coupon_discount_amount || 0).toLocaleString('en-IN')}</span>
                </div>
              )}
              {(pa.proposal_gst_amount || 0) > 0 && (
                <div className="flex justify-between">
                  <span className="text-slate-600">GST (18%)</span>
                  <span className="font-semibold text-slate-800">₹{(pa.proposal_gst_amount || 0).toLocaleString('en-IN')}</span>
                </div>
              )}
              {(pa.proposal_promo_discount || 0) > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Promo applied{pa.proposal_promo_code ? ` (${pa.proposal_promo_code})` : ''}</span>
                  <span>-₹{(pa.proposal_promo_discount || 0).toLocaleString('en-IN')}</span>
                </div>
              )}
              {(pa.proposal_additional_discount || 0) > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Additional Discount</span>
                  <span>-₹{(pa.proposal_additional_discount || 0).toLocaleString('en-IN')}</span>
                </div>
              )}
              {(pa.proposal_upsells || []).length > 0 && (
                <div className="border-t border-slate-100 pt-2 mt-2">
                  <p className="text-xs text-slate-500 mb-1.5">Add-on Services:</p>
                  {(pa.proposal_upsells || []).map(u => (
                    <div key={u.id} className="flex justify-between text-[#f7620b]">
                      <span>+ {u.name}</span>
                      <span>+₹{(u.amount || 0).toLocaleString('en-IN')}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="border-t-2 border-slate-200 pt-2 mt-2 flex justify-between items-center">
                <span className="font-bold text-slate-800">Total Payable</span>
                <span className="text-2xl font-bold text-[#2a777a]" data-testid="client-total">₹{(pa.proposal_fee || 0).toLocaleString('en-IN')}</span>
              </div>
            </div>

            {/* Payment Method + Parts Schedule */}
            {(pa.proposal_payment_parts || []).length > 1 && (
              <div className="bg-white rounded-lg border border-slate-200 p-4" data-testid="client-payment-parts">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Payment Plan — {pa.proposal_payment_method_type === 'split_50_50' ? '50-50 Split' : 'Installments'}
                </p>
                <div className="space-y-2">
                  {pa.proposal_payment_parts.map((part) => (
                    <div key={part.index} className={`flex items-center justify-between p-2.5 rounded-lg border ${
                      part.status === 'paid' ? 'bg-emerald-50 border-emerald-200' :
                      part.status === 'pending' ? 'bg-amber-50 border-amber-200' :
                      'bg-slate-50 border-slate-200'
                    }`}>
                      <div className="flex items-center gap-2">
                        {part.status === 'paid' ? <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" /> :
                        part.status === 'pending' ? <Clock className="h-4 w-4 text-amber-600 shrink-0" /> :
                        part.status === 'pending_verification' ? <Clock className="h-4 w-4 text-blue-500 shrink-0" /> :
                        <AlertTriangle className="h-4 w-4 text-slate-400 shrink-0" />}
                        <div>
                          <p className="text-sm font-medium text-slate-700">{part.label}</p>
                          {part.due_date && <p className="text-[10px] text-slate-500">Due: {part.due_date}</p>}
                          {part.status === 'locked' && part.trigger_condition && (
                            <p className="text-[10px] text-slate-400 italic">Unlocks: {part.trigger_condition}</p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-slate-800">₹{Number(part.amount).toLocaleString('en-IN')}</p>
                        <Badge className={`text-[9px] ${
                          part.status === 'paid' ? 'bg-emerald-100 text-emerald-700' :
                          part.status === 'pending' ? 'bg-amber-100 text-amber-700' :
                          part.status === 'pending_verification' ? 'bg-blue-100 text-blue-700' :
                          'bg-slate-100 text-slate-500'
                        }`}>
                          {part.status === 'paid' ? 'Paid' : part.status === 'pending' ? 'Pay Now' :
                          part.status === 'pending_verification' ? 'Verifying' : 'Locked'}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex justify-between mt-3 pt-3 border-t border-slate-100 text-sm">
                  <span className="text-slate-500">Paid so far</span>
                  <span className="font-semibold text-emerald-700">₹{Number(pa.proposal_amount_paid || 0).toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Remaining</span>
                  <span className="font-semibold text-[#f7620b]">₹{Number(pa.proposal_amount_pending ?? pa.proposal_fee ?? 0).toLocaleString('en-IN')}</span>
                </div>
              </div>
            )}

            {pa.proposal_notes && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <p className="text-xs font-semibold text-slate-500 mb-1">Partner Note:</p>
                <p className="text-xs text-slate-600 italic">"{pa.proposal_notes}"</p>
              </div>
            )}
          </div>

          {/* Consent box — only after consent given → show Pay button */}
          {!pa.proposal_consent_given ? (
            <div className="bg-amber-50 border-2 border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-3 mb-3">
                <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                <div>
                  <h4 className="font-bold text-amber-900">Before You Pay — Confirmation Required</h4>
                  <p className="text-xs text-amber-800 mt-1">Please read and confirm the following before proceeding with payment:</p>
                </div>
              </div>
              <label className="flex items-start gap-2 cursor-pointer select-none">
                <input type="checkbox" checked={consentChecked} onChange={e => setConsentChecked(e.target.checked)}
                  className="mt-1 h-4 w-4 text-[#2a777a]" data-testid="consent-checkbox" />
                <span className="text-xs text-slate-700 leading-relaxed">
                  I confirm that I have <strong>read and understood</strong> the proposal details, pricing breakdown, and add-ons listed above.
                  I have had a <strong>final discussion with my partner</strong> and clarified my doubts.
                  I agree to the <strong>Service Level Agreement</strong> and acknowledge that the partner has NOT provided any misleading or incorrect information.
                  I voluntarily proceed with the payment of <strong>₹{(pa.proposal_fee || 0).toLocaleString('en-IN')}</strong> for the services described.
                </span>
              </label>
              <Button onClick={handleGiveConsent} disabled={!consentChecked || givingConsent}
                className="w-full mt-4 bg-amber-600 hover:bg-amber-700 text-white" data-testid="submit-consent">
                {givingConsent ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <CheckCircle2 className="h-4 w-4 mr-2" />}
                I Agree — Unlock Payment
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  <p className="text-xs font-semibold text-emerald-800">Consent recorded at {new Date(pa.proposal_consent_at).toLocaleString()}</p>
                </div>
                {(consentSummary?.reference_id || pa.proposal_consent_reference_id) && (
                  <p className="text-[11px] text-emerald-700">Reference ID: <span className="font-mono font-bold">{consentSummary?.reference_id || pa.proposal_consent_reference_id}</span> · A summary has been emailed to you (mock).</p>
                )}
              </div>
              {(() => {
                const parts = pa.proposal_payment_parts || [];
                const nextPart = parts.find(p => p.status === 'pending');
                const lockedPart = parts.find(p => p.status === 'locked');
                const verifyingPart = parts.find(p => p.status === 'pending_verification');
                const payAmount = nextPart ? nextPart.amount : (pa.proposal_amount_pending ?? pa.proposal_fee ?? 0);
                const isMultiPart = parts.length > 1;

                // International wire transfer claimed but not yet confirmed by partner
                if (verifyingPart) {
                  return (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                      <Clock className="h-6 w-6 text-blue-500 mx-auto mb-1" />
                      <p className="text-sm text-slate-700 font-medium">
                        {verifyingPart.label} — Payment claim submitted
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Your consultant is verifying your international transfer. This usually takes 1-2 business days.
                      </p>
                    </div>
                  );
                }

                if (!nextPart && lockedPart) {
                  return (
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center">
                      <Clock className="h-6 w-6 text-slate-400 mx-auto mb-1" />
                      <p className="text-sm text-slate-600">Next installment ({lockedPart.label}) is locked.</p>
                      <p className="text-xs text-slate-400 mt-1">Waiting on: {lockedPart.trigger_condition || 'admin approval'}</p>
                    </div>
                  );
                }

                return (
                  <div className="bg-white border border-slate-200 rounded-lg p-4">
                    {/* ── Domestic / International Tabs ── */}
                    <div className="flex gap-2 mb-4 p-1 bg-slate-100 rounded-lg">
                      <button
                        onClick={() => setProposalPayTab('domestic')}
                        className={`flex-1 py-2 rounded-md text-sm font-semibold transition ${
                          proposalPayTab === 'domestic' ? 'bg-white text-[#2a777a] shadow' : 'text-slate-500'
                        }`}
                      >
                        🇮🇳 Pay from India
                      </button>
                      <button
                        onClick={() => setProposalPayTab('international')}
                        className={`flex-1 py-2 rounded-md text-sm font-semibold transition ${
                          proposalPayTab === 'international' ? 'bg-white text-[#2a777a] shadow' : 'text-slate-500'
                        }`}
                      >
                        🌍 Pay from Outside India
                      </button>
                    </div>

                    {proposalPayTab === 'domestic' ? (
                      <>
                        <Button onClick={handlePayProposal} disabled={paying}
                          className="w-full bg-[#f7620b] hover:bg-[#e55a09] text-white text-base py-6" data-testid="mini-pay-proposal">
                          {paying ? <Loader2 className="h-5 w-5 animate-spin mr-2" /> : <CreditCard className="h-5 w-5 mr-2" />}
                          {isMultiPart && nextPart
                            ? `Pay ${nextPart.label} — ₹${Number(payAmount).toLocaleString('en-IN')}`
                            : `Pay ₹${Number(payAmount).toLocaleString('en-IN')}`}
                        </Button>
                        <p className="text-[10px] text-slate-400 text-center mt-2">🔒 Secured by Razorpay — Cards, UPI, Netbanking & Wallets accepted.</p>
                      </>
                    ) : (
                      <>
                        <div className="flex gap-1.5 mb-3 flex-wrap">
                          {INTL_COUNTRIES.map((c) => (
                            <button
                              key={c.code}
                              onClick={() => setProposalSelectedCountry(c.code)}
                              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                                proposalSelectedCountry === c.code
                                  ? 'bg-[#2a777a] text-white border-[#2a777a]'
                                  : 'bg-white text-slate-600 border-slate-300 hover:border-[#2a777a]'
                              }`}
                            >
                              {c.label}
                            </button>
                          ))}
                        </div>

                        {proposalBankLoading ? (
                          <div className="text-center py-6">
                            <Loader2 className="h-6 w-6 animate-spin text-[#2a777a] mx-auto mb-2" />
                            <p className="text-sm text-slate-500">Loading bank details…</p>
                          </div>
                        ) : proposalBankDetails ? (
                          <>
                            <p className="text-sm text-slate-700 mb-3">
                              Please transfer <strong>₹{Number(payAmount).toLocaleString('en-IN')}</strong>
                              {isMultiPart && nextPart ? ` (${nextPart.label})` : ''} via bank wire, then confirm below.
                            </p>
                            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1.5 text-sm mb-3">
                              <div className="flex justify-between"><span className="text-slate-500">Account Name</span><span className="font-medium">{proposalBankDetails.account_name}</span></div>
                              <div className="flex justify-between"><span className="text-slate-500">Account Number</span><span className="font-medium">{proposalBankDetails.account_number}</span></div>
                              <div className="flex justify-between"><span className="text-slate-500">IFSC / SWIFT</span><span className="font-medium">{proposalBankDetails.ifsc_or_swift}</span></div>
                              <div className="flex justify-between"><span className="text-slate-500">Bank Name</span><span className="font-medium">{proposalBankDetails.bank_name}</span></div>
                              <div className="flex justify-between"><span className="text-slate-500">Bank Address</span><span className="font-medium">{proposalBankDetails.bank_address}</span></div>
                            </div>
                            <input
                              type="text"
                              placeholder="Transaction Reference / UTR (optional)"
                              value={proposalTransferRef}
                              onChange={(e) => setProposalTransferRef(e.target.value)}
                              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-[#2a777a]"
                            />
                            <label className="block mb-3">
                              <span className="text-xs text-slate-500 mb-1 block">Attach Payment Screenshot / Receipt (optional)</span>
                              <input
                                type="file"
                                accept="image/*,.pdf"
                                onChange={(e) => setProposalProofFile(e.target.files?.[0] || null)}
                                className="w-full text-sm border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
                              />
                              {proposalProofFile && (
                                <span className="text-xs text-emerald-600 mt-1 block">✓ {proposalProofFile.name}</span>
                              )}
                            </label>
                            <Button onClick={handleProposalInternationalClaim} disabled={proposalClaiming}
                              className="w-full bg-[#2a777a] hover:bg-[#1d5658] text-white font-semibold py-6">
                              {proposalClaiming ? <Loader2 className="h-5 w-5 animate-spin mr-2" /> : null}
                              I've Made the Transfer
                            </Button>
                            <p className="text-[10px] text-slate-400 text-center mt-2">
                              Your consultant will manually verify this transfer and confirm within 1-2 business days.
                            </p>
                          </>
                        ) : (
                          <p className="text-sm text-slate-500 text-center py-6">Unable to load bank details.</p>
                        )}
                      </>
                    )}
                  </div>
                );
              })()}
            </div>
          )}
        </Card>
      </div>
    )}

      {/* STAGE: proposal_paid — awaiting partner to upload receipt */}
      {stage === 'proposal_paid' && (
        <Card className="p-6 bg-gradient-to-br from-blue-50 to-white border-blue-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center shrink-0">
              <Clock className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-lg">Payment Received 🎉</h3>
              <p className="text-sm text-slate-600 mt-1">
                Thank you! Your partner is preparing the payment receipt, signed agreement, and basic onboarding documents. Once submitted, our admin team will activate your case.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* E-SIGN Agreement (shown once main fee paid) — uses partner-generated agreement if available, else falls back to generic canvas */}
      {['proposal_paid', 'awaiting_final_approval', 'case_created'].includes(stage) && pa.active_agreement_id && (
        <ClientAgreementSigning paId={pa.id} onSigned={() => load()} />
      )}

      {/* Generic E-Sign fallback (only when no template-based agreement exists yet) */}
      {['proposal_paid', 'awaiting_final_approval', 'case_created'].includes(stage) && !pa.active_agreement_id && !esignRec && (
        <Card className="p-6 border-amber-200 bg-gradient-to-br from-amber-50 to-white" data-testid="esign-card">
          <div className="flex items-start gap-3 mb-3">
            <div className="h-10 w-10 bg-amber-100 rounded-full flex items-center justify-center shrink-0">
              <FileCheck className="h-5 w-5 text-amber-700" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800">E-Sign Your Service Agreement</h3>
              <p className="text-xs text-slate-600">Your partner is preparing a country-specific service agreement. In the meantime you can pre-sign a generic placeholder.</p>
            </div>
          </div>
          <SignatureCanvas onSigned={handleSaveSignature} disabled={savingSig} />
        </Card>
      )}

      {/* Signed confirmation */}
      {esignRec && (
        <Card className="p-4 border-emerald-200 bg-emerald-50" data-testid="esign-done">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-emerald-900">Agreement e-signed by {esignRec.typed_name}</p>
              <p className="text-[11px] text-emerald-700">Signed on {new Date(esignRec.signed_at).toLocaleString()} · IP {esignRec.ip_address || 'n/a'}</p>
            </div>
            {esignRec.signature_data_url && (
              <img src={esignRec.signature_data_url} alt="Signature" className="h-10 bg-white border border-emerald-200 rounded" />
            )}
          </div>
        </Card>
      )}

      {/* Payment history + Doc downloads (post-payment) */}
     {/* Payment history + Doc downloads — also show once at least 1 installment is paid */}
      {(['proposal_paid', 'awaiting_final_approval', 'case_created'].includes(stage)
        || (pa.proposal_amount_paid || 0) > 0) && (
        <Card className="p-5 border-slate-200" data-testid="client-payment-history">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 className="text-sm font-semibold text-slate-800">Your Payment Records</h3>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => downloadDoc('proposal')} className="h-7 text-xs" data-testid="client-dl-proposal">
                <Download className="h-3 w-3 mr-1" /> Proposal
              </Button>
              <Button variant="outline" size="sm" onClick={() => downloadDoc('invoice')} className="h-7 text-xs" data-testid="client-dl-invoice">
                <Download className="h-3 w-3 mr-1" /> Invoice
              </Button>
            </div>
          </div>
          <PaymentHistoryTimeline scope="pa" id={pa.id} />
        </Card>
      )}

      {/* STAGE: awaiting_final_approval — admin working on it */}
      {stage === 'awaiting_final_approval' && (
        <Card className="p-6 bg-gradient-to-br from-leamss-teal-50 to-white border-leamss-teal-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-leamss-teal-100 rounded-full flex items-center justify-center shrink-0">
              <Clock className="h-6 w-6 text-leamss-teal-600" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-lg">Activating Your Case</h3>
              <p className="text-sm text-slate-600 mt-1">
                All documents received! Our admin team is creating your case file and will assign a dedicated case manager within 24 hours.
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
