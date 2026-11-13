import React from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  Globe2, ExternalLink, TrendingUp, DollarSign, MapPin, Sparkles, CheckCircle2,
  AlertCircle, ShieldCheck, Flag, Compass, BarChart3, Search,
} from 'lucide-react';

const AU_STATES = [
  { code: 'NSW', name: 'New South Wales' },
  { code: 'VIC', name: 'Victoria' },
  { code: 'WA', name: 'Western Australia' },
  { code: 'QLD', name: 'Queensland' },
  { code: 'SA', name: 'South Australia' },
  { code: 'TAS', name: 'Tasmania' },
  { code: 'ACT', name: 'Canberra (ACT)' },
  { code: 'NT', name: 'Northern Territory' },
];

export default function PublicAtlasEditorTab({ edit, setEdit, item }) {
  const country = (item.country_code || 'AU').toUpperCase();
  const publicUrl = `/atlas/${country.toLowerCase()}/${item.code}`;

  // Helper updaters
  const upMinPoints = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      min_invitation_points: {
        ...(prev.min_invitation_points || {}),
        [k]: v,
      },
    }));
  };

  const upState = (stCode, field, val) => {
    setEdit((prev) => {
      const ste = { ...(prev.state_territory_eligibility || {}) };
      ste[stCode] = { ...(ste[stCode] || {}), [field]: val };
      return { ...prev, state_territory_eligibility: ste };
    });
  };

  const upAnzscoProfile = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      anzsco_profile: {
        ...(prev.anzsco_profile || {}),
        [k]: v,
      },
      abs_data: {
        ...(prev.abs_data || {}),
        [k === 'median_salary_aud' ? 'median_ft_annual_aud' : k]: v,
      },
    }));
  };

  const upJsaData = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      jsa_data: {
        ...(prev.jsa_data || {}),
        [k]: v,
      },
    }));
  };

  const upEe = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      ee_eligibility: {
        ...(prev.ee_eligibility || {}),
        [k]: v,
      },
    }));
  };

  const toggleEeCategory = (catId) => {
    setEdit((prev) => {
      const current = prev.ee_eligibility?.categories || [];
      const exists = current.includes(catId);
      const updated = exists ? current.filter((c) => c !== catId) : [...current, catId];
      return {
        ...prev,
        ee_eligibility: {
          ...(prev.ee_eligibility || {}),
          categories: updated,
        },
      };
    });
  };

  const upNz = (field, val) => {
    setEdit((prev) => ({
      ...prev,
      aewv_eligibility: {
        ...(prev.aewv_eligibility || {}),
        [field]: val,
      },
    }));
  };

  const upSmc = (field, val) => {
    setEdit((prev) => ({
      ...prev,
      smc_points_breakdown: {
        ...(prev.smc_points_breakdown || {}),
        [field]: val,
      },
    }));
  };

  const upSeo = (field, val) => {
    setEdit((prev) => ({
      ...prev,
      seo_meta: {
        ...(prev.seo_meta || {}),
        [field]: val,
      },
    }));
  };

  const minPts = edit.min_invitation_points || {};
  const anzscoProf = edit.anzsco_profile || {};
  const absD = edit.abs_data || {};
  const jsaD = edit.jsa_data || {};
  const ste = edit.state_territory_eligibility || {};
  const ee = edit.ee_eligibility || {};
  const aewv = edit.aewv_eligibility || {};
  const smc = edit.smc_points_breakdown || {};
  const seo = edit.seo_meta || {};

  return (
    <div className="space-y-4 pt-1" data-testid="public-atlas-editor-tab">
      {/* ── Public URL & Live Preview Banner ── */}
      <div className="rounded-xl border border-teal-300 bg-gradient-to-r from-teal-50 via-emerald-50 to-white p-3.5 flex items-center justify-between flex-wrap gap-2.5 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-teal-600 text-white flex items-center justify-center shadow-sm shrink-0">
            <Globe2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold text-teal-950">Public Atlas Money Page</span>
              <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-mono">
                {country} · {item.code}
              </Badge>
              <Badge className="bg-white text-slate-700 border-slate-300 text-[10px]">
                Live Route: <code className="font-mono text-teal-800 ml-1">{publicUrl}</code>
              </Badge>
            </div>
            <p className="text-[11px] text-teal-800 mt-0.5">
              All information configured in this tab directly controls the client-facing public guide, SEO metadata, scorecard cutoffs, and state radars.
            </p>
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={() => window.open(publicUrl, '_blank')}
          className="bg-teal-700 hover:bg-teal-800 text-white font-semibold text-xs shadow-sm h-8"
        >
          <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
          Open Live Public Page ↗
        </Button>
      </div>

      {/* ── SECTION 1: AUSTRALIA CHANCES & INVITATION SCORECARD ── */}
      {country === 'AU' && (
        <Card className="p-4 border-slate-200 bg-white space-y-3">
          <div className="flex items-center justify-between border-b pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-teal-600" />
              Chances of Invitation Scorecard (DHA SkillSelect Cutoffs)
            </h4>
            <span className="text-[10px] text-slate-500 font-mono">Subclasses 189, 190, 491</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
            <div>
              <Label className="text-[11px] font-semibold text-slate-600">Subclass 189 Pass Mark (Points)</Label>
              <Input
                type="number"
                placeholder="e.g. 75 or 85"
                value={minPts.subclass_189 ?? ''}
                onChange={(e) => upMinPoints('subclass_189', e.target.value)}
                className="h-8 text-xs font-mono font-bold text-teal-900 bg-teal-50/40 border-teal-200 mt-1"
              />
              <span className="text-[10px] text-slate-400">Leave blank if ineligible for 189</span>
            </div>

            <div>
              <Label className="text-[11px] font-semibold text-slate-600">Subclass 190 Pass Mark (Points)</Label>
              <Input
                type="number"
                placeholder="e.g. 70"
                value={minPts.subclass_190 ?? ''}
                onChange={(e) => upMinPoints('subclass_190', e.target.value)}
                className="h-8 text-xs font-mono font-bold text-teal-900 bg-teal-50/40 border-teal-200 mt-1"
              />
              <span className="text-[10px] text-slate-400">State-nominated PR benchmark</span>
            </div>

            <div>
              <Label className="text-[11px] font-semibold text-slate-600">Subclass 491 Pass Mark (Points)</Label>
              <Input
                type="number"
                placeholder="e.g. 65"
                value={minPts.subclass_491 ?? ''}
                onChange={(e) => upMinPoints('subclass_491', e.target.value)}
                className="h-8 text-xs font-mono font-bold text-teal-900 bg-teal-50/40 border-teal-200 mt-1"
              />
              <span className="text-[10px] text-slate-400">Regional provisional benchmark</span>
            </div>

            <div>
              <Label className="text-[11px] font-semibold text-slate-600">Pathway Skilled List</Label>
              <Select
                value={edit.pathway_list || 'MLTSSL'}
                onValueChange={(v) => setEdit({ ...edit, pathway_list: v })}
              >
                <SelectTrigger className="h-8 text-xs font-bold text-slate-800 mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MLTSSL">MLTSSL (Medium &amp; Long-term)</SelectItem>
                  <SelectItem value="STSOL">STSOL (Short-term)</SelectItem>
                  <SelectItem value="ROL">ROL (Regional List)</SelectItem>
                  <SelectItem value="MLTSSL / STSOL">MLTSSL / STSOL Dual</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-[10px] text-slate-400">Controls 189 direct PR eligibility</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
            <div>
              <Label className="text-[11px] font-semibold text-slate-600">Program Year / Snapshot Date</Label>
              <Input
                value={minPts.as_of_program_year || '2025-26'}
                onChange={(e) => upMinPoints('as_of_program_year', e.target.value)}
                placeholder="e.g. 2025-26 Home Affairs Round"
                className="h-8 text-xs mt-1"
              />
            </div>
            <div>
              <Label className="text-[11px] font-semibold text-slate-600">Scorecard Public Notes / Explanatory Text</Label>
              <Input
                value={minPts.notes || ''}
                onChange={(e) => upMinPoints('notes', e.target.value)}
                placeholder="e.g. Estimated competitive cutoff for offshore applicants under current quota."
                className="h-8 text-xs mt-1"
              />
            </div>
          </div>
        </Card>
      )}

      {/* ── SECTION 2: 8-STATE AUSTRALIAN NOMINATION RADAR ── */}
      {country === 'AU' && (
        <Card className="p-4 border-slate-200 bg-white space-y-3">
          <div className="flex items-center justify-between border-b pb-2 flex-wrap gap-2">
            <div>
              <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <Compass className="w-4 h-4 text-emerald-600" />
                8-State Australian Nomination Radar
              </h4>
              <p className="text-[10px] text-slate-500">Configure state status, eligible visa subclasses, and priority badge across all 8 states.</p>
            </div>
            <span className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-medium">
              Powers Public Radar Grid
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {AU_STATES.map((st) => {
              const s = ste[st.code] || {};
              const stStatus = s.status || (s.rating === 'S' ? 'open' : s.rating === 'R' ? 'conditional' : s.eligible_190 !== false ? 'open' : 'conditional');
              const stSubclass = s.subclass || (s.eligible_190 && s.eligible_491 ? '190 & 491' : s.eligible_190 ? '190 Nominated' : '491 Regional');
              const stBadge = s.badge || (stStatus === 'open' ? 'Priority Open' : stStatus === 'conditional' ? '491 Regional Only' : 'Closed / Restricted');

              return (
                <div key={st.code} className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/70 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-slate-900">{st.code} — {st.name}</span>
                    <span className={`w-2 h-2 rounded-full ${stStatus === 'open' ? 'bg-emerald-500' : stStatus === 'conditional' ? 'bg-amber-500' : 'bg-rose-500'}`} />
                  </div>

                  <div>
                    <Label className="text-[10px] text-slate-500">Jurisdiction Status</Label>
                    <Select value={stStatus} onValueChange={(v) => upState(st.code, 'status', v)}>
                      <SelectTrigger className="h-7 text-xs bg-white mt-0.5"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open">🟢 Open (Active Quota)</SelectItem>
                        <SelectItem value="conditional">🟡 Conditional / Regional</SelectItem>
                        <SelectItem value="closed">🔴 Closed / Restricted</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-[10px] text-slate-500">Public Badge Label</Label>
                    <Input
                      value={stBadge}
                      onChange={(e) => upState(st.code, 'badge', e.target.value)}
                      placeholder="e.g. Priority Open"
                      className="h-7 text-xs bg-white mt-0.5"
                    />
                  </div>

                  <div>
                    <Label className="text-[10px] text-slate-500">Eligible Subclasses</Label>
                    <Select value={stSubclass} onValueChange={(v) => upState(st.code, 'subclass', v)}>
                      <SelectTrigger className="h-7 text-xs bg-white mt-0.5"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="190 & 491">190 &amp; 491</SelectItem>
                        <SelectItem value="190 Nominated">190 Nominated</SelectItem>
                        <SelectItem value="491 Regional">491 Regional Only</SelectItem>
                        <SelectItem value="DAMA Concession">DAMA Concession</SelectItem>
                        <SelectItem value="Restricted">Restricted</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <label className="flex items-center gap-1.5 text-[11px] text-slate-700 cursor-pointer pt-0.5">
                    <input
                      type="checkbox"
                      checked={s.offshore ?? true}
                      onChange={(e) => upState(st.code, 'offshore', e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-emerald-500"
                    />
                    <span>Offshore Applicants Accepted</span>
                  </label>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* ── SECTION 3: SALARY, EARNINGS & 10-YEAR OUTLOOK (ABS / JSA) ── */}
      <Card className="p-4 border-slate-200 bg-white space-y-3">
        <div className="flex items-center justify-between border-b pb-2">
          <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <DollarSign className="w-4 h-4 text-amber-600" />
            Official Salary, Earnings &amp; 10-Year Workforce Outlook (ABS / JSA)
          </h4>
          <span className="text-[10px] text-slate-500 font-mono">Powers Public Salary &amp; Projections Card</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          <div>
            <Label className="text-[11px] font-semibold text-slate-600">Full-Time Median Annual Salary (AUD)</Label>
            <Input
              type="number"
              placeholder="e.g. 180000"
              value={anzscoProf.median_salary_aud || absD.median_ft_annual_aud || anzscoProf.median_annual_earnings_aud || ''}
              onChange={(e) => upAnzscoProfile('median_salary_aud', e.target.value)}
              className="h-8 text-xs font-mono font-bold text-amber-900 bg-amber-50/40 border-amber-200 mt-1"
            />
            <span className="text-[10px] text-slate-400">Displayed in hero &amp; salary overview</span>
          </div>

          <div>
            <Label className="text-[11px] font-semibold text-slate-600">Full-Time Weekly Earnings (AUD)</Label>
            <Input
              type="number"
              placeholder="e.g. 3460"
              value={absD.median_ft_weekly_earnings_aud || anzscoProf.median_weekly_earnings_aud || ''}
              onChange={(e) => upAnzscoProfile('median_weekly_earnings_aud', e.target.value)}
              className="h-8 text-xs font-mono mt-1"
            />
          </div>

          <div>
            <Label className="text-[11px] font-semibold text-slate-600">Current Workforce Size (Workers 2025)</Label>
            <Input
              type="number"
              placeholder="e.g. 42500"
              value={anzscoProf.workforce_size || jsaD.employment_2025 || anzscoProf.employed_count || ''}
              onChange={(e) => upAnzscoProfile('workforce_size', e.target.value)}
              className="h-8 text-xs font-mono mt-1"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
          <div>
            <Label className="text-[11px] font-semibold text-slate-600">10-Year Growth Outlook (Demand)</Label>
            <Select
              value={jsaD.future_growth || 'Strong'}
              onValueChange={(v) => upJsaData('future_growth', v)}
            >
              <SelectTrigger className="h-8 text-xs font-bold mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Very Strong">Very Strong Demand</SelectItem>
                <SelectItem value="Strong">Strong Demand</SelectItem>
                <SelectItem value="Moderate">Moderate Demand</SelectItem>
                <SelectItem value="Stable">Stable</SelectItem>
                <SelectItem value="Declining">Declining</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-[11px] font-semibold text-slate-600">Growth Rate % (2025 to 2035)</Label>
            <Input
              type="number"
              step="0.1"
              placeholder="e.g. 12.5"
              value={jsaD.growth_pct_2025_to_2035 ?? ''}
              onChange={(e) => upJsaData('growth_pct_2025_to_2035', e.target.value)}
              className="h-8 text-xs font-mono mt-1"
            />
          </div>

          <div>
            <Label className="text-[11px] font-semibold text-slate-600">Projected 2035 Workforce</Label>
            <Input
              type="number"
              placeholder="e.g. 47800"
              value={jsaD.projected_employment_2035 || ''}
              onChange={(e) => upJsaData('projected_employment_2035', e.target.value)}
              className="h-8 text-xs font-mono mt-1"
            />
          </div>
        </div>
      </Card>

      {/* ── SECTION 4: CANADA (CA) EXPRESS ENTRY & NOC 2021 ── */}
      <Card className="p-4 border-slate-200 bg-white space-y-3">
        <div className="flex items-center justify-between border-b pb-2">
          <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            🇨🇦 Canada Express Entry &amp; NOC TEER Classification
          </h4>
          <span className="text-[10px] text-slate-500 font-mono">Powers Canada Public Atlas Section</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
          <div>
            <Label className="text-[11px] font-semibold text-slate-600">NOC TEER Category (0–5)</Label>
            <Select
              value={edit.teer_category !== '' && edit.teer_category != null ? String(edit.teer_category) : '1'}
              onValueChange={(v) => setEdit({ ...edit, teer_category: v })}
            >
              <SelectTrigger className="h-8 text-xs font-bold mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="0">TEER 0 — Executive &amp; Senior Management</SelectItem>
                <SelectItem value="1">TEER 1 — University Degree (Bachelor+)</SelectItem>
                <SelectItem value="2">TEER 2 — College Diploma 2–3 yrs or Apprentice</SelectItem>
                <SelectItem value="3">TEER 3 — College Diploma &lt;2 yrs</SelectItem>
                <SelectItem value="4">TEER 4 — Secondary School Diploma</SelectItem>
                <SelectItem value="5">TEER 5 — No Formal Education Required</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2 pt-5">
            <label className="flex items-center gap-1.5 text-xs font-medium text-slate-800 cursor-pointer">
              <input
                type="checkbox"
                checked={ee.fswp_eligible !== false}
                onChange={(e) => upEe('fswp_eligible', e.target.checked)}
                className="rounded text-teal-600 focus:ring-teal-500"
              />
              <span>FSWP Eligible (Skilled Worker)</span>
            </label>
          </div>

          <div className="flex items-center gap-2 pt-5">
            <label className="flex items-center gap-1.5 text-xs font-medium text-slate-800 cursor-pointer">
              <input
                type="checkbox"
                checked={ee.cec_eligible !== false}
                onChange={(e) => upEe('cec_eligible', e.target.checked)}
                className="rounded text-teal-600 focus:ring-teal-500"
              />
              <span>CEC Eligible (Experience Class)</span>
            </label>
          </div>

          <div className="flex items-center gap-2 pt-5">
            <label className="flex items-center gap-1.5 text-xs font-medium text-slate-800 cursor-pointer">
              <input
                type="checkbox"
                checked={Boolean(ee.fstp_eligible)}
                onChange={(e) => upEe('fstp_eligible', e.target.checked)}
                className="rounded text-teal-600 focus:ring-teal-500"
              />
              <span>FSTP Eligible (Skilled Trades)</span>
            </label>
          </div>
        </div>

        <div>
          <Label className="text-[11px] font-semibold text-slate-600 block mb-1">
            Express Entry Category-Based Selections
          </Label>
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'stem', label: '💻 STEM Occupations' },
              { id: 'healthcare', label: '🩺 Healthcare' },
              { id: 'trades', label: '🔨 Trades' },
              { id: 'transport', label: '🚛 Transport' },
              { id: 'agri', label: '🌾 Agriculture & Agri-Food' },
              { id: 'french', label: '🇫🇷 French-Language Proficiency' },
            ].map((cat) => {
              const active = (ee.categories || []).includes(cat.id);
              return (
                <button
                  type="button"
                  key={cat.id}
                  onClick={() => toggleEeCategory(cat.id)}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                    active ? 'bg-amber-100 text-amber-900 border-amber-300 font-bold' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {active ? '✓ ' : '+ '} {cat.label}
                </button>
              );
            })}
          </div>
        </div>
      </Card>

      {/* ── SECTION 5: NEW ZEALAND (NZ) AEWV & GREEN LIST ── */}
      <Card className="p-4 border-slate-200 bg-white space-y-3">
        <div className="flex items-center justify-between border-b pb-2">
          <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            🇳🇿 New Zealand AEWV &amp; Green List Residence
          </h4>
          <span className="text-[10px] text-slate-500 font-mono">Powers NZ Public Atlas Section</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
          <div>
            <Label className="text-[11px] font-semibold text-slate-600">Green List Tier</Label>
            <Select
              value={edit.nz_green_list_tier !== '' && edit.nz_green_list_tier != null ? String(edit.nz_green_list_tier) : '0'}
              onValueChange={(v) => setEdit({ ...edit, nz_green_list_tier: v === '0' ? null : v })}
            >
              <SelectTrigger className="h-8 text-xs font-bold mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="0">Not on Green List</SelectItem>
                <SelectItem value="1">Tier 1 — Straight to Residence</SelectItem>
                <SelectItem value="2">Tier 2 — Work to Residence (2 yrs)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-[11px] font-semibold text-slate-600">AEWV Occupational Band</Label>
            <Input
              value={aewv.occupational_band || 'Level 1'}
              onChange={(e) => upNz('occupational_band', e.target.value)}
              placeholder="e.g. Level 1 or ANZSCO Level 1"
              className="h-8 text-xs mt-1"
            />
          </div>

          <div>
            <Label className="text-[11px] font-semibold text-slate-600">AEWV Max Stay (Years)</Label>
            <Input
              type="number"
              value={aewv.max_stay_years || '5'}
              onChange={(e) => upNz('max_stay_years', e.target.value)}
              placeholder="5"
              className="h-8 text-xs mt-1"
            />
          </div>

          <div className="flex items-center gap-2 pt-5">
            <label className="flex items-center gap-1.5 text-xs font-medium text-slate-800 cursor-pointer">
              <input
                type="checkbox"
                checked={smc.green_list_auto_pass !== false}
                onChange={(e) => upSmc('green_list_auto_pass', e.target.checked)}
                className="rounded text-teal-600 focus:ring-teal-500"
              />
              <span>SMC Green List Auto-Pass</span>
            </label>
          </div>
        </div>
      </Card>

      {/* ── SECTION 6: SEARCH ENGINE OPTIMIZATION (SEO METADATA) ── */}
      <Card className="p-4 border-slate-200 bg-white space-y-3">
        <div className="flex items-center justify-between border-b pb-2">
          <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <Search className="w-4 h-4 text-indigo-600" />
            SEO Title &amp; Public Meta Description Override
          </h4>
          <span className="text-[10px] text-slate-500 font-mono">Google Search &amp; Social Previews</span>
        </div>

        <div>
          <Label className="text-[11px] font-semibold text-slate-600">Custom SEO Page Title (optional override)</Label>
          <Input
            value={seo.meta_title || ''}
            onChange={(e) => upSeo('meta_title', e.target.value)}
            placeholder={`e.g. ${edit.title || item.title} (${item.code}) — Australia Migration Guide | LEAMSS`}
            className="h-8 text-xs mt-1"
          />
        </div>

        <div>
          <Label className="text-[11px] font-semibold text-slate-600">Custom Meta Description (optional override)</Label>
          <Textarea
            value={seo.meta_description || ''}
            onChange={(e) => upSeo('meta_description', e.target.value)}
            placeholder="e.g. Full evaluation guide for migrating to Australia as a Chief Executive (111111). Check 189/190 cutoff points, 8-state nomination radar, assessing body criteria and salary."
            className="text-xs min-h-[60px] mt-1"
          />
        </div>
      </Card>
    </div>
  );
}
