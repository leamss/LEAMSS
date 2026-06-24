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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Sparkles, ArrowLeft, Wand2, Copy, RefreshCw, Save,
  Megaphone, FileText, Mail, Share2, Newspaper, Target,
  Clock, Languages, Loader2,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CONTENT_TYPES = [
  { id: 'email', label: 'Email', icon: Mail },
  { id: 'blog', label: 'Blog', icon: Newspaper },
  { id: 'social_post', label: 'Social Post', icon: Share2 },
  { id: 'landing_copy', label: 'Landing Copy', icon: FileText },
  { id: 'press_release', label: 'Press Release', icon: Megaphone },
  { id: 'ad_copy', label: 'Ad Copy', icon: Target },
];

const VOICES = ['professional', 'conversational', 'authoritative', 'empathetic', 'witty'];
const LANGS = [
  { id: 'en', label: 'English' },
  { id: 'hi', label: 'Hindi' },
  { id: 'hinglish', label: 'Hinglish' },
];

export default function MarketingContentStudio() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [form, setForm] = useState({
    brief: '',
    content_type: 'email',
    target_audience: 'Indian IT professionals',
    keywords: '',
    brand_voice: 'professional',
    language: 'en',
    variants_count: 3,
  });
  const [variants, setVariants] = useState([]);
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [finalContent, setFinalContent] = useState('');
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  const generate = async () => {
    if (!form.brief.trim()) {
      toast.error('Please enter a brief first');
      return;
    }
    setGenerating(true);
    try {
      const payload = {
        ...form,
        keywords: form.keywords.split(',').map(k => k.trim()).filter(Boolean),
        variants_count: Number(form.variants_count) || 3,
      };
      const { data } = await axios.post(`${API}/content-studio/generate`, payload, auth);
      setVariants(data.variants || []);
      setSelectedVariant(null);
      toast.success(`Generated ${data.variants?.length || 0} variants with ${data.model}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const selectVariant = (v) => {
    setSelectedVariant(v.variant_number);
    setFinalContent(`Subject: ${v.subject_or_headline}\n\n${v.body}\n\nCTA: ${v.cta}`);
    toast.success(`Selected variant ${v.variant_number}`);
  };

  const saveDraft = async () => {
    if (!variants.length) {
      toast.error('Generate variants first');
      return;
    }
    setSaving(true);
    try {
      await axios.post(`${API}/content-studio/save-draft`, {
        title: form.brief.slice(0, 80),
        type: form.content_type,
        brief: form.brief,
        variants,
        selected_variant: selectedVariant,
        final_content: finalContent || null,
      }, auth);
      toast.success('Draft saved');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied!');
  };

  return (
    <div className="min-h-screen bg-slate-50" data-testid="content-studio-page">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/marketing')} data-testid="back-marketing">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Marketing
            </Button>
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-leamss-teal-600 to-leamss-orange-500 flex items-center justify-center">
                <Wand2 className="h-4 w-4 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">Content Studio <Badge className="bg-leamss-orange-500 text-white text-[10px]">AI · Claude Sonnet 4.5</Badge></h1>
                <p className="text-xs text-slate-500">Generate ready-to-publish marketing variants in seconds</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT: Brief form */}
        <Card className="lg:col-span-4 p-5 space-y-3 h-fit" data-testid="brief-panel">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-leamss-orange-500" />
            <h2 className="font-semibold text-slate-900">Brief</h2>
          </div>

          <div>
            <Label>What do you want to write?</Label>
            <Textarea
              rows={4}
              placeholder="e.g., Promote our Australia PR consultation service to Indian IT professionals in Bengaluru"
              value={form.brief}
              onChange={e => setForm({ ...form, brief: e.target.value })}
              data-testid="input-brief"
            />
          </div>

          <div>
            <Label>Content Type</Label>
            <div className="grid grid-cols-3 gap-1.5 mt-1">
              {CONTENT_TYPES.map(c => {
                const Icon = c.icon;
                const active = form.content_type === c.id;
                return (
                  <button
                    key={c.id}
                    onClick={() => setForm({ ...form, content_type: c.id })}
                    className={`flex flex-col items-center gap-1 p-2 rounded border text-[10px] font-medium transition-all ${
                      active ? 'bg-leamss-teal-50 border-leamss-teal-300 text-leamss-teal-700' : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                    }`}
                    data-testid={`type-${c.id}`}
                  >
                    <Icon className="h-3.5 w-3.5" /> {c.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <Label>Target Audience</Label>
            <Input
              value={form.target_audience}
              onChange={e => setForm({ ...form, target_audience: e.target.value })}
              data-testid="input-audience"
            />
          </div>

          <div>
            <Label>Keywords (comma-separated)</Label>
            <Input
              placeholder="australia pr, 189 visa, skilled migration"
              value={form.keywords}
              onChange={e => setForm({ ...form, keywords: e.target.value })}
              data-testid="input-keywords"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label>Brand Voice</Label>
              <Select value={form.brand_voice} onValueChange={v => setForm({ ...form, brand_voice: v })}>
                <SelectTrigger data-testid="input-voice"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {VOICES.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Language</Label>
              <Select value={form.language} onValueChange={v => setForm({ ...form, language: v })}>
                <SelectTrigger data-testid="input-language"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LANGS.map(l => <SelectItem key={l.id} value={l.id}>{l.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label>Variants</Label>
            <Input
              type="number"
              min="1"
              max="5"
              value={form.variants_count}
              onChange={e => setForm({ ...form, variants_count: e.target.value })}
              data-testid="input-variants-count"
            />
          </div>

          <Button
            onClick={generate}
            disabled={generating}
            className="w-full bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white"
            data-testid="generate-btn"
          >
            {generating ? <><Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> Generating…</> : <><Wand2 className="h-4 w-4 mr-1.5" /> Generate {form.variants_count} Variants</>}
          </Button>
        </Card>

        {/* RIGHT: Variants + Editor */}
        <div className="lg:col-span-8 space-y-3">
          {variants.length === 0 && !generating && (
            <Card className="p-12 text-center border-dashed border-slate-300" data-testid="empty-state">
              <Wand2 className="h-12 w-12 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">Enter a brief on the left and click "Generate" — Claude will write {form.variants_count} unique variants for you.</p>
            </Card>
          )}

          {variants.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3" data-testid="variants-grid">
              {variants.map(v => (
                <Card
                  key={v.variant_number}
                  className={`p-4 transition-all ${selectedVariant === v.variant_number ? 'ring-2 ring-leamss-teal-500 border-leamss-teal-300' : 'hover:shadow-md'}`}
                  data-testid={`variant-${v.variant_number}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <Badge className="bg-leamss-teal-100 text-leamss-teal-700">Variant {v.variant_number}</Badge>
                    <span className="text-[10px] text-slate-400 inline-flex items-center gap-0.5"><Clock className="h-3 w-3" /> {v.estimated_reading_time_min || 1} min</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 mb-2 line-clamp-2">{v.subject_or_headline}</h4>
                  <p className="text-xs text-slate-600 line-clamp-4 whitespace-pre-wrap mb-3">{v.body}</p>
                  {v.cta && <Badge variant="outline" className="text-[10px] mb-3"><Target className="h-2.5 w-2.5 mr-0.5" /> {v.cta}</Badge>}
                  {v.suggested_image_prompt && (
                    <p className="text-[10px] text-slate-400 italic mb-3 line-clamp-2">🎨 {v.suggested_image_prompt}</p>
                  )}
                  <div className="flex gap-1.5">
                    <Button size="sm" onClick={() => selectVariant(v)} className="flex-1 bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid={`use-variant-${v.variant_number}`}>
                      Use This
                    </Button>
                    <Button size="icon" variant="outline" onClick={() => copyToClipboard(`${v.subject_or_headline}\n\n${v.body}`)} data-testid={`copy-variant-${v.variant_number}`}>
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* Editor */}
          {selectedVariant && (
            <Card className="p-5" data-testid="editor-panel">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-slate-900 flex items-center gap-1.5">
                  <FileText className="h-4 w-4 text-leamss-teal-600" /> Final content
                </h3>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={generate} disabled={generating} data-testid="regenerate-btn">
                    <RefreshCw className="h-3.5 w-3.5 mr-1" /> Regenerate
                  </Button>
                  <Button size="sm" onClick={saveDraft} disabled={saving} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="save-draft-btn">
                    {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />} Save Draft
                  </Button>
                </div>
              </div>
              <Textarea
                rows={12}
                value={finalContent}
                onChange={e => setFinalContent(e.target.value)}
                placeholder="Selected variant content appears here — edit as needed"
                className="font-mono text-sm"
                data-testid="final-editor"
              />
              <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
                <span>{finalContent.length} chars · {finalContent.split(/\s+/).filter(Boolean).length} words</span>
                <span><Languages className="h-3 w-3 inline" /> {form.language}</span>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
