import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import {
  Video,
  Calendar,
  Clock,
  Link as LinkIcon,
  Copy,
  ExternalLink,
  MessageCircle,
  Mail,
  RefreshCw,
  Check,
  Shield,
  Sparkles,
  Info,
  CalendarPlus,
  ClipboardPaste,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const sanitizePhone = (phone) => {
  if (!phone) return '';
  const digits = String(phone).replace(/\D/g, '');
  if (digits.length === 10) return `91${digits}`;
  return digits;
};

export default function MeetingModal({
  isOpen,
  onClose,
  lead = null,
  leads = [],
  currentUser,
  onMeetingScheduled,
  onOpenEmailModal
}) {
  const [selectedLeadId, setSelectedLeadId] = useState('');
  const [customName, setCustomName] = useState('');
  const [customPhone, setCustomPhone] = useState('');
  const [customEmail, setCustomEmail] = useState('');

  const activeLead = lead || (selectedLeadId ? leads.find(l => l.id === selectedLeadId) : null);

  const [platform, setPlatform] = useState('Google Meet'); // 'Google Meet', 'Zoom', or 'Calendly'
  const [title, setTitle] = useState('');
  const [meetingDate, setMeetingDate] = useState('');
  const [meetingTime, setMeetingTime] = useState('11:00');
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [meetingLink, setMeetingLink] = useState('');
  const [meetingPassword, setMeetingPassword] = useState('');
  const [notes, setNotes] = useState('');
  const [generatingLink, setGeneratingLink] = useState(false);
  const [generatingCalendlyLink, setGeneratingCalendlyLink] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [sendConfirmationEmail, setSendConfirmationEmail] = useState(true);

  // Default link persistence for Google Meet, Zoom, and Calendly
  const [defaultMeetLink, setDefaultMeetLink] = useState('');
  const [defaultZoomLink, setDefaultZoomLink] = useState('');
  const [defaultCalendlyLink, setDefaultCalendlyLink] = useState('https://calendly.com/rohit-leamss/permanent-residency-visa');
  const [saveAsDefault, setSaveAsDefault] = useState(false);

  // Fetch saved default links from localStorage and DB config on mount
  useEffect(() => {
    const savedLocalMeet = localStorage.getItem('default_google_meet_link') || '';
    if (savedLocalMeet) setDefaultMeetLink(savedLocalMeet);

    const savedLocalZoom = localStorage.getItem('zoom_pmi_link') || '';
    if (savedLocalZoom) setDefaultZoomLink(savedLocalZoom);

    const fetchConfig = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        const res = await axios.get(`${API}/crm/meetings/config`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.data?.default_google_meet_link) {
          setDefaultMeetLink(res.data.default_google_meet_link);
          localStorage.setItem('default_google_meet_link', res.data.default_google_meet_link);
        }
        if (res.data?.zoom_pmi_link) {
          setDefaultZoomLink(res.data.zoom_pmi_link);
          localStorage.setItem('zoom_pmi_link', res.data.zoom_pmi_link);
        }
      } catch (e) {
        // quiet fallback
      }
    };
    fetchConfig();
  }, []);

  // Initialize defaults when modal opens or lead changes
  useEffect(() => {
    if (isOpen) {
      if (lead) {
        setSelectedLeadId(lead.id || '');
      } else if (leads && leads.length > 0 && !selectedLeadId) {
        setSelectedLeadId(leads[0].id || '');
      }

      const clientName = lead?.name || 'Client';
      setTitle(`Immigration Consultation - ${clientName}`);

      // Default date: today
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth() + 1).padStart(2, '0');
      const dd = String(today.getDate()).padStart(2, '0');
      setMeetingDate(`${yyyy}-${mm}-${dd}`);

      // Default time: next hour or 11:00
      const nowH = today.getHours();
      const nextH = (nowH + 1) % 24;
      const formattedH = String(nextH).padStart(2, '0') + ':00';
      setMeetingTime(nextH >= 9 && nextH <= 19 ? formattedH : '11:00');

      setDurationMinutes(30);
      setNotes('Discuss visa eligibility, required documents, and migration roadmap.');

      // Check if we have a default link for current platform
      if (platform === 'Google Meet') {
        const savedMeet = localStorage.getItem('default_google_meet_link') || defaultMeetLink;
        if (savedMeet) {
          setMeetingLink(savedMeet);
          setSaveAsDefault(false);
        } else {
          setMeetingLink('');
          setSaveAsDefault(true);
        }
        setMeetingPassword('');
      } else if (platform === 'Zoom') {
        const savedZoom = localStorage.getItem('zoom_pmi_link') || defaultZoomLink;
        if (savedZoom) {
          setMeetingLink(savedZoom);
          setSaveAsDefault(false);
        } else {
          setMeetingLink('');
          setSaveAsDefault(true);
        }
        setMeetingPassword('');
      } else if (platform === 'Calendly') {
        const savedCal = localStorage.getItem('calendly_link') || defaultCalendlyLink;
        setMeetingLink(savedCal || 'https://calendly.com/rohit-leamss/permanent-residency-visa');
        setSaveAsDefault(false);
        setMeetingPassword('');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, lead]);

  // When selected lead changes in dropdown
  useEffect(() => {
    if (activeLead && !lead) {
      setTitle(`Immigration Consultation - ${activeLead.name || 'Client'}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLeadId]);

  const handleGenerateCalendlyLink = async () => {
    setGeneratingCalendlyLink(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(
        `${API}/integrations/calendly/create-booking-link`,
        { max_event_count: 1 },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.data?.booking_url) {
        setMeetingLink(res.data.booking_url);
        toast.success('Generated single-use Calendly booking link for client!');
      } else {
        setMeetingLink(defaultCalendlyLink);
        toast.info('Using default Calendly booking page');
      }
    } catch (e) {
      setMeetingLink(defaultCalendlyLink);
      toast.info('Using primary Calendly link');
    } finally {
      setGeneratingCalendlyLink(false);
    }
  };

  const handleGenerateLink = async (targetPlatform = platform) => {
    if (targetPlatform === 'Calendly') {
      return handleGenerateCalendlyLink();
    }
    setGeneratingLink(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(
        `${API}/crm/meetings/generate-link`,
        {
          platform: targetPlatform,
          title: title || `Consultation - ${lead?.name || 'Client'}`,
          meeting_date: meetingDate,
          meeting_time: meetingTime,
          duration_minutes: durationMinutes
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (res.data?.meeting_link) {
        setMeetingLink(res.data.meeting_link);
        if (res.data.password) {
          setMeetingPassword(res.data.password);
        } else {
          setMeetingPassword('');
        }
      } else if (targetPlatform === 'Google Meet') {
        const savedLink = localStorage.getItem('default_google_meet_link') || defaultMeetLink;
        setMeetingLink(savedLink || '');
        setMeetingPassword('');
      } else {
        const savedZoom = localStorage.getItem('zoom_pmi_link') || defaultZoomLink;
        setMeetingLink(savedZoom || '');
        setMeetingPassword('');
      }
    } catch (err) {
      if (targetPlatform === 'Google Meet') {
        const savedLink = localStorage.getItem('default_google_meet_link') || defaultMeetLink;
        setMeetingLink(savedLink || '');
        setMeetingPassword('');
      } else {
        const savedZoom = localStorage.getItem('zoom_pmi_link') || defaultZoomLink;
        setMeetingLink(savedZoom || '');
        setMeetingPassword('');
      }
    } finally {
      setGeneratingLink(false);
    }
  };

  const handlePlatformChange = (newPlatform) => {
    setPlatform(newPlatform);
    if (newPlatform === 'Google Meet') {
      const savedLink = localStorage.getItem('default_google_meet_link') || defaultMeetLink;
      if (savedLink) {
        setMeetingLink(savedLink);
        setSaveAsDefault(false);
      } else {
        setMeetingLink('');
        setSaveAsDefault(true);
      }
      setMeetingPassword('');
    } else if (newPlatform === 'Zoom') {
      const savedZoom = localStorage.getItem('zoom_pmi_link') || defaultZoomLink;
      if (savedZoom) {
        setMeetingLink(savedZoom);
        setSaveAsDefault(false);
      } else {
        setMeetingLink('');
        setSaveAsDefault(true);
      }
      setMeetingPassword('');
    } else if (newPlatform === 'Calendly') {
      const savedCal = localStorage.getItem('calendly_link') || defaultCalendlyLink;
      setMeetingLink(savedCal || 'https://calendly.com/rohit-leamss/permanent-residency-visa');
      setMeetingPassword('');
      setSaveAsDefault(false);
    }
  };

  const handleLaunchGoogleMeet = () => {
    window.open('https://meet.google.com/new', '_blank');
    toast.info('Google Meet opened in a new tab! Once your room opens, copy its link and click "Paste Link" below.', {
      duration: 6000
    });
  };

  const handleLaunchZoom = () => {
    window.open('https://zoom.us/start/videomeeting', '_blank');
    toast.info('Zoom opened! Once your meeting starts, copy its invite link and click "Paste Link" below.', {
      duration: 6000
    });
  };

  const handlePasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (!text || !text.trim()) {
        toast.warning('Clipboard is empty. Copy your meeting link first.');
        return;
      }
      const trimmed = text.trim();
      const match = trimmed.match(/https?:\/\/[^\s]+/);
      const url = match ? match[0] : trimmed;
      setMeetingLink(url);
      toast.success('Pasted meeting link from clipboard!');
    } catch (e) {
      toast.info('Please paste directly into the box with Ctrl+V or Cmd+V');
    }
  };

  const consultantName = currentUser?.name || 'LEAMSS Consultant';
  const targetContactName = activeLead?.name || customName || 'Client';
  const targetContactPhone = activeLead?.whatsapp_number || activeLead?.phone || customPhone || '';
  const targetContactEmail = activeLead?.email || customEmail || '';

  // Google Calendar URL generator
  const getGoogleCalendarUrl = () => {
    if (!meetingDate || !meetingTime) {
      return 'https://calendar.google.com/calendar/render?action=TEMPLATE';
    }
    try {
      const [y, m, d] = meetingDate.split('-');
      const [hh, mm] = meetingTime.split(':');
      const start = new Date(parseInt(y), parseInt(m) - 1, parseInt(d), parseInt(hh), parseInt(mm));
      const end = new Date(start.getTime() + (durationMinutes || 30) * 60000);
      const toGCal = (dt) => dt.toISOString().replace(/-|:|\.\d\d\d/g, '');
      const datesStr = `${toGCal(start)}/${toGCal(end)}`;
      const details = `${notes || 'Consultation Meeting'}\n\nClient: ${targetContactName} (${targetContactPhone})\nConsultant: ${consultantName}\nLEAMSS Immigration Consulting`;
      return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title || 'Immigration Consultation')}&dates=${datesStr}&details=${encodeURIComponent(details)}&add=${encodeURIComponent(targetContactEmail || '')}`;
    } catch {
      return 'https://calendar.google.com/calendar/render?action=TEMPLATE';
    }
  };

  // Format meeting date nicely (e.g. Monday, 15 Oct 2026)
  const getFormattedDate = () => {
    if (!meetingDate) return 'Upcoming';
    try {
      const parts = meetingDate.split('-');
      if (parts.length === 3) {
        const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
        return d.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
      }
      return meetingDate;
    } catch {
      return meetingDate;
    }
  };

  // Generate Invitation Message Text
  const getInvitationText = () => {
    const formattedDate = getFormattedDate();
    let text = `Dear ${targetContactName},\n\n`;
    text += `Your immigration consultation meeting with ${consultantName} has been scheduled!\n\n`;
    text += `📅 Date: ${formattedDate}\n`;
    text += `⏰ Time: ${meetingTime} (${durationMinutes} mins)\n`;
    text += `💻 Platform: ${platform}\n`;
    text += `🔗 Join Link: ${meetingLink}\n`;
    if (platform === 'Zoom' && meetingPassword) {
      text += `🔑 Passcode: ${meetingPassword}\n`;
    }
    if (notes && notes.trim()) {
      text += `📋 Agenda: ${notes.trim()}\n`;
    }
    text += `\nPlease join 2 minutes prior to the start time. Let me know if you need to reschedule.\n\n`;
    text += `Best regards,\n${consultantName}\nLEAMSS Immigration Consulting`;
    return text;
  };

  const copyToClipboard = (text, msg = 'Copied to clipboard!') => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
    toast.success(msg);
  };

  const saveMeetingToBackend = async () => {
    if (!meetingDate || !meetingTime) {
      toast.error('Please specify both meeting date and time.');
      return null;
    }

    const trimmedLink = (meetingLink || '').trim();
    if (!trimmedLink) {
      if (platform === 'Google Meet') {
        toast.error('Please add your Google Meet link. Click "1. Launch meet.google.com/new" to start a live room.');
      } else if (platform === 'Zoom') {
        toast.error('Please add your Zoom link. Click "1. Launch Instant Zoom" or paste your personal Zoom room link.');
      } else {
        toast.error('Please add or generate your Calendly booking link.');
      }
      return null;
    }

    if (platform === 'Google Meet') {
      if (trimmedLink === 'https://meet.google.com/new' || trimmedLink === 'meet.google.com/new') {
        toast.error('Please launch meet.google.com/new, create your room, and copy the room link (e.g. meet.google.com/xxx-yyyy-zzz).');
        return null;
      }
      if (!trimmedLink.includes('meet.google.com')) {
        toast.warning('Note: Google Meet links usually look like https://meet.google.com/xxx-yyyy-zzz');
      }
    }

    if (platform === 'Zoom') {
      if (trimmedLink === 'https://zoom.us/start/videomeeting' || trimmedLink === 'zoom.us/start/videomeeting') {
        toast.error('Please launch Zoom, start your meeting, and copy your actual room link (e.g. https://us05web.zoom.us/j/... or personal link).');
        return null;
      }
      if (!trimmedLink.includes('zoom.us')) {
        toast.warning('Note: Zoom links typically contain zoom.us (e.g. https://us05web.zoom.us/j/... or https://zoom.us/my/...)');
      }
    }

    if (platform === 'Calendly') {
      if (!trimmedLink.includes('calendly.com')) {
        toast.warning('Note: Calendly links typically contain calendly.com');
      }
    }

    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const payload = {
        lead_id: activeLead?.id || null,
        contact_name: targetContactName,
        contact_phone: targetContactPhone,
        contact_email: targetContactEmail,
        title: title || `Consultation - ${targetContactName}`,
        meeting_type: platform,
        meeting_date: meetingDate,
        meeting_time: meetingTime,
        duration_minutes: durationMinutes,
        meeting_link: trimmedLink,
        meeting_password: meetingPassword,
        notes: notes,
        sales_person_name: consultantName,
        send_client_email: sendConfirmationEmail
      };

      const res = await axios.post(`${API}/crm/meetings`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      // Save as default permanent link if requested
      if (saveAsDefault && trimmedLink) {
        if (platform === 'Google Meet') {
          localStorage.setItem('default_google_meet_link', trimmedLink);
          setDefaultMeetLink(trimmedLink);
          try {
            axios.post(
              `${API}/crm/meetings/config`,
              { default_google_meet_link: trimmedLink },
              { headers: { Authorization: `Bearer ${token}` } }
            ).catch(() => {});
          } catch (e) {}
        } else if (platform === 'Zoom') {
          localStorage.setItem('zoom_pmi_link', trimmedLink);
          setDefaultZoomLink(trimmedLink);
          try {
            axios.post(
              `${API}/crm/meetings/config`,
              { zoom_pmi_link: trimmedLink },
              { headers: { Authorization: `Bearer ${token}` } }
            ).catch(() => {});
          } catch (e) {}
        } else if (platform === 'Calendly') {
          localStorage.setItem('calendly_link', trimmedLink);
          setDefaultCalendlyLink(trimmedLink);
        }
      }

      return res.data;
    } catch (err) {
      console.error('Failed to schedule meeting:', err);
      toast.error(err.response?.data?.detail || 'Failed to save meeting in CRM.');
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handleScheduleOnly = async () => {
    const saved = await saveMeetingToBackend();
    if (saved) {
      toast.success(`Meeting scheduled for ${targetContactName}!`);
      if (onMeetingScheduled) onMeetingScheduled(saved);
      onClose();
    }
  };

  const handleScheduleAndShareWhatsApp = async () => {
    const saved = await saveMeetingToBackend();
    if (!saved) return;

    if (!targetContactPhone) {
      toast.warning('Client has no phone number on file. Saved to CRM.');
      if (onMeetingScheduled) onMeetingScheduled(saved);
      onClose();
      return;
    }

    const cleanPhone = sanitizePhone(targetContactPhone);
    const invitationText = getInvitationText();

    // Log the WhatsApp message in CRM backend as sent
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/crm/whatsapp/send-web`,
        {
          lead_id: activeLead?.id,
          phone: cleanPhone,
          message: invitationText,
          template_name: `Meeting Invitation (${platform})`
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (e) {
      console.warn('Could not auto-log WhatsApp activity:', e);
    }

    // Open WhatsApp Web with the client's actual phone number and invitation
    const waUrl = `https://web.whatsapp.com/send?phone=${cleanPhone}&text=${encodeURIComponent(invitationText)}`;
    window.open(waUrl, '_blank');

    toast.success(`Meeting saved! Opening WhatsApp Web for ${targetContactName}...`);
    if (onMeetingScheduled) onMeetingScheduled(saved);
    onClose();
  };

  const handleScheduleAndShareEmail = async () => {
    const saved = await saveMeetingToBackend();
    if (!saved) return;

    const invitationText = getInvitationText();
    const subject = `Scheduled Consultation Meeting: ${title || 'LEAMSS Immigration'} - ${getFormattedDate()} at ${meetingTime}`;

    if (onOpenEmailModal && activeLead) {
      onOpenEmailModal(subject, invitationText, null, activeLead);
    } else if (targetContactEmail) {
      const mailtoUrl = `mailto:${targetContactEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(invitationText)}`;
      window.open(mailtoUrl, '_blank');
    }

    toast.success(`Meeting saved! Email invitation ready.`);
    if (onMeetingScheduled) onMeetingScheduled(saved);
    onClose();
  };

  if (!isOpen) return null;

  const isDefaultApplied =
    (platform === 'Google Meet' && meetingLink && meetingLink === defaultMeetLink) ||
    (platform === 'Zoom' && meetingLink && meetingLink === defaultZoomLink);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[92vh] overflow-y-auto p-0 rounded-2xl border-slate-200 shadow-2xl">
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-5 rounded-t-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20">
                <Video className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h3 className="font-bold text-base text-white flex items-center gap-2">
                  Schedule Video Consultation
                  <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-400/30 text-[10px] font-semibold py-0.5">
                    Live Video Room
                  </Badge>
                </h3>
                <p className="text-xs text-slate-300 mt-0.5">
                  Client: <span className="font-semibold text-white">{targetContactName}</span>
                  {targetContactPhone && <span className="ml-2 text-slate-400">({targetContactPhone})</span>}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 text-xs text-slate-700">
          {/* Client Selector (if not preselected) */}
          {!lead && leads && leads.length > 0 && (
            <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
              <label className="block text-xs font-bold text-slate-900 mb-1">
                Select Client / Lead *
              </label>
              <Select
                value={selectedLeadId}
                onValueChange={(val) => {
                  setSelectedLeadId(val);
                  const found = leads.find(l => l.id === val);
                  if (found) {
                    setTitle(`Immigration Consultation - ${found.name || 'Client'}`);
                  }
                }}
              >
                <SelectTrigger className="h-9 text-xs bg-white">
                  <SelectValue placeholder="Choose client from CRM..." />
                </SelectTrigger>
                <SelectContent className="max-h-56">
                  {leads.map(l => (
                    <SelectItem key={l.id} value={l.id}>
                      {l.name} {l.phone ? `(${l.phone})` : ''} - {l.country || 'Lead'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Platform Toggle */}
          <div>
            <label className="block text-xs font-bold text-slate-900 mb-2">
              Select Consultation Platform *
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Google Meet Card */}
              <div
                onClick={() => handlePlatformChange('Google Meet')}
                className={`cursor-pointer rounded-xl p-3 border-2 transition-all flex items-center gap-2.5 ${
                  platform === 'Google Meet'
                    ? 'border-emerald-500 bg-emerald-50/50 shadow-sm ring-1 ring-emerald-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-700 font-bold shrink-0">
                  <Video className="w-4 h-4 text-emerald-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-xs">Google Meet</span>
                    {platform === 'Google Meet' && (
                      <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500 truncate mt-0.5">Instant browser room</p>
                </div>
              </div>

              {/* Zoom Card */}
              <div
                onClick={() => handlePlatformChange('Zoom')}
                className={`cursor-pointer rounded-xl p-3 border-2 transition-all flex items-center gap-2.5 ${
                  platform === 'Zoom'
                    ? 'border-blue-500 bg-blue-50/50 shadow-sm ring-1 ring-blue-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center text-blue-700 font-bold shrink-0">
                  <Video className="w-4 h-4 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-xs">Zoom</span>
                    {platform === 'Zoom' && (
                      <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500 truncate mt-0.5">HD video & screen share</p>
                </div>
              </div>

              {/* Calendly Card */}
              <div
                onClick={() => handlePlatformChange('Calendly')}
                className={`cursor-pointer rounded-xl p-3 border-2 transition-all flex items-center gap-2.5 ${
                  platform === 'Calendly'
                    ? 'border-sky-500 bg-sky-50/50 shadow-sm ring-1 ring-sky-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="w-8 h-8 rounded-lg bg-sky-100 flex items-center justify-center text-sky-700 font-bold shrink-0">
                  <Calendar className="w-4 h-4 text-sky-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-xs">Calendly</span>
                    {platform === 'Calendly' && (
                      <span className="w-2 h-2 rounded-full bg-sky-600"></span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500 truncate mt-0.5">Auto-sync & reminders</p>
                </div>
              </div>
            </div>
          </div>

          {/* Meeting Title / Topic */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Meeting Topic / Title
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Canada PR Eligibility Assessment"
              className="h-9 text-xs"
            />
          </div>

          {/* Date, Time & Duration */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-500" /> Date *
              </label>
              <Input
                type="date"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
                className="h-9 text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-500" /> Time *
              </label>
              <Input
                type="time"
                value={meetingTime}
                onChange={(e) => setMeetingTime(e.target.value)}
                className="h-9 text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Duration
              </label>
              <Select
                value={String(durationMinutes)}
                onValueChange={(v) => setDurationMinutes(parseInt(v) || 30)}
              >
                <SelectTrigger className="h-9 text-xs bg-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">15 Minutes</SelectItem>
                  <SelectItem value="30">30 Minutes (Recommended)</SelectItem>
                  <SelectItem value="45">45 Minutes</SelectItem>
                  <SelectItem value="60">60 Minutes (1 Hour)</SelectItem>
                  <SelectItem value="90">90 Minutes</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Real Meeting Link Section */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <label className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                <LinkIcon className="w-3.5 h-3.5 text-indigo-600" />
                {platform === 'Google Meet' ? 'Google Meet Room Link *' : (platform === 'Zoom' ? 'Zoom Room Link *' : 'Calendly Booking Link *')}
              </label>
              {isDefaultApplied && (
                <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 font-semibold bg-emerald-100/70 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Saved Permanent Room
                </span>
              )}
            </div>

            {/* Quick Action Helpers for Google Meet */}
            {platform === 'Google Meet' && (
              <div className="p-3 bg-white rounded-lg border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="text-[11px] text-slate-600 font-medium flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                    Quick Actions:
                  </span>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleLaunchGoogleMeet}
                      className="h-7 px-2.5 text-[11px] bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1 shadow-sm"
                      title="Open Google Meet in a new tab to create a live room"
                    >
                      <Video className="w-3 h-3" /> 1. Launch meet.google.com/new
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={handlePasteFromClipboard}
                      className="h-7 px-2.5 text-[11px] bg-white hover:bg-slate-50 text-slate-700 border-slate-300 font-semibold gap-1"
                      title="Paste copied Google Meet link from clipboard"
                    >
                      <ClipboardPaste className="w-3 h-3 text-indigo-600" /> 2. Paste Link
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => window.open(getGoogleCalendarUrl(), '_blank')}
                      className="h-7 px-2 text-[11px] text-slate-600 hover:text-slate-900 gap-1"
                      title="Schedule in Google Calendar with Google Meet enabled"
                    >
                      <CalendarPlus className="w-3 h-3 text-indigo-600" /> Google Calendar
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Quick Action Helpers for Zoom */}
            {platform === 'Zoom' && (
              <div className="p-3 bg-white rounded-lg border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="text-[11px] text-slate-600 font-medium flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                    Zoom Room Actions:
                  </span>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleLaunchZoom}
                      className="h-7 px-2.5 text-[11px] bg-blue-600 hover:bg-blue-700 text-white font-semibold gap-1 shadow-sm"
                      title="Launch an instant real Zoom meeting"
                    >
                      <Video className="w-3 h-3" /> 1. Launch Instant Zoom
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={handlePasteFromClipboard}
                      className="h-7 px-2.5 text-[11px] bg-white hover:bg-slate-50 text-slate-700 border-slate-300 font-semibold gap-1"
                      title="Paste copied Zoom link from clipboard"
                    >
                      <ClipboardPaste className="w-3 h-3 text-indigo-600" /> 2. Paste Link
                    </Button>
                  </div>
                </div>
                <p className="text-[11px] text-slate-500">
                  Tip: Paste your Personal Meeting ID (PMI) or custom link (e.g. <code>https://us05web.zoom.us/j/1234567890</code> or <code>https://zoom.us/my/yourname</code>).
                </p>
              </div>
            )}

            {/* Quick Action Helpers for Calendly */}
            {platform === 'Calendly' && (
              <div className="p-3 bg-white rounded-lg border border-slate-200/80 space-y-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="text-[11px] text-slate-600 font-medium flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-sky-500" />
                    Calendly Integration Actions:
                  </span>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleGenerateCalendlyLink}
                      disabled={generatingCalendlyLink}
                      className="h-7 px-2.5 text-[11px] bg-sky-600 hover:bg-sky-700 text-white font-semibold gap-1 shadow-sm"
                      title="Generate a dynamic single-use scheduling link for this client via Calendly API"
                    >
                      <RefreshCw className={`w-3 h-3 ${generatingCalendlyLink ? 'animate-spin' : ''}`} />
                      {generatingCalendlyLink ? 'Generating Link...' : '1. Generate Single-Use Link'}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => window.open(meetingLink || defaultCalendlyLink, '_blank')}
                      className="h-7 px-2.5 text-[11px] bg-white hover:bg-slate-50 text-slate-700 border-slate-300 font-semibold gap-1"
                      title="Open Calendly booking page in new tab"
                    >
                      <ExternalLink className="w-3 h-3 text-sky-600" /> 2. Open Page
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={handlePasteFromClipboard}
                      className="h-7 px-2.5 text-[11px] bg-white hover:bg-slate-50 text-slate-700 border-slate-300 font-semibold gap-1"
                      title="Paste link from clipboard"
                    >
                      <ClipboardPaste className="w-3 h-3 text-indigo-600" /> 3. Paste Link
                    </Button>
                  </div>
                </div>
                <p className="text-[11px] text-slate-500">
                  Clients receive automated Google Meet calendar invitation & CRM real-time sync with 24h/1h/15m reminders.
                </p>
              </div>
            )}

            {/* Link Input Row */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Input
                  value={meetingLink}
                  onChange={(e) => setMeetingLink(e.target.value)}
                  placeholder={
                    platform === 'Google Meet'
                      ? 'https://meet.google.com/xxx-yyyy-zzz'
                      : (platform === 'Zoom'
                          ? 'https://us05web.zoom.us/j/... or https://zoom.us/my/...'
                          : 'https://calendly.com/rohit-leamss/permanent-residency-visa')
                  }
                  className="h-9 text-xs font-mono bg-white pr-20"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(meetingLink, 'Meeting link copied!')}
                  className="absolute right-1 top-1 h-7 px-2 text-[11px] text-slate-600 hover:text-slate-900 gap-1"
                >
                  {copiedLink ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  {copiedLink ? 'Copied' : 'Copy'}
                </Button>
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  if (meetingLink) {
                    window.open(meetingLink, '_blank');
                  } else {
                    toast.error('No meeting link entered yet');
                  }
                }}
                className="h-9 text-xs gap-1 text-slate-700 hover:text-slate-900 bg-white"
                title="Test join room in new tab"
              >
                <ExternalLink className="w-3.5 h-3.5 text-indigo-600" /> Test Join
              </Button>
            </div>

            {/* Save as Permanent Default Checkbox */}
            <label className="flex items-center gap-2 pt-1 text-xs cursor-pointer select-none">
              <input
                type="checkbox"
                checked={saveAsDefault}
                onChange={(e) => setSaveAsDefault(e.target.checked)}
                className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
              />
              <span className="text-slate-700 font-medium">
                Save as my permanent {platform === 'Google Meet' ? 'Google Meet' : (platform === 'Zoom' ? 'Zoom' : 'Calendly')} link (automatically pre-fills for all future client consultations)
              </span>
            </label>

            {/* Booking Confirmation Email Toggle */}
            <label className="flex items-center gap-2 pt-0.5 text-xs cursor-pointer select-none">
              <input
                type="checkbox"
                checked={sendConfirmationEmail}
                onChange={(e) => setSendConfirmationEmail(e.target.checked)}
                className="w-4 h-4 rounded text-emerald-600 border-slate-300 focus:ring-emerald-500"
              />
              <span className="text-slate-800 font-semibold flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-emerald-600" />
                Send booking confirmation email with Google Meet link to client {targetContactEmail ? `(${targetContactEmail})` : '(No email set)'}
              </span>
            </label>

            {/* Optional Zoom Passcode field */}
            {platform === 'Zoom' && (
              <div className="flex items-center gap-3 pt-1 text-xs">
                <span className="font-semibold text-slate-700">Zoom Passcode (Optional):</span>
                <Input
                  value={meetingPassword}
                  onChange={(e) => setMeetingPassword(e.target.value)}
                  placeholder="Optional passcode"
                  className="h-7 w-36 text-xs font-mono bg-white"
                />
                <span className="text-[11px] text-slate-500">Leave blank if passcode is already inside the join URL</span>
              </div>
            )}
          </div>

          {/* Agenda / Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Consultation Agenda & Preparation Notes
            </label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Key topics to discuss with the client..."
              className="h-16 text-xs resize-none"
            />
          </div>

          {/* Live Invitation Message Preview Accordion */}
          <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
            <button
              type="button"
              onClick={() => setShowPreview(!showPreview)}
              className="w-full px-3.5 py-2.5 bg-slate-50 hover:bg-slate-100 flex items-center justify-between text-left transition-colors"
            >
              <span className="font-semibold text-xs text-slate-800 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                Preview Client Invitation Message
              </span>
              <span className="text-[11px] text-slate-500 font-medium">
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </span>
            </button>

            {showPreview && (
              <div className="p-3 bg-slate-50/50 border-t border-slate-200 space-y-2">
                <pre className="text-[11px] whitespace-pre-wrap font-sans text-slate-700 bg-white p-3 rounded-lg border border-slate-200 leading-relaxed shadow-inner">
                  {getInvitationText()}
                </pre>
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(getInvitationText(), 'Invitation message copied!')}
                    className="h-6 text-[11px] text-slate-600 gap-1"
                  >
                    <Copy className="w-3 h-3" /> Copy Message Text
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer with 1-Click Sharing Actions */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 rounded-b-2xl flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-[11px] text-slate-500 hidden sm:block">
            Auto-records to complete client timeline & CRM history.
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end flex-wrap">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onClose}
              className="h-8 text-xs text-slate-600"
            >
              Cancel
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleScheduleOnly}
              disabled={saving}
              className="h-8 text-xs bg-white text-slate-800 hover:bg-slate-100"
            >
              Save Only
            </Button>

            <Button
              type="button"
              size="sm"
              onClick={handleScheduleAndShareEmail}
              disabled={saving}
              className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm"
            >
              <Mail className="w-3.5 h-3.5" /> Share via Email
            </Button>

            <Button
              type="button"
              size="sm"
              onClick={handleScheduleAndShareWhatsApp}
              disabled={saving}
              className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 shadow-sm"
            >
              <MessageCircle className="w-3.5 h-3.5" /> Share via WhatsApp
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
