import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import {
  Loader2, Mail, Plus, Trash2, Key, Eye, EyeOff, ShieldCheck, CheckCircle2,
} from 'lucide-react';
import { API } from './lib/constants';

export default function MailAccountsDialog({ headers, onClose, onChanged }) {
  const [list, setList] = useState([]);
  const [defaultSender, setDefaultSender] = useState('info@leamss.com');
  const [domain, setDomain] = useState('leamss.com');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form states
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [appPassword, setAppPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Edit states
  const [editingId, setEditingId] = useState(null);
  const [editPassword, setEditPassword] = useState('');

  const authHeaders = headers || {
    Authorization: `Bearer ${localStorage.getItem('token')}`,
  };

  const reload = async () => {
    try {
      // Fetch senders and default configuration
      const r = await axios.get(`${API}/email-settings/mail-senders`, { headers: authHeaders });
      if (r.data?.senders) {
        setList(r.data.senders || []);
        if (r.data.default_sender) setDefaultSender(r.data.default_sender);
        if (r.data.domain) setDomain(r.data.domain);
      } else if (Array.isArray(r.data)) {
        setList(r.data);
      }
      if (onChanged) onChanged();
    } catch (e) {
      // Fallback to bulk-assessments endpoint
      try {
        const fallback = await axios.get(`${API}/bulk-assessments/mail-senders`, { headers: authHeaders });
        setList(fallback.data || []);
      } catch (err) {
        console.error('Failed to load mail senders:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const add = async () => {
    if (!name.trim() || !email.trim()) {
      toast.error('Enter both consultant name and email address');
      return;
    }
    if (!email.includes('@')) {
      toast.error('Enter a valid email address');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: name.trim(),
        email: email.trim().toLowerCase(),
        active: true,
      };
      if (appPassword.trim()) {
        payload.app_password = appPassword.replace(/\s+/g, '').trim();
      }
      const r = await axios.post(`${API}/email-settings/mail-senders`, payload, { headers: authHeaders });
      if (r.data?.domain_warning) {
        toast.warning(`${email.trim()} is added, but is not on @${domain || 'leamss.com'}`);
      } else {
        toast.success(`Sender account ${name.trim()} added successfully!`);
      }
      setName('');
      setEmail('');
      setAppPassword('');
      await reload();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not add mailbox');
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (s) => {
    try {
      await axios.patch(`${API}/email-settings/mail-senders/${s.id}`, { active: !s.active }, { headers: authHeaders });
      await reload();
    } catch (e) {
      toast.error('Could not update status');
    }
  };

  const updateAppPassword = async (senderId) => {
    if (!editPassword.trim()) {
      toast.error('Enter an App Password');
      return;
    }
    try {
      await axios.patch(`${API}/email-settings/mail-senders/${senderId}`, {
        app_password: editPassword.replace(/\s+/g, '').trim(),
      }, { headers: authHeaders });
      toast.success('App Password updated successfully');
      setEditingId(null);
      setEditPassword('');
      await reload();
    } catch (e) {
      toast.error('Could not update App Password');
    }
  };

  const remove = async (s) => {
    if (!window.confirm(`Are you sure you want to remove ${s.name} (${s.email}) from sender accounts?`)) {
      return;
    }
    try {
      await axios.delete(`${API}/email-settings/mail-senders/${s.id}`, { headers: authHeaders });
      toast.success('Sender account removed');
      await reload();
    } catch (e) {
      toast.error('Could not remove sender');
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-xl max-h-[88vh] overflow-y-auto" data-testid="mail-accounts-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-slate-900">
            <Mail className="h-4 w-4 text-indigo-600" />
            Sender &amp; Consultant Mail Accounts
          </DialogTitle>
          <DialogDescription className="text-[12px] text-slate-500">
            Configure sender accounts used for emailing client assessment reports and follow-ups. You can add each consultant with their individual Google App Password.
          </DialogDescription>
        </DialogHeader>

        {/* System Default Primary Account Banner */}
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/70 p-3 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Primary System Account (Default)
            </span>
            <span className="text-[10px] bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded-full border border-emerald-300">
              Verified &amp; Active
            </span>
          </div>
          <p className="text-[11px] text-emerald-800">
            <strong>LEAMSS Consultation</strong> &lt;{defaultSender}&gt; — uses default Google Workspace SMTP credentials with TLS on port 587.
          </p>
        </div>

        {/* Add New Mail Account Form */}
        <div className="border border-slate-200 rounded-lg p-3.5 bg-slate-50/80 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
              <Plus className="h-3.5 w-3.5 text-indigo-600" />
              Add New Sender / Consultant Account
            </span>
            <span className="text-[10px] text-slate-500">SMTP App Password Support</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div>
              <Label className="text-[11px] font-semibold text-slate-700">Display / Consultant Name *</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Pooja Ghatkar"
                className="h-8 text-xs bg-white mt-1"
                data-testid="mailbox-name-input"
              />
            </div>
            <div>
              <Label className="text-[11px] font-semibold text-slate-700">Email Address *</Label>
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={`consultant@${domain || 'leamss.com'}`}
                className="h-8 text-xs bg-white mt-1"
                data-testid="mailbox-email-input"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <Label className="text-[11px] font-semibold text-slate-700 flex items-center gap-1">
                <Key className="h-3 w-3 text-slate-500" />
                Google App Password (Optional)
              </Label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-[10px] text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
              >
                {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <div className="relative mt-1">
              <Input
                type={showPassword ? 'text' : 'password'}
                value={appPassword}
                onChange={(e) => setAppPassword(e.target.value)}
                placeholder="16-character Google App Password (e.g. keuq zpul cfar zeo)"
                className="h-8 text-xs font-mono bg-white pr-20"
                data-testid="mailbox-password-input"
              />
              <span className="absolute right-2 top-2 text-[10px] text-slate-400 font-sans pointer-events-none">
                16-chars
              </span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">
              Generate in: <em>Google Account &gt; Security &gt; 2-Step Verification &gt; App Passwords</em>. Leave empty to use system fallback.
            </p>
          </div>

          <div className="flex justify-end pt-1">
            <Button
              onClick={add}
              disabled={saving}
              className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4"
              data-testid="mailbox-add-btn"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Plus className="h-3.5 w-3.5 mr-1.5" />}
              {saving ? 'Adding...' : 'Add Sender Account'}
            </Button>
          </div>
        </div>

        {/* Existing Accounts List */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Active Sender Accounts ({list.length})
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={reload}
              className="h-6 text-[11px] text-indigo-600 hover:text-indigo-800"
            >
              Refresh List
            </Button>
          </div>

          {loading ? (
            <div className="py-6 text-center text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin mx-auto text-indigo-500" />
            </div>
          ) : list.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-4 bg-slate-50 border border-dashed rounded-lg">
              No consultant mail accounts configured yet. Add your team mailboxes above.
            </p>
          ) : (
            <div className="space-y-1.5" data-testid="mailbox-list">
              {list.map((s) => (
                <div
                  key={s.id || s.email}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border border-slate-200 rounded-lg px-3 py-2 bg-white hover:border-slate-300 transition-colors"
                  data-testid={`mailbox-item-${s.email}`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="text-xs font-bold text-slate-900 truncate">{s.name}</p>
                      {s.has_app_password && (
                        <span className="text-[9px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.2 rounded flex items-center gap-0.5">
                          <CheckCircle2 className="h-2.5 w-2.5" /> App Password
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 font-mono truncate">{s.email}</p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {editingId === s.id ? (
                      <div className="flex items-center gap-1">
                        <Input
                          type="password"
                          placeholder="New App Password"
                          value={editPassword}
                          onChange={(e) => setEditPassword(e.target.value)}
                          className="h-7 text-xs font-mono w-36"
                        />
                        <Button
                          size="sm"
                          className="h-7 text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white"
                          onClick={() => updateAppPassword(s.id)}
                        >
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-[10px]"
                          onClick={() => { setEditingId(null); setEditPassword(''); }}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => { setEditingId(s.id); setEditPassword(''); }}
                        className="text-[10px] text-slate-500 hover:text-indigo-600 underline font-medium"
                      >
                        {s.has_app_password ? 'Update Password' : '+ Add Password'}
                      </button>
                    )}

                    <div className="flex items-center gap-1 text-[10px] text-slate-500">
                      <Switch
                        checked={s.active !== false}
                        onCheckedChange={() => toggleActive(s)}
                        data-testid={`mailbox-active-${s.email}`}
                      />
                      <span className="w-8">{s.active !== false ? 'Active' : 'Off'}</span>
                    </div>

                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                      onClick={() => remove(s)}
                      title="Remove Account"
                      data-testid={`mailbox-delete-${s.email}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <DialogFooter className="pt-2 border-t mt-2">
          <Button
            type="button"
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs"
            onClick={onClose}
            data-testid="mail-accounts-close"
          >
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
