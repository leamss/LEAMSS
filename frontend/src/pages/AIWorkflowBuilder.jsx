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
  ChevronDown, ChevronRight, Globe, Plane, Star, Loader2, Plus, Trash2,
  Download, Lightbulb, ShieldAlert
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_FLAGS = {
  canada: '/flags/ca.svg', australia: '/flags/au.svg', uk: '/flags/gb.svg',
  new_zealand: '/flags/nz.svg', usa: '/flags/us.svg', singapore: '/flags/sg.svg',
  dubai: '/flags/ae.svg',
};

const AIWorkflowBuilder = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [step, setStep] = useState('select');
  const [countries, setCountries] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [customInstructions, setCustomInstructions] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generatedWorkflow, setGeneratedWorkflow] = useState(null);
  const [saving, setSaving] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [editMode, setEditMode] = useState(false);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  useEffect(() => {
    const userData = JSON.parse(localStorage.getItem('user') || '{}');
    if (userData.role !== 'admin') { navigate('/'); return; }
    setUser(userData);
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [countriesRes, templatesRes] = await Promise.all([
        axios.get(`${API}/ai-workflow/countries`, getAuthHeader()),
        axios.get(`${API}/ai-workflow/templates`, getAuthHeader()),
      ]);
      setCountries(countriesRes.data);
      setTemplates(templatesRes.data);
    } catch (err) {
      toast.error('Failed to load workflow data');
    }
  };

  const handleGenerate = async () => {
    if (!selectedCountry || !selectedService) {
      toast.error('Please select country and service type');
      return;
    }
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/ai-workflow/generate`, {
        country: selectedCountry,
        service_type: selectedService,
        custom_instructions: customInstructions,
      }, getAuthHeader());
      setGeneratedWorkflow(res.data);
      setStep('review');
      // Expand all steps by default
      const expanded = {};
      (res.data.steps || []).forEach((_, i) => { expanded[i] = true; });
      setExpandedSteps(expanded);
      toast.success('Workflow generated successfully!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to generate workflow');
    }
    setGenerating(false);
  };

  const handleQuickTemplate = (template) => {
    setSelectedCountry(template.country);
    setSelectedService(template.service);
    setStep('configure');
  };

  const handleSave = async () => {
    if (!generatedWorkflow) return;
    setSaving(true);
    try {
      const res = await axios.post(`${API}/ai-workflow/save`, {
        product_name: generatedWorkflow.product_name,
        description: generatedWorkflow.description,
        category: generatedWorkflow.category || 'immigration',
        base_fee: generatedWorkflow.estimated_government_fees ? 0 : 0,
        commission_rate: 10,
        steps: generatedWorkflow.steps || [],
      }, getAuthHeader());
      toast.success(`Product "${generatedWorkflow.product_name}" saved with ${res.data.steps_created} steps!`);
      setStep('saved');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save workflow');
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
      description: '', duration_days: 7, required_documents: [], important_notes: ''
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

  const navGroups = [
    { id: 'back', icon: ArrowLeft, label: 'Back to Dashboard', onClick: () => navigate('/admin') },
  ];

  if (!user) return null;

  return (
    <DashboardShell
      user={user}
      roleLabel="Admin"
      navGroups={navGroups}
      activeTab="ai-workflow"
      pageTitle="AI Workflow Builder"
      showBackButton={step !== 'select'}
      onBack={() => {
        if (step === 'review' || step === 'saved') setStep('configure');
        else if (step === 'configure') setStep('select');
      }}
      onLogout={() => { localStorage.clear(); navigate('/'); }}
    >
      {/* Step 1: Select Template or Custom */}
      {step === 'select' && (
        <div className="space-y-6" data-testid="workflow-select">
          <Card className="p-6 bg-gradient-to-r from-[#2a777a] to-[#236466] text-white">
            <div className="flex items-center gap-3 mb-3">
              <Wand2 className="h-8 w-8" />
              <div>
                <h2 className="text-xl font-bold">AI Workflow Builder</h2>
                <p className="text-sm opacity-90">Generate complete immigration workflows powered by AI. Select a country and service type, or use a quick template.</p>
              </div>
            </div>
          </Card>

          {/* Quick Templates */}
          <div>
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">Quick Templates</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {templates.map((t) => (
                <Card key={t.id} className="p-4 cursor-pointer hover:border-[#2a777a]/40 hover:shadow-md transition-all border border-gray-200"
                      onClick={() => handleQuickTemplate(t)} data-testid={`template-${t.id}`}>
                  <div className="text-center">
                    <Globe className="h-8 w-8 mx-auto mb-2 text-[#2a777a]" />
                    <p className="text-xs font-semibold text-gray-900 leading-tight">{t.label}</p>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Custom Selection */}
          <Card className="p-6 border border-gray-200">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-4">Or Custom Selection</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label>Country</Label>
                <Select value={selectedCountry} onValueChange={setSelectedCountry}>
                  <SelectTrigger data-testid="country-select"><SelectValue placeholder="Select Country" /></SelectTrigger>
                  <SelectContent>
                    {countries.map(c => (
                      <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Service Type</Label>
                <Input value={selectedService} onChange={(e) => setSelectedService(e.target.value)}
                       placeholder="e.g., PR, Visitor, Student, Work" data-testid="service-input" />
              </div>
              <div className="flex items-end">
                <Button onClick={() => setStep('configure')} disabled={!selectedCountry || !selectedService}
                        className="w-full bg-[#2a777a] hover:bg-[#236466]" data-testid="next-configure-btn">
                  Configure <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Step 2: Configure & Generate */}
      {step === 'configure' && (
        <div className="space-y-6" data-testid="workflow-configure">
          <Card className="p-6 border border-gray-200">
            <h3 className="font-bold text-gray-900 mb-4">Generate Workflow</h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <Label>Country</Label>
                <Input value={selectedCountry} onChange={(e) => setSelectedCountry(e.target.value)} data-testid="config-country" />
              </div>
              <div>
                <Label>Service Type</Label>
                <Input value={selectedService} onChange={(e) => setSelectedService(e.target.value)} data-testid="config-service" />
              </div>
            </div>
            <div className="mb-4">
              <Label>Custom Instructions (Optional)</Label>
              <Textarea value={customInstructions} onChange={(e) => setCustomInstructions(e.target.value)}
                        placeholder="e.g., Include IELTS preparation step, add estimated processing times, focus on skilled worker stream..."
                        rows={3} data-testid="custom-instructions" />
            </div>
            <Button onClick={handleGenerate} disabled={generating} className="w-full bg-[#f7620b] hover:bg-[#e55a09]" data-testid="generate-btn">
              {generating ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> AI is generating workflow...</>
              ) : (
                <><Wand2 className="h-4 w-4 mr-2" /> Generate Workflow with AI</>
              )}
            </Button>
          </Card>
          {generating && (
            <Card className="p-8 text-center border border-[#2a777a]/20 bg-[#2a777a]/5">
              <Loader2 className="h-12 w-12 mx-auto mb-4 text-[#2a777a] animate-spin" />
              <p className="text-lg font-semibold text-gray-800">AI is analyzing immigration requirements...</p>
              <p className="text-sm text-gray-500 mt-1">Referencing official government sources for {selectedCountry} {selectedService}</p>
            </Card>
          )}
        </div>
      )}

      {/* Step 3: Review Generated Workflow */}
      {step === 'review' && generatedWorkflow && (
        <div className="space-y-4" data-testid="workflow-review">
          {/* Header Card */}
          <Card className="p-6 border border-gray-200">
            <div className="flex items-start justify-between mb-4">
              <div>
                {editMode ? (
                  <Input value={generatedWorkflow.product_name} className="text-lg font-bold mb-1"
                         onChange={(e) => setGeneratedWorkflow({ ...generatedWorkflow, product_name: e.target.value })} />
                ) : (
                  <h2 className="text-xl font-bold text-gray-900">{generatedWorkflow.product_name}</h2>
                )}
                <p className="text-sm text-gray-500 mt-1">{generatedWorkflow.description}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setEditMode(!editMode)}>
                  {editMode ? 'Done Editing' : 'Edit'}
                </Button>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              {generatedWorkflow.estimated_total_duration_days && (
                <Badge variant="outline" className="text-xs"><Clock className="h-3 w-3 mr-1" /> ~{generatedWorkflow.estimated_total_duration_days} days</Badge>
              )}
              {generatedWorkflow.estimated_government_fees && (
                <Badge variant="outline" className="text-xs">Fees: {generatedWorkflow.estimated_government_fees}</Badge>
              )}
              <Badge className="bg-[#2a777a] text-white text-xs">{(generatedWorkflow.steps || []).length} steps</Badge>
            </div>
          </Card>

          {/* Tips & Warnings */}
          {generatedWorkflow.success_tips && generatedWorkflow.success_tips.length > 0 && (
            <Card className="p-4 border border-green-200 bg-green-50">
              <h4 className="font-semibold text-green-800 mb-2 flex items-center gap-2"><Lightbulb className="h-4 w-4" /> Success Tips</h4>
              <ul className="space-y-1">
                {generatedWorkflow.success_tips.map((tip, i) => (
                  <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                    <CheckCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" /> {tip}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {generatedWorkflow.common_rejection_reasons && generatedWorkflow.common_rejection_reasons.length > 0 && (
            <Card className="p-4 border border-red-200 bg-red-50">
              <h4 className="font-semibold text-red-800 mb-2 flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> Common Rejection Reasons</h4>
              <ul className="space-y-1">
                {generatedWorkflow.common_rejection_reasons.map((reason, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" /> {reason}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Steps */}
          <div className="space-y-3">
            {(generatedWorkflow.steps || []).map((s, idx) => (
              <Card key={idx} className="border border-gray-200 overflow-hidden" data-testid={`workflow-step-${idx}`}>
                <div className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50" onClick={() => toggleStep(idx)}>
                  <div className="h-8 w-8 rounded-full bg-[#2a777a] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                    {s.step_order}
                  </div>
                  <div className="flex-1 min-w-0">
                    {editMode ? (
                      <Input value={s.step_name} className="font-semibold" onClick={(e) => e.stopPropagation()}
                             onChange={(e) => updateStep(idx, 'step_name', e.target.value)} />
                    ) : (
                      <h4 className="font-semibold text-gray-900">{s.step_name}</h4>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {s.duration_days && <Badge variant="outline" className="text-xs"><Clock className="h-3 w-3 mr-1" />{s.duration_days}d</Badge>}
                    <Badge variant="outline" className="text-xs">{(s.required_documents || []).length} docs</Badge>
                    {editMode && (
                      <Button variant="ghost" size="sm" className="text-red-500 h-7 w-7 p-0" onClick={(e) => { e.stopPropagation(); removeStep(idx); }}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                    {expandedSteps[idx] ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
                  </div>
                </div>
                {expandedSteps[idx] && (
                  <div className="px-4 pb-4 pt-0 border-t border-gray-100">
                    <p className="text-sm text-gray-600 mb-3">{s.description}</p>
                    {s.important_notes && (
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3">
                        <p className="text-xs text-amber-800"><AlertTriangle className="h-3 w-3 inline mr-1" />{s.important_notes}</p>
                      </div>
                    )}
                    {s.government_fees && (
                      <p className="text-xs text-gray-500 mb-2">Government Fees: <span className="font-semibold">{s.government_fees}</span></p>
                    )}
                    {(s.required_documents || []).length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">Required Documents</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {s.required_documents.map((doc, di) => (
                            <div key={di} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                              <FileText className="h-4 w-4 text-[#2a777a] mt-0.5 flex-shrink-0" />
                              <div>
                                <p className="text-sm font-medium text-gray-800">{doc.name || doc}</p>
                                {doc.description && <p className="text-xs text-gray-500">{doc.description}</p>}
                                {doc.mandatory !== undefined && (
                                  <Badge className={`text-[10px] mt-1 ${doc.mandatory ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                                    {doc.mandatory ? 'Mandatory' : 'Optional'}
                                  </Badge>
                                )}
                              </div>
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
            <Button variant="outline" className="w-full border-dashed" onClick={addStep}>
              <Plus className="h-4 w-4 mr-2" /> Add Step
            </Button>
          )}

          {/* Save Actions */}
          <Card className="p-4 border border-gray-200 bg-gray-50 sticky bottom-4">
            <div className="flex items-center gap-3">
              <Button onClick={handleSave} disabled={saving} className="flex-1 bg-[#2a777a] hover:bg-[#236466]" data-testid="save-workflow-btn">
                {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                Save as Product
              </Button>
              <Button variant="outline" onClick={() => { setStep('configure'); setGeneratedWorkflow(null); }}>
                Regenerate
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Step 4: Saved Confirmation */}
      {step === 'saved' && (
        <div className="text-center py-12" data-testid="workflow-saved">
          <div className="w-20 h-20 mx-auto mb-6 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle className="h-10 w-10 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Workflow Saved!</h2>
          <p className="text-gray-500 mb-6">"{generatedWorkflow?.product_name}" has been saved as a product with all workflow steps.</p>
          <div className="flex justify-center gap-3">
            <Button onClick={() => { setStep('select'); setGeneratedWorkflow(null); setSelectedCountry(''); setSelectedService(''); }}
                    className="bg-[#2a777a] hover:bg-[#236466]">
              <Plus className="h-4 w-4 mr-2" /> Create Another
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
