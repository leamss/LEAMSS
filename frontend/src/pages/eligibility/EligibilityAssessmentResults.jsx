/**
 * Phase 6.3 + 6.4 — Eligibility Assessment Runner + Results UI
 *
 * URL: /eligibility/profile/:profileId/assess  — Run an assessment (loading screen)
 * URL: /eligibility/results/:assessmentId      — View results
 *
 * Workflow:
 *   1. From profile detail → click "Run AI Analysis"
 *   2. Runner page shows progress + calls POST /run
 *   3. Once complete → auto-redirect to /eligibility/results/{id}
 *   4. Results page shows: Best Match hero card + comparison + detailed tabs per country
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  ArrowLeft, Sparkles, Trophy, AlertCircle, CheckCircle2, XCircle, RefreshCw,
  Globe, Briefcase, FileText, TrendingUp, Award, Target, ExternalLink,
  ChevronRight, Star, Loader2, AlertTriangle, ThumbsUp, ThumbsDown, Zap,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;


// ════════════════════════════════════════════════════════════════
// Runner — shows progress while assessment runs
// ════════════════════════════════════════════════════════════════
export function EligibilityAssessmentRunner() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('Initialising…');
  const [error, setError] = useState(null);
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    // Pre-fetch profile for the loading screen context
    axios.get(`${API}/eligibility/profiles/${profileId}`, { headers })
      .then(r => setProfile(r.data))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

  useEffect(() => {
    let cancelled = false;
    const stages = [
      { p: 10, t: 'Loading client profile…' },
      { p: 25, t: 'Calculating points across countries…' },
      { p: 45, t: 'Matching occupation codes (ANZSCO / NOC / NZ)…' },
      { p: 65, t: 'Identifying skill assessment bodies…' },
      { p: 80, t: 'Running Claude AI deep analysis…' },
      { p: 95, t: 'Compiling recommendations…' },
    ];
    let idx = 0;
    const interval = setInterval(() => {
      if (cancelled || idx >= stages.length) return;
      setProgress(stages[idx].p);
      setStage(stages[idx].t);
      idx++;
    }, 5500);

    (async () => {
      try {
        const r = await axios.post(`${API}/eligibility/assessments/run`, { profile_id: profileId }, { headers, timeout: 120000 });
        if (cancelled) return;
        setProgress(100);
        setStage('Done');
        await new Promise(res => setTimeout(res, 600));
        navigate(`/eligibility/results/${r.data.id}`, { replace: true });
      } catch (e) {
        if (cancelled) return;
        setError(formatApiError(e, 'Assessment failed'));
      }
    })();

    return () => { cancelled = true; clearInterval(interval); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6" data-testid="assessment-runner">
      <Card className="max-w-xl w-full p-8 text-center space-y-5">
        <div className="flex justify-center">
          {!error ? (
            <div className="relative">
              <Sparkles className="h-16 w-16 text-indigo-600 animate-pulse" />
              <Loader2 className="absolute inset-0 m-auto h-16 w-16 text-indigo-300 animate-spin opacity-50" />
            </div>
          ) : (
            <XCircle className="h-16 w-16 text-rose-500" />
          )}
        </div>
        <h1 className="text-xl font-bold">
          {error ? 'Assessment Failed' : 'Analysing eligibility…'}
        </h1>
        {profile && !error && (
          <p className="text-sm text-slate-500">
            for <strong>{profile.name}</strong> · {profile.professional?.current_profession || '—'}
          </p>
        )}
        {!error ? (
          <>
            <Progress value={progress} className="h-2" data-testid="assessment-progress" />
            <p className="text-sm text-indigo-700 font-medium">{stage}</p>
            <p className="text-[11px] text-slate-400">Claude AI analysis can take up to 60 seconds. Please don&apos;t close this window.</p>
          </>
        ) : (
          <>
            <p className="text-sm text-rose-600">{error}</p>
            <div className="flex gap-2 justify-center">
              <Button variant="outline" onClick={() => navigate(-1)}>Back</Button>
              <Button onClick={() => window.location.reload()} className="bg-indigo-600 hover:bg-indigo-700">
                <RefreshCw className="h-4 w-4 mr-1" />Retry
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}


// ════════════════════════════════════════════════════════════════
// Results Page — Best Match + comparison + per-country tabs
// ════════════════════════════════════════════════════════════════
export function EligibilityAssessmentResults() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeCountry, setActiveCountry] = useState(null);
  const [reRunning, setReRunning] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/eligibility/assessments/${assessmentId}`, { headers });
      setData(r.data);
      const first = (r.data.ranked || [])[0];
      if (first) setActiveCountry(first.country_code);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load assessment'));
    } finally { setLoading(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  useEffect(() => { load(); }, [load]);

  const reRun = async () => {
    setReRunning(true);
    try {
      const r = await axios.post(`${API}/eligibility/assessments/${assessmentId}/re-run`, {}, { headers, timeout: 120000 });
      toast.success('Re-analysis complete');
      navigate(`/eligibility/results/${r.data.id}`, { replace: true });
    } catch (e) {
      toast.error(formatApiError(e, 'Re-run failed'));
    } finally { setReRunning(false); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-400">Loading assessment…</div>;
  if (!data) return null;

  const best = data.best_match;
  const ranked = data.ranked || [];
  const active = ranked.find(c => c.country_code === activeCountry) || ranked[0];

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="results-page">
      <div className="max-w-6xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate(`/eligibility/profile/${data.profile_id}`)}>
              <ArrowLeft className="h-4 w-4 mr-1" />Profile
            </Button>
            <div>
              <h1 className="text-xl font-bold">
                <Sparkles className="inline h-5 w-5 text-indigo-600 mr-1" />
                AI Eligibility Analysis · {data.profile_name}
              </h1>
              <p className="text-[11px] text-slate-500">
                {data.id} · {new Date(data.created_at).toLocaleString('en-IN')} · Mode: <strong>{data.mode_used}</strong> · Duration {data.duration_seconds}s
                {data.from_cache && <Badge className="ml-2 bg-amber-100 text-amber-700 text-[9px]">FROM CACHE</Badge>}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={reRun} disabled={reRunning} data-testid="rerun-btn">
              <RefreshCw className={`h-4 w-4 mr-1 ${reRunning ? 'animate-spin' : ''}`} />
              {reRunning ? 'Re-running…' : 'Re-run'}
            </Button>
          </div>
        </div>

        {/* Best Match Hero Card */}
        {best ? (
          <Card className="p-6 bg-gradient-to-br from-indigo-50 via-white to-emerald-50 border-l-4 border-l-emerald-500" data-testid="best-match-card">
            <div className="flex items-start gap-5">
              <div className="text-7xl">{best.country_flag}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Trophy className="h-5 w-5 text-amber-500" />
                  <Badge className="bg-amber-100 text-amber-800 text-[10px]">BEST MATCH</Badge>
                  <ProbabilityBadge label={best.label} score={best.score} />
                </div>
                <h2 className="text-2xl font-bold">{best.country}</h2>
                <p className="text-sm text-slate-600 mt-1">
                  Recommended: <strong>{best.recommended_visa?.name || '—'}</strong>
                  {best.recommended_visa?.code && <span className="text-slate-400"> · {best.recommended_visa.code}</span>}
                </p>
                <p className="text-sm text-slate-700 mt-3 italic">&ldquo;{best.narrative}&rdquo;</p>
                <div className="flex flex-wrap gap-2 mt-4">
                  <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={() => setActiveCountry(best.country_code)} data-testid="view-details-best">
                    <ChevronRight className="h-4 w-4 mr-1" />View Detailed Analysis
                  </Button>
                  <Button size="sm" variant="outline" disabled title="Coming in Phase 6.5">
                    <FileText className="h-4 w-4 mr-1" />Generate Doc Checklist (6.5)
                  </Button>
                  <Button size="sm" variant="outline" disabled title="Coming in Phase 6.6">
                    <Zap className="h-4 w-4 mr-1" />Create PA from this (6.6)
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        ) : (
          <Card className="p-6 bg-rose-50 border-l-4 border-l-rose-500">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-8 w-8 text-rose-500 flex-shrink-0" />
              <div>
                <h2 className="text-lg font-bold text-rose-900">No strong match found</h2>
                <p className="text-sm text-rose-700 mt-1">
                  None of the analysed countries returned a clear &ldquo;eligible&rdquo; verdict. Review the per-country tabs below for suggested improvements.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Country Comparison Strip */}
        {ranked.length > 1 && (
          <Card className="p-3" data-testid="country-comparison">
            <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">Compare All ({ranked.length})</p>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-2">
              {ranked.map(r => (
                <button
                  key={r.country_code}
                  onClick={() => setActiveCountry(r.country_code)}
                  className={`text-left p-3 border-2 rounded transition ${
                    activeCountry === r.country_code ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 hover:border-slate-300 bg-white'
                  }`}
                  data-testid={`compare-${r.country_code}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-2xl">{r.country_flag}</span>
                    <div className="flex-1">
                      <p className="text-sm font-bold truncate">{r.country}</p>
                      <p className="text-[9px] text-slate-500">{r.country_code}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[10px]">
                    <VerdictBadge verdict={r.overall_verdict} />
                    <span className="font-bold">{(r.success_prediction || {}).score ?? '—'}/100</span>
                  </div>
                </button>
              ))}
            </div>
          </Card>
        )}

        {/* Per-Country Detailed Tabs */}
        {active && !active.error && (
          <Card className="p-5" data-testid={`country-detail-${active.country_code}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{active.country_flag}</span>
                <div>
                  <h2 className="text-lg font-bold">{active.country}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <VerdictBadge verdict={active.overall_verdict} />
                    <ProbabilityBadge label={active.success_prediction?.label} score={active.success_prediction?.score} />
                  </div>
                </div>
              </div>
              <AIStatusBadge enrichment={active.ai_enrichment} />
            </div>

            <Tabs defaultValue="visa" className="space-y-3">
              <TabsList className="grid grid-cols-5">
                <TabsTrigger value="visa" data-testid="tab-visa"><Award className="h-3 w-3 mr-1" />Visa</TabsTrigger>
                <TabsTrigger value="skill" data-testid="tab-skill"><Briefcase className="h-3 w-3 mr-1" />Skill</TabsTrigger>
                <TabsTrigger value="points" data-testid="tab-points"><Target className="h-3 w-3 mr-1" />Points</TabsTrigger>
                <TabsTrigger value="success" data-testid="tab-success"><TrendingUp className="h-3 w-3 mr-1" />Success</TabsTrigger>
                <TabsTrigger value="next" data-testid="tab-next"><Star className="h-3 w-3 mr-1" />Next Steps</TabsTrigger>
              </TabsList>

              <TabsContent value="visa"><VisaTab country={active} /></TabsContent>
              <TabsContent value="skill"><SkillTab country={active} /></TabsContent>
              <TabsContent value="points"><PointsTab country={active} /></TabsContent>
              <TabsContent value="success"><SuccessTab country={active} /></TabsContent>
              <TabsContent value="next"><NextStepsTab country={active} /></TabsContent>
            </Tabs>
          </Card>
        )}

        {active && active.error && (
          <Card className="p-6 bg-amber-50 border-l-4 border-l-amber-500">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-6 w-6 text-amber-600 flex-shrink-0" />
              <div>
                <p className="font-bold text-amber-900">{active.country} unavailable</p>
                <p className="text-sm text-amber-700">{active.error}</p>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────
function ProbabilityBadge({ label, score }) {
  const map = {
    high: { color: 'bg-emerald-100 text-emerald-700 border-emerald-300', icon: ThumbsUp, label: 'HIGH' },
    medium: { color: 'bg-amber-100 text-amber-700 border-amber-300', icon: AlertTriangle, label: 'MEDIUM' },
    low: { color: 'bg-rose-100 text-rose-700 border-rose-300', icon: ThumbsDown, label: 'LOW' },
  };
  const m = map[label] || map.medium;
  const Icon = m.icon;
  return (
    <Badge className={`${m.color} border text-[10px]`}>
      <Icon className="h-3 w-3 mr-0.5" />{m.label}{score ? ` · ${score}/100` : ''}
    </Badge>
  );
}

function VerdictBadge({ verdict }) {
  const map = {
    eligible: { color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2, label: 'Eligible' },
    marginal: { color: 'bg-amber-100 text-amber-700', icon: AlertCircle, label: 'Marginal' },
    ineligible: { color: 'bg-rose-100 text-rose-700', icon: XCircle, label: 'Ineligible' },
    unavailable: { color: 'bg-slate-100 text-slate-600', icon: XCircle, label: 'N/A' },
  };
  const m = map[verdict] || map.unavailable;
  const Icon = m.icon;
  return <Badge className={`${m.color} text-[9px]`}><Icon className="h-2.5 w-2.5 mr-0.5" />{m.label}</Badge>;
}

function AIStatusBadge({ enrichment }) {
  if (!enrichment) return null;
  const ok = enrichment._ai_status === 'ok';
  return (
    <Badge className={ok ? 'bg-purple-100 text-purple-700 text-[9px]' : 'bg-slate-100 text-slate-600 text-[9px]'} title={enrichment._ai_fallback_reason || ''}>
      <Sparkles className="h-2.5 w-2.5 mr-0.5" />
      {ok ? `Claude ${enrichment._ai_model || ''}` : 'Rules-only fallback'}
    </Badge>
  );
}


function VisaTab({ country }) {
  const rec = country.recommended_visa;
  const visas = country.visas_evaluated || [];
  const ai = country.ai_enrichment || {};
  return (
    <div className="space-y-3">
      {rec && (
        <Card className="p-4 bg-emerald-50 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase font-bold text-emerald-700">Recommended Visa</p>
              <h3 className="text-lg font-bold">{rec.code} · {rec.name}</h3>
              <VerdictBadge verdict={rec.verdict} />
            </div>
          </div>
          {ai.recommended_visa_reasoning && (
            <p className="text-sm text-emerald-900 mt-3 italic">{ai.recommended_visa_reasoning}</p>
          )}
          {rec.reasons?.length > 0 && (
            <ul className="mt-2 text-xs space-y-0.5">
              {rec.reasons.map((r, i) => <li key={i} className="flex items-start gap-1.5"><CheckCircle2 className="h-3 w-3 text-emerald-500 mt-0.5 flex-shrink-0" />{r}</li>)}
            </ul>
          )}
          {rec.warnings?.length > 0 && (
            <ul className="mt-2 text-xs space-y-0.5">
              {rec.warnings.map((w, i) => <li key={i} className="flex items-start gap-1.5 text-amber-700"><AlertCircle className="h-3 w-3 text-amber-500 mt-0.5 flex-shrink-0" />{w}</li>)}
            </ul>
          )}
        </Card>
      )}

      <div>
        <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">All Evaluated Visas ({visas.length})</p>
        <div className="space-y-2">
          {visas.map(v => (
            <Card key={v.visa_id || v.code} className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm font-bold">{v.code} · {v.name}</p>
                  <p className="text-[10px] text-slate-500">{v.type} · {v.pathway_type || '—'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <VerdictBadge verdict={v.verdict} />
                  {v.points_minimum > 0 && <Badge className="bg-slate-100 text-slate-700 text-[9px]">Need {v.points_minimum} pts</Badge>}
                </div>
              </div>
              {v.failures?.length > 0 && (
                <div className="mt-2 text-[11px] text-rose-700">
                  {v.failures.map((f, i) => <p key={i}>✗ {f}</p>)}
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>

      {ai.alternative_pathways_in_country?.length > 0 && (
        <Card className="p-3 bg-sky-50 border-l-4 border-l-sky-400">
          <p className="text-[10px] uppercase font-bold text-sky-700 mb-1">Alternative Pathways (AI)</p>
          <ul className="text-xs space-y-0.5">
            {ai.alternative_pathways_in_country.map((a, i) => <li key={i}>• {a}</li>)}
          </ul>
        </Card>
      )}
    </div>
  );
}


function SkillTab({ country }) {
  const body = country.skill_body;
  const occ = (country.occupation || {}).primary;
  const ai = country.ai_enrichment || {};
  return (
    <div className="space-y-3">
      {occ ? (
        <Card className="p-4 bg-indigo-50 border-l-4 border-l-indigo-500">
          <p className="text-[10px] uppercase font-bold text-indigo-700">Occupation Code</p>
          <h3 className="text-lg font-bold">{occ.code} · {occ.title}</h3>
          <p className="text-xs text-slate-600 mt-1">Group: {occ.group} · Pathway: {occ.pathway || '—'}</p>
          <Badge className="bg-indigo-100 text-indigo-700 text-[10px] mt-2">{Math.round((occ.confidence || 0) * 100)}% confidence</Badge>
          {occ.match_reason && <p className="text-[11px] text-slate-500 mt-1">{occ.match_reason}</p>}
          {ai.occupation_code_reasoning && (
            <p className="text-sm text-indigo-900 mt-3 italic">{ai.occupation_code_reasoning}</p>
          )}
        </Card>
      ) : (
        <Card className="p-4 bg-amber-50 border-l-4 border-l-amber-500">
          <p className="text-sm text-amber-800">No clear occupation code match. Manual review recommended.</p>
        </Card>
      )}

      {body && (
        <Card className="p-4 bg-amber-50 border-l-4 border-l-amber-500">
          <p className="text-[10px] uppercase font-bold text-amber-700">Skill Assessment Body</p>
          <h3 className="text-lg font-bold">{body.name}{body.full_name && <span className="text-sm text-slate-500 ml-2">({body.full_name})</span>}</h3>
          <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
            <div><span className="text-slate-500">Fee:</span> <strong>₹{((body.assessment_fee_inr || 0) / 1000).toFixed(0)}K</strong></div>
            <div><span className="text-slate-500">Processing:</span> <strong>{body.processing_time_weeks || '?'} weeks</strong></div>
          </div>
          {body.website && (
            <a href={body.website} target="_blank" rel="noreferrer" className="text-[11px] text-indigo-600 hover:underline mt-2 inline-flex items-center gap-1">
              {body.website.replace(/^https?:\/\//, '')} <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {ai.skill_body_advice && (
            <p className="text-sm text-amber-900 mt-3 italic">{ai.skill_body_advice}</p>
          )}
          {body.documents_required?.length > 0 && (
            <div className="mt-3">
              <p className="text-[10px] uppercase font-bold text-amber-700 mb-1">Documents Required</p>
              <ul className="text-xs space-y-0.5">
                {body.documents_required.map((d, i) => <li key={i} className="flex items-start gap-1.5"><FileText className="h-3 w-3 text-amber-500 mt-0.5 flex-shrink-0" />{d}</li>)}
              </ul>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}


function PointsTab({ country }) {
  const points = country.points || { total: 0, breakdown: {} };
  const entries = Object.entries(points.breakdown || {});
  const total = points.total;
  const minRequired = country.recommended_visa?.code ? (country.visas_evaluated || []).find(v => v.code === country.recommended_visa.code)?.points_minimum || 0 : 0;

  return (
    <div className="space-y-3">
      <Card className="p-4 bg-gradient-to-r from-emerald-50 to-amber-50">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-500">Your Total Points</p>
            <p className="text-4xl font-bold">{total}</p>
            {minRequired > 0 && (
              <p className="text-xs mt-1">
                {total >= minRequired ? (
                  <span className="text-emerald-700">✓ {total - minRequired} above minimum ({minRequired})</span>
                ) : (
                  <span className="text-rose-700">✗ {minRequired - total} below minimum ({minRequired})</span>
                )}
              </p>
            )}
          </div>
          {minRequired > 0 && (
            <div className="w-32">
              <Progress value={Math.min(100, (total / minRequired) * 100)} className="h-2" />
              <p className="text-[10px] text-slate-500 text-center mt-1">{Math.round((total / minRequired) * 100)}% of minimum</p>
            </div>
          )}
        </div>
      </Card>

      <div>
        <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">Points Breakdown</p>
        <div className="space-y-1">
          {entries.length === 0 ? (
            <p className="text-xs italic text-slate-400">No points categories matched the profile.</p>
          ) : entries.map(([cat, val]) => (
            <Card key={cat} className="p-3 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium capitalize">{cat.replace(/_/g, ' ')}</p>
                <p className="text-[10px] text-slate-500">{val.value || val.bucket || val.matched_key} · {val.bucket || val.matched_key || ''}</p>
              </div>
              <Badge className="bg-emerald-100 text-emerald-700">+{val.points}</Badge>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}


function SuccessTab({ country }) {
  const sp = country.success_prediction || {};
  const ai = country.ai_enrichment || {};
  return (
    <div className="space-y-3">
      <Card className="p-4 text-center bg-gradient-to-br from-indigo-50 to-emerald-50">
        <p className="text-[10px] uppercase font-bold text-slate-500">Success Probability</p>
        <ProbabilityBadge label={sp.label} score={sp.score} />
        {ai.estimated_success_probability_text && (
          <p className="text-sm text-slate-700 mt-3 italic">{ai.estimated_success_probability_text}</p>
        )}
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Card className="p-4 bg-emerald-50 border-l-4 border-l-emerald-500">
          <p className="text-[10px] uppercase font-bold text-emerald-700 mb-2 flex items-center gap-1"><ThumbsUp className="h-3 w-3" />Strengths</p>
          <ul className="text-xs space-y-1">
            {(ai.strengths || sp.factors_positive || []).map((s, i) => (
              <li key={i} className="flex items-start gap-1.5"><CheckCircle2 className="h-3 w-3 text-emerald-500 mt-0.5 flex-shrink-0" />{s}</li>
            ))}
          </ul>
        </Card>
        <Card className="p-4 bg-rose-50 border-l-4 border-l-rose-500">
          <p className="text-[10px] uppercase font-bold text-rose-700 mb-2 flex items-center gap-1"><ThumbsDown className="h-3 w-3" />Areas to Improve</p>
          <ul className="text-xs space-y-1">
            {(ai.weaknesses || sp.factors_negative || []).map((s, i) => (
              <li key={i} className="flex items-start gap-1.5"><AlertCircle className="h-3 w-3 text-rose-500 mt-0.5 flex-shrink-0" />{s}</li>
            ))}
          </ul>
        </Card>
      </div>

      {ai.risk_factors?.length > 0 && (
        <Card className="p-4 bg-amber-50 border-l-4 border-l-amber-500">
          <p className="text-[10px] uppercase font-bold text-amber-700 mb-2 flex items-center gap-1"><AlertTriangle className="h-3 w-3" />Risk Factors to Discuss with Client</p>
          <ul className="text-xs space-y-1">
            {ai.risk_factors.map((r, i) => (
              <li key={i} className="flex items-start gap-1.5"><AlertTriangle className="h-3 w-3 text-amber-500 mt-0.5 flex-shrink-0" />{r}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}


function NextStepsTab({ country }) {
  const ai = country.ai_enrichment || {};
  return (
    <div className="space-y-3">
      <Card className="p-4 bg-indigo-50 border-l-4 border-l-indigo-500">
        <p className="text-[10px] uppercase font-bold text-indigo-700 mb-2">Personalised Advice</p>
        {ai.personalised_advice?.length > 0 ? (
          <ol className="text-sm space-y-2">
            {ai.personalised_advice.map((a, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="font-bold text-indigo-600 w-5">{i + 1}.</span>
                <span>{a}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-xs italic text-slate-500">No advice generated. Re-run with AI for personalised guidance.</p>
        )}
      </Card>

      <Card className="p-4 bg-slate-50">
        <p className="text-[10px] uppercase font-bold text-slate-500 mb-2">AI Executive Summary</p>
        <p className="text-sm italic text-slate-700">&ldquo;{ai.narrative || country.recommended_visa?.name + ' — see other tabs for details.'}&rdquo;</p>
      </Card>
    </div>
  );
}
