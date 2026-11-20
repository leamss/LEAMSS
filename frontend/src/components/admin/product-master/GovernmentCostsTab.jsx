import React from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Trash2, DollarSign, ExternalLink, Calendar, Calculator, ShieldCheck } from 'lucide-react';

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

export default function GovernmentCostsTab({
  costs,
  onChangeCosts,
  readOnly = false,
}) {
  const lineItems = costs?.line_items || [];
  const currency = costs?.currency || 'AUD';
  const exchangeRate = parseFloat(costs?.exchange_rate_to_inr) || 55.0;

  const updateCosts = (patch) => {
    if (readOnly) return;
    onChangeCosts({ ...costs, ...patch });
  };

  const addLineItem = () => {
    if (readOnly) return;
    updateCosts({
      line_items: [
        ...lineItems,
        {
          applicant_type: 'Primary Applicant',
          amount: 0,
          currency: currency,
          inr_approx: 0,
          notes: '',
        },
      ],
    });
  };

  const updateLineItem = (idx, patch) => {
    if (readOnly) return;
    const next = [...lineItems];
    const current = { ...next[idx], ...patch };
    if ('amount' in patch) {
      const amt = parseFloat(patch.amount) || 0;
      current.inr_approx = Math.round(amt * exchangeRate);
    }
    next[idx] = current;
    updateCosts({ line_items: next });
  };

  const removeLineItem = (idx) => {
    if (readOnly) return;
    updateCosts({ line_items: lineItems.filter((_, i) => i !== idx) });
  };

  // Pre-seed standard lines if empty
  const seedStandard = () => {
    if (readOnly) return;
    updateCosts({
      currency: currency || 'AUD',
      exchange_rate_to_inr: exchangeRate,
      line_items: [
        {
          applicant_type: 'Primary Applicant',
          amount: currency === 'AUD' ? 4765 : 1500,
          currency: currency,
          inr_approx: Math.round((currency === 'AUD' ? 4765 : 1500) * exchangeRate),
          notes: 'Department visa application lodgement fee (VAC)',
        },
        {
          applicant_type: 'Adult Secondary Applicant (18+)',
          amount: currency === 'AUD' ? 2385 : 750,
          currency: currency,
          inr_approx: Math.round((currency === 'AUD' ? 2385 : 750) * exchangeRate),
          notes: 'Spouse or adult dependent fee',
        },
        {
          applicant_type: 'Child Secondary Applicant (under 18)',
          amount: currency === 'AUD' ? 1195 : 375,
          currency: currency,
          inr_approx: Math.round((currency === 'AUD' ? 1195 : 375) * exchangeRate),
          notes: 'Per dependent child',
        },
      ],
    });
  };

  const totalPrimarySecondaryINR = lineItems.reduce((acc, it) => acc + (parseFloat(it.inr_approx) || 0), 0);

  return (
    <div className="space-y-4 text-xs">
      <Card className="p-4 space-y-4 bg-white border border-slate-200">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b">
          <div>
            <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-emerald-600" />
              Statutory Government Fee Schedule
            </h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Official visa department application charges (VAC), spouse fees, and minor child charges.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {lineItems.length === 0 && !readOnly && (
              <Button size="sm" variant="outline" onClick={seedStandard} className="h-7 text-xs border-emerald-300 text-emerald-800">
                + Seed Standard Rates
              </Button>
            )}
            {!readOnly && (
              <Button size="sm" onClick={addLineItem} className="h-7 text-xs bg-slate-800 hover:bg-slate-900 text-white gap-1">
                <Plus className="h-3 w-3" />Add Fee Item
              </Button>
            )}
          </div>
        </div>

        {/* Currency & Exchange Rate Bar */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3 bg-slate-50 border rounded-lg">
          <div>
            <Label className="text-[11px] font-bold text-slate-700">Government Currency</Label>
            <select
              disabled={readOnly}
              value={currency}
              onChange={(e) => updateCosts({ currency: e.target.value })}
              className="mt-1 flex h-8 w-full rounded border border-input bg-white px-2 text-xs font-bold"
            >
              <option value="AUD">AUD (Australian Dollar - A$)</option>
              <option value="CAD">CAD (Canadian Dollar - C$)</option>
              <option value="USD">USD (US Dollar - $)</option>
              <option value="GBP">GBP (British Pound - £)</option>
              <option value="EUR">EUR (Euro - €)</option>
              <option value="NZD">NZD (New Zealand Dollar - NZ$)</option>
              <option value="SGD">SGD (Singapore Dollar - S$)</option>
              <option value="INR">INR (Indian Rupee - ₹)</option>
            </select>
          </div>

          <div>
            <Label className="text-[11px] font-bold text-slate-700">Exchange Rate to INR (₹)</Label>
            <Input
              type="number"
              step="0.01"
              disabled={readOnly}
              className="h-8 text-xs mt-1 font-bold"
              value={exchangeRate}
              onChange={(e) => {
                const newRate = parseFloat(e.target.value) || 1;
                const nextLines = lineItems.map((it) => ({
                  ...it,
                  inr_approx: Math.round((parseFloat(it.amount) || 0) * newRate),
                }));
                updateCosts({ exchange_rate_to_inr: newRate, line_items: nextLines });
              }}
              placeholder="e.g. 55.00"
            />
          </div>

          <div>
            <Label className="text-[11px] font-bold text-slate-700">Effective / Gazette Date</Label>
            <Input
              type="date"
              disabled={readOnly}
              className="h-8 text-xs mt-1"
              value={costs?.effective_date || ''}
              onChange={(e) => updateCosts({ effective_date: e.target.value })}
            />
          </div>

          <div>
            <Label className="text-[11px] font-bold text-slate-700">Official Source Fee URL</Label>
            <div className="flex items-center gap-1 mt-1">
              <Input
                disabled={readOnly}
                className="h-8 text-xs flex-1"
                placeholder="https://immi.homeaffairs.gov.au/..."
                value={costs?.source_link || ''}
                onChange={(e) => updateCosts({ source_link: e.target.value })}
              />
              {costs?.source_link && (
                <a
                  href={costs.source_link}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100"
                  title="Open official fee page"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Line Items List */}
        {lineItems.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 border-dashed border rounded-lg">
            <DollarSign className="h-8 w-8 text-slate-300 mx-auto mb-1" />
            <p className="text-xs font-bold text-slate-600">No government fee line items</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Click "Seed Standard Rates" to auto-populate primary, spouse, and child fees.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {lineItems.map((it, idx) => (
              <div key={idx} className="p-3 bg-slate-50 border rounded-lg space-y-2">
                <div className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-4">
                    <Input
                      disabled={readOnly}
                      className="h-7 text-xs font-bold text-slate-900 bg-white"
                      value={it.applicant_type || ''}
                      onChange={(e) => updateLineItem(idx, { applicant_type: e.target.value })}
                      placeholder="Applicant (e.g. Primary Applicant)"
                    />
                  </div>

                  <div className="col-span-3">
                    <div className="relative flex items-center">
                      <Input
                        type="number"
                        disabled={readOnly}
                        className="h-7 text-xs font-bold text-slate-900 bg-white pr-12"
                        value={it.amount ?? ''}
                        onChange={(e) => updateLineItem(idx, { amount: parseFloat(e.target.value) || 0 })}
                        placeholder="0"
                      />
                      <span className="absolute right-2 text-[10px] font-bold text-slate-400 pointer-events-none">
                        {currency}
                      </span>
                    </div>
                  </div>

                  <div className="col-span-4">
                    <div className="p-1.5 bg-emerald-50/60 border border-emerald-200 rounded text-right flex items-center justify-between">
                      <span className="text-[10px] text-emerald-800 font-semibold">INR Equivalent:</span>
                      <span className="text-xs font-extrabold text-emerald-900">{formatINR(it.inr_approx || 0)}</span>
                    </div>
                  </div>

                  {!readOnly && (
                    <div className="col-span-1 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => removeLineItem(idx)}
                        className="h-7 w-7 p-0 text-rose-500 hover:bg-rose-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </div>

                <div className="pt-1 border-t border-slate-200">
                  <Input
                    disabled={readOnly}
                    className="h-6 text-[11px] bg-white text-slate-600"
                    placeholder="Statutory notes (e.g. Non-refundable department lodgement charge; payable via ImmiAccount)"
                    value={it.notes || ''}
                    onChange={(e) => updateLineItem(idx, { notes: e.target.value })}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Live Total Government Fees Summary */}
        <Card className="p-3 bg-gradient-to-r from-emerald-50 to-blue-50 border border-emerald-200">
          <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-500">Estimated Combined Family Govt Outlay</p>
              <p className="text-sm font-extrabold text-emerald-900">{formatINR(totalPrimarySecondaryINR)}</p>
            </div>
            <div className="text-right">
              <Badge className="bg-emerald-100 text-emerald-800 text-[10px] gap-1">
                <ShieldCheck className="h-3 w-3" />
                Statutory Non-LEAMSS Fee
              </Badge>
              <p className="text-[10px] text-slate-500 mt-0.5">Payable directly to destination government portal.</p>
            </div>
          </div>
        </Card>
      </Card>
    </div>
  );
}
