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
import { Switch } from '@/components/ui/switch';
import {
  Coins, Plus, Trash2, RefreshCw, Loader2, Sparkles, Info, ShieldCheck,
  Package, Star, Check, X, Crown, ChevronDown, ChevronUp,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';
import { API } from '../lib/constants';
import { buildTargets } from '../lib/buildProfile';

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

export default function Step6CostEstimator({ data, setData, saved, editingId, headers, onSaveAssessment }) {
  const [items, setItems] = useState(data.cost_estimator?.items || []);
  const [packages, setPackages] = useState(data.cost_estimator?.service_packages || data.cost_estimator?.packages || []);
  const [notes, setNotes] = useState(data.cost_estimator?.notes || '');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasLoadedDefaults, setHasLoadedDefaults] = useState(
    Boolean(data.cost_estimator?.items?.length),
  );

  // Determine first target country + subclass + assessing body.
  // Use buildTargets() (same logic the save flow uses) since the wizard stores
  // country selection as country_mode/specific_country/visa_subclass, not data.targets.
  // The wizard only stores an explicit subclass for AU — for CA/NZ we fall back to
  // a representative program code so KB cost defaults still auto-load.
  const ctx = useMemo(() => {
    const DEFAULT_SUBCLASS = { AU: '189', CA: 'EE', NZ: 'SMC' };
    const tgt = buildTargets(data)[0] || {};
    const cc = tgt.country || data.occupation_country || '';
    return {
      country_code: cc,
      visa_subclass: tgt.visa_subclass || data.occupation_pathway || DEFAULT_SUBCLASS[cc] || '',
      assessing_body: data.occupation_body || '',
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
      // Only set packages if none set yet (preserve consultant edits on reload)
      if ((r.data.service_packages || []).length) {
        setPackages(prev => (prev.length ? prev : r.data.service_packages));
      }
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
      cost_estimator: {
        items,
        service_packages: packages,
        packages,
        notes,
      },
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, packages, notes]);

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

  // ── Service package helpers ──────────────────────────────────
  const addPackage = () => {
    const defaultInclusions = [
      'Professional Processing Support',
      'Dedicated Case Manager',
      'Documentation Assistance',
    ];
    const newPkg = {
      key: `custom_${Date.now()}`,
      name: 'Custom Service Package',
      show: true,
      professional_fee: 120000,
      professional_fee_label: 'Professional Fee',
      discount: 0,
      gst: 21600,
      total: 141600,
      currency: 'INR',
      protection_level: 'High',
      professional_fee_refund: true,
      govt_fee_refund: false,
      inclusions: defaultInclusions,
      addon: {
        label: 'Optional Partner Skill Assessment',
        amount: 50000,
        currency: 'INR',
        enabled: false,
      },
      highlight: false,
      note: 'Custom package. GST @18% included.',
    };
    setPackages(prev => [...prev, newPkg]);
    toast.success('New package added — customize details below');
  };

  const removePackage = (idx) => {
    setPackages(prev => prev.filter((_, i) => i !== idx));
    toast.info('Package removed');
  };

  const updatePackage = (idx, field, value) => {
    setPackages(prev => prev.map((p, i) => {
      if (i !== idx) return p;
      const next = { ...p, [field]: value };
      // Auto-calculate GST (18%) & Total Payable when fee or discount changes
      if (field === 'professional_fee' || field === 'discount') {
        const fee = parseFloat(field === 'professional_fee' ? value : next.professional_fee) || 0;
        const disc = parseFloat(field === 'discount' ? value : next.discount) || 0;
        const taxable = Math.max(0, fee - disc);
        const gst = Math.round(taxable * 0.18);
        next.gst = gst;
        next.total = taxable + gst;
      } else if (field === 'gst') {
        const fee = parseFloat(next.professional_fee) || 0;
        const disc = parseFloat(next.discount) || 0;
        const gst = parseFloat(value) || 0;
        next.total = Math.max(0, fee - disc + gst);
      }
      return next;
    }));
  };

  const updatePackageAddon = (idx, field, value) => {
    setPackages(prev => prev.map((p, i) => (
      i === idx ? { ...p, addon: { ...(p.addon || {}), [field]: value } } : p
    )));
  };

  const updatePackageInclusions = (idx, inclusions) => {
    setPackages(prev => prev.map((p, i) => (
      i === idx ? { ...p, inclusions } : p
    )));
  };

  const isAU = ctx.country_code === 'AU';

  // Auto-compute totals
  const totals = useMemo(() => {
    const out = {};
    items.forEach(it => {
      const cur = it.currency || 'INR';
      out[cur] = (out[cur] || 0) + (parseFloat(it.amount) || 0);
    });
    return out;
  }, [items]);

  // Persist to backend. If the assessment isn't created yet (Cost Estimator is
  // Step 6, but the assessment is only saved at Step 7), create it first so the
  // cost lines can be attached — then persist the cost estimator.
  const persist = async () => {
    if (items.length === 0 && packages.length === 0) {
      toast.error('Add at least one cost item or package before saving');
      return;
    }
    setSaving(true);
    try {
      let assessmentId = saved?.id || editingId;
      if (!assessmentId && onSaveAssessment) {
        const created = await onSaveAssessment({ advance: false });
        assessmentId = created?.id;
      }
      if (!assessmentId) {
        toast.error('Could not create assessment. Please complete the earlier steps (client name, profile, countries) first.');
        return;
      }
      await axios.post(`${API}/sales/wizard/cost-estimator/save`, {
        assessment_id: assessmentId,
        currency: 'INR',
        items,
        service_packages: packages,
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
            disabled={saving || items.length === 0}
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

      {/* ── LEAMSS Service Packages Section ───────────────── */}
      <div className="space-y-3 pt-3 border-t" data-testid="service-packages-section">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="text-lg font-bold flex items-center gap-2 text-teal-900">
              <Package className="h-5 w-5 text-teal-700" />
              LEAMSS Service Packages
            </h3>
            <p className="text-xs text-slate-600 mt-0.5">
              Editable per client. Toggle <strong>Show in report</strong> to choose which packages appear in the Assessment Report comparison.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              onClick={addPackage}
              className="bg-teal-700 hover:bg-teal-800 text-white text-xs h-8"
              data-testid="add-new-package-btn"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              Add New Package
            </Button>
            <Badge className="bg-teal-100 text-teal-800 text-[10px]">
              {ctx.country_code ? `${ctx.country_code} · 2026` : '2026'}
            </Badge>
          </div>
        </div>

        {packages.length === 0 ? (
          <div className="text-center py-6 text-slate-400 border-2 border-dashed border-teal-200 rounded-lg bg-teal-50/30">
            <Package className="h-8 w-8 mx-auto mb-2 text-teal-400 opacity-60" />
            <p className="text-sm font-medium text-teal-900">No service packages added yet</p>
            <p className="text-xs text-slate-500 mb-3">Add a custom package to present tailored investment options to the client.</p>
            <Button
              type="button"
              size="sm"
              onClick={addPackage}
              className="bg-teal-600 hover:bg-teal-700 text-white text-xs"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              Add New Package
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {packages.map((pkg, idx) => (
              <ServicePackageCard
                key={pkg.key || idx}
                pkg={pkg}
                idx={idx}
                onChange={updatePackage}
                onRemove={removePackage}
                onAddonChange={updatePackageAddon}
                onInclusionsChange={updatePackageInclusions}
              />
            ))}
          </div>
        )}
      </div>

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

const PROTECTION_LEVELS = ['Basic', 'High', 'Maximum'];
const CUR_SYMBOL = { INR: '₹', AUD: '$', CAD: '$', NZD: '$', GBP: '£', USD: '$' };

function ServicePackageCard({ pkg, idx, onChange, onRemove, onAddonChange, onInclusionsChange }) {
  const sym = CUR_SYMBOL[pkg.currency || 'INR'] || '₹';
  const addon = pkg.addon || null;
  const grandTotal = (parseFloat(pkg.total) || 0) + (addon?.enabled ? (parseFloat(addon.amount) || 0) : 0);
  const [showInclusions, setShowInclusions] = useState(false);
  const [newInclusionText, setNewInclusionText] = useState('');

  const handleAddInclusion = () => {
    if (!newInclusionText.trim()) return;
    const updated = [...(pkg.inclusions || []), newInclusionText.trim()];
    onInclusionsChange(idx, updated);
    setNewInclusionText('');
  };

  const handleRemoveInclusion = (incIdx) => {
    const updated = (pkg.inclusions || []).filter((_, i) => i !== incIdx);
    onInclusionsChange(idx, updated);
  };

  return (
    <Card
      className={`p-3 space-y-2.5 transition relative ${
        pkg.highlight
          ? 'border-teal-500 border-2 shadow-md bg-teal-50/20'
          : 'border-slate-200 bg-white hover:border-slate-300'
      } ${pkg.show ? '' : 'opacity-60 bg-slate-50'}`}
      data-testid={`pkg-card-${pkg.key || idx}`}
    >
      {/* Card Header: Package Name + Highlight/Star + Delete */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-1.5">
          <div className="flex items-center gap-1 flex-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => onChange(idx, 'highlight', !pkg.highlight)}
              className={`h-7 w-7 p-0 shrink-0 ${
                pkg.highlight
                  ? 'text-amber-500 hover:text-amber-600'
                  : 'text-slate-300 hover:text-amber-500'
              }`}
              title={pkg.highlight ? 'Recommended package (click to unmark)' : 'Mark as Recommended'}
              data-testid={`pkg-highlight-${pkg.key || idx}`}
            >
              <Star className={`h-4 w-4 ${pkg.highlight ? 'fill-amber-400 text-amber-500' : ''}`} />
            </Button>
            <Input
              value={pkg.name}
              onChange={(e) => onChange(idx, 'name', e.target.value)}
              placeholder="Package Name"
              className="h-7 text-xs font-bold text-teal-950 bg-teal-50/40 border-teal-200/80 focus:bg-white"
              data-testid={`pkg-name-${pkg.key || idx}`}
            />
          </div>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => onRemove(idx)}
            className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50 shrink-0"
            title="Delete this package"
            data-testid={`pkg-remove-${pkg.key || idx}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>

        {pkg.highlight && (
          <div className="flex items-center gap-1 text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded font-semibold">
            <Crown className="h-3 w-3 text-amber-500" />
            <span>Recommended Package Badge</span>
          </div>
        )}
      </div>

      {/* Show in report toggle */}
      <div className="flex items-center justify-between bg-slate-50 border border-slate-100 rounded px-2 py-1">
        <span className="text-[11px] font-medium text-slate-700">Show in report</span>
        <Switch
          checked={!!pkg.show}
          onCheckedChange={(v) => onChange(idx, 'show', v)}
          data-testid={`pkg-show-${pkg.key || idx}`}
        />
      </div>

      {/* Editable amounts */}
      <div className="space-y-1.5">
        <div>
          <div className="flex justify-between items-center mb-0.5">
            <Label className="text-[10px] text-slate-500">{pkg.professional_fee_label || 'Professional Fee'}</Label>
            <span className="text-[10px] text-slate-400">{sym}</span>
          </div>
          <Input
            type="number"
            value={pkg.professional_fee}
            onChange={(e) => onChange(idx, 'professional_fee', parseFloat(e.target.value) || 0)}
            className="h-7 text-xs font-mono"
            data-testid={`pkg-fee-${pkg.key || idx}`}
          />
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <div>
            <Label className="text-[10px] text-slate-500">Discount</Label>
            <Input
              type="number"
              value={pkg.discount}
              onChange={(e) => onChange(idx, 'discount', parseFloat(e.target.value) || 0)}
              className="h-7 text-xs font-mono text-emerald-700"
              data-testid={`pkg-discount-${pkg.key || idx}`}
            />
          </div>
          <div>
            <Label className="text-[10px] text-slate-500">GST (18%)</Label>
            <Input
              type="number"
              value={pkg.gst}
              onChange={(e) => onChange(idx, 'gst', parseFloat(e.target.value) || 0)}
              className="h-7 text-xs font-mono"
              data-testid={`pkg-gst-${pkg.key || idx}`}
            />
          </div>
        </div>
        <div>
          <Label className="text-[10px] text-slate-500 font-semibold">Total Payable (editable)</Label>
          <Input
            type="number"
            value={pkg.total}
            onChange={(e) => onChange(idx, 'total', parseFloat(e.target.value) || 0)}
            className="h-8 text-sm font-bold text-teal-900 font-mono bg-teal-50/50"
            data-testid={`pkg-total-${pkg.key || idx}`}
          />
        </div>
      </div>

      {/* Protection level + refund flags */}
      <div className="space-y-1.5 pt-1 border-t border-slate-100">
        <div>
          <Label className="text-[10px] text-slate-500">Protection Level</Label>
          <select
            value={pkg.protection_level || 'Basic'}
            onChange={(e) => onChange(idx, 'protection_level', e.target.value)}
            className="text-[11px] w-full px-2 py-1 border rounded bg-white h-7 text-slate-800"
            data-testid={`pkg-level-${pkg.key || idx}`}
          >
            {PROTECTION_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </div>
        <label className="flex items-center justify-between text-[11px] text-slate-700 cursor-pointer hover:bg-slate-50 px-1 py-0.5 rounded">
          <span className="flex items-center gap-1">
            {pkg.professional_fee_refund
              ? <Check className="h-3 w-3 text-emerald-600 font-bold" />
              : <X className="h-3 w-3 text-rose-400" />}
            100% Professional Fee refund
          </span>
          <Switch
            checked={!!pkg.professional_fee_refund}
            onCheckedChange={(v) => onChange(idx, 'professional_fee_refund', v)}
            data-testid={`pkg-profrefund-${pkg.key || idx}`}
          />
        </label>
        <label className="flex items-center justify-between text-[11px] text-slate-700 cursor-pointer hover:bg-slate-50 px-1 py-0.5 rounded">
          <span className="flex items-center gap-1">
            {pkg.govt_fee_refund
              ? <Check className="h-3 w-3 text-emerald-600 font-bold" />
              : <X className="h-3 w-3 text-rose-400" />}
            100% Government Fee refund
          </span>
          <Switch
            checked={!!pkg.govt_fee_refund}
            onCheckedChange={(v) => onChange(idx, 'govt_fee_refund', v)}
            data-testid={`pkg-govrefund-${pkg.key || idx}`}
          />
        </label>
      </div>

      {/* Inclusions Toggle & Editor */}
      <div className="pt-1 border-t border-slate-100">
        <button
          type="button"
          onClick={() => setShowInclusions(!showInclusions)}
          className="flex items-center justify-between w-full text-[10px] text-slate-500 font-semibold hover:text-teal-800 transition"
        >
          <span>What's Included ({(pkg.inclusions || []).length})</span>
          {showInclusions ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
        {showInclusions && (
          <div className="mt-1.5 space-y-1.5 bg-slate-50 p-2 rounded border border-slate-200">
            <ul className="space-y-1">
              {(pkg.inclusions || []).map((inc, incIdx) => (
                <li key={incIdx} className="flex items-center justify-between text-[10px] text-slate-700 gap-1 bg-white p-1 rounded border border-slate-100">
                  <span className="truncate">• {inc}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveInclusion(incIdx)}
                    className="text-slate-400 hover:text-rose-500 p-0.5"
                  >
                    <Trash2 className="h-2.5 w-2.5" />
                  </button>
                </li>
              ))}
            </ul>
            <div className="flex gap-1 pt-1">
              <Input
                value={newInclusionText}
                onChange={(e) => setNewInclusionText(e.target.value)}
                placeholder="Add inclusion..."
                className="h-6 text-[10px]"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddInclusion();
                  }
                }}
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleAddInclusion}
                className="h-6 px-2 text-[10px]"
              >
                <Plus className="h-3 w-3" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Optional add-on */}
      {addon && (
        <div className="bg-amber-50 border border-amber-200 rounded p-2 space-y-1.5" data-testid={`pkg-addon-${pkg.key || idx}`}>
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-amber-800">{addon.label || 'Optional Add-on'}</span>
            <Switch
              checked={!!addon.enabled}
              onCheckedChange={(v) => onAddonChange(idx, 'enabled', v)}
              data-testid={`pkg-addon-toggle-${pkg.key || idx}`}
            />
          </div>
          {addon.enabled && (
            <Input
              type="number"
              value={addon.amount}
              onChange={(e) => onAddonChange(idx, 'amount', parseFloat(e.target.value) || 0)}
              className="h-7 text-xs font-mono"
              data-testid={`pkg-addon-amount-${pkg.key || idx}`}
            />
          )}
        </div>
      )}

      {/* Grand total footer */}
      <div className="pt-1.5 border-t border-slate-200 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold">
          {addon?.enabled ? 'Total + Add-on' : 'Total Payable'}
        </span>
        <span className="text-base font-bold text-teal-900 font-mono">
          {sym}{grandTotal.toLocaleString()}
        </span>
      </div>
    </Card>
  );
}
