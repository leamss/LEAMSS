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
  ArrowLeft, MessageCircleQuestion, Mic, Sparkles, Loader2, Wand2, Copy, X,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

/**
 * Phase 21 Slice 3 Day 5 — AEO (Answer Engine Optimization) Tools.
 * FAQ schema JSON-LD · voice search rewrites · featured snippet drafts.
 */
export default function AEOToolsHub() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  // FAQ
  const [questions, setQuestions] = useState(['What is Australia 189 visa?']);
  const [faqTopic, setFaqTopic] = useState('Australia PR pathways');
  const [faqResult, setFaqResult] = useState(null);
  const [faqLoading, setFaqLoading] = useState(false);

  // Voice
  const [voiceContent, setVoiceContent] = useState('');
  const [voiceResult, setVoiceResult] = useState(null);
  const [voiceLoading, setVoiceLoading] = useState(false);

  // Featured snippet
  const [snippetTopic, setSnippetTopic] = useState('');
  const [snippetResult, setSnippetResult] = useState(null);
  const [snippetLoading, setSnippetLoading] = useState(false);

  const copy = (s) => { navigator.clipboard.writeText(typeof s === 'string' ? s : JSON.stringify(s, null, 2)); toast.success('Copied'); };

  const runFaq = async () => {
    const qs = questions.filter(q => q.trim());
    if (qs.length === 0) { toast.error('Enter at least one question'); return; }
    setFaqLoading(true);
    try {
      const { data } = await axios.post(`${API}/aeo/faq-schema-generate`, { questions: qs, topic: faqTopic }, auth);
      setFaqResult(data);
      toast.success('FAQ schema generated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setFaqLoading(false); }
  };

  const runVoice = async () => {
    if (!voiceContent.trim()) { toast.error('Paste content'); return; }
    setVoiceLoading(true);
    try {
      const { data } = await axios.post(`${API}/aeo/voice-search-optimize`, { content: voiceContent }, auth);
      setVoiceResult(data);
      toast.success('Voice variants generated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setVoiceLoading(false); }
  };

  const runSnippet = async () => {
    if (!snippetTopic.trim()) { toast.error('Enter a topic'); return; }
    setSnippetLoading(true);
    try {
      const { data } = await axios.post(`${API}/aeo/featured-snippet-target`, { topic: snippetTopic }, auth);
      setSnippetResult(data);
      toast.success('Snippet draft generated');
    } catch (e) { toast.error(e.response?.data?.detail || 'Failed'); }
    finally { setSnippetLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="aeo-hub-page">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin/marketing')} data-testid="aeo-back">
            <ArrowLeft className="h-4 w-4 mr-1.5" /> Marketing
          </Button>
          <div className="flex items-center gap-2">
            <MessageCircleQuestion className="h-5 w-5 text-leamss-orange-600" />
            <div>
              <h1 className="text-lg font-bold text-slate-900">AEO Tools Hub</h1>
              <p className="text-xs text-slate-500">FAQ schema · Voice search · Featured snippet — Powered by Claude Sonnet 4.5</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
        <Tabs defaultValue="faq" className="space-y-4">
          <TabsList data-testid="aeo-tabs">
            <TabsTrigger value="faq" data-testid="aeo-tab-faq"><MessageCircleQuestion className="h-3.5 w-3.5 mr-1" />FAQ Schema</TabsTrigger>
            <TabsTrigger value="voice" data-testid="aeo-tab-voice"><Mic className="h-3.5 w-3.5 mr-1" />Voice Search</TabsTrigger>
            <TabsTrigger value="snippet" data-testid="aeo-tab-snippet"><Sparkles className="h-3.5 w-3.5 mr-1" />Featured Snippet</TabsTrigger>
          </TabsList>

          {/* FAQ */}
          <TabsContent value="faq">
            <Card className="p-5 space-y-3">
              <div>
                <Label>Topic (optional)</Label>
                <Input value={faqTopic} onChange={e => setFaqTopic(e.target.value)} data-testid="faq-topic" />
              </div>
              <div className="space-y-2">
                <Label>Questions</Label>
                {questions.map((q, i) => (
                  <div key={i} className="flex gap-2">
                    <Input
                      value={q}
                      onChange={e => setQuestions(qs => qs.map((qq, idx) => idx === i ? e.target.value : qq))}
                      placeholder={`Question ${i + 1}`}
                      data-testid={`faq-q-${i}`}
                    />
                    <Button size="icon" variant="ghost" onClick={() => setQuestions(qs => qs.filter((_, idx) => idx !== i))} data-testid={`faq-remove-${i}`}>
                      <X className="h-4 w-4 text-leamss-red-500" />
                    </Button>
                  </div>
                ))}
                <Button size="sm" variant="outline" onClick={() => setQuestions([...questions, ''])} data-testid="faq-add">+ Add question</Button>
              </div>
              <Button onClick={runFaq} disabled={faqLoading} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="faq-run">
                {faqLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Wand2 className="h-4 w-4 mr-1" />} Generate FAQ + JSON-LD
              </Button>

              {faqResult?.answers?.length > 0 && (
                <div className="mt-4 space-y-3" data-testid="faq-results">
                  <div className="space-y-2">
                    {faqResult.answers.map((a, i) => (
                      <Card key={i} className="p-3">
                        <p className="text-sm font-semibold text-slate-900">Q: {a.q}</p>
                        <p className="text-xs text-slate-600 mt-1">A: {a.a}</p>
                      </Card>
                    ))}
                  </div>
                  <Card className="p-3 bg-slate-900 text-emerald-300 font-mono text-[11px] overflow-x-auto">
                    <div className="flex items-center justify-between mb-2">
                      <Badge className="bg-emerald-700 text-white">Schema.org JSON-LD</Badge>
                      <Button size="sm" variant="ghost" className="h-7 text-emerald-300 hover:text-white" onClick={() => copy(faqResult.json_ld)} data-testid="copy-json-ld">
                        <Copy className="h-3 w-3 mr-1" /> Copy
                      </Button>
                    </div>
                    <pre className="whitespace-pre-wrap text-[10px]">{JSON.stringify(faqResult.json_ld, null, 2)}</pre>
                  </Card>
                </div>
              )}
            </Card>
          </TabsContent>

          {/* VOICE */}
          <TabsContent value="voice">
            <Card className="p-5 space-y-3">
              <div>
                <Label>Page content</Label>
                <Textarea rows={5} value={voiceContent} onChange={e => setVoiceContent(e.target.value)} placeholder="Paste content to optimize for voice search…" data-testid="voice-content" />
              </div>
              <Button onClick={runVoice} disabled={voiceLoading} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="voice-run">
                {voiceLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Mic className="h-4 w-4 mr-1" />} Optimise for voice
              </Button>
              {voiceResult && (
                <div className="mt-3 space-y-3" data-testid="voice-results">
                  <Card className="p-3">
                    <h4 className="text-xs font-semibold text-slate-700 mb-1">Natural phrasings (Siri/Alexa-ready)</h4>
                    <ul className="text-xs text-slate-700 space-y-1 list-disc ml-4">
                      {voiceResult.natural_language_phrasings?.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </Card>
                  <Card className="p-3">
                    <h4 className="text-xs font-semibold text-slate-700 mb-1">Question variants</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {voiceResult.question_variants?.map((q, i) => <Badge key={i} variant="outline" className="text-[10px]">{q}</Badge>)}
                    </div>
                  </Card>
                  <Card className="p-3 bg-leamss-orange-50 border-leamss-orange-200">
                    <h4 className="text-xs font-semibold text-leamss-orange-700 mb-1">Conversational rewrite</h4>
                    <p className="text-xs text-slate-700 whitespace-pre-wrap">{voiceResult.conversational_tone_rewrite}</p>
                  </Card>
                </div>
              )}
            </Card>
          </TabsContent>

          {/* SNIPPET */}
          <TabsContent value="snippet">
            <Card className="p-5 space-y-3">
              <div>
                <Label>Topic / search query target</Label>
                <Input value={snippetTopic} onChange={e => setSnippetTopic(e.target.value)} placeholder="e.g., how to apply for australia 189 visa" data-testid="snippet-topic" />
              </div>
              <Button onClick={runSnippet} disabled={snippetLoading} className="bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" data-testid="snippet-run">
                {snippetLoading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1" />} Generate snippet
              </Button>
              {snippetResult && (
                <Card className="p-4 border-leamss-orange-200 mt-3" data-testid="snippet-result">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className="bg-leamss-orange-100 text-leamss-orange-700 capitalize">{snippetResult.best_snippet_type}</Badge>
                    <span className="text-[11px] text-slate-500 italic">Target: {snippetResult.target_query}</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mb-2">Why this type: {snippetResult.rationale}</p>
                  <div className="bg-slate-50 p-3 rounded border" dangerouslySetInnerHTML={{ __html: snippetResult.draft_content }} />
                  <Button size="sm" variant="outline" className="mt-2" onClick={() => copy(snippetResult.draft_content)} data-testid="copy-snippet">
                    <Copy className="h-3 w-3 mr-1" /> Copy HTML
                  </Button>
                </Card>
              )}
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
