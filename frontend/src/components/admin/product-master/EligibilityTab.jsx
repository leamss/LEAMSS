import React from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Plus, Trash2, CheckCircle2, Award, Shield, UserCheck, GraduationCap,
  Briefcase, Languages, Landmark, FileText, DollarSign
} from 'lucide-react';

export default function EligibilityTab({
  product,
  eligibility,
  conditions,
  onChangeEligibility,
  onChangeConditions,
  readOnly = false,
}) {
  const mandatory = eligibility?.mandatory || [];
  const optional = eligibility?.optional || [];
  const points = eligibility?.points_based || { is_points_tested: false, minimum_points: 65, scoring_factors: [] };
  const conds = conditions || [];

  // Structured criteria fields
  const ageReq = eligibility?.age_requirement || { min_age: 18, max_age: 44, notes: 'Must be under 45 at time of invitation' };
  const eduReq = eligibility?.qualification_requirement || { min_level: "Bachelor's Degree", discipline: 'Relevant to nominated ANZSCO occupation', notes: '' };
  const expReq = eligibility?.experience_requirement || { min_years: 3, nominated_field: true, notes: 'Post-qualification full-time paid experience' };
  const engReq = eligibility?.english_requirement || { benchmark: 'Competent English (IELTS 6.0 all bands / PTE 50)', tests: 'IELTS, PTE Academic, TOEFL iBT', min_score: '6.0 each / 50 each' };
  const skillsReq = eligibility?.skills_assessment || { authority: 'ACS / VETASSESS / Engineers Australia', code: '', validity_years: 3, notes: 'Positive assessment outcome required before EOI' };
  const anzscoReq = eligibility?.anzsco || { code: '', occupation_title: '', list_type: 'MLTSSL / STSOL', notes: '' };
  const fundsReq = eligibility?.funds_requirement || { required: true, amount_inr: 500000, foreign_amount: 10000, currency: 'AUD', notes: 'Liquid funds proof required for settlement' };

  const updateField = (key, val) => {
    if (readOnly) return;
    onChangeEligibility({
      ...eligibility,
      [key]: val,
    });
  };

  const updateMandatory = (idx, patch) => {
    if (readOnly) return;
    const next = [...mandatory];
    next[idx] = { ...next[idx], ...patch };
    onChangeEligibility({ ...eligibility, mandatory: next });
  };

  const addMandatory = () => {
    if (readOnly) return;
    onChangeEligibility({
      ...eligibility,
      mandatory: [...mandatory, { criterion: '', description: '' }],
    });
  };

  const removeMandatory = (idx) => {
    if (readOnly) return;
    onChangeEligibility({
      ...eligibility,
      mandatory: mandatory.filter((_, i) => i !== idx),
    });
  };

  const updatePoints = (patch) => {
    if (readOnly) return;
    onChangeEligibility({
      ...eligibility,
      points_based: { ...points, ...patch },
    });
  };

  const addScoringFactor = () => {
    if (readOnly) return;
    const factors = points.scoring_factors || [];
    updatePoints({
      scoring_factors: [...factors, { factor: '', max_points: 10, details: '' }],
    });
  };

  const updateScoringFactor = (idx, patch) => {
    if (readOnly) return;
    const factors = [...(points.scoring_factors || [])];
    factors[idx] = { ...factors[idx], ...patch };
    updatePoints({ scoring_factors: factors });
  };

  const removeScoringFactor = (idx) => {
    if (readOnly) return;
    const factors = (points.scoring_factors || []).filter((_, i) => i !== idx);
    updatePoints({ scoring_factors: factors });
  };

  const addCondition = () => {
    if (readOnly) return;
    onChangeConditions([...conds, '']);
  };

  const updateCondition = (idx, val) => {
    if (readOnly) return;
    const next = [...conds];
    next[idx] = val;
    onChangeConditions(next);
  };

  const removeCondition = (idx) => {
    if (readOnly) return;
    onChangeConditions(conds.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-4 text-xs">
      {/* Core Structured Eligibility Criteria Grid */}
      <Card className="p-4 space-y-4 bg-white border border-slate-200">
        <div className="flex items-center justify-between pb-2 border-b">
          <div className="flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-emerald-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">Statutory Eligibility Requirements</h3>
          </div>
          <Badge variant="outline" className="text-[10px]">Statutory Criteria Matrix</Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Age Criterion */}
          <div className="p-3 bg-slate-50 rounded-lg border space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold flex items-center gap-1.5 text-slate-800">
                <UserCheck className="h-3.5 w-3.5 text-blue-600" />
                Age Limit Requirement
              </Label>
              <span className="text-[10px] text-slate-500 font-medium">Under {ageReq.max_age || 45} yrs</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Max Eligible Age</Label>
                <Input
                  type="number"
                  disabled={readOnly}
                  value={ageReq.max_age || ''}
                  onChange={(e) => updateField('age_requirement', { ...ageReq, max_age: parseInt(e.target.value) || 0 })}
                  className="h-7 text-xs font-bold"
                  placeholder="e.g. 44"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Age Rule / Cutoff</Label>
                <Input
                  disabled={readOnly}
                  value={ageReq.notes || ''}
                  onChange={(e) => updateField('age_requirement', { ...ageReq, notes: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. At time of invitation"
                />
              </div>
            </div>
          </div>

          {/* Education Qualification */}
          <div className="p-3 bg-slate-50 rounded-lg border space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold flex items-center gap-1.5 text-slate-800">
                <GraduationCap className="h-3.5 w-3.5 text-purple-600" />
                Qualification Requirement
              </Label>
              <span className="text-[10px] text-slate-500 font-medium">{eduReq.min_level}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Minimum Level</Label>
                <Input
                  disabled={readOnly}
                  value={eduReq.min_level || ''}
                  onChange={(e) => updateField('qualification_requirement', { ...eduReq, min_level: e.target.value })}
                  className="h-7 text-xs font-bold"
                  placeholder="e.g. Bachelor's Degree"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Discipline / Major</Label>
                <Input
                  disabled={readOnly}
                  value={eduReq.discipline || ''}
                  onChange={(e) => updateField('qualification_requirement', { ...eduReq, discipline: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. Relevant to nominated occupation"
                />
              </div>
            </div>
          </div>

          {/* Work Experience */}
          <div className="p-3 bg-slate-50 rounded-lg border space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold flex items-center gap-1.5 text-slate-800">
                <Briefcase className="h-3.5 w-3.5 text-amber-600" />
                Experience Requirement
              </Label>
              <span className="text-[10px] text-slate-500 font-medium">{expReq.min_years}+ Years</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Min Full-Time Years</Label>
                <Input
                  type="number"
                  disabled={readOnly}
                  value={expReq.min_years || ''}
                  onChange={(e) => updateField('experience_requirement', { ...expReq, min_years: parseFloat(e.target.value) || 0 })}
                  className="h-7 text-xs font-bold"
                  placeholder="e.g. 3"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Experience Rules</Label>
                <Input
                  disabled={readOnly}
                  value={expReq.notes || ''}
                  onChange={(e) => updateField('experience_requirement', { ...expReq, notes: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. In nominated ANZSCO"
                />
              </div>
            </div>
          </div>

          {/* English Proficiency */}
          <div className="p-3 bg-slate-50 rounded-lg border space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold flex items-center gap-1.5 text-slate-800">
                <Languages className="h-3.5 w-3.5 text-emerald-600" />
                English Score Benchmark
              </Label>
              <span className="text-[10px] text-slate-500 font-medium">{engReq.min_score}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Benchmark Tier</Label>
                <Input
                  disabled={readOnly}
                  value={engReq.benchmark || ''}
                  onChange={(e) => updateField('english_requirement', { ...engReq, benchmark: e.target.value })}
                  className="h-7 text-xs font-bold"
                  placeholder="e.g. Competent / Proficient"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Min Per-Band / Overall</Label>
                <Input
                  disabled={readOnly}
                  value={engReq.min_score || ''}
                  onChange={(e) => updateField('english_requirement', { ...engReq, min_score: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. IELTS 6.0 each / PTE 50"
                />
              </div>
            </div>
          </div>

          {/* Skills Assessment Authority */}
          <div className="p-3 bg-slate-50 rounded-lg border space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold flex items-center gap-1.5 text-slate-800">
                <Landmark className="h-3.5 w-3.5 text-blue-600" />
                Skills Assessment Authority
              </Label>
              <Badge className="bg-blue-50 text-blue-700 text-[9px] py-0">{skillsReq.validity_years || 3} Yrs Validity</Badge>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Assessing Body</Label>
                <Input
                  disabled={readOnly}
                  value={skillsReq.authority || ''}
                  onChange={(e) => updateField('skills_assessment', { ...skillsReq, authority: e.target.value })}
                  className="h-7 text-xs font-bold"
                  placeholder="e.g. ACS, VETASSESS, Engineers Australia"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Authority Notes</Label>
                <Input
                  disabled={readOnly}
                  value={skillsReq.notes || ''}
                  onChange={(e) => updateField('skills_assessment', { ...skillsReq, notes: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. Positive outcome mandatory"
                />
              </div>
            </div>
          </div>

          {/* ANZSCO / Nominated Occupation */}
          <div className="p-3 bg-slate-50 rounded-lg border space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold flex items-center gap-1.5 text-slate-800">
                <FileText className="h-3.5 w-3.5 text-slate-600" />
                ANZSCO / Occupation Classification
              </Label>
              <span className="text-[10px] text-slate-500 font-medium">{anzscoReq.list_type || 'MLTSSL'}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">ANZSCO Code / Range</Label>
                <Input
                  disabled={readOnly}
                  value={anzscoReq.code || ''}
                  onChange={(e) => updateField('anzsco', { ...anzscoReq, code: e.target.value })}
                  className="h-7 text-xs font-bold font-mono"
                  placeholder="e.g. 261313, 233211"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Occupation List Type</Label>
                <Input
                  disabled={readOnly}
                  value={anzscoReq.list_type || ''}
                  onChange={(e) => updateField('anzsco', { ...anzscoReq, list_type: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. MLTSSL / STSOL / ROL"
                />
              </div>
            </div>
          </div>

          {/* Proof of Settlement Funds */}
          <div className="p-3 bg-slate-50 rounded-lg border space-y-2 md:col-span-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-bold flex items-center gap-1.5 text-slate-800">
                <DollarSign className="h-3.5 w-3.5 text-emerald-600" />
                Proof of Settlement Funds
              </Label>
              <span className="text-[10px] text-emerald-700 font-bold">Approx. ₹{(fundsReq.amount_inr || 500000).toLocaleString('en-IN')}</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Estimated Funds (₹ INR)</Label>
                <Input
                  type="number"
                  disabled={readOnly}
                  value={fundsReq.amount_inr || ''}
                  onChange={(e) => updateField('funds_requirement', { ...fundsReq, amount_inr: parseFloat(e.target.value) || 0 })}
                  className="h-7 text-xs font-bold text-emerald-800"
                  placeholder="e.g. 500000"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Foreign Currency Amount</Label>
                <Input
                  disabled={readOnly}
                  value={fundsReq.foreign_amount ? `${fundsReq.foreign_amount} ${fundsReq.currency || 'AUD'}` : ''}
                  onChange={(e) => updateField('funds_requirement', { ...fundsReq, foreign_amount: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. 10000 AUD"
                />
              </div>
              <div>
                <Label className="text-[10px] text-slate-500 font-semibold">Funds Documentation Rules</Label>
                <Input
                  disabled={readOnly}
                  value={fundsReq.notes || ''}
                  onChange={(e) => updateField('funds_requirement', { ...fundsReq, notes: e.target.value })}
                  className="h-7 text-xs"
                  placeholder="e.g. Liquid savings/FD held for 3+ months"
                />
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Mandatory Criteria List */}
      <Card className="p-4 space-y-3 bg-white border border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-bold text-slate-800 text-sm">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            Mandatory Eligibility Checklist ({mandatory.length})
          </div>
          {!readOnly && (
            <Button size="sm" variant="outline" onClick={addMandatory} className="h-7 text-xs">
              <Plus className="h-3.5 w-3.5 mr-1" />Add Criterion
            </Button>
          )}
        </div>

        {mandatory.length === 0 ? (
          <p className="text-slate-400 italic">No mandatory criteria defined yet. Use "AI Enrich" or add manually.</p>
        ) : (
          <div className="space-y-2">
            {mandatory.map((item, idx) => (
              <div key={idx} className="p-2.5 bg-slate-50 border rounded-lg flex items-start gap-2">
                <div className="flex-1 space-y-1.5">
                  <Input
                    disabled={readOnly}
                    className="h-7 text-xs font-semibold"
                    placeholder="Criterion title (e.g. Age under 45)"
                    value={item.criterion || ''}
                    onChange={(e) => updateMandatory(idx, { criterion: e.target.value })}
                  />
                  <Input
                    disabled={readOnly}
                    className="h-7 text-xs text-slate-600"
                    placeholder="Detailed explanation / rules"
                    value={item.description || ''}
                    onChange={(e) => updateMandatory(idx, { description: e.target.value })}
                  />
                </div>
                {!readOnly && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeMandatory(idx)}
                    className="h-7 text-rose-500 hover:bg-rose-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Points Testing Section */}
      <Card className="p-4 space-y-3 bg-white border border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Award className="h-4 w-4 text-blue-600" />
            <span className="font-bold text-slate-800 text-sm">Points-Based Testing Matrix</span>
            <Badge className={points.is_points_tested ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-600'}>
              {points.is_points_tested ? 'Points Tested' : 'Direct / Non-Points'}
            </Badge>
          </div>
          {!readOnly && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="pts-test-toggle"
                checked={!!points.is_points_tested}
                onChange={(e) => updatePoints({ is_points_tested: e.target.checked })}
                className="h-4 w-4"
              />
              <Label htmlFor="pts-test-toggle" className="cursor-pointer font-semibold">Enable Points Test</Label>
            </div>
          )}
        </div>

        {points.is_points_tested && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center gap-2">
              <Label className="font-bold">Minimum Pass Mark / Threshold:</Label>
              <Input
                type="number"
                disabled={readOnly}
                value={points.minimum_points || 65}
                onChange={(e) => updatePoints({ minimum_points: parseInt(e.target.value) || 0 })}
                className="w-24 h-7 text-xs font-bold text-blue-900"
              />
              <span className="text-slate-500">points</span>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between font-bold text-slate-700">
                <span>Scoring Factors & Matrices ({points.scoring_factors?.length || 0})</span>
                {!readOnly && (
                  <Button size="sm" variant="outline" onClick={addScoringFactor} className="h-6 text-[11px]">
                    <Plus className="h-3 w-3 mr-1" />Add Factor
                  </Button>
                )}
              </div>

              {(points.scoring_factors || []).map((f, idx) => (
                <div key={idx} className="p-2 bg-blue-50/40 border border-blue-100 rounded flex items-center gap-2">
                  <Input
                    disabled={readOnly}
                    className="w-48 h-7 text-xs font-semibold"
                    placeholder="Factor name (e.g. Age, English)"
                    value={f.factor || ''}
                    onChange={(e) => updateScoringFactor(idx, { factor: e.target.value })}
                  />
                  <div className="flex items-center gap-1">
                    <span className="text-[11px] text-slate-500">Max:</span>
                    <Input
                      type="number"
                      disabled={readOnly}
                      className="w-16 h-7 text-xs font-bold"
                      value={f.max_points || 0}
                      onChange={(e) => updateScoringFactor(idx, { max_points: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                  <Input
                    disabled={readOnly}
                    className="flex-1 h-7 text-xs"
                    placeholder="Details (e.g. 25-32 yrs = 30 pts)"
                    value={f.details || ''}
                    onChange={(e) => updateScoringFactor(idx, { details: e.target.value })}
                  />
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeScoringFactor(idx)}
                      className="h-7 text-rose-500 hover:bg-rose-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Visa Conditions & Rights */}
      <Card className="p-4 space-y-3 bg-white border border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 font-bold text-slate-800 text-sm">
            <Shield className="h-4 w-4 text-purple-600" />
            Visa Rights & Conditions ({conds.length})
          </div>
          {!readOnly && (
            <Button size="sm" variant="outline" onClick={addCondition} className="h-7 text-xs">
              <Plus className="h-3.5 w-3.5 mr-1" />Add Condition
            </Button>
          )}
        </div>

        {conds.length === 0 ? (
          <p className="text-slate-400 italic">No conditions specified.</p>
        ) : (
          <div className="space-y-1.5">
            {conds.map((c, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <Input
                  disabled={readOnly}
                  className="h-7 text-xs"
                  placeholder="e.g. Full unrestricted work and study rights"
                  value={c}
                  onChange={(e) => updateCondition(idx, e.target.value)}
                />
                {!readOnly && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => removeCondition(idx)}
                    className="h-7 text-rose-500 hover:bg-rose-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
