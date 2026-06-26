import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { User, Shield, Activity, Edit, X, UserCheck, UserX, KeyRound, ArrowRight, Eye, History, Mail, Link2, Copy } from 'lucide-react';
import DashboardPreviewModal from './DashboardPreviewModal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TABS = [
  { key: 'profile', label: 'Profile', icon: User },
  { key: 'role', label: 'Role & Permissions', icon: Shield },
  { key: 'history', label: 'Role History', icon: History },
  { key: 'activity', label: 'Activity', icon: Activity },
];

export default function EmployeeDetailModal({ employeeId, onClose, onUpdated }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [activity, setActivity] = useState([]);
  const [roles, setRoles] = useState([]);
  const [activeTab, setActiveTab] = useState('profile');
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [roleChange, setRoleChange] = useState({ open: false, new_role: '', new_designation: '', effective_date: '', reason: '' });
  const [resetPwdDialog, setResetPwdDialog] = useState({ open: false, delivery: 'show_once', reason: '' });
  const [resetPwdResult, setResetPwdResult] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const token = localStorage.getItem('token');

  // Permission check helpers — same logic as backend
  const myPerms = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}').permissions || []; }
    catch { return []; }
  }, []);
  const canManage = myPerms.includes('*') ||
    myPerms.includes('user.update.any') ||
    myPerms.includes('employee.update.all') ||
    myPerms.includes('employee.terminate.any') ||
    myPerms.includes('system.update.any');

  const load = async () => {
    try {
      const [u, h, a, r] = await Promise.all([
        axios.get(`${API}/employees/${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees/${employeeId}/history`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees/${employeeId}/activity?limit=30`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/departments/_meta/roles`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      setUser(u.data);
      setHistory(h.data);
      setActivity(a.data);
      setRoles(r.data);
      setEditForm({
        name: u.data.name || '',
        mobile: u.data.mobile || '',
        designation: u.data.designation || '',
        work_location: u.data.work_location || '',
        work_mode: u.data.work_mode || 'onsite',
      });
    } catch (err) {
      console.error(err);
      toast.error('Failed to load employee');
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [employeeId]);

  const saveProfile = async () => {
    try {
      await axios.patch(`${API}/employees/${employeeId}`, editForm, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Profile updated');
      setEditing(false);
      load();
      onUpdated && onUpdated();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Update failed';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  const changeRole = async () => {
    if (!roleChange.new_role) return toast.error('Pick a role');
    if (!roleChange.reason || roleChange.reason.trim().length < 20) return toast.error('Reason must be at least 20 characters');
    try {
      const body = {
        new_role: roleChange.new_role,
        reason: roleChange.reason,
      };
      if (roleChange.new_designation) body.new_designation = roleChange.new_designation;
      if (roleChange.effective_date) body.effective_date = new Date(roleChange.effective_date).toISOString();
      await axios.patch(`${API}/employees/${employeeId}/role`, body,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Role changed to ${roleChange.new_role}`);
      setRoleChange({ open: false, new_role: '', new_designation: '', effective_date: '', reason: '' });
      load();
      onUpdated && onUpdated();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Role change failed';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  const toggleActive = async () => {
    const active = user.employment_status === 'active';
    try {
      const url = `${API}/employees/${employeeId}/${active ? 'deactivate' : 'reactivate'}`;
      await axios.post(url, null, { headers: { Authorization: `Bearer ${token}` } });
      toast.success(active ? 'Employee deactivated' : 'Employee reactivated');
      load();
      onUpdated && onUpdated();
    } catch (err) {
      toast.error('Action failed');
    }
  };

  const resetPwd = async () => {
    if (!resetPwdDialog.reason || resetPwdDialog.reason.trim().length < 10) {
      toast.error('Reason must be at least 10 characters');
      return;
    }
    try {
      const res = await axios.post(`${API}/admin/users/${employeeId}/reset-password`, {
        delivery: resetPwdDialog.delivery,
        reason: resetPwdDialog.reason,
      }, { headers: { Authorization: `Bearer ${token}` } });
      setResetPwdDialog({ open: false, delivery: 'show_once', reason: '' });
      setResetPwdResult(res.data);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Password reset failed';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  const copyText = (txt) => { navigator.clipboard.writeText(txt); toast.success('Copied!'); };

  if (!user) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent className="max-w-3xl"><div className="p-6">Loading...</div></DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto p-0" data-testid="employee-detail-modal">
        {/* Header */}
        <div className="p-6 border-b border-slate-100 bg-gradient-to-r from-teal-50 via-leamss-teal-50 to-leamss-red-50">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-teal-500 to-leamss-teal-600 flex items-center justify-center text-white font-bold text-xl shadow-md">
              {(user.name || '?').charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <h2 className="text-2xl font-bold text-slate-900">{user.name}</h2>
                <Badge variant="outline" className="font-mono text-xs">{user.employee_id || '—'}</Badge>
                <Badge className={user.employment_status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}>{user.employment_status || 'active'}</Badge>
              </div>
              <p className="text-slate-600 text-sm mt-1">{user.designation || user.rbac_role} · {user.department || 'No dept'}</p>
              <p className="text-slate-500 text-xs mt-0.5">{user.email} · {user.mobile || 'No mobile'}</p>
            </div>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" onClick={() => setShowPreview(true)} className="text-amber-600 border-amber-200" data-testid="view-dashboard-btn">
                <Eye className="h-3.5 w-3.5 mr-1" /> View Dashboard
              </Button>
              {canManage && (
                <>
                  <Button variant="outline" size="sm" onClick={() => setResetPwdDialog({ open: true, delivery: 'show_once', reason: '' })} data-testid="reset-pwd-btn"><KeyRound className="h-3.5 w-3.5 mr-1" /> Reset Pwd</Button>
                  <Button variant="outline" size="sm" onClick={toggleActive} className={user.employment_status === 'active' ? 'text-rose-600 border-rose-200' : 'text-emerald-600 border-emerald-200'} data-testid="toggle-active-btn">
                    {user.employment_status === 'active' ? <><UserX className="h-3.5 w-3.5 mr-1" /> Deactivate</> : <><UserCheck className="h-3.5 w-3.5 mr-1" /> Reactivate</>}
                  </Button>
                </>
              )}
              <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-md"><X className="h-4 w-4" /></button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mt-5 border-b -mb-6">
            {TABS.map(t => {
              const Icon = t.icon;
              return (
                <button key={t.key} onClick={() => setActiveTab(t.key)} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${activeTab === t.key ? 'border-teal-700 text-teal-700' : 'border-transparent text-slate-500 hover:text-slate-700'}`} data-testid={`tab-${t.key}`}>
                  <Icon className="h-3.5 w-3.5" /> {t.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'profile' && (
            <div className="space-y-4" data-testid="profile-tab">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Profile Details</h3>
                {!editing ? (
                  <Button size="sm" variant="outline" onClick={() => setEditing(true)} disabled={!canManage} title={!canManage ? "Admin only" : ""} data-testid="edit-profile-btn"><Edit className="h-3.5 w-3.5 mr-1" /> Edit</Button>
                ) : (
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setEditing(false)} data-testid="cancel-edit">Cancel</Button>
                    <Button size="sm" onClick={saveProfile} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="save-profile">Save</Button>
                  </div>
                )}
              </div>

              {editing ? (
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>Name</Label><Input value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} data-testid="edit-name" /></div>
                  <div><Label>Mobile</Label><Input value={editForm.mobile} onChange={e => setEditForm({...editForm, mobile: e.target.value})} data-testid="edit-mobile" /></div>
                  <div><Label>Designation</Label><Input value={editForm.designation} onChange={e => setEditForm({...editForm, designation: e.target.value})} data-testid="edit-designation" /></div>
                  <div><Label>Work Location</Label><Input value={editForm.work_location} onChange={e => setEditForm({...editForm, work_location: e.target.value})} data-testid="edit-location" /></div>
                  <div className="col-span-2"><Label>Work Mode</Label>
                    <Select value={editForm.work_mode} onValueChange={v => setEditForm({...editForm, work_mode: v})}>
                      <SelectTrigger data-testid="edit-work-mode"><SelectValue /></SelectTrigger>
                      <SelectContent>{['onsite', 'remote', 'hybrid'].map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  {[
                    ['Employee ID', user.employee_id],
                    ['Designation', user.designation || '—'],
                    ['Department', user.department],
                    ['Date of Joining', user.date_of_joining ? new Date(user.date_of_joining).toLocaleDateString() : '—'],
                    ['Employment Type', user.employment_type || '—'],
                    ['Work Mode', user.work_mode || '—'],
                    ['Work Location', user.work_location || '—'],
                    ['Reports To', user.manager?.name || '—'],
                    ['2FA Enabled', user.two_fa_enabled ? 'Yes' : 'No'],
                    ['User Type', user.user_type],
                  ].map(([k, v]) => (
                    <div key={k} className="border-b border-slate-100 pb-2">
                      <p className="text-xs text-slate-500 uppercase tracking-wider">{k}</p>
                      <p className="font-medium text-slate-800 mt-0.5">{v}</p>
                    </div>
                  ))}
                </div>
              )}

              {user.direct_reports && user.direct_reports.length > 0 && (
                <Card className="p-4 mt-4 bg-slate-50">
                  <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-3">Direct Reports ({user.direct_reports.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {user.direct_reports.map(r => (
                      <div key={r.id} className="flex items-center gap-2 bg-white px-2 py-1.5 rounded border border-slate-200 text-xs">
                        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-teal-500 to-leamss-teal-600 flex items-center justify-center text-white text-[10px] font-semibold">{(r.name || '?').charAt(0)}</div>
                        <span className="font-medium">{r.name}</span>
                        <span className="text-slate-400">· {r.rbac_role}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}

          {activeTab === 'role' && (
            <div className="space-y-4" data-testid="role-tab">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Role & Permissions</h3>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => { onClose(); navigate(`/admin/rbac?user_id=${user.id}`); }}
                  data-testid="change-role-btn"
                  className="border-leamss-teal-400 text-leamss-teal-700 hover:bg-leamss-teal-50"
                >
                  Manage Roles & Capabilities <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </div>

              <Card className="p-4 bg-teal-50 border-teal-200">
                <p className="text-xs uppercase tracking-wider text-teal-700 font-semibold">Current Role</p>
                <p className="text-lg font-bold text-teal-900 mt-1">{user.rbac_role}</p>
                <p className="text-xs text-teal-600 mt-1">{user.permissions?.length || 0} permissions · {user.ui_modules?.length || 0} UI modules</p>
              </Card>

              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Permissions ({user.permissions?.length || 0})</p>
                <div className="flex flex-wrap gap-1.5 max-h-64 overflow-y-auto p-2 bg-slate-50 rounded-md">
                  {(user.permissions || []).map(p => (
                    <Badge key={p} variant="outline" className="font-mono text-[10px]">{p}</Badge>
                  ))}
                  {(!user.permissions || user.permissions.length === 0) && <p className="text-slate-400 text-xs italic">No permissions</p>}
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">UI Modules ({user.ui_modules?.length || 0})</p>
                <div className="flex flex-wrap gap-1.5 p-2 bg-slate-50 rounded-md">
                  {(user.ui_modules || []).map(m => (
                    <Badge key={m} className="bg-leamss-teal-100 text-leamss-teal-700 text-[10px]">{m}</Badge>
                  ))}
                </div>
              </div>

              {history.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Role Change History</p>
                  <div className="space-y-2">
                    {history.map(h => (
                      <Card key={h.id} className="p-3 text-xs">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-slate-500">{h.changed_from || '—'}</span>
                          <ArrowRight className="h-3 w-3 text-slate-400" />
                          <span className="font-semibold text-slate-800">{h.changed_to}</span>
                          <span className="text-slate-400 ml-auto">{new Date(h.effective_date).toLocaleString()}</span>
                        </div>
                        {h.reason && <p className="text-slate-500 mt-1 italic">"{h.reason}"</p>}
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'history' && (
            <div className="space-y-3" data-testid="role-history-tab">
              <h3 className="text-lg font-semibold flex items-center gap-2"><History className="h-4 w-4 text-teal-700" /> Role Change History ({history.length})</h3>
              {history.length === 0 ? (
                <Card className="p-8 text-center text-slate-400 text-sm italic">
                  <History className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                  No role changes yet
                </Card>
              ) : (
                <div className="relative pl-6 space-y-3 before:absolute before:left-2 before:top-0 before:bottom-0 before:w-px before:bg-slate-200">
                  {history.map((h) => (
                    <div key={h.id} className="relative" data-testid={`history-entry-${h.id}`}>
                      <div className="absolute -left-5 top-3 w-3 h-3 rounded-full bg-teal-600 border-2 border-white" />
                      <Card className="p-4">
                        <div className="flex items-start justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="outline" className="text-xs">{h.changed_from || 'initial'}</Badge>
                            <ArrowRight className="h-3 w-3 text-slate-400" />
                            <Badge className="bg-teal-100 text-teal-700 text-xs">{h.changed_to}</Badge>
                          </div>
                          <span className="text-xs text-slate-400">{new Date(h.effective_date).toLocaleDateString()}</span>
                        </div>
                        {h.changed_to_detail && (
                          <div className="mt-2 text-xs text-slate-600 space-x-3">
                            <span>Dept: <strong>{h.changed_to_detail.department}</strong></span>
                            <span>Designation: <strong>{h.changed_to_detail.designation}</strong></span>
                          </div>
                        )}
                        {h.reason && <p className="text-xs text-slate-500 mt-2 italic">"{h.reason}"</p>}
                        <p className="text-[10px] text-slate-400 mt-2">Changed by {h.changed_by_name || h.changed_by?.slice(0, 8)} · {new Date(h.created_at).toLocaleString()}</p>
                      </Card>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'activity' && (
            <div className="space-y-2" data-testid="activity-tab">
              <h3 className="text-lg font-semibold mb-2">Recent Activity ({activity.length})</h3>
              {activity.length === 0 ? (
                <p className="text-slate-500 text-sm italic">No activity recorded</p>
              ) : activity.map(a => (
                <Card key={a.id} className="p-3 text-xs">
                  <div className="flex items-start gap-2">
                    <Activity className="h-3.5 w-3.5 text-slate-400 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-medium text-slate-800">{a.action}</p>
                      <p className="text-slate-500">{a.entity_type} · {a.entity_id?.slice(0, 8)}</p>
                    </div>
                    <span className="text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Change Role Dialog */}
        <Dialog open={roleChange.open} onOpenChange={(v) => !v && setRoleChange({ open: false, new_role: '', new_designation: '', effective_date: '', reason: '' })}>
          <DialogContent>
            <DialogHeader><DialogTitle>Change Role</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Card className="p-3 bg-slate-50 text-xs">
                <p className="text-slate-500 uppercase tracking-wider font-semibold">Current Role</p>
                <p className="font-bold text-slate-900 mt-1">{user.designation || user.rbac_role}</p>
                <p className="text-slate-500">{user.department} · {user.permissions?.length || 0} permissions</p>
              </Card>
              <div>
                <Label>New Role *</Label>
                <Select value={roleChange.new_role} onValueChange={(v) => {
                  const selected = roles.find(r => r.key === v);
                  setRoleChange({ ...roleChange, new_role: v, new_designation: selected?.name || '' });
                }}>
                  <SelectTrigger data-testid="new-role-select"><SelectValue placeholder="Select new role..." /></SelectTrigger>
                  <SelectContent>{roles.map(r => <SelectItem key={r.key} value={r.key}>{r.name} · {r.department}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              {roleChange.new_role && (
                <Card className="p-3 bg-teal-50 border-teal-200 text-xs">
                  <p className="font-semibold text-teal-900">Summary of change:</p>
                  <div className="mt-2 space-y-1 text-teal-800">
                    <p>Role: <strong>{user.rbac_role}</strong> → <strong>{roleChange.new_role}</strong></p>
                    {(() => {
                      const newRole = roles.find(r => r.key === roleChange.new_role);
                      return (
                        <>
                          <p>Permissions: <strong>{user.permissions?.length || 0}</strong> → <strong>{newRole?.permissions?.length || 0}</strong></p>
                          {newRole?.department !== user.department && <p>Department: <strong>{user.department}</strong> → <strong>{newRole?.department}</strong></p>}
                          <p className="italic text-teal-700 pt-1">⚠️ Reports To may be reset if old manager invalid for new role</p>
                        </>
                      );
                    })()}
                  </div>
                </Card>
              )}
              <div>
                <Label>New Designation</Label>
                <Input value={roleChange.new_designation} onChange={e => setRoleChange({ ...roleChange, new_designation: e.target.value })} placeholder="Auto-filled from role" data-testid="role-change-designation" />
              </div>
              <div>
                <Label>Effective Date</Label>
                <Input type="date" value={roleChange.effective_date} onChange={e => setRoleChange({ ...roleChange, effective_date: e.target.value })} data-testid="role-change-effective" />
              </div>
              <div>
                <Label>Reason * (min 20 chars)</Label>
                <Textarea rows={3} value={roleChange.reason} onChange={e => setRoleChange({ ...roleChange, reason: e.target.value })} placeholder="e.g. Promoted to Sales Manager after exceeding Q1 targets by 150%" data-testid="role-change-reason" />
                <p className="text-xs text-slate-400 mt-1">{roleChange.reason.length}/20 chars minimum</p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRoleChange({ open: false, new_role: '', new_designation: '', effective_date: '', reason: '' })}>Cancel</Button>
              <Button onClick={changeRole} disabled={!roleChange.new_role || roleChange.reason.length < 20} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="confirm-role-change">Confirm Change</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Enhanced Reset Password Dialog */}
        <Dialog open={resetPwdDialog.open} onOpenChange={(v) => !v && setResetPwdDialog({ open: false, delivery: 'show_once', reason: '' })}>
          <DialogContent data-testid="reset-pwd-dialog">
            <DialogHeader><DialogTitle>Reset User Password</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Card className="p-3 bg-rose-50 border-rose-200 text-xs text-rose-800">
                ⚠️ This will invalidate the user's current password. They'll be forced to change it on next login.
              </Card>
              <div>
                <Label>Delivery Method *</Label>
                <div className="grid grid-cols-3 gap-2 mt-1">
                  <button
                    type="button"
                    onClick={() => setResetPwdDialog({ ...resetPwdDialog, delivery: 'show_once' })}
                    className={`p-2 border rounded text-xs flex flex-col items-center gap-1 ${resetPwdDialog.delivery === 'show_once' ? 'border-teal-700 bg-teal-50 text-teal-900' : 'border-slate-200'}`}
                    data-testid="delivery-show-once"
                  >
                    <Eye className="h-4 w-4" />
                    Show Once
                  </button>
                  <button
                    type="button"
                    onClick={() => setResetPwdDialog({ ...resetPwdDialog, delivery: 'email' })}
                    className={`p-2 border rounded text-xs flex flex-col items-center gap-1 ${resetPwdDialog.delivery === 'email' ? 'border-teal-700 bg-teal-50 text-teal-900' : 'border-slate-200'}`}
                    data-testid="delivery-email"
                  >
                    <Mail className="h-4 w-4" />
                    Email (mocked)
                  </button>
                  <button
                    type="button"
                    onClick={() => setResetPwdDialog({ ...resetPwdDialog, delivery: 'magic_link' })}
                    className={`p-2 border rounded text-xs flex flex-col items-center gap-1 ${resetPwdDialog.delivery === 'magic_link' ? 'border-teal-700 bg-teal-50 text-teal-900' : 'border-slate-200'}`}
                    data-testid="delivery-magic-link"
                  >
                    <Link2 className="h-4 w-4" />
                    Magic Link (72h)
                  </button>
                </div>
              </div>
              <div>
                <Label>Reason * (min 10 chars)</Label>
                <Textarea rows={2} value={resetPwdDialog.reason} onChange={(e) => setResetPwdDialog({ ...resetPwdDialog, reason: e.target.value })} placeholder="e.g. User forgot password" data-testid="reset-pwd-reason" />
                <p className="text-xs text-slate-400 mt-1">{resetPwdDialog.reason.length}/10 chars minimum</p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setResetPwdDialog({ open: false, delivery: 'show_once', reason: '' })}>Cancel</Button>
              <Button onClick={resetPwd} disabled={resetPwdDialog.reason.length < 10} className="bg-rose-600 hover:bg-rose-700 text-white" data-testid="confirm-reset-pwd">Confirm Reset</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Reset Pwd Result */}
        <Dialog open={!!resetPwdResult} onOpenChange={() => setResetPwdResult(null)}>
          <DialogContent data-testid="reset-pwd-result-dialog">
            <DialogHeader><DialogTitle>Password Reset Complete</DialogTitle></DialogHeader>
            {resetPwdResult?.temporary_password && (
              <Card className="p-4 bg-amber-50 border-amber-200">
                <p className="text-xs uppercase text-amber-700 font-semibold">Temporary Password (show ONCE)</p>
                <div className="flex items-center gap-2 mt-2">
                  <code className="block bg-white px-3 py-2 rounded font-mono text-sm select-all flex-1" data-testid="reset-pwd-result">{resetPwdResult.temporary_password}</code>
                  <Button size="sm" variant="outline" onClick={() => copyText(resetPwdResult.temporary_password)}><Copy className="h-3.5 w-3.5" /></Button>
                </div>
                <p className="text-xs text-amber-700 mt-2">User must change this on first login.</p>
              </Card>
            )}
            {resetPwdResult?.reset_url && (
              <Card className="p-4 bg-blue-50 border-blue-200">
                <p className="text-xs uppercase text-blue-700 font-semibold">Magic Link (72h expiry)</p>
                <div className="flex items-center gap-2 mt-2">
                  <code className="block bg-white px-3 py-2 rounded font-mono text-[10px] select-all flex-1 truncate" data-testid="reset-pwd-magic-link">{window.location.origin + resetPwdResult.reset_url}</code>
                  <Button size="sm" variant="outline" onClick={() => copyText(window.location.origin + resetPwdResult.reset_url)}><Copy className="h-3.5 w-3.5" /></Button>
                </div>
              </Card>
            )}
            {resetPwdResult?.email_sent && (
              <Card className="p-3 bg-slate-100 text-xs text-slate-600">
                📨 Email queued (MOCKED — Resend not live). Above password is shown for visibility.
              </Card>
            )}
            <DialogFooter><Button onClick={() => setResetPwdResult(null)}>Got it</Button></DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Dashboard Preview Modal */}
        {showPreview && (
          <DashboardPreviewModal userId={employeeId} onClose={() => setShowPreview(false)} />
        )}
      </DialogContent>
    </Dialog>
  );
}
