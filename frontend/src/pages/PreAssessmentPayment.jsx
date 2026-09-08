import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, ShieldCheck, Globe, FileText, Users, Clock, CreditCard, Sparkles, AlertTriangle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const READY_STAGES = [
  'awaiting_package_selection', 'package_selected', 'proposal_sent',
  'proposal_paid', 'awaiting_final_approval', 'case_created',
];


/** Public page at /pre-assess/:token — no login required */
export default function PreAssessmentPayment() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paying, setPaying] = useState(false);
  const [success, setSuccess] = useState(null);
  const [entering, setEntering] = useState(false);
  const [paymentTab, setPaymentTab] = useState('domestic'); // 'domestic' | 'international'
  const [bankDetails, setBankDetails] = useState(null);
  const [bankLoading, setBankLoading] = useState(false);
  const [transferRef, setTransferRef] = useState('');
  const [claiming, setClaiming] = useState(false);
  const [proofFile, setProofFile] = useState(null);
  const [selectedCountry, setSelectedCountry] = useState('Australia');

  const INTL_COUNTRIES = [
    { code: 'Australia', label: '🇦🇺 AUS' },
    { code: 'Canada', label: '🇨🇦 Canada' },
    { code: 'USA', label: '🇺🇸 USA' },
    { code: 'UK', label: '🇬🇧 UK' },
    { code: 'New Zealand', label: '🇳🇿 NZ' },
  ];

  const loadData = useCallback(() => {
    axios.get(`${API}/pre-assess-portal/public/${token}`)
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.data?.detail || 'Link unavailable'))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    loadData();
  }, [loadData]);

useEffect(() => {
    if (!data) return;
    const isExpress = data.sale_type === 'express';
    if (isExpress && READY_STAGES.includes(data.stage) && !entering) {
      setEntering(true);
      axios.post(`${API}/pre-assess-portal/public/enter-portal`, { token })
        .then(r => {
          const magicToken = r.data.magic_link.split('/magic/').pop();
          toast.success('Your proposal is ready! Redirecting to your portal…');
          setTimeout(() => navigate(`/magic/${magicToken}`), 1200);
        })
        .catch(() => setEntering(false));
    }
  }, [data]);

