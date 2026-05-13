import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { ChevronRight, ChevronLeft, Check, Copy, Mail, Shield } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EMP_TYPES = ['full_time', 'part_time', 'contract', 'intern'];
const WORK_MODES = ['onsite', 'remote', 'hybrid'];

const Step = ({ num, label, active, done }) => (
  <div className="flex items-center gap-2">
    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
      done ? 'bg-emerald-500 text-white' : active ? 'bg-teal-700 text-white' : 'bg-slate-200 text-slate-500'
    }`}>{done ? <Check className="h-4 w-4" /> : num}</div>
    <span className={`text-sm font-medium ${active ? 'text-slate-900' : 'text-slate-500'}`}>{label}</span>
  </div>
);

export default function AddEmployeeForm({ onNavigate }) {
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [departments, setDepartments] = useState([]);
  const [allRoles, setAllRoles] = useState([]);
  const [managers, setManagers] = useState([]);
  const [result, setResult] = useState(null);

  const [form, setForm] = useState({
    name: '', email: '', mobile: '', date_of_birth: '',
    department: '', role: '', designation: '', reports_to: 'none',
    date_of_joining: new Date().toISOString().slice(0, 10),
    employment_type: 'full_time', work_mode: 'onsite', work_location: '',
    send_welcome_email: true, require_2fa: false,
  });

  const token = localStorage.getItem('token');

  useEffect(() => {
    const load = async () => {
      try {
        const [d, r, e] = await Promise.all([
          axios.get(`${API}/departments`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/departments/_meta/roles`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/employees?status=active&limit=200`, { headers: { Authorization: `Bearer ${token}` } }),
        ]);
        setDepartments(d.data);
        setAllRoles(r.data);
        setManagers(e.data.items || []);
      } catch (err) { console.error(err); }
    };
    load();
  }, [token]);

  const availableRoles = useMemo(() => {
    if (!form.department) return [];
    return allRoles.filter(r => r.department === form.department);
  }, [form.department, allRoles]);

  const selectedRoleObj = useMemo(() => allRoles.find(r => r.key === form.role), [form.role, allRoles]);

  // Auto-suggest 2FA based on role hierarchy
  useEffect(() => {
    if (selectedRoleObj && selectedRoleObj.hierarchy_level >= 3) {
      setForm(f => ({ ...f, require_2fa: true }));
    }
  }, [selectedRoleObj]);

  const validate = () => {
    if (step === 1) {
      if (!form.name || form.name.length < 2) { toast.error('Name is required (min 2 chars)'); return false; }
      if (!form.email || !form.email.includes('@')) { toast.error('Valid email required'); return false; }
    }
    if (step === 2) {
      if (!form.department) { toast.error('Select a department'); return false; }
      if (!form.role) { toast.error('Select a role'); return false; }
    }
    return true;
  };

  const next = () => { if (validate()) setStep(s => Math.min(3, s + 1)); };
  const back = () => setStep(s => Math.max(1, s - 1));

  const submit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    try {
      const payload = {
        ...form,
        reports_to: form.reports_to === 'none' ? null : form.reports_to,
      };
      const res = await axios.post(`${API}/employees`, payload, { headers: { Authorization: `Bearer ${token}` } });
      setResult(res.data);
      toast.success(`Employee ${form.name} created!`);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to create employee';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  const copyText = (txt) => { navigator.clipboard.writeText(txt); toast.success('Copied!'); };

  // Success screen
  if (result) {
    return (
      <div className="p-6 max-w-2xl mx-auto" data-testid="add-employee-success">
        <Card className="p-8 text-center">
          <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 flex items-center justify-center mb-4">
            <Check className="h-8 w-8 text-emerald-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900">Employee Created Successfully</h2>
          <p className="text-slate-500 mt-2">{result.message}</p>

          <div className="mt-6 grid grid-cols-2 gap-3 text-left text-sm">
            <div className="p-3 bg-slate-50 rounded-md">
              <p className="text-xs text-slate-500 uppercase tracking-wider">Employee ID</p>
              <p className="font-mono font-semibold text-slate-900">{result.employee_id}</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-md">
              <p className="text-xs text-slate-500 uppercase tracking-wider">Email</p>
              <p className="font-medium text-slate-900 truncate">{result.email}</p>
            </div>
          </div>

          <Card className="mt-4 p-4 bg-amber-50 border-amber-200 text-left">
            <p className="text-xs uppercase tracking-wider text-amber-700 font-semibold mb-2 flex items-center gap-2"><Shield className="h-3.5 w-3.5" /> Temporary Password (show ONCE)</p>
            <div className="flex items-center gap-2">
              <code className="bg-white px-3 py-2 rounded font-mono text-sm text-slate-900 flex-1 select-all" data-testid="temp-password">{result.temporary_password}</code>
              <Button size="sm" variant="outline" onClick={() => copyText(result.temporary_password)} data-testid="copy-password"><Copy className="h-3.5 w-3.5" /></Button>
            </div>
            <p className="text-xs text-amber-700 mt-2">Share this password securely with the employee. They should change it on first login.</p>
          </Card>

          {result.welcome_email_sent && (
            <p className="mt-3 text-xs text-slate-500 flex items-center justify-center gap-1"><Mail className="h-3 w-3" /> Welcome email queued (Resend MOCKED — would deliver when live)</p>
          )}
          {result.require_2fa && (
            <p className="mt-1 text-xs text-violet-600 flex items-center justify-center gap-1"><Shield className="h-3 w-3" /> 2FA will be required on first login</p>
          )}

          <div className="mt-6 flex gap-2 justify-center">
            <Button variant="outline" onClick={() => { setResult(null); setStep(1); setForm({ ...form, name: '', email: '', mobile: '', designation: '' }); }} data-testid="add-another-btn">Add Another</Button>
            <Button onClick={() => onNavigate('emp-list')} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="goto-list-btn">View All Employees</Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-3xl mx-auto" data-testid="add-employee-form">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Add New Employee</h1>
        <p className="text-slate-500 mt-1 text-sm">Step-by-step onboarding · creates user with RBAC fields populated</p>
      </div>

      {/* Stepper */}
      <Card className="p-5">
        <div className="flex items-center justify-between gap-2">
          <Step num={1} label="Basic Info" active={step === 1} done={step > 1} />
          <div className="flex-1 h-px bg-slate-200" />
          <Step num={2} label="Employment" active={step === 2} done={step > 2} />
          <div className="flex-1 h-px bg-slate-200" />
          <Step num={3} label="Access & Security" active={step === 3} done={false} />
        </div>
      </Card>

      <Card className="p-6">
        {step === 1 && (
          <div className="space-y-4" data-testid="step-1">
            <h3 className="text-lg font-semibold">Basic Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Full Name *</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Rohit Sharma" data-testid="form-name" />
              </div>
              <div>
                <Label>Email *</Label>
                <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="rohit@leamss.com" data-testid="form-email" />
              </div>
              <div>
                <Label>Mobile</Label>
                <Input value={form.mobile} onChange={(e) => setForm({ ...form, mobile: e.target.value })} placeholder="+91 98765 43210" data-testid="form-mobile" />
              </div>
              <div>
                <Label>Date of Birth</Label>
                <Input type="date" value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} data-testid="form-dob" />
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4" data-testid="step-2">
            <h3 className="text-lg font-semibold">Employment Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Department *</Label>
                <Select value={form.department} onValueChange={(v) => setForm({ ...form, department: v, role: '' })}>
                  <SelectTrigger data-testid="form-department"><SelectValue placeholder="Select department" /></SelectTrigger>
                  <SelectContent>
                    {departments.map(d => <SelectItem key={d.key} value={d.key}>{d.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Role *</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })} disabled={!form.department}>
                  <SelectTrigger data-testid="form-role"><SelectValue placeholder={form.department ? 'Select role' : 'Pick a department first'} /></SelectTrigger>
                  <SelectContent>
                    {availableRoles.map(r => <SelectItem key={r.key} value={r.key}>{r.name} (L{r.hierarchy_level})</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2">
                <Label>Designation</Label>
                <Input value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} placeholder={selectedRoleObj?.name || 'e.g. Senior Sales Executive'} data-testid="form-designation" />
              </div>
              <div>
                <Label>Reports To</Label>
                <Select value={form.reports_to} onValueChange={(v) => setForm({ ...form, reports_to: v })}>
                  <SelectTrigger data-testid="form-reports-to"><SelectValue placeholder="Select manager" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No manager</SelectItem>
                    {managers.map(m => <SelectItem key={m.id} value={m.id}>{m.name} · {m.designation || m.rbac_role}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Date of Joining</Label>
                <Input type="date" value={form.date_of_joining} onChange={(e) => setForm({ ...form, date_of_joining: e.target.value })} data-testid="form-doj" />
              </div>
              <div>
                <Label>Employment Type</Label>
                <Select value={form.employment_type} onValueChange={(v) => setForm({ ...form, employment_type: v })}>
                  <SelectTrigger data-testid="form-emp-type"><SelectValue /></SelectTrigger>
                  <SelectContent>{EMP_TYPES.map(t => <SelectItem key={t} value={t}>{t.replace('_', ' ')}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label>Work Mode</Label>
                <Select value={form.work_mode} onValueChange={(v) => setForm({ ...form, work_mode: v })}>
                  <SelectTrigger data-testid="form-work-mode"><SelectValue /></SelectTrigger>
                  <SelectContent>{WORK_MODES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2">
                <Label>Work Location</Label>
                <Input value={form.work_location} onChange={(e) => setForm({ ...form, work_location: e.target.value })} placeholder="e.g. Mumbai HQ, Bangalore office" data-testid="form-location" />
              </div>
            </div>

            {selectedRoleObj && (
              <Card className="p-3 bg-teal-50 border-teal-200 text-xs">
                <p className="font-semibold text-teal-900">{selectedRoleObj.name} — {selectedRoleObj.permissions?.length || 0} permissions, {selectedRoleObj.ui_modules?.length || 0} UI modules</p>
                <p className="text-teal-700 mt-1">{selectedRoleObj.description}</p>
              </Card>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4" data-testid="step-3">
            <h3 className="text-lg font-semibold">Access & Security</h3>

            <Card className="p-4 bg-slate-50 border-slate-200 text-sm">
              <p className="text-slate-700"><strong>Auto-generated:</strong> A secure temporary password will be created. You can copy it after submission.</p>
              <p className="text-slate-500 text-xs mt-1">The employee will be prompted to change it on first login.</p>
            </Card>

            <label className="flex items-center gap-3 cursor-pointer p-3 hover:bg-slate-50 rounded-md">
              <input type="checkbox" checked={form.send_welcome_email} onChange={(e) => setForm({ ...form, send_welcome_email: e.target.checked })} className="w-4 h-4 rounded text-teal-700" data-testid="form-send-email" />
              <div className="flex-1">
                <p className="font-medium text-slate-800">Send welcome email</p>
                <p className="text-xs text-slate-500">Email with login link + temp password (Resend currently mocked)</p>
              </div>
              <Mail className="h-4 w-4 text-slate-400" />
            </label>

            <label className="flex items-center gap-3 cursor-pointer p-3 hover:bg-slate-50 rounded-md">
              <input type="checkbox" checked={form.require_2fa} onChange={(e) => setForm({ ...form, require_2fa: e.target.checked })} className="w-4 h-4 rounded text-violet-600" data-testid="form-require-2fa" />
              <div className="flex-1">
                <p className="font-medium text-slate-800">Require 2FA on first login</p>
                <p className="text-xs text-slate-500">{selectedRoleObj?.hierarchy_level >= 3 ? 'Auto-enabled (senior role L3+)' : 'Recommended for sensitive roles'}</p>
              </div>
              <Shield className="h-4 w-4 text-violet-500" />
            </label>

            {/* Summary */}
            <Card className="p-4 bg-teal-50 border-teal-200 mt-4">
              <p className="text-xs uppercase tracking-wider text-teal-700 font-semibold mb-2">Review</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-slate-500">Name:</span> <strong>{form.name}</strong></div>
                <div><span className="text-slate-500">Email:</span> <strong>{form.email}</strong></div>
                <div><span className="text-slate-500">Department:</span> <strong className="capitalize">{form.department}</strong></div>
                <div><span className="text-slate-500">Role:</span> <strong>{selectedRoleObj?.name}</strong></div>
                <div><span className="text-slate-500">Type:</span> <strong>{form.employment_type.replace('_', ' ')}</strong></div>
                <div><span className="text-slate-500">Mode:</span> <strong>{form.work_mode}</strong></div>
              </div>
            </Card>
          </div>
        )}

        <div className="flex justify-between mt-6 pt-6 border-t border-slate-100">
          {step > 1 ? <Button variant="outline" onClick={back} data-testid="form-back"><ChevronLeft className="h-4 w-4 mr-1" /> Back</Button> : <div />}
          {step < 3 ? (
            <Button onClick={next} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="form-next">Next <ChevronRight className="h-4 w-4 ml-1" /></Button>
          ) : (
            <Button onClick={submit} disabled={submitting} className="bg-teal-700 hover:bg-teal-800 text-white" data-testid="form-submit">{submitting ? 'Creating...' : 'Create Employee'}</Button>
          )}
        </div>
      </Card>
    </div>
  );
}
