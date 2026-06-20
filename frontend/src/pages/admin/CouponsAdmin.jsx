/**
 * Phase 20.8 — Coupons Admin
 *
 * CRUD + validation engine for discount coupons.
 * Admin can create/edit/archive coupons; sales can browse + validate.
 * Brand: leamss-teal (primary), leamss-orange (discount), leamss-red (archive).
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
import { Tag, Plus, Archive, RefreshCw, CheckCircle, XCircle, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const inrFmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`;
const tokenHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

const EMPTY_FORM = {
  code: '', description: '',
  discount_type: 'pct', discount_value: 10,
  applicable_to: 'any',
  min_order_value_inr: '',
  valid_from: new Date().toISOString().slice(0, 16),
  valid_until: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 16),
  usage_limit_total: '',
  usage_limit_per_client: 1,
  stackable: false,
};

export default function CouponsAdmin() {
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [filter, setFilter] = useState('all');
  const [validating, setValidating] = useState({ code: '', order: 100000, result: null });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/coupons?status=${filter}`, { headers: tokenHeaders() });
      if (r.ok) {
        const d = await r.json();
        setCoupons(d.coupons || []);
      }
    } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const seedDefaults = async () => {
    const r = await fetch(`${API}/api/coupons/seed`, { method: 'POST', headers: tokenHeaders() });
    if (r.ok) {
      const d = await r.json();
      toast.success(`Seeded ${d.created.length} new · ${d.skipped.length} already exists`);
      load();
    } else { toast.error('Seed failed'); }
  };

  const submitForm = async () => {
    const payload = {
      ...form,
      code: form.code.toUpperCase().trim(),
      discount_value: Number(form.discount_value),
      min_order_value_inr: form.min_order_value_inr ? Number(form.min_order_value_inr) : null,
      usage_limit_total: form.usage_limit_total ? Number(form.usage_limit_total) : null,
      usage_limit_per_client: Number(form.usage_limit_per_client),
      valid_from: new Date(form.valid_from).toISOString(),
      valid_until: new Date(form.valid_until).toISOString(),
    };
    const r = await fetch(`${API}/api/coupons`, {
      method: 'POST', headers: tokenHeaders(), body: JSON.stringify(payload),
    });
    if (r.ok) {
      toast.success(`Coupon ${payload.code} created · revocable for 24h`);
      setShowForm(false); setForm(EMPTY_FORM); load();
    } else {
      const e = await r.json().catch(() => ({}));
      toast.error(`Create failed: ${e.detail || r.status}`);
    }
  };

  const archive = async (id, code) => {
    if (!window.confirm(`Archive coupon ${code}?`)) return;
    const r = await fetch(`${API}/api/coupons/${id}`, { method: 'DELETE', headers: tokenHeaders() });
    if (r.ok) { toast.success(`Archived ${code}`); load(); }
    else { toast.error('Archive failed'); }
  };

  const runValidator = async () => {
    if (!validating.code) { toast.error('Enter a code'); return; }
    const r = await fetch(
      `${API}/api/coupons/validate?code=${encodeURIComponent(validating.code)}&order_value_inr=${validating.order}`,
      { headers: tokenHeaders() }
    );
    if (r.status === 404) {
      setValidating(v => ({ ...v, result: { eligible: false, reason: 'Unknown code' } }));
      return;
    }
    if (r.ok) {
      const d = await r.json();
      setValidating(v => ({ ...v, result: d }));
    }
  };

  return (
    <div className="min-h-screen bg-leamss-bg_white p-6" data-testid="coupons-admin">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-leamss-teal flex items-center gap-2">
              <Tag className="h-7 w-7" /> Coupons Engine
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Phase 20.8 · Idempotent application · 24h revocable via import_batches
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={seedDefaults} data-testid="seed-defaults-btn">
              <Sparkles className="h-4 w-4 mr-1" /> Seed Defaults
            </Button>
            <Button
              className="bg-leamss-teal hover:bg-leamss-teal/90 text-white"
              onClick={() => setShowForm(!showForm)}
              data-testid="new-coupon-btn"
            >
              <Plus className="h-4 w-4 mr-1" /> New Coupon
            </Button>
          </div>
        </div>

        {/* VALIDATOR CARD */}
        <Card className="p-4 mb-6 border-leamss-teal/40 bg-gradient-to-br from-leamss-teal_50 to-emerald-50">
          <Label className="text-xs font-bold uppercase text-leamss-teal">Quick Validator</Label>
          <div className="flex gap-3 mt-2 items-end flex-wrap">
            <div>
              <Label className="text-xs">Code</Label>
              <Input
                value={validating.code}
                onChange={(e) => setValidating(v => ({ ...v, code: e.target.value.toUpperCase() }))}
                placeholder="LUMPSUM20"
                className="w-40"
                data-testid="validator-code-input"
              />
            </div>
            <div>
              <Label className="text-xs">Order Value (₹)</Label>
              <Input
                type="number"
                value={validating.order}
                onChange={(e) => setValidating(v => ({ ...v, order: Number(e.target.value) }))}
                className="w-32"
                data-testid="validator-order-input"
              />
            </div>
            <Button onClick={runValidator} className="bg-leamss-orange hover:bg-leamss-orange/90 text-white"
                    data-testid="run-validator-btn">
              Validate
            </Button>
            {validating.result && (
              <div className="ml-2 text-sm">
                {validating.result.eligible ? (
                  <span className="text-emerald-700 flex items-center gap-1">
                    <CheckCircle className="h-4 w-4" /> Eligible · saves {inrFmt(validating.result.discount_amount_inr)}
                  </span>
                ) : (
                  <span className="text-leamss-red flex items-center gap-1">
                    <XCircle className="h-4 w-4" /> {validating.result.reason}
                  </span>
                )}
              </div>
            )}
          </div>
        </Card>

        {/* CREATE FORM */}
        {showForm && (
          <Card className="p-4 mb-6 border-leamss-orange/40" data-testid="coupon-form">
            <h3 className="font-bold text-leamss-orange mb-3">Create New Coupon</h3>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <Label>Code *</Label>
                <Input value={form.code}
                       onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                       placeholder="DIWALI25" data-testid="form-code" />
              </div>
              <div>
                <Label>Discount Type</Label>
                <Select value={form.discount_type} onValueChange={(v) => setForm({ ...form, discount_type: v })}>
                  <SelectTrigger data-testid="form-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pct">Percentage</SelectItem>
                    <SelectItem value="fixed">Fixed Amount ₹</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Value ({form.discount_type === 'pct' ? '%' : '₹'})</Label>
                <Input type="number" value={form.discount_value}
                       onChange={(e) => setForm({ ...form, discount_value: e.target.value })}
                       data-testid="form-value" />
              </div>
              <div className="col-span-3">
                <Label>Description *</Label>
                <Textarea rows={2} value={form.description}
                          onChange={(e) => setForm({ ...form, description: e.target.value })}
                          placeholder="20% off professional fees — Sir's brochure offer"
                          data-testid="form-description" />
              </div>
              <div>
                <Label>Applicable To</Label>
                <Select value={form.applicable_to} onValueChange={(v) => setForm({ ...form, applicable_to: v })}>
                  <SelectTrigger data-testid="form-applicable"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any product</SelectItem>
                    <SelectItem value="professional_fees">Professional fees only</SelectItem>
                    <SelectItem value="addon_products">Add-on products only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Min Order (₹)</Label>
                <Input type="number" value={form.min_order_value_inr}
                       onChange={(e) => setForm({ ...form, min_order_value_inr: e.target.value })}
                       placeholder="optional" data-testid="form-min-order" />
              </div>
              <div>
                <Label>Total Usage Cap</Label>
                <Input type="number" value={form.usage_limit_total}
                       onChange={(e) => setForm({ ...form, usage_limit_total: e.target.value })}
                       placeholder="optional" data-testid="form-cap" />
              </div>
              <div>
                <Label>Valid From</Label>
                <Input type="datetime-local" value={form.valid_from}
                       onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
                       data-testid="form-from" />
              </div>
              <div>
                <Label>Valid Until</Label>
                <Input type="datetime-local" value={form.valid_until}
                       onChange={(e) => setForm({ ...form, valid_until: e.target.value })}
                       data-testid="form-until" />
              </div>
              <div>
                <Label>Per-Client Cap</Label>
                <Input type="number" value={form.usage_limit_per_client}
                       onChange={(e) => setForm({ ...form, usage_limit_per_client: e.target.value })}
                       data-testid="form-per-client" />
              </div>
            </div>
            <div className="flex gap-2 mt-4 justify-end">
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button className="bg-leamss-teal hover:bg-leamss-teal/90 text-white"
                      onClick={submitForm} data-testid="submit-coupon-btn">
                Create Coupon
              </Button>
            </div>
          </Card>
        )}

        {/* FILTER + LIST */}
        <div className="flex items-center gap-3 mb-3">
          <Label>Filter:</Label>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-44" data-testid="filter-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="expired">Expired</SelectItem>
              <SelectItem value="exhausted">Exhausted</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="ghost" size="sm" onClick={load} data-testid="refresh-btn">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <span className="text-xs text-slate-500 ml-auto">{coupons.length} coupon(s)</span>
        </div>

        <Card className="p-0 overflow-hidden">
          <table className="w-full text-sm" data-testid="coupons-table">
            <thead className="bg-leamss-teal/10 text-xs uppercase text-leamss-teal">
              <tr>
                <th className="text-left p-3">Code</th>
                <th className="text-left p-3">Discount</th>
                <th className="text-left p-3">Applies To</th>
                <th className="text-left p-3">Used</th>
                <th className="text-left p-3">Status</th>
                <th className="text-right p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {coupons.length === 0 && (
                <tr><td colSpan="6" className="p-8 text-center text-slate-400">
                  No coupons. Click "Seed Defaults" for the 3 brochure offers.
                </td></tr>
              )}
              {coupons.map((c) => (
                <tr key={c.id} className="border-t hover:bg-leamss-teal/5" data-testid={`coupon-row-${c.code}`}>
                  <td className="p-3 font-mono font-bold text-leamss-teal">{c.code}</td>
                  <td className="p-3">
                    <span className="text-leamss-orange font-bold">
                      {c.discount_type === 'pct' ? `${c.discount_value}%` : inrFmt(c.discount_value)}
                    </span>
                    <p className="text-xs text-slate-500">{c.description}</p>
                  </td>
                  <td className="p-3 text-xs">{c.applicable_to}</td>
                  <td className="p-3">
                    {c.used_count || 0}
                    {c.usage_limit_total && <span className="text-slate-400">/{c.usage_limit_total}</span>}
                  </td>
                  <td className="p-3">
                    <Badge variant={c.computed_status === 'active' ? 'default' : 'secondary'}
                           className={c.computed_status === 'active' ? 'bg-leamss-teal' :
                                      c.computed_status === 'expired' ? 'bg-leamss-red' : ''}>
                      {c.computed_status}
                    </Badge>
                  </td>
                  <td className="p-3 text-right">
                    {c.computed_status !== 'archived' && (
                      <Button variant="ghost" size="sm" onClick={() => archive(c.id, c.code)}
                              data-testid={`archive-${c.code}`}>
                        <Archive className="h-4 w-4 text-leamss-red" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