useEffect(() => {
    if (paymentTab !== 'international') return;
    setBankLoading(true);
    setBankDetails(null);
    axios.get(`${API}/pre-assess-portal/public/bank-details/${token}`, { params: { country: selectedCountry } })
      .then(r => setBankDetails(r.data))
      .catch(e => toast.error(e?.response?.data?.detail || 'Could not load bank details'))
      .finally(() => setBankLoading(false));
  }, [paymentTab, token, selectedCountry]);

  const handleInternationalClaim = async () => {
    setClaiming(true);
    try {
      const r = await axios.post(`${API}/pre-assess-portal/public/international-payment-claim`, {
        token,
        reference_note: transferRef,
      });

      // Upload payment proof (if attached) — log in via magic link first to get a token
      if (proofFile) {
        try {
          const magicToken = r.data.magic_link.split('/magic/').pop();
          const loginRes = await axios.post(`${API}/pre-assess-portal/magic-login`, { token: magicToken });
          const jwt = loginRes.data.token;
          const fd = new FormData();
          fd.append('document_type', 'payment_proof');
          fd.append('file', proofFile);
          await axios.post(`${API}/pre-assessment/${r.data.pa_id}/upload-document`, fd, {
            headers: { Authorization: `Bearer ${jwt}`, 'Content-Type': 'multipart/form-data' },
          });
          // Save token so /magic/:token page doesn't need to re-consume the (now used) magic link
          localStorage.setItem('token', jwt);
        } catch (uploadErr) {
          console.error('Proof upload failed:', uploadErr);
          toast.error('Payment claimed, but proof upload failed — you can upload it from your portal.');
        }
      }

      setSuccess(r.data);
      toast.success('Payment claim submitted! Redirecting to your portal…');
      setTimeout(() => {
        if (proofFile && localStorage.getItem('token')) {
          navigate('/client'); // already logged in via magic-login above
        } else {
          const magicToken = r.data.magic_link.split('/magic/').pop();
          navigate(`/magic/${magicToken}`);
        }
      }, 2500);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Something went wrong');
    } finally {
      setClaiming(false);
    }
  };

  const handlePay = async () => {
    setPaying(true);
    try {
      // Step 1: Backend कडून Razorpay order तयार करून घे
      const orderRes = await axios.post(`${API}/pre-assess-portal/public/create-order`, { token });
      const { order_id, amount, currency, key_id, client_name, client_email, client_mobile } = orderRes.data;

      // Step 2: Razorpay Checkout Popup उघड (इथेच Card/UPI/Netbanking आपोआप दिसतं)
      const options = {
        key: key_id,
        amount: amount,
        currency: currency,
        name: 'LEAMSS Immigration',
        description: 'Pre-Assessment Fee',
        order_id: order_id,
        prefill: {
          name: client_name || '',
          email: client_email || '',
          contact: client_mobile || '',
        },
        theme: { color: '#f7620b' },
        handler: async function (response) {
          // Step 3: Payment झाल्यावर backend वर verify साठी पाठव
          try {
            const verifyRes = await axios.post(`${API}/pre-assess-portal/public/verify-payment`, {
              token: token,
              order_id: response.razorpay_order_id,
              payment_id: response.razorpay_payment_id,
              signature: response.razorpay_signature,
            });
            setSuccess(verifyRes.data);
            toast.success('Payment successful! Redirecting to your portal…');
            setTimeout(() => {
              const magicToken = verifyRes.data.magic_link.split('/magic/').pop();
              navigate(`/magic/${magicToken}`);
            }, 2500);
          } catch (e) {
            toast.error(e?.response?.data?.detail || 'Payment verification failed');
          } finally {
            setPaying(false);
          }
        },
        modal: {
          ondismiss: function () {
            // Client ने पॉपअप बंद केलं तर (payment cancel केलं)
            setPaying(false);
          },
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Unable to start payment');
      setPaying(false);
    }
  };

  if (loading) return <FullPageLoader msg="Loading your pre-assessment…" />;

  if (error) return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <Card className="max-w-md p-8 text-center">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="h-8 w-8 text-red-500" />
        </div>
        <h1 className="text-xl font-bold text-slate-800 mb-2">Link Unavailable</h1>
        <p className="text-sm text-slate-500 mb-4">{error}</p>
        <p className="text-xs text-slate-400 mb-5">
          This link may have expired, been deactivated, or never existed.
          Please ask your LEAMSS consultant to share a fresh secure link.
        </p>
        <div className="flex gap-2 justify-center flex-wrap">
          <Button variant="outline" onClick={() => navigate('/eligibility')}>Check Eligibility</Button>
          <Button onClick={() => navigate('/')} className="bg-[#2a777a] hover:bg-[#1d5658] text-white">Login</Button>
        </div>
      </Card>
    </div>
  );

  const gstIncluded = !!data.step1_gst_included;
  const baseAmount = data.step1_base_amount || data.pre_assessment_fee || 5100;
  const gstAmount = data.step1_gst_amount || 0;
  const amount = data.step1_total_amount || data.pre_assessment_fee || 5100; // client pays this total
  const isExpress = data.sale_type === 'express';

  // Phase 4C — For Express Sales, skip PA fee entirely
  if (isExpress) {
    const isTokenMode = data.express_mode === 'token';
    const tokenAmount = data.express_token_amount || 0;
    return (
      <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-amber-50/40">
        <div className="bg-gradient-to-r from-[#2a777a] to-[#1f5c5f] text-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-2.5">
            <div className="w-10 h-10 bg-white/15 rounded-lg flex items-center justify-center backdrop-blur-sm">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="font-bold text-lg leading-tight">LEAMSS Immigration</p>
              <p className="text-xs opacity-80">Express Sale — fast-tracked</p>
            </div>
          </div>
        </div>
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10 space-y-5">
          <Card className="p-8 text-center">
            <div className="w-20 h-20 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Sparkles className="h-10 w-10 text-amber-600" />
            </div>
            <Badge className="bg-amber-100 text-amber-700 mb-3">⚡ Express Sale</Badge>
            <h1 className="text-2xl font-bold text-slate-800 mb-3">Welcome, {data.client_name}!</h1>
            {isTokenMode ? (
              <>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Your <strong>{data.service_type}</strong> case has been fast-tracked. To confirm your slot and lock-in the timeline, please pay a small token amount of <strong>₹{Math.round(tokenAmount).toLocaleString('en-IN')}</strong>.
                </p>
                <p className="text-xs text-slate-500 mt-2">This token will be adjusted in your final invoice.</p>
                <Button
                  className="w-full mt-5 bg-emerald-600 hover:bg-emerald-700 h-12"
                  data-testid="pay-token-btn"
                  onClick={async () => {
                    try {
                      const r = await axios.post(`${API}/pre-assess-portal/public/mock-pay`, { token });
                      if (r.data?.ok) {
                        toast.success(`Token of ₹${Math.round(tokenAmount).toLocaleString('en-IN')} received! Your consultant will share the full proposal shortly.`);
                        loadData();
                      }
                    } catch (e) { toast.error(e?.response?.data?.detail || 'Payment failed'); }
                  }}
                >
                  Pay Token ₹{Math.round(tokenAmount).toLocaleString('en-IN')} (Mock)
                </Button>
              </>
): entering ? (
              // 👇 ADD THIS NEW BRANCH
              <div className="py-4">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-600 mx-auto mb-2" />
                <p className="text-sm text-slate-600">Your proposal is ready — taking you to your portal…</p>
              </div>
              
            
) : (
              <>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Your <strong>{data.service_type}</strong> case has been fast-tracked under our Express Sales process — <strong>no pre-assessment fee is required</strong>.
                </p>
                <p className="text-sm text-slate-600 mt-2">
                  Your consultant <strong>{data.partner_name}</strong> will share the full service proposal with you shortly.
                  For any questions, please reply directly to their email or WhatsApp.
                </p>
              </>
            )}
            <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-left">
              <p className="text-xs font-bold text-emerald-800 mb-2">📋 Your Case Summary</p>
              <div className="space-y-1 text-xs text-slate-700">
                <Row label="Destination" value={data.country} />
                <Row label="Service" value={data.service_type} />
                <Row label="Mode" value={isTokenMode ? `Token ₹${Math.round(tokenAmount).toLocaleString('en-IN')}` : 'Direct Proposal'} />
                <Row label="Stage" value={isTokenMode ? 'Awaiting token payment' : 'Awaiting proposal'} />
                <Row label="Pre-assessment Fee" value="✓ Waived (Express)" />
              </div>
            </div>
            <p className="text-[11px] text-slate-400 mt-5">
              🔒 This is a secure preview link. Your consultant will contact you soon.
            </p>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50/40">
      <div className="bg-gradient-to-r from-[#2a777a] to-[#1f5c5f] text-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-2.5">
          <div className="w-10 h-10 bg-white/15 rounded-lg flex items-center justify-center backdrop-blur-sm">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <p className="font-bold text-lg leading-tight">LEAMSS Immigration</p>
            <p className="text-xs opacity-80">Secure pre-assessment payment</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        <Card className="overflow-hidden border-0 shadow-xl">
          <div className="bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] text-white p-6 sm:p-8">
            <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/20 mb-3">
              Welcome, {data.client_name}
            </Badge>
            <h1 className="text-2xl sm:text-3xl font-bold leading-tight">Start Your {data.service_type} Journey</h1>
            <p className="text-sm opacity-80 mt-2">Prepared by <span className="font-semibold">{data.partner_name}</span></p>
            <div className="mt-6 flex items-end gap-3">
              <p className="text-5xl font-bold">₹{amount.toLocaleString('en-IN')}</p>
              <span className="text-sm opacity-80 mb-1.5">pre-assessment fee{gstIncluded ? ' (incl. GST)' : ''}</span>
            </div>
            {gstIncluded && (
              <div className="mt-3 bg-white/10 rounded-lg p-3 text-sm space-y-1">
                <div className="flex justify-between"><span className="opacity-80">Base Fee</span><span>₹{baseAmount.toLocaleString('en-IN')}</span></div>
                <div className="flex justify-between"><span className="opacity-80">GST (18%)</span><span>₹{gstAmount.toLocaleString('en-IN')}</span></div>
                <div className="flex justify-between font-bold border-t border-white/20 pt-1 mt-1"><span>Total Payable</span><span>₹{amount.toLocaleString('en-IN')}</span></div>
              </div>
            )}
            <p className="text-xs opacity-70 mt-1">One-time, non-refundable. Covers document review + eligibility evaluation.</p>
          </div>
        </Card>

        <div className="grid md:grid-cols-2 gap-4">
          <Card className="p-5 bg-white border-slate-200">
            <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-3">
              <Sparkles className="h-4 w-4 text-[#f7620b]" /> What's Included
            </h3>
            <ul className="space-y-2 text-sm text-slate-600">
              {[
                'Document verification by certified consultant',
                'AI-powered eligibility scoring',
                'Personalised country-specific feedback',
                'Full client portal access (72h login link)',
                'Proposal generation if you qualify',
              ].map((b, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5 bg-white border-slate-200">
            <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-3">
              <Globe className="h-4 w-4 text-[#2a777a]" /> Case Summary
            </h3>
            <Row label="Destination" value={data.country} />
            <Row label="Service" value={data.service_type} />
            <Row label="Pre-assessment fee" value={gstIncluded ? `₹${amount.toLocaleString('en-IN')} (incl. GST)` : `₹${amount.toLocaleString('en-IN')}`} />
            <Row label="Est. review time" value="1-2 business days" />
          </Card>
        </div>

        <Card className="p-5 bg-gradient-to-br from-[#f7620b]/5 to-[#2a777a]/5 border-[#2a777a]/20">
          {success ? (
            <div className="text-center py-6" data-testid="pay-success">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 className="h-8 w-8 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-slate-800">
                {paymentTab === 'international' ? 'Payment Claim Submitted!' : 'Payment Successful!'}
              </h3>
              <p className="text-sm text-slate-600 mt-2">Redirecting you to the client portal…</p>
            </div>
          ) : (
            <>
              {/* ── Domestic / International Tabs ── */}
              <div className="flex gap-2 mb-4 p-1 bg-slate-100 rounded-lg">
                <button
                  onClick={() => setPaymentTab('domestic')}
                  className={`flex-1 py-2 rounded-md text-sm font-semibold transition ${
                    paymentTab === 'domestic' ? 'bg-white text-[#2a777a] shadow' : 'text-slate-500'
                  }`}
                >
                  🇮🇳 Pay from India
                </button>
                <button
                  onClick={() => setPaymentTab('international')}
                  className={`flex-1 py-2 rounded-md text-sm font-semibold transition ${
                    paymentTab === 'international' ? 'bg-white text-[#2a777a] shadow' : 'text-slate-500'
                  }`}
                >
                  🌍 Pay from Outside India
                </button>
              </div>

              {paymentTab === 'domestic' ? (
                <>
                  <p className="text-sm text-slate-700 mb-3 flex items-start gap-2">
                    <Clock className="h-4 w-4 text-[#f7620b] shrink-0 mt-0.5" />
                    <span>Click Pay Now to start your pre-assessment. You'll instantly get portal access to upload documents and track progress.</span>
                  </p>
                  <Button onClick={handlePay} disabled={paying}
                    className="w-full bg-[#f7620b] hover:bg-[#e55a09] text-white font-semibold h-12 text-base" data-testid="pay-btn">
                    {paying ? <Loader2 className="h-5 w-5 animate-spin mr-2" /> : <CreditCard className="h-5 w-5 mr-2" />}
                    Pay ₹{amount.toLocaleString('en-IN')} Securely
                  </Button>
                  <p className="text-[10px] text-slate-400 text-center mt-2">
                    🔒 Secured by Razorpay — Cards, UPI, Netbanking & Wallets accepted.
                  </p>
                </>
              ) : (
                <>
                                  {/* ── Country Sub-Tabs ── */}
                  <div className="flex gap-1.5 mb-4 flex-wrap">
                    {INTL_COUNTRIES.map((c) => (
                      <button
                        key={c.code}
                        onClick={() => setSelectedCountry(c.code)}
                        className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                          selectedCountry === c.code
                            ? 'bg-[#2a777a] text-white border-[#2a777a]'
                            : 'bg-white text-slate-600 border-slate-300 hover:border-[#2a777a]'
                        }`}
                      >
                        {c.label}
                      </button>
                    ))}
                  </div>

                  {bankLoading ? (
                    <div className="text-center py-6">
                      <Loader2 className="h-6 w-6 animate-spin text-[#2a777a] mx-auto mb-2" />
                      <p className="text-sm text-slate-500">Loading bank details…</p>
                    </div>
                  ) : bankDetails ? (
                    <>
                      <p className="text-sm text-slate-700 mb-3">
                        Please transfer <strong>₹{amount.toLocaleString('en-IN')}</strong> via bank wire to the account below, then confirm your payment.
                      </p>
                      <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-1.5 text-sm mb-4">
                        <Row label="Account Name" value={bankDetails.account_name} />
                        <Row label="Account Number" value={bankDetails.account_number} />
                        <Row label="IFSC / SWIFT" value={bankDetails.ifsc_or_swift} />
                        <Row label="Bank Name" value={bankDetails.bank_name} />
                        <Row label="Bank Address" value={bankDetails.bank_address} />
                      </div>
                      <input
                        type="text"
                        placeholder="Transaction Reference / UTR (optional)"
                        value={transferRef}
                        onChange={(e) => setTransferRef(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-[#2a777a]"
                      />
                      <label className="block mb-3">
                        <span className="text-xs text-slate-500 mb-1 block">Attach Payment Screenshot / Receipt (optional)</span>
                        <input
                          type="file"
                          accept="image/*,.pdf"
                          onChange={(e) => setProofFile(e.target.files?.[0] || null)}
                          className="w-full text-sm border border-slate-300 rounded-lg px-2 py-1.5 bg-white"
                        />
                        {proofFile && <span className="text-xs text-emerald-600 mt-1 block">✓ {proofFile.name}</span>}
                      </label>
                      <Button onClick={handleInternationalClaim} disabled={claiming}
                        className="w-full bg-[#2a777a] hover:bg-[#1d5658] text-white font-semibold h-12 text-base">
                        {claiming ? <Loader2 className="h-5 w-5 animate-spin mr-2" /> : null}
                        I've Made the Transfer
                      </Button>
                      <p className="text-[10px] text-slate-400 text-center mt-2">
                        Your consultant will manually verify this transfer and confirm your payment within 1-2 business days.
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-slate-500 text-center py-6">Unable to load bank details. Please try again.</p>
                  )}
                </>
              )}
            </>
          )}
        </Card>

        <p className="text-center text-xs text-slate-400 pb-6">
          Questions? Reply to our email or WhatsApp for support.
        </p>
      </div>
    </div>
  );
}

const FullPageLoader = ({ msg }) => (
  <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
    <div className="text-center">
      <Loader2 className="h-10 w-10 animate-spin text-[#2a777a] mx-auto mb-3" />
      <p className="text-slate-500 text-sm">{msg}</p>
    </div>
  </div>
);

const Row = ({ label, value }) => (
  <div className="flex items-center justify-between text-sm py-1.5 border-b border-slate-100 last:border-0">
    <span className="text-slate-500">{label}</span>
    <span className="font-medium text-slate-800">{value || '—'}</span>
  </div>
);
