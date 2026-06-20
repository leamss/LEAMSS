/**
 * Option D / X5 — Admin Client Portal Preview (Read-Only "Client View")
 *
 * Admin/CM/Sales can see exactly what a client sees, without needing the
 * client's password. Eliminates "what does my portal look like?" support
 * tickets. All access audit-logged on backend.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  LayoutDashboard, FileText, FolderOpen, FileSignature,
  ArrowLeft, Eye, CheckCircle, Clock,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const inrFmt = (n) => `₹${Number(n || 0).toLocaleString('en-IN')}`;
const tokenHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});

const TABS = [
  { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
  { id: 'info_sheet', icon: FileText, label: 'Info Sheet' },
  { id: 'documents', icon: FolderOpen, label: 'Documents' },
  { id: 'proposal', icon: FileSignature, label: 'Proposal' },
];

export default function AdminClientPortalPreview() {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [infoSheet, setInfoSheet] = useState(null);
  const [docs, setDocs] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [loading, setLoading] = useState(true);

  const base = `${API}/api/admin/client-portal-preview/${clientId}`;

  const loadOverview = useCallback(async () => {
    const r = await fetch(`${base}/overview`, { headers: tokenHeaders() });
    if (r.ok) setOverview(await r.json());
  }, [base]);

  const loadInfoSheet = useCallback(async () => {
    const r = await fetch(`${base}/info-sheet`, { headers: tokenHeaders() });
    if (r.ok) setInfoSheet(await r.json());
  }, [base]);

  const loadDocs = useCallback(async () => {
    const r = await fetch(`${base}/documents`, { headers: tokenHeaders() });
    if (r.ok) setDocs(await r.json());
  }, [base]);

  const loadProposal = useCallback(async () => {
    const r = await fetch(`${base}/proposal`, { headers: tokenHeaders() });
    if (r.ok) setProposal(await r.json());
  }, [base]);

  useEffect(() => {
    (async () => {
      await loadOverview();
      setLoading(false);
    })();
  }, [loadOverview]);

  useEffect(() => {
    if (tab === 'info_sheet' && !infoSheet) loadInfoSheet();
    if (tab === 'documents' && !docs) loadDocs();
    if (tab === 'proposal' && !proposal) loadProposal();
  }, [tab, infoSheet, docs, proposal, loadInfoSheet, loadDocs, loadProposal]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-leamss-bg_white">
        <div className="text-slate-400">Loading client preview…</div>
      </div>
    );
  }
  if (!overview) {
    return (
      <Card className="p-8 max-w-xl mx-auto mt-12 text-center">
        <p className="text-leamss-red font-bold mb-2">Cannot load preview</p>
        <p className="text-sm text-slate-500">Client portal not found or access denied.</p>
        <Button className="mt-4" onClick={() => navigate(-1)}>← Back</Button>
      </Card>
    );
  }

  const client = overview._viewing_as || {};

  return (
    <div className="min-h-screen bg-leamss-bg_white" data-testid="admin-client-portal-preview">
      {/* READ-ONLY BANNER — strikingly visible */}
      <div className="bg-leamss-orange text-white py-2 px-4 sticky top-0 z-20"
           data-testid="client-view-readonly-banner">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <Eye className="h-4 w-4" />
            <span className="font-bold">Read-Only Client View</span>
            <span className="opacity-90">— Viewing as <strong>{client.client_name}</strong> ({client.client_email})</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}
                  className="text-white hover:bg-white/20"
                  data-testid="preview-back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back to admin
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-5 flex gap-6">
        {/* Sidebar */}
        <aside className="w-56 shrink-0">
          <Card className="p-2" data-testid="client-view-preview-tab">
            {TABS.map(t => {
              const Icon = t.icon;
              return (
                <button key={t.id} onClick={() => setTab(t.id)}
                        className={`w-full flex items-center gap-2 px-3 py-2.5 rounded text-sm font-medium transition ${
                          tab === t.id ? 'bg-leamss-teal text-white' : 'hover:bg-slate-100 text-slate-700'
                        }`}
                        data-testid={`preview-tab-${t.id}`}>
                  <Icon className="h-4 w-4" /> {t.label}
                </button>
              );
            })}
            {/* Settings tab disabled */}
            <div className="px-3 py-2 text-xs text-slate-400 italic mt-2 border-t pt-2">
              Settings ✗ (Client-managed only)
            </div>
          </Card>
        </aside>

        {/* Main */}
        <main className="flex-1">
          {tab === 'overview' && <PreviewOverview data={overview} />}
          {tab === 'info_sheet' && <PreviewInfoSheet data={infoSheet} />}
          {tab === 'documents' && <PreviewDocs data={docs} />}
          {tab === 'proposal' && <PreviewProposal data={proposal} />}
        </main>
      </div>
    </div>
  );
}

