import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import {
  Calculator, IndianRupee, CheckCircle2, Shield, Info,
  ExternalLink, Loader2, Send, Receipt, Globe, Clock, AlertTriangle,
  Sparkles, Mail, Phone, User as UserIcon
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CURRENCY_SYMBOL = {
  INR: '₹', USD: '$', CAD: 'C$', AUD: 'A$', GBP: '£', EUR: '€',
  NZD: 'NZ$', SGD: 'S$', JPY: '¥', SEK: 'kr', DKK: 'kr', CHF: 'Fr',
  HKD: 'HK$', MYR: 'RM', KRW: '₩', AED: 'د.إ',
};

const fmt = (num, cur = 'INR') => {
  if (num == null) return '--';
  const sym = CURRENCY_SYMBOL[cur] || '';
  const n = Number(num);
  if (cur === 'INR') return `${sym}${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  return `${sym}${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
};

export default function SharedEstimate() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [lead, setLead] = useState({ name: '', email: '', phone: '', message: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    axios.get(`${API}/fee-calculator/public/${token}`)
      .then(r => setData(r.data))
      .catch(e => {
        const detail = e?.response?.data?.detail || 'Link not available';
        setError(detail);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const submitLead = async (e) => {
    e.preventDefault();
    if (!lead.name.trim() || !lead.email.trim()) {
      toast.error('Name and email are required');
      return;
    }
    setSubmitting(true);
    try {
      await axios.post(`${API}/fee-calculator/public/${token}/lead`, lead);
      setSubmitted(true);
      toast.success('Thank you! We will reach out within 24 hours.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin text-[#2a777a] mx-auto mb-3" />
          <p className="text-slate-500 text-sm">Loading your estimate…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <Card className="max-w-md p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="h-8 w-8 text-red-500" />
          </div>
          <h1 className="text-xl font-bold text-slate-800 mb-2">Link Unavailable</h1>
          <p className="text-sm text-slate-500">{error}</p>
          <p className="text-xs text-slate-400 mt-4">If you believe this is an error, please contact the person who sent you this link.</p>
        </Card>
      </div>
    );
  }

  const p = data.payload || {};
  const totals = p.totals || {};
  const lineItems = (p.line_items || []).filter(li => li.selected);
  const cur = p.country?.currency || 'INR';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50/40 print:bg-white">
      {/* Top bar */}
      <div className="bg-gradient-to-r from-[#2a777a] to-[#1f5c5f] text-white print:hidden">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 bg-white/15 rounded-lg flex items-center justify-center backdrop-blur-sm">
              <Calculator className="h-5 w-5" />
            </div>
            <div>
              <p className="font-bold text-lg leading-tight">{data.branding?.agency_name || 'LEAMSS Immigration'}</p>
              <p className="text-xs opacity-80">Your Visa Cost Estimate</p>
            </div>
          </div>
          <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/20 hidden sm:inline-flex">
            <Shield className="h-3 w-3 mr-1" /> Secured Link
          </Badge>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Hero */}
        <Card className="overflow-hidden border-0 shadow-xl">
          <div className="bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] text-white p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
              <div className="flex-1">
                <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/20 mb-3">
                  {p.category?.name}
                </Badge>
                <h1 className="text-2xl sm:text-3xl font-bold leading-tight">
                  {p.country?.name} Visa — Cost Estimate
                </h1>
                <p className="text-sm opacity-80 mt-2">
                  Prepared by <span className="font-semibold">{data.created_by_name || 'our team'}</span>
                </p>
                {data.share_message && (
                  <p className="mt-4 text-sm bg-white/10 rounded-lg p-3 border border-white/20 leading-relaxed">
                    "{data.share_message}"
                  </p>
                )}
              </div>
              <div className="text-right shrink-0">
                <div className="text-6xl sm:text-7xl leading-none mb-2">{p.country?.flag}</div>
                <div className="flex items-center gap-1 justify-end text-xs opacity-80">
                  <Clock className="h-3 w-3" /> {p.category?.processing_days} days
                </div>
              </div>
            </div>

            <Separator className="my-6 bg-white/20" />

            <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wider opacity-70">Estimated Total</p>
                <p className="text-4xl sm:text-5xl font-bold mt-1 flex items-center gap-1" data-testid="public-grand-total">
                  <IndianRupee className="h-8 w-8 sm:h-10 sm:w-10" />
                  {(totals.grand_total_inr || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </p>
                <p className="text-sm opacity-80 mt-1">
                  incl. {fmt(totals.govt_fees_native, cur)} government fees{totals.service_total_inr > 0 ? ' + service charges' : ''}
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs opacity-80">
                <Globe className="h-3.5 w-3.5" />
                <span>1 {cur} = ₹{(p.exchange_rate?.native_to_inr || 0).toFixed(2)}</span>
              </div>
            </div>
          </div>
        </Card>

        <div className="grid lg:grid-cols-5 gap-5">
          {/* Left: Breakdown */}
          <Card className="lg:col-span-3 p-5 sm:p-6 bg-white shadow-sm border-slate-200">
            <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-4">
              <Receipt className="h-5 w-5 text-[#2a777a]" />
              Detailed Breakdown
            </h2>

            <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100">
              {lineItems.map((li, idx) => (
                <div key={li.id || idx} className="flex items-start justify-between gap-3 px-4 py-3 hover:bg-slate-50/60 text-sm">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-slate-800 font-medium">{li.label}</span>
                      {li.multiplier > 1 && (
                        <Badge variant="outline" className="text-xs py-0 h-5">×{li.multiplier}</Badge>
                      )}
                    </div>
                    {li.notes && <p className="text-xs text-slate-400 mt-1">{li.notes}</p>}
                  </div>
                  <div className="text-right whitespace-nowrap">
                    <p className="text-slate-600 text-xs">{fmt(li.total_native, cur)}</p>
                    <p className="font-semibold text-[#2a777a]">{fmt(li.total_inr, 'INR')}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 bg-slate-50 rounded-lg p-4 space-y-2 text-sm border border-slate-200">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Total Government Fees</span>
                <span className="font-semibold">{fmt(totals.govt_fees_native, cur)} / <span className="text-[#2a777a]">{fmt(totals.govt_fees_inr, 'INR')}</span></span>
              </div>
              {totals.service_fee_inr > 0 && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Consultancy Service Fee</span>
                    <span className="font-semibold">{fmt(totals.service_fee_inr, 'INR')}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">GST @ {totals.gst_pct}%</span>
                    <span className="font-semibold">{fmt(totals.gst_amount_inr, 'INR')}</span>
                  </div>
                </>
              )}
              <Separator />
              <div className="flex items-center justify-between text-base">
                <span className="font-bold text-slate-800">Grand Total</span>
                <span className="font-bold text-[#2a777a]">{fmt(totals.grand_total_inr, 'INR')}</span>
              </div>
            </div>

            {p.category?.official_url && (
              <a href={p.category.official_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 mt-4 text-sm text-[#2a777a] hover:underline">
                <ExternalLink className="h-3.5 w-3.5" /> View official source
              </a>
            )}

            <div className="mt-4 text-xs text-slate-400 flex items-start gap-1.5 p-3 bg-blue-50 border border-blue-100 rounded">
              <Info className="h-3.5 w-3.5 mt-0.5 text-blue-500 shrink-0" />
              <span>Government fees are indicative (2025-26 official rates). Exchange rates refreshed from ECB. Third-party costs (tuition, travel, insurance) not included.</span>
            </div>
          </Card>

          {/* Right: Lead capture */}
          <div className="lg:col-span-2 space-y-4 print:hidden">
            {data.allow_lead_capture !== false ? (
              <Card className="p-5 sm:p-6 bg-gradient-to-br from-[#f7620b]/5 to-[#f7620b]/10 border-2 border-[#f7620b]/30 shadow-md">
                {submitted ? (
                  <div className="text-center py-4" data-testid="lead-success">
                    <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <CheckCircle2 className="h-8 w-8 text-emerald-600" />
                    </div>
                    <h3 className="text-lg font-bold text-slate-800">You're all set!</h3>
                    <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                      A case advisor will reach out within 24 hours to walk you through next steps.
                    </p>
                  </div>
                ) : (
                  <form onSubmit={submitLead} className="space-y-3" data-testid="lead-form">
                    <div className="flex items-center gap-2 mb-1">
                      <Sparkles className="h-5 w-5 text-[#f7620b]" />
                      <h3 className="text-lg font-bold text-slate-800">Ready to start?</h3>
                    </div>
                    <p className="text-sm text-slate-600 leading-relaxed">
                      Share a few details and a senior advisor will reach out within 24 hours with a custom roadmap.
                    </p>

                    <div>
                      <Label className="text-xs font-semibold text-slate-600">Full Name *</Label>
                      <div className="relative mt-1">
                        <UserIcon className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                        <Input required value={lead.name} onChange={e => setLead({ ...lead, name: e.target.value })}
                          placeholder="Your name" className="pl-9" data-testid="lead-name" />
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs font-semibold text-slate-600">Email *</Label>
                      <div className="relative mt-1">
                        <Mail className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                        <Input required type="email" value={lead.email} onChange={e => setLead({ ...lead, email: e.target.value })}
                          placeholder="you@example.com" className="pl-9" data-testid="lead-email" />
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs font-semibold text-slate-600">Phone / WhatsApp</Label>
                      <div className="relative mt-1">
                        <Phone className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                        <Input value={lead.phone} onChange={e => setLead({ ...lead, phone: e.target.value })}
                          placeholder="+91 98765 43210" className="pl-9" data-testid="lead-phone" />
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs font-semibold text-slate-600">Anything specific?</Label>
                      <Textarea value={lead.message} onChange={e => setLead({ ...lead, message: e.target.value })}
                        placeholder="e.g., timeline concerns, dependents, funds…" rows={3} className="mt-1 resize-none" data-testid="lead-message" />
                    </div>

                    <Button type="submit" disabled={submitting}
                      className="w-full bg-[#f7620b] hover:bg-[#e55a09] text-white font-semibold shadow-sm" data-testid="lead-submit">
                      {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                      Get My Custom Roadmap
                    </Button>
                    <p className="text-[11px] text-slate-400 text-center">
                      Your details are private & used only to contact you. No spam.
                    </p>
                  </form>
                )}
              </Card>
            ) : (
              <Card className="p-5 bg-white border-slate-200 text-center">
                <p className="text-sm text-slate-500">Contact the sender for next steps.</p>
              </Card>
            )}

            {data.expires_at && (
              <div className="text-xs text-slate-400 text-center flex items-center justify-center gap-1">
                <Clock className="h-3 w-3" />
                Link valid until {new Date(data.expires_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}
              </div>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-slate-400 pt-4 pb-8">
          Generated by {data.branding?.agency_name || 'LEAMSS Immigration'} · Rates from official government sources
        </p>
      </div>
    </div>
  );
}
