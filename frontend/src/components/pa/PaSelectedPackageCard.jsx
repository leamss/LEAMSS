import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Package, CheckCircle2, Clock, CreditCard, Sparkles,
  FileText, Users, Check, ArrowRight, ShieldCheck, ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';

/**
 * PaSelectedPackageCard — Displays the details of the Package selected by the Client
 * to the Partner in a clear, card layout with key specs, pricing, features, and action buttons.
 */
export default function PaSelectedPackageCard({
  pa,
  onSetPaymentMethod,
  onViewDoc,
}) {
  const pkg = pa?.selected_package_snapshot || pa?.selected_package;
  const isAwaitingSelection = pa?.stage === 'awaiting_package_selection';
  const availablePackages = pa?.available_packages_snapshot || [];

  const handleViewDocument = (url) => {
    if (!url) return;
    const token = localStorage.getItem('token');
    const fullUrl = url.startsWith('http') ? url : `${process.env.REACT_APP_BACKEND_URL}${url}`;
    fetch(fullUrl, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (!r.ok) throw new Error('Fetch failed');
        return r.blob();
      })
      .then(blob => {
        const objUrl = URL.createObjectURL(blob);
        const w = window.open(objUrl, '_blank');
        if (!w) toast.info('Popup blocked — please allow popups to view document');
      })
      .catch(() => toast.error('Failed to open document'));
  };

  // If no package selected and awaiting selection from client
  if (!pkg && isAwaitingSelection) {
    return (
      <div className="bg-gradient-to-r from-amber-50/70 to-orange-50/50 rounded-xl p-4 border border-amber-200 shadow-xs" data-testid={`awaiting-package-card-${pa.id}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-100 flex items-center justify-center text-amber-700 shrink-0 mt-0.5">
              <Package className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="font-semibold text-slate-800 text-sm">Package Selection Options Sent</h4>
                <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-[10px]">
                  ⏳ Awaiting Client Selection
                </Badge>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Client has been presented with <strong>{availablePackages.length} package option(s)</strong>. Once the client picks their preferred package, its details will appear here.
              </p>
              {availablePackages.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {availablePackages.map((p) => (
                    <span
                      key={p.id}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-white border border-amber-200 font-medium text-slate-700 shadow-2xs"
                    >
                      <Package className="h-3 w-3 text-amber-600" />
                      {p.name} · <strong className="text-amber-800">₹{Number(p.price || 0).toLocaleString('en-IN')}</strong>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // If no package selected at all
  if (!pkg) return null;

  const price = Number(pkg.price || 0);
  const paDeduction = (pa.fee_payment_status === 'paid' || pa.fee_amount) ? (Number(pa.fee_amount) || 5100) : 0;
  const paymentMethods = pkg.payment_methods || {};
  const isPackageSelectedStage = pa.stage === 'package_selected';

  // Parse feature notes if available
  const featureList = pkg.info_notes
    ? pkg.info_notes.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
    : [];

  return (
    <div className="bg-gradient-to-br from-white to-slate-50/60 rounded-xl p-4 border border-slate-200/90 shadow-sm hover:border-[#2a777a]/40 transition-colors space-y-3" data-testid={`selected-package-card-${pa.id}`}>
      {/* CARD HEADER */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="w-8 h-8 rounded-lg bg-emerald-100/90 text-emerald-800 flex items-center justify-center shrink-0 shadow-2xs">
            <Package className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-bold text-slate-800 text-sm">
                Client Selected Package
              </h4>
              <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-semibold flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-emerald-700" /> Package Confirmed
              </Badge>
              {pkg.requires_partner_info && (
                <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-[10px] flex items-center gap-1 font-medium">
                  <Users className="h-3 w-3" /> Spouse/Partner Details Required
                </Badge>
              )}
            </div>
          </div>
        </div>

        {pa.package_selected_at && (
          <span className="text-[11px] text-slate-400 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Selected on {new Date(pa.package_selected_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
          </span>
        )}
      </div>

      {/* PACKAGE DETAILS GRID */}
      <div className="grid md:grid-cols-3 gap-3">
        {/* Package Name & Description (2 Cols) */}
        <div className="md:col-span-2 space-y-2 bg-white rounded-lg p-3 border border-slate-200/70">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Package Name</span>
            <p className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
              {pkg.name}
              {pkg.tag && (
                <Badge className="text-[10px] bg-blue-50 text-blue-700 border-blue-200 font-medium">
                  {pkg.tag}
                </Badge>
              )}
            </p>
          </div>

          {pkg.description && (
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Overview</span>
              <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                {pkg.description}
              </p>
            </div>
          )}

          {featureList.length > 0 && (
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider mb-1 block">Included In Package</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mt-1">
                {featureList.map((feature, idx) => (
                  <div key={idx} className="flex items-center gap-1.5 text-xs text-slate-700 bg-slate-50 px-2 py-1 rounded border border-slate-100">
                    <Check className="h-3 w-3 text-emerald-600 shrink-0 font-bold" />
                    <span className="truncate">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Package Attached Document (if configured) */}
          {(pkg.document_name || pkg.document_url) && (
            <div className="pt-1 flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleViewDocument(pkg.document_url)}
                className="h-7 text-xs flex items-center gap-1.5 border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                <FileText className="h-3.5 w-3.5 text-[#2a777a]" />
                <span>View {pkg.document_name || 'Package Specification PDF'}</span>
                <ExternalLink className="h-3 w-3 text-slate-400 ml-0.5" />
              </Button>
            </div>
          )}
        </div>

        {/* Pricing & Supported Payment Methods (1 Col) */}
        <div className="space-y-2.5 bg-gradient-to-br from-[#2a777a]/5 to-[#f7620b]/5 rounded-lg p-3 border border-[#2a777a]/20 flex flex-col justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Package Base Price</span>
            <div className="mt-0.5">
              <span className="text-2xl font-black text-[#2a777a]">
                ₹{price.toLocaleString('en-IN')}
              </span>
              <span className="text-[11px] text-slate-500 font-medium ml-1">+ GST</span>
            </div>

            {paDeduction > 0 && (
              <p className="text-[11px] text-emerald-700 font-medium mt-1 flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
                ₹{paDeduction.toLocaleString('en-IN')} PA fee deductible
              </p>
            )}

            {/* Allowed Payment Options */}
            <div className="mt-3">
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block mb-1.5">
                Allowed Payment Plans
              </span>
              <div className="flex flex-wrap gap-1">
                {paymentMethods.full_payment?.enabled !== false && (
                  <Badge variant="outline" className="text-[10px] bg-white border-slate-200 text-slate-700 font-normal">
                    100% Full Payment
                  </Badge>
                )}
                {paymentMethods.split_50_50?.enabled && (
                  <Badge variant="outline" className="text-[10px] bg-white border-slate-200 text-slate-700 font-normal">
                    50 : 50 Split
                  </Badge>
                )}
                {paymentMethods.installments?.enabled && (
                  <Badge variant="outline" className="text-[10px] bg-white border-slate-200 text-slate-700 font-normal">
                    Up to {paymentMethods.installments?.max_installments || 5} Installments
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {/* Action Area */}
          {isPackageSelectedStage && onSetPaymentMethod && (
            <Button
              onClick={() => onSetPaymentMethod(pa.id)}
              className="w-full bg-[#f7620b] hover:bg-[#e0580a] text-white text-xs font-bold h-8 px-3 rounded-md shadow-xs flex items-center justify-center gap-1.5 transition-colors mt-2"
              data-testid={`set-payment-method-card-${pa.id}`}
            >
              <CreditCard className="h-3.5 w-3.5" />
              Set Payment Method
              <ArrowRight className="h-3.5 w-3.5 ml-0.5" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
