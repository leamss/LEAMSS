/**
 * Phase 22 — RoleCapabilityBuilder
 * Admin-only 4-layer Role & Capability Builder.
 *
 * Layer 1: Pack toggles (9 capability packs)
 * Layer 2: Feature catalog (search · category filter · checkbox grid)
 * Layer 3: Live preview (effective features/perms/ui_modules count + diff)
 * Layer 4: Save with required reason
 *
 * Brand: leamss.teal/orange/red/sky/slate/emerald only. data-testid on every interactive.
 */
import React, { useEffect, useMemo, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Search, Save, RotateCcw, AlertCircle, CheckCircle2, Lock, Sparkles } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const PACK_ACCENT = {
  baseline_employee: 'bg-leamss-teal-50 border-leamss-teal-300 text-leamss-teal-800',
  marketing: 'bg-leamss-orange-50 border-leamss-orange-300 text-leamss-orange-800',
  it: 'bg-slate-50 border-slate-300 text-slate-800',
  accounts: 'bg-sky-50 border-sky-300 text-sky-800',
  hr: 'bg-leamss-red-50 border-leamss-red-300 text-leamss-red-800',
  operations: 'bg-emerald-50 border-emerald-300 text-emerald-800',
  ai_power_tools: 'bg-leamss-orange-50 border-leamss-orange-400 text-leamss-orange-900',
  manager_elevation: 'bg-leamss-teal-100 border-leamss-teal-500 text-leamss-teal-900',
  admin_elevation: 'bg-leamss-red-100 border-leamss-red-500 text-leamss-red-900',
};
const PACK_SOLID = {
  baseline_employee: 'bg-leamss-teal-600',
  marketing: 'bg-leamss-orange-600',
  it: 'bg-slate-600',
  accounts: 'bg-sky-600',
  hr: 'bg-leamss-red-600',
  operations: 'bg-emerald-600',
  ai_power_tools: 'bg-leamss-orange-700',
  manager_elevation: 'bg-leamss-teal-700',
  admin_elevation: 'bg-leamss-red-700',
};

