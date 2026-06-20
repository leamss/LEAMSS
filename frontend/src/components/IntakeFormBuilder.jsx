import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Plus, Trash2, Save, Loader2, GripVertical, ChevronDown, ChevronRight,
  FileText, UserCircle, Users, ClipboardList, X
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const FIELD_TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'textarea', label: 'Long Text' },
  { value: 'date', label: 'Date' },
  { value: 'select', label: 'Dropdown' },
  { value: 'file', label: 'File Upload' },
];
const ROLE_OPTIONS = [
  { value: 'client', label: 'Client Only', icon: UserCircle, color: 'bg-blue-100 text-blue-700' },
  { value: 'cm', label: 'CM Only', icon: FileText, color: 'bg-leamss-orange-100 text-leamss-orange-700' },
  { value: 'both', label: 'Both', icon: Users, color: 'bg-emerald-100 text-emerald-700' },
];

const IntakeFormBuilder = ({ token, products = [] }) => {
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [sections, setSections] = useState([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState({});
  const [newOption, setNewOption] = useState({});

  const headers = { Authorization: `Bearer ${token}` };

  const loadForm = async (product) => {
    setSelectedProduct(product);
    setLoading(true);
    try {
      const res = await axios.get(`${API}/intake-forms/product/${product.id}`, { headers });
      if (res.data.exists) {
        setSections(res.data.sections || []);
        const exp = {};
        (res.data.sections || []).forEach(s => { exp[s.id] = true; });
        setExpanded(exp);
      } else {
        setSections([]);
      }
    } catch { setSections([]); }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!selectedProduct) return;
    setSaving(true);
    try {
      await axios.post(`${API}/intake-forms/save`, {
        product_id: selectedProduct.id,
        product_name: selectedProduct.name,
        sections,
      }, { headers });
      toast.success('Intake form saved!');
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
    setSaving(false);
  };

  const addSection = () => {
    const id = `section_${Date.now()}`;
    setSections([...sections, { id, title: 'New Section', fields: [] }]);
    setExpanded({ ...expanded, [id]: true });
  };

  const updateSection = (idx, field, val) => {
    const s = [...sections]; s[idx][field] = val; setSections(s);
  };

  const removeSection = (idx) => {
    if (!window.confirm('Delete this section and all its fields?')) return;
    const s = [...sections]; s.splice(idx, 1); setSections(s);
  };

  const addField = (sIdx) => {
    const s = [...sections];
    s[sIdx].fields.push({
      key: `field_${Date.now()}`, label: '', field_type: 'text',
      options: [], required: false, filled_by: 'client', placeholder: '', help_text: ''
    });
    setSections(s);
  };

  const updateField = (sIdx, fIdx, field, val) => {
    const s = [...sections]; s[sIdx].fields[fIdx][field] = val; setSections(s);
  };

  const removeField = (sIdx, fIdx) => {
    const s = [...sections]; s[sIdx].fields.splice(fIdx, 1); setSections(s);
  };

  const addOption = (sIdx, fIdx) => {
    const optKey = `${sIdx}-${fIdx}`;
    const val = (newOption[optKey] || '').trim();
    if (!val) return;
    const s = [...sections];
    s[sIdx].fields[fIdx].options = [...(s[sIdx].fields[fIdx].options || []), val];
    setSections(s);
    setNewOption({ ...newOption, [optKey]: '' });
  };

  const removeOption = (sIdx, fIdx, oIdx) => {
    const s = [...sections];
    s[sIdx].fields[fIdx].options.splice(oIdx, 1);
    setSections(s);
  };

  const toggleSection = (id) => setExpanded(p => ({ ...p, [id]: !p[id] }));

  const totalFields = sections.reduce((a, s) => a + s.fields.length, 0);
  const clientFields = sections.reduce((a, s) => a + s.fields.filter(f => f.filled_by === 'client' || f.filled_by === 'both').length, 0);
  const cmFields = sections.reduce((a, s) => a + s.fields.filter(f => f.filled_by === 'cm' || f.filled_by === 'both').length, 0);

  return (
    <div className="space-y-5" data-testid="intake-form-builder" style={{ fontFamily: "'IBM Plex Sans', sans-serif" }}>
      {/* Product Selection */}
      {!selectedProduct ? (
        <div>
          <Card className="p-5 bg-gradient-to-r from-[#2a777a] to-[#1e6365] text-white border-0 rounded-xl mb-5">
            <h3 className="text-lg font-bold flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <ClipboardList className="h-5 w-5" /> Intake Form Builder
            </h3>
            <p className="text-white/70 text-sm mt-1">Select a product to build or edit its intake form. Assign fields to Client, CM, or Both.</p>
          </Card>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {products.map(p => (
              <Card key={p.id} className="p-4 border hover:shadow-md hover:border-[#2a777a]/40 transition-all cursor-pointer rounded-xl"
                    onClick={() => loadForm(p)} data-testid={`product-${p.id}`}>
                <h4 className="font-bold text-sm text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>{p.name}</h4>
                <p className="text-xs text-slate-500 mt-1">{p.category || 'Immigration'}</p>
                <Badge variant="outline" className="text-[10px] mt-2">{(p.workflow_steps || []).length} steps</Badge>
              </Card>
            ))}
          </div>
        </div>
      ) : (
        <div>
          {/* Header */}
          <Card className="p-5 bg-gradient-to-r from-[#2a777a] to-[#1e6365] text-white border-0 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>{selectedProduct.name} - Intake Form</h3>
                <div className="flex gap-3 mt-2 text-xs">
                  <span className="bg-white/15 px-2.5 py-1 rounded-lg">{totalFields} total fields</span>
                  <span className="bg-blue-400/30 px-2.5 py-1 rounded-lg">{clientFields} client</span>
                  <span className="bg-leamss-orange-400/30 px-2.5 py-1 rounded-lg">{cmFields} CM</span>
                </div>
              </div>
              <Button variant="outline" className="text-white border-white/30 hover:bg-white/10" onClick={() => setSelectedProduct(null)}>
                Back to Products
              </Button>
            </div>
          </Card>

          {loading ? (
            <div className="p-12 text-center"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a] mx-auto" /></div>
          ) : (
            <>
              {/* Sections */}
              <div className="space-y-4 mt-5">
                {sections.map((section, sIdx) => (
                  <Card key={section.id} className="border rounded-xl overflow-hidden" data-testid={`section-${sIdx}`}>
                    {/* Section Header */}
                    <div className="flex items-center gap-3 p-4 bg-slate-50 cursor-pointer" onClick={() => toggleSection(section.id)}>
                      <GripVertical className="h-4 w-4 text-slate-300 flex-shrink-0" />
                      {expanded[section.id] ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                      <Input value={section.title} onClick={e => e.stopPropagation()}
                             onChange={e => updateSection(sIdx, 'title', e.target.value)}
                             className="font-bold text-sm h-8 border-none bg-transparent shadow-none p-0 focus-visible:ring-0 flex-1"
                             style={{ fontFamily: 'Manrope, sans-serif' }} />
                      <Badge variant="outline" className="text-[10px]">{section.fields.length} fields</Badge>
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-400 hover:text-red-600"
                              onClick={e => { e.stopPropagation(); removeSection(sIdx); }}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>

                    {/* Fields */}
                    {expanded[section.id] && (
                      <div className="p-4 space-y-3 border-t">
                        {section.fields.map((field, fIdx) => {
                          const roleInfo = ROLE_OPTIONS.find(r => r.value === field.filled_by) || ROLE_OPTIONS[0];
                          return (
                            <div key={fIdx} className="p-3 bg-slate-50 rounded-lg border border-slate-200" data-testid={`field-${sIdx}-${fIdx}`}>
                              <div className="grid grid-cols-12 gap-2 items-start">
                                {/* Label */}
                                <div className="col-span-3">
                                  <Label className="text-[9px] font-bold uppercase text-slate-400">Field Label</Label>
                                  <Input value={field.label} onChange={e => updateField(sIdx, fIdx, 'label', e.target.value)}
                                         className="h-8 text-xs mt-0.5 rounded-lg" placeholder="e.g., WES Reference Number" />
                                </div>
                                {/* Key */}
                                <div className="col-span-2">
                                  <Label className="text-[9px] font-bold uppercase text-slate-400">Field Key</Label>
                                  <Input value={field.key} onChange={e => updateField(sIdx, fIdx, 'key', e.target.value)}
                                         className="h-8 text-xs mt-0.5 rounded-lg font-mono" placeholder="field_key" />
                                </div>
                                {/* Type */}
                                <div className="col-span-2">
                                  <Label className="text-[9px] font-bold uppercase text-slate-400">Type</Label>
                                  <Select value={field.field_type} onValueChange={v => updateField(sIdx, fIdx, 'field_type', v)}>
                                    <SelectTrigger className="h-8 text-xs mt-0.5 rounded-lg"><SelectValue /></SelectTrigger>
                                    <SelectContent>{FIELD_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}</SelectContent>
                                  </Select>
                                </div>
                                {/* Filled By */}
                                <div className="col-span-2">
                                  <Label className="text-[9px] font-bold uppercase text-slate-400">Who Fills?</Label>
                                  <Select value={field.filled_by} onValueChange={v => updateField(sIdx, fIdx, 'filled_by', v)}>
                                    <SelectTrigger className="h-8 text-xs mt-0.5 rounded-lg"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                      {ROLE_OPTIONS.map(r => (
                                        <SelectItem key={r.value} value={r.value}>
                                          <span className="flex items-center gap-1.5">{r.label}</span>
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                                {/* Required + Delete */}
                                <div className="col-span-3 flex items-end gap-2 pb-0.5">
                                  <label className="flex items-center gap-1.5 cursor-pointer select-none">
                                    <input type="checkbox" checked={field.required} onChange={e => updateField(sIdx, fIdx, 'required', e.target.checked)} className="rounded h-3.5 w-3.5" />
                                    <span className="text-[10px] font-semibold text-slate-600">Required</span>
                                  </label>
                                  <Badge className={`text-[8px] ${roleInfo.color}`}>{roleInfo.label}</Badge>
                                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600 ml-auto"
                                          onClick={() => removeField(sIdx, fIdx)}>
                                    <X className="h-3 w-3" />
                                  </Button>
                                </div>
                              </div>

                              {/* Dropdown options */}
                              {field.field_type === 'select' && (
                                <div className="mt-2 pl-1">
                                  <Label className="text-[9px] font-bold uppercase text-slate-400">Dropdown Options</Label>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {(field.options || []).map((opt, oIdx) => (
                                      <Badge key={oIdx} variant="outline" className="text-[10px] gap-1 pr-1">
                                        {opt}
                                        <button onClick={() => removeOption(sIdx, fIdx, oIdx)} className="text-red-400 hover:text-red-600"><X className="h-2.5 w-2.5" /></button>
                                      </Badge>
                                    ))}
                                  </div>
                                  <div className="flex gap-1 mt-1">
                                    <Input value={newOption[`${sIdx}-${fIdx}`] || ''} onChange={e => setNewOption({ ...newOption, [`${sIdx}-${fIdx}`]: e.target.value })}
                                           className="h-7 text-xs flex-1 rounded-lg" placeholder="Add option..."
                                           onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addOption(sIdx, fIdx); } }} />
                                    <Button size="sm" variant="outline" className="h-7 text-[10px] rounded-lg" onClick={() => addOption(sIdx, fIdx)}>Add</Button>
                                  </div>
                                </div>
                              )}

                              {/* Help text */}
                              <div className="mt-2">
                                <Input value={field.help_text || ''} onChange={e => updateField(sIdx, fIdx, 'help_text', e.target.value)}
                                       className="h-7 text-[10px] text-slate-500 rounded-lg" placeholder="Help text (optional)" />
                              </div>
                            </div>
                          );
                        })}

                        <Button variant="outline" size="sm" className="w-full border-dashed rounded-lg h-9 text-xs" onClick={() => addField(sIdx)}>
                          <Plus className="h-3.5 w-3.5 mr-1" />Add Field
                        </Button>
                      </div>
                    )}
                  </Card>
                ))}
              </div>

              <Button variant="outline" className="w-full border-dashed rounded-xl h-11 text-sm" onClick={addSection}>
                <Plus className="h-4 w-4 mr-1.5" />Add Section
              </Button>

              {/* Save Bar */}
              {sections.length > 0 && (
                <Card className="p-4 border-0 shadow-xl bg-white sticky bottom-4 rounded-xl">
                  <Button onClick={handleSave} disabled={saving} className="w-full bg-[#2a777a] hover:bg-[#215f62] h-11 rounded-lg font-bold" data-testid="save-form-btn">
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    Save Intake Form ({totalFields} fields)
                  </Button>
                </Card>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default IntakeFormBuilder;
