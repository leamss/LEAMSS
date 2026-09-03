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
import ClientPaymentModal from '@/components/ClientPaymentModal';

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
  { key: 'paid', label: 'Payment Done', stages: ['payment_received', 'partner_review', 'documents_submitted', 'under_review', 'approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'uploading', label: 'Upload Documents', stages: ['partner_review', 'documents_submitted', 'under_review', 'approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'reviewing', label: 'Under Review', stages: ['documents_submitted', 'under_review', 'approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'approved', label: 'Approved', stages: ['approved', 'awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'proposal', label: 'Proposal & Signing', stages: ['awaiting_package_selection', 'package_selected', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
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
  const [installmentModalData, setInstallmentModalData] = useState({ open: false, data: null });
  const [appliedPromo, setAppliedPromo] = useState(null);
  const [promoInput, setPromoInput] = useState('');
  const [validatingPromo, setValidatingPromo] = useState(false);

  // Auto-fill assigned promo if partner forwarded it
  useEffect(() => {
    const defaultCode = pa?.assigned_promo_code || pa?.proposal_promo_code || pa?.proposal_coupon_code;
    if (defaultCode && !promoInput) {
      setPromoInput(defaultCode);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pa?.assigned_promo_code, pa?.proposal_promo_code, pa?.proposal_coupon_code]);

  const handleApplyPromo = async (codeToApply) => {
    const code = (codeToApply || promoInput || '').trim().toUpperCase();
    if (!code) {
      toast.error('Please enter a promo code');
      return;
    }
    setValidatingPromo(true);
    try {
      const baseFee = pa.proposal_base_fee ?? pa.proposal_fee ?? 0;
      const res = await axios.post(`${API}/marketing/promo/public-validate`, {
        code,
        amount: baseFee,
      });
      if (res.data.valid) {
        setPromoInput(code);
        setAppliedPromo({
          code,
          discount_amount: res.data.discount_amount,
          final_amount: res.data.final_amount,
          discount_type: res.data.discount_type,
          discount_value: res.data.discount_value,
        });
        toast.success(`Promo code ${code} applied! Saved ₹${Number(res.data.discount_amount).toLocaleString('en-IN')}`);
      } else {
        toast.error(res.data.message || 'Invalid promo code');
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Invalid or expired promo code');
    } finally {
      setValidatingPromo(false);
    }
  };

  const handleRemovePromo = () => {
    setAppliedPromo(null);
    toast.info('Promo code removed');
  };

  const INTL_COUNTRIES = [
    { code: 'Australia', label: '🇦🇺 AUS' },
    { code: 'Canada', label: '🇨🇦 Canada' },
    { code: 'USA', label: '🇺🇸 USA' },
    { code: 'UK', label: '🇬🇧 UK' },
    { code: 'New Zealand', label: '🇳🇿 NZ' },
  ];

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
    try {
      const r = await axios.get(`${API}/pre-assess-portal/client/consent-summary/${pa.id}`, getAuth());
      if (r.data.exists) setConsentSummary(r.data.record);
    } catch (e) { /* silent */ }
  }, [pa.id]);

  const loadEsign = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/proposal-docs/${pa.id}/esign`, getAuth());
      if (r.data.signed) setEsignRec(r.data.record);
    } catch (e) { /* silent */ }
  }, [pa.id]);

  useEffect(() => {
    if (pa.proposal_consent_given) loadConsentSummary();
    if (['proposal_paid', 'awaiting_final_approval', 'case_created'].includes(pa.stage)) loadEsign();
  }, [pa.proposal_consent_given, pa.stage, loadConsentSummary, loadEsign]);

  const handleSaveSignature = async (dataUrl, meta) => {
    setSavingSig(true);
    try {
      const r = await axios.post(`${API}/proposal-docs/${pa.id}/esign`, {
        signature_data_url: dataUrl,
        typed_name: meta.typed_name,
        consent_text: 'I electronically sign this service agreement',
        biometric_packet: meta.biometric_packet || null,
      }, getAuth());
      toast.success('Agreement e-signed · ' + new Date(r.data.signed_at).toLocaleString());
      await loadEsign();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Sign failed'); }
    setSavingSig(false);
  };

  const downloadDoc = async (kind) => {
    try {
      const r = await fetch(`${API}/proposal-docs/${pa.id}/${kind}.pdf`, {
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
    setSelectingPkg(packageId);
    try {
      const paId = pa?.id || pa?._id;
      const authToken = localStorage.getItem('token');
      if (authToken && paId) {
        await axios.post(`${API}/pre-assess-portal/client/select-package/${paId}`, { package_id: packageId }, getAuth());
      } else if (pa?.public_token || pa?.share_token) {
        const token = pa.public_token || pa.share_token;
        await axios.post(`${API}/pre-assess-portal/public/select-package/${token}`, { package_id: packageId });
      } else if (paId) {
        await axios.post(`${API}/pre-assess-portal/client/select-package/${paId}`, { package_id: packageId }, getAuth());
      } else {
        throw new Error('Pre-assessment identifier not found');
      }
      toast.success('Package selected! Your partner will set up the payment plan.');
      onRefresh?.();
    } catch (e) {
      console.error('Failed to select package:', e);
      toast.error(e?.response?.data?.detail || e?.message || 'Failed to select package');
    } finally {
      setSelectingPkg(null);
    }
  };

  const viewPackageDoc = async (documentUrl) => {
    if (!documentUrl) return;
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}${documentUrl}`, {
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
      const activePromoCode = appliedPromo ? appliedPromo.code : null;
      // Step 1: Backend creates Razorpay order with promo discount (only if applied)
      const orderRes = await axios.post(`${API}/pre-assess-portal/client/proposal/create-order/${pa.id}`, {
        promo_code: activePromoCode
      }, getAuth());
      const { order_id, amount, currency, key_id, client_name, client_email, client_mobile } = orderRes.data;

      // Step 2: Razorpay Checkout Popup
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
              order_id: response.razorpay_order_id || order_id,
              payment_id: response.razorpay_payment_id || response.payment_id || '',
              signature: response.razorpay_signature || response.signature || '',
              promo_code: activePromoCode
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
            {(pa.available_packages_snapshot || []).map((pkg) => (
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
      )}

      {/* STAGE: Package selected — waiting for partner to set payment method */}
      {stage === 'package_selected' && (
        <Card className="p-6 bg-gradient-to-br from-emerald-50 to-white border-emerald-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center shrink-0">
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            </div>
<div>
              <h3 className="font-bold text-slate-800 text-lg">Package Selected: {pa.selected_package_snapshot?.name}</h3>
              <p className="text-sm text-slate-600 mt-1">
                Your partner is now setting up the payment plan for this package. You'll be able to pay shortly.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* STAGE: Proposal received — full details + consent + pay */}
      {stage === 'proposal_sent' && (() => {
        const isAnyPartPaid = (pa?.proposal_payment_parts || []).some(p => p.status === 'paid') || (pa?.proposal_amount_paid || 0) > 0;
        const sharedPromoCode = (pa?.assigned_promo_code || pa?.proposal_promo_code || pa?.proposal_coupon_code || '').trim();
        const isPromoShared = Boolean(sharedPromoCode && pa?.promo_enabled !== false);

        // Promo is active ONLY IF client applied it in UI or if already paid with promo
        const isPromoActive = Boolean(appliedPromo || (isAnyPartPaid && (pa?.promo_code_used || pa?.proposal_promo_code)));
        const promoCodeUsed = appliedPromo ? appliedPromo.code : (isAnyPartPaid ? (pa?.promo_code_used || pa?.proposal_promo_code) : null);

        const baseServiceFee = pa?.proposal_base_fee ?? pa?.proposal_fee ?? 0;
        const paDeduction = (pa?.proposal_deduct_pa_fee || pa?.deduct_pre_assessment_fee) ? (Number(pa?.proposal_pa_deduction) || 5100) : 0;
        const isGstApplicable = Boolean(pa?.proposal_gst_included || (pa?.proposal_gst_amount || 0) > 0);

        const promoDiscountVal = appliedPromo
          ? Number(appliedPromo.discount_amount || 0)
          : (isAnyPartPaid && (pa?.promo_code_used || pa?.proposal_promo_code) ? (pa?.proposal_promo_discount || Math.round(baseServiceFee * 0.1)) : 0);

        const discountedBaseFee = Math.max(0, baseServiceFee - promoDiscountVal - paDeduction);
        const proposalGstVal = isGstApplicable ? Math.round(discountedBaseFee * 0.18) : 0;
        const undiscountedBaseFee = Math.max(0, baseServiceFee - paDeduction);
        const undiscountedGstVal = isGstApplicable ? Math.round(undiscountedBaseFee * 0.18) : 0;
        const effectiveTotalProposal = isPromoActive
          ? (discountedBaseFee + proposalGstVal)
          : (undiscountedBaseFee + undiscountedGstVal);

        const rawPartsList = pa?.proposal_payment_parts || [];
        const dynamicParts = isAnyPartPaid
          ? rawPartsList
          : rawPartsList.map((part) => {
              if (rawPartsList.length === 1 || pa?.proposal_payment_method_type === 'full_payment') {
                return { ...part, amount: effectiveTotalProposal };
              }
              if (rawPartsList.length === 2 && pa?.proposal_payment_method_type === 'split_50_50') {
                const part1Amt = Math.round(effectiveTotalProposal / 2);
                const partAmt = part.index === 0 ? part1Amt : Math.max(0, effectiveTotalProposal - part1Amt);
                return { ...part, amount: partAmt };
              }
              if (isPromoActive && rawPartsList.length > 0) {
                const originalTotal = (undiscountedBaseFee + undiscountedGstVal) || 1;
                const ratio = effectiveTotalProposal / originalTotal;
                return { ...part, amount: Math.round(part.amount * ratio) };
              }
              return part;
            });

        const nextPart = dynamicParts.find(p => p.status === 'pending');
        const lockedPart = dynamicParts.find(p => p.status === 'locked');
        const verifyingPart = dynamicParts.find(p => p.status === 'pending_verification');
        const payAmount = nextPart ? nextPart.amount : effectiveTotalProposal;
        const isMultiPart = dynamicParts.length > 1;

        return (
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
            {pa?.proposal_ai_text && (
              <div className="bg-white rounded-lg border border-slate-200 p-4">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Proposal Details</p>
                <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{pa.proposal_ai_text}</p>
              </div>
            )}

            {/* 🏷️ Partner Promo Banner / Client Promo Card */}
            {isAnyPartPaid ? (
              promoCodeUsed ? (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">🏷️</span>
                    <div>
                      <p className="text-sm font-bold text-emerald-950 flex items-center gap-2">
                        <span>Promo Code Applied:</span>
                        <span className="font-mono bg-white text-emerald-800 px-2.5 py-0.5 rounded border border-emerald-300 font-bold">
                          {promoCodeUsed}
                        </span>
                      </p>
                      <p className="text-xs text-emerald-700 mt-0.5">
                        Discount of ₹{promoDiscountVal.toLocaleString('en-IN')} has been applied to your payment plan.
                      </p>
                    </div>
                  </div>
                  <Badge className="bg-emerald-600 text-white font-bold text-xs px-3 py-1">Applied & Active ✓</Badge>
                </div>
              ) : null
            ) : (
              (isPromoShared || appliedPromo) && (
                <div className="bg-white rounded-xl border border-emerald-200 p-4 space-y-3 shadow-xs" data-testid="proposal-promo-section">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">🏷️</span>
                      <h4 className="text-sm font-bold text-slate-800">Promo Code & Discount Offer</h4>
                    </div>
                    {appliedPromo ? (
                      <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2.5 py-0.5 rounded-full border border-emerald-300">
                        Active & Applied ✓
                      </span>
                    ) : (
                      <span className="text-xs bg-amber-100 text-amber-800 font-bold px-2.5 py-0.5 rounded-full border border-amber-300">
                        Partner Special Offer Available
                      </span>
                    )}
                  </div>

                  {isPromoShared && !appliedPromo && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5">
                      <div>
                        <p className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                          <span>Special Offer from your Partner:</span>
                          <span className="font-mono bg-white text-emerald-800 px-2 py-0.5 rounded border border-emerald-300 font-bold">
                            {sharedPromoCode}
                          </span>
                        </p>
                        <p className="text-[11px] text-emerald-700 mt-0.5">
                          Your partner shared this promo code. Click Apply to deduct the discount from your service fee.
                        </p>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleApplyPromo(sharedPromoCode)}
                        disabled={validatingPromo}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-8 px-4 shrink-0 shadow-sm"
                        data-testid="apply-partner-promo-btn"
                      >
                        {validatingPromo ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                        Apply Code
                      </Button>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Enter promo code (e.g. SUMMER2026)"
                      value={promoInput}
                      onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
                      className="flex-1 uppercase font-mono border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                      data-testid="proposal-promo-input"
                    />
                    {appliedPromo ? (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={handleRemovePromo}
                        className="text-rose-600 border-rose-200 hover:bg-rose-50 text-xs font-semibold px-3"
                      >
                        Remove
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        onClick={() => handleApplyPromo(promoInput)}
                        disabled={validatingPromo || !promoInput.trim()}
                        className="bg-[#1f4d44] hover:bg-[#163832] text-white text-xs font-bold px-4"
                        data-testid="apply-promo-btn"
                      >
                        {validatingPromo ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : 'Apply'}
                      </Button>
                    )}
                  </div>

                  {appliedPromo && (
                    <p className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Promo <strong>{appliedPromo.code}</strong> applied — Saved ₹{appliedPromo.discount_amount.toLocaleString('en-IN')}!
                    </p>
                  )}
                </div>
              )
            )}

            {/* Pricing breakdown */}
            <div className="bg-white rounded-lg border border-slate-200 p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Pricing Breakdown</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Base Service Fee</span>
                  <span className="font-semibold text-slate-800">₹{baseServiceFee.toLocaleString('en-IN')}</span>
                </div>
                {paDeduction > 0 && (
                  <div className="flex justify-between text-emerald-700 font-semibold" data-testid="pre-assessment-deduction-row">
                    <span className="flex items-center gap-1.5">
                      <span>Pre-Assessment Fee Paid</span>
                      <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-bold">Deducted ✓</span>
                    </span>
                    <span>-₹{paDeduction.toLocaleString('en-IN')}</span>
                  </div>
                )}
                {promoDiscountVal > 0 && isPromoActive && (
                  <div className="flex justify-between text-emerald-700 font-semibold">
                    <span>Promo Discount ({promoCodeUsed || 'Applied'})</span>
                    <span>-₹{promoDiscountVal.toLocaleString('en-IN')}</span>
                  </div>
                )}
                {proposalGstVal > 0 && (
                  <div className="flex justify-between">
                    <span className="text-slate-600">GST (18%)</span>
                    <span className="font-semibold text-slate-800">₹{proposalGstVal.toLocaleString('en-IN')}</span>
                  </div>
                )}
                {(pa?.proposal_additional_discount || 0) > 0 && (
                  <div className="flex justify-between text-emerald-700">
                    <span>Additional Discount</span>
                    <span>-₹{(pa.proposal_additional_discount || 0).toLocaleString('en-IN')}</span>
                  </div>
                )}
                {(pa?.proposal_upsells || []).length > 0 && (
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
                  <div className="text-right">
                    {promoDiscountVal > 0 && isPromoActive && (
                      <span className="text-xs text-slate-400 line-through mr-2">
                        ₹{(undiscountedBaseFee + undiscountedGstVal).toLocaleString('en-IN')}
                      </span>
                    )}
                    <span className="text-2xl font-bold text-[#2a777a]" data-testid="client-total">
                      ₹{effectiveTotalProposal.toLocaleString('en-IN')}
                    </span>
                  </div>
                </div>
              </div>

              {/* Payment Method + Parts Schedule */}
              {dynamicParts.length > 1 && (
                <div className="bg-white rounded-lg border border-slate-200 p-4 mt-4" data-testid="client-payment-parts">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                    Payment Plan — {pa?.proposal_payment_method_type === 'split_50_50' ? '50-50 Split' : 'Installments'}
                  </p>
                  <div className="space-y-2">
                    {dynamicParts.map((part) => (
                      <div key={part.index}
                        className={`p-3 rounded-lg border flex items-center justify-between ${
                          part.status === 'paid' ? 'bg-emerald-50/50 border-emerald-200' :
                          part.status === 'pending' ? 'bg-amber-50/50 border-amber-200' :
                          part.status === 'pending_verification' ? 'bg-blue-50/50 border-blue-200' :
                          'bg-slate-50 border-slate-200'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
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
                        <div className="text-right flex items-center gap-2">
                          <p className="text-sm font-bold text-slate-800">₹{Number(part.amount).toLocaleString('en-IN')}</p>
                          {part.status === 'pending' ? (
                            <Button
                              size="sm"
                              onClick={() => setInstallmentModalData({
                                open: true,
                                data: {
                                  paId: pa.id,
                                  saleId: pa.sale_id,
                                  part: part,
                                  amount: part.amount,
                                  promoCode: promoCodeUsed,
                                  discountAmount: promoDiscountVal,
                                  productName: pa.product_name || 'PR Journey & Immigration',
                                  partnerName: pa.partner_name || 'LEAMSS Consultant',
                                  clientName: pa.client_name || 'Client',
                                  destination: pa.country || 'Australia',
                                  serviceType: pa.service_type || 'PR',
                                  pa: pa
                                }
                              })}
                              className="bg-[#f7620b] hover:bg-[#e0580a] text-white h-7 text-xs font-semibold px-2.5 shadow-sm"
                              data-testid={`pay-part-${part.index}-btn`}
                            >
                              Pay Now
                            </Button>
                          ) : (
                            <Badge className={`text-[9px] ${
                              part.status === 'paid' ? 'bg-emerald-100 text-emerald-700' :
                              part.status === 'pending_verification' ? 'bg-blue-100 text-blue-700' :
                              'bg-slate-100 text-slate-500'
                            }`}>
                              {part.status === 'paid' ? 'Paid' :
                              part.status === 'pending_verification' ? 'Verifying' : 'Locked'}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between mt-3 pt-3 border-t border-slate-100 text-sm">
                    <span className="text-slate-500">Paid so far</span>
                    <span className="font-semibold text-emerald-700">₹{Number(pa?.proposal_amount_paid || 0).toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Remaining</span>
                    <span className="font-semibold text-[#f7620b]">₹{Number(pa?.proposal_amount_pending ?? (effectiveTotalProposal - (pa?.proposal_amount_paid || 0))).toLocaleString('en-IN')}</span>
                  </div>
                </div>
              )}

              {pa?.proposal_notes && (
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <p className="text-xs font-semibold text-slate-500 mb-1">Partner Note:</p>
                  <p className="text-xs text-slate-600 italic">"{pa.proposal_notes}"</p>
                </div>
              )}
            </div>

            {/* Consent box — only after consent given → show Pay button */}
            {!pa?.proposal_consent_given ? (
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
                    I voluntarily proceed with the payment of <strong>₹{effectiveTotalProposal.toLocaleString('en-IN')}</strong> for the services described.
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

                {verifyingPart ? (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                    <Clock className="h-6 w-6 text-blue-500 mx-auto mb-1" />
                    <p className="text-sm text-slate-700 font-medium">
                      {verifyingPart.label} — Payment claim submitted
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Your consultant is verifying your international transfer. This usually takes 1-2 business days.
                    </p>
                  </div>
                ) : !nextPart && lockedPart ? (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center">
                    <Clock className="h-6 w-6 text-slate-400 mx-auto mb-1" />
                    <p className="text-sm text-slate-600">Next installment ({lockedPart.label}) is locked.</p>
                    <p className="text-xs text-slate-400 mt-1">Waiting on: {lockedPart.trigger_condition || 'admin approval'}</p>
                  </div>
                ) : (
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
                )}
              </div>
            )}
          </Card>
        );
      })()}

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

      {/* Pending / Unlocked Installment Action Banner */}
      {(() => {
        const baseServiceFee = pa.proposal_base_fee ?? pa.proposal_fee ?? 0;
        const promoDiscountVal = appliedPromo ? appliedPromo.discount_amount : 0;
        const discountedBaseFee = Math.max(0, baseServiceFee - promoDiscountVal);
        const isGstApplicable = Boolean(pa.proposal_gst_included || (pa.proposal_gst_amount || 0) > 0);
        const proposalGstVal = isGstApplicable ? Math.round(discountedBaseFee * 0.18) : 0;
        const effectiveTotalProposal = discountedBaseFee + proposalGstVal;

        const rawPartsList = pa.proposal_payment_parts || [];
        const dynamicParts = rawPartsList.map((part) => {
          if (rawPartsList.length === 2 && pa.proposal_payment_method_type === 'split_50_50') {
            const part1Amt = Math.round(effectiveTotalProposal / 2);
            const partAmt = part.index === 0 ? part1Amt : Math.max(0, effectiveTotalProposal - part1Amt);
            return { ...part, amount: partAmt };
          }
          if (appliedPromo && rawPartsList.length > 0) {
            const originalTotal = (baseServiceFee + (isGstApplicable ? Math.round(baseServiceFee * 0.18) : 0)) || 1;
            const ratio = effectiveTotalProposal / originalTotal;
            return { ...part, amount: Math.round(part.amount * ratio) };
          }
          return part;
        });

        const nextPending = dynamicParts.find(p => p.status === 'pending');
        if (stage === 'proposal_sent' || !nextPending) return null;
        return (
          <Card className="p-5 bg-gradient-to-r from-amber-50 to-orange-50 border-amber-300 shadow-sm" data-testid="unlocked-installment-card">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 bg-[#f7620b]/10 rounded-full flex items-center justify-center text-[#f7620b] shrink-0 font-bold">
                  <CreditCard className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-base font-bold text-slate-800">{nextPending.label} is Ready for Payment</h4>
                  <p className="text-xs text-slate-600">Pending Amount: <strong className="text-[#f7620b] font-bold">₹{Number(nextPending.amount).toLocaleString('en-IN')}</strong> (incl. GST)</p>
                </div>
              </div>
              <Button
                onClick={() => setInstallmentModalData({
                  open: true,
                  data: {
                    paId: pa.id,
                    saleId: pa.sale_id,
                    part: nextPending,
                    amount: nextPending.amount,
                    promoCode: appliedPromo ? appliedPromo.code : null,
                    discountAmount: promoDiscountVal,
                    productName: pa.product_name || 'PR Journey & Immigration',
                    partnerName: pa.partner_name || 'LEAMSS Consultant',
                    clientName: pa.client_name || 'Client',
                    destination: pa.country || 'Australia',
                    serviceType: pa.service_type || 'PR',
                    pa: pa
                  }
                })}
                className="bg-[#f7620b] hover:bg-[#e0580a] text-white font-bold px-6 py-2.5 text-sm shadow-md rounded-xl"
                data-testid="pay-unlocked-part-btn"
              >
                <CreditCard className="h-4 w-4 mr-1.5" /> Pay Now
              </Button>
            </div>
          </Card>
        );
      })()}

      {/* Access level hint */}
      {access && (
        <p className="text-center text-xs text-slate-400">
          Portal access level: <span className="font-semibold text-slate-500 capitalize">{access.access_level}</span>
          {' · '}Current stage: <span className="font-semibold text-slate-500">{stage.replace(/_/g, ' ')}</span>
        </p>
      )}

      {/* Installment Payment Modal with exact First Payment UI */}
      <ClientPaymentModal
        open={installmentModalData.open}
        onClose={() => setInstallmentModalData({ open: false, data: null })}
        paymentData={installmentModalData.data}
        onSuccess={() => {
          load();
          onRefresh?.();
        }}
      />
    </div>
  );
}
