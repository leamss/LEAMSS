// Step 3 — Profile form + embedded AI helpers (occupation finder + resume upload)
import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Bot, Briefcase, Heart, Upload, Map } from 'lucide-react';
import FieldWithLabel from '../lib/FieldWithLabel';
import SuggesterModal from '../lib/SuggesterModal';
import ResumeUploadModal from '../lib/ResumeUploadModal';
import ANZSCOPreviewCard from '../components/ANZSCOPreviewCard';
import AtlasVerifyCard from '../components/AtlasVerifyCard';
import { QUALIFICATIONS, MARITAL_OPTIONS, CONTRIBUTION_OPTIONS } from '../lib/constants';

export default function Step3Profile({ data, update, setData, headers }) {
  const [showSuggester, setShowSuggester] = useState(false);
  const [showResumeUpload, setShowResumeUpload] = useState(false);
  const [showAtlas, setShowAtlas] = useState(false);

  // Auto-open the chosen helper on first visit
  useEffect(() => {
    if (data.approach === 'occupation_finder' && !data.occupation_code) setShowSuggester(true);
    if (data.approach === 'resume_upload' && !data.age) setShowResumeUpload(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isMarried = data.marital_status === 'married' || data.marital_status === 'de_facto';

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold flex items-center gap-2">
        <Briefcase className="h-5 w-5 text-indigo-600" />Capture Client Profile
      </h2>

      <div className="flex gap-2 flex-wrap">
        <Button variant="outline" size="sm" onClick={() => setShowSuggester(true)} data-testid="open-suggester">
          <Bot className="h-3.5 w-3.5 mr-1" />AI Occupation Helper
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
          onClose={() => setShowSuggester(false)}
          onSelect={(s) => {
            update('occupation_country', s.country_code);
            update('occupation_code', s.code);
            update('occupation_title', s.title);
            update('occupation_body', s.assessing_body);
            update('occupation_pathway', s.pathway);
            setShowSuggester(false);
            toast.success(`Selected ${s.code} ${s.title}`);
          }}
          headers={headers}
        />
      )}

      {showResumeUpload && (
        <ResumeUploadModal
          onClose={() => setShowResumeUpload(false)}
          onExtracted={(extracted) => {
            const p = extracted.primary_applicant || {};
            const ed = p.education || {};
            const pf = p.professional || {};
            const lg = (p.language || {}).scores || {};
            setData(d => ({
              ...d,
              age: (p.personal || {}).age || d.age,
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
            toast.success('Resume data loaded — please review the fields below');
          }}
          headers={headers}
        />
      )}
    </div>
  );
}
