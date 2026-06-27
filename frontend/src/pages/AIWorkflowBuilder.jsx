import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import Flag from 'react-world-flags';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import DashboardShell from '@/components/DashboardShell';
import {
  ArrowLeft, Wand2, Save, FileText, Clock, AlertTriangle, CheckCircle,
  ChevronDown, ChevronRight, Loader2, Plus, Trash2,
  Lightbulb, ShieldAlert, Sparkles, ExternalLink, DollarSign,
  Search, FileCheck, Edit3, X, Download, ShieldCheck, Globe2
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ISO country code mapping for SVG flags
const ISO_CODES = {
  argentina:'AR',australia:'AU',austria:'AT',bahrain:'BH',belgium:'BE',brazil:'BR',
  canada:'CA',chile:'CL',china:'CN',colombia:'CO',costa_rica:'CR',czech_republic:'CZ',
  denmark:'DK',egypt:'EG',finland:'FI',france:'FR',germany:'DE',greece:'GR',hong_kong:'HK',
  india:'IN',indonesia:'ID',ireland:'IE',italy:'IT',japan:'JP',kenya:'KE',malaysia:'MY',
  mauritius:'MU',mexico:'MX',netherlands:'NL',new_zealand:'NZ',nigeria:'NG',norway:'NO',
  oman:'OM',panama:'PA',philippines:'PH',poland:'PL',portugal:'PT',qatar:'QA',
  saudi_arabia:'SA',singapore:'SG',south_africa:'ZA',south_korea:'KR',spain:'ES',
  sweden:'SE',switzerland:'CH',thailand:'TH',turkey:'TR',uae:'AE',uk:'GB',usa:'US',vietnam:'VN',
};

const getISO = (id) => ISO_CODES[id] || id?.toUpperCase()?.slice(0,2) || 'UN';

const AIWorkflowBuilder = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [view, setView] = useState('gallery');
  const [countries, setCountries] = useState([]);
  const [docTemplates, setDocTemplates] = useState([]);
  const [searchQ, setSearchQ] = useState('');
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [visaCategories, setVisaCategories] = useState([]);
  const [loadingVisa, setLoadingVisa] = useState(false);
  const [selectedVisa, setSelectedVisa] = useState(null);
  const [customInstructions, setCustomInstructions] = useState('');
  const [generating, setGenerating] = useState(false);
  const [workflow, setWorkflow] = useState(null);
  const [expandedSteps, setExpandedSteps] = useState({});
  const [saving, setSaving] = useState(false);
  const [applyingTemplate, setApplyingTemplate] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [newDocForm, setNewDocForm] = useState({ stepIdx: null, name: '', description: '', mandatory: true });
  const [govForms, setGovForms] = useState([]);
  const [verified, setVerified] = useState(false);
  const [workflowSource, setWorkflowSource] = useState('');
  // Sweep A.2 — Background-job progress state
  const [jobId, setJobId] = useState(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobStep, setJobStep] = useState('');
  const [cachedHit, setCachedHit] = useState(false);
  const [jobError, setJobError] = useState('');

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  useEffect(() => {
    const u = JSON.parse(localStorage.getItem('user') || '{}');
    if (u.role !== 'admin') { navigate('/'); return; }
    setUser(u);
    Promise.all([
      axios.get(`${API}/ai-workflow/countries`, auth()),
      axios.get(`${API}/step-documents/templates`, auth()),
    ]).then(([cRes, tRes]) => {
      setCountries(cRes.data);
      setDocTemplates(tRes.data.templates || []);
    }).catch(() => toast.error('Failed to load data'));
  }, []);

  const loadGovForms = async (countryName) => {
    try { const r = await axios.get(`${API}/step-documents/government-forms/${encodeURIComponent(countryName)}`, auth()); setGovForms(r.data.forms || []); } catch { setGovForms([]); }
  };

  const selectCountry = async (country) => {
    setSelectedCountry(country); setVisaCategories([]); setSelectedVisa(null); setLoadingVisa(true); setView('pick-visa');
    try { const r = await axios.post(`${API}/ai-workflow/visa-categories`, { country: country.name }, auth()); setVisaCategories(r.data.categories || []); } catch { toast.error('Failed to load visa categories'); }
    setLoadingVisa(false);
  };

  const generateWorkflow = async (visaSelection) => {
    // Sweep A.2 — Background-job pattern. POST returns instantly with job_id;
    // poll /generate/status/{job_id} until status=complete|failed.
    // B.2 HOTFIX (Feb 27) — visaSelection may be an object (preferred, from visa card)
    // OR a string (legacy / custom instruction path). Prefer canonical service_type.
    const visaName = (visaSelection && typeof visaSelection === 'object')
      ? (visaSelection.service_type || visaSelection.category || visaSelection.name || '')
      : (visaSelection || '');
    const visaSubclassId = (visaSelection && typeof visaSelection === 'object') ? (visaSelection.subclass_id || '') : '';
    setGenerating(true); setView('review'); setJobError(''); setCachedHit(false); setJobProgress(0); setJobStep('queued'); setWorkflow(null);
    let pollTimer = null;
    let cancelled = false;
    try {
      const r = await axios.post(`${API}/ai-workflow/generate`,
        { country: selectedCountry.name, service_type: visaName, subclass_id: visaSubclassId, custom_instructions: customInstructions },
        auth());
      const jid = r.data.job_id;
      setJobId(jid);

      // B.2 HOTFIX — Seeded fastpath: response is already complete (no polling needed)
      if (r.data.status === 'complete' && r.data.result) {
        setWorkflow(r.data.result);
        const exp = {}; (r.data.result.steps || []).forEach((_, i) => { exp[i] = true; }); setExpandedSteps(exp);
        setJobProgress(100); setJobStep('done');
        const isSeeded = r.data.source === 'seeded_verified';
        if (isSeeded) {
          toast.success('Loaded verified template — instant ⚡');
          setWorkflowSource('verified'); setVerified(true);
        } else {
          toast.success('Loaded from cache — instant ⚡');
          setWorkflowSource('ai'); setVerified(false);
        }
        setCachedHit(!isSeeded);
        if (selectedCountry?.name) loadGovForms(selectedCountry.name);
        setGenerating(false);
        return;
      }

      // Cache hit (legacy code path)
      if (r.data.cached && r.data.result) {
        setWorkflow(r.data.result);
        const exp = {}; (r.data.result.steps || []).forEach((_, i) => { exp[i] = true; }); setExpandedSteps(exp);
        setCachedHit(true);
        setJobProgress(100); setJobStep('done');
        toast.success('Loaded from cache — instant ⚡');
        setWorkflowSource('ai'); setVerified(false);
        if (selectedCountry?.name) loadGovForms(selectedCountry.name);
        setGenerating(false);
        return;
      }

      // Polling loop
      const poll = async () => {
        if (cancelled) return;
        try {
          const s = await axios.get(`${API}/ai-workflow/generate/status/${jid}`, auth());
          const job = s.data;
          setJobProgress(job.progress || 0);
          setJobStep(job.current_step || 'running');
          if (job.status === 'complete' && job.result) {
            setWorkflow(job.result);
            const exp = {}; (job.result.steps || []).forEach((_, i) => { exp[i] = true; }); setExpandedSteps(exp);
            const m = job.result?._meta?.model_used || job.model_used || 'AI';
            const degraded = job.result?._degraded_mode;
            if (degraded === 'template_fallback') {
              toast.warning('AI budget exceeded — using verified template fallback. Top up at Profile → Universal Key → Add Balance.');
            } else {
              const dur = job.duration_ms ? ` in ${(job.duration_ms / 1000).toFixed(0)}s` : '';
              toast.success(`Workflow generated via ${m.replace('anthropic/', '').replace('-20250929', '')}${dur} 🎉`);
            }
            setWorkflowSource('ai'); setVerified(false);
            if (selectedCountry?.name) loadGovForms(selectedCountry.name);
            setGenerating(false);
            return;
          }
          if (job.status === 'failed') {
            setJobError(job.error || 'Generation failed');
            toast.error(job.error || 'Workflow generation failed');
            setGenerating(false);
            setView('pick-visa');
            return;
          }
          // Still queued/running — re-poll in 2.5s
          pollTimer = setTimeout(poll, 2500);
        } catch (e) {
          // Network blip — keep retrying for a while
          console.warn('Workflow status poll failed', e);
          pollTimer = setTimeout(poll, 4000);
        }
      };
      pollTimer = setTimeout(poll, 1500);
    } catch (e) {
      const detail = e.response?.data?.detail || 'Generation failed';
      toast.error(detail);
      setGenerating(false);
      setView('pick-visa');
    }

    // Cleanup if component unmounts mid-generation — handled by jobId watcher below
    return () => { cancelled = true; if (pollTimer) clearTimeout(pollTimer); };
  };

  // Sweep A.2 — Cancel a running workflow generation job
  const cancelWorkflowJob = async () => {
    if (!jobId) return;
    try {
      await axios.delete(`${API}/ai-workflow/generate/${jobId}`, auth());
      toast.message('Generation cancelled', { description: 'Aap firse koshish kar sakte hain.' });
    } catch (e) {
      console.warn('Cancel failed', e);
    } finally {
      setGenerating(false);
      setJobId(null);
      setView('pick-visa');
    }
  };

  // Phase 20.1 — persist verification to `ai_workflow_templates` collection
  const handleVerifyToggle = async (checked) => {
    setVerified(checked);
    if (!checked || !workflow || workflowSource !== 'ai') return;
    try {
      await axios.post(`${API}/ai-workflow/verify`, {
        workflow_payload: workflow,
        country: selectedCountry?.name || '',
        service_type: workflow?.product_name?.split(' - ').pop() || '',
        notes: '',
      }, auth());
      toast.success('Verified — saved to template library');
    } catch (e) {
      console.warn('Verify persist failed:', e?.response?.data?.detail);
      // Don't block UX — verification still works locally
    }
  };

  const applyTemplate = async (tmpl) => {
    setApplyingTemplate(true);
    try {
      const r = await axios.post(`${API}/step-documents/ai-suggest-bulk`, { product_name: tmpl.label, steps: tmpl.steps.map(s => ({ step_name: s })) }, auth());
      const suggs = r.data.suggestions || {};
      const steps = tmpl.steps.map((sn, i) => ({
        step_name: sn, step_order: i + 1, description: '', duration_days: 14,
        required_documents: (suggs[sn] || []).map(d => ({ name: d.doc_name, description: d.description || '', mandatory: d.is_mandatory !== false })),
      }));
      setWorkflow({ product_name: tmpl.label, description: `Immigration workflow for ${tmpl.label}`, category: 'immigration', estimated_government_fees: tmpl.fees_info || '', steps });
      const exp = {}; steps.forEach((_, i) => { exp[i] = true; }); setExpandedSteps(exp);
      setView('review'); setWorkflowSource('template'); setVerified(false);
      toast.success(`Template loaded with ${steps.reduce((a, s) => a + s.required_documents.length, 0)} documents!`);
      const cn = tmpl.label.split(' ')[0]; loadGovForms(cn);
    } catch { toast.error('Failed to apply template'); }
    setApplyingTemplate(false);
  };

  const handleSave = async () => {
    if (!workflow) return; setSaving(true);
    try {
      const r = await axios.post(`${API}/ai-workflow/save`, { product_name: workflow.product_name, description: workflow.description, category: 'immigration', base_fee: 0, commission_rate: 10, steps: workflow.steps || [] }, auth());
      toast.success(`"${workflow.product_name}" saved with ${r.data.steps_created} steps!`); setView('saved');
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
    setSaving(false);
  };

  const updateField = (f, v) => setWorkflow({ ...workflow, [f]: v });
  const updateStep = (i, f, v) => { const w = { ...workflow }; w.steps[i][f] = v; setWorkflow(w); };
  const addStep = () => { const w = { ...workflow }; const n = (w.steps?.length||0)+1; w.steps = [...(w.steps||[]), {step_name:`New Step ${n}`,step_order:n,description:'',duration_days:7,required_documents:[]}]; setWorkflow(w); setExpandedSteps({...expandedSteps,[w.steps.length-1]:true}); };
  const removeStep = (i) => { const w = { ...workflow }; w.steps.splice(i,1); w.steps.forEach((s,j) => {s.step_order=j+1;}); setWorkflow(w); };
  const addDoc = (si) => { if(!newDocForm.name.trim()){toast.error('Enter name');return;} const w={...workflow}; w.steps[si].required_documents.push({name:newDocForm.name,description:newDocForm.description,mandatory:newDocForm.mandatory}); setWorkflow(w); setNewDocForm({stepIdx:null,name:'',description:'',mandatory:true}); };
  const removeDoc = (si,di) => { const w={...workflow}; w.steps[si].required_documents.splice(di,1); setWorkflow(w); };
  const updateDoc = (si,di,f,v) => { const w={...workflow}; w.steps[si].required_documents[di][f]=v; setWorkflow(w); };
  const toggleStep = (i) => setExpandedSteps(p => ({...p,[i]:!p[i]}));

  const filteredCountries = countries.filter(c => !searchQ || c.name.toLowerCase().includes(searchQ.toLowerCase()));
  const filteredTemplates = docTemplates.filter(t => !searchQ || t.label.toLowerCase().includes(searchQ.toLowerCase()));

  if (!user) return null;

  return (
    <DashboardShell user={user} roleLabel="Admin" activeTab="ai-workflow" pageTitle="AI Workflow Builder"
      navGroups={[{id:'back',icon:ArrowLeft,label:'Back to Dashboard',onClick:()=>navigate('/admin')}]}
      showBackButton={view!=='gallery'}
      onBack={() => { if(view==='review'||view==='saved') setView('pick-visa'); else if(view==='pick-visa') setView('gallery'); }}
      onLogout={() => {localStorage.clear();navigate('/');}}>

      {/* ===== GALLERY ===== */}
      {view === 'gallery' && (
        <div className="space-y-8" data-testid="workflow-gallery" style={{fontFamily:"'IBM Plex Sans',sans-serif"}}>
          {/* Hero */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#2a777a] via-[#1e6365] to-[#163e40] p-8 text-white">
            <div className="absolute inset-0 opacity-10" style={{backgroundImage:'radial-gradient(circle at 20% 50%, rgba(255,255,255,0.3) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(247,98,11,0.3) 0%, transparent 40%)'}} />
            <div className="relative z-10">
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight mb-2" style={{fontFamily:'Manrope,sans-serif'}}>AI Workflow Builder</h1>
              <p className="text-white/70 text-sm max-w-xl leading-relaxed">Select a country to explore all visa categories, or use a verified template. Build complete immigration workflows with real documents, fees & government references.</p>
              <div className="flex gap-3 mt-5">
                <div className="flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-1.5 text-xs"><Globe2 className="h-3.5 w-3.5" />{countries.length} Countries</div>
                <div className="flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-1.5 text-xs"><FileCheck className="h-3.5 w-3.5" />{docTemplates.length} Verified Templates</div>
              </div>
            </div>
          </div>

          {/* Search */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight" style={{fontFamily:'Manrope,sans-serif'}}>Select Country</h2>
            <div className="relative w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input className="pl-9 h-10 text-sm rounded-lg border-slate-200 bg-slate-50 focus:bg-white" placeholder="Search countries or templates..." value={searchQ} onChange={e => setSearchQ(e.target.value)} data-testid="search-input" />
            </div>
          </div>

          {/* Countries Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredCountries.map(c => (
              <div key={c.id} onClick={() => selectCountry(c)}
                   className="flex items-center gap-3.5 p-4 bg-white rounded-xl border border-slate-200 cursor-pointer hover:border-[#2a777a]/40 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
                   data-testid={`country-${c.id}`}>
                <div className="w-10 h-10 rounded-full overflow-hidden border-2 border-slate-100 flex-shrink-0 flex items-center justify-center bg-slate-50">
                  <Flag code={getISO(c.id)} style={{width:'40px',height:'40px',objectFit:'cover',borderRadius:'50%'}} fallback={<Globe2 className="h-5 w-5 text-slate-400" />} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm text-slate-800 truncate" style={{fontFamily:'Manrope,sans-serif'}}>{c.name}</p>
                  <p className="text-[11px] text-slate-500">{c.services.length} visa types</p>
                </div>
                <ChevronRight className="h-4 w-4 text-slate-300 flex-shrink-0" />
              </div>
            ))}
          </div>

          {/* Verified Templates */}
          {filteredTemplates.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h2 className="text-lg font-bold text-slate-900 tracking-tight" style={{fontFamily:'Manrope,sans-serif'}}>Verified Templates</h2>
                <Badge className="bg-[#f7620b]/10 text-[#f7620b] text-[10px] font-bold border-0">PRE-BUILT</Badge>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {filteredTemplates.map(t => (
                  <Card key={t.id} className="overflow-hidden border border-slate-200 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200" data-testid={`template-card-${t.id}`}>
                    <div className="p-5">
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-9 h-9 rounded-lg overflow-hidden border border-slate-100 flex-shrink-0 flex items-center justify-center bg-slate-50">
                          <Flag code={getISO(t.id.split('_')[0] === 'student' ? 'UN' : t.id.split('_')[0])} style={{width:'36px',height:'36px',objectFit:'cover'}} fallback={<Globe2 className="h-5 w-5 text-slate-400" />} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-bold text-sm text-slate-900" style={{fontFamily:'Manrope,sans-serif'}}>{t.label}</h3>
                          <div className="flex gap-1.5 mt-1.5">
                            <Badge variant="outline" className="text-[10px] font-medium">{t.steps.length} steps</Badge>
                            <Badge variant="outline" className="text-[10px] font-medium">{t.total_documents} docs</Badge>
                          </div>
                        </div>
                      </div>
                      {t.fees_info && (
                        <div className="p-2.5 bg-amber-50/60 rounded-lg mb-3 border border-amber-100">
                          <p className="text-[10px] font-bold text-amber-600 uppercase tracking-wider mb-0.5">Government Fees</p>
                          <p className="text-[11px] text-amber-800 leading-relaxed">{t.fees_info.substring(0, 120)}{t.fees_info.length > 120 ? '...' : ''}</p>
                        </div>
                      )}
                      <Button size="sm" className="w-full bg-[#2a777a] hover:bg-[#215f62] text-xs h-9 rounded-lg font-semibold" disabled={applyingTemplate}
                              onClick={() => applyTemplate(t)} data-testid={`apply-${t.id}`}>
                        {applyingTemplate ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Sparkles className="h-3.5 w-3.5 mr-1.5" />}Use This Template
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== PICK VISA ===== */}
      {view === 'pick-visa' && selectedCountry && (
        <div className="space-y-6" data-testid="pick-visa-view" style={{fontFamily:"'IBM Plex Sans',sans-serif"}}>
          <div className="flex items-center gap-4 p-6 bg-white rounded-2xl border border-slate-200 shadow-sm">
            <div className="w-14 h-14 rounded-xl overflow-hidden border-2 border-slate-100 flex items-center justify-center bg-slate-50">
              <Flag code={getISO(selectedCountry.id)} style={{width:'56px',height:'56px',objectFit:'cover'}} fallback={<Globe2 className="h-7 w-7 text-slate-400" />} />
            </div>
            <div>
              <h2 className="text-xl font-extrabold text-slate-900 tracking-tight" style={{fontFamily:'Manrope,sans-serif'}}>{selectedCountry.name}</h2>
              <p className="text-sm text-slate-500">Select a visa category to generate workflow</p>
            </div>
          </div>

          {loadingVisa ? (
            <div className="p-16 text-center bg-white rounded-2xl border border-slate-200">
              <Loader2 className="h-10 w-10 mx-auto mb-4 text-[#2a777a] animate-spin" />
              <p className="font-bold text-slate-800" style={{fontFamily:'Manrope,sans-serif'}}>Loading visa categories for {selectedCountry.name}...</p>
              <p className="text-sm text-slate-500 mt-1">Referencing official government immigration data</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {visaCategories.map((vc, i) => (
                  <div key={vc.id || i} onClick={() => { setSelectedVisa(vc); generateWorkflow(vc); }}
                       className="p-5 bg-white rounded-xl border border-slate-200 hover:border-[#2a777a]/40 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer group"
                       data-testid={`visa-${vc.id}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <h3 className="font-bold text-sm text-slate-900 group-hover:text-[#2a777a] transition-colors" style={{fontFamily:'Manrope,sans-serif'}}>{vc.name}</h3>
                        {vc.description && <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">{vc.description}</p>}
                        <div className="flex flex-wrap gap-1.5 mt-2.5">
                          {vc.category && <Badge className="text-[9px] bg-[#2a777a]/10 text-[#2a777a] font-semibold border-0">{vc.category.replace('_',' ')}</Badge>}
                          {vc.estimated_fees && <Badge variant="outline" className="text-[9px] font-medium"><DollarSign className="h-2.5 w-2.5 mr-0.5" />{vc.estimated_fees}</Badge>}
                        </div>
                      </div>
                      <div className="w-8 h-8 rounded-full bg-slate-100 group-hover:bg-[#2a777a]/10 flex items-center justify-center transition-colors flex-shrink-0">
                        <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-[#2a777a]" />
                      </div>
                    </div>
                    {vc.official_url && (
                      <a href={vc.official_url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#2a777a] hover:underline mt-2.5 flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        <ExternalLink className="h-2.5 w-2.5" />Official Source
                      </a>
                    )}
                  </div>
                ))}
              </div>

              <div className="p-5 bg-white rounded-xl border-2 border-dashed border-slate-300">
                <h4 className="font-bold text-sm text-slate-700 mb-3" style={{fontFamily:'Manrope,sans-serif'}}>Custom Visa Type</h4>
                <div className="flex gap-2">
                  <Input placeholder={`Enter visa type for ${selectedCountry.name}...`} value={customInstructions}
                         onChange={e => setCustomInstructions(e.target.value)} className="flex-1 h-10 rounded-lg" data-testid="custom-visa-input" />
                  <Button className="bg-[#f7620b] hover:bg-[#d95509] h-10 rounded-lg px-5 font-semibold" disabled={!customInstructions.trim() || generating}
                          onClick={() => generateWorkflow(customInstructions)} data-testid="generate-custom-btn">
                    {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Wand2 className="h-4 w-4 mr-1.5" />Generate</>}
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ===== REVIEW ===== */}
      {view === 'review' && (
        <div className="space-y-5" data-testid="workflow-review" style={{fontFamily:"'IBM Plex Sans',sans-serif"}}>
          {generating ? (
            <div className="p-12 sm:p-16 bg-white rounded-2xl border border-leamss-teal-200 shadow-sm" data-testid="ai-workflow-progress">
              <div className="max-w-xl mx-auto text-center">
                <div className="relative h-16 w-16 mx-auto mb-5">
                  <div className="absolute inset-0 rounded-full bg-gradient-to-br from-leamss-teal-100 to-leamss-orange-100 animate-pulse" />
                  <Loader2 className="absolute inset-2 h-12 w-12 text-leamss-teal-600 animate-spin" />
                </div>
                <p className="text-lg font-bold text-slate-800" style={{fontFamily:'Manrope,sans-serif'}}>
                  AI generating workflow…
                </p>
                <p className="text-sm text-slate-500 mt-1" data-testid="ai-workflow-current-step">
                  {jobStep === 'queued' && 'Job queued — kicking off background generation'}
                  {jobStep === 'analyzing' && 'Analyzing visa category and resolving authoritative sources'}
                  {jobStep === 'generating' && 'Calling Claude Sonnet 4.5 for step-by-step workflow'}
                  {jobStep === 'regenerating' && 'Re-prompting AI to meet our quality bar (≥5 steps, ≥3 docs/step)'}
                  {jobStep === 'formatting' && 'Formatting and validating the workflow output'}
                  {!['queued','analyzing','generating','regenerating','formatting'].includes(jobStep) && 'Working on it…'}
                </p>

                {/* Progress bar */}
                <div className="mt-6 w-full bg-slate-100 rounded-full h-2 overflow-hidden" data-testid="ai-workflow-progress-bar">
                  <div
                    className="h-full bg-gradient-to-r from-leamss-teal-500 to-leamss-orange-500 transition-all duration-700 ease-out"
                    style={{width: `${jobProgress}%`}}
                  />
                </div>
                <p className="text-xs text-slate-400 mt-2 font-mono">{jobProgress}% · {jobId ? `job ${jobId.slice(0, 8)}…` : 'starting…'}</p>

                <p className="text-xs text-slate-400 mt-4">
                  Generation typically takes 60–180 seconds. Aap is page ko chhod kar wapas aa sakte hain — generation backend pe continue hogi.
                </p>

                <div className="flex justify-center gap-2 mt-5">
                  <Button variant="outline" size="sm"
                    className="border-leamss-red-300 text-leamss-red-700 hover:bg-leamss-red-50"
                    onClick={cancelWorkflowJob} data-testid="ai-workflow-cancel-btn">
                    <X className="h-3.5 w-3.5 mr-1.5" /> Cancel
                  </Button>
                </div>

                {jobError && (
                  <div className="mt-5 bg-leamss-red-50 border border-leamss-red-200 rounded-lg p-3 text-left">
                    <p className="text-xs text-leamss-red-800 font-semibold">Error</p>
                    <p className="text-xs text-leamss-red-700 mt-0.5">{jobError}</p>
                  </div>
                )}
              </div>
            </div>
          ) : workflow && (
            <>
              {/* Cache hit badge */}
              {cachedHit && (
                <div className="px-4 py-2 bg-leamss-sky-50 border border-leamss-sky-200 rounded-lg flex items-center justify-between gap-3" data-testid="ai-workflow-cached-badge">
                  <p className="text-sm text-leamss-sky-800 flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    <span>Loaded from cache (saved last hour). Want fresh AI output? <Button variant="link" className="h-auto p-0 text-leamss-sky-800 underline" onClick={() => { setCachedHit(false); generateWorkflow(selectedVisa?.name || ''); }} data-testid="ai-workflow-regenerate-btn">Regenerate</Button></span>
                  </p>
                </div>
              )}

              {/* Verification Banner */}
              {workflowSource === 'ai' && !verified && (
                <div className="p-5 bg-amber-50 border-2 border-amber-300 rounded-xl" data-testid="ai-verify-warning">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0"><AlertTriangle className="h-5 w-5 text-amber-600" /></div>
                    <div className="flex-1">
                      <h4 className="font-bold text-amber-900" style={{fontFamily:'Manrope,sans-serif'}}>AI Generated - Verification Required</h4>
                      <p className="text-xs text-amber-700 mt-1 leading-relaxed">Fees, documents, and requirements may not reflect the latest policies. Please verify from the official government website before saving.</p>
                      <div className="flex items-center gap-4 mt-3">
                        {selectedVisa?.official_url && (
                          <a href={selectedVisa.official_url} target="_blank" rel="noopener noreferrer" className="text-xs bg-amber-600 text-white px-4 py-2 rounded-lg hover:bg-amber-700 font-semibold flex items-center gap-1.5 transition-colors">
                            <ExternalLink className="h-3.5 w-3.5" />Verify on Official Website
                          </a>
                        )}
                        <label className="flex items-center gap-2 cursor-pointer select-none">
                          <input type="checkbox" checked={verified} onChange={e => handleVerifyToggle(e.target.checked)} className="rounded border-amber-400 h-4 w-4 text-amber-600" data-testid="verify-checkbox" />
                          <span className="text-xs font-semibold text-amber-800">I have verified this information</span>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {workflowSource === 'template' && !verified && (
                <div className="p-4 bg-[#2a777a]/5 border border-[#2a777a]/20 rounded-xl flex items-center gap-3" data-testid="template-verify-notice">
                  <ShieldCheck className="h-5 w-5 text-[#2a777a] flex-shrink-0" />
                  <p className="text-xs text-[#2a777a] flex-1"><span className="font-bold">Verified Template</span> - Based on official sources. Review fees and edit if needed.</p>
                  <label className="flex items-center gap-1.5 cursor-pointer flex-shrink-0 select-none">
                    <input type="checkbox" checked={verified} onChange={e => setVerified(e.target.checked)} className="rounded h-4 w-4" />
                    <span className="text-[11px] font-semibold text-[#2a777a]">Reviewed</span>
                  </label>
                </div>
              )}
              {verified && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 justify-center">
                  <CheckCircle className="h-4 w-4 text-emerald-600" />
                  <span className="text-xs font-bold text-emerald-700">Verified by Admin - Ready to save</span>
                </div>
              )}

              {/* Header Card */}
              <Card className="p-6 rounded-xl border border-slate-200" data-testid="workflow-header">
                <div className="space-y-4">
                  <div><Label className="text-[10px] font-bold uppercase tracking-wider text-slate-400" style={{fontFamily:'Manrope,sans-serif'}}>Product Name</Label>
                    <Input value={workflow.product_name} onChange={e => updateField('product_name', e.target.value)} className="font-bold text-lg h-11 mt-1 rounded-lg" data-testid="edit-product-name" style={{fontFamily:'Manrope,sans-serif'}} /></div>
                  <div><Label className="text-[10px] font-bold uppercase tracking-wider text-slate-400" style={{fontFamily:'Manrope,sans-serif'}}>Description</Label>
                    <Textarea value={workflow.description || ''} onChange={e => updateField('description', e.target.value)} rows={2} className="text-sm mt-1 rounded-lg" /></div>
                  <div className="flex gap-2 flex-wrap">
                    {workflow.estimated_total_duration_days && <Badge variant="outline" className="text-xs font-medium"><Clock className="h-3 w-3 mr-1" />~{workflow.estimated_total_duration_days}d</Badge>}
                    <Badge className="bg-[#2a777a] text-white text-xs font-semibold">{(workflow.steps || []).length} steps</Badge>
                    <Badge variant="outline" className="text-xs font-medium">{(workflow.steps || []).reduce((a, s) => a + (s.required_documents?.length || 0), 0)} documents</Badge>
                  </div>
                </div>
              </Card>

              {/* Fees */}
              <Card className="p-5 border-l-4 border-l-amber-400 bg-amber-50/40 rounded-xl" data-testid="edit-fees">
                <Label className="text-[10px] font-bold uppercase tracking-wider text-amber-600 flex items-center gap-1.5 mb-2" style={{fontFamily:'Manrope,sans-serif'}}><DollarSign className="h-3.5 w-3.5" />Government Fees (Editable)</Label>
                <Textarea value={workflow.estimated_government_fees || ''} onChange={e => updateField('estimated_government_fees', e.target.value)} rows={2} className="text-sm bg-white rounded-lg" placeholder="Enter government fee breakdown..." data-testid="edit-fees-input" />
              </Card>

              {/* Tips & Warnings */}
              {workflow.success_tips?.length > 0 && (
                <Card className="p-4 border-emerald-200 bg-emerald-50/40 rounded-xl">
                  <h4 className="font-bold text-xs text-emerald-800 mb-2 flex items-center gap-1.5" style={{fontFamily:'Manrope,sans-serif'}}><Lightbulb className="h-3.5 w-3.5" />Success Tips</h4>
                  <ul className="space-y-1">{workflow.success_tips.map((t, i) => <li key={i} className="text-[11px] text-emerald-700 flex items-start gap-1.5"><CheckCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />{t}</li>)}</ul>
                </Card>
              )}
              {workflow.common_rejection_reasons?.length > 0 && (
                <Card className="p-4 border-red-200 bg-red-50/40 rounded-xl">
                  <h4 className="font-bold text-xs text-red-800 mb-2 flex items-center gap-1.5" style={{fontFamily:'Manrope,sans-serif'}}><ShieldAlert className="h-3.5 w-3.5" />Common Rejection Reasons</h4>
                  <ul className="space-y-1">{workflow.common_rejection_reasons.map((r, i) => <li key={i} className="text-[11px] text-red-700 flex items-start gap-1.5"><AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />{r}</li>)}</ul>
                </Card>
              )}

              {/* Government Forms */}
              {govForms.length > 0 && (
                <Card className="p-5 border-l-4 border-l-leamss-teal bg-leamss-teal_50/30 rounded-xl" data-testid="gov-forms-section">
                  <h4 className="font-bold text-sm text-leamss-teal mb-3 flex items-center gap-1.5" style={{fontFamily:'Manrope,sans-serif'}}><Download className="h-4 w-4" /> Official Government Forms ({govForms.length})</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {govForms.map((form, fi) => (
                      <a key={fi} href={form.url} target="_blank" rel="noopener noreferrer"
                         className="flex items-start gap-2.5 p-3 bg-white rounded-lg border border-leamss-teal_50 hover:border-leamss-teal_50 hover:shadow-sm transition-all group" data-testid={`gov-form-${fi}`}>
                        <FileText className="h-4 w-4 text-leamss-teal mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-xs text-slate-800 group-hover:text-leamss-teal">{form.name}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5">{form.description}</p>
                          <Badge className={`text-[8px] mt-1 ${form.mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'}`}>{form.mandatory ? 'Required' : 'Optional'}</Badge>
                        </div>
                        <ExternalLink className="h-3.5 w-3.5 text-leamss-teal group-hover:text-leamss-teal flex-shrink-0" />
                      </a>
                    ))}
                  </div>
                </Card>
              )}

              {/* Steps */}
              <div className="space-y-3">
                {(workflow.steps || []).map((s, si) => (
                  <Card key={si} className="border border-slate-200 rounded-xl overflow-hidden" data-testid={`step-${si}`}>
                    <div className="flex items-center gap-3 p-4 cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => toggleStep(si)}>
                      <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-[#2a777a] to-[#1e6365] text-white flex items-center justify-center text-sm font-bold flex-shrink-0 shadow-sm">{s.step_order}</div>
                      <div className="flex-1 min-w-0">
                        <Input value={s.step_name} className="font-bold text-sm h-8 border-none shadow-none p-0 focus-visible:ring-0" style={{fontFamily:'Manrope,sans-serif'}}
                               onClick={e => e.stopPropagation()} onChange={e => updateStep(si,'step_name',e.target.value)} />
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <Input type="number" value={s.duration_days||''} className="w-14 h-8 text-xs text-center rounded-lg" placeholder="days"
                               onClick={e => e.stopPropagation()} onChange={e => updateStep(si,'duration_days',parseInt(e.target.value)||null)} />
                        <span className="text-[10px] text-slate-400">days</span>
                        <Badge variant="outline" className="text-[10px] font-medium">{(s.required_documents||[]).length} docs</Badge>
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                                onClick={e => {e.stopPropagation();if(window.confirm('Delete step?'))removeStep(si);}}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                        {expandedSteps[si] ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                      </div>
                    </div>
                    {expandedSteps[si] && (
                      <div className="px-4 pb-4 border-t border-slate-100 space-y-3 pt-3">
                        <Textarea value={s.description||''} onChange={e => updateStep(si,'description',e.target.value)} rows={1} className="text-xs rounded-lg" placeholder="Step description..." />
                        {s.government_fees && <div className="flex items-center gap-2"><Label className="text-[10px] text-slate-500 flex-shrink-0">Fees:</Label><Input value={s.government_fees} onChange={e => updateStep(si,'government_fees',e.target.value)} className="h-8 text-xs flex-1 rounded-lg" /></div>}
                        
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2" style={{fontFamily:'Manrope,sans-serif'}}>Documents ({(s.required_documents||[]).length})</p>
                          <div className="space-y-1.5">
                            {(s.required_documents||[]).map((doc, di) => (
                              <div key={di} className="flex items-start gap-2.5 p-3 bg-slate-50 rounded-lg text-xs group hover:bg-slate-100 transition-colors" data-testid={`doc-${si}-${di}`}>
                                <FileText className="h-3.5 w-3.5 text-[#2a777a] mt-0.5 flex-shrink-0" />
                                <div className="flex-1 min-w-0 space-y-1">
                                  {editingDoc?.stepIdx===si && editingDoc?.docIdx===di ? (
                                    <><Input value={doc.name||doc.doc_name||''} onChange={e => updateDoc(si,di,doc.name!==undefined?'name':'doc_name',e.target.value)} className="h-7 text-xs rounded-lg font-semibold" />
                                    <Input value={doc.description||''} onChange={e => updateDoc(si,di,'description',e.target.value)} className="h-7 text-[10px] rounded-lg" placeholder="Description" />
                                    <div className="flex items-center gap-2">
                                      <label className="flex items-center gap-1 text-[10px]"><input type="checkbox" checked={doc.mandatory||doc.is_mandatory} onChange={e => updateDoc(si,di,doc.mandatory!==undefined?'mandatory':'is_mandatory',e.target.checked)} className="rounded h-3 w-3" />Mandatory</label>
                                      <Button size="sm" variant="ghost" className="h-5 text-[10px] text-emerald-600" onClick={() => setEditingDoc(null)}>Done</Button>
                                    </div></>
                                  ) : (
                                    <><p className="font-semibold text-slate-800">{doc.name||doc.doc_name||''}</p>
                                    {doc.description && <p className="text-[10px] text-slate-500">{doc.description}</p>}</>
                                  )}
                                </div>
                                <div className="flex items-center gap-1 flex-shrink-0">
                                  <Badge className={`text-[8px] ${(doc.mandatory||doc.is_mandatory)?'bg-red-100 text-red-700':'bg-slate-100 text-slate-500'}`}>{(doc.mandatory||doc.is_mandatory)?'Required':'Optional'}</Badge>
                                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 rounded-lg" onClick={() => setEditingDoc({stepIdx:si,docIdx:di})}><Edit3 className="h-3 w-3 text-slate-400" /></Button>
                                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 rounded-lg" onClick={() => removeDoc(si,di)}><X className="h-3 w-3 text-red-400" /></Button>
                                </div>
                              </div>
                            ))}
                          </div>
                          {newDocForm.stepIdx === si ? (
                            <div className="mt-2 p-3 border-2 border-dashed border-slate-300 rounded-lg space-y-2 bg-white">
                              <Input value={newDocForm.name} onChange={e => setNewDocForm({...newDocForm,name:e.target.value})} className="h-8 text-xs rounded-lg" placeholder="Document name" />
                              <Input value={newDocForm.description} onChange={e => setNewDocForm({...newDocForm,description:e.target.value})} className="h-8 text-xs rounded-lg" placeholder="Description (optional)" />
                              <div className="flex items-center justify-between">
                                <label className="flex items-center gap-1 text-[10px]"><input type="checkbox" checked={newDocForm.mandatory} onChange={e => setNewDocForm({...newDocForm,mandatory:e.target.checked})} className="rounded h-3 w-3" />Mandatory</label>
                                <div className="flex gap-1"><Button size="sm" className="h-7 text-[10px] bg-[#2a777a] rounded-lg" onClick={() => addDoc(si)}>Add</Button><Button size="sm" variant="ghost" className="h-7 text-[10px]" onClick={() => setNewDocForm({stepIdx:null,name:'',description:'',mandatory:true})}>Cancel</Button></div>
                              </div>
                            </div>
                          ) : (
                            <Button size="sm" variant="outline" className="mt-2 h-8 text-xs border-dashed w-full rounded-lg" onClick={() => setNewDocForm({stepIdx:si,name:'',description:'',mandatory:true})}>
                              <Plus className="h-3 w-3 mr-1" />Add Document
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>

              <Button variant="outline" className="w-full border-dashed text-sm rounded-xl h-11" onClick={addStep}><Plus className="h-4 w-4 mr-1.5" />Add Step</Button>

              {/* Save Bar */}
              <Card className="p-4 border-0 shadow-xl bg-white sticky bottom-4 rounded-xl">
                <div className="flex items-center gap-3">
                  <Button onClick={handleSave} disabled={saving||!verified} className={`flex-1 h-11 rounded-lg font-bold ${verified?'bg-[#2a777a] hover:bg-[#215f62] shadow-sm':'bg-slate-300 cursor-not-allowed'}`} data-testid="save-btn">
                    {saving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                    {verified ? 'Save as Product' : 'Verify to Save'}
                  </Button>
                  <Button variant="outline" className="h-11 rounded-lg" onClick={() => setView('gallery')}>Back</Button>
                </div>
                {!verified && <p className="text-[10px] text-center text-slate-400 mt-1.5">Review and verify the information above before saving</p>}
              </Card>
            </>
          )}
        </div>
      )}

      {/* ===== SAVED ===== */}
      {view === 'saved' && (
        <div className="text-center py-16" data-testid="workflow-saved" style={{fontFamily:"'IBM Plex Sans',sans-serif"}}>
          <div className="w-20 h-20 mx-auto mb-6 bg-emerald-100 rounded-2xl flex items-center justify-center"><CheckCircle className="h-10 w-10 text-emerald-600" /></div>
          <h2 className="text-2xl font-extrabold text-slate-900 mb-2" style={{fontFamily:'Manrope,sans-serif'}}>Workflow Saved!</h2>
          <p className="text-slate-500 text-sm mb-8">&ldquo;{workflow?.product_name}&rdquo; saved with all steps and documents.</p>
          <div className="flex justify-center gap-3">
            <Button onClick={() => {setView('gallery');setWorkflow(null);}} className="bg-[#2a777a] hover:bg-[#215f62] h-11 rounded-lg px-6 font-semibold"><Plus className="h-4 w-4 mr-2" />Create Another</Button>
            <Button variant="outline" className="h-11 rounded-lg px-6 font-semibold" onClick={() => navigate('/admin')}>Dashboard</Button>
          </div>
        </div>
      )}
    </DashboardShell>
  );
};

export default AIWorkflowBuilder;
