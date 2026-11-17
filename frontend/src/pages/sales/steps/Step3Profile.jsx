// Step 3 — Profile form + embedded AI helpers (occupation finder + resume upload)
import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
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
import { buildProfile } from '../lib/buildProfile';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function getStandardDeduction(code, body) {
  const c = String(code || '').trim();
  const b = String(body || '').toUpperCase();
  if (c.startsWith('3') || b.includes('TRA') || b.includes('TRADES RECOGNITION')) return 3.0;
  if (c.startsWith('26') || c.startsWith('1351') || b.includes('ACS') || b.includes('COMPUTER SOCIETY')) return 2.0;
  if (b.includes('VETASSESS')) return 1.0;
  return 0.0;
}

export function round1(val) {
  if (val === '' || val === null || val === undefined) return '';
  const n = parseFloat(val);
  if (isNaN(n)) return '';
  return Math.round(n * 10) / 10;
}

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

  // Auto-sync deduction and claimable experience whenever primary occupation is set or changed
  useEffect(() => {
    if (!data.occupation_code) return;
    const stdDed = getStandardDeduction(data.occupation_code, data.occupation_body);
    const currentDed = round1(
      (data.skills_assessment_deducted_years !== '' && data.skills_assessment_deducted_years !== undefined && data.skills_assessment_deducted_years !== null)
        ? parseFloat(data.skills_assessment_deducted_years)
        : stdDed
    );

    if (data.skills_assessment_deducted_years === undefined || data.skills_assessment_deducted_years === '') {
      update('skills_assessment_deducted_years', currentDed);
    }

    // If years_experience_total is empty but skills assessment has claimable years, populate it directly
    if ((data.years_experience_total === '' || data.years_experience_total === undefined || data.years_experience_total === null) &&
        (data.skills_assessment_claimable_years != null || data.skills_assessment_data?.points_claimable_years != null)) {
      const initClaimable = round1(data.skills_assessment_claimable_years ?? data.skills_assessment_data?.points_claimable_years);
      update('years_experience_total', initClaimable);
    }

    // Keep claimable experience in sync with what is in years_experience_total
    const expNum = parseFloat(data.years_experience_total);
    if (!isNaN(expNum)) {
      const claimableYrs = round1(expNum);
      const claimablePts = claimableYrs >= 8 ? 15 : claimableYrs >= 5 ? 10 : claimableYrs >= 3 ? 5 : 0;
      if (data.skills_assessment_claimable_years !== claimableYrs) {
        update('skills_assessment_claimable_years', claimableYrs);
      }
      if (data.skills_assessment_claimable_points !== claimablePts) {
        update('skills_assessment_claimable_points', claimablePts);
      }
      // If there are long floating point decimals in years_experience_total, round it
      if (String(data.years_experience_total).includes('.') && String(data.years_experience_total).split('.')[1].length > 1) {
        update('years_experience_total', claimableYrs);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.occupation_code, data.occupation_body, data.years_experience_total]);

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
    skills_assessment: s.skills_assessment,
  });

  const handleSelectMultiple = (list) => {
    if (!list || !list.length) return;
    const [primary, ...rest] = list;
    update('occupation_country', primary.country_code || 'AU');
    update('occupation_code', primary.code);
    update('occupation_title', primary.title);
    update('occupation_body', primary.assessing_body);
    update('occupation_pathway', primary.pathway);

    const stdDed = round1(getStandardDeduction(primary.code, primary.assessing_body));
    const ded = (primary.skills_assessment && primary.skills_assessment.deducted_years != null)
      ? round1(parseFloat(primary.skills_assessment.deducted_years))
      : stdDed;

    const sa = primary.skills_assessment || {};
    // Directly fill the evaluated claimable experience from the selected occupation
    let claimableYrs = '';
    if (sa.points_claimable_years != null && sa.points_claimable_years !== '') {
      claimableYrs = round1(sa.points_claimable_years);
    } else if (sa.claimable_years != null && sa.claimable_years !== '') {
      claimableYrs = round1(sa.claimable_years);
    } else if (data.years_experience_total !== '' && data.years_experience_total != null && !isNaN(parseFloat(data.years_experience_total))) {
      claimableYrs = round1(data.years_experience_total);
    } else {
      claimableYrs = 0;
    }

    const claimablePts = sa.points_claimable_points != null
      ? Number(sa.points_claimable_points)
      : (claimableYrs >= 8 ? 15 : claimableYrs >= 5 ? 10 : claimableYrs >= 3 ? 5 : 0);

    const totalCareerExp = sa.total_experience_years != null
      ? round1(sa.total_experience_years)
      : round1(claimableYrs + (ded || 0));

    update('raw_years_experience_total', totalCareerExp);
    update('years_experience_total', claimableYrs);
    update('skills_assessment_outcome', sa.assessment_outcome || 'Likely Positive Assessment');
    update('skills_assessment_deducted_years', ded);
    update('skills_assessment_claimable_years', claimableYrs);
    update('skills_assessment_claimable_points', claimablePts);
    update('skills_assessment_rpl_required', Boolean(sa.rpl_required));
    update('skills_assessment_data', {
      ...sa,
      total_experience_years: totalCareerExp,
      deducted_years: ded,
      points_claimable_years: claimableYrs,
      points_claimable_points: claimablePts,
    });

    // Dedupe alternatives against the primary
    const primaryKey = `${primary.code}-${primary.country_code}`;
    const extras = rest
      .map(mapOcc)
      .filter(o => `${o.code}-${o.country_code}` !== primaryKey);
    update('additional_occupations', extras);
    setShowSuggester(false);
    setSuggesterPrefill(null);
    toast.success(extras.length
      ? `Primary ${primary.code} (${primary.assessing_body}) + ${extras.length} alternative${extras.length > 1 ? 's' : ''} added`
      : `Selected ${primary.code} · ${primary.title} (${primary.assessing_body})`);
    setShowAtlas(true);
  };

  const removeAdditional = (idx) => {
    update('additional_occupations', (data.additional_occupations || []).filter((_, i) => i !== idx));
  };

  const makeAlternativePrimary = async (idx) => {
    const alts = [...(data.additional_occupations || [])];
    const newPrimary = alts[idx];
    if (!newPrimary) return;

    // Remove newPrimary from alternatives
    alts.splice(idx, 1);

    // Old primary to be preserved as an alternative
    const oldPrimary = {
      country_code: data.occupation_country || 'AU',
      code: data.occupation_code,
      title: data.occupation_title,
      assessing_body: data.occupation_body,
      pathway: data.occupation_pathway,
      skills_assessment: data.skills_assessment_data,
    };

    if (oldPrimary.code && String(oldPrimary.code) !== String(newPrimary.code)) {
      alts.unshift(oldPrimary);
    }

    const newCode = newPrimary.code;
    const newTitle = newPrimary.title;
    const newBody = newPrimary.assessing_body || (String(newCode).startsWith('3') ? 'Trades Recognition Australia' : String(newCode).startsWith('26') ? 'Australian Computer Society' : 'Designated Assessing Body');
    const newPathway = newPrimary.pathway || 'Core Skills / GSM';

    // Calculate deduction
    let deduction = 0;
    if (newPrimary.skills_assessment && newPrimary.skills_assessment.deducted_years != null) {
      deduction = round1(parseFloat(newPrimary.skills_assessment.deducted_years));
    } else {
      deduction = round1(getStandardDeduction(newCode, newBody));
    }

    const sa = newPrimary.skills_assessment || {};
    let claimableYrs = '';
    if (sa.points_claimable_years != null && sa.points_claimable_years !== '') {
      claimableYrs = round1(sa.points_claimable_years);
    } else if (sa.claimable_years != null && sa.claimable_years !== '') {
      claimableYrs = round1(sa.claimable_years);
    } else if (data.years_experience_total !== '' && data.years_experience_total != null && !isNaN(parseFloat(data.years_experience_total))) {
      claimableYrs = round1(data.years_experience_total);
    } else {
      claimableYrs = 0;
    }

    const claimablePts = sa.points_claimable_points != null
      ? Number(sa.points_claimable_points)
      : (claimableYrs >= 8 ? 15 : claimableYrs >= 5 ? 10 : claimableYrs >= 3 ? 5 : 0);

    const totalCareerExp = sa.total_experience_years != null
      ? round1(sa.total_experience_years)
      : round1(claimableYrs + (deduction || 0));

    // Update state
    update('occupation_country', newPrimary.country_code || 'AU');
    update('occupation_code', newCode);
    update('occupation_title', newTitle);
    update('occupation_body', newBody);
    update('occupation_pathway', newPathway);
    update('raw_years_experience_total', totalCareerExp);
    update('years_experience_total', claimableYrs);
    update('skills_assessment_deducted_years', deduction);
    update('skills_assessment_claimable_years', claimableYrs);
    update('skills_assessment_claimable_points', claimablePts);
    update('skills_assessment_outcome', sa.assessment_outcome || 'Likely Positive Assessment');
    update('skills_assessment_data', {
      ...sa,
      total_experience_years: totalCareerExp,
      deducted_years: deduction,
      points_claimable_years: claimableYrs,
      points_claimable_points: claimablePts,
    });
    update('additional_occupations', alts);

    toast.success(`Set ${newCode} · ${newTitle} as Primary Occupation! Claimable: ${claimableYrs.toFixed(1)} yrs (+${claimablePts} GSM pts)`);

    // Asynchronously call backend to enrich with deep assessing authority data & ABS tasks
    try {
      const evalResp = await axios.post(`${API}/sales/ai/evaluate-occupation-skills`, {
        code: newCode,
        country_code: newPrimary.country_code || 'AU',
        title: newTitle,
        assessing_body: newBody,
        qualification: data.qualification,
        field_of_study: data.field_of_study,
        years_experience_total: claimableYrs,
        profile: buildProfile({ ...data, occupation_code: newCode, occupation_title: newTitle, occupation_body: newBody, years_experience_total: claimableYrs, skills_assessment_claimable_years: claimableYrs }),
      }, { headers });

      if (evalResp.data && evalResp.data.skills_assessment) {
        const enrichedSa = evalResp.data.skills_assessment;
        const enrichedClaimable = enrichedSa.points_claimable_years != null ? round1(enrichedSa.points_claimable_years) : claimableYrs;
        const enrichedPts = enrichedSa.points_claimable_points != null ? enrichedSa.points_claimable_points : claimablePts;
        const enrichedDed = enrichedSa.deducted_years != null ? round1(enrichedSa.deducted_years) : deduction;
        update('skills_assessment_outcome', enrichedSa.assessment_outcome || 'Likely Positive Assessment');
        update('skills_assessment_deducted_years', enrichedDed);
        update('skills_assessment_claimable_years', enrichedClaimable);
        update('skills_assessment_claimable_points', enrichedPts);
        update('years_experience_total', enrichedClaimable);
        update('skills_assessment_data', enrichedSa);
      }
    } catch (e) {
      console.warn('Asynchronous enrichment failed: ', e);
    }
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
          <Upload className="h-3.5 w-3.5 mr-1" />{data.resume_filename ? 'Replace Resume' : 'Upload Resume'}
        </Button>
        {data.resume_filename && (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-medium self-center">
            📄 {data.resume_filename} <span className="text-[10px] text-indigo-500 font-normal">· will be attached to email</span>
          </span>
        )}
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
          <div className="flex items-center justify-between mb-1.5 flex-wrap gap-1">
            <p className="text-[10px] uppercase font-bold text-indigo-700">
              Alternative Occupations · shown side-by-side in the report
            </p>
            <span className="text-[10px] text-indigo-600 font-medium">Click &quot;Set as Primary&quot; to swap any alternative code to primary</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {(data.additional_occupations || []).map((o, i) => (
              <div
                key={`${o.code}-${o.country_code}-${i}`}
                className="flex items-center gap-2 bg-white border border-indigo-200 rounded px-2.5 py-1.5 text-xs shadow-xs"
                data-testid={`additional-occ-${i}`}
              >
                <div>
                  <span className="font-bold text-slate-800">{o.code}</span>
                  <span className="text-slate-600"> · {o.title}</span>
                  <span className="text-[10px] text-slate-400 ml-1">({o.country_code || 'AU'})</span>
                  {o.assessing_body && (
                    <span className="text-[10px] text-indigo-600 block font-medium">{o.assessing_body}</span>
                  )}
                </div>
                <div className="flex items-center gap-1 ml-1.5">
                  <Button
                    size="sm"
                    type="button"
                    onClick={() => makeAlternativePrimary(i)}
                    className="h-6 text-[10px] px-2 font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs"
                    data-testid={`make-primary-btn-${i}`}
                    title="Promote this occupation to Primary"
                  >
                    ★ Set as Primary
                  </Button>
                  <button
                    type="button"
                    onClick={() => removeAdditional(i)}
                    className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded"
                    data-testid={`remove-additional-${i}`}
                    title="Remove alternative"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
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
          <Input
            type="number"
            step="0.1"
            value={data.years_experience_total !== '' && data.years_experience_total !== undefined && !isNaN(parseFloat(data.years_experience_total))
              ? round1(data.years_experience_total)
              : (data.years_experience_total ?? '')}
            onChange={e => {
              const val = e.target.value;
              update('years_experience_total', val);
              const numVal = parseFloat(val);
              if (!isNaN(numVal)) {
                const ded = (data.skills_assessment_deducted_years !== '' && data.skills_assessment_deducted_years !== undefined)
                  ? round1(parseFloat(data.skills_assessment_deducted_years))
                  : round1(getStandardDeduction(data.occupation_code, data.occupation_body));
                const claimableYrs = round1(numVal);
                const claimablePts = claimableYrs >= 8 ? 15 : claimableYrs >= 5 ? 10 : claimableYrs >= 3 ? 5 : 0;
                const rawTotal = round1(claimableYrs + (ded || 0));
                update('raw_years_experience_total', rawTotal);
                update('skills_assessment_claimable_years', claimableYrs);
                update('skills_assessment_claimable_points', claimablePts);
                if (data.skills_assessment_data) {
                  update('skills_assessment_data', {
                    ...data.skills_assessment_data,
                    total_experience_years: rawTotal,
                    deducted_years: ded,
                    points_claimable_years: claimableYrs,
                    points_claimable_points: claimablePts,
                  });
                }
              }
            }}
            onBlur={() => {
              const numVal = parseFloat(data.years_experience_total);
              if (!isNaN(numVal)) {
                update('years_experience_total', round1(numVal));
              }
            }}
            data-testid="ca-exp-total"
            placeholder="1.6"
          />
        </FieldWithLabel>
      </div>

      {/* Professional Work Experience & Job Duties Details */}
      <Card className="p-3 bg-slate-50 border border-slate-200 space-y-3" data-testid="work-experience-section">
        <div className="flex items-center justify-between pb-1.5 border-b">
          <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
            <Briefcase className="h-4 w-4 text-indigo-600" /> Professional Work Experience &amp; Education Details
          </span>
          <span className="text-[10px] text-slate-400">Used by AI to match official ABS ANZSCO unit tasks</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          <FieldWithLabel label="Current Designation / Profession *">
            <Input
              value={data.current_profession || ''}
              onChange={e => update('current_profession', e.target.value)}
              placeholder="e.g. Senior Software Developer, Accountant, Civil Engineer"
              className="h-8 text-xs font-semibold"
              data-testid="ca-current-profession"
            />
          </FieldWithLabel>

          <FieldWithLabel label="Field of Study *">
            <Input
              value={data.field_of_study || ''}
              onChange={e => update('field_of_study', e.target.value)}
              placeholder="e.g. Computer Science, Mechanical Engineering, Commerce"
              className="h-8 text-xs"
              data-testid="ca-field-of-study"
            />
          </FieldWithLabel>

          <FieldWithLabel label="Recent Employer / Company Name">
            <Input
              value={data.employer_name || ''}
              onChange={e => update('employer_name', e.target.value)}
              placeholder="e.g. Tech Solutions Pvt Ltd"
              className="h-8 text-xs"
              data-testid="ca-employer-name"
            />
          </FieldWithLabel>

          <FieldWithLabel label="Nature of Company / Business Sector">
            <Input
              value={data.employer_nature || ''}
              onChange={e => update('employer_nature', e.target.value)}
              placeholder="e.g. Information Technology, Financial Services, Construction"
              className="h-8 text-xs"
              data-testid="ca-employer-nature"
            />
          </FieldWithLabel>
        </div>

        <div>
          <FieldWithLabel label="Core Roles, Responsibilities &amp; Job Duties">
            <Textarea
              value={data.roles_and_responsibilities || ''}
              onChange={e => update('roles_and_responsibilities', e.target.value)}
              placeholder="Describe actual work duties, technical tools, APIs, frameworks, systems, or responsibilities performed on the job..."
              rows={3}
              className="text-xs"
              data-testid="ca-roles-responsibilities"
            />
          </FieldWithLabel>
        </div>
      </Card>

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
          initialDescription={suggesterPrefill?.description || (() => {
            const parts = [];
            if (data.current_profession) parts.push(data.current_profession);
            if (data.employer_name) parts.push(`at ${data.employer_name}`);
            if (data.employer_nature) parts.push(`(Sector: ${data.employer_nature})`);
            if (data.years_experience_total) parts.push(`with ${data.years_experience_total} years of experience`);
            if (data.qualification || data.field_of_study) parts.push(`. Education: ${data.qualification} in ${data.field_of_study || 'General'}`);
            if (data.roles_and_responsibilities) parts.push(`. Core duties: ${data.roles_and_responsibilities}`);
            if (data.work_history?.length > 0) {
              const whList = data.work_history.map(w =>
                `${w.designation || w.title || 'Role'} at ${w.employer || w.employer_name || 'Company'} (${w.company_nature || w.employer_nature || ''}) [${w.dates || ''}]: ${w.duties || (w.duty_bullets && w.duty_bullets.join(', ')) || ''}`
              ).join('. ');
              parts.push(`. Work history: ${whList}`);
            }
            return parts.join(' ').trim();
          })()}
          initialCountry={suggesterPrefill?.country || data.occupation_country || 'AU'}
          initialQualification={suggesterPrefill?.qualification || data.qualification || ''}
          initialFieldOfStudy={suggesterPrefill?.field_of_study || data.field_of_study || ''}
          initialExpYears={suggesterPrefill?.years_experience_total != null ? suggesterPrefill.years_experience_total : (data.years_experience_total || 0)}
          initialProfile={suggesterPrefill?.profile || {
            qualification: data.qualification,
            field_of_study: data.field_of_study,
            years_experience_total: data.years_experience_total ? Number(data.years_experience_total) : 0,
            current_profession: data.current_profession || '',
            profession: data.current_profession || '',
            employer_name: data.employer_name || '',
            nature_of_company: data.employer_nature || '',
            company_nature: data.employer_nature || '',
            roles_and_responsibilities: data.roles_and_responsibilities || '',
            duty_bullets: data.duty_bullets || [],
            work_history: data.work_history || [],
            age: data.age ? Number(data.age) : 30,
            primary_applicant: {
              personal: { age: data.age ? Number(data.age) : 30, full_name: data.client_name || '' },
              education: { highest_qualification: data.qualification, field_of_study: data.field_of_study },
              professional: {
                current_profession: data.current_profession || '',
                designation: data.current_profession || '',
                employer_name: data.employer_name || '',
                employer_nature: data.employer_nature || '',
                years_experience_total: data.years_experience_total ? Number(data.years_experience_total) : 0,
              },
              work_history: data.work_history || [],
            },
          }}
          autoRun={false}
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
            const lg = (p.language || {}).scores || (p.english || {}).scores || {};

            // Extract all fields cleanly from both nested & top-level schemas
            const clientName = extracted.name || extracted.client_name || p.name || per.full_name || per.name || '';
            const clientEmail = extracted.email || extracted.client_email || per.email || per.contact_email || (extracted.personal || {}).email || '';
            const clientPhone = extracted.phone || extracted.client_phone || per.phone || per.contact_phone || per.mobile || (extracted.personal || {}).phone || '';
            const ageVal = per.age || p.age || '';
            const qualVal = ed.highest_qualification || p.highest_qualification || extracted.qualification || '';
            const fieldVal = ed.field_of_study || p.field_of_study || extracted.field_of_study || '';
            const profVal = pf.current_profession || p.current_profession || pf.designation || p.nominated_occupation_title || '';
            const expVal = pf.years_experience_total != null ? pf.years_experience_total : (p.years_experience_total != null ? p.years_experience_total : (p.experience_years_overall != null ? p.experience_years_overall : ''));
            const maritalVal = extracted.marital_status || p.marital_status || '';

            // 2) Build rich candidate profile summary for AI occupation & assessment engine across ALL jobs
            const allWorkHist = (p.work_history || extracted.work_history || []);
            const allDutyBullets = [];
            if (Array.isArray(extracted.duty_bullets) && extracted.duty_bullets.length > 0) {
              allDutyBullets.push(...extracted.duty_bullets);
            }
            allWorkHist.forEach(w => {
              if (Array.isArray(w.duty_bullets)) {
                w.duty_bullets.forEach(b => { if (b && !allDutyBullets.includes(b)) allDutyBullets.push(b); });
              } else if (w.duties && typeof w.duties === 'string') {
                w.duties.split(/[;\n]/).map(s => s.trim()).filter(Boolean).forEach(b => {
                  if (b && !allDutyBullets.includes(b)) allDutyBullets.push(b);
                });
              }
            });
            const dutiesList = allDutyBullets.length > 0 ? allDutyBullets : (extracted.duty_bullets || []);

            // Total experience across all historical positions
            let totalExpNum = Number(expVal) || 0;
            const whYearsSum = allWorkHist.reduce((acc, w) => acc + (Number(w.years) || 0), 0);
            if (whYearsSum > totalExpNum) {
              totalExpNum = whYearsSum;
            }

            const empName = pf.employer_name || extracted.employer_name || (allWorkHist[0]?.employer || allWorkHist[0]?.employer_name) || '';
            const empNature = pf.employer_nature || extracted.company_nature || (allWorkHist[0]?.company_nature) || (allWorkHist[0]?.nature_of_company) || '';

            // Update form state
            setData(d => ({
              ...d,
              client_name: clientName || d.client_name,
              client_email: clientEmail || d.client_email,
              client_phone: clientPhone || d.client_phone,
              age: ageVal || d.age,
              qualification: qualVal || d.qualification,
              field_of_study: fieldVal || d.field_of_study,
              years_experience_total: totalExpNum || expVal || d.years_experience_total,
              current_profession: profVal || d.current_profession,
              employer_name: empName || d.employer_name,
              employer_nature: empNature || d.employer_nature,
              roles_and_responsibilities: extracted.roles_and_responsibilities || (dutiesList.join('\n')) || d.roles_and_responsibilities,
              duty_bullets: dutiesList.length > 0 ? dutiesList : (d.duty_bullets || []),
              work_history: allWorkHist.length > 0 ? allWorkHist : (d.work_history || []),
              ielts_overall: lg.overall || d.ielts_overall,
              ielts_listening: lg.listening || d.ielts_listening,
              ielts_reading: lg.reading || d.ielts_reading,
              ielts_writing: lg.writing || d.ielts_writing,
              ielts_speaking: lg.speaking || d.ielts_speaking,
              marital_status: maritalVal || d.marital_status,
              resume_file_id: extracted.resume_file_id || d.resume_file_id,
              resume_filename: extracted.resume_filename || d.resume_filename,
            }));
            setShowResumeUpload(false);

            const parts = [];
            if (profVal) parts.push(profVal);
            if (empName) parts.push(`at ${empName}`);
            if (empNature) parts.push(`(Sector: ${empNature})`);
            if (totalExpNum || expVal) parts.push(`with ${totalExpNum || expVal} years of total career experience`);
            if (qualVal || fieldVal) parts.push(`. Education: ${qualVal} in ${fieldVal || 'General'}`);
            if (dutiesList.length > 0) {
              parts.push(`. Core duties & responsibilities across positions: ${dutiesList.join('; ')}`);
            }
            
            const wh = allWorkHist
              .map(w => [
                w.designation || w.job_title || w.title,
                (w.employer || w.employer_name) && `at ${w.employer || w.employer_name}`,
                (w.company_nature || w.nature_of_company || w.employer_nature) && `(${w.company_nature || w.nature_of_company || w.employer_nature})`,
                w.dates && `[${w.dates}]`,
                w.duties || (w.duty_bullets && w.duty_bullets.join(', '))
              ].filter(Boolean).join(' '))
              .filter(Boolean).join('. ');
            
            let desc = parts.join(' ').trim();
            if (wh && !desc.includes(wh)) desc += `. Work history: ${wh}`;
            desc = desc.replace(/\s+/g, ' ').trim();

            // Fallback to guarantee a rich description
            if (desc.length < 20) {
              desc = `${profVal || 'Experienced Professional'} with ${totalExpNum || expVal || 5} years of work experience in ${fieldVal || 'Information Technology'}. Holds a ${qualVal || 'bachelor'} degree.`;
            }

            const preferredCountry =
              (data.country_mode === 'specific' && data.specific_country)
                ? data.specific_country
                : (data.occupation_country || 'AU');

            toast.success(`Resume loaded (${clientName || 'Candidate'}) — select your target visa subclasses below and click 'Find Matching Codes'.`);
            
            setSuggesterPrefill({
              description: desc.slice(0, 1900),
              country: preferredCountry,
              qualification: qualVal,
              field_of_study: fieldVal,
              years_experience_total: Number(expVal) || 0,
              profile: {
                qualification: qualVal,
                field_of_study: fieldVal,
                years_experience_total: Number(expVal) || 0,
                profession: profVal,
                employer_name: empName,
                nature_of_company: empNature,
                company_nature: empNature,
                roles_and_responsibilities: extracted.roles_and_responsibilities || (dutiesList.join('\n')),
                duty_bullets: dutiesList,
                work_history: p.work_history || extracted.work_history || [],
                age: Number(ageVal) || 30,
                primary_applicant: p,
              },
            });
            setShowSuggester(true);
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
