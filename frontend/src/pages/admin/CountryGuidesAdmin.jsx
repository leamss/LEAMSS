/**
 * Phase 6.10 Part 3 — Country Guides Admin
 * Route: /admin/country-guides
 *
 * 5-country (AU/CA/NZ/UK/USA) editable knowledge base. Admin can:
 *   • Browse + filter by status (draft / verified / archived)
 *   • Edit hero + sections + FAQ
 *   • Generate AI draft (Claude Sonnet 4.6 via Emergent LLM Key)
 *   • Verify with mandatory source URL → flips status, publishes for public view
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ArrowLeft, Globe2, Wand2, CheckCircle2, AlertCircle, Loader2, Save, Sparkles,
  Plus, Trash2, ExternalLink, FileText, MessageSquare, ShieldCheck,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_PILL = {
  draft: 'bg-amber-100 text-amber-800',
  verified: 'bg-emerald-100 text-emerald-800',
  archived: 'bg-slate-200 text-slate-600',
};

export default function CountryGuidesAdmin() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [guides, setGuides] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCode, setSelectedCode] = useState(params.get('code') || '');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const url = statusFilter
        ? `${API}/country-guides/?status=${statusFilter}`
        : `${API}/country-guides/`;
      const r = await axios.get(url, { headers });
      setGuides(r.data.items || []);
      if (!selectedCode && r.data.items?.length) {
        setSelectedCode(r.data.items[0].country_code);
      }
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load guides'));
    } finally {
      setLoading(false);
    }
  }, [headers, statusFilter, selectedCode]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const selected = guides.find(g => g.country_code === selectedCode);

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="country-guides-admin">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/admin')} data-testid="back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />Admin Home
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Globe2 className="h-7 w-7 text-indigo-600" />
              Country Guides Admin
              <Badge className="bg-indigo-600 text-white text-[9px]">Phase 6.10.3</Badge>
            </h1>
            <p className="text-sm text-slate-500">AI drafts · Admin verifies · Public reads verified only</p>
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-xs text-slate-500">Status:</Label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs px-2 py-1 border rounded"
              data-testid="status-filter"
            >
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="verified">Verified</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* Left rail — guides list */}
          <Card className="col-span-3 p-3 h-[calc(100vh-140px)] overflow-auto" data-testid="guides-list">
            {loading ? (
              <div className="flex items-center justify-center py-10 text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : guides.length === 0 ? (
              <p className="text-xs text-slate-400 italic p-3">No guides yet.</p>
            ) : (
              <ul className="space-y-1.5">
                {guides.map(g => (
                  <li key={g.country_code}>
                    <button
                      onClick={() => {
                        setSelectedCode(g.country_code);
                        setParams({ code: g.country_code });
                      }}
                      className={`w-full text-left px-3 py-2 rounded text-sm transition ${
                        selectedCode === g.country_code
                          ? 'bg-indigo-50 border-l-4 border-indigo-500 font-semibold'
                          : 'hover:bg-slate-50 border-l-4 border-transparent'
                      }`}
                      data-testid={`guide-row-${g.country_code}`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{g.flag} {g.name}</span>
                        <Badge className={`text-[9px] ${STATUS_PILL[g.status] || 'bg-slate-100'}`}>
                          {g.status}
                        </Badge>
                      </div>
                      <p className="text-[10px] text-slate-500 mt-0.5">{g.country_code}</p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Right panel — editor */}
          <div className="col-span-9 space-y-3">
            {selected ? (
              <GuideEditor
                key={selected.country_code}
                guide={selected}
                headers={headers}
                onSaved={fetchAll}
              />
            ) : (
              <Card className="p-10 text-center text-slate-400">
                <Globe2 className="h-12 w-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">Select a country from the left to edit its guide.</p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function GuideEditor({ guide, headers, onSaved }) {
  const [doc, setDoc] = useState(() => structuredClone(guide));
  const [saving, setSaving] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [sourceRef, setSourceRef] = useState('');
  const [tab, setTab] = useState('hero');

  useEffect(() => { setDoc(structuredClone(guide)); }, [guide]);

  const updateSection = (key, body) => {
    setDoc(prev => ({
      ...prev,
      sections: prev.sections.map(s => (s.key === key ? { ...s, body_markdown: body } : s)),
    }));
  };

  const addFAQ = () => {
    setDoc(prev => ({ ...prev, faq: [...(prev.faq || []), { question: '', answer: '' }] }));
  };

  const removeFAQ = (idx) => {
    setDoc(prev => ({ ...prev, faq: prev.faq.filter((_, i) => i !== idx) }));
  };

  const updateFAQ = (idx, field, val) => {
    setDoc(prev => ({
      ...prev,
      faq: prev.faq.map((f, i) => (i === idx ? { ...f, [field]: val } : f)),
    }));
  };

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/country-guides/${doc.country_code}`,
        { hero: doc.hero, sections: doc.sections, faq: doc.faq }, { headers });
      toast.success('Saved · Status reset to draft. Verify again to publish.');
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  const generateAIDraft = async () => {
    if (!window.confirm('Generate AI draft via Claude Sonnet 4.6? Output goes to AI Draft tab — your manual edits stay intact.')) return;
    setDrafting(true);
    try {
      const r = await axios.post(`${API}/country-guides/${doc.country_code}/ai-draft`, {}, { headers });
      toast.success('AI Draft generated · Review under AI Draft tab');
      setDoc(prev => ({ ...prev, ai_draft: r.data.ai_draft }));
      setTab('ai-draft');
    } catch (e) {
      toast.error(formatApiError(e, 'AI draft failed'));
    } finally { setDrafting(false); }
  };

  const copyAIToManual = (key) => {
    if (!doc.ai_draft?.sections?.[key]) return;
    updateSection(key, doc.ai_draft.sections[key]);
    toast.success('Copied to manual editor — review then Save');
    setTab('sections');
  };

  const copyAIFAQToManual = () => {
    if (!doc.ai_draft?.faq?.length) return;
    setDoc(prev => ({ ...prev, faq: structuredClone(doc.ai_draft.faq) }));
    toast.success('AI FAQ copied to manual editor');
    setTab('faq');
  };

  const verify = async () => {
    if (!sourceRef || sourceRef.length < 5) {
      toast.error('Source reference URL required (min 5 chars)');
      return;
    }
    setVerifying(true);
    try {
      await axios.post(`${API}/country-guides/${doc.country_code}/verify`,
        { source_reference: sourceRef }, { headers });
      toast.success(`${doc.name} guide verified and published`);
      setSourceRef('');
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Verify failed'));
    } finally { setVerifying(false); }
  };

  return (
    <>
      <Card className="p-4" data-testid={`guide-editor-${doc.country_code}`}>
        <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
          <div>
            <h2 className="text-xl font-bold">{doc.flag} {doc.name}</h2>
            <p className="text-xs text-slate-500">
              {doc.country_code}
              {doc.verification?.at && (
                <span className="ml-2">· Verified by {doc.verification.by_name || 'admin'} on {new Date(doc.verification.at).toLocaleDateString()}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={STATUS_PILL[doc.status]}>{doc.status}</Badge>
            <a
              href={`/countries/${doc.country_code}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-indigo-600 hover:underline flex items-center gap-1"
              data-testid="preview-public-link"
            >
              <ExternalLink className="h-3 w-3" />Preview Public Page
            </a>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 pb-3 border-b">
          <Button size="sm" variant="outline" onClick={generateAIDraft} disabled={drafting}
                  className="border-violet-400 text-violet-700 hover:bg-violet-50" data-testid="ai-draft-btn">
            {drafting ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Wand2 className="h-3 w-3 mr-1" />}
            {drafting ? 'Drafting…' : 'AI Draft (Claude)'}
          </Button>
          <Button size="sm" onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-guide-btn">
            {saving ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Save className="h-3 w-3 mr-1" />}
            {saving ? 'Saving…' : 'Save Changes'}
          </Button>
          {doc.status === 'draft' && (
            <div className="flex items-center gap-2 ml-auto">
              <Input
                placeholder="Source URL (e.g., immi.gov.au)"
                value={sourceRef}
                onChange={(e) => setSourceRef(e.target.value)}
                className="h-8 text-xs w-64"
                data-testid="source-ref-input"
              />
              <Button size="sm" onClick={verify} disabled={verifying || !sourceRef}
                      className="bg-emerald-600 hover:bg-emerald-700" data-testid="verify-guide-btn">
                {verifying ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <ShieldCheck className="h-3 w-3 mr-1" />}
                Verify &amp; Publish
              </Button>
            </div>
          )}
        </div>

        <Tabs value={tab} onValueChange={setTab} className="mt-3">
          <TabsList className="bg-slate-100">
            <TabsTrigger value="hero" data-testid="tab-hero">Hero</TabsTrigger>
            <TabsTrigger value="sections" data-testid="tab-sections">Sections ({doc.sections?.length || 0})</TabsTrigger>
            <TabsTrigger value="faq" data-testid="tab-faq">FAQ ({doc.faq?.length || 0})</TabsTrigger>
            <TabsTrigger value="ai-draft" data-testid="tab-ai-draft">
              <Sparkles className="h-3 w-3 mr-1" />AI Draft
            </TabsTrigger>
          </TabsList>

          <TabsContent value="hero" className="pt-3 space-y-3">
            <div>
              <Label className="text-xs">Hero Title</Label>
              <Input
                value={doc.hero?.title || ''}
                onChange={(e) => setDoc(prev => ({ ...prev, hero: { ...prev.hero, title: e.target.value } }))}
                data-testid="hero-title-input"
              />
            </div>
            <div>
              <Label className="text-xs">Hero Subtitle</Label>
              <Textarea
                rows={2}
                value={doc.hero?.subtitle || ''}
                onChange={(e) => setDoc(prev => ({ ...prev, hero: { ...prev.hero, subtitle: e.target.value } }))}
                data-testid="hero-subtitle-input"
              />
            </div>
            <div>
              <Label className="text-xs">Hero Image URL (optional)</Label>
              <Input
                placeholder="https://images.unsplash.com/..."
                value={doc.hero?.image_url || ''}
                onChange={(e) => setDoc(prev => ({ ...prev, hero: { ...prev.hero, image_url: e.target.value } }))}
                data-testid="hero-image-input"
              />
            </div>
          </TabsContent>

          <TabsContent value="sections" className="pt-3 space-y-4">
            {(doc.sections || []).map(s => (
              <div key={s.key} className="space-y-1" data-testid={`section-${s.key}`}>
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-semibold">{s.title}</Label>
                  {doc.ai_draft?.sections?.[s.key] && (
                    <Button size="sm" variant="ghost"
                      onClick={() => copyAIToManual(s.key)}
                      className="text-[10px] text-violet-600 hover:bg-violet-50"
                      data-testid={`copy-ai-${s.key}`}>
                      <Sparkles className="h-3 w-3 mr-1" />Copy AI Draft
                    </Button>
                  )}
                </div>
                <Textarea
                  rows={6}
                  placeholder="Markdown supported (## headings, **bold**, lists)"
                  value={s.body_markdown}
                  onChange={(e) => updateSection(s.key, e.target.value)}
                  className="font-mono text-xs"
                  data-testid={`section-textarea-${s.key}`}
                />
              </div>
            ))}
          </TabsContent>

          <TabsContent value="faq" className="pt-3 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500">Up to 10 short Q&amp;A items.</p>
              <div className="flex gap-2">
                {doc.ai_draft?.faq?.length > 0 && (
                  <Button size="sm" variant="outline"
                    onClick={copyAIFAQToManual}
                    className="border-violet-300 text-violet-700"
                    data-testid="copy-ai-faq">
                    <Sparkles className="h-3 w-3 mr-1" />Copy AI FAQ ({doc.ai_draft.faq.length})
                  </Button>
                )}
                <Button size="sm" variant="outline" onClick={addFAQ} data-testid="add-faq-btn">
                  <Plus className="h-3 w-3 mr-1" />Add FAQ
                </Button>
              </div>
            </div>
            {(doc.faq || []).map((f, i) => (
              <Card key={i} className="p-3 space-y-2" data-testid={`faq-row-${i}`}>
                <div className="flex items-start gap-2">
                  <span className="text-xs font-bold text-slate-400 pt-2">Q{i + 1}.</span>
                  <Input
                    placeholder="Question"
                    value={f.question}
                    onChange={(e) => updateFAQ(i, 'question', e.target.value)}
                    data-testid={`faq-q-${i}`}
                  />
                  <Button size="sm" variant="ghost" onClick={() => removeFAQ(i)} data-testid={`faq-remove-${i}`}>
                    <Trash2 className="h-3 w-3 text-rose-500" />
                  </Button>
                </div>
                <Textarea
                  rows={2}
                  placeholder="Short answer (1-2 sentences)"
                  value={f.answer}
                  onChange={(e) => updateFAQ(i, 'answer', e.target.value)}
                  className="text-xs"
                  data-testid={`faq-a-${i}`}
                />
              </Card>
            ))}
            {!doc.faq?.length && (
              <p className="text-xs text-slate-400 italic">No FAQ yet — add some, or copy from AI Draft.</p>
            )}
          </TabsContent>

          <TabsContent value="ai-draft" className="pt-3 space-y-3">
            {!doc.ai_draft?.generated_at ? (
              <div className="text-center py-8 text-slate-400">
                <Sparkles className="h-10 w-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No AI draft yet — click "AI Draft (Claude)" above to generate.</p>
              </div>
            ) : (
              <>
                <div className="text-xs text-slate-500">
                  Generated {new Date(doc.ai_draft.generated_at).toLocaleString()} · Model: {doc.ai_draft.model}
                </div>
                {doc.ai_draft.admin_verify_note && (
                  <div className="bg-amber-50 border-l-4 border-amber-500 p-3 rounded text-xs">
                    <p className="font-semibold text-amber-900 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />Admin Verify Note
                    </p>
                    <p className="text-amber-800 mt-0.5">{doc.ai_draft.admin_verify_note}</p>
                  </div>
                )}
                {doc.ai_draft.hero_subtitle && (
                  <Card className="p-3" data-testid="ai-hero-section">
                    <div className="flex items-center justify-between mb-1">
                      <Label className="text-xs font-bold">Hero Subtitle Suggestion</Label>
                      <Button size="sm" variant="ghost"
                        onClick={() => {
                          setDoc(prev => ({ ...prev, hero: { ...prev.hero, subtitle: doc.ai_draft.hero_subtitle } }));
                          toast.success('Hero subtitle copied');
                          setTab('hero');
                        }}
                        className="text-[10px] text-violet-600"
                        data-testid="copy-ai-hero">
                        <Sparkles className="h-3 w-3 mr-1" />Use
                      </Button>
                    </div>
                    <p className="text-xs text-slate-700 italic">{doc.ai_draft.hero_subtitle}</p>
                  </Card>
                )}
                {Object.entries(doc.ai_draft.sections || {}).map(([key, body]) => (
                  <Card key={key} className="p-3" data-testid={`ai-section-${key}`}>
                    <div className="flex items-center justify-between mb-1">
                      <Label className="text-xs font-bold uppercase text-violet-700">{key.replace(/_/g, ' ')}</Label>
                      <Button size="sm" variant="ghost"
                        onClick={() => copyAIToManual(key)}
                        className="text-[10px] text-violet-600"
                        data-testid={`ai-copy-${key}`}>
                        <Sparkles className="h-3 w-3 mr-1" />Copy to Editor
                      </Button>
                    </div>
                    <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans">{body}</pre>
                  </Card>
                ))}
              </>
            )}
          </TabsContent>
        </Tabs>
      </Card>
    </>
  );
}
