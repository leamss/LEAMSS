/**
 * Step 2 — Client Portal Dashboard
 *
 * 5-tab layout: Overview · Info Sheet · Documents · Proposal · Settings
 * Strict client-token isolation (separate from staff session).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboard, FileText, FolderOpen, FileSignature, Settings,
  LogOut, CheckCircle, Clock, AlertCircle, Upload, Trash2, Download,
  Mail, Phone, MessageCircle, KeyRound,
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const inrFmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`;
const tok = () => localStorage.getItem('client_token') || '';
const cfg = () => ({ Authorization: `Bearer ${tok()}` });

const TABS = [
  { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
  { id: 'info_sheet', icon: FileText, label: 'Info Sheet' },
  { id: 'documents', icon: FolderOpen, label: 'Documents' },
  { id: 'proposal', icon: FileSignature, label: 'Proposal' },
  { id: 'settings', icon: Settings, label: 'Settings' },
];

export default function ClientPortalDashboard() {
  const [tab, setTab] = useState('overview');
  const [me, setMe] = useState(null);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tok()) { window.location.href = '/client-portal/login'; return; }
    (async () => {
      try {
        const [meR, ovR] = await Promise.all([
          fetch(`${API}/api/client-auth/me`, { headers: cfg() }),
          fetch(`${API}/api/client-portal/overview`, { headers: cfg() }),
        ]);
        if (meR.status === 401 || meR.status === 403) {
          localStorage.removeItem('client_token');
          window.location.href = '/client-portal/login';
          return;
        }
        if (meR.ok) setMe(await meR.json());
        if (ovR.ok) setOverview(await ovR.json());
      } finally { setLoading(false); }
    })();
  }, []);

  const logout = async () => {
    try { await fetch(`${API}/api/client-auth/logout`, { method: 'POST', headers: cfg() }); } catch {}
    localStorage.removeItem('client_token');
    localStorage.removeItem('client_info');
    window.location.href = '/client-portal/login';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-leamss-bg_white">
        <div className="text-slate-400">Loading your portal…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-leamss-bg_white" data-testid="client-portal-dashboard">
      {/* Top bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-xl font-bold">
              <span className="text-leamss-teal">LE</span>
              <span className="text-leamss-orange">AM</span>
              <span className="text-leamss-red">SS</span>
              <span className="text-xs text-slate-500 ml-2 font-normal">· Client Portal</span>
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="text-right">
              <div className="font-bold text-leamss-teal">Welcome, {me?.name?.split(' ')[0] || 'Client'}</div>
              <div className="text-xs text-slate-500">{me?.email}</div>
            </div>
            <Badge className="bg-emerald-100 text-emerald-700 border-0">{me?.status || 'active'}</Badge>
            <Button variant="ghost" size="sm" onClick={logout} data-testid="client-logout-btn">
              <LogOut className="h-4 w-4 mr-1" /> Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 flex gap-6">
        {/* Sidebar */}
        <aside className="w-56 shrink-0" data-testid="client-sidebar">
          <Card className="p-2">
            {TABS.map(t => {
              const Icon = t.icon;
              return (
                <button key={t.id} onClick={() => setTab(t.id)}
                        className={`w-full flex items-center gap-2 px-3 py-2.5 rounded text-sm font-medium transition ${
                          tab === t.id ? 'bg-leamss-teal text-white' : 'hover:bg-slate-100 text-slate-700'
                        }`}
                        data-testid={`tab-${t.id}`}>
                  <Icon className="h-4 w-4" /> {t.label}
                </button>
              );
            })}
          </Card>
          {/* Contact card */}
          <Card className="p-4 mt-4 text-xs">
            <p className="font-bold text-leamss-teal mb-2">Need help?</p>
            <div className="space-y-1 text-slate-600">
              <a href="mailto:hello@leamss.com" className="flex items-center gap-1 hover:text-leamss-teal"><Mail className="h-3 w-3"/>hello@leamss.com</a>
              <a href="tel:+919999999999" className="flex items-center gap-1 hover:text-leamss-teal"><Phone className="h-3 w-3"/>+91 99999 99999</a>
              <a href="https://wa.me/919999999999" className="flex items-center gap-1 hover:text-leamss-teal"><MessageCircle className="h-3 w-3"/>WhatsApp</a>
            </div>
          </Card>
        </aside>

        {/* Main */}
        <main className="flex-1 min-w-0">
          {tab === 'overview' && <OverviewTab overview={overview} onTab={setTab} />}
          {tab === 'info_sheet' && <InfoSheetTab me={me} />}
          {tab === 'documents' && <DocumentsTab me={me} />}
          {tab === 'proposal' && <ProposalTab />}
          {tab === 'settings' && <SettingsTab me={me} />}
        </main>
      </div>
    </div>
  );
}

