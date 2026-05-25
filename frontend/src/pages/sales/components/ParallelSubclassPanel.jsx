/**
 * Phase 7.2 — Parallel Subclass Comparison
 *
 * Sir's complaint: "Sirf 1 subclass ke points aate hain" (e.g., user picks
 * 190, only 190 score shown, can't compare with 491).
 *
 * This panel runs the unified calculator across ALL relevant subclasses for
 * each picked country (AU: 189/190/491 · CA: EE · NZ: SMC) and shows them
 * side-by-side. Highlights the BEST option.
 *
 * Backend: POST /api/sales/wizard/calculate-parallel
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Trophy, Loader2, RefreshCw, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';
import { API } from '../lib/constants';

const COUNTRY_SUBCLASSES = {
  AU: ['189', '190', '491'],
  CA: ['EE'],
  NZ: ['SMC'],
  UK: ['skilled_worker'],
  USA: ['h1b', 'eb2_niw'],
};

const COUNTRY_FLAGS = { AU: '🇦🇺', CA: '🇨🇦', NZ: '🇳🇿', UK: '🇬🇧', USA: '🇺🇸' };

export default function ParallelSubclassPanel({ data, headers }) {
  // Build profile from wizard data (matches Step5Calculator's calc shape)
  const profile = useMemo(() => ({
    marital_status: data.marital_status,
    primary_applicant: {
      personal: { age: parseInt(data.age, 10) || 0 },
      education: { highest_qualification: data.highest_qualification },
      language: {
        scores: {
          overall: parseFloat(data.lang_overall) || 0,
          listening: parseFloat(data.lang_listening) || 0,
          reading: parseFloat(data.lang_reading) || 0,
          writing: parseFloat(data.lang_writing) || 0,
          speaking: parseFloat(data.lang_speaking) || 0,
        },
      },
      professional: {
        current_profession: data.occupation_title,
        years_experience_total: parseFloat(data.years_experience_total) || 0,
        years_experience_overseas: parseFloat(data.years_experience_overseas) || 0,
        years_experience_in_country: parseFloat(data.years_experience_australia) || 0,
      },
      au_extras: {
        naati_accredited: !!data.naati_accredited,
        professional_year_completed: !!data.professional_year_completed,
        australian_study_2_years: !!data.australian_study_2_years,
        specialist_education_stem_au: !!data.specialist_education_stem_au,
        regional_study_au: !!data.regional_study_au,
        state_nominated: !!data.state_nominated,
        regional_visa: !!data.regional_visa,
      },
      ca_extras: {
        provincial_nomination: !!data.provincial_nomination,
        canadian_education_3plus_years: !!data.canadian_education_3plus_years,
        canadian_education_1_2_years: !!data.canadian_education_1_2_years,
        sibling_in_canada: !!data.sibling_in_canada,
        french_proficiency_clb_7: !!data.french_proficiency_clb_7,
      },
      nz_extras: {
        nz_skilled_employment_current: !!data.nz_skilled_employment_current,
        nz_job_offer: !!data.nz_job_offer,
        regional_employment_nz: !!data.regional_employment_nz,
      },
    },
  }), [data]);

  const activeCountries = useMemo(() => {
    if (data?.country_mode === 'top_3') return ['AU', 'CA', 'NZ'];
    if (data?.country_mode === 'custom') return data.custom_countries || ['AU'];
    return [data?.specific_country || 'AU'];
  }, [data?.country_mode, data?.specific_country, data?.custom_countries]);

  const [results, setResults] = useState({});  // {country: {subclasses, best_subclass, pass_mark}}
  const [loading, setLoading] = useState(false);

  const runComparison = useCallback(async () => {
    setLoading(true);
    try {
      const promises = activeCountries.map(cc =>
        axios.post(`${API}/sales/wizard/calculate-parallel`, {
          country_code: cc,
          visa_subclasses: COUNTRY_SUBCLASSES[cc] || ['189'],
          profile,
          occupation: data.occupation_code ? {
            country_code: data.occupation_country || cc,
            code: data.occupation_code,
            title: data.occupation_title,
            assessing_body: data.occupation_body,
            pathway: data.occupation_pathway,
          } : null,
        }, { headers }).then(r => [cc, r.data])
        .catch(() => [cc, null]),
      );
      const out = {};
      for (const [cc, res] of await Promise.all(promises)) {
        if (res) out[cc] = res;
      }
      setResults(out);
    } finally { setLoading(false); }
  }, [activeCountries, profile, data.occupation_code, data.occupation_country, data.occupation_title, data.occupation_body, data.occupation_pathway, headers]);

  // Auto-run on mount + on factor changes (debounced via key memo)
  useEffect(() => {
    runComparison();
  }, [runComparison]);

  return (
    <Card className="p-4 border-l-4 border-l-emerald-500 bg-gradient-to-br from-emerald-50/40 to-white" data-testid="parallel-subclass-panel">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <h3 className="text-base font-bold flex items-center gap-2 text-emerald-900">
          <Trophy className="h-5 w-5 text-amber-500" />Parallel Subclass Comparison
          <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">Phase 7.2</Badge>
        </h3>
        <Button size="sm" variant="outline" onClick={runComparison} disabled={loading} data-testid="rerun-parallel-btn">
          {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCw className="h-3 w-3 mr-1" />}
          Refresh
        </Button>
      </div>
      <p className="text-[11px] text-slate-600 mb-3">
        Same calculator engine runs across all subclasses — pick the best pathway for this client.
      </p>

      {loading && !Object.keys(results).length ? (
        <div className="flex items-center justify-center py-8 text-slate-400">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />Calculating across subclasses…
        </div>
      ) : (
        <div className="space-y-3">
          {activeCountries.map(cc => {
            const r = results[cc];
            if (!r) return null;
            return (
              <Card key={cc} className="p-3" data-testid={`parallel-country-${cc}`}>
                <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                  <h4 className="text-sm font-bold flex items-center gap-2">
                    <span className="text-xl">{COUNTRY_FLAGS[cc]}</span>
                    {cc} · Pass mark: <span className="text-indigo-700">{r.pass_mark ?? '—'}</span>
                  </h4>
                  {r.best_subclass && (
                    <Badge className="bg-amber-100 text-amber-800 text-[10px] font-bold">
                      <Sparkles className="h-3 w-3 mr-1" />Best: Subclass {r.best_subclass}
                    </Badge>
                  )}
                  {r.template_status && r.template_status !== 'verified' && (
                    <Badge className="bg-amber-50 text-amber-700 text-[9px]">
                      ⚠️ Template {r.template_status}
                    </Badge>
                  )}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2" data-testid={`parallel-subs-${cc}`}>
                  {(r.subclasses || []).map(s => {
                    const isBest = s.visa_subclass === r.best_subclass;
                    return (
                      <Card
                        key={s.visa_subclass}
                        className={`p-3 text-center ${
                          isBest ? 'border-2 border-amber-400 bg-amber-50' :
                          s.eligible ? 'border border-emerald-200 bg-emerald-50/40' :
                          'border border-slate-200'
                        }`}
                        data-testid={`parallel-sub-${cc}-${s.visa_subclass}`}
                      >
                        <p className="text-[10px] uppercase font-bold text-slate-500">Subclass</p>
                        <p className="text-base font-bold text-slate-800">{s.visa_subclass}</p>
                        {s.error ? (
                          <p className="text-[10px] text-rose-500 mt-1">{s.error.slice(0, 40)}</p>
                        ) : (
                          <>
                            <p className={`text-3xl font-bold my-1 ${isBest ? 'text-amber-700' : 'text-indigo-700'}`}>
                              {s.total ?? '—'}
                            </p>
                            <Badge className={`text-[9px] ${
                              s.eligible ? 'bg-emerald-200 text-emerald-800' : 'bg-rose-100 text-rose-700'
                            }`}>
                              {s.eligible ? <><CheckCircle2 className="h-2.5 w-2.5 mr-1 inline" />Eligible</> : <><AlertCircle className="h-2.5 w-2.5 mr-1 inline" />Below pass</>}
                            </Badge>
                          </>
                        )}
                      </Card>
                    );
                  })}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </Card>
  );
}
