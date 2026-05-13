import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { KeyRound, CheckCircle2, XCircle } from 'lucide-react';
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ResetPasswordWithToken() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) {
      toast.error('No reset token provided. Use the link from your email.');
    }
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (newPwd !== confirmPwd) { toast.error('Passwords do not match'); return; }
    setSubmitting(true);
    try {
      await axios.post(`${API}/auth/reset-password-with-token`, {
        token, new_password: newPwd, confirm_password: confirmPwd,
      });
      setDone(true);
      setTimeout(() => navigate('/'), 2500);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Reset failed';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4" data-testid="reset-pwd-page">
      <Card className="w-full max-w-md p-8 shadow-xl">
        {!token ? (
          <div className="text-center">
            <XCircle className="h-12 w-12 mx-auto text-rose-500 mb-3" />
            <h2 className="text-xl font-bold text-slate-900">Invalid Reset Link</h2>
            <p className="text-sm text-slate-500 mt-2">No token in URL. Request a new link.</p>
            <Button onClick={() => navigate('/forgot-password')} className="mt-4 bg-teal-700 text-white">Request new link</Button>
          </div>
        ) : done ? (
          <div className="text-center" data-testid="reset-success">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 flex items-center justify-center mb-4">
              <CheckCircle2 className="h-8 w-8 text-emerald-600" />
            </div>
            <h2 className="text-xl font-bold text-slate-900">Password Reset!</h2>
            <p className="text-sm text-slate-500 mt-2">Redirecting to login...</p>
          </div>
        ) : (
          <>
            <KeyRound className="h-10 w-10 text-teal-700 mb-3" />
            <h1 className="text-2xl font-bold text-slate-900">Set New Password</h1>
            <p className="text-sm text-slate-500 mt-1">Choose a strong password you haven't used recently.</p>
            <form onSubmit={submit} className="space-y-4 mt-6">
              <div>
                <Label>New Password</Label>
                <Input type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required data-testid="new-pwd" />
                <PasswordStrengthMeter password={newPwd} />
              </div>
              <div>
                <Label>Confirm Password</Label>
                <Input type="password" value={confirmPwd} onChange={(e) => setConfirmPwd(e.target.value)} required data-testid="confirm-pwd" />
                {confirmPwd && newPwd && confirmPwd !== newPwd && (
                  <p className="text-xs text-rose-600 mt-1">Passwords don't match</p>
                )}
              </div>
              <Button type="submit" disabled={submitting || newPwd !== confirmPwd || !newPwd} className="w-full bg-teal-700 hover:bg-teal-800 text-white" data-testid="submit-reset">
                {submitting ? 'Resetting...' : 'Set New Password'}
              </Button>
            </form>
          </>
        )}
      </Card>
    </div>
  );
}
