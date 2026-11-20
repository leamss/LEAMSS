import React, { useMemo } from 'react';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DollarSign,
  Package,
  Layers,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  FileCheck,
  Percent,
} from 'lucide-react';
import RefundPolicySection from './RefundPolicySection';
import PackageRefundPolicyEditor from './PackageRefundPolicyEditor';

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const VENDOR_CATS = [
  { key: 'internal_partner', label: 'Internal Salesperson (Employee)', internal: true },
  { key: 'external_partner', label: 'External Salesperson / Partner' },
  { key: 'case_manager',     label: 'Case Manager Fee',      internal: true },
  { key: 'sales_commission', label: 'Sales Commission',      internal: true },
  { key: 'tutor',            label: 'Tutor (IELTS/PTE)' },
  { key: 'lawyer',           label: 'Legal Counsel / Lawyer' },
  { key: 'translator',       label: 'NAATI / Document Translator' },
  { key: 'consultant',       label: 'Consultant' },
  { key: 'medical_examiner', label: 'Medical Examiner' },
  { key: 'courier',          label: 'Courier' },
  { key: 'other',            label: 'Other Cost' },
];

const PKG_TYPES = [
  { key: 'standard', label: 'Standard Package' },
  { key: 'smart',    label: 'Smart Package' },
  { key: 'premium',  label: 'Premium Package' },
  { key: 'custom',   label: 'Custom Package' },
];

