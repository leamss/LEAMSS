import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { User, Mail, Phone, Globe, GraduationCap, Briefcase, MousePointer2, Zap, AlertTriangle, Sparkles } from 'lucide-react';

const LEAD_SOURCES = [
  { value: '', label: '— Select source (optional) —' },
  { value: 'maple_crm', label: 'Maple CRM Lead' },
  { value: 'walkin', label: 'Walk-in', detail_label: 'Location' },
  { value: 'referral', label: 'Referral', detail_label: 'Referrer Name' },
  { value: 'cold_call', label: 'Cold Call' },
  { value: 'linkedin', label: 'LinkedIn Outreach' },
  { value: 'whatsapp', label: 'WhatsApp Inquiry' },
  { value: 'email', label: 'Email Inquiry' },
  { value: 'event', label: 'Event / Seminar' },
  { value: 'direct', label: 'Direct Inquiry' },
  { value: 'other', label: 'Other', detail_label: 'Specify' },
];

const EXPRESS_REASONS = [
  { value: 'repeat_client', label: 'Repeat Client (PA done previously)' },
  { value: 'pre_qualified_referral', label: 'Pre-qualified Referral' },
  { value: 'vip_customer', label: 'VIP Customer' },
  { value: 'direct_walkin', label: 'Direct Walk-in (already decided)' },
  { value: 'partner_channel', label: 'Partner Channel (pre-screened)' },
  { value: 'renewal_upgrade', label: 'Renewal / Upgrade' },
  { value: 'other', label: 'Other (specify in justification)' },
];

/**
 * PaCreateForm — extracted from PreAssessmentPipeline.jsx
 * Phase 4B Part 2 — Added Sale Type selector at top with Express Sale conditional fields.
 *   - Standard: existing flow (PA fees + first approval + proposal)
 *   - Express: skip PA fees, admin approval needed, then direct to proposal
 */
