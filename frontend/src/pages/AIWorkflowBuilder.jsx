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
import DashboardShell from '@/components/DashboardShell';
import {
  ArrowLeft, Wand2, Save, FileText, Clock, AlertTriangle, CheckCircle,
  ChevronDown, ChevronRight, Globe, Loader2, Plus, Trash2,
  Lightbulb, ShieldAlert, Sparkles, ExternalLink, DollarSign,
  Search, FileCheck, Edit3, X, Download
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_ICONS = {
  'argentina':'🇦🇷','australia':'🇦🇺','austria':'🇦🇹','bahrain':'🇧🇭','belgium':'🇧🇪',
  'brazil':'🇧🇷','canada':'🇨🇦','chile':'🇨🇱','china':'🇨🇳','colombia':'🇨🇴',
  'costa rica':'🇨🇷','czech republic':'🇨🇿','denmark':'🇩🇰','egypt':'🇪🇬','finland':'🇫🇮',
  'france':'🇫🇷','germany':'🇩🇪','greece':'🇬🇷','hong kong':'🇭🇰','india':'🇮🇳',
  'indonesia':'🇮🇩','ireland':'🇮🇪','italy':'🇮🇹','japan':'🇯🇵','kenya':'🇰🇪',
  'malaysia':'🇲🇾','mauritius':'🇲🇺','mexico':'🇲🇽','netherlands':'🇳🇱','new zealand':'🇳🇿',
  'nigeria':'🇳🇬','norway':'🇳🇴','oman':'🇴🇲','panama':'🇵🇦','philippines':'🇵🇭',
  'poland':'🇵🇱','portugal':'🇵🇹','qatar':'🇶🇦','saudi arabia':'🇸🇦','singapore':'🇸🇬',
  'south africa':'🇿🇦','south korea':'🇰🇷','spain':'🇪🇸','sweden':'🇸🇪','switzerland':'🇨🇭',
  'thailand':'🇹🇭','turkey':'🇹🇷','uae':'🇦🇪','uk':'🇬🇧','usa':'🇺🇸','vietnam':'🇻🇳',
  'student':'🎓',
};
const getIcon = (label) => {
  const l = label.toLowerCase();
  for (const [k, v] of Object.entries(COUNTRY_ICONS)) { if (l.includes(k)) return v; }
  return '🌍';
};

const AIWorkflowBuilder = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [view, setView] = useState('gallery'); // gallery | pick-visa | builder | review | saved
  const [countries, setCountries] = useState([]);
  const [docTemplates, setDocTemplates] = useState([]);
  const [searchQ, setSearchQ] = useState('');

  // Country -> Visa flow
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [visaCategories, setVisaCategories] = useState([]);
  const [loadingVisa, setLoadingVisa] = useState(false);
  const [selectedVisa, setSelectedVisa] = useState(null);
  const [customInstructions, setCustomInstructions] = useState('');

  // Generation
  const [generating, setGenerating] = useState(false);
  const [workflow, setWorkflow] = useState(null);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [saving, setSaving] = useState(false);
  const [applyingTemplate, setApplyingTemplate] = useState(false);

  // Inline editing
  const [editingDoc, setEditingDoc] = useState(null); // {stepIdx, docIdx}
  const [newDocForm, setNewDocForm] = useState({ stepIdx: null, name: '', description: '', mandatory: true });
  const [govForms, setGovForms] = useState([]);
  const [verified, setVerified] = useState(false);
  const [workflowSource, setWorkflowSource] = useState(''); // 'ai' or 'template'

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const loadGovForms = async (countryName) => {
    try {
      const res = await axios.get(`${API}/step-documents/government-forms/${encodeURIComponent(countryName)}`, auth());
      setGovForms(res.data.forms || []);
    } catch { setGovForms([]); }
  };

  useEffect(() => {
    const u = JSON.parse(localStorage.getItem('user') || '{}');
    if (u.role !== 'admin') { navigate('/'); return; }
    setUser(u);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [cRes, tRes] = await Promise.all([
        axios.get(`${API}/ai-workflow/countries`, auth()),
        axios.get(`${API}/step-documents/templates`, auth()),
      ]);
      setCountries(cRes.data);
      setDocTemplates(tRes.data.templates || []);
    } catch { toast.error('Failed to load data'); }
  };

  // Country -> Visa categories
  const selectCountry = async (country) => {
    setSelectedCountry(country);
    setVisaCategories([]);
    setSelectedVisa(null);
    setLoadingVisa(true);
    setView('pick-visa');
    try {
      const res = await axios.post(`${API}/ai-workflow/visa-categories`, { country: country.name }, auth());
      const aiCats = res.data.categories || [];
      setVisaCategories(aiCats);
    } catch { toast.error('Failed to load visa categories'); }
    setLoadingVisa(false);
  };

  // Generate workflow for selected visa
  const generateWorkflow = async (visaName) => {
    setGenerating(true);
    setView('review');
    try {
      const res = await axios.post(`${API}/ai-workflow/generate`, {
        country: selectedCountry.name,
        service_type: visaName || selectedVisa?.name || '',
        custom_instructions: customInstructions,
      }, auth());
      setWorkflow(res.data);
      const exp = {};
      (res.data.steps || []).forEach((_, i) => { exp[i] = true; });
      setExpandedSteps(exp);
      toast.success('Workflow generated!');
      setWorkflowSource('ai');
      setVerified(false);
      if (selectedCountry?.name) loadGovForms(selectedCountry.name);
    } catch (e) { toast.error(e.response?.data?.detail || 'Generation failed'); setView('pick-visa'); }
    setGenerating(false);
  };

  // Apply doc template
  const applyTemplate = async (tmpl) => {
    setApplyingTemplate(true);
    try {
      const res = await axios.post(`${API}/step-documents/ai-suggest-bulk`, {
        product_name: tmpl.label,
        steps: tmpl.steps.map(s => ({ step_name: s })),
      }, auth());
      const suggs = res.data.suggestions || {};
      const steps = tmpl.steps.map((sn, i) => ({
        step_name: sn, step_order: i + 1, description: '', duration_days: 14,
        required_documents: (suggs[sn] || []).map(d => ({
          name: d.doc_name, description: d.description || '',
          mandatory: d.is_mandatory !== false, doc_type: d.doc_type || 'other'
        })),
      }));
      setWorkflow({
        product_name: tmpl.label,
        description: `Immigration workflow for ${tmpl.label}`,
        category: 'immigration',
        estimated_government_fees: tmpl.fees_info || '',
        steps,
      });
      const exp = {}; steps.forEach((_, i) => { exp[i] = true; }); setExpandedSteps(exp);
      setView('review');
      setWorkflowSource('template');
      setVerified(false);
      toast.success(`Template loaded with ${steps.reduce((a, s) => a + s.required_documents.length, 0)} documents!`);
      // Load government forms for this country
      const countryName = tmpl.label.split(' ')[0]; // "Canada", "Australia", etc.
      loadGovForms(countryName);
    } catch { toast.error('Failed to apply template'); }
    setApplyingTemplate(false);
  };

  // Save
  const handleSave = async () => {
    if (!workflow) return;
    setSaving(true);
    try {
      const res = await axios.post(`${API}/ai-workflow/save`, {
        product_name: workflow.product_name, description: workflow.description,
        category: workflow.category || 'immigration', base_fee: 0, commission_rate: 10,
        steps: workflow.steps || [],
      }, auth());
      toast.success(`"${workflow.product_name}" saved with ${res.data.steps_created} steps!`);
      setView('saved');
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
    setSaving(false);
  };

  // Edit helpers
  const updateField = (field, val) => setWorkflow({ ...workflow, [field]: val });
  const updateStep = (idx, field, val) => {
    const w = { ...workflow }; w.steps[idx][field] = val; setWorkflow(w);
  };
  const addStep = () => {
    const w = { ...workflow };
    const n = (w.steps?.length || 0) + 1;
    w.steps = [...(w.steps || []), { step_name: `New Step ${n}`, step_order: n, description: '', duration_days: 7, required_documents: [] }];
    setWorkflow(w); setExpandedSteps({ ...expandedSteps, [w.steps.length - 1]: true });
  };
  const removeStep = (idx) => {
    const w = { ...workflow }; w.steps.splice(idx, 1);
    w.steps.forEach((s, i) => { s.step_order = i + 1; }); setWorkflow(w);
  };
  const addDoc = (stepIdx) => {
    if (!newDocForm.name.trim()) { toast.error('Enter document name'); return; }
    const w = { ...workflow };
    w.steps[stepIdx].required_documents.push({ name: newDocForm.name, description: newDocForm.description, mandatory: newDocForm.mandatory });
    setWorkflow(w); setNewDocForm({ stepIdx: null, name: '', description: '', mandatory: true });
  };
  const removeDoc = (stepIdx, docIdx) => {
    const w = { ...workflow }; w.steps[stepIdx].required_documents.splice(docIdx, 1); setWorkflow(w);
  };
  const updateDoc = (stepIdx, docIdx, field, val) => {
    const w = { ...workflow }; w.steps[stepIdx].required_documents[docIdx][field] = val; setWorkflow(w);
  };
  const toggleStep = (i) => setExpandedSteps(p => ({ ...p, [i]: !p[i] }));

  const filteredTemplates = docTemplates.filter(t => !searchQ || t.label.toLowerCase().includes(searchQ.toLowerCase()));
  const filteredCountries = countries.filter(c => !searchQ || c.name.toLowerCase().includes(searchQ.toLowerCase()));

  if (!user) return null;

  return (
    <DashboardShell user={user} roleLabel="Admin" activeTab="ai-workflow" pageTitle="AI Workflow Builder"
      navGroups={[{ id: 'back', icon: ArrowLeft, label: 'Back to Dashboard', onClick: () => navigate('/admin') }]}
      showBackButton={view !== 'gallery'}
      onBack={() => { if (view === 'review' || view === 'saved') setView('pick-visa'); else if (view === 'pick-visa' || view === 'builder') setView('gallery'); }}
      onLogout={() => { localStorage.clear(); navigate('/'); }}>

      {/* ===== GALLERY ===== */}
      {view === 'gallery' && (
        <div className="space-y-6" data-testid="workflow-gallery">
          <Card className="p-5 bg-gradient-to-r from-[#2a777a] to-[#1a5c5e] text-white border-0 shadow-xl">
            <div className="flex items-center gap-3 mb-2"><Wand2 className="h-6 w-6" /><h2 className="text-lg font-bold">AI Workflow Builder</h2></div>
            <p className="text-white/80 text-sm max-w-xl">Select a country to see all visa categories, or use a verified template. Generate complete workflows with real documents, fees & government references.</p>
          </Card>

          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-800">Select Country ({countries.length} countries)</h3>
            <div className="relative w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input className="pl-9 h-9 text-sm" placeholder="Search countries or templates..." value={searchQ} onChange={e => setSearchQ(e.target.value)} data-testid="search-input" />
            </div>
          </div>

          {/* Country Grid */}
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
            {filteredCountries.map(c => (
              <Card key={c.id} className="p-3 text-center cursor-pointer hover:shadow-md hover:border-[#2a777a]/40 transition-all border"
                    onClick={() => selectCountry(c)} data-testid={`country-${c.id}`}>
                <span className="text-2xl block mb-1">{getIcon(c.name)}</span>
                <p className="text-xs font-medium text-slate-800 leading-tight">{c.name}</p>
                <p className="text-[10px] text-slate-500">{c.services.length} types</p>
              </Card>
            ))}
          </div>

          {/* Verified Templates */}
          {filteredTemplates.length > 0 && (
            <div>
              <h3 className="text-base font-bold text-slate-800 mb-3">Verified Templates ({filteredTemplates.length})</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {filteredTemplates.map(t => (
                  <Card key={t.id} className="p-4 border hover:shadow-md transition-all">
                    <div className="flex items-start gap-2 mb-2">
                      <span className="text-xl">{getIcon(t.label)}</span>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-sm text-slate-800">{t.label}</h4>
                        <div className="flex gap-1 mt-1"><Badge variant="outline" className="text-[10px]">{t.steps.length} steps</Badge><Badge variant="outline" className="text-[10px]">{t.total_documents} docs</Badge></div>
                      </div>
                    </div>
                    {t.fees_info && <p className="text-[11px] text-slate-600 bg-amber-50 p-2 rounded mb-2"><DollarSign className="h-3 w-3 inline" /> {t.fees_info.substring(0, 120)}{t.fees_info.length > 120 ? '...' : ''}</p>}
                    <Button size="sm" className="w-full bg-[#2a777a] hover:bg-[#236466] h-8 text-xs" disabled={applyingTemplate}
                            onClick={() => applyTemplate(t)} data-testid={`apply-${t.id}`}>
                      {applyingTemplate ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <FileCheck className="h-3 w-3 mr-1" />}Use Template
                    </Button>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== PICK VISA ===== */}
      {view === 'pick-visa' && selectedCountry && (
        <div className="space-y-5" data-testid="pick-visa-view">
          <Card className="p-5 border-0 shadow-md">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{getIcon(selectedCountry.name)}</span>
              <div>
                <h2 className="text-lg font-bold text-slate-900">{selectedCountry.name}</h2>
                <p className="text-sm text-slate-500">Select a visa category to generate workflow</p>
              </div>
            </div>
          </Card>

          {loadingVisa ? (
            <Card className="p-12 text-center border-0 shadow-sm">
              <Loader2 className="h-10 w-10 mx-auto mb-3 text-[#2a777a] animate-spin" />
              <p className="font-semibold text-slate-800">AI loading visa categories for {selectedCountry.name}...</p>
              <p className="text-sm text-slate-500 mt-1">Referencing official government immigration website</p>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {visaCategories.map((vc, i) => (
                  <Card key={vc.id || i} className="p-4 border hover:shadow-md hover:border-[#2a777a]/30 transition-all cursor-pointer"
                        onClick={() => { setSelectedVisa(vc); generateWorkflow(vc.name); }}
                        data-testid={`visa-${vc.id}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-sm text-slate-800">{vc.name}</h4>
                        {vc.description && <p className="text-xs text-slate-500 mt-1">{vc.description}</p>}
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {vc.category && <Badge className="text-[9px] bg-[#2a777a]/10 text-[#2a777a]">{vc.category.replace('_', ' ')}</Badge>}
                          {vc.estimated_fees && <Badge variant="outline" className="text-[9px]"><DollarSign className="h-2.5 w-2.5 mr-0.5" />{vc.estimated_fees}</Badge>}
                        </div>
                      </div>
                      <ChevronRight className="h-5 w-5 text-slate-300 mt-1 flex-shrink-0" />
                    </div>
                    {vc.official_url && (
                      <a href={vc.official_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#2a777a] hover:underline mt-2 flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        <ExternalLink className="h-2.5 w-2.5" />Official Source
                      </a>
                    )}
                  </Card>
                ))}
              </div>

              {/* Custom option */}
              <Card className="p-4 border-dashed border-2">
                <h4 className="font-semibold text-sm text-slate-700 mb-3">Custom Visa Type</h4>
                <div className="flex gap-2">
                  <Input placeholder={`Enter visa type for ${selectedCountry.name}...`} value={customInstructions}
                         onChange={e => setCustomInstructions(e.target.value)} className="flex-1 h-9 text-sm" data-testid="custom-visa-input" />
                  <Button size="sm" className="bg-[#f7620b] hover:bg-[#e55a09] h-9" disabled={!customInstructions.trim() || generating}
                          onClick={() => generateWorkflow(customInstructions)} data-testid="generate-custom-btn">
                    {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4 mr-1" />}Generate
                  </Button>
                </div>
              </Card>
            </>
          )}
        </div>
      )}

      {/* ===== REVIEW (Fully Editable) ===== */}
      {view === 'review' && (
        <div className="space-y-4" data-testid="workflow-review">
          {generating ? (
            <Card className="p-12 text-center border-[#2a777a]/20 bg-[#2a777a]/5">
              <Loader2 className="h-12 w-12 mx-auto mb-4 text-[#2a777a] animate-spin" />
              <p className="text-lg font-semibold text-slate-800">AI generating workflow...</p>
              <p className="text-sm text-slate-500 mt-1">Referencing official government sources</p>
            </Card>
          ) : workflow && (
            <>
              {/* AI Verification Warning */}
              {workflowSource === 'ai' && !verified && (
                <Card className="p-4 border-2 border-amber-400 bg-amber-50" data-testid="ai-verify-warning">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="h-6 w-6 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h4 className="font-bold text-sm text-amber-800">AI Generated - Verification Required</h4>
                      <p className="text-xs text-amber-700 mt-1">This workflow was generated by AI. Fees, documents, and requirements may not reflect the latest government policies. Please verify all information from the official government website before saving.</p>
                      <div className="flex items-center gap-3 mt-3">
                        {workflow.estimated_government_fees && (
                          <a href={selectedVisa?.official_url || '#'} target="_blank" rel="noopener noreferrer"
                             className="text-xs bg-amber-600 text-white px-3 py-1.5 rounded-md hover:bg-amber-700 flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" />Verify on Official Website
                          </a>
                        )}
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input type="checkbox" checked={verified} onChange={e => setVerified(e.target.checked)}
                                 className="rounded border-amber-400 h-4 w-4" data-testid="verify-checkbox" />
                          <span className="text-xs font-semibold text-amber-800">I have verified this information is correct</span>
                        </label>
                      </div>
                    </div>
                  </div>
                </Card>
              )}

              {workflowSource === 'template' && !verified && (
                <Card className="p-3 border border-blue-200 bg-blue-50/50" data-testid="template-verify-notice">
                  <div className="flex items-center gap-2">
                    <FileCheck className="h-5 w-5 text-blue-600 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-xs text-blue-700"><span className="font-semibold">Verified Template</span> - Data from official sources. Please review fees and edit if needed before saving.</p>
                    </div>
                    <label className="flex items-center gap-1.5 cursor-pointer flex-shrink-0">
                      <input type="checkbox" checked={verified} onChange={e => setVerified(e.target.checked)} className="rounded h-3.5 w-3.5" />
                      <span className="text-[10px] font-medium text-blue-700">Reviewed</span>
                    </label>
                  </div>
                </Card>
              )}

              {verified && (
                <Card className="p-2 border border-green-200 bg-green-50/50">
                  <div className="flex items-center gap-2 justify-center">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-xs font-semibold text-green-700">Verified by Admin - Ready to save</span>
                  </div>
                </Card>
              )}
              {/* Editable Header */}
              <Card className="p-4 border-0 shadow-md" data-testid="workflow-header">
                <div className="space-y-3">
                  <div>
                    <Label className="text-xs text-slate-500">Product Name</Label>
                    <Input value={workflow.product_name} onChange={e => updateField('product_name', e.target.value)} className="font-bold text-base h-10" data-testid="edit-product-name" />
                  </div>
                  <div>
                    <Label className="text-xs text-slate-500">Description</Label>
                    <Textarea value={workflow.description || ''} onChange={e => updateField('description', e.target.value)} rows={2} className="text-sm" />
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {workflow.estimated_total_duration_days && <Badge variant="outline" className="text-xs"><Clock className="h-3 w-3 mr-1" />~{workflow.estimated_total_duration_days}d</Badge>}
                    <Badge className="bg-[#2a777a] text-white text-xs">{(workflow.steps || []).length} steps</Badge>
                    <Badge variant="outline" className="text-xs">{(workflow.steps || []).reduce((a, s) => a + (s.required_documents?.length || 0), 0)} docs</Badge>
                  </div>
                </div>
              </Card>

              {/* Editable Fees */}
              <Card className="p-4 border-l-4 border-l-amber-400 bg-amber-50/50" data-testid="edit-fees">
                <Label className="text-xs text-amber-600 font-semibold flex items-center gap-1 mb-1"><DollarSign className="h-3 w-3" />Government Fees (Editable)</Label>
                <Textarea value={workflow.estimated_government_fees || ''} onChange={e => updateField('estimated_government_fees', e.target.value)} rows={2} className="text-sm bg-white" placeholder="Enter government fee breakdown..." data-testid="edit-fees-input" />
              </Card>

              {/* Tips */}
              {workflow.success_tips?.length > 0 && (
                <Card className="p-3 border-green-200 bg-green-50/50">
                  <h4 className="font-semibold text-xs text-green-800 mb-1 flex items-center gap-1"><Lightbulb className="h-3 w-3" />Tips</h4>
                  <ul className="space-y-0.5">{workflow.success_tips.map((t, i) => <li key={i} className="text-[11px] text-green-700 flex items-start gap-1"><CheckCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />{t}</li>)}</ul>
                </Card>
              )}
              {workflow.common_rejection_reasons?.length > 0 && (
                <Card className="p-3 border-red-200 bg-red-50/50">
                  <h4 className="font-semibold text-xs text-red-800 mb-1 flex items-center gap-1"><ShieldAlert className="h-3 w-3" />Rejection Reasons</h4>
                  <ul className="space-y-0.5">{workflow.common_rejection_reasons.map((r, i) => <li key={i} className="text-[11px] text-red-700 flex items-start gap-1"><AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />{r}</li>)}</ul>
                </Card>
              )}

              {/* Government Forms */}
              {govForms.length > 0 && (
                <Card className="p-4 border-l-4 border-l-blue-400 bg-blue-50/30" data-testid="gov-forms-section">
                  <h4 className="font-semibold text-sm text-blue-800 mb-3 flex items-center gap-1.5">
                    <Download className="h-4 w-4" /> Official Government Forms ({govForms.length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {govForms.map((form, fi) => (
                      <a key={fi} href={form.url} target="_blank" rel="noopener noreferrer"
                         className="flex items-start gap-2 p-2.5 bg-white rounded-lg border border-blue-100 hover:border-blue-300 hover:shadow-sm transition-all group text-xs"
                         data-testid={`gov-form-${fi}`}>
                        <FileText className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-slate-800 group-hover:text-blue-700 transition-colors">{form.name}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">{form.description}</p>
                          <div className="flex items-center gap-1 mt-1">
                            <Badge className={`text-[8px] ${form.mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>
                              {form.mandatory ? 'Required' : 'Optional'}
                            </Badge>
                            <Badge variant="outline" className="text-[8px]">{form.category}</Badge>
                          </div>
                        </div>
                        <ExternalLink className="h-3.5 w-3.5 text-blue-400 group-hover:text-blue-600 flex-shrink-0 mt-0.5" />
                      </a>
                    ))}
                  </div>
                </Card>
              )}

              {/* Editable Steps */}
              <div className="space-y-3">
                {(workflow.steps || []).map((s, si) => (
                  <Card key={si} className="border overflow-hidden" data-testid={`step-${si}`}>
                    <div className="flex items-center gap-2 p-3 cursor-pointer hover:bg-slate-50" onClick={() => toggleStep(si)}>
                      <div className="h-7 w-7 rounded-lg bg-[#2a777a] text-white flex items-center justify-center text-xs font-bold flex-shrink-0">{s.step_order}</div>
                      <div className="flex-1 min-w-0">
                        <Input value={s.step_name} className="font-semibold text-sm h-7 border-none shadow-none p-0 focus-visible:ring-0"
                               onClick={e => e.stopPropagation()} onChange={e => updateStep(si, 'step_name', e.target.value)} />
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <Input type="number" value={s.duration_days || ''} className="w-14 h-7 text-xs text-center" placeholder="days"
                               onClick={e => e.stopPropagation()} onChange={e => updateStep(si, 'duration_days', parseInt(e.target.value) || null)} />
                        <span className="text-[10px] text-slate-500">days</span>
                        <Badge variant="outline" className="text-[10px]">{(s.required_documents || []).length} docs</Badge>
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600"
                                onClick={e => { e.stopPropagation(); if (window.confirm('Delete this step?')) removeStep(si); }}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                        {expandedSteps[si] ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                      </div>
                    </div>

                    {expandedSteps[si] && (
                      <div className="px-3 pb-3 border-t border-slate-100 space-y-2">
                        <Textarea value={s.description || ''} onChange={e => updateStep(si, 'description', e.target.value)}
                                  rows={1} className="text-xs mt-2" placeholder="Step description..." />
                        {s.government_fees && (
                          <div className="flex items-center gap-2">
                            <Label className="text-[10px] text-slate-500 flex-shrink-0">Step Fees:</Label>
                            <Input value={s.government_fees} onChange={e => updateStep(si, 'government_fees', e.target.value)} className="h-7 text-xs flex-1" />
                          </div>
                        )}
                        {s.important_notes && (
                          <div className="bg-amber-50 border border-amber-200 rounded p-2">
                            <Input value={s.important_notes} onChange={e => updateStep(si, 'important_notes', e.target.value)} className="text-[11px] bg-transparent border-none p-0 h-auto shadow-none focus-visible:ring-0" />
                          </div>
                        )}

                        {/* Documents - Fully Editable */}
                        <div>
                          <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1">Documents ({(s.required_documents || []).length})</p>
                          <div className="space-y-1">
                            {(s.required_documents || []).map((doc, di) => (
                              <div key={di} className="flex items-start gap-2 p-2 bg-slate-50 rounded text-xs group" data-testid={`doc-${si}-${di}`}>
                                <FileText className="h-3.5 w-3.5 text-[#2a777a] mt-1 flex-shrink-0" />
                                <div className="flex-1 min-w-0 space-y-1">
                                  {editingDoc?.stepIdx === si && editingDoc?.docIdx === di ? (
                                    <>
                                      <Input value={doc.name || doc.doc_name || ''} onChange={e => updateDoc(si, di, doc.name !== undefined ? 'name' : 'doc_name', e.target.value)} className="h-6 text-xs font-medium" />
                                      <Input value={doc.description || ''} onChange={e => updateDoc(si, di, 'description', e.target.value)} className="h-6 text-[10px]" placeholder="Description" />
                                      <div className="flex items-center gap-2">
                                        <label className="flex items-center gap-1 text-[10px]">
                                          <input type="checkbox" checked={doc.mandatory || doc.is_mandatory} onChange={e => updateDoc(si, di, doc.mandatory !== undefined ? 'mandatory' : 'is_mandatory', e.target.checked)} className="rounded h-3 w-3" />Mandatory
                                        </label>
                                        <Button size="sm" variant="ghost" className="h-5 text-[10px] text-green-600" onClick={() => setEditingDoc(null)}>Done</Button>
                                      </div>
                                    </>
                                  ) : (
                                    <>
                                      <p className="font-medium text-slate-800">{doc.name || doc.doc_name || ''}</p>
                                      {doc.description && <p className="text-[10px] text-slate-500">{doc.description}</p>}
                                    </>
                                  )}
                                </div>
                                <div className="flex items-center gap-1 flex-shrink-0">
                                  <Badge className={`text-[8px] ${(doc.mandatory || doc.is_mandatory) ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>
                                    {(doc.mandatory || doc.is_mandatory) ? 'Required' : 'Optional'}
                                  </Badge>
                                  <Button variant="ghost" size="sm" className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100" onClick={() => setEditingDoc({ stepIdx: si, docIdx: di })}>
                                    <Edit3 className="h-3 w-3 text-slate-400" />
                                  </Button>
                                  <Button variant="ghost" size="sm" className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100" onClick={() => removeDoc(si, di)}>
                                    <X className="h-3 w-3 text-red-400" />
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>

                          {/* Add Document Form */}
                          {newDocForm.stepIdx === si ? (
                            <div className="mt-2 p-2 border border-dashed rounded space-y-1.5 bg-white">
                              <Input value={newDocForm.name} onChange={e => setNewDocForm({ ...newDocForm, name: e.target.value })} className="h-7 text-xs" placeholder="Document name" />
                              <Input value={newDocForm.description} onChange={e => setNewDocForm({ ...newDocForm, description: e.target.value })} className="h-7 text-xs" placeholder="Description (optional)" />
                              <div className="flex items-center justify-between">
                                <label className="flex items-center gap-1 text-[10px]">
                                  <input type="checkbox" checked={newDocForm.mandatory} onChange={e => setNewDocForm({ ...newDocForm, mandatory: e.target.checked })} className="rounded h-3 w-3" />Mandatory
                                </label>
                                <div className="flex gap-1">
                                  <Button size="sm" className="h-6 text-[10px] bg-[#2a777a]" onClick={() => addDoc(si)}>Add</Button>
                                  <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => setNewDocForm({ stepIdx: null, name: '', description: '', mandatory: true })}>Cancel</Button>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <Button size="sm" variant="outline" className="mt-1.5 h-7 text-xs border-dashed w-full" onClick={() => setNewDocForm({ stepIdx: si, name: '', description: '', mandatory: true })}>
                              <Plus className="h-3 w-3 mr-1" />Add Document
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>

              <Button variant="outline" className="w-full border-dashed text-sm" onClick={addStep}><Plus className="h-4 w-4 mr-1" />Add Step</Button>

              {/* Save Bar */}
              <Card className="p-3 border-0 shadow-lg bg-white sticky bottom-4">
                <div className="flex items-center gap-2">
                  <Button onClick={handleSave} disabled={saving || !verified} className={`flex-1 ${verified ? 'bg-[#2a777a] hover:bg-[#236466]' : 'bg-slate-300 cursor-not-allowed'}`} data-testid="save-btn">
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    {verified ? 'Save as Product' : 'Verify to Save'}
                  </Button>
                  <Button variant="outline" onClick={() => setView('gallery')}>Back</Button>
                </div>
                {!verified && <p className="text-[10px] text-center text-slate-500 mt-1">Please review and verify the information above before saving</p>}
              </Card>
            </>
          )}
        </div>
      )}

      {/* ===== SAVED ===== */}
      {view === 'saved' && (
        <div className="text-center py-12" data-testid="workflow-saved">
          <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center"><CheckCircle className="h-8 w-8 text-green-600" /></div>
          <h2 className="text-xl font-bold text-slate-900 mb-1">Workflow Saved!</h2>
          <p className="text-slate-500 text-sm mb-6">"{workflow?.product_name}" saved with all steps and documents.</p>
          <div className="flex justify-center gap-3">
            <Button onClick={() => { setView('gallery'); setWorkflow(null); }} className="bg-[#2a777a] hover:bg-[#236466]"><Plus className="h-4 w-4 mr-1" />Create Another</Button>
            <Button variant="outline" onClick={() => navigate('/admin')}>Dashboard</Button>
          </div>
        </div>
      )}
    </DashboardShell>
  );
};

export default AIWorkflowBuilder;
