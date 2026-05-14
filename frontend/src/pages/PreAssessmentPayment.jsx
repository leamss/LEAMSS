import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, ShieldCheck, Globe, FileText, Users, Clock, CreditCard, Sparkles, AlertTriangle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/** Public page at /pre-assess/:token — no login required */
export default function PreAssessmentPayment() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paying, setPaying] = useState(false);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    axios.get(`${API}/pre-assess-portal/public/${token}`)
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.data?.detail || 'Link unavailable'))
      .finally(() => setLoading(false));
  }, [token]);

  const handlePay = async () => {
    setPaying(true);
    try {
      const r = await axios.post(`${API}/pre-assess-portal/public/mock-pay`, { token });
      setSuccess(r.data);
      toast.success('Payment successful! Redirecting to your portal…');
      setTimeout(() => {
        const magicToken = r.data.magic_link.split('/magic/').pop();
        navigate(`/magic/${magicToken}`);
      }, 2500);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Payment failed');
    } finally {
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

  const amount = data.pre_assessment_fee || 5100;
  const isExpress = data.sale_type === 'express';

  // Phase 4C — For Express Sales, skip PA fee entirely
  if (isExpress) {
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
            <p className="text-sm text-slate-600 leading-relaxed">
              Your <strong>{data.service_type}</strong> case has been fast-tracked under our Express Sales process — <strong>no pre-assessment fee is required</strong>.
            </p>
            <p className="text-sm text-slate-600 mt-2">
              Your consultant <strong>{data.partner_name}</strong> will share the full service proposal with you shortly.
              For any questions, please reply directly to their email or WhatsApp.
            </p>
            <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-left">
              <p className="text-xs font-bold text-emerald-800 mb-2">📋 Your Case Summary</p>
              <div className="space-y-1 text-xs text-slate-700">
                <Row label="Destination" value={data.country} />
                <Row label="Service" value={data.service_type} />
                <Row label="Stage" value="Express Sale — Awaiting proposal" />
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
              <span className="text-sm opacity-80 mb-1.5">pre-assessment fee</span>
            </div>
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
            <Row label="Pre-assessment fee" value={`₹${amount.toLocaleString('en-IN')}`} />
            <Row label="Est. review time" value="1-2 business days" />
          </Card>
        </div>

        <Card className="p-5 bg-gradient-to-br from-[#f7620b]/5 to-[#2a777a]/5 border-[#2a777a]/20">
          {success ? (
            <div className="text-center py-6" data-testid="pay-success">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 className="h-8 w-8 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-slate-800">Payment Successful!</h3>
              <p className="text-sm text-slate-600 mt-2">Redirecting you to the client portal…</p>
            </div>
          ) : (
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
                🔒 MOCK payment mode (for demo). Real Razorpay/Stripe integration coming soon.
              </p>
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
