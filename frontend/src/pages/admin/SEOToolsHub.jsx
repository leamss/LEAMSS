import { useState } from 'react';
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
  ArrowLeft, Search, Tag, Link2, Loader2, Wand2, Copy,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

/**
 * Phase 21 Slice 3 Day 5 — SEO Tools Hub.
 * 3 AI tools: keyword research, meta optimization, internal linking suggestions.
 */
export default function SEOToolsHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [seedKw, setSeedKw] = useState('australia pr visa');
  const [kwResult, setKwResult] = useState(null);
  const [kwLoading, setKwLoading] = useState(false);

  const [metaContent, setMetaContent] = useState('');
  const [metaKeywords, setMetaKeywords] = useState('');
  const [metaResult, setMetaResult] = useState(null);
  const [metaLoading, setMetaLoading] = useState(false);

  const [linkContent, setLinkContent] = useState('');
  const [linkPages, setLinkPages] = useState('');
  const [linkResult, setLinkResult] = useState(null);
  const [linkLoading, setLinkLoading] = useState(false);

  const copy = (s) => { navigator.clipboard.writeText(s); toast.success('Copied'); };

  const runKw = async () => {
    if (!seedKw.trim()) { toast.error('Enter a seed keyword'); return; }
    setKwLoading(true);
    try {
      const { data } = await axios.post(`${API}/seo/keyword-research`, { seed_keyword: seedKw }, auth);
      setKwResult(data);
      toast.success('Keywords generated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setKwLoading(false); }
  };

  const runMeta = async () => {
    if (!metaContent.trim()) { toast.error('Paste content'); return; }
    setMetaLoading(true);
    try {
      const { data } = await axios.post(`${API}/seo/meta-optimize`, {
        raw_content: metaContent,
        target_keywords: metaKeywords.split(',').map(k => k.trim()).filter(Boolean),
      }, auth);
      setMetaResult(data);
      toast.success('Meta options generated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setMetaLoading(false); }
  };

  const runLinks = async () => {
    if (!linkContent.trim()) { toast.error('Paste page content'); return; }
    setLinkLoading(true);
    try {
      let pages = [];
      if (linkPages.trim()) {
        try { pages = JSON.parse(linkPages); } catch { pages = []; }
      }
      const { data } = await axios.post(`${API}/seo/internal-link-suggestions`, {
        page_content: linkContent,
        available_pages: pages,
      }, auth);
      setLinkResult(data);
      toast.success('Suggestions generated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setLinkLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="seo-hub-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin/marketing')} data-testid="seo-back">
            <ArrowLeft className="h-4 w-4 mr-1.5" /> Marketing
          </Button>
          <div className="flex items-center gap-2">
            <Search className="h-5 w-5 text-leamss-teal-600" />
            <div>
              <h1 className="text-lg font-bold text-slate-900">SEO Tools Hub</h1>
              <p className="text-xs text-slate-500">Keyword research · Meta optimisation · Internal linking — Powered by Claude Sonnet 4.5</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
        <Tabs defaultValue="keywords" className="space-y-4">
          <TabsList data-testid="seo-tabs">
            <TabsTrigger value="keywords" data-testid="seo-tab-keywords"><Search className="h-3.5 w-3.5 mr-1" />Keywords</TabsTrigger>
            <TabsTrigger value="meta" data-testid="seo-tab-meta"><Tag className="h-3.5 w-3.5 mr-1" />Meta</TabsTrigger>
            <TabsTrigger value="links" data-testid="seo-tab-links"><Link2 className="h-3.5 w-3.5 mr-1" />Internal Links</TabsTrigger>
          </TabsList>

          {/* KEYWORDS */}
          <TabsContent value="keywords">
            <Card className="p-5">
              <div className="flex items-end gap-2 mb-4">
                <div className="flex-1">
                  <Label>Seed keyword</Label>
                  <Input value={seedKw} onChange={e => setSeedKw(e.target.value)} data-testid="kw-seed" />
                </div>
                <Button onClick={runKw} disabled={kwLoading} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="kw-run">
                  {kwLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Wand2 className="h-4 w-4 mr-1" />} Research
                </Button>
              </div>
              {kwResult?.keywords?.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2" data-testid="kw-results">
                  {kwResult.keywords.map((k, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded border border-slate-200">
                      <div className="flex-1">
                        <p className="font-medium text-sm text-slate-800">{k.keyword}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-[10px] capitalize">{k.intent}</Badge>
                          <span className="text-[10px] text-slate-400">Difficulty {k.difficulty_pct}%</span>
                          <span className="text-[10px] text-slate-400">~{k.monthly_searches_estimate?.toLocaleString()}/mo</span>
                        </div>
                      </div>
                      <Button size="icon" variant="ghost" onClick={() => copy(k.keyword)}><Copy className="h-3.5 w-3.5" /></Button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </TabsContent>

          {/* META */}
          <TabsContent value="meta">
            <Card className="p-5 space-y-3">
              <div>
                <Label>Page content (excerpt)</Label>
                <Textarea rows={6} value={metaContent} onChange={e => setMetaContent(e.target.value)} placeholder="Paste the page content here…" data-testid="meta-content" />
              </div>
              <div>
                <Label>Target keywords (comma-separated)</Label>
                <Input value={metaKeywords} onChange={e => setMetaKeywords(e.target.value)} placeholder="australia pr, 189 visa" data-testid="meta-keywords" />
              </div>
              <Button onClick={runMeta} disabled={metaLoading} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="meta-run">
                {metaLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Wand2 className="h-4 w-4 mr-1" />} Optimise
              </Button>
              {metaResult?.options?.length > 0 && (
                <div className="space-y-3 mt-3" data-testid="meta-results">
                  {metaResult.options.map((o, i) => (
                    <Card key={i} className="p-4 border-leamss-teal-200">
                      <Badge className="bg-leamss-teal-100 text-leamss-teal-700 mb-2">Option {i + 1}</Badge>
                      <p className="text-sm font-semibold text-slate-900">Title: {o.meta_title}</p>
                      <p className="text-xs text-slate-600 mt-1">{o.meta_description}</p>
                      <p className="text-xs text-slate-500 mt-2">H1: <span className="font-medium">{o.h1}</span></p>
                      <p className="text-[11px] text-slate-400 italic mt-1">Why: {o.rationale}</p>
                      <div className="mt-2 flex gap-1.5">
                        <Button size="sm" variant="outline" onClick={() => copy(o.meta_title)} data-testid={`copy-title-${i}`}>Copy title</Button>
                        <Button size="sm" variant="outline" onClick={() => copy(o.meta_description)} data-testid={`copy-desc-${i}`}>Copy desc</Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </Card>
          </TabsContent>

          {/* INTERNAL LINKS */}
          <TabsContent value="links">
            <Card className="p-5 space-y-3">
              <div>
                <Label>Page content</Label>
                <Textarea rows={6} value={linkContent} onChange={e => setLinkContent(e.target.value)} placeholder="Paste the page content…" data-testid="link-content" />
              </div>
              <div>
                <Label>Available pages (JSON array, optional)</Label>
                <Textarea rows={3} value={linkPages} onChange={e => setLinkPages(e.target.value)} placeholder='[{"url":"/au","title":"AU PR","summary":"Australia PR pathways"}]' className="font-mono text-xs" data-testid="link-pages" />
              </div>
              <Button onClick={runLinks} disabled={linkLoading} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="link-run">
                {linkLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Wand2 className="h-4 w-4 mr-1" />} Suggest links
              </Button>
              {linkResult?.suggestions?.length > 0 && (
                <div className="space-y-2 mt-3" data-testid="link-results">
                  {linkResult.suggestions.map((s, i) => (
                    <div key={i} className="p-3 bg-slate-50 rounded border border-slate-200 text-sm">
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-slate-800">{s.anchor_text} → <code className="text-leamss-teal-700 text-xs">{s.target_url}</code></p>
                        <Badge variant="outline" className="text-[10px]">Score {s.relevance_score}/10</Badge>
                      </div>
                      <p className="text-[11px] text-slate-500 italic mt-1">{s.placement_hint}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
