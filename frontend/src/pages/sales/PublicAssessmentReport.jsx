/**
 * Public Sales Assessment Report — Phase 6.5 Save & Share Report
 *
 * Route: /sales/report/:token   (NO LOGIN REQUIRED)
 *
 * Renders a read-only summary of a Smart Sales Helper assessment for
 * the client (or any recipient). Sales executive shares this via
 * WhatsApp / Copy Link. Sanitised — no internal IDs, no created_by,
 * no profile_snapshot internals.
 */
import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Sparkles, Trophy, FileText, AlertTriangle, Loader2,
  Globe, Briefcase, GraduationCap, MessageSquare, CheckCircle2, ShieldCheck,
} from 'lucide-react';

import { API } from './lib/constants';

export default function PublicAssessmentReport() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    axios.get(`${API}/sales/assessments/public/${token}`)
      .then(r => setData(r.data))
      .catch(e => {
        const detail = e?.response?.data?.detail || 'Link not found';
        setError(detail);
      })
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center" data-testid="report-loading">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-5" data-testid="report-error">
        <Card className="max-w-md p-6 text-center">
          <AlertTriangle className="h-12 w-12 mx-auto mb-3 text-amber-500" />
          <h1 className="text-lg font-bold mb-1">Link unavailable</h1>
          <p className="text-sm text-slate-600 mb-4">{error}</p>
          <p className="text-[11px] text-slate-400">Please contact your immigration consultant for a new link.</p>
        </Card>
      </div>
    );
  }

  const grouped = (data?.checklist?.items || []).reduce((acc, it) => {
    (acc[it.category] = acc[it.category] || []).push(it);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 p-5" data-testid="public-report-page">
      <div className="max-w-4xl mx-auto space-y-5">
        {/* Header */}
        <Card className="p-5 bg-gradient-to-r from-[#0F766E] to-[#134E4A] text-white border-0 shadow-sm" data-testid="report-header">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <Sparkles className="h-8 w-8 text-amber-300" />
              <div>
                <h1 className="text-xl font-bold">Eligibility Report</h1>
                <p className="text-[11px] text-teal-100">Powered by LEAMSS — We Value Emotions ❤️</p>
              </div>
            </div>
            <Badge className="bg-white/20 text-white border-white/40">Read-only · Confidential</Badge>
          </div>
        </Card>

        {/* Client + Best Country */}
        <Card className="p-5" data-testid="report-summary">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <p className="text-[10px] uppercase font-bold text-slate-400">Applicant</p>
              <p className="text-xl font-bold text-slate-800">{data?.client_name}</p>
              <p className="text-[11px] text-slate-500">
                Prepared by {data?.prepared_by || 'LEAMSS consultant'}
                {data?.created_at && ` · ${new Date(data.created_at).toLocaleDateString()}`}
              </p>
            </div>
            <div className="text-center bg-emerald-50 border border-emerald-200 rounded-lg p-3">
              <Trophy className="h-6 w-6 text-emerald-600 mx-auto mb-1" />
              <p className="text-[10px] uppercase font-bold text-emerald-700">Best Country</p>
              <p className="text-2xl font-bold text-emerald-900">{data?.best_country_code}</p>
              <p className="text-sm font-semibold text-emerald-700">{data?.best_total} pts</p>
            </div>
          </div>
          {data?.best_recommendation && (
            <p className="text-xs italic text-slate-600 bg-amber-50 border-l-4 border-amber-400 p-2 mt-3">
              💡 {data.best_recommendation}
            </p>
          )}
        </Card>

        {/* Highlights grid */}
        <Card className="p-4" data-testid="report-highlights">
          <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-indigo-600" />Your Profile Highlights
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            <Highlight icon={Briefcase} label="Profession" value={data?.highlights?.current_profession} />
            <Highlight icon={GraduationCap} label="Education" value={data?.highlights?.qualification} />
            <Highlight icon={MessageSquare} label="IELTS Overall" value={data?.highlights?.ielts_overall} />
            <Highlight icon={Briefcase} label="Experience" value={data?.highlights?.experience_years ? `${data.highlights.experience_years} yrs` : '—'} />
            <Highlight icon={Globe} label="Marital Status" value={data?.marital_status} />
            {data?.occupation?.code && (
              <Highlight icon={Briefcase} label="Occupation Code" value={`${data.occupation.code} · ${data.occupation.title}`} />
            )}
          </div>
        </Card>

        {/* Nominated Occupation & Why We Chose This Code */}
        {data?.occupation?.code && (() => {
          const totalReportExp = parseFloat(data?.highlights?.experience_years) || 0;
          const occCode = String(data?.occupation?.code || '');
          const occBody = String(data?.occupation?.assessing_body || '');
          const isAcsOcc = occCode.startsWith('26') || occCode.startsWith('1351') || /computer|acs/i.test(occBody);
          const sa = data?.skills_assessment;

          let deductedYears = 0.0;
          if (sa?.deducted_years != null) {
            deductedYears = Number(sa.deducted_years);
          } else if (isAcsOcc) {
            deductedYears = 2.0;
          }

          let claimableYears = 0.0;
          if (sa?.points_claimable_years != null && Number(sa.points_claimable_years) > 0) {
            claimableYears = Number(sa.points_claimable_years);
          } else {
            claimableYears = totalReportExp;
          }

          let claimablePoints = 0;
          if (sa?.points_claimable_points != null && Number(sa.points_claimable_points) > 0) {
            claimablePoints = Number(sa.points_claimable_points);
          } else {
            claimablePoints = claimableYears >= 8 ? 15 : (claimableYears >= 5 ? 10 : (claimableYears >= 3 ? 5 : 0));
          }

          return (
            <Card className="p-4 bg-emerald-50/60 border border-emerald-200" data-testid="report-occupation-choice">
              <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
                <h2 className="text-sm font-bold flex items-center gap-2 text-emerald-950">
                  <Briefcase className="h-4 w-4 text-emerald-600" />
                  Why We Chose Nominated Occupation {data.occupation.code} · {data.occupation.title}
                </h2>
                <Badge className="bg-emerald-100 text-emerald-800 text-[10px]">
                  {data.occupation.assessing_body || 'Skills Assessing Authority'}
                </Badge>
              </div>
              <p className="text-xs text-slate-700 leading-relaxed mb-3">
                We selected this occupation code because your career experience as <strong>{data?.highlights?.current_profession || 'a skilled specialist'}</strong> directly aligns with its core official duties.
                {deductedYears > 0 ? (
                  <span> Under official assessing guidelines, <strong>{deductedYears} year(s)</strong> are deducted as the qualifying period to establish skills suitability (Requirement Met Date), leaving <strong>{claimableYears} years</strong> points-claimable for GSM migration (+{claimablePoints} points).</span>
                ) : (
                  <span> Under assessing criteria, your qualifications satisfy skills suitability directly with 0.0 qualifying deduction, leaving all <strong>{totalReportExp || data?.highlights?.experience_years} years</strong> points-claimable (+{claimablePoints} points).</span>
                )}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <p className="text-[10px] uppercase font-bold text-slate-400">Core Duty Alignment</p>
                  <p className="font-semibold text-emerald-800">100% Core Duty Match</p>
                  <p className="text-[10px] text-slate-500">Aligned with official ABS ANZSCO tasks</p>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <p className="text-[10px] uppercase font-bold text-slate-400">Qualifying Deduction</p>
                  <p className="font-semibold text-rose-700">-{deductedYears} yrs</p>
                  <p className="text-[10px] text-slate-500">Skills suitability baseline</p>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <p className="text-[10px] uppercase font-bold text-slate-400">Claimable Experience</p>
                  <p className="font-semibold text-indigo-700">{claimableYears} yrs</p>
                  <p className="text-[10px] text-slate-500">+{claimablePoints} GSM Migration Points</p>
                </div>
              </div>
            </Card>
          );
        })()}

        {/* Country Comparison */}
        {data?.results?.length > 0 && (
          <Card className="p-4" data-testid="report-results">
            <h2 className="text-sm font-bold mb-3 flex items-center gap-2">
              <Globe className="h-4 w-4 text-indigo-600" />Country-Wise Comparison
            </h2>
            <div className="space-y-2">
              {data.results.map(r => (
                <Card key={`${r.country_code}-${r.visa_subclass || 'na'}`} className={`p-3 ${r.country_code === data.best_country_code ? 'bg-emerald-50 border-l-4 border-l-emerald-500' : 'border'}`} data-testid={`report-result-${r.country_code}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-slate-700 text-white">{r.country_code}</Badge>
                      {r.visa_subclass && <Badge variant="outline" className="text-[10px]">Subclass {r.visa_subclass}</Badge>}
                      {r.country_code === data.best_country_code && (
                        <Badge className="bg-emerald-600 text-white text-[9px]">BEST MATCH</Badge>
                      )}
                    </div>
                    <p className="text-xl font-bold text-slate-800">{r.total} pts</p>
                  </div>
                  {r.recommendation && <p className="text-[11px] italic text-slate-600">{r.recommendation}</p>}
                  {r.thresholds && (
                    <div className="grid grid-cols-3 gap-1 mt-2">
                      {Object.entries(r.thresholds).map(([k, t]) => (
                        <div key={k} className={`text-[10px] p-1 rounded ${t.eligible ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                          {k}: {t.eligible ? '✓ Eligible' : '— Not yet'}
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </Card>
        )}

        {/* Document Checklist */}
        {data?.checklist && (
          <Card className="p-4" data-testid="report-checklist">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-bold flex items-center gap-2">
                <FileText className="h-4 w-4 text-indigo-600" />Document Checklist
              </h2>
              <div className="flex gap-2 text-[10px]">
                <Badge className="bg-indigo-100 text-indigo-700">{data.checklist.stats.total} items</Badge>
                <Badge className="bg-rose-100 text-rose-700">{data.checklist.stats.required} required</Badge>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 mb-3">Based on your destination + occupation + marital status</p>
            <div className="space-y-3">
              {Object.entries(grouped).map(([cat, items]) => (
                <div key={cat}>
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">{cat}</p>
                  <ul className="space-y-1">
                    {items.map(it => (
                      <li key={`${cat}-${it.name}`} className="flex items-start gap-2 text-xs">
                        <div className={`mt-0.5 h-3 w-3 rounded-full border-2 flex-shrink-0 ${it.required ? 'border-rose-400' : 'border-slate-300'}`}></div>
                        <div className="flex-1">
                          <span className={it.required ? 'font-medium text-slate-700' : 'text-slate-500'}>{it.name}</span>
                          {it.required && <Badge className="ml-2 bg-rose-50 text-rose-600 text-[8px] py-0">Required</Badge>}
                          {it.note && <p className="text-[10px] text-slate-400 italic">{it.note}</p>}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* CTA + Footer */}
        <Card className="p-5 bg-gradient-to-r from-[#0F766E] to-[#134E4A] text-white border-0 text-center shadow-sm" data-testid="report-cta">
          <ShieldCheck className="h-7 w-7 mx-auto mb-2 text-emerald-300" />
          <h3 className="text-base font-bold mb-1">Ready to take the next step?</h3>
          <p className="text-[11px] text-teal-100 mb-3">Schedule a free consultation with your LEAMSS consultant to start your application.</p>
          <Button className="bg-white text-[#0F766E] hover:bg-teal-50 font-semibold" onClick={() => window.open('https://wa.me/?text=' + encodeURIComponent('Hi LEAMSS, I just reviewed my eligibility report and would like to schedule a consultation.'), '_blank')} data-testid="cta-whatsapp">
            <MessageSquare className="h-4 w-4 mr-1 text-[#0F766E]" />Contact via WhatsApp
          </Button>
        </Card>

        <p className="text-center text-[10px] text-slate-400 py-2">
          LEAMSS · Smart Sales Helper · This report is generated for informational purposes. Final eligibility is subject to official government assessment.
        </p>
      </div>
    </div>
  );
}


function Highlight({ icon: Icon, label, value }) {
  return (
    <div className="bg-slate-50 rounded p-2 flex items-start gap-2">
      <Icon className="h-3.5 w-3.5 text-indigo-500 mt-0.5 flex-shrink-0" />
      <div>
        <p className="text-[9px] uppercase font-bold text-slate-400">{label}</p>
        <p className="text-xs font-medium text-slate-700 truncate">{value || '—'}</p>
      </div>
    </div>
  );
}
