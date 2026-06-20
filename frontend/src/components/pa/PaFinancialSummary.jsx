import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { IndianRupee, Download, Send, FilePlus } from 'lucide-react';

/**
 * Financial Summary block for Partner pipeline view.
 * Shown at proposal_paid / awaiting_final_approval / case_created stages.
 *
 * Props:
 *  - pa            current pre-assessment object
 *  - onDownload    (paId, kind: 'proposal'|'invoice') -> void
 *  - onSendInvoice (paId) -> void
 *  - onGenerateAgreement (pa) -> void  (opens AgreementGenerator modal)
 *  - sendingInvoice  paId currently sending, or null
 */
export default function PaFinancialSummary({ pa, onDownload, onSendInvoice, onGenerateAgreement, sendingInvoice }) {
  if (!['proposal_paid', 'awaiting_final_approval', 'case_created'].includes(pa.stage)) return null;

  const totalReceived = (pa.pre_assessment_fee || 0) + (pa.proposal_fee || 0);
  const upsells = pa.proposal_upsells || [];

  return (
    <div className="bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50 rounded-xl p-4 border border-emerald-200" data-testid={`fin-summary-${pa.id}`}>
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <p className="text-sm font-bold text-emerald-900 flex items-center gap-2">
          <IndianRupee className="h-4 w-4" /> Financial Summary
        </p>
        <Badge className="bg-emerald-600 text-white">
          Total Received: ₹{totalReceived.toLocaleString('en-IN')}
        </Badge>
      </div>
      <div className="grid md:grid-cols-2 gap-3 text-xs">
        {/* Pre-Assessment Fee */}
        <div className="bg-white/70 rounded-lg p-3 border border-emerald-100">
          <p className="font-semibold text-slate-700 mb-1.5">Step 1 · Pre-Assessment Fee</p>
          <div className="flex justify-between"><span className="text-slate-500">Amount:</span> <span className="font-semibold">₹{(pa.pre_assessment_fee || 5100).toLocaleString('en-IN')}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Status:</span> <Badge className="h-4 text-[10px] bg-emerald-100 text-emerald-700 px-1.5">PAID</Badge></div>
        </div>
        {/* Main Fee Breakdown */}
        <div className="bg-white/70 rounded-lg p-3 border border-emerald-100">
          <p className="font-semibold text-slate-700 mb-1.5">Step 2 · Main Service Fee</p>
          {pa.proposal_base_fee != null && (
            <div className="flex justify-between"><span className="text-slate-500">Base Fee:</span> <span>₹{(pa.proposal_base_fee || 0).toLocaleString('en-IN')}</span></div>
          )}
          {pa.proposal_promo_code && (
            <div className="flex justify-between text-red-600"><span>Promo ({pa.proposal_promo_code}):</span> <span>- ₹{(pa.proposal_promo_discount || 0).toLocaleString('en-IN')}</span></div>
          )}
          {(pa.proposal_additional_discount || 0) > 0 && (
            <div className="flex justify-between text-red-600"><span>Custom Discount:</span> <span>- ₹{(pa.proposal_additional_discount || 0).toLocaleString('en-IN')}</span></div>
          )}
          {(pa.proposal_upsell_total || 0) > 0 && (
            <div className="flex justify-between text-leamss-teal-600"><span>Upsells ({upsells.length}):</span> <span>+ ₹{(pa.proposal_upsell_total || 0).toLocaleString('en-IN')}</span></div>
          )}
          <div className="border-t border-dashed border-emerald-300 mt-1.5 pt-1.5 flex justify-between font-bold text-emerald-800">
            <span>Final Paid:</span><span>₹{(pa.proposal_fee || 0).toLocaleString('en-IN')}</span>
          </div>
        </div>
      </div>
      {upsells.length > 0 && (
        <div className="mt-3 bg-white/70 rounded-lg p-3 border border-emerald-100">
          <p className="text-[11px] font-semibold text-slate-700 mb-1">Upsell Add-ons:</p>
          <div className="flex flex-wrap gap-1.5">
            {upsells.map((u, i) => (
              <Badge key={i} className="bg-leamss-teal-100 text-leamss-teal-700 text-[10px]">{u.name} · ₹{(u.amount || 0).toLocaleString('en-IN')}</Badge>
            ))}
          </div>
        </div>
      )}
      {pa.proposal_notes && (
        <div className="mt-3 bg-white/70 rounded-lg p-3 border border-emerald-100">
          <p className="text-[11px] font-semibold text-slate-700 mb-1">Proposal Notes:</p>
          <p className="text-xs text-slate-600 whitespace-pre-line">{pa.proposal_notes}</p>
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={() => onDownload(pa.id, 'proposal')}
          className="h-8 text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50" data-testid={`dl-proposal-${pa.id}`}>
          <Download className="h-3.5 w-3.5 mr-1" /> Proposal PDF
        </Button>
        <Button size="sm" variant="outline" onClick={() => onDownload(pa.id, 'invoice')}
          className="h-8 text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50" data-testid={`dl-invoice-${pa.id}`}>
          <Download className="h-3.5 w-3.5 mr-1" /> Invoice PDF
        </Button>
        <Button size="sm" onClick={() => onSendInvoice(pa.id)} disabled={sendingInvoice === pa.id}
          className="h-8 text-xs bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid={`send-invoice-${pa.id}`}>
          <Send className="h-3.5 w-3.5 mr-1" /> {sendingInvoice === pa.id ? 'Sending…' : 'Send Invoice to Client'}
        </Button>
        {onGenerateAgreement && (
          <Button size="sm" onClick={() => onGenerateAgreement(pa)}
            className="h-8 text-xs bg-gradient-to-r from-leamss-teal-500 to-leamss-orange-600 hover:opacity-90 text-white" data-testid={`gen-agreement-${pa.id}`}>
            <FilePlus className="h-3.5 w-3.5 mr-1" />
            {pa.active_agreement_status === 'signed' ? 'Agreement Signed ✓' : pa.active_agreement_id ? 'View Agreement' : 'Generate Agreement'}
          </Button>
        )}
      </div>
    </div>
  );
}
