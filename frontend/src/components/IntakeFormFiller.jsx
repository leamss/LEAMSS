import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Save, Loader2, ChevronDown, ChevronRight, ClipboardList,
  UserCircle, FileText, Users, Lock, CheckCircle, Clock, Info
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLE_BADGE = {
  client: { label: 'Client', color: 'bg-blue-100 text-blue-700', icon: UserCircle },
  cm: { label: 'Case Manager', color: 'bg-leamss-orange-100 text-leamss-orange-700', icon: FileText },
  both: { label: 'Both', color: 'bg-emerald-100 text-emerald-700', icon: Users },
};

const IntakeFormFiller = ({ token, caseId, role = 'client', caseName = '' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formValues, setFormValues] = useState({});
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [dirty, setDirty] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = useCallback(async () => {
    if (!caseId) { setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/intake-forms/case/${caseId}`, { headers });
      setData(res.data);
      // Build form values from existing data
      const vals = {};
      for (const section of (res.data.sections || [])) {
        for (const field of (section.fields || [])) {
          if (field.value !== undefined && field.value !== '') vals[field.key] = field.value;
        }
      }
      setFormValues(vals);
      // Auto-expand first section
      if (res.data.sections?.length > 0) setExpanded({ [res.data.sections[0].id]: true });
    } catch (e) { console.error('Failed to load intake form', e); }
    setLoading(false);
  }, [caseId]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleChange = (key, val) => {
    setFormValues(prev => ({ ...prev, [key]: val }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await axios.post(`${API}/intake-forms/case/save`, { case_id: caseId, data: formValues }, { headers });
      toast.success(`${res.data.updated_fields?.length || 0} field(s) saved!`);
      setDirty(false);
      loadData(); // Refresh to get updated meta
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
    setSaving(false);
  };

  const toggleSection = (id) => setExpanded(p => ({ ...p, [id]: !p[id] }));

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  if (!data?.has_form) {
    return (
      <Card className="p-12 text-center border-0 shadow-sm" data-testid="no-intake-form">
        <ClipboardList className="h-12 w-12 text-slate-200 mx-auto mb-3" />
        <p className="font-semibold text-slate-600" style={{ fontFamily: 'Manrope, sans-serif' }}>No Intake Form Available</p>
        <p className="text-sm text-slate-400 mt-1">Admin has not created an intake form for this product yet.</p>
      </Card>
    );
  }

  const sections = data.sections || [];
  const totalFields = sections.reduce((a, s) => a + s.fields.length, 0);
  const filledFields = sections.reduce((a, s) => a + s.fields.filter(f => formValues[f.key]).length, 0);
  const myEditableFields = sections.reduce((a, s) => a + s.fields.filter(f => f.editable).length, 0);
  const completionPct = totalFields > 0 ? Math.round((filledFields / totalFields) * 100) : 0;

  return (
    <div className="space-y-5" data-testid="intake-form-filler" style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}>
      {/* Header */}
      <Card className="overflow-hidden border-0 shadow-lg" data-testid="intake-header">
        <div className="bg-gradient-to-r from-[#2a777a] to-[#1e6365] p-5 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
                <ClipboardList className="h-5 w-5" /> Case Intake Form
              </h3>
              <p className="text-white/70 text-sm mt-0.5">{data.product_name} {caseName ? `- ${caseName}` : ''}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">{completionPct}%</p>
              <p className="text-white/70 text-xs">{filledFields}/{totalFields} filled</p>
            </div>
          </div>
          <div className="w-full bg-white/20 rounded-full h-2 mt-3">
            <div className="bg-white rounded-full h-2 transition-all duration-700" style={{ width: `${completionPct}%` }} />
          </div>
        </div>
        <div className="grid grid-cols-3 divide-x bg-white">
          <div className="p-3 text-center">
            <p className="text-lg font-bold text-slate-800">{totalFields}</p>
            <p className="text-[10px] text-slate-500">Total Fields</p>
          </div>
          <div className="p-3 text-center">
            <p className="text-lg font-bold text-emerald-600">{filledFields}</p>
            <p className="text-[10px] text-slate-500">Filled</p>
          </div>
          <div className="p-3 text-center">
            <p className="text-lg font-bold text-blue-600">{myEditableFields}</p>
            <p className="text-[10px] text-slate-500">Your Fields</p>
          </div>
        </div>
      </Card>

      {/* Role Legend */}
      <div className="flex gap-2 items-center flex-wrap">
        <span className="text-[10px] text-slate-500 font-semibold uppercase">Legend:</span>
        <Badge className="bg-blue-100 text-blue-700 text-[9px]"><UserCircle className="h-3 w-3 mr-0.5" />Client fills</Badge>
        <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-[9px]"><FileText className="h-3 w-3 mr-0.5" />CM fills</Badge>
        <Badge className="bg-emerald-100 text-emerald-700 text-[9px]"><Users className="h-3 w-3 mr-0.5" />Both can fill</Badge>
        <Badge className="bg-slate-100 text-slate-500 text-[9px]"><Lock className="h-3 w-3 mr-0.5" />Read-only for you</Badge>
      </div>

      {/* Sections */}
      {sections.map((section, sIdx) => {
        const sectionFilled = section.fields.filter(f => formValues[f.key]).length;
        const sectionTotal = section.fields.length;
        return (
          <Card key={section.id} className="border rounded-xl overflow-hidden" data-testid={`intake-section-${sIdx}`}>
            <button onClick={() => toggleSection(section.id)}
                    className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors">
              <div className="flex items-center gap-2.5">
                {expanded[section.id] ? <ChevronDown className="h-4 w-4 text-[#2a777a]" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                <h4 className="font-bold text-sm text-slate-800" style={{ fontFamily: 'Manrope, sans-serif' }}>{section.title}</h4>
                <Badge variant="outline" className="text-[10px]">{sectionFilled}/{sectionTotal}</Badge>
              </div>
              {sectionFilled === sectionTotal && sectionTotal > 0 && <CheckCircle className="h-4 w-4 text-emerald-500" />}
            </button>

            {expanded[section.id] && (
              <div className="px-5 pb-5 border-t">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
                  {section.fields.map((field, fIdx) => {
                    const roleBadge = ROLE_BADGE[field.filled_by] || ROLE_BADGE.client;
                    const isEditable = field.editable;
                    const isFilled = formValues[field.key];
                    const filledByOther = field.filled_by_user && field.filled_by_role && field.filled_by_role !== role;

                    return (
                      <div key={fIdx} className={`space-y-1.5 p-3 rounded-lg ${isEditable ? 'bg-white border' : 'bg-slate-50 border border-slate-200'}`}
                           data-testid={`intake-field-${field.key}`}>
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-semibold text-slate-700 flex items-center gap-1">
                            {field.label}
                            {field.required && <span className="text-red-500">*</span>}
                          </label>
                          <div className="flex items-center gap-1">
                            <Badge className={`text-[8px] ${roleBadge.color}`}>{roleBadge.label}</Badge>
                            {!isEditable && <Lock className="h-3 w-3 text-slate-400" />}
                          </div>
                        </div>

                        {field.help_text && <p className="text-[10px] text-slate-400 flex items-center gap-1"><Info className="h-3 w-3" />{field.help_text}</p>}

                        {/* Field Input */}
                        {isEditable ? (
                          <>
                            {field.field_type === 'text' && (
                              <Input value={formValues[field.key] || ''} onChange={e => handleChange(field.key, e.target.value)}
                                     placeholder={field.placeholder || field.label} className="h-9 text-sm rounded-lg" />
                            )}
                            {field.field_type === 'textarea' && (
                              <Textarea value={formValues[field.key] || ''} onChange={e => handleChange(field.key, e.target.value)}
                                        placeholder={field.placeholder || field.label} rows={2} className="text-sm rounded-lg" />
                            )}
                            {field.field_type === 'date' && (
                              <Input type="date" value={formValues[field.key] || ''} onChange={e => handleChange(field.key, e.target.value)}
                                     className="h-9 text-sm rounded-lg" />
                            )}
                            {field.field_type === 'select' && (
                              <Select value={formValues[field.key] || ''} onValueChange={v => handleChange(field.key, v)}>
                                <SelectTrigger className="h-9 text-sm rounded-lg"><SelectValue placeholder="Select..." /></SelectTrigger>
                                <SelectContent>{(field.options || []).map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
                              </Select>
                            )}
                            {field.field_type === 'file' && (
                              <Input type="file" className="text-sm rounded-lg" onChange={e => handleChange(field.key, e.target.files?.[0]?.name || '')} />
                            )}
                          </>
                        ) : (
                          <div className="p-2.5 bg-slate-100 rounded-lg min-h-[36px] flex items-center">
                            {isFilled ? (
                              <span className="text-sm text-slate-800">{formValues[field.key]}</span>
                            ) : (
                              <span className="text-sm text-slate-400 italic">Not filled yet</span>
                            )}
                          </div>
                        )}

                        {/* Filled by info */}
                        {filledByOther && field.filled_by_user && (
                          <p className="text-[10px] text-emerald-600 flex items-center gap-1">
                            <CheckCircle className="h-3 w-3" />
                            Updated by {field.filled_by_user}
                            {field.filled_at && ` on ${new Date(field.filled_at).toLocaleDateString()}`}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </Card>
        );
      })}

      {/* Save Bar */}
      {myEditableFields > 0 && (
        <Card className="p-4 border-0 shadow-xl bg-white sticky bottom-4 rounded-xl">
          <Button onClick={handleSave} disabled={saving || !dirty}
                  className={`w-full h-11 rounded-lg font-bold ${dirty ? 'bg-[#2a777a] hover:bg-[#215f62]' : 'bg-slate-300'}`}
                  data-testid="save-intake-btn">
            {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            {dirty ? 'Save Changes' : 'No Changes'}
          </Button>
        </Card>
      )}
    </div>
  );
};

export default IntakeFormFiller;
