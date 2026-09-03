import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  CreditCard,
  Globe,
  Loader2,
  CheckCircle2,
  Clock,
  Sparkles,
  Copy,
  X,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const API = `${BACKEND_URL}/api`;

const INTL_COUNTRIES = [
  { code: 'Australia', label: '🇦🇺 AUS' },
  { code: 'Canada', label: '🇨🇦 Canada' },
  { code: 'USA', label: '🇺🇸 USA' },
  { code: 'UK', label: '🇬🇧 UK' },
  { code: 'New Zealand', label: '🇳🇿 NZ' },
];

export default function ClientPaymentModal({
  open,
  onClose,
  paymentData,
  onSuccess,
}) {
  const [activeTab, setActiveTab] = useState('domestic'); // 'domestic' | 'international'
  const [selectedCountry, setSelectedCountry] = useState('Australia');
  const [bankDetails, setBankDetails] = useState(null);
  const [bankLoading, setBankLoading] = useState(false);
  const [paying, setPaying] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const [transferRef, setTransferRef] = useState('');
  const [proofFile, setProofFile] = useState(null);
  const [claimSuccess, setClaimSuccess] = useState(false);

  // Promo code state
  // Promo code state
  const proposalPromoCode = (
    paymentData?.proposal?.promo_code ||
    paymentData?.proposal?.assigned_promo_code ||
    paymentData?.pa?.proposal_promo_code ||
    paymentData?.pa?.assigned_promo_code ||
    paymentData?.promoCode ||
    ''
  ).trim();

  const [promoInput, setPromoInput] = useState('');
  const [appliedPromo, setAppliedPromo] = useState(null);
  const [promoLoading, setPromoLoading] = useState(false);

  const saleId = paymentData?.saleId || paymentData?.proposal?.id || paymentData?.pa?.sale_id;
  const paId = paymentData?.paId || paymentData?.pa?.id;
  const caseId = paymentData?.caseId || paymentData?.case_id;
  const originalAmount = Number(paymentData?.amount || paymentData?.part?.amount || paymentData?.proposal?.pending_amount || paymentData?.pa?.proposal_amount_pending || 0);
  const productName = paymentData?.productName || paymentData?.proposal?.product_name || paymentData?.pa?.product_name || 'PR Journey & Immigration';
  const partnerName = paymentData?.partnerName || paymentData?.proposal?.partner_name || paymentData?.pa?.partner_name || 'LEAMSS Consultant';
  const clientName = paymentData?.clientName || paymentData?.proposal?.client_name || paymentData?.pa?.client_name || 'Client';
  const destination = paymentData?.destination || paymentData?.proposal?.country || paymentData?.pa?.country || 'Australia';
  const serviceType = paymentData?.serviceType || paymentData?.proposal?.service_type || paymentData?.pa?.service_type || 'PR';
  const partIndex = paymentData?.part?.index;
  const partLabel = paymentData?.part?.label || (paymentData?.part?.index === 1 ? '2nd Installment (50%)' : paymentData?.part?.index === 0 ? '1st Installment (50%)' : 'Milestone Installment');
  const isSubsequentInstallment = (typeof partIndex === 'number' && partIndex > 0) ||
    /2nd|3rd|4th|second|third|final installment/i.test(partLabel || '');
  const showPromoSection = !isSubsequentInstallment;

  // Dynamic calculations with promo code
  const discountAmount = (appliedPromo && showPromoSection) ? Number(appliedPromo.discount_amount || 0) : 0;
  const finalPayable = Math.max(1, originalAmount - discountAmount);
  const baseFee = Math.round((finalPayable / 1.18) * 100) / 100;
  const gstFee = Math.round((finalPayable - baseFee) * 100) / 100;

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  });

  const handleApplyPromo = async (codeToUse) => {
    const code = (codeToUse || promoInput || '').trim().toUpperCase();
    if (!code) {
      toast.error('Please enter a promo code');
      return;
    }
    setPromoLoading(true);
    try {
      let res;
      try {
        res = await axios.post(`${API}/marketing/promo/validate`, {
          code,
          amount: originalAmount,
        }, getAuthHeader());
      } catch (authErr) {
        if (authErr?.response?.status === 401 || !localStorage.getItem('token')) {
          res = await axios.post(`${API}/marketing/promo/public-validate`, {
            code,
            amount: originalAmount,
          });
        } else {
          throw authErr;
        }
      }

      if (res.data?.valid) {
        setAppliedPromo(res.data);
        setPromoInput(res.data.code);
        toast.success(`Promo code applied! ${res.data.message || ''}`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Invalid promo code');
    } finally {
      setPromoLoading(false);
    }
  };

  const handleRemovePromo = () => {
    setAppliedPromo(null);
    setPromoInput('');
    toast.info('Promo code removed');
  };

  // Fetch bank details when international tab or country changes
  useEffect(() => {
    if (!open || activeTab !== 'international') return;
    setBankLoading(true);
    setBankDetails(null);
    axios
      .get(`${API}/payments/bank-details`, {
        params: { country: selectedCountry },
        ...getAuthHeader(),
      })
      .then((r) => setBankDetails(r.data))
      .catch(() => {
        // Fallback default bank details
        setBankDetails({
          country: selectedCountry,
          account_name: 'LEAMSS Immigration Services Pvt Ltd',
          account_number: '921020048192841',
          ifsc_or_swift: 'UTIB0000123 / AXISINBB',
          bank_name: 'Axis Bank Ltd',
          bank_address: 'Connaught Place Branch, New Delhi, India',
          currency: 'INR',
        });
      })
      .finally(() => setBankLoading(false));
  }, [open, activeTab, selectedCountry]);

  // Reset / initialize states on modal close/open
  useEffect(() => {
    if (open) {
      setClaimSuccess(false);
      setTransferRef('');
      setProofFile(null);
      setPaying(false);
      setClaiming(false);
      setActiveTab('domestic');
      setAppliedPromo(null);
      if (showPromoSection && proposalPromoCode) {
        setPromoInput(proposalPromoCode);
      } else {
        setPromoInput('');
      }
    }
  }, [open, proposalPromoCode, showPromoSection]);

  // Helper to load Razorpay script
  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }
      const existing = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
      if (existing) {
        existing.addEventListener('load', () => resolve(true));
        existing.addEventListener('error', () => resolve(false));
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  // Domestic: Razorpay Payment Flow
  const handleRazorpayPay = async () => {
    setPaying(true);

    try {
      // Step 1: Create Razorpay Order
      const orderRes = await axios.post(
        `${API}/payments/razorpay/create-order`,
        {
          sale_id: saleId || null,
          case_id: caseId || null,
          pa_id: paId || null,
          amount: finalPayable,
          promo_code: appliedPromo ? appliedPromo.code : null,
        },
        getAuthHeader()
      );

      const {
        order_id,
        amount: order_amount_paise,
        currency,
        key_id,
        client_name: ord_name,
        client_email: ord_email,
        client_mobile: ord_mobile,
        sale_id: resolved_sale_id,
      } = orderRes.data;

      // Step 2: Load SDK
      const isLoaded = await loadRazorpayScript();
      if (!isLoaded || typeof window.Razorpay === 'undefined') {
        throw new Error('Could not load Razorpay SDK. Please check your internet connection.');
      }

      // Step 3: Open Razorpay Checkout popup
      const options = {
        key: key_id || 'rzp_test_TIsfNCEO8uAj3s',
        amount: order_amount_paise || Math.round(finalPayable * 100),
        currency: currency || 'INR',
        name: 'LEAMSS Immigration',
        description: `${productName} — ${partLabel}`,
        order_id: order_id,
        prefill: {
          name: ord_name || clientName || '',
          email: ord_email || '',
          contact: ord_mobile || '',
        },
        handler: async function (response) {
          try {
            await axios.post(
              `${API}/payments/razorpay/verify`,
              {
                sale_id: resolved_sale_id || saleId,
                case_id: caseId || null,
                order_id: response.razorpay_order_id || order_id,
                payment_id: response.razorpay_payment_id || `pay_${Date.now()}`,
                signature: response.razorpay_signature || '',
                promo_code: appliedPromo ? appliedPromo.code : null,
                discount_amount: discountAmount,
                original_amount: originalAmount,
              },
              getAuthHeader()
            );

            toast.success(`Payment of ₹${finalPayable.toLocaleString('en-IN')} successful!`);
            onSuccess?.();
            onClose();
          } catch (verifyErr) {
            toast.error(verifyErr?.response?.data?.detail || 'Payment verification failed');
          } finally {
            setPaying(false);
          }
        },
        modal: {
          ondismiss: function () {
            setPaying(false);
          },
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (e) {
      console.error('Razorpay payment initiation error:', e);
      toast.error(e?.response?.data?.detail || e.message || 'Unable to start payment gateway');
      setPaying(false);
    }
  };

  // International: Wire Transfer Claim Flow
  const handleInternationalClaim = async () => {
    setClaiming(true);

    try {
      if (saleId) {
        await axios.post(
          `${API}/payments/international-claim`,
          {
            sale_id: saleId,
            reference_note: transferRef,
            country: selectedCountry,
            promo_code: appliedPromo ? appliedPromo.code : null,
            discount_amount: discountAmount,
            original_amount: originalAmount,
          },
          getAuthHeader()
        );
      } else if (paId) {
        await axios.post(
          `${API}/pre-assess-portal/client/proposal/international-claim/${paId}`,
          {
            reference_note: transferRef,
            country: selectedCountry,
            promo_code: appliedPromo ? appliedPromo.code : null,
          },
          getAuthHeader()
        );
      }

      // If proof file attached, upload
      if (proofFile) {
        try {
          const fd = new FormData();
          fd.append('document_type', 'payment_proof');
          fd.append('file', proofFile);
          fd.append('step_name', partLabel);
          if (paId) {
            await axios.post(`${API}/pre-assessment/${paId}/upload-document`, fd, {
              ...getAuthHeader(),
              headers: { ...getAuthHeader().headers, 'Content-Type': 'multipart/form-data' },
            });
          } else {
            await axios.post(`${API}/documents/upload`, fd, getAuthHeader());
          }
        } catch (uploadErr) {
          console.warn('Proof upload note:', uploadErr);
        }
      }

      setClaimSuccess(true);
      toast.success('Payment claim submitted! Your consultant will verify.');
      setTimeout(() => {
        onSuccess?.();
        onClose();
      }, 2000);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to submit payment claim');
    } finally {
      setClaiming(false);
    }
  };

  const copyToClipboard = (text, label) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl p-0 overflow-y-auto max-h-[92vh] bg-slate-50 shadow-2xl border-0 rounded-2xl" data-testid="installment-payment-modal">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 z-20 text-white/80 hover:text-white bg-black/20 hover:bg-black/40 rounded-full p-1.5 transition"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="p-4 sm:p-6 space-y-4">
          {/* ═══════════════════════════════════════════════════════════════ */}
          {/* 1. TOP HERO BANNER (Dark Teal Card - Matching Screenshot 1) */}
          {/* ═══════════════════════════════════════════════════════════════ */}
          <div className="bg-[#1f4d44] text-white rounded-2xl p-5 sm:p-7 shadow-lg relative overflow-hidden">
            {/* Background ambient lighting */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-teal-400/10 rounded-full blur-3xl pointer-events-none" />

            <div className="relative z-10 space-y-3">
              <Badge className="bg-white/15 text-white border-0 text-xs px-3 py-1 font-medium rounded-full">
                Welcome, {clientName}
              </Badge>

              <div>
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                  {productName}
                </h1>
                <p className="text-sm text-teal-100/90 mt-0.5">
                  Prepared by <span className="font-semibold text-white">{partnerName}</span>
                </p>
              </div>

              <div className="flex items-baseline gap-2 pt-1 flex-wrap">
                <span className="text-3xl sm:text-4xl font-extrabold text-white">
                  ₹{finalPayable.toLocaleString('en-IN')}
                </span>
                {appliedPromo && (
                  <span className="text-lg line-through text-teal-200/60 font-semibold">
                    ₹{originalAmount.toLocaleString('en-IN')}
                  </span>
                )}
                <span className="text-xs sm:text-sm text-teal-100/80 font-medium">
                  {partLabel} (incl. GST)
                </span>
              </div>

              {/* Inner Breakdown Table Box */}
              <div className="bg-black/20 rounded-xl p-3.5 space-y-2 border border-white/10 text-xs sm:text-sm">
                <div className="flex justify-between text-teal-100/90">
                  <span>Base Fee</span>
                  <span className="font-semibold text-white">₹{baseFee.toLocaleString('en-IN')}</span>
                </div>
                {appliedPromo && (
                  <div className="flex justify-between text-amber-300 font-medium">
                    <span>Promo Discount ({appliedPromo.code})</span>
                    <span>- ₹{appliedPromo.discount_amount.toLocaleString('en-IN')}</span>
                  </div>
                )}
                <div className="flex justify-between text-teal-100/90">
                  <span>GST (18%)</span>
                  <span className="font-semibold text-white">₹{gstFee.toLocaleString('en-IN')}</span>
                </div>
                <div className="flex justify-between font-bold text-white border-t border-white/15 pt-2 text-sm sm:text-base">
                  <span>Total Payable</span>
                  <span className="text-emerald-300">₹{finalPayable.toLocaleString('en-IN')}</span>
                </div>
              </div>

              <p className="text-[11px] sm:text-xs text-teal-200/70 pt-1">
                One-time milestone payment. Covers document filing + case processing.
              </p>
            </div>
          </div>

          {/* ═══════════════════════════════════════════════════════════════ */}
          {/* PROMO CODE SECTION — Shown ONLY during 1st installment payment */}
          {/* ═══════════════════════════════════════════════════════════════ */}
          {showPromoSection && (
            <Card className="p-4 bg-white border-slate-200 shadow-sm rounded-xl">
              <div className="flex items-center justify-between gap-2 mb-2">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-[#f7620b]" /> Apply Promo Code
                </h3>
                {appliedPromo && (
                  <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-xs font-semibold">
                    ✓ {appliedPromo.code} Active
                  </Badge>
                )}
              </div>

              {appliedPromo ? (
                <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg p-2.5">
                  <div className="text-xs text-emerald-900">
                    <span className="font-bold font-mono text-sm">{appliedPromo.code}</span>
                    <span className="ml-1.5 text-emerald-700">({appliedPromo.message || 'Discount applied'})</span>
                    <p className="text-[11px] text-emerald-600 mt-0.5 font-medium">Discount: ₹{appliedPromo.discount_amount.toLocaleString('en-IN')}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleRemovePromo} className="text-red-600 border-red-200 hover:bg-red-50 text-xs h-7">
                    Remove
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Enter Promo Code (e.g. SUMMER2026)"
                      value={promoInput}
                      onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
                      onKeyDown={(e) => { if (e.key === 'Enter') handleApplyPromo(); }}
                      className="flex-1 border rounded-lg px-3 py-1.5 text-xs uppercase font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-[#1f4d44]"
                      data-testid="promo-code-input"
                    />
                    <Button
                      onClick={() => handleApplyPromo()}
                      disabled={promoLoading || !promoInput.trim()}
                      className="bg-[#1f4d44] hover:bg-[#163831] text-white px-4 h-8 text-xs font-semibold"
                      data-testid="apply-promo-btn"
                    >
                      {promoLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                      Apply
                    </Button>
                  </div>
                  {proposalPromoCode && promoInput !== proposalPromoCode && (
                    <button
                      type="button"
                      onClick={() => {
                        setPromoInput(proposalPromoCode);
                        handleApplyPromo(proposalPromoCode);
                      }}
                      className="text-xs text-[#2a777a] hover:underline flex items-center gap-1 font-medium pt-0.5"
                      data-testid="quick-apply-promo"
                    >
                      🏷️ Available Proposal Promo: <span className="font-bold font-mono text-[#f7620b]">{proposalPromoCode}</span> (Click to Apply)
                    </button>
                  )}
                </div>
              )}
            </Card>
          )}

          {claimSuccess ? (
            <Card className="p-8 text-center space-y-3 bg-white border-emerald-200">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto text-emerald-600">
                <CheckCircle2 className="h-10 w-10" />
              </div>
              <h3 className="text-xl font-bold text-slate-800">Payment Claim Submitted!</h3>
              <p className="text-sm text-slate-600 max-w-sm mx-auto">
                Your wire transfer reference has been recorded. Your consultant will verify the payment within 1–2 business days.
              </p>
            </Card>
          ) : (
            <>
              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* 2. TWO SUMMARY CARDS (What's Included + Case Summary) */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Left Card: What's Included */}
                <Card className="p-5 bg-white border-slate-200 shadow-sm rounded-xl space-y-3">
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-[#f7620b]" /> What's Included
                  </h3>
                  <ul className="space-y-2 text-xs text-slate-600">
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Document verification by certified consultant</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>AI-powered eligibility scoring & updates</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Personalised country-specific feedback</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Full client portal access & receipt download</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Case manager milestone execution</span>
                    </li>
                  </ul>
                </Card>

                {/* Right Card: Case Summary */}
                <Card className="p-5 bg-white border-slate-200 shadow-sm rounded-xl space-y-2.5">
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 mb-2">
                    <Globe className="h-4 w-4 text-[#1f4d44]" /> Case Summary
                  </h3>
                  <div className="flex justify-between items-center text-xs py-1 border-b border-slate-100">
                    <span className="text-slate-500">Destination</span>
                    <span className="font-semibold text-slate-800 capitalize">{destination}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs py-1 border-b border-slate-100">
                    <span className="text-slate-500">Service</span>
                    <span className="font-semibold text-slate-800">{serviceType}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs py-1 border-b border-slate-100">
                    <span className="text-slate-500">Installment</span>
                    <span className="font-semibold text-slate-800">{partLabel}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs py-1 border-b border-slate-100">
                    <span className="text-slate-500">Total Payable</span>
                    <span className="font-bold text-[#1f4d44]">₹{finalPayable.toLocaleString('en-IN')} (incl. GST)</span>
                  </div>
                  <div className="flex justify-between items-center text-xs py-1">
                    <span className="text-slate-500">Est. review time</span>
                    <span className="font-semibold text-slate-800">1-2 business days</span>
                  </div>
                </Card>
              </div>

              {/* ═══════════════════════════════════════════════════════════════ */}
              {/* 3. PAYMENT METHOD CARD (Domestic Razorpay & International Wire) */}
              {/* ═══════════════════════════════════════════════════════════════ */}
              <Card className="p-5 sm:p-6 bg-white border border-[#1f4d44]/20 shadow-sm rounded-2xl space-y-4">
                {/* ── Domestic vs International Rounded Tabs ── */}
                <div className="flex gap-2 p-1.5 bg-slate-100 rounded-xl">
                  <button
                    type="button"
                    onClick={() => setActiveTab('domestic')}
                    className={`flex-1 py-2.5 px-3 rounded-lg text-xs sm:text-sm font-semibold transition ${
                      activeTab === 'domestic'
                        ? 'bg-white text-[#1f4d44] shadow-sm font-bold'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                    data-testid="pay-tab-domestic"
                  >
                    🇮🇳 Pay from India
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('international')}
                    className={`flex-1 py-2.5 px-3 rounded-lg text-xs sm:text-sm font-semibold transition ${
                      activeTab === 'international'
                        ? 'bg-white text-[#1f4d44] shadow-sm font-bold'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                    data-testid="pay-tab-international"
                  >
                    🌍 Pay from Outside India
                  </button>
                </div>

                {/* ── Tab 1: Domestic Razorpay Flow ── */}
                {activeTab === 'domestic' && (
                  <div className="space-y-4 pt-1">
                    <p className="text-xs sm:text-sm text-slate-700 flex items-start gap-2">
                      <Clock className="h-4 w-4 text-[#f7620b] shrink-0 mt-0.5" />
                      <span>
                        Click Pay Now to complete your {partLabel}. You'll instantly get receipt and case status will be updated.
                      </span>
                    </p>

                    <Button
                      onClick={handleRazorpayPay}
                      disabled={paying || finalPayable <= 0}
                      className="w-full bg-[#f7620b] hover:bg-[#e55a09] text-white font-bold h-12 sm:h-14 text-base sm:text-lg shadow-md transition rounded-xl"
                      data-testid="proceed-razorpay-btn"
                    >
                      {paying ? (
                        <>
                          <Loader2 className="h-5 w-5 animate-spin mr-2" />
                          Opening Payment Gateway…
                        </>
                      ) : (
                        <>
                          <CreditCard className="h-5 w-5 mr-2" />
                          Pay ₹{finalPayable.toLocaleString('en-IN')} Securely
                        </>
                      )}
                    </Button>

                    <p className="text-[11px] text-slate-400 text-center">
                      🔒 Secured by Razorpay — Cards, UPI, Netbanking & Wallets accepted.
                    </p>
                  </div>
                )}

                {/* ── Tab 2: International Wire Transfer Flow ── */}
                {activeTab === 'international' && (
                  <div className="space-y-3.5 pt-1">
                    {/* Country selector */}
                    <div>
                      <label className="text-xs font-semibold text-slate-600 mb-1.5 block">
                        Select Destination Bank Account:
                      </label>
                      <div className="flex gap-1.5 flex-wrap">
                        {INTL_COUNTRIES.map((c) => (
                          <button
                            key={c.code}
                            type="button"
                            onClick={() => setSelectedCountry(c.code)}
                            className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                              selectedCountry === c.code
                                ? 'bg-[#1f4d44] text-white border-[#1f4d44]'
                                : 'bg-white text-slate-600 border-slate-300 hover:border-[#1f4d44]'
                            }`}
                            data-testid={`intl-country-${c.code}`}
                          >
                            {c.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {bankLoading ? (
                      <div className="text-center py-6">
                        <Loader2 className="h-6 w-6 animate-spin text-[#1f4d44] mx-auto mb-2" />
                        <p className="text-xs text-slate-500">Loading bank details…</p>
                      </div>
                    ) : bankDetails ? (
                      <div className="space-y-3">
                        <p className="text-xs sm:text-sm text-slate-700">
                          Please transfer <strong>₹{finalPayable.toLocaleString('en-IN')}</strong> via bank wire to the account below, then confirm your payment.
                        </p>

                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2 text-xs sm:text-sm">
                          <div className="flex justify-between items-center py-1 border-b border-slate-200/60">
                            <span className="text-slate-500">Account Name</span>
                            <span className="font-semibold text-slate-800 text-right">{bankDetails.account_name}</span>
                          </div>
                          <div className="flex justify-between items-center py-1 border-b border-slate-200/60">
                            <span className="text-slate-500">Account Number</span>
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono font-bold text-slate-800">{bankDetails.account_number}</span>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(bankDetails.account_number, 'Account Number')}
                                className="text-slate-400 hover:text-slate-700 p-0.5"
                              >
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                          <div className="flex justify-between items-center py-1 border-b border-slate-200/60">
                            <span className="text-slate-500">IFSC / SWIFT</span>
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono font-bold text-slate-800">{bankDetails.ifsc_or_swift}</span>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(bankDetails.ifsc_or_swift, 'SWIFT / IFSC')}
                                className="text-slate-400 hover:text-slate-700 p-0.5"
                              >
                                <Copy className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </div>
                          <div className="flex justify-between items-center py-1 border-b border-slate-200/60">
                            <span className="text-slate-500">Bank Name</span>
                            <span className="font-semibold text-slate-800">{bankDetails.bank_name}</span>
                          </div>
                          {bankDetails.bank_address && (
                            <div className="flex justify-between items-start py-1">
                              <span className="text-slate-500">Bank Address</span>
                              <span className="text-slate-700 text-right max-w-[260px] truncate">{bankDetails.bank_address}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : null}

                    {/* Reference / Proof Inputs */}
                    <div className="space-y-2 pt-1">
                      <div>
                        <label className="text-xs font-semibold text-slate-600 mb-1 block">
                          Transaction Reference / UTR (optional)
                        </label>
                        <input
                          type="text"
                          placeholder="e.g., UTR123456789 or Wire Conf #"
                          value={transferRef}
                          onChange={(e) => setTransferRef(e.target.value)}
                          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-[#1f4d44]"
                          data-testid="intl-ref-input"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-slate-600 mb-1 block">
                          Attach Payment Screenshot / Receipt (optional)
                        </label>
                        <input
                          type="file"
                          accept="image/*,.pdf"
                          onChange={(e) => setProofFile(e.target.files?.[0] || null)}
                          className="w-full text-xs sm:text-sm border border-slate-300 rounded-lg px-2 py-1.5 bg-white cursor-pointer"
                          data-testid="intl-proof-input"
                        />
                        {proofFile && (
                          <span className="text-xs text-emerald-600 mt-1 block font-medium">✓ {proofFile.name}</span>
                        )}
                      </div>
                    </div>

                    <Button
                      onClick={handleInternationalClaim}
                      disabled={claiming || finalPayable <= 0}
                      className="w-full bg-[#1f4d44] hover:bg-[#183d36] text-white font-bold h-12 text-sm sm:text-base shadow transition rounded-xl mt-1"
                      data-testid="confirm-intl-wire-btn"
                    >
                      {claiming ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          Submitting Claim…
                        </>
                      ) : (
                        <>
                          <Globe className="h-4 w-4 mr-2" />
                          I've Made the Transfer
                        </>
                      )}
                    </Button>

                    <p className="text-[10px] text-slate-400 text-center mt-2">
                      Your consultant will manually verify this transfer and confirm within 1-2 business days.
                    </p>
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
