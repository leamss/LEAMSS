import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  ArrowLeft, Bot, FileCode2, Quote, Loader2, Wand2, Copy, Activity,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

/**
 * Phase 21 Slice 3 Day 5 — GEO (Generative Engine Optimization) Tools.
 * NEW DIFFERENTIATOR — make content quotable by LLMs (ChatGPT/Claude/Perplexity).
 * 4 tools: LLM content audit · structured data validator · crawl tracker · citation optimizer.
 */
export default function GEOToolsHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  // Audit
  const [auditUrl, setAuditUrl] = useState('');
  const [auditContent, setAuditContent] = useState('');
  const [auditResult, setAuditResult] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);

  // Structured data
  const [sdUrl, setSdUrl] = useState('');
  const [sdHtml, setSdHtml] = useState('');
  const [sdResult, setSdResult] = useState(null);
  const [sdLoading, setSdLoading] = useState(false);

  // Crawl tracker
  const [crawl, setCrawl] = useState(null);
  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get(`${API}/geo/llm-crawl-tracker`, auth);
        setCrawl(data);
      } catch {}
    })();
    // eslint-disable-next-line
  }, []);

  // Citation
  const [citContent, setCitContent] = useState('');
  const [citResult, setCitResult] = useState(null);
  const [citLoading, setCitLoading] = useState(false);

  const copy = (s) => { navigator.clipboard.writeText(typeof s === 'string' ? s : JSON.stringify(s, null, 2)); toast.success('Copied'); };

  const runAudit = async () => {
    if (!auditUrl.trim() && !auditContent.trim()) { toast.error('Provide URL or content'); return; }
    setAuditLoading(true);
    try {
      const { data } = await axios.post(`${API}/geo/llm-content-audit`, { url: auditUrl || null, content: auditContent || null }, auth);
      setAuditResult(data);
      toast.success('LLM audit done');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setAuditLoading(false); }
  };

  const runSd = async () => {
    if (!sdUrl.trim() && !sdHtml.trim()) { toast.error('Provide URL or HTML'); return; }
    setSdLoading(true);
    try {
      const { data } = await axios.post(`${API}/geo/structured-data-validator`, { url: sdUrl || null, html: sdHtml || null }, auth);
      setSdResult(data);
      toast.success('Schema validated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setSdLoading(false); }
  };

  const runCit = async () => {
    if (!citContent.trim()) { toast.error('Paste content'); return; }
    setCitLoading(true);
    try {
      const { data } = await axios.post(`${API}/geo/citation-optimizer`, { content: citContent }, auth);
      setCitResult(data);
      toast.success('Citation suggestions generated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setCitLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="geo-hub-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin/marketing')} data-testid="geo-back">
            <ArrowLeft className="h-4 w-4 mr-1.5" /> Marketing
          </Button>
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-leamss-red-600" />
            <div>
              <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">GEO Tools Hub <Badge className="bg-leamss-red-100 text-leamss-red-700 text-[10px]">NEW · LLM-era SEO</Badge></h1>
              <p className="text-xs text-slate-500">Make your content quotable by ChatGPT, Claude, Perplexity</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
        <Tabs defaultValue="audit" className="space-y-4">
          <TabsList data-testid="geo-tabs">
            <TabsTrigger value="audit" data-testid="geo-tab-audit"><Bot className="h-3.5 w-3.5 mr-1" />LLM Audit</TabsTrigger>
            <TabsTrigger value="schema" data-testid="geo-tab-schema"><FileCode2 className="h-3.5 w-3.5 mr-1" />Schema Validator</TabsTrigger>
            <TabsTrigger value="crawl" data-testid="geo-tab-crawl"><Activity className="h-3.5 w-3.5 mr-1" />LLM Crawl</TabsTrigger>
            <TabsTrigger value="citation" data-testid="geo-tab-citation"><Quote className="h-3.5 w-3.5 mr-1" />Citation</TabsTrigger>
          </TabsList>

          {/* AUDIT */}
          <TabsContent value="audit">
            <Card className="p-5 space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>Page URL (optional)</Label>
                  <Input value={auditUrl} onChange={e => setAuditUrl(e.target.value)} placeholder="https://leamss.com/au" data-testid="audit-url" />
                </div>
              </div>
              <div>
                <Label>OR paste content</Label>
                <Textarea rows={6} value={auditContent} onChange={e => setAuditContent(e.target.value)} placeholder="Paste up to 2500 chars…" data-testid="audit-content" />
              </div>
              <Button onClick={runAudit} disabled={auditLoading} className="bg-leamss-red-600 hover:bg-leamss-red-700 text-white" data-testid="audit-run">
                {auditLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Wand2 className="h-4 w-4 mr-1" />} Audit for LLM citations
              </Button>
              {auditResult && (
                <div className="space-y-3 mt-3" data-testid="audit-results">
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                    <ScoreTile label="Overall" value={auditResult.overall_score} max={10} accent="leamss-red" />
                    <ScoreTile label="Clarity" value={auditResult.clarity_score} max={10} accent="leamss-teal" />
                    <ScoreTile label="Citation-worthy" value={auditResult.citation_worthiness_score} max={10} accent="leamss-orange" />
                    <ScoreTile label="Structure" value={auditResult.structure_quality_score} max={10} accent="sky" />
                    <ScoreTile label="Factual" value={auditResult.factual_specificity_score} max={10} accent="emerald" />
                  </div>
                  <Card className="p-3 bg-emerald-50 border-emerald-200">
                    <h4 className="text-xs font-semibold text-emerald-800 mb-1">Strengths</h4>
                    <ul className="text-xs text-slate-700 space-y-1 list-disc ml-4">
                      {auditResult.strengths?.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </Card>
                  <Card className="p-3 bg-leamss-orange-50 border-leamss-orange-200">
                    <h4 className="text-xs font-semibold text-leamss-orange-700 mb-1">Improvements</h4>
                    <ul className="text-xs text-slate-700 space-y-1 list-disc ml-4">
                      {auditResult.improvements?.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </Card>
                  <Card className="p-3 bg-leamss-teal-50 border-leamss-teal-200">
                    <h4 className="text-xs font-semibold text-leamss-teal-700 mb-1">Recommended additions</h4>
                    <ul className="text-xs text-slate-700 space-y-1 list-disc ml-4">
                      {auditResult.recommended_additions?.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </Card>
                </div>
              )}
            </Card>
          </TabsContent>

          {/* SCHEMA */}
          <TabsContent value="schema">
            <Card className="p-5 space-y-3">
              <div>
                <Label>Page URL (optional)</Label>
                <Input value={sdUrl} onChange={e => setSdUrl(e.target.value)} placeholder="https://leamss.com/start" data-testid="sd-url" />
              </div>
              <div>
                <Label>OR paste HTML</Label>
                <Textarea rows={6} value={sdHtml} onChange={e => setSdHtml(e.target.value)} placeholder="<script type='application/ld+json'>…" className="font-mono text-xs" data-testid="sd-html" />
              </div>
              <Button onClick={runSd} disabled={sdLoading} className="bg-leamss-red-600 hover:bg-leamss-red-700 text-white" data-testid="sd-run">
                {sdLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <FileCode2 className="h-4 w-4 mr-1" />} Validate Schema.org
              </Button>
              {sdResult && (
                <div className="space-y-2 mt-3" data-testid="sd-results">
                  <ScoreTile label="Compliance" value={sdResult.compliance_score} max={10} accent="leamss-red" />
                  {sdResult.found_schemas?.length > 0 && (
                    <Card className="p-3">
                      <h4 className="text-xs font-semibold text-slate-700 mb-1">Found schemas</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {sdResult.found_schemas.map((s, i) => (
                          <Badge key={i} className={s.valid ? 'bg-emerald-100 text-emerald-700' : 'bg-leamss-red-100 text-leamss-red-700'}>
                            {s.type} {s.valid ? '✓' : '✗'}
                          </Badge>
                        ))}
                      </div>
                    </Card>
                  )}
                  {sdResult.errors?.length > 0 && (
                    <Card className="p-3 bg-leamss-red-50">
                      <h4 className="text-xs font-semibold text-leamss-red-700 mb-1">Errors</h4>
                      <ul className="text-xs text-slate-700 list-disc ml-4">{sdResult.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
                    </Card>
                  )}
                  {sdResult.missing_recommended_schemas?.length > 0 && (
                    <Card className="p-3 bg-leamss-orange-50">
                      <h4 className="text-xs font-semibold text-leamss-orange-700 mb-1">Missing recommended</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {sdResult.missing_recommended_schemas.map((s, i) => <Badge key={i} variant="outline" className="text-[10px]">{s}</Badge>)}
                      </div>
                    </Card>
                  )}
                </div>
              )}
            </Card>
          </TabsContent>

          {/* CRAWL */}
          <TabsContent value="crawl">
            <Card className="p-5" data-testid="crawl-card">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="h-4 w-4 text-leamss-red-600" />
                <h3 className="font-semibold text-slate-900 text-sm">LLM Bot Crawl Activity ({crawl?.tracking_period || 'last 7 days'})</h3>
              </div>
              {!crawl && <p className="text-xs text-slate-400">Loading…</p>}
              {crawl?.bots_detected && (
                <div className="space-y-2">
                  {crawl.bots_detected.map((b, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded border" data-testid={`bot-${b.user_agent}`}>
                      <div>
                        <p className="font-medium text-sm text-slate-800">{b.user_agent}</p>
                        <p className="text-[10px] text-slate-400">Last seen: {b.last_seen || 'Never'}</p>
                      </div>
                      <Badge className={b.visits > 0 ? 'bg-leamss-teal-100 text-leamss-teal-700' : 'bg-slate-100 text-slate-500'}>
                        {b.visits} visits
                      </Badge>
                    </div>
                  ))}
                  {crawl.note && <p className="text-[11px] text-slate-400 italic mt-2">{crawl.note}</p>}
                </div>
              )}
            </Card>
          </TabsContent>

          {/* CITATION */}
          <TabsContent value="citation">
            <Card className="p-5 space-y-3">
              <div>
                <Label>Content to make LLM-quotable</Label>
                <Textarea rows={6} value={citContent} onChange={e => setCitContent(e.target.value)} placeholder="Paste content…" data-testid="cit-content" />
              </div>
              <Button onClick={runCit} disabled={citLoading} className="bg-leamss-red-600 hover:bg-leamss-red-700 text-white" data-testid="cit-run">
                {citLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Quote className="h-4 w-4 mr-1" />} Optimise for citations
              </Button>
              {citResult && (
                <div className="space-y-3 mt-3" data-testid="cit-results">
                  {citResult.issues_found?.length > 0 && (
                    <Card className="p-3 bg-leamss-red-50">
                      <h4 className="text-xs font-semibold text-leamss-red-700 mb-1">Issues found</h4>
                      <ul className="text-xs text-slate-700 list-disc ml-4">{citResult.issues_found.map((i, idx) => <li key={idx}>{i}</li>)}</ul>
                    </Card>
                  )}
                  {citResult.suggestions?.map((s, i) => (
                    <Card key={i} className="p-3 border-leamss-teal-200">
                      <div className="flex items-center justify-between mb-1">
                        <Badge className="bg-leamss-teal-100 text-leamss-teal-700">{s.issue}</Badge>
                        <Badge variant="outline" className="capitalize text-[10px]">{s.expected_impact} impact</Badge>
                      </div>
                      <p className="text-xs text-slate-700">{s.fix}</p>
                    </Card>
                  ))}
                  {citResult.rewritten_intro_paragraph && (
                    <Card className="p-3 bg-leamss-orange-50 border-leamss-orange-200">
                      <h4 className="text-xs font-semibold text-leamss-orange-700 mb-1">Rewritten intro (LLM-friendly)</h4>
                      <p className="text-xs text-slate-700 whitespace-pre-wrap">{citResult.rewritten_intro_paragraph}</p>
                      <Button size="sm" variant="outline" className="mt-2" onClick={() => copy(citResult.rewritten_intro_paragraph)} data-testid="cit-copy-intro">
                        <Copy className="h-3 w-3 mr-1" /> Copy
                      </Button>
                    </Card>
                  )}
                  {citResult.key_facts_to_add?.length > 0 && (
                    <Card className="p-3">
                      <h4 className="text-xs font-semibold text-slate-700 mb-1">Key facts LLMs love to cite</h4>
                      <ul className="text-xs text-slate-700 list-disc ml-4">{citResult.key_facts_to_add.map((f, i) => <li key={i}>{f}</li>)}</ul>
                    </Card>
                  )}
                </div>
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function ScoreTile({ label, value, max, accent }) {
  const pct = (value / max) * 100;
  const color = {
    'leamss-red': 'text-leamss-red-600 bg-leamss-red-50 border-leamss-red-200',
    'leamss-teal': 'text-leamss-teal-700 bg-leamss-teal-50 border-leamss-teal-200',
    'leamss-orange': 'text-leamss-orange-700 bg-leamss-orange-50 border-leamss-orange-200',
    'sky': 'text-sky-700 bg-sky-50 border-sky-200',
    'emerald': 'text-emerald-700 bg-emerald-50 border-emerald-200',
  }[accent];
  return (
    <Card className={`p-3 border ${color}`}>
      <p className="text-[10px] uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-2xl font-bold">{value}<span className="text-sm opacity-50">/{max}</span></p>
      <div className="h-1 bg-white/50 rounded mt-1.5 overflow-hidden">
        <div className="h-full bg-current" style={{ width: `${pct}%` }} />
      </div>
    </Card>
  );
}
