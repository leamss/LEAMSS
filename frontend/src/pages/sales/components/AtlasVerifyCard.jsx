/**
 * Phase 9.2 — Atlas Verify Card
 *
 * Compact card that surfaces all Migration Atlas enrichment data for a single
 * 6-digit ANZSCO occupation. Triggered from the Smart Sales Helper wizard
 * (Step 3 — Profile) so sales can show clients live, official-source-backed
 * data right at the moment of occupation selection.
 *
 * Data fetched: /api/anz-intel/verify/{code}
 * Sources: Home Affairs + jobsandskills.gov.au + state nomination sites + VETASSESS
 */
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Loader2, Award, CheckCircle2, XCircle, MapPin, Building2,
  ShieldCheck, FileDown, ExternalLink, X, Target, Factory, Briefcase,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// LEAMSS brand-aligned palette (no blue/indigo)
const C = {
  teal:     '#0F766E', tealDeep: '#115E59', tealWash: '#F0FDFA', tealWash2: '#CCFBF1',
  orange:   '#EA7C2E', orangeDeep: '#C2410C', orangeWash: '#FFF7ED', orangeWash2: '#FFEDD5',
  red:      '#D32F2F', redWash:   '#FEE2E2',
  gold:     '#D4A017', goldWash:  '#FEF3C7', goldLight: '#FBBF24',
  ink:      '#1F2937', body: '#475569', muted: '#94A3B8',
  border:   '#E5E7EB', borderSoft: '#F1F5F9', card: '#FFFFFF',
};

const TIER_TONE = {
  teal:   { bg: C.tealWash2,  fg: C.tealDeep,   bd: C.teal },
  gold:   { bg: C.goldWash,   fg: C.orangeDeep, bd: C.gold },
  orange: { bg: C.orangeWash, fg: C.orangeDeep, bd: C.orange },
};

const STATE_ORDER = ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'];

