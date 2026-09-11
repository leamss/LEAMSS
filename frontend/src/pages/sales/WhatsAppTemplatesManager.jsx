/**
 * WhatsApp Templates Manager — create / edit / delete reusable WhatsApp templates
 * with {placeholders}, attachment toggles (Report, SLA, Payment QR), AI drafting,
 * and a realistic live WhatsApp chat preview. Route: /sales/whatsapp-templates
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
  ArrowLeft, Plus, Save, Trash2, Loader2, MessageSquare, Star, Sparkles,
  FileText, ShieldCheck, QrCode, CheckCheck, Mail
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

const BLANK = {
  name: '',
  category: 'general',
  body: '',
  is_default: false,
  attach_report: true,
  attach_sla: false,
  attach_qr: false,
};

export default function WhatsAppTemplatesManager() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [templates, setTemplates] = useState([]);
  const [placeholders, setPlaceholders] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(BLANK);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewText, setPreviewText] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const bodyRef = useRef(null);

  const draftWithAI = async () => {
    if (!aiPrompt.trim()) {
      toast.error('Describe the WhatsApp message you want AI to write');
      return;
    }
    setAiLoading(true);
    try {
      const r = await axios.post(
        `${API}/whatsapp-templates/ai-draft`,
        { prompt: aiPrompt, category: form.category },
        { headers }
      );
      upd({ body: r.data.body || form.body });
      toast.success('AI drafted your WhatsApp template — review & tweak, then Save');
    } catch (e) {
      toast.error(formatApiError(e, 'AI draft failed'));
    } finally {
      setAiLoading(false);
    }
  };

  const rewriteWithAI = async (instruction) => {
    if (!form.body.trim()) {
      toast.error('Write or load a template first, then AI can improve it');
      return;
    }
    setAiLoading(true);
    try {
      const r = await axios.post(
        `${API}/whatsapp-templates/ai-draft`,
        {
          mode: 'rewrite',
          prompt: instruction,
          category: form.category,
          current_body: form.body,
        },
        { headers }
      );
      upd({ body: r.data.body || form.body });
      toast.success('AI improved your WhatsApp message — review the changes, then Save');
    } catch (e) {
      toast.error(formatApiError(e, 'AI rewrite failed'));
    } finally {
      setAiLoading(false);
    }
  };

  const load = useCallback(async () => {
    try {
      const [t, ph] = await Promise.all([
        axios.get(`${API}/whatsapp-templates`, { headers }),
        axios.get(`${API}/whatsapp-templates/placeholders`, { headers }),
      ]);
      const list = t.data.templates || [];
      setTemplates(list);
      setPlaceholders(ph.data.placeholders || []);
      if (list.length > 0) {
        setSelectedId((prev) => {
          if (!prev) {
            const first = list[0];
            setForm({
              name: first.name,
              category: first.category,
              body: first.body,
              is_default: Boolean(first.is_default),
              attach_report: Boolean(first.attach_report ?? true),
              attach_sla: Boolean(first.attach_sla),
              attach_qr: Boolean(first.attach_qr),
            });
            return first.id;
          }
          return prev;
        });
      }
    } catch (e) {
      toast.error(formatApiError(e, 'Could not load WhatsApp templates'));
    }
  }, [headers]);

  useEffect(() => {
    load();
  }, [load]);

  // Live preview (debounced)
  useEffect(() => {
    const h = setTimeout(async () => {
      if (!form.body) {
        setPreviewText('');
        return;
      }
      try {
        const r = await axios.post(
          `${API}/whatsapp-templates/preview`,
          { body: form.body },
          { headers }
        );
        setPreviewText(r.data.rendered || '');
      } catch (e) {
        /* silent */
      }
    }, 300);
    return () => clearTimeout(h);
  }, [form.body, headers]);

  const selectTemplate = (t) => {
    setSelectedId(t.id);
    setForm({
      name: t.name,
      category: t.category,
      body: t.body,
      is_default: Boolean(t.is_default),
      attach_report: Boolean(t.attach_report ?? true),
      attach_sla: Boolean(t.attach_sla),
      attach_qr: Boolean(t.attach_qr),
    });
    setDirty(false);
  };

  const newTemplate = () => {
    setSelectedId(null);
    setForm(BLANK);
    setDirty(false);
  };

  const upd = (patch) => {
    setForm((f) => ({ ...f, ...patch }));
    setDirty(true);
  };

  const save = async () => {
    if (!form.name.trim()) {
      toast.error('Please give the WhatsApp template a name');
      return;
    }
    if (!form.body.trim()) {
      toast.error('Please write a message body for the template');
      return;
    }
    setSaving(true);
    try {
      if (selectedId) {
        const r = await axios.put(`${API}/whatsapp-templates/${selectedId}`, form, { headers });
        toast.success('WhatsApp template updated');
        setSelectedId(r.data.id);
      } else {
        const r = await axios.post(`${API}/whatsapp-templates`, form, { headers });
        toast.success('WhatsApp template created');
        setSelectedId(r.data.id);
      }
      setDirty(false);
      await load();
    } catch (e) {
      toast.error(formatApiError(e, 'Could not save template'));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this WhatsApp template?')) return;
    try {
      await axios.delete(`${API}/whatsapp-templates/${id}`, { headers });
      toast.success('WhatsApp template deleted');
      if (selectedId === id) newTemplate();
      await load();
    } catch (e) {
      toast.error(formatApiError(e, 'Could not delete template'));
    }
  };

  const insertPlaceholder = (token) => {
    const el = bodyRef.current;
    if (!el) {
      upd({ body: form.body + token });
      return;
    }
    const start = el.selectionStart ?? form.body.length;
    const end = el.selectionEnd ?? form.body.length;
    const next = form.body.slice(0, start) + token + form.body.slice(end);
    upd({ body: next });
    setTimeout(() => {
      el.focus();
      el.selectionStart = el.selectionEnd = start + token.length;
    }, 0);
  };

  // Helper to format WhatsApp text (*bold*, linebreaks) for preview
  const formatWhatsAppText = (text) => {
    if (!text) return null;
    const parts = text.split('\n');
    return parts.map((line, idx) => {
      // replace *text* with bold
      const boldFormatted = line.split(/(\*[^*]+\*)/g).map((chunk, cIdx) => {
        if (chunk.startsWith('*') && chunk.endsWith('*') && chunk.length > 2) {
          return <strong key={cIdx} className="font-semibold text-slate-900">{chunk.slice(1, -1)}</strong>;
        }
        return chunk;
      });
      return (
        <span key={idx} className="block min-h-[1.2em]">
          {boldFormatted}
        </span>
      );
    });
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-[1440px] mx-auto p-4 sm:p-6">
        {/* Top Header & Switcher */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-5">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/sales/bulk-assessment')}
              data-testid="back-btn"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />Back
            </Button>
            <div>
              <h1 className="text-xl font-bold flex items-center gap-2 text-slate-900">
                <MessageSquare className="h-5 w-5 text-emerald-600" />
                WhatsApp Templates Manager
              </h1>
              <p className="text-xs text-slate-500">
                Create reusable WhatsApp templates with AI drafting, placeholders, and multi-file attachments.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Switch to Email Templates */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/sales/email-templates')}
              className="text-xs border-slate-300 text-slate-700 hover:bg-slate-100"
            >
              <Mail className="h-3.5 w-3.5 mr-1 text-teal-600" />
              Email Templates
            </Button>

            <Button
              onClick={newTemplate}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-9"
              data-testid="new-template-btn"
            >
              <Plus className="h-4 w-4 mr-1" />New WhatsApp Template
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr_380px] gap-5">
          {/* Column 1: Templates List */}
          <Card className="p-2 h-fit bg-white shadow-sm border-slate-200" data-testid="templates-list">
            <div className="px-2 py-1.5 mb-1 flex items-center justify-between border-b border-slate-100">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Saved Templates ({templates.length})
              </span>
            </div>
            {templates.length === 0 && (
              <p className="text-xs text-slate-400 p-4 text-center">No WhatsApp templates yet</p>
            )}
            <div className="space-y-1 max-h-[calc(100vh-220px)] overflow-y-auto pr-1">
              {templates.map((t) => (
                <button
                  key={t.id}
                  onClick={() => selectTemplate(t)}
                  className={`w-full text-left p-3 rounded-xl transition-all ${
                    selectedId === t.id
                      ? 'bg-emerald-50/80 border-2 border-emerald-500 shadow-sm'
                      : 'hover:bg-slate-50 border border-transparent'
                  }`}
                  data-testid={`template-item-${t.id}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-slate-800 truncate">{t.name}</span>
                    {t.is_default && (
                      <Star className="h-3.5 w-3.5 text-amber-500 shrink-0" fill="currentColor" />
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                    <Badge className={`text-[9px] px-1.5 py-0 ${CATEGORY_COLORS[t.category] || 'bg-slate-100 text-slate-700'}`}>
                      {CATEGORY_LABELS[t.category] || t.category}
                    </Badge>
                    {t.attach_report && (
                      <span className="text-[9px] font-medium text-emerald-700 bg-emerald-50 px-1 rounded border border-emerald-200">
                        📄 Report
                      </span>
                    )}
                    {t.attach_sla && (
                      <span className="text-[9px] font-medium text-blue-700 bg-blue-50 px-1 rounded border border-blue-200">
                        📑 SLA
                      </span>
                    )}
                    {t.attach_qr && (
                      <span className="text-[9px] font-medium text-purple-700 bg-purple-50 px-1 rounded border border-purple-200">
                        💳 QR
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </Card>

          {/* Column 2: Editor */}
          <Card className="p-5 space-y-4 bg-white shadow-sm border-slate-200" data-testid="template-editor">
            {/* AI Assistant Box */}
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-3.5" data-testid="ai-draft-box">
              <div className="flex items-center gap-2 mb-1.5">
                <Sparkles className="h-4 w-4 text-emerald-600" />
                <span className="text-xs font-bold text-emerald-800">Draft WhatsApp Message with AI</span>
              </div>
              <Textarea
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                rows={2}
                placeholder="e.g. A positive assessment follow-up message with emojis, urgent discount reminder, and call booking link..."
                className="text-xs bg-white border-emerald-200 focus-visible:ring-emerald-500"
                data-testid="ai-prompt"
              />
              <div className="flex justify-end mt-2">
                <Button
                  size="sm"
                  onClick={draftWithAI}
                  disabled={aiLoading}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white h-8 text-xs font-medium shadow-sm"
                  data-testid="ai-draft-btn"
                >
                  {aiLoading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Sparkles className="h-3.5 w-3.5 mr-1" />}
                  Generate Message
                </Button>
              </div>
              {form.body.trim() && (
                <div className="mt-2.5 pt-2.5 border-t border-emerald-200/60">
                  <span className="text-[10px] text-emerald-700 font-semibold mr-1.5">One-click Polish:</span>
                  {[
                    ['Polish', 'Polish it: make it clearer, warmer and punchier while keeping emojis and all tokens intact.'],
                    ['Shorten', 'Make it noticeably shorter and concise for quick mobile reading.'],
                    ['More Urgent', 'Add persuasive urgency regarding limited slot availability and deadline.'],
                    ['Fix Grammar', 'Fix grammar and spacing while keeping the conversational tone.'],
                  ].map(([label, instr]) => (
                    <button
                      key={label}
                      onClick={() => rewriteWithAI(instr)}
                      disabled={aiLoading}
                      className="text-[10px] px-2.5 py-0.5 rounded-full bg-white border border-emerald-300 text-emerald-800 hover:bg-emerald-100 font-medium disabled:opacity-50 mr-1.5 mb-1 transition-colors"
                      data-testid={`ai-rewrite-${label.toLowerCase().replace(/\s+/g, '-')}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Template Info & Category */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold text-slate-700">Template Name</Label>
                <Input
                  value={form.name}
                  onChange={(e) => upd({ name: e.target.value })}
                  placeholder="e.g. Positive Assessment Welcome"
                  className="mt-1 text-xs"
                  data-testid="tpl-name"
                />
              </div>
              <div>
                <Label className="text-xs font-semibold text-slate-700">Category</Label>
                <Select value={form.category} onValueChange={(v) => upd({ category: v })}>
                  <SelectTrigger className="mt-1 text-xs" data-testid="tpl-category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Message Body */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs font-semibold text-slate-700">WhatsApp Message Body</Label>
                <span className="text-[11px] text-slate-400">{form.body.length} chars</span>
              </div>
              <Textarea
                ref={bodyRef}
                value={form.body}
                onChange={(e) => upd({ body: e.target.value })}
                rows={11}
                placeholder={'Hello {client_name}! 🎉\n\nYour Australia PR assessment outcome is *POSITIVE*...'}
                className="font-mono text-xs leading-relaxed"
                data-testid="tpl-body"
              />
              <p className="text-[10px] text-slate-500 mt-1">
                💡 Tip: Use <code className="text-emerald-700">*bold text*</code> for bold formatting in WhatsApp. Line breaks and emojis are preserved.
              </p>
            </div>

            {/* Placeholders */}
            <div>
              <Label className="text-[11px] font-semibold text-slate-600">Insert Dynamic Placeholder</Label>
              <div className="flex flex-wrap gap-1 mt-1.5 max-h-24 overflow-y-auto">
                {placeholders.map((ph) => (
                  <button
                    key={ph.token}
                    onClick={() => insertPlaceholder(ph.token)}
                    title={ph.desc}
                    className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 hover:bg-emerald-100 hover:text-emerald-800 text-slate-700 border border-slate-200 transition-colors"
                    data-testid={`ph-${ph.token}`}
                  >
                    {ph.token}
                  </button>
                ))}
              </div>
            </div>

            {/* Attachments & Defaults Selection */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
              <div className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                <span>📎 Direct WhatsApp Attachments & Flags</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                  <Switch
                    checked={form.attach_report}
                    onCheckedChange={(v) => upd({ attach_report: v })}
                    data-testid="tpl-attach-report"
                  />
                  <span>📄 Attach Assessment Report (23-pg PDF)</span>
                </label>

                <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                  <Switch
                    checked={form.attach_sla}
                    onCheckedChange={(v) => upd({ attach_sla: v })}
                    data-testid="tpl-attach-sla"
                  />
                  <span>📑 Attach Service Level Agreement (SLA PDF)</span>
                </label>

                <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                  <Switch
                    checked={form.attach_qr}
                    onCheckedChange={(v) => upd({ attach_qr: v })}
                    data-testid="tpl-attach-qr"
                  />
                  <span>💳 Attach Official Payment QR Code</span>
                </label>

                <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                  <Switch
                    checked={form.is_default}
                    onCheckedChange={(v) => upd({ is_default: v })}
                    data-testid="tpl-default"
                  />
                  <span>⭐ Set as Default for {CATEGORY_LABELS[form.category] || 'Category'}</span>
                </label>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2">
              <Button
                onClick={save}
                disabled={saving || !dirty}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-9 font-semibold"
                data-testid="save-template-btn"
              >
                {saving ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />}
                {selectedId ? 'Save Changes' : 'Create Template'}
              </Button>
              {selectedId && (
                <Button
                  variant="outline"
                  onClick={() => remove(selectedId)}
                  className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 text-xs h-9"
                  data-testid="delete-template-btn"
                >
                  <Trash2 className="h-4 w-4 mr-1" /> Delete
                </Button>
              )}
            </div>
          </Card>

          {/* Column 3: Realistic WhatsApp Live Chat Bubble Preview */}
          <Card className="p-0 overflow-hidden h-fit bg-[#EFEAE2] border-slate-300 shadow-md" data-testid="whatsapp-live-preview">
            {/* WhatsApp Header */}
            <div className="bg-[#075E54] text-white px-3.5 py-3 flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-emerald-700 border border-white/40 flex items-center justify-center font-bold text-xs text-white">
                  L
                </div>
                <div>
                  <div className="text-xs font-bold leading-tight">LEAMSS Official</div>
                  <div className="text-[10px] text-emerald-200">Verified Business Account</div>
                </div>
              </div>
              <Badge className="bg-emerald-800 text-[9px] text-emerald-100 border-none font-normal">
                Live Preview
              </Badge>
            </div>

            {/* WhatsApp Chat Area */}
            <div className="p-3.5 space-y-3 min-h-[480px] max-h-[620px] overflow-y-auto">
              <div className="text-center">
                <span className="text-[9px] font-semibold text-slate-500 bg-white/80 px-2.5 py-0.5 rounded-full shadow-xs">
                  TODAY
                </span>
              </div>

              {/* Message Bubble */}
              <div className="flex justify-end">
                <div className="bg-[#DCF8C6] text-slate-800 rounded-lg rounded-tr-none p-3 max-w-[92%] shadow-xs text-xs relative">
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap leading-relaxed break-words text-[11.5px]">
                    {previewText ? formatWhatsAppText(previewText) : (
                      <span className="text-slate-400 italic">Start typing message body to preview here...</span>
                    )}
                  </div>

                  {/* Attachment Cards Preview */}
                  {(form.attach_report || form.attach_sla || form.attach_qr) && (
                    <div className="mt-2.5 pt-2 border-t border-emerald-300/60 space-y-1.5">
                      <div className="text-[9.5px] font-bold text-emerald-900 uppercase tracking-wide">
                        Attached Files ({[form.attach_report, form.attach_sla, form.attach_qr].filter(Boolean).length})
                      </div>
                      {form.attach_report && (
                        <div className="flex items-center gap-2 p-1.5 bg-white rounded border border-emerald-200 text-[10.5px]">
                          <FileText className="h-4 w-4 text-rose-600 shrink-0" />
                          <div className="flex-1 truncate font-medium text-slate-800">
                            Rahul_Sharma_Assessment_Report.pdf
                          </div>
                          <span className="text-[9px] text-slate-400">23 pgs</span>
                        </div>
                      )}
                      {form.attach_sla && (
                        <div className="flex items-center gap-2 p-1.5 bg-white rounded border border-blue-200 text-[10.5px]">
                          <ShieldCheck className="h-4 w-4 text-blue-600 shrink-0" />
                          <div className="flex-1 truncate font-medium text-slate-800">
                            LEAMSS-Service-Level-Agreement.pdf
                          </div>
                          <span className="text-[9px] text-slate-400">SLA</span>
                        </div>
                      )}
                      {form.attach_qr && (
                        <div className="flex items-center gap-2 p-1.5 bg-white rounded border border-purple-200 text-[10.5px]">
                          <QrCode className="h-4 w-4 text-purple-600 shrink-0" />
                          <div className="flex-1 truncate font-medium text-slate-800">
                            LEAMSS-Payment-QR.png
                          </div>
                          <span className="text-[9px] text-purple-600 font-bold">UPI</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Timestamp & Double Blue Checks */}
                  <div className="flex items-center justify-end gap-1 mt-1 text-[9px] text-slate-500">
                    <span>11:42 AM</span>
                    <CheckCheck className="h-3.5 w-3.5 text-blue-500" />
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
