import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import DashboardShell from '@/components/DashboardShell';
import {
  ArrowLeft, Wand2, Save, FileText, Clock, AlertTriangle, CheckCircle,
  ChevronDown, ChevronRight, Globe, Loader2, Plus, Trash2,
  Lightbulb, ShieldAlert, Sparkles, ExternalLink, DollarSign,
  BookOpen, Download, FileCheck, Search, LayoutGrid, List
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CURRENCY_SYMBOLS = { CAD: 'C$', AUD: 'A$', GBP: '£', USD: '$', NZD: 'NZ$', AED: 'AED', SGD: 'S$' };

const COUNTRY_ICONS = {
  'canada': '🇨🇦', 'australia': '🇦🇺', 'uk': '🇬🇧', 'new zealand': '🇳🇿',
  'usa': '🇺🇸', 'uae': '🇦🇪', 'dubai': '🇦🇪', 'singapore': '🇸🇬', 'student': '🎓',
};

const getCountryIcon = (label) => {
  const lower = label.toLowerCase();
  for (const [key, icon] of Object.entries(COUNTRY_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return '🌍';
};

const AIWorkflowBuilder = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [activeView, setActiveView] = useState('gallery'); // gallery, builder, review, saved
  const [countries, setCountries] = useState([]);
  const [docTemplates, setDocTemplates] = useState([]);
  const [aiTemplates, setAiTemplates] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [customInstructions, setCustomInstructions] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generatedWorkflow, setGeneratedWorkflow] = useState(null);
  const [saving, setSaving] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [editMode, setEditMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [applyingTemplate, setApplyingTemplate] = useState(false);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user') || '{}');
    if (userData.role !== 'admin') { navigate('/'); return; }
    setUser(userData);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [countriesRes, aiTemplatesRes, docTemplatesRes] = await Promise.all([
        axios.get(`${API}/ai-workflow/countries`, getAuthHeader()),
        axios.get(`${API}/ai-workflow/templates`, getAuthHeader()),
        axios.get(`${API}/step-documents/templates`, getAuthHeader()),
      ]);
      setCountries(countriesRes.data);
      setAiTemplates(aiTemplatesRes.data);
      setDocTemplates(docTemplatesRes.data.templates || []);
    } catch (err) {
      toast.error('Failed to load data');
    }
  };

  const handleGenerate = async () => {
    if (!selectedCountry || !selectedService) { toast.error('Select country and service'); return; }
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/ai-workflow/generate`, {
        country: selectedCountry, service_type: selectedService,
        custom_instructions: customInstructions,
      }, getAuthHeader());
      setGeneratedWorkflow(res.data);
      setActiveView('review');
      const expanded = {};
      (res.data.steps || []).forEach((_, i) => { expanded[i] = true; });
      setExpandedSteps(expanded);
      toast.success('Workflow generated!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed');
    }
    setGenerating(false);
  };

  const handleApplyTemplate = async (template) => {
    setApplyingTemplate(true);
    try {
      // Use bulk suggest to get docs for each step
      const res = await axios.post(`${API}/step-documents/ai-suggest-bulk`, {
        product_name: template.label,
        steps: template.steps.map(s => ({ step_name: s })),
      }, getAuthHeader());
      const suggestions = res.data.suggestions || {};

      // Build workflow from template
      const steps = template.steps.map((stepName, i) => ({
        step_name: stepName,
        step_order: i + 1,
        description: '',
        duration_days: 14,
        required_documents: (suggestions[stepName] || []).map(d => ({
          name: d.doc_name, description: d.description || '',
          mandatory: d.is_mandatory !== false, doc_type: d.doc_type || 'other'
        })),
      }));

      setGeneratedWorkflow({
        product_name: template.label,
        description: `Immigration workflow for ${template.label}`,
        category: 'immigration',
        estimated_government_fees: template.fees_info || '',
        steps,
      });

      const expanded = {};
      steps.forEach((_, i) => { expanded[i] = true; });
      setExpandedSteps(expanded);
      setActiveView('review');
      toast.success(`Template "${template.label}" loaded with ${steps.reduce((a, s) => a + s.required_documents.length, 0)} documents!`);
    } catch (err) {
      toast.error('Failed to apply template');
    }
    setApplyingTemplate(false);
  };

  const handleSave = async () => {
    if (!generatedWorkflow) return;
    setSaving(true);
    try {
      const res = await axios.post(`${API}/ai-workflow/save`, {
        product_name: generatedWorkflow.product_name,
        description: generatedWorkflow.description,
        category: generatedWorkflow.category || 'immigration',
        base_fee: 0, commission_rate: 10,
        steps: generatedWorkflow.steps || [],
      }, getAuthHeader());
      toast.success(`"${generatedWorkflow.product_name}" saved with ${res.data.steps_created} steps!`);
      setActiveView('saved');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed');
    }
    setSaving(false);
  };

  const updateStep = (idx, field, value) => {
    const updated = { ...generatedWorkflow };
    updated.steps[idx][field] = value;
    setGeneratedWorkflow(updated);
  };

  const addStep = () => {
    const updated = { ...generatedWorkflow };
    const newOrder = (updated.steps?.length || 0) + 1;
    updated.steps = [...(updated.steps || []), {
      step_name: `New Step ${newOrder}`, step_order: newOrder,
      description: '', duration_days: 7, required_documents: []
    }];
    setGeneratedWorkflow(updated);
    setExpandedSteps({ ...expandedSteps, [updated.steps.length - 1]: true });
  };

  const removeStep = (idx) => {
    const updated = { ...generatedWorkflow };
    updated.steps.splice(idx, 1);
    updated.steps.forEach((s, i) => { s.step_order = i + 1; });
    setGeneratedWorkflow(updated);
  };

  const toggleStep = (idx) => {
    setExpandedSteps(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const filteredTemplates = docTemplates.filter(t =>
    !searchQuery || t.label.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const navGroups = [
    { id: 'back', icon: ArrowLeft, label: 'Back to Dashboard', onClick: () => navigate('/admin') },
  ];

  if (!user) return null;

  return (
    <DashboardShell
      user={user} roleLabel="Admin" navGroups={navGroups}
      activeTab="ai-workflow" pageTitle="AI Workflow Builder"
      showBackButton={activeView !== 'gallery'}
      onBack={() => {
        if (activeView === 'review' || activeView === 'saved') setActiveView('builder');
        else if (activeView === 'builder') setActiveView('gallery');
      }}
      onLogout={() => { localStorage.clear(); navigate('/'); }}
    >
      {/* ===== GALLERY VIEW ===== */}
      {activeView === 'gallery' && (
        <div className="space-y-6" data-testid="workflow-gallery">
          {/* Hero */}
          <Card className="p-6 bg-gradient-to-r from-[#2a777a] to-[#1a5c5e] text-white border-0 shadow-xl overflow-hidden relative">
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-2">
                <Wand2 className="h-7 w-7" />
                <h2 className="text-xl font-bold">AI Workflow Builder</h2>
              </div>
              <p className="text-white/80 text-sm max-w-xl">Create complete immigration workflows from verified government templates or generate custom ones with AI. Includes real document requirements, fees, and assessment body details.</p>
              <div className="flex gap-3 mt-4">
                <Button size="sm" className="bg-white text-[#2a777a] hover:bg-white/90" onClick={() => setActiveView('builder')} data-testid="custom-workflow-btn">
                  <Sparkles className="h-4 w-4 mr-1.5" />Custom AI Workflow
                </Button>
              </div>
            </div>
          </Card>

          {/* Template Gallery */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-800">Verified Templates</h3>
                <p className="text-xs text-slate-500">{docTemplates.length} templates with real government requirements & fees</p>
              </div>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input className="pl-9 h-9 text-sm" placeholder="Search templates..."
                       value={searchQuery} onChange={e => setSearchQuery(e.target.value)} data-testid="template-search" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filteredTemplates.map((tmpl) => (
                <Card key={tmpl.id} className={`overflow-hidden border hover:shadow-lg transition-all cursor-pointer group ${selectedTemplate?.id === tmpl.id ? 'ring-2 ring-[#2a777a] border-[#2a777a]' : 'border-slate-200'}`}
                      onClick={() => setSelectedTemplate(selectedTemplate?.id === tmpl.id ? null : tmpl)}
                      data-testid={`template-card-${tmpl.id}`}>
                  <div className="p-4">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl flex-shrink-0">{getCountryIcon(tmpl.label)}</span>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-sm text-slate-800 leading-tight group-hover:text-[#2a777a] transition-colors">{tmpl.label}</h4>
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          <Badge variant="outline" className="text-[10px]">{tmpl.steps.length} steps</Badge>
                          <Badge variant="outline" className="text-[10px]">{tmpl.total_documents} docs</Badge>
                        </div>
                      </div>
                    </div>

                    {/* Fees */}
                    {tmpl.fees_info && (
                      <div className="mt-3 p-2.5 bg-slate-50 rounded-lg">
                        <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1 flex items-center gap-1"><DollarSign className="h-3 w-3" />Government Fees</p>
                        <p className="text-xs text-slate-700 leading-relaxed">{tmpl.fees_info}</p>
                      </div>
                    )}

                    {/* Steps Preview */}
                    <div className="mt-3">
                      <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1.5">Workflow Steps</p>
                      <div className="space-y-1">
                        {tmpl.steps.map((stepName, si) => (
                          <div key={si} className="flex items-center gap-2 text-xs text-slate-600">
                            <span className="w-4 h-4 rounded-full bg-[#2a777a]/10 text-[#2a777a] flex items-center justify-center text-[9px] font-bold flex-shrink-0">{si + 1}</span>
                            <span className="truncate">{stepName}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Assessment Bodies */}
                    {tmpl.assessment_bodies?.length > 0 && (
                      <div className="mt-3">
                        <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1">Assessment Bodies</p>
                        <div className="flex flex-wrap gap-1">
                          {tmpl.assessment_bodies.map((ab, i) => (
                            <Badge key={i} className="text-[9px] bg-blue-50 text-blue-700 border-blue-200">{ab}</Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Government URL */}
                    {tmpl.government_url && (
                      <a href={tmpl.government_url} target="_blank" rel="noopener noreferrer"
                         className="mt-3 flex items-center gap-1 text-[10px] text-[#2a777a] hover:underline"
                         onClick={e => e.stopPropagation()}>
                        <ExternalLink className="h-3 w-3" /> Official Government Source
                      </a>
                    )}

                    {/* Apply Button */}
                    <Button className="w-full mt-3 bg-[#2a777a] hover:bg-[#236466] text-sm h-9"
                            disabled={applyingTemplate}
                            onClick={(e) => { e.stopPropagation(); handleApplyTemplate(tmpl); }}
                            data-testid={`apply-template-${tmpl.id}`}>
                      {applyingTemplate ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <FileCheck className="h-4 w-4 mr-1.5" />}
                      Use This Template
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ===== BUILDER VIEW ===== */}
      {activeView === 'builder' && (
        <div className="space-y-6" data-testid="workflow-builder">
          <Card className="p-6 border border-slate-200">
            <h3 className="font-bold text-slate-900 mb-1">Custom AI Workflow</h3>
            <p className="text-xs text-slate-500 mb-4">Generate a custom workflow for any country and visa type using AI</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <Label className="text-sm">Country</Label>
                <Select value={selectedCountry} onValueChange={setSelectedCountry}>
                  <SelectTrigger data-testid="country-select"><SelectValue placeholder="Select Country" /></SelectTrigger>
                  <SelectContent>
                    {countries.map(c => <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-sm">Service / Visa Type</Label>
                <Input value={selectedService} onChange={(e) => setSelectedService(e.target.value)}
                       placeholder="e.g., PR, Visitor, Student, Work Permit" data-testid="service-input" />
              </div>
            </div>
            <div className="mb-4">
              <Label className="text-sm">Custom Instructions (Optional)</Label>
              <Textarea value={customInstructions} onChange={(e) => setCustomInstructions(e.target.value)}
                        placeholder="e.g., Include IELTS prep step, focus on skilled worker stream, add estimated processing times..."
                        rows={3} data-testid="custom-instructions" />
            </div>
            <Button onClick={handleGenerate} disabled={generating || !selectedCountry || !selectedService}
                    className="w-full bg-[#f7620b] hover:bg-[#e55a09]" data-testid="generate-btn">
              {generating ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />AI is generating...</> : <><Wand2 className="h-4 w-4 mr-2" />Generate Workflow</>}
            </Button>
          </Card>
          {generating && (
            <Card className="p-8 text-center border border-[#2a777a]/20 bg-[#2a777a]/5">
              <Loader2 className="h-12 w-12 mx-auto mb-4 text-[#2a777a] animate-spin" />
              <p className="text-lg font-semibold text-slate-800">AI analyzing immigration requirements...</p>
              <p className="text-sm text-slate-500 mt-1">Referencing official sources for {selectedCountry} {selectedService}</p>
            </Card>
          )}

          {/* Quick Templates row */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Or use a verified template</p>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {docTemplates.slice(0, 6).map(t => (
                <Button key={t.id} variant="outline" size="sm" className="flex-shrink-0 text-xs h-8"
                        onClick={() => handleApplyTemplate(t)} disabled={applyingTemplate}>
                  <span className="mr-1.5">{getCountryIcon(t.label)}</span>{t.label.split('(')[0].trim()}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ===== REVIEW VIEW ===== */}
      {activeView === 'review' && generatedWorkflow && (
        <div className="space-y-4" data-testid="workflow-review">
          {/* Header */}
          <Card className="p-5 border-0 shadow-md">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                {editMode ? (
                  <Input value={generatedWorkflow.product_name} className="text-lg font-bold mb-1"
                         onChange={(e) => setGeneratedWorkflow({ ...generatedWorkflow, product_name: e.target.value })} />
                ) : (
                  <h2 className="text-lg font-bold text-slate-900">{generatedWorkflow.product_name}</h2>
                )}
                <p className="text-sm text-slate-500">{generatedWorkflow.description}</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setEditMode(!editMode)}>
                {editMode ? 'Done' : 'Edit'}
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {generatedWorkflow.estimated_total_duration_days && (
                <Badge variant="outline" className="text-xs"><Clock className="h-3 w-3 mr-1" />~{generatedWorkflow.estimated_total_duration_days} days</Badge>
              )}
              <Badge className="bg-[#2a777a] text-white text-xs">{(generatedWorkflow.steps || []).length} steps</Badge>
              <Badge variant="outline" className="text-xs">{(generatedWorkflow.steps || []).reduce((a, s) => a + (s.required_documents?.length || 0), 0)} documents</Badge>
            </div>
          </Card>

          {/* Fee Calculator */}
          {generatedWorkflow.estimated_government_fees && (
            <Card className="p-4 border-l-4 border-l-amber-400 bg-amber-50/50" data-testid="fee-calculator">
              <h4 className="font-semibold text-sm text-amber-800 mb-1.5 flex items-center gap-1.5">
                <DollarSign className="h-4 w-4" /> Government Fees Breakdown
              </h4>
              <p className="text-sm text-amber-700 leading-relaxed">{generatedWorkflow.estimated_government_fees}</p>
            </Card>
          )}

          {/* Tips */}
          {generatedWorkflow.success_tips?.length > 0 && (
            <Card className="p-4 border border-green-200 bg-green-50/50">
              <h4 className="font-semibold text-sm text-green-800 mb-2 flex items-center gap-1.5"><Lightbulb className="h-4 w-4" />Tips</h4>
              <ul className="space-y-1">
                {generatedWorkflow.success_tips.map((tip, i) => (
                  <li key={i} className="text-xs text-green-700 flex items-start gap-1.5">
                    <CheckCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />{tip}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {generatedWorkflow.common_rejection_reasons?.length > 0 && (
            <Card className="p-4 border border-red-200 bg-red-50/50">
              <h4 className="font-semibold text-sm text-red-800 mb-2 flex items-center gap-1.5"><ShieldAlert className="h-4 w-4" />Common Rejection Reasons</h4>
              <ul className="space-y-1">
                {generatedWorkflow.common_rejection_reasons.map((r, i) => (
                  <li key={i} className="text-xs text-red-700 flex items-start gap-1.5">
                    <AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />{r}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Steps */}
          <div className="space-y-3">
            {(generatedWorkflow.steps || []).map((s, idx) => (
              <Card key={idx} className="border border-slate-200 overflow-hidden" data-testid={`review-step-${idx}`}>
                <div className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => toggleStep(idx)}>
                  <div className="h-8 w-8 rounded-lg bg-[#2a777a] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">{s.step_order}</div>
                  <div className="flex-1 min-w-0">
                    {editMode ? (
                      <Input value={s.step_name} className="font-semibold text-sm h-8" onClick={e => e.stopPropagation()}
                             onChange={e => updateStep(idx, 'step_name', e.target.value)} />
                    ) : (
                      <h4 className="font-semibold text-sm text-slate-900">{s.step_name}</h4>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5">
                    {s.duration_days && <Badge variant="outline" className="text-[10px]"><Clock className="h-3 w-3 mr-0.5" />{s.duration_days}d</Badge>}
                    <Badge variant="outline" className="text-[10px]">{(s.required_documents || []).length} docs</Badge>
                    {editMode && (
                      <Button variant="ghost" size="sm" className="text-red-500 h-6 w-6 p-0" onClick={e => { e.stopPropagation(); removeStep(idx); }}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    {expandedSteps[idx] ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                  </div>
                </div>
                {expandedSteps[idx] && (
                  <div className="px-3 pb-3 pt-0 border-t border-slate-100">
                    {s.description && <p className="text-xs text-slate-600 mb-2">{s.description}</p>}
                    {s.important_notes && (
                      <div className="bg-amber-50 border border-amber-200 rounded p-2 mb-2">
                        <p className="text-[11px] text-amber-800"><AlertTriangle className="h-3 w-3 inline mr-1" />{s.important_notes}</p>
                      </div>
                    )}
                    {s.government_fees && (
                      <p className="text-[11px] text-slate-500 mb-2">Fees: <span className="font-semibold">{s.government_fees}</span></p>
                    )}
                    {(s.required_documents || []).length > 0 && (
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1.5">Required Documents</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                          {s.required_documents.map((doc, di) => (
                            <div key={di} className="flex items-start gap-2 p-2 bg-slate-50 rounded text-xs">
                              <FileText className="h-3.5 w-3.5 text-[#2a777a] mt-0.5 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-slate-800">{doc.name || doc.doc_name || doc}</p>
                                {doc.description && <p className="text-[10px] text-slate-500">{doc.description}</p>}
                              </div>
                              <Badge className={`text-[8px] flex-shrink-0 ${(doc.mandatory || doc.is_mandatory) ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>
                                {(doc.mandatory || doc.is_mandatory) ? 'Required' : 'Optional'}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>

          {editMode && (
            <Button variant="outline" className="w-full border-dashed text-sm" onClick={addStep}>
              <Plus className="h-4 w-4 mr-1.5" />Add Step
            </Button>
          )}

          {/* Save Bar */}
          <Card className="p-4 border-0 shadow-lg bg-white sticky bottom-4">
            <div className="flex items-center gap-3">
              <Button onClick={handleSave} disabled={saving} className="flex-1 bg-[#2a777a] hover:bg-[#236466]" data-testid="save-workflow-btn">
                {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                Save as Product
              </Button>
              <Button variant="outline" onClick={() => { setActiveView('builder'); setGeneratedWorkflow(null); }}>
                Regenerate
              </Button>
              <Button variant="outline" onClick={() => { setActiveView('gallery'); setGeneratedWorkflow(null); }}>
                Templates
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* ===== SAVED VIEW ===== */}
      {activeView === 'saved' && (
        <div className="text-center py-12" data-testid="workflow-saved">
          <div className="w-20 h-20 mx-auto mb-6 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle className="h-10 w-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Workflow Saved!</h2>
          <p className="text-slate-500 mb-6">"{generatedWorkflow?.product_name}" saved as a product with all steps and document requirements.</p>
          <div className="flex justify-center gap-3">
            <Button onClick={() => { setActiveView('gallery'); setGeneratedWorkflow(null); setSelectedCountry(''); setSelectedService(''); }}
                    className="bg-[#2a777a] hover:bg-[#236466]">
              <Plus className="h-4 w-4 mr-2" />Create Another
            </Button>
            <Button variant="outline" onClick={() => navigate('/admin')}>
              Back to Dashboard
            </Button>
          </div>
        </div>
      )}
    </DashboardShell>
  );
};

export default AIWorkflowBuilder;
