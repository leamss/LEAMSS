/**
 * Sweep B.1 — Country Workflows Hub (Admin)
 * Path: /admin/country-workflows
 *
 * Authoritative library of verified immigration workflows per country/subclass.
 * Verified entries are served instantly by /api/ai-workflow/generate (no AI call).
 */
import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Plus, Sparkles, CheckCircle, Archive, Edit, Globe, RefreshCw,
  Loader2, ExternalLink, AlertTriangle, Award
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const COUNTRY_OPTIONS = [
  { code: 'AU', name: 'Australia' },
  { code: 'CA', name: 'Canada' },
  { code: 'NZ', name: 'New Zealand' },
  { code: 'UK', name: 'United Kingdom' },
  { code: 'US', name: 'United States' },
  { code: 'DE', name: 'Germany' },
  { code: 'EU', name: 'Schengen Area' },
  { code: 'AE', name: 'United Arab Emirates' },
  { code: 'SG', name: 'Singapore' },
  { code: 'IE', name: 'Ireland' },
];

const SERVICE_TYPES = [
  { id: 'pr', name: 'Permanent Residency' },
  { id: 'work', name: 'Work Visa' },
  { id: 'student', name: 'Student Visa' },
  { id: 'visitor', name: 'Visitor / Tourist' },
  { id: 'partner', name: 'Partner / Family' },
  { id: 'business', name: 'Business / Investor' },
];

const STATUS_COLORS = {
  draft: 'bg-slate-100 text-slate-700 border-slate-200',
  ai_drafted: 'bg-leamss-orange-100 text-leamss-orange-800 border-leamss-orange-200',
  verified: 'bg-leamss-teal-100 text-leamss-teal-800 border-leamss-teal-200',
  archived: 'bg-slate-100 text-slate-500 border-slate-200',
};

