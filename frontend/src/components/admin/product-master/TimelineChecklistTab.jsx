import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Clock, ListChecks, Plus, Trash2, CheckCircle2, AlertCircle,
  FileText, ShieldCheck, Sparkles, ArrowRight, Layers, Lock, Unlock
} from 'lucide-react';

const CATEGORIES = [
  'Identity & Civil',
  'Academic Credentials',
  'Employment & Experience',
  'Language Proficiency',
  'Statutory Dossier',
  'Police Clearance & Character',
  'Health & Medical',
  'Financial Proof',
  'Family & Relationship',
  'Other'
];

const REQUIRED_FOR = [
  { val: 'all_applicants', label: 'All Applicants' },
  { val: 'primary_applicant', label: 'Primary Applicant Only' },
  { val: 'spouse', label: 'Spouse / Partner' },
  { val: 'dependents', label: 'Dependents / Children' },
  { val: 'applicants_16_plus', label: 'Applicants 16+' },
];

export default function TimelineChecklistTab({
  timeline,
  checklist,
  workflowSteps,
  onChangeTimeline,
  onChangeChecklist,
  onChangeWorkflowSteps,
  readOnly = false,
}) {
  const [subTab, setSubTab] = useState('timeline'); // 'timeline' | 'checklist'
  const [checklistFilter, setChecklistFilter] = useState('all');

  const stages = timeline?.stages || [];
  const items = checklist || [];
  const wfSteps = workflowSteps || [];

  // Update Timeline
  const updateTimeline = (patch) => {
    if (readOnly) return;
    onChangeTimeline({ ...timeline, ...patch });
  };

  const addStage = () => {
    if (readOnly) return;
    const nextOrder = stages.length + 1;
    updateTimeline({
      stages: [
        ...stages,
        {
          stage_order: nextOrder,
          stage_name: `Stage ${nextOrder}: New Workflow Stage`,
          duration_days: 14,
          description: '',
          government_fees: '',
          important_notes: '',
        },
      ],
    });
  };

  const updateStage = (idx, patch) => {
    if (readOnly) return;
    const next = [...stages];
    next[idx] = { ...next[idx], ...patch };
    updateTimeline({ stages: next });
  };

  const removeStage = (idx) => {
    if (readOnly) return;
    const next = stages.filter((_, i) => i !== idx).map((s, i) => ({ ...s, stage_order: i + 1 }));
    updateTimeline({ stages: next });
  };

  // Update Checklist
  const addItem = () => {
    if (readOnly) return;
    onChangeChecklist([
      ...items,
      {
        id: `doc-${Date.now()}`,
        category: 'Identity & Civil',
        document_name: '',
        form_code: '',
        required_for: 'all_applicants',
        standard: 'Color Scan / Original',
        is_mandatory: true,
        is_locked_until_paid: false,
        stage_name: stages[0]?.stage_name || 'Stage 1',
        description: '',
      },
    ]);
  };

  const updateItem = (idx, patch) => {
    if (readOnly) return;
    const next = [...items];
    next[idx] = { ...next[idx], ...patch };
    onChangeChecklist(next);
  };

  const removeItem = (idx) => {
    if (readOnly) return;
    onChangeChecklist(items.filter((_, i) => i !== idx));
  };

  const filteredItems = items.filter((it) => {
    if (checklistFilter === 'all') return true;
    if (checklistFilter === 'mandatory') return it.is_mandatory;
    if (checklistFilter === 'primary') return it.required_for === 'primary_applicant';
    if (checklistFilter === 'spouse') return it.required_for === 'spouse';
    return (it.category || '').toLowerCase().includes(checklistFilter.toLowerCase());
  });

  return (
    <div className="space-y-4 text-xs">
      {/* Sub-navigation pill toggle */}
      <div className="flex items-center justify-between pb-2 border-b">
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg bg-slate-100 p-1">
            <button
              onClick={() => setSubTab('timeline')}
              className={`px-3 py-1 rounded-md text-xs font-bold transition flex items-center gap-1.5 ${
                subTab === 'timeline' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Clock className="h-3.5 w-3.5 text-blue-600" />
              Visa Process Timeline ({stages.length} Stages)
            </button>
            <button
              onClick={() => setSubTab('checklist')}
              className={`px-3 py-1 rounded-md text-xs font-bold transition flex items-center gap-1.5 ${
                subTab === 'checklist' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <ListChecks className="h-3.5 w-3.5 text-emerald-600" />
              Document Checklist Matrix ({items.length} Docs)
            </button>
          </div>
        </div>

        {wfSteps.length > 0 && (
          <Badge className="bg-purple-50 text-purple-700 border-purple-200 text-[10px] gap-1">
            <Sparkles className="h-2.5 w-2.5 text-purple-600" />
            AI Workflow Builder Connected ({wfSteps.length} Steps)
          </Badge>
        )}
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* SECTION 1: VISA PROCESS TIMELINE STAGES                       */}
      {/* ───────────────────────────────────────────────────────────── */}
      {subTab === 'timeline' && (
        <div className="space-y-3">
          <Card className="p-4 bg-white border border-slate-200 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-600" />
                  Step-by-Step Visa Execution Timeline
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Sequential delivery milestones, expected duration, and statutory submission stages.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5 bg-slate-50 border rounded px-2.5 py-1">
                  <span className="text-[11px] text-slate-500 font-semibold">Total Duration:</span>
                  <Input
                    disabled={readOnly}
                    value={timeline?.standard_duration || ''}
                    onChange={(e) => updateTimeline({ standard_duration: e.target.value })}
                    className="h-6 w-32 text-xs font-bold"
                    placeholder="e.g. 6 - 9 months"
                  />
                </div>
                {!readOnly && (
                  <Button size="sm" onClick={addStage} className="h-7 text-xs bg-slate-800 hover:bg-slate-900 text-white gap-1">
                    <Plus className="h-3 w-3" />Add Stage
                  </Button>
                )}
              </div>
            </div>

            {stages.length === 0 ? (
              <div className="p-8 text-center bg-slate-50 rounded-lg border-dashed border">
                <Clock className="h-8 w-8 text-slate-300 mx-auto mb-1.5" />
                <p className="text-xs font-bold text-slate-600">No process timeline stages defined</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Click "Add Stage" or save an AI Workflow to populate.</p>
              </div>
            ) : (
              <div className="space-y-3 relative before:absolute before:left-5 before:top-4 before:bottom-4 before:w-0.5 before:bg-slate-200">
                {stages.map((st, idx) => (
                  <div key={idx} className="relative pl-10">
                    {/* Step order circle */}
                    <div className="absolute left-2.5 top-3.5 -translate-x-1/2 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center font-extrabold text-[11px] shadow-sm z-10">
                      {st.stage_order || idx + 1}
                    </div>

                    <Card className="p-3 bg-slate-50/70 hover:bg-slate-50 border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <Input
                          disabled={readOnly}
                          className="h-7 text-xs font-bold text-slate-900 flex-1 bg-white"
                          value={st.stage_name || st.stage || ''}
                          onChange={(e) => updateStage(idx, { stage_name: e.target.value, stage: e.target.value })}
                          placeholder={`Stage ${idx + 1} Title (e.g. Skills Assessment Lodgement)`}
                        />

                        <div className="flex items-center gap-1.5 shrink-0">
                          <div className="flex items-center gap-1 bg-white border rounded px-2 h-7 text-[11px]">
                            <Clock className="h-3 w-3 text-slate-400" />
                            <Input
                              type="number"
                              disabled={readOnly}
                              value={st.duration_days || ''}
                              onChange={(e) => updateStage(idx, { duration_days: parseInt(e.target.value) || 0 })}
                              className="h-5 w-12 text-xs font-bold border-none p-0 text-center"
                              placeholder="14"
                            />
                            <span className="text-slate-400 font-semibold">days</span>
                          </div>

                          {!readOnly && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => removeStage(idx)}
                              className="h-7 w-7 p-0 text-rose-500 hover:bg-rose-50"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Input
                          disabled={readOnly}
                          className="h-7 text-xs bg-white text-slate-600"
                          value={st.description || ''}
                          onChange={(e) => updateStage(idx, { description: e.target.value })}
                          placeholder="Action items / what client and case manager must do in this stage"
                        />
                        <Input
                          disabled={readOnly}
                          className="h-7 text-xs bg-white text-slate-600"
                          value={st.government_fees || ''}
                          onChange={(e) => updateStage(idx, { government_fees: e.target.value })}
                          placeholder="Govt or assessment fee due at this stage (e.g. AUD 530 ACS fee)"
                        />
                      </div>
                    </Card>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* SECTION 2: DOCUMENT CHECKLIST MATRIX                          */}
      {/* ───────────────────────────────────────────────────────────── */}
      {subTab === 'checklist' && (
        <Card className="p-4 bg-white border border-slate-200 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
                <ListChecks className="h-4 w-4 text-emerald-600" />
                Document Checklist & Statutory Form Matrix
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Statutory forms, apostille standards, NAATI translations, and applicant scope breakdown.
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={checklistFilter}
                onChange={(e) => setChecklistFilter(e.target.value)}
                className="h-7 rounded border border-input bg-white px-2 text-xs text-slate-700"
              >
                <option value="all">All Documents ({items.length})</option>
                <option value="mandatory">Mandatory Only</option>
                <option value="primary">Primary Applicant Only</option>
                <option value="spouse">Spouse / Partner</option>
                <option value="Identity">Identity & Civil</option>
                <option value="Academic">Academic Credentials</option>
                <option value="Employment">Employment</option>
              </select>

              {!readOnly && (
                <Button size="sm" onClick={addItem} className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white gap-1">
                  <Plus className="h-3 w-3" />Add Document
                </Button>
              )}
            </div>
          </div>

          {filteredItems.length === 0 ? (
            <div className="p-8 text-center bg-slate-50 rounded-lg border-dashed border">
              <ListChecks className="h-8 w-8 text-slate-300 mx-auto mb-1.5" />
              <p className="text-xs font-bold text-slate-600">No document requirements found</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Add mandatory statutory documents or sync with AI Workflow Builder.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredItems.map((it, idx) => (
                <div key={idx} className="p-3 bg-slate-50/80 hover:bg-slate-50 border rounded-lg space-y-2">
                  <div className="grid grid-cols-12 gap-2 items-center">
                    {/* Category */}
                    <div className="col-span-3">
                      <select
                        disabled={readOnly}
                        value={it.category || 'Identity & Civil'}
                        onChange={(e) => updateItem(idx, { category: e.target.value })}
                        className="h-7 w-full rounded border border-input bg-white px-2 text-xs font-bold"
                      >
                        {CATEGORIES.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Document Name */}
                    <div className="col-span-5">
                      <Input
                        disabled={readOnly}
                        className="h-7 text-xs font-bold text-slate-900 bg-white"
                        placeholder="Document Name (e.g. Valid Passport, Form 80)"
                        value={it.document_name || ''}
                        onChange={(e) => updateItem(idx, { document_name: e.target.value })}
                      />
                    </div>

                    {/* Statutory Form Code */}
                    <div className="col-span-2">
                      <Input
                        disabled={readOnly}
                        className="h-7 text-xs font-mono bg-white"
                        placeholder="Form (e.g. Form 80)"
                        value={it.form_code || ''}
                        onChange={(e) => updateItem(idx, { form_code: e.target.value })}
                      />
                    </div>

                    {/* Applicant Scope */}
                    <div className="col-span-2">
                      <select
                        disabled={readOnly}
                        value={it.required_for || 'all_applicants'}
                        onChange={(e) => updateItem(idx, { required_for: e.target.value })}
                        className="h-7 w-full rounded border border-input bg-white px-2 text-[11px]"
                      >
                        {REQUIRED_FOR.map((r) => (
                          <option key={r.val} value={r.val}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-12 gap-2 items-center text-[11px] pt-1 border-t border-slate-200">
                    <div className="col-span-5">
                      <Input
                        disabled={readOnly}
                        className="h-6 text-[11px] bg-white text-slate-600"
                        placeholder="Standard (e.g. Notarized True Copy / NAATI Certified Translation)"
                        value={it.standard || ''}
                        onChange={(e) => updateItem(idx, { standard: e.target.value })}
                      />
                    </div>

                    <div className="col-span-4">
                      <Input
                        disabled={readOnly}
                        className="h-6 text-[11px] bg-white text-slate-600"
                        placeholder="Execution notes / description..."
                        value={it.description || ''}
                        onChange={(e) => updateItem(idx, { description: e.target.value })}
                      />
                    </div>

                    <div className="col-span-2 flex items-center gap-2">
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          disabled={readOnly}
                          checked={it.is_mandatory !== false}
                          onChange={(e) => updateItem(idx, { is_mandatory: e.target.checked })}
                          className="h-3.5 w-3.5 rounded"
                        />
                        <span className="text-[10px] font-bold text-slate-700">Mandatory</span>
                      </label>

                      <label className="flex items-center gap-1 cursor-pointer" title="Locked until stage fee is paid">
                        <input
                          type="checkbox"
                          disabled={readOnly}
                          checked={!!it.is_locked_until_paid}
                          onChange={(e) => updateItem(idx, { is_locked_until_paid: e.target.checked })}
                          className="h-3.5 w-3.5 rounded"
                        />
                        <span className="text-[10px] text-slate-500">Gated</span>
                      </label>
                    </div>

                    {!readOnly && (
                      <div className="col-span-1 text-right">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removeItem(idx)}
                          className="h-6 w-6 p-0 text-rose-500 hover:bg-rose-50"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
