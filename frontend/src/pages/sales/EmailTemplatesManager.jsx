/**
 * Email Templates Manager — create / edit / delete reusable email templates
 * with {placeholders} and a live preview. Route: /sales/email-templates
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  ArrowLeft, Plus, Save, Trash2, Loader2, Eye, LayoutTemplate, Star, Sparkles,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORY_LABELS = {
  eligible: 'Eligible (Positive)',
  not_eligible: 'Not-Eligible',
  resume: 'Resume Request',
  general: 'General',
};
const CATEGORY_COLORS = {
  eligible: 'bg-emerald-100 text-emerald-700',
  not_eligible: 'bg-amber-100 text-amber-700',
  resume: 'bg-rose-100 text-rose-700',
  general: 'bg-slate-100 text-slate-700',
};

const BLANK = { name: '', category: 'general', subject: '', body: '', is_default: false, attach_report: true, attach_resume: true };

export default function EmailTemplatesManager() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [templates, setTemplates] = useState([]);
  const [placeholders, setPlaceholders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(BLANK);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const bodyRef = useRef(null);

  const draftWithAI = async () => {
    if (!aiPrompt.trim()) { toast.error('Describe the email you want AI to write'); return; }
    setAiLoading(true);
    try {
      const r = await axios.post(`${API}/email-templates/ai-draft`, { prompt: aiPrompt, category: form.category }, { headers });
      upd({ subject: r.data.subject || form.subject, body: r.data.body || form.body });
      toast.success('AI drafted your email — review & tweak, then Save');
    } catch (e) { toast.error(formatApiError(e, 'AI draft failed')); }
    finally { setAiLoading(false); }
  };

  const rewriteWithAI = async (instruction) => {
    if (!form.body.trim()) { toast.error('Write or load a template first, then AI can improve it'); return; }
    setAiLoading(true);
    try {
      const r = await axios.post(`${API}/email-templates/ai-draft`, {
        mode: 'rewrite', prompt: instruction, category: form.category,
        current_subject: form.subject, current_body: form.body,
      }, { headers });
      upd({ subject: r.data.subject || form.subject, body: r.data.body || form.body });
      toast.success('AI improved your email — review the changes, then Save');
    } catch (e) { toast.error(formatApiError(e, 'AI rewrite failed')); }
    finally { setAiLoading(false); }
  };

  const load = useCallback(async () => {
    try {
      const [t, ph] = await Promise.all([
        axios.get(`${API}/email-templates`, { headers }),
        axios.get(`${API}/email-templates/placeholders`, { headers }),
      ]);
      setTemplates(t.data.templates || []);
      setPlaceholders(ph.data.placeholders || []);
    } catch (e) { toast.error(formatApiError(e, 'Could not load templates')); }
  }, [headers]);
  useEffect(() => { load(); }, [load]);

  // Live preview (debounced)
  useEffect(() => {
    const h = setTimeout(async () => {
      if (!form.subject && !form.body) { setPreviewHtml(''); return; }
      try {
        const r = await axios.post(`${API}/email-templates/preview`, { subject: form.subject, body: form.body }, { headers });
        setPreviewHtml(r.data.html || '');
      } catch (e) { /* silent */ }
    }, 500);
    return () => clearTimeout(h);
  }, [form.subject, form.body, headers]);

  const selectTemplate = (t) => {
    setSelectedId(t.id);
    setForm({
      name: t.name,
      category: t.category,
      subject: t.subject,
      body: t.body,
      is_default: t.is_default,
      attach_report: t.attach_report,
      attach_resume: t.attach_resume ?? true,
    });
    setDirty(false);
  };
  const newTemplate = () => { setSelectedId(null); setForm(BLANK); setDirty(false); };
  const upd = (patch) => { setForm((f) => ({ ...f, ...patch })); setDirty(true); };

  const save = async () => {
    if (!form.name.trim()) { toast.error('Please give the template a name'); return; }
    setSaving(true);
    try {
      if (selectedId) {
        const r = await axios.put(`${API}/email-templates/${selectedId}`, form, { headers });
        toast.success('Template updated');
        setSelectedId(r.data.id);
      } else {
        const r = await axios.post(`${API}/email-templates`, form, { headers });
        toast.success('Template created');
        setSelectedId(r.data.id);
      }
      setDirty(false);
      await load();
    } catch (e) { toast.error(formatApiError(e, 'Could not save template')); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this template?')) return;
    try {
      await axios.delete(`${API}/email-templates/${id}`, { headers });
      toast.success('Template deleted');
      if (selectedId === id) newTemplate();
      await load();
    } catch (e) { toast.error(formatApiError(e, 'Could not delete template')); }
  };

  const insertPlaceholder = (token) => {
    const el = bodyRef.current;
    if (!el) { upd({ body: form.body + token }); return; }
    const start = el.selectionStart ?? form.body.length;
    const end = el.selectionEnd ?? form.body.length;
    const next = form.body.slice(0, start) + token + form.body.slice(end);
    upd({ body: next });
    setTimeout(() => { el.focus(); el.selectionStart = el.selectionEnd = start + token.length; }, 0);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-[1400px] mx-auto p-4 sm:p-6">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/sales/bulk-assessment')} data-testid="back-btn">
              <ArrowLeft className="h-4 w-4 mr-1" />Back
            </Button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2"><LayoutTemplate className="h-5 w-5 text-teal-700" />Email Templates</h1>
              <p className="text-xs text-slate-500">Create reusable emails with placeholders — pick them when sending to clients.</p>
            </div>
          </div>
          <Button onClick={newTemplate} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="new-template-btn">
            <Plus className="h-4 w-4 mr-1" />New Template
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_1fr] gap-4">
          {/* List */}
          <Card className="p-2 h-fit" data-testid="templates-list">
            {templates.length === 0 && <p className="text-xs text-slate-400 p-4 text-center">No templates yet</p>}
            {templates.map((t) => (
              <button key={t.id} onClick={() => selectTemplate(t)}
                className={`w-full text-left p-2.5 rounded-lg mb-1 transition-colors ${selectedId === t.id ? 'bg-teal-50 border border-teal-200' : 'hover:bg-slate-50 border border-transparent'}`}
                data-testid={`template-item-${t.id}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium truncate">{t.name}</span>
                  {t.is_default && <Star className="h-3.5 w-3.5 text-amber-500 shrink-0" fill="currentColor" />}
                </div>
                <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                  <Badge className={`text-[9px] px-1.5 py-0 ${CATEGORY_COLORS[t.category]}`}>{CATEGORY_LABELS[t.category]}</Badge>
                  {t.attach_report && <span className="text-[9px] text-slate-400">📎 report</span>}
                  {t.attach_resume !== false && <span className="text-[9px] text-indigo-500">📎 resume</span>}
                </div>
              </button>
            ))}
          </Card>

          {/* Editor */}
          <Card className="p-4 space-y-3" data-testid="template-editor">
            <div className="rounded-lg border border-violet-200 bg-violet-50/60 p-3" data-testid="ai-draft-box">
              <div className="flex items-center gap-2 mb-1.5">
                <Sparkles className="h-4 w-4 text-violet-600" />
                <span className="text-xs font-semibold text-violet-700">Draft with AI</span>
              </div>
              <Textarea value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} rows={2}
                placeholder="e.g. A warm reminder email nudging clients that our Independence Day offer ends soon — book a call or pay to lock the slot."
                className="text-xs bg-white" data-testid="ai-prompt" />
              <div className="flex justify-end mt-2">
                <Button size="sm" onClick={draftWithAI} disabled={aiLoading}
                  className="bg-violet-600 hover:bg-violet-700 text-white h-8 text-xs" data-testid="ai-draft-btn">
                  {aiLoading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Sparkles className="h-3.5 w-3.5 mr-1" />}
                  Generate email
                </Button>
              </div>
              {form.body.trim() && (
                <div className="mt-2 pt-2 border-t border-violet-200/70">
                  <span className="text-[10px] text-violet-500 font-medium mr-1">Improve current:</span>
                  {[
                    ['Polish', 'Polish it: make it clearer, warmer and more persuasive while keeping it concise.'],
                    ['Shorten', 'Make it noticeably shorter and punchier without losing the key message or the call to action.'],
                    ['More persuasive', 'Make it more persuasive and urgency-driven to boost conversions, staying professional and warm.'],
                    ['Fix grammar', 'Fix any grammar and spelling, improve flow, keep the meaning and tone the same.'],
                  ].map(([label, instr]) => (
                    <button key={label} onClick={() => rewriteWithAI(instr)} disabled={aiLoading}
                      className="text-[10px] px-2 py-0.5 rounded-full bg-white border border-violet-300 text-violet-700 hover:bg-violet-100 disabled:opacity-50 mr-1 mb-1"
                      data-testid={`ai-rewrite-${label.toLowerCase().replace(/\s+/g, '-')}`}>
                      {label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Template name</Label>
                <Input value={form.name} onChange={(e) => upd({ name: e.target.value })} placeholder="e.g. Warm follow-up" data-testid="tpl-name" />
              </div>
              <div>
                <Label className="text-xs">Category</Label>
                <Select value={form.category} onValueChange={(v) => upd({ category: v })}>
                  <SelectTrigger data-testid="tpl-category"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(CATEGORY_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <Label className="text-xs">Subject</Label>
              <Input value={form.subject} onChange={(e) => upd({ subject: e.target.value })} placeholder="Hi {client_name}, your assessment outcome" data-testid="tpl-subject" />
            </div>

            <div>
              <Label className="text-xs">Body</Label>
              <Textarea ref={bodyRef} value={form.body} onChange={(e) => upd({ body: e.target.value })} rows={12}
                placeholder={'Dear {client_name},\n\nYour indicative score is {points} points for Subclass {best_subclass}...'}
                className="font-mono text-xs" data-testid="tpl-body" />
              <p className="text-[10px] text-slate-400 mt-1">Tip: start a line with "• " for a bullet. Use double line breaks for paragraphs.</p>
            </div>

            <div>
              <Label className="text-[11px] text-slate-500">Insert placeholder</Label>
              <div className="flex flex-wrap gap-1 mt-1">
                {placeholders.map((ph) => (
                  <button key={ph.token} onClick={() => insertPlaceholder(ph.token)} title={ph.desc}
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 hover:bg-teal-100 text-slate-600 hover:text-teal-700"
                    data-testid={`ph-${ph.token}`}>
                    {ph.token}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t">
              <div className="flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2 text-xs cursor-pointer">
                  <Switch checked={form.is_default} onCheckedChange={(v) => upd({ is_default: v })} data-testid="tpl-default" />
                  Default for category
                </label>
                <label className="flex items-center gap-2 text-xs cursor-pointer">
                  <Switch checked={form.attach_report} onCheckedChange={(v) => upd({ attach_report: v })} data-testid="tpl-attach" />
                  Attach PDF report
                </label>
                <label className="flex items-center gap-2 text-xs cursor-pointer">
                  <Switch checked={form.attach_resume ?? true} onCheckedChange={(v) => upd({ attach_resume: v })} data-testid="tpl-attach-resume" />
                  Attach Candidate Resume
                </label>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <Button onClick={save} disabled={saving || !dirty} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="save-template-btn">
                {saving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />}
                {selectedId ? 'Save changes' : 'Create template'}
              </Button>
              {selectedId && (
                <Button variant="outline" onClick={() => remove(selectedId)} className="text-rose-600 hover:text-rose-700" data-testid="delete-template-btn">
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          </Card>

          {/* Live preview */}
          <Card className="p-0 overflow-hidden h-fit" data-testid="template-preview">
            <div className="flex items-center gap-2 px-3 py-2 border-b bg-slate-50">
              <Eye className="h-3.5 w-3.5 text-slate-500" />
              <span className="text-xs font-semibold text-slate-600">Live Preview (sample data)</span>
            </div>
            {previewHtml
              ? <iframe title="preview" srcDoc={previewHtml} sandbox="allow-same-origin" className="w-full" style={{ height: 620, border: 'none' }} data-testid="preview-iframe" />
              : <div className="p-8 text-center text-xs text-slate-400">Start typing a subject or body to see the preview</div>}
          </Card>
        </div>
      </div>
    </div>
  );
}
