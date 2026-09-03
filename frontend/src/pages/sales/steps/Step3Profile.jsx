// Step 3 — Profile form + embedded AI helpers (occupation finder + resume upload)
import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Bot, Briefcase, Heart, Upload, Map, Sparkles, X, Database, Loader2 } from 'lucide-react';
import FieldWithLabel from '../lib/FieldWithLabel';
import SuggesterModal from '../lib/SuggesterModal';
import ResumeUploadModal from '../lib/ResumeUploadModal';
import ANZSCOPreviewCard from '../components/ANZSCOPreviewCard';
import AtlasVerifyCard from '../components/AtlasVerifyCard';
import AtlasAutoSuggestModal from '../components/AtlasAutoSuggestModal';
import { QUALIFICATIONS, MARITAL_OPTIONS, CONTRIBUTION_OPTIONS } from '../lib/constants';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Step3Profile({ data, update, setData, headers }) {
  const [showSuggester, setShowSuggester] = useState(false);
  const [showResumeUpload, setShowResumeUpload] = useState(false);
  const [showAtlas, setShowAtlas] = useState(false);
  const [showAutoSuggest, setShowAutoSuggest] = useState(false);
  const [suggesterPrefill, setSuggesterPrefill] = useState(null);

  // Auto-open the chosen helper on first visit
  useEffect(() => {
    if (data.approach === 'occupation_finder' && !data.occupation_code) setShowSuggester(true);
    if (data.approach === 'resume_upload' && !data.age) setShowResumeUpload(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isMarried = data.marital_status === 'married' || data.marital_status === 'de_facto';

  const handleAutoSuggestPick = (picked) => {
    update('occupation_code', picked.code);
    update('occupation_title', picked.title);
    if (picked.country_code) update('occupation_country', picked.country_code);
    toast.success(`Selected ${picked.code} · ${picked.title}`);
    setShowAtlas(true);  // auto-open Atlas Verify for the new pick
  };

  const mapOcc = (s) => ({
    country_code: s.country_code,
    code: s.code,
    title: s.title,
    assessing_body: s.assessing_body,
    pathway: s.pathway,
  });

  const handleSelectMultiple = (list) => {
    if (!list || !list.length) return;
    const [primary, ...rest] = list;
    update('occupation_country', primary.country_code);
    update('occupation_code', primary.code);
    update('occupation_title', primary.title);
    update('occupation_body', primary.assessing_body);
    update('occupation_pathway', primary.pathway);
    // Dedupe alternatives against the primary
    const primaryKey = `${primary.code}-${primary.country_code}`;
    const extras = rest
      .map(mapOcc)
      .filter(o => `${o.code}-${o.country_code}` !== primaryKey);
    update('additional_occupations', extras);
    setShowSuggester(false);
    setSuggesterPrefill(null);
    toast.success(extras.length
      ? `Primary ${primary.code} + ${extras.length} alternative${extras.length > 1 ? 's' : ''} added`
      : `Selected ${primary.code} ${primary.title}`);
    setShowAtlas(true);
  };

  const removeAdditional = (idx) => {
    update('additional_occupations', (data.additional_occupations || []).filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Briefcase className="h-5 w-5 text-indigo-600" />Capture Client Profile
      </h2>

      <div className="flex gap-2 flex-wrap">
        <Button variant="outline" size="sm" onClick={() => setShowSuggester(true)} data-testid="open-suggester">
          <Bot className="h-3.5 w-3.5 mr-1" />AI Occupation Helper
        </Button>
        <Button
          size="sm"
          onClick={() => setShowAutoSuggest(true)}
          data-testid="open-atlas-auto-suggest"
          style={{ background: '#EA7C2E', color: '#fff' }}
        >
          <Sparkles className="h-3.5 w-3.5 mr-1" />AI Atlas Auto-Suggest
        </Button>
        <Button variant="outline" size="sm" onClick={() => setShowResumeUpload(true)} data-testid="open-resume-upload">
          <Upload className="h-3.5 w-3.5 mr-1" />Upload Resume
        </Button>
      </div>

      {data.occupation_code && (
        <>
          <Card className="p-3 bg-emerald-50 border-l-4 border-l-emerald-500" data-testid="selected-occ-card">
            <p className="text-[10px] uppercase font-bold text-emerald-700">Selected Occupation</p>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <p className="text-sm font-bold">{data.occupation_code} · {data.occupation_title}</p>
                <p className="text-[10px] text-slate-500">{data.occupation_body} · {data.occupation_pathway}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowAtlas(s => !s)}
                  data-testid="verify-in-atlas-btn"
                  style={{ background: '#0F766E', color: '#fff', borderColor: '#0F766E' }}
                >
                  <Map className="h-3.5 w-3.5 mr-1" />
                  {showAtlas ? 'Hide Atlas' : 'Verify in Atlas'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => {
                  update('occupation_code', '');
                  update('occupation_title', '');
                  update('occupation_body', '');
                  update('occupation_pathway', '');
                  setShowAtlas(false);
                }}>Change</Button>
              </div>
            </div>
          </Card>

          {/* Phase 9.2 — Migration Atlas verified data drawer */}
          {showAtlas && (
            <AtlasVerifyCard
              code={data.occupation_code}
              country={data.occupation_country || 'AU'}
              headers={headers}
              onClose={() => setShowAtlas(false)}
            />
          )}

          {/* Phase 7.2 — Auto-populate ANZSCO 4-digit KB preview */}
          <ANZSCOPreviewCard
            code={data.occupation_code}
            occupationTitle={data.occupation_title}
            headers={headers}
          />
        </>
      )}

      {/* EOI Backlog — consultant preview + show/hide toggle (AU only) */}
      {data.occupation_code && (data.occupation_country || 'AU') === 'AU' && (
        <EOIBacklogCard
          code={data.occupation_code}
          headers={headers}
          show={!!data.show_eoi_backlog}
          onToggle={(v) => update('show_eoi_backlog', v)}
        />
      )}

      {(data.additional_occupations || []).length > 0 && (
        <Card className="p-3 bg-indigo-50 border-l-4 border-l-indigo-400" data-testid="additional-occ-card">
          <p className="text-[10px] uppercase font-bold text-indigo-700 mb-1.5">
            Alternative Occupations · shown side-by-side in the report
          </p>
          <div className="flex flex-wrap gap-2">
            {(data.additional_occupations || []).map((o, i) => (
              <div
                key={`${o.code}-${o.country_code}-${i}`}
                className="flex items-center gap-1.5 bg-white border rounded px-2 py-1 text-[11px]"
                data-testid={`additional-occ-${i}`}
              >
                <span className="font-bold">{o.code}</span>
                <span className="text-slate-500">· {o.title}</span>
                <span className="text-[9px] text-slate-400">({o.country_code})</span>
                <button
                  onClick={() => removeAdditional(i)}
                  className="ml-0.5 text-rose-500 hover:text-rose-700"
                  data-testid={`remove-additional-${i}`}
                  title="Remove"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Profile fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <FieldWithLabel label="Marital Status *">
          <Select value={data.marital_status} onValueChange={v => update('marital_status', v)}>
            <SelectTrigger data-testid="ca-marital"><SelectValue placeholder="Select…" /></SelectTrigger>
            <SelectContent>{MARITAL_OPTIONS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
          </Select>
        </FieldWithLabel>
        <FieldWithLabel label="Age *">
          <Input type="number" value={data.age} onChange={e => update('age', e.target.value)} placeholder="e.g., 32" data-testid="ca-age" />
        </FieldWithLabel>
        <FieldWithLabel label="Highest Qualification *">
          <Select value={data.qualification} onValueChange={v => update('qualification', v)}>
            <SelectTrigger data-testid="ca-qualification"><SelectValue placeholder="Select…" /></SelectTrigger>
            <SelectContent>{QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}</SelectContent>
          </Select>
        </FieldWithLabel>
        <FieldWithLabel label="Total Years Experience">
          <Input type="number" step="0.5" value={data.years_experience_total} onChange={e => update('years_experience_total', e.target.value)} data-testid="ca-exp-total" placeholder="6" />
        </FieldWithLabel>
      </div>

      <p className="text-[11px] uppercase font-bold text-slate-500 mt-3 mb-1">IELTS Scores (all 4 bands)</p>
      <div className="grid grid-cols-5 gap-2">
        <FieldWithLabel label="Overall"><Input type="number" step="0.5" value={data.ielts_overall} onChange={e => update('ielts_overall', e.target.value)} placeholder="7.5" data-testid="ca-ielts-overall" /></FieldWithLabel>
        <FieldWithLabel label="L"><Input type="number" step="0.5" value={data.ielts_listening} onChange={e => update('ielts_listening', e.target.value)} placeholder="7.5" data-testid="ca-ielts-listening" /></FieldWithLabel>
        <FieldWithLabel label="R"><Input type="number" step="0.5" value={data.ielts_reading} onChange={e => update('ielts_reading', e.target.value)} placeholder="7.0" data-testid="ca-ielts-reading" /></FieldWithLabel>
        <FieldWithLabel label="W"><Input type="number" step="0.5" value={data.ielts_writing} onChange={e => update('ielts_writing', e.target.value)} placeholder="7.0" data-testid="ca-ielts-writing" /></FieldWithLabel>
        <FieldWithLabel label="S"><Input type="number" step="0.5" value={data.ielts_speaking} onChange={e => update('ielts_speaking', e.target.value)} placeholder="7.5" data-testid="ca-ielts-speaking" /></FieldWithLabel>
      </div>

      {isMarried && (
        <Card className="p-3 bg-pink-50 border-l-4 border-l-pink-400 mt-3">
          <h3 className="text-sm font-bold text-pink-900 mb-2 flex items-center gap-1">
            <Heart className="h-3.5 w-3.5" />Spouse Configuration
          </h3>
          <div className="space-y-2">
            <FieldWithLabel label="Spouse will migrate?">
              <Select value={data.spouse_will_migrate} onValueChange={v => update('spouse_will_migrate', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="yes">Yes — migrating</SelectItem>
                  <SelectItem value="no">No — not migrating</SelectItem>
                </SelectContent>
              </Select>
            </FieldWithLabel>
            {data.spouse_will_migrate === 'yes' && (
              <FieldWithLabel label="Spouse contribution">
                <Select value={data.spouse_contribution} onValueChange={v => update('spouse_contribution', v)}>
                  <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                  <SelectContent>{CONTRIBUTION_OPTIONS.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}</SelectContent>
                </Select>
              </FieldWithLabel>
            )}
            {data.spouse_contribution && data.spouse_contribution !== 'non_contributing' && data.spouse_contribution !== 'australian_pr_citizen' && (
              <div className="grid grid-cols-3 gap-2">
                <FieldWithLabel label="Age"><Input type="number" value={data.spouse_age} onChange={e => update('spouse_age', e.target.value)} placeholder="30" /></FieldWithLabel>
                <FieldWithLabel label="Edu">
                  <Select value={data.spouse_qualification} onValueChange={v => update('spouse_qualification', v)}>
                    <SelectTrigger><SelectValue placeholder="…" /></SelectTrigger>
                    <SelectContent>{QUALIFICATIONS.map(q => <SelectItem key={q.v} value={q.v}>{q.l}</SelectItem>)}</SelectContent>
                  </Select>
                </FieldWithLabel>
                <FieldWithLabel label="IELTS"><Input type="number" step="0.5" value={data.spouse_ielts_overall} onChange={e => update('spouse_ielts_overall', e.target.value)} placeholder="6.5" /></FieldWithLabel>
              </div>
            )}
          </div>
        </Card>
      )}

      {showSuggester && (
        <SuggesterModal
          initialDescription={suggesterPrefill?.description || ''}
          initialCountry={suggesterPrefill?.country || 'AU'}
          autoRun={Boolean(suggesterPrefill)}
          onClose={() => { setShowSuggester(false); setSuggesterPrefill(null); }}
          onSelectMultiple={handleSelectMultiple}
          onSelect={(s) => handleSelectMultiple([s])}
          headers={headers}
        />
      )}

      {showResumeUpload && (
        <ResumeUploadModal
          onClose={() => setShowResumeUpload(false)}
          onExtracted={(extracted) => {
            const p = extracted.primary_applicant || {};
            const per = p.personal || {};
            const ed = p.education || {};
            const pf = p.professional || {};
            const lg = (p.language || {}).scores || {};
            // 1) Fetch client details + profile fields from the resume
            setData(d => ({
              ...d,
              client_name: extracted.name || per.full_name || d.client_name,
              client_email: extracted.email || d.client_email,
              client_phone: extracted.phone || d.client_phone,
              age: per.age || d.age,
              qualification: ed.highest_qualification || d.qualification,
              years_experience_total: pf.years_experience_total || d.years_experience_total,
              ielts_overall: lg.overall || d.ielts_overall,
              ielts_listening: lg.listening || d.ielts_listening,
              ielts_reading: lg.reading || d.ielts_reading,
              ielts_writing: lg.writing || d.ielts_writing,
              ielts_speaking: lg.speaking || d.ielts_speaking,
              marital_status: extracted.marital_status || d.marital_status,
            }));
            setShowResumeUpload(false);

            // 2) Build a rich job description from the resume → auto-suggest the RIGHT occupation code
            const parts = [];
            if (pf.current_profession) parts.push(pf.current_profession);
            if (pf.designation && pf.designation !== pf.current_profession) parts.push(`(designation: ${pf.designation})`);
            if (pf.years_experience_total) parts.push(`with ${pf.years_experience_total} years of experience`);
            if (pf.industry) parts.push(`in the ${pf.industry} industry`);
            if (pf.has_managerial_experience) parts.push('including managerial responsibilities');
            if (ed.field_of_study) parts.push(`. Educational background: ${ed.field_of_study}${ed.highest_qualification ? ` (${ed.highest_qualification})` : ''}`);
            const wh = (p.work_history || []).slice(0, 2)
              .map(w => [w.designation, w.employer && `at ${w.employer}`, w.duties].filter(Boolean).join(' '))
              .filter(Boolean).join('. ');
            let desc = parts.join(' ').trim();
            if (wh) desc += `. Recent roles — ${wh}`;
            desc = desc.replace(/\s+/g, ' ').trim();

            if (desc.length >= 20) {
              // Country-first: scope the suggestion to the client's target country
              // (defaults to the wizard's selected country, AU by default). Each
              // country has different codes/criteria — the consultant can switch
              // country or fall back to "All" inside the helper.
              const preferredCountry =
                (data.country_mode === 'specific' && data.specific_country)
                  ? data.specific_country
                  : (data.occupation_country || 'AU');
              toast.success(`Resume loaded — finding matching codes for ${preferredCountry}…`);
              setSuggesterPrefill({ description: desc.slice(0, 1900), country: preferredCountry });
              setShowSuggester(true);
            } else {
              toast.success('Resume data loaded — please review the fields below');
              toast.message('Tip: use "AI Occupation Helper" to find the matching occupation code.');
            }
          }}
          headers={headers}
        />
      )}

      {/* Phase 10.3/10.7 — AI Atlas Auto-Suggest modal */}
      <AtlasAutoSuggestModal
        open={showAutoSuggest}
        onClose={() => setShowAutoSuggest(false)}
        country={data.occupation_country || 'AU'}
        headers={headers}
        onSelect={handleAutoSuggestPick}
      />
    </div>
  );
}

function EOIBacklogCard({ code, headers, show, onToggle }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true); setNotFound(false); setData(null);
    axios.get(`${API}/eoi-backlog/occupation/${code}`, { headers })
      .then((r) => { if (alive) setData(r.data); })
      .catch(() => { if (alive) setNotFound(true); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [code, headers]);

  return (
    <Card className="p-3 bg-teal-50 border-l-4 border-l-teal-500" data-testid="eoi-backlog-card">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-teal-700" />
          <div>
            <p className="text-xs font-bold text-teal-900">SkillSelect EOI Backlog (pool competition)</p>
            <p className="text-[10px] text-slate-500">Your view — decide whether to show this in the client's report</p>
          </div>
        </div>
        <label className="flex items-center gap-2 text-[11px] font-medium text-slate-700 cursor-pointer">
          Show in report
          <Switch checked={!!show} onCheckedChange={onToggle} data-testid="eoi-show-toggle" />
        </label>
      </div>

      <div className="mt-2">
        {loading ? (
          <p className="text-[11px] text-slate-500 flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />Loading pool data…</p>
        ) : notFound || !data ? (
          <p className="text-[11px] text-slate-500" data-testid="eoi-card-nodata">No EOI backlog data for {code}. Upload the latest SkillSelect export in Admin → EOI Backlog.</p>
        ) : (
          <div className="flex gap-2 flex-wrap" data-testid="eoi-card-totals">
            {(data.subclasses || []).map((s) => (
              <div key={s.subclass} className="bg-white border rounded px-3 py-1.5 text-center" data-testid={`eoi-card-sc-${s.subclass}`}>
                <p className="text-[9px] uppercase text-slate-500">Subclass {s.subclass}</p>
                <p className="text-sm font-bold text-teal-800">{s.total.toLocaleString()}{s.total_suppressed ? '+' : ''}</p>
                <p className="text-[9px] text-slate-400">in pool</p>
              </div>
            ))}
            <p className="text-[10px] text-slate-500 self-center ml-1">as at {data.as_at_month}</p>
          </div>
        )}
      </div>
      {show && !notFound && (
        <p className="text-[10px] text-emerald-700 mt-2 font-medium" data-testid="eoi-will-show">✓ This EOI backlog will appear in the client's Assessment Report.</p>
      )}
    </Card>
  );
}
