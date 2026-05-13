import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Shield, AlertTriangle, LogOut } from 'lucide-react';
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

/**
 * Forced password change after admin reset. Blocks access to all routes
 * until the user picks a new password.
 */
export default function ForceChangePassword() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    axios.get(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        setUser(r.data);
        // If flag already cleared somehow, redirect away
        if (!r.data.must_change_password_on_next_login) {
          // Fallback redirect based on role
          const role = r.data.rbac_role || r.data.role;
          const fixed = { admin: '/admin', admin_owner: '/admin', partner: '/partner', case_manager: '/case-manager', client: '/client' };
          navigate(fixed[role] || '/portal/welcome');
        }
      })
      .catch(() => navigate('/'));
  }, [navigate]);

  const submit = async (e) => {
    e.preventDefault();
    if (newPwd !== confirmPwd) { toast.error('Passwords do not match'); return; }
    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/auth/change-password`, {
        current_password: oldPwd,
        new_password: newPwd,
        confirm_password: confirmPwd,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Password updated. Please login again.');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setTimeout(() => navigate('/'), 1200);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Update failed';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  const cancel = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  if (!user) return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading...</div>;

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50 flex items-center justify-center p-4" data-testid="force-change-pwd-page">
      <Card className="w-full max-w-md p-8 shadow-xl border-2 border-amber-300">
        <div className="text-center mb-6">
          <div className="w-14 h-14 mx-auto rounded-full bg-amber-100 flex items-center justify-center mb-3">
            <AlertTriangle className="h-7 w-7 text-amber-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Password Change Required</h1>
          <p className="text-sm text-slate-600 mt-1">Your admin reset your password. Please choose a new one to continue.</p>
        </div>

        <Card className="p-3 bg-slate-100 text-xs text-slate-700 mb-4">
          <strong>Account:</strong> {user.email}<br />
          <strong>Role:</strong> {user.designation || user.rbac_role}
        </Card>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <Label>Current (Temporary) Password</Label>
            <Input type="password" value={oldPwd} onChange={(e) => setOldPwd(e.target.value)} required data-testid="old-pwd" />
          </div>
          <div>
            <Label>New Password</Label>
            <Input type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required data-testid="new-pwd" />
            <PasswordStrengthMeter password={newPwd} />
          </div>
          <div>
            <Label>Confirm New Password</Label>
            <Input type="password" value={confirmPwd} onChange={(e) => setConfirmPwd(e.target.value)} required data-testid="confirm-pwd" />
          </div>
          <Button type="submit" disabled={submitting || newPwd !== confirmPwd || !newPwd} className="w-full bg-amber-600 hover:bg-amber-700 text-white" data-testid="submit-change-pwd">
            <Shield className="h-4 w-4 mr-2" /> {submitting ? 'Updating...' : 'Update Password'}
          </Button>
          <Button type="button" variant="outline" onClick={cancel} className="w-full" data-testid="cancel-change-pwd">
            <LogOut className="h-4 w-4 mr-2" /> Logout & Try Later
          </Button>
        </form>
      </Card>
    </div>
  );
}
