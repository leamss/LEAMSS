import React, { useState } from 'react';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Plus, Trash2, BookOpen, MessageSquare, HelpCircle, CheckCircle,
  Copy, Sparkles, AlertTriangle, ArrowUpRight, Search, Target
} from 'lucide-react';

export default function SalesPlaybookTab({
  playbook,
  objections,
  faqs,
  onChangePlaybook,
  onChangeObjections,
  onChangeFaqs,
  readOnly = false,
}) {
  const [objectionSearch, setObjectionSearch] = useState('');

  const pitchPoints = playbook?.pitch_points || [];
  const keyBenefits = playbook?.key_benefits || [];
  const usps = playbook?.usps || [];
  const discoveryQuestions = playbook?.discovery_questions || [];
  const upselling = playbook?.upselling_opportunities || [];
  const redFlags = playbook?.red_flags || [];
  const elevatorPitch = playbook?.elevator_pitch || (
    pitchPoints.length > 0 ? pitchPoints.join(' ') : 'Direct permanent residency visa with full work and study rights from day 1, no employer sponsor required.'
  );

  const objs = objections || [];
  const faqList = faqs || [];

  const updatePlaybook = (patch) => {
    if (readOnly) return;
    onChangePlaybook({ ...playbook, ...patch });
  };

  const copyPitch = () => {
    navigator.clipboard.writeText(elevatorPitch);
    toast.success('Elevator pitch copied to clipboard!');
  };

  // Helper arrays update
  const addArrayItem = (key, defaultVal = '') => {
    if (readOnly) return;
    const arr = playbook?.[key] || [];
    updatePlaybook({ [key]: [...arr, defaultVal] });
  };

  const updateArrayItem = (key, idx, val) => {
    if (readOnly) return;
    const arr = [...(playbook?.[key] || [])];
    arr[idx] = val;
    updatePlaybook({ [key]: arr });
  };

  const removeArrayItem = (key, idx) => {
    if (readOnly) return;
    const arr = (playbook?.[key] || []).filter((_, i) => i !== idx);
    updatePlaybook({ [key]: arr });
  };

  // Objections
  const addObjection = () => {
    if (readOnly) return;
    onChangeObjections([...objs, { objection: '', rebuttal: '' }]);
  };

  const updateObjection = (idx, patch) => {
    if (readOnly) return;
    const next = [...objs];
    next[idx] = { ...next[idx], ...patch };
    onChangeObjections(next);
  };

  const removeObjection = (idx) => {
    if (readOnly) return;
    onChangeObjections(objs.filter((_, i) => i !== idx));
  };

  // FAQs
  const addFaq = () => {
    if (readOnly) return;
    onChangeFaqs([...faqList, { question: '', answer: '' }]);
  };

  const updateFaq = (idx, patch) => {
    if (readOnly) return;
    const next = [...faqList];
    next[idx] = { ...next[idx], ...patch };
    onChangeFaqs(next);
  };

  const removeFaq = (idx) => {
    if (readOnly) return;
    onChangeFaqs(faqList.filter((_, i) => i !== idx));
  };

  const filteredObjs = objs.filter((o) => {
    if (!objectionSearch.trim()) return true;
    const q = objectionSearch.toLowerCase();
    return (o.objection || '').toLowerCase().includes(q) || (o.rebuttal || '').toLowerCase().includes(q);
  });

  return (
    <div className="space-y-4 text-xs">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. ELEVATOR PITCH BANNER WITH 1-CLICK COPY BUTTON              */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-gradient-to-r from-amber-500/10 via-emerald-500/10 to-blue-500/10 border-2 border-amber-300 space-y-2.5">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">30-Second Client Call Elevator Pitch</h3>
            <Badge className="bg-amber-100 text-amber-800 text-[10px]">High Converting</Badge>
          </div>
          <Button
            size="sm"
            onClick={copyPitch}
            className="h-7 text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold gap-1.5 shadow-sm"
            data-testid="copy-pitch-btn"
          >
            <Copy className="h-3.5 w-3.5" />
            Copy Elevator Pitch
          </Button>
        </div>

        <Textarea
          disabled={readOnly}
          rows={2}
          className="text-xs font-semibold text-slate-900 bg-white/90 border-amber-200"
          value={elevatorPitch}
          onChange={(e) => updatePlaybook({ elevator_pitch: e.target.value })}
          placeholder="Concise 30-second phone pitch highlighting immediate benefits and exclusivity..."
        />
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. IDEAL CLIENT PROFILE & USPs                                */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Ideal Client Profile */}
        <Card className="p-4 bg-white border border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between pb-1.5 border-b">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
              <Target className="h-4 w-4 text-blue-600" />
              Ideal Client Profile (ICP)
            </h4>
            <Badge variant="outline" className="text-[10px]">Target Prospect</Badge>
          </div>
          <Textarea
            disabled={readOnly}
            rows={3}
            className="text-xs"
            placeholder="e.g. IT software engineers, registered nurses, accountants, 25-35 yrs old with 3+ years experience seeking PR status"
            value={playbook?.target_client || ''}
            onChange={(e) => updatePlaybook({ target_client: e.target.value })}
          />
        </Card>

        {/* Unique Selling Propositions (USPs) */}
        <Card className="p-4 bg-white border border-slate-200 space-y-2.5">
          <div className="flex items-center justify-between pb-1.5 border-b">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              Unique Selling Propositions (USPs)
            </h4>
            {!readOnly && (
              <Button size="sm" variant="outline" onClick={() => addArrayItem('usps', '')} className="h-6 text-[10px]">
                <Plus className="h-3 w-3 mr-1" />Add USP
              </Button>
            )}
          </div>
          <div className="space-y-1.5 max-h-36 overflow-y-auto">
            {(usps.length > 0 ? usps : keyBenefits).map((u, idx) => (
              <div key={idx} className="flex items-center gap-1.5">
                <Input
                  disabled={readOnly}
                  className="h-7 text-xs font-medium"
                  placeholder="e.g. 100% direct permanent residency, Medicare coverage from arrival"
                  value={u}
                  onChange={(e) => updateArrayItem('usps', idx, e.target.value)}
                />
                {!readOnly && (
                  <Button size="sm" variant="ghost" onClick={() => removeArrayItem('usps', idx)} className="h-7 w-7 p-0 text-rose-500">
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 3. DISCOVERY QUESTIONS & UPSELLING / RED FLAGS                */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Discovery Questions */}
        <Card className="p-3 bg-white border border-slate-200 space-y-2">
          <div className="flex items-center justify-between pb-1 border-b">
            <span className="font-bold text-slate-800 text-[11px] flex items-center gap-1">
              <MessageSquare className="h-3.5 w-3.5 text-blue-600" />
              Discovery Questions ({discoveryQuestions.length})
            </span>
            {!readOnly && (
              <Button size="sm" variant="outline" onClick={() => addArrayItem('discovery_questions', '')} className="h-5 text-[9px] px-1.5">
                <Plus className="h-2.5 w-2.5" />
              </Button>
            )}
          </div>
          <div className="space-y-1.5 max-h-44 overflow-y-auto">
            {discoveryQuestions.map((q, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <Input
                  disabled={readOnly}
                  className="h-6 text-[11px]"
                  placeholder="e.g. What is your current IELTS or PTE score?"
                  value={q}
                  onChange={(e) => updateArrayItem('discovery_questions', idx, e.target.value)}
                />
                {!readOnly && (
                  <Button size="sm" variant="ghost" onClick={() => removeArrayItem('discovery_questions', idx)} className="h-6 w-6 p-0 text-rose-500">
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>

        {/* Upselling & Cross-Selling */}
        <Card className="p-3 bg-white border border-slate-200 space-y-2">
          <div className="flex items-center justify-between pb-1 border-b">
            <span className="font-bold text-slate-800 text-[11px] flex items-center gap-1">
              <ArrowUpRight className="h-3.5 w-3.5 text-emerald-600" />
              Upsell / Cross-Sell ({upselling.length})
            </span>
            {!readOnly && (
              <Button size="sm" variant="outline" onClick={() => addArrayItem('upselling_opportunities', '')} className="h-5 text-[9px] px-1.5">
                <Plus className="h-2.5 w-2.5" />
              </Button>
            )}
          </div>
          <div className="space-y-1.5 max-h-44 overflow-y-auto">
            {upselling.map((u, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <Input
                  disabled={readOnly}
                  className="h-6 text-[11px]"
                  placeholder="e.g. IELTS 8+ Booster Package, Spouse Skill Assessment (+5 pts)"
                  value={u}
                  onChange={(e) => updateArrayItem('upselling_opportunities', idx, e.target.value)}
                />
                {!readOnly && (
                  <Button size="sm" variant="ghost" onClick={() => removeArrayItem('upselling_opportunities', idx)} className="h-6 w-6 p-0 text-rose-500">
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>

        {/* Red Flags & Disqualifiers */}
        <Card className="p-3 bg-white border border-slate-200 space-y-2">
          <div className="flex items-center justify-between pb-1 border-b">
            <span className="font-bold text-slate-800 text-[11px] flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
              Red Flags / Disqualifiers ({redFlags.length})
            </span>
            {!readOnly && (
              <Button size="sm" variant="outline" onClick={() => addArrayItem('red_flags', '')} className="h-5 text-[9px] px-1.5">
                <Plus className="h-2.5 w-2.5" />
              </Button>
            )}
          </div>
          <div className="space-y-1.5 max-h-44 overflow-y-auto">
            {redFlags.map((r, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <Input
                  disabled={readOnly}
                  className="h-6 text-[11px] text-rose-900 bg-rose-50/50 border-rose-200"
                  placeholder="e.g. Age >= 45, past visa rejection undisclosed, criminal conviction"
                  value={r}
                  onChange={(e) => updateArrayItem('red_flags', idx, e.target.value)}
                />
                {!readOnly && (
                  <Button size="sm" variant="ghost" onClick={() => removeArrayItem('red_flags', idx)} className="h-6 w-6 p-0 text-rose-500">
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 4. OBJECTIONS & REBUTTALS LIBRARY                             */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-emerald-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">Objections & Rebuttals Script Library ({objs.length})</h3>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative w-48">
              <Search className="h-3.5 w-3.5 absolute left-2 top-2 text-slate-400" />
              <Input
                placeholder="Search objections..."
                className="h-7 text-xs pl-7"
                value={objectionSearch}
                onChange={(e) => setObjectionSearch(e.target.value)}
              />
            </div>
            {!readOnly && (
              <Button size="sm" onClick={addObjection} className="h-7 text-xs bg-slate-800 hover:bg-slate-900 text-white gap-1">
                <Plus className="h-3 w-3" />Add Objection
              </Button>
            )}
          </div>
        </div>

        {filteredObjs.length === 0 ? (
          <p className="text-slate-400 italic py-2">No matching objections found.</p>
        ) : (
          <div className="space-y-3">
            {filteredObjs.map((ob, idx) => (
              <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-700 text-xs">Client Objection / Hesitation:</span>
                  {!readOnly && (
                    <Button size="sm" variant="ghost" onClick={() => removeObjection(idx)} className="h-6 w-6 p-0 text-rose-500">
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
                <Input
                  disabled={readOnly}
                  className="h-7 text-xs font-semibold text-rose-950 bg-white"
                  placeholder="e.g. Fees are higher than other agents / Visa takes too long"
                  value={ob.objection || ''}
                  onChange={(e) => updateObjection(idx, { objection: e.target.value })}
                />
                <span className="font-bold text-emerald-700 block text-xs mt-1">Recommended Consultant Rebuttal:</span>
                <Textarea
                  disabled={readOnly}
                  rows={2}
                  className="text-xs text-slate-900 bg-white font-medium"
                  placeholder="e.g. We provide end-to-end transparent lawyer reviews with stage-gated milestone payments..."
                  value={ob.rebuttal || ''}
                  onChange={(e) => updateObjection(idx, { rebuttal: e.target.value })}
                />
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 5. FREQUENTLY ASKED QUESTIONS (FAQS)                          */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Card className="p-4 bg-white border border-slate-200 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b">
          <div className="flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-blue-600" />
            <h3 className="font-extrabold text-slate-900 text-sm">Frequently Asked Questions ({faqList.length})</h3>
          </div>
          {!readOnly && (
            <Button size="sm" onClick={addFaq} className="h-7 text-xs bg-slate-800 hover:bg-slate-900 text-white gap-1">
              <Plus className="h-3 w-3" />Add FAQ
            </Button>
          )}
        </div>

        {faqList.length === 0 ? (
          <p className="text-slate-400 italic py-2">No FAQs defined yet.</p>
        ) : (
          <div className="space-y-3">
            {faqList.map((fq, idx) => (
              <div key={idx} className="p-3 bg-slate-50 border rounded-lg space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-blue-900 text-xs">Question:</span>
                  {!readOnly && (
                    <Button size="sm" variant="ghost" onClick={() => removeFaq(idx)} className="h-6 w-6 p-0 text-rose-500">
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
                <Input
                  disabled={readOnly}
                  className="h-7 text-xs font-semibold bg-white"
                  placeholder="e.g. Can my spouse work full-time on this visa?"
                  value={fq.question || ''}
                  onChange={(e) => updateFaq(idx, { question: e.target.value })}
                />
                <span className="font-bold text-slate-700 block text-xs mt-1">Answer:</span>
                <Textarea
                  disabled={readOnly}
                  rows={2}
                  className="text-xs bg-white text-slate-800"
                  placeholder="e.g. Yes, secondary applicants receive full unrestricted work rights..."
                  value={fq.answer || ''}
                  onChange={(e) => updateFaq(idx, { answer: e.target.value })}
                />
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
