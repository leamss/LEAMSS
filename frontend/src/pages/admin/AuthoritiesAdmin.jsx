/**
 * Phase 19.9 — Authority Admin UI.
 *
 * 3-panel layout: top stats · body list (left) · detail editor (right)
 * Plus modals: Verify Wizard, LAA Split, Diff Audit (mandatory before commit).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import {
  ArrowLeft, CheckCircle, Edit3, Lock, RefreshCw, Search, Shield, Split, X, Eye, AlertTriangle,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('token')}` };
}

const STATUS_COLORS = {
  active: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  draft: 'bg-amber-100 text-amber-800 border-amber-300',
  deprecated: 'bg-slate-100 text-slate-600 border-slate-300',
};

export default function AuthoritiesAdmin() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || 'all');
  const [selected, setSelected] = useState(null);
  const [edit, setEdit] = useState({});
  const [busy, setBusy] = useState(false);
  // Modals
  const [diff, setDiff] = useState(null);
  const [wizardOpen, setWizardOpen] = useState(searchParams.get('wizard') === 'true');
  const [wizardIdx, setWizardIdx] = useState(0);
  const [laaSplitOpen, setLaaSplitOpen] = useState(false);
  const [laaBodies, setLaaBodies] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/assessing-authorities?country=AU&include_drafts=true`, { headers: authHeaders() });
      setItems(r.data.items || []);
    } catch (e) { toast.error('Failed to load authorities'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => items.filter(b => {
    if (statusFilter !== 'all' && b.status !== statusFilter) return false;
    if (statusFilter === 'placeholder' && b._seed_quality !== 'placeholder') return false;
    if (search && !((b.code || '').toLowerCase().includes(search.toLowerCase()) ||
                     (b.full_name || '').toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  }), [items, statusFilter, search]);

  const stats = useMemo(() => ({
    total: items.length,
    active: items.filter(b => b.status === 'active').length,
    draft: items.filter(b => b.status === 'draft').length,
    deprecated: items.filter(b => b.status === 'deprecated').length,
    placeholder: items.filter(b => b._seed_quality === 'placeholder').length,
    total_linked: items.reduce((sum, b) => sum + (b.occupation_count || 0), 0),
  }), [items]);

  // Click body → load detail + start editing
  const selectBody = (b) => {
    setSelected(b);
    setEdit({
      full_name: b.full_name || '',
      website: b.website || '',
      msa_fee_aud: b.fees?.msa_fee_aud || 0,
      standard_days_min: b.processing?.standard_days_min || 0,
      standard_days_max: b.processing?.standard_days_max || 0,
      methodology_summary: b.methodology_summary || '',
    });
  };

  const computeChanges = () => {
    if (!selected) return null;
    const changes = {};
    if (edit.full_name !== (selected.full_name || '')) changes.full_name = edit.full_name;
    if (edit.website !== (selected.website || '')) changes.website = edit.website;
    const feesPatch = {};
    if (+edit.msa_fee_aud !== (selected.fees?.msa_fee_aud || 0)) feesPatch.msa_fee_aud = +edit.msa_fee_aud;
    if (Object.keys(feesPatch).length) changes.fees = feesPatch;
    const procPatch = {};
    if (+edit.standard_days_min !== (selected.processing?.standard_days_min || 0)) procPatch.standard_days_min = +edit.standard_days_min;
    if (+edit.standard_days_max !== (selected.processing?.standard_days_max || 0)) procPatch.standard_days_max = +edit.standard_days_max;
    if (Object.keys(procPatch).length) changes.processing = procPatch;
    if (edit.methodology_summary !== (selected.methodology_summary || '')) changes.methodology_summary = edit.methodology_summary;
    return changes;
  };

  // Click "Save" → MANDATORY diff preview first
  const onSave = async () => {
    const changes = computeChanges();
    if (!changes || Object.keys(changes).length === 0) { toast.info('No changes to save'); return; }
    setBusy(true);
    try {
      const r = await axios.post(
        `${API}/assessing-authorities/${selected.code}/diff-preview`,
        { proposed_changes: changes },
        { headers: authHeaders() },
      );
      setDiff({ changes, preview: r.data });
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Diff preview failed');
    } finally { setBusy(false); }
  };

  // Confirm in Diff modal → run actual PATCH
  const commitDiff = async () => {
    if (!diff || !selected) return;
    setBusy(true);
    try {
      await axios.patch(`${API}/assessing-authorities/${selected.code}`, diff.changes, { headers: authHeaders() });
      toast.success(`Patched ${selected.code} · ${diff.preview.affected_occupation_count} occupations will reflect`);
      setDiff(null);
      await load();
      const updated = items.find(i => i.code === selected.code);
      if (updated) setSelected(updated);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Patch failed');
    } finally { setBusy(false); }
  };

  const onVerify = async (code) => {
    setBusy(true);
    try {
      await axios.post(`${API}/assessing-authorities/${code}/verify`, {}, { headers: authHeaders() });
      toast.success(`${code} → active`);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Verify failed');
    } finally { setBusy(false); }
  };

  const openLaaSplit = async () => {
    // Pre-populate 6 state bodies (admin can override fees)
    setLaaBodies([
      { code: 'LAA-NSW', full_name: 'NSW Legal Profession Admission Board', website: 'https://www.lpab.justice.nsw.gov.au/', msa_fee_aud: 580 },
      { code: 'LAA-VIC', full_name: 'Victorian Legal Admissions Board', website: 'https://www.lawadmissions.vic.gov.au/', msa_fee_aud: 540 },
      { code: 'LAA-QLD', full_name: 'Queensland Legal Practitioners Admissions Board', website: 'https://www.lpab.qld.gov.au/', msa_fee_aud: 500 },
      { code: 'LAA-SA',  full_name: 'Legal Practitioners Education and Admission Council of SA', website: 'https://www.courts.sa.gov.au/lpeac/', msa_fee_aud: 480 },
      { code: 'LAA-WA',  full_name: 'Legal Practice Board of Western Australia', website: 'https://www.lpbwa.org.au/', msa_fee_aud: 460 },
      { code: 'LAA-TAS', full_name: 'Tasmanian Legal Practice Board', website: 'https://www.lpbtas.org.au/', msa_fee_aud: 440 },
    ]);
    setLaaSplitOpen(true);
  };

  const confirmLaaSplit = async () => {
    setBusy(true);
    try {
      const r = await axios.post(`${API}/assessing-authorities/LAA/split-laa`,
        { state_bodies: laaBodies, reassign_strategy: 'manual' },
        { headers: authHeaders() });
      toast.success(`LAA split — created ${r.data.created_codes?.length || 0} state bodies, LAA deprecated`);
      setLaaSplitOpen(false);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Split failed');
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="authorities-admin-page">
      <div className="max-w-7xl mx-auto">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-4">
          <button onClick={() => navigate('/admin/verify-hub')} className="flex items-center gap-2 text-slate-600 hover:text-slate-900 text-sm">
            <ArrowLeft className="h-4 w-4" />Back to Verification Hub
          </button>
          <h1 className="text-xl font-bold text-slate-900">Phase 19.9 · Authority Admin</h1>
          <Button onClick={load} variant="ghost" size="sm" disabled={loading} data-testid="auth-admin-refresh">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Top stats */}
        <div className="grid grid-cols-6 gap-3 mb-4">
          <StatBox label="Total Bodies" value={stats.total} testid="stat-total" />
          <StatBox label="Active" value={stats.active} color="emerald" testid="stat-active" />
          <StatBox label="Draft" value={stats.draft} color="amber" testid="stat-draft" />
          <StatBox label="Deprecated" value={stats.deprecated} color="slate" testid="stat-deprecated" />
          <StatBox label="Placeholder" value={stats.placeholder} color="rose" testid="stat-placeholder" />
          <StatBox label="Linked Occupations" value={stats.total_linked} color="indigo" testid="stat-linked" />
        </div>

        {/* Action bar */}
        <div className="flex items-center gap-2 mb-3">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <Input placeholder="Search by code or full name…" value={search} onChange={e => setSearch(e.target.value)} className="pl-7 h-9 text-sm" data-testid="auth-search" />
          </div>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="border border-slate-300 rounded-md text-sm h-9 px-2" data-testid="auth-status-filter">
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="deprecated">Deprecated</option>
            <option value="placeholder">Placeholder only</option>
          </select>
          <Button size="sm" onClick={() => setWizardOpen(true)} data-testid="open-verify-wizard">
            <Shield className="h-3.5 w-3.5 mr-1" />Verify Wizard
          </Button>
          <Button size="sm" variant="outline" onClick={openLaaSplit} data-testid="auth-split-laa-btn">
            <Split className="h-3.5 w-3.5 mr-1" />Split LAA Umbrella
          </Button>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* Body list */}
          <Card className="col-span-7 p-3 max-h-[70vh] overflow-y-auto" data-testid="auth-body-list">
            <table className="w-full text-xs">
              <thead className="text-slate-500 sticky top-0 bg-white">
                <tr><th className="text-left p-2">Code</th><th className="text-left p-2">Full name</th><th className="text-left p-2">Status</th><th className="text-right p-2">Occ</th></tr>
              </thead>
              <tbody>
                {filtered.map(b => (
                  <tr key={b.code} className={`border-b hover:bg-slate-50 cursor-pointer ${selected?.code === b.code ? 'bg-leamss-teal_50' : ''}`}
                      onClick={() => selectBody(b)} data-testid={`auth-row-${b.code}`}>
                    <td className="p-2 font-mono font-bold">{b.code}</td>
                    <td className="p-2">{b.full_name?.substring(0, 50)}{b._seed_quality === 'placeholder' && <Badge className="ml-1 text-[9px] bg-rose-100 text-rose-700">PLACEHOLDER</Badge>}</td>
                    <td className="p-2"><Badge className={`text-[9px] border ${STATUS_COLORS[b.status] || ''}`}>{b.status}</Badge></td>
                    <td className="p-2 text-right">{b.occupation_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* Detail editor */}
          <Card className="col-span-5 p-4 max-h-[70vh] overflow-y-auto" data-testid="auth-detail-editor">
            {!selected ? (
              <p className="text-slate-500 text-sm italic">Select a body from the list to edit</p>
            ) : (
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-slate-900">{selected.code}</h3>
                    <p className="text-xs text-slate-500">{selected.occupation_count || 0} linked occupations</p>
                  </div>
                  {selected.status === 'draft' && (
                    <Button size="sm" onClick={() => onVerify(selected.code)} className="bg-emerald-600 hover:bg-emerald-700" disabled={busy} data-testid={`auth-verify-${selected.code}`}>
                      <CheckCircle className="h-3 w-3 mr-1" />Verify Now
                    </Button>
                  )}
                </div>
                <Field label="Full name" value={edit.full_name} onChange={v => setEdit({...edit, full_name: v})} testid="edit-full-name" />
                <Field label="Website" value={edit.website} onChange={v => setEdit({...edit, website: v})} testid="edit-website" />
                <Field label="MSA Fee (AUD)" type="number" value={edit.msa_fee_aud} onChange={v => setEdit({...edit, msa_fee_aud: v})} testid="edit-msa-fee" />
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Processing min days" type="number" value={edit.standard_days_min} onChange={v => setEdit({...edit, standard_days_min: v})} testid="edit-proc-min" />
                  <Field label="Processing max days" type="number" value={edit.standard_days_max} onChange={v => setEdit({...edit, standard_days_max: v})} testid="edit-proc-max" />
                </div>
                <div>
                  <label className="text-[10px] font-semibold text-slate-700 uppercase">Methodology Summary</label>
                  <textarea className="w-full border border-slate-300 rounded p-1.5 text-xs h-20" value={edit.methodology_summary} onChange={e => setEdit({...edit, methodology_summary: e.target.value})} data-testid="edit-methodology" />
                </div>
                <Button size="sm" onClick={onSave} disabled={busy} className="w-full" data-testid="auth-save-btn">
                  <Eye className="h-3 w-3 mr-1" />Preview Diff Audit & Save
                </Button>
                <p className="text-[10px] text-slate-400 italic">Changes will preview before committing. Mandatory diff audit shows downstream impact on Atlas + Sales pages.</p>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Diff Audit Modal */}
      {diff && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" data-testid="diff-modal-open">
          <Card className="w-full max-w-3xl p-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />Diff Audit · Phase 19.9
              </h3>
              <Button variant="ghost" size="sm" onClick={() => setDiff(null)}><X className="h-4 w-4" /></Button>
            </div>

            <div className="bg-amber-50 border border-amber-300 rounded p-3 mb-3 text-xs">
              <p><strong>This change affects {diff.preview.affected_occupation_count} occupation pages</strong> ({diff.preview.atlas_pages_affected_count} atlas + {diff.preview.sales_flow_pages_affected} sales-flow). Estimated SEO impact: <Badge className={`ml-1 ${diff.preview.estimated_seo_impact === 'high' ? 'bg-rose-600' : diff.preview.estimated_seo_impact === 'medium' ? 'bg-amber-500' : 'bg-emerald-600'} text-white text-[9px]`}>{diff.preview.estimated_seo_impact}</Badge></p>
            </div>

            <div className="mb-3">
              <h4 className="text-xs font-bold text-slate-700 mb-1.5">Proposed changes:</h4>
              <pre className="bg-slate-900 text-emerald-200 p-2 rounded text-[10px] overflow-x-auto">{JSON.stringify(diff.changes, null, 2)}</pre>
            </div>

            {diff.preview.meta_description_diffs?.length > 0 ? (
              <div className="mb-3">
                <h4 className="text-xs font-bold text-slate-700 mb-1.5">SEO meta description redline (top {diff.preview.meta_description_diffs.length} samples):</h4>
                <div className="space-y-2">
                  {diff.preview.meta_description_diffs.map((d, i) => (
                    <div key={i} className="border border-slate-200 rounded p-2 text-[11px]" data-testid={`diff-sample-${i}`}>
                      <div className="font-mono font-bold text-slate-700">{d.code} · char_diff={d.char_diff}</div>
                      <div className="text-rose-700 line-through mt-1">- {d.before}</div>
                      <div className="text-emerald-700 mt-0.5">+ {d.after}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic mb-3">No SEO meta description differences detected from this change. Internal field changes only.</p>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button variant="ghost" onClick={() => setDiff(null)} data-testid="diff-modal-cancel">Cancel</Button>
              <Button onClick={commitDiff} disabled={busy} className="bg-emerald-600 hover:bg-emerald-700" data-testid="diff-modal-confirm">
                <CheckCircle className="h-3.5 w-3.5 mr-1" />Confirm & Commit
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Verify Wizard Modal */}
      {wizardOpen && (
        <VerifyWizardModal
          items={items.filter(b => b.status === 'draft')}
          idx={wizardIdx}
          setIdx={setWizardIdx}
          onClose={() => { setWizardOpen(false); load(); }}
          onVerify={async (code) => { await onVerify(code); await load(); }}
        />
      )}

      {/* LAA Split Modal */}
      {laaSplitOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" data-testid="laa-split-modal">
          <Card className="w-full max-w-2xl p-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-bold">LAA Umbrella Split · 6 State Bodies</h3>
              <Button variant="ghost" size="sm" onClick={() => setLaaSplitOpen(false)}><X className="h-4 w-4" /></Button>
            </div>
            <p className="text-xs text-slate-600 mb-3">Pre-populated with default state-level legal admissions bodies. Edit fees if needed. LAA will be marked deprecated; occupations stay linked until you migrate them.</p>
            <div className="space-y-2">
              {laaBodies.map((b, i) => (
                <div key={b.code} className="grid grid-cols-12 gap-2 text-xs" data-testid={`laa-state-row-${b.code}`}>
                  <div className="col-span-2 font-mono font-bold py-1.5">{b.code}</div>
                  <input className="col-span-7 border rounded px-2 text-xs" value={b.full_name} onChange={e => { const next = [...laaBodies]; next[i].full_name = e.target.value; setLaaBodies(next); }} />
                  <input type="number" className="col-span-3 border rounded px-2 text-xs" value={b.msa_fee_aud} onChange={e => { const next = [...laaBodies]; next[i].msa_fee_aud = +e.target.value; setLaaBodies(next); }} placeholder="MSA Fee" />
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="ghost" onClick={() => setLaaSplitOpen(false)} data-testid="laa-split-cancel">Cancel</Button>
              <Button onClick={confirmLaaSplit} disabled={busy} className="bg-amber-600 hover:bg-amber-700" data-testid="laa-split-confirm">Confirm Split</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, color = 'slate', testid }) {
  const colorClass = { slate: 'text-slate-900', emerald: 'text-emerald-700', amber: 'text-amber-700', rose: 'text-rose-700', indigo: 'text-leamss-teal' }[color];
  return (
    <Card className="p-3 text-center">
      <p className="text-[10px] uppercase font-bold tracking-wider text-slate-500">{label}</p>
      <p className={`text-xl font-bold ${colorClass} mt-1`} data-testid={testid}>{value}</p>
    </Card>
  );
}

function Field({ label, value, onChange, type = 'text', testid }) {
  return (
    <div>
      <label className="text-[10px] font-semibold text-slate-700 uppercase">{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} className="w-full border border-slate-300 rounded px-2 py-1 text-xs" data-testid={testid} />
    </div>
  );
}

function VerifyWizardModal({ items, idx, setIdx, onClose, onVerify }) {
  if (items.length === 0) return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" data-testid="verify-wizard-empty">
      <Card className="p-5 max-w-md">
        <h3 className="text-base font-bold">All bodies verified!</h3>
        <p className="text-xs text-slate-600 mt-1">No draft bodies remain.</p>
        <Button size="sm" className="mt-3" onClick={onClose}>Close</Button>
      </Card>
    </div>
  );
  const body = items[Math.min(idx, items.length - 1)];
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" data-testid="verify-wizard-modal">
      <Card className="w-full max-w-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-bold">Verify Wizard · Step {idx + 1} of {items.length}</h3>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <div className="bg-slate-50 border rounded p-3 mb-3 space-y-1 text-xs" data-testid={`verify-wizard-step-${idx + 1}`}>
          <p><strong>Code:</strong> {body.code}</p>
          <p><strong>Full name:</strong> {body.full_name}</p>
          <p><strong>Linked occupations:</strong> {body.occupation_count || 0}</p>
          <p><strong>MSA fee:</strong> AUD ${body.fees?.msa_fee_aud || '—'}</p>
          <p><strong>Processing:</strong> {body.processing?.standard_days_min || '?'}-{body.processing?.standard_days_max || '?'} days</p>
          {body._seed_quality === 'placeholder' && <Badge className="bg-rose-100 text-rose-700 text-[9px]">PLACEHOLDER — Needs review before verifying</Badge>}
        </div>
        <div className="flex justify-between items-center pt-3 border-t">
          <Button size="sm" variant="ghost" onClick={() => setIdx(Math.max(0, idx - 1))} disabled={idx === 0} data-testid="verify-wizard-prev">‹ Previous</Button>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setIdx(Math.min(items.length - 1, idx + 1))} data-testid="verify-wizard-skip">Skip</Button>
            <Button size="sm" onClick={async () => { await onVerify(body.code); setIdx(Math.min(items.length - 1, idx + 1)); }} className="bg-emerald-600 hover:bg-emerald-700" data-testid="verify-wizard-next">Verify & Next ›</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
