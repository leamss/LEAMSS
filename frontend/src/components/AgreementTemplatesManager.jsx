import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { FileText, Plus, Edit, Copy, Trash2, Save, Upload, X, Check, Eye } from 'lucide-react';
import './agreement-doc.css';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EMPTY = { id: null, name: '', country: '', visa_category: '', policy_variant: 'Standard', body_html: '', notes: '', is_active: true };

export default function AgreementTemplatesManager() {
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null); // current template object being edited
  const [showUpload, setShowUpload] = useState(false);
  const [uploadForm, setUploadForm] = useState({ name: '', country: '', visa_category: 'PR', policy_variant: 'Standard', file: null });
  const [previewing, setPreviewing] = useState(null);
  const [loading, setLoading] = useState(true);

  const auth = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/agreement-templates?include_inactive=true`, auth());
      setItems(r.data.items || []);
    } catch (e) { toast.error('Load failed'); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const startNew = () => setEditing({ ...EMPTY });
  const startEdit = async (id) => {
    try {
      const r = await axios.get(`${API}/agreement-templates/${id}`, auth());
      setEditing(r.data);
    } catch (e) { toast.error('Failed to load'); }
  };
  const cancel = () => setEditing(null);

  const save = async () => {
    if (!editing.name || !editing.country || !editing.body_html) {
      toast.error('Name, Country and Body are required'); return;
    }
    try {
      if (editing.id) {
        await axios.put(`${API}/agreement-templates/${editing.id}`, editing, auth());
        toast.success('Template updated');
      } else {
        await axios.post(`${API}/agreement-templates`, editing, auth());
        toast.success('Template created');
      }
      setEditing(null);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
  };

  const clone = async (t) => {
    const newName = window.prompt('New template name:', `${t.name} (Copy)`);
    if (!newName) return;
    try {
      await axios.post(`${API}/agreement-templates/${t.id}/clone`, { new_name: newName }, auth());
      toast.success('Cloned');
      load();
    } catch (e) { toast.error('Clone failed'); }
  };

  const remove = async (t) => {
    if (!window.confirm(`Deactivate "${t.name}"? It can be re-activated later.`)) return;
    try {
      await axios.delete(`${API}/agreement-templates/${t.id}`, auth());
      toast.success('Deactivated');
      load();
    } catch (e) { toast.error('Delete failed'); }
  };

  const handleDocxUpload = async () => {
    if (!uploadForm.file || !uploadForm.name || !uploadForm.country) {
      toast.error('Fill all fields and select a .docx file'); return;
    }
    const fd = new FormData();
    fd.append('file', uploadForm.file);
    fd.append('name', uploadForm.name);
    fd.append('country', uploadForm.country);
    fd.append('visa_category', uploadForm.visa_category);
    fd.append('policy_variant', uploadForm.policy_variant);
    try {
      const r = await axios.post(`${API}/agreement-templates/upload-docx`, fd, {
        headers: { ...auth().headers, 'Content-Type': 'multipart/form-data' }
      });
      toast.success(`Draft created · ${r.data.draft.placeholders.length} placeholders detected`);
      setEditing({ ...EMPTY, ...r.data.draft });
      setShowUpload(false);
      setUploadForm({ name: '', country: '', visa_category: 'PR', policy_variant: 'Standard', file: null });
    } catch (e) { toast.error(e.response?.data?.detail || 'Upload failed'); }
  };

  if (editing) {
    const placeholders = (editing.body_html || '').match(/\{\{\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\}\}/g) || [];
    const uniquePlaceholders = [...new Set(placeholders.map(p => p.replace(/\{\{|\}\}|\s/g, '')))];
    return (
      <div className="space-y-4" data-testid="agreement-template-editor">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">{editing.id ? 'Edit Template' : 'New Template'}</h2>
          <div className="flex gap-2">
            <Button variant="outline" onClick={cancel}><X className="h-4 w-4 mr-1" /> Cancel</Button>
            <Button onClick={save} className="bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="template-save-btn"><Save className="h-4 w-4 mr-1" /> Save</Button>
          </div>
        </div>
        <Card className="p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600">Template Name *</label>
              <Input value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} placeholder="e.g. Australia · PR · Standard" data-testid="template-name" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">Country *</label>
              <Input value={editing.country} onChange={e => setEditing({ ...editing, country: e.target.value })} placeholder="e.g. Australia" data-testid="template-country" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">Visa Category *</label>
              <Input value={editing.visa_category} onChange={e => setEditing({ ...editing, visa_category: e.target.value })} placeholder="e.g. PR (Skilled Migration)" data-testid="template-category" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">Policy Variant *</label>
              <Input value={editing.policy_variant} onChange={e => setEditing({ ...editing, policy_variant: e.target.value })} placeholder="e.g. Standard / Protection" data-testid="template-variant" />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-slate-600">Body (HTML allowed) — use <code className="bg-slate-100 px-1">{'{{variable}}'}</code> for placeholders</label>
              <span className="text-[11px] text-slate-400">{uniquePlaceholders.length} placeholders detected</span>
            </div>
            <textarea
              value={editing.body_html}
              onChange={e => setEditing({ ...editing, body_html: e.target.value })}
              className="w-full border rounded-md p-3 font-mono text-xs h-96"
              placeholder="<h2>Service Agreement</h2><p>Client: {{client_name}}...</p>"
              data-testid="template-body"
            />
            {uniquePlaceholders.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {uniquePlaceholders.map((p, i) => (
                  <Badge key={i} className="bg-indigo-100 text-indigo-700 text-[10px] font-mono">{`{{${p}}}`}</Badge>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">Notes</label>
            <Input value={editing.notes || ''} onChange={e => setEditing({ ...editing, notes: e.target.value })} placeholder="Internal notes" />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={editing.is_active !== false} onChange={e => setEditing({ ...editing, is_active: e.target.checked })} />
            Active (visible to partners)
          </label>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="agreement-templates-manager">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2"><FileText className="h-6 w-6 text-[#2a777a]" /> Agreement Templates</h1>
          <p className="text-sm text-slate-500 mt-1">Country/Visa-aware retainer templates with auto-fill placeholders.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowUpload(true)} data-testid="upload-docx-btn">
            <Upload className="h-4 w-4 mr-1" /> Upload DOCX
          </Button>
          <Button onClick={startNew} className="bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="new-template-btn">
            <Plus className="h-4 w-4 mr-1" /> New Template
          </Button>
        </div>
      </div>

      <Card className="border-slate-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading…</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-slate-400">No templates yet. Click "New Template" or "Upload DOCX" to start.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">Name</th>
                <th className="px-3 py-2 text-left">Country</th>
                <th className="px-3 py-2 text-left">Visa Category</th>
                <th className="px-3 py-2 text-left">Variant</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Updated</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map(t => (
                <tr key={t.id} className="hover:bg-slate-50" data-testid={`template-row-${t.id}`}>
                  <td className="px-3 py-2.5 font-medium text-slate-800">{t.name}</td>
                  <td className="px-3 py-2.5 text-xs">{t.country}</td>
                  <td className="px-3 py-2.5 text-xs">{t.visa_category}</td>
                  <td className="px-3 py-2.5"><Badge className={t.policy_variant === 'Protection' ? 'bg-amber-100 text-amber-700 h-5 text-[11px]' : 'bg-slate-100 text-slate-700 h-5 text-[11px]'}>{t.policy_variant}</Badge></td>
                  <td className="px-3 py-2.5">
                    {t.is_active ? <Badge className="bg-emerald-100 text-emerald-700 h-5 text-[11px]">Active</Badge> : <Badge className="bg-slate-200 text-slate-600 h-5 text-[11px]">Inactive</Badge>}
                  </td>
                  <td className="px-3 py-2.5 text-[11px] text-slate-500">{t.updated_at ? new Date(t.updated_at).toLocaleDateString() : '—'} · v{t.version}</td>
                  <td className="px-3 py-2.5 text-right space-x-1">
                    <Button size="sm" variant="ghost" onClick={() => setPreviewing(t.id)} className="h-7 text-xs" data-testid={`tpl-view-${t.id}`}><Eye className="h-3 w-3" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => startEdit(t.id)} className="h-7 text-xs" data-testid={`tpl-edit-${t.id}`}><Edit className="h-3 w-3" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => clone(t)} className="h-7 text-xs" data-testid={`tpl-clone-${t.id}`}><Copy className="h-3 w-3" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => remove(t)} className="h-7 text-xs text-red-500" data-testid={`tpl-del-${t.id}`}><Trash2 className="h-3 w-3" /></Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Upload DOCX Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowUpload(false)}>
          <div className="bg-white rounded-xl max-w-md w-full p-5" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold">Upload DOCX Template</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowUpload(false)} className="h-7 w-7 p-0"><X className="h-4 w-4" /></Button>
            </div>
            <div className="space-y-2">
              <Input placeholder="Template name" value={uploadForm.name} onChange={e => setUploadForm({ ...uploadForm, name: e.target.value })} data-testid="upload-name" />
              <Input placeholder="Country" value={uploadForm.country} onChange={e => setUploadForm({ ...uploadForm, country: e.target.value })} data-testid="upload-country" />
              <Input placeholder="Visa Category" value={uploadForm.visa_category} onChange={e => setUploadForm({ ...uploadForm, visa_category: e.target.value })} />
              <Input placeholder="Policy Variant" value={uploadForm.policy_variant} onChange={e => setUploadForm({ ...uploadForm, policy_variant: e.target.value })} />
              <input type="file" accept=".docx" onChange={e => setUploadForm({ ...uploadForm, file: e.target.files[0] })} className="block w-full text-sm" data-testid="upload-file" />
              <p className="text-[11px] text-slate-500">Upload your blank agreement DOCX. Headings + paragraphs will be converted to HTML. Add <code className="bg-slate-100 px-1">{'{{client_name}}'}</code> placeholders manually after.</p>
            </div>
            <Button onClick={handleDocxUpload} className="w-full mt-3 bg-[#2a777a] hover:bg-[#206063] text-white" data-testid="upload-submit">
              <Upload className="h-4 w-4 mr-2" /> Extract & Open in Editor
            </Button>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewing && (
        <PreviewModal tid={previewing} onClose={() => setPreviewing(null)} />
      )}
    </div>
  );
}

function PreviewModal({ tid, onClose }) {
  const [t, setT] = useState(null);
  useEffect(() => {
    axios.get(`${API}/agreement-templates/${tid}`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      .then(r => setT(r.data));
  }, [tid]);
  if (!t) return null;
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="p-4 border-b flex items-center justify-between sticky top-0 bg-white">
          <div>
            <h3 className="font-bold">{t.name}</h3>
            <p className="text-xs text-slate-500">{t.country} · {t.visa_category} · {t.policy_variant} · v{t.version}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0"><X className="h-4 w-4" /></Button>
        </div>
        <div className="agreement-doc-wrap" dangerouslySetInnerHTML={{ __html: t.body_html }} />
      </div>
    </div>
  );
}
