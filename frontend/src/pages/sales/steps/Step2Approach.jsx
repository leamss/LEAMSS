// Step 2 — Choose profile-capture approach (direct / occupation finder / resume upload)
import { Card } from '@/components/ui/card';
import { Bot, Briefcase, CheckCircle2, Upload, Wand2 } from 'lucide-react';

export default function Step2Approach({ data, update }) {
  const options = [
    { v: 'direct', icon: Briefcase, label: 'I know the profession', desc: 'Fill the form directly with client details' },
    { v: 'occupation_finder', icon: Bot, label: 'Find the best code (AI)', desc: 'Describe the profession in your words → AI suggests top 3-5 codes' },
    { v: 'resume_upload', icon: Upload, label: 'Upload Resume', desc: 'AI extracts profile fields from PDF/DOCX/TXT (10-20 sec)' },
  ];
  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Wand2 className="h-5 w-5 text-indigo-600" />How would you like to start?
      </h2>
      <p className="text-sm text-slate-600">Pick the fastest path for this client. You can switch later.</p>
      <div className="space-y-2">
        {options.map(o => {
          const Icon = o.icon;
          return (
            <Card
              key={o.v}
              className={`p-4 cursor-pointer transition ${data.approach === o.v ? 'border-indigo-500 ring-2 ring-indigo-200 bg-indigo-50' : 'hover:border-slate-300'}`}
              onClick={() => update('approach', o.v)}
              data-testid={`approach-${o.v}`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`h-6 w-6 ${data.approach === o.v ? 'text-indigo-600' : 'text-slate-400'}`} />
                <div className="flex-1">
                  <p className="font-bold text-sm">{o.label}</p>
                  <p className="text-[11px] text-slate-500">{o.desc}</p>
                </div>
                {data.approach === o.v && <CheckCircle2 className="h-5 w-5 text-indigo-600" />}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
