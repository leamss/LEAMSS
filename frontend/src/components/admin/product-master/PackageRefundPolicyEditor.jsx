import React from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ShieldCheck, ShieldAlert, CheckCircle2, Clock,
  Plus, Trash2, DollarSign, Check, X, ShieldX
} from 'lucide-react';

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  return `₹${num.toLocaleString('en-IN')}`;
};

export const defaultPackagePolicyConfigs = {
  protection: {
    policy_type: 'protection',
    name: 'Protection Policy',
    label: 'Protection Policy Guarantee',
    is_service_fee_refundable: true,
    refundable_service_fee_pct: 100,
    include_govt_fees: true,
    govt_fees_handling: 'subsidized',
    negative_skills_assessment_guarantee: true,
    visa_refusal_guarantee: true,
    voluntary_withdrawal_milestones: true,
    claim_window_days: 30,
    payout_time_days: 14,
    conditions: [
      '100% genuine documentation provided without omissions',
      'Client responds to case manager queries within 7 working days',
      'Medical examination and police clearance passed without adverse records'
    ]
  },
  standard: {
    policy_type: 'standard',
    name: 'Standard Policy',
    label: 'Standard Milestone Policy',
    is_service_fee_refundable: true,
    refundable_service_fee_pct: 50,
    include_govt_fees: false,
    govt_fees_handling: 'non_refundable',
    negative_skills_assessment_guarantee: true,
    visa_refusal_guarantee: false,
    voluntary_withdrawal_milestones: true,
    claim_window_days: 30,
    payout_time_days: 14,
    conditions: [
      '100% genuine documentation provided without omissions',
      'Withdrawal prior to skills assessment filing: 50% refund less file charges'
    ]
  },
  no_refund: {
    policy_type: 'no_refund',
    name: 'No Refund',
    label: 'No Refund Policy',
    is_service_fee_refundable: false,
    refundable_service_fee_pct: 0,
    include_govt_fees: false,
    govt_fees_handling: 'non_refundable',
    negative_skills_assessment_guarantee: false,
    visa_refusal_guarantee: false,
    voluntary_withdrawal_milestones: false,
    claim_window_days: 0,
    payout_time_days: 0,
    conditions: ['Strictly non-refundable service fee once dossier work commences']
  }
};

