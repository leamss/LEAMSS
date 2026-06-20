/**
 * Phase 7.1 — Protection Policies Admin
 * Route: /admin/protection-policies
 *
 * Sir's USP: LEAMSS Protection Policy — 100% refund on negative outcomes.
 * Admin manages here, gets verified, surfaces in Assessment Report (Phase 7.3).
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  ArrowLeft, ShieldCheck, Plus, Loader2, Save, EyeOff, Eye,
  CheckCircle2, FileText, ExternalLink,
} from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_PILL = {
  draft: 'bg-amber-100 text-amber-800',
  verified: 'bg-emerald-100 text-emerald-800',
  hidden: 'bg-slate-200 text-slate-600',
};

export default function ProtectionPoliciesAdmin() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/protection-policies/`, { headers });
      setPolicies(r.data.items || []);
      if (!selectedId && r.data.items?.length) setSelectedId(r.data.items[0].policy_id);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load policies'));
    } finally { setLoading(false); }
  }, [headers, selectedId]);

  useEffect(() => { load(); }, []);

  const seedDefault = async () => {
    if (!window.confirm('Seed the default LEAMSS Protection Policy? Skipped if already exists.')) return;
    try {
      const r = await axios.post(`${API}/protection-policies/seed-default`, {}, { headers });
      if (r.data.already_seeded) {
        toast.info('Default policy already exists — opening it');
      } else {
        toast.success('Default LEAMSS Protection Policy seeded');
      }
      setSelectedId(r.data.policy.policy_id);
      load();
    } catch (e) {
      toast.error(formatApiError(e, 'Seed failed'));
    }
  };

  const selected = policies.find(p => p.policy_id === selectedId);

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="protection-policies-admin">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/admin')} data-testid="back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />Admin Home
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold flex items-center gap-2 text-emerald-900">
              <ShieldCheck className="h-7 w-7 text-emerald-600" />
              Protection Policies
              <Badge className="bg-emerald-600 text-white text-[9px]">Phase 7.1</Badge>
            </h1>
            <p className="text-xs text-slate-500">LEAMSS USP — 100% refund commitments managed here, surfaces in client Assessment Reports</p>
          </div>
          {policies.length === 0 && (
            <Button onClick={seedDefault} className="bg-emerald-600 hover:bg-emerald-700" data-testid="seed-default-btn">
              <Plus className="h-4 w-4 mr-1" />Seed Default LEAMSS Policy
            </Button>
          )}
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* Left rail */}
          <Card className="col-span-3 p-3 h-[calc(100vh-140px)] overflow-auto" data-testid="policies-list">
            {loading ? (
              <div className="flex items-center justify-center py-10 text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : policies.length === 0 ? (
              <div className="p-4 text-center">
                <ShieldCheck className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                <p className="text-xs text-slate-400 italic">No policies yet</p>
                <Button size="sm" variant="outline" onClick={seedDefault} className="mt-3 text-[10px]">
                  Seed Default
                </Button>
              </div>
            ) : (
              <ul className="space-y-1.5">
                {policies.map(p => (
                  <li key={p.policy_id}>
                    <button
                      onClick={() => setSelectedId(p.policy_id)}
                      className={`w-full text-left px-3 py-2 rounded text-xs transition ${
                        selectedId === p.policy_id ? 'bg-emerald-50 border-l-4 border-emerald-500 font-semibold' : 'hover:bg-slate-50 border-l-4 border-transparent'
                      }`}
                      data-testid={`policy-row-${p.policy_id}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="truncate">{p.title}</span>
                        <Badge className={`text-[9px] ${STATUS_PILL[p.status] || 'bg-slate-100'}`}>{p.status}</Badge>
                      </div>
                      <p className="text-[10px] text-slate-500 mt-0.5 font-mono">{p.policy_id}</p>
                      {p.is_default_leamss && (
                        <Badge className="bg-amber-100 text-amber-700 text-[9px] mt-1">★ Default LEAMSS</Badge>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Right editor */}
          <div className="col-span-9">
            {selected ? (
              <PolicyEditor key={selected.policy_id} policy={selected} headers={headers} onSaved={load} />
            ) : (
              <Card className="p-10 text-center text-slate-400">
                <ShieldCheck className="h-12 w-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">Select a policy from the left, or seed the default LEAMSS policy.</p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PolicyEditor({ policy, headers, onSaved }) {
  const [doc, setDoc] = useState(() => structuredClone(policy));
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [sourceRef, setSourceRef] = useState('');

  useEffect(() => { setDoc(structuredClone(policy)); }, [policy]);

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/protection-policies/${doc.policy_id}`, {
        title: doc.title,
        description_markdown: doc.description_markdown,
        refund_terms: doc.refund_terms,
        applicable_countries: doc.applicable_countries,
        applicable_visa_types: doc.applicable_visa_types,
      }, { headers });
      toast.success('Saved · Status reset to draft. Verify to publish.');
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  const verify = async () => {
    if (!sourceRef.trim() || sourceRef.length < 5) {
      toast.error('Source reference required (min 5 chars) — e.g., internal policy doc URL or PDF link');
      return;
    }
    setVerifying(true);
    try {
      await axios.post(`${API}/protection-policies/${doc.policy_id}/verify`, {
        source_reference: sourceRef.trim(),
      }, { headers });
      toast.success(`Policy ${doc.policy_id} verified — now appears in Assessment Reports`);
      setSourceRef('');
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Verify failed'));
    } finally { setVerifying(false); }
  };

  const toggleHide = async () => {
    const action = doc.status === 'hidden' ? 'unhide' : 'hide';
    if (!window.confirm(`${action.toUpperCase()} this policy? Sir's directive: hide instead of delete.`)) return;
    try {
      await axios.post(`${API}/protection-policies/${doc.policy_id}/${action}`, {}, { headers });
      toast.success(`Policy ${action}d successfully`);
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, `${action} failed`));
    }
  };

  return (
    <Card className="p-4 space-y-4" data-testid={`policy-editor-${doc.policy_id}`}>
      <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b">
        <div>
          <h2 className="text-lg font-bold">{doc.title}</h2>
          <p className="text-xs text-slate-500">
            <span className="font-mono">{doc.policy_id}</span> · v{doc.version}
            {doc.verification?.at && (
              <span className="ml-2">· Verified by {doc.verification.by_name} on {new Date(doc.verification.at).toLocaleDateString()}</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={STATUS_PILL[doc.status]}>{doc.status}</Badge>
          <Button size="sm" variant="outline" onClick={toggleHide} data-testid="toggle-hide-btn">
            {doc.status === 'hidden' ? <><Eye className="h-3 w-3 mr-1" />Unhide</> : <><EyeOff className="h-3 w-3 mr-1" />Hide</>}
          </Button>
        </div>
      </div>

      <div>
        <Label className="text-xs">Title</Label>
        <Input value={doc.title} onChange={(e) => setDoc(prev => ({ ...prev, title: e.target.value }))} data-testid="title-input" />
      </div>

      <div>
        <Label className="text-xs">Description (Markdown)</Label>
        <Textarea
          rows={10}
          value={doc.description_markdown || ''}
          onChange={(e) => setDoc(prev => ({ ...prev, description_markdown: e.target.value }))}
          className="font-mono text-xs"
          data-testid="description-input"
        />
        <p className="text-[10px] text-slate-400 mt-1">## Headings · **bold** · *italic* · - bullets — all supported in the Assessment Report PDF</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-3 bg-emerald-50/40">
          <p className="text-[10px] font-bold uppercase text-emerald-800 mb-2">What's Covered (Refund)</p>
          <Textarea
            rows={3}
            placeholder="professional_fees, government_fees, body_fees (comma-separated)"
            value={(doc.refund_terms?.covers || []).join(', ')}
            onChange={(e) => setDoc(prev => ({
              ...prev,
              refund_terms: { ...prev.refund_terms, covers: e.target.value.split(',').map(s => s.trim()).filter(Boolean) },
            }))}
            className="text-xs"
            data-testid="covers-input"
          />
        </Card>
        <Card className="p-3 bg-rose-50/40">
          <p className="text-[10px] font-bold uppercase text-rose-800 mb-2">What's NOT Covered (Excludes)</p>
          <Textarea
            rows={3}
            placeholder="english_test_fees, medical_test_fees (comma-separated)"
            value={(doc.refund_terms?.excludes || []).join(', ')}
            onChange={(e) => setDoc(prev => ({
              ...prev,
              refund_terms: { ...prev.refund_terms, excludes: e.target.value.split(',').map(s => s.trim()).filter(Boolean) },
            }))}
            className="text-xs"
            data-testid="excludes-input"
          />
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <Label className="text-xs">Claim Within (days)</Label>
          <Input
            type="number"
            value={doc.refund_terms?.claim_within_days || 90}
            onChange={(e) => setDoc(prev => ({
              ...prev,
              refund_terms: { ...prev.refund_terms, claim_within_days: parseInt(e.target.value, 10) || 90 },
            }))}
            data-testid="claim-days-input"
          />
        </div>
        <div>
          <Label className="text-xs">Applicable Countries (comma-separated, * for all)</Label>
          <Input
            value={(doc.applicable_countries || []).join(', ')}
            onChange={(e) => setDoc(prev => ({
              ...prev, applicable_countries: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
            }))}
            data-testid="countries-input"
          />
        </div>
        <div>
          <Label className="text-xs">Applicable Visa Types (comma-separated, * for all)</Label>
          <Input
            value={(doc.applicable_visa_types || []).join(', ')}
            onChange={(e) => setDoc(prev => ({
              ...prev, applicable_visa_types: e.target.value.split(',').map(s => s.trim()).filter(Boolean),
            }))}
            data-testid="visa-types-input"
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 pt-3 border-t">
        <Button onClick={save} disabled={saving} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="save-btn">
          {saving ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Save className="h-3 w-3 mr-1" />}
          {saving ? 'Saving…' : 'Save Changes'}
        </Button>
        {doc.status !== 'verified' && (
          <div className="flex items-center gap-2 ml-auto">
            <Input
              placeholder="Source reference (internal policy doc URL / approval ID)"
              value={sourceRef}
              onChange={(e) => setSourceRef(e.target.value)}
              className="h-9 text-xs w-72"
              data-testid="source-ref-input"
            />
            <Button onClick={verify} disabled={verifying || !sourceRef.trim()} className="bg-emerald-600 hover:bg-emerald-700" data-testid="verify-btn">
              {verifying ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <ShieldCheck className="h-3 w-3 mr-1" />}
              Verify &amp; Publish
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
