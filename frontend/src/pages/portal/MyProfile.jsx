import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import {
  User, Briefcase, Building2, CreditCard, Phone, Shield, FileText, Upload,
  Check, Loader2, ArrowLeft, History, AlertCircle, Mail,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SAVE_DEBOUNCE_MS = 1000;

// ─────────────────── Auto-save helper ───────────────────
const useDebouncedSave = (saveFn, delay = SAVE_DEBOUNCE_MS) => {
  const timer = useRef(null);
  const [status, setStatus] = useState('idle'); // idle | typing | saving | saved | error
  const trigger = useCallback((payload) => {
    setStatus('typing');
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setStatus('saving');
      try {
        await saveFn(payload);
        setStatus('saved');
        setTimeout(() => setStatus('idle'), 2000);
      } catch (e) {
        setStatus('error');
        toast.error(e?.response?.data?.detail || 'Save failed');
      }
    }, delay);
  }, [saveFn, delay]);
  return [status, trigger];
};

const SaveIndicator = ({ status }) => {
  if (status === 'idle') return null;
  const map = {
    typing: { icon: Loader2, label: 'Typing…', class: 'text-slate-400', spin: false },
    saving: { icon: Loader2, label: 'Saving…', class: 'text-leamss-teal-600', spin: true },
    saved: { icon: Check, label: 'Saved', class: 'text-emerald-600', spin: false },
    error: { icon: AlertCircle, label: 'Save failed', class: 'text-leamss-red-600', spin: false },
  };
  const m = map[status];
  if (!m) return null;
  const Icon = m.icon;
  return (
    <span className={`text-xs font-medium inline-flex items-center gap-1 ${m.class}`} data-testid={`save-status-${status}`}>
      <Icon className={`h-3 w-3 ${m.spin ? 'animate-spin' : ''}`} /> {m.label}
    </span>
  );
};

// ─────────────────── Section card wrapper ───────────────────
const Section = ({ icon: Icon, title, status, children, accent = 'leamss-teal', testId }) => (
  <Card className="p-5" data-testid={testId}>
    <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
      <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
        <Icon className={`h-4 w-4 text-${accent}-600`} /> {title}
      </h3>
      <SaveIndicator status={status} />
    </div>
    <div className="space-y-3">{children}</div>
  </Card>
);

