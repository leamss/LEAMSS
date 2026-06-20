import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { IndianRupee, Send, RefreshCw, Lock, Unlock, Package } from 'lucide-react';

/**
 * PaProposalForm — Send Service Proposal form (extracted from PreAssessmentPipeline.jsx).
 * Pure presentation; all callbacks supplied by parent.
 *
 * Phase 4C Unification — fee_amount is locked to product.service_price when PA is
 * linked to a product. Admin can override by toggling unlock. Partners cannot change.
 */
export default function PaProposalForm({
  pa, proposalForm, setProposalForm, upsellCatalog,
  validatingPromo, handleValidatePromo,
  aiGenerating, handleGenerateAI, handleSendProposal,
  breakdown, onCancel, currentUserRole,
}) {
  const bd = breakdown;
  const hasLockedPrice = !!proposalForm.product_locked_price;
  const isAdmin = currentUserRole === 'admin';
  const isLocked = hasLockedPrice && !proposalForm.price_overridden;

  return (
    <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-200 space-y-4">
      <p className="text-sm font-semibold text-emerald-800 mb-1 flex items-center gap-2">
        <IndianRupee className="h-4 w-4" /> Send Service Proposal to {pa.client_name}
      </p>
      {/* Phase 4C — Product price lock indicator */}
      {hasLockedPrice && (
        <div className={`text-xs rounded p-2 flex items-center justify-between ${isLocked ? 'bg-leamss-teal-50 border border-leamss-teal-200 text-leamss-teal-800' : 'bg-amber-50 border border-amber-200 text-amber-800'}`}>
          <span className="flex items-center gap-1.5">
            <Package className="h-3.5 w-3.5" />
            <span>Linked to product: <strong>{proposalForm.product_name}</strong> · Base price <strong>₹{parseFloat(proposalForm.product_locked_price).toLocaleString('en-IN')}</strong></span>
          </span>
          {isAdmin && (
            <button
              type="button"
              onClick={() => setProposalForm({ ...proposalForm, price_overridden: !proposalForm.price_overridden })}
              className="flex items-center gap-1 text-[11px] font-bold underline hover:no-underline"
              data-testid="toggle-price-lock"
            >
              {isLocked ? <><Unlock className="h-3 w-3" />Override (admin)</> : <><Lock className="h-3 w-3" />Re-lock to product price</>}
            </button>
          )}
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1">
            Base Service Fee (₹) *
            {isLocked && <span className="ml-2 text-[10px] text-leamss-teal-600 font-bold inline-flex items-center gap-1"><Lock className="h-2.5 w-2.5" />Locked to product</span>}
          </label>
          <Input
            type="number"
            value={proposalForm.fee_amount}
            onChange={e => !isLocked && setProposalForm({ ...proposalForm, fee_amount: e.target.value })}
            placeholder="150000"
            readOnly={isLocked}
            className={isLocked ? 'bg-slate-100 cursor-not-allowed' : ''}
            data-testid="proposal-fee"
          />
          {hasLockedPrice && !isAdmin && (
            <p className="text-[10px] text-slate-500 mt-1">💡 Price is locked to product. Only admins can override. Use discount/coupon below to reduce final amount.</p>
          )}
        </div>
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1">Promo Code (optional)</label>
          <div className="flex gap-1">
            <Input value={proposalForm.promo_code}
              onChange={e => setProposalForm({ ...proposalForm, promo_code: e.target.value.toUpperCase(), promo_applied: null })}
              placeholder="SAVE10" className="uppercase" data-testid="proposal-promo" />
            <Button size="sm" variant="outline" onClick={handleValidatePromo}
              disabled={validatingPromo || !proposalForm.promo_code}
              data-testid="apply-promo">
              {validatingPromo ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : 'Apply'}
            </Button>
          </div>
          {proposalForm.promo_applied && (
            <p className="text-[11px] text-emerald-600 mt-1">✓ {proposalForm.promo_applied.code} applied</p>
          )}
        </div>
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1">Additional Discount (₹ flat)</label>
          <Input type="number" value={proposalForm.additional_discount}
            onChange={e => setProposalForm({ ...proposalForm, additional_discount: e.target.value })}
            placeholder="0" data-testid="proposal-add-discount" />
        </div>
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1">Proposal Notes</label>
          <Input value={proposalForm.notes}
            onChange={e => setProposalForm({ ...proposalForm, notes: e.target.value })}
            placeholder="e.g. Canada PR Express Entry..." />
        </div>
      </div>

      {upsellCatalog.length > 0 && (
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1.5">Upsell Bundles (optional — increase deal size)</label>
          <div className="grid md:grid-cols-2 gap-2">
            {upsellCatalog.map(b => {
              const checked = proposalForm.upsell_ids.includes(b.id);
              return (
                <label key={b.id} className={`flex items-start gap-2 p-2 rounded border cursor-pointer text-xs ${checked ? 'bg-white border-emerald-300' : 'bg-white border-slate-200 hover:border-slate-300'}`}>
                  <input type="checkbox" checked={checked}
                    onChange={() => setProposalForm(p => ({
                      ...p,
                      upsell_ids: checked ? p.upsell_ids.filter(x => x !== b.id) : [...p.upsell_ids, b.id]
                    }))}
                    className="mt-0.5" data-testid={`upsell-${b.id}`} />
                  <div className="flex-1">
                    <div className="flex justify-between">
                      <span className="font-semibold text-slate-700">{b.name}</span>
                      <span className="font-bold text-emerald-700">₹{b.amount.toLocaleString('en-IN')}</span>
                    </div>
                    <p className="text-slate-500 text-[11px] mt-0.5">{b.description}</p>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-1 gap-2 flex-wrap">
          <label className="text-xs font-medium text-slate-600">Proposal Body (personalised)</label>
          <div className="flex gap-1.5">
            <Button size="sm" variant="outline" onClick={() => handleGenerateAI(pa.id, false)}
              disabled={!!aiGenerating}
              className="h-7 text-xs border-leamss-orange-300 text-leamss-orange-700 hover:bg-leamss-orange-50"
              data-testid="ai-generate-btn">
              {aiGenerating === 'std' ? <><RefreshCw className="h-3 w-3 animate-spin mr-1" /> Generating…</> : <>✨ Generate with AI</>}
            </Button>
            <Button size="sm" onClick={() => handleGenerateAI(pa.id, true)}
              disabled={!!aiGenerating}
              className="h-7 text-xs bg-gradient-to-r from-amber-500 via-orange-500 to-pink-500 hover:opacity-90 text-white"
              data-testid="ai-premium-btn"
              title="Uses Claude Opus 4.6 — deepest reasoning, best for high-value proposals">
              {aiGenerating === 'premium' ? <><RefreshCw className="h-3 w-3 animate-spin mr-1" /> Crafting…</> : <>👑 Premium AI</>}
            </Button>
          </div>
        </div>
        <textarea value={proposalForm.ai_text}
          onChange={e => setProposalForm({ ...proposalForm, ai_text: e.target.value })}
          className="w-full border rounded-md px-3 py-2 text-sm h-28"
          placeholder="Click 'Generate with AI' (Sonnet 4.6) for a quick draft, or 'Premium AI' (Opus 4.6) for high-value clients…"
          data-testid="proposal-ai-text" />
      </div>

      <div className="bg-white rounded p-3 border border-emerald-200 text-sm font-mono">
        <div className="flex justify-between"><span className="text-slate-500">Base fee</span><span>₹{bd.base.toLocaleString('en-IN')}</span></div>
        {bd.promoDiscount > 0 && <div className="flex justify-between text-emerald-600"><span>Promo ({proposalForm.promo_applied?.code})</span><span>-₹{bd.promoDiscount.toLocaleString('en-IN')}</span></div>}
        {bd.addDisc > 0 && <div className="flex justify-between text-emerald-600"><span>Additional discount</span><span>-₹{bd.addDisc.toLocaleString('en-IN')}</span></div>}
        {bd.upsellTotal > 0 && <div className="flex justify-between text-[#f7620b]"><span>Upsells ({proposalForm.upsell_ids.length})</span><span>+₹{bd.upsellTotal.toLocaleString('en-IN')}</span></div>}
        <div className="border-t border-slate-200 mt-1.5 pt-1.5 flex justify-between font-bold text-emerald-800 text-base">
          <span>Final Amount</span><span data-testid="proposal-final">₹{bd.final.toLocaleString('en-IN')}</span>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => handleSendProposal(pa.id)}
          className="bg-emerald-600 hover:bg-emerald-700" data-testid="submit-proposal">
          <Send className="h-4 w-4 mr-1" /> Send Proposal to Client
        </Button>
      </div>
    </div>
  );
}
