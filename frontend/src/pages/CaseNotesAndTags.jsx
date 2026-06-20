import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StickyNote, Plus, Trash2, Pin, Tag, Loader2, X } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const NOTE_COLORS = [
  { name: 'yellow', bg: 'bg-yellow-50 border-yellow-200', dot: 'bg-yellow-400' },
  { name: 'blue', bg: 'bg-blue-50 border-blue-200', dot: 'bg-blue-400' },
  { name: 'green', bg: 'bg-green-50 border-green-200', dot: 'bg-green-400' },
  { name: 'pink', bg: 'bg-pink-50 border-pink-200', dot: 'bg-pink-400' },
  { name: 'purple', bg: 'bg-leamss-orange-50 border-leamss-orange-200', dot: 'bg-leamss-orange-400' },
];

export default function CaseNotesAndTags({ caseId, token }) {
  const [notes, setNotes] = useState([]);
  const [tags, setTags] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ content: '', color: 'yellow', is_pinned: false });
  const [tagInput, setTagInput] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => { if (caseId) { fetchNotes(); fetchTags(); } }, [caseId]);

  const fetchNotes = async () => {
    try {
      const res = await fetch(`${API}/api/case-notes/case/${caseId}`, { headers: { Authorization: `Bearer ${token}` } });
      setNotes(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const fetchTags = async () => {
    try {
      const res = await fetch(`${API}/api/case-notes/tags/${caseId}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setTags(data.tags || []);
    } catch (e) { console.error(e); }
  };

  const addNote = async () => {
    if (!form.content.trim()) return;
    await fetch(`${API}/api/case-notes`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ case_id: caseId, ...form })
    });
    setForm({ content: '', color: 'yellow', is_pinned: false });
    setShowForm(false);
    fetchNotes();
  };

  const deleteNote = async (id) => {
    await fetch(`${API}/api/case-notes/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    fetchNotes();
  };

  const addTag = async () => {
    if (!tagInput.trim()) return;
    const newTags = [...tags, tagInput.trim()];
    await fetch(`${API}/api/case-notes/tags`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ case_id: caseId, tags: newTags })
    });
    setTags(newTags);
    setTagInput('');
  };

  const removeTag = async (tag) => {
    const newTags = tags.filter(t => t !== tag);
    await fetch(`${API}/api/case-notes/tags`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ case_id: caseId, tags: newTags })
    });
    setTags(newTags);
  };

  if (loading) return <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin" /></div>;

  const colorInfo = (c) => NOTE_COLORS.find(nc => nc.name === c) || NOTE_COLORS[0];

  return (
    <div className="space-y-6" data-testid="case-notes-tags">
      {/* Tags Section */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Tag className="w-4 h-4" /> Case Tags</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2 mb-2">
            {tags.map(tag => (
              <Badge key={tag} variant="outline" className="gap-1 pr-1">
                {tag}
                <button onClick={() => removeTag(tag)} className="ml-1 hover:text-red-500"><X className="w-3 h-3" /></button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <input className="border rounded-md px-2 py-1 text-sm flex-1" placeholder="Add tag..." value={tagInput} onChange={e => setTagInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && addTag()} data-testid="tag-input" />
            <Button size="sm" onClick={addTag} data-testid="add-tag-btn"><Plus className="w-3 h-3" /></Button>
          </div>
        </CardContent>
      </Card>

      {/* Notes Section */}
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-sm flex items-center gap-2"><StickyNote className="w-4 h-4" /> Notes ({notes.length})</h3>
        <Button size="sm" onClick={() => setShowForm(!showForm)} data-testid="add-note-btn">
          <Plus className="w-3 h-3 mr-1" /> Add Note
        </Button>
      </div>

      {showForm && (
        <Card className="border-dashed">
          <CardContent className="pt-4 space-y-3">
            <textarea className="w-full border rounded-md p-2 text-sm" rows={3} placeholder="Write a note..." value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} data-testid="note-content" />
            <div className="flex items-center gap-3">
              <div className="flex gap-1">
                {NOTE_COLORS.map(c => (
                  <button key={c.name} onClick={() => setForm({ ...form, color: c.name })} className={`w-6 h-6 rounded-full ${c.dot} ${form.color === c.name ? 'ring-2 ring-offset-1 ring-gray-400' : ''}`} />
                ))}
              </div>
              <label className="flex items-center gap-1 text-xs">
                <input type="checkbox" checked={form.is_pinned} onChange={e => setForm({ ...form, is_pinned: e.target.checked })} /> <Pin className="w-3 h-3" /> Pin
              </label>
              <div className="flex-1" />
              <Button size="sm" onClick={addNote} data-testid="save-note-btn">Save</Button>
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {[...notes].sort((a, b) => (b.is_pinned ? 1 : 0) - (a.is_pinned ? 1 : 0)).map(n => {
          const ci = colorInfo(n.color);
          return (
            <Card key={n.id} className={`${ci.bg} border`}>
              <CardContent className="pt-3 pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    {n.is_pinned && <Pin className="w-3 h-3 text-gray-500 inline mr-1" />}
                    <p className="text-sm whitespace-pre-wrap">{n.content}</p>
                  </div>
                  <button onClick={() => deleteNote(n.id)} className="text-gray-400 hover:text-red-500 ml-2"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
                <p className="text-[10px] text-gray-400 mt-2">{n.author_name} — {new Date(n.created_at).toLocaleDateString()}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
