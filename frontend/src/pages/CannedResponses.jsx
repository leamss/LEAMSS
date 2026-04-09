import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Plus, Edit, Trash2, Copy, Loader2, Zap } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function CannedResponses({ token, onInsert }) {
  const [responses, setResponses] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ title: '', content: '', category: 'general', shortcut: '', is_shared: false });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => { fetchResponses(); }, []);

  const fetchResponses = async () => {
    try {
      const res = await fetch(`${API}/api/canned-responses`, { headers: { Authorization: `Bearer ${token}` } });
      setResponses(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const save = async () => {
    if (!form.title || !form.content) return;
    const url = editId ? `${API}/api/canned-responses/${editId}` : `${API}/api/canned-responses`;
    const method = editId ? 'PUT' : 'POST';
    await fetch(url, { method, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(form) });
    setShowForm(false); setEditId(null);
    setForm({ title: '', content: '', category: 'general', shortcut: '', is_shared: false });
    fetchResponses();
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this response?')) return;
    await fetch(`${API}/api/canned-responses/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    fetchResponses();
  };

  const applyResponse = async (resp) => {
    await fetch(`${API}/api/canned-responses/${resp.id}/use`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
    if (onInsert) {
      onInsert(resp.content);
    } else {
      navigator.clipboard.writeText(resp.content);
      toast.success('Copied to clipboard');
    }
    fetchResponses();
  };

  const filtered = responses.filter(r =>
    !search || r.title.toLowerCase().includes(search.toLowerCase()) || r.content.toLowerCase().includes(search.toLowerCase()) || r.shortcut?.includes(search)
  );

  const categories = [...new Set(responses.map(r => r.category))];

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  return (
    <div className="space-y-4" data-testid="canned-responses">
      <div className="flex gap-2 items-center">
        <input className="border rounded-md px-3 py-2 text-sm flex-1" placeholder="Search responses or type shortcut..." value={search} onChange={e => setSearch(e.target.value)} data-testid="canned-search" />
        <Button onClick={() => { setShowForm(true); setEditId(null); setForm({ title: '', content: '', category: 'general', shortcut: '', is_shared: false }); }} data-testid="new-canned-btn">
          <Plus className="w-4 h-4 mr-1" /> New
        </Button>
      </div>

      {showForm && (
        <Card className="border-dashed">
          <CardContent className="pt-4 space-y-3">
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Title (e.g., Document Received)" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} data-testid="canned-title" />
            <textarea className="w-full border rounded-md p-2 text-sm" rows={3} placeholder="Response content..." value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} data-testid="canned-content" />
            <div className="grid grid-cols-3 gap-2">
              <input className="border rounded-md p-2 text-sm" placeholder="Category" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} />
              <input className="border rounded-md p-2 text-sm" placeholder="Shortcut (e.g., /docs)" value={form.shortcut} onChange={e => setForm({ ...form, shortcut: e.target.value })} />
              <label className="flex items-center gap-1 text-sm"><input type="checkbox" checked={form.is_shared} onChange={e => setForm({ ...form, is_shared: e.target.checked })} /> Share with team</label>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={save} data-testid="canned-save-btn">Save</Button>
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Category filter */}
      <div className="flex gap-1 flex-wrap">
        {categories.map(c => (
          <Badge key={c} variant="outline" className="text-xs cursor-pointer" onClick={() => setSearch(c)}>{c}</Badge>
        ))}
      </div>

      <div className="space-y-2">
        {filtered.map(r => (
          <Card key={r.id} className="hover:shadow-sm transition-shadow">
            <CardContent className="py-3 px-4">
              <div className="flex items-start justify-between">
                <div className="flex-1 cursor-pointer" onClick={() => applyResponse(r)}>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm">{r.title}</p>
                    {r.shortcut && <Badge variant="outline" className="text-[10px] px-1.5">{r.shortcut}</Badge>}
                    {r.is_shared && <Badge className="text-[10px] bg-blue-100 text-blue-700">Shared</Badge>}
                  </div>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{r.content}</p>
                  <p className="text-[10px] text-gray-400 mt-1">Used {r.usage_count || 0} times</p>
                </div>
                <div className="flex gap-1 ml-2">
                  <Button size="sm" variant="ghost" onClick={() => applyResponse(r)} title="Use"><Copy className="w-3 h-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => { setEditId(r.id); setForm(r); setShowForm(true); }}><Edit className="w-3 h-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(r.id)}><Trash2 className="w-3 h-3 text-red-500" /></Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filtered.length === 0 && (
        <Card><CardContent className="py-8 text-center text-gray-500"><MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" /><p>No canned responses yet. Create your first one!</p></CardContent></Card>
      )}
    </div>
  );
}
