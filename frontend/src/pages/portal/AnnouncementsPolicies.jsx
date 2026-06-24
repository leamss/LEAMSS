import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Megaphone, BookOpen, Pin, ArrowLeft, Plus, Check, AlertCircle, Info,
  Users, Building2, Clock, ShieldCheck, Edit3, Trash2,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PRIORITY_BADGE = {
  info: { class: 'bg-sky-100 text-sky-700 border-sky-200', icon: Info, label: 'Info' },
  important: { class: 'bg-leamss-orange-100 text-leamss-orange-700 border-leamss-orange-200', icon: AlertCircle, label: 'Important' },
  urgent: { class: 'bg-leamss-red-100 text-leamss-red-700 border-leamss-red-200', icon: AlertCircle, label: 'Urgent' },
};

const CATEGORIES = ['HR', 'IT', 'Finance', 'Code of Conduct', 'Security', 'Other'];
const CATEGORY_COLOR = {
  HR: 'bg-leamss-teal-100 text-leamss-teal-700',
  IT: 'bg-slate-100 text-slate-700',
  Finance: 'bg-emerald-100 text-emerald-700',
  'Code of Conduct': 'bg-leamss-orange-100 text-leamss-orange-700',
  Security: 'bg-leamss-red-100 text-leamss-red-700',
  Other: 'bg-amber-100 text-amber-700',
};

