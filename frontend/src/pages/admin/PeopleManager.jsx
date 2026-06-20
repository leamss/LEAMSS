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
import { useState, useEffect, useMemo, useCallback } from 'react';
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
  Eye, EyeOff, FileText, Upload, Trash2, CheckCircle2, Building2, CreditCard,
  Calendar as CalendarIcon, Download,
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
function CredentialsDialog({ open, onClose, credentials }) {
  const [showPw, setShowPw] = useState(false);
  if (!credentials) return null;
  const { email, temp_password, role, vendor_code, linked_user_role } = credentials;
  const displayRole = linked_user_role || role || '—';

  const copy = async (text, label) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
      }
      toast.success(`${label} copied`);
    } catch { toast.error(`${label} copy failed — please select manually`); }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent data-testid="creds-dialog" className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-emerald-600" />Person Created Successfully</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="bg-emerald-50 border border-emerald-200 rounded p-3 text-xs text-emerald-800">
            ✅ <strong>Login credentials generated.</strong> Share these securely with the user.
            <br />They will be asked to change the password on first login.
          </div>

          <div>
            <Label className="text-[10px] uppercase font-bold text-slate-500">Email</Label>
            <div className="flex gap-2 mt-1">
              <Input readOnly value={email} onFocus={(e) => e.target.select()} className="font-mono text-sm bg-slate-50" data-testid="creds-email" />
              <Button size="sm" variant="outline" onClick={() => copy(email, 'Email')} data-testid="copy-email">Copy</Button>
            </div>
          </div>

          <div>
            <Label className="text-[10px] uppercase font-bold text-slate-500">Temporary Password</Label>
            <div className="flex gap-2 mt-1">
              <div className="relative flex-1">
                <Input
                  readOnly
                  type={showPw ? 'text' : 'password'}
                  value={temp_password}
                  onFocus={(e) => e.target.select()}
                  className="font-mono text-sm bg-slate-50 pr-10"
                  data-testid="creds-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-800"
                  data-testid="toggle-pw"
                  title={showPw ? 'Hide' : 'Show'}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <Button size="sm" variant="outline" onClick={() => copy(temp_password, 'Password')} data-testid="copy-pw">Copy</Button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label className="text-[10px] uppercase font-bold text-slate-500">Role</Label>
              <p className="text-sm font-medium mt-1">{displayRole}</p>
            </div>
            {vendor_code && (
              <div>
                <Label className="text-[10px] uppercase font-bold text-slate-500">Vendor Code</Label>
                <p className="text-sm font-mono mt-1">{vendor_code}</p>
              </div>
            )}
          </div>

          <Button
            variant="outline"
            className="w-full text-xs"
            onClick={() => copy(`Email: ${email}\nPassword: ${temp_password}\nRole: ${displayRole}\nLogin: ${window.location.origin}`, 'All credentials')}
            data-testid="copy-all"
          >
            📋 Copy All (Email + Password + Login URL)
          </Button>
        </div>
        <DialogFooter>
          <Button onClick={onClose} className="bg-emerald-600 hover:bg-emerald-700" data-testid="close-creds">Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function AddPersonWizard({ open, onClose, onCreated }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    person_type: '',
    name: '', email: '', mobile: '',
    role: '', department: '',
    vendor_category: '', specialization: '',
    send_invite: true,
    // Onboarding (Step 4)
    onboarding: {
      designation: '', date_of_joining: '', dob: '', gender: '', blood_group: '',
      current_address: '', permanent_address: '', city: '', state: '', pincode: '',
      emergency_contact_name: '', emergency_contact_phone: '', emergency_contact_relation: '',
      pan_number: '', aadhaar_number: '', gst_number: '',
      bank_account_number: '', bank_ifsc: '', bank_name: '', bank_account_holder_name: '',
      notes: '',
    },
  });
  const [submitting, setSubmitting] = useState(false);
  const [vendorCats, setVendorCats] = useState([]);
  const [docChecklist, setDocChecklist] = useState([]);
  const [credsResult, setCredsResult] = useState(null);  // Phase 4D — proper copy-able credentials dialog

  useEffect(() => {
    if (!open) {
      setStep(1);
      setForm({
        person_type: '', name: '', email: '', mobile: '',
        role: '', department: '', vendor_category: '', specialization: '', send_invite: true,
        onboarding: {
          designation: '', date_of_joining: '', dob: '', gender: '', blood_group: '',
          current_address: '', permanent_address: '', city: '', state: '', pincode: '',
          emergency_contact_name: '', emergency_contact_phone: '', emergency_contact_relation: '',
          pan_number: '', aadhaar_number: '', gst_number: '',
          bank_account_number: '', bank_ifsc: '', bank_name: '', bank_account_holder_name: '',
          notes: '',
        },
      });
      return;
    }
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/vendors/categories`, { headers: { Authorization: `Bearer ${token}` } });
        setVendorCats(r.data.categories || []);
      } catch (_) {}
    })();
  }, [open]);

  // Load doc checklist when type changes
  useEffect(() => {
    if (!form.person_type) { setDocChecklist([]); return; }
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const r = await axios.get(`${API}/people/document-checklist/${form.person_type}`, { headers: { Authorization: `Bearer ${token}` } });
        setDocChecklist(r.data.items || []);
      } catch (_) { setDocChecklist([]); }
    })();
  }, [form.person_type]);

  const setOnb = (k, v) => setForm(f => ({ ...f, onboarding: { ...f.onboarding, [k]: v } }));

  const canNext1 = !!form.person_type;
  const canNext2 = form.name && form.email;
  const canNext3 = canNext1 && canNext2 && (
    form.person_type === 'employee_internal' ? !!form.role :
    form.person_type.startsWith('vendor_') ? !!form.vendor_category : true
  );
  const canSubmit = canNext3;  // Step 4 is optional

  const submit = async () => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      // Filter onboarding empty strings → undefined so backend gets clean data
      const onboarding = Object.fromEntries(
        Object.entries(form.onboarding).filter(([_, v]) => v && String(v).trim() !== '')
      );
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
        onboarding: Object.keys(onboarding).length > 0 ? onboarding : null,
      };
      const r = await axios.post(`${API}/people`, payload, { headers: { Authorization: `Bearer ${token}` } });
      const temp = r.data.temp_password;
      if (temp) {
        setCredsResult({
          email: form.email,
          temp_password: temp,
          role: form.role,
          linked_user_role: r.data.linked_user_role,
          vendor_code: r.data.vendor_code,
          person_id: r.data.person_id,
        });
      } else {
        toast.success(`${TYPE_META[form.person_type].label} created`);
        onCreated(r.data.person_id);
        onClose();
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Create failed');
    } finally { setSubmitting(false); }
  };

  if (!open) return null;
  const meta = form.person_type ? TYPE_META[form.person_type] : null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="add-person-wizard">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-leamss-teal-600" />
            Add Person — Step {step} of 4
          </DialogTitle>
        </DialogHeader>

        {/* Progress bar */}
        <div className="flex items-center gap-2 mb-4">
          {[1, 2, 3, 4].map(s => (
            <div key={s} className={`h-1.5 flex-1 rounded ${step >= s ? 'bg-leamss-teal-500' : 'bg-slate-200'}`} />
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
              <div className="p-3 bg-leamss-orange-50 rounded text-xs">
                <p className="font-bold text-leamss-orange-900">Partner Role</p>
                <p className="text-leamss-orange-700 mt-1">This person will get the <strong>partner</strong> role with access to create pre-assessments, send proposals, and earn commissions per slab.</p>
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
            <p className="text-[11px] text-slate-500 italic">Step 4 will capture employment details, KYC, and bank info. You can skip those fields if not available yet — they can be added later from the person&apos;s detail view.</p>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <div className="p-3 bg-leamss-teal-50 border border-leamss-teal-200 rounded text-xs">
              <p className="font-bold text-leamss-teal-900 flex items-center gap-1.5"><FileText className="h-4 w-4" />Onboarding Details (optional but recommended)</p>
              <p className="text-leamss-teal-700 mt-1">Fill what you have now. KYC documents can be uploaded after creation from the person&apos;s detail view.</p>
            </div>

            {/* Employment */}
            <div>
              <p className="text-xs font-bold text-slate-700 mb-2 flex items-center gap-1"><Building2 className="h-3.5 w-3.5" />Employment Details</p>
              <div className="grid grid-cols-2 gap-2">
                <div><Label className="text-[11px]">Designation</Label><Input value={form.onboarding.designation} onChange={e => setOnb('designation', e.target.value)} placeholder="e.g., Sr. Sales Executive" data-testid="onb-designation" /></div>
                <div><Label className="text-[11px]">Date of Joining</Label><Input type="date" value={form.onboarding.date_of_joining} onChange={e => setOnb('date_of_joining', e.target.value)} data-testid="onb-doj" /></div>
                <div><Label className="text-[11px]">Date of Birth</Label><Input type="date" value={form.onboarding.dob} onChange={e => setOnb('dob', e.target.value)} data-testid="onb-dob" /></div>
                <div>
                  <Label className="text-[11px]">Gender</Label>
                  <Select value={form.onboarding.gender || ''} onValueChange={v => setOnb('gender', v)}>
                    <SelectTrigger data-testid="onb-gender"><SelectValue placeholder="—" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Address */}
            <div>
              <p className="text-xs font-bold text-slate-700 mb-2 flex items-center gap-1"><Globe className="h-3.5 w-3.5" />Address</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="col-span-2"><Label className="text-[11px]">Current Address</Label><Input value={form.onboarding.current_address} onChange={e => setOnb('current_address', e.target.value)} placeholder="Flat/Building, Street" data-testid="onb-addr-current" /></div>
                <div><Label className="text-[11px]">City</Label><Input value={form.onboarding.city} onChange={e => setOnb('city', e.target.value)} data-testid="onb-city" /></div>
                <div><Label className="text-[11px]">State</Label><Input value={form.onboarding.state} onChange={e => setOnb('state', e.target.value)} data-testid="onb-state" /></div>
                <div><Label className="text-[11px]">Pincode</Label><Input value={form.onboarding.pincode} onChange={e => setOnb('pincode', e.target.value)} data-testid="onb-pincode" /></div>
              </div>
            </div>

            {/* Emergency */}
            <div>
              <p className="text-xs font-bold text-slate-700 mb-2 flex items-center gap-1"><Phone className="h-3.5 w-3.5" />Emergency Contact</p>
              <div className="grid grid-cols-3 gap-2">
                <div><Label className="text-[11px]">Name</Label><Input value={form.onboarding.emergency_contact_name} onChange={e => setOnb('emergency_contact_name', e.target.value)} data-testid="onb-ec-name" /></div>
                <div><Label className="text-[11px]">Phone</Label><Input value={form.onboarding.emergency_contact_phone} onChange={e => setOnb('emergency_contact_phone', e.target.value)} data-testid="onb-ec-phone" /></div>
                <div><Label className="text-[11px]">Relation</Label><Input value={form.onboarding.emergency_contact_relation} onChange={e => setOnb('emergency_contact_relation', e.target.value)} placeholder="Parent / Spouse…" data-testid="onb-ec-rel" /></div>
              </div>
            </div>

            {/* KYC */}
            <div>
              <p className="text-xs font-bold text-slate-700 mb-2 flex items-center gap-1"><Shield className="h-3.5 w-3.5" />KYC / Identity</p>
              <div className="grid grid-cols-3 gap-2">
                <div><Label className="text-[11px]">PAN Number</Label><Input value={form.onboarding.pan_number} onChange={e => setOnb('pan_number', e.target.value.toUpperCase())} placeholder="ABCDE1234F" maxLength={10} data-testid="onb-pan" /></div>
                <div><Label className="text-[11px]">Aadhaar (last 4)</Label><Input value={form.onboarding.aadhaar_number} onChange={e => setOnb('aadhaar_number', e.target.value)} placeholder="XXXX XXXX 1234" maxLength={20} data-testid="onb-aadhaar" /></div>
                <div><Label className="text-[11px]">GST Number {(form.person_type === 'vendor_external' || form.person_type === 'partner_external') ? '' : '(if any)'}</Label><Input value={form.onboarding.gst_number} onChange={e => setOnb('gst_number', e.target.value.toUpperCase())} placeholder="29ABCDE1234F1Z5" maxLength={15} data-testid="onb-gst" /></div>
              </div>
            </div>

            {/* Bank */}
            <div>
              <p className="text-xs font-bold text-slate-700 mb-2 flex items-center gap-1"><CreditCard className="h-3.5 w-3.5" />Bank Details (for payouts)</p>
              <div className="grid grid-cols-2 gap-2">
                <div><Label className="text-[11px]">Account Holder Name</Label><Input value={form.onboarding.bank_account_holder_name} onChange={e => setOnb('bank_account_holder_name', e.target.value)} data-testid="onb-bank-holder" /></div>
                <div><Label className="text-[11px]">Account Number</Label><Input value={form.onboarding.bank_account_number} onChange={e => setOnb('bank_account_number', e.target.value)} data-testid="onb-bank-acc" /></div>
                <div><Label className="text-[11px]">IFSC Code</Label><Input value={form.onboarding.bank_ifsc} onChange={e => setOnb('bank_ifsc', e.target.value.toUpperCase())} placeholder="HDFC0001234" maxLength={11} data-testid="onb-ifsc" /></div>
                <div><Label className="text-[11px]">Bank Name</Label><Input value={form.onboarding.bank_name} onChange={e => setOnb('bank_name', e.target.value)} placeholder="HDFC Bank" data-testid="onb-bank-name" /></div>
              </div>
            </div>

            {/* Document checklist preview */}
            {docChecklist.length > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded">
                <p className="text-xs font-bold text-amber-900 mb-2 flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5" />
                  Documents to upload after creation
                </p>
                <ul className="text-[11px] space-y-1">
                  {docChecklist.map(d => (
                    <li key={d.key} className="flex items-center gap-1.5 text-amber-800">
                      {d.required
                        ? <span className="text-rose-600 font-bold">●</span>
                        : <span className="text-slate-400">○</span>}
                      {d.label}{d.required && <span className="text-rose-600 text-[10px]"> (required)</span>}
                    </li>
                  ))}
                </ul>
                <p className="text-[10px] text-amber-700 mt-2 italic">After creating the person, open their detail view and use the Documents tab to upload files (PDF/JPG/PNG, max 10 MB each).</p>
              </div>
            )}

            <Card className="p-3 bg-slate-50 text-xs space-y-1">
              <p className="font-bold text-slate-700">Summary</p>
              <p>Type: <strong>{meta.label}</strong></p>
              <p>Name: <strong>{form.name}</strong></p>
              <p>Email: <strong>{form.email}</strong></p>
              {form.role && <p>Role: <strong>{form.role}</strong></p>}
              {form.vendor_category && <p>Category: <strong>{form.vendor_category}</strong></p>}
              {form.onboarding.designation && <p>Designation: <strong>{form.onboarding.designation}</strong></p>}
              {form.onboarding.pan_number && <p>PAN: <strong>{form.onboarding.pan_number}</strong></p>}
              <p className="text-[10px] text-slate-500 mt-2 italic">A temporary password will be generated and shown to you — share with the user. They must change it on first login.</p>
            </Card>
          </div>
        )}

        <DialogFooter>
          {step > 1 && <Button variant="outline" onClick={() => setStep(step - 1)} data-testid="wizard-back">Back</Button>}
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          {step < 4 && (
            <Button
              onClick={() => setStep(step + 1)}
              disabled={step === 1 ? !canNext1 : step === 2 ? !canNext2 : !canNext3}
              className="bg-leamss-teal-600 hover:bg-leamss-teal-700"
              data-testid="wizard-next"
            >
              Next
            </Button>
          )}
          {step === 4 && (
            <Button onClick={submit} disabled={!canSubmit || submitting} className="bg-emerald-600 hover:bg-emerald-700" data-testid="wizard-submit">
              {submitting ? 'Creating…' : 'Create Person'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
      <CredentialsDialog
        open={!!credsResult}
        credentials={credsResult}
        onClose={() => {
          if (credsResult) {
            onCreated(credsResult.person_id);
            onClose();
            setCredsResult(null);
          }
        }}
      />
    </Dialog>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// Onboarding & Documents Panels (Phase 4D+)
// ═══════════════════════════════════════════════════════════════════════
function OnboardingPanel({ onboarding }) {
  if (!onboarding || Object.keys(onboarding).length === 0) return null;
  const groups = [
    {
      title: 'Employment', icon: Building2, color: 'indigo',
      fields: [
        ['designation', 'Designation'], ['date_of_joining', 'Joined'],
        ['dob', 'DOB'], ['gender', 'Gender'], ['blood_group', 'Blood Group'],
      ],
    },
    {
      title: 'Address', icon: Globe, color: 'sky',
      fields: [
        ['current_address', 'Current Address'], ['permanent_address', 'Permanent Address'],
        ['city', 'City'], ['state', 'State'], ['pincode', 'Pincode'],
      ],
    },
    {
      title: 'Emergency Contact', icon: Phone, color: 'rose',
      fields: [
        ['emergency_contact_name', 'Name'],
        ['emergency_contact_phone', 'Phone'],
        ['emergency_contact_relation', 'Relation'],
      ],
    },
    {
      title: 'KYC / Identity', icon: Shield, color: 'amber',
      fields: [
        ['pan_number', 'PAN'], ['aadhaar_number', 'Aadhaar'], ['gst_number', 'GST'],
      ],
    },
    {
      title: 'Bank Details', icon: CreditCard, color: 'emerald',
      fields: [
        ['bank_account_holder_name', 'Holder'],
        ['bank_account_number', 'Account'],
        ['bank_ifsc', 'IFSC'],
        ['bank_name', 'Bank'],
      ],
    },
  ];

  return (
    <Card className="p-3 border-l-4 border-l-leamss-teal-400" data-testid="onboarding-panel">
      <p className="text-[10px] font-bold uppercase text-slate-500 mb-2 flex items-center gap-1">
        <FileText className="h-3 w-3" />Onboarding Details
      </p>
      <div className="space-y-2">
        {groups.map(g => {
          const visible = g.fields.filter(([k]) => onboarding[k]);
          if (visible.length === 0) return null;
          const Icon = g.icon;
          return (
            <div key={g.title} className="border rounded p-2 bg-slate-50">
              <p className={`text-[10px] font-bold uppercase text-${g.color}-700 mb-1 flex items-center gap-1`}>
                <Icon className="h-3 w-3" />{g.title}
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                {visible.map(([k, label]) => (
                  <div key={k}>
                    <p className="text-[10px] text-slate-500">{label}</p>
                    <p className="font-medium text-slate-800 break-all">{onboarding[k]}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}


function DocumentsPanel({ personId, personType, onChanged }) {
  const [docs, setDocs] = useState([]);
  const [checklist, setChecklist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [pickDocType, setPickDocType] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [dRes, cRes] = await Promise.all([
        axios.get(`${API}/people/${personId}/documents`, { headers }),
        personType ? axios.get(`${API}/people/document-checklist/${personType}`, { headers }).catch(() => ({ data: { items: [] } })) : Promise.resolve({ data: { items: [] } }),
      ]);
      setDocs(dRes.data.items || []);
      setChecklist(cRes.data.items || []);
    } catch (e) { toast.error('Failed to load documents'); }
    finally { setLoading(false); }
  }, [personId, personType]);

  useEffect(() => { if (personId) load(); }, [personId, load]);

  const handleUpload = async (file) => {
    if (!file) return;
    if (!pickDocType) { toast.error('Pick a document type first'); return; }
    setUploading(true);
    try {
      const token = localStorage.getItem('token');
      const fd = new FormData();
      fd.append('file', file);
      fd.append('doc_type', pickDocType);
      const lbl = checklist.find(c => c.key === pickDocType)?.label || pickDocType;
      fd.append('doc_label', lbl);
      await axios.post(`${API}/people/${personId}/documents`, fd, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`${lbl} uploaded`);
      setPickDocType('');
      load();
      onChanged?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Upload failed');
    } finally { setUploading(false); }
  };

  const removeDoc = async (doc) => {
    if (!window.confirm(`Delete ${doc.doc_label || doc.file_name}?`)) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/people/${personId}/documents/${doc.id}`, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Deleted');
      load();
    } catch (e) { toast.error('Delete failed'); }
  };

  const verifyDoc = async (doc) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/people/${personId}/documents/${doc.id}/verify`, {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Marked verified');
      load();
    } catch (e) { toast.error('Verify failed'); }
  };

  const downloadDoc = async (doc) => {
    try {
      const token = localStorage.getItem('token');
      const r = await axios.get(`${API}/people/${personId}/documents/${doc.id}/download`, {
        headers: { Authorization: `Bearer ${token}` }, responseType: 'blob',
      });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url; a.download = doc.file_name; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error('Download failed'); }
  };

  // Build status map: docs that exist by type
  const existingByType = useMemo(() => {
    const m = {};
    docs.forEach(d => { m[d.doc_type] = d; });
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docs]);

  return (
    <Card className="p-3 border-l-4 border-l-amber-400" data-testid="documents-panel">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-bold uppercase text-slate-500 flex items-center gap-1">
          <FileText className="h-3 w-3" />KYC & Onboarding Documents ({docs.length})
        </p>
      </div>

      {/* Required checklist */}
      {checklist.length > 0 && (
        <div className="bg-slate-50 rounded p-2 mb-3" data-testid="doc-checklist">
          <p className="text-[10px] font-semibold text-slate-600 mb-1">Required Checklist:</p>
          <div className="grid grid-cols-2 gap-1 text-[11px]">
            {checklist.map(c => {
              const have = !!existingByType[c.key];
              return (
                <div key={c.key} className="flex items-center gap-1.5">
                  {have ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" />
                  ) : c.required ? (
                    <AlertCircle className="h-3.5 w-3.5 text-rose-500 flex-shrink-0" />
                  ) : (
                    <span className="h-3.5 w-3.5 rounded-full border border-slate-300 flex-shrink-0" />
                  )}
                  <span className={have ? 'text-emerald-700 line-through' : c.required ? 'text-rose-700 font-medium' : 'text-slate-600'}>
                    {c.label}{c.required && !have ? ' *' : ''}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Upload */}
      <div className="grid grid-cols-3 gap-2 mb-3 p-2 border border-dashed border-slate-300 rounded">
        <div className="col-span-2">
          <Select value={pickDocType} onValueChange={setPickDocType}>
            <SelectTrigger className="h-8 text-xs" data-testid="doc-type-select"><SelectValue placeholder="Pick document type" /></SelectTrigger>
            <SelectContent>
              {checklist.length === 0 ? (
                <SelectItem value="other">Other / Custom Document</SelectItem>
              ) : (
                <>
                  {checklist.map(c => (
                    <SelectItem key={c.key} value={c.key}>{c.label}{c.required ? ' *' : ''}</SelectItem>
                  ))}
                  <SelectItem value="other">Other / Custom Document</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="block">
            <Input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
              disabled={uploading || !pickDocType}
              onChange={e => handleUpload(e.target.files?.[0])}
              className="h-8 text-xs file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-amber-500 file:text-white"
              data-testid="doc-file-input"
            />
          </label>
        </div>
      </div>
      <p className="text-[10px] text-slate-500 mb-3">PDF / JPG / PNG / WEBP / DOC / DOCX · Max 10 MB per file.</p>

      {/* List */}
      {loading ? (
        <p className="text-xs text-slate-400 text-center py-4">Loading…</p>
      ) : docs.length === 0 ? (
        <p className="text-xs text-slate-400 italic text-center py-3">No documents uploaded yet.</p>
      ) : (
        <div className="space-y-1">
          {docs.map((d, i) => (
            <div key={d.id} className="flex items-center gap-2 p-2 bg-white border rounded text-xs" data-testid={`doc-row-${i}`}>
              <FileText className="h-4 w-4 text-amber-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{d.doc_label || d.doc_type}</p>
                <p className="text-[10px] text-slate-500 truncate">
                  {d.file_name} · {(d.size_bytes / 1024).toFixed(0)} KB
                  {d.uploaded_at && ` · ${new Date(d.uploaded_at).toLocaleDateString('en-IN')}`}
                </p>
              </div>
              {d.verified && <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">VERIFIED</Badge>}
              <Button size="sm" variant="outline" className="h-6 w-6 p-0" onClick={() => downloadDoc(d)} title="Download" data-testid={`doc-dl-${i}`}>
                <Download className="h-3 w-3" />
              </Button>
              {!d.verified && (
                <Button size="sm" variant="outline" className="h-6 w-6 p-0 text-emerald-600 border-emerald-200" onClick={() => verifyDoc(d)} title="Mark verified" data-testid={`doc-verify-${i}`}>
                  <CheckCircle2 className="h-3 w-3" />
                </Button>
              )}
              <Button size="sm" variant="outline" className="h-6 w-6 p-0 text-rose-600 border-rose-200" onClick={() => removeDoc(d)} title="Delete" data-testid={`doc-del-${i}`}>
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}


// ═══════════════════════════════════════════════════════════════════════
// Person Detail Drawer
// ═══════════════════════════════════════════════════════════════════════
function PersonDetail({ personId, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [resetCreds, setResetCreds] = useState(null);  // Phase 4D — show copy-able dialog on reset

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
        // Phase 4D — Show proper Dialog with copy buttons
        setResetCreds({
          email: r.data.email,
          temp_password: r.data.temp_password,
          role: data?.user?.rbac_role || data?.user?.role,
        });
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
              <Card className="p-3 border-l-4 border-l-leamss-teal-400">
                <p className="text-[10px] font-bold uppercase text-slate-500 mb-2 flex items-center gap-1"><Lock className="h-3 w-3" />Login Credentials & Security</p>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="text-slate-500">Login Email</p>
                    <p className="font-mono text-sm">{data.user.email}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Login ID (internal)</p>
                    <p className="font-mono text-[10px] text-slate-400">{data.user.id}</p>
                  </div>
                  <div>
                    <p className="text-slate-500">Password Status</p>
                    <p className="text-sm">
                      {data.user.must_change_password_on_next_login ? (
                        <Badge className="bg-amber-100 text-amber-700 text-[10px]">⚠️ Must change on next login</Badge>
                      ) : (
                        <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">✓ Active (user-managed)</Badge>
                      )}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      {data.user.password_changed_at ? `Last changed: ${new Date(data.user.password_changed_at).toLocaleDateString()}` : 'Never changed'}
                    </p>
                  </div>
                  <div>
                    <p className="text-slate-500">Last Login</p>
                    <p className="text-sm">{data.user.last_login_at ? new Date(data.user.last_login_at).toLocaleString() : <span className="italic text-slate-400">— never —</span>}</p>
                  </div>
                </div>
                <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800">
                  🔐 <strong>Password Security:</strong> For security, the stored password is hashed (bcrypt) and cannot be retrieved or viewed. Use the <strong>Reset Password</strong> button below to generate a new temporary password that you can share with the user.
                </div>
                <div className="mt-2 text-xs space-y-0.5">
                  <p>Permissions assigned: <strong>{(data.user.permissions || []).length}</strong></p>
                  {data.user.auto_created_from_vendor && <p className="text-leamss-teal-700">🔗 Auto-created from vendor record</p>}
                  {data.user.created_by && <p className="text-slate-400">Onboarded by admin: <code className="text-[10px]">{data.user.created_by.substring(0, 8)}…</code></p>}
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

            {/* Onboarding details */}
            {(data.user?.onboarding || data.vendor?.onboarding) && (
              <OnboardingPanel onboarding={data.user?.onboarding || data.vendor?.onboarding} />
            )}

            {/* Documents */}
            <DocumentsPanel personId={personId} personType={data.person_type} onChanged={load} />
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
      <CredentialsDialog open={!!resetCreds} credentials={resetCreds} onClose={() => setResetCreds(null)} />
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
              <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-2"><Users className="h-7 w-7 text-leamss-teal-600" />People</h1>
              <p className="text-sm text-slate-500 mt-1">Unified directory — employees, partners, vendors, clients. Single source of identity.</p>
            </div>
          </div>
          <Button onClick={() => setWizardOpen(true)} className="bg-leamss-teal-600 hover:bg-leamss-teal-700" data-testid="add-person-btn"><Plus className="h-4 w-4 mr-1.5" />Add Person</Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <Card className="p-3 bg-gradient-to-br from-leamss-teal-50 to-leamss-teal-100 border-leamss-teal-300" data-testid="stat-total">
            <p className="text-[10px] uppercase font-bold text-leamss-teal-800">Total People</p>
            <p className="text-2xl font-extrabold text-leamss-teal-900 mt-0.5">{stats?.total || 0}</p>
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
              className={`px-4 py-2 text-sm font-medium border-b-2 flex items-center gap-1.5 transition ${tab === k ? 'border-leamss-teal-600 text-leamss-teal-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
              data-testid={`tab-${k}`}>
              {Icon && <Icon className="h-3.5 w-3.5" />}{label}
              {tab !== 'all' && k !== 'all' && tab === k && <Badge className="ml-1 bg-leamss-teal-100 text-leamss-teal-700 text-[10px]">{filtered.length}</Badge>}
            </button>
          ))}
        </div>

        {/* List */}
        {loading ? (
          <Card className="p-12 text-center"><Sparkles className="h-10 w-10 text-leamss-teal-300 mx-auto animate-pulse mb-2" /><p className="text-slate-500">Loading…</p></Card>
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