export default function AtlasVerifyCard({ code, headers, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!code || code.length !== 6) return;
    setLoading(true);
    setError(null);
    axios.get(`${API}/anz-intel/verify/${code}`, { headers })
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'Failed to fetch Atlas data'))
      .finally(() => setLoading(false));
  }, [code, headers]);

  if (!code) return null;

  if (loading) {
    return (
      <Card className="p-4 flex items-center gap-2" data-testid="atlas-verify-loading"
            style={{ background: C.tealWash, border: `1px solid ${C.tealWash2}` }}>
        <Loader2 className="h-4 w-4 animate-spin" style={{ color: C.teal }} />
        <span className="text-sm" style={{ color: C.tealDeep }}>Fetching from LEAMSS Migration Atlas…</span>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="p-4" data-testid="atlas-verify-error"
            style={{ background: C.orangeWash, border: `1px solid ${C.orangeWash2}` }}>
        <p className="text-sm font-bold" style={{ color: C.orangeDeep }}>Atlas data not available</p>
        <p className="text-xs mt-1" style={{ color: C.body }}>{error || 'Occupation not yet enriched in Atlas. Admin can scrape via Verification Hub.'}</p>
      </Card>
    );
  }

  const tier = data.skillselect_tier || {};
  const tierTone = TIER_TONE[tier.tone] || TIER_TONE.orange;
  const aa = data.assessing_authority || {};
  const vet = data.vetassess || {};
  const visas = data.visa_eligibility || [];
  const states = data.state_nomination_matrix || {};
  const isVerified = data.verification_status === 'verified';

  return (
    <Card data-testid="atlas-verify-card"
          className="overflow-hidden border-0 shadow-lg"
          style={{ background: C.card, border: `2px solid ${C.teal}` }}>
      {/* Header */}
      <div className="p-4 flex items-start justify-between"
           style={{ background: `linear-gradient(135deg, ${C.tealDeep} 0%, ${C.teal} 100%)`, color: '#fff' }}>
        <div className="flex-1">
          <p className="text-[10px] uppercase font-bold tracking-widest opacity-90"
             style={{ letterSpacing: '0.14em' }}>
            LEAMSS Migration Atlas · Verified Data
          </p>
          <h3 className="text-lg font-bold mt-0.5" style={{ fontFamily: "'Playfair Display', serif" }}>
            {data.title}
          </h3>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[11px] font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(255,255,255,0.18)' }}>
              ANZSCO {data.code}
            </span>
            {data.classification_dual_code?.['2022'] && (
              <span className="text-[10px] opacity-80">v2022: {data.classification_dual_code['2022']}</span>
            )}
            {isVerified ? (
              <Badge style={{ background: C.gold, color: '#fff', fontSize: 9 }}>
                <ShieldCheck className="h-3 w-3 mr-1" />Admin Verified
              </Badge>
            ) : (
              <Badge style={{ background: 'rgba(255,255,255,0.18)', color: '#fff', fontSize: 9 }}>Draft</Badge>
            )}
          </div>
        </div>
        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose}
                  className="text-white hover:bg-white/20"
                  data-testid="atlas-verify-close">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* SkillSelect Tier hero */}
        <div className="rounded-lg p-3 flex items-center gap-3"
             style={{ background: tierTone.bg, border: `1px solid ${tierTone.bd}` }}
             data-testid="atlas-skillselect-tier">
          <div className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center"
               style={{ background: tierTone.bd, color: '#fff' }}>
            <Award className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <p className="text-[10px] uppercase font-bold tracking-wider opacity-70"
               style={{ color: tierTone.fg, letterSpacing: '0.1em' }}>
              SkillSelect Priority
            </p>
            <p className="text-base font-bold" style={{ color: tierTone.fg }}>
              {tier.label} · {tier.tag}
            </p>
            {tier.reason && (
              <p className="text-[10px] italic" style={{ color: tierTone.fg, opacity: 0.8 }}>
                Classification: {tier.reason.replace(/_/g, ' ')}
              </p>
            )}
          </div>
          {data.pathway_lists?.length > 0 && (
            <div className="flex flex-wrap gap-1 justify-end max-w-[40%]">
              {data.pathway_lists.map(p => (
                <Badge key={p} style={{ background: '#fff', color: tierTone.fg, border: `1px solid ${tierTone.bd}`, fontSize: 9 }}>
                  {p}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Assessing Authority + VETASSESS Group side-by-side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-lg p-3 border" style={{ background: C.tealWash, borderColor: C.tealWash2 }}
               data-testid="atlas-assessing-authority">
            <p className="text-[10px] uppercase font-bold tracking-wider flex items-center gap-1"
               style={{ color: C.tealDeep, letterSpacing: '0.1em' }}>
              <Building2 className="h-3 w-3" />Assessing Body
            </p>
            {aa.short_name || aa.name ? (
              <>
                <p className="text-sm font-bold mt-1" style={{ color: C.ink }}>
                  {aa.short_name || aa.full_name || aa.name}
                </p>
                {aa.name && aa.name !== aa.short_name && (
                  <p className="text-[11px]" style={{ color: C.body }}>{aa.full_name || aa.name}</p>
                )}
                {(aa.url || aa.website) && (
                  <a href={aa.url || aa.website} target="_blank" rel="noreferrer"
                     className="text-[11px] inline-flex items-center gap-1 mt-1 underline"
                     style={{ color: C.teal }}>
                    <ExternalLink className="h-3 w-3" />Visit official site
                  </a>
                )}
              </>
            ) : (
              <p className="text-xs italic mt-1" style={{ color: C.muted }}>Not yet mapped</p>
            )}
          </div>

          <div className="rounded-lg p-3 border" style={{ background: C.goldWash, borderColor: C.goldLight }}
               data-testid="atlas-vetassess">
            <p className="text-[10px] uppercase font-bold tracking-wider flex items-center gap-1"
               style={{ color: C.orangeDeep, letterSpacing: '0.1em' }}>
              <Award className="h-3 w-3" />VETASSESS Group
            </p>
            {vet.group ? (
              <>
                <p className="text-2xl font-bold mt-1 leading-none"
                   style={{ color: C.orangeDeep, fontFamily: "'Playfair Display', serif" }}>
                  Group {vet.group}
                </p>
                <p className="text-[10px] mt-1" style={{ color: C.body }}>
                  <strong>Quals:</strong> {vet.qualification_required || '—'}
                </p>
                <p className="text-[10px]" style={{ color: C.body }}>
                  <strong>Exp:</strong> {vet.experience_required || '—'}
                </p>
              </>
            ) : (
              <p className="text-xs italic mt-1" style={{ color: C.muted }}>Not VETASSESS-assessed (or not yet seeded)</p>
            )}
          </div>
        </div>

        {/* Visa pathways */}
        {visas.length > 0 && (
          <div className="rounded-lg border p-3" style={{ background: C.card, borderColor: C.border }}
               data-testid="atlas-visa-pathways">
            <p className="text-[10px] uppercase font-bold tracking-wider mb-2"
               style={{ color: C.tealDeep, letterSpacing: '0.1em' }}>
              Visa Subclass Eligibility (Home Affairs)
            </p>
            <div className="flex flex-wrap gap-1.5">
              {visas.map(v => (
                <div key={v.visa_subclass} className="flex items-center gap-1 px-2 py-1 rounded text-xs"
                     style={{
                       background: v.eligible ? C.tealWash2 : C.redWash,
                       color: v.eligible ? C.tealDeep : C.red,
                       border: `1px solid ${v.eligible ? C.teal : C.red}33`,
                     }}
                     title={v.notes}
                     data-testid={`atlas-visa-${v.visa_subclass}`}>
                  {v.eligible
                    ? <CheckCircle2 className="h-3 w-3" />
                    : <XCircle className="h-3 w-3" />}
                  <span className="font-bold">{v.visa_subclass}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* State nomination matrix */}
        {Object.keys(states).length > 0 && (
          <div className="rounded-lg border p-3" style={{ background: C.card, borderColor: C.border }}
               data-testid="atlas-state-matrix">
            <p className="text-[10px] uppercase font-bold tracking-wider mb-2 flex items-center gap-1"
               style={{ color: C.tealDeep, letterSpacing: '0.1em' }}>
              <MapPin className="h-3 w-3" />State / Territory Nomination
            </p>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}`, color: C.muted }}>
                  <th className="text-left py-1 font-semibold">State</th>
                  <th className="py-1 font-semibold">190</th>
                  <th className="py-1 font-semibold">491</th>
                  <th className="text-left py-1 font-semibold">Notes</th>
                </tr>
              </thead>
              <tbody>
                {STATE_ORDER.filter(st => states[st]).map(st => {
                  const m = states[st];
                  return (
                    <tr key={st} style={{ borderBottom: `1px solid ${C.borderSoft}` }} data-testid={`atlas-state-${st}`}>
                      <td className="py-1.5 font-mono font-bold" style={{ color: C.ink }}>{st}</td>
                      <td className="text-center">
                        {m.sc190
                          ? <CheckCircle2 className="h-4 w-4 inline" style={{ color: C.teal }} />
                          : <XCircle className="h-4 w-4 inline" style={{ color: C.muted }} />}
                      </td>
                      <td className="text-center">
                        {m.sc491
                          ? <CheckCircle2 className="h-4 w-4 inline" style={{ color: C.teal }} />
                          : <XCircle className="h-4 w-4 inline" style={{ color: C.muted }} />}
                      </td>
                      <td className="py-1.5 text-[10px]" style={{ color: C.body }}>
                        {m.demand && <Badge style={{ background: C.goldWash, color: C.orangeDeep, fontSize: 9 }}>{m.demand}</Badge>}
                        {m.caveats && <span className="ml-1 italic">{m.caveats.slice(0, 40)}</span>}
                        {m.unit_group_match && (
                          <span className="ml-1 opacity-60">via {m.unit_group_match}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Phase 9.5 — Min Invitation Points */}
        {data.min_invitation_points && Object.keys(data.min_invitation_points).length > 0 && (
          <div className="rounded-lg border p-3" style={{ background: C.goldWash, borderColor: C.goldLight }}
               data-testid="atlas-min-invitation-points">
            <p className="text-[10px] uppercase font-bold tracking-wider mb-2 flex items-center gap-1"
               style={{ color: C.orangeDeep, letterSpacing: '0.1em' }}>
              <Target className="h-3 w-3" />SkillSelect Minimum Invitation Points
              <span className="ml-auto text-[9px] opacity-70 normal-case font-normal">
                As of {data.min_invitation_points.as_of_program_year}
              </span>
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center p-2 rounded" style={{ background: '#fff' }}>
                <p className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.08em' }}>Subclass 189</p>
                <p className="text-2xl font-bold leading-none mt-1" style={{ color: C.orangeDeep, fontFamily: "'Playfair Display', serif" }}>
                  {data.min_invitation_points['189'] || '—'}
                </p>
                <p className="text-[9px] mt-0.5" style={{ color: C.muted }}>points minimum</p>
              </div>
              <div className="text-center p-2 rounded" style={{ background: '#fff' }}>
                <p className="text-[10px] uppercase font-bold" style={{ color: C.muted, letterSpacing: '0.08em' }}>Subclass 491 (Family)</p>
                <p className="text-2xl font-bold leading-none mt-1" style={{ color: C.orangeDeep, fontFamily: "'Playfair Display', serif" }}>
                  {data.min_invitation_points['491_family'] || '—'}
                </p>
                <p className="text-[9px] mt-0.5" style={{ color: C.muted }}>points minimum</p>
              </div>
            </div>
            <p className="text-[9px] italic mt-2" style={{ color: C.body }}>
              State-nominated 491 has separate cutoffs (see State Nomination above).
            </p>
          </div>
        )}

        {/* Phase 9.5 — DAMA eligibility */}
        {data.dama_eligibility && data.dama_eligibility.length > 0 && (
          <div className="rounded-lg border p-3" style={{ background: C.tealWash, borderColor: C.tealWash2 }}
               data-testid="atlas-dama-eligibility">
            <p className="text-[10px] uppercase font-bold tracking-wider mb-2 flex items-center gap-1"
               style={{ color: C.tealDeep, letterSpacing: '0.1em' }}>
              <MapPin className="h-3 w-3" />DAMA — Designated Area Migration Agreements
              <span className="ml-auto text-[9px] opacity-70 normal-case font-normal">{data.dama_eligibility.length} match</span>
            </p>
            <div className="space-y-1.5">
              {data.dama_eligibility.slice(0, 4).map((dama, i) => (
                <div key={i} className="p-2 rounded text-xs flex items-start gap-2"
                     style={{ background: '#fff', border: `1px solid ${C.tealWash2}` }}
                     data-testid={`atlas-dama-${dama.id || i}`}>
                  <Badge style={{ background: C.teal, color: '#fff', fontSize: 9 }}>{dama.state}</Badge>
                  <div className="flex-1">
                    <p className="font-bold" style={{ color: C.ink }}>{dama.region}</p>
                    <p className="text-[10px]" style={{ color: C.muted }}>Valid until {dama.valid_until}</p>
                    {dama.concessions && dama.concessions.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {dama.concessions.slice(0, 3).map((c, j) => (
                          <span key={j} className="text-[9px] px-1.5 py-0.5 rounded"
                                style={{ background: C.tealWash2, color: C.tealDeep }}>{c}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {data.dama_eligibility.length > 4 && (
                <p className="text-[10px] italic text-center" style={{ color: C.muted }}>
                  +{data.dama_eligibility.length - 4} more DAMAs available
                </p>
              )}
            </div>
          </div>
        )}

        {/* Phase 9.5 — ILA eligibility */}
        {data.ila_eligibility && data.ila_eligibility.length > 0 && (
          <div className="rounded-lg border p-3" style={{ background: C.orangeWash, borderColor: C.orangeWash2 }}
               data-testid="atlas-ila-eligibility">
            <p className="text-[10px] uppercase font-bold tracking-wider mb-2 flex items-center gap-1"
               style={{ color: C.orangeDeep, letterSpacing: '0.1em' }}>
              <Factory className="h-3 w-3" />ILA — Industry Labour Agreements
            </p>
            <div className="space-y-1.5">
              {data.ila_eligibility.map((ila, i) => (
                <div key={i} className="p-2 rounded text-xs flex items-start gap-2"
                     style={{ background: '#fff', border: `1px solid ${C.orangeWash2}` }}
                     data-testid={`atlas-ila-${ila.id || i}`}>
                  <Briefcase className="h-3.5 w-3.5 mt-0.5" style={{ color: C.orange }} />
                  <div className="flex-1">
                    <p className="font-bold" style={{ color: C.ink }}>{ila.industry}</p>
                    <div className="mt-0.5 flex flex-wrap gap-1 items-center">
                      <span className="text-[9px]" style={{ color: C.muted }}>Visa:</span>
                      {(ila.visa_subclasses || []).map(v => (
                        <Badge key={v} style={{ background: C.orange, color: '#fff', fontSize: 9 }}>{v}</Badge>
                      ))}
                    </div>
                    {ila.concessions && ila.concessions.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {ila.concessions.slice(0, 3).map((c, j) => (
                          <span key={j} className="text-[9px] px-1.5 py-0.5 rounded"
                                style={{ background: C.orangeWash2, color: C.orangeDeep }}>{c}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer — actions */}
        <div className="flex items-center gap-2 flex-wrap pt-2 border-t" style={{ borderColor: C.borderSoft }}>
          <a href={`${API}/anz-intel/occupation/${data.code}/infosheet.pdf`}
             target="_blank" rel="noreferrer"
             className="px-3 py-1.5 rounded-md text-xs font-bold flex items-center gap-1.5"
             style={{ background: C.teal, color: '#fff' }}
             data-testid="atlas-download-infosheet">
            <FileDown className="h-3.5 w-3.5" />Download 4-Page Infosheet PDF
          </a>
          <a href={`/admin/anz-intel/audit`} target="_blank" rel="noreferrer"
             className="px-3 py-1.5 rounded-md text-xs font-bold border flex items-center gap-1.5"
             style={{ background: C.card, color: C.teal, borderColor: C.teal }}
             data-testid="atlas-open-dashboard">
            <ExternalLink className="h-3.5 w-3.5" />Open Atlas Dashboard
          </a>
          <p className="text-[10px] ml-auto" style={{ color: C.muted }}>
            Sources: immi.homeaffairs.gov.au · jobsandskills.gov.au · state migration sites
          </p>
        </div>
      </div>
    </Card>
  );
}
