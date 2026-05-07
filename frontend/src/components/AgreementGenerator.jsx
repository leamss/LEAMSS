import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { X, FileText, Send, ChevronRight, ChevronLeft, Eye, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * AgreementGenerator — partner-side modal for selecting + generating client agreement.
 * Props:
 *   pa            current pre-assessment (must have id, country, etc.)
 *   onClose       () => void
 *   onGenerated   (agreement) => void — called after successful generation
 */
export default function AgreementGenerator({ pa, onClose, onGenerated }) {
  const [step, setStep] = useState(1); // 1 = pick template, 2 = fill vars, 3 = preview
  const [meta, setMeta] = useState({ countries: [], categories: [], variants: [] });
  const [filters, setFilters] = useState({ country: pa?.country || '', category: '', variant: '' });
  const [templates, setTemplates] = useState([]);
  const [picked, setPicked] = useState(null);
  const [autoVars, setAutoVars] = useState({});
  const [vars, setVars] = useState({});
  const [generating, setGenerating] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  useEffect(() => {
    axios.get(`${API}/agreement-templates/meta/options`, auth()).then(r => setMeta(r.data)).catch(() => {});
    axios.get(`${API}/pa-agreements/auto-vars/${pa.id}`, auth()).then(r => {
      setAutoVars(r.data.variables || {});
      setVars(r.data.variables || {});
    }).catch(() => {});
  }, [pa.id]);

  const loadTemplates = useCallback(async () => {
    const params = new URLSearchParams();
    if (filters.country) params.set('country', filters.country);
    if (filters.category) params.set('visa_category', filters.category);
    if (filters.variant) params.set('policy_variant', filters.variant);
    try {
      const r = await axios.get(`${API}/agreement-templates?${params}`, auth());
      setTemplates(r.data.items || []);
    } catch (e) { /* ignore */ }
  }, [filters]);

  useEffect(() => { loadTemplates(); }, [loadTemplates]);

  const pickTemplate = async (t) => {
    try {
      const r = await axios.get(`${API}/agreement-templates/${t.id}`, auth());
      setPicked(r.data);
      setStep(2);
    } catch (e) { toast.error('Load failed'); }
  };

  const renderPreview = () => {
    if (!picked) return;
    let html = picked.body_html;
    Object.entries(vars).forEach(([k, v]) => {
      const re = new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g');
      html = html.replace(re, v || `<span class="bg-amber-100 text-amber-700 px-1 rounded text-xs">{{${k}}}</span>`);
    });
    setPreviewHtml(html);
    setStep(3);
  };

  const generate = async () => {
    setGenerating(true);
    try {
      const r = await axios.post(`${API}/pa-agreements/generate`, {
        pa_id: pa.id, template_id: picked.id, variables: vars,
      }, auth());
      toast.success(`Agreement generated · Ref ${r.data.reference_id}`);
      onGenerated && onGenerated(r.data);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Generation failed');
    }
    setGenerating(false);
  };

  // Distinct values from current templates list (helps with cascading dropdowns)
  const allCountries = [...new Set(templates.map(t => t.country))];
  const allCategories = filters.country ? [...new Set(templates.filter(t => t.country === filters.country).map(t => t.visa_category))] : meta.categories;
  const allVariants = (filters.country && filters.category) ? [...new Set(templates.filter(t => t.country === filters.country && t.visa_category === filters.category).map(t => t.policy_variant))] : meta.variants;

  const placeholders = picked ? (picked.placeholders || []) : [];

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()} data-testid="agreement-generator-modal">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between bg-gradient-to-r from-[#2a777a] to-teal-600 text-white">
          <div>
            <h3 className="font-bold flex items-center gap-2"><FileText className="h-5 w-5" /> Generate Service Agreement</h3>
            <p className="text-xs opacity-80">Step {step} of 3 · {pa.client_name} · {pa.country}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0 text-white hover:bg-white/20"><X className="h-4 w-4" /></Button>
        </div>

        {/* Step Indicator */}
        <div className="flex border-b">
          {[1, 2, 3].map(s => (
            <div key={s} className={`flex-1 py-2 text-center text-xs font-medium ${step >= s ? 'bg-[#2a777a]/10 text-[#2a777a]' : 'text-slate-400'}`}>
              {s === 1 ? 'Select Template' : s === 2 ? 'Fill Variables' : 'Preview & Send'}
            </div>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {/* Step 1: Pick Template */}
          {step === 1 && (
            <div className="space-y-4" data-testid="step-pick-template">
              <div className="grid grid-cols-3 gap-2">
                <select value={filters.country} onChange={e => setFilters({ ...filters, country: e.target.value, category: '', variant: '' })} className="border rounded-md px-2 py-2 text-sm" data-testid="filter-country">
                  <option value="">All Countries</option>
                  {meta.countries.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select value={filters.category} onChange={e => setFilters({ ...filters, category: e.target.value, variant: '' })} className="border rounded-md px-2 py-2 text-sm" data-testid="filter-category">
                  <option value="">All Categories</option>
                  {allCategories.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select value={filters.variant} onChange={e => setFilters({ ...filters, variant: e.target.value })} className="border rounded-md px-2 py-2 text-sm" data-testid="filter-variant">
                  <option value="">All Variants</option>
                  {allVariants.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              {templates.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-sm">No templates match your filter. Adjust filters or ask Admin to create one.</div>
              ) : (
                <div className="space-y-2">
                  {templates.map(t => (
                    <button key={t.id} onClick={() => pickTemplate(t)} className="w-full text-left border rounded-lg p-3 hover:border-[#2a777a] hover:bg-teal-50 transition" data-testid={`pick-tpl-${t.id}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-slate-800">{t.name}</p>
                          <p className="text-xs text-slate-500">{t.country} · {t.visa_category}</p>
                        </div>
                        <Badge className={t.policy_variant === 'Protection' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-700'}>{t.policy_variant}</Badge>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 2: Fill Variables */}
          {step === 2 && picked && (
            <div className="space-y-3" data-testid="step-fill-vars">
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-xs text-blue-800">
                <p className="font-semibold flex items-center gap-1"><Sparkles className="h-3.5 w-3.5" /> Auto-filled from PA data — edit any field if needed.</p>
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                {placeholders.map(p => (
                  <div key={p}>
                    <label className="text-[11px] font-medium text-slate-600 block">{p.replace(/_/g, ' ')}</label>
                    <Input
                      value={vars[p] || ''}
                      onChange={e => setVars({ ...vars, [p]: e.target.value })}
                      placeholder={`{{${p}}}`}
                      className={(vars[p] || '') === '' ? 'border-amber-300 bg-amber-50' : ''}
                      data-testid={`var-${p}`}
                    />
                  </div>
                ))}
              </div>
              {placeholders.length === 0 && (
                <p className="text-sm text-slate-400">This template has no placeholders.</p>
              )}
            </div>
          )}

          {/* Step 3: Preview */}
          {step === 3 && (
            <div data-testid="step-preview">
              <div className="border rounded-lg p-4 prose prose-sm max-w-none bg-white" dangerouslySetInnerHTML={{ __html: previewHtml }} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t bg-slate-50 flex items-center justify-between">
          <Button variant="outline" size="sm" onClick={() => step > 1 ? setStep(step - 1) : onClose()} data-testid="step-back">
            <ChevronLeft className="h-4 w-4 mr-1" /> {step > 1 ? 'Back' : 'Cancel'}
          </Button>
          {step === 1 && <span className="text-xs text-slate-500">Pick a template above</span>}
          {step === 2 && (
            <Button size="sm" onClick={renderPreview} className="bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="step-preview-btn">
              <Eye className="h-4 w-4 mr-1" /> Preview <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          )}
          {step === 3 && (
            <Button size="sm" onClick={generate} disabled={generating} className="bg-[#f7620b] hover:bg-[#e55a09] text-white" data-testid="step-generate-btn">
              <Send className="h-4 w-4 mr-1" /> {generating ? 'Generating…' : 'Generate & Send to Client'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
