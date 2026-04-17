import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, AlertTriangle, Mail, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function MagicLinkLogin() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState('loading'); // loading | fallback | error
  const [error, setError] = useState('');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return; // guard against StrictMode double-run
    attempted.current = true;
    axios.post(`${API}/pre-assess-portal/magic-login`, { token })
      .then(r => {
        localStorage.setItem('token', r.data.token);
        localStorage.setItem('user', JSON.stringify(r.data.user));
        toast.success(`Welcome back, ${r.data.user.name}!`);
        navigate('/client');
      })
      .catch(e => {
        setError(e?.response?.data?.detail || 'Login link invalid or expired');
        setState('fallback');
      });
  }, [token, navigate]);

  const requestOtp = async () => {
    if (!email.trim()) { toast.error('Enter your email'); return; }
    setBusy(true);
    try {
      await axios.post(`${API}/pre-assess-portal/otp/request`, { email });
      toast.success('OTP sent to your email (check spam)');
      setOtpSent(true);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not send OTP');
    } finally {
      setBusy(false);
    }
  };

  const verifyOtp = async () => {
    if (!code.trim()) { toast.error('Enter OTP'); return; }
    setBusy(true);
    try {
      const r = await axios.post(`${API}/pre-assess-portal/otp/verify`, { email, code });
      localStorage.setItem('token', r.data.token);
      localStorage.setItem('user', JSON.stringify(r.data.user));
      toast.success('Logged in');
      navigate('/client');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Invalid OTP');
    } finally {
      setBusy(false);
    }
  };

  if (state === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin text-[#2a777a] mx-auto mb-3" />
          <p className="text-slate-500 text-sm">Logging you in…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <Card className="max-w-md w-full p-8" data-testid="magic-fallback">
        <div className="text-center mb-5">
          <div className="w-14 h-14 mx-auto bg-amber-100 rounded-full flex items-center justify-center mb-3">
            <AlertTriangle className="h-7 w-7 text-amber-500" />
          </div>
          <h1 className="text-xl font-bold text-slate-800">Login Link Expired</h1>
          <p className="text-sm text-slate-500 mt-1">{error}</p>
        </div>

        <div className="space-y-3">
          <p className="text-sm text-slate-600 flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4 text-[#2a777a]" /> Use OTP to login
          </p>
          <div>
            <Label className="text-xs font-semibold">Email</Label>
            <div className="relative mt-1">
              <Mail className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <Input value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com" className="pl-9" disabled={otpSent} data-testid="otp-email" />
            </div>
          </div>
          {otpSent && (
            <div>
              <Label className="text-xs font-semibold">OTP (6 digits)</Label>
              <Input value={code} onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="123456" className="mt-1 text-center text-lg tracking-widest font-mono"
                maxLength={6} data-testid="otp-code" />
            </div>
          )}
          {!otpSent ? (
            <Button onClick={requestOtp} disabled={busy} className="w-full bg-[#2a777a] hover:bg-[#236466]" data-testid="otp-request-btn">
              {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null} Send OTP
            </Button>
          ) : (
            <Button onClick={verifyOtp} disabled={busy || code.length < 6} className="w-full bg-[#f7620b] hover:bg-[#e55a09]" data-testid="otp-verify-btn">
              {busy ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null} Verify & Login
            </Button>
          )}
          {otpSent && (
            <button onClick={() => { setOtpSent(false); setCode(''); }} className="text-xs text-[#2a777a] hover:underline w-full text-center">
              Re-send OTP to different email
            </button>
          )}
        </div>
      </Card>
    </div>
  );
}