export default function PackageRefundPolicyEditor({
  packagePrice = 0,
  refundPolicy,
  onChange,
  readOnly = false
}) {
  const [newCondText, setNewCondText] = React.useState('');

  const activeType = refundPolicy?.enabled !== false && refundPolicy?.policy_type
    ? refundPolicy.policy_type
    : 'none';

  const currentPolicy = React.useMemo(() => {
    if (activeType === 'none' || !refundPolicy) return null;
    const def = defaultPackagePolicyConfigs[activeType] || defaultPackagePolicyConfigs.protection;
    return {
      ...def,
      ...refundPolicy,
      policy_type: activeType
    };
  }, [activeType, refundPolicy]);

  const priceNum = Number(packagePrice) || 0;
  const pct = currentPolicy?.refundable_service_fee_pct != null
    ? Number(currentPolicy.refundable_service_fee_pct)
    : (activeType === 'protection' ? 100 : activeType === 'standard' ? 50 : 0);
  const calculatedRefundAmt = Math.round((priceNum * pct) / 100);

  const handleSelectType = (typeKey) => {
    if (readOnly) return;
    if (typeKey === 'none') {
      onChange(null);
      return;
    }
    const def = defaultPackagePolicyConfigs[typeKey] || defaultPackagePolicyConfigs.protection;
    onChange({
      ...def,
      enabled: true,
      policy_type: typeKey
    });
  };

  const updateField = (field, value) => {
    if (readOnly || !currentPolicy) return;
    onChange({
      ...currentPolicy,
      enabled: true,
      [field]: value
    });
  };

  const handleAddCondition = () => {
    const text = newCondText.trim();
    if (!text || !currentPolicy) return;
    const nextConds = [...(currentPolicy.conditions || []), text];
    updateField('conditions', nextConds);
    setNewCondText('');
  };

  const handleRemoveCondition = (idx) => {
    if (!currentPolicy) return;
    const nextConds = (currentPolicy.conditions || []).filter((_, i) => i !== idx);
    updateField('conditions', nextConds);
  };

  return (
    <div className="bg-amber-50/40 rounded-lg p-3 border border-amber-200/70 space-y-3">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="h-4 w-4 text-emerald-700" />
          <span className="text-[11px] uppercase font-bold text-slate-700 tracking-wide">
            Refund Policy for this Package
          </span>
        </div>
        {activeType !== 'none' && (
          <Badge
            className={`text-[10px] font-bold ${
              activeType === 'protection'
                ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                : activeType === 'standard'
                ? 'bg-indigo-100 text-indigo-800 border-indigo-300'
                : 'bg-rose-100 text-rose-800 border-rose-300'
            }`}
          >
            {activeType === 'protection'
              ? 'Protection Policy Selected'
              : activeType === 'standard'
              ? 'Standard Policy Selected'
              : 'No Refund Policy Selected'}
          </Badge>
        )}
      </div>

      {/* POLICY MODEL TILES */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
        {/* Protection Policy */}
        <div
          onClick={() => handleSelectType('protection')}
          className={`p-2.5 rounded-lg border-2 cursor-pointer transition text-left flex flex-col justify-between ${
            activeType === 'protection'
              ? 'border-emerald-600 bg-emerald-50/70 shadow-2xs ring-1 ring-emerald-400'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
          data-testid="pkg-refund-type-protection"
        >
          <div>
            <div className="flex items-center justify-between pb-1">
              <span className="font-extrabold text-xs text-slate-900 flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                Protection Policy
              </span>
              {activeType === 'protection' && (
                <Check className="h-3.5 w-3.5 text-emerald-600" />
              )}
            </div>
            <p className="text-[10px] text-slate-600 leading-tight">
              100% Refund (Govt. & Professional Fees) on negative outcome.
            </p>
          </div>
        </div>

        {/* Standard Policy */}
        <div
          onClick={() => handleSelectType('standard')}
          className={`p-2.5 rounded-lg border-2 cursor-pointer transition text-left flex flex-col justify-between ${
            activeType === 'standard'
              ? 'border-indigo-600 bg-indigo-50/70 shadow-2xs ring-1 ring-indigo-400'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
          data-testid="pkg-refund-type-standard"
        >
          <div>
            <div className="flex items-center justify-between pb-1">
              <span className="font-extrabold text-xs text-slate-900 flex items-center gap-1">
                <Clock className="h-3.5 w-3.5 text-indigo-600" />
                Standard Policy
              </span>
              {activeType === 'standard' && (
                <Check className="h-3.5 w-3.5 text-indigo-600" />
              )}
            </div>
            <p className="text-[10px] text-slate-600 leading-tight">
              Tiered/Milestone Refund (Professional Fees Only).
            </p>
          </div>
        </div>

        {/* No Refund */}
        <div
          onClick={() => handleSelectType('no_refund')}
          className={`p-2.5 rounded-lg border-2 cursor-pointer transition text-left flex flex-col justify-between ${
            activeType === 'no_refund'
              ? 'border-rose-600 bg-rose-50/70 shadow-2xs ring-1 ring-rose-400'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
          data-testid="pkg-refund-type-norefund"
        >
          <div>
            <div className="flex items-center justify-between pb-1">
              <span className="font-extrabold text-xs text-slate-900 flex items-center gap-1">
                <ShieldAlert className="h-3.5 w-3.5 text-rose-600" />
                No Refund
              </span>
              {activeType === 'no_refund' && (
                <Check className="h-3.5 w-3.5 text-rose-600" />
              )}
            </div>
            <p className="text-[10px] text-slate-600 leading-tight">
              Strictly Non-Refundable service fee.
            </p>
          </div>
        </div>

        {/* Not Configured / Disabled */}
        <div
          onClick={() => handleSelectType('none')}
          className={`p-2.5 rounded-lg border-2 cursor-pointer transition text-left flex flex-col justify-between ${
            activeType === 'none'
              ? 'border-slate-500 bg-slate-100 shadow-2xs ring-1 ring-slate-400'
              : 'border-slate-200 bg-white hover:border-slate-300'
          }`}
          data-testid="pkg-refund-type-none"
        >
          <div>
            <div className="flex items-center justify-between pb-1">
              <span className="font-bold text-xs text-slate-600 flex items-center gap-1">
                <ShieldX className="h-3.5 w-3.5 text-slate-400" />
                No Policy
              </span>
              {activeType === 'none' && (
                <Check className="h-3.5 w-3.5 text-slate-600" />
              )}
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">
              Do not display refund options for this package.
            </p>
          </div>
        </div>
      </div>

      {/* DETAILED CONFIGURATION WHEN A POLICY IS SELECTED */}
      {currentPolicy && activeType !== 'none' && (
        <div className="space-y-3 pt-2 border-t border-amber-200/60">
          {/* Service Fee Percentage & Calculated Amount */}
          <div className="bg-white rounded-lg p-2.5 border space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly || activeType === 'no_refund'}
                  checked={!!currentPolicy.is_service_fee_refundable}
                  onChange={(e) => updateField('is_service_fee_refundable', e.target.checked)}
                  className="h-3.5 w-3.5 rounded text-emerald-600"
                />
                <span className="text-xs font-bold text-slate-800">
                  Service Fee Refundable
                </span>
              </label>

              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    disabled={readOnly || !currentPolicy.is_service_fee_refundable || activeType === 'no_refund'}
                    value={currentPolicy.refundable_service_fee_pct ?? ''}
                    onChange={(e) => {
                      const val = e.target.value === '' ? '' : Math.min(100, Math.max(0, Number(e.target.value)));
                      updateField('refundable_service_fee_pct', val);
                    }}
                    className="h-7 w-20 text-xs font-bold text-right"
                  />
                  <span className="text-xs font-bold text-slate-500">%</span>
                </div>

                <div className="bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded text-right min-w-[120px]">
                  <p className="text-[9px] uppercase font-bold text-emerald-700">Calculated Refund</p>
                  <p className="text-xs font-black text-emerald-800">
                    {formatINR(calculatedRefundAmt)}
                  </p>
                </div>
              </div>
            </div>

            {priceNum <= 0 && (
              <p className="text-[10px] text-amber-700 font-medium">
                Tip: Enter a Package Price above to compute the exact refundable amount in ₹.
              </p>
            )}
          </div>

          {/* Fee Inclusion & Guarantees Checkboxes */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {/* Left: Fee Inclusion */}
            <div className="bg-white rounded-lg p-2.5 border space-y-2">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">
                Fee Inclusions (Protection vs Standard)
              </span>

              <label className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly || activeType === 'no_refund'}
                  checked={!!currentPolicy.include_govt_fees}
                  onChange={(e) => updateField('include_govt_fees', e.target.checked)}
                  className="h-3.5 w-3.5 rounded text-emerald-600"
                />
                <div>
                  <span className="font-semibold">
                    {currentPolicy.include_govt_fees
                      ? '100% Refund* (Including Govt. & Professional Fees)'
                      : '100% Refund* (Professional Fees Only)'}
                  </span>
                  <p className="text-[10px] text-slate-500">
                    {currentPolicy.include_govt_fees
                      ? 'Full reimbursement covering statutory authority & consultant charges'
                      : 'Statutory government charges excluded from refund'}
                  </p>
                </div>
              </label>
            </div>

            {/* Right: Triggers & Guarantees */}
            <div className="bg-white rounded-lg p-2.5 border space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 block">
                Statutory Guarantees
              </span>

              <label className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly || activeType === 'no_refund'}
                  checked={!!currentPolicy.negative_skills_assessment_guarantee}
                  onChange={(e) => updateField('negative_skills_assessment_guarantee', e.target.checked)}
                  className="h-3.5 w-3.5 rounded text-emerald-600"
                />
                <span>Negative Skills Assessment Guarantee</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly || activeType === 'no_refund'}
                  checked={!!currentPolicy.visa_refusal_guarantee}
                  onChange={(e) => updateField('visa_refusal_guarantee', e.target.checked)}
                  className="h-3.5 w-3.5 rounded text-emerald-600"
                />
                <span>Official Visa Refusal Guarantee</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                <input
                  type="checkbox"
                  disabled={readOnly || activeType === 'no_refund'}
                  checked={!!currentPolicy.voluntary_withdrawal_milestones}
                  onChange={(e) => updateField('voluntary_withdrawal_milestones', e.target.checked)}
                  className="h-3.5 w-3.5 rounded text-emerald-600"
                />
                <span>Voluntary Withdrawal Milestones</span>
              </label>
            </div>
          </div>

          {/* Claim Window & Payout SLA */}
          <div className="grid grid-cols-2 gap-2 bg-white rounded-lg p-2.5 border">
            <div>
              <Label className="text-[10px] font-bold text-slate-600">Claim Window (Days)</Label>
              <Input
                type="number"
                min="1"
                disabled={readOnly || activeType === 'no_refund'}
                value={currentPolicy.claim_window_days ?? 30}
                onChange={(e) => updateField('claim_window_days', Number(e.target.value) || 30)}
                className="h-7 text-xs font-bold mt-1"
              />
            </div>
            <div>
              <Label className="text-[10px] font-bold text-slate-600">Payout SLA (Days)</Label>
              <Input
                type="number"
                min="1"
                disabled={readOnly || activeType === 'no_refund'}
                value={currentPolicy.payout_time_days ?? 14}
                onChange={(e) => updateField('payout_time_days', Number(e.target.value) || 14)}
                className="h-7 text-xs font-bold mt-1"
              />
            </div>
          </div>

          {/* Conditions List */}
          <div className="bg-white rounded-lg p-2.5 border space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-[10px] uppercase font-bold text-slate-500">
                Refund Qualifying Conditions ({(currentPolicy.conditions || []).length})
              </Label>
            </div>

            <div className="space-y-1">
              {(currentPolicy.conditions || []).map((c, idx) => (
                <div key={idx} className="flex items-center justify-between gap-1 text-[11px] bg-slate-50 p-1.5 rounded border">
                  <span className="text-slate-700 leading-tight">• {c}</span>
                  {!readOnly && (
                    <button
                      type="button"
                      onClick={() => handleRemoveCondition(idx)}
                      className="text-slate-400 hover:text-rose-600 p-0.5"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            {!readOnly && (
              <div className="flex items-center gap-1.5 pt-1">
                <Input
                  value={newCondText}
                  onChange={(e) => setNewCondText(e.target.value)}
                  placeholder="Add custom condition (e.g. Genuine documents submitted)..."
                  className="h-7 text-xs flex-1"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddCondition();
                    }
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleAddCondition}
                  className="h-7 text-xs font-semibold gap-1"
                >
                  <Plus className="h-3 w-3" /> Add
                </Button>
              </div>
            )}
          </div>

          {/* LIVE SUMMARY PREVIEW */}
          <div className="bg-slate-900 text-white rounded-lg p-2.5 space-y-1 shadow-inner">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                Live Preview: What Sales & Clients Will See
              </span>
              <Badge className="bg-emerald-600 text-white text-[9px]">
                {currentPolicy.name || 'Refund Policy'}
              </Badge>
            </div>
            <p className="text-xs font-semibold text-emerald-300">
              {currentPolicy.is_service_fee_refundable
                ? `${pct}% Refundable — ${formatINR(calculatedRefundAmt)}`
                : 'Non-Refundable'}
              {' · '}
              <span className="text-slate-200">
                {currentPolicy.include_govt_fees ? 'Govt. & Professional Fees' : 'Professional Fees Only'}
              </span>
            </p>
            <div className="flex flex-wrap gap-1.5 pt-0.5 text-[10px] text-slate-300">
              {currentPolicy.negative_skills_assessment_guarantee && (
                <span className="bg-slate-800 px-1.5 py-0.5 rounded">✓ Skills Assessment Guarantee</span>
              )}
              {currentPolicy.visa_refusal_guarantee && (
                <span className="bg-slate-800 px-1.5 py-0.5 rounded">✓ Visa Refusal Guarantee</span>
              )}
              {currentPolicy.voluntary_withdrawal_milestones && (
                <span className="bg-slate-800 px-1.5 py-0.5 rounded">✓ Withdrawal Milestones</span>
              )}
              {currentPolicy.claim_window_days > 0 && (
                <span className="bg-slate-800 px-1.5 py-0.5 rounded">⏱ {currentPolicy.claim_window_days}d Claim Window</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
