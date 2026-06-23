/**
 * Option 2 — Public Proposal View (NO LOGIN REQUIRED)
 *
 * URL: /proposal/view?t=<signed_token>
 * Client opens email link → reviews proposal + key terms → accepts / declines.
 * On accept, redirects to client-portal login.
 */
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle, XCircle, Mail, Phone, FileText, AlertTriangle,
  Sparkles, ShieldCheck, Download,
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const inrFmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`;

export default function PublicProposalView() {
  const [params] = useSearchParams();
  const token = params.get('t') || '';
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [decideMode, setDecideMode] = useState(null);   // 'accept' | 'decline' | null
  const [declineReason, setDeclineReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    if (!token) { setErr('Invalid link. Contact sales for a new link.'); setLoading(false); return; }
    (async () => {
      try {
        const r = await fetch(`${API}/api/proposals/public/view?t=${encodeURIComponent(token)}`);
        if (r.ok) { setData(await r.json()); }
        else {
          const e = await r.json().catch(() => ({}));
          setErr(e.detail || 'This link is no longer valid.');
        }
      } catch (e) {
        setErr('Network error. Please retry or contact sales.');
      } finally { setLoading(false); }
    })();
  }, [token]);

  const accept = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/proposals/public/accept?t=${encodeURIComponent(token)}`, { method: 'POST' });
      const d = await r.json();
      if (r.ok) {
        setAccepted(true);
        toast.success('Proposal accepted! Redirecting…');
        setTimeout(() => { window.location.href = '/client-portal/login'; }, 2000);
      } else {
        toast.error(d.detail || 'Accept failed');
      }
    } finally { setBusy(false); }
  };

  const decline = async () => {
    if (declineReason.trim().length < 10) { toast.error('Please provide a reason (min 10 chars)'); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/proposals/public/decline?t=${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: declineReason.trim() }),
      });
      const d = await r.json();
      if (r.ok) { toast.success('Proposal declined. Our team will reach out.'); setDecideMode(null); window.location.reload(); }
      else { toast.error(d.detail || 'Decline failed'); }
    } finally { setBusy(false); }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-leamss-bg_white">
        <div className="text-slate-400">Loading your proposal…</div>
      </div>
    );
  }

  if (err) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-leamss-bg_white p-6">
        <Card className="max-w-md p-8 text-center border-leamss-red/30" data-testid="public-proposal-error">
          <AlertTriangle className="h-12 w-12 text-leamss-red mx-auto mb-3" />
          <h1 className="text-xl font-bold text-leamss-red mb-2">Link unavailable</h1>
          <p className="text-sm text-slate-600 mb-4">{err}</p>
          <p className="text-xs text-slate-500">Contact sales: <a className="text-leamss-teal" href="mailto:hello@leamss.com">hello@leamss.com</a></p>
        </Card>
      </div>
    );
  }

  const p = data.proposal;
  const isSent = p.status === 'sent';
  const isAccepted = p.status === 'accepted' || accepted;
  const isDeclined = p.status === 'declined';

  return (
    <div className="min-h-screen bg-leamss-bg_white pb-12" data-testid="public-proposal-view">
      {/* Hero */}
      <header className="bg-gradient-to-br from-leamss-teal to-emerald-700 text-white py-10">
        <div className="max-w-4xl mx-auto px-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xl font-bold">
              <span className="text-white">LE</span>
              <span className="text-leamss-orange">AM</span>
              <span style={{color:'#fda4af'}}>SS</span>
            </span>
            <Badge className={
              isAccepted ? 'bg-emerald-500' :
              isDeclined ? 'bg-leamss-red' : 'bg-leamss-orange'
            } data-testid="proposal-status-badge">
              {p.status}
            </Badge>
          </div>
          <h1 className="text-3xl font-bold mb-1">Your Migration Proposal</h1>
          <p className="text-sm opacity-90">Ref <code className="bg-white/20 px-2 py-0.5 rounded">{p.id.slice(0,12).toUpperCase()}</code> · Expires {(p.expires_at || '').slice(0, 10)}</p>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 mt-6 space-y-5">
        {/* Status messaging */}
        {isAccepted && !accepted && (
          <Card className="p-5 bg-emerald-50 border-emerald-300 flex items-start gap-3" data-testid="already-accepted-banner">
            <CheckCircle className="h-6 w-6 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-bold text-emerald-700">Already accepted</h3>
              <p className="text-sm text-emerald-700/80 mt-1">This proposal was accepted on {(p.accepted_at || '').slice(0, 10)}.</p>
              <a href="/client-portal/login" className="text-sm text-leamss-teal underline mt-2 inline-block">Login to your Client Portal →</a>
            </div>
          </Card>
        )}
        {isDeclined && (
          <Card className="p-5 bg-red-50 border-leamss-red/30 flex items-start gap-3">
            <XCircle className="h-6 w-6 text-leamss-red shrink-0 mt-0.5" />
            <div>
              <h3 className="font-bold text-leamss-red">Proposal declined</h3>
              <p className="text-sm text-slate-600 mt-1">Our sales team will contact you to discuss.</p>
            </div>
          </Card>
        )}
        {accepted && (
          <Card className="p-5 bg-emerald-50 border-emerald-300" data-testid="accept-success-banner">
            <div className="flex items-center gap-3 mb-3">
              <CheckCircle className="h-8 w-8 text-emerald-600" />
              <h3 className="text-xl font-bold text-emerald-700">Proposal accepted! 🎉</h3>
            </div>
            <p className="text-sm text-slate-700">Your case is now active. Redirecting to your Client Portal…</p>
          </Card>
        )}

        {/* Pricing summary */}
        <Card className="p-6" data-testid="pricing-summary">
          <h2 className="text-lg font-bold text-leamss-teal mb-1 flex items-center gap-2">
            <Sparkles className="h-5 w-5" /> Investment Summary
          </h2>
          <p className="text-xs text-slate-500 mb-4">All fees in INR · Includes GST at 18%</p>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>Product: <strong>{p.product_name}</strong></div>
            <div>Country / Visa: <strong>{p.country} · {p.service_type}</strong></div>
            <div className="text-slate-600">Base Professional Fees</div><div className="text-right">{inrFmt(p.base_fees_inr)}</div>
            <div className="text-slate-600">Add-on Products</div><div className="text-right">{inrFmt(p.addon_total_inr)}</div>
            <div className="text-leamss-teal">Coupon Savings</div><div className="text-right text-leamss-teal">−{inrFmt(p.coupon_total_inr)}</div>
            {p.admin_discount_inr > 0 && (<>
              <div className="text-leamss-red">Special Discount</div><div className="text-right text-leamss-red">−{inrFmt(p.admin_discount_inr)}</div>
            </>)}
            <div className="text-slate-600">Subtotal</div><div className="text-right">{inrFmt(p.subtotal_inr)}</div>
            <div className="text-slate-600">GST 18%</div><div className="text-right">{inrFmt(p.gst_inr)}</div>
          </div>
          <div className="border-t border-leamss-orange pt-3 mt-3 flex items-baseline justify-between">
            <span className="text-sm uppercase font-bold text-slate-500">Your Total</span>
            <span className="text-3xl font-bold text-leamss-orange" data-testid="total-inr">{inrFmt(p.total_inr)}</span>
          </div>
          <a href={`${API}${data.pdf_url}`} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-1 text-sm text-leamss-teal hover:underline mt-4"
             data-testid="download-pdf-link">
            <Download className="h-4 w-4" /> Download full PDF
          </a>
        </Card>

        {/* PDF iframe preview (best-effort; some browsers may block cross-origin) */}
        <Card className="p-0 overflow-hidden h-[500px]" data-testid="pdf-preview">
          <iframe
            src={`${API}${data.pdf_url}`}
            className="w-full h-full border-0"
            title="Proposal PDF"
            onError={() => {}}
          />
        </Card>

        {/* Decision area */}
        {isSent && !accepted && (
          <Card className="p-6 border-leamss-orange/30">
            {!decideMode ? (
              <>
                <h2 className="text-lg font-bold text-leamss-teal mb-1 flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5" /> Ready to proceed?
                </h2>
                <p className="text-sm text-slate-500 mb-4">No login required — just one click to activate your case.</p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <Button onClick={accept} disabled={busy}
                          className="flex-1 bg-leamss-orange hover:bg-leamss-orange/90 text-white font-bold text-base py-6"
                          data-testid="public-accept-btn">
                    {busy ? 'Processing…' : '✓ Accept & Activate My Case'}
                  </Button>
                  <Button onClick={() => setDecideMode('decline')} variant="outline"
                          className="border-leamss-red text-leamss-red hover:bg-red-50 sm:flex-none px-6"
                          data-testid="public-decline-btn">
                    Decline
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Label className="text-base font-bold">Reason for declining</Label>
                <p className="text-xs text-slate-500 mb-2">Helps us improve our service (min 10 chars)</p>
                <textarea rows={4} value={declineReason}
                          onChange={(e) => setDeclineReason(e.target.value)}
                          className="w-full border border-slate-300 rounded p-3 text-sm"
                          placeholder="e.g. Pricing concerns / Need more time / Going with another provider"
                          data-testid="public-decline-reason" />
                <div className="flex gap-2 mt-3">
                  <Button variant="ghost" onClick={() => { setDecideMode(null); setDeclineReason(''); }}>Cancel</Button>
                  <Button onClick={decline} disabled={busy}
                          className="bg-leamss-red hover:bg-leamss-red/90 text-white"
                          data-testid="confirm-public-decline">
                    {busy ? 'Submitting…' : 'Confirm Decline'}
                  </Button>
                </div>
              </>
            )}
          </Card>
        )}

        {/* Contact card */}
        <Card className="p-5 bg-leamss-teal/5 border-leamss-teal/20">
          <h3 className="font-bold text-leamss-teal mb-2 flex items-center gap-2">
            <FileText className="h-4 w-4" /> Need to discuss before deciding?
          </h3>
          <p className="text-sm text-slate-600 mb-3">Your dedicated LEAMSS migration consultant is one click away:</p>
          <div className="grid sm:grid-cols-2 gap-2 text-sm">
            <a href="mailto:hello@leamss.com" className="flex items-center gap-1 text-leamss-teal hover:underline"><Mail className="h-3 w-3"/>hello@leamss.com</a>
            <a href="tel:+919999999999" className="flex items-center gap-1 text-leamss-teal hover:underline"><Phone className="h-3 w-3"/>+91 99999 99999</a>
          </div>
        </Card>

        <p className="text-xs text-slate-400 text-center mt-6">
          © LEAMSS · Licensed Migration Specialists · This proposal is valid until {(p.expires_at || '').slice(0, 10)}.
        </p>
      </div>
    </div>
  );
}
