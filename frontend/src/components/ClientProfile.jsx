import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { User, Mail, Phone, Lock, Save, Bell, BellOff, Globe, Shield, Eye, EyeOff } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ClientProfile = ({ user, onProfileUpdate }) => {
  const [name, setName] = useState(user?.name || '');
  const [mobile, setMobile] = useState(user?.mobile || '');
  const [language, setLanguage] = useState(user?.preferred_language || 'en');
  const [saving, setSaving] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [changingPass, setChangingPass] = useState(false);

  const [prefs, setPrefs] = useState({
    email: true, sms: false, in_app: true,
    case_updates: true, payment_reminders: true,
    document_requests: true, marketing: false
  });
  const [savingPrefs, setSavingPrefs] = useState(false);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  useEffect(() => {
    axios.get(`${API}/auth/notifications-preferences`, getAuthHeader())
      .then(res => { if (res.data) setPrefs(res.data); })
      .catch(() => {});
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const res = await axios.put(`${API}/auth/update-profile`, {
        name, mobile, preferred_language: language
      }, getAuthHeader());
      toast.success('Profile updated successfully!');
      if (onProfileUpdate && res.data.user) {
        onProfileUpdate(res.data.user);
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to update profile');
    }
    setSaving(false);
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    setChangingPass(true);
    try {
      await axios.post(`${API}/auth/change-password`, {
        current_password: currentPassword,
        new_password: newPassword
      }, getAuthHeader());
      toast.success('Password changed successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to change password');
    }
    setChangingPass(false);
  };

  const handleSavePrefs = async () => {
    setSavingPrefs(true);
    try {
      await axios.put(`${API}/auth/update-profile`, {
        notification_preferences: prefs
      }, getAuthHeader());
      toast.success('Notification preferences saved!');
    } catch (e) {
      toast.error('Failed to save preferences');
    }
    setSavingPrefs(false);
  };

  const togglePref = (key) => setPrefs(p => ({ ...p, [key]: !p[key] }));

  return (
    <div className="space-y-6" data-testid="client-profile">
      {/* Profile Info */}
      <Card className="p-6 bg-white shadow-md border-0">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-16 h-16 bg-gradient-to-br from-[#2a777a] to-[#236466] rounded-full flex items-center justify-center text-white text-2xl font-bold shadow-lg">
            {(user?.name || 'U')[0].toUpperCase()}
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-800">{user?.name}</h2>
            <p className="text-sm text-slate-500 flex items-center gap-1"><Mail className="h-3 w-3" /> {user?.email}</p>
            <Badge className="bg-[#2a777a]/10 text-[#2a777a] mt-1 capitalize">{user?.role?.replace('_', ' ')}</Badge>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Full Name</label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input value={name} onChange={e => setName(e.target.value)} className="pl-10" data-testid="profile-name" />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Mobile Number</label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input value={mobile} onChange={e => setMobile(e.target.value)} className="pl-10" placeholder="+91-XXXXXXXXXX" data-testid="profile-mobile" />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Preferred Language</label>
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <select value={language} onChange={e => setLanguage(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-md text-sm focus:ring-1 focus:ring-[#2a777a] focus:border-[#2a777a] bg-white"
                data-testid="profile-language">
                <option value="en">English</option>
                <option value="hi">Hindi</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Email (read-only)</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input value={user?.email || ''} disabled className="pl-10 bg-slate-50" />
            </div>
          </div>
        </div>
        <div className="flex justify-end mt-6">
          <Button onClick={handleSaveProfile} disabled={saving} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="save-profile-btn">
            <Save className="h-4 w-4 mr-2" /> {saving ? 'Saving...' : 'Save Profile'}
          </Button>
        </div>
      </Card>

      {/* Change Password */}
      <Card className="p-6 bg-white shadow-md border-0">
        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Lock className="h-5 w-5 text-[#f7620b]" /> Change Password
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Current Password</label>
            <Input type={showPasswords ? 'text' : 'password'} value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)} placeholder="Enter current password" data-testid="current-password" />
          </div>
          <div className="relative">
            <label className="text-sm font-medium text-slate-700 block mb-1.5">New Password</label>
            <Input type={showPasswords ? 'text' : 'password'} value={newPassword}
              onChange={e => setNewPassword(e.target.value)} placeholder="Min 6 characters" data-testid="new-password" />
          </div>
          <div className="relative">
            <label className="text-sm font-medium text-slate-700 block mb-1.5">Confirm New Password</label>
            <Input type={showPasswords ? 'text' : 'password'} value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)} placeholder="Re-enter new password" data-testid="confirm-password" />
          </div>
        </div>
        <div className="flex items-center justify-between mt-4">
          <button onClick={() => setShowPasswords(!showPasswords)} className="text-sm text-slate-500 flex items-center gap-1 hover:text-slate-700">
            {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            {showPasswords ? 'Hide' : 'Show'} passwords
          </button>
          <Button onClick={handleChangePassword} disabled={changingPass || !currentPassword || !newPassword}
            className="bg-[#f7620b] hover:bg-[#e55a09]" data-testid="change-password-btn">
            <Shield className="h-4 w-4 mr-2" /> {changingPass ? 'Changing...' : 'Change Password'}
          </Button>
        </div>
      </Card>

      {/* Notification Preferences */}
      <Card className="p-6 bg-white shadow-md border-0">
        <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Bell className="h-5 w-5 text-[#2a777a]" /> Notification Preferences
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { key: 'case_updates', label: 'Case Status Updates', desc: 'When your case progresses to next step' },
            { key: 'document_requests', label: 'Document Requests', desc: 'When case manager requests documents' },
            { key: 'payment_reminders', label: 'Payment Reminders', desc: 'When you have pending payments' },
            { key: 'email', label: 'Email Notifications', desc: 'Receive updates via email' },
            { key: 'in_app', label: 'In-App Notifications', desc: 'Receive in-app push notifications' },
            { key: 'marketing', label: 'Marketing & Updates', desc: 'News, offers and company updates' },
          ].map(item => (
            <button key={item.key} onClick={() => togglePref(item.key)}
              className={`flex items-center gap-3 p-4 rounded-xl border transition-all text-left ${
                prefs[item.key] ? 'bg-[#2a777a]/5 border-[#2a777a]/30' : 'bg-slate-50 border-slate-200'
              }`} data-testid={`pref-${item.key}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                prefs[item.key] ? 'bg-[#2a777a] text-white' : 'bg-slate-200 text-slate-400'
              }`}>
                {prefs[item.key] ? <Bell className="h-5 w-5" /> : <BellOff className="h-5 w-5" />}
              </div>
              <div>
                <p className="font-medium text-slate-800 text-sm">{item.label}</p>
                <p className="text-xs text-slate-500">{item.desc}</p>
              </div>
            </button>
          ))}
        </div>
        <div className="flex justify-end mt-4">
          <Button onClick={handleSavePrefs} disabled={savingPrefs} className="bg-[#2a777a] hover:bg-[#236466]" data-testid="save-prefs-btn">
            <Save className="h-4 w-4 mr-2" /> {savingPrefs ? 'Saving...' : 'Save Preferences'}
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default ClientProfile;
