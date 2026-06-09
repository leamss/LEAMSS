/**
 * Phase 10.3/10.7 — Atlas Auto-Suggest Modal
 *
 * Sales partner types a free-text candidate description, optionally picks a
 * destination country + region, and the system returns the top 3-5 NOC/ANZSCO
 * matches with full country-specific Atlas data (TEER/skill level, federal
 * eligibility, PNPs / state nominations, round cutoffs, regional pilots,
 * Quebec section for CA, etc.).
 *
 * Works for AU, CA, NZ (and any future country added to occupation_master).
 */
import { useState } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import {
  Sparkles, Loader2, CheckCircle2, MapPin, Globe, TrendingUp, Award,
  ShieldCheck, Stethoscope, Microscope, Hammer, BookOpen, Plane, Users,
  Shield as ShieldIcon, Languages,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// LEAMSS palette
const C = {
  teal: '#0F766E', tealDeep: '#115E59', tealWash: '#F0FDFA', tealWash2: '#CCFBF1',
  orange: '#EA7C2E', orangeDeep: '#C2410C', orangeWash: '#FFF7ED',
  gold: '#D4A017', goldWash: '#FEF3C7', goldLight: '#FBBF24',
  ink: '#1F2937', body: '#475569', muted: '#94A3B8',
  border: '#E5E7EB', card: '#FFFFFF',
};

// Country-specific region options (state/province)
const REGION_OPTIONS = {
  AU: ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'],
  CA: ['BC', 'ON', 'AB', 'SK', 'MB', 'NB', 'NS', 'PE', 'NL', 'YT', 'NT', 'QC'],
  NZ: ['Auckland', 'Wellington', 'Canterbury', 'Otago', 'Waikato', 'Bay of Plenty'],
};

const CAT_META = {
  french_language:        { icon: Languages,   label: 'French' },
  healthcare:             { icon: Stethoscope, label: 'Healthcare' },
  stem:                   { icon: Microscope,  label: 'STEM' },
  trade:                  { icon: Hammer,      label: 'Trade' },
  education:              { icon: BookOpen,    label: 'Education' },
  transport:              { icon: Plane,       label: 'Transport' },
  physicians_ca_exp:      { icon: Stethoscope, label: 'Physicians-CA' },
  senior_managers_ca_exp: { icon: Users,       label: 'Sr Mgr-CA' },
  researchers_ca_exp:     { icon: Microscope,  label: 'Researchers-CA' },
  military_recruits:      { icon: ShieldIcon,  label: 'Military' },
};

export default function AtlasAutoSuggestModal({
  open, onClose, country = 'CA', headers, onSelect,
}) {
  const [description, setDescription] = useState('');
  const [regionCode, setRegionCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    if (description.length < 15) {
      setError('Description should be at least 15 characters.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await axios.post(`${API}/sales/ai/atlas-auto-suggest`, {
        description,
        country_code: country,
        region_code: regionCode || null,
        max_suggestions: 5,
      }, { headers });
      setResult(r.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'AI call failed');
    }
    setLoading(false);
  };

  const handlePick = (s) => {
    if (onSelect) {
      onSelect({
        code: s.code,
        title: s.title,
        country_code: country,
        atlas: s.atlas,
      });
    }
    onClose();
  };

  const reset = () => {
    setDescription('');
    setRegionCode('');
    setResult(null);
    setError(null);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { reset(); onClose(); } }}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" data-testid="atlas-auto-suggest-modal">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>
            <Sparkles className="h-5 w-5" style={{ color: C.orange }} />
            AI Atlas Auto-Suggest
            <Badge style={{ background: C.orangeWash, color: C.orangeDeep, fontSize: 9, marginLeft: 8 }}>
              {country === 'AU' ? '🇦🇺 Australia' : country === 'CA' ? '🇨🇦 Canada' : '🇳🇿 New Zealand'}
            </Badge>
          </DialogTitle>
          <DialogDescription style={{ color: C.body }}>
            Describe the candidate&apos;s current job in plain English. AI will return the top occupation
            matches enriched with full Atlas data (eligibility, programs, cutoffs).
          </DialogDescription>
        </DialogHeader>

        {/* Input form */}
        <div className="space-y-3 mt-2">
          <div>
            <label className="text-[10px] uppercase font-bold tracking-wider block mb-1"
                   style={{ color: C.tealDeep, letterSpacing: '0.08em' }}>
              Candidate Description
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Backend software engineer at fintech, 8 years experience in Python distributed systems, wants to settle in Vancouver."
              rows={3}
              className="text-sm"
              data-testid="aas-description-input"
            />
            <p className="text-[10px] mt-1" style={{ color: C.muted }}>
              Minimum 15 characters. AI matches on duties — be specific about role + sector.
            </p>
          </div>

          <div>
            <label className="text-[10px] uppercase font-bold tracking-wider block mb-1"
                   style={{ color: C.tealDeep, letterSpacing: '0.08em' }}>
              <MapPin className="h-3 w-3 inline mr-1" />Destination Region (optional)
            </label>
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setRegionCode('')}
                className="text-xs px-2 py-1 rounded transition-colors"
                style={{
                  background: !regionCode ? C.teal : C.card,
                  color: !regionCode ? '#fff' : C.body,
                  border: `1px solid ${!regionCode ? C.teal : C.border}`,
                }}
                data-testid="aas-region-any"
              >Any</button>
              {(REGION_OPTIONS[country] || []).map(r => (
                <button
                  key={r}
                  onClick={() => setRegionCode(r)}
                  className="text-xs px-2 py-1 rounded transition-colors"
                  style={{
                    background: regionCode === r ? C.teal : C.card,
                    color: regionCode === r ? '#fff' : C.body,
                    border: `1px solid ${regionCode === r ? C.teal : C.border}`,
                  }}
                  data-testid={`aas-region-${r}`}
                >{r}</button>
              ))}
            </div>
          </div>

          <Button
            onClick={handleSearch}
            disabled={loading || description.length < 15}
            style={{ background: C.orange, color: '#fff' }}
            className="w-full"
            data-testid="aas-search-btn"
          >
            {loading
              ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Analysing with AI (Haiku 4.5)…</>
              : <><Sparkles className="h-4 w-4 mr-2" />Get AI Suggestions</>}
          </Button>

          {error && (
            <div className="rounded p-2 text-sm" style={{ background: '#FEE2E2', color: '#991B1B' }}>
              {error}
            </div>
          )}
        </div>

        {/* Results */}
        {result && result.suggestions && (
          <div className="mt-4 space-y-3" data-testid="aas-results">
            {result.tip && (
              <div className="rounded-lg p-3 border" style={{ background: C.goldWash, borderColor: C.goldLight }}>
                <p className="text-[10px] uppercase font-bold mb-0.5" style={{ color: C.orangeDeep, letterSpacing: '0.08em' }}>
                  Sales Tip
                </p>
                <p className="text-sm" style={{ color: C.ink }}>{result.tip}</p>
              </div>
            )}

            {result.suggestions.length === 0 && (
              <div className="rounded-lg p-4 text-center" style={{ background: C.tealWash, border: `1px dashed ${C.tealWash2}` }}>
                <p className="text-sm" style={{ color: C.body }}>
                  AI couldn&apos;t match this description. Try refining with more specific job duties.
                </p>
              </div>
            )}

            {/* Phase 10.8 — Compare All button (2+ suggestions) */}
            {result.suggestions.length >= 2 && (
              <div className="rounded-lg p-3 flex items-center justify-between gap-2"
                   style={{ background: C.tealWash, border: `1px dashed ${C.teal}` }}>
                <p className="text-xs" style={{ color: C.body }}>
                  <strong style={{ color: C.tealDeep }}>Compare these {Math.min(result.suggestions.length, 5)} suggestions side-by-side</strong> —
                  rich table with TEER/skill, EE/PNPs/Quebec, cutoffs, best-fit auto-highlighted.
                </p>
                <Button
                  size="sm"
                  onClick={() => {
                    const ids = result.suggestions.slice(0, 5).map(s => `${country}:${s.code}`);
                    sessionStorage.setItem('compare_ids', JSON.stringify(ids));
                    window.open('/sales/occupations/compare', '_blank');
                  }}
                  style={{ background: C.teal, color: '#fff', fontSize: 11 }}
                  data-testid="aas-compare-all-btn"
                >
                  <Sparkles className="h-3 w-3 mr-1" />Compare All
                </Button>
              </div>
            )}

            {result.suggestions.map((s, idx) => (
              <SuggestionCard
                key={`${s.code}-${idx}`}
                s={s}
                country={country}
                regionCode={regionCode}
                onPick={() => handlePick(s)}
              />
            ))}

            <p className="text-[10px] text-center italic" style={{ color: C.muted }}>
              {result._total_candidates_considered} candidates considered · Model: {result._ai_model}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}


/**
 * One suggestion card — renders country-specific Atlas data.
 */
function SuggestionCard({ s, country, regionCode, onPick }) {
  const a = s.atlas || {};
  const confColor = s.confidence === 'high' ? C.teal : s.confidence === 'medium' ? C.gold : C.muted;
  const confLabel = s.confidence?.toUpperCase() || '—';

  return (
    <Card className="p-3" style={{ borderLeftWidth: 4, borderLeftColor: confColor }} data-testid={`aas-card-${s.code}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-bold" style={{ color: C.tealDeep, fontFamily: "'Playfair Display', serif" }}>
              {country === 'CA' ? 'NOC' : 'ANZSCO'} {s.code}
            </span>
            <Badge style={{ background: confColor, color: '#fff', fontSize: 9 }}>{confLabel}</Badge>
            {s.destination_region_match && regionCode && (
              <Badge style={{ background: C.tealWash2, color: C.tealDeep, fontSize: 9 }}>
                <MapPin className="h-2.5 w-2.5 mr-0.5" />{regionCode} match
              </Badge>
            )}
          </div>
          <p className="text-sm font-bold mt-0.5" style={{ color: C.ink }}>{s.title}</p>
          <p className="text-xs italic mt-1" style={{ color: C.body }}>{s.reasoning}</p>
        </div>
        <Button size="sm" onClick={onPick}
                style={{ background: C.tealDeep, color: '#fff', fontSize: 11 }}
                data-testid={`aas-pick-${s.code}`}>
          <CheckCircle2 className="h-3 w-3 mr-1" />Pick this
        </Button>
      </div>

      {/* Country-specific atlas data */}
      <div className="mt-2 pt-2 border-t grid grid-cols-1 md:grid-cols-2 gap-2" style={{ borderColor: C.border }}>
        {/* CA */}
        {country === 'CA' && (
          <>
            <AtlasMicroBlock label="TEER" value={`${a.teer_category} · ${a.teer_label || '—'}`} icon={Award} />
            <AtlasMicroBlock label="Federal Programs"
              value={['FSWP', 'CEC', 'FSTP'].filter(p => a.ee_eligibility?.[`${p.toLowerCase()}_eligible`]).join(' · ') || 'None'}
              icon={ShieldCheck} />
            {/* Categories */}
            {(a.ee_eligibility?.categories || []).length > 0 && (
              <div className="md:col-span-2 flex flex-wrap gap-1 mt-1">
                {a.ee_eligibility.categories.map(cid => {
                  const m = CAT_META[cid];
                  if (!m) return null;
                  const Icon = m.icon;
                  return (
                    <span key={cid} className="text-[10px] px-1.5 py-0.5 rounded flex items-center gap-0.5"
                          style={{ background: C.tealWash2, color: C.tealDeep }}>
                      <Icon className="h-2.5 w-2.5" />{m.label}
                    </span>
                  );
                })}
              </div>
            )}
            {/* PNPs */}
            {(a.pnp_eligibility || []).length > 0 && (
              <div className="md:col-span-2">
                <p className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.06em' }}>
                  Provincial Nominee Programs
                </p>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {a.pnp_eligibility.slice(0, 8).map(p => (
                    <span key={p.pnp_id} className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold"
                          style={{
                            background: regionCode && p.province_code === regionCode ? C.gold : C.tealWash,
                            color: regionCode && p.province_code === regionCode ? '#fff' : C.tealDeep,
                          }}>
                      {p.province_code}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {/* IRCC Round Cutoffs */}
            {a.ircc_round_cutoffs?.cutoffs_by_category && Object.keys(a.ircc_round_cutoffs.cutoffs_by_category).length > 0 && (
              <div className="md:col-span-2">
                <p className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.06em' }}>
                  Latest CRS Cutoffs
                </p>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {Object.entries(a.ircc_round_cutoffs.cutoffs_by_category).slice(0, 5).map(([cid, cv]) => (
                    <span key={cid} className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{ background: C.goldWash, color: C.orangeDeep }}>
                      {cid}: {cv.latest_crs_min || '—'}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {/* Regional Pilots (AIP/RCIP/FCIP) */}
            {(a.regional_pilot_eligibility || []).length > 0 && (
              <div className="md:col-span-2">
                <p className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.06em' }}>
                  Regional Pilots
                </p>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {a.regional_pilot_eligibility.slice(0, 6).map((p, i) => (
                    <span key={i} className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{ background: C.orangeWash, color: C.orangeDeep }}>
                      {p.pilot?.toUpperCase()}{p.community_name ? ` · ${p.community_name.split(',')[0]}` : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {/* Quebec */}
            {a.quebec_eligibility?.eligible && (
              <div className="md:col-span-2">
                <p className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.06em' }}>
                  🇫🇷 Quebec PSTQ (FEER {a.quebec_eligibility.feer_category})
                </p>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {(a.quebec_eligibility.sections || []).map(sec => (
                    <span key={sec.section_id} className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{
                            background: sec.priority ? C.gold : C.goldWash,
                            color: sec.priority ? '#fff' : C.orangeDeep,
                          }}>
                      {sec.priority ? '⭐ ' : ''}{sec.section_id.toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* AU */}
        {country === 'AU' && (
          <>
            <AtlasMicroBlock label="Skill Level" value={`Level ${a.skill_level_or_teer ?? '—'}`} icon={Award} />
            <AtlasMicroBlock label="Skill Body" value={a.assessing_authority?.name || '—'} icon={ShieldCheck} />
            <AtlasMicroBlock label="SkillSelect Tier" value={a.skillselect_tier?.label || '—'} icon={TrendingUp} />
            {(a.visa_pathways || []).length > 0 && (
              <div className="md:col-span-2 flex flex-wrap gap-1">
                {a.visa_pathways.slice(0, 6).map((v, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                        style={{ background: C.tealWash2, color: C.tealDeep }}>
                    {typeof v === 'string' ? v : v?.code || JSON.stringify(v).slice(0, 30)}
                  </span>
                ))}
              </div>
            )}
            {a.state_nomination && Object.keys(a.state_nomination).length > 0 && (
              <div className="md:col-span-2">
                <p className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.06em' }}>
                  State Nominations
                </p>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {Object.keys(a.state_nomination).filter(k => a.state_nomination[k]).slice(0, 8).map(st => (
                    <span key={st} className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold"
                          style={{
                            background: regionCode === st ? C.gold : C.tealWash,
                            color: regionCode === st ? '#fff' : C.tealDeep,
                          }}>
                      {st}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* NZ */}
        {country === 'NZ' && (
          <>
            <AtlasMicroBlock label="Skill Level" value={`Level ${a.skill_level_or_teer ?? '—'}`} icon={Award} />
            <AtlasMicroBlock label="Visa Pathways" value={(a.visa_pathways || []).length + ' available'} icon={Globe} />
          </>
        )}
      </div>
    </Card>
  );
}

function AtlasMicroBlock({ label, value, icon: Icon }) {
  return (
    <div className="text-xs">
      <span className="text-[9px] uppercase font-bold flex items-center gap-1"
            style={{ color: C.muted, letterSpacing: '0.06em' }}>
        <Icon className="h-3 w-3" />{label}
      </span>
      <p className="font-semibold" style={{ color: C.ink }}>{value}</p>
    </div>
  );
}
