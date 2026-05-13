import { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (!email.includes('@')) { toast.error('Valid email required'); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/auth/forgot-password`, { email });
      setSubmitted(true);
    } catch {
      // Always show success (no email enumeration)
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4" data-testid="forgot-password-page">
      <Card className="w-full max-w-md p-8 shadow-xl">
        {!submitted ? (
          <>
            <h1 className="text-2xl font-bold text-slate-900">Forgot Password?</h1>
            <p className="text-sm text-slate-500 mt-1">Enter your email — we'll send reset instructions.</p>
            <form onSubmit={submit} className="space-y-4 mt-6">
              <div>
                <Label>Email</Label>
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@leamss.com" data-testid="forgot-email" required />
              </div>
              <Button type="submit" disabled={loading} className="w-full bg-teal-700 hover:bg-teal-800 text-white" data-testid="forgot-submit">
                <Mail className="h-4 w-4 mr-2" /> {loading ? 'Sending...' : 'Send Reset Link'}
              </Button>
            </form>
            <div className="mt-6 text-center">
              <Link to="/" className="text-sm text-slate-500 hover:text-slate-700 flex items-center justify-center gap-1" data-testid="back-to-login">
                <ArrowLeft className="h-3.5 w-3.5" /> Back to login
              </Link>
            </div>
            <Card className="mt-4 p-3 bg-amber-50 border-amber-200 text-xs text-amber-800">
              📨 Email service is activating soon. For now, please contact admin for password reset assistance.
            </Card>
          </>
        ) : (
          <div className="text-center" data-testid="forgot-success">
            <div className="w-16 h-16 mx-auto rounded-full bg-emerald-100 flex items-center justify-center mb-4">
              <CheckCircle2 className="h-8 w-8 text-emerald-600" />
            </div>
            <h2 className="text-xl font-bold text-slate-900">Check Your Email</h2>
            <p className="text-sm text-slate-600 mt-2">
              If an account with <strong>{email}</strong> exists, we've sent reset instructions.
            </p>
            <Card className="mt-4 p-3 bg-slate-50 text-xs text-slate-600 text-left">
              <strong>Note:</strong> Emails currently mocked. Contact your admin to retrieve the reset link until email service is live.
            </Card>
            <Button onClick={() => navigate('/')} variant="outline" className="mt-6 w-full" data-testid="back-btn">Back to Login</Button>
          </div>
        )}
      </Card>
    </div>
  );
}
