import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CreditCard, CheckCircle2, Clock, Send, ArrowRight,
  ShieldCheck, ExternalLink, UserCheck, AlertCircle, FileText
} from 'lucide-react';

/**
 * PaPaymentReviewCard — Displays a payment review card on the Partner Home Page
 * under 'Actions Waiting for You'.
 * Status transitions:
 * - 'Payment is Under Review' (when client paid, partner needs to forward)
 * - 'Payment is Under Review – Forwarded to Admin' (once partner forwards to Admin)
 */
export default function PaPaymentReviewCard({
  pa,
  onForward,
  onViewInPA,
  forwarding = false,
}) {
  // Determine whether payment has been forwarded to admin
  const isForwarded = Boolean(
    pa.stage === 'awaiting_final_approval' ||
    (pa.pending_installment_unlock && pa.installment_forwarded_at) ||
    pa.partner_final_submitted_at ||
    pa.stage === 'documents_submitted' ||
    pa.stage === 'under_review'
  );

  const amountPaid = Number(
    pa.proposal_amount_paid ??
    pa.amount_received ??
    pa.fee_amount ??
    pa.proposal_discounted_total ??
    pa.proposal_fee ??
    0
  );

  const packageName = pa.selected_package_snapshot?.name || pa.product_name || pa.service_type || 'Main Service Package';
  const paymentPlanType = pa.proposal_payment_method_type === 'split_50_50'
    ? '50 : 50 Milestone Split'
    : pa.proposal_payment_method_type === 'installments'
    ? `Installment Plan (${pa.proposal_payment_parts?.length || 3} Parts)`
    : 'Full Payment';

  const paymentDate = pa.proposal_paid_at || pa.fee_paid_at || pa.updated_at;

  return (
    <div
      className={`bg-white rounded-xl p-4 border transition-all shadow-sm ${
        isForwarded
          ? 'border-blue-200 bg-gradient-to-br from-white to-blue-50/30'
          : 'border-amber-200 bg-gradient-to-br from-white to-amber-50/40 hover:border-amber-400'
      }`}
      data-testid={`payment-review-card-${pa.id}`}
    >
      {/* Top Header Row */}
      <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div
            className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm shadow-xs ${
              isForwarded
                ? 'bg-blue-100 text-blue-800'
                : 'bg-amber-100 text-amber-800'
            }`}
          >
            {pa.client_name?.charAt(0).toUpperCase() || 'C'}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-bold text-slate-800 text-sm">{pa.client_name}</p>
              <Badge className="bg-slate-100 text-slate-700 text-xs font-semibold">{pa.pa_number}</Badge>
              {pa.product_name && (
                <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-[11px] font-normal">
                  {pa.product_name}
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {pa.client_email} · {pa.country} — {pa.service_type}
            </p>
          </div>
        </div>

        {/* STATUS BADGE */}
        <div className="flex items-center gap-2">
          {isForwarded ? (
            <Badge
              className="bg-blue-100 text-blue-800 border-blue-300 font-bold text-xs flex items-center gap-1.5 px-2.5 py-1"
              data-testid={`status-forwarded-${pa.id}`}
            >
              <CheckCircle2 className="h-3.5 w-3.5 text-blue-600" />
              Payment is Under Review – Forwarded to Admin
            </Badge>
          ) : (
            <Badge
              className="bg-amber-100 text-amber-800 border-amber-300 font-bold text-xs flex items-center gap-1.5 px-2.5 py-1"
              data-testid={`status-under-review-${pa.id}`}
            >
              <Clock className="h-3.5 w-3.5 text-amber-700" />
              Payment is Under Review
            </Badge>
          )}

          {onViewInPA && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewInPA(pa.id)}
              className="text-xs h-7 border-slate-300 text-slate-700 hover:bg-slate-50 hidden sm:inline-flex"
            >
              <ExternalLink className="h-3 w-3 mr-1 text-slate-400" />
              View PA
            </Button>
          )}
        </div>
      </div>

      {/* Main Details Grid */}
      <div className="grid md:grid-cols-3 gap-3 mt-3">
        {/* Left Column: Payment & Package Details (2 Cols) */}
        <div className="md:col-span-2 space-y-2.5 bg-slate-50/70 rounded-lg p-3 border border-slate-100">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Amount Paid</span>
              <p className="text-base font-extrabold text-emerald-700 mt-0.5">
                ₹{amountPaid.toLocaleString('en-IN')}
              </p>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Package / Plan</span>
              <p className="font-semibold text-slate-800 truncate mt-0.5" title={packageName}>
                {packageName}
              </p>
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Payment Type</span>
              <p className="font-medium text-slate-700 mt-0.5">
                {paymentPlanType}
              </p>
            </div>
          </div>

          {/* Additional details */}
          <div className="flex items-center gap-4 text-xs text-slate-500 pt-1 border-t border-slate-200/60 flex-wrap">
            {paymentDate && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3 text-slate-400" />
                Paid on: {new Date(paymentDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            {pa.client_mobile && (
              <span>Mobile: <strong className="text-slate-700">{pa.client_mobile}</strong></span>
            )}
          </div>
        </div>

        {/* Right Column: Status Summary & Action */}
        <div
          className={`rounded-lg p-3 border flex flex-col justify-between ${
            isForwarded
              ? 'bg-blue-50/50 border-blue-200/80 text-blue-950'
              : 'bg-amber-50/50 border-amber-200/80 text-amber-950'
          }`}
        >
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">Action Status</span>
            {isForwarded ? (
              <div className="mt-1 space-y-1">
                <p className="text-xs font-semibold text-blue-900 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5 text-blue-600 shrink-0" />
                  Submitted to Admin
                </p>
                <p className="text-[11px] text-blue-700 leading-tight">
                  Admin is verifying payment receipt & agreement to activate the client case and assign a Case Manager.
                </p>
              </div>
            ) : (
              <div className="mt-1 space-y-1">
                <p className="text-xs font-semibold text-amber-900 flex items-center gap-1">
                  <AlertCircle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                  Partner Review Required
                </p>
                <p className="text-[11px] text-amber-800 leading-tight">
                  Client has completed the payment. Verify the details and forward to Admin for final case activation.
                </p>
              </div>
            )}
          </div>

          {/* Action Button */}
          {!isForwarded && onForward && (
            <Button
              onClick={() => onForward(pa.id)}
              disabled={forwarding}
              className="w-full bg-[#f7620b] hover:bg-[#e0580a] text-white text-xs font-bold h-8 px-3 rounded-md shadow-xs flex items-center justify-center gap-1.5 transition-colors mt-2"
              data-testid={`forward-to-admin-btn-${pa.id}`}
            >
              <Send className="h-3.5 w-3.5" />
              {forwarding ? 'Forwarding...' : 'Forward to Admin'}
              <ArrowRight className="h-3.5 w-3.5 ml-0.5" />
            </Button>
          )}

          {isForwarded && (
            <div className="mt-2 text-center py-1 bg-white/70 rounded border border-blue-200/50">
              <span className="text-[11px] font-medium text-blue-700">⏳ Awaiting Admin Approval</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
