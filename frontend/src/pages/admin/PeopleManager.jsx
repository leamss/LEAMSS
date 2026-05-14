/**
 * Phase 4D — Unified People Manager
 *
 * ONE place for all user/vendor management:
 *   - Internal Employees (admin, sales, CM, ops, HR, IT, marketing, finance)
 *   - External Partners
 *   - Internal Vendors (auto-linked CMs, sales reps)
 *   - External Vendors (tutors, lawyers, consultants)
 *   - Clients (read-only)
 *
 * Replaces fragmented user-creation paths. Single "Add Person" wizard intelligently
 * routes based on chosen person_type.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import {
  ArrowLeft, Plus, Search, Users, UserCog, Briefcase, Shield, Mail, Phone,
  Sparkles, IndianRupee, Globe, Lock, RefreshCw, Power, KeyRound, AlertCircle,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TYPE_META = {
  employee_internal: { label: 'Internal Employee',  icon: UserCog, color: 'indigo', desc: 'Admin, Sales, CM, Ops, HR…' },
  partner_external:  { label: 'External Partner',   icon: Briefcase, color: 'purple', desc: 'Channel partner / agent' },
  vendor_internal:   { label: 'Internal Vendor',    icon: Shield, color: 'emerald', desc: 'CM / Sales rep linked via vendor master' },
  vendor_external:   { label: 'External Vendor',    icon: Globe, color: 'amber', desc: 'Tutor, Lawyer, Consultant…' },
  client:            { label: 'Client',             icon: Users, color: 'slate', desc: 'End customer' },
  unknown:           { label: 'Unknown',            icon: AlertCircle, color: 'rose', desc: 'Orphan record' },
};

const ROLE_OPTIONS = {
  employee_internal: [
    { v: 'admin', l: 'Admin' },
    { v: 'sales_executive', l: 'Sales Executive' },
    { v: 'sr_sales_executive', l: 'Senior Sales Executive' },
    { v: 'sales_manager', l: 'Sales Manager' },
    { v: 'sales_head', l: 'Sales Head' },
    { v: 'case_manager', l: 'Case Manager' },
    { v: 'case_officer', l: 'Case Officer' },
    { v: 'operations', l: 'Operations' },
    { v: 'hr_manager', l: 'HR Manager' },
    { v: 'hr_admin', l: 'HR Admin' },
    { v: 'accountant', l: 'Accountant' },
    { v: 'it_admin', l: 'IT Admin' },
    { v: 'marketing', l: 'Marketing' },
  ],
};

const STATUS_BADGE = {
  active: 'bg-emerald-100 text-emerald-700',
  inactive: 'bg-rose-100 text-rose-700',
  pending: 'bg-amber-100 text-amber-700',
};


// ═══════════════════════════════════════════════════════════════════════
// Add Person Wizard
// ═══════════════════════════════════════════════════════════════════════
function AddPersonWizard({ open, onClose, onCreated }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    person_type: '',
    name: '', email: '', mobile: '',
    role: '', department: '',
    vendor_category: '', specialization: '',
    send_invite: true,
  });
  const [submitting, setSubmitting] = useState(false);
  const [vendorCats, setVendorCats] = useState([]);

  useEffect(() => {
    if (!open) { setStep(1); setForm({ person_type: '', name: '', email: '', mobile: '', role: '', department: '', vendor_category: '', specialization: '', send_invite: true }); return; }
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/vendors/categories`, { headers: { Authorization: `Bearer ${token}` } });
        setVendorCats(r.data.categories || []);
      } catch (_) {}
    })();
  }, [open]);

  const canNext1 = !!form.person_type;
  const canNext2 = form.name && form.email;
  const canSubmit = canNext1 && canNext2 && (
    form.person_type === 'employee_internal' ? !!form.role :
    form.person_type.startsWith('vendor_') ? !!form.vendor_category : true
  );

  const submit = async () => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const payload = {
        person_type: form.person_type,
        name: form.name,
        email: form.email,
        mobile: form.mobile || '',
        role: form.role || null,
        department: form.department || null,
        vendor_category: form.vendor_category || null,
        specialization: form.specialization ? form.specialization.split(',').map(s => s.trim()) : [],
        send_invite: form.send_invite,
      };
      const r = await axios.post(`${API}/people`, payload, { headers: { Authorization: `Bearer ${token}` } });
      const temp = r.data.temp_password;
      const role = r.data.linked_user_role || form.role || form.vendor_category;
      if (temp) {
        window.alert(
          `✅ Person created successfully!\n\n` +
          `📧 Email: ${form.email}\n` +
          `🔑 Temp Password: ${temp}\n` +
          `🎭 Role: ${role}\n\n` +
          `Share these credentials with the user — they will be asked to change the password on first login.`
        );
      } else {
        toast.success(`${TYPE_META[form.person_type].label} created`);
      }
      onCreated(r.data.person_id);
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Create failed');
    } finally { setSubmitting(false); }
  };

  if (!open) return null;
  const meta = form.person_type ? TYPE_META[form.person_type] : null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl" data-testid="add-person-wizard">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            Add Person — Step {step} of 3
          </DialogTitle>
        </DialogHeader>

        {/* Progress bar */}
        <div className="flex items-center gap-2 mb-4">
          {[1, 2, 3].map(s => (
            <div key={s} className={`h-1.5 flex-1 rounded ${step >= s ? 'bg-indigo-500' : 'bg-slate-200'}`} />
          ))}
        </div>

        {step === 1 && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600 mb-2">What kind of person are you adding?</p>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(TYPE_META).filter(([k]) => k !== 'unknown' && k !== 'client').map(([key, m]) => {
                const Icon = m.icon;
                return (
                  <button key={key} onClick={() => setForm({ ...form, person_type: key })}
                    className={`text-left p-4 rounded-lg border-2 transition ${form.person_type === key ? `border-${m.color}-500 bg-${m.color}-50` : 'border-slate-200 hover:border-slate-300'}`}
                    data-testid={`type-${key}`}>
                    <Icon className={`h-5 w-5 mb-2 text-${m.color}-600`} />
                    <p className="font-bold text-sm">{m.label}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">{m.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <div className={`p-3 rounded bg-${meta.color}-50 border border-${meta.color}-200 text-xs`}>
              <strong>{meta.label}</strong> — {meta.desc}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs font-bold">Full Name *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g., Rohit Sharma" data-testid="person-name" /></div>
              <div><Label className="text-xs font-bold">Email *</Label><Input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="rohit@leamss.com" data-testid="person-email" /></div>
              <div><Label className="text-xs font-bold">Mobile</Label><Input value={form.mobile} onChange={e => setForm({ ...form, mobile: e.target.value })} placeholder="+91 ..." data-testid="person-mobile" /></div>
              <div><Label className="text-xs font-bold">Department</Label><Input value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} placeholder="Sales / Ops / IT…" data-testid="person-dept" /></div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3">
            {form.person_type === 'employee_internal' && (
              <div>
                <Label className="text-xs font-bold">Role / Designation *</Label>
                <Select value={form.role} onValueChange={v => setForm({ ...form, role: v })}>
                  <SelectTrigger data-testid="person-role"><SelectValue placeholder="Select role" /></SelectTrigger>
                  <SelectContent>
                    {ROLE_OPTIONS.employee_internal.map(o => <SelectItem key={o.v} value={o.v}>{o.l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}
            {form.person_type === 'partner_external' && (
              <div className="p-3 bg-purple-50 rounded text-xs">
                <p className="font-bold text-purple-900">Partner Role</p>
                <p className="text-purple-700 mt-1">This person will get the <strong>partner</strong> role with access to create pre-assessments, send proposals, and earn commissions per slab.</p>
              </div>
            )}
            {(form.person_type === 'vendor_internal' || form.person_type === 'vendor_external') && (
              <>
                <div>
                  <Label className="text-xs font-bold">Vendor Category *</Label>
                  <Select value={form.vendor_category} onValueChange={v => setForm({ ...form, vendor_category: v })}>
                    <SelectTrigger data-testid="person-vendor-cat"><SelectValue placeholder="Pick category" /></SelectTrigger>
                    <SelectContent>
                      {vendorCats.filter(c =>
                        form.person_type === 'vendor_internal' ? c.is_internal : !c.is_internal
                      ).map(c => <SelectItem key={c.key} value={c.key}>{c.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                {form.vendor_category === 'case_manager' && form.person_type === 'vendor_internal' && (
                  <div className="text-[11px] p-2 bg-emerald-50 rounded">
                    ✓ A linked <strong>Case Manager user account</strong> will be auto-created.
                  </div>
                )}
                {form.vendor_category === 'sales_commission' && form.person_type === 'vendor_internal' && (
                  <div className="text-[11px] p-2 bg-emerald-50 rounded">
                    ✓ A linked <strong>Sales Executive user account</strong> will be auto-created.
                  </div>
                )}
                <div>
                  <Label className="text-xs font-bold">Specialization (comma-separated)</Label>
                  <Input value={form.specialization} onChange={e => setForm({ ...form, specialization: e.target.value })} placeholder="e.g., Canada PR, Australia Skilled" data-testid="person-spec" />
                </div>
              </>
            )}
            <Card className="p-3 bg-slate-50 text-xs space-y-1">
              <p className="font-bold text-slate-700">Summary</p>
              <p>Type: <strong>{meta.label}</strong></p>
              <p>Name: <strong>{form.name}</strong></p>
              <p>Email: <strong>{form.email}</strong></p>
              {form.role && <p>Role: <strong>{form.role}</strong></p>}
              {form.vendor_category && <p>Category: <strong>{form.vendor_category}</strong></p>}
              <p className="text-[10px] text-slate-500 mt-2 italic">A temporary password will be generated and shown to you — share with the user. They must change it on first login.</p>
            </Card>
          </div>
        )}

        <DialogFooter>
          {step > 1 && <Button variant="outline" onClick={() => setStep(step - 1)} data-testid="wizard-back">Back</Button>}
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          {step < 3 && <Button onClick={() => setStep(step + 1)} disabled={step === 1 ? !canNext1 : !canNext2} className="bg-indigo-600 hover:bg-indigo-700" data-testid="wizard-next">Next</Button>}
          {step === 3 && <Button onClick={submit} disabled={!canSubmit || submitting} className="bg-emerald-600 hover:bg-emerald-700" data-testid="wizard-submit">{submitting ? 'Creating…' : 'Create Person'}</Button>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// Person Detail Drawer
// ═══════════════════════════════════════════════════════════════════════
function PersonDetail({ personId, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/people/${personId}`, { headers: { Authorization: `Bearer ${token}` } });
      setData(r.data);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  };
  useEffect(() => { if (personId) load(); /* eslint-disable-next-line */ }, [personId]);

  if (!personId) return null;

  const action = async (path) => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.post(`${API}/people/${personId}/${path}`, {}, { headers: { Authorization: `Bearer ${token}` } });
      if (r.data.temp_password) {
        window.alert(`✅ Password reset!\n\nEmail: ${r.data.email}\nNew Temp Password: ${r.data.temp_password}\n\nShare with the user.`);
      } else {
        toast.success(`Action ${path} done`);
      }
      load();
      onChanged?.();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed'); }
  };

  return (
    <Dialog open={!!personId} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-3xl" data-testid="person-detail">
        <DialogHeader>
          <DialogTitle>{loading ? 'Loading…' : (data?.user?.name || data?.vendor?.name)}</DialogTitle>
        </DialogHeader>
        {loading || !data ? (
          <p className="text-sm text-slate-400 text-center py-8">Loading…</p>
        ) : (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            {/* Identity */}
            <Card className="p-3 bg-slate-50">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-[10px] font-bold uppercase text-slate-500">Person Type</p>
                  <Badge className={`bg-${(TYPE_META[data.person_type] || TYPE_META.unknown).color}-100 text-${(TYPE_META[data.person_type] || TYPE_META.unknown).color}-700 mt-0.5`}>{(TYPE_META[data.person_type] || TYPE_META.unknown).label}</Badge>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase text-slate-500">Status</p>
                  <Badge className={STATUS_BADGE[(data.user || data.vendor)?.status] || ''}>{(data.user || data.vendor)?.status || '—'}</Badge>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase text-slate-500">Email</p>
                  <p className="flex items-center gap-1"><Mail className="h-3.5 w-3.5 text-slate-400" />{(data.user || data.vendor)?.email}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase text-slate-500">Mobile</p>
                  <p className="flex items-center gap-1"><Phone className="h-3.5 w-3.5 text-slate-400" />{data.user?.mobile || data.vendor?.phone || '—'}</p>
                </div>
                {data.user && (
                  <>
                    <div><p className="text-[10px] font-bold uppercase text-slate-500">Role</p><p>{data.user.rbac_role || data.user.role}</p></div>
                    <div><p className="text-[10px] font-bold uppercase text-slate-500">Department</p><p>{data.user.department || '—'}</p></div>
                  </>
                )}
                {data.vendor && (
                  <>
                    <div><p className="text-[10px] font-bold uppercase text-slate-500">Vendor Code</p><p className="font-mono">{data.vendor.vendor_code}</p></div>
                    <div><p className="text-[10px] font-bold uppercase text-slate-500">Category</p><p>{data.vendor.category} ({data.vendor.vendor_type})</p></div>
                  </>
                )}
              </div>
            </Card>

            {/* User-side details */}
            {data.user && (
              <Card className="p-3">
                <p className="text-[10px] font-bold uppercase text-slate-500 mb-2 flex items-center gap-1"><Lock className="h-3 w-3" />User Account</p>
                <div className="text-xs space-y-0.5">
                  <p>Login ID: <strong>{data.user.id.substring(0, 8)}…</strong></p>
                  <p>Last login: <strong>{data.user.last_login_at ? new Date(data.user.last_login_at).toLocaleString() : '— never —'}</strong></p>
                  <p>Permissions assigned: <strong>{(data.user.permissions || []).length}</strong></p>
                  {data.user.must_change_password_on_next_login && <p className="text-amber-700">⚠️ Must change password on next login</p>}
                  {data.user.auto_created_from_vendor && <p className="text-indigo-700">🔗 Auto-created from vendor record</p>}
                </div>
              </Card>
            )}

            {/* Linked vendor */}
            {data.vendor && data.user && (
              <Card className="p-3 bg-emerald-50">
                <p className="text-[10px] font-bold uppercase text-emerald-700 mb-1">Linked Vendor Record</p>
                <p className="text-xs">{data.vendor.name} · {data.vendor.vendor_code} · {data.vendor.category}</p>
              </Card>
            )}
            {data.vendor && !data.user && (
              <Card className="p-3 bg-amber-50">
                <p className="text-[10px] font-bold uppercase text-amber-700 mb-1">Vendor-only profile</p>
                <p className="text-xs text-amber-700">This person doesn&apos;t have a login account yet. Send a portal invite from the Vendors tab.</p>
              </Card>
            )}
          </div>
        )}
        <DialogFooter className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={onClose}>Close</Button>
          {data?.user && (
            <Button variant="outline" onClick={() => action('reset-password')} data-testid="reset-pw"><KeyRound className="h-3.5 w-3.5 mr-1" />Reset Password</Button>
          )}
          {(data?.user?.status === 'active' || data?.vendor?.status === 'active') ? (
            <Button variant="outline" className="text-rose-600 border-rose-300" onClick={() => action('deactivate')} data-testid="deact"><Power className="h-3.5 w-3.5 mr-1" />Deactivate</Button>
          ) : (
            <Button variant="outline" className="text-emerald-600 border-emerald-300" onClick={() => action('reactivate')} data-testid="reactivate"><Power className="h-3.5 w-3.5 mr-1" />Reactivate</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// PAGE
// ═══════════════════════════════════════════════════════════════════════
export default function PeopleManager() {
  const navigate = useNavigate();
  const [people, setPeople] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('all');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [selectedPersonId, setSelectedPersonId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [pRes, sRes] = await Promise.all([
        axios.get(`${API}/people`, { headers }),
        axios.get(`${API}/people/stats`, { headers }),
      ]);
      setPeople(pRes.data.people || []);
      setStats(sRes.data);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Failed to load'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    let out = people;
    if (tab !== 'all') out = out.filter(p => p.person_type === tab);
    if (statusFilter) out = out.filter(p => p.status === statusFilter);
    if (search) {
      const s = search.toLowerCase();
      out = out.filter(p =>
        (p.name || '').toLowerCase().includes(s) ||
        (p.email || '').toLowerCase().includes(s) ||
        (p.vendor_code || '').toLowerCase().includes(s));
    }
    return out;
  }, [people, tab, search, statusFilter]);

  const counts = stats?.by_type || {};

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="people-manager">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/admin')} className="p-2 rounded-lg hover:bg-slate-200" data-testid="back-btn"><ArrowLeft className="h-5 w-5 text-slate-700" /></button>
            <div>
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Users className="h-7 w-7 text-indigo-600" />People</h1>
              <p className="text-sm text-slate-500 mt-1">Unified directory — employees, partners, vendors, clients. Single source of identity.</p>
            </div>
          </div>
          <Button onClick={() => setWizardOpen(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-person-btn"><Plus className="h-4 w-4 mr-1.5" />Add Person</Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <Card className="p-3 bg-gradient-to-br from-indigo-50 to-indigo-100 border-indigo-300" data-testid="stat-total">
            <p className="text-[10px] uppercase font-bold text-indigo-800">Total People</p>
            <p className="text-2xl font-extrabold text-indigo-900 mt-0.5">{stats?.total || 0}</p>
          </Card>
          {[
            ['employee_internal', 'Employees'],
            ['partner_external', 'Partners'],
            ['vendor_internal', 'Vendors (Int)'],
            ['vendor_external', 'Vendors (Ext)'],
          ].map(([k, label]) => {
            const m = TYPE_META[k];
            return (
              <Card key={k} className={`p-3 bg-${m.color}-50 border-${m.color}-200`} data-testid={`stat-${k}`}>
                <p className={`text-[10px] uppercase font-bold text-${m.color}-800`}>{label}</p>
                <p className={`text-2xl font-extrabold text-${m.color}-900 mt-0.5`}>{counts[k] || 0}</p>
              </Card>
            );
          })}
        </div>

        {/* Filters */}
        <Card className="p-3 mb-4 flex items-center gap-3 flex-wrap" data-testid="filter-bar">
          <div className="relative flex-1 min-w-48">
            <Search className="h-4 w-4 absolute left-2.5 top-2.5 text-slate-400" />
            <Input placeholder="Search name, email, vendor code…" value={search} onChange={e => setSearch(e.target.value)} className="pl-8" data-testid="search-input" />
          </div>
          <Select value={statusFilter || 'all'} onValueChange={v => setStatusFilter(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-32" data-testid="status-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh"><RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh</Button>
        </Card>

        {/* Tabs */}
        <div className="flex gap-1 mb-3 border-b" data-testid="type-tabs">
          {[
            ['all', 'All', null],
            ['employee_internal', 'Employees', UserCog],
            ['partner_external', 'Partners', Briefcase],
            ['vendor_internal', 'Vendors (Internal)', Shield],
            ['vendor_external', 'Vendors (External)', Globe],
            ['client', 'Clients', Users],
          ].map(([k, label, Icon]) => (
            <button key={k} onClick={() => setTab(k)}
              className={`px-4 py-2 text-sm font-medium border-b-2 flex items-center gap-1.5 transition ${tab === k ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
              data-testid={`tab-${k}`}>
              {Icon && <Icon className="h-3.5 w-3.5" />}{label}
              {tab !== 'all' && k !== 'all' && tab === k && <Badge className="ml-1 bg-indigo-100 text-indigo-700 text-[10px]">{filtered.length}</Badge>}
            </button>
          ))}
        </div>

        {/* List */}
        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-10 w-10 text-indigo-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
        ) : filtered.length === 0 ? (
          <Card className="p-12 text-center">
            <Users className="h-10 w-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No people match your filter.</p>
          </Card>
        ) : (
          <Card className="p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-100">
                <tr className="text-[10px] uppercase text-slate-500">
                  <th className="px-3 py-2 text-left">Name</th>
                  <th className="px-3 py-2 text-left">Email</th>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Role / Category</th>
                  <th className="px-3 py-2 text-left">Department</th>
                  <th className="px-3 py-2 text-center">Status</th>
                  <th className="px-3 py-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p, i) => {
                  const m = TYPE_META[p.person_type] || TYPE_META.unknown;
                  return (
                    <tr key={p.id} className="border-t hover:bg-slate-50" data-testid={`row-${i}`}>
                      <td className="px-3 py-2"><p className="font-medium">{p.name}</p>{p.vendor_code && <p className="text-[10px] text-slate-500 font-mono">{p.vendor_code}</p>}</td>
                      <td className="px-3 py-2 text-xs">{p.email}<br /><span className="text-[10px] text-slate-500">{p.mobile}</span></td>
                      <td className="px-3 py-2"><Badge className={`bg-${m.color}-100 text-${m.color}-700 text-[10px]`}>{m.label}</Badge></td>
                      <td className="px-3 py-2 text-xs">{p.role || '—'}</td>
                      <td className="px-3 py-2 text-xs">{p.department || '—'}</td>
                      <td className="px-3 py-2 text-center"><Badge className={`${STATUS_BADGE[p.status] || ''} text-[10px]`}>{p.status}</Badge></td>
                      <td className="px-3 py-2 text-right">
                        <Button size="sm" variant="outline" onClick={() => setSelectedPersonId(p.id)} className="h-7 text-xs" data-testid={`view-${i}`}>View</Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )}
      </div>

      <AddPersonWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onCreated={() => load()} />
      <PersonDetail personId={selectedPersonId} onClose={() => setSelectedPersonId(null)} onChanged={load} />
    </div>
  );
}
