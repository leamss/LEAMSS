/**
 * Phase 20.8 — Proposal Builder
 *
 * Sales/admin builds proposal pulling fees + add-ons + coupons + admin discount.
 * Sends to client, downloads PDF.
 * Brand: leamss-teal (primary), leamss-orange (totals/CTA), leamss-red (admin discount).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { FileText, Plus, X, Send, Download, CheckCircle, Tag, RefreshCw, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const inrFmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`;
const tokenHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

export default function ProposalBuilder() {
  const [step, setStep] = useState(1);
  const [products, setProducts] = useState([]);
  const [proposal, setProposal] = useState(null);

  const [form, setForm] = useState({
    client_id: '', product_id: '',
    base_fees_inr: 0, addon_products: [],
    applied_coupon_codes: [],
    admin_special_discount_inr: 0, admin_special_discount_reason: '',
    closing_message: '', custom_terms: '',
  });
  const [newAddon, setNewAddon] = useState({ name: '', price_inr: '' });
  const [newCoupon, setNewCoupon] = useState('');
  const [livePreview, setLivePreview] = useState(null);

  const loadProducts = useCallback(async () => {
    const r = await fetch(`${API}/api/products?status=active`, { headers: tokenHeaders() });
    if (r.ok) {
      const d = await r.json();
      setProducts(d.products || d || []);
    }
  }, []);

  useEffect(() => { loadProducts(); }, [loadProducts]);

  const selectProduct = (pid) => {
    const p = products.find(x => x.id === pid);
    setForm({ ...form, product_id: pid,
              base_fees_inr: p?.base_fee || p?.service_price || 0 });
  };

  const addAddon = () => {
    if (!newAddon.name || !newAddon.price_inr) return;
    setForm({ ...form, addon_products: [...form.addon_products,
            { name: newAddon.name, price_inr: Number(newAddon.price_inr) }] });
    setNewAddon({ name: '', price_inr: '' });
  };

  const removeAddon = (i) => {
    setForm({ ...form, addon_products: form.addon_products.filter((_, idx) => idx !== i) });
  };

  const validateAndAddCoupon = async () => {
    if (!newCoupon) return;
    const order = form.base_fees_inr + form.addon_products.reduce((s, a) => s + Number(a.price_inr), 0);
    const r = await fetch(
      `${API}/api/coupons/validate?code=${encodeURIComponent(newCoupon)}&order_value_inr=${order}`,
      { headers: tokenHeaders() }
    );
    if (r.status === 404) { toast.error(`Coupon ${newCoupon} not found`); return; }
    const d = await r.json();
    if (!d.eligible) { toast.error(d.reason); return; }
    if (form.applied_coupon_codes.includes(newCoupon.toUpperCase())) {
      toast.error('Already applied'); return;
    }
    setForm({ ...form, applied_coupon_codes: [...form.applied_coupon_codes, newCoupon.toUpperCase()] });
    setNewCoupon('');
    toast.success(`${newCoupon} applied · saves ${inrFmt(d.discount_amount_inr)}`);
  };

  const removeCoupon = (code) => {
    setForm({ ...form, applied_coupon_codes: form.applied_coupon_codes.filter(c => c !== code) });
  };

  // Live preview totals on each form change
  useEffect(() => {
    const addonTotal = form.addon_products.reduce((s, a) => s + Number(a.price_inr || 0), 0);
    const subtotalPre = Number(form.base_fees_inr || 0) + addonTotal;
    // Approx coupon — server gives exact value at create time
    setLivePreview({ addon_total: addonTotal, subtotal_pre: subtotalPre });
  }, [form.base_fees_inr, form.addon_products]);

  const createProposal = async () => {
    if (!form.client_id || !form.product_id || !form.base_fees_inr) {
      toast.error('Client ID, Product and Base Fees are required'); return;
    }
    const payload = {
      ...form,
      base_fees_inr: Number(form.base_fees_inr),
      admin_special_discount_inr: Number(form.admin_special_discount_inr || 0),
    };
    const r = await fetch(`${API}/api/proposals`, {
      method: 'POST', headers: tokenHeaders(), body: JSON.stringify(payload),
    });
    if (r.ok) {
      const p = await r.json();
      setProposal(p); setStep(3);
      toast.success(`Proposal created · ${inrFmt(p.total_inr)} · revocable 24h`);
    } else {
      const e = await r.json().catch(() => ({}));
      toast.error(`Create failed: ${e.detail || r.status}`);
    }
  };

  const sendProposal = async () => {
    const r = await fetch(`${API}/api/proposals/${proposal.id}/send`,
                          { method: 'POST', headers: tokenHeaders() });
    if (r.ok) {
      const d = await r.json();
      setProposal({ ...proposal, status: 'sent' });
      toast.success(`Sent · ${d.delivery}`);
    } else { toast.error('Send failed'); }
  };

  const downloadPDF = async () => {
    const r = await fetch(`${API}/api/proposals/${proposal.id}/pdf`, { headers: tokenHeaders() });
    if (!r.ok) { toast.error('PDF generation failed'); return; }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `proposal_${proposal.id.slice(0, 8)}.${r.headers.get('content-type')?.includes('pdf') ? 'pdf' : 'html'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-leamss-bg_white p-6" data-testid="proposal-builder">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-leamss-teal flex items-center gap-2">
            <FileText className="h-7 w-7" /> Proposal Builder
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Phase 20.8 · WeasyPrint-powered PDF · Cascading discounts · 24h revocable
          </p>
        </div>

        {/* Stepper */}
        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3].map((n) => (
            <div key={n} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                step >= n ? 'bg-leamss-teal text-white' : 'bg-slate-200 text-slate-500'
              }`} data-testid={`step-indicator-${n}`}>
                {n}
              </div>
              <span className={step >= n ? 'text-leamss-teal font-bold' : 'text-slate-400'}>
                {n === 1 ? 'Client & Product' : n === 2 ? 'Discounts & Terms' : 'Send & PDF'}
              </span>
              {n < 3 && <div className="w-12 h-0.5 bg-slate-200" />}
            </div>
          ))}
        </div>

        {/* STEP 1 */}
        {step === 1 && (
          <Card className="p-6">
            <h2 className="text-lg font-bold text-leamss-teal mb-4">Step 1 — Client & Product</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Client ID *</Label>
                <Input value={form.client_id}
                       onChange={(e) => setForm({ ...form, client_id: e.target.value })}
                       placeholder="client_xxx" data-testid="form-client-id" />
              </div>
              <div>
                <Label>Product *</Label>
                <Select value={form.product_id} onValueChange={selectProduct}>
                  <SelectTrigger data-testid="form-product"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    {products.map(p => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name} ({p.country} · {p.service_type || p.visa_type})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Base Professional Fees (₹) *</Label>
                <Input type="number" value={form.base_fees_inr}
                       onChange={(e) => setForm({ ...form, base_fees_inr: e.target.value })}
                       data-testid="form-base-fees" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button className="bg-leamss-teal hover:bg-leamss-teal/90 text-white"
                      onClick={() => setStep(2)} data-testid="next-step-2">Next →</Button>
            </div>
          </Card>
        )}

        {/* STEP 2 */}
        {step === 2 && (
          <Card className="p-6">
            <h2 className="text-lg font-bold text-leamss-teal mb-4">Step 2 — Add-ons, Coupons & Admin Discount</h2>

            {/* Add-ons */}
            <div className="mb-4">
              <Label className="text-sm font-bold">Add-on Products</Label>
              <div className="flex gap-2 mt-2">
                <Input placeholder="Name (e.g. Document Review)" value={newAddon.name}
                       onChange={(e) => setNewAddon({ ...newAddon, name: e.target.value })}
                       className="flex-1" data-testid="addon-name" />
                <Input type="number" placeholder="₹ price" value={newAddon.price_inr}
                       onChange={(e) => setNewAddon({ ...newAddon, price_inr: e.target.value })}
                       className="w-32" data-testid="addon-price" />
                <Button onClick={addAddon} variant="outline" data-testid="add-addon-btn">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {form.addon_products.map((a, i) => (
                <div key={i} className="flex items-center justify-between mt-2 p-2 bg-leamss-teal/10 rounded text-sm">
                  <span>+ {a.name}</span>
                  <span className="flex items-center gap-3">
                    <span className="font-bold">{inrFmt(a.price_inr)}</span>
                    <X className="h-4 w-4 cursor-pointer text-leamss-red"
                       onClick={() => removeAddon(i)} data-testid={`remove-addon-${i}`} />
                  </span>
                </div>
              ))}
            </div>

            {/* Coupons */}
            <div className="mb-4">
              <Label className="text-sm font-bold">Coupons</Label>
              <div className="flex gap-2 mt-2">
                <Input placeholder="LUMPSUM20" value={newCoupon}
                       onChange={(e) => setNewCoupon(e.target.value.toUpperCase())}
                       className="flex-1" data-testid="coupon-input" />
                <Button onClick={validateAndAddCoupon}
                        className="bg-leamss-orange hover:bg-leamss-orange/90 text-white"
                        data-testid="apply-coupon-btn">
                  <Tag className="h-4 w-4 mr-1" /> Validate & Apply
                </Button>
              </div>
              {form.applied_coupon_codes.map((code) => (
                <Badge key={code} variant="outline"
                       className="mt-2 mr-2 bg-leamss-teal/10 text-leamss-teal border-leamss-teal/40">
                  {code}
                  <X className="h-3 w-3 ml-1 cursor-pointer" onClick={() => removeCoupon(code)}
                     data-testid={`remove-coupon-${code}`} />
                </Badge>
              ))}
            </div>

            {/* Admin Special */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div>
                <Label className="text-sm font-bold text-leamss-red">Admin Special Discount (₹)</Label>
                <Input type="number" value={form.admin_special_discount_inr}
                       onChange={(e) => setForm({ ...form, admin_special_discount_inr: e.target.value })}
                       data-testid="form-admin-discount" />
              </div>
              <div>
                <Label className="text-sm font-bold">Reason (audited)</Label>
                <Input value={form.admin_special_discount_reason}
                       onChange={(e) => setForm({ ...form, admin_special_discount_reason: e.target.value })}
                       placeholder="Festive Q4 / VIP / Bulk corporate"
                       data-testid="form-discount-reason" />
              </div>
            </div>

            {/* Closing & Terms */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div>
                <Label className="text-sm">Closing Message</Label>
                <Textarea rows={3} value={form.closing_message}
                          onChange={(e) => setForm({ ...form, closing_message: e.target.value })}
                          placeholder="Optional — overrides default" data-testid="form-closing" />
              </div>
              <div>
                <Label className="text-sm">Custom Terms</Label>
                <Textarea rows={3} value={form.custom_terms}
                          onChange={(e) => setForm({ ...form, custom_terms: e.target.value })}
                          placeholder="Optional — appears in PDF Section 4"
                          data-testid="form-terms" />
              </div>
            </div>

            {livePreview && (
              <div className="bg-leamss-orange/10 p-3 rounded border border-leamss-orange/30 mb-4">
                <p className="text-xs uppercase text-leamss-orange font-bold mb-1">Live Preview</p>
                <p className="text-sm">Base + Add-ons (pre-discount): <strong>{inrFmt(livePreview.subtotal_pre)}</strong></p>
                <p className="text-xs text-slate-500">Final total computed on Create with coupons + GST</p>
              </div>
            )}

            <div className="flex justify-between gap-2 mt-4">
              <Button variant="outline" onClick={() => setStep(1)}>← Back</Button>
              <Button className="bg-leamss-teal hover:bg-leamss-teal/90 text-white"
                      onClick={createProposal} data-testid="create-proposal-btn">
                <Sparkles className="h-4 w-4 mr-1" /> Create Proposal
              </Button>
            </div>
          </Card>
        )}

        {/* STEP 3 */}
        {step === 3 && proposal && (
          <Card className="p-6">
            <h2 className="text-lg font-bold text-leamss-teal mb-4">Step 3 — Send & Download</h2>
            <div className="bg-gradient-to-br from-leamss-teal_50 to-emerald-50 p-4 rounded mb-4">
              <p className="text-xs uppercase text-leamss-teal font-bold">Proposal Reference</p>
              <p className="text-xl font-mono font-bold">{proposal.id.slice(0, 12).toUpperCase()}</p>
              <Badge className="bg-leamss-teal mt-1">{proposal.status}</Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
              <div>Product: <strong>{proposal.product_name}</strong></div>
              <div>Country/Visa: <strong>{proposal.country} · {proposal.service_type}</strong></div>
              <div>Base Fees: {inrFmt(proposal.base_fees_inr)}</div>
              <div>Add-on Total: {inrFmt(proposal.addon_total_inr)}</div>
              <div className="text-leamss-teal">Coupons: −{inrFmt(proposal.coupon_total_inr)}</div>
              <div className="text-leamss-red">Admin Discount: −{inrFmt(proposal.admin_discount_inr)}</div>
              <div>Subtotal: {inrFmt(proposal.subtotal_inr)}</div>
              <div>GST 18%: {inrFmt(proposal.gst_inr)}</div>
              <div className="col-span-2 border-t pt-2 mt-2">
                <span className="text-xl font-bold text-leamss-orange">Total: {inrFmt(proposal.total_inr)}</span>
              </div>
            </div>

            <div className="flex gap-2">
              {proposal.status === 'draft' && (
                <Button onClick={sendProposal} className="bg-leamss-teal hover:bg-leamss-teal/90 text-white"
                        data-testid="send-proposal-btn">
                  <Send className="h-4 w-4 mr-1" /> Send to Client
                </Button>
              )}
              <Button onClick={downloadPDF} variant="outline" data-testid="download-pdf-btn">
                <Download className="h-4 w-4 mr-1" /> Download PDF
              </Button>
              <Button onClick={() => { setStep(1); setProposal(null);
                                       setForm({ client_id: '', product_id: '',
                                                 base_fees_inr: 0, addon_products: [],
                                                 applied_coupon_codes: [],
                                                 admin_special_discount_inr: 0,
                                                 admin_special_discount_reason: '',
                                                 closing_message: '', custom_terms: '' }); }}
                      variant="outline" data-testid="new-proposal-btn">
                <RefreshCw className="h-4 w-4 mr-1" /> New Proposal
              </Button>
            </div>

            {proposal.status === 'sent' && (
              <p className="text-xs text-emerald-700 mt-3 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" /> Proposal sent · expires {(proposal.expires_at || '').slice(0, 10)}
              </p>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
