/**
 * Phase 22 — Admin RBAC Hub
 * Standalone admin page to manage capability packs / overrides per user.
 * Takes ?user_id=… query OR shows a user picker.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, ShieldCheck, ArrowLeft } from 'lucide-react';
import DashboardShell from '@/components/DashboardShell';
import RoleCapabilityBuilder from '@/components/admin/RoleCapabilityBuilder';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminRbacHub() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const userId = params.get('user_id');
  const [me, setMe] = useState(null);
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');
  const [pickedName, setPickedName] = useState('');
  const [auditLog, setAuditLog] = useState([]);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const loadMe = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/auth/me`, auth);
      setMe(data);
    } catch (err) { navigate('/'); }
  }, [navigate]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadUsers = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/employees?limit=100`, auth);
      setUsers(Array.isArray(data) ? data : data?.items || []);
    } catch { setUsers([]); }
    finally { setLoading(false); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const loadAuditFor = useCallback(async (uid) => {
    try {
      const { data } = await axios.get(`${API}/rbac/audit-log?target_user_id=${uid}&limit=10`, auth);
      setAuditLog(data?.items || []);
    } catch { setAuditLog([]); }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (!token) { navigate('/'); return; } loadMe(); loadUsers(); }, [token, navigate, loadMe, loadUsers]);
  useEffect(() => {
    if (userId) {
      const u = users.find(x => (x.id || x.user_id) === userId);
      setPickedName(u?.name || u?.email || userId);
      loadAuditFor(userId);
    } else { setPickedName(''); setAuditLog([]); }
  }, [userId, users, loadAuditFor]);

  const filtered = users.filter(u => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (u.name || '').toLowerCase().includes(q) ||
           (u.email || '').toLowerCase().includes(q) ||
           (u.department || '').toLowerCase().includes(q);
  });

  if (!me) return null;

  return (
    <DashboardShell user={me} onLogout={() => { localStorage.removeItem('token'); navigate('/'); }} pageTitle="RBAC v2 Hub">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-5 space-y-4" data-testid="admin-rbac-hub">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h1 className="text-xl font-bold text-leamss-teal-800 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" /> RBAC v2 — Capability Builder
          </h1>
          <Badge className="bg-leamss-orange-100 text-leamss-orange-700 border border-leamss-orange-200">
            Phase 22 · 9 packs · 140 features
          </Badge>
        </div>

        {!userId && (
          <Card className="p-4">
            <h3 className="text-sm font-semibold mb-2">Step 1 — Pick a user to manage</h3>
            <div className="relative mb-3 max-w-md">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search name / email / dept…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
                data-testid="rbac-user-search"
              />
            </div>
            {loading ? <p className="text-sm text-slate-500">Loading users…</p> : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-[500px] overflow-y-auto">
                {filtered.slice(0, 60).map((u, i) => (
                  <button
                    key={u.id || u.user_id || i}
                    onClick={() => setParams({ user_id: u.id || u.user_id })}
                    className="text-left p-2 border border-slate-200 rounded hover:border-leamss-teal-400 hover:bg-leamss-teal-50/50 transition-all"
                    data-testid={`rbac-pick-user-${u.id || u.user_id}`}
                  >
                    <div className="font-semibold text-sm text-slate-800">{u.name || u.email}</div>
                    <div className="text-xs text-slate-500">{u.email}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {u.department || '—'} · {u.rbac_role || u.role || 'no-role'} ·
                      {' '}{(u.capability_packs?.length || 0)} packs
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>
        )}

        {userId && (
          <>
            <Button variant="ghost" size="sm" onClick={() => setParams({})} data-testid="rbac-back-to-picker">
              <ArrowLeft className="h-4 w-4 mr-1" /> Back to user picker
            </Button>
            <RoleCapabilityBuilder
              targetUserId={userId}
              targetUserName={pickedName}
              currentUser={me}
              onSaved={() => loadAuditFor(userId)}
            />
            {auditLog.length > 0 && (
              <Card className="p-4" data-testid="rbac-audit-section">
                <h3 className="text-sm font-semibold mb-2 text-slate-700">Recent Audit Log (last 10)</h3>
                <div className="space-y-1.5 max-h-60 overflow-y-auto">
                  {auditLog.map((e) => (
                    <div key={e.id} className="text-xs border-l-2 border-leamss-teal-300 pl-2 py-1">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span className="font-semibold text-slate-800">{e.action}</span>
                        <span className="text-[10px] text-slate-400">{new Date(e.timestamp).toLocaleString()}</span>
                      </div>
                      <div className="text-slate-600 mt-0.5">by <span className="font-medium">{e.actor_name}</span> — {e.reason}</div>
                      {e.diff?.added_packs?.length > 0 && <div className="text-emerald-700">+ packs: {e.diff.added_packs.join(', ')}</div>}
                      {e.diff?.removed_packs?.length > 0 && <div className="text-leamss-red-700">− packs: {e.diff.removed_packs.join(', ')}</div>}
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </DashboardShell>
  );
}
