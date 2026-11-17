// Step 6 — Review & Confirm before saving
import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Briefcase, Award, ShieldCheck } from 'lucide-react';

export default function Step6Review({ data, results }) {
  const best = useMemo(
    () => (results.length ? results.reduce((a, b) => (a.total > b.total ? a : b)) : null),
    [results],
  );

  const claimableYears = data.skills_assessment_claimable_years !== '' && data.skills_assessment_claimable_years !== null && data.skills_assessment_claimable_years !== undefined
    ? parseFloat(data.skills_assessment_claimable_years)
    : (data.skills_assessment_data?.points_claimable_years != null ? parseFloat(data.skills_assessment_data.points_claimable_years) : (parseFloat(data.years_experience_total) || 0));
  const deductedYears = data.skills_assessment_deducted_years !== '' && data.skills_assessment_deducted_years !== null && data.skills_assessment_deducted_years !== undefined
    ? parseFloat(data.skills_assessment_deducted_years)
    : (data.skills_assessment_data?.deducted_years != null ? parseFloat(data.skills_assessment_data.deducted_years) : 0);
  const totalExp = (data.raw_years_experience_total && parseFloat(data.raw_years_experience_total) >= claimableYears)
    ? parseFloat(data.raw_years_experience_total)
    : (claimableYears + deductedYears);
  const claimablePoints = data.skills_assessment_claimable_points !== '' && data.skills_assessment_claimable_points !== null && data.skills_assessment_claimable_points !== undefined
    ? parseFloat(data.skills_assessment_claimable_points)
    : (claimableYears >= 8 ? 15 : claimableYears >= 5 ? 10 : claimableYears >= 3 ? 5 : 0);

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <CheckCircle2 className="h-5 w-5 text-emerald-600" />Review &amp; Confirm
      </h2>

      {/* Client card */}
      <Card className="p-4 bg-slate-50">
        <p className="text-[10px] uppercase font-bold text-slate-500">Client</p>
        <p className="font-bold">{data.client_name}</p>
        <p className="text-xs text-slate-500">{data.client_email || 'no email'} · {data.client_phone || 'no phone'}</p>
      </Card>

      {/* Profile & Professional Details */}
      <Card className="p-4 space-y-2.5" data-testid="review-profile-card">
        <div className="flex items-center justify-between">
          <p className="text-[10px] uppercase font-bold text-slate-500 flex items-center gap-1.5">
            <Briefcase className="h-3.5 w-3.5 text-indigo-600" />Applicant Profile &amp; Career Details
          </p>
          <span className="text-[10px] text-slate-400 capitalize font-medium">{data.marital_status || 'Single'} · Age {data.age || '—'}</span>
        </div>
        <p className="text-xs leading-relaxed">
          <strong>{data.qualification || 'Qualification'}</strong>
          {data.field_of_study ? <> in <em>{data.field_of_study}</em></> : ''}
          {data.current_profession ? <> · Designation: <strong>{data.current_profession}</strong></> : ''}
          {data.employer_name ? <> at <strong>{data.employer_name}</strong>{data.employer_nature ? ` (${data.employer_nature})` : ''}</> : ''}
          {data.ielts_overall ? <> · IELTS <strong>{data.ielts_overall}</strong> (L:{data.ielts_listening || '—'} R:{data.ielts_reading || '—'} W:{data.ielts_writing || '—'} S:{data.ielts_speaking || '—'})</> : ''}
          <> · Total Exp: <strong>{totalExp.toFixed(1)} yrs</strong></>
        </p>

        {data.roles_and_responsibilities && (
          <div className="bg-slate-50 p-2.5 rounded border border-slate-200 text-xs">
            <p className="text-[10px] font-bold uppercase text-slate-500 mb-1">Core Roles, Responsibilities &amp; Job Duties</p>
            <p className="whitespace-pre-line text-[11px] text-slate-700 leading-relaxed">{data.roles_and_responsibilities}</p>
          </div>
        )}
      </Card>

      {/* Assessing Authority & Experience Deduction Summary */}
      {data.occupation_code && (
        <Card className="p-4 border-l-4 border-l-teal-600 bg-teal-50/40" data-testid="review-skills-assessment">
          <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
            <div>
              <p className="text-[10px] uppercase font-bold text-teal-800 tracking-wider flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-teal-700" />Assessing Authority &amp; Experience Deduction
              </p>
              <p className="font-bold text-sm text-teal-950 mt-0.5">
                {data.occupation_body || 'Designated Assessing Authority'} · {data.occupation_code} {data.occupation_title}
              </p>
            </div>
            {data.skills_assessment_outcome && (
              <Badge className={data.skills_assessment_outcome.toLowerCase().includes('positive') ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' : 'bg-amber-100 text-amber-800 border border-amber-300'}>
                {data.skills_assessment_outcome}
              </Badge>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center my-2.5">
            <div className="bg-white p-2 rounded border border-teal-200">
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Total Experience</p>
              <p className="text-base font-extrabold text-slate-800">{totalExp.toFixed(1)} yrs</p>
            </div>
            <div className="bg-white p-2 rounded border border-rose-200">
              <p className="text-[10px] text-rose-600 uppercase font-semibold">Qualifying Deduction</p>
              <p className="text-base font-extrabold text-rose-600">-{deductedYears.toFixed(1)} yrs</p>
            </div>
            <div className="bg-white p-2 rounded border border-emerald-200">
              <p className="text-[10px] text-emerald-700 uppercase font-semibold">Net Claimable</p>
              <p className="text-base font-extrabold text-emerald-700">{claimableYears.toFixed(1)} yrs</p>
            </div>
            <div className="bg-white p-2 rounded border border-indigo-200">
              <p className="text-[10px] text-indigo-700 uppercase font-semibold">GSM Points Claim</p>
              <p className="text-base font-extrabold text-indigo-700">+{claimablePoints} pts</p>
            </div>
          </div>

          <p className="text-[11px] text-slate-600 leading-relaxed">
            {deductedYears > 0 ? (
              <>Under official <strong>{data.occupation_body}</strong> suitability criteria, <strong>{deductedYears.toFixed(1)} years</strong> are deducted to establish skills suitability (Requirement Met Date). The remaining <strong>{claimableYears.toFixed(1)} years</strong> are fully points-claimable under Australian GSM (<strong>+{claimablePoints} points</strong>).</>
            ) : (
              <>Under official <strong>{data.occupation_body}</strong> criteria, 0.0 years deducted. All <strong>{totalExp.toFixed(1)} years</strong> are points-claimable (<strong>+{claimablePoints} points</strong>).</>
            )}
          </p>
        </Card>
      )}

      {/* Alternative Occupations */}
      {data.additional_occupations?.length > 0 && (
        <Card className="p-3 bg-indigo-50/50 border border-indigo-200">
          <p className="text-[10px] uppercase font-bold text-indigo-700 mb-1.5">Alternative Occupations (Side-by-Side in Report)</p>
          <div className="flex flex-wrap gap-2 text-xs">
            {data.additional_occupations.map((alt, idx) => (
              <span key={idx} className="bg-white px-2.5 py-1 rounded border border-indigo-200 text-[11px] shadow-sm">
                <strong>{alt.code}</strong> · {alt.title} <span className="text-slate-400">({alt.assessing_body})</span>
              </span>
            ))}
          </div>
        </Card>
      )}

      {/* Best Match */}
      {best && (
        <Card className="p-4 border-l-4 border-l-indigo-500 bg-indigo-50">
          <p className="text-[10px] uppercase font-bold text-indigo-700">Best Match</p>
          <p className="text-2xl font-bold text-indigo-900">{best.country_code} · {best.total} pts</p>
          <p className="text-[11px] text-indigo-700 italic">{best.recommendation}</p>
        </Card>
      )}

      {/* Cost Estimator */}
      {data.cost_estimator && (
        <Card className="p-4 bg-teal-50/50 border border-teal-200" data-testid="review-cost-estimator">
          <p className="text-[10px] uppercase font-bold text-teal-800 mb-1.5">Cost Estimator &amp; Service Packages</p>
          <div className="space-y-2 text-xs">
            {data.cost_estimator.items?.length > 0 && (
              <p className="text-slate-600">
                <strong>{data.cost_estimator.items.length}</strong> itemised fee/cost item(s) configured.
              </p>
            )}
            {(data.cost_estimator.service_packages || data.cost_estimator.packages || []).filter(p => p.show !== false && p.show_in_report !== false).length > 0 && (
              <div>
                <p className="font-semibold text-teal-900 mb-1">Active Report Packages:</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                  {(data.cost_estimator.service_packages || data.cost_estimator.packages || [])
                    .filter(p => p.show !== false && p.show_in_report !== false)
                    .map((p, idx) => (
                      <div key={idx} className="bg-white p-2 rounded border border-teal-200">
                        <p className="font-bold text-teal-950 truncate">{p.name}</p>
                        <p className="text-[11px] font-mono text-teal-800">₹{(parseFloat(p.total) || 0).toLocaleString()} {p.addon?.enabled ? `(+₹${(parseFloat(p.addon.amount) || 0).toLocaleString()} Add-on)` : ''}</p>
                        <p className="text-[10px] text-slate-500">{p.protection_level || 'Basic'} Protection</p>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      <Card className="p-3 bg-amber-50 border border-amber-200">
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input type="checkbox" defaultChecked data-testid="confirm-checkbox" className="rounded text-amber-600" />
          <span>I confirm this profile, assessing authority deduction, selected packages, and fees are ready for client report generation.</span>
        </label>
      </Card>
    </div>
  );
}