// ─────────────────── Announcement card ───────────────────
const AnnouncementCard = ({ a, onRead, isManager, onEdit, onDelete }) => {
  const p = PRIORITY_BADGE[a.priority] || PRIORITY_BADGE.info;
  const PIcon = p.icon;
  return (
    <Card
      className={`p-4 transition-all ${a.pinned ? 'border-leamss-orange-300 bg-leamss-orange-50/30' : 'border-slate-200'} ${a.i_read_it ? 'opacity-80' : ''}`}
      data-testid={`announcement-${a.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {a.pinned && <Pin className="h-3.5 w-3.5 text-leamss-orange-500" />}
            <Badge className={`${p.class} border text-[10px]`}><PIcon className="h-3 w-3 mr-0.5" /> {p.label}</Badge>
            <Badge variant="outline" className="text-[10px] capitalize">{a.target_audience.replace('_', ' ')}</Badge>
            {a.i_read_it && <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><Check className="h-3 w-3" /> Read</Badge>}
          </div>
          <h3 className="text-base font-semibold text-slate-900">{a.title}</h3>
          <p className="text-sm text-slate-600 mt-1 whitespace-pre-wrap line-clamp-3">{a.content}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
            <span>By {a.posted_by_name}</span>
            <span>·</span>
            <span>{new Date(a.posted_at).toLocaleString()}</span>
            <span>·</span>
            <span className="inline-flex items-center gap-0.5"><Users className="h-3 w-3" /> {a.read_count} read</span>
          </div>
        </div>
        <div className="flex gap-1">
          {!a.i_read_it && (
            <Button size="sm" variant="outline" onClick={() => onRead(a.id)} data-testid={`mark-read-${a.id}`}>
              <Check className="h-3 w-3 mr-1" /> Read
            </Button>
          )}
          {isManager && (
            <>
              <Button size="icon" variant="ghost" onClick={() => onEdit(a)} data-testid={`edit-announcement-${a.id}`} className="h-7 w-7">
                <Edit3 className="h-3 w-3" />
              </Button>
              <Button size="icon" variant="ghost" onClick={() => onDelete(a.id)} data-testid={`delete-announcement-${a.id}`} className="h-7 w-7">
                <Trash2 className="h-3 w-3 text-leamss-red-500" />
              </Button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
};

// ─────────────────── Policy card ───────────────────
const PolicyCard = ({ p, onAcknowledge, onView, isManager, ackPercent }) => (
  <Card className="p-4" data-testid={`policy-${p.id}`}>
    <div className="flex items-start justify-between gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Badge className={`${CATEGORY_COLOR[p.category] || 'bg-slate-100 text-slate-700'} text-[10px]`}>{p.category}</Badge>
          <Badge variant="outline" className="text-[10px] font-mono">v{p.version}</Badge>
          {p.requires_acknowledgment && <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-[10px]"><ShieldCheck className="h-3 w-3" /> Sign required</Badge>}
          {p.i_acknowledged && <Badge className="bg-emerald-100 text-emerald-700 text-[10px]"><Check className="h-3 w-3" /> Acknowledged</Badge>}
        </div>
        <h3 className="text-base font-semibold text-slate-900">{p.title}</h3>
        <p className="text-sm text-slate-600 mt-1 line-clamp-2 whitespace-pre-wrap">{p.content}</p>
        <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
          <span>{p.created_by_name}</span>
          {p.effective_date && <><span>·</span><span><Clock className="h-3 w-3 inline" /> {new Date(p.effective_date).toLocaleDateString()}</span></>}
          <span>·</span>
          <span><Users className="h-3 w-3 inline" /> {p.acknowledgment_count} acknowledged{ackPercent != null ? ` (${ackPercent}%)` : ''}</span>
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <Button size="sm" variant="outline" onClick={() => onView(p)} data-testid={`view-policy-${p.id}`}>Read</Button>
        {!p.i_acknowledged && p.requires_acknowledgment && (
          <Button size="sm" onClick={() => onAcknowledge(p.id)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid={`acknowledge-${p.id}`}>
            <ShieldCheck className="h-3 w-3 mr-1" /> Acknowledge
          </Button>
        )}
      </div>
    </div>
  </Card>
);

// ─────────────────── Main page ───────────────────
export default function AnnouncementsPolicies({ defaultTab = 'announcements' }) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const initialTab = params.get('tab') || defaultTab;
  const [tab, setTab] = useState(initialTab);
  const [announcements, setAnnouncements] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [activeCat, setActiveCat] = useState('all');
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [annDraft, setAnnDraft] = useState(null);
  const [polDraft, setPolDraft] = useState(null);
  const [polView, setPolView] = useState(null);

  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const load = useCallback(async () => {
    try {
      const [me, ann, pol] = await Promise.all([
        axios.get(`${API}/auth/me`, auth),
        axios.get(`${API}/announcements?for=true`, auth),
        axios.get(`${API}/internal-policies?active_only=true`, auth),
      ]);
      setCurrentUser(me.data);
      setAnnouncements(ann.data);
      setPolicies(pol.data);
    } catch (e) {
      navigate('/');
    } finally {
      setLoading(false);
    }
  }, [navigate, token]);

  useEffect(() => {
    if (!token) { navigate('/'); return; }
    load();
  }, [load, navigate, token]);

  useEffect(() => {
    setParams(p => { p.set('tab', tab); return p; }, { replace: true });
  }, [tab, setParams]);

  const isManager = currentUser && (
    currentUser.permissions?.includes('*') ||
    currentUser.role === 'admin' ||
    ['admin', 'owner', 'head', 'manager', 'lead'].some(k => (currentUser.rbac_role || '').toLowerCase().includes(k))
  );

  const filteredPolicies = activeCat === 'all' ? policies : policies.filter(p => p.category === activeCat);

  // ─── Announcement actions ───
  const handleMarkRead = async (id) => {
    try { await axios.patch(`${API}/announcements/${id}/mark-read`, {}, auth); load(); }
    catch (e) { toast.error('Failed to mark read'); }
  };
  const handleSaveAnnouncement = async () => {
    if (!annDraft?.title?.trim() || !annDraft?.content?.trim()) { toast.error('Title and content required'); return; }
    try {
      if (annDraft.id) {
        await axios.patch(`${API}/announcements/${annDraft.id}`, annDraft, auth);
      } else {
        await axios.post(`${API}/announcements`, annDraft, auth);
      }
      toast.success('Announcement saved');
      setAnnDraft(null);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
  };
  const handleDeleteAnnouncement = async (id) => {
    if (!confirm('Delete this announcement?')) return;
    try { await axios.delete(`${API}/announcements/${id}`, auth); toast.success('Deleted'); load(); }
    catch (e) { toast.error('Delete failed'); }
  };

  // ─── Policy actions ───
  const handleAcknowledge = async (id) => {
    try {
      const { data } = await axios.post(`${API}/internal-policies/${id}/acknowledge`, {}, auth);
      toast.success(`Signed · ${data.signature_hash?.slice(0, 16) || 'ok'}`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Acknowledge failed'); }
  };
  const handleSavePolicy = async () => {
    if (!polDraft?.title?.trim() || !polDraft?.content?.trim()) { toast.error('Title and content required'); return; }
    try {
      if (polDraft.id) {
        await axios.patch(`${API}/internal-policies/${polDraft.id}`, polDraft, auth);
      } else {
        await axios.post(`${API}/internal-policies`, polDraft, auth);
      }
      toast.success('Policy saved');
      setPolDraft(null);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || 'Save failed'); }
  };

  if (loading) return <div className="flex items-center justify-center h-screen text-slate-500">Loading…</div>;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="announcements-policies-page">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/portal-hub')} data-testid="back-hub">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setTab('announcements')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${tab === 'announcements' ? 'bg-white text-leamss-teal-700 shadow-sm' : 'text-slate-500'}`}
                data-testid="tab-announcements"
              >
                <Megaphone className="h-3.5 w-3.5" /> Announcements ({announcements.length})
              </button>
              <button
                onClick={() => setTab('policies')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${tab === 'policies' ? 'bg-white text-leamss-teal-700 shadow-sm' : 'text-slate-500'}`}
                data-testid="tab-policies"
              >
                <BookOpen className="h-3.5 w-3.5" /> Policies ({policies.length})
              </button>
            </div>
          </div>
          {isManager && (
            <Button
              size="sm"
              onClick={() => {
                if (tab === 'announcements') {
                  setAnnDraft({ title: '', content: '', priority: 'info', target_audience: 'all', pinned: false });
                } else {
                  setPolDraft({ title: '', content: '', category: 'HR', requires_acknowledgment: true, version: 1 });
                }
              }}
              className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white"
              data-testid={`new-${tab}-btn`}
            >
              <Plus className="h-4 w-4 mr-1" /> New {tab === 'announcements' ? 'Announcement' : 'Policy'}
            </Button>
          )}
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6">
        {tab === 'announcements' && (
          <div className="space-y-3" data-testid="announcements-feed">
            {announcements.length === 0 && (
              <Card className="p-8 text-center text-slate-500 italic">No announcements yet. Check back later!</Card>
            )}
            {announcements.map(a => (
              <AnnouncementCard
                key={a.id}
                a={a}
                onRead={handleMarkRead}
                isManager={isManager}
                onEdit={(item) => setAnnDraft(item)}
                onDelete={handleDeleteAnnouncement}
              />
            ))}
          </div>
        )}

        {tab === 'policies' && (
          <div data-testid="policies-feed">
            <div className="flex gap-2 overflow-x-auto pb-2 mb-3" data-testid="policy-categories">
              <button
                onClick={() => setActiveCat('all')}
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap border ${activeCat === 'all' ? 'bg-leamss-teal-600 text-white border-leamss-teal-600' : 'bg-white text-slate-600 border-slate-200'}`}
              >
                All ({policies.length})
              </button>
              {CATEGORIES.map(c => {
                const count = policies.filter(p => p.category === c).length;
                if (count === 0) return null;
                return (
                  <button
                    key={c}
                    onClick={() => setActiveCat(c)}
                    className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap border ${activeCat === c ? 'bg-leamss-teal-600 text-white border-leamss-teal-600' : `${CATEGORY_COLOR[c]} border-transparent`}`}
                    data-testid={`category-chip-${c}`}
                  >
                    {c} ({count})
                  </button>
                );
              })}
            </div>
            <div className="space-y-3">
              {filteredPolicies.length === 0 && (
                <Card className="p-8 text-center text-slate-500 italic">No active policies in this category.</Card>
              )}
              {filteredPolicies.map(p => (
                <PolicyCard key={p.id} p={p} onAcknowledge={handleAcknowledge} onView={setPolView} isManager={isManager} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Announcement edit dialog */}
      <Dialog open={!!annDraft} onOpenChange={(o) => !o && setAnnDraft(null)}>
        <DialogContent className="max-w-lg" data-testid="announcement-dialog">
          <DialogHeader><DialogTitle>{annDraft?.id ? 'Edit' : 'New'} Announcement</DialogTitle></DialogHeader>
          {annDraft && (
            <div className="space-y-3">
              <div>
                <Label>Title *</Label>
                <Input value={annDraft.title} onChange={e => setAnnDraft({ ...annDraft, title: e.target.value })} data-testid="ann-title" />
              </div>
              <div>
                <Label>Content *</Label>
                <Textarea rows={5} value={annDraft.content} onChange={e => setAnnDraft({ ...annDraft, content: e.target.value })} data-testid="ann-content" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Priority</Label>
                  <Select value={annDraft.priority} onValueChange={v => setAnnDraft({ ...annDraft, priority: v })}>
                    <SelectTrigger data-testid="ann-priority"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.keys(PRIORITY_BADGE).map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Audience</Label>
                  <Select value={annDraft.target_audience} onValueChange={v => setAnnDraft({ ...annDraft, target_audience: v })}>
                    <SelectTrigger data-testid="ann-audience"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All employees</SelectItem>
                      <SelectItem value="department">By department</SelectItem>
                      <SelectItem value="role">By role</SelectItem>
                      <SelectItem value="specific_users">Specific users</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={!!annDraft.pinned} onChange={e => setAnnDraft({ ...annDraft, pinned: e.target.checked })} data-testid="ann-pinned" />
                <Pin className="h-3.5 w-3.5 text-leamss-orange-500" /> Pin this announcement
              </label>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setAnnDraft(null)}>Cancel</Button>
            <Button onClick={handleSaveAnnouncement} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="ann-save">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Policy edit dialog */}
      <Dialog open={!!polDraft} onOpenChange={(o) => !o && setPolDraft(null)}>
        <DialogContent className="max-w-2xl" data-testid="policy-dialog">
          <DialogHeader><DialogTitle>{polDraft?.id ? 'Edit' : 'New'} Policy</DialogTitle></DialogHeader>
          {polDraft && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Title *</Label>
                  <Input value={polDraft.title} onChange={e => setPolDraft({ ...polDraft, title: e.target.value })} data-testid="pol-title" />
                </div>
                <div>
                  <Label>Category</Label>
                  <Select value={polDraft.category} onValueChange={v => setPolDraft({ ...polDraft, category: v })}>
                    <SelectTrigger data-testid="pol-category"><SelectValue /></SelectTrigger>
                    <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <Label>Content (markdown ok) *</Label>
                <Textarea rows={10} value={polDraft.content} onChange={e => setPolDraft({ ...polDraft, content: e.target.value })} data-testid="pol-content" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Effective date</Label>
                  <Input type="date" value={polDraft.effective_date || ''} onChange={e => setPolDraft({ ...polDraft, effective_date: e.target.value })} data-testid="pol-effective" />
                </div>
                <label className="flex items-center gap-2 text-sm pt-6">
                  <input type="checkbox" checked={!!polDraft.requires_acknowledgment} onChange={e => setPolDraft({ ...polDraft, requires_acknowledgment: e.target.checked })} data-testid="pol-ack-required" />
                  <ShieldCheck className="h-3.5 w-3.5 text-leamss-orange-500" /> Requires acknowledgment
                </label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPolDraft(null)}>Cancel</Button>
            <Button onClick={handleSavePolicy} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="pol-save">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Policy reader */}
      <Dialog open={!!polView} onOpenChange={(o) => !o && setPolView(null)}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto" data-testid="policy-reader">
          {polView && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Badge className={CATEGORY_COLOR[polView.category]}>{polView.category}</Badge>
                  <span>{polView.title}</span>
                  <Badge variant="outline" className="font-mono text-[10px]">v{polView.version}</Badge>
                </DialogTitle>
              </DialogHeader>
              <div className="prose prose-sm max-w-none whitespace-pre-wrap text-slate-700">{polView.content}</div>
              <div className="text-xs text-slate-400 mt-4 pt-3 border-t">
                Created by {polView.created_by_name} · {polView.acknowledgment_count} employees acknowledged
              </div>
              {!polView.i_acknowledged && polView.requires_acknowledgment && (
                <DialogFooter>
                  <Button onClick={() => { handleAcknowledge(polView.id); setPolView(null); }} className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" data-testid="reader-acknowledge">
                    <ShieldCheck className="h-4 w-4 mr-1" /> I Acknowledge
                  </Button>
                </DialogFooter>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
