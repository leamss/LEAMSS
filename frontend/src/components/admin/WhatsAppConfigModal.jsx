import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  MessageCircle,
  Shield,
  Key,
  Phone,
  Hash,
  CheckCircle2,
  AlertCircle,
  Copy,
  RefreshCw,
  ExternalLink,
  Eye,
  EyeOff,
  Zap,
  Check
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function WhatsAppConfigModal({ isOpen, onClose, onSaved }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showToken, setShowToken] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [copiedField, setCopiedField] = useState(null);

  const [form, setForm] = useState({
    phone_number_id: '',
    waba_id: '',
    access_token: '',
    app_secret: '',
    verify_token: '',
    sender_display: '',
    is_configured: false,
    is_token_set: false,
    is_secret_set: false
  });

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  const loadConfig = async () => {
    setLoading(true);
    setTestResult(null);
    try {
      const res = await axios.get(`${API}/crm/whatsapp/config`, getAuthHeader());
      if (res.data) {
        setForm(prev => ({
          ...prev,
          phone_number_id: res.data.phone_number_id || '',
          waba_id: res.data.waba_id || '',
          access_token: res.data.access_token || '',
          app_secret: res.data.app_secret || '',
          verify_token: res.data.verify_token || 'leamss_wa_verify_token_2026',
          sender_display: res.data.sender_display || '',
          is_configured: Boolean(res.data.is_configured),
          is_token_set: Boolean(res.data.is_token_set),
          is_secret_set: Boolean(res.data.is_secret_set)
        }));
      }
    } catch (err) {
      console.error('Failed to load WhatsApp config:', err);
      toast.error('Could not load WhatsApp configuration');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/crm/whatsapp/config`, {
        phone_number_id: form.phone_number_id.trim(),
        waba_id: form.waba_id.trim(),
        access_token: form.access_token.trim(),
        app_secret: form.app_secret.trim(),
        verify_token: form.verify_token.trim(),
        sender_display: form.sender_display.trim()
      }, getAuthHeader());

      toast.success('WhatsApp Cloud API configuration saved successfully!');
      if (onSaved) onSaved();
      loadConfig();
    } catch (err) {
      console.error('Failed to save WhatsApp config:', err);
      toast.error(err.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await axios.post(`${API}/crm/whatsapp/config/test`, {}, getAuthHeader());
      setTestResult(res.data);
      if (res.data.success) {
        toast.success(`Connected! Meta Phone: ${res.data.verified_name || res.data.display_phone_number}`);
      } else {
        toast.error(res.data.error || 'Connection failed');
      }
    } catch (err) {
      console.error('Test connection error:', err);
      setTestResult({
        success: false,
        error: err.response?.data?.detail || err.message || 'Connection test failed'
      });
      toast.error('Failed to communicate with Meta Cloud API');
    } finally {
      setTesting(false);
    }
  };

  const handleCopy = (text, fieldName) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    toast.success(`Copied ${fieldName} to clipboard!`);
    setTimeout(() => setCopiedField(null), 2000);
  };

  // Derive webhook URL for Meta Developer Portal
  const webhookUrl = `${window.location.origin}/api/crm/whatsapp/webhook`;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader className="border-b border-slate-100 pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 flex items-center justify-center shadow-xs">
                <MessageCircle className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
                  Meta WhatsApp Cloud API Settings
                  {form.is_configured ? (
                    <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px] font-semibold">
                      Connected
                    </Badge>
                  ) : (
                    <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[10px] font-semibold">
                      Action Required
                    </Badge>
                  )}
                </DialogTitle>
                <DialogDescription className="text-xs text-slate-500 mt-0.5">
                  Direct official two-way WhatsApp Business Platform integration with real-time webhooks.
                </DialogDescription>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleTestConnection}
              disabled={testing || loading}
              className="text-xs h-8 gap-1.5 font-semibold text-emerald-700 border-emerald-300 hover:bg-emerald-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
              Test Connection
            </Button>
          </div>
        </DialogHeader>

        {loading ? (
          <div className="py-12 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-emerald-600 mb-2" />
            <p className="text-xs">Loading WhatsApp configuration...</p>
          </div>
        ) : (
          <div className="space-y-4 py-2 text-xs">
            {/* Live Test Feedback Banner */}
            {testResult && (
              <div
                className={`p-3.5 rounded-xl border text-xs flex items-start gap-2.5 ${
                  testResult.success
                    ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
                    : 'bg-rose-50 border-rose-200 text-rose-900'
                }`}
              >
                {testResult.success ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1 space-y-1">
                  <p className="font-bold">
                    {testResult.success ? 'Meta Cloud API Connected Successfully' : 'Connection Error'}
                  </p>
                  {testResult.success ? (
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-emerald-800">
                      <div>Verified Name: <strong>{testResult.verified_name || 'N/A'}</strong></div>
                      <div>Display Phone: <strong>{testResult.display_phone_number || 'N/A'}</strong></div>
                      <div>Quality Rating: <strong>{testResult.quality_rating || 'N/A'}</strong></div>
                      <div>Status: <strong>{testResult.code_verification_status || 'VERIFIED'}</strong></div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-rose-700">{testResult.error}</p>
                  )}
                </div>
              </div>
            )}

            {/* Meta API Credentials Card */}
            <div className="bg-slate-50/70 border border-slate-200 rounded-xl p-3.5 space-y-3">
              <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
                <Key className="w-4 h-4 text-emerald-600" /> Meta Cloud API Credentials
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    Phone Number ID <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <Input
                      placeholder="e.g. 589218491823901"
                      value={form.phone_number_id}
                      onChange={(e) => setForm({ ...form, phone_number_id: e.target.value })}
                      className="text-xs font-mono h-8 pr-8"
                    />
                    <Hash className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
                  </div>
                  <span className="text-[10px] text-slate-400">Found in Meta App &gt; WhatsApp &gt; API Setup</span>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    WhatsApp Business Account ID (WABA ID)
                  </label>
                  <div className="relative">
                    <Input
                      placeholder="e.g. 109283019283019"
                      value={form.waba_id}
                      onChange={(e) => setForm({ ...form, waba_id: e.target.value })}
                      className="text-xs font-mono h-8 pr-8"
                    />
                    <Hash className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
                  </div>
                  <span className="text-[10px] text-slate-400">Meta Business Portfolio WhatsApp Account ID</span>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                  Permanent System User Access Token <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Input
                    type={showToken ? 'text' : 'password'}
                    placeholder="EAABw..."
                    value={form.access_token}
                    onChange={(e) => setForm({ ...form, access_token: e.target.value })}
                    className="text-xs font-mono h-8 pr-16"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 text-xs flex items-center gap-1"
                  >
                    {showToken ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <span className="text-[10px] text-slate-400">
                  Generate under Meta Business Settings &gt; System Users &gt; Generate Token (scopes: <code>whatsapp_business_messaging</code>, <code>whatsapp_business_management</code>)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    Meta App Secret (HMAC Validation)
                  </label>
                  <div className="relative">
                    <Input
                      type={showSecret ? 'text' : 'password'}
                      placeholder="App Secret for X-Hub signature"
                      value={form.app_secret}
                      onChange={(e) => setForm({ ...form, app_secret: e.target.value })}
                      className="text-xs font-mono h-8 pr-8"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret(!showSecret)}
                      className="absolute right-2 top-2 text-slate-400 hover:text-slate-600"
                    >
                      {showSecret ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <span className="text-[10px] text-slate-400">Found in Meta App &gt; App Settings &gt; Basic</span>
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    Sender Display Label
                  </label>
                  <Input
                    placeholder="e.g. +91 77383 52427 (LEAMSS Official)"
                    value={form.sender_display}
                    onChange={(e) => setForm({ ...form, sender_display: e.target.value })}
                    className="text-xs h-8"
                  />
                  <span className="text-[10px] text-slate-400">Display name shown to CRM sales reps</span>
                </div>
              </div>
            </div>

            {/* Meta Webhook Endpoint Configuration Guide */}
            <div className="bg-emerald-50/50 border border-emerald-200/80 rounded-xl p-3.5 space-y-2.5">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-emerald-950 flex items-center gap-1.5 text-xs">
                  <Shield className="w-4 h-4 text-emerald-700" /> Meta Real-Time Webhook Configuration
                </h4>
                <a
                  href="https://developers.facebook.com/apps"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] text-emerald-700 hover:text-emerald-900 font-semibold flex items-center gap-1 hover:underline"
                >
                  Meta Developer Console <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <p className="text-[11px] text-emerald-900">
                To receive client WhatsApp replies and real-time delivery ticks (sent/delivered/read) in LEAMSS CRM, configure your webhook in Meta Developer App &gt; WhatsApp &gt; Configuration:
              </p>

              <div className="space-y-2 bg-white/90 p-3 rounded-lg border border-emerald-100">
                <div>
                  <span className="text-[10px] font-bold text-slate-500 block uppercase tracking-wider">Callback URL</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <Input
                      readOnly
                      value={webhookUrl}
                      className="text-xs font-mono bg-slate-50 h-7"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopy(webhookUrl, 'Webhook URL')}
                      className="h-7 px-2 text-xs gap-1"
                    >
                      {copiedField === 'Webhook URL' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      Copy
                    </Button>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] font-bold text-slate-500 block uppercase tracking-wider">Verify Token</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <Input
                      value={form.verify_token}
                      onChange={(e) => setForm({ ...form, verify_token: e.target.value })}
                      className="text-xs font-mono bg-slate-50 h-7"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopy(form.verify_token, 'Verify Token')}
                      className="h-7 px-2 text-xs gap-1"
                    >
                      {copiedField === 'Verify Token' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      Copy
                    </Button>
                  </div>
                </div>

                <div className="pt-1 flex items-center gap-2 text-[11px] text-emerald-800">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Subscribe to Webhook Field: <strong>messages</strong></span>
                </div>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="border-t border-slate-100 pt-3 flex items-center justify-between sm:justify-between">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            className="text-xs h-8 text-slate-500 hover:text-slate-800"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={saving || loading}
            className="text-xs h-8 bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 px-4 shadow-sm"
          >
            {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