export default function CountryWorkflowsHub() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({ by_country: {}, totals: {} });
  const [loading, setLoading] = useState(true);
  const [filterCountry, setFilterCountry] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterService, setFilterService] = useState('');
  // Edit modal
  const [editingWorkflow, setEditingWorkflow] = useState(null);
  // AI Draft dialog
  const [aiDraftDialog, setAiDraftDialog] = useState({ open: false, country_code: 'AU', country_name: 'Australia', subclass_id: '', subclass_name: '', service_type: 'pr' });
  const [aiJobId, setAiJobId] = useState(null);
  const [aiProgress, setAiProgress] = useState(0);
  const [aiStep, setAiStep] = useState('');
  // Verify dialog
  const [verifyDialog, setVerifyDialog] = useState({ open: false, workflow: null, notes: '' });

  const auth = useCallback(() => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }), []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterCountry) params.append('country_code', filterCountry);
      if (filterStatus) params.append('status', filterStatus);
      if (filterService) params.append('service_type', filterService);
      const r = await axios.get(`${API}/country-workflows${params.toString() ? '?' + params : ''}`, auth());
      setItems(r.data.items || []);
      const s = await axios.get(`${API}/country-workflows/stats`, auth());
      setStats(s.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load workflows');
    } finally {
      setLoading(false);
    }
  }, [filterCountry, filterStatus, filterService, auth]);

  useEffect(() => { load(); }, [load]);

  // ── AI Draft ─────────────────────────────────────────────────────────────────
  const kickOffAiDraft = async () => {
    const r = aiDraftDialog;
    if (!r.country_code || !r.subclass_id || !r.service_type) { toast.error('Country, subclass, and service type required'); return; }
    try {
      const res = await axios.post(`${API}/country-workflows/ai-draft`, r, auth());
      const jid = res.data.job_id;
      setAiJobId(jid); setAiProgress(0); setAiStep('queued');
      toast.message('AI draft started', { description: 'Polling for progress every 2.5s — typical 60-90s.' });
      const poll = async () => {
        try {
          const s = await axios.get(`${API}/country-workflows/ai-draft/status/${jid}`, auth());
          const j = s.data;
          setAiProgress(j.progress || 0);
          setAiStep(j.current_step || '');
          if (j.status === 'complete') {
            toast.success('AI draft complete — opening editor');
            setAiDraftDialog({ ...aiDraftDialog, open: false });
            setAiJobId(null);
            // Open editor for the new workflow
            const w = await axios.get(`${API}/country-workflows/${j.workflow_id}`, auth());
            setEditingWorkflow(w.data);
            load();
            return;
          }
          if (j.status === 'failed') {
            toast.error(j.error || 'AI draft failed');
            setAiJobId(null);
            return;
          }
          setTimeout(poll, 2500);
        } catch (e) { setTimeout(poll, 4000); }
      };
      setTimeout(poll, 1500);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to kick off AI draft');
    }
  };

  // ── Manual create ────────────────────────────────────────────────────────────
  const createBlank = () => {
    setEditingWorkflow({
      workflow_id: null,
      country_code: 'AU', country_name: 'Australia',
      subclass_id: '', subclass_name: '', service_type: 'pr',
      category: 'immigration', description: '',
      eligibility_summary: '', eligibility_criteria: [],
      fees_local_currency_code: '', fees_local_currency_amount: 0, fees_inr_approx: 0,
      fees_breakdown: [], processing_time_days_min: 0, processing_time_days_max: 0,
      step_by_step: [], document_checklist: [],
      common_rejection_reasons: [], success_tips: [], faqs: [],
      official_url: '', vfs_url: '', source_urls: [],
      status: 'draft', version: 0,
    });
  };

  const saveWorkflow = async () => {
    if (!editingWorkflow) return;
    if (!editingWorkflow.country_code || !editingWorkflow.subclass_id || !editingWorkflow.service_type) {
      toast.error('Country, subclass, and service type required');
      return;
    }
    try {
      if (editingWorkflow.workflow_id) {
        // Update
        const { workflow_id, status, version, created_at, created_by, created_by_name, updated_at, updated_by, updated_by_name, verified_at, verified_by, verified_by_name, verified_notes, ...payload } = editingWorkflow;
        await axios.patch(`${API}/country-workflows/${workflow_id}`, payload, auth());
        toast.success('Workflow updated');
      } else {
        await axios.post(`${API}/country-workflows`, editingWorkflow, auth());
        toast.success('Workflow created');
      }
      setEditingWorkflow(null);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    }
  };

  const archiveWorkflow = async (id) => {
    if (!window.confirm('Archive this workflow?')) return;
    try {
      await axios.post(`${API}/country-workflows/${id}/archive`, {}, auth());
      toast.success('Archived');
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Archive failed'); }
  };

  const doVerify = async () => {
    if (!verifyDialog.workflow) return;
    try {
      await axios.post(`${API}/country-workflows/${verifyDialog.workflow.workflow_id}/verify`,
        { notes: verifyDialog.notes }, auth());
      toast.success('Marked as verified — /ai-workflow/generate will now serve this instantly');
      setVerifyDialog({ open: false, workflow: null, notes: '' });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Verify failed'); }
  };

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto" data-testid="country-workflows-hub">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-3" style={{fontFamily:'Manrope,sans-serif'}}>
            <Globe className="h-7 w-7 text-leamss-teal-600" />
            Country Workflows
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Authoritative library of verified immigration workflows. Verified entries are served instantly by AI Workflow Builder (no AI call needed).
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} data-testid="refresh-btn">
            <RefreshCw className="h-4 w-4 mr-1.5" /> Refresh
          </Button>
          <Button onClick={createBlank} variant="outline"
            className="border-leamss-teal-300 text-leamss-teal-700 hover:bg-leamss-teal-50"
            data-testid="new-blank-btn">
            <Plus className="h-4 w-4 mr-1.5" /> New (blank)
          </Button>
          <Button onClick={() => setAiDraftDialog({ ...aiDraftDialog, open: true })}
            className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white"
            data-testid="new-ai-draft-btn">
            <Sparkles className="h-4 w-4 mr-1.5" /> Generate AI Draft
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: 'Total', value: stats.totals?.total || 0, color: 'from-slate-500 to-slate-600' },
          { label: 'Verified', value: stats.totals?.verified || 0, color: 'from-leamss-teal-500 to-leamss-teal-600' },
          { label: 'AI Drafted', value: stats.totals?.ai_drafted || 0, color: 'from-leamss-orange-500 to-leamss-orange-600' },
          { label: 'Draft', value: stats.totals?.draft || 0, color: 'from-slate-400 to-slate-500' },
          { label: 'Archived', value: stats.totals?.archived || 0, color: 'from-slate-300 to-slate-400' },
        ].map((s, i) => (
          <Card key={i} className={`bg-gradient-to-br ${s.color} text-white p-4 border-0 shadow-lg`}>
            <p className="text-2xl font-bold">{s.value}</p>
            <p className="text-xs text-white/80">{s.label}</p>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center bg-white rounded-lg border border-slate-200 p-3">
        <span className="text-sm font-medium text-slate-600">Filters:</span>
        <Select value={filterCountry || 'all'} onValueChange={(v) => setFilterCountry(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-40" data-testid="filter-country"><SelectValue placeholder="Country" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All countries</SelectItem>
            {COUNTRY_OPTIONS.map(c => <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filterStatus || 'all'} onValueChange={(v) => setFilterStatus(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-40" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="ai_drafted">AI Drafted</SelectItem>
            <SelectItem value="verified">Verified</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterService || 'all'} onValueChange={(v) => setFilterService(v === 'all' ? '' : v)}>
          <SelectTrigger className="w-44" data-testid="filter-service"><SelectValue placeholder="Service type" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All services</SelectItem>
            {SERVICE_TYPES.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <span className="text-xs text-slate-400 ml-auto">{items.length} item{items.length === 1 ? '' : 's'}</span>
      </div>

      {/* List */}
      {loading ? (
        <div className="p-12 text-center"><Loader2 className="h-8 w-8 mx-auto animate-spin text-leamss-teal-600" /></div>
      ) : items.length === 0 ? (
        <Card className="p-12 text-center" data-testid="empty-state">
          <Globe className="h-12 w-12 mx-auto text-slate-300 mb-3" />
          <p className="text-slate-600 font-medium">No workflows yet</p>
          <p className="text-sm text-slate-500 mt-1">Click <span className="font-medium">Generate AI Draft</span> to create your first one — typical 60-90s using Claude Sonnet 4.5</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map(it => (
            <Card key={it.workflow_id} className="p-4 hover:shadow-md transition-shadow" data-testid={`workflow-row-${it.workflow_id}`}>
              <div className="flex items-start gap-4 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className="bg-leamss-teal-100 text-leamss-teal-800 border border-leamss-teal-200 font-mono text-xs">
                      {it.country_code}
                    </Badge>
                    <span className="font-bold text-slate-800">{it.subclass_id}</span>
                    <span className="text-slate-600">— {it.subclass_name || it.country_name}</span>
                    <Badge className={STATUS_COLORS[it.status] || STATUS_COLORS.draft}>
                      {it.status === 'verified' && <Award className="h-3 w-3 mr-1" />}
                      {it.status?.replace('_', ' ').toUpperCase()}
                    </Badge>
                    <Badge variant="outline" className="text-xs">v{it.version}</Badge>
                  </div>
                  <p className="text-sm text-slate-500 mt-1">{it.service_type} · {it.country_name}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Updated {it.updated_at ? new Date(it.updated_at).toLocaleString() : ''}
                    {it.verified_at && <> · <span className="text-emerald-700">Verified {new Date(it.verified_at).toLocaleDateString()}</span> by {it.verified_by_name}</>}
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  {it.official_url && (
                    <Button variant="ghost" size="sm" onClick={() => window.open(it.official_url, '_blank')} title="Open official URL">
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  )}
                  <Button variant="outline" size="sm" onClick={() => setEditingWorkflow(it)}
                    data-testid={`edit-btn-${it.workflow_id}`}>
                    <Edit className="h-4 w-4 mr-1" /> Edit
                  </Button>
                  {it.status !== 'verified' && it.status !== 'archived' && (
                    <Button size="sm"
                      className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      onClick={() => setVerifyDialog({ open: true, workflow: it, notes: '' })}
                      data-testid={`verify-btn-${it.workflow_id}`}>
                      <CheckCircle className="h-4 w-4 mr-1" /> Mark Verified
                    </Button>
                  )}
                  {it.status !== 'archived' && (
                    <Button variant="ghost" size="sm" onClick={() => archiveWorkflow(it.workflow_id)}
                      className="text-slate-500 hover:text-leamss-red-700"
                      data-testid={`archive-btn-${it.workflow_id}`}>
                      <Archive className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* ── Edit Dialog ───────────────────────────────────────────────────── */}
      <Dialog open={!!editingWorkflow} onOpenChange={(o) => { if (!o) setEditingWorkflow(null); }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="edit-workflow-dialog">
          <DialogHeader>
            <DialogTitle>
              {editingWorkflow?.workflow_id ? `Edit Workflow v${editingWorkflow.version}` : 'New Workflow'}
            </DialogTitle>
            <DialogDescription>
              {editingWorkflow?.status === 'verified'
                ? 'Editing a verified workflow will demote status to ai_drafted; re-verify after changes.'
                : 'Fill in fields, then Save. Click Mark Verified when source-checked.'}
            </DialogDescription>
          </DialogHeader>
          {editingWorkflow && (
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
                <TabsTrigger value="fees">Fees & Time</TabsTrigger>
                <TabsTrigger value="content">Content</TabsTrigger>
                <TabsTrigger value="source">Source URLs</TabsTrigger>
              </TabsList>
              <TabsContent value="overview" className="space-y-3 mt-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-sm font-medium">Country Code</label>
                    <Input value={editingWorkflow.country_code} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, country_code: e.target.value.toUpperCase() })} maxLength={2} /></div>
                  <div><label className="text-sm font-medium">Country Name</label>
                    <Input value={editingWorkflow.country_name} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, country_name: e.target.value })} /></div>
                  <div><label className="text-sm font-medium">Subclass ID</label>
                    <Input value={editingWorkflow.subclass_id} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, subclass_id: e.target.value })} placeholder="e.g. 189" /></div>
                  <div><label className="text-sm font-medium">Subclass Name</label>
                    <Input value={editingWorkflow.subclass_name} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, subclass_name: e.target.value })} placeholder="e.g. Skilled Independent" /></div>
                  <div><label className="text-sm font-medium">Service Type</label>
                    <Select value={editingWorkflow.service_type} onValueChange={(v) => setEditingWorkflow({ ...editingWorkflow, service_type: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>{SERVICE_TYPES.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
                    </Select></div>
                  <div><label className="text-sm font-medium">Category</label>
                    <Input value={editingWorkflow.category || ''} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, category: e.target.value })} /></div>
                </div>
                <div><label className="text-sm font-medium">Description</label>
                  <Textarea rows={3} value={editingWorkflow.description} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, description: e.target.value })} /></div>
                <div><label className="text-sm font-medium">Eligibility Summary</label>
                  <Textarea rows={2} value={editingWorkflow.eligibility_summary} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, eligibility_summary: e.target.value })} /></div>
              </TabsContent>
              <TabsContent value="fees" className="space-y-3 mt-3">
                <div className="grid grid-cols-3 gap-3">
                  <div><label className="text-sm font-medium">Currency Code</label>
                    <Input value={editingWorkflow.fees_local_currency_code} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, fees_local_currency_code: e.target.value.toUpperCase() })} placeholder="AUD" /></div>
                  <div><label className="text-sm font-medium">Amount (local)</label>
                    <Input type="number" value={editingWorkflow.fees_local_currency_amount || 0} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, fees_local_currency_amount: parseFloat(e.target.value || 0) })} /></div>
                  <div><label className="text-sm font-medium">~ INR</label>
                    <Input type="number" value={editingWorkflow.fees_inr_approx || 0} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, fees_inr_approx: parseFloat(e.target.value || 0) })} /></div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-sm font-medium">Processing days (min)</label>
                    <Input type="number" value={editingWorkflow.processing_time_days_min || 0} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, processing_time_days_min: parseInt(e.target.value || 0) })} /></div>
                  <div><label className="text-sm font-medium">Processing days (max)</label>
                    <Input type="number" value={editingWorkflow.processing_time_days_max || 0} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, processing_time_days_max: parseInt(e.target.value || 0) })} /></div>
                </div>
                <p className="text-xs text-slate-500 italic">Fee breakdown items and detailed step-by-step JSON can be edited via API for now (full UI editor in next sub-slice).</p>
              </TabsContent>
              <TabsContent value="content" className="space-y-3 mt-3">
                <p className="text-xs text-slate-500">Editing structured arrays (steps, documents, FAQs) via JSON:</p>
                <div><label className="text-sm font-medium">Step-by-step (JSON)</label>
                  <Textarea rows={6} className="font-mono text-xs"
                    value={JSON.stringify(editingWorkflow.step_by_step || [], null, 2)}
                    onChange={(e) => { try { setEditingWorkflow({ ...editingWorkflow, step_by_step: JSON.parse(e.target.value) }); } catch {} }} /></div>
                <div><label className="text-sm font-medium">Document Checklist (JSON)</label>
                  <Textarea rows={5} className="font-mono text-xs"
                    value={JSON.stringify(editingWorkflow.document_checklist || [], null, 2)}
                    onChange={(e) => { try { setEditingWorkflow({ ...editingWorkflow, document_checklist: JSON.parse(e.target.value) }); } catch {} }} /></div>
                <div><label className="text-sm font-medium">Success Tips (one per line)</label>
                  <Textarea rows={3}
                    value={(editingWorkflow.success_tips || []).join('\n')}
                    onChange={(e) => setEditingWorkflow({ ...editingWorkflow, success_tips: e.target.value.split('\n').filter(Boolean) })} /></div>
                <div><label className="text-sm font-medium">Common Rejection Reasons (one per line)</label>
                  <Textarea rows={3}
                    value={(editingWorkflow.common_rejection_reasons || []).join('\n')}
                    onChange={(e) => setEditingWorkflow({ ...editingWorkflow, common_rejection_reasons: e.target.value.split('\n').filter(Boolean) })} /></div>
              </TabsContent>
              <TabsContent value="source" className="space-y-3 mt-3">
                <div><label className="text-sm font-medium">Official Government URL</label>
                  <Input value={editingWorkflow.official_url} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, official_url: e.target.value })} placeholder="https://immi.homeaffairs.gov.au/..." /></div>
                <div><label className="text-sm font-medium">VFS / Application Centre URL</label>
                  <Input value={editingWorkflow.vfs_url} onChange={(e) => setEditingWorkflow({ ...editingWorkflow, vfs_url: e.target.value })} placeholder="https://visa.vfsglobal.com/..." /></div>
                <div><label className="text-sm font-medium">Additional Source URLs (one per line)</label>
                  <Textarea rows={3}
                    value={(editingWorkflow.source_urls || []).join('\n')}
                    onChange={(e) => setEditingWorkflow({ ...editingWorkflow, source_urls: e.target.value.split('\n').filter(Boolean) })} /></div>
                {editingWorkflow.verified_at && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-sm">
                    <p className="font-medium text-emerald-800">
                      <Award className="h-4 w-4 inline mr-1.5" />
                      Verified by {editingWorkflow.verified_by_name} on {new Date(editingWorkflow.verified_at).toLocaleString()}
                    </p>
                    {editingWorkflow.verified_notes && <p className="text-emerald-700 text-xs mt-1">"{editingWorkflow.verified_notes}"</p>}
                  </div>
                )}
              </TabsContent>
            </Tabs>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingWorkflow(null)} data-testid="edit-cancel">Cancel</Button>
            <Button className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" onClick={saveWorkflow} data-testid="edit-save">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── AI Draft Dialog ───────────────────────────────────────────────── */}
      <Dialog open={aiDraftDialog.open} onOpenChange={(o) => { if (!o && !aiJobId) setAiDraftDialog({ ...aiDraftDialog, open: false }); }}>
        <DialogContent data-testid="ai-draft-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-leamss-teal-600" /> Generate AI Draft</DialogTitle>
            <DialogDescription>
              Claude Sonnet 4.5 will generate a complete workflow draft. You can edit + mark Verified after review (~60-90s).
            </DialogDescription>
          </DialogHeader>
          {!aiJobId ? (
            <div className="space-y-3">
              <div><label className="text-sm font-medium">Country</label>
                <Select value={aiDraftDialog.country_code} onValueChange={(v) => {
                  const c = COUNTRY_OPTIONS.find(x => x.code === v);
                  setAiDraftDialog({ ...aiDraftDialog, country_code: v, country_name: c?.name || v });
                }}>
                  <SelectTrigger data-testid="ai-draft-country"><SelectValue /></SelectTrigger>
                  <SelectContent>{COUNTRY_OPTIONS.map(c => <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>)}</SelectContent>
                </Select></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-sm font-medium">Subclass ID</label>
                  <Input value={aiDraftDialog.subclass_id} onChange={(e) => setAiDraftDialog({ ...aiDraftDialog, subclass_id: e.target.value })} placeholder="189" data-testid="ai-draft-subclass-id" /></div>
                <div><label className="text-sm font-medium">Subclass Name</label>
                  <Input value={aiDraftDialog.subclass_name} onChange={(e) => setAiDraftDialog({ ...aiDraftDialog, subclass_name: e.target.value })} placeholder="Skilled Independent" data-testid="ai-draft-subclass-name" /></div>
              </div>
              <div><label className="text-sm font-medium">Service Type</label>
                <Select value={aiDraftDialog.service_type} onValueChange={(v) => setAiDraftDialog({ ...aiDraftDialog, service_type: v })}>
                  <SelectTrigger data-testid="ai-draft-service"><SelectValue /></SelectTrigger>
                  <SelectContent>{SERVICE_TYPES.map(s => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
                </Select></div>
            </div>
          ) : (
            <div className="py-6 text-center">
              <Loader2 className="h-10 w-10 mx-auto text-leamss-teal-600 animate-spin" />
              <p className="font-medium mt-3">Generating with Claude Sonnet 4.5…</p>
              <p className="text-xs text-slate-500 mt-1">Step: {aiStep || 'queued'}</p>
              <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden mt-3" data-testid="ai-draft-progress-bar">
                <div className="h-full bg-gradient-to-r from-leamss-teal-500 to-leamss-orange-500 transition-all duration-700" style={{width: `${aiProgress}%`}} />
              </div>
              <p className="text-xs text-slate-400 font-mono mt-2">{aiProgress}% · job {aiJobId?.slice(0, 8)}…</p>
            </div>
          )}
          <DialogFooter>
            {!aiJobId && <Button variant="outline" onClick={() => setAiDraftDialog({ ...aiDraftDialog, open: false })}>Cancel</Button>}
            {!aiJobId && (
              <Button className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white" onClick={kickOffAiDraft} data-testid="ai-draft-submit">
                <Sparkles className="h-4 w-4 mr-1.5" /> Generate Draft
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Verify Dialog ─────────────────────────────────────────────────── */}
      <Dialog open={verifyDialog.open} onOpenChange={(o) => { if (!o) setVerifyDialog({ open: false, workflow: null, notes: '' }); }}>
        <DialogContent data-testid="verify-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-emerald-700">
              <CheckCircle className="h-5 w-5" /> Mark as Verified
            </DialogTitle>
            <DialogDescription>
              {verifyDialog.workflow ? (
                <>This will mark <span className="font-semibold">{verifyDialog.workflow.country_code} {verifyDialog.workflow.subclass_id}</span> as the authoritative source. /api/ai-workflow/generate will serve it instantly.</>
              ) : null}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-sm font-medium">Verification notes (recommended)</label>
            <Textarea rows={3} placeholder="e.g. Source-verified against immi.homeaffairs.gov.au on Feb 26, 2026. Fees current as of FY2025-26."
              value={verifyDialog.notes} onChange={(e) => setVerifyDialog({ ...verifyDialog, notes: e.target.value })}
              data-testid="verify-notes" />
            <div className="bg-leamss-orange-50 border border-leamss-orange-200 rounded-lg p-3 text-xs text-leamss-orange-800">
              <AlertTriangle className="h-3.5 w-3.5 inline mr-1" />
              Once verified, this becomes the source-of-truth for the country+subclass+service combo. Future edits will reset status back to ai_drafted.
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVerifyDialog({ open: false, workflow: null, notes: '' })}>Cancel</Button>
            <Button className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={doVerify} data-testid="verify-confirm">
              <CheckCircle className="h-4 w-4 mr-1.5" /> Confirm Verify
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
