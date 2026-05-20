// Step 5 — Live multi-country calculation results
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Calculator, CheckCircle2, Loader2 } from 'lucide-react';

export default function Step5Calculator({ results, calculating }) {
  return (
    <div>
      <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
        <Calculator className="h-5 w-5 text-indigo-600" />Live Calculation
        {calculating && <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />}
      </h2>
      {!results.length ? (
        <p className="text-sm text-slate-500 italic">Calculating…</p>
      ) : (
        <div className={`grid gap-3 ${results.length === 1 ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'}`} data-testid="calc-results">
          {results.map(r => (
            <Card key={`${r.country_code}-${r.visa_subclass || 'na'}`} className="p-4 border-2 border-indigo-200 bg-gradient-to-br from-white to-indigo-50" data-testid={`result-${r.country_code}`}>
              <div className="flex items-center justify-between mb-2">
                <Badge className="bg-indigo-600 text-white">{r.country_code}</Badge>
                {r.visa_subclass && <Badge variant="outline" className="text-[10px]">Subclass {r.visa_subclass}</Badge>}
              </div>
              <p className="text-4xl font-bold text-indigo-700 text-center my-3">{r.total}</p>
              <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">Top Categories</p>
              <div className="space-y-0.5">
                {Object.entries(r.breakdown || {}).slice(0, 6).map(([cat, val]) => (
                  <div key={cat} className="flex items-center justify-between text-[11px]">
                    <span className="capitalize">{cat.replace(/^ca_|^nz_/, '').replace(/_/g, ' ')}</span>
                    <Badge className={(val.points || 0) > 0 ? 'bg-emerald-100 text-emerald-700 text-[9px]' : 'bg-slate-100 text-slate-500 text-[9px]'}>+{val.points || 0}</Badge>
                  </div>
                ))}
              </div>
              <div className="mt-3 space-y-1">
                {Object.entries(r.visa_eligibility || {}).map(([code, v]) => (
                  <div key={code} className={`text-[10px] flex items-center gap-1 ${v.eligible ? 'text-emerald-700' : 'text-slate-500'}`}>
                    {v.eligible ? <CheckCircle2 className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                    {code} · {v.eligible ? 'ELIGIBLE' : 'NOT YET'}
                  </div>
                ))}
              </div>
              <p className="text-[10px] mt-2 italic text-amber-900">{r.recommendation}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
