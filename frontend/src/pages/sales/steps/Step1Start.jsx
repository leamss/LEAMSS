// Step 1 — Capture client name + optional email/phone
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { User } from 'lucide-react';

export default function Step1Start({ data, update }) {
  return (
    <div className="max-w-xl mx-auto space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <User className="h-5 w-5 text-indigo-600" />Start a New Assessment
      </h2>
      <p className="text-sm text-slate-600">Enter the client's basic contact info. You can edit these later.</p>
      <div>
        <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Client Name *</Label>
        <Input value={data.client_name} onChange={e => update('client_name', e.target.value)} placeholder="e.g., Rajesh Kumar" data-testid="ca-client-name" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Email</Label>
          <Input type="email" value={data.client_email} onChange={e => update('client_email', e.target.value)} placeholder="optional" data-testid="ca-client-email" />
        </div>
        <div>
          <Label className="text-xs uppercase font-bold text-slate-500 mb-1 block">Phone</Label>
          <Input value={data.client_phone} onChange={e => update('client_phone', e.target.value)} placeholder="optional" data-testid="ca-client-phone" />
        </div>
      </div>
    </div>
  );
}
