import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, RefreshCw, Package, FileText, CheckCircle2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const getAuth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

/**
 * PaProposalForm — Package Forwarding form.
 *
 * NEW FLOW (per partner request — amount input removed):
 * Partner does NOT type any fee amount. Instead, this form loads the
 * product's admin-configured packages (Standard/Smart/Premium…) and lets
 * the partner check off which ones to forward to the client. The client
 * then picks ONE of the forwarded packages from their portal
 * (`awaiting_package_selection` stage → `available_packages_snapshot`).
 * Partner sets up the payment method afterward, once the client has chosen.
 */
export default function PaProposalForm({
  pa, proposalForm, setProposalForm,
  aiGenerating, handleGenerateAI, handleSendProposal,
  onCancel,
}) {
  const [packages, setPackages] = useState([]);
  const [loadingPkgs, setLoadingPkgs] = useState(true);

  useEffect(() => {
    const load = async () => {
      if (!pa.product_id) { setLoadingPkgs(false); return; }
      try {
        const r = await axios.get(`${API}/products/${pa.product_id}`, getAuth());
        setPackages((r.data.packages || []).filter(p => p.is_active));
      } catch (e) { console.error(e); }
      finally { setLoadingPkgs(false); }
    };
    load();
  }, [pa.product_id]);

  const selectedIds = proposalForm.selected_package_ids || [];

  const togglePackage = (pkgId) => {
    setProposalForm(p => ({
      ...p,
      selected_package_ids: (p.selected_package_ids || []).includes(pkgId)
        ? p.selected_package_ids.filter(id => id !== pkgId)
        : [...(p.selected_package_ids || []), pkgId],
    }));
  };

  const viewPackageDoc = async (documentUrl) => {
    if (!documentUrl) return;
    try {
      const r = await fetch(`${process.env.REACT_APP_BACKEND_URL}${documentUrl}`, getAuth());
      if (!r.ok) throw new Error();
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch { /* ignore */ }
  };

  const canSubmit = selectedIds.length > 0;

  return (
    <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-200 space-y-4">
      <p className="text-sm font-semibold text-emerald-800 mb-1 flex items-center gap-2">
        <Package className="h-4 w-4" /> Send Packages to {pa.client_name}
      </p>
      <p className="text-xs text-slate-500 -mt-2">
        Select the package(s) you want your client to see. They'll pick one from their portal — you'll set up the payment method after they choose.
      </p>

      {loadingPkgs ? (
        <p className="text-xs text-slate-400 flex items-center gap-1">
          <RefreshCw className="h-3 w-3 animate-spin" /> Loading packages…
        </p>
      ) : !pa.product_id ? (
        <p className="text-xs text-rose-600">This pre-assessment isn't linked to a product, so no packages are available. Ask admin to link a product first.</p>
      ) : packages.length === 0 ? (
        <p className="text-xs text-rose-600">No active packages found on the linked product. Ask admin to configure packages for this product.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-1 md:grid-cols-3">
          {packages.map(pkg => {
            const checked = selectedIds.includes(pkg.id);
            return (
              <label key={pkg.id}
                className={`p-3 rounded-lg border-2 cursor-pointer flex flex-col transition ${checked ? 'border-emerald-500 bg-white ring-1 ring-emerald-300' : 'border-slate-200 bg-white hover:border-slate-300'}`}
                data-testid={`fwd-pkg-${pkg.package_type || pkg.id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-bold text-slate-800 text-sm">{pkg.name}</p>
                  <input type="checkbox" checked={checked} onChange={() => togglePackage(pkg.id)} className="mt-0.5 shrink-0" />
                </div>
                <p className="text-xl font-extrabold text-emerald-700 mt-1">
                  ₹{Number(pkg.price || 0).toLocaleString('en-IN')}
                </p>
                {pkg.description && <p className="text-xs text-slate-500 mt-1">{pkg.description}</p>}
                {pkg.document_name && (
                  <button type="button" onClick={() => viewPackageDoc(pkg.document_url)}
                    className="text-xs text-emerald-700 underline mt-2 text-left flex items-center gap-1 w-fit"
                    data-testid={`fwd-pkg-doc-${pkg.id}`}>
                    <FileText className="h-3 w-3" /> View {pkg.document_name}
                  </button>
                )}
                {checked && (
                  <span className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Will be sent to client
                  </span>
                )}
              </label>
            );
          })}
        </div>
      )}

      <div>
        <label className="text-xs font-medium text-slate-600 block mb-1">Proposal Notes (optional)</label>
        <Input value={proposalForm.notes || ''}
          onChange={e => setProposalForm({ ...proposalForm, notes: e.target.value })}
          placeholder="e.g. Canada PR Express Entry..." data-testid="proposal-notes" />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1 gap-2 flex-wrap">
          <label className="text-xs font-medium text-slate-600">Proposal Body (personalised, optional)</label>
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
        <textarea value={proposalForm.ai_text || ''}
          onChange={e => setProposalForm({ ...proposalForm, ai_text: e.target.value })}
          className="w-full border rounded-md px-3 py-2 text-sm h-24"
          placeholder="Optional personalised note to accompany the packages…"
          data-testid="proposal-ai-text" />
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => handleSendProposal(pa.id)}
          disabled={!canSubmit}
          className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="submit-proposal">
          <Send className="h-4 w-4 mr-1" /> Send to Client for Package Selection
        </Button>
      </div>
    </div>
  );
}