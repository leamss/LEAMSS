/**
 * Phase 4C.6 — Vendor Accept Invite Page.
 * Public page consumed via /vendor/accept-invite/{token}.
 * Sets password, links user, then redirects to login.
 */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Shield, Briefcase, CheckCircle } from 'lucide-react';
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;


export default function VendorAcceptInvite() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async () => {
    if (password !== confirm) { toast.error('Passwords do not match'); return; }
    setSubmitting(true);
    try {
      const r = await axios.post(`${API}/vendor-portal/accept-invite`, { token, password });
      toast.success(r.data.message || 'Account activated');
      setDone(true);
      setTimeout(() => navigate('/'), 2500);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Activation failed');
    } finally { setSubmitting(false); }
  };

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-blue-50 p-6">
        <Card className="p-8 max-w-md text-center" data-testid="vendor-accept-success">
          <CheckCircle className="h-16 w-16 text-emerald-500 mx-auto mb-4" />
          <h1 className="text-2xl font-extrabold text-slate-800 mb-2">Welcome aboard!</h1>
          <p className="text-sm text-slate-600">Your vendor account has been activated. Redirecting to login…</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-blue-50 to-slate-50 p-6">
      <Card className="p-8 max-w-md w-full" data-testid="vendor-accept-page">
        <div className="text-center mb-6">
          <Briefcase className="h-12 w-12 text-indigo-600 mx-auto mb-2" />
          <h1 className="text-2xl font-extrabold text-slate-800">Activate Vendor Portal</h1>
          <p className="text-sm text-slate-500 mt-1">Set your password to access your assignments & payments</p>
        </div>
        <div className="space-y-4">
          <div>
            <Label className="text-xs font-bold">New Password *</Label>
            <Input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 8 chars, mixed case, digit, special" data-testid="vendor-password" />
            {password.length > 0 && <PasswordStrengthMeter password={password} />}
          </div>
          <div>
            <Label className="text-xs font-bold">Confirm Password *</Label>
            <Input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} data-testid="vendor-confirm" />
            {confirm.length > 0 && password !== confirm && <p className="text-xs text-rose-600 mt-1">Passwords don&apos;t match</p>}
          </div>
          <Button onClick={submit} disabled={submitting || password.length < 8 || password !== confirm} className="w-full bg-indigo-600 hover:bg-indigo-700" data-testid="vendor-activate-btn">
            <Shield className="h-4 w-4 mr-1.5" />
            {submitting ? 'Activating…' : 'Activate Account'}
          </Button>
        </div>
        <p className="mt-6 text-[11px] text-center text-slate-400">
          By activating, you agree to LEAMSS terms for external vendors.<br />
          For support: contact your administrator.
        </p>
      </Card>
    </div>
  );
}