/* ─── Overview ────────────────────────────────────────────────────────────── */
function OverviewTab({ overview, onTab }) {
  if (!overview) return <Card className="p-6">No data yet.</Card>;
  const tl = overview.timeline || [];
  return (
    <div className="space-y-5" data-testid="overview-tab">
      <Card className="p-6">
        <h2 className="text-xl font-bold text-leamss-teal mb-1">Your Journey</h2>
        <p className="text-sm text-slate-500 mb-5">Track every stage from Pre-Assessment to Visa Lodgement.</p>
        <div className="space-y-3" data-testid="status-timeline">
          {tl.map((s, i) => {
            const done = s.status === 'done';
            const inP = s.status === 'in_progress';
            return (
              <div key={i} className="flex items-start gap-3" data-testid={`timeline-${i}`}>
                <div className={`mt-1 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                  done ? 'bg-leamss-teal text-white' :
                  inP ? 'bg-leamss-orange text-white' :
                  'bg-slate-200 text-slate-400'
                }`}>
                  {done ? <CheckCircle className="h-4 w-4" /> :
                   inP ? <Clock className="h-4 w-4" /> :
                   <span className="text-xs">{i+1}</span>}
                </div>
                <div className="flex-1">
                  <div className={`font-medium ${done ? 'text-leamss-teal' : inP ? 'text-leamss-orange' : 'text-slate-600'}`}>
                    {s.stage}
                  </div>
                  {s.count !== undefined && <div className="text-xs text-slate-400">{s.count} uploaded</div>}
                  {s.review_status && s.review_status !== 'pending' && <div className="text-xs text-slate-400">Status: {s.review_status}</div>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {overview.next_action && (
        <Card className="p-6 bg-gradient-to-br from-leamss-orange/10 to-orange-50 border-leamss-orange/40">
          <p className="text-xs uppercase font-bold text-leamss-orange mb-1">Next Step</p>
          <h3 className="text-lg font-bold mb-1">{overview.next_action.label}</h3>
          <p className="text-sm text-slate-600 mb-3">{overview.next_action.subtitle}</p>
          {overview.next_action.tab && overview.next_action.tab !== 'overview' && (
            <Button onClick={() => onTab(overview.next_action.tab)}
                    className="bg-leamss-orange hover:bg-leamss-orange/90 text-white"
                    data-testid="next-action-btn">
              Go to {TABS.find(t => t.id === overview.next_action.tab)?.label || 'next step'} →
            </Button>
          )}
        </Card>
      )}

      <div className="grid grid-cols-3 gap-3">
        <Card className="p-4 text-center">
          <div className="text-2xl font-bold text-leamss-teal">{overview.summary.doc_count}</div>
          <div className="text-xs uppercase text-slate-500 mt-1">Documents</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-lg font-bold text-leamss-teal">{overview.summary.has_info_sheet ? '✓' : '–'}</div>
          <div className="text-xs uppercase text-slate-500 mt-1">Info Sheet</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-lg font-bold text-leamss-orange">{overview.summary.proposal_status || '–'}</div>
          <div className="text-xs uppercase text-slate-500 mt-1">Proposal</div>
        </Card>
      </div>
    </div>
  );
}

/* ─── Info Sheet ──────────────────────────────────────────────────────────── */
function InfoSheetTab() {
  const [sheet, setSheet] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/client-portal/info-sheet`, { headers: cfg() });
    if (r.ok) setSheet(await r.json());
  }, []);
  useEffect(() => { load(); }, [load]);

  const debouncedSave = useCallback((field, val) => {
    let timer;
    return ((v) => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        setSaving(true);
        const updated = { ...sheet, [field]: v };
        setSheet(updated);
        const r = await fetch(`${API}/api/client-portal/info-sheet`, {
          method: 'PATCH', headers: { 'Content-Type': 'application/json', ...cfg() },
          body: JSON.stringify({ [field]: v }),
        });
        setSaving(false);
        if (!r.ok) toast.error('Save failed');
      }, 700);
    })(val);
  }, [sheet]);

  if (!sheet) return <Card className="p-6">Loading info sheet…</Card>;

  const personal = sheet.personal || {};
  const setPersonal = (k, v) => debouncedSave('personal', { ...personal, [k]: v });

  return (
    <div className="space-y-5" data-testid="info-sheet-tab">
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-leamss-teal">Information Sheet</h2>
          <span className="text-xs text-slate-500">{saving ? 'Saving…' : 'All changes auto-saved'}</span>
        </div>

        <h3 className="font-bold mt-2 mb-3 text-leamss-orange">Personal Details</h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><Label>Given Names</Label>
            <Input defaultValue={personal.given_names || ''} onBlur={(e) => setPersonal('given_names', e.target.value)}
                   data-testid="is-given-names" /></div>
          <div><Label>Family Name</Label>
            <Input defaultValue={personal.family_name || ''} onBlur={(e) => setPersonal('family_name', e.target.value)}
                   data-testid="is-family-name" /></div>
          <div><Label>Date of Birth</Label>
            <Input type="date" defaultValue={personal.date_of_birth || ''} onBlur={(e) => setPersonal('date_of_birth', e.target.value)}
                   data-testid="is-dob" /></div>
          <div><Label>Nationality</Label>
            <Input defaultValue={personal.nationality || ''} onBlur={(e) => setPersonal('nationality', e.target.value)}
                   data-testid="is-nationality" /></div>
          <div><Label>Email</Label>
            <Input type="email" defaultValue={personal.email || ''} onBlur={(e) => setPersonal('email', e.target.value)}
                   data-testid="is-email" /></div>
          <div><Label>Contact Number</Label>
            <Input defaultValue={personal.contact_number || ''} onBlur={(e) => setPersonal('contact_number', e.target.value)}
                   data-testid="is-phone" /></div>
        </div>

        <p className="text-xs text-slate-400 mt-4">
          Schema v{sheet.schema_version} · Last updated: {(sheet.updated_at || '').slice(0, 19).replace('T', ' ')}
        </p>
      </Card>

      <Card className="p-4 bg-leamss-teal/5 border-leamss-teal/30 text-sm">
        💡 More sections (Qualifications · Employment · Resume Upload with AI extract) are accessible via your case manager. For self-service edits, the universal Info Sheet supports all 6 sections.
      </Card>
    </div>
  );
}

/* ─── Documents ───────────────────────────────────────────────────────────── */
function DocumentsTab() {
  const [data, setData] = useState(null);
  const [uploading, setUploading] = useState(null);

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/client-portal/documents`, { headers: cfg() });
    if (r.ok) setData(await r.json());
  }, []);
  useEffect(() => { load(); }, [load]);

  const upload = async (category, file) => {
    if (!file) return;
    setUploading(category);
    const fd = new FormData();
    fd.append('file', file);
    fd.append('document_type', category);
    fd.append('document_name', file.name);
    try {
      const r = await fetch(`${API}/api/client-portal/documents`, {
        method: 'POST', headers: cfg(), body: fd,
      });
      if (r.ok) { toast.success(`Uploaded ${file.name}`); load(); }
      else { const e = await r.json(); toast.error(e.detail || 'Upload failed'); }
    } finally { setUploading(null); }
  };

  const del = async (id, name) => {
    if (!window.confirm(`Delete "${name}"?`)) return;
    const r = await fetch(`${API}/api/client-portal/documents/${id}`, { method: 'DELETE', headers: cfg() });
    if (r.ok) { toast.success('Deleted'); load(); }
    else { const e = await r.json(); toast.error(e.detail || 'Delete failed'); }
  };

  if (!data) return <Card className="p-6">Loading documents…</Card>;

  const CAT_LABELS = {
    identity: { title: 'Identity', desc: 'Passport, Aadhaar, Birth Certificate' },
    qualifications: { title: 'Qualifications', desc: 'Marksheets, Degree Certificates, Transcripts' },
    employment: { title: 'Employment', desc: 'Reference Letters, Pay Slips, Tax Returns' },
    english_test: { title: 'English Test', desc: 'PTE / IELTS scorecard' },
    other: { title: 'Other', desc: 'Any supporting documents' },
  };

  return (
    <div className="space-y-4" data-testid="documents-tab">
      <Card className="p-5">
        <h2 className="text-xl font-bold text-leamss-teal mb-2">Your Documents</h2>
        <p className="text-sm text-slate-500">
          {data.total} uploaded · PDF / JPG / PNG / Word / Excel · max 10MB per file
        </p>
      </Card>

      {data.categories.map(cat => {
        const meta = CAT_LABELS[cat];
        const docs = data.by_category[cat] || [];
        return (
          <Card key={cat} className="p-5" data-testid={`category-${cat}`}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-bold text-leamss-orange">{meta.title}</h3>
                <p className="text-xs text-slate-500">{meta.desc}</p>
              </div>
              <Badge variant="outline">{docs.length} uploaded</Badge>
            </div>

            <label className={`block border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition ${
              uploading === cat ? 'border-leamss-orange bg-leamss-orange/5' : 'border-slate-300 hover:border-leamss-teal hover:bg-leamss-teal/5'
            }`}>
              <input type="file" hidden onChange={(e) => upload(cat, e.target.files[0])}
                     accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xlsx"
                     data-testid={`upload-${cat}`} />
              <Upload className="h-6 w-6 mx-auto mb-1 text-slate-400" />
              <p className="text-sm font-medium">
                {uploading === cat ? 'Uploading…' : `Drop file here or click to browse`}
              </p>
            </label>

            {docs.length > 0 && (
              <div className="mt-3 space-y-2">
                {docs.map(d => (
                  <div key={d.id} className="flex items-center justify-between p-3 bg-slate-50 rounded text-sm" data-testid={`doc-row-${d.id}`}>
                    <div className="flex-1">
                      <div className="font-medium">{d.document_name}</div>
                      <div className="text-xs text-slate-500">
                        {Math.round(d.file_size_bytes / 1024)} KB · {(d.uploaded_at || '').slice(0, 10)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={
                        d.status === 'verified' ? 'bg-emerald-500' :
                        d.status === 'rejected' ? 'bg-leamss-red' : 'bg-slate-400'
                      }>{d.status}</Badge>
                      {d.status !== 'verified' && (
                        <Button variant="ghost" size="sm" onClick={() => del(d.id, d.document_name)}
                                data-testid={`delete-doc-${d.id}`}>
                          <Trash2 className="h-4 w-4 text-leamss-red" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

/* ─── Proposal ────────────────────────────────────────────────────────────── */
function ProposalTab() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [declineMode, setDeclineMode] = useState(false);
  const [declineReason, setDeclineReason] = useState('');

  const load = useCallback(async () => {
    const r = await fetch(`${API}/api/client-portal/proposal`, { headers: cfg() });
    if (r.ok) setData(await r.json());
  }, []);
  useEffect(() => { load(); }, [load]);

  const accept = async (id) => {
    setBusy(true);
    const r = await fetch(`${API}/api/client-portal/proposal/${id}/accept`,
                          { method: 'POST', headers: { 'Content-Type': 'application/json', ...cfg() },
                            body: JSON.stringify({}) });
    setBusy(false);
    if (r.ok) { toast.success('Proposal accepted! Your full case is now active. 🎉'); load(); }
    else { const e = await r.json(); toast.error(e.detail); }
  };

  const decline = async (id) => {
    if (declineReason.length < 3) { toast.error('Please provide a reason'); return; }
    setBusy(true);
    const r = await fetch(`${API}/api/client-portal/proposal/${id}/decline`,
                          { method: 'POST', headers: { 'Content-Type': 'application/json', ...cfg() },
                            body: JSON.stringify({ reason: declineReason }) });
    setBusy(false);
    if (r.ok) { toast.success('Proposal declined. Our team will reach out.'); setDeclineMode(false); load(); }
    else { const e = await r.json(); toast.error(e.detail); }
  };

  if (!data) return <Card className="p-6">Loading proposal…</Card>;
  if (!data.proposal) {
    return (
      <Card className="p-8 text-center" data-testid="no-proposal">
        <FileSignature className="h-12 w-12 mx-auto text-slate-300 mb-3" />
        <h3 className="font-bold mb-1">No proposal yet</h3>
        <p className="text-sm text-slate-500">{data.message}</p>
      </Card>
    );
  }
  const p = data.proposal;
  const isSent = p.status === 'sent';

  return (
    <div className="space-y-4" data-testid="proposal-tab">
      <Card className={`p-5 ${isSent ? 'bg-leamss-teal/10 border-leamss-teal/30' :
                                  p.status === 'accepted' ? 'bg-emerald-50 border-emerald-300' :
                                  'bg-slate-50'}`}>
        <p className="text-xs uppercase font-bold text-leamss-teal">Proposal Status</p>
        <h3 className="text-lg font-bold mt-1">
          {isSent ? '📬 Your proposal is ready!' :
           p.status === 'accepted' ? '🎉 Proposal accepted — case is active' :
           p.status === 'declined' ? 'Declined' : p.status}
        </h3>
        <p className="text-xs text-slate-600 mt-1">
          Ref: <code>{p.id.slice(0, 12).toUpperCase()}</code> · Expires: {(p.expires_at || '').slice(0, 10)}
        </p>
      </Card>

      <Card className="p-5">
        <h3 className="font-bold mb-3 text-leamss-teal">Investment Breakdown</h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>Product: <strong>{p.product_name}</strong></div>
          <div>Country: <strong>{p.country} · {p.service_type}</strong></div>
          <div>Base Fees: {inrFmt(p.base_fees_inr)}</div>
          <div>Add-ons: {inrFmt(p.addon_total_inr)}</div>
          <div className="text-leamss-teal">Coupons: −{inrFmt(p.coupon_total_inr)}</div>
          <div className="text-leamss-red">Admin Discount: −{inrFmt(p.admin_discount_inr)}</div>
          <div>Subtotal: {inrFmt(p.subtotal_inr)}</div>
          <div>GST 18%: {inrFmt(p.gst_inr)}</div>
        </div>
        <div className="border-t pt-3 mt-3 flex items-baseline justify-between">
          <span className="text-sm uppercase font-bold text-slate-500">Total</span>
          <span className="text-3xl font-bold text-leamss-orange">{inrFmt(p.total_inr)}</span>
        </div>
        <a href={`${API}/api/proposals/${p.id}/pdf`} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1 text-sm text-leamss-teal hover:underline mt-3"
           data-testid="proposal-pdf-link">
          <Download className="h-4 w-4" /> Download full PDF
        </a>
      </Card>

      {isSent && (
        <Card className="p-5">
          {!declineMode ? (
            <div className="flex gap-3">
              <Button disabled={busy} onClick={() => accept(p.id)}
                      className="flex-1 bg-leamss-orange hover:bg-leamss-orange/90 text-white font-bold text-base py-6"
                      data-testid="accept-proposal-btn">
                ✓ Accept & Activate My Case
              </Button>
              <Button disabled={busy} variant="outline" onClick={() => setDeclineMode(true)}
                      className="border-leamss-red text-leamss-red hover:bg-red-50"
                      data-testid="decline-proposal-btn">
                Decline
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Reason for declining (helps us improve)</Label>
              <textarea rows={3} value={declineReason}
                        onChange={(e) => setDeclineReason(e.target.value)}
                        className="w-full border border-slate-300 rounded p-2 text-sm"
                        placeholder="e.g. Need more time / price concern / pursuing other option"
                        data-testid="decline-reason-input" />
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => setDeclineMode(false)}>Cancel</Button>
                <Button disabled={busy} onClick={() => decline(p.id)}
                        className="bg-leamss-red hover:bg-leamss-red/90 text-white"
                        data-testid="confirm-decline-btn">
                  Confirm Decline
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

/* ─── Settings ────────────────────────────────────────────────────────────── */
function SettingsTab({ me }) {
  const [cur, setCur] = useState('');
  const [neu, setNeu] = useState('');
  const [conf, setConf] = useState('');
  const [busy, setBusy] = useState(false);

  const change = async (e) => {
    e.preventDefault();
    if (neu !== conf) { toast.error('New passwords do not match'); return; }
    if (neu.length < 8) { toast.error('New password must be at least 8 characters'); return; }
    setBusy(true);
    const r = await fetch(`${API}/api/client-auth/change-password`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...cfg() },
      body: JSON.stringify({ current_password: cur, new_password: neu }),
    });
    setBusy(false);
    if (r.ok) { toast.success('Password updated successfully'); setCur(''); setNeu(''); setConf(''); }
    else { const e = await r.json(); toast.error(e.detail); }
  };

  return (
    <div className="space-y-5" data-testid="settings-tab">
      <Card className="p-5">
        <h2 className="text-xl font-bold text-leamss-teal mb-4">Your Profile</h2>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><Label className="text-xs text-slate-500">Full Name</Label><div className="font-medium">{me?.name}</div></div>
          <div><Label className="text-xs text-slate-500">Email</Label><div className="font-medium">{me?.email}</div></div>
          <div><Label className="text-xs text-slate-500">Phone</Label><div className="font-medium">{me?.phone || '—'}</div></div>
          <div><Label className="text-xs text-slate-500">Account Created</Label><div className="font-medium text-xs">{(me?.created_at || '').slice(0, 10)}</div></div>
        </div>
      </Card>

      <Card className="p-5">
        <h3 className="font-bold mb-4 text-leamss-orange flex items-center gap-2">
          <KeyRound className="h-4 w-4" /> Change Password
        </h3>
        {me?.must_change_password && (
          <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 p-3 rounded mb-4 text-sm">
            ⚠ You are using a temporary password. Please change it now for security.
          </div>
        )}
        <form onSubmit={change} className="space-y-3">
          <div>
            <Label>Current Password</Label>
            <Input type="password" required value={cur} onChange={(e) => setCur(e.target.value)}
                   data-testid="settings-current-password" />
          </div>
          <div>
            <Label>New Password (min 8 chars, upper/lower/digit/special)</Label>
            <Input type="password" required value={neu} onChange={(e) => setNeu(e.target.value)}
                   data-testid="settings-new-password" />
          </div>
          <div>
            <Label>Confirm New Password</Label>
            <Input type="password" required value={conf} onChange={(e) => setConf(e.target.value)}
                   data-testid="settings-confirm-password" />
          </div>
          <Button type="submit" disabled={busy}
                  className="bg-leamss-teal hover:bg-leamss-teal/90 text-white"
                  data-testid="settings-change-password-btn">
            {busy ? 'Updating…' : 'Update Password'}
          </Button>
        </form>
      </Card>

      <Card className="p-5 bg-leamss-teal/5">
        <h3 className="font-bold mb-2">Need help?</h3>
        <p className="text-sm text-slate-600">Your dedicated migration consultant is one click away:</p>
        <div className="mt-3 space-y-1 text-sm">
          <a href="mailto:hello@leamss.com" className="flex items-center gap-1 text-leamss-teal hover:underline"><Mail className="h-3 w-3"/>hello@leamss.com</a>
          <a href="tel:+919999999999" className="flex items-center gap-1 text-leamss-teal hover:underline"><Phone className="h-3 w-3"/>+91 99999 99999</a>
        </div>
      </Card>
    </div>
  );
}
