import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  Users, Mail, Phone, Clock, MessageSquare, CheckCircle2, ExternalLink,
  RefreshCw, Globe, Sparkles, Search, IndianRupee, Loader2, UserPlus,
  CalendarClock, Eye, Send
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STAGE_CONFIG = {
  new: { label: 'New', color: 'bg-blue-100 text-blue-800 border-blue-200' },
  contacted: { label: 'Contacted', color: 'bg-amber-100 text-amber-800 border-amber-200' },
  qualified: { label: 'Qualified', color: 'bg-purple-100 text-purple-800 border-purple-200' },
  payment_pending: { label: 'Payment Pending', color: 'bg-orange-100 text-orange-800 border-orange-200' },
  converted: { label: 'Converted', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  lost: { label: 'Lost', color: 'bg-slate-100 text-slate-600 border-slate-200' },
};

/**
 * EstimateLeadsPanel — shows all leads captured via shared fee-estimate links.
 * - Filter: all / contacted / new
 * - Actions: Call / Email / WhatsApp / Mark Contacted / Add Note
 */
export default function EstimateLeadsPanel({ token, role = 'partner' }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [selected, setSelected] = useState(null);
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadLeads = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/leads/`, {
        headers, params: { source: 'shared_fee_estimate', limit: 200 },
      });
      setLeads(r.data || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load leads');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line
  }, [token]);

  useEffect(() => { loadLeads(); }, [loadLeads]);

  const filtered = leads.filter(l => {
    if (stageFilter !== 'all' && l.stage !== stageFilter) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (l.name || '').toLowerCase().includes(q)
        || (l.email || '').toLowerCase().includes(q)
        || (l.phone || '').toLowerCase().includes(q)
        || (l.country_of_interest || '').toLowerCase().includes(q)
        || (l.service_interested || '').toLowerCase().includes(q);
  });

  const stats = {
    total: leads.length,
    new: leads.filter(l => l.stage === 'new').length,
    contacted: leads.filter(l => l.stage === 'contacted').length,
    converted: leads.filter(l => l.stage === 'converted').length,
  };

  const markContacted = async (lead) => {
    try {
      await axios.put(`${API}/leads/${lead.id}`, { stage: 'contacted' }, { headers });
      toast.success('Marked as contacted');
      loadLeads();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Update failed');
    }
  };

  const updateStage = async (lead, stage) => {
    try {
      await axios.put(`${API}/leads/${lead.id}`, { stage }, { headers });
      toast.success('Stage updated');
      loadLeads();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Update failed');
    }
  };

  const addNote = async () => {
    if (!note.trim() || !selected) return;
    setSaving(true);
    try {
      await axios.post(`${API}/leads/${selected.id}/note`, { text: note.trim() }, { headers });
      toast.success('Note added');
      setNote('');
      setSelected(null);
      loadLeads();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to add note');
    } finally {
      setSaving(false);
    }
  };

  const waLink = (phone, name) => {
    if (!phone) return null;
    const clean = phone.replace(/[^\d+]/g, '');
    const text = encodeURIComponent(`Hi ${name}, thanks for your interest in our immigration services! Following up on the estimate you viewed.`);
    return `https://wa.me/${clean.replace(/^\+/, '')}?text=${text}`;
  };

  return (
    <div className="space-y-4" data-testid="estimate-leads-panel">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <div className="p-2 bg-gradient-to-br from-[#f7620b] to-[#d64f05] rounded-lg text-white">
              <UserPlus className="h-4 w-4" />
            </div>
            Leads from Shared Estimates
          </h2>
          <p className="text-xs text-slate-500 mt-1">Clients who submitted their details from your shared fee-estimate pages</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadLeads} data-testid="leads-refresh">
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard color="slate" label="Total" value={stats.total} icon={Users} />
        <StatCard color="blue" label="New (uncontacted)" value={stats.new} icon={Sparkles} />
        <StatCard color="amber" label="Contacted" value={stats.contacted} icon={CheckCircle2} />
        <StatCard color="emerald" label="Converted" value={stats.converted} icon={IndianRupee} />
      </div>

      {/* Filters */}
      <Card className="p-3 bg-white border-slate-200">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <Input placeholder="Search name, email, country…" value={search}
              onChange={(e) => setSearch(e.target.value)} className="pl-9 h-9" data-testid="leads-search" />
          </div>
          <Select value={stageFilter} onValueChange={setStageFilter}>
            <SelectTrigger className="w-40 h-9" data-testid="leads-stage-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All stages</SelectItem>
              <SelectItem value="new">New only</SelectItem>
              <SelectItem value="contacted">Contacted</SelectItem>
              <SelectItem value="qualified">Qualified</SelectItem>
              <SelectItem value="converted">Converted</SelectItem>
              <SelectItem value="lost">Lost</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* Leads list */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" />
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-12 text-center bg-white border-slate-200 border-dashed">
          <UserPlus className="h-12 w-12 text-slate-200 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-600">No leads yet</h3>
          <p className="text-sm text-slate-400 mt-1">
            When clients submit their details from your shared estimate links, they will appear here.
          </p>
        </Card>
      ) : (
        <div className="space-y-3" data-testid="leads-list">
          {filtered.map(lead => (
            <Card key={lead.id} className="p-4 bg-white border-slate-200 hover:border-[#2a777a]/40 transition-colors" data-testid={`lead-row-${lead.id}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 shrink-0 bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] rounded-full flex items-center justify-center text-white font-bold text-sm">
                    {(lead.name || 'U')[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-slate-800 truncate">{lead.name}</h3>
                      <Badge variant="outline" className={STAGE_CONFIG[lead.stage]?.color || 'bg-slate-100'}>
                        {STAGE_CONFIG[lead.stage]?.label || lead.stage}
                      </Badge>
                      {lead.priority === 'high' && (
                        <Badge className="bg-red-50 text-red-700 border-red-200 text-xs">🔥 Hot</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-500 mt-1 flex-wrap">
                      <a href={`mailto:${lead.email}`} className="inline-flex items-center gap-1 hover:text-[#2a777a]">
                        <Mail className="h-3 w-3" /> {lead.email}
                      </a>
                      {lead.phone && (
                        <a href={`tel:${lead.phone}`} className="inline-flex items-center gap-1 hover:text-[#2a777a]">
                          <Phone className="h-3 w-3" /> {lead.phone}
                        </a>
                      )}
                      {lead.country_of_interest && (
                        <span className="inline-flex items-center gap-1">
                          <Globe className="h-3 w-3" /> {lead.country_of_interest} — {lead.service_interested}
                        </span>
                      )}
                      <span className="inline-flex items-center gap-1">
                        <CalendarClock className="h-3 w-3" />
                        {new Date(lead.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}
                      </span>
                    </div>
                    {lead.message && (
                      <p className="text-sm text-slate-600 mt-2 italic bg-slate-50 rounded px-3 py-2 border-l-2 border-slate-200">
                        "{lead.message}"
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 flex-wrap">
                  {lead.phone && (
                    <a href={waLink(lead.phone, lead.name)} target="_blank" rel="noreferrer">
                      <Button size="sm" variant="outline" className="h-8 text-emerald-700 border-emerald-200 hover:bg-emerald-50" data-testid={`lead-wa-${lead.id}`}>
                        <MessageSquare className="h-3.5 w-3.5 mr-1" /> WhatsApp
                      </Button>
                    </a>
                  )}
                  <a href={`mailto:${lead.email}?subject=${encodeURIComponent('Your ' + (lead.country_of_interest || 'immigration') + ' estimate')}`}>
                    <Button size="sm" variant="outline" className="h-8" data-testid={`lead-email-${lead.id}`}>
                      <Mail className="h-3.5 w-3.5 mr-1" /> Email
                    </Button>
                  </a>
                  {lead.phone && (
                    <a href={`tel:${lead.phone}`}>
                      <Button size="sm" variant="outline" className="h-8" data-testid={`lead-call-${lead.id}`}>
                        <Phone className="h-3.5 w-3.5 mr-1" /> Call
                      </Button>
                    </a>
                  )}
                  <Button size="sm" variant="outline" className="h-8"
                    onClick={() => { setSelected(lead); setNote(''); }} data-testid={`lead-note-${lead.id}`}>
                    <Send className="h-3.5 w-3.5 mr-1" /> Note
                  </Button>
                  {lead.stage === 'new' && (
                    <Button size="sm" className="h-8 bg-[#2a777a] hover:bg-[#236466]"
                      onClick={() => markContacted(lead)} data-testid={`lead-mark-${lead.id}`}>
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Mark Contacted
                    </Button>
                  )}
                  <Select value={lead.stage} onValueChange={(v) => updateStage(lead, v)}>
                    <SelectTrigger className="h-8 w-32 text-xs" data-testid={`lead-stage-${lead.id}`}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="new">New</SelectItem>
                      <SelectItem value="contacted">Contacted</SelectItem>
                      <SelectItem value="qualified">Qualified</SelectItem>
                      <SelectItem value="payment_pending">Payment Pending</SelectItem>
                      <SelectItem value="converted">Converted</SelectItem>
                      <SelectItem value="lost">Lost</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {lead.notes && lead.notes.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-100 space-y-1">
                  <p className="text-xs font-semibold text-slate-600 flex items-center gap-1">
                    <Eye className="h-3 w-3" /> {lead.notes.length} note{lead.notes.length > 1 ? 's' : ''}
                  </p>
                  {lead.notes.slice(-2).map((n, i) => (
                    <p key={i} className="text-xs text-slate-500 pl-4 border-l-2 border-slate-200">
                      {n.text} <span className="text-slate-400 ml-1">— {n.created_by || 'system'}</span>
                    </p>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Add Note Dialog */}
      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-w-md" data-testid="note-dialog">
          <DialogHeader>
            <DialogTitle>Add follow-up note</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-3">
              <p className="text-sm text-slate-600">Contact: <span className="font-semibold">{selected.name}</span> ({selected.email})</p>
              <Textarea value={note} onChange={(e) => setNote(e.target.value)}
                placeholder="e.g., Called at 3pm, discussed Canada PR timeline, will send profile evaluation form" rows={4}
                data-testid="note-text" />
              <div className="flex items-center gap-2 justify-end">
                <Button variant="outline" size="sm" onClick={() => setSelected(null)}>Cancel</Button>
                <Button size="sm" className="bg-[#2a777a] hover:bg-[#236466]" disabled={!note.trim() || saving} onClick={addNote} data-testid="note-save">
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Send className="h-3.5 w-3.5 mr-1.5" />}
                  Save Note
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

const StatCard = ({ color, label, value, icon: Icon }) => {
  const colors = {
    slate: 'bg-slate-50 border-slate-200 text-slate-700',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  };
  return (
    <Card className={`p-3 border ${colors[color] || colors.slate}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider opacity-75">{label}</p>
          <p className="text-2xl font-bold mt-0.5">{value}</p>
        </div>
        <Icon className="h-5 w-5 opacity-60" />
      </div>
    </Card>
  );
};
