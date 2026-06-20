// Step 6 — Review & Confirm before saving
import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { CheckCircle2 } from 'lucide-react';

export default function Step6Review({ data, results }) {
  const best = useMemo(
    () => (results.length ? results.reduce((a, b) => (a.total > b.total ? a : b)) : null),
    [results],
  );
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />Review & Confirm
      </h2>
      <Card className="p-4 bg-slate-50">
        <p className="text-[10px] uppercase font-bold text-slate-500">Client</p>
        <p className="font-bold">{data.client_name}</p>
        <p className="text-xs text-slate-500">{data.client_email || 'no email'} · {data.client_phone || 'no phone'}</p>
      </Card>
      <Card className="p-4">
        <p className="text-[10px] uppercase font-bold text-slate-500">Profile</p>
        <p className="text-xs"><strong>{data.marital_status}</strong> · Age {data.age} · {data.qualification} · IELTS {data.ielts_overall} overall · {data.years_experience_total} yrs exp</p>
      </Card>
      {data.occupation_code && (
        <Card className="p-4 bg-emerald-50">
          <p className="text-[10px] uppercase font-bold text-emerald-700">Occupation</p>
          <p className="font-bold text-sm">{data.occupation_code} · {data.occupation_title}</p>
          <p className="text-[11px] text-slate-500">{data.occupation_body} · {data.occupation_pathway}</p>
        </Card>
      )}
      {best && (
        <Card className="p-4 border-l-4 border-l-leamss-teal-500 bg-leamss-teal-50">
          <p className="text-[10px] uppercase font-bold text-leamss-teal-700">Best Match</p>
          <p className="text-2xl font-bold text-leamss-teal-900">{best.country_code} · {best.total} pts</p>
          <p className="text-[11px] text-leamss-teal-700 italic">{best.recommendation}</p>
        </Card>
      )}
      <Card className="p-3 bg-amber-50 border border-amber-200">
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" defaultChecked data-testid="confirm-checkbox" /> I confirm this profile and code match the client's actual situation.
        </label>
      </Card>
    </div>
  );
}
