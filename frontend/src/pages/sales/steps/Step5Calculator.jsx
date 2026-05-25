// Step 5 — Live multi-country calculation + Additional Factors panel.
//
// Phase 6.8.4 — surface the full factor set from /sales/calculator (state
// nomination, AU bonuses, CA PNP / CLB-7 / sibling, NZ employment) so the user
// can fine-tune the score without re-doing the wizard.
//
// Factors are filtered by which countries the user picked in Step 4 — we only
// show factors that actually influence the selected destinations.
import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { AlertCircle, Calculator, CheckCircle2, Loader2, SlidersHorizontal } from 'lucide-react';
import ParallelSubclassPanel from '../components/ParallelSubclassPanel';

const AU_STATES = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'];

export default function Step5Calculator({ results, calculating, data, update, headers }) {
  // Determine which destination countries the user picked so we can scope the
  // additional-factor toggles. Falls back to AU if nothing matches.
  const activeCountries = useMemo(() => {
    if (data?.country_mode === 'top_3') return ['AU', 'CA', 'NZ'];
    if (data?.country_mode === 'custom') return data.custom_countries || ['AU'];
    return [data?.specific_country || 'AU'];
  }, [data?.country_mode, data?.specific_country, data?.custom_countries]);

  const visaSubclass = data?.visa_subclass || '189';
  const showAU = activeCountries.includes('AU');
  const showCA = activeCountries.includes('CA');
  const showNZ = activeCountries.includes('NZ');

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Calculator className="h-5 w-5 text-indigo-600" />Live Calculation
        {calculating && <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />}
      </h2>

      {/* RESULTS */}
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
              {r.template_status && r.template_status !== 'verified' && (
                <div className="text-[9px] mb-2 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 inline-block" data-testid={`template-status-${r.country_code}`}>
                  ⚠️ Template {r.template_status} · admin verification pending
                </div>
              )}
              {r.template_in_use && (
                <div className="text-[9px] mb-2 px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 inline-block" data-testid={`template-status-${r.country_code}`}>
                  ✓ Verified template applied
                </div>
              )}
              <p className="text-4xl font-bold text-indigo-700 text-center my-3">{r.total}</p>
              <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">Top Categories</p>
              <div className="space-y-0.5">
                {Object.entries(r.breakdown || {}).slice(0, 8).map(([cat, val]) => (
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

      {/* Phase 7.2 — Parallel Subclass Comparison (Sir's request) */}
      {headers && data.marital_status && <ParallelSubclassPanel data={data} headers={headers} />}

      {/* ADDITIONAL FACTORS — Phase 6.8.4 */}
      {update && (
        <Card className="p-4 border-l-4 border-l-amber-400 bg-amber-50/30" data-testid="additional-factors">
          <h3 className="text-sm font-bold flex items-center gap-2 mb-1">
            <SlidersHorizontal className="h-4 w-4 text-amber-600" />Additional Factors
            <Badge className="bg-amber-100 text-amber-700 text-[9px]">Live recalc</Badge>
          </h3>
          <p className="text-[11px] text-slate-500 mb-3">Toggle these to see the impact on your score in real time.</p>

          {/* In-country experience — relevant for AU & CA */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            {showAU && (
              <Field label="Australian work experience (yrs)">
                <Input type="number" step="0.5" value={data.years_experience_australia ?? ''}
                  onChange={e => update('years_experience_australia', e.target.value)}
                  placeholder="0" data-testid="factor-exp-au" />
              </Field>
            )}
            {showCA && (
              <Field label="Canadian work experience (yrs)">
                <Input type="number" step="0.5" value={data.canadian_work_years ?? ''}
                  onChange={e => update('canadian_work_years', e.target.value)}
                  placeholder="0" data-testid="factor-exp-ca" />
              </Field>
            )}
          </div>

          {/* AU bonuses */}
          {showAU && (
            <FactorGroup title="Australia · Bonus Points" color="blue">
              <FactorToggle label="Australian Study Requirement (2+ years AU study)"
                pts={5} checked={!!data.australian_study_2_years}
                onChange={v => update('australian_study_2_years', v)}
                testid="factor-au-study" />
              <FactorToggle label="Specialist Education (STEM Master's/PhD at AU institution)"
                pts={10} checked={!!data.specialist_education_stem_au}
                onChange={v => update('specialist_education_stem_au', v)}
                testid="factor-stem" />
              <FactorToggle label="Professional Year Programme (PY) completed"
                pts={5} checked={!!data.professional_year_completed}
                onChange={v => update('professional_year_completed', v)}
                testid="factor-py" />
              <FactorToggle label="NAATI Accredited (Paraprofessional+)"
                pts={5} checked={!!data.naati_accredited}
                onChange={v => update('naati_accredited', v)}
                testid="factor-naati" />
              <FactorToggle label="Regional Study (in regional Australia)"
                pts={5} checked={!!data.regional_study_au}
                onChange={v => update('regional_study_au', v)}
                testid="factor-regional-study" />

              {(visaSubclass === '190' || visaSubclass === '491') && (
                <div className="mt-2 bg-amber-50 p-2 rounded space-y-2">
                  <FactorToggle
                    label={visaSubclass === '190' ? 'Nominated by a state/territory' : 'Sponsored for regional 491'}
                    pts={visaSubclass === '190' ? 5 : 15}
                    checked={!!data.state_nominated}
                    onChange={v => update('state_nominated', v)}
                    testid="factor-state-nominated"
                  />
                  {data.state_nominated && (
                    <Select value={data.state_code || ''} onValueChange={v => update('state_code', v)}>
                      <SelectTrigger className="h-8 text-xs" data-testid="factor-state-code"><SelectValue placeholder="Select state/territory…" /></SelectTrigger>
                      <SelectContent>{AU_STATES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                    </Select>
                  )}
                </div>
              )}
            </FactorGroup>
          )}

          {/* CA bonuses */}
          {showCA && (
            <FactorGroup title="Canada · Additional Points" color="red">
              <FactorToggle label="Provincial Nomination (PNP)"
                pts={600} checked={!!data.provincial_nomination}
                onChange={v => update('provincial_nomination', v)}
                testid="factor-pnp" />
              <FactorToggle label="Valid job offer (NOC 00 — senior management)"
                pts={200} checked={!!data.job_offer_noc_00}
                onChange={v => update('job_offer_noc_00', v)}
                testid="factor-noc-00" />
              <FactorToggle label="Valid job offer (NOC 0 / A / B)"
                pts={50} checked={!!data.job_offer_noc_0_a_b}
                onChange={v => update('job_offer_noc_0_a_b', v)}
                testid="factor-noc-0ab" />
              <FactorToggle label="Canadian post-secondary (3+ years)"
                pts={30} checked={!!data.canadian_education_3plus_years}
                onChange={v => update('canadian_education_3plus_years', v)}
                testid="factor-ca-edu-3" />
              <FactorToggle label="Canadian post-secondary (1-2 years)"
                pts={15} checked={!!data.canadian_education_1_2_years}
                onChange={v => update('canadian_education_1_2_years', v)}
                testid="factor-ca-edu-12" />
              <FactorToggle label="Sibling in Canada (Citizen/PR)"
                pts={15} checked={!!data.sibling_in_canada}
                onChange={v => update('sibling_in_canada', v)}
                testid="factor-sibling" />
              <FactorToggle label="French proficiency CLB 7+"
                pts={50} checked={!!data.french_proficiency_clb_7}
                onChange={v => update('french_proficiency_clb_7', v)}
                testid="factor-french" />
            </FactorGroup>
          )}

          {/* NZ extras */}
          {showNZ && (
            <FactorGroup title="New Zealand · Additional Factors" color="emerald">
              <FactorToggle label="Currently in skilled employment in NZ"
                pts={50} checked={!!data.nz_skilled_employment_current}
                onChange={v => update('nz_skilled_employment_current', v)}
                testid="factor-nz-current" />
              <FactorToggle label="Valid skilled job offer in NZ"
                pts={30} checked={!!data.nz_job_offer}
                onChange={v => update('nz_job_offer', v)}
                testid="factor-nz-offer" />
              <FactorToggle label="Job in regional NZ (outside Auckland)"
                pts={30} checked={!!data.regional_employment_nz}
                onChange={v => update('regional_employment_nz', v)}
                testid="factor-nz-regional" />
            </FactorGroup>
          )}
        </Card>
      )}
    </div>
  );
}


function Field({ label, children }) {
  return (
    <div>
      <Label className="text-[10px] text-slate-600 mb-1 block uppercase font-bold">{label}</Label>
      {children}
    </div>
  );
}

const COLOR_MAP = {
  blue: 'bg-blue-50 border-blue-200 text-blue-700',
  red: 'bg-red-50 border-red-200 text-red-700',
  emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
};

function FactorGroup({ title, color, children }) {
  const cls = COLOR_MAP[color] || COLOR_MAP.blue;
  return (
    <div className={`p-3 rounded border ${cls} mb-2`} data-testid={`group-${color}`}>
      <p className="text-[11px] uppercase font-bold mb-2">{title}</p>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function FactorToggle({ label, pts, checked, onChange, testid }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <Switch checked={checked} onCheckedChange={onChange} data-testid={testid} />
      <span className="flex-1">{label}</span>
      <Badge className={checked ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}>+{pts}</Badge>
    </div>
  );
}