// ─────────────────── Main page ───────────────────
export default function MyProfile() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [history, setHistory] = useState([]);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false);
  const token = localStorage.getItem('token');
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  // Form state per section
  const [personalForm, setPersonalForm] = useState({});
  const [bankForm, setBankForm] = useState({});
  const [emergencyForm, setEmergencyForm] = useState({});

  // Doc upload draft
  const [docDraft, setDocDraft] = useState({ doc_type: '', file_name: '', file_url: '' });

  const load = useCallback(async () => {
    try {
      const [p, h, d] = await Promise.all([
        axios.get(`${API}/employees/me/profile`, auth),
        axios.get(`${API}/employees/me/audit-history`, auth).catch(() => ({ data: [] })),
        axios.get(`${API}/employees/me/documents`, auth).catch(() => ({ data: [] })),
      ]);
      setProfile(p.data);
      setHistory(h.data);
      setDocs(d.data);
      setPersonalForm({
        mobile: p.data.mobile || '',
        alt_contact: p.data.alt_contact || '',
        address: p.data.address || {},
      });
      setBankForm({
        bank_account: p.data.bank_account || {},
        pan_number: p.data.pan_number || '',
      });
      setEmergencyForm(p.data.emergency_contact || {});
    } catch (e) {
      navigate('/');
    } finally {
      setLoading(false);
    }
  }, [navigate, token]);

  useEffect(() => {
    if (!token) { navigate('/'); return; }
    load();
  }, [load, navigate, token]);

  // Section savers
  const savePersonal = useCallback(async (payload) => {
    await axios.patch(`${API}/employees/me/section/personal`, payload, auth);
    load();
  }, [load]);
  const saveBank = useCallback(async (payload) => {
    await axios.patch(`${API}/employees/me/section/bank`, payload, auth);
    load();
  }, [load]);
  const saveEmergency = useCallback(async (payload) => {
    await axios.patch(`${API}/employees/me/section/emergency`, { emergency_contact: payload }, auth);
    load();
  }, [load]);

  const [personalStatus, triggerPersonal] = useDebouncedSave(savePersonal);
  const [bankStatus, triggerBank] = useDebouncedSave(saveBank);
  const [emergencyStatus, triggerEmergency] = useDebouncedSave(saveEmergency);

  const handlePersonal = (patch) => {
    const next = { ...personalForm, ...patch };
    setPersonalForm(next);
    triggerPersonal(next);
  };
  const handlePersonalAddress = (key, val) => {
    const next = { ...personalForm, address: { ...(personalForm.address || {}), [key]: val } };
    setPersonalForm(next);
    triggerPersonal({ address: next.address });
  };
  const handleBank = (key, val) => {
    const next = { ...bankForm, bank_account: { ...(bankForm.bank_account || {}), [key]: val } };
    setBankForm(next);
    triggerBank({ bank_account: next.bank_account });
  };
  const handlePAN = (val) => {
    const next = { ...bankForm, pan_number: val.toUpperCase() };
    setBankForm(next);
    triggerBank({ pan_number: next.pan_number });
  };
  const handleEmergency = (key, val) => {
    const next = { ...emergencyForm, [key]: val };
    setEmergencyForm(next);
    triggerEmergency(next);
  };

  const handleDocUpload = async () => {
    if (!docDraft.doc_type || !docDraft.file_url) {
      toast.error('Document type and file URL are required');
      return;
    }
    try {
      await axios.post(`${API}/employees/me/documents`, docDraft, auth);
      toast.success('Document recorded — pending HR verification');
      setDocDraft({ doc_type: '', file_name: '', file_url: '' });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    }
  };

  if (loading || !profile) {
    return <div className="flex items-center justify-center h-screen text-slate-500">Loading your profile…</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50" data-testid="my-profile-page">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/portal-hub')} data-testid="back-hub-btn">
              <ArrowLeft className="h-4 w-4 mr-1.5" /> Hub
            </Button>
            <div>
              <h1 className="text-lg font-bold text-slate-900">My Profile</h1>
              <p className="text-xs text-slate-500">Self-service · Auto-saves as you type</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="sm" data-testid="open-history-btn">
                  <History className="h-3.5 w-3.5 mr-1.5" /> History
                </Button>
              </SheetTrigger>
              <SheetContent data-testid="history-drawer">
                <SheetHeader><SheetTitle>Audit History</SheetTitle></SheetHeader>
                <div className="mt-4 space-y-2 max-h-[80vh] overflow-y-auto pr-2">
                  {history.length === 0 && <p className="text-sm text-slate-500 italic">No edits yet</p>}
                  {history.map(h => (
                    <Card key={h.id} className="p-3 text-xs" data-testid={`history-${h.id}`}>
                      <div className="flex items-center justify-between">
                        <Badge variant="outline">{(h.action || '').replace('section_updated:', '')}</Badge>
                        <span className="text-slate-400">{new Date(h.created_at).toLocaleString()}</span>
                      </div>
                      {h.details?.after && (
                        <div className="mt-2 text-slate-600 font-mono text-[10px] truncate">
                          {Object.keys(h.details.after).join(', ')}
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 md:px-6 py-6 space-y-5">
        {/* Hero card with profile snapshot */}
        <Card className="p-5 bg-gradient-to-r from-leamss-teal-50 via-white to-leamss-orange-50 border-leamss-teal-100" data-testid="profile-hero">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-leamss-teal-500 to-leamss-teal-700 flex items-center justify-center text-white font-bold text-2xl shadow-md">
              {(profile.name || '?').charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-xl font-bold text-slate-900">{profile.name}</h2>
              <p className="text-sm text-slate-600">{profile.designation || profile.rbac_role} · {profile.department || 'No dept'}</p>
              <div className="flex gap-2 mt-2 flex-wrap">
                <Badge variant="outline" className="font-mono text-[10px]">{profile.employee_id || '—'}</Badge>
                <Badge className="bg-emerald-100 text-emerald-700 text-[10px]">{profile.employment_status || 'active'}</Badge>
                {profile.work_mode && <Badge variant="outline" className="text-[10px] capitalize">{profile.work_mode}</Badge>}
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Reports to</p>
              <p className="text-sm font-medium text-slate-700">{profile.manager?.name || '—'}</p>
            </div>
          </div>
        </Card>

        {/* PERSONAL */}
        <Section icon={User} title="Personal" status={personalStatus} testId="section-personal">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label>Email <span className="text-slate-400">(read-only)</span></Label>
              <Input value={profile.email || ''} disabled data-testid="field-email" />
            </div>
            <div>
              <Label>Mobile</Label>
              <Input
                value={personalForm.mobile || ''}
                onChange={e => handlePersonal({ mobile: e.target.value })}
                placeholder="+91 98765 43210"
                data-testid="field-mobile"
              />
            </div>
            <div>
              <Label>Alternate contact</Label>
              <Input
                value={personalForm.alt_contact || ''}
                onChange={e => handlePersonal({ alt_contact: e.target.value })}
                placeholder="WhatsApp / parent / spouse"
                data-testid="field-alt-contact"
              />
            </div>
            <div>
              <Label>Date of birth <span className="text-slate-400">(read-only)</span></Label>
              <Input value={profile.date_of_birth || '—'} disabled data-testid="field-dob" />
            </div>
            <div className="md:col-span-2">
              <Label>Address</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-1">
                <Input
                  placeholder="Line 1"
                  value={personalForm.address?.line1 || ''}
                  onChange={e => handlePersonalAddress('line1', e.target.value)}
                  data-testid="field-address-line1"
                />
                <Input
                  placeholder="Line 2 (optional)"
                  value={personalForm.address?.line2 || ''}
                  onChange={e => handlePersonalAddress('line2', e.target.value)}
                  data-testid="field-address-line2"
                />
                <Input
                  placeholder="City"
                  value={personalForm.address?.city || ''}
                  onChange={e => handlePersonalAddress('city', e.target.value)}
                  data-testid="field-address-city"
                />
                <Input
                  placeholder="State"
                  value={personalForm.address?.state || ''}
                  onChange={e => handlePersonalAddress('state', e.target.value)}
                  data-testid="field-address-state"
                />
                <Input
                  placeholder="PIN code"
                  value={personalForm.address?.pincode || ''}
                  onChange={e => handlePersonalAddress('pincode', e.target.value)}
                  data-testid="field-address-pincode"
                />
                <Input
                  placeholder="Country"
                  value={personalForm.address?.country || ''}
                  onChange={e => handlePersonalAddress('country', e.target.value)}
                  data-testid="field-address-country"
                />
              </div>
            </div>
          </div>
        </Section>

        {/* PROFESSIONAL (read-only) */}
        <Section icon={Briefcase} title="Professional" status="idle" testId="section-professional">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-xs text-slate-500">Department</p>
              <p className="font-medium text-slate-800 mt-0.5 capitalize">{profile.department || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Designation</p>
              <p className="font-medium text-slate-800 mt-0.5">{profile.designation || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Manager</p>
              <p className="font-medium text-slate-800 mt-0.5">{profile.manager?.name || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Date of joining</p>
              <p className="font-medium text-slate-800 mt-0.5">{profile.date_of_joining ? new Date(profile.date_of_joining).toLocaleDateString() : '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Employment type</p>
              <p className="font-medium text-slate-800 mt-0.5 capitalize">{(profile.employment_type || '—').replace('_', ' ')}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Work mode</p>
              <p className="font-medium text-slate-800 mt-0.5 capitalize">{profile.work_mode || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Work location</p>
              <p className="font-medium text-slate-800 mt-0.5">{profile.work_location || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Permissions</p>
              <p className="font-medium text-slate-800 mt-0.5">{profile.permissions?.length || 0}</p>
            </div>
          </div>
          <p className="text-xs text-slate-400 italic mt-2 flex items-center gap-1"><Shield className="h-3 w-3" /> To change any field above, please contact HR.</p>
        </Section>

        {/* BANK & TAX */}
        <Section icon={CreditCard} title="Bank & Tax" status={bankStatus} testId="section-bank">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label>Account number</Label>
              <Input
                value={bankForm.bank_account?.account_number || ''}
                onChange={e => handleBank('account_number', e.target.value)}
                placeholder="1234567890"
                data-testid="field-account-number"
              />
            </div>
            <div>
              <Label>IFSC</Label>
              <Input
                value={bankForm.bank_account?.ifsc || ''}
                onChange={e => handleBank('ifsc', e.target.value.toUpperCase())}
                placeholder="SBIN0001234"
                maxLength={11}
                data-testid="field-ifsc"
              />
            </div>
            <div>
              <Label>Bank name</Label>
              <Input
                value={bankForm.bank_account?.bank_name || ''}
                onChange={e => handleBank('bank_name', e.target.value)}
                placeholder="State Bank of India"
                data-testid="field-bank-name"
              />
            </div>
            <div>
              <Label>Account holder name</Label>
              <Input
                value={bankForm.bank_account?.holder_name || ''}
                onChange={e => handleBank('holder_name', e.target.value)}
                placeholder="As per bank records"
                data-testid="field-holder-name"
              />
            </div>
            <div>
              <Label>PAN number</Label>
              <Input
                value={bankForm.pan_number || ''}
                onChange={e => handlePAN(e.target.value)}
                placeholder="ABCDE1234F"
                maxLength={10}
                data-testid="field-pan"
              />
            </div>
          </div>
          <p className="text-xs text-amber-700 mt-2 flex items-center gap-1 bg-amber-50 px-2 py-1.5 rounded">
            <Shield className="h-3 w-3" /> Bank & PAN changes are verified by HR before payroll updates.
          </p>
        </Section>

        {/* EMERGENCY */}
        <Section icon={Phone} title="Emergency Contact" status={emergencyStatus} testId="section-emergency">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label>Name</Label>
              <Input
                value={emergencyForm.name || ''}
                onChange={e => handleEmergency('name', e.target.value)}
                placeholder="Family member name"
                data-testid="field-emergency-name"
              />
            </div>
            <div>
              <Label>Relation</Label>
              <Input
                value={emergencyForm.relation || ''}
                onChange={e => handleEmergency('relation', e.target.value)}
                placeholder="Father / Mother / Spouse"
                data-testid="field-emergency-relation"
              />
            </div>
            <div>
              <Label>Primary mobile</Label>
              <Input
                value={emergencyForm.mobile || ''}
                onChange={e => handleEmergency('mobile', e.target.value)}
                placeholder="+91 …"
                data-testid="field-emergency-mobile"
              />
            </div>
            <div>
              <Label>Alternate mobile</Label>
              <Input
                value={emergencyForm.alt_mobile || ''}
                onChange={e => handleEmergency('alt_mobile', e.target.value)}
                placeholder="Optional"
                data-testid="field-emergency-alt"
              />
            </div>
          </div>
        </Section>

        {/* DOCUMENTS */}
        <Section icon={FileText} title={`Documents (${docs.length})`} status="idle" testId="section-documents" accent="leamss-orange">
          {docs.length === 0 && (
            <p className="text-sm text-slate-500 italic">No documents uploaded yet. Add your first below.</p>
          )}
          {docs.length > 0 && (
            <div className="space-y-2">
              {docs.map(d => (
                <div key={d.id} className="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-100" data-testid={`doc-${d.id}`}>
                  <div className="flex items-center gap-3">
                    <div className="p-1.5 bg-white rounded">
                      <FileText className="h-4 w-4 text-leamss-orange-500" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-800">{d.doc_type}</p>
                      <p className="text-xs text-slate-500">{d.file_name} · {new Date(d.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <Badge className={d.status === 'verified' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>{d.status}</Badge>
                </div>
              ))}
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-700 mb-2">Upload new document</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <Input
                placeholder="Doc type (e.g. Aadhar, PAN, Resume)"
                value={docDraft.doc_type}
                onChange={e => setDocDraft({ ...docDraft, doc_type: e.target.value })}
                data-testid="upload-doc-type"
              />
              <Input
                placeholder="File name"
                value={docDraft.file_name}
                onChange={e => setDocDraft({ ...docDraft, file_name: e.target.value })}
                data-testid="upload-file-name"
              />
              <Input
                placeholder="File URL (paste link)"
                value={docDraft.file_url}
                onChange={e => setDocDraft({ ...docDraft, file_url: e.target.value })}
                data-testid="upload-file-url"
              />
            </div>
            <Button onClick={handleDocUpload} className="mt-2 bg-leamss-orange-500 hover:bg-leamss-orange-600 text-white" size="sm" data-testid="upload-doc-btn">
              <Upload className="h-3.5 w-3.5 mr-1.5" /> Add document
            </Button>
            <p className="text-[10px] text-slate-400 mt-1">Cloud upload integration (Phase 21.C) coming. For now paste a link.</p>
          </div>
        </Section>

        {/* Email change disabled hint */}
        <Card className="p-3 border-dashed border-slate-300 bg-slate-50/50" data-testid="email-change-hint">
          <p className="text-xs text-slate-500 flex items-center gap-2">
            <Mail className="h-3 w-3 text-leamss-teal-500" /> Need to change your email or trigger a 2FA reset? Contact HR — only they can do that.
          </p>
        </Card>
      </div>
    </div>
  );
}
