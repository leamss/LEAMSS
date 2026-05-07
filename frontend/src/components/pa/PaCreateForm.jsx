import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { User, Mail, Phone, Globe, GraduationCap, Briefcase } from 'lucide-react';

/**
 * PaCreateForm — extracted from PreAssessmentPipeline.jsx
 * Pure controlled component: receives `form`, `setForm`, products list, plus close + submit handlers.
 */
export default function PaCreateForm({ form, setForm, products, onCancel, onSubmit }) {
  const upd = (patch) => setForm({ ...form, ...patch });

  return (
    <Card className="p-6 bg-white shadow-xl border-0 border-l-4 border-l-[#2a777a]" data-testid="pa-create-form">
      <h3 className="text-lg font-bold text-slate-800 mb-4">New Pre-Assessment</h3>
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
