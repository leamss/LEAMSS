// Step 4 — Country selection (specific / top-3 / custom)
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Globe } from 'lucide-react';
import FieldWithLabel from '../lib/FieldWithLabel';
import { COUNTRIES } from '../lib/constants';

export default function Step4Countries({ data, update }) {
  const toggleCustom = (code) => {
    const list = data.custom_countries.includes(code)
      ? data.custom_countries.filter(c => c !== code)
      : [...data.custom_countries, code];
    update('custom_countries', list);
  };
  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Globe className="h-5 w-5 text-leamss-teal-600" />Country Selection
      </h2>
      <div className="space-y-2">
        {[
          { v: 'specific', label: 'Specific country (deep dive)', desc: 'Pick one country + specific visa subclass' },
          { v: 'top_3', label: 'Top 3 comparison (AU + CA + NZ)', desc: 'Calculate side-by-side across the big 3' },
          { v: 'custom', label: 'Custom selection', desc: 'Pick 2+ countries to compare' },
        ].map(o => (
          <Card key={o.v}
            className={`p-3 cursor-pointer ${data.country_mode === o.v ? 'border-leamss-teal-500 ring-2 ring-leamss-teal-200 bg-leamss-teal-50' : ''}`}
            onClick={() => update('country_mode', o.v)}
            data-testid={`country-mode-${o.v}`}>
            <p className="font-bold text-sm">{o.label}</p>
            <p className="text-[11px] text-slate-500">{o.desc}</p>
          </Card>
        ))}
      </div>
      {data.country_mode === 'specific' && (
        <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded">
          <FieldWithLabel label="Country">
            <Select value={data.specific_country} onValueChange={v => update('specific_country', v)}>
              <SelectTrigger data-testid="ca-specific-country"><SelectValue /></SelectTrigger>
              <SelectContent>{COUNTRIES.map(c => <SelectItem key={c.code} value={c.code}>{c.flag} {c.name}</SelectItem>)}</SelectContent>
            </Select>
          </FieldWithLabel>
          {data.specific_country === 'AU' && (
            <FieldWithLabel label="Visa">
              <Select value={data.visa_subclass} onValueChange={v => update('visa_subclass', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="189">Subclass 189</SelectItem>
                  <SelectItem value="190">Subclass 190</SelectItem>
                  <SelectItem value="491">Subclass 491</SelectItem>
                </SelectContent>
              </Select>
            </FieldWithLabel>
          )}
        </div>
      )}
      {data.country_mode === 'custom' && (
        <div className="bg-slate-50 p-3 rounded space-y-1">
          <p className="text-[10px] uppercase font-bold text-slate-500">Pick at least 2 countries</p>
          {COUNTRIES.map(c => (
            <label key={c.code} className="flex items-center gap-2 text-sm">
              <Switch checked={data.custom_countries.includes(c.code)} onCheckedChange={() => toggleCustom(c.code)} />
              {c.flag} {c.name}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
