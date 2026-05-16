/**
 * Admin · Express Sales Settings
 *
 * Lets an admin control:
 *   • Global enable / disable of Express Sales
 *   • Default monthly limits per role
 *   • Per-user overrides (custom limit / unlimited / blocked / remove override)
 *   • Min justification chars, auto-approve roles, max value cap
 */
import { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '@/components/ui/dialog';
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from '@/components/ui/select';
import {
  ArrowLeft, Zap, Save, Trash2, Search, Plus, Infinity as InfinityIcon,
  Shield, Users, Settings as SettingsIcon, AlertCircle, CheckCircle2,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLE_LABELS = {
  sales_executive: 'Sales Executive',
  sr_sales_executive: 'Sr. Sales Executive',
  sales_manager: 'Sales Manager',
  sales_head: 'Sales Head',
  admin_owner: 'Admin Owner',
  admin: 'Admin',
  partner: 'External Partner',
};

const LIMIT_PRESETS = [
  { value: 'unlimited', label: 'Unlimited', limit: -1, color: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  { value: 'custom', label: 'Custom Limit', limit: null, color: 'bg-indigo-100 text-indigo-700 border-indigo-300' },
  { value: 'blocked', label: 'Blocked (0)', limit: 0, color: 'bg-rose-100 text-rose-700 border-rose-300' },
];

const limitLabel = (limit) => {
  if (limit === null || limit === undefined || limit === -1) return 'Unlimited';
  if (limit === 0) return 'Blocked';
  return `${limit}/month`;
};

const limitBadgeClass = (limit) => {
  if (limit === null || limit === undefined || limit === -1) return 'bg-emerald-100 text-emerald-700 border-emerald-300';
  if (limit === 0) return 'bg-rose-100 text-rose-700 border-rose-300';
  return 'bg-indigo-100 text-indigo-700 border-indigo-300';
};

// ────────────────────────────────────────────────────────────
// Add / Edit Override Dialog
// ────────────────────────────────────────────────────────────
function OverrideDialog({ open, onClose, initialUser, onSaved }) {
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedUser, setSelectedUser] = useState(initialUser || null);
  const [preset, setPreset] = useState('custom');
  const [customLimit, setCustomLimit] = useState(5);
  const [saving, setSaving] = useState(false);
  const isEdit = !!initialUser;
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    if (open) {
      setSelectedUser(initialUser || null);
      setSearch('');
      setSearchResults([]);
      if (initialUser) {
        if (initialUser.limit === -1 || initialUser.limit === null) setPreset('unlimited');
        else if (initialUser.limit === 0) setPreset('blocked');
        else { setPreset('custom'); setCustomLimit(initialUser.limit || 5); }
      } else {
        setPreset('custom');
        setCustomLimit(5);
      }
    }
  }, [open, initialUser]);

  useEffect(() => {
    if (!open || isEdit) return;
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const { data } = await axios.get(`${API}/express/settings/searchable-users`, {
          headers, params: { q: search || '', limit: 15 },
        });
        setSearchResults(data.items || []);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, open, isEdit]);

  const handleSave = async () => {
    if (!selectedUser) {
      toast.error('Please select a user first');
      return;
    }
    let limitVal = -1;
    if (preset === 'unlimited') limitVal = -1;
    else if (preset === 'blocked') limitVal = 0;
    else {
      const n = Number(customLimit);
      if (!Number.isInteger(n) || n <= 0) {
        toast.error('Custom limit must be a positive integer');
        return;
      }
      limitVal = n;
    }
    setSaving(true);
    try {
      await axios.put(
        `${API}/express/settings/user-limit`,
        { user_id: selectedUser.id || selectedUser.user_id, limit: limitVal },
        { headers },
      );
      toast.success(`Override saved for ${selectedUser.name || selectedUser.email}`);
      onSaved && onSaved();
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to save override');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-lg" data-testid="override-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-indigo-600" />
            {isEdit ? 'Edit Override' : 'Add Per-User Override'}
          </DialogTitle>
          <DialogDescription>
            Per-user overrides win over the role default. Use this for VIP sales, trial accounts,
            or to revoke express access from a single user without changing the role policy.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {!isEdit && (
            <div>
              <Label className="text-xs font-semibold text-slate-600">Select User</Label>
              <div className="relative mt-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search by name or email…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                  data-testid="override-user-search"
                />
              </div>
              <div className="mt-2 border rounded-md max-h-44 overflow-auto bg-white">
                {searching && <div className="text-xs text-slate-400 p-3">Searching…</div>}
                {!searching && searchResults.length === 0 && (
                  <div className="text-xs text-slate-400 p-3">No users found</div>
                )}
                {searchResults.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => setSelectedUser(u)}
                    className={`w-full text-left px-3 py-2 text-sm border-b last:border-b-0 hover:bg-indigo-50 transition ${
                      selectedUser?.id === u.id ? 'bg-indigo-100' : ''
                    }`}
                    data-testid={`override-user-pick-${u.id}`}
                  >
                    <div className="font-medium text-slate-800">{u.name || u.email}</div>
                    <div className="text-xs text-slate-500 flex items-center gap-2">
                      {u.email} ·
                      <Badge variant="outline" className="text-[10px] uppercase">
                        {ROLE_LABELS[u.rbac_role || u.role] || u.role}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {selectedUser && (
            <Card className="p-3 bg-indigo-50/50 border-indigo-200">
              <div className="text-sm font-semibold text-indigo-900">
                {selectedUser.name || selectedUser.email}
              </div>
              <div className="text-xs text-indigo-700">
                {selectedUser.email} · {ROLE_LABELS[selectedUser.rbac_role || selectedUser.role] || selectedUser.role}
                {typeof selectedUser.used_this_month === 'number' && (
                  <> · Used this month: <strong>{selectedUser.used_this_month}</strong></>
                )}
              </div>
            </Card>
          )}

          <div>
            <Label className="text-xs font-semibold text-slate-600">Override Type</Label>
            <div className="grid grid-cols-3 gap-2 mt-1">
              {LIMIT_PRESETS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setPreset(p.value)}
                  className={`px-3 py-2 rounded-md text-xs font-semibold border transition ${
                    preset === p.value ? p.color + ' ring-2 ring-offset-1 ring-indigo-400' : 'bg-white text-slate-600 border-slate-200'
                  }`}
                  data-testid={`override-preset-${p.value}`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {preset === 'custom' && (
            <div>
              <Label className="text-xs font-semibold text-slate-600">Monthly Limit</Label>
              <Input
                type="number"
                min={1}
                value={customLimit}
                onChange={(e) => setCustomLimit(e.target.value)}
                className="mt-1"
                data-testid="override-custom-limit"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Max number of express sales this user can create per calendar month.
              </p>
            </div>
          )}

          {preset === 'blocked' && (
            <div className="flex items-start gap-2 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-md p-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>This user will be unable to create any new Express Sales until you remove this block.</span>
            </div>
          )}

          {preset === 'unlimited' && (
            <div className="flex items-start gap-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md p-2">
              <InfinityIcon className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>No monthly cap will be enforced for this user.</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving} data-testid="override-cancel">
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !selectedUser}
            data-testid="override-save"
            className="bg-indigo-600 hover:bg-indigo-700"
          >
            <Save className="h-4 w-4 mr-1.5" />
            {saving ? 'Saving…' : 'Save Override'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ────────────────────────────────────────────────────────────
// Main Page
// ────────────────────────────────────────────────────────────
export default function ExpressSalesSettings() {
  const navigate = useNavigate();
  const [settings, setSettings] = useState(null);
  const [overrides, setOverrides] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingFlag, setSavingFlag] = useState(false);
  const [roleEdits, setRoleEdits] = useState({});
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingOverride, setEditingOverride] = useState(null);
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, o] = await Promise.all([
        axios.get(`${API}/express/settings`, { headers }),
        axios.get(`${API}/express/settings/user-overrides`, { headers }),
      ]);
      setSettings(s.data);
      setRoleEdits(s.data.express_monthly_limits || {});
      setOverrides(o.data.items || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  const handleToggleEnabled = async (next) => {
    setSavingFlag(true);
    try {
      await axios.patch(`${API}/express/settings`, { express_sale_enabled: next }, { headers });
      toast.success(next ? 'Express Sales enabled' : 'Express Sales disabled');
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to update');
    } finally {
      setSavingFlag(false);
    }
  };

  const handleRoleSave = async () => {
    setSavingFlag(true);
    try {
      // Convert empty string → null (unlimited)
      const cleaned = {};
      for (const [role, val] of Object.entries(roleEdits)) {
        if (val === '' || val === null || val === undefined) cleaned[role] = null;
        else cleaned[role] = parseInt(val, 10);
      }
      await axios.patch(`${API}/express/settings`, { express_monthly_limits: cleaned }, { headers });
      toast.success('Role default limits saved');
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to save');
    } finally {
      setSavingFlag(false);
    }
  };

  const handleRemoveOverride = async (userId, userName) => {
    if (!window.confirm(`Remove override for ${userName}? They will fall back to the role default limit.`)) return;
    try {
      await axios.put(
        `${API}/express/settings/user-limit`,
        { user_id: userId, limit: null },
        { headers },
      );
      toast.success('Override removed');
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to remove');
    }
  };

  if (loading || !settings) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="text-slate-400 text-sm">Loading Express Sales settings…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="express-settings-page">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/admin')}
              data-testid="back-btn"
            >
              <ArrowLeft className="h-4 w-4 mr-1" /> Back
            </Button>
            <div>
              <h1 className="text-2xl font-semibold flex items-center gap-2">
                <Zap className="h-7 w-7 text-amber-500" /> Express Sales Settings
              </h1>
              <p className="text-sm text-slate-500">
                Why limits exist: prevents abuse of the "skip-pre-assessment-fee" flow.
                Customise per role or per individual user below.
              </p>
            </div>
          </div>
        </div>

        {/* Global toggle */}
        <Card className="p-5 border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                <SettingsIcon className="h-4 w-4 text-amber-600" />
                Global Express Sales Switch
              </div>
              <div className="text-xs text-slate-500 mt-1 max-w-xl">
                When OFF: every user (including admins) will be blocked from creating Express Sales,
                regardless of role limits or per-user overrides.
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={settings.express_sale_enabled
                ? 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                : 'bg-rose-100 text-rose-700 border border-rose-300'}>
                {settings.express_sale_enabled ? 'ENABLED' : 'DISABLED'}
              </Badge>
              <Switch
                checked={!!settings.express_sale_enabled}
                onCheckedChange={handleToggleEnabled}
                disabled={savingFlag}
                data-testid="global-toggle"
              />
            </div>
          </div>
        </Card>

        <Tabs defaultValue="overrides" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overrides" data-testid="tab-overrides">
              <Users className="h-4 w-4 mr-1.5" /> Per-User Overrides ({overrides.length})
            </TabsTrigger>
            <TabsTrigger value="roles" data-testid="tab-roles">
              <Shield className="h-4 w-4 mr-1.5" /> Role Defaults
            </TabsTrigger>
          </TabsList>

          {/* Per-user overrides */}
          <TabsContent value="overrides">
            <Card className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-sm font-semibold text-slate-800">Custom limits per individual user</div>
                  <div className="text-xs text-slate-500">
                    Overrides win over the role default. Useful for VIP sales, trial accounts,
                    or to revoke express access from one user without changing the role policy.
                  </div>
                </div>
                <Button
                  size="sm"
                  onClick={() => { setEditingOverride(null); setDialogOpen(true); }}
                  className="bg-indigo-600 hover:bg-indigo-700"
                  data-testid="add-override-btn"
                >
                  <Plus className="h-4 w-4 mr-1" /> Add Override
                </Button>
              </div>

              {overrides.length === 0 ? (
                <div className="text-center py-10 text-slate-400 text-sm border-2 border-dashed border-slate-200 rounded-lg">
                  No per-user overrides yet. Click "Add Override" to grant unlimited access,
                  set a custom limit, or block a specific user.
                </div>
              ) : (
                <div className="border rounded-md overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-100 text-slate-700">
                      <tr>
                        <th className="text-left px-3 py-2 font-semibold">User</th>
                        <th className="text-left px-3 py-2 font-semibold">Role</th>
                        <th className="text-left px-3 py-2 font-semibold">Override</th>
                        <th className="text-left px-3 py-2 font-semibold">Used (This Month)</th>
                        <th className="text-right px-3 py-2 font-semibold">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overrides.map((o) => (
                        <tr key={o.user_id} className="border-t" data-testid={`override-row-${o.user_id}`}>
                          <td className="px-3 py-2">
                            <div className="font-medium text-slate-800">{o.name || '—'}</div>
                            <div className="text-xs text-slate-500">{o.email}</div>
                          </td>
                          <td className="px-3 py-2">
                            <Badge variant="outline" className="text-[10px] uppercase">
                              {ROLE_LABELS[o.rbac_role || o.role] || o.role}
                            </Badge>
                          </td>
                          <td className="px-3 py-2">
                            <Badge className={`${limitBadgeClass(o.limit)} border`}>
                              {limitLabel(o.limit)}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-slate-700">{o.used_this_month}</td>
                          <td className="px-3 py-2 text-right space-x-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => { setEditingOverride(o); setDialogOpen(true); }}
                              data-testid={`edit-override-${o.user_id}`}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRemoveOverride(o.user_id, o.name || o.email)}
                              className="text-rose-600 border-rose-200 hover:bg-rose-50"
                              data-testid={`remove-override-${o.user_id}`}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </TabsContent>

          {/* Role defaults */}
          <TabsContent value="roles">
            <Card className="p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-sm font-semibold text-slate-800">Default monthly limits per role</div>
                  <div className="text-xs text-slate-500">
                    Leave blank for <strong>unlimited</strong>. Per-user overrides above always win over these defaults.
                  </div>
                </div>
                <Button
                  size="sm"
                  onClick={handleRoleSave}
                  disabled={savingFlag}
                  className="bg-emerald-600 hover:bg-emerald-700"
                  data-testid="save-role-limits"
                >
                  <Save className="h-4 w-4 mr-1" /> {savingFlag ? 'Saving…' : 'Save Role Limits'}
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.keys(ROLE_LABELS).map((role) => (
                  <Card key={role} className="p-3 flex items-center gap-3" data-testid={`role-card-${role}`}>
                    <div className="flex-1">
                      <div className="text-sm font-medium text-slate-800">{ROLE_LABELS[role]}</div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-wide">{role}</div>
                    </div>
                    <Input
                      type="number"
                      min={0}
                      placeholder="Unlimited"
                      value={roleEdits[role] ?? ''}
                      onChange={(e) => setRoleEdits({ ...roleEdits, [role]: e.target.value === '' ? null : e.target.value })}
                      className="w-28"
                      data-testid={`role-input-${role}`}
                    />
                    <Badge className={limitBadgeClass(roleEdits[role] === '' || roleEdits[role] === null ? -1 : Number(roleEdits[role]))}>
                      {roleEdits[role] === '' || roleEdits[role] === null || roleEdits[role] === undefined
                        ? 'Unlimited'
                        : roleEdits[role] === '0' || roleEdits[role] === 0
                          ? 'Blocked'
                          : `${roleEdits[role]}/mo`}
                    </Badge>
                  </Card>
                ))}
              </div>

              <div className="mt-4 flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div>
                  <strong>Why limits exist:</strong> Express Sales bypass the standard ₹5,100 pre-assessment fee,
                  so we cap how many a single salesperson can issue per month. Use overrides above for trusted
                  staff who need unlimited access.
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="text-[11px] text-slate-400 text-right">
          Last updated: {settings.updated_at ? new Date(settings.updated_at).toLocaleString('en-IN') : '—'}
        </div>
      </div>

      <OverrideDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        initialUser={editingOverride}
        onSaved={() => { setDialogOpen(false); load(); }}
      />
    </div>
  );
}
