import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Loader2, Upload, Trash2, Plus, XCircle, Mail, Gift, CreditCard, Paperclip, MessageSquare, Send,
} from 'lucide-react';
import { API } from './lib/constants';

const Field = ({ label, children, hint }) => (
  <div className="space-y-1">
    <Label className="text-[11px] font-semibold text-slate-600">{label}</Label>
    {children}
    {hint && <p className="text-[10px] text-slate-400">{hint}</p>}
  </div>
);

export default function EmailSettingsDialog({ headers, onClose }) {
  const [st, setSt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testTo, setTestTo] = useState('');
  const [testWhatsAppTo, setTestWhatsAppTo] = useState('');
  const [testingWhatsApp, setTestingWhatsApp] = useState(false);
  const [uploading, setUploading] = useState('');
  const slaRef = useRef(null);
  const qrRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/email-settings`, { headers });
      setSt(r.data);
      setTestTo(r.data?.contact_email || '');
      setTestWhatsAppTo(r.data?.contact_phone || '+91');
    } catch (e) { toast.error('Could not load email settings'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const up = (k, v) => setSt((s) => ({ ...s, [k]: v }));
  const upBank = (k, v) => setSt((s) => ({ ...s, bank_domestic: { ...(s.bank_domestic || {}), [k]: v } }));

  const save = async () => {
    setSaving(true);
    try {
      const editable = [
        'subject_template', 'outcome_title', 'body_message', 'services_list', 'gov_charges',
        'offer_enabled', 'offer_badge', 'offer_title', 'offer_regular_fee', 'offer_price',
        'offer_savings', 'offer_valid_till', 'offer_note', 'payment_enabled', 'payment_intro',
        'payment_link', 'upi_id', 'bank_domestic', 'banks_international', 'calendly_link',
        'indicative_note', 'closing', 'contact_phone', 'contact_email', 'website',
        'attach_report', 'attach_sla', 'sla_filename', 'attach_resume',
        'whatsapp_phone_number_id', 'whatsapp_access_token', 'whatsapp_waba_id', 'whatsapp_sender_display',
      ];
      const updates = {};
      editable.forEach((k) => { if (st[k] !== undefined) updates[k] = st[k]; });
      await axios.put(`${API}/email-settings`, { updates }, { headers });
      toast.success('Email settings saved');
    } catch (e) { toast.error('Could not save settings'); }
    finally { setSaving(false); }
  };

  const uploadAsset = async (asset, file) => {
    if (!file) return;
    setUploading(asset);
    try {
      const fd = new FormData();
      fd.append('file', file);
      await axios.post(`${API}/email-settings/upload/${asset}`, fd, { headers: { ...headers, 'Content-Type': 'multipart/form-data' } });
      toast.success(`${asset.toUpperCase()} uploaded`);
      await load();
    } catch (e) { toast.error(`Could not upload ${asset}`); }
    finally { setUploading(''); }
  };

  const deleteAsset = async (asset) => {
    try { await axios.delete(`${API}/email-settings/asset/${asset}`, { headers }); toast.success('Removed'); await load(); }
    catch (e) { toast.error('Could not remove'); }
  };

  const sendTest = async () => {
    if (!testTo || !testTo.includes('@')) { toast.error('Enter a valid email'); return; }
    try {
      await save();
      const r = await axios.post(`${API}/email-settings/test`, { to: testTo }, { headers });
      toast.success(`Test email sent to ${r.data.sent_to}`);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Could not send test'); }
  };

  const sendWhatsAppTest = async () => {
    if (!testWhatsAppTo || testWhatsAppTo.replace(/[^\d]/g, '').length < 8) {
      toast.error('Enter a valid WhatsApp number with country code (e.g. +91 9876543210)');
      return;
    }
    setTestingWhatsApp(true);
    try {
      await save();
      const r = await axios.post(`${API}/email-settings/test-whatsapp`, { to: testWhatsAppTo }, { headers });
      if (r.data.is_simulated) {
        toast.warning(`Simulated WhatsApp dispatch to ${r.data.sent_to}`, {
          description: 'Meta WhatsApp Cloud API credentials are not yet verified. Configure Phone Number ID and Access Token above.',
        });
      } else {
        toast.success(`Test WhatsApp message delivered to ${r.data.sent_to}!`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not send WhatsApp test');
    } finally {
      setTestingWhatsApp(false);
    }
  };

  // list editors
  const addBank = () => up('banks_international', [...(st.banks_international || []), { label: '', details: '' }]);
  const editBank = (i, k, v) => up('banks_international', st.banks_international.map((b, idx) => idx === i ? { ...b, [k]: v } : b));
  const rmBank = (i) => up('banks_international', st.banks_international.filter((_, idx) => idx !== i));
  const addService = () => up('services_list', [...(st.services_list || []), '']);
  const editService = (i, v) => up('services_list', st.services_list.map((x, idx) => idx === i ? v : x));
  const rmService = (i) => up('services_list', st.services_list.filter((_, idx) => idx !== i));
  const addGov = () => up('gov_charges', [...(st.gov_charges || []), { label: '', amount: '' }]);
  const editGov = (i, k, v) => up('gov_charges', st.gov_charges.map((g, idx) => idx === i ? { ...g, [k]: v } : g));
  const rmGov = (i) => up('gov_charges', st.gov_charges.filter((_, idx) => idx !== i));

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col" data-testid="email-settings-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Mail className="h-4 w-4" />Email &amp; WhatsApp Settings</DialogTitle>
          <DialogDescription className="text-[12px]">Configure client report emails, payment details, attachments, and Meta WhatsApp Cloud API credentials.</DialogDescription>
        </DialogHeader>

        {loading || !st ? (
          <div className="py-16 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></div>
        ) : (
          <Tabs defaultValue="message" className="flex-1 overflow-hidden flex flex-col">
            <TabsList className="grid grid-cols-5 shrink-0">
              <TabsTrigger value="message" data-testid="tab-message"><MessageSquare className="h-3.5 w-3.5 mr-1" />Message</TabsTrigger>
              <TabsTrigger value="offer" data-testid="tab-offer"><Gift className="h-3.5 w-3.5 mr-1" />Offer</TabsTrigger>
              <TabsTrigger value="payment" data-testid="tab-payment"><CreditCard className="h-3.5 w-3.5 mr-1" />Payment</TabsTrigger>
              <TabsTrigger value="attach" data-testid="tab-attach"><Paperclip className="h-3.5 w-3.5 mr-1" />Attachments</TabsTrigger>
              <TabsTrigger value="whatsapp" data-testid="tab-whatsapp"><MessageSquare className="h-3.5 w-3.5 mr-1 text-emerald-600" />WhatsApp</TabsTrigger>
            </TabsList>

            <div className="overflow-y-auto flex-1 pr-1 mt-3 space-y-3">
              {/* MESSAGE */}
              <TabsContent value="message" className="space-y-3 mt-0">
                <Field label="Subject line" hint="{name} = client ka naam automatically insert hoga">
                  <Input value={st.subject_template || ''} onChange={(e) => up('subject_template', e.target.value)} className="text-xs" data-testid="es-subject" />
                </Field>
                <Field label="Outcome headline">
                  <Input value={st.outcome_title || ''} onChange={(e) => up('outcome_title', e.target.value)} className="text-xs" data-testid="es-outcome" />
                </Field>
                <Field label="Body message" hint="Blank line = naya paragraph">
                  <Textarea value={st.body_message || ''} onChange={(e) => up('body_message', e.target.value)} rows={8} className="text-xs" data-testid="es-body" />
                </Field>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Label className="text-[11px] font-semibold text-slate-600">Services list (bullets)</Label>
                    <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={addService}><Plus className="h-3 w-3 mr-0.5" />Add</Button>
                  </div>
                  <div className="space-y-1">
                    {(st.services_list || []).map((x, i) => (
                      <div key={i} className="flex gap-1">
                        <Input value={x} onChange={(e) => editService(i, e.target.value)} className="text-xs h-7" />
                        <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500" onClick={() => rmService(i)}><XCircle className="h-3.5 w-3.5" /></Button>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <Label className="text-[11px] font-semibold text-slate-600">Estimated Govt charges</Label>
                    <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={addGov}><Plus className="h-3 w-3 mr-0.5" />Add</Button>
                  </div>
                  {(st.gov_charges || []).map((g, i) => (
                    <div key={i} className="flex gap-1 mb-1">
                      <Input placeholder="Label" value={g.label} onChange={(e) => editGov(i, 'label', e.target.value)} className="text-xs h-7 flex-1" />
                      <Input placeholder="Amount" value={g.amount} onChange={(e) => editGov(i, 'amount', e.target.value)} className="text-xs h-7 w-28" />
                      <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500" onClick={() => rmGov(i)}><XCircle className="h-3.5 w-3.5" /></Button>
                    </div>
                  ))}
                </div>
                <Field label="Closing / signature" hint="Har line alag dikhegi">
                  <Textarea value={st.closing || ''} onChange={(e) => up('closing', e.target.value)} rows={4} className="text-xs" data-testid="es-closing" />
                </Field>
                <div className="grid grid-cols-3 gap-2">
                  <Field label="Contact phone"><Input value={st.contact_phone || ''} onChange={(e) => up('contact_phone', e.target.value)} className="text-xs" /></Field>
                  <Field label="Contact email"><Input value={st.contact_email || ''} onChange={(e) => up('contact_email', e.target.value)} className="text-xs" /></Field>
                  <Field label="Website"><Input value={st.website || ''} onChange={(e) => up('website', e.target.value)} className="text-xs" /></Field>
                </div>
              </TabsContent>

              {/* OFFER */}
              <TabsContent value="offer" className="space-y-3 mt-0">
                <label className="flex items-center gap-2 text-xs cursor-pointer rounded-md bg-amber-50 border border-amber-200 px-3 py-2">
                  <Switch checked={!!st.offer_enabled} onCheckedChange={(v) => up('offer_enabled', v)} data-testid="es-offer-enabled" />
                  <span className="font-semibold text-amber-900">Show offer banner in the email</span>
                </label>
                <Field label="Offer badge"><Input value={st.offer_badge || ''} onChange={(e) => up('offer_badge', e.target.value)} className="text-xs" data-testid="es-offer-badge" /></Field>
                <Field label="Offer title"><Input value={st.offer_title || ''} onChange={(e) => up('offer_title', e.target.value)} className="text-xs" /></Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Regular fee"><Input value={st.offer_regular_fee || ''} onChange={(e) => up('offer_regular_fee', e.target.value)} className="text-xs" /></Field>
                  <Field label="Offer price"><Input value={st.offer_price || ''} onChange={(e) => up('offer_price', e.target.value)} className="text-xs" /></Field>
                  <Field label="Savings badge"><Input value={st.offer_savings || ''} onChange={(e) => up('offer_savings', e.target.value)} className="text-xs" /></Field>
                  <Field label="Valid till"><Input value={st.offer_valid_till || ''} onChange={(e) => up('offer_valid_till', e.target.value)} className="text-xs" /></Field>
                </div>
                <Field label="Offer note / terms"><Textarea value={st.offer_note || ''} onChange={(e) => up('offer_note', e.target.value)} rows={3} className="text-xs" /></Field>
              </TabsContent>

              {/* PAYMENT */}
              <TabsContent value="payment" className="space-y-3 mt-0">
                <label className="flex items-center gap-2 text-xs cursor-pointer">
                  <Switch checked={!!st.payment_enabled} onCheckedChange={(v) => up('payment_enabled', v)} data-testid="es-payment-enabled" />
                  <span className="font-semibold text-slate-700">Show payment section in the email</span>
                </label>
                <Field label="Payment intro line"><Textarea value={st.payment_intro || ''} onChange={(e) => up('payment_intro', e.target.value)} rows={2} className="text-xs" /></Field>
                <Field label="Payment link (Razorpay etc.)"><Input value={st.payment_link || ''} onChange={(e) => up('payment_link', e.target.value)} className="text-xs" data-testid="es-payment-link" /></Field>
                <Field label="UPI ID"><Input value={st.upi_id || ''} onChange={(e) => up('upi_id', e.target.value)} className="text-xs" data-testid="es-upi" /></Field>

                <div className="rounded-md border p-2.5 bg-slate-50">
                  <p className="text-[11px] font-bold text-slate-700 mb-2">🇮🇳 Domestic Bank (India)</p>
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Account name"><Input value={st.bank_domestic?.account_name || ''} onChange={(e) => upBank('account_name', e.target.value)} className="text-xs" /></Field>
                    <Field label="Account number"><Input value={st.bank_domestic?.account_number || ''} onChange={(e) => upBank('account_number', e.target.value)} className="text-xs" /></Field>
                    <Field label="IFSC"><Input value={st.bank_domestic?.ifsc || ''} onChange={(e) => upBank('ifsc', e.target.value)} className="text-xs" /></Field>
                    <Field label="Bank name"><Input value={st.bank_domestic?.bank_name || ''} onChange={(e) => upBank('bank_name', e.target.value)} className="text-xs" /></Field>
                    <Field label="Branch"><Input value={st.bank_domestic?.branch || ''} onChange={(e) => upBank('branch', e.target.value)} className="text-xs" /></Field>
                    <Field label="Account type"><Input value={st.bank_domestic?.account_type || ''} onChange={(e) => upBank('account_type', e.target.value)} className="text-xs" /></Field>
                  </div>
                </div>

                <div className="rounded-md border p-2.5">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[11px] font-bold text-slate-700">🌍 International Bank Accounts</p>
                    <Button size="sm" variant="outline" className="h-6 text-[10px]" onClick={addBank} data-testid="es-add-intl-bank"><Plus className="h-3 w-3 mr-0.5" />Add account</Button>
                  </div>
                  <div className="space-y-2">
                    {(st.banks_international || []).map((b, i) => (
                      <div key={i} className="border rounded p-2 bg-white">
                        <div className="flex gap-1 mb-1">
                          <Input placeholder="Label e.g. USA (USD)" value={b.label} onChange={(e) => editBank(i, 'label', e.target.value)} className="text-xs h-7 flex-1" />
                          <Button size="sm" variant="ghost" className="h-7 px-2 text-rose-500" onClick={() => rmBank(i)}><Trash2 className="h-3.5 w-3.5" /></Button>
                        </div>
                        <Textarea placeholder="Account details (multiline)" value={b.details} onChange={(e) => editBank(i, 'details', e.target.value)} rows={4} className="text-[11px]" />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-md border p-2.5 bg-slate-50">
                  <p className="text-[11px] font-bold text-slate-700 mb-2">📱 Payment QR image</p>
                  <div className="flex items-center gap-3">
                    {st.has_qr ? (
                      <img src={`${API}/email-settings/asset/qr?t=${Date.now()}`} alt="QR" className="h-24 w-24 object-contain border rounded bg-white" />
                    ) : <div className="h-24 w-24 border rounded bg-white flex items-center justify-center text-[10px] text-slate-400 text-center">No QR</div>}
                    <div className="space-y-1">
                      <input ref={qrRef} type="file" accept="image/*" className="hidden" onChange={(e) => uploadAsset('qr', e.target.files?.[0])} data-testid="es-qr-file" />
                      <Button size="sm" variant="outline" className="h-7 text-[11px]" onClick={() => qrRef.current?.click()} disabled={uploading === 'qr'}>
                        {uploading === 'qr' ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Upload className="h-3.5 w-3.5 mr-1" />}Upload QR
                      </Button>
                      {st.has_qr && <Button size="sm" variant="ghost" className="h-7 text-[11px] text-rose-500 block" onClick={() => deleteAsset('qr')}>Remove</Button>}
                      <p className="text-[10px] text-slate-400 max-w-[180px]">QR email mein dikhega aur attachment mein bhi jaayega</p>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* ATTACHMENTS + CONSULTATION */}
              <TabsContent value="attach" className="space-y-3 mt-0">
                <Field label="Calendly link (Book a Consultation button)">
                  <Input value={st.calendly_link || ''} onChange={(e) => up('calendly_link', e.target.value)} className="text-xs" data-testid="es-calendly" />
                </Field>
                <Field label="Disclaimer / indicative-assessment note" hint="Highlighted callout above the Book Consultation button">
                  <Textarea value={st.indicative_note || ''} onChange={(e) => up('indicative_note', e.target.value)} rows={3} className="text-xs" data-testid="es-indicative" />
                </Field>

                <div className="rounded-md border p-2.5 bg-slate-50 space-y-2">
                  <label className="flex items-center gap-2 text-xs cursor-pointer">
                    <Switch checked={!!st.attach_sla} onCheckedChange={(v) => up('attach_sla', v)} data-testid="es-attach-sla" />
                    <span className="font-semibold text-slate-700">Attach Service Level Agreement (PDF)</span>
                  </label>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-500 flex-1 truncate">{st.has_sla ? `✓ ${st.sla_filename || 'SLA.pdf'}` : 'No SLA uploaded'}</span>
                    <input ref={slaRef} type="file" accept="application/pdf,.pdf,.doc,.docx" className="hidden" onChange={(e) => uploadAsset('sla', e.target.files?.[0])} data-testid="es-sla-file" />
                    <Button size="sm" variant="outline" className="h-7 text-[11px]" onClick={() => slaRef.current?.click()} disabled={uploading === 'sla'}>
                      {uploading === 'sla' ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Upload className="h-3.5 w-3.5 mr-1" />}Upload
                    </Button>
                    {st.has_sla && <Button size="sm" variant="ghost" className="h-7 text-[11px] text-rose-500" onClick={() => deleteAsset('sla')}>Remove</Button>}
                  </div>
                  <p className="text-[10px] text-slate-400">PDF recommended. Word bhi upload kar sakte hain (as-is attach hoga).</p>
                </div>

                <label className="flex items-center gap-2 text-xs cursor-pointer rounded-md border px-3 py-2">
                  <Switch checked={!!st.attach_resume} onCheckedChange={(v) => up('attach_resume', v)} data-testid="es-attach-resume" />
                  <span className="font-semibold text-slate-700">Attach client's resume (fetched from their link)</span>
                </label>
                <label className="flex items-center gap-2 text-xs cursor-pointer rounded-md border px-3 py-2">
                  <Switch checked={st.attach_report !== false} onCheckedChange={(v) => up('attach_report', v)} data-testid="es-attach-report" />
                  <span className="font-semibold text-slate-700">Attach Pre-Assessment Report PDF</span>
                </label>
              </TabsContent>

              {/* WHATSAPP CLOUD API */}
              <TabsContent value="whatsapp" className="space-y-3 mt-0">
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs text-emerald-900 space-y-1">
                  <p className="font-bold flex items-center gap-1.5"><MessageSquare className="h-4 w-4 text-emerald-600" />Meta WhatsApp Cloud API (Automated Dispatches)</p>
                  <p className="text-[11px] text-emerald-700">
                    Configure your official Meta WhatsApp Business API keys to allow 1-click automated report deliveries. If left blank, the system automatically uses <strong>1-Click WhatsApp Web / App</strong> deep-linking.
                  </p>
                </div>

                <Field label="Phone Number ID (Meta Graph API)" hint="From Meta Developer App -> WhatsApp -> API Setup">
                  <Input placeholder="e.g. 105829472948271" value={st.whatsapp_phone_number_id || ''} onChange={(e) => up('whatsapp_phone_number_id', e.target.value)} className="text-xs font-mono" data-testid="es-whatsapp-phone-id" />
                </Field>

                <Field label="WhatsApp System User Permanent Access Token" hint="Meta Business Manager -> System Users -> WhatsApp Message Send Token">
                  <Input type="password" placeholder="EAAG..." value={st.whatsapp_access_token || ''} onChange={(e) => up('whatsapp_access_token', e.target.value)} className="text-xs font-mono" data-testid="es-whatsapp-token" />
                </Field>

                <div className="grid grid-cols-2 gap-2">
                  <Field label="WhatsApp Business Account ID (WABA ID)">
                    <Input placeholder="e.g. 109283746501928" value={st.whatsapp_waba_id || ''} onChange={(e) => up('whatsapp_waba_id', e.target.value)} className="text-xs font-mono" data-testid="es-whatsapp-waba-id" />
                  </Field>
                  <Field label="Official Sender Display Name / Number">
                    <Input placeholder="+91 77383 52427 (LEAMSS Official)" value={st.whatsapp_sender_display || ''} onChange={(e) => up('whatsapp_sender_display', e.target.value)} className="text-xs" data-testid="es-whatsapp-sender" />
                  </Field>
                </div>

                <div className="rounded-lg border bg-slate-50 p-3 space-y-2 mt-2">
                  <p className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Send className="h-3.5 w-3.5 text-emerald-600" />Test WhatsApp Message Dispatch
                  </p>
                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="+91 98765 43210"
                      value={testWhatsAppTo}
                      onChange={(e) => setTestWhatsAppTo(e.target.value)}
                      className="text-xs font-mono h-8 flex-1"
                      data-testid="es-test-whatsapp-phone"
                    />
                    <Button
                      size="sm"
                      className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
                      onClick={sendWhatsAppTest}
                      disabled={testingWhatsApp}
                      data-testid="es-send-whatsapp-test"
                    >
                      {testingWhatsApp ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Send className="h-3.5 w-3.5 mr-1" />}
                      {testingWhatsApp ? 'Testing…' : 'Test WhatsApp'}
                    </Button>
                  </div>
                  <p className="text-[10px] text-slate-400">
                    Sends an instant test notification to verify Cloud API connectivity.
                  </p>
                </div>
              </TabsContent>
            </div>
          </Tabs>
        )}

        <DialogFooter className="border-t pt-3 mt-1 flex-col sm:flex-row gap-2 shrink-0">
          <div className="flex items-center gap-1 flex-1 w-full">
            <Input placeholder="you@leamss.com" value={testTo} onChange={(e) => setTestTo(e.target.value)} className="h-8 text-xs max-w-[220px]" data-testid="es-test-to" />
            <Button size="sm" variant="outline" className="h-8 text-[11px]" onClick={sendTest} data-testid="es-send-test"><Send className="h-3.5 w-3.5 mr-1" />Send Email Test</Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} data-testid="es-close">Close</Button>
            <Button onClick={save} disabled={saving} className="bg-teal-700 hover:bg-teal-800" data-testid="es-save">
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}Save Settings
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
