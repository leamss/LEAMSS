import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { ShieldCheck, ShieldAlert, Clock, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  return `₹${num.toLocaleString('en-IN')}`;
};

export default function PackageRefundBadge({ pkg, compact = false, showConditions = true }) {
  const [expanded, setExpanded] = useState(false);
  const rp = pkg?.refund_policy;

  if (!rp || rp.enabled === false || rp.policy_type === 'none') {
    return null;
  }

  const isProtection = rp.policy_type === 'protection';
  const isStandard = rp.policy_type === 'standard';
  const isNoRefund = rp.policy_type === 'no_refund';

  const priceNum = Number(pkg.price) || 0;
  const pct = rp.refundable_service_fee_pct != null
    ? Number(rp.refundable_service_fee_pct)
    : (isProtection ? 100 : isStandard ? 50 : 0);
  const calculatedRefundAmt = Math.round((priceNum * pct) / 100);

  if (isNoRefund) {
    if (compact) {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
          <ShieldAlert className="h-3 w-3" /> No Refund
        </span>
      );
    }
    return (
      <div className="bg-rose-50/70 rounded-lg p-2.5 border border-rose-200 text-xs text-rose-900 space-y-1">
        <div className="flex items-center gap-1.5 font-bold">
          <ShieldAlert className="h-3.5 w-3.5 text-rose-600" />
          <span>No Refund Policy</span>
        </div>
        <p className="text-[11px] text-rose-700">
          Service fees for this package are strictly non-refundable once onboarding commences.
        </p>
      </div>
    );
  }

  // Protection or Standard Policy
  const badgeColor = isProtection
    ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
    : 'bg-indigo-50 text-indigo-800 border-indigo-300';
  const iconColor = isProtection ? 'text-emerald-600' : 'text-indigo-600';
  const policyName = rp.name || (isProtection ? 'Protection Policy' : 'Standard Policy');
  const feeScopeText = rp.include_govt_fees
    ? 'Govt. & Professional Fees Included'
    : 'Professional Fees Only';

  if (compact) {
    return (
      <div className={`inline-flex flex-col gap-0.5 px-2 py-1 rounded-md border text-xs ${badgeColor}`}>
        <div className="flex items-center gap-1 font-bold">
          <ShieldCheck className={`h-3 w-3 ${iconColor}`} />
          <span>{policyName}</span>
          <span className="font-extrabold ml-1">
            ({pct}% — {formatINR(calculatedRefundAmt)})
          </span>
        </div>
        <span className="text-[10px] text-slate-600 font-medium">
          {feeScopeText}
        </span>
      </div>
    );
  }

  return (
    <div className={`rounded-xl p-3 border transition-colors space-y-2 ${
      isProtection ? 'bg-gradient-to-br from-emerald-50/70 to-teal-50/40 border-emerald-200/90' : 'bg-gradient-to-br from-indigo-50/70 to-blue-50/40 border-indigo-200/90'
    }`}>
      {/* Top row: Badge, % and calculated amount */}
      <div className="flex items-start sm:items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1.5">
          <div className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 ${
            isProtection ? 'bg-emerald-100 text-emerald-700' : 'bg-indigo-100 text-indigo-700'
          }`}>
            <ShieldCheck className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-bold text-slate-900">{policyName}</span>
              <Badge className={`text-[10px] font-bold ${
                isProtection ? 'bg-emerald-600 text-white' : 'bg-indigo-600 text-white'
              }`}>
                {pct}% Refundable Guarantee
              </Badge>
            </div>
            <p className="text-[10px] text-slate-500 font-medium">
              {feeScopeText}
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">Eligible Refund</span>
          <span className={`text-sm font-extrabold ${isProtection ? 'text-emerald-800' : 'text-indigo-800'}`}>
            {formatINR(calculatedRefundAmt)}
          </span>
        </div>
      </div>

      {/* Selected Guarantees Chips */}
      <div className="flex flex-wrap gap-1.5 text-[10px]">
        {rp.negative_skills_assessment_guarantee && (
          <span className="inline-flex items-center gap-1 bg-white/90 border px-2 py-0.5 rounded text-slate-700 font-medium">
            <CheckCircle2 className="h-2.5 w-2.5 text-emerald-600" /> Negative Skills Assessment Refund
          </span>
        )}
        {rp.visa_refusal_guarantee && (
          <span className="inline-flex items-center gap-1 bg-white/90 border px-2 py-0.5 rounded text-slate-700 font-medium">
            <CheckCircle2 className="h-2.5 w-2.5 text-emerald-600" /> Visa Refusal Guarantee
          </span>
        )}
        {rp.voluntary_withdrawal_milestones && (
          <span className="inline-flex items-center gap-1 bg-white/90 border px-2 py-0.5 rounded text-slate-700 font-medium">
            <Clock className="h-2.5 w-2.5 text-indigo-600" /> Withdrawal Milestones
          </span>
        )}
        {rp.claim_window_days > 0 && (
          <span className="inline-flex items-center gap-1 bg-white/90 border px-2 py-0.5 rounded text-slate-600">
            ⏱ {rp.claim_window_days}-Day Claim Window
          </span>
        )}
        {rp.payout_time_days > 0 && (
          <span className="inline-flex items-center gap-1 bg-white/90 border px-2 py-0.5 rounded text-slate-600">
            ⚡ {rp.payout_time_days}-Day Payout SLA
          </span>
        )}
      </div>

      {/* Expandable Qualifying Conditions */}
      {showConditions && (rp.conditions || []).length > 0 && (
        <div className="pt-1 border-t border-slate-200/60">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-[10px] font-bold text-slate-600 hover:text-slate-900 transition-colors"
          >
            <span>{expanded ? 'Hide Terms & Qualifying Conditions' : `View Terms & Conditions (${rp.conditions.length})`}</span>
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>

          {expanded && (
            <ul className="mt-1.5 space-y-1 pl-3 text-[11px] text-slate-600 list-disc">
              {rp.conditions.map((cond, i) => (
                <li key={i} className="leading-snug">{cond}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