function PreviewOverview({ data }) {
  if (!data) return <Card className="p-6">Loading…</Card>;
  return (
    <div className="space-y-5" data-testid="preview-overview">
      <Card className="p-6">
        <h2 className="text-xl font-bold text-leamss-teal mb-1">Client's Journey View</h2>
        <p className="text-sm text-slate-500 mb-5">Exactly what {data._viewing_as?.client_name?.split(' ')[0] || 'the client'} sees in their portal.</p>
        <div className="space-y-3">
          {data.timeline.map((s, i) => {
            const done = s.status === 'done';
            const inP = s.status === 'in_progress';
            return (
              <div key={i} className="flex items-start gap-3">
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
                  {s.review_status && <div className="text-xs text-slate-400">Status: {s.review_status}</div>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid grid-cols-3 gap-3">
        <Card className="p-4 text-center">
          <div className="text-2xl font-bold text-leamss-teal">{data.summary.doc_count}</div>
          <div className="text-xs uppercase text-slate-500 mt-1">Documents</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-lg font-bold text-leamss-teal">{data.summary.has_info_sheet ? '✓' : '–'}</div>
          <div className="text-xs uppercase text-slate-500 mt-1">Info Sheet</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-lg font-bold text-leamss-orange">{data.summary.proposal_status || '–'}</div>
          <div className="text-xs uppercase text-slate-500 mt-1">Proposal</div>
        </Card>
      </div>
    </div>
  );
}

function PreviewInfoSheet({ data }) {
  if (!data) return <Card className="p-6">Loading info sheet…</Card>;
  const sheet = data.info_sheet;
  if (!sheet) return <Card className="p-6 text-slate-500">{data.message || 'No info sheet'}</Card>;
  const p = sheet.personal || {};
  return (
    <Card className="p-6" data-testid="preview-info-sheet">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-leamss-teal">Info Sheet (Read-Only)</h2>
        <Badge className="bg-leamss-orange">Preview Only</Badge>
      </div>
      <h3 className="font-bold mt-2 mb-3 text-leamss-orange">Personal Details</h3>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><span className="text-slate-500">Given Names:</span> <strong>{p.given_names || '—'}</strong></div>
        <div><span className="text-slate-500">Family Name:</span> <strong>{p.family_name || '—'}</strong></div>
        <div><span className="text-slate-500">DOB:</span> <strong>{p.date_of_birth || '—'}</strong></div>
        <div><span className="text-slate-500">Nationality:</span> <strong>{p.nationality || '—'}</strong></div>
        <div><span className="text-slate-500">Email:</span> <strong>{p.email || '—'}</strong></div>
        <div><span className="text-slate-500">Phone:</span> <strong>{p.contact_number || '—'}</strong></div>
      </div>
      <p className="text-xs text-slate-400 mt-4">
        Last updated: {(sheet.updated_at || '').slice(0, 19).replace('T', ' ')} · Schema v{sheet.schema_version}
      </p>
    </Card>
  );
}

function PreviewDocs({ data }) {
  if (!data) return <Card className="p-6">Loading documents…</Card>;
  const cats = ['identity', 'qualifications', 'employment', 'english_test', 'other'];
  const labels = {
    identity: 'Identity', qualifications: 'Qualifications',
    employment: 'Employment', english_test: 'English Test', other: 'Other',
  };
  return (
    <Card className="p-6" data-testid="preview-documents">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-leamss-teal">Documents (Read-Only)</h2>
        <Badge className="bg-leamss-orange">{data.total} uploaded</Badge>
      </div>
      {cats.map(cat => {
        const items = (data.by_category && data.by_category[cat]) || [];
        return (
          <div key={cat} className="mb-4 border-b pb-3 last:border-0">
            <h3 className="font-bold text-leamss-orange text-sm uppercase">{labels[cat]} ({items.length})</h3>
            {items.length === 0 ? (
              <p className="text-xs text-slate-400 mt-1">No documents in this category yet</p>
            ) : (
              <ul className="mt-2 space-y-1 text-sm">
                {items.map(d => (
                  <li key={d.id} className="flex justify-between p-2 bg-slate-50 rounded">
                    <span>{d.document_name}</span>
                    <span className="text-xs text-slate-500">{(d.uploaded_at || '').slice(0, 10)} · {d.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </Card>
  );
}

function PreviewProposal({ data }) {
  if (!data) return <Card className="p-6">Loading proposal…</Card>;
  const p = data.proposal;
  if (!p) return <Card className="p-6 text-slate-500">{data.message}</Card>;
  return (
    <Card className="p-6" data-testid="preview-proposal">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-leamss-teal">Proposal (Read-Only)</h2>
        <Badge className="bg-leamss-orange">{p.status}</Badge>
      </div>
      <p className="text-xs text-slate-500 mb-3">Ref <code>{p.id.slice(0, 12).toUpperCase()}</code></p>
      <div className="grid grid-cols-2 gap-3 text-sm mb-3">
        <div>Product: <strong>{p.product_name}</strong></div>
        <div>Country/Visa: <strong>{p.country} · {p.service_type}</strong></div>
        <div>Base: {inrFmt(p.base_fees_inr)}</div>
        <div>Add-ons: {inrFmt(p.addon_total_inr)}</div>
        <div className="text-leamss-teal">Coupons: −{inrFmt(p.coupon_total_inr)}</div>
        <div className="text-leamss-red">Admin Disc: −{inrFmt(p.admin_discount_inr)}</div>
        <div>Subtotal: {inrFmt(p.subtotal_inr)}</div>
        <div>GST 18%: {inrFmt(p.gst_inr)}</div>
      </div>
      <div className="border-t pt-3 flex items-baseline justify-between">
        <span className="text-sm uppercase font-bold text-slate-500">Total</span>
        <span className="text-2xl font-bold text-leamss-orange">{inrFmt(p.total_inr)}</span>
      </div>
    </Card>
  );
}
