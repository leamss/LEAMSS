/**
 * Step 2 — Client Portal Login Page
 *
 * Visually distinct from /login (staff). Stores token under `client_token`.
 */
import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Mail, Lock, AlertCircle, Briefcase } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ClientPortalLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');

  const onLogin = async (e) => {
    e.preventDefault();
    setErr('');
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/client-auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await r.json();
      if (!r.ok) { setErr(data.detail || 'Login failed'); return; }
      localStorage.setItem('client_token', data.token);
      localStorage.setItem('client_info', JSON.stringify(data.client));
      toast.success(`Welcome back, ${data.client.name?.split(' ')[0] || 'Client'}!`);
      window.location.href = '/client-portal/dashboard';
    } catch (e) {
      setErr('Network error. Please try again.');
    } finally { setBusy(false); }
  };

  const onForgot = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await fetch(`${API}/api/client-auth/forgot-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail }),
      });
      toast.success('If an account exists, a reset link has been sent.');
      setShowForgot(false);
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-stretch bg-leamss-bg_white" data-testid="client-portal-login">
      {/* Left visual */}
      <div className="hidden lg:flex flex-1 bg-gradient-to-br from-leamss-teal to-emerald-700 text-white p-12 flex-col justify-between">
        <div>
          <div className="text-2xl font-bold mb-2">
            <span className="text-white">LE</span>
            <span className="text-leamss-orange">AM</span>
            <span style={{color: '#fda4af'}}>SS</span>
          </div>
          <p className="text-sm opacity-80">Client Portal</p>
        </div>
        <div>
          <Briefcase className="h-14 w-14 mb-4 opacity-90" />
          <h2 className="text-3xl font-bold leading-tight mb-3">Track your migration journey with LEAMSS</h2>
          <p className="text-sm opacity-90 leading-relaxed">Review your documents, info sheet, and proposal — all in one secure portal. Need help? Your dedicated migration consultant is one click away.</p>
        </div>
        <p className="text-xs opacity-60">© LEAMSS · Licensed Migration Specialists</p>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <Card className="w-full max-w-md p-8 shadow-xl border-leamss-teal/20">
          <h1 className="text-2xl font-bold text-leamss-teal mb-1">Welcome back</h1>
          <p className="text-sm text-slate-500 mb-6">Login to your LEAMSS Client Portal</p>

          {err && (
            <div className="bg-red-50 border border-leamss-red/30 text-leamss-red rounded p-3 mb-4 flex items-start gap-2 text-sm" data-testid="login-error">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" /> {err}
            </div>
          )}

          {!showForgot ? (
            <form onSubmit={onLogin} className="space-y-4">
              <div>
                <Label className="text-xs uppercase font-bold text-slate-600">Email</Label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                  <Input type="email" required value={email}
                         onChange={(e) => setEmail(e.target.value)}
                         placeholder="your@email.com" className="pl-9"
                         data-testid="client-login-email" />
                </div>
              </div>
              <div>
                <Label className="text-xs uppercase font-bold text-slate-600">Password</Label>
                <div className="relative mt-1">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                  <Input type="password" required value={password}
                         onChange={(e) => setPassword(e.target.value)}
                         placeholder="Your password" className="pl-9"
                         data-testid="client-login-password" />
                </div>
              </div>
              <Button type="submit" disabled={busy}
                      className="w-full bg-leamss-orange hover:bg-leamss-orange/90 text-white font-bold"
                      data-testid="client-login-submit">
                {busy ? 'Signing in…' : 'Login →'}
              </Button>
              <div className="flex justify-between items-center text-sm">
                <button type="button" onClick={() => setShowForgot(true)}
                        className="text-leamss-teal hover:underline"
                        data-testid="forgot-password-link">
                  Forgot password?
                </button>
                <a href="/" className="text-slate-400 hover:underline">Staff login →</a>
              </div>
            </form>
          ) : (
            <form onSubmit={onForgot} className="space-y-4">
              <h2 className="text-lg font-bold">Reset your password</h2>
              <p className="text-sm text-slate-500">Enter your email and we'll send you a reset link.</p>
              <Input type="email" required value={forgotEmail}
                     onChange={(e) => setForgotEmail(e.target.value)}
                     placeholder="your@email.com"
                     data-testid="forgot-email-input" />
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setShowForgot(false)} className="flex-1">
                  Back
                </Button>
                <Button type="submit" disabled={busy}
                        className="flex-1 bg-leamss-teal hover:bg-leamss-teal/90 text-white"
                        data-testid="forgot-submit">
                  Send link
                </Button>
              </div>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
