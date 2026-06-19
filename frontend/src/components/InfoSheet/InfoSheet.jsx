/**
 * Phase 20.4 — Universal Info Sheet component.
 *
 * Mountable on any page (Sales Create, Sales Detail, Admin Case Mgmt).
 * Tabbed 6-section UI with 1-second debounced auto-save + dirty indicator.
 * Resume upload + AI extraction + prefill confirmation modal + audit trail drawer.
 *
 * Usage:
 *   <InfoSheet entityType="case" entityId={caseId} clientId={clientId} />
 *   <InfoSheet entityType="sale" entityId={saleId} />
 *   <InfoSheet entityType="standalone" entityId="lead-xyz" />
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  User, Users, Baby, GraduationCap, Briefcase, FileText, Lock, Unlock,
  Upload, Wand2, History, CheckCircle2, AlertCircle, RefreshCw, X, Plus, Trash2,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

const TAB_ICONS = {
  personal: User,
  family: Users,
  dependents: Baby,
  qualifications: GraduationCap,
  employment: Briefcase,
  resume: FileText,
};

const SAVE_DEBOUNCE_MS = 1000;


function FieldInput({ field, value, onChange }) {
  const common = {
    'data-testid': `field-${field.key}`,
    value: value ?? '',
    onChange: (e) => onChange(field.key, e.target.value),
    placeholder: field.label,
  };
  if (field.type === 'select') {
    return (
      <Select value={value || ''} onValueChange={(v) => onChange(field.key, v)}>
        <SelectTrigger data-testid={`field-${field.key}`}><SelectValue placeholder={`Select ${field.label}`} /></SelectTrigger>
        <SelectContent>
          {(field.options || []).map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
        </SelectContent>
      </Select>
    );
  }
  if (field.type === 'textarea') {
    return <textarea rows={3} className="w-full border rounded p-2 text-sm" {...common} />;
  }
  if (field.type === 'date') {
    return <Input type="date" {...common} />;
  }
  if (field.type === 'boolean') {
    return (
      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={!!value} onChange={(e) => onChange(field.key, e.target.checked)} data-testid={`field-${field.key}`} />
        <span className="text-xs">{field.label}</span>
      </label>
    );
  }
  return <Input type={field.type === 'email' ? 'email' : field.type === 'tel' ? 'tel' : 'text'} {...common} />;
}


function SectionFlatFields({ section, value, onChange }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {section.fields.map((f) => (
        <div key={f.key} className={f.type === 'textarea' ? 'md:col-span-2' : ''}>
          <Label className="text-xs font-bold flex items-center gap-1">
            {f.label}{f.required && <span className="text-leamss-red">*</span>}
          </Label>
          <FieldInput field={f} value={value?.[f.key]} onChange={(k, v) => onChange({...(value || {}), [k]: v})} />
        </div>
      ))}
    </div>
  );
}


function SectionArrayFields({ section, items, onChange }) {
  const addEntry = () => onChange([...(items || []), {}]);
  const removeEntry = (idx) => onChange(items.filter((_, i) => i !== idx));
  const updateEntry = (idx, patch) => {
    const next = [...items];
    next[idx] = {...next[idx], ...patch};
    onChange(next);
  };
  return (
    <div className="space-y-3">
      {(items || []).map((entry, idx) => (
        <Card key={idx} className="p-3 bg-leamss-teal_50 border border-leamss-teal/20" data-testid={`${section.id}-entry-${idx}`}>
          <div className="flex justify-between items-center mb-2">
            <p className="text-xs font-bold text-leamss-teal">#{idx + 1}</p>
            <Button size="sm" variant="ghost" onClick={() => removeEntry(idx)} data-testid={`${section.id}-remove-${idx}`}>
              <Trash2 className="h-3.5 w-3.5 text-leamss-red" />
            </Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {section.entry_fields.map((f) => (
              <div key={f.key} className={f.type === 'textarea' ? 'md:col-span-2' : ''}>
                <Label className="text-[10px] uppercase font-bold text-slate-500">{f.label}</Label>
                <FieldInput field={f} value={entry?.[f.key]} onChange={(k, v) => updateEntry(idx, {[k]: v})} />
              </div>
            ))}
          </div>
        </Card>
      ))}
      {items?.length < (section.max_entries || 20) && (
        <Button variant="outline" size="sm" onClick={addEntry} className="border-leamss-teal text-leamss-teal" data-testid={`${section.id}-add-btn`}>
          <Plus className="h-3.5 w-3.5 mr-1" />Add {section.title.replace(/s$/, '')}
        </Button>
      )}
    </div>
  );
}


function ResumeSection({ sheet, onResumeUpdated }) {
  const [uploading, setUploading] = useState(false);
  const [showPrefill, setShowPrefill] = useState(false);
  const resume = sheet?.resume || {};

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/info-sheets/${sheet.id}/resume`, fd, {
        ...auth(),
        headers: {...auth().headers, 'Content-Type': 'multipart/form-data'},
      });
      toast.success(`Resume extracted via ${r.data.resume.model_used?.split('/').pop()}`);
      onResumeUpdated();
      setShowPrefill(true);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Resume upload failed');
    }
    setUploading(false);
  };

  const applyPrefill = async (mergeStrategy) => {
    try {
      const r = await axios.post(`${API}/info-sheets/${sheet.id}/resume/apply-prefill`,
        { apply_qualifications: true, apply_employment: true, merge_strategy: mergeStrategy }, auth());
      toast.success(`Prefilled ${r.data.qualifications_added} quals + ${r.data.employment_added} employment entries`);
      setShowPrefill(false);
      onResumeUpdated();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Prefill failed');
    }
  };

  return (
    <div className="space-y-4" data-testid="resume-section">
      <Card className="p-4 bg-leamss-orange_50 border border-leamss-orange/30">
        <div className="flex items-start gap-3">
          <Wand2 className="h-5 w-5 text-leamss-orange mt-1" />
          <div className="flex-1">
            <p className="text-sm font-bold text-leamss-orange">AI Resume Extraction (Claude Sonnet 4.5)</p>
            <p className="text-xs text-slate-600 mt-1">
              Upload your CV/Resume (PDF/DOCX/TXT, max 5MB). Claude Sonnet 4.5 will extract structured data — qualifications, employment, skills — which you can review + prefill into the other sections.
            </p>
            <label className="mt-3 inline-flex items-center gap-2 px-3 py-2 bg-leamss-orange hover:bg-leamss-orange/90 text-white rounded text-sm cursor-pointer" data-testid="resume-upload-btn">
              <Upload className="h-3.5 w-3.5" />
              {uploading ? 'Extracting…' : (resume.file_name ? 'Re-upload Resume' : 'Upload Resume')}
              <input type="file" accept=".pdf,.docx,.doc,.txt" onChange={handleUpload} disabled={uploading} className="hidden" data-testid="resume-file-input" />
            </label>
          </div>
        </div>
      </Card>

      {resume.file_name && (
        <Card className="p-4">
          <div className="flex justify-between items-start mb-3">
            <div>
              <p className="text-sm font-bold flex items-center gap-2">
                <FileText className="h-4 w-4" />{resume.file_name}
              </p>
              <p className="text-xs text-slate-500">
                Uploaded {resume.uploaded_at?.slice(0, 19).replace('T', ' ')} · Model: <span className="font-mono">{resume.model_used}</span> · Confidence: <span className="font-bold text-leamss-teal">{Math.round((resume.confidence_score || 0) * 100)}%</span>
              </p>
            </div>
            {!resume._used_to_prefill && (
              <Button size="sm" onClick={() => setShowPrefill(true)} className="bg-leamss-teal hover:bg-leamss-teal/90" data-testid="resume-show-prefill-btn">
                <Wand2 className="h-3.5 w-3.5 mr-1" />Apply Prefill
              </Button>
            )}
            {resume._used_to_prefill && (
              <Badge className="bg-leamss-teal text-white"><CheckCircle2 className="h-3 w-3 mr-1" />Prefilled</Badge>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
            <Card className="p-3 bg-leamss-teal_50">
              <p className="text-xs font-bold text-leamss-teal">Qualifications</p>
              <p className="text-2xl font-bold">{resume.extracted_qualifications?.length || 0}</p>
              <p className="text-[10px] text-slate-500">{resume.extracted_qualifications?.[0]?.degree?.slice(0, 30)}</p>
            </Card>
            <Card className="p-3 bg-leamss-orange_50">
              <p className="text-xs font-bold text-leamss-orange">Employment</p>
              <p className="text-2xl font-bold">{resume.extracted_employment?.length || 0}</p>
              <p className="text-[10px] text-slate-500">{resume.summary?.total_years_experience} yrs total</p>
            </Card>
            <Card className="p-3 bg-leamss-red_50">
              <p className="text-xs font-bold text-leamss-red">Skills</p>
              <p className="text-2xl font-bold">{resume.summary?.skills?.length || 0}</p>
              <p className="text-[10px] text-slate-500">{(resume.summary?.skills || []).slice(0, 3).join(', ')}</p>
            </Card>
          </div>
        </Card>
      )}

      {showPrefill && resume.file_name && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-lg p-5" data-testid="prefill-modal">
            <div className="flex justify-between mb-3">
              <h3 className="text-lg font-bold text-leamss-teal">Confirm Resume Prefill</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowPrefill(false)}><X className="h-4 w-4" /></Button>
            </div>
            <p className="text-sm text-slate-700 mb-3">
              Claude ne <span className="font-bold text-leamss-teal">{resume.extracted_qualifications?.length || 0}</span> qualifications + <span className="font-bold text-leamss-orange">{resume.extracted_employment?.length || 0}</span> employment entries extract kiye hain. Kaise apply karein?
            </p>
            <div className="space-y-2 mb-4">
              <Button onClick={() => applyPrefill('append')} className="w-full bg-leamss-teal hover:bg-leamss-teal/90" data-testid="prefill-append-btn">
                Append (add to existing entries)
              </Button>
              <Button onClick={() => applyPrefill('replace')} variant="outline" className="w-full border-leamss-red text-leamss-red" data-testid="prefill-replace-btn">
                Replace (overwrite existing arrays)
              </Button>
            </div>
            <p className="text-[10px] text-slate-500">Tip: Append safer hai — extracted data ko review-able rakhta hai.</p>
          </Card>
        </div>
      )}
    </div>
  );
}


function AuditTrailDrawer({ sheetId, onClose }) {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    axios.get(`${API}/info-sheets/${sheetId}/audit-trail?limit=50`, auth())
      .then(r => setEvents(r.data.events || []))
      .catch(() => toast.error('Failed to load audit trail'));
  }, [sheetId]);
  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl z-50 overflow-y-auto" data-testid="audit-trail-drawer">
      <div className="p-4 border-b flex justify-between items-center">
        <h3 className="font-bold flex items-center gap-2"><History className="h-4 w-4 text-leamss-teal" />Audit Trail</h3>
        <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
      </div>
      <div className="p-3 space-y-2">
        {events.length === 0 && <p className="text-xs text-slate-500">No edit history yet.</p>}
        {events.map((ev, i) => (
          <Card key={i} className="p-2 text-xs">
            <div className="flex justify-between">
              <Badge variant="outline" className="text-[10px]">{ev.action}</Badge>
              <span className="text-slate-400 text-[10px]">{ev.at?.slice(11, 19)}</span>
            </div>
            <p className="text-slate-600 mt-1">{ev.by_name || ev.by}</p>
            {ev.sections_changed && <p className="text-[10px] text-slate-500">Sections: {ev.sections_changed.join(', ')}</p>}
            {ev.changes_summary && <p className="text-[10px] italic">{ev.changes_summary}</p>}
            {ev.file_name && <p className="text-[10px] text-leamss-orange">📄 {ev.file_name}</p>}
          </Card>
        ))}
      </div>
    </div>
  );
}


export default function InfoSheet({ entityType, entityId, clientId, caseId, readOnly = false }) {
  const [schema, setSchema] = useState(null);
  const [sheet, setSheet] = useState(null);
  const [activeTab, setActiveTab] = useState('personal');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [showAudit, setShowAudit] = useState(false);
  const [completion, setCompletion] = useState(null);
  const debounceRef = useRef(null);
  const pendingPatchRef = useRef({});

  // Load schema + existing sheet
  useEffect(() => {
    const load = async () => {
      try {
        const [sR, eR] = await Promise.all([
          axios.get(`${API}/info-sheets/schema`, auth()),
          axios.get(`${API}/info-sheets/by-entity?entity_type=${entityType}&entity_id=${entityId}`, auth()),
        ]);
        setSchema(sR.data);
        if (eR.data.exists) {
          setSheet(eR.data.data);
        } else {
          // Auto-create empty sheet
          const cR = await axios.post(`${API}/info-sheets`, {
            entity_type: entityType, entity_id: entityId, case_id: caseId, client_id: clientId,
          }, auth());
          setSheet(cR.data);
        }
      } catch (e) {
        toast.error(e?.response?.data?.detail || 'Failed to load info sheet');
      }
    };
    load();
  }, [entityType, entityId, clientId, caseId]);

  // Debounced auto-save: when `dirty` is true, wait 1s of inactivity then PATCH
  const flushSave = useCallback(async () => {
    if (!sheet?.id || Object.keys(pendingPatchRef.current).length === 0) return;
    setSaving(true);
    try {
      const patch = {...pendingPatchRef.current};
      pendingPatchRef.current = {};
      const r = await axios.patch(`${API}/info-sheets/${sheet.id}`, patch, auth());
      setCompletion(r.data.completion);
      setLastSaved(new Date());
      setDirty(false);
    } catch (e) {
      if (e?.response?.status === 423) {
        toast.error('Info sheet is locked — admin only');
      } else {
        toast.error(e?.response?.data?.detail || 'Auto-save failed');
      }
    }
    setSaving(false);
  }, [sheet?.id]);

  const queueSave = useCallback((sectionKey, value) => {
    if (readOnly) return;
    pendingPatchRef.current[sectionKey] = value;
    setSheet(prev => ({...prev, [sectionKey]: value}));
    setDirty(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(flushSave, SAVE_DEBOUNCE_MS);
  }, [flushSave, readOnly]);

  // Reload sheet after resume upload
  const refetchSheet = useCallback(async () => {
    if (!sheet?.id) return;
    const r = await axios.get(`${API}/info-sheets/${sheet.id}`, auth());
    setSheet(r.data);
  }, [sheet?.id]);

  if (!schema || !sheet) {
    return <Card className="p-8 text-center text-slate-500" data-testid="info-sheet-loading">
      <RefreshCw className="h-5 w-5 mx-auto animate-spin mb-2" />Loading info sheet…
    </Card>;
  }

  const tabs = schema.sections;
  const activeSection = tabs.find(s => s.id === activeTab);
  const locked = sheet.locked;

  return (
    <div className="space-y-3" data-testid="info-sheet-root">
      {/* Header bar */}
      <Card className="p-3 flex justify-between items-center bg-leamss-teal_50 border-leamss-teal/30">
        <div>
          <p className="text-xs font-bold text-leamss-teal flex items-center gap-2">
            <FileText className="h-4 w-4" />Universal Info Sheet · v{schema.schema_version}
            {locked && <Badge className="bg-leamss-red text-white text-[10px]"><Lock className="h-2.5 w-2.5 mr-1" />Locked</Badge>}
          </p>
          <p className="text-[10px] text-slate-500">
            {entityType} · {entityId.slice(0, 10)}…
            {completion && <span className="ml-2 font-bold text-leamss-orange">{completion.personal_percentage}% complete</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-[10px] text-slate-600 flex items-center gap-1">
            {saving && <><RefreshCw className="h-3 w-3 animate-spin" /> Saving…</>}
            {!saving && dirty && <><AlertCircle className="h-3 w-3 text-leamss-orange" /> Unsaved</>}
            {!saving && !dirty && lastSaved && <><CheckCircle2 className="h-3 w-3 text-leamss-teal" /> Saved {lastSaved.toLocaleTimeString().slice(0, 5)}</>}
          </div>
          <Button size="sm" variant="outline" onClick={() => setShowAudit(true)} data-testid="audit-trail-btn">
            <History className="h-3.5 w-3.5 mr-1" />Trail
          </Button>
        </div>
      </Card>

      {/* Tab strip */}
      <div className="flex flex-wrap gap-1 border-b" data-testid="info-sheet-tabs">
        {tabs.map(t => {
          const Icon = TAB_ICONS[t.id] || FileText;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              data-testid={`tab-${t.id}`}
              className={`px-3 py-2 text-xs font-bold flex items-center gap-1.5 border-b-2 transition-colors ${
                isActive ? 'border-leamss-teal text-leamss-teal bg-leamss-teal_50/50' : 'border-transparent text-slate-500 hover:text-leamss-teal'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />{t.title}
            </button>
          );
        })}
      </div>

      {/* Section content */}
      <Card className="p-4" data-testid={`section-${activeTab}`}>
        {activeSection.is_resume_section ? (
          <ResumeSection sheet={sheet} onResumeUpdated={refetchSheet} />
        ) : activeSection.array_field ? (
          <SectionArrayFields
            section={activeSection}
            items={sheet[activeSection.array_field] || []}
            onChange={(v) => queueSave(activeSection.array_field, v)}
          />
        ) : (
          <SectionFlatFields
            section={activeSection}
            value={sheet[activeSection.id] || {}}
            onChange={(v) => queueSave(activeSection.id, v)}
          />
        )}
      </Card>

      {showAudit && <AuditTrailDrawer sheetId={sheet.id} onClose={() => setShowAudit(false)} />}
    </div>
  );
}