export default function RoleCapabilityBuilder({ targetUserId, targetUserName, currentUser, onSaved }) {
  const [packs, setPacks] = useState([]);          // catalog of 9 packs
  const [catalog, setCatalog] = useState([]);      // 140 features
  const [byCategory, setByCategory] = useState({});
  const [originalState, setOriginalState] = useState(null);

  const [selectedPacks, setSelectedPacks] = useState(new Set());
  const [overrideGranted, setOverrideGranted] = useState(new Set());
  const [overrideRevoked, setOverrideRevoked] = useState(new Set());

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [showOnlyGranted, setShowOnlyGranted] = useState(false);

  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem('token');
  const auth = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);

  // ─── Bootstrap ───
  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [p, c, eff] = await Promise.all([
        axios.get(`${API}/rbac/packs`, auth),
        axios.get(`${API}/rbac/feature-catalog`, auth),
        axios.get(`${API}/rbac/users/${targetUserId}/effective-capabilities`, auth),
      ]);
      setPacks(p.data);
      setCatalog(c.data.items);
      setByCategory(c.data.by_category);
      setOriginalState(eff.data);
      setSelectedPacks(new Set(eff.data.capability_packs || []));
      setOverrideGranted(new Set(eff.data.feature_overrides?.granted || []));
      setOverrideRevoked(new Set(eff.data.feature_overrides?.revoked || []));
    } catch (err) {
      toast.error('Failed to load RBAC data');
    } finally {
      setLoading(false);
    }
  }, [targetUserId, auth]);

  useEffect(() => { if (targetUserId) loadAll(); }, [targetUserId, loadAll]);

  // ─── Compute effective set live ───
  const effectiveFeatures = useMemo(() => {
    const fromPacks = new Set();
    for (const p of packs) {
      if (selectedPacks.has(p.pack_id)) {
        for (const fid of p.feature_ids || []) fromPacks.add(fid);
      }
    }
    // grant adds, revoke removes
    for (const fid of overrideGranted) fromPacks.add(fid);
    for (const fid of overrideRevoked) fromPacks.delete(fid);
    return fromPacks;
  }, [packs, selectedPacks, overrideGranted, overrideRevoked]);

  const featuresInSelectedPacks = useMemo(() => {
    const s = new Set();
    for (const p of packs) {
      if (selectedPacks.has(p.pack_id)) {
        for (const fid of p.feature_ids || []) s.add(fid);
      }
    }
    return s;
  }, [packs, selectedPacks]);

  const diff = useMemo(() => {
    if (!originalState) return { added: [], removed: [] };
    const origFeatures = new Set(originalState.effective_features || []);
    const newFeatures = effectiveFeatures;
    return {
      added: [...newFeatures].filter(f => !origFeatures.has(f)),
      removed: [...origFeatures].filter(f => !newFeatures.has(f)),
    };
  }, [originalState, effectiveFeatures]);

  // ─── Handlers ───
  const togglePack = (packId) => {
    if (packId === 'baseline_employee') {
      toast.info('Baseline Employee pack cannot be removed (system-protected)');
      return;
    }
    if (packId === 'admin_elevation' && currentUser?.rbac_role !== 'admin_owner') {
      toast.error('Only admin_owner can assign Admin Elevation pack');
      return;
    }
    const newSet = new Set(selectedPacks);
    if (newSet.has(packId)) newSet.delete(packId);
    else newSet.add(packId);
    setSelectedPacks(newSet);
  };

  const toggleFeature = (fid) => {
    const inPack = featuresInSelectedPacks.has(fid);
    const isGranted = overrideGranted.has(fid);
    const isRevoked = overrideRevoked.has(fid);
    const newGranted = new Set(overrideGranted);
    const newRevoked = new Set(overrideRevoked);

    if (inPack) {
      // currently active via pack — toggle means revoke
      if (isRevoked) newRevoked.delete(fid);
      else newRevoked.add(fid);
    } else {
      // not in any pack — toggle means explicit grant
      if (isGranted) newGranted.delete(fid);
      else newGranted.add(fid);
    }
    setOverrideGranted(newGranted);
    setOverrideRevoked(newRevoked);
  };

  const handleReset = () => {
    if (!originalState) return;
    setSelectedPacks(new Set(originalState.capability_packs || []));
    setOverrideGranted(new Set(originalState.feature_overrides?.granted || []));
    setOverrideRevoked(new Set(originalState.feature_overrides?.revoked || []));
    setReason('');
  };

  const handleSave = async () => {
    if (!reason.trim()) {
      toast.error('Reason required');
      return;
    }
    setSaving(true);
    try {
      // First update packs
      await axios.patch(`${API}/rbac/users/${targetUserId}/capability-packs`,
        { packs: [...selectedPacks], reason: reason.trim() }, auth);
      // Then update overrides
      await axios.patch(`${API}/rbac/users/${targetUserId}/feature-overrides`,
        { granted: [...overrideGranted], revoked: [...overrideRevoked], reason: reason.trim() }, auth);
      toast.success('Capabilities saved successfully');
      if (onSaved) onSaved();
      await loadAll();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  // ─── Filtered catalog ───
  const filteredCatalog = useMemo(() => {
    let items = catalog;
    if (categoryFilter !== 'all') items = items.filter(f => f.category === categoryFilter);
    if (search) {
      const q = search.toLowerCase();
      items = items.filter(f =>
        f.feature_id.toLowerCase().includes(q) ||
        f.name.toLowerCase().includes(q) ||
        (f.description || '').toLowerCase().includes(q)
      );
    }
    if (showOnlyGranted) {
      items = items.filter(f => effectiveFeatures.has(f.feature_id));
    }
    // Group again post-filter
    const grouped = {};
    for (const f of items) (grouped[f.category] = grouped[f.category] || []).push(f);
    return grouped;
  }, [catalog, categoryFilter, search, showOnlyGranted, effectiveFeatures]);

  const canSave = !saving && reason.trim().length > 0 && (
    diff.added.length > 0 || diff.removed.length > 0
  );

  if (loading) return <div className="p-6 text-sm text-slate-500" data-testid="rbac-loading">Loading capability data…</div>;

  return (
    <div className="space-y-4" data-testid="role-capability-builder">
      {/* HEADER */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h2 className="text-lg font-bold text-leamss-teal-800 flex items-center gap-2">
            <Sparkles className="h-4 w-4" /> Role & Capability Builder
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Editing capabilities for <span className="font-semibold text-slate-800">{targetUserName || targetUserId}</span>.
            Changes force re-login for target user.
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={handleReset} data-testid="rbac-reset-btn">
            <RotateCcw className="h-3.5 w-3.5 mr-1" /> Reset
          </Button>
        </div>
      </div>

      {/* LAYER 1: PACK TOGGLES */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold mb-3 text-slate-700">Layer 1 — Capability Packs</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2" data-testid="rbac-packs-grid">
          {packs.map(p => {
            const isOn = selectedPacks.has(p.pack_id);
            const isLocked = p.pack_id === 'baseline_employee';
            const isAdminOnly = p.pack_id === 'admin_elevation' && currentUser?.rbac_role !== 'admin_owner';
            return (
              <button
                key={p.pack_id}
                onClick={() => togglePack(p.pack_id)}
                disabled={isLocked || isAdminOnly}
                className={`text-left p-2.5 border-2 rounded-lg transition-all ${
                  isOn ? `${PACK_SOLID[p.pack_id]} text-white border-transparent shadow-md` : `${PACK_ACCENT[p.pack_id] || 'bg-white border-slate-200'} hover:shadow-sm`
                } ${(isLocked || isAdminOnly) ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer'}`}
                data-testid={`rbac-pack-toggle-${p.pack_id}`}
              >
                <div className="flex items-center justify-between gap-1">
                  <div className="font-semibold text-xs flex items-center gap-1">
                    {(isLocked || isAdminOnly) && <Lock className="h-3 w-3" />}
                    {p.name}
                  </div>
                  <Badge className={`text-[9px] ${isOn ? 'bg-white/25 text-white' : 'bg-slate-200 text-slate-700'}`}>
                    {p.feature_count}
                  </Badge>
                </div>
                <p className={`text-[10px] mt-1 ${isOn ? 'text-white/80' : 'text-slate-500'} line-clamp-2`}>
                  {p.description}
                </p>
              </button>
            );
          })}
        </div>
      </Card>

      {/* LAYER 2: FEATURE CATALOG */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
          <h3 className="text-sm font-semibold text-slate-700">Layer 2 — Feature Catalog ({catalog.length})</h3>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
              <Input
                placeholder="search features…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-8 pl-7 text-xs w-44"
                data-testid="rbac-search-input"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="h-8 w-36 text-xs" data-testid="rbac-category-filter">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {Object.keys(byCategory).sort().map(cat => (
                  <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <label className="flex items-center gap-1 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={showOnlyGranted}
                onChange={(e) => setShowOnlyGranted(e.target.checked)}
                data-testid="rbac-show-only-granted"
              />
              Show only granted
            </label>
          </div>
        </div>
        <div className="space-y-3 max-h-[400px] overflow-y-auto" data-testid="rbac-feature-list">
          {Object.entries(filteredCatalog).sort().map(([cat, items]) => (
            <div key={cat}>
              <h4 className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-1.5 sticky top-0 bg-white py-1">
                {cat} <span className="text-slate-400">({items.length})</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {items.map(f => {
                  const inPack = featuresInSelectedPacks.has(f.feature_id);
                  const isGranted = overrideGranted.has(f.feature_id);
                  const isRevoked = overrideRevoked.has(f.feature_id);
                  const isActive = effectiveFeatures.has(f.feature_id);
                  const hasOverride = (inPack && isRevoked) || (!inPack && isGranted);
                  return (
                    <label
                      key={f.feature_id}
                      className={`flex items-start gap-2 p-1.5 rounded border text-xs cursor-pointer transition-all ${
                        isActive ? 'bg-leamss-teal-50 border-leamss-teal-200' : 'bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isActive}
                        onChange={() => toggleFeature(f.feature_id)}
                        className="mt-0.5"
                        data-testid={`rbac-feature-toggle-${f.feature_id}`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1 flex-wrap">
                          <span className="font-medium text-slate-800 truncate">{f.name}</span>
                          {hasOverride && (
                            <Badge className="bg-leamss-orange-100 text-leamss-orange-700 text-[9px] h-4 px-1">override</Badge>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono">{f.feature_id}</span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* LAYER 3: LIVE PREVIEW */}
      <Card className="p-4 bg-slate-50">
        <h3 className="text-sm font-semibold mb-2 text-slate-700">Layer 3 — Live Preview</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <div className="text-slate-500">Effective features</div>
            <div className="text-lg font-bold text-leamss-teal-700" data-testid="rbac-preview-features-count">
              {effectiveFeatures.size}
            </div>
          </div>
          <div>
            <div className="text-slate-500">Packs assigned</div>
            <div className="text-lg font-bold text-sky-700" data-testid="rbac-preview-pack-count">
              {selectedPacks.size}
            </div>
          </div>
          <div>
            <div className="text-slate-500">Will add</div>
            <div className="text-lg font-bold text-emerald-700" data-testid="rbac-preview-added-count">
              +{diff.added.length}
            </div>
          </div>
          <div>
            <div className="text-slate-500">Will remove</div>
            <div className="text-lg font-bold text-leamss-red-700" data-testid="rbac-preview-removed-count">
              −{diff.removed.length}
            </div>
          </div>
        </div>
        {(diff.added.length > 0 || diff.removed.length > 0) && (
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[10px]">
            {diff.added.length > 0 && (
              <div className="bg-emerald-50 border border-emerald-200 rounded p-2">
                <div className="text-emerald-700 font-semibold mb-1 flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Added ({diff.added.length})
                </div>
                <div className="font-mono text-emerald-800 max-h-20 overflow-y-auto">
                  {diff.added.slice(0, 8).map(fid => <div key={fid}>{fid}</div>)}
                  {diff.added.length > 8 && <div className="text-emerald-500">…and {diff.added.length - 8} more</div>}
                </div>
              </div>
            )}
            {diff.removed.length > 0 && (
              <div className="bg-leamss-red-50 border border-leamss-red-200 rounded p-2">
                <div className="text-leamss-red-700 font-semibold mb-1 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" /> Removed ({diff.removed.length})
                </div>
                <div className="font-mono text-leamss-red-800 max-h-20 overflow-y-auto">
                  {diff.removed.slice(0, 8).map(fid => <div key={fid}>{fid}</div>)}
                  {diff.removed.length > 8 && <div className="text-leamss-red-500">…and {diff.removed.length - 8} more</div>}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* LAYER 4: SAVE */}
      <Card className="p-4 border-leamss-teal-300 border-2">
        <h3 className="text-sm font-semibold mb-2 text-slate-700">Layer 4 — Save</h3>
        <Textarea
          placeholder="Reason for change (required) — e.g. 'Promoted to Senior Marketing Lead — granting manager_elevation + marketing-specific overrides'"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="text-xs mb-2"
          rows={2}
          data-testid="rbac-reason-input"
        />
        <div className="flex justify-end gap-2">
          <Button
            onClick={handleSave}
            disabled={!canSave}
            className="bg-leamss-teal-600 hover:bg-leamss-teal-700 text-white"
            data-testid="rbac-save-btn"
          >
            <Save className="h-3.5 w-3.5 mr-1" /> {saving ? 'Saving…' : 'Save Changes'}
          </Button>
        </div>
      </Card>
    </div>
  );
}