export default function LEAMSSPricingTab({
  product,
  onChange,
  onSaved,
  readOnly = false,
}) {
  const baseFee = parseFloat(product?.service_price || product?.base_fee || 0);

  const gstApplicable = product?.gst_applicable !== undefined
    ? Boolean(product?.gst_applicable)
    : (product?.commercials?.gst_applicable !== undefined
        ? Boolean(product?.commercials?.gst_applicable)
        : true);

  const gstAmount = gstApplicable ? Math.round(baseFee * 0.18) : 0;
  const totalWithGst = baseFee + gstAmount;

  const packageGstApplicable = product?.package_gst_applicable !== undefined
    ? Boolean(product?.package_gst_applicable)
    : false;

  const rawPackages = product?.packages || [
    { package_type: 'standard', name: 'Standard Package', price: baseFee || 150000, description: 'Core visa application guidance & assessment filing', is_active: true, gst_applicable: packageGstApplicable },
    { package_type: 'smart', name: 'Smart Package', price: (baseFee || 150000) * 1.25, description: 'Includes documentation prep, priority reviews & exam support', is_active: true, gst_applicable: packageGstApplicable },
    { package_type: 'premium', name: 'Premium Package', price: (baseFee || 150000) * 1.5, description: 'Full concierge, dedicated senior case manager & resume rebuild', is_active: true, gst_applicable: packageGstApplicable },
  ];

  const packages = rawPackages.map((p) => ({
    ...p,
    gst_applicable: p.gst_applicable !== undefined ? Boolean(p.gst_applicable) : packageGstApplicable,
  }));

  const milestones = product?.commercials?.milestones || [
    { milestone_order: 1, name: 'Milestone 1: Retainer & Case Onboarding', percentage: 40, amount: Math.round(baseFee * 0.4), trigger: 'Signing engagement agreement' },
    { milestone_order: 2, name: 'Milestone 2: Skills Assessment Filing', percentage: 30, amount: Math.round(baseFee * 0.3), trigger: 'Dossier ready & assessment lodged' },
    { milestone_order: 3, name: 'Milestone 3: State EOI / Visa Lodgement', percentage: 30, amount: Math.round(baseFee * 0.3), trigger: 'Invitation received & final lodgement' },
  ];

  const refundTerms = product?.refund_options || [
    { rule: 'Withdrawal prior to skills assessment filing: 50% refund less ₹25,000 administrative costs.' },
    { rule: 'Withdrawal post skills assessment filing: Nil refund on Stage 1; Stage 2 & 3 not charged.' },
    { rule: 'Government statutory rejections due to department quota changes: 50% service fee credit towards alternate visa pathway.' },
  ];

  const allocations = useMemo(() => product?.cost_allocations || [], [product?.cost_allocations]);

  const totalCommissions = useMemo(() => {
    return allocations.reduce((acc, a) => {
      if (a.is_optional) return acc;
      const rateVal = parseFloat(a.rate !== undefined && a.rate !== null && a.rate !== '' ? a.rate : a.amount) || 0;
      if (a.payment_type === 'percentage') return acc + (baseFee * rateVal / 100);
      return acc + (parseFloat(a.amount !== undefined && a.amount !== null && a.amount !== '' ? a.amount : a.rate) || 0);
    }, 0);
  }, [allocations, baseFee]);

  const netMargin = baseFee - totalCommissions;
  const marginPct = baseFee > 0 ? ((netMargin / baseFee) * 100).toFixed(1) : 0;

  // Handlers
  const handleFeeChange = (val) => {
    const num = parseFloat(val) || 0;
    onChange({
      service_price: num,
      base_fee: num,
    });
  };

  const updatePackages = (pkgs) => {
    onChange({ packages: pkgs });
  };

  const addPackage = () => {
    const nextPkg = {
      id: crypto.randomUUID(),
      package_type: 'standard',
      name: `Package ${packages.length + 1}`,
      price: baseFee || 150000,
      description: '',
      is_active: true,
      gst_applicable: packageGstApplicable,
    };
    updatePackages([...packages, nextPkg]);
    toast.success('Added new package');
  };

  const updatePackage = (idx, field, value) => {
    const next = [...packages];
    next[idx] = {
      ...next[idx],
      [field]: value,
    };
    updatePackages(next);
  };

  const removePackage = (idx) => {
    const next = packages.filter((_, i) => i !== idx);
    updatePackages(next);
    toast.success('Removed package');
  };

  const updateMilestones = (ms) => {
    onChange({
      commercials: {
        ...(product?.commercials || {}),
        milestones: ms,
      },
    });
  };

  const addMilestone = () => {
    const nextOrder = milestones.length + 1;
    updateMilestones([
      ...milestones,
      {
        milestone_order: nextOrder,
        name: `Milestone ${nextOrder}: New Payment Stage`,
        percentage: 20,
        amount: Math.round(baseFee * 0.2),
        trigger: 'Upon stage completion',
      },
    ]);
  };

  const removeMilestone = (idx) => {
    updateMilestones(milestones.filter((_, i) => i !== idx).map((m, i) => ({ ...m, milestone_order: i + 1 })));
  };

  const updateAllocations = (allocs) => {
    onChange({ cost_allocations: allocs });
  };

  const addRoleAllocation = (catKey, defaultLabel, defaultType = 'percentage', defaultVal = 5) => {
    const existing = allocations.find((a) => a.vendor_category === catKey);
    if (existing) {
      toast.info(`${defaultLabel} is already in the allocations list.`);
      return;
    }
    updateAllocations([
      ...allocations,
      {
        id: crypto.randomUUID(),
        vendor_category: catKey,
        label: defaultLabel,
        payment_type: defaultType,
        amount: defaultType === 'flat' ? defaultVal : 0,
        rate: defaultType === 'percentage' ? defaultVal : 0,
        is_optional: false,
      },
    ]);
    toast.success(`Added ${defaultLabel}`);
  };

  const addCustomAllocation = () => {
    updateAllocations([
      ...allocations,
      {
        id: crypto.randomUUID(),
        vendor_category: 'other',
        label: 'New Allocation',
        payment_type: 'flat',
        amount: 0,
        rate: 0,
        is_optional: false,
      },
    ]);
    toast.success('Added new commission allocation');
  };

  return (
    <div className="space-y-4 text-xs">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. BASE SERVICE FEE & GST SCHEDULE (ADMIN TOGGLEABLE)          */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">LEAMSS Professional Retainer Package & Tax Schedule</h3>
          </div>
          <div className="flex items-center gap-2">
            {!readOnly && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  const nextVal = !gstApplicable;
                  onChange({
                    gst_applicable: nextVal,
                    commercials: {
                      ...(product?.commercials || {}),
                      gst_applicable: nextVal,
                    },
                  });
                  toast.success(nextVal ? 'Retainer 18% GST Enabled' : 'Retainer GST Disabled (0%)');
                }}
                className={`text-xs h-7 gap-1.5 font-bold transition-all ${
                  gstApplicable
                    ? 'border-emerald-400 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 shadow-2xs'
                    : 'border-slate-300 bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
                data-testid="toggle-retainer-gst-btn"
              >
                <Percent className={`h-3.5 w-3.5 ${gstApplicable ? 'text-emerald-600' : 'text-slate-400'}`} />
                {gstApplicable ? '18% Statutory GST: Applied' : 'Retainer GST: Disabled (0%)'}
              </Button>
            )}
            <Badge className={gstApplicable ? "bg-emerald-100 text-emerald-800 text-[10px]" : "bg-slate-100 text-slate-600 text-[10px]"}>
              {gstApplicable ? "18% Statutory GST" : "GST Exempt / 0%"}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          <div>
            <Label className="text-xs font-bold text-slate-800">Base Professional Retainer Fee (₹ INR)</Label>
            <Input
              type="number"
              disabled={readOnly}
              value={baseFee || ''}
              onChange={(e) => handleFeeChange(e.target.value)}
              className="mt-1 h-9 text-base font-extrabold text-slate-900"
              placeholder="e.g. 150000"
              data-testid="base-service-fee"
            />
            <p className="text-[10px] text-slate-400 mt-1">Excludes official government visa & assessment filing levies.</p>
          </div>

          <div className={`p-3 border rounded-lg ${gstApplicable ? 'bg-slate-50 border-slate-200' : 'bg-slate-50/50 border-dashed border-slate-200'}`}>
            <span className="text-[10px] text-slate-500 uppercase font-bold">
              {gstApplicable ? '18% Statutory GST (CGST 9% + SGST 9%)' : 'Statutory GST (Not Selected)'}
            </span>
            <p className="text-sm font-bold text-slate-700 mt-0.5">
              {gstApplicable ? formatINR(gstAmount) : '₹0 (Not Applicable)'}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              {gstApplicable ? 'Calculated automatically on invoice issuance.' : 'No GST will be added on invoices or sales pitches.'}
            </p>
          </div>

          <div className={`p-3 rounded-lg border ${gstApplicable ? 'bg-emerald-50/70 border-emerald-200' : 'bg-slate-100/70 border-slate-300'}`}>
            <span className={`text-[10px] uppercase font-bold ${gstApplicable ? 'text-emerald-800' : 'text-slate-700'}`}>
              {gstApplicable ? 'Total Client Payable (Incl. 18% GST)' : 'Total Client Payable (Net Retainer)'}
            </span>
            <p className={`text-lg font-black mt-0.5 ${gstApplicable ? 'text-emerald-800' : 'text-slate-900'}`}>
              {formatINR(totalWithGst)}
            </p>
            <p className={`text-[10px] mt-0.5 ${gstApplicable ? 'text-emerald-600' : 'text-slate-500'}`}>
              {gstApplicable ? 'Final contract value presented on client agreement.' : 'Net retainer contract value without GST levies.'}
            </p>
          </div>
        </div>
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. TRANCHE / MILESTONE PAYMENT SCHEDULE                      */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b">
          <div>
            <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
              <FileCheck className="h-4 w-4 text-blue-600" />
              Retainer Milestone Payment Schedule (Tranches)
            </h3>
            <p className="text-[11px] text-slate-500 mt-0.5">Client milestone installments linked to operational immigration delivery stages.</p>
          </div>
          {!readOnly && (
            <Button size="sm" variant="outline" onClick={addMilestone} className="text-xs h-7 border-slate-300 gap-1" data-testid="add-milestone">
              <Plus className="h-3.5 w-3.5" />
              Add Milestone
            </Button>
          )}
        </div>

        <div className="space-y-2">
          {milestones.map((m, idx) => (
            <div key={idx} className="p-3 border rounded-lg bg-slate-50/50 space-y-2 hover:border-slate-300 transition-colors">
              <div className="flex items-center justify-between gap-2">
                <Input
                  disabled={readOnly}
                  className="h-7 text-xs font-bold text-slate-800 bg-white"
                  value={m.name || ''}
                  onChange={(e) => {
                    const next = [...milestones];
                    next[idx].name = e.target.value;
                    updateMilestones(next);
                  }}
                  placeholder="Milestone Title"
                />
                <div className="flex items-center gap-1 shrink-0">
                  <Input
                    type="number"
                    disabled={readOnly}
                    className="w-16 h-7 text-xs font-bold text-center bg-white"
                    value={m.percentage || 0}
                    onChange={(e) => {
                      const next = [...milestones];
                      const pct = parseFloat(e.target.value) || 0;
                      next[idx].percentage = pct;
                      next[idx].amount = Math.round(baseFee * (pct / 100));
                      updateMilestones(next);
                    }}
                  />
                  <span className="text-xs font-bold text-slate-500">%</span>
                  {!readOnly && milestones.length > 1 && (
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-rose-500 hover:bg-rose-50" onClick={() => removeMilestone(idx)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>

              <div>
                <Input
                  disabled={readOnly}
                  className="h-7 text-xs bg-white text-slate-600"
                  value={m.trigger || ''}
                  onChange={(e) => {
                    const next = [...milestones];
                    next[idx].trigger = e.target.value;
                    updateMilestones(next);
                  }}
                  placeholder="Invoicing / Delivery Trigger Condition (e.g. Dossier lodged, Invitation received)"
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-200">
                <span>Tranche Amount: <strong className="text-emerald-700">{formatINR(m.amount || Math.round(baseFee * ((m.percentage || 0) / 100)))}</strong></span>
                <span className={gstApplicable ? "text-slate-400" : "text-slate-400 italic"}>
                  {gstApplicable
                    ? `+ 18% GST (${formatINR(Math.round((m.amount || 0) * 0.18))})`
                    : 'No GST Applied (0%)'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 3. CLIENT PORTAL PACKAGE TIERS & PAYMENT OPTIONS              */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Package className="h-4 w-4 text-purple-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">
              Client Portal Package Tiers (Standard / Smart / Premium)
            </h3>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {!readOnly && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  const nextVal = !packageGstApplicable;
                  const updatedPkgs = packages.map((p) => ({ ...p, gst_applicable: nextVal }));
                  onChange({
                    package_gst_applicable: nextVal,
                    packages: updatedPkgs,
                  });
                  toast.success(nextVal ? 'Package Tiers 18% GST Enabled' : 'Package Tiers GST Disabled (0%)');
                }}
                className={`text-xs h-7 gap-1.5 font-bold transition-all ${
                  packageGstApplicable
                    ? 'border-purple-400 bg-purple-50 text-purple-800 hover:bg-purple-100 shadow-2xs'
                    : 'border-slate-300 bg-slate-50 text-slate-600 hover:bg-slate-100'
                }`}
                data-testid="toggle-package-gst-btn"
              >
                <Percent className={`h-3.5 w-3.5 ${packageGstApplicable ? 'text-purple-600' : 'text-slate-400'}`} />
                {packageGstApplicable ? 'Package GST: 18% ON' : 'Package GST: OFF (0%)'}
              </Button>
            )}
            {!readOnly && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={addPackage}
                className="text-xs h-7 border-purple-300 bg-purple-50 text-purple-800 hover:bg-purple-100 font-semibold gap-1"
                data-testid="add-package-btn"
              >
                <Plus className="h-3.5 w-3.5 text-purple-600" />
                Add Package
              </Button>
            )}
            <Badge variant="outline" className={packageGstApplicable ? "text-[10px] text-purple-700 border-purple-200 bg-purple-50" : "text-[10px] text-slate-600"}>
              {packageGstApplicable ? "+18% GST Applied" : "GST Not Selected (0%)"}
            </Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {packages.map((pkg, idx) => {
            const isPkgGst = pkg.gst_applicable !== undefined ? Boolean(pkg.gst_applicable) : packageGstApplicable;
            const pPrice = parseFloat(pkg.price) || 0;
            const pGst = isPkgGst ? Math.round(pPrice * 0.18) : 0;
            const pTotal = pPrice + pGst;

            return (
              <Card key={pkg.id || idx} className="p-3 border space-y-2 bg-slate-50/60 rounded-xl hover:border-purple-300 transition-colors">
                <div className="flex items-center justify-between gap-1">
                  <select
                    disabled={readOnly}
                    value={pkg.package_type || 'standard'}
                    onChange={(e) => updatePackage(idx, 'package_type', e.target.value)}
                    className="h-6 rounded border border-slate-300 bg-white px-1.5 text-[11px] font-bold text-slate-800"
                  >
                    {PKG_TYPES.map((t) => (
                      <option key={t.key} value={t.key}>
                        {t.label}
                      </option>
                    ))}
                  </select>

                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-1 text-[10px] text-purple-700 font-bold cursor-pointer" title="Toggle 18% GST for this package">
                      <input
                        type="checkbox"
                        disabled={readOnly}
                        checked={isPkgGst}
                        onChange={(e) => updatePackage(idx, 'gst_applicable', e.target.checked)}
                        className="h-3.5 w-3.5 rounded text-purple-600"
                        data-testid={`pkg-gst-check-${idx}`}
                      />
                      18% GST
                    </label>

                    <label className="flex items-center gap-1 text-[10px] text-slate-600 font-semibold cursor-pointer">
                      <input
                        type="checkbox"
                        disabled={readOnly}
                        checked={pkg.is_active !== false}
                        onChange={(e) => updatePackage(idx, 'is_active', e.target.checked)}
                        className="h-3.5 w-3.5 rounded text-purple-600"
                      />
                      Active
                    </label>
                    {!readOnly && packages.length > 1 && (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-rose-500 hover:bg-rose-50"
                        onClick={() => removePackage(idx)}
                        data-testid={`pkg-del-${idx}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500 font-bold">Display Name</Label>
                  <Input
                    disabled={readOnly}
                    className="h-7 text-xs font-bold text-slate-900 mt-0.5 bg-white"
                    value={pkg.name || ''}
                    onChange={(e) => updatePackage(idx, 'name', e.target.value)}
                    placeholder="Package Name"
                  />
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500 font-bold">Package Price (₹)</Label>
                  <Input
                    type="number"
                    disabled={readOnly}
                    className="h-7 text-xs font-bold text-purple-700 mt-0.5 bg-white"
                    value={pkg.price || ''}
                    onChange={(e) => updatePackage(idx, 'price', parseFloat(e.target.value) || 0)}
                  />
                </div>

                {/* GST & Total Client Payable Breakdown */}
                <div className={`p-2 rounded border text-[11px] space-y-0.5 ${isPkgGst ? 'bg-purple-50/50 border-purple-200' : 'bg-white border-slate-200'}`}>
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Base Investment:</span>
                    <span className="font-semibold">{formatINR(pPrice)}</span>
                  </div>
                  {isPkgGst ? (
                    <>
                      <div className="flex justify-between items-center text-purple-700">
                        <span>+ 18% Statutory GST:</span>
                        <span className="font-semibold">{formatINR(pGst)}</span>
                      </div>
                      <div className="flex justify-between items-center pt-1 border-t border-purple-200 font-bold text-purple-950">
                        <span>Total Payable:</span>
                        <span className="text-emerald-700">{formatINR(pTotal)}</span>
                      </div>
                    </>
                  ) : (
                    <div className="flex justify-between items-center pt-1 border-t border-slate-200 font-bold text-slate-800">
                      <span>Total (No GST):</span>
                      <span className="text-emerald-700">{formatINR(pPrice)}</span>
                    </div>
                  )}
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500 font-bold">Included Scope & Deliverables</Label>
                  <Textarea
                    rows={2}
                    disabled={readOnly}
                    className="text-xs mt-0.5 bg-white"
                    value={pkg.description || ''}
                    onChange={(e) => updatePackage(idx, 'description', e.target.value)}
                    placeholder="Key package inclusions..."
                  />
                </div>

                {/* Package-level Refund Policy */}
                <PackageRefundPolicyEditor
                  packagePrice={pkg.price}
                  refundPolicy={pkg.refund_policy}
                  onChange={(updatedPolicy) => updatePackage(idx, 'refund_policy', updatedPolicy)}
                  readOnly={readOnly}
                />
              </Card>
            );
          })}
        </div>
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 4. COMMISSIONS & COST ALLOCATIONS WITH LIVE MARGIN            */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b">
          <div>
            <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-600" />
              Commissions, Partner Splits & Margin Economics
            </h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Configure internal salesperson commission, partner splits, case manager, and other custom allocations.
            </p>
          </div>

          {!readOnly && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => addRoleAllocation('internal_partner', 'Internal Salesperson', 'percentage', 5)}
                className="text-[11px] h-7 border-emerald-200 text-emerald-700 hover:bg-emerald-50 font-medium"
                data-testid="add-internal-salesperson"
              >
                <Plus className="h-3 w-3 mr-0.5 text-emerald-600" />
                Internal Salesperson
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => addRoleAllocation('external_partner', 'External Partner', 'percentage', 10)}
                className="text-[11px] h-7 border-purple-200 text-purple-700 hover:bg-purple-50 font-medium"
                data-testid="add-external-partner"
              >
                <Plus className="h-3 w-3 mr-0.5 text-purple-600" />
                External Partner
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => addRoleAllocation('case_manager', 'Case Manager Fee', 'flat', 5000)}
                className="text-[11px] h-7 border-blue-200 text-blue-700 hover:bg-blue-50 font-medium"
                data-testid="add-case-manager"
              >
                <Plus className="h-3 w-3 mr-0.5 text-blue-600" />
                Case Manager
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={addCustomAllocation}
                className="text-[11px] h-7 border-slate-300 text-slate-700 hover:bg-slate-100 font-semibold"
                data-testid="add-custom-allocation"
              >
                <Plus className="h-3 w-3 mr-0.5" />
                Custom
              </Button>
            </div>
          )}
        </div>

        {allocations.length === 0 ? (
          <div className="p-6 text-center bg-slate-50 border-dashed border rounded-lg">
            <Layers className="h-7 w-7 text-slate-300 mx-auto mb-1" />
            <p className="text-xs font-semibold text-slate-600">No commission or cost allocations defined</p>
            <p className="text-[10px] text-slate-400 mt-0.5">Use quick buttons above to assign salesperson or partner splits.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {allocations.map((a, i) => {
              const currentVal =
                a.payment_type === 'percentage'
                  ? a.rate !== undefined && a.rate !== null
                    ? a.rate
                    : a.amount !== undefined
                    ? a.amount
                    : ''
                  : a.amount !== undefined && a.amount !== null
                  ? a.amount
                  : a.rate !== undefined
                  ? a.rate
                  : '';
              const estCalc =
                a.payment_type === 'percentage' && baseFee > 0 ? (baseFee * (parseFloat(currentVal) || 0)) / 100 : null;

              return (
                <Card key={a.id || i} className="p-3 border-l-4 border-slate-300 hover:border-emerald-500 transition-colors">
                  <div className="grid grid-cols-12 gap-2 items-center">
                    <div className="col-span-4">
                      <Input
                        disabled={readOnly}
                        className="h-8 text-xs font-medium bg-white"
                        value={a.label || ''}
                        onChange={(e) => {
                          const next = [...allocations];
                          next[i].label = e.target.value;
                          updateAllocations(next);
                        }}
                        placeholder="Label / Beneficiary"
                      />
                    </div>

                    <div className="col-span-3">
                      <select
                        disabled={readOnly}
                        value={a.vendor_category || 'internal_partner'}
                        onChange={(e) => {
                          const next = [...allocations];
                          next[i].vendor_category = e.target.value;
                          updateAllocations(next);
                        }}
                        className="h-8 w-full rounded border border-input bg-white px-2 text-xs font-semibold"
                      >
                        {VENDOR_CATS.map((c) => (
                          <option key={c.key} value={c.key}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="col-span-2">
                      <select
                        disabled={readOnly}
                        value={a.payment_type || 'flat'}
                        onChange={(e) => {
                          const next = [...allocations];
                          next[i].payment_type = e.target.value;
                          updateAllocations(next);
                        }}
                        className="h-8 w-full rounded border border-input bg-white px-2 text-xs font-semibold"
                      >
                        <option value="flat">Flat ₹</option>
                        <option value="percentage">% of Price</option>
                      </select>
                    </div>

                    <div className="col-span-2 relative flex items-center">
                      <Input
                        type="number"
                        disabled={readOnly}
                        className="h-8 text-xs font-bold bg-white"
                        value={currentVal}
                        onChange={(e) => {
                          const next = [...allocations];
                          if (a.payment_type === 'percentage') {
                            next[i].rate = e.target.value;
                          } else {
                            next[i].amount = e.target.value;
                          }
                          updateAllocations(next);
                        }}
                        placeholder="Val"
                      />
                      {a.payment_type === 'percentage' && (
                        <span className="absolute right-2 text-xs font-bold text-slate-400 pointer-events-none">%</span>
                      )}
                    </div>

                    <div className="col-span-1 flex items-center justify-between gap-1">
                      <label className="flex items-center gap-1 text-[10px] text-slate-600 font-semibold cursor-pointer">
                        <input
                          type="checkbox"
                          disabled={readOnly}
                          checked={!!a.is_optional}
                          onChange={(e) => {
                            const next = [...allocations];
                            next[i].is_optional = e.target.checked;
                            updateAllocations(next);
                          }}
                          className="h-3.5 w-3.5 rounded"
                        />
                        Opt
                      </label>
                      {!readOnly && (
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="text-rose-500 hover:bg-rose-50 h-8 p-0 w-7"
                          onClick={() => updateAllocations(allocations.filter((_, idx) => idx !== i))}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>
                  {estCalc !== null && (
                    <p className="text-[10px] text-slate-500 mt-1 text-right font-medium">
                      {currentVal}% of {formatINR(baseFee)} = <strong className="text-emerald-700">{formatINR(estCalc)}</strong>
                    </p>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Live Economics Margin Summary Card */}
        <Card className="p-3 bg-gradient-to-br from-slate-50 to-emerald-50/40 border border-slate-200 mt-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400">Base Retainer Fee</p>
              <p className="text-sm font-extrabold text-slate-900">{formatINR(baseFee)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400">Total Commissions & Splits</p>
              <p className="text-sm font-extrabold text-rose-700">{formatINR(totalCommissions)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400">Net Expected LEAMSS Margin</p>
              <p className={`text-sm font-extrabold ${netMargin > 0 ? 'text-emerald-700' : 'text-rose-600'}`}>
                {formatINR(netMargin)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400">Gross Margin %</p>
              <p className="text-sm font-extrabold text-emerald-800">{marginPct}%</p>
            </div>
          </div>
        </Card>
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 5. REFUND POLICY MASTER & STATUTORY SAFEGUARDS                */}
      {/* ───────────────────────────────────────────────────────────── */}
      <RefundPolicySection
        product={product}
        refundPolicy={product?.refund_policy}
        onChange={(updatedPolicy) => onChange({ refund_policy: updatedPolicy })}
        onSaved={onSaved}
        readOnly={readOnly}
      />
    </div>
  );
}
