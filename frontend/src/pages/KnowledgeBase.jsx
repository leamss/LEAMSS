import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Search, Plus, Edit, Trash2, Eye, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function KnowledgeBase({ token, role }) {
  const [articles, setArticles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedCat, setSelectedCat] = useState('');
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', content: '', category: 'general', tags: [], is_published: true });
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchArticles(); fetchCategories(); }, []);

  const fetchArticles = async (cat = '', q = '') => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (cat) params.set('category', cat);
      if (q) params.set('search', q);
      const res = await fetch(`${API}/api/knowledge-base/articles?${params}`, { headers: { Authorization: `Bearer ${token}` } });
      setArticles(await res.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const fetchCategories = async () => {
    try {
      const res = await fetch(`${API}/api/knowledge-base/categories`, { headers: { Authorization: `Bearer ${token}` } });
      setCategories(await res.json());
    } catch (e) { console.error(e); }
  };

  const handleSearch = (e) => { e.preventDefault(); fetchArticles(selectedCat, search); };

  const saveArticle = async () => {
    try {
      const url = selectedArticle ? `${API}/api/knowledge-base/articles/${selectedArticle.id}` : `${API}/api/knowledge-base/articles`;
      const method = selectedArticle ? 'PUT' : 'POST';
      await fetch(url, { method, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(form) });
      setShowForm(false); setSelectedArticle(null);
      setForm({ title: '', content: '', category: 'general', tags: [], is_published: true });
      fetchArticles(); fetchCategories();
    } catch (e) { console.error(e); }
  };

  const deleteArticle = async (id) => {
    if (!window.confirm('Delete this article?')) return;
    await fetch(`${API}/api/knowledge-base/articles/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
    fetchArticles(); fetchCategories();
  };

  const viewArticle = async (id) => {
    const res = await fetch(`${API}/api/knowledge-base/articles/${id}`, { headers: { Authorization: `Bearer ${token}` } });
    setSelectedArticle(await res.json());
  };

  if (selectedArticle && !showForm) {
    return (
      <div className="space-y-4" data-testid="kb-article-view">
        <Button variant="outline" onClick={() => setSelectedArticle(null)} data-testid="kb-back-btn">Back to Articles</Button>
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Badge>{selectedArticle.category}</Badge>
              <span className="text-xs text-gray-400"><Eye className="w-3 h-3 inline" /> {selectedArticle.views} views</span>
            </div>
            <CardTitle className="text-xl mt-2">{selectedArticle.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose max-w-none text-sm whitespace-pre-wrap">{selectedArticle.content}</div>
            {selectedArticle.tags?.length > 0 && (
              <div className="flex gap-1 mt-4">{selectedArticle.tags.map((t, i) => <Badge key={i} variant="outline" className="text-xs">{t}</Badge>)}</div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="knowledge-base">
      {/* Search & Filter */}
      <div className="flex gap-3 flex-wrap">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
            <input type="text" placeholder="Search articles..." className="w-full border rounded-md pl-9 pr-3 py-2 text-sm" value={search} onChange={e => setSearch(e.target.value)} data-testid="kb-search" />
          </div>
          <Button type="submit" variant="outline">Search</Button>
        </form>
        {role === 'admin' && (
          <Button onClick={() => { setShowForm(true); setSelectedArticle(null); setForm({ title: '', content: '', category: 'general', tags: [], is_published: true }); }} data-testid="kb-new-btn">
            <Plus className="w-4 h-4 mr-2" /> New Article
          </Button>
        )}
      </div>

      {/* Categories */}
      <div className="flex gap-2 flex-wrap">
        <Badge variant={!selectedCat ? 'default' : 'outline'} className="cursor-pointer" onClick={() => { setSelectedCat(''); fetchArticles('', search); }}>All</Badge>
        {categories.map(c => (
          <Badge key={c.name} variant={selectedCat === c.name ? 'default' : 'outline'} className="cursor-pointer" onClick={() => { setSelectedCat(c.name); fetchArticles(c.name, search); }}>
            {c.name} ({c.count})
          </Badge>
        ))}
      </div>

      {/* Article Form */}
      {showForm && role === 'admin' && (
        <Card>
          <CardHeader><CardTitle className="text-lg">{selectedArticle ? 'Edit' : 'New'} Article</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Article Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} data-testid="kb-title-input" />
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Category" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} data-testid="kb-category-input" />
            <textarea className="w-full border rounded-md p-2 text-sm" rows={8} placeholder="Article content..." value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} data-testid="kb-content-input" />
            <input className="w-full border rounded-md p-2 text-sm" placeholder="Tags (comma separated)" value={form.tags?.join(', ')} onChange={e => setForm({ ...form, tags: e.target.value.split(',').map(t => t.trim()).filter(Boolean) })} />
            <div className="flex gap-2">
              <Button onClick={saveArticle} data-testid="kb-save-btn">Save</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Article List */}
      {loading ? <div className="text-center py-8"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {articles.map(a => (
            <Card key={a.id} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => viewArticle(a.id)}>
              <CardContent className="pt-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className="text-xs">{a.category}</Badge>
                      <span className="text-xs text-gray-400"><Eye className="w-3 h-3 inline" /> {a.views || 0}</span>
                    </div>
                    <h3 className="font-medium text-sm">{a.title}</h3>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{a.content?.substring(0, 120)}...</p>
                  </div>
                  {role === 'admin' && (
                    <div className="flex gap-1 ml-2" onClick={e => e.stopPropagation()}>
                      <Button size="sm" variant="ghost" onClick={() => { setSelectedArticle(a); setForm(a); setShowForm(true); }}><Edit className="w-3 h-3" /></Button>
                      <Button size="sm" variant="ghost" onClick={() => deleteArticle(a.id)}><Trash2 className="w-3 h-3 text-red-500" /></Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {!loading && articles.length === 0 && (
        <Card><CardContent className="py-8 text-center text-gray-500"><BookOpen className="w-12 h-12 mx-auto mb-3 text-gray-300" /><p>No articles found. {role === 'admin' ? 'Create your first article!' : 'Check back soon!'}</p></CardContent></Card>
      )}
    </div>
  );
}
