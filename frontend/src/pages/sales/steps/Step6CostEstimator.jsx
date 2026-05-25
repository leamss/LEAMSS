/**
 * Phase 7.2 — Step 6: Cost Estimator (NEW wizard step)
 *
 * Sir's complaint: "Fees mein amounts nahi hain" in Assessment Report.
 *
 * UX:
 *   - On open, pulls KB defaults from /api/sales/wizard/cost-estimator/defaults
 *   - Each item editable inline (label, amount, currency, notes)
 *   - + Add Item / Trash any row
 *   - Auto-computes totals per currency
 *   - Saves to sales_assessments.cost_estimator on Next click
 *   - Renders into Assessment Report PDF (Phase 7.3 wires the rest)
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Coins, Plus, Trash2, RefreshCw, Loader2, Sparkles, Info, ShieldCheck,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';
import { API } from '../lib/constants';

const CATEGORY_PILL = {
  'Government Fees': 'bg-blue-100 text-blue-800',
  'Skill Assessment': 'bg-indigo-100 text-indigo-800',
  'English Test': 'bg-violet-100 text-violet-800',
  'LEAMSS Professional Fees': 'bg-amber-100 text-amber-800',
  'Protection Policy Coverage': 'bg-emerald-100 text-emerald-800',
  'Other': 'bg-slate-100 text-slate-700',
};

const CATEGORY_OPTIONS = [
  'Government Fees', 'Skill Assessment', 'English Test',
  'Medical Tests', 'Police Clearance', 'Translation',
  'LEAMSS Professional Fees', 'Protection Policy Coverage', 'Other',
];

export default function Step6CostEstimator({ data, setData, saved, headers }) {
  const [items, setItems] = useState(data.cost_estimator?.items || []);
  const [notes, setNotes] = useState(data.cost_estimator?.notes || '');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasLoadedDefaults, setHasLoadedDefaults] = useState(
    Boolean(data.cost_estimator?.items?.length),
  );

  // Determine first target country + subclass + assessing body
  const ctx = useMemo(() => {
    const tgt = (data.targets || [])[0] || {};
    const occ = data.occupation || {};
    return {
      country_code: tgt.country || occ.country_code,
      visa_subclass: tgt.visa_subclass || occ.pathway,
      assessing_body: occ.assessing_body,
    };
  }, [data]);

  const loadDefaults = useCallback(async () => {
    if (!ctx.country_code || !ctx.visa_subclass) {
      toast.error('Country + visa subclass selection required before loading cost defaults');
      return;
    }
    setLoading(true);
    try {
      const r = await axios.get(`${API}/sales/wizard/cost-estimator/defaults`, {
        headers,
        params: ctx,
      });
      setItems(r.data.items || []);
      setHasLoadedDefaults(true);
      toast.success('KB defaults loaded — edit as needed');
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load defaults'));
    } finally { setLoading(false); }
  }, [headers, ctx]);

  // Auto-load on first visit
  useEffect(() => {
    if (!hasLoadedDefaults && ctx.country_code && ctx.visa_subclass) {
      loadDefaults();
    }
  }, [hasLoadedDefaults, ctx, loadDefaults]);

  // Sync to parent data so review step + save flows can read it
  useEffect(() => {
    setData(prev => ({
      ...prev,
      cost_estimator: { items, notes },
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, notes]);

  const updateItem = (idx, field, value) => {
    setItems(prev => prev.map((it, i) => (i === idx ? { ...it, [field]: value } : it)));
  };

  const removeItem = (idx) => {
    setItems(prev => prev.filter((_, i) => i !== idx));
  };

  const addItem = () => {
    setItems(prev => [...prev, {
      category: 'Other', label: '', amount: 0,
      currency: 'INR', is_estimated: true, is_editable: true,
    }]);
  };

  // Auto-compute totals
  const totals = useMemo(() => {
    const out = {};
    items.forEach(it => {
      const cur = it.currency || 'INR';
      out[cur] = (out[cur] || 0) + (parseFloat(it.amount) || 0);
    });
    return out;
  }, [items]);

  // Persist to backend when saved exists
  const persist = async () => {
    if (!saved?.id) return;
    setSaving(true);
    try {
      await axios.post(`${API}/sales/wizard/cost-estimator/save`, {
        assessment_id: saved.id,
        currency: 'INR',
        items,
        notes,
      }, { headers });
      toast.success('Cost estimator saved to assessment');
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  return (
    <Card className="p-5 space-y-4" data-testid="step6-cost-estimator">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2 text-indigo-900">
            <Coins className="h-6 w-6 text-amber-600" />
            Step 6 — Cost Estimator
            <Badge className="bg-indigo-100 text-indigo-700 text-[9px]">Phase 7.2</Badge>
          </h2>
          <p className="text-xs text-slate-600 mt-1">
            KB-driven default fees and costs. Edit each line per client, save to attach to Assessment Report.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={loadDefaults}
            disabled={loading}
            data-testid="reload-defaults-btn"
          >
            {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCw className="h-3 w-3 mr-1" />}
            Reload KB Defaults
          </Button>
          <Button
            size="sm"
            onClick={persist}
            disabled={!saved?.id || saving}
            className="bg-indigo-600 hover:bg-indigo-700"
            data-testid="save-cost-btn"
          >
            {saving ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Sparkles className="h-3 w-3 mr-1" />}
            Save to Assessment
          </Button>
        </div>
      </div>

      <div className="bg-amber-50 border-l-4 border-l-amber-400 p-3 rounded text-xs" data-testid="ctx-info">
        <Info className="h-3.5 w-3.5 inline mr-1 text-amber-700" />
        <strong>Quote context:</strong> {ctx.country_code || '—'} / subclass {ctx.visa_subclass || '—'} {ctx.assessing_body ? `/ ${ctx.assessing_body}` : ''}
      </div>

      {/* Items table */}
      <div className="space-y-2" data-testid="cost-items-list">
        {items.length === 0 && !loading && (
          <div className="text-center py-8 text-slate-400 border-2 border-dashed rounded">
            <Coins className="h-8 w-8 mx-auto mb-2 opacity-30" />
            <p className="text-sm">No cost items yet — click "Reload KB Defaults" or "+ Add Item"</p>
          </div>
        )}
        {loading && (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />Loading KB defaults…
          </div>
        )}
        {items.map((it, idx) => (
          <div
            key={idx}
            className="grid grid-cols-12 gap-2 items-start p-2 border rounded bg-white hover:shadow-sm transition"
            data-testid={`cost-item-${idx}`}
          >
            <div className="col-span-2">
              <select
                value={it.category}
                onChange={(e) => updateItem(idx, 'category', e.target.value)}
                className="text-[11px] w-full px-2 py-1.5 border rounded bg-white"
                data-testid={`cost-category-${idx}`}
              >
                {CATEGORY_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
              <Badge className={`mt-1 text-[9px] ${CATEGORY_PILL[it.category] || 'bg-slate-100'}`}>
                {it.category}
              </Badge>
            </div>
            <div className="col-span-5">
              <Input
                value={it.label}
                onChange={(e) => updateItem(idx, 'label', e.target.value)}
                placeholder="Item label (e.g., ACS Skill Assessment)"
                className="h-8 text-xs"
                data-testid={`cost-label-${idx}`}
              />
              {it.notes && (
                <p className="text-[10px] text-slate-400 italic mt-1">{it.notes}</p>
              )}
              {it.kb_source && (
                <p className="text-[9px] text-indigo-600 font-mono mt-0.5">↗ {it.kb_source}</p>
              )}
            </div>
            <div className="col-span-2">
              <Input
                type="number"
                value={it.amount}
                onChange={(e) => updateItem(idx, 'amount', parseFloat(e.target.value) || 0)}
                className="h-8 text-xs"
                data-testid={`cost-amount-${idx}`}
              />
            </div>
            <div className="col-span-2">
              <select
                value={it.currency}
                onChange={(e) => updateItem(idx, 'currency', e.target.value)}
                className="text-xs w-full px-2 py-1.5 border rounded bg-white h-8"
                data-testid={`cost-currency-${idx}`}
              >
                <option value="INR">INR ₹</option>
                <option value="AUD">AUD $</option>
                <option value="CAD">CAD $</option>
                <option value="NZD">NZD $</option>
                <option value="GBP">GBP £</option>
                <option value="USD">USD $</option>
              </select>
            </div>
            <div className="col-span-1 text-right">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeItem(idx)}
                className="text-rose-500 hover:bg-rose-50 h-8 px-2"
                data-testid={`cost-remove-${idx}`}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={addItem}
          className="w-full border-dashed text-xs"
          data-testid="add-cost-item-btn"
        >
          <Plus className="h-3 w-3 mr-1" />Add Custom Item
        </Button>
      </div>

      {/* Totals */}
      {items.length > 0 && (
        <Card className="p-3 bg-gradient-to-r from-indigo-50 to-blue-50 border-indigo-200" data-testid="cost-totals">
          <p className="text-[10px] uppercase font-bold tracking-wider text-indigo-700 mb-2">Total Investment</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(totals).map(([cur, amt]) => (
              <div key={cur}>
                <p className="text-[10px] text-slate-500">{cur}</p>
                <p className="text-lg font-bold text-indigo-900 font-mono">
                  {cur === 'INR' ? '₹' : cur === 'GBP' ? '£' : '$'}{amt.toLocaleString()}
                </p>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-2 text-[10px] text-emerald-700">
            <ShieldCheck className="h-3 w-3" />
            <span><strong>LEAMSS Protection Policy</strong> covers professional + government fees on negative outcomes</span>
          </div>
        </Card>
      )}

      {/* Notes */}
      <div>
        <Label className="text-xs">Notes / Validity</Label>
        <Textarea
          rows={2}
          placeholder="E.g., Quoted on 25-May-2026, valid for 30 days. Government fees subject to revision by visa authority."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="text-xs"
          data-testid="cost-notes-input"
        />
      </div>
    </Card>
  );
}
