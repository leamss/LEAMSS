import { useState, useEffect } from 'react';
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
import { User, Shield, Activity, Edit, X, UserCheck, UserX, KeyRound, ArrowRight } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TABS = [
  { key: 'profile', label: 'Profile', icon: User },
  { key: 'role', label: 'Role & Permissions', icon: Shield },
  { key: 'activity', label: 'Activity', icon: Activity },
];

export default function EmployeeDetailModal({ employeeId, onClose, onUpdated }) {
  const [user, setUser] = useState(null);
  const [history, setHistory] = useState([]);
  const [activity, setActivity] = useState([]);
  const [roles, setRoles] = useState([]);
  const [activeTab, setActiveTab] = useState('profile');
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [roleChange, setRoleChange] = useState({ open: false, new_role: '', reason: '' });
  const [resetPwdResult, setResetPwdResult] = useState(null);
  const token = localStorage.getItem('token');

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
    try {
      await axios.patch(`${API}/employees/${employeeId}/role`,
        { new_role: roleChange.new_role, reason: roleChange.reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Role changed to ${roleChange.new_role}`);
      setRoleChange({ open: false, new_role: '', reason: '' });
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
    try {
      const res = await axios.post(`${API}/employees/${employeeId}/reset-password`, null, { headers: { Authorization: `Bearer ${token}` } });
      setResetPwdResult(res.data.temporary_password);
    } catch (err) {
      toast.error('Password reset failed');
    }
  };

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
        <div className="p-6 border-b border-slate-100 bg-gradient-to-r from-teal-50 via-indigo-50 to-violet-50">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-teal-500 to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-md">
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
              <Button variant="outline" size="sm" onClick={resetPwd} data-testid="reset-pwd-btn"><KeyRound className="h-3.5 w-3.5 mr-1" /> Reset Pwd</Button>
              <Button variant="outline" size="sm" onClick={toggleActive} className={user.employment_status === 'active' ? 'text-rose-600 border-rose-200' : 'text-emerald-600 border-emerald-200'} data-testid="toggle-active-btn">
                {user.employment_status === 'active' ? <><UserX className="h-3.5 w-3.5 mr-1" /> Deactivate</> : <><UserCheck className="h-3.5 w-3.5 mr-1" /> Reactivate</>}
              </Button>
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
                  <Button size="sm" variant="outline" onClick={() => setEditing(true)} data-testid="edit-profile-btn"><Edit className="h-3.5 w-3.5 mr-1" /> Edit</Button>
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
                        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-teal-500 to-indigo-600 flex items-center justify-center text-white text-[10px] font-semibold">{(r.name || '?').charAt(0)}</div>
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
                <Button size="sm" variant="outline" onClick={() => setRoleChange({ open: true, new_role: '', reason: '' })} data-testid="change-role-btn">
                  Change Role <ArrowRight className="h-3.5 w-3.5 ml-1" />
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
                    <Badge key={m} className="bg-indigo-100 text-indigo-700 text-[10px]">{m}</Badge>
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
        <Dialog open={roleChange.open} onOpenChange={(v) => !v && setRoleChange({ open: false, new_role: '', reason: '' })}>
          <DialogContent>
            <DialogHeader><DialogTitle>Change Role</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div>
                <Label>New Role</Label>
                <Select value={roleChange.new_role} onValueChange={(v) => setRoleChange({ ...roleChange, new_role: v })}>
                  <SelectTrigger data-testid="new-role-select"><SelectValue placeholder="Select new role..." /></SelectTrigger>
                  <SelectContent>{roles.map(r => <SelectItem key={r.key} value={r.key}>{r.name} · {r.department}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label>Reason (optional)</Label>
                <Textarea rows={2} value={roleChange.reason} onChange={e => setRoleChange({ ...roleChange, reason: e.target.value })} placeholder="e.g. Promotion to senior level" data-testid="role-change-reason" />
              </div>
              <Card className="p-3 bg-amber-50 border-amber-200 text-xs">
                Changing role will update permissions + UI modules + reassign legacy role field. Logged to history.
              </Card>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRoleChange({ open: false, new_role: '', reason: '' })}>Cancel</Button>
              <Button onClick={changeRole} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="confirm-role-change">Confirm Change</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Reset Pwd Result */}
        <Dialog open={!!resetPwdResult} onOpenChange={() => setResetPwdResult(null)}>
          <DialogContent>
            <DialogHeader><DialogTitle>Temporary Password Generated</DialogTitle></DialogHeader>
            <Card className="p-4 bg-amber-50 border-amber-200">
              <p className="text-xs uppercase text-amber-700 font-semibold">Show this once, then share securely:</p>
              <code className="block mt-2 bg-white px-3 py-2 rounded font-mono text-sm select-all" data-testid="reset-pwd-result">{resetPwdResult}</code>
            </Card>
            <DialogFooter><Button onClick={() => setResetPwdResult(null)}>Got it</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </DialogContent>
    </Dialog>
  );
}
