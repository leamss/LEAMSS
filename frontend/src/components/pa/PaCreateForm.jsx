import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { User, Mail, Phone, Globe, GraduationCap, Briefcase, MousePointer2 } from 'lucide-react';

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

/**
 * PaCreateForm — extracted from PreAssessmentPipeline.jsx
 * Pure controlled component: receives `form`, `setForm`, products list, plus close + submit handlers.
 *
 * Phase 4A — Added Lead Source dropdown at top (visible to partners + sales execs).
 */
export default function PaCreateForm({ form, setForm, products, onCancel, onSubmit }) {
  const upd = (patch) => setForm({ ...form, ...patch });
  const currentSource = LEAD_SOURCES.find(s => s.value === form.lead_source);
  const showDetailField = currentSource && currentSource.detail_label;

  return (
    <Card className="p-6 bg-white shadow-xl border-0 border-l-4 border-l-[#2a777a]" data-testid="pa-create-form">
      <h3 className="text-lg font-bold text-slate-800 mb-4">New Pre-Assessment</h3>

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
          <label className="text-sm font-medium text-slate-700 block mb-1">Product</label>
          <select value={form.product_id} onChange={e => upd({ product_id: e.target.value })}
            className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm" data-testid="pa-product">
            <option value="">Select product</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
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
        <Button onClick={onSubmit} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="submit-create-pa">Create Pre-Assessment</Button>
      </div>
    </Card>
  );
}