export default function PaCreateForm({ form, setForm, products, onCancel, onSubmit, expressUsage }) {
  const upd = (patch) => setForm({ ...form, ...patch });
  const currentSource = LEAD_SOURCES.find(s => s.value === form.lead_source);
  const showDetailField = currentSource && currentSource.detail_label;
  const isExpress = form.sale_type === 'express';
  const justifChars = (form.express_sale_justification || '').length;
  const justifValid = justifChars >= 30;
  const reasonValid = isExpress ? !!form.express_sale_reason : true;
  const limitReached = expressUsage && expressUsage.allowed === false;

  return (
    <Card className="p-6 bg-white shadow-xl border-0 border-l-4 border-l-[#2a777a]" data-testid="pa-create-form">
      <h3 className="text-lg font-bold text-slate-800 mb-4">New Pre-Assessment</h3>

      {/* Phase 4B Part 2 — Sale Type Selector */}
      <div className="mb-4" data-testid="sale-type-section">
        <label className="text-sm font-semibold text-slate-700 block mb-2">Sale Type *</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => upd({ sale_type: 'standard', express_sale_reason: null, express_sale_justification: '' })}
            className={`text-left p-3 rounded-md border-2 transition-all ${form.sale_type !== 'express' ? 'border-[#2a777a] bg-[#2a777a]/5' : 'border-slate-200 bg-white hover:border-slate-300'}`}
            data-testid="sale-type-standard"
          >
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="h-4 w-4 text-[#2a777a]" />
              <span className="font-bold text-slate-800 text-sm">Standard Sale</span>
              {form.sale_type !== 'express' && <span className="ml-auto text-[10px] uppercase tracking-wide font-bold text-[#2a777a]">Default</span>}
            </div>
            <p className="text-xs text-slate-600">Customer goes through screening · PA fees ₹5,100 · Standard 5-step funnel</p>
          </button>
          <button
            type="button"
            onClick={() => upd({ sale_type: 'express' })}
            disabled={limitReached}
            className={`text-left p-3 rounded-md border-2 transition-all ${isExpress ? 'border-amber-500 bg-amber-50' : 'border-slate-200 bg-white hover:border-amber-300'} ${limitReached ? 'opacity-50 cursor-not-allowed' : ''}`}
            data-testid="sale-type-express"
          >
            <div className="flex items-center gap-2 mb-1">
              <Zap className="h-4 w-4 text-amber-600" />
              <span className="font-bold text-slate-800 text-sm">Express Sale</span>
              {expressUsage && expressUsage.limit_per_month != null && (
                <span className="ml-auto text-[10px] font-bold uppercase tracking-wide text-amber-700">
                  {expressUsage.used_this_month}/{expressUsage.limit_per_month} this month
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600">Skip PA fees · For pre-qualified customers · Requires admin approval · Direct to main service</p>
            {limitReached && <p className="text-[11px] text-rose-700 mt-1 font-medium">{expressUsage.message}</p>}
          </button>
        </div>
      </div>

      {/* Express Sale conditional fields */}
      {isExpress && (
        <div className="mb-4 p-4 bg-amber-50 border-2 border-amber-200 rounded-md space-y-3" data-testid="express-fields">
          <div className="flex items-start gap-2 text-amber-900 text-xs">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <p><strong>Express sales require admin approval</strong> before service starts. Make sure you have proper justification — this will be reviewed.</p>
          </div>
          <div>
            <label className="text-sm font-semibold text-slate-700 block mb-1">Reason for Express Sale *</label>
            <select
              value={form.express_sale_reason || ''}
              onChange={e => upd({ express_sale_reason: e.target.value })}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm bg-white"
              data-testid="express-reason-select"
            >
              <option value="">— Select a reason —</option>
              {EXPRESS_REASONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-semibold text-slate-700 block mb-1">
              Justification * <span className={`text-xs font-normal ${justifValid ? 'text-emerald-600' : 'text-rose-600'}`}>({justifChars}/30 chars min)</span>
            </label>
            <textarea
              value={form.express_sale_justification || ''}
              onChange={e => upd({ express_sale_justification: e.target.value })}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm h-20"
              placeholder="Explain why this customer qualifies for Express Sale (min 30 characters)..."
              data-testid="express-justification"
            />
          </div>
        </div>
      )}

      {/* Phase 4A — Lead Source Tracking */}
      <div className="mb-4 p-3 bg-indigo-50/50 rounded-md border border-indigo-100" data-testid="lead-source-section">
        <label className="text-sm font-semibold text-slate-700 flex items-center gap-2 mb-1.5">
          <MousePointer2 className="h-3.5 w-3.5 text-indigo-600" />
          Lead Source
          <span className="text-xs font-normal text-slate-500">— Optional but recommended for analytics</span>
        </label>
        <div className={`grid grid-cols-1 ${showDetailField ? 'md:grid-cols-2' : ''} gap-3`}>
          <select
            value={form.lead_source || ''}
            onChange={e => upd({ lead_source: e.target.value || null, lead_source_detail: '' })}
            className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm bg-white"
            data-testid="pa-lead-source"
          >
            {LEAD_SOURCES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
          {showDetailField && (
            <Input
              value={form.lead_source_detail || ''}
              onChange={e => upd({ lead_source_detail: e.target.value })}
              placeholder={currentSource.detail_label}
              data-testid="pa-lead-source-detail"
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Client Name *</label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input value={form.client_name} onChange={e => upd({ client_name: e.target.value })} className="pl-9" placeholder="Full name" data-testid="pa-client-name" />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Email *</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input type="email" value={form.client_email} onChange={e => upd({ client_email: e.target.value })} className="pl-9" placeholder="email@example.com" data-testid="pa-client-email" />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Mobile</label>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input value={form.client_mobile} onChange={e => upd({ client_mobile: e.target.value })} className="pl-9" placeholder="+91-XXXXXXXXXX" data-testid="pa-client-mobile" />
          </div>
        </div>
        <div className="md:col-span-2">
          <label className="text-sm font-medium text-slate-700 block mb-1 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-indigo-500" />
            Product * <span className="text-xs text-slate-400 font-normal">— pick a product first; country &amp; visa type auto-fill</span>
          </label>
          <select
            value={form.product_id}
            onChange={e => {
              const pid = e.target.value;
              const p = products.find(x => x.id === pid);
              if (p) {
                upd({
                  product_id: pid,
                  country: p.country || form.country,
                  service_type: p.visa_type || form.service_type,
                });
              } else {
                upd({ product_id: pid });
              }
            }}
            className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm bg-white"
            data-testid="pa-product"
          >
            <option value="">— Select product —</option>
            {products.map(p => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.country ? ` · ${p.country}` : ''}
                {p.visa_type ? ` · ${p.visa_type}` : ''}
                {p.service_price || p.base_fee ? ` · ₹${(p.service_price || p.base_fee).toLocaleString('en-IN')}` : ''}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Country *</label>
          <div className="relative">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input value={form.country} onChange={e => upd({ country: e.target.value })} className="pl-9" placeholder="Canada, Australia..." data-testid="pa-country" />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Service Type *</label>
          <Input value={form.service_type} onChange={e => upd({ service_type: e.target.value })} placeholder="PR, Work Visa, Study..." data-testid="pa-service-type" />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Age</label>
          <Input type="number" value={form.client_age} onChange={e => upd({ client_age: e.target.value })} placeholder="28" />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Education</label>
          <div className="relative">
            <GraduationCap className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input value={form.education} onChange={e => upd({ education: e.target.value })} className="pl-9" placeholder="Bachelor's, Master's..." />
          </div>
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700 block mb-1">Work Experience</label>
          <div className="relative">
            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input value={form.work_experience} onChange={e => upd({ work_experience: e.target.value })} className="pl-9" placeholder="5 years IT..." />
          </div>
        </div>
      </div>
      <div className="mt-4">
        <label className="text-sm font-medium text-slate-700 block mb-1">Notes</label>
        <textarea value={form.notes} onChange={e => upd({ notes: e.target.value })}
          className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm h-20" placeholder="Additional notes..." />
      </div>
      <div className="flex justify-end gap-3 mt-4">
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
        <Button
          onClick={onSubmit}
          disabled={isExpress && (!reasonValid || !justifValid || limitReached)}
          className={isExpress ? "bg-amber-600 hover:bg-amber-700" : "bg-[#2a777a] hover:bg-[#236466]"}
          data-testid="submit-create-pa"
        >
          {isExpress ? '⚡ Submit Express Sale for Approval' : 'Create Pre-Assessment'}
        </Button>
      </div>
    </Card>
  );
}
