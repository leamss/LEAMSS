/**
 * My CRM — Comprehensive Sales CRM System
 * Manages the complete sales lifecycle:
 * Lead → Assignment → Call → WhatsApp → Email → Follow-up → Assessment → Proposal → Payment → Deal Closing → Client Conversion → Client Portal & Case Manager Handover
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import {
  ArrowLeft, Plus, Search, RefreshCw, ArrowUpDown, LayoutGrid, List as ListIcon,
  Phone, Mail, MessageCircle, X, Clock, User, MapPin, GraduationCap,
  Briefcase, ChevronRight, ChevronDown, Send, Sparkles, CheckCircle2, LayoutDashboard,
  CalendarClock, TrendingUp, Users, Menu, UserPlus, ListChecks, CheckCheck,
  PhoneCall, PhoneIncoming, PhoneOutgoing, Video, Calendar, DollarSign,
  FileText, ShieldCheck, ShieldAlert, AlertCircle, Upload, GitMerge, FileSpreadsheet,
  Flame, Zap, Snowflake, Check, Award, ArrowUpRight, ArrowDownLeft, Filter, ChevronLeft,
  PieChart, BarChart3, Bot, Activity, HelpCircle, Inbox, Tag, Download, UserCheck, FileCheck, Eye,
  Mic, MicOff, PhoneOff, Play, Pause, Volume2, FastForward, Radio, Disc,
  Trash2, Split, SlidersHorizontal, Layers, Hash, ArrowRightLeft, CheckSquare, Edit, Pencil, QrCode,
  MessageSquareReply, LayoutTemplate, Settings, Key, Shield, Bell, BellOff, Paperclip, PenTool,
  Copy, ClipboardPaste, ExternalLink, Globe, Target, Instagram, Facebook, MessageSquare, Save,
  CloudDownload, StickyNote
} from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';
import GmailComposer from '@/components/GmailComposer';
import EmailSignatureEditor from '@/components/EmailSignatureEditor';
import WhatsAppConfigModal from '@/components/admin/WhatsAppConfigModal';
import MeetingModal from '@/components/MeetingModal';
import EmailTemplatesManager from '@/pages/sales/EmailTemplatesManager';
import WhatsAppTemplatesManager from '@/pages/sales/WhatsAppTemplatesManager';
import SalesPersonOverview from '@/pages/admin/SalesPersonOverview';
import WebsiteLeadsOverview from '@/pages/admin/WebsiteLeadsOverview';
import CRMSalespersonActivityAudit from '@/pages/admin/CRMSalespersonActivityAudit';

const BACKEND_URL = (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com'))
  ? 'https://api.leamss.com'
  : (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const STAGES = [
  { key: 'new', label: 'New', color: 'bg-slate-500', bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-300' },
  { key: 'contacted', label: 'Contacted', color: 'bg-blue-500', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-300' },
  { key: 'connected', label: 'Connected', color: 'bg-sky-500', bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-300' },
  { key: 'interested', label: 'Interested', color: 'bg-cyan-500', bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-300' },
  { key: 'qualified', label: 'Qualified', color: 'bg-indigo-500', bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-300' },
  { key: 'assessment', label: 'Assessment', color: 'bg-purple-500', bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-300' },
  { key: 'proposal', label: 'Proposal', color: 'bg-violet-500', bg: 'bg-violet-50', text: 'text-violet-700', border: 'border-violet-300' },
  { key: 'negotiation', label: 'Negotiation', color: 'bg-amber-500', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-300' },
  { key: 'payment_pending', label: 'Payment Pending', color: 'bg-orange-500', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-300' },
  { key: 'payment_received', label: 'Payment Received', color: 'bg-teal-500', bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-300' },
  { key: 'won', label: 'Won', color: 'bg-emerald-600', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300' },
  { key: 'closed_won', label: 'Closed Won', color: 'bg-emerald-600', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300' },
  { key: 'converted', label: 'Converted', color: 'bg-emerald-500', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-300' },
  { key: 'not_interested', label: 'Not Interested', color: 'bg-rose-500', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-300' },
  { key: 'lost', label: 'Lost', color: 'bg-red-600', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-300' },
];
const STAGE_MAP = Object.fromEntries(STAGES.map(s => [s.key, s]));

const SOURCES = [
  'Website',
  'Calendly',
  'Google Ads',
  'Facebook Ads',
  'Instagram',
  'Google Sheets',
  'Zoho',
  'WhatsApp',
  'Referral',
  'Walk-In',
  'Direct Call',
  'Excel Import',
  'Unknown'
];

const SOURCE_CONFIG = {
  'Website': { label: 'Website', bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200', icon: Globe },
  'Calendly': { label: 'Calendly', bg: 'bg-slate-900', text: 'text-white', border: 'border-slate-800', icon: Calendar },
  'calendly': { label: 'Calendly', bg: 'bg-slate-900', text: 'text-white', border: 'border-slate-800', icon: Calendar },
  'Calendly Bookings': { label: 'Calendly', bg: 'bg-slate-900', text: 'text-white', border: 'border-slate-800', icon: Calendar },
  'Google Ads': { label: 'Google Ads', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: Target },
  'Facebook Ads': { label: 'Facebook Ads', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Facebook },
  'Facebook': { label: 'Facebook Ads', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Facebook },
  'Instagram': { label: 'Instagram', bg: 'bg-pink-50', text: 'text-pink-700', border: 'border-pink-200', icon: Instagram },
  'Google Sheets': { label: 'Google Sheets', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: FileSpreadsheet },
  'Google_sheets': { label: 'Google Sheets', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: FileSpreadsheet },
  'Zoho': { label: 'Zoho', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', icon: Zap },
  'Zoho CRM': { label: 'Zoho', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', icon: Zap },
  'WhatsApp': { label: 'WhatsApp', bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-300', icon: MessageSquare },
  'Referral': { label: 'Referral', bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: Users },
  'Excel Import': { label: 'Excel Import', bg: '!bg-purple-600 hover:!bg-purple-700', text: '!text-white', border: '!border-purple-600', icon: FileSpreadsheet },
  'Walk-In': { label: 'Walk-In', bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200', icon: MapPin },
  'Direct Call': { label: 'Direct Call', bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200', icon: PhoneCall },
  'Unknown': { label: 'Unknown', bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-300', icon: HelpCircle },
};

const getSourceConfig = (source) => {
  if (!source || String(source).trim() === '' || String(source).toLowerCase() === 'unknown') {
    return SOURCE_CONFIG['Unknown'];
  }
  const clean = String(source).trim();
  if (SOURCE_CONFIG[clean]) return SOURCE_CONFIG[clean];
  const lower = clean.toLowerCase();
  if (lower.includes('calendly')) return SOURCE_CONFIG['Calendly'];
  if (lower.includes('google ads') || lower.includes('adwords')) return SOURCE_CONFIG['Google Ads'];
  if (lower.includes('facebook') || lower.includes('meta')) return SOURCE_CONFIG['Facebook Ads'];
  if (lower.includes('instagram') || lower.includes('ig')) return SOURCE_CONFIG['Instagram'];
  if (lower.includes('sheet')) return SOURCE_CONFIG['Google Sheets'];
  if (lower.includes('zoho')) return SOURCE_CONFIG['Zoho'];
  if (lower.includes('whatsapp')) return SOURCE_CONFIG['WhatsApp'];
  if (lower.includes('website') || lower.includes('popup')) return SOURCE_CONFIG['Website'];
  return { label: clean, bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200', icon: Globe };
};
const COUNTRIES = ['Canada', 'Australia', 'UK', 'USA', 'Germany', 'New Zealand', 'Singapore', 'Other'];

const emptyLead = {
  name: '', email: '', phone: '', alternate_phone: '', whatsapp_number: '', address: '', city: '', country: 'India',
  service_interested: 'Canada PR Express Entry', country_of_interest: 'Canada', source: 'Website', campaign: 'Organic',
  date_of_birth: '', occupation: '', total_work_experience: '', budget: '₹75,000',
  priority: 'medium', stage: 'new', message: '', latest_qualification: '', university: '', course: '',
  assigned_to: '', assigned_to_name: '',
};

const timeAgo = (iso) => {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

const getInitials = (name) => {
  if (!name) return 'CL';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

const getSanitizedWhatsAppNumber = (phone) => {
  if (!phone) return '';
  let p = String(phone).trim();
  if (p.includes('E') || p.includes('e')) {
    try {
      const num = Number(p);
      if (!isNaN(num)) {
        p = num.toLocaleString('fullwide', { useGrouping: false });
      }
    } catch (e) {}
  }
  const digits = p.replace(/[^\d]/g, '');
  if (digits.length === 10) return `91${digits}`;
  return digits;
};

const getDirectWhatsAppWebLink = (phone, text = '') => {
  if (!phone) return null;
  const clean = getSanitizedWhatsAppNumber(phone);
  if (!clean) return null;
  return text
    ? `https://web.whatsapp.com/send?phone=${clean}&text=${encodeURIComponent(text)}`
    : `https://web.whatsapp.com/send?phone=${clean}`;
};

const getWhatsAppDesktopAppLink = (phone, text = '') => {
  if (!phone) return null;
  const clean = getSanitizedWhatsAppNumber(phone);
  if (!clean) return null;
  return text
    ? `whatsapp://send?phone=${clean}&text=${encodeURIComponent(text)}`
    : `whatsapp://send?phone=${clean}`;
};

const waLink = (phone, text = '') => {
  if (!phone) return null;
  const clean = getSanitizedWhatsAppNumber(phone);
  if (!clean) return null;
  const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  if (isMobile) {
    return text ? `https://wa.me/${clean}?text=${encodeURIComponent(text)}` : `https://wa.me/${clean}`;
  }
  return text
    ? `https://web.whatsapp.com/send?phone=${clean}&text=${encodeURIComponent(text)}`
    : `https://web.whatsapp.com/send?phone=${clean}`;
};

const getPersonalizedWaTemplates = (lead, repName, customTemplates = null) => {
  const clientName = lead?.name ? lead.name.trim().split(' ')[0] : 'Client';
  const fullName = lead?.name ? lead.name.trim() : 'Client';
  const rep = repName || 'LEAMSS Consultant';
  const country = lead?.country_of_interest || lead?.interested_country || 'Canada';
  const service = lead?.service_interested || 'Immigration Consulting';
  const phone = lead?.phone || lead?.whatsapp_number || '';

  if (Array.isArray(customTemplates) && customTemplates.length > 0) {
    return customTemplates.map((tpl) => {
      let bodyText = tpl.body || tpl.text || '';
      bodyText = bodyText
        .replace(/\{client_name\}/gi, clientName)
        .replace(/\{full_name\}/gi, fullName)
        .replace(/\{consultant_name\}/gi, rep)
        .replace(/\{country\}/gi, country)
        .replace(/\{service\}/gi, service)
        .replace(/\{phone\}/gi, phone);
      return {
        id: tpl.id || tpl._id || `tpl_${Math.random()}`,
        title: tpl.title || tpl.name || 'WhatsApp Template',
        category: tpl.category || 'General',
        text: bodyText
      };
    });
  }

  return [
    {
      id: 'tpl_welcome',
      title: '🌟 Welcome & Introduction',
      category: 'Introduction',
      text: `Hello ${clientName}, this is ${rep} from LEAMSS Immigration Consulting. Thank you for your interest in our ${country} ${service} pathways. When would be a good time for a quick 5-minute call today to review your profile?`
    },
    {
      id: 'tpl_assessment',
      title: '📋 Assessment Ready',
      category: 'Assessment',
      text: `Hi ${clientName}, this is ${rep} from LEAMSS. Great news! Your preliminary profile assessment for ${country} immigration is ready for review. Would you like to connect over a quick call to go through your eligibility score?`
    },
    {
      id: 'tpl_followup',
      title: '⏰ Quick Check-in Follow-up',
      category: 'Follow-up',
      text: `Hi ${clientName}, ${rep} here from LEAMSS following up on our previous conversation regarding your ${country} visa application. Do you have any questions I can help clarify for you today?`
    },
    {
      id: 'tpl_documents',
      title: '📄 Document Checklist Request',
      category: 'Documentation',
      text: `Hello ${clientName}, this is ${rep} from LEAMSS. To evaluate your points accurately and initiate your ${country} application, could you please share your updated CV/Resume and latest qualification degree?`
    },
    {
      id: 'tpl_consultation',
      title: '📅 Consultation Confirmation',
      category: 'Meeting',
      text: `Dear ${clientName}, your one-on-one consultation with ${rep} regarding your ${country} ${service} has been scheduled. Please ensure you have your documents ready. Feel free to message here if you need to reschedule.`
    },
    {
      id: 'tpl_retainer',
      title: '💳 Retainer Proposal Next Steps',
      category: 'Closing',
      text: `Dear ${clientName}, this is ${rep} from LEAMSS. Your customized immigration retainer proposal for ${country} has been prepared. Please let me know when we can connect to finalize the onboarding steps.`
    },
    {
      id: 'tpl_visa_update',
      title: '✈️ Visa & Case File Update',
      category: 'Update',
      text: `Hi ${clientName}, this is ${rep} from LEAMSS with an update on your ${country} file. We have reviewed your case file and are moving to the next submission stage. Please check your email or let me know if you have any questions.`
    },
    {
      id: 'tpl_urgent_action',
      title: '⚡ Urgent Document Confirmation',
      category: 'Urgent',
      text: `Hello ${clientName}, urgent update from ${rep} at LEAMSS regarding your ${country} application. We require your immediate confirmation on your pending paperwork to avoid application deadlines. Please reply or call me back as soon as you see this.`
    }
  ];
};

const formatPhoneNumber = (phone) => {
  if (!phone) return 'No phone';
  let p = String(phone).trim();
  if (p.includes('E') || p.includes('e')) {
    try {
      const num = Number(p);
      if (!isNaN(num)) {
        p = num.toLocaleString('fullwide', { useGrouping: false });
      }
    } catch (e) {}
  }
  return p;
};

const formatCallDuration = (sec) => {
  if (!sec || isNaN(sec)) return '0s';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
};

function CallAudioPlayer({ recordingUrl, durationSeconds, callerName }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(durationSeconds || 0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const audioRef = useRef(null);

  const fullUrl = useMemo(() => {
    if (!recordingUrl) return '';
    if (recordingUrl.startsWith('http') || recordingUrl.startsWith('blob:') || recordingUrl.startsWith('data:')) {
      return recordingUrl;
    }
    const base = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
    return `${base}${recordingUrl.startsWith('/') ? '' : '/'}${recordingUrl}`;
  }, [recordingUrl]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => {
      if (audio.duration && !isNaN(audio.duration)) {
        setDuration(Math.round(audio.duration));
      }
    };
    const onEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
    };
  }, []);

  const togglePlay = () => {
    if (!audioRef.current || !fullUrl) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.playbackRate = playbackRate;
      audioRef.current.play().then(() => setIsPlaying(true)).catch((e) => {
        console.error('Audio playback error:', e);
      });
    }
  };

  const handleSeek = (e) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  const cycleSpeed = () => {
    const speeds = [1, 1.25, 1.5, 2.0];
    const nextSpeed = speeds[(speeds.indexOf(playbackRate) + 1) % speeds.length];
    setPlaybackRate(nextSpeed);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed;
    }
  };

  const formatTime = (secs) => {
    const s = Math.floor(secs || 0);
    const m = Math.floor(s / 60);
    const rem = s % 60;
    return `${m}:${rem < 10 ? '0' : ''}${rem}`;
  };

  if (!recordingUrl) return null;

  return (
    <div className="mt-2.5 p-2.5 bg-slate-900 text-white rounded-xl border border-slate-800 shadow-sm flex flex-col gap-2">
      <audio ref={audioRef} src={fullUrl} preload="metadata" />
      <div className="flex items-center justify-between text-[11px] text-slate-400">
        <span className="flex items-center gap-1 font-semibold text-emerald-400">
          <Disc className={`w-3.5 h-3.5 ${isPlaying ? 'animate-spin text-emerald-400' : 'text-slate-400'}`} />
          Call Recording Playback
        </span>
        <span className="font-mono text-xs text-slate-300">
          {formatTime(currentTime)} / {formatTime(duration || durationSeconds || 0)}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          onClick={togglePlay}
          className="h-7 w-7 rounded-full p-0 bg-emerald-600 hover:bg-emerald-500 text-white shrink-0 flex items-center justify-center shadow"
        >
          {isPlaying ? <Pause className="w-3.5 h-3.5 fill-white" /> : <Play className="w-3.5 h-3.5 fill-white translate-x-0.5" />}
        </Button>

        <input
          type="range"
          min="0"
          max={duration || durationSeconds || 100}
          step="0.1"
          value={currentTime}
          onChange={handleSeek}
          className="flex-1 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />

        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={cycleSpeed}
          className="h-6 px-1.5 text-[10px] font-mono text-slate-300 hover:text-white hover:bg-slate-800 rounded"
        >
          {playbackRate}x
        </Button>

        <a
          href={fullUrl}
          download={callerName ? `Call_${callerName}_Recording.webm` : 'call_recording.webm'}
          target="_blank"
          rel="noreferrer"
          className="h-6 px-1.5 flex items-center gap-1 text-[10px] text-slate-300 hover:text-emerald-400 hover:bg-slate-800 rounded transition-colors"
          title="Download Recording"
        >
          <Download className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}

export default function MyCRM() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const u = localStorage.getItem('user');
      return u ? JSON.parse(u) : null;
    } catch (e) {
      return null;
    }
  });

  // Role check: Only Admin can access Website Leads, Bulk Import, and Template Management
  const isAdmin = currentUser?.role === 'admin' || currentUser?.role === 'admin_owner' || currentUser?.role === 'super_admin' || currentUser?.rbac_role === 'admin' || currentUser?.rbac_role === 'admin_owner' || currentUser?.rbac_role === 'super_admin';

  const [leads, setLeads] = useState([]);
  const [deals, setDeals] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [calls, setCalls] = useState([]);
  const [allEmails, setAllEmails] = useState([]);
  const [allEmailsLoading, setAllEmailsLoading] = useState(false);
  const [callSearch, setCallSearch] = useState('');
  const [callFilterOutcome, setCallFilterOutcome] = useState('all');
  const [callFilterDirection, setCallFilterDirection] = useState('all');
  const [callFilterSalesperson, setCallFilterSalesperson] = useState('all');
  const [callDatePreset, setCallDatePreset] = useState('all'); // all, today, yesterday, this_week, this_month, custom
  const [callDateFrom, setCallDateFrom] = useState('');
  const [callDateTo, setCallDateTo] = useState('');
  const [callTranscript, setCallTranscript] = useState('');
  const [expandedTranscripts, setExpandedTranscripts] = useState({});
  const [transcriptModal, setTranscriptModal] = useState({ open: false, call: null, transcriptText: '', saving: false });
  const [regeneratingAiCalls, setRegeneratingAiCalls] = useState({});
  const [emailCenterSearch, setEmailCenterSearch] = useState('');
  const [emailFilterDirection, setEmailFilterDirection] = useState('all');
  const [selectedEmailClientKey, setSelectedEmailClientKey] = useState(null);
  const [emailCenterQuickReplyText, setEmailCenterQuickReplyText] = useState('');
  const [emailCenterQuickNotify, setEmailCenterQuickNotify] = useState(false);
  const [sendingEmailCenterReply, setSendingEmailCenterReply] = useState(false);
  const [emailCenterThreadSortAsc, setEmailCenterThreadSortAsc] = useState(true);
  const [showQuickCallSelectModal, setShowQuickCallSelectModal] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [payments, setPayments] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [automationRules, setAutomationRules] = useState([]);
  const [actionsWaiting, setActionsWaiting] = useState({
    calls_due: 0, follow_ups_due: 0, whatsapp_replies: 0, emails_pending: 0,
    payment_followups: 0, documents_pending: 0, meetings_today: 0, overdue_actions: 0
  });
  const [stats, setStats] = useState({ total: 0, conversion_rate: 0, stages: {}, revenue: 0, score_breakdown: {} });
  const [performance, setPerformance] = useState(null);
  const [caseManagers, setCaseManagers] = useState([]);
  const [salesReps, setSalesReps] = useState([]);
  const [loading, setLoading] = useState(true);

  // Active View & Navigation
  const [view, setView] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [leadsMenuOpen, setLeadsMenuOpen] = useState(true);
  const [commMenuOpen, setCommMenuOpen] = useState(true);
  const [activitiesMenuOpen, setActivitiesMenuOpen] = useState(true);
  const [waTemplates, setWaTemplates] = useState([]);
  const [websiteLeadsCount, setWebsiteLeadsCount] = useState(0);
  const [websiteLeadsUnassignedCount, setWebsiteLeadsUnassignedCount] = useState(0);
  const [websiteMenuOpen, setWebsiteMenuOpen] = useState(true);
  const [selectedWebsiteCategory, setSelectedWebsiteCategory] = useState('all');
  const [websiteCategoriesData, setWebsiteCategoriesData] = useState({});

  const location = useLocation();
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const qView = params.get('view');
    const qCat = params.get('category');
    if (qCat && ['all', 'PR', 'TR', 'Work', 'Study', 'Tourist', 'Family', 'General'].includes(qCat)) {
      setSelectedWebsiteCategory(qCat);
    }
    if (qView && ['website_leads', 'email_templates', 'whatsapp_templates', 'internal_salespersons', 'external_salespersons', 'dashboard', 'table', 'kanban', 'calls', 'whatsapp', 'emails', 'followups', 'meetings', 'pipeline', 'payments', 'performance'].includes(qView)) {
      if (qView === 'website_leads' && !isAdmin) {
        setView('table');
      } else {
        setView(qView);
      }
    }
  }, [location.search, isAdmin]);

  // If a non-admin is in website_leads view, redirect them to table
  useEffect(() => {
    if (!isAdmin && view === 'website_leads') {
      setView('table');
    }
  }, [isAdmin, view]);

  // Filter States
  const [search, setSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [countryFilter, setCountryFilter] = useState('all');
  const [assignedTodayFilter, setAssignedTodayFilter] = useState(false);
  const [paymentFilter, setPaymentFilter] = useState('all'); // all, paid, unpaid
  const [reportFilter, setReportFilter] = useState('all'); // all, generated, paid_pending
  const [salespersonFilter, setSalespersonFilter] = useState('all');
  const [recentLeadsTab, setRecentLeadsTab] = useState('all');

  // Cockpit Action States
  const [syncingLeads, setSyncingLeads] = useState(false);
  const [markingPaidId, setMarkingPaidId] = useState(null);
  const [checkingPaymentId, setCheckingPaymentId] = useState(null);
  const [sendingPaymentLinkId, setSendingPaymentLinkId] = useState(null);
  const [sendingResumeReqId, setSendingResumeReqId] = useState(null);
  const [convertingLeadId, setConvertingLeadId] = useState(null);
  const [showPartnerReportModal, setShowPartnerReportModal] = useState(false);
  const [partnerReportData, setPartnerReportData] = useState(null);
  const [loadingPartnerReport, setLoadingPartnerReport] = useState(false);


  // Modals & Selected Workspace
  const [selectedLead, setSelectedLead] = useState(null);
  const [workspaceTab, setWorkspaceTab] = useState('overview'); // overview, timeline, communication, followups, deals, handover
  const [leadTimeline, setLeadTimeline] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [showAddLead, setShowAddLead] = useState(false);
  const [newLead, setNewLead] = useState(emptyLead);
  const [newLeadResumeFile, setNewLeadResumeFile] = useState(null);
  const [showEditLead, setShowEditLead] = useState(false);
  const [editLeadForm, setEditLeadForm] = useState({});
  const [editingLeadId, setEditingLeadId] = useState(null);
  const [editingLead, setEditingLead] = useState(null);
  const [editLeadResumeFile, setEditLeadResumeFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [websiteLeadsRefreshKey, setWebsiteLeadsRefreshKey] = useState(0);

  // In-App Resume Preview & Download State
  const [resumePreviewModal, setResumePreviewModal] = useState({
    open: false,
    lead: null,
    resumeUrl: '',
    filename: '',
  });

  const getResumeUrl = (lead) => {
    if (!lead) return '';
    const isLive = typeof window !== 'undefined' && window.location.hostname.includes('leamss.com');
    const backendBase = isLive
      ? 'https://api.leamss.com'
      : (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001').replace(/\/+$/, '');

    const rawUrl = lead.resume_url || lead.resume_path || lead.resume_link || '';
    if (rawUrl) {
      if (rawUrl.startsWith('/api')) {
        return `${backendBase}${rawUrl}`;
      }
      if (rawUrl.startsWith('http://') || rawUrl.startsWith('https://')) {
        if (isLive && rawUrl.includes('localhost:8001')) {
          return rawUrl.replace('http://localhost:8001', 'https://api.leamss.com');
        }
        if (rawUrl.includes('leamss.com') && !rawUrl.includes('api.leamss.com')) {
          const fname = lead.resume_filename || `${(lead.name || 'Candidate').replace(/\s+/g, '_')}_Resume.pdf`;
          return `${backendBase}/api/cockpit/resume-proxy?url=${encodeURIComponent(rawUrl)}&filename=${encodeURIComponent(fname)}`;
        }
        return rawUrl;
      }
      const cleanPath = rawUrl.startsWith('/') ? rawUrl : `/${rawUrl}`;
      return `${backendBase}/api${cleanPath}`;
    }
    const fileId = lead.resume_file_id || lead.id || lead.lead_number;
    return `${backendBase}/api/cockpit/resume/${fileId}`;
  };

  const handleOpenResumePreview = (lead) => {
    if (!lead) return;
    const clientName = lead.name || 'Candidate';
    const currentTimeStr = getFormattedLocalTimeStr();
    const sourceTabName = view === 'kanban' ? 'Leads Board' : 'All Leads Table';

    axios.post(`${API}/salesperson-activity/log`, {
      activity_type: 'client_view',
      client_id: lead.id || lead.unique_id,
      client_name: clientName,
      client_phone: lead.phone,
      client_email: lead.email,
      title: `Viewed Resume: ${clientName} (${sourceTabName})`,
      details: `Salesperson previewed candidate resume for ${clientName} from ${sourceTabName} at ${currentTimeStr}.`,
      start_time: currentTimeStr,
      metadata: {
        source_view: view,
        source_tab: sourceTabName,
        lead_id: lead.id,
        lead_number: lead.lead_number,
        timezone: 'Asia/Kolkata'
      }
    }, getAuthHeader()).catch(() => {});

    const url = getResumeUrl(lead);
    setResumePreviewModal({
      open: true,
      lead,
      resumeUrl: url,
      filename: lead.resume_filename || `${lead.name?.replace(/\s+/g, '_') || 'Candidate'}_Resume.pdf`,
    });
  };

  const handleDownloadResume = (lead) => {
    if (!lead) return;
    const url = getResumeUrl(lead);
    const link = document.createElement('a');
    link.href = url;
    link.download = lead.resume_filename || `${lead.name?.replace(/\s+/g, '_') || 'Candidate'}_Resume.pdf`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  // In-App Pre-Assessment Report Preview & Download State
  const [reportPreviewModal, setReportPreviewModal] = useState({
    open: false,
    lead: null,
    reportUrl: '',
    filename: '',
  });

  const getPreAssessmentReportUrl = (lead) => {
    if (!lead) return '';
    if (lead.pre_assessment_report_url) {
      if (lead.pre_assessment_report_url.startsWith('http')) return lead.pre_assessment_report_url;
      const cleanPath = lead.pre_assessment_report_url.startsWith('/api')
        ? lead.pre_assessment_report_url
        : `/api${lead.pre_assessment_report_url.startsWith('/') ? '' : '/'}${lead.pre_assessment_report_url}`;
      const backendBase = (
        process.env.REACT_APP_BACKEND_URL ||
        (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001')
      ).replace(/\/+$/, '');
      return `${backendBase}${cleanPath}`;
    }
    const fileId = lead.assessment_report_file_id || lead.assessment_report_id || lead.id;
    return `${API}/cockpit/resume/${fileId}`;
  };

  const handleOpenReportPreview = (lead) => {
    if (!lead) return;
    const clientName = lead.name || 'Client';
    const currentTimeStr = getFormattedLocalTimeStr();
    const sourceTabName = view === 'kanban' ? 'Leads Board' : 'All Leads Table';

    axios.post(`${API}/salesperson-activity/log`, {
      activity_type: 'client_view',
      client_id: lead.id || lead.unique_id,
      client_name: clientName,
      client_phone: lead.phone,
      client_email: lead.email,
      title: `Viewed Pre-Assessment Report: ${clientName} (${sourceTabName})`,
      details: `Salesperson previewed Pre-Assessment Report for client ${clientName} from ${sourceTabName} at ${currentTimeStr}.`,
      start_time: currentTimeStr,
      metadata: {
        source_view: view,
        source_tab: sourceTabName,
        lead_id: lead.id,
        lead_number: lead.lead_number,
        timezone: 'Asia/Kolkata'
      }
    }, getAuthHeader()).catch(() => {});

    const url = getPreAssessmentReportUrl(lead);
    setReportPreviewModal({
      open: true,
      lead,
      reportUrl: url,
      filename: lead.assessment_report_filename || `${lead.name?.replace(/\s+/g, '_') || 'Client'}_Pre_Assessment_Report.pdf`,
    });

  };

  const handleDownloadReport = (lead) => {
    if (!lead) return;
    const url = getPreAssessmentReportUrl(lead);
    const link = document.createElement('a');
    link.href = url;
    link.download = lead.assessment_report_filename || `${lead.name?.replace(/\s+/g, '_') || 'Client'}_Pre_Assessment_Report.pdf`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Multi-Selection State for Leads (Bulk Pre-Assessment Report)
  const [selectedLeadIds, setSelectedLeadIds] = useState(new Set());
  const [isCreatingBulkBatch, setIsCreatingBulkBatch] = useState(false);

  const isLeadResumeAttached = (lead) => {
    if (!lead) return false;
    return Boolean(
      lead.resume_file_id ||
      lead.resume_url ||
      lead.has_resume ||
      lead.resume_uploaded ||
      lead.resume_path ||
      lead.resume_link
    );
  };

  const toggleSelectLead = (leadId) => {
    if (!leadId) return;
    setSelectedLeadIds(prev => {
      const next = new Set(prev);
      if (next.has(leadId)) next.delete(leadId);
      else next.add(leadId);
      return next;
    });
  };

  const toggleSelectAllLeads = () => {
    if (selectedLeadIds.size > 0 && selectedLeadIds.size >= filteredLeads.length) {
      setSelectedLeadIds(new Set());
    } else {
      const allIds = new Set(filteredLeads.map(l => l.id).filter(Boolean));
      setSelectedLeadIds(allIds);
    }
  };

  const handleBulkPreAssessmentClick = async () => {
    // Case 1: No clients selected -> redirect directly to existing Bulk Assessment page
    if (selectedLeadIds.size === 0) {
      toast.info('Redirecting to Bulk Pre-Assessment page...');
      navigate('/sales/bulk-assessment');
      return;
    }

    // Case 2: Clients selected -> validate resume attachment before adding to Bulk Assessment
    const selected = leads.filter(l => selectedLeadIds.has(l.id) || selectedLeadIds.has(l.unique_id));
    const eligible = selected.filter(isLeadResumeAttached);
    const ineligible = selected.filter(l => !isLeadResumeAttached(l));

    if (eligible.length === 0) {
      toast.error("None of the selected clients have an attached resume. A resume is required to proceed with Bulk Pre-Assessment.");
      return;
    }

    if (ineligible.length > 0) {
      toast.warning(`Skipped ${ineligible.length} client(s) without attached resume (${ineligible.map(l => l.name || 'Client').slice(0, 3).join(', ')}${ineligible.length > 3 ? '...' : ''}). Proceeding with ${eligible.length} eligible client(s).`);
    }

    setIsCreatingBulkBatch(true);
    const toastId = toast.loading(`Creating Bulk Pre-Assessment batch for ${eligible.length} client(s)...`);
    try {
      const payload = {
        lead_ids: eligible.map(l => l.id),
        batch_name: `CRM Selected Leads (${new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })})`,
      };
      const res = await axios.post(`${API}/bulk-assessments/from-leads`, payload, getAuthHeader());
      toast.success(`Bulk Pre-Assessment batch created with ${res.data.total || eligible.length} client(s)! Redirecting...`, { id: toastId });
      setSelectedLeadIds(new Set());
      navigate(`/sales/bulk-assessment?batch_id=${res.data.batch_id}`);
    } catch (err) {
      console.error('Error creating bulk pre-assessment batch:', err);
      toast.error(err.response?.data?.detail || 'Failed to create Bulk Pre-Assessment batch', { id: toastId });
    } finally {
      setIsCreatingBulkBatch(false);
    }
  };

  // Real-time resume check and drawer polling
  const [checkingResumeStatusId, setCheckingResumeStatusId] = useState(null);

  const handleCheckResumeStatus = async (lead) => {
    if (!lead?.id) return;
    setCheckingResumeStatusId(lead.id);
    try {
      const res = await axios.get(`${API}/crm/leads/${lead.id}/resume-status`, getAuthHeader());
      if (res.data?.has_resume) {
        const updated = res.data;
        const patch = {
          resume_file_id: updated.resume_file_id,
          resume_filename: updated.resume_filename,
          resume_url: updated.resume_url,
          resume_uploaded: true,
          has_resume: true,
        };
        setSelectedLead(prev => (prev && (prev.id === lead.id || prev.lead_number === lead.lead_number)) ? { ...prev, ...patch } : prev);
        setLeads(prev => prev.map(l => (l.id === lead.id || l.lead_number === lead.lead_number) ? { ...l, ...patch } : l));
        toast.success(`Resume attached: ${updated.resume_filename || 'Candidate Resume'}`);
      } else {
        toast.info("No resume uploaded yet by the client. You can send an upload link via Email & WhatsApp.");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to check resume status");
    } finally {
      setCheckingResumeStatusId(null);
    }
  };

  // Auto-poll resume status every 4 seconds when lead drawer is open and lead doesn't have resume attached yet
  useEffect(() => {
    const leadId = selectedLead?.id;
    if (!leadId) return;
    if (selectedLead.resume_file_id || selectedLead.resume_url) return;

    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/crm/leads/${leadId}/resume-status`, getAuthHeader());
        if (isMounted && res.data?.has_resume) {
          const updated = res.data;
          const patch = {
            resume_file_id: updated.resume_file_id,
            resume_filename: updated.resume_filename,
            resume_url: updated.resume_url,
            resume_uploaded: true,
            has_resume: true,
          };
          setSelectedLead(prev => (prev && (prev.id === leadId || prev.lead_number === selectedLead.lead_number)) ? { ...prev, ...patch } : prev);
          setLeads(prev => prev.map(l => (l.id === leadId || l.lead_number === selectedLead.lead_number) ? { ...l, ...patch } : l));
          toast.success(`Resume uploaded by client: ${updated.resume_filename || 'Candidate Resume'}`, { id: `resume-poll-${leadId}` });
        }
      } catch (_) {}
    }, 4000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [selectedLead?.id, selectedLead?.resume_file_id, selectedLead?.resume_url]);

  // In-App Calling & Live Recording State
  const [showCallModal, setShowCallModal] = useState(false);
  const [callLead, setCallLead] = useState(null);
  const [leadCalls, setLeadCalls] = useState([]);
  const [leadCallsLoading, setLeadCallsLoading] = useState(false);
  const [showCallQR, setShowCallQR] = useState(false);
  const [callState, setCallState] = useState('idle'); // 'idle' | 'dialing' | 'ringing' | 'connected' | 'saving'
  const [callDirection, setCallDirection] = useState('outgoing'); // 'outgoing' | 'incoming'
  const [callDuration, setCallDuration] = useState(0);
  const [callMuted, setCallMuted] = useState(false);
  const [callNotes, setCallNotes] = useState('');
  const [callOutcome, setCallOutcome] = useState('interested');
  const [showIncomingPrompt, setShowIncomingPrompt] = useState(false);
  const [timelineFilter, setTimelineFilter] = useState('all'); // all, call, whatsapp, email, follow_up, meeting, payment, stage_change
  
  // PC Live Audio Recording States
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [uploadingRecording, setUploadingRecording] = useState(false);

  const callTimerRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioStreamRef = useRef(null);
  const conversationPaneRef = useRef(null);

  const [callData, setCallData] = useState({ duration_seconds: 120, status: 'connected', outcome: 'follow_up_required', notes: '' });
  const [showWhatsAppModal, setShowWhatsAppModal] = useState(false);
  const [viewingWaMessage, setViewingWaMessage] = useState(null);
  const [waMessage, setWaMessage] = useState('');
  const [selectedWaTemplate, setSelectedWaTemplate] = useState('');
  const [leadWhatsApp, setLeadWhatsApp] = useState([]);
  const [leadWhatsAppLoading, setLeadWhatsAppLoading] = useState(false);
  const [waComposerText, setWaComposerText] = useState('');
  const [waSending, setWaSending] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailData, setEmailData] = useState({ subject: '', body_html: '' });
  const [emailTemplates, setEmailTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailServiceStatus, setEmailServiceStatus] = useState(null);
  const [recipientEmail, setRecipientEmail] = useState('');
  const [simulatingReply, setSimulatingReply] = useState(false);
  const [leadEmails, setLeadEmails] = useState([]);
  const [emailsLoading, setEmailsLoading] = useState(false);
  const [emailSortOrder, setEmailSortOrder] = useState('desc');
  const [syncingMailbox, setSyncingMailbox] = useState(false);
  const [quickReplyText, setQuickReplyText] = useState('');
  const [sendingQuickReply, setSendingQuickReply] = useState(false);
  const [emailNotifyByEmail, setEmailNotifyByEmail] = useState(false);
  const [emailCc, setEmailCc] = useState('');
  const [showCcField, setShowCcField] = useState(false);
  const [quickReplyNotifyByEmail, setQuickReplyNotifyByEmail] = useState(false);
  const [showMailboxModal, setShowMailboxModal] = useState(false);
  const [emailSettingsTab, setEmailSettingsTab] = useState('signature');
  const [signatureHtml, setSignatureHtml] = useState('');
  const [isCustomSig, setIsCustomSig] = useState(false);
  const [loadingSig, setLoadingSig] = useState(false);
  const [savingSig, setSavingSig] = useState(false);

  // AI Sales Communication Assistant States
  const [aiWaLoading, setAiWaLoading] = useState(false);
  const [aiWaSuggestion, setAiWaSuggestion] = useState('');
  const [aiWaTalkingPoints, setAiWaTalkingPoints] = useState([]);
  const [aiWaMatchedProduct, setAiWaMatchedProduct] = useState(null);
  const [showAiWaPanel, setShowAiWaPanel] = useState(false);
  const [aiWaCustomPrompt, setAiWaCustomPrompt] = useState('');

  // Live Call Copilot States
  const [aiCallLoading, setAiCallLoading] = useState(false);
  const [aiCallQuery, setAiCallQuery] = useState('');
  const [aiCallSpeakingScript, setAiCallSpeakingScript] = useState('');
  const [aiCallTalkingPoints, setAiCallTalkingPoints] = useState([]);
  const [showCallCopilot, setShowCallCopilot] = useState(true);

  const [mailboxForm, setMailboxForm] = useState({
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_user: '',
    smtp_pass: '',
    sender_name: '',
    sender_email: '',
  });
  const [testingMailbox, setTestingMailbox] = useState(false);
  const [savingMailbox, setSavingMailbox] = useState(false);
  const [mailboxTestResult, setMailboxTestResult] = useState(null);
  const [showFollowUpModal, setShowFollowUpModal] = useState(false);
  const [followUpData, setFollowUpData] = useState({ type: 'Call', priority: 'medium', scheduled_at: '', notes: '', reminder_before: '30_mins' });
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [taskData, setTaskData] = useState({ title: '', priority: 'medium', due_date: '', description: '' });
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [meetingData, setMeetingData] = useState({ title: 'Consultation Meeting', meeting_type: 'Google Meet', meeting_date: '', meeting_time: '11:00', meeting_link: 'https://meet.google.com/new', notes: '' });

  // Meeting Reschedule & Recap States
  const [showRescheduleModal, setShowRescheduleModal] = useState(false);
  const [rescheduleMeeting, setRescheduleMeeting] = useState(null);
  const [rescheduleForm, setRescheduleForm] = useState({
    meeting_date: '',
    meeting_time: '11:00',
    duration_minutes: 30,
    reason: '',
    notes: '',
    notify_client: true,
  });
  const [rescheduleSubmitting, setRescheduleSubmitting] = useState(false);

  const [showRecapModal, setShowRecapModal] = useState(false);
  const [recapMeeting, setRecapMeeting] = useState(null);
  const [recapForm, setRecapForm] = useState({
    summary: '',
    transcripts: '',
    recording_url: '',
    action_items_text: '',
    participants_text: '',
  });
  const [recapSubmitting, setRecapSubmitting] = useState(false);
  const [syncingRecapId, setSyncingRecapId] = useState(null);
  const [expandedRecapId, setExpandedRecapId] = useState(null);
  const [expandedHistoryId, setExpandedHistoryId] = useState(null);

  const [showDealModal, setShowDealModal] = useState(false);
  const [dealData, setDealData] = useState({ deal_name: '', service: 'Canada PR Express Entry', country: 'Canada', deal_value: 75000, discount: 0, priority: 'high', stage: 'proposal' });
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentData, setPaymentData] = useState({ package_name: 'Standard Visa Processing', package_price: 75000, discount: 5000, paid_amount: 35000, payment_method: 'Bank Transfer', notes: '' });
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [convertData, setConvertData] = useState({ package_price: 75000, discount: 0, paid_amount: 35000 });
  const [showHandoverModal, setShowHandoverModal] = useState(false);
  const [handoverData, setHandoverData] = useState({ case_manager_id: '', notes: 'Client consultation completed. Ready for document filing.', package_details: 'Standard Visa Package' });

  // Bulk Import & Duplicates (Admin Only)
  const [showImportModal, setShowImportModal] = useState(false);
  const [importMode, setImportMode] = useState('file'); // 'file' or 'paste'
  const [importFile, setImportFile] = useState(null);
  const [importCsvText, setImportCsvText] = useState('');
  const [importAssignmentMethod, setImportAssignmentMethod] = useState('specific'); // 'specific', 'round_robin', 'from_file', 'unassigned', 'row_ranges'
  const [importSalesPersonId, setImportSalesPersonId] = useState('');
  const [importUploading, setImportUploading] = useState(false);
  const [importResults, setImportResults] = useState(null);
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);
  const [duplicateMatches, setDuplicateMatches] = useState([]);

  // Row Range & Auto Split states
  const [filePreviewStats, setFilePreviewStats] = useState({ total_rows: 0, headers: [], filename: '' });
  const [previewLoading, setPreviewLoading] = useState(false);
  const [rowRanges, setRowRanges] = useState([
    { id: 'rng_1', from_row: 1, to_row: 100, sales_person_id: '' }
  ]);
  const [splitToolTab, setSplitToolTab] = useState('equal'); // 'equal' | 'batch'
  const [splitSelectedReps, setSplitSelectedReps] = useState([]);
  const [splitBatchSize, setSplitBatchSize] = useState(50);
  const [showSplitPanel, setShowSplitPanel] = useState(false);

  // WhatsApp Inbox & Meta Cloud API Live State
  const [waInboxTab, setWaInboxTab] = useState('all');
  const [waThreads, setWaThreads] = useState([]);
  const [activeWaThread, setActiveWaThread] = useState(null);
  const [activeWaMessages, setActiveWaMessages] = useState([]);
  const [waReplyText, setWaReplyText] = useState('');
  const [showWhatsAppConfigModal, setShowWhatsAppConfigModal] = useState(false);
  const [whatsappSessionStatus, setWhatsappSessionStatus] = useState(null);
  const [waUploadingMedia, setWaUploadingMedia] = useState(false);
  const [waAttachedMedia, setWaAttachedMedia] = useState(null);
  const waFileInputRef = useRef(null);

  // Client Notes & Remarks state
  const [clientNoteType, setClientNoteType] = useState('Other Remarks');
  const [clientNoteText, setClientNoteText] = useState('');
  const [isSavingNote, setIsSavingNote] = useState(false);

  const playWhatsAppChime = useCallback(() => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.setValueAtTime(880, ctx.currentTime + 0.1); // A5
      gain.gain.setValueAtTime(0.12, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } catch (e) {
      // AudioContext autoplay restriction fallback
    }
  }, []);

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });

  // Initial user load
  useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        setCurrentUser(JSON.parse(userStr));
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  const loadWhatsAppTemplates = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/whatsapp-templates`, getAuthHeader());
      if (res.data?.templates) setWaTemplates(res.data.templates);
    } catch (e) {
      console.error('Failed to load WhatsApp templates', e);
    }
  }, []);

  const fetchAllCRMData = useCallback(async () => {
    setLoading(true);
    try {
      const [leadsRes, statsRes, actionsRes, dealsRes, followUpsRes, callsRes, paymentsRes, campsRes, perfRes, autoRes, emailsRes, meetingsRes, waRes, webLeadsOverviewRes] = await Promise.all([
        axios.get(`${API}/leads/?limit=2000`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/leads/pipeline-stats`, getAuthHeader()).catch(() => ({ data: {} })),
        axios.get(`${API}/crm/actions-waiting`, getAuthHeader()).catch(() => ({ data: {} })),
        axios.get(`${API}/crm/deals`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/follow-ups`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/calls`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/payments`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/campaigns`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/reports/performance`, getAuthHeader()).catch(() => ({ data: null })),
        axios.get(`${API}/crm/automation/rules`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/emails?limit=250&sort=desc`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/meetings?limit=200`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/whatsapp-templates`, getAuthHeader()).catch(() => ({ data: { templates: [] } })),
        isAdmin ? axios.get(`${API}/crm/website-leads/overview`, getAuthHeader()).catch(() => ({ data: {} })) : Promise.resolve({ data: {} }),
      ]);

      const freshLeads = leadsRes.data || [];
      setLeads(freshLeads);
      setSelectedLead(currentSelected => {
        if (!currentSelected) return null;
        const fresh = freshLeads.find(l => l.id === currentSelected.id || l._id === currentSelected.id || l.lead_number === currentSelected.lead_number);
        return fresh ? { ...currentSelected, ...fresh } : currentSelected;
      });
      setStats(statsRes.data || {});
      setActionsWaiting(actionsRes.data || {});
      setDeals(dealsRes.data || []);
      setFollowUps(followUpsRes.data || []);
      setCalls(callsRes.data || []);
      setPayments(paymentsRes.data || []);
      setCampaigns(campsRes.data || []);
      setPerformance(perfRes.data);
      setAutomationRules(autoRes.data || []);
      setAllEmails(emailsRes.data || []);
      setMeetings(meetingsRes.data || []);
      setWaTemplates(waRes.data?.templates || []);
      if (webLeadsOverviewRes.data) {
        setWebsiteLeadsCount(webLeadsOverviewRes.data.total_website_leads || 0);
        setWebsiteLeadsUnassignedCount(webLeadsOverviewRes.data.unassigned_count || 0);
        if (webLeadsOverviewRes.data.categories) {
          setWebsiteCategoriesData(webLeadsOverviewRes.data.categories);
        }
      }

      // Fetch users for assignment/handover
      const usersRes = await axios.get(`${API}/users/`, getAuthHeader()).catch(() => ({ data: [] }));
      if (Array.isArray(usersRes.data)) {
        setCaseManagers(usersRes.data.filter(u => u.role === 'case_manager' || u.rbac_role === 'case_manager'));
        setSalesReps(usersRes.data.filter(u => {
          const r = (u.role || '').toLowerCase();
          const rbac = (u.rbac_role || '').toLowerCase();
          const salesRoles = ['partner', 'sales_executive', 'sr_sales_executive', 'sales_manager', 'sales_specialist', 'sales_rep', 'admin', 'admin_owner'];
          return salesRoles.includes(r) || salesRoles.includes(rbac);
        }));
      }
    } catch (err) {
      console.error('Error fetching CRM data:', err);
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    fetchAllCRMData();
    // Background polling every 20s to keep payments and new leads live without manual refresh
    const pollInterval = setInterval(() => {
      axios.get(`${API}/leads/?limit=2000`, getAuthHeader())
        .then(res => {
          if (Array.isArray(res.data)) {
            setLeads(res.data);
          }
        })
        .catch(() => {});
    }, 20000);
    return () => clearInterval(pollInterval);
  }, [fetchAllCRMData]);

  // ── Salesperson Activity Tracking: Leads Board, Client Details & Multi-Tab Sessions ──
  const activeProfileViewRef = useRef(null);
  const lastLoggedViewRef = useRef(null);

  // Helper for timezone-formatted time string (Asia/Kolkata / IST standard)
  const getFormattedLocalTimeStr = useCallback((d = new Date()) => {
    try {
      return d.toLocaleTimeString('en-US', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    } catch {
      return d.toLocaleTimeString();
    }
  }, []);

  // Track Page Visits (specifically recording CRM Leads Board and All Leads Table visits with active client)
  useEffect(() => {
    if (!currentUser) return;
    if (lastLoggedViewRef.current === view) return;
    lastLoggedViewRef.current = view;

    const viewLabels = {
      dashboard: 'Dashboard',
      table: 'All Leads Table',
      kanban: 'Leads Board',
      pipeline: 'Sales Pipeline',
      calls: 'Calls & Telephony',
      whatsapp: 'WhatsApp Inbox',
      emails: 'Email Center',
      followups: 'Follow-ups Due',
      meetings: 'Meetings',
      payments: 'Sales Payments',
      performance: 'Performance Targets',
      website_leads: 'Website Leads',
      salesperson_activity_audit: 'Activity Report & Audit',
    };
    const label = viewLabels[view] || view;
    const isLeadsBoard = view === 'kanban';
    const isAllLeadsTable = view === 'table';
    const currentTimeStr = getFormattedLocalTimeStr();

    const activeLead = selectedLead || activeProfileViewRef.current?.lead;
    const clientName = activeLead ? (activeLead.name || activeLead.full_name) : null;
    const clientId = activeLead ? (activeLead.id || activeLead.unique_id) : null;

    if (!clientName && (isAllLeadsTable || isLeadsBoard)) {
      // For All Leads Table and Leads Board, we only log client-attributed visits
      // Client opening is tracked with full name, start/end time, and duration via handleOpenLeadWorkspace
      return;
    }

    let title = isLeadsBoard ? 'Visited CRM Leads Board' : `Visited CRM ${label}`;
    let details = isLeadsBoard
      ? `Salesperson opened and navigated to CRM Leads Board (Kanban view) at ${currentTimeStr}.`
      : `Navigated to ${label} in CRM at ${currentTimeStr}.`;

    if (clientName) {
      title = `Visited CRM ${isAllLeadsTable ? 'All Leads Table' : isLeadsBoard ? 'Leads Board' : label} • Client: ${clientName}`;
      details = `Salesperson opened ${label} in CRM while working on client ${clientName} at ${currentTimeStr}.`;
    }

    axios.post(`${API}/salesperson-activity/log`, {
      activity_type: 'page_visit',
      title,
      details,
      client_id: clientId,
      client_name: clientName,
      client_phone: activeLead?.phone,
      client_email: activeLead?.email,
      start_time: currentTimeStr,
      metadata: {
        view,
        view_label: label,
        is_leads_board: isLeadsBoard,
        is_all_leads_table: isAllLeadsTable,
        source_tab: isAllLeadsTable ? 'All Leads Table' : isLeadsBoard ? 'Leads Board' : label,
        active_client_name: clientName,
        active_client_id: clientId,
        start_time: currentTimeStr,
        timezone: 'Asia/Kolkata'
      }
    }, getAuthHeader()).catch(() => {});
  }, [view, currentUser, selectedLead, getFormattedLocalTimeStr]);

  // Helper to log completed client session with start time, end time, and dwell duration
  const logActiveClientCompleted = useCallback((reason = 'closed') => {
    if (!activeProfileViewRef.current) return;
    const { lead: prevLead, startMs, startTimeStr, clientName, sourceView } = activeProfileViewRef.current;
    const dwellSeconds = Math.max(1, Math.round((Date.now() - startMs) / 1000));
    const endTimeStr = getFormattedLocalTimeStr();
    const sourceTabName = sourceView === 'kanban' ? 'Leads Board' : 'All Leads Table';

    if (prevLead && dwellSeconds >= 1) {
      const durDisplay = dwellSeconds >= 3600
        ? `${Math.floor(dwellSeconds / 3600)}h ${Math.floor((dwellSeconds % 3600) / 60)}m ${dwellSeconds % 60}s`
        : dwellSeconds >= 60
        ? `${Math.floor(dwellSeconds / 60)}m ${dwellSeconds % 60}s`
        : `${dwellSeconds}s`;

      axios.post(`${API}/salesperson-activity/log`, {
        activity_type: 'client_view',
        client_id: prevLead.id || prevLead.unique_id,
        client_name: clientName,
        client_phone: prevLead.phone,
        client_email: prevLead.email,
        duration_seconds: dwellSeconds,
        start_time: startTimeStr,
        end_time: endTimeStr,
        session_state: 'completed',
        title: `Worked on Client: ${clientName} (${sourceTabName})`,
        details: `Active client session on ${clientName} from ${sourceTabName} • Start: ${startTimeStr} • End: ${endTimeStr} (${durDisplay})`,
        metadata: {
          session_state: 'completed',
          start_time: startTimeStr,
          end_time: endTimeStr,
          duration_seconds: dwellSeconds,
          duration_display: durDisplay,
          source_view: sourceView,
          source_tab: sourceTabName,
          switch_reason: reason,
          timezone: 'Asia/Kolkata'
        }
      }, getAuthHeader()).catch(() => {});
    }
    activeProfileViewRef.current = null;
  }, [getFormattedLocalTimeStr]);

  // Track Client Details Open, Active Viewing, and Session Duration
  useEffect(() => {
    // If a previous client was open and changed, log the previous session's completion
    if (activeProfileViewRef.current) {
      const prevId = activeProfileViewRef.current.lead?.id || activeProfileViewRef.current.lead?.unique_id;
      const currentId = selectedLead?.id || selectedLead?.unique_id;
      if (prevId !== currentId) {
        logActiveClientCompleted('switched_client');
      }
    }

    // When client details are opened, immediately log active viewing start
    if (selectedLead && (selectedLead.id || selectedLead.unique_id)) {
      const clientName = selectedLead.name || selectedLead.full_name || 'Client';
      const startTimeStr = getFormattedLocalTimeStr();
      const startMs = Date.now();
      const sourceTabName = view === 'kanban' ? 'Leads Board' : 'All Leads Table';

      activeProfileViewRef.current = {
        lead: selectedLead,
        startMs,
        startTimeStr,
        clientName,
        sourceView: view
      };

      axios.post(`${API}/salesperson-activity/log`, {
        activity_type: 'client_view',
        client_id: selectedLead.id || selectedLead.unique_id,
        client_name: clientName,
        client_phone: selectedLead.phone,
        client_email: selectedLead.email,
        title: `Opened Client Details: ${clientName} (${sourceTabName})`,
        details: `Salesperson opened and actively viewing details for ${clientName} (Stage: ${selectedLead.stage || selectedLead.status || 'Active'}) from ${sourceTabName} • Started: ${startTimeStr}.`,
        start_time: startTimeStr,
        session_state: 'active',
        metadata: {
          session_state: 'active',
          start_time: startTimeStr,
          source_view: view,
          source_tab: sourceTabName,
          stage: selectedLead.stage || selectedLead.status || 'Active',
          lead_number: selectedLead.lead_number,
          timezone: 'Asia/Kolkata'
        }
      }, getAuthHeader()).catch(() => {});
    }

    return () => {
      // Cleanup on unmount or client change
      logActiveClientCompleted('closed');
    };
  }, [selectedLead?.id, selectedLead?.unique_id, view, getFormattedLocalTimeStr, logActiveClientCompleted]);

  // Track active client tab when salesperson switches between multiple browser tabs or windows
  useEffect(() => {
    const handleVisibilityOrFocusChange = () => {
      if (document.hidden) {
        // Tab switched away: pause/log completion of active session on current client
        if (activeProfileViewRef.current) {
          logActiveClientCompleted('tab_switched_away');
        }
      } else {
        // Tab gained focus / became active: if client details are open, resume active session
        if (selectedLead && (selectedLead.id || selectedLead.unique_id) && !activeProfileViewRef.current) {
          const clientName = selectedLead.name || selectedLead.full_name || 'Client';
          const startTimeStr = getFormattedLocalTimeStr();

          activeProfileViewRef.current = {
            lead: selectedLead,
            startMs: Date.now(),
            startTimeStr,
            clientName,
            sourceView: view
          };

          axios.post(`${API}/salesperson-activity/log`, {
            activity_type: 'client_view',
            client_id: selectedLead.id || selectedLead.unique_id,
            client_name: clientName,
            client_phone: selectedLead.phone,
            client_email: selectedLead.email,
            title: `Active Client Tab: ${clientName}`,
            details: `Salesperson switched focus to active client tab for ${clientName} • Started: ${startTimeStr}.`,
            start_time: startTimeStr,
            session_state: 'active',
            metadata: {
              session_state: 'active',
              start_time: startTimeStr,
              source_view: view,
              switch_type: 'tab_focus',
              timezone: 'Asia/Kolkata'
            }
          }, getAuthHeader()).catch(() => {});
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityOrFocusChange);
    window.addEventListener('blur', () => {
      if (activeProfileViewRef.current) {
        logActiveClientCompleted('window_blur');
      }
    });

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityOrFocusChange);
    };
  }, [selectedLead, view, getFormattedLocalTimeStr, logActiveClientCompleted]);

  const loadAllEmails = useCallback(async () => {
    setAllEmailsLoading(true);
    try {
      const res = await axios.get(`${API}/crm/emails?limit=250&sort=desc`, getAuthHeader());
      setAllEmails(res.data || []);
    } catch (e) {
      console.error('Error loading CRM emails', e);
    } finally {
      setAllEmailsLoading(false);
    }
  }, []);

  const loadAllCalls = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/crm/calls?limit=200`, getAuthHeader());
      setCalls(res.data || []);
    } catch (e) {
      console.error('Error loading calls', e);
    }
  }, []);

  // Meetings loader and handlers
  const [meetingsLoading, setMeetingsLoading] = useState(false);
  const [meetingFilter, setMeetingFilter] = useState('all'); // all, upcoming, today, past, google_meet, zoom
  const [meetingSearch, setMeetingSearch] = useState('');

  const loadMeetings = useCallback(async () => {
    setMeetingsLoading(true);
    try {
      const res = await axios.get(`${API}/crm/meetings?limit=200`, getAuthHeader());
      setMeetings(res.data || []);
    } catch (e) {
      console.error('Error loading meetings', e);
    } finally {
      setMeetingsLoading(false);
    }
  }, []);

  const handleUpdateMeetingStatus = async (meetingId, newStatus) => {
    try {
      await axios.put(`${API}/crm/meetings/${meetingId}/status`, { status: newStatus }, getAuthHeader());
      toast.success(`Meeting marked as ${newStatus}`);
      loadMeetings();
      if (selectedLead?.id) {
        loadLeadTimeline(selectedLead.id);
      }
    } catch (e) {
      console.error(e);
      toast.error('Failed to update meeting status');
    }
  };

  const handleDeleteMeeting = async (meetingId) => {
    if (!window.confirm('Are you sure you want to cancel this meeting?')) return;
    try {
      await axios.delete(`${API}/crm/meetings/${meetingId}`, getAuthHeader());
      toast.success('Meeting cancelled and removed');
      loadMeetings();
      if (selectedLead?.id) {
        loadLeadTimeline(selectedLead.id);
      }
    } catch (e) {
      console.error(e);
      toast.error('Failed to cancel meeting');
    }
  };

  // Editing existing meeting link
  const [editingMeeting, setEditingMeeting] = useState(null); // { id, title, currentLink, platform, contact_name }
  const [editMeetingNewLink, setEditMeetingNewLink] = useState('');
  const [editMeetingSaveDefault, setEditMeetingSaveDefault] = useState(false);
  const [savingMeetingLink, setSavingMeetingLink] = useState(false);

  const handleOpenEditMeetingLink = (meetingId, currentLink, meetingTitle, extra = {}) => {
    setEditingMeeting({
      id: meetingId,
      currentLink: currentLink || '',
      title: meetingTitle || 'Consultation Meeting',
      platform: extra?.meeting_type || 'Google Meet',
      contact_name: extra?.contact_name || ''
    });
    setEditMeetingNewLink(currentLink || '');
    setEditMeetingSaveDefault(false);
  };

  const handleSaveUpdatedMeetingLink = async () => {
    if (!editingMeeting?.id) return;
    const trimmed = (editMeetingNewLink || '').trim();
    if (!trimmed) {
      toast.error('Please enter a valid meeting link.');
      return;
    }
    if (trimmed === 'https://meet.google.com/new' || trimmed === 'meet.google.com/new') {
      toast.error('Please launch meet.google.com/new, create your room, and copy the room code (e.g. meet.google.com/xxx-yyyy-zzz).');
      return;
    }
    if (trimmed === 'https://zoom.us/start/videomeeting' || trimmed === 'zoom.us/start/videomeeting') {
      toast.error('Please launch Zoom, start/schedule your meeting, and copy your actual room link (e.g. https://us05web.zoom.us/j/... or personal link).');
      return;
    }

    setSavingMeetingLink(true);
    try {
      await axios.put(
        `${API}/crm/meetings/${editingMeeting.id}`,
        { meeting_link: trimmed },
        getAuthHeader()
      );

      if (editMeetingSaveDefault) {
        if (trimmed.includes('zoom.us')) {
          localStorage.setItem('zoom_pmi_link', trimmed);
          axios.post(
            `${API}/crm/meetings/config`,
            { zoom_pmi_link: trimmed },
            getAuthHeader()
          ).catch(() => {});
        } else if (trimmed.includes('calendly.com') || String(editingMeeting.platform || '').toLowerCase().includes('calendly')) {
          localStorage.setItem('default_calendly_link', trimmed);
          axios.post(
            `${API}/crm/meetings/config`,
            { default_calendly_link: trimmed },
            getAuthHeader()
          ).catch(() => {});
        } else if (trimmed.includes('meet.google.com')) {
          localStorage.setItem('default_google_meet_link', trimmed);
          axios.post(
            `${API}/crm/meetings/config`,
            { default_google_meet_link: trimmed },
            getAuthHeader()
          ).catch(() => {});
        }
      }

      toast.success('Meeting link updated successfully! You can now join or share the real room.');
      setEditingMeeting(null);
      loadMeetings();
      if (selectedLead?.id) {
        loadLeadTimeline(selectedLead.id);
      }
    } catch (e) {
      console.error(e);
      toast.error(e.response?.data?.detail || 'Failed to update meeting link');
    } finally {
      setSavingMeetingLink(false);
    }
  };

  const handleOpenRescheduleModal = (meeting) => {
    if (!meeting) return;
    const meetingId = meeting.id || meeting.meeting_id;
    setRescheduleMeeting({
      ...meeting,
      id: meetingId
    });
    setRescheduleForm({
      meeting_date: meeting.meeting_date || '',
      meeting_time: meeting.meeting_time || '11:00',
      duration_minutes: meeting.duration_minutes || 30,
      reason: '',
      notes: '',
      notify_client: true,
    });
    setShowRescheduleModal(true);
  };

  const handleSubmitReschedule = async (e) => {
    if (e) e.preventDefault();
    if (!rescheduleMeeting?.id) return;
    if (!rescheduleForm.meeting_date) {
      toast.error('Please select the new meeting date.');
      return;
    }
    if (!rescheduleForm.meeting_time) {
      toast.error('Please enter the new meeting time.');
      return;
    }
    const cleanReason = (rescheduleForm.reason || '').trim();
    if (!cleanReason) {
      toast.error('Reason for rescheduling is strictly mandatory. Please specify why the meeting is being rescheduled.');
      return;
    }

    setRescheduleSubmitting(true);
    try {
      const resp = await axios.post(
        `${API}/crm/meetings/${rescheduleMeeting.id}/reschedule`,
        {
          meeting_date: rescheduleForm.meeting_date,
          meeting_time: rescheduleForm.meeting_time,
          duration_minutes: Number(rescheduleForm.duration_minutes) || 30,
          reason: cleanReason,
          notes: (rescheduleForm.notes || '').trim(),
          notify_client: rescheduleForm.notify_client
        },
        getAuthHeader()
      );

      const msg = resp.data?.email_dispatched
        ? 'Meeting rescheduled successfully! Updated invitation email sent to client.'
        : 'Meeting rescheduled successfully!';
      toast.success(msg);
      setShowRescheduleModal(false);
      setRescheduleMeeting(null);
      loadMeetings();
      loadLeads();
      if (selectedLead?.id) {
        loadLeadTimeline(selectedLead.id);
        const updatedLeadResp = await axios.get(`${API}/leads/${selectedLead.id}`, getAuthHeader()).catch(() => null);
        if (updatedLeadResp?.data) {
          setSelectedLead(updatedLeadResp.data);
        }
      }
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || 'Failed to reschedule meeting');
    } finally {
      setRescheduleSubmitting(false);
    }
  };

  const handleOpenRecapModal = (meeting) => {
    if (!meeting) return;
    const meetingId = meeting.id || meeting.meeting_id;
    setRecapMeeting({
      ...meeting,
      id: meetingId
    });
    const r = meeting.recap || {};
    setRecapForm({
      summary: r.summary || '',
      transcripts: r.transcripts || '',
      recording_url: r.recording_url || '',
      action_items_text: Array.isArray(r.action_items) ? r.action_items.join('\n') : '',
      participants_text: Array.isArray(r.participants) ? r.participants.join(', ') : (meeting.contact_name ? `${meeting.contact_name}, ${meeting.sales_person_name || 'Consultant'}` : '')
    });
    setShowRecapModal(true);
  };

  const handleSubmitRecap = async (e) => {
    if (e) e.preventDefault();
    if (!recapMeeting?.id) return;
    setRecapSubmitting(true);
    try {
      const actionItems = recapForm.action_items_text
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean);
      const participants = recapForm.participants_text
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

      await axios.post(
        `${API}/crm/meetings/${recapMeeting.id}/recap`,
        {
          summary: (recapForm.summary || '').trim(),
          transcripts: (recapForm.transcripts || '').trim(),
          recording_url: (recapForm.recording_url || '').trim(),
          action_items: actionItems,
          participants: participants
        },
        getAuthHeader()
      );

      toast.success('Meeting recap, transcript & recording saved successfully!');
      setShowRecapModal(false);
      setRecapMeeting(null);
      loadMeetings();
      if (selectedLead?.id) {
        loadLeadTimeline(selectedLead.id);
      }
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || 'Failed to save meeting recap');
    } finally {
      setRecapSubmitting(false);
    }
  };

  const handleSyncRecap = async (meetingId) => {
    if (!meetingId) return;
    setSyncingRecapId(meetingId);
    try {
      const resp = await axios.post(
        `${API}/crm/meetings/${meetingId}/sync-recap`,
        {},
        getAuthHeader()
      );
      toast.success(resp.data?.message || 'Recap synchronized!');
      loadMeetings();
      if (selectedLead?.id) {
        loadLeadTimeline(selectedLead.id);
      }
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || 'Failed to sync recap from Calendly');
    } finally {
      setSyncingRecapId(null);
    }
  };

  useEffect(() => {
    if (view === 'emails' || view === 'email') {
      loadAllEmails();
    } else if (view === 'calls') {
      loadAllCalls();
    } else if (view === 'meetings') {
      loadMeetings();
    }
  }, [view, loadAllEmails, loadAllCalls, loadMeetings]);

  // Load Lead Timeline when Lead workspace opened
  const loadLeadTimeline = async (leadId) => {
    if (!leadId) return;
    setTimelineLoading(true);
    try {
      const res = await axios.get(`${API}/crm/timeline/lead/${leadId}`, getAuthHeader());
      setLeadTimeline(res.data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setTimelineLoading(false);
    }
  };

  // Load Lead Calls when Lead workspace opened
  const loadLeadCalls = async (leadId) => {
    if (!leadId) return;
    setLeadCallsLoading(true);
    try {
      const res = await axios.get(`${API}/crm/calls?lead_id=${leadId}&limit=100`, getAuthHeader());
      setLeadCalls(res.data || []);
    } catch (e) {
      console.error('Error loading lead calls', e);
    } finally {
      setLeadCallsLoading(false);
    }
  };

  // Load Lead WhatsApp Messages & Session Status
  const loadWhatsAppSessionStatus = async (leadId) => {
    if (!leadId) return;
    try {
      const res = await axios.get(`${API}/crm/whatsapp/session-status/${leadId}`, getAuthHeader());
      setWhatsappSessionStatus(res.data);
    } catch (e) {
      console.error('Error loading WhatsApp session status', e);
    }
  };

  const loadLeadWhatsApp = async (leadId, silent = false) => {
    if (!leadId) return;
    if (!silent) setLeadWhatsAppLoading(true);
    try {
      const res = await axios.get(`${API}/crm/whatsapp/thread/${leadId}`, getAuthHeader());
      const newMessages = res.data || [];
      setLeadWhatsApp(prev => {
        if (silent && prev.length > 0 && newMessages.length > prev.length) {
          const newest = newMessages[newMessages.length - 1];
          if (newest && newest.direction === 'inbound') {
            playWhatsAppChime();
            toast.info(`New WhatsApp from ${newest.contact_name || 'Client'}: "${(newest.text || '').substring(0, 45)}..."`);
          }
        }
        return newMessages;
      });
    } catch (e) {
      console.error('Error loading lead WhatsApp messages', e);
    } finally {
      if (!silent) setLeadWhatsAppLoading(false);
    }
  };

  // Load notes specifically for a lead to ensure fresh notes are displayed
  const loadLeadNotes = async (leadId) => {
    if (!leadId) return;
    try {
      const res = await axios.get(`${API}/leads/${leadId}/notes`, getAuthHeader());
      if (res.data?.notes) {
        setSelectedLead(prev => (prev && (prev.id === leadId || prev.unique_id === leadId)) ? { ...prev, notes: res.data.notes } : prev);
      }
    } catch (e) {
      // silently ignore if lead has no notes or endpoint error
    }
  };

  // Add a categorized note or remark to the client's permanent record
  const handleAddClientNote = async () => {
    if (!selectedLead || !selectedLead.id) return;
    const trimmed = (clientNoteText || '').trim();
    if (!trimmed) {
      toast.error('Please enter a note or remark description');
      return;
    }
    setIsSavingNote(true);
    try {
      const res = await axios.post(
        `${API}/leads/${selectedLead.id}/note`,
        {
          note_type: clientNoteType,
          text: trimmed,
          description: trimmed
        },
        getAuthHeader()
      );
      toast.success(`Remark (${clientNoteType}) saved successfully!`);
      setClientNoteText('');

      const updatedNotes = res.data?.notes || (
        res.data?.note
          ? [res.data.note, ...(selectedLead.notes || [])]
          : selectedLead.notes || []
      );
      setSelectedLead(prev => ({
        ...prev,
        notes: updatedNotes
      }));

      // Update in global leads list so notes persist across selections
      setLeads(prev => prev.map(l => (l.id === selectedLead.id || l.unique_id === selectedLead.id) ? { ...l, notes: updatedNotes } : l));

      // Reload unified timeline so remark immediately appears in Complete History
      loadLeadTimeline(selectedLead.id);
    } catch (err) {
      console.error('Failed to add client note:', err);
      toast.error(err.response?.data?.detail || 'Failed to save note');
    } finally {
      setIsSavingNote(false);
    }
  };

  // Handle Stage -> More actions (Drop a Message, Drop a Mail)
  const handleStageMoreAction = (actionType) => {
    if (!selectedLead) return;
    if (actionType === 'message') {
      setClientNoteType('Dropped a Message');
      setWorkspaceTab('overview');
      toast.info('Selected "Dropped a Message" — enter your note below or click Open WhatsApp');
      setTimeout(() => {
        const el = document.getElementById('client-notes-remarks-section');
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const textarea = document.getElementById('client-remark-textarea');
        if (textarea) textarea.focus();
      }, 150);
    } else if (actionType === 'mail') {
      setClientNoteType('Dropped a Mail');
      setWorkspaceTab('overview');
      handleOpenEmailModal('', '', null, selectedLead);
    }
  };

  const handleOpenLeadWorkspace = (lead, tab = 'overview') => {
    if (!lead) return;
    const clientName = lead.name || lead.full_name || 'Client';
    const currentTimeStr = getFormattedLocalTimeStr();
    const sourceTabName = view === 'kanban' ? 'Leads Board' : 'All Leads Table';

    axios.post(`${API}/salesperson-activity/log`, {
      activity_type: 'client_view',
      client_id: lead.id || lead.unique_id,
      client_name: clientName,
      client_phone: lead.phone,
      client_email: lead.email,
      title: `Visited CRM ${sourceTabName} • Client: ${clientName}`,
      details: `Salesperson opened and working on client ${clientName} (Lead #${lead.lead_number || '—'}, Stage: ${lead.stage || 'New'}) in ${sourceTabName} at ${currentTimeStr}.`,
      start_time: currentTimeStr,
      session_state: 'active',
      metadata: {
        session_state: 'active',
        start_time: currentTimeStr,
        source_view: view,
        source_tab: sourceTabName,
        stage: lead.stage || lead.status || 'Active',
        lead_number: lead.lead_number,
        timezone: 'Asia/Kolkata'
      }
    }, getAuthHeader()).catch(() => {});

    setSelectedLead(lead);
    setWorkspaceTab(tab);
    loadLeadNotes(lead.id);
    loadLeadTimeline(lead.id);
    loadLeadEmails(lead.id);
    loadLeadCalls(lead.id);
    loadLeadWhatsApp(lead.id);
    loadWhatsAppSessionStatus(lead.id);
  };


  // WhatsApp Inbox Loader
  const loadWhatsAppInbox = async (silent = false) => {
    try {
      const res = await axios.get(`${API}/crm/whatsapp/inbox?tab=${waInboxTab}`, getAuthHeader());
      setWaThreads(res.data || []);
      if (!silent && res.data && res.data.length > 0 && !activeWaThread) {
        handleSelectWaThread(res.data[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSelectWaThread = async (thread) => {
    setActiveWaThread(thread);
    try {
      const res = await axios.get(`${API}/crm/whatsapp/thread/${thread.thread_id}`, getAuthHeader());
      setActiveWaMessages(res.data || []);
      if (thread.lead_id) {
        loadWhatsAppSessionStatus(thread.lead_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Auto-polling for real-time live incoming WhatsApp messages (4s interval)
  useEffect(() => {
    let interval = null;

    if (workspaceTab === 'whatsapp' && selectedLead?.id) {
      loadWhatsAppSessionStatus(selectedLead.id);
      interval = setInterval(() => {
        loadLeadWhatsApp(selectedLead.id, true);
        loadWhatsAppSessionStatus(selectedLead.id);
      }, 4000);
    } else if (view === 'whatsapp') {
      loadWhatsAppInbox();
      interval = setInterval(async () => {
        loadWhatsAppInbox(true);
        if (activeWaThread?.thread_id) {
          try {
            const res = await axios.get(`${API}/crm/whatsapp/thread/${activeWaThread.thread_id}`, getAuthHeader());
            const newMsgs = res.data || [];
            setActiveWaMessages(prev => {
              if (prev.length > 0 && newMsgs.length > prev.length) {
                const newest = newMsgs[newMsgs.length - 1];
                if (newest && newest.direction === 'inbound') {
                  playWhatsAppChime();
                  toast.info(`New WhatsApp message from ${newest.contact_name || 'Client'}: "${(newest.text || '').substring(0, 45)}..."`);
                }
              }
              return newMsgs;
            });
          } catch (e) {
            // silent polling catch
          }
        }
      }, 4000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, waInboxTab, activeWaThread?.thread_id, workspaceTab, selectedLead?.id]);

  // Real-time background data refresh: Polling for new website leads and CRM pipeline updates
  useEffect(() => {
    const leadsPollingInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/leads/?limit=2000`, getAuthHeader());
        if (res.data && Array.isArray(res.data)) {
          setLeads(prevLeads => {
            if (res.data.length !== prevLeads.length || (res.data[0]?.id !== prevLeads[0]?.id)) {
              if (prevLeads.length > 0 && res.data.length > prevLeads.length) {
                const newest = res.data[0];
                toast.success(`⚡ New lead received: ${newest.name || 'Website Enquiry'} (${newest.lead_number || 'New'})`);
              }
              return res.data;
            }
            return prevLeads;
          });
        }
      } catch (err) {
        // silent fail on network hiccups
      }
    }, 10000); // 10 second real-time polling

    return () => clearInterval(leadsPollingInterval);
  }, []);

  // Outbound Media Attachment Handler
  const handleWaMediaUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 16 * 1024 * 1024) {
      toast.error('File exceeds WhatsApp maximum size of 16MB');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    setWaUploadingMedia(true);
    try {
      const res = await axios.post(`${API}/crm/whatsapp/media/upload`, formData, {
        ...getAuthHeader(),
        headers: {
          ...getAuthHeader().headers,
          'Content-Type': 'multipart/form-data'
        }
      });
      setWaAttachedMedia({
        url: res.data.media_url,
        type: res.data.media_type,
        filename: res.data.filename
      });
      toast.success(`Attached ${res.data.filename} (${res.data.media_type})`);
    } catch (err) {
      console.error('Media upload error:', err);
      toast.error('Failed to upload media attachment');
    } finally {
      setWaUploadingMedia(false);
      if (waFileInputRef.current) waFileInputRef.current.value = '';
    }
  };

  const scopedCalls = useMemo(() => {
    if (isAdmin) return calls || [];
    const assignedLeadIds = new Set((leads || []).map(l => l.id).filter(Boolean));
    const myId = String(currentUser?.id || '').trim();
    return (calls || []).filter(c => {
      if (c.lead_id && assignedLeadIds.has(c.lead_id)) return true;
      if (myId && c.sales_person_id === myId) return true;
      return false;
    });
  }, [calls, leads, isAdmin, currentUser]);

  // Filtered Calls with RBAC, Salesperson, Date, and Deep Search
  const filteredCalls = useMemo(() => {
    return scopedCalls.filter(c => {
      if (callFilterOutcome !== 'all' && c.outcome !== callFilterOutcome) return false;
      if (callFilterDirection !== 'all' && c.direction !== callFilterDirection) return false;
      if (callFilterSalesperson !== 'all' && c.sales_person_id !== callFilterSalesperson) return false;

      // Date filtering
      if (callDateFrom || callDateTo) {
        if (!c.created_at) return false;
        try {
          const callTime = new Date(c.created_at).getTime();
          if (callDateFrom) {
            const fromTime = new Date(callDateFrom).setHours(0, 0, 0, 0);
            if (callTime < fromTime) return false;
          }
          if (callDateTo) {
            const toTime = new Date(callDateTo).setHours(23, 59, 59, 999);
            if (callTime > toTime) return false;
          }
        } catch (e) {}
      }

      // Comprehensive search: client name, phone, consultant, notes, transcript, AI summary
      if (callSearch && callSearch.trim()) {
        const q = callSearch.toLowerCase().trim();
        const nameMatch = (c.lead_name || c.client_name || '').toLowerCase().includes(q);
        const phoneMatch = (c.lead_phone || c.client_phone || '').includes(q);
        const notesMatch = (c.notes || '').toLowerCase().includes(q);
        const agentMatch = (c.sales_person_name || '').toLowerCase().includes(q);
        const transcriptMatch = (c.transcript || '').toLowerCase().includes(q);
        const aiSummaryMatch = (c.ai_summary || '').toLowerCase().includes(q);
        const discMatch = (c.ai_summary_structured?.main_discussion || '').toLowerCase().includes(q);
        const reqMatch = (c.ai_summary_structured?.client_requirements || '').toLowerCase().includes(q);
        const concMatch = (c.ai_summary_structured?.concerns || '').toLowerCase().includes(q);
        const stepMatch = (c.ai_summary_structured?.next_steps || '').toLowerCase().includes(q);
        return nameMatch || phoneMatch || notesMatch || agentMatch || transcriptMatch || aiSummaryMatch || discMatch || reqMatch || concMatch || stepMatch;
      }
      return true;
    });
  }, [scopedCalls, callFilterOutcome, callFilterDirection, callFilterSalesperson, callDateFrom, callDateTo, callSearch]);

  const scopedEmails = useMemo(() => {
    if (isAdmin) return allEmails || [];
    const assignedLeadIds = new Set((leads || []).map(l => l.id).filter(Boolean));
    const assignedEmails = new Set((leads || []).map(l => (l.email || '').trim().toLowerCase()).filter(Boolean));
    return (allEmails || []).filter(e => {
      if (e.lead_id && assignedLeadIds.has(e.lead_id)) return true;
      const to = (e.to_email || '').trim().toLowerCase();
      const from = (e.from_email || '').trim().toLowerCase();
      return assignedEmails.has(to) || assignedEmails.has(from);
    });
  }, [allEmails, leads, isAdmin]);

  const displayedAllEmails = useMemo(() => {
    return scopedEmails.filter(e => {
      if (emailFilterDirection !== 'all' && e.direction !== emailFilterDirection) return false;
      if (emailCenterSearch) {
        const q = emailCenterSearch.toLowerCase();
        const contactMatch = (e.contact_name || '').toLowerCase().includes(q);
        const toMatch = (e.to_email || '').toLowerCase().includes(q);
        const fromMatch = (e.from_email || '').toLowerCase().includes(q);
        const subjMatch = (e.subject || '').toLowerCase().includes(q);
        const bodyMatch = (e.raw_text || '').toLowerCase().includes(q);
        return contactMatch || toMatch || fromMatch || subjMatch || bodyMatch;
      }
      return true;
    }).sort((a, b) => {
      const timeA = new Date(a.created_at || a.sent_at || 0).getTime();
      const timeB = new Date(b.created_at || b.sent_at || 0).getTime();
      return emailSortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });
  }, [allEmails, emailFilterDirection, emailCenterSearch, emailSortOrder]);

  const clientConversations = useMemo(() => {
    const map = new Map();
    const myEmail = (currentUser?.email || 'tech@leamss.com').toLowerCase().trim();

    (allEmails || []).forEach(e => {
      const isInbound = e.direction === 'inbound' || e.direction === 'incoming';
      let clientEmail = '';
      if (isInbound) {
        clientEmail = (e.from_email || '').trim().toLowerCase();
      } else {
        clientEmail = (e.to_email || '').trim().toLowerCase();
      }

      if (!clientEmail || clientEmail === myEmail || clientEmail === 'tech@leamss.com' || clientEmail === 'info@leamss.com') {
        const alt = (isInbound ? e.to_email : e.from_email || '').trim().toLowerCase();
        if (alt && alt !== myEmail && alt !== 'tech@leamss.com' && alt !== 'info@leamss.com') {
          clientEmail = alt;
        }
      }
      if (!clientEmail) return;

      const match = clientEmail.match(/[\w\.-]+@[\w\.-]+\.\w+/);
      const cleanEmail = match ? match[0] : clientEmail;

      const matchedLead = leads.find(l => 
        (e.lead_id && l.id === e.lead_id) || 
        (l.email && l.email.toLowerCase().trim() === cleanEmail)
      );

      let clientName = matchedLead?.name;
      if (!clientName && e.contact_name && !e.contact_name.toLowerCase().includes('advisor') && !e.contact_name.toLowerCase().includes('leamss')) {
        clientName = e.contact_name;
      }
      if (!clientName && isInbound && e.from_name && !e.from_name.toLowerCase().includes('leamss') && e.from_name.toLowerCase() !== 'pooja') {
        clientName = e.from_name;
      }
      if (!clientName) {
        const userPrefix = cleanEmail.split('@')[0].replace(/[0-9_.-]+/g, ' ').trim();
        clientName = userPrefix ? userPrefix.replace(/\b\w/g, c => c.toUpperCase()) : cleanEmail;
      }

      if (!map.has(cleanEmail)) {
        map.set(cleanEmail, {
          email: cleanEmail,
          name: clientName,
          lead: matchedLead || null,
          lead_id: matchedLead?.id || e.lead_id || null,
          emails: [],
          inboundCount: 0,
          outboundCount: 0,
          hasInboundReply: false,
          latestEmail: e,
          latestDate: new Date(e.created_at || e.sent_at || 0),
          latestSubject: e.subject || '(No Subject)',
        });
      }

      const conv = map.get(cleanEmail);
      conv.emails.push(e);
      if (isInbound) {
        conv.inboundCount += 1;
        conv.hasInboundReply = true;
      } else {
        conv.outboundCount += 1;
      }

      if (matchedLead?.name) {
        conv.name = matchedLead.name;
        conv.lead = matchedLead;
      } else if (e.contact_name && (!conv.name || conv.name === cleanEmail)) {
        conv.name = e.contact_name;
      }

      const eDate = new Date(e.created_at || e.sent_at || 0);
      if (eDate > conv.latestDate) {
        conv.latestDate = eDate;
        conv.latestEmail = e;
        conv.latestSubject = e.subject || '(No Subject)';
      }
    });

    const list = Array.from(map.values()).sort((a, b) => b.latestDate - a.latestDate);

    list.forEach(conv => {
      conv.emails.sort((a, b) => {
        const tA = new Date(a.created_at || a.sent_at || 0).getTime();
        const tB = new Date(b.created_at || b.sent_at || 0).getTime();
        return tA - tB;
      });
    });

    return list;
  }, [allEmails, leads, currentUser]);

  const filteredClientConversations = useMemo(() => {
    return clientConversations.filter(c => {
      if (emailFilterDirection === 'inbound' && !c.hasInboundReply) return false;
      if (emailFilterDirection === 'outbound' && c.outboundCount === 0) return false;
      if (emailCenterSearch.trim()) {
        const q = emailCenterSearch.toLowerCase().trim();
        const nameMatch = (c.name || '').toLowerCase().includes(q);
        const emailMatch = (c.email || '').toLowerCase().includes(q);
        const subjMatch = (c.latestSubject || '').toLowerCase().includes(q) || c.emails.some(e => (e.subject || '').toLowerCase().includes(q));
        const bodyMatch = c.emails.some(e => (e.raw_text || e.body_html || '').toLowerCase().includes(q));
        return nameMatch || emailMatch || subjMatch || bodyMatch;
      }
      return true;
    });
  }, [clientConversations, emailFilterDirection, emailCenterSearch]);

  const activeConversation = useMemo(() => {
    if (!clientConversations.length) return null;
    if (selectedEmailClientKey) {
      const found = clientConversations.find(c => c.email.toLowerCase() === selectedEmailClientKey.toLowerCase());
      if (found) return found;
    }
    return filteredClientConversations[0] || clientConversations[0] || null;
  }, [clientConversations, filteredClientConversations, selectedEmailClientKey]);

  const displayedEmails = useMemo(() => {
    return [...leadEmails].sort((a, b) => {
      const timeA = new Date(a.created_at || a.sent_at || 0).getTime();
      const timeB = new Date(b.created_at || b.sent_at || 0).getTime();
      return emailSortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });
  }, [leadEmails, emailSortOrder]);

  const sourceCounts = useMemo(() => {
    const counts = {};
    const bookedEmails = new Set(
      meetings
        .filter(m => String(m.meeting_type || m.source || '').toLowerCase().includes('calendly'))
        .map(m => String(m.contact_email || '').toLowerCase().trim())
        .filter(Boolean)
    );
    const bookedLeadIds = new Set(
      meetings
        .filter(m => String(m.meeting_type || m.source || '').toLowerCase().includes('calendly'))
        .map(m => String(m.lead_id || '').trim())
        .filter(Boolean)
    );

    leads.forEach(l => {
      const src = (l.source || '').trim();
      let norm = 'Unknown';
      if (!src || src.toLowerCase() === 'unknown') norm = 'Unknown';
      else if (['website', 'website popup'].includes(src.toLowerCase())) norm = 'Website';
      else if (['calendly'].includes(src.toLowerCase())) norm = 'Calendly';
      else if (['facebook ads', 'facebook'].includes(src.toLowerCase())) norm = 'Facebook Ads';
      else if (['google sheets', 'google_sheets'].includes(src.toLowerCase())) norm = 'Google Sheets';
      else if (['zoho', 'zoho crm'].includes(src.toLowerCase())) norm = 'Zoho';
      else norm = src;
      counts[norm] = (counts[norm] || 0) + 1;

      // Count leads who booked a Calendly meeting under Calendly as well
      if (norm !== 'Calendly' && (
        (l.email && bookedEmails.has(String(l.email).toLowerCase().trim())) ||
        (l.id && bookedLeadIds.has(String(l.id).trim())) ||
        l.has_booking ||
        (Array.isArray(l.tags) && l.tags.includes('calendly'))
      )) {
        counts['Calendly'] = (counts['Calendly'] || 0) + 1;
      }
    });
    return counts;
  }, [leads, meetings]);

  const isLeadAssignedToday = useCallback((l) => {
    if (!l) return false;
    const todayStr = new Date().toISOString().slice(0, 10);
    const localTodayStr = new Date().toLocaleDateString('en-CA');

    const checkMatch = (val) => {
      if (!val) return false;
      try {
        const d = new Date(val);
        if (isNaN(d.getTime())) return false;
        const s1 = d.toISOString().slice(0, 10);
        const s2 = d.toLocaleDateString('en-CA');
        return s1 === todayStr || s2 === localTodayStr || s1 === localTodayStr || s2 === todayStr;
      } catch {
        return false;
      }
    };

    // Strict: If assigned_at exists, it MUST be today
    if (l.assigned_at) {
      return checkMatch(l.assigned_at);
    }

    // Only if assigned_at is missing: check if lead was created today with an assignment
    if (l.assigned_to && checkMatch(l.created_at)) {
      return true;
    }

    return false;
  }, []);

  const todayAssignedLeads = useMemo(() => {
    return leads.filter(l => isLeadAssignedToday(l));
  }, [leads, isLeadAssignedToday]);

  const filteredLeads = useMemo(() => {
    const bookedEmails = new Set(
      meetings
        .filter(m => String(m.meeting_type || m.source || '').toLowerCase().includes('calendly'))
        .map(m => String(m.contact_email || '').toLowerCase().trim())
        .filter(Boolean)
    );
    const bookedLeadIds = new Set(
      meetings
        .filter(m => String(m.meeting_type || m.source || '').toLowerCase().includes('calendly'))
        .map(m => String(m.lead_id || '').trim())
        .filter(Boolean)
    );

    return leads
      .filter(l => {
        // Filter out bot spam and scam promotions
        if (l.is_spam || l.source === 'Sample Leads') return false;
        const lName = (l.name || '').toLowerCase().trim();
        const lEmail = (l.email || '').toLowerCase().trim();
        if (lName.includes('scam service') || lName.includes('myxa.cc') || lName.includes('<a href') || lName.includes('[url=') || lName.startsWith('* * *')) return false;
        if (lEmail.includes('merepost.com') || lEmail.includes('myxa.cc') || lEmail.endsWith('@example.com')) return false;

        // Salespersons can only view leads assigned to them; Managers and Admins can view all leads
        const isManagerOrAdmin = isAdmin || currentUser?.role === 'sales_manager' || currentUser?.role === 'sales_head' || currentUser?.rbac_role === 'sales_manager' || currentUser?.rbac_role === 'sales_head';
        if (!isManagerOrAdmin && currentUser) {
          const myId = String(currentUser.id || '').trim();
          const myEmail = String(currentUser.email || '').toLowerCase().trim();
          const myName = String(currentUser.name || '').toLowerCase().trim();
          const assignedTo = String(l.assigned_to || '').trim();
          const assignedToEmail = String(l.assigned_to_email || '').toLowerCase().trim();
          const assignedToName = String(l.assigned_to_name || '').toLowerCase().trim();

          const isAssignedToMe = (
            (myId && (assignedTo === myId || String(l.assigned_sales_rep_id || '').trim() === myId || String(l.assigned_sales_person_id || '').trim() === myId || String(l.sales_person_id || '').trim() === myId || String(l.created_by || '').trim() === myId)) ||
            (myEmail && (assignedTo.toLowerCase() === myEmail || assignedToEmail === myEmail || String(l.assigned_sales_person_name || '').toLowerCase() === myName)) ||
            (myName && (assignedToName === myName || String(l.assigned_sales_person_name || '').toLowerCase() === myName))
          );
          if (!isAssignedToMe) return false;
        }

        if (assignedTodayFilter) {
          if (!isLeadAssignedToday(l)) return false;
        }

        if (stageFilter !== 'all') {
          if (stageFilter === 'converted') {
            const isConverted = l.stage === 'converted' || l.status === 'converted' || Boolean(l.converted) || ['won', 'closed_won', 'case_created'].includes(String(l.stage || l.status || '').toLowerCase());
            if (!isConverted) return false;
          } else if (l.stage !== stageFilter && l.status !== stageFilter) {
            return false;
          }
        }
        if (sourceFilter !== 'all') {
          const leadSrc = (l.source || '').trim();
          if (sourceFilter === 'Unknown') {
            if (leadSrc && leadSrc.toLowerCase() !== 'unknown') return false;
          } else if (sourceFilter === 'Website') {
            if (!['website', 'website popup'].includes(leadSrc.toLowerCase())) return false;
          } else if (sourceFilter === 'Calendly' || sourceFilter === 'Calendly Bookings') {
            const isCalendlySource = ['calendly'].includes(leadSrc.toLowerCase());
            const hasCalendlyTag = Array.isArray(l.tags) && l.tags.includes('calendly');
            const emailMatch = l.email && bookedEmails.has(String(l.email).toLowerCase().trim());
            const idMatch = l.id && bookedLeadIds.has(String(l.id).trim());
            if (!isCalendlySource && !hasCalendlyTag && !emailMatch && !idMatch && !l.has_booking) {
              return false;
            }
          } else if (sourceFilter === 'Facebook Ads') {
            if (!['facebook ads', 'facebook'].includes(leadSrc.toLowerCase())) return false;
          } else if (sourceFilter === 'Google Sheets') {
            if (!['google sheets', 'google_sheets'].includes(leadSrc.toLowerCase())) return false;
          } else if (sourceFilter === 'Zoho') {
            if (!['zoho', 'zoho crm'].includes(leadSrc.toLowerCase())) return false;
          } else {
            if (leadSrc.toLowerCase() !== sourceFilter.toLowerCase()) return false;
          }
        }
        if (countryFilter !== 'all' && l.country_of_interest !== countryFilter && l.interested_country !== countryFilter) return false;
        
        // Pipeline Cockpit Filters
        if (paymentFilter === 'paid' && !l.is_paid) return false;
        if (paymentFilter === 'unpaid' && (l.is_paid || l.payment_status === 'failed')) return false;
        if (paymentFilter === 'failed' && l.payment_status !== 'failed') return false;
        if (paymentFilter === 'partially_paid' && l.payment_status !== 'partially_paid') return false;
        if (reportFilter === 'generated' && !l.report_generated) return false;
        if (reportFilter === 'paid_pending' && !(l.is_paid && !l.report_generated)) return false;

        // Salesperson Filter
        if (salespersonFilter !== 'all') {
          const assignedTo = String(l.assigned_to || '').trim();
          const assignedToName = String(l.assigned_to_name || '').toLowerCase().trim();
          if (salespersonFilter === 'unassigned') {
            if (assignedTo && assignedTo !== 'unassigned' && assignedTo !== 'none') return false;
          } else {
            const matchesId = assignedTo === salespersonFilter;
            const rep = salesReps.find(r => r.id === salespersonFilter);
            const matchesName = rep && assignedToName === rep.name.toLowerCase().trim();
            if (!matchesId && !matchesName) return false;
          }
        }

        if (search) {
          const q = search.toLowerCase();
          return (l.name || '').toLowerCase().includes(q) ||
            (l.phone || '').includes(q) ||
            (l.email || '').toLowerCase().includes(q) ||
            (l.lead_number || '').toLowerCase().includes(q) ||
            (l.service_interested || '').toLowerCase().includes(q);
        }
        return true;
      })
      .sort((a, b) => {
        // Compare lead numbers if they follow LD\d+ pattern (e.g. LD006997 > LD006996) so newest submissions always appear first
        const numA = parseInt(String(a.lead_number || '').replace(/\D/g, ''), 10) || 0;
        const numB = parseInt(String(b.lead_number || '').replace(/\D/g, ''), 10) || 0;
        if (numA && numB && numA !== numB) {
          return numB - numA;
        }
        const timeA = Math.max(new Date(a.updated_at || 0).getTime(), new Date(a.created_at || 0).getTime());
        const timeB = Math.max(new Date(b.updated_at || 0).getTime(), new Date(b.created_at || 0).getTime());
        return timeB - timeA;
      });
  }, [leads, stageFilter, sourceFilter, countryFilter, paymentFilter, reportFilter, salespersonFilter, search, isAdmin, currentUser, meetings, assignedTodayFilter, isLeadAssignedToday, salesReps]);

  // Action Click Handler for "Actions Waiting for You" cards
  const handleActionWaitingClick = (actionKey) => {
    if (actionKey === 'assigned_today') {
      setView('table');
      setAssignedTodayFilter(true);
    } else if (actionKey === 'calls_due') {
      setView('followups');
    } else if (actionKey === 'follow_ups_due') {
      setView('followups');
    } else if (actionKey === 'whatsapp_replies') {
      setView('whatsapp');
      setWaInboxTab('unread');
    } else if (actionKey === 'emails_pending') {
      setView('emails');
    } else if (actionKey === 'payment_followups') {
      setView('pipeline');
      setStageFilter('payment_pending');
    } else if (actionKey === 'documents_pending') {
      setView('table');
      setStageFilter('assessment');
    } else if (actionKey === 'meetings_today') {
      setView('meetings');
    } else if (actionKey === 'overdue_actions') {
      setView('followups');
    }
  };

  // ─── PIPELINE COCKPIT INTEGRATION ACTIONS ───
  const handleSyncWebsiteLeads = async () => {
    setSyncingLeads(true);
    const toastId = toast.loading('Syncing website enquiries and form submissions...');
    try {
      const res = await axios.post(`${API}/crm/website-leads/sync-now`, {}, getAuthHeader());
      if (res.data?.success) {
        toast.success(res.data.message || `Synced ${res.data.total_new_leads || 0} leads from website!`, { id: toastId });
        await fetchAllCRMData();
      } else {
        toast.info(res.data?.message || 'Sync completed', { id: toastId });
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to sync website leads', { id: toastId });
    } finally {
      setSyncingLeads(false);
    }
  };

  const handleMarkLeadPaid = async (lead, customAmount = 2427.0) => {
    if (!lead?.id) return;
    setMarkingPaidId(lead.id);
    const toastId = toast.loading(`Marking payment of ₹${Number(customAmount).toLocaleString('en-IN')} for ${lead.name || 'lead'}...`);
    try {
      const res = await axios.post(`${API}/crm/leads/${lead.id}/mark-paid`, {
        payment_mode: 'upi',
        payment_amount: customAmount,
        trigger_auto_resume_request: true
      }, getAuthHeader());
      if (res.data?.success) {
        toast.success(res.data.message || `Payment of ₹${customAmount} recorded!`, { id: toastId });
        setLeads(prev => prev.map(l => (l.id === lead.id || l.unique_id === lead.id) ? { ...l, is_paid: true, payment_status: 'paid', payment_amount: customAmount, stage: 'payment_done' } : l));
        if (selectedLead && (selectedLead.id === lead.id || selectedLead.unique_id === lead.id)) {
          setSelectedLead(prev => ({ ...prev, is_paid: true, payment_status: 'paid', payment_amount: customAmount, stage: 'payment_done' }));
        }
        fetchAllCRMData();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record payment', { id: toastId });
    } finally {
      setMarkingPaidId(null);
    }
  };

  const handleCheckRazorpayPayment = async (lead) => {
    if (!lead?.id) return;
    setCheckingPaymentId(lead.id);
    const toastId = toast.loading(`Checking live Razorpay payments for ${lead.name || 'client'}...`);
    try {
      const res = await axios.post(`${API}/crm/leads/${lead.id}/check-razorpay-payment`, {}, getAuthHeader());
      if (res.data?.success) {
        if (res.data.matched) {
          const p = res.data.payment || {};
          const isPaid = p.status === 'captured';
          const paidAmt = p.amount ? p.amount / 100 : (isPaid ? 2427 : 0);
          toast.success(
            isPaid
              ? `Payment confirmed! ₹${Number(paidAmt).toLocaleString('en-IN')} captured (ID: ${p.id})`
              : `Payment found: ${p.status?.toUpperCase()} (${p.error_description || p.id})`,
            { id: toastId }
          );
          if (res.data.lead) {
            setSelectedLead(res.data.lead);
            setLeads(prev => prev.map(l => (l.id === lead.id || l.unique_id === lead.id) ? res.data.lead : l));
          } else {
            fetchAllCRMData();
          }
        } else {
          toast.info(res.data.message || 'No matching Razorpay payments found in recent records.', { id: toastId });
        }
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to check Razorpay payment', { id: toastId });
    } finally {
      setCheckingPaymentId(null);
    }
  };

  const handleSendPaymentLink = async (lead) => {
    if (!lead?.id) return;
    setSendingPaymentLinkId(lead.id);
    const toastId = toast.loading(`Sending payment link to ${lead.name || 'client'}...`);
    try {
      const res = await axios.post(`${API}/crm/leads/${lead.id}/send-payment-link`, {}, getAuthHeader());
      if (res.data?.success) {
        toast.success(res.data.message || 'Payment link sent via Email & WhatsApp!', { id: toastId });
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send payment link', { id: toastId });
    } finally {
      setSendingPaymentLinkId(null);
    }
  };

  const handleSendResumeRequest = async (lead) => {
    if (!lead?.id) return;
    setSendingResumeReqId(lead.id);
    const toastId = toast.loading(`Dispatching resume upload request to ${lead.name || 'client'}...`);
    try {
      const res = await axios.post(`${API}/crm/leads/${lead.id}/send-resume-request`, { base_url: window.location.origin }, getAuthHeader());
      if (res.data?.success) {
        toast.success(res.data.message || 'Resume request sent via Email & WhatsApp!', { id: toastId });
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to dispatch resume request', { id: toastId });
    } finally {
      setSendingResumeReqId(null);
    }
  };
  const handleOpenPreAssessmentReport = (lead) => {
    if (!lead) return;
    const clientName = lead.name || 'Client';
    const currentTimeStr = getFormattedLocalTimeStr();
    const sourceTabName = view === 'kanban' ? 'Leads Board' : 'All Leads Table';

    axios.post(`${API}/salesperson-activity/log`, {
      activity_type: 'client_view',
      client_id: lead.id || lead.unique_id,
      client_name: clientName,
      client_phone: lead.phone,
      client_email: lead.email,
      title: `Opened Pre-Assessment Report: ${clientName} (${sourceTabName})`,
      details: `Salesperson opened Pre-Assessment Report generator for client ${clientName} from ${sourceTabName} at ${currentTimeStr}.`,
      start_time: currentTimeStr,
      metadata: {
        source_view: view,
        source_tab: sourceTabName,
        lead_id: lead.id,
        lead_number: lead.lead_number,
        timezone: 'Asia/Kolkata'
      }
    }, getAuthHeader()).catch(() => {});

    const prefillData = {
      name: lead.name || '',
      email: lead.email || '',
      phone: lead.phone || '',
      qualification: lead.latest_qualification || lead.qualification || lead.education || '',
      experience: lead.total_work_experience || lead.experience || lead.experience_years || '',
      dob: lead.dob || '',
      marital_status: lead.marital_status || lead.marital || '',
      resume_url: lead.resume_url || '',
      lead_id: lead.id || '',
    };
    try {
      sessionStorage.setItem('client_assessment_prefill', JSON.stringify(prefillData));
    } catch (_) {}

    const params = new URLSearchParams();
    if (prefillData.name) params.set('name', prefillData.name);
    if (prefillData.email) params.set('email', prefillData.email);
    if (prefillData.phone) params.set('phone', prefillData.phone);
    if (prefillData.qualification) params.set('qualification', prefillData.qualification);
    if (prefillData.experience) params.set('experience', prefillData.experience);
    if (prefillData.dob) params.set('dob', prefillData.dob);
    if (prefillData.marital_status) params.set('marital', prefillData.marital_status);
    if (prefillData.resume_url) params.set('resume_url', prefillData.resume_url);
    if (prefillData.lead_id) params.set('lead_id', prefillData.lead_id);

    navigate(`/sales/client-assessment?${params.toString()}`);
  };

  const handleConvertToPreAssessment = async (lead) => {
    if (!lead?.id) return;
    if (!lead.resume_file_id && !lead.resume_url && !lead.resume_uploaded) {
      toast.error("Please upload client resume first!");
      return;
    }
    setConvertingLeadId(lead.id);
    const toastId = toast.loading(`Converting lead ${lead.name || ''} to Pre-Assessment...`);
    try {
      const res = await axios.post(`${API}/leads/${lead.id}/convert-to-pa`, {}, getAuthHeader());
      if (res.data?.pa_number) {
        toast.success(`Converted to Pre-Assessment (${res.data.pa_number})!`, { id: toastId });
        await fetchAllCRMData();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to convert to Pre-Assessment', { id: toastId });
    } finally {
      setConvertingLeadId(null);
    }
  };

  const fetchPartnerReport = async () => {
    setLoadingPartnerReport(true);
    try {
      const res = await axios.get(`${API}/crm/partner-report?period=lifetime`, getAuthHeader());
      setPartnerReportData(res.data);
      setShowPartnerReportModal(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load partner report');
    } finally {
      setLoadingPartnerReport(false);
    }
  };

  // Handle Add Lead
  const handleCreateLead = async (e) => {
    e.preventDefault();
    if (!newLead.name || !newLead.phone) {
      toast.error('Name and phone are required');
      return;
    }
    setSaving(true);
    const toastId = toast.loading(newLeadResumeFile ? 'Saving lead and uploading candidate resume...' : 'Saving lead...');
    try {
      const res = await axios.post(`${API}/leads/capture`, newLead, getAuthHeader());
      const leadId = res.data?.lead_id || res.data?.lead?.id;

      if (newLeadResumeFile && leadId) {
        try {
          const formData = new FormData();
          formData.append('file', newLeadResumeFile);
          await axios.post(`${API}/leads/${leadId}/resume`, formData, {
            headers: {
              ...getAuthHeader().headers,
              'Content-Type': 'multipart/form-data',
            },
          });
          toast.success('Lead and candidate resume saved successfully', { id: toastId });
        } catch (resumeErr) {
          console.error('Failed to attach resume to new lead:', resumeErr);
          toast.warning('Lead created successfully, but resume upload failed. You can re-attach it anytime.', { id: toastId });
        }
      } else {
        toast.success(res.data.message || 'Lead created successfully', { id: toastId });
      }

      setShowAddLead(false);
      setNewLead(emptyLead);
      setNewLeadResumeFile(null);
      setWebsiteLeadsRefreshKey(k => k + 1);
      fetchAllCRMData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save lead', { id: toastId });
    } finally {
      setSaving(false);
    }
  };

  // Handle Edit Lead
  const handleOpenEditLead = (lead) => {
    const target = lead || selectedLead;
    if (!target) {
      toast.error('No lead selected for editing');
      return;
    }
    const resolvedId = target.id || target._id || target.lead_number;
    setEditingLeadId(resolvedId);
    setEditingLead(target);
    setSelectedLead(target);
    setEditLeadResumeFile(null);
    setEditLeadForm({
      id: resolvedId,
      name: target.name || '',
      phone: target.phone || '',
      email: target.email || '',
      whatsapp_number: target.whatsapp_number || target.phone || '',
      occupation: target.occupation || '',
      total_work_experience: target.total_work_experience || target.experience || '',
      latest_qualification: target.latest_qualification || target.qualification || '',
      city: target.city || '',
      country: target.country || '',
      country_of_interest: target.country_of_interest || target.interested_country || 'Canada',
      service_interested: target.service_interested || target.service || '',
      interested_program: target.interested_program || target.visa_type || '',
      budget: target.budget || '',
      source: target.source || 'Website',
      priority: target.priority || 'medium',
      message: target.message || '',
      assigned_to: target.assigned_to || '',
      assigned_to_name: target.assigned_name || target.assigned_to_name || ''
    });
    setShowEditLead(true);
  };

  const handleSaveEditLead = async (e) => {
    if (e) {
      if (typeof e.preventDefault === 'function') e.preventDefault();
      if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    const targetId = editingLeadId || editLeadForm.id || selectedLead?.id || selectedLead?._id || selectedLead?.lead_number;
    if (!targetId) {
      toast.error('Unable to determine lead record ID to update');
      return;
    }
    if (!editLeadForm.name || !editLeadForm.phone) {
      toast.error('Name and phone are required');
      return;
    }
    setSaving(true);
    const toastId = toast.loading(editLeadResumeFile ? 'Updating lead and uploading resume...' : 'Updating lead...');
    try {
      const payload = { ...editLeadForm };
      delete payload.id;
      delete payload._id;

      const res = await axios.put(`${API}/leads/${targetId}`, payload, getAuthHeader());
      let updatedResumeFields = {};

      if (editLeadResumeFile) {
        try {
          const formData = new FormData();
          formData.append('file', editLeadResumeFile);
          const resumeRes = await axios.post(`${API}/leads/${targetId}/resume`, formData, {
            headers: {
              ...getAuthHeader().headers,
              'Content-Type': 'multipart/form-data',
            },
          });
          updatedResumeFields = {
            resume_file_id: resumeRes.data?.resume_file_id,
            resume_filename: resumeRes.data?.resume_filename || editLeadResumeFile.name,
            resume_url: resumeRes.data?.resume_url || `/cockpit/resume/${resumeRes.data?.resume_file_id}`,
            resume_uploaded: true,
          };
          toast.success('Lead and resume updated successfully', { id: toastId });
        } catch (resumeErr) {
          console.error('Failed to update resume for lead:', resumeErr);
          toast.warning('Lead updated, but resume upload failed.', { id: toastId });
        }
      } else {
        toast.success(res.data?.message || 'Lead updated successfully', { id: toastId });
      }

      const mergedLead = { ...(editingLead || selectedLead || {}), ...payload, ...updatedResumeFields };
      setSelectedLead(mergedLead);
      setLeads(prev => prev.map(l => (l.id === targetId || l._id === targetId || l.lead_number === targetId || (payload.email && l.email?.toLowerCase() === payload.email.toLowerCase())) ? { ...l, ...payload, ...updatedResumeFields } : l));
      if (payload.assigned_to !== undefined) {
        setMeetings(prev => prev.map(m => (m.lead_id === targetId || (m.contact_email && payload.email && m.contact_email.toLowerCase() === payload.email.toLowerCase())) ? { ...m, sales_person_id: payload.assigned_to, sales_person_name: payload.assigned_to_name } : m));
      }
      setShowEditLead(false);
      setEditLeadResumeFile(null);
      setEditingLeadId(null);
      setEditingLead(null);
      setWebsiteLeadsRefreshKey(k => k + 1);
      fetchAllCRMData();
    } catch (err) {
      console.error('Failed to update lead:', err);
      toast.error(err.response?.data?.detail || err.message || 'Failed to update lead', { id: toastId });
    } finally {
      setSaving(false);
    }
  };

  // ────────────────────────────────────────────────────────────
  // PC-SIDE AUTOMATIC LIVE CALL RECORDING HANDLERS
  // ────────────────────────────────────────────────────────────
  const startAudioRecording = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('MediaDevices API not supported in this browser');
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      audioStreamRef.current = stream;
      audioChunksRef.current = [];

      let mimeType = 'audio/webm;codecs=opus';
      if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== 'function' || !MediaRecorder.isTypeSupported(mimeType)) {
        if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/webm')) mimeType = 'audio/webm';
        else if (window.MediaRecorder && MediaRecorder.isTypeSupported('audio/ogg')) mimeType = 'audio/ogg';
        else mimeType = '';
      }

      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(1000); // chunk every second
      setIsRecording(true);
      setIsMuted(false);
      setRecordingDuration(0);

      if (callTimerRef.current) clearInterval(callTimerRef.current);
      callTimerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
    } catch (err) {
      console.warn('Microphone access for PC call recording not granted:', err);
      setIsRecording(false);
      toast.info('Microphone recording inactive. (Call timer is running — you can dial via mobile SIM/FaceTime and log notes/duration).');
    }
  };

  const stopAudioTracks = () => {
    if (callTimerRef.current) {
      clearInterval(callTimerRef.current);
      callTimerRef.current = null;
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }
    setIsRecording(false);
    setIsMuted(false);
  };

  const toggleMute = () => {
    if (audioStreamRef.current) {
      const audioTracks = audioStreamRef.current.getAudioTracks();
      const nextMuted = !isMuted;
      audioTracks.forEach(t => { t.enabled = !nextMuted; });
      setIsMuted(nextMuted);
    }
  };

  // Start Phone Call & Auto Start PC-Side Live Recording
  const handleStartCall = async (lead) => {
    const targetLead = lead || selectedLead;
    if (!targetLead) {
      toast.error('No client selected to call');
      return;
    }
    setCallLead(targetLead);
    if (!selectedLead) {
      setSelectedLead(targetLead);
    }
    setCallDirection('outgoing');
    setCallNotes('');
    setCallTranscript('');
    setCallOutcome('interested');
    setRecordingDuration(0);
    setShowCallModal(true);

    // Auto-start duration timer immediately for this call session
    if (callTimerRef.current) clearInterval(callTimerRef.current);
    callTimerRef.current = setInterval(() => {
      setRecordingDuration(prev => prev + 1);
    }, 1000);

    // Auto-start microphone recording for the live call if supported
    await startAudioRecording();
  };

  const handleManualDial = (phone) => {
    if (!phone) return;
    const cleanPhone = String(phone).replace(/[^0-9+]/g, '');
    const telUrl = cleanPhone.startsWith('+') ? `tel:${cleanPhone}` : `tel:+91${cleanPhone}`;
    try {
      window.location.href = telUrl;
    } catch (e) {
      console.warn('Could not trigger tel: protocol', e);
    }
  };

  const handleWhatsAppCall = async (phone, lead = null) => {
    const targetLead = lead || selectedLead;
    const rawPhone = phone || targetLead?.whatsapp_number || targetLead?.phone;
    if (!rawPhone) {
      toast.error('No phone number registered for WhatsApp call');
      return;
    }
    const cleanDigits = String(rawPhone).replace(/[^0-9]/g, '');
    const fullPhone = cleanDigits.length === 10 ? `91${cleanDigits}` : cleanDigits;
    const salesRepName = currentUser?.name || 'LEAMSS Consultant';
    const contactName = targetLead?.name || 'Client';

    // Log the WhatsApp call to CRM
    try {
      await axios.post(`${API}/crm/whatsapp/call-log`, {
        lead_id: targetLead?.id,
        phone: fullPhone,
        contact_name: contactName,
        sales_person_name: salesRepName,
        notes: `Outgoing WhatsApp call to ${contactName} (${fullPhone}) by ${salesRepName}`,
        direction: 'outgoing'
      }, getAuthHeader());
      
      toast.success(`WhatsApp call initiated & logged to ${contactName}'s history!`);
      if (targetLead?.id) {
        loadLeadWhatsApp(targetLead.id);
        loadLeadTimeline(targetLead.id);
        loadLeadCalls(targetLead.id);
      }
      fetchAllCRMData();
    } catch (err) {
      console.warn('Could not log WhatsApp call', err);
    }

    // Open WhatsApp direct link (direct WhatsApp Web on desktop to bypass landing page)
    const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const callUrl = isMobile ? `https://wa.me/${fullPhone}` : `https://web.whatsapp.com/send?phone=${fullPhone}`;
    window.open(callUrl, '_blank');
  };

  const handleSaveCallNotes = async () => {
    const targetLead = callLead || selectedLead;
    if (!targetLead) return;
    setUploadingRecording(true);

    let recordingUrl = '';
    const finalDuration = recordingDuration;

    try {
      // 1. If recording was active, gracefully stop MediaRecorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        await new Promise((resolve) => {
          mediaRecorderRef.current.onstop = resolve;
          mediaRecorderRef.current.stop();
        });
      }

      stopAudioTracks();

      // 2. If recorded chunks exist, upload audio file
      if (audioChunksRef.current && audioChunksRef.current.length > 0) {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (audioBlob.size > 1000) {
          const formData = new FormData();
          const cleanName = (targetLead.name || 'client').replace(/[^a-zA-Z0-9]/g, '_');
          formData.append('file', audioBlob, `call_${cleanName}_${Date.now()}.webm`);

          try {
            const upRes = await axios.post(`${API}/crm/calls/recordings/upload`, formData, {
              headers: {
                ...getAuthHeader().headers,
                'Content-Type': 'multipart/form-data'
              }
            });
            if (upRes.data && upRes.data.recording_url) {
              recordingUrl = upRes.data.recording_url;
            }
          } catch (upErr) {
            console.error('Failed to upload call recording:', upErr);
          }
        }
      }

      // 3. Save Call record with duration and recording URL to CRM database
      const noteContent = callNotes.trim() ? `[Consultation Note] ${callNotes}` : 'PC Live Call Session';
      await axios.post(`${API}/crm/calls`, {
        lead_id: targetLead.id,
        direction: callDirection || 'outgoing',
        duration_seconds: finalDuration || 0,
        status: 'connected',
        outcome: callOutcome || 'interested',
        notes: noteContent,
        lead_phone: targetLead.phone,
        lead_name: targetLead.name,
        recording_url: recordingUrl || '',
        transcript: callTranscript.trim()
      }, getAuthHeader());

      toast.success(recordingUrl ? 'Call ended, recorded & saved to client history!' : 'Call logged to client history!');
      setShowCallModal(false);
      if (targetLead.id) {
        loadLeadCalls(targetLead.id);
        loadLeadTimeline(targetLead.id);
      }
      loadAllCalls();
      fetchAllCRMData();
    } catch (err) {
      console.error('Error saving call:', err);
      toast.error('Failed to save call');
      setShowCallModal(false);
    } finally {
      setUploadingRecording(false);
      audioChunksRef.current = [];
    }
  };

  const handleCloseCallModal = () => {
    stopAudioTracks();
    setShowCallModal(false);
  };

  // Call Intelligence & Transcript Handlers
  const handleDatePresetChange = (preset) => {
    setCallDatePreset(preset);
    const now = new Date();
    const formatYMD = (d) => {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };

    if (preset === 'all') {
      setCallDateFrom('');
      setCallDateTo('');
    } else if (preset === 'today') {
      const todayStr = formatYMD(now);
      setCallDateFrom(todayStr);
      setCallDateTo(todayStr);
    } else if (preset === 'yesterday') {
      const y = new Date(now);
      y.setDate(y.getDate() - 1);
      const yStr = formatYMD(y);
      setCallDateFrom(yStr);
      setCallDateTo(yStr);
    } else if (preset === 'this_week') {
      const w = new Date(now);
      w.setDate(w.getDate() - 7);
      setCallDateFrom(formatYMD(w));
      setCallDateTo(formatYMD(now));
    } else if (preset === 'this_month') {
      const m = new Date(now.getFullYear(), now.getMonth(), 1);
      setCallDateFrom(formatYMD(m));
      setCallDateTo(formatYMD(now));
    }
  };

  const handleRegenerateAiSummary = async (callId) => {
    setRegeneratingAiCalls(prev => ({ ...prev, [callId]: true }));
    try {
      const res = await axios.post(`${API}/crm/calls/${callId}/ai-summary`, {}, getAuthHeader());
      toast.success('AI summary updated successfully!');
      if (res.data) {
        setCalls(prev => prev.map(c => c.id === callId ? { ...c, ...res.data } : c));
        setLeadCalls(prev => prev.map(c => c.id === callId ? { ...c, ...res.data } : c));
      }
    } catch (err) {
      console.error('Error regenerating AI summary:', err);
      toast.error('Failed to regenerate AI summary');
    } finally {
      setRegeneratingAiCalls(prev => ({ ...prev, [callId]: false }));
    }
  };

  const handleOpenTranscriptModal = (call) => {
    setTranscriptModal({
      open: true,
      call,
      transcriptText: call?.transcript || '',
      saving: false
    });
  };

  const handleSaveTranscript = async () => {
    const targetCall = transcriptModal.call;
    const targetCallId = targetCall?.id || targetCall?._id;
    const targetLeadId = targetCall?.lead_id || (targetCall?.lead_name ? targetCall?.id : null) || selectedLead?.id;

    if (!targetCallId && !targetLeadId) {
      toast.error('No call or client record selected');
      return;
    }

    setTranscriptModal(prev => ({ ...prev, saving: true }));
    try {
      const endpoint = targetCallId
        ? `${API}/crm/calls/${targetCallId}/transcript`
        : `${API}/crm/calls`;

      const payload = targetCallId ? {
        transcript: transcriptModal.transcriptText,
        lead_id: targetLeadId
      } : {
        lead_id: targetLeadId,
        direction: targetCall?.direction || 'outgoing',
        duration_seconds: targetCall?.duration_seconds || 0,
        status: targetCall?.status || 'connected',
        outcome: targetCall?.outcome || 'interested',
        notes: targetCall?.notes || 'Call transcript attached via CRM',
        lead_phone: targetCall?.lead_phone || targetCall?.phone,
        lead_name: targetCall?.lead_name || targetCall?.name,
        transcript: transcriptModal.transcriptText
      };

      const res = await axios.post(endpoint, payload, getAuthHeader());
      toast.success('Transcript saved & AI summary updated!');

      if (res.data) {
        const resolvedId = res.data.id || res.data.call_id || targetCallId;
        const updatedCallObj = {
          ...res.data,
          id: resolvedId,
          transcript: transcriptModal.transcriptText,
          transcription_status: res.data.transcription_status || 'completed'
        };

        setCalls(prev => {
          const exists = prev.some(c => c.id === resolvedId || c._id === resolvedId);
          if (exists) {
            return prev.map(c => (c.id === resolvedId || c._id === resolvedId) ? { ...c, ...updatedCallObj } : c);
          }
          return [updatedCallObj, ...prev];
        });

        setLeadCalls(prev => {
          const exists = prev.some(c => c.id === resolvedId || c._id === resolvedId);
          if (exists) {
            return prev.map(c => (c.id === resolvedId || c._id === resolvedId) ? { ...c, ...updatedCallObj } : c);
          }
          return [updatedCallObj, ...prev];
        });
      }

      setTranscriptModal({ open: false, call: null, transcriptText: '', saving: false });
    } catch (err) {
      console.error('Error saving transcript:', err);
      const errMsg = err?.response?.data?.detail || err?.response?.data?.message || err?.message || 'Failed to save transcript';
      toast.error(typeof errMsg === 'string' ? errMsg : 'Failed to save transcript');
      setTranscriptModal(prev => ({ ...prev, saving: false }));
    }
  };

  const toggleTranscript = (callId) => {
    setExpandedTranscripts(prev => ({ ...prev, [callId]: !prev[callId] }));
  };

  const handleDeclineIncomingCall = async () => {
    setShowIncomingPrompt(false);
    if (!selectedLead) return;
    try {
      await axios.post(`${API}/crm/calls`, {
        lead_id: selectedLead.id,
        direction: 'incoming',
        duration_seconds: 0,
        status: 'missed',
        outcome: 'call_back',
        notes: 'Inbound call declined / missed by consultant',
        lead_phone: selectedLead.phone,
        lead_name: selectedLead.name
      }, getAuthHeader());
      toast.info('Missed call logged');
      loadLeadTimeline(selectedLead.id);
      fetchAllCRMData();
    } catch (e) {}
  };

  // Unified WhatsApp Send (WhatsApp Web Direct + Meta Cloud API Optional)
  const handleSendWhatsAppMessage = async ({
    lead = null,
    text = '',
    openWeb = false,
    mode = 'web',
    template_name = null,
    template_components = null,
    media_url = null,
    media_type = null,
    media_filename = null
  }) => {
    const targetLead = lead || selectedLead;
    const rawPhone = targetLead?.whatsapp_number || targetLead?.phone;
    if (!targetLead || !rawPhone) {
      toast.error('No client or phone number selected for WhatsApp');
      return;
    }
    const fullPhone = getSanitizedWhatsAppNumber(rawPhone);
    const salesRepName = currentUser?.name || 'LEAMSS Consultant';
    const msgText = (text || waComposerText || waMessage || '').trim();
    const finalTemplateName = template_name || selectedWaTemplate || null;

    const finalMediaUrl = media_url || waAttachedMedia?.url || null;
    const finalMediaType = media_type || waAttachedMedia?.type || null;
    const finalMediaFilename = media_filename || waAttachedMedia?.filename || null;

    if (!msgText && !finalTemplateName && !finalMediaUrl) {
      toast.error('Please enter a WhatsApp message, select a template, or attach a media file');
      return;
    }

    const dispatchMode = mode || (openWeb ? 'web' : 'web');

    setWaSending(true);
    try {
      const res = await axios.post(`${API}/crm/whatsapp/send`, {
        lead_id: targetLead.id,
        phone: fullPhone,
        contact_name: targetLead.name,
        sales_person_name: salesRepName,
        text: msgText,
        mode: dispatchMode,
        template_name: finalTemplateName,
        template_components,
        media_url: finalMediaUrl,
        media_type: finalMediaType,
        media_filename: finalMediaFilename
      }, getAuthHeader());

      setWaComposerText('');
      setWaMessage('');
      setSelectedWaTemplate('');
      setWaAttachedMedia(null);
      setShowWhatsAppModal(false);

      if (targetLead.id) {
        loadLeadWhatsApp(targetLead.id, false);
        loadLeadTimeline(targetLead.id);
        loadWhatsAppSessionStatus(targetLead.id);
      }
      loadWhatsAppInbox();
      fetchAllCRMData();

      if (dispatchMode === 'direct') {
        if (res.data?.delivered) {
          toast.success(`Message sent directly via official Meta WhatsApp Cloud API to ${targetLead.name}!`);
        } else {
          toast.info(`Message logged in CRM for ${targetLead.name}.`);
        }
        return;
      }

      if (dispatchMode === 'crm_only') {
        toast.success(`Message recorded in CRM timeline for ${targetLead.name}!`);
        return;
      }

      const messageId = res.data?.id;

      if (dispatchMode === 'app' || dispatchMode === 'web') {
        if (dispatchMode === 'app') {
          window.open(`whatsapp://send?phone=${fullPhone}&text=${encodeURIComponent(msgText)}`, '_blank');
        } else {
          const isMobile = typeof navigator !== 'undefined' && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
          const webUrl = isMobile
            ? `https://wa.me/${fullPhone}?text=${encodeURIComponent(msgText)}`
            : `https://web.whatsapp.com/send?phone=${fullPhone}&text=${encodeURIComponent(msgText)}`;
          window.open(webUrl, '_blank');
        }

        // Prompt salesperson to confirm actual sending in WhatsApp Web before logging in Audit Log
        const confirmToastId = messageId ? `wa-confirm-${messageId}` : `wa-confirm-${Date.now()}`;
        toast(
          <div className="space-y-2 py-1 text-slate-900 w-full max-w-[340px]">
            <div className="font-semibold text-xs flex items-center gap-1.5 text-emerald-800">
              <MessageSquare className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>WhatsApp Web opened for <strong>{targetLead?.name || 'Lead'}</strong></span>
            </div>
            <p className="text-[11px] text-slate-600 leading-tight">
              Did you send the message inside WhatsApp? Confirm to log in CRM Audit Log:
            </p>
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={async () => {
                  toast.dismiss(confirmToastId);
                  await handleConfirmWhatsAppStatus(messageId, 'sent', targetLead);
                }}
                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-bold text-xs shadow-xs transition-colors cursor-pointer"
              >
                ✓ Yes, Sent
              </button>
              <button
                type="button"
                onClick={async () => {
                  toast.dismiss(confirmToastId);
                  await handleConfirmWhatsAppStatus(messageId, 'failed', targetLead);
                }}
                className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs transition-colors cursor-pointer"
              >
                ✕ Cancel / Failed
              </button>
            </div>
          </div>,
          { duration: 25000, id: confirmToastId }
        );
      }
    } catch (err) {
      console.error('Failed to send WhatsApp message', err);
      toast.error(err.response?.data?.detail || 'Failed to dispatch WhatsApp message');
    } finally {
      setWaSending(false);
    }
  };

  const handleConfirmWhatsAppStatus = async (messageId, status, leadObj) => {
    const targetMsgId = messageId || (typeof viewingWaMessage === 'object' ? (viewingWaMessage?.id || viewingWaMessage?._id) : null);
    if (!targetMsgId) return;
    try {
      await axios.post(`${API}/crm/whatsapp/confirm-status`, {
        id: targetMsgId,
        status,
        lead_id: leadObj?.id,
        contact_name: leadObj?.name
      }, getAuthHeader());

      if (status === 'sent') {
        toast.success(`WhatsApp message confirmed sent & logged in CRM Audit Log for ${leadObj?.name || 'client'}!`);
      } else {
        toast.info(`WhatsApp message marked as failed/cancelled. Excluded from Audit Log.`);
      }

      setViewingWaMessage((prev) => (prev && (prev.id === targetMsgId || prev._id === targetMsgId)) ? { ...prev, status, confirmed_at: new Date().toISOString() } : prev);

      const targetLeadId = leadObj?.id || selectedLead?.id;
      if (targetLeadId) {
        loadLeadWhatsApp(targetLeadId, false);
        loadLeadTimeline(targetLeadId);
      }
      loadWhatsAppInbox();
      fetchAllCRMData();
    } catch (err) {
      console.error('Failed to update WhatsApp confirmation status', err);
      toast.error('Could not update WhatsApp delivery status');
    }
  };

  const handleSendWhatsAppSubmit = async () => {
    await handleSendWhatsAppMessage({ lead: selectedLead, text: waMessage, mode: 'web', template_name: selectedWaTemplate });
  };

  // ────────────────────────────────────────────────────────────
  // AI SALES COMMUNICATION ASSISTANT (WhatsApp & Live Calls)
  // ────────────────────────────────────────────────────────────
  const handleGenerateAiWaReply = async (intent = 'reply_client', customPrompt = '') => {
    if (!selectedLead) {
      toast.error('Please select a lead first');
      return;
    }
    setAiWaLoading(true);
    setShowAiWaPanel(true);
    try {
      // Find latest client message from conversation history if available
      const lastInbound = Array.isArray(leadWhatsApp)
        ? [...leadWhatsApp].reverse().find(m => m.direction === 'inbound' || m.sender === 'client' || m.from_client)
        : null;
      const inboundText = lastInbound?.message || lastInbound?.text || '';

      const queryText = customPrompt || inboundText || `Client inquiring about immigration programs for ${selectedLead.interested_country || selectedLead.country || 'Canada'}`;

      const res = await axios.post(`${API}/crm/ai/suggest-reply`, {
        channel: 'whatsapp',
        intent_type: intent,
        client_message: queryText,
        lead_id: selectedLead.id,
        target_country: selectedLead.interested_country || selectedLead.country,
        service_interested: selectedLead.service || selectedLead.interested_program,
        lead_context: {
          name: selectedLead.name,
          phone: selectedLead.phone,
          email: selectedLead.email,
          country: selectedLead.interested_country || selectedLead.country,
          service: selectedLead.service || selectedLead.interested_program,
          sales_rep_name: currentUser?.name || 'LEAMSS Consultant'
        }
      }, getAuthHeader());

      if (res.data?.success) {
        const replyText = res.data.suggested_text || res.data.reply_text || '';
        setAiWaSuggestion(replyText);
        setAiWaTalkingPoints(res.data.talking_points || []);
        setAiWaMatchedProduct(res.data.product_matched || null);
        toast.success('AI reply suggested based on Product Master!');
      } else {
        toast.error('Could not generate AI reply');
      }
    } catch (err) {
      console.error('Error generating AI WhatsApp reply:', err);
      toast.error(err.response?.data?.detail || 'Failed to generate AI reply');
    } finally {
      setAiWaLoading(false);
    }
  };

  const handleAskCallCopilot = async (customQuestion = '') => {
    const activeLead = callLead || selectedLead;
    if (!activeLead) {
      toast.error('No active lead in call');
      return;
    }
    const q = (customQuestion || aiCallQuery || '').trim();
    if (!q) {
      toast.error('Please enter a question or select a quick topic');
      return;
    }
    setAiCallLoading(true);
    try {
      const res = await axios.post(`${API}/crm/ai/suggest-reply`, {
        channel: 'live_call',
        intent_type: 'live_qa',
        client_message: q,
        lead_id: activeLead.id,
        target_country: activeLead.interested_country || activeLead.country,
        service_interested: activeLead.service || activeLead.interested_program,
        lead_context: {
          name: activeLead.name,
          phone: activeLead.phone,
          country: activeLead.interested_country || activeLead.country,
          service: activeLead.service || activeLead.interested_program,
          sales_rep_name: currentUser?.name || 'LEAMSS Consultant'
        }
      }, getAuthHeader());

      if (res.data?.success) {
        setAiCallSpeakingScript(res.data.speaking_script || res.data.suggested_text || res.data.reply_text || '');
        setAiCallTalkingPoints(res.data.talking_points || []);
        toast.success('Live call copilot answer ready!');
      } else {
        toast.error('Could not fetch copilot answer');
      }
    } catch (err) {
      console.error('Error in Call Copilot:', err);
      toast.error(err.response?.data?.detail || 'Copilot query failed');
    } finally {
      setAiCallLoading(false);
    }
  };

  // ────────────────────────────────────────────────────────────
  // EMAIL TEMPLATE MERGING & REAL SENDING
  // ────────────────────────────────────────────────────────────
  const loadEmailTemplates = async () => {
    try {
      const [res, statusRes] = await Promise.all([
        axios.get(`${API}/crm/emails/templates`, getAuthHeader()),
        axios.get(`${API}/crm/emails/service-status`, getAuthHeader()).catch(() => ({ data: null }))
      ]);
      setEmailTemplates(res.data || []);
      if (statusRes && statusRes.data) setEmailServiceStatus(statusRes.data);
    } catch (e) {
      console.error('Failed to load email templates', e);
    }
  };

  useEffect(() => {
    loadEmailTemplates();
  }, []);

  const loadMyMailbox = async () => {
    try {
      const res = await axios.get(`${API}/crm/emails/my-mailbox`, getAuthHeader());
      if (res.data) {
        setMailboxForm({
          smtp_host: res.data.smtp_host || 'smtp.gmail.com',
          smtp_port: res.data.smtp_port || 587,
          smtp_user: res.data.smtp_user || currentUser?.email || '',
          smtp_pass: '',
          sender_name: res.data.sender_name || currentUser?.name || '',
          sender_email: res.data.sender_email || res.data.email || currentUser?.email || '',
        });
      }
    } catch (e) {
      console.error('Failed to load mailbox config', e);
    }
  };

  const handleTestMailbox = async () => {
    setTestingMailbox(true);
    setMailboxTestResult(null);
    try {
      const res = await axios.post(`${API}/crm/emails/my-mailbox/test`, mailboxForm, getAuthHeader());
      if (res.data.success) {
        setMailboxTestResult({ success: true, message: res.data.message });
        toast.success(res.data.message || 'SMTP Connection & Login Successful!');
      } else {
        setMailboxTestResult({ success: false, message: res.data.error || 'Authentication failed' });
        toast.error(res.data.error || 'SMTP Connection Failed');
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Failed to test mailbox';
      setMailboxTestResult({ success: false, message: msg });
      toast.error(msg);
    } finally {
      setTestingMailbox(false);
    }
  };

  const handleSaveMailbox = async () => {
    setSavingMailbox(true);
    try {
      const res = await axios.put(`${API}/crm/emails/my-mailbox`, mailboxForm, getAuthHeader());
      toast.success(res.data.message || 'Mailbox saved successfully!');
      setShowMailboxModal(false);
      loadEmailTemplates();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save mailbox settings');
    } finally {
      setSavingMailbox(false);
    }
  };

  const loadUserSignature = async () => {
    try {
      setLoadingSig(true);
      const res = await axios.get(`${API}/crm/emails/signature`, getAuthHeader());
      if (res.data?.signature) {
        setSignatureHtml(res.data.signature);
        setIsCustomSig(Boolean(res.data.is_custom));
      }
    } catch (e) {
      console.error('Failed loading signature in CRM:', e);
    } finally {
      setLoadingSig(false);
    }
  };

  const handleSaveSignatureInSettings = async (overrideHtml = null) => {
    const sigToSave = overrideHtml !== null ? overrideHtml : signatureHtml;
    try {
      setSavingSig(true);
      const res = await axios.put(`${API}/crm/emails/signature`, { signature: sigToSave }, getAuthHeader());
      const saved = res.data?.signature || sigToSave;
      setSignatureHtml(saved);
      setIsCustomSig(true);
      toast.success(res.data?.message || 'Default email signature updated successfully!');
    } catch (e) {
      toast.error('Failed saving default signature');
    } finally {
      setSavingSig(false);
    }
  };

  const interpolateTemplate = (text, lead, consultantName) => {
    if (!text || !lead) return text || '';
    const nowStr = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    const countryVal = lead.country_of_interest || lead.country || lead.interested_country || 'Australia';
    const programVal = lead.interested_program || lead.service_interested || lead.visa_type || 'General Skilled Migration';
    return text
      .replace(/\{\{?(client_name|name)\}?\}/gi, lead.name || 'Valued Client')
      .replace(/\{\{?(client_email|email)\}?\}/gi, lead.email || '')
      .replace(/\{\{?(client_phone|phone)\}?\}/gi, lead.phone || '')
      .replace(/\{\{?(sales_person|consultant_name)\}?\}/gi, consultantName || 'LEAMSS Immigration Advisor')
      .replace(/\{\{?country\}?\}/gi, countryVal)
      .replace(/\{\{?(program|visa_type|service)\}?\}/gi, programVal)
      .replace(/\{\{?date\}?\}/gi, nowStr);
  };

  const handleOpenEmailModal = (replySubject = '', replyBody = '', customThreadId = null, overrideLead = null) => {
    const cleanSubject = (typeof replySubject === 'string') ? replySubject : '';
    const cleanBody = (typeof replyBody === 'string') ? replyBody : (overrideLead?.bodyHtml || '');
    const cleanThreadId = (typeof customThreadId === 'string') ? customThreadId : null;
    const targetLead = (overrideLead && typeof overrideLead === 'object' && !overrideLead.nativeEvent) ? overrideLead : selectedLead;
    if (overrideLead && typeof overrideLead === 'object' && !overrideLead.nativeEvent) {
      setSelectedLead(overrideLead);
    }
    if (targetLead?.email) {
      setRecipientEmail(targetLead.email);
    } else {
      setRecipientEmail('');
    }
    loadEmailTemplates();
    setSelectedTemplateId('');
    setEmailNotifyByEmail(false);
    setEmailCc('');
    setShowCcField(false);
    setEmailData({
      subject: cleanSubject,
      body_html: cleanBody,
      thread_id: cleanThreadId || undefined,
      attach_resume: overrideLead?.attach_resume ?? !!targetLead?.resume_file_id,
      resume_file_id: overrideLead?.resume_file_id || targetLead?.resume_file_id,
    });
    setShowEmailModal(true);
  };

  const handleResumeFileUpload = async (lead, file) => {
    if (!file) return;
    if (file.size > 15 * 1024 * 1024) {
      toast.error('Resume file exceeds maximum limit of 15MB');
      return;
    }
    const targetLeadId = lead?.id || lead?._id || lead?.lead_number;
    if (!targetLeadId) {
      toast.error('Cannot identify lead record ID');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);

    const toastId = toast.loading('Uploading and synchronizing resume...');
    try {
      const res = await axios.post(`${API}/leads/${targetLeadId}/resume`, formData, {
        headers: {
          ...getAuthHeader().headers,
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success(res.data.message || 'Resume uploaded successfully', { id: toastId });

      const updatedLead = {
        ...lead,
        resume_file_id: res.data.resume_file_id,
        resume_filename: res.data.resume_filename || file.name,
        resume_url: res.data.resume_url || `/cockpit/resume/${res.data.resume_file_id}`,
        resume_uploaded: true,
      };

      setLeads((prev) => prev.map((l) => ((l.id === lead.id || l._id === lead._id) ? updatedLead : l)));
      if (selectedLead && (selectedLead.id === lead.id || selectedLead._id === lead._id)) {
        setSelectedLead(updatedLead);
      }
      setResumePreviewModal((prev) => {
        if (prev.open && (prev.lead?.id === lead.id || prev.lead?._id === lead._id)) {
          return {
            ...prev,
            lead: updatedLead,
            resumeUrl: `${API}/cockpit/resume/${res.data.resume_file_id}?t=${Date.now()}`,
            filename: res.data.resume_filename || file.name,
          };
        }
        return prev;
      });
    } catch (err) {
      console.error('Error uploading resume:', err);
      toast.error(err.response?.data?.detail || err.message || 'Failed to upload resume', { id: toastId });
    }
  };

  const handlePreAssessmentReportUpload = async (lead, file) => {
    if (!file) return;
    if (file.size > 15 * 1024 * 1024) {
      toast.error('Pre-Assessment Report exceeds maximum limit of 15MB');
      return;
    }
    const targetLeadId = lead?.id || lead?._id || lead?.lead_number;
    if (!targetLeadId) {
      toast.error('Cannot identify lead record ID');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);

    const toastId = toast.loading('Uploading and attaching Pre-Assessment Report...');
    try {
      const res = await axios.post(`${API}/leads/${targetLeadId}/pre-assessment-report`, formData, {
        headers: {
          ...getAuthHeader().headers,
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success(res.data.message || 'Pre-Assessment Report attached successfully', { id: toastId });

      const updatedLead = {
        ...lead,
        assessment_report_file_id: res.data.assessment_report_file_id,
        assessment_report_filename: res.data.assessment_report_filename || file.name,
        assessment_report_url: res.data.report_url || `/cockpit/resume/${res.data.assessment_report_file_id}`,
        pre_assessment_report_url: res.data.report_url || `/cockpit/resume/${res.data.assessment_report_file_id}`,
        has_pre_assessment_report: true,
        report_generated: true,
      };

      setLeads((prev) => prev.map((l) => ((l.id === lead.id || l._id === lead._id) ? updatedLead : l)));
      if (selectedLead && (selectedLead.id === lead.id || selectedLead._id === lead._id)) {
        setSelectedLead(updatedLead);
      }
      setReportPreviewModal((prev) => {
        if (prev.open && (prev.lead?.id === lead.id || prev.lead?._id === lead._id)) {
          return {
            ...prev,
            lead: updatedLead,
            reportUrl: `${API}/cockpit/resume/${res.data.assessment_report_file_id}?t=${Date.now()}`,
            filename: res.data.assessment_report_filename || file.name,
          };
        }
        return prev;
      });
    } catch (err) {
      console.error('Error uploading pre-assessment report:', err);
      toast.error(err.response?.data?.detail || err.message || 'Failed to upload pre-assessment report', { id: toastId });
    }
  };

  const handleForwardLeadByEmail = (lead) => {
    if (!lead) return;
    const resumeUrl = lead.resume_file_id ? `${window.location.origin}/cockpit/resume/${lead.resume_file_id}` : '';
    const subject = `Forwarding Candidate Profile: ${lead.name || 'Candidate'} - ${lead.service_interested || 'Immigration'}`;
    const bodyHtml = `
      <div style="font-family: Arial, sans-serif; font-size: 14px; color: #1e293b; max-width: 600px;">
        <h3 style="color: #047857; margin-bottom: 8px;">Candidate Profile Summary</h3>
        <p>Please find below the candidate profile details${lead.resume_file_id ? ' and attached resume' : ''}:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px;">
          <tr style="background: #f8fafc;"><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold; width: 35%;">Name</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.name || '—'}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">Phone</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.phone || '—'}</td></tr>
          <tr style="background: #f8fafc;"><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">Email</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.email || '—'}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">Occupation</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.occupation || '—'}</td></tr>
          <tr style="background: #f8fafc;"><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">Qualification</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.latest_qualification || lead.qualification || '—'}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">Experience</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.total_work_experience || lead.experience || '—'}</td></tr>
          <tr style="background: #f8fafc;"><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">Target Country</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.country_of_interest || lead.country || '—'}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">Service Interested</td><td style="padding: 8px; border: 1px solid #e2e8f0;">${lead.service_interested || '—'}</td></tr>
          ${lead.resume_file_id ? `<tr style="background: #ecfdf5;"><td style="padding: 8px; border: 1px solid #a7f3d0; font-weight: bold; color: #047857;">Attached Resume</td><td style="padding: 8px; border: 1px solid #a7f3d0;"><a href="${resumeUrl}" style="color: #047857; font-weight: bold;">${lead.resume_filename || 'Download Candidate Resume'}</a></td></tr>` : ''}
        </table>
        <p style="font-size: 12px; color: #64748b;">Forwarded by Sales Consultant · LEAMSS Portal</p>
      </div>
    `;
    handleOpenEmailModal('', subject, null, {
      ...lead,
      bodyHtml,
      attach_resume: !!lead.resume_file_id,
      resume_file_id: lead.resume_file_id,
      resume_filename: lead.resume_filename,
    });
  };

  const handleForwardLeadByWhatsApp = (lead) => {
    if (!lead) return;
    const resumeUrl = lead.resume_file_id
      ? `${window.location.origin}/cockpit/resume/${lead.resume_file_id}`
      : (lead.resume_url ? `${window.location.origin}${lead.resume_url}` : '');

    const text = `*LEAMSS Candidate Profile Summary*
*Name:* ${lead.name || '—'}
*Phone:* ${lead.phone || '—'}
*Email:* ${lead.email || '—'}
*Target Country:* ${lead.country_of_interest || lead.country || 'Canada'}
*Service:* ${lead.service_interested || 'Immigration Consulting'}
*Qualification:* ${lead.latest_qualification || lead.qualification || '—'}
*Experience:* ${lead.total_work_experience || lead.experience || '—'}
${resumeUrl ? `\n📄 *Attached Resume:* ${resumeUrl}` : '\n⚠️ *Resume:* Not yet attached'}

_Forwarded via LEAMSS CRM_`;

    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`, '_blank');
  };

  const handleSelectEmailTemplate = (tplId) => {
    setSelectedTemplateId(tplId);
    const tpl = emailTemplates.find(t => t.id === tplId);
    if (!tpl || !selectedLead) return;
    const consultantName = currentUser?.name || 'LEAMSS Immigration Advisor';
    const parsedSubj = interpolateTemplate(tpl.subject || '', selectedLead, consultantName);
    const parsedBody = interpolateTemplate(tpl.body || tpl.body_html || '', selectedLead, consultantName);
    setEmailData(prev => ({
      ...prev,
      subject: parsedSubj,
      body_html: parsedBody
    }));
  };

  const loadLeadEmails = async (leadId, customSort = null) => {
    if (!leadId) return;
    const sortParam = customSort || emailSortOrder;
    setEmailsLoading(true);
    try {
      const res = await axios.get(`${API}/crm/emails?lead_id=${leadId}&sort=${sortParam}`, getAuthHeader());
      setLeadEmails(res.data || []);
    } catch (e) {
      console.error('Error loading lead emails', e);
    } finally {
      setEmailsLoading(false);
    }
  };

  const handleSyncMailbox = async (targetLeadId = null, targetEmail = null, silent = false) => {
    const leadId = targetLeadId || selectedLead?.id;
    const contactEmail = targetEmail || selectedLead?.email;
    setSyncingMailbox(true);
    try {
      const res = await axios.post(`${API}/crm/emails/sync`, {
        lead_id: leadId || undefined,
        contact_email: contactEmail || undefined
      }, getAuthHeader());

      const count = res.data?.total_synced || 0;
      if (!silent) {
        if (count > 0) {
          toast.success(res.data?.message || `Synced ${count} new email(s) from your mailbox!`);
        } else {
          toast.info(res.data?.message || 'Mailbox is up to date. No new replies found.');
        }
      }
      if (leadId) {
        await loadLeadEmails(leadId);
        loadLeadTimeline(leadId);
      }
      loadAllEmails();
    } catch (err) {
      if (!silent) {
        console.error('Mailbox sync error', err);
        toast.error(err.response?.data?.detail || 'Failed to sync mailbox via IMAP');
      }
    } finally {
      setSyncingMailbox(false);
    }
  };

  const handleSendEmailSubmit = async () => {
    const to = (recipientEmail || selectedLead?.email || '').trim();
    if (!to || !to.includes('@')) {
      toast.error('Please enter a valid recipient email address');
      return;
    }
    const cleanSubject = typeof emailData?.subject === 'string' ? emailData.subject.trim() : String(emailData?.subject || '').trim();
    if (!cleanSubject) {
      toast.error('Please enter an email subject');
      return;
    }
    const cleanBody = typeof emailData?.body_html === 'string' ? emailData.body_html.trim() : String(emailData?.body_html || '').trim();
    if (!cleanBody) {
      toast.error('Please write an email message');
      return;
    }

    setEmailSending(true);
    try {
      const userEmail = (currentUser?.email || '').toLowerCase().trim();
      let effectiveCc = (emailCc || '').trim();
      if (emailNotifyByEmail) {
        if (userEmail) {
          const list = effectiveCc ? effectiveCc.split(',').map(s => s.trim().toLowerCase()) : [];
          if (!list.includes(userEmail)) {
            effectiveCc = effectiveCc ? `${effectiveCc}, ${currentUser.email}` : currentUser.email;
          }
        }
      } else {
        if (effectiveCc && userEmail) {
          effectiveCc = effectiveCc
            .split(',')
            .map(s => s.trim())
            .filter(s => s.toLowerCase() !== userEmail)
            .join(', ');
        }
      }
      effectiveCc = effectiveCc.trim() || undefined;

      const targetLeadId = selectedLead?.id;
      const targetContactName = selectedLead?.name || to.split('@')[0];

      const res = await axios.post(`${API}/crm/emails/send`, {
        lead_id: targetLeadId,
        to_email: to,
        contact_name: targetContactName,
        subject: cleanSubject,
        body_html: cleanBody,
        template_id: selectedTemplateId || null,
        thread_id: emailData?.thread_id || undefined,
        notify_by_email: emailNotifyByEmail,
        cc: effectiveCc,
        attach_resume: emailData?.attach_resume ?? !!selectedLead?.resume_file_id,
        resume_file_id: emailData?.resume_file_id || selectedLead?.resume_file_id,
      }, getAuthHeader());

      const status = res.data.status;
      if (status === 'delivered') {
        toast.success(`Email delivered to ${to} from your sales mailbox`);
      } else if (status === 'pending_configuration') {
        toast.success(`Email saved to CRM timeline. (Click 'Configure My Mailbox' to enter your App Password for live sending)`);
      } else if (status === 'failed') {
        const rawErr = (res.data.delivery_error || '').toLowerCase();
        if (rawErr.includes('connection lost') || rawErr.includes('eof') || rawErr.includes('disconnect')) {
          toast.error('Mailbox authentication failed: Google rejected the App Password. Please check Mailbox Settings.');
        } else {
          toast.error(res.data.delivery_error || 'Email recorded in CRM, but mailbox authentication failed. Please check your App Password.');
        }
      } else {
        if (res.data.mailbox_warning) {
          toast.success(`Email sent & recorded in CRM timeline. (Check Mailbox Settings for external Gmail dispatch)`);
        } else {
          toast.success('Email sent and logged successfully');
        }
      }

      setShowEmailModal(false);
      setEmailData({ subject: '', body_html: '' });
      setSelectedTemplateId('');
      setEmailNotifyByEmail(false);
      setEmailCc('');
      setShowCcField(false);
      loadLeadTimeline(selectedLead.id);
      loadLeadEmails(selectedLead.id);
      loadAllEmails();
      fetchAllCRMData();
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || '';
      if (detail.toLowerCase().includes('connection lost') || detail.toLowerCase().includes('eof')) {
        toast.error('Mailbox authentication failed: Google rejected the App Password. Please check Mailbox Settings.');
      } else {
        toast.error(detail || 'Failed to send email');
      }
    } finally {
      setEmailSending(false);
    }
  };

  const handleQuickReplySubmit = async () => {
    if (!selectedLead) return;
    const to = (selectedLead.email || '').trim();
    if (!to || !to.includes('@')) {
      toast.error('Client has no valid email address registered');
      return;
    }
    const text = quickReplyText.trim();
    if (!text) {
      toast.error('Please enter a reply message');
      return;
    }

    // Determine subject and thread_id from latest email in leadEmails
    const sortedByDate = [...leadEmails].sort((a, b) => new Date(b.created_at || b.sent_at || 0) - new Date(a.created_at || a.sent_at || 0));
    const latestEmail = sortedByDate.length > 0 ? sortedByDate[0] : null;
    let replySubject = 'Immigration Consultation Follow-up';
    let threadId = null;
    let inReplyTo = null;

    if (latestEmail) {
      threadId = latestEmail.thread_id || null;
      inReplyTo = latestEmail.message_id || null;
      replySubject = latestEmail.subject || replySubject;
      if (!replySubject.toLowerCase().startsWith('re:')) {
        replySubject = `Re: ${replySubject}`;
      }
    }

    setSendingQuickReply(true);
    try {
      const res = await axios.post(`${API}/crm/emails/send`, {
        lead_id: selectedLead.id,
        to_email: to,
        contact_name: selectedLead.name,
        subject: replySubject,
        body_html: text,
        thread_id: threadId,
        in_reply_to: inReplyTo,
        notify_by_email: quickReplyNotifyByEmail,
        cc: quickReplyNotifyByEmail && currentUser?.email ? currentUser.email : undefined
      }, getAuthHeader());

      if (res.data.status === 'delivered') {
        toast.success(`Reply sent and delivered to ${to}`);
      } else {
        toast.success('Reply sent and logged to CRM');
      }

      setQuickReplyText('');
      setQuickReplyNotifyByEmail(false);
      loadLeadEmails(selectedLead.id);
      loadLeadTimeline(selectedLead.id);
      loadAllEmails();
      fetchAllCRMData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reply');
    } finally {
      setSendingQuickReply(false);
    }
  };

  const handleSendEmailCenterQuickReply = async (conv) => {
    if (!conv) return;
    const text = emailCenterQuickReplyText.trim();
    if (!text) {
      toast.error('Please enter a reply message');
      return;
    }

    const to = conv.email;
    const latest = conv.latestEmail;
    let replySubject = conv.latestSubject || 'Immigration Consultation Follow-up';
    if (!replySubject.toLowerCase().startsWith('re:')) {
      replySubject = `Re: ${replySubject}`;
    }

    const threadId = latest?.thread_id || undefined;
    const inReplyTo = latest?.message_id || undefined;
    const leadId = conv.lead?.id || conv.lead_id || undefined;

    setSendingEmailCenterReply(true);
    try {
      const userEmail = (currentUser?.email || '').toLowerCase().trim();
      let effectiveCc = undefined;
      if (emailCenterQuickNotify && userEmail) {
        effectiveCc = userEmail;
      }

      const res = await axios.post(`${API}/crm/emails/send`, {
        lead_id: leadId,
        to_email: to,
        contact_name: conv.name,
        subject: replySubject,
        body_html: text,
        thread_id: threadId,
        in_reply_to: inReplyTo,
        notify_by_email: emailCenterQuickNotify,
        cc: effectiveCc
      }, getAuthHeader());

      if (res.data.status === 'delivered') {
        toast.success(`Reply delivered to ${to} from your sales mailbox`);
      } else {
        toast.success('Reply sent and logged to CRM');
      }

      setEmailCenterQuickReplyText('');
      setEmailCenterQuickNotify(false);
      loadAllEmails();
      if (leadId) {
        loadLeadEmails(leadId);
        loadLeadTimeline(leadId);
      }
      fetchAllCRMData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reply');
    } finally {
      setSendingEmailCenterReply(false);
    }
  };

  const handleSimulateReply = async (emailId) => {
    if (!selectedLead) return;
    setSimulatingReply(true);
    try {
      const res = await axios.post(`${API}/crm/emails/simulate-reply`, {
        lead_id: selectedLead.id,
        email_id: emailId || null,
        reply_subject: emailData.subject ? `Re: ${emailData.subject}` : `Re: Australia Migration Consultation`,
        reply_body: `Hi, thank you for sending this information. I have reviewed the requirements and wish to proceed. When can we discuss the next steps?`
      }, getAuthHeader());

      toast.success(`Client reply captured into thread from ${res.data.reply.from_email}`);
      loadLeadTimeline(selectedLead.id);
      loadLeadEmails(selectedLead.id);
      fetchAllCRMData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to simulate client reply');
    } finally {
      setSimulatingReply(false);
    }
  };

  // Quick Action Schedule Follow-up
  const handleScheduleFollowUpSubmit = async () => {
    if (!selectedLead || !followUpData.scheduled_at) {
      toast.error('Follow-up date/time is required');
      return;
    }
    try {
      await axios.post(`${API}/crm/follow-ups`, {
        lead_id: selectedLead.id,
        type: followUpData.type,
        priority: followUpData.priority,
        scheduled_at: followUpData.scheduled_at,
        notes: followUpData.notes,
        reminder_before: followUpData.reminder_before
      }, getAuthHeader());
      toast.success('Follow-up scheduled successfully');
      setShowFollowUpModal(false);
      loadLeadTimeline(selectedLead.id);
      fetchAllCRMData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to schedule follow-up');
    }
  };

  // Quick Action Convert to Client
  const handleConvertLeadSubmit = async () => {
    if (!selectedLead) return;
    try {
      const res = await axios.post(`${API}/leads/${selectedLead.id}/convert-to-client`, convertData, getAuthHeader());
      toast.success(res.data.message || 'Lead converted to Client successfully');
      setShowConvertModal(false);
      loadLeadTimeline(selectedLead.id);
      fetchAllCRMData();
      // Auto open handover prompt
      setShowHandoverModal(true);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Conversion failed');
    }
  };

  // Quick Action Case Manager Handover
  const handleCaseHandoverSubmit = async () => {
    if (!selectedLead) return;
    try {
      const res = await axios.post(`${API}/leads/${selectedLead.id}/case-manager-handover`, handoverData, getAuthHeader());
      toast.success(res.data.message || 'Case handed over to Case Manager');
      setShowHandoverModal(false);
      loadLeadTimeline(selectedLead.id);
      fetchAllCRMData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Handover failed');
    }
  };

  // Quick Action Record Payment
  const handleRecordPaymentSubmit = async () => {
    if (!selectedLead) return;
    try {
      await axios.post(`${API}/crm/payments`, {
        lead_id: selectedLead.id,
        client_name: selectedLead.name,
        package_name: paymentData.package_name,
        package_price: paymentData.package_price,
        discount: paymentData.discount,
        paid_amount: paymentData.paid_amount,
        payment_method: paymentData.payment_method,
        notes: paymentData.notes
      }, getAuthHeader());
      toast.success('Payment recorded and synced with Deal');
      setShowPaymentModal(false);
      loadLeadTimeline(selectedLead.id);
      fetchAllCRMData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Payment record failed');
    }
  };

  // Bulk Excel/CSV File Selection & Preview
  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImportFile(file);
      setImportResults(null);
      setPreviewLoading(true);
      try {
        const fd = new FormData();
        fd.append('file', file);
        const res = await axios.post(`${API}/leads/bulk-import-preview`, fd, {
          ...getAuthHeader(),
          headers: {
            ...getAuthHeader().headers,
            'Content-Type': 'multipart/form-data'
          }
        });
        const total = res.data.total_rows || 0;
        setFilePreviewStats({
          total_rows: total,
          headers: res.data.headers || [],
          filename: res.data.filename || file.name
        });
        if (total > 0) {
          setRowRanges([
            { id: `rng_${Date.now()}`, from_row: 1, to_row: Math.min(100, total), sales_person_id: '' }
          ]);
        }
      } catch (err) {
        console.error('File preview error:', err);
        setFilePreviewStats({ total_rows: 0, headers: [], filename: file.name });
      } finally {
        setPreviewLoading(false);
      }
    }
  };

  const handleCsvTextChange = (text) => {
    setImportCsvText(text);
    setImportResults(null);
    const lines = text.trim().split('\n').filter(l => l.trim().length > 0);
    const dataRowsCount = Math.max(0, lines.length - 1);
    setFilePreviewStats({
      total_rows: dataRowsCount,
      headers: lines.length > 0 ? lines[0].split(',').map(h => h.trim()) : [],
      filename: 'pasted_data.csv'
    });
    if (dataRowsCount > 0 && rowRanges.length === 1 && (rowRanges[0].to_row === 100 || rowRanges[0].to_row === 0)) {
      setRowRanges([
        { id: `rng_${Date.now()}`, from_row: 1, to_row: Math.min(100, dataRowsCount), sales_person_id: '' }
      ]);
    }
  };

  // Row Range Management
  const addRangeRow = () => {
    const total = filePreviewStats.total_rows || 1000;
    let nextFrom = 1;
    if (rowRanges.length > 0) {
      const last = rowRanges[rowRanges.length - 1];
      nextFrom = (parseInt(last.to_row, 10) || 0) + 1;
    }
    const nextTo = Math.min(total, nextFrom + 99);
    setRowRanges([
      ...rowRanges,
      { id: `rng_${Date.now()}_${rowRanges.length}`, from_row: nextFrom, to_row: nextTo, sales_person_id: '' }
    ]);
  };

  const removeRangeRow = (id) => {
    if (rowRanges.length <= 1) {
      toast.info('At least one row range is required');
      return;
    }
    setRowRanges(rowRanges.filter(r => r.id !== id));
  };

  const updateRangeRow = (id, field, value) => {
    setRowRanges(rowRanges.map(r => {
      if (r.id === id) {
        return { ...r, [field]: value };
      }
      return r;
    }));
  };

  // Auto Split / Divide Tools
  const handleAutoSplitEqually = () => {
    const total = filePreviewStats.total_rows || 0;
    if (total <= 0) {
      toast.error('No data rows detected. Please upload or paste leads data first.');
      return;
    }
    if (splitSelectedReps.length === 0) {
      toast.error('Please select at least one Sales Person to divide leads.');
      return;
    }
    const count = splitSelectedReps.length;
    const baseSize = Math.floor(total / count);
    let remainder = total % count;
    let currentFrom = 1;
    const newRanges = [];

    splitSelectedReps.forEach((repId, idx) => {
      const take = baseSize + (remainder > 0 ? 1 : 0);
      if (remainder > 0) remainder--;
      const toRow = Math.min(total, currentFrom + take - 1);
      if (currentFrom <= total) {
        newRanges.push({
          id: `rng_${Date.now()}_${idx}`,
          from_row: currentFrom,
          to_row: toRow,
          sales_person_id: repId
        });
        currentFrom = toRow + 1;
      }
    });

    setRowRanges(newRanges);
    toast.success(`Split ${total} leads equally across ${newRanges.length} Sales Persons!`);
  };

  const handleAutoSplitByBatchSize = () => {
    const total = filePreviewStats.total_rows || 0;
    if (total <= 0) {
      toast.error('No data rows detected. Please upload or paste leads data first.');
      return;
    }
    const size = parseInt(splitBatchSize, 10);
    if (!size || size <= 0) {
      toast.error('Please enter a valid batch size (e.g. 50 or 100).');
      return;
    }
    const newRanges = [];
    let currentFrom = 1;
    let batchIdx = 0;

    while (currentFrom <= total) {
      const toRow = Math.min(total, currentFrom + size - 1);
      newRanges.push({
        id: `rng_${Date.now()}_${batchIdx}`,
        from_row: currentFrom,
        to_row: toRow,
        sales_person_id: ''
      });
      currentFrom = toRow + 1;
      batchIdx++;
    }

    setRowRanges(newRanges);
    toast.success(`Created ${newRanges.length} batches of size ${size} for ${total} leads!`);
  };

  // Bulk Excel/CSV Import Submit (Admin Only)
  const handleBulkImportSubmit = async () => {
    if (importAssignmentMethod === 'row_ranges') {
      if (!rowRanges || rowRanges.length === 0) {
        toast.error('Please configure at least one row range');
        return;
      }
      for (let i = 0; i < rowRanges.length; i++) {
        const rng = rowRanges[i];
        const f = parseInt(rng.from_row, 10);
        const t = parseInt(rng.to_row, 10);
        if (!f || !t || f <= 0 || t < f) {
          toast.error(`Range #${i + 1} has invalid row bounds (${rng.from_row} to ${rng.to_row})`);
          return;
        }
        if (!rng.sales_person_id) {
          toast.error(`Please select a Sales Person for Range #${i + 1} (Rows ${f}–${t})`);
          return;
        }
      }
    }

    if (importMode === 'file') {
      if (!importFile) {
        toast.error('Please select an Excel (.xlsx/.xls) or CSV (.csv) file');
        return;
      }
      setImportUploading(true);
      try {
        const fd = new FormData();
        fd.append('file', importFile);
        fd.append('assignment_method', importAssignmentMethod);
        if (importSalesPersonId && importSalesPersonId !== 'all') {
          fd.append('sales_person_id', importSalesPersonId);
        }
        if (importAssignmentMethod === 'row_ranges') {
          fd.append('row_ranges', JSON.stringify(rowRanges.map(r => ({
            from_row: parseInt(r.from_row, 10),
            to_row: parseInt(r.to_row, 10),
            sales_person_id: r.sales_person_id
          }))));
        }

        const res = await axios.post(`${API}/leads/bulk-import-file`, fd, {
          ...getAuthHeader(),
          headers: {
            ...getAuthHeader().headers,
            'Content-Type': 'multipart/form-data'
          }
        });
        setImportResults(res.data);
        toast.success(`Imported ${res.data.imported_count} leads successfully!`);
        fetchAllCRMData();
      } catch (e) {
        toast.error(e.response?.data?.detail || 'Excel/CSV bulk import failed');
      } finally {
        setImportUploading(false);
      }
    } else {
      if (!importCsvText.trim()) {
        toast.error('Please enter CSV text data');
        return;
      }
      setImportUploading(true);
      try {
        const lines = importCsvText.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/[\s-]/g, '_'));
        const parsedRecords = [];

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i].trim()) continue;
          const vals = lines[i].split(',').map(v => v.trim());
          const row = {};
          headers.forEach((h, idx) => {
            row[h] = vals[idx] || '';
          });
          parsedRecords.push(row);
        }

        const payload = {
          records: parsedRecords,
          assignment_method: importAssignmentMethod,
          sales_person_id: importSalesPersonId !== 'all' ? importSalesPersonId : null
        };
        if (importAssignmentMethod === 'row_ranges') {
          payload.row_ranges = rowRanges.map(r => ({
            from_row: parseInt(r.from_row, 10),
            to_row: parseInt(r.to_row, 10),
            sales_person_id: r.sales_person_id
          }));
        }

        const res = await axios.post(`${API}/leads/bulk-import`, payload, getAuthHeader());
        setImportResults(res.data);
        toast.success(`Imported ${res.data.imported_count} leads successfully!`);
        fetchAllCRMData();
      } catch (e) {
        toast.error(e.response?.data?.detail || 'Bulk import failed');
      } finally {
        setImportUploading(false);
      }
    }
  };

  const handleDownloadTemplate = () => {
    const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(
      'name,phone,email,alternate_phone,country,service,budget,source,campaign,notes,occupation,experience,qualification,city,assigned_to\n' +
      'Rahul Verma,+919876543210,rahul.verma@example.com,+919876543211,Canada,Canada PR Express Entry,75000,Google Ads,Canada Spring 2026,High CRS candidate with IELTS 8.0,Software Engineer,5 Years,Bachelor of Technology,Delhi,\n' +
      'Priya Sharma,+919812345678,priya.sharma@example.com,,Australia,Subclass 189 Skilled Independent,60000,Referral,Direct Inbound,Ready to apply,Data Analyst,4 Years,Master of Science,Bangalore,\n' +
      'Vikram Singh,+919711223344,vikram.singh@example.com,,Germany,EU Blue Card,50000,Meta Ads,Tech Europe 2026,German B1 certified,Registered Nurse,6 Years,B.Sc Nursing,Mumbai,'
    );
    const link = document.createElement('a');
    link.setAttribute('href', csvContent);
    link.setAttribute('download', 'leamss_leads_import_template.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Stage change directly
  const handleStageChange = async (leadId, newStage) => {
    try {
      await axios.put(`${API}/leads/${leadId}`, { stage: newStage, status: newStage }, getAuthHeader());
      toast.success(`Lead moved to ${STAGE_MAP[newStage]?.label || newStage}`);
      if (selectedLead && selectedLead.id === leadId) {
        setSelectedLead(prev => ({ ...prev, stage: newStage, status: newStage }));
        loadLeadTimeline(leadId);
        loadLeadCalls(leadId);
        loadLeadWhatsApp(leadId);
        loadLeadEmails(leadId);
      }
      fetchAllCRMData();
    } catch (e) {
      toast.error('Failed to update stage');
    }
  };

  // Pipeline Bar Chart Data
  const chartData = useMemo(() => {
    return STAGES.map(s => ({
      name: s.label,
      count: stats.stages?.[s.key] || 0,
      fill: s.key === 'won' || s.key === 'converted' ? '#10b981' : s.key === 'lost' ? '#ef4444' : '#6366f1'
    }));
  }, [stats]);

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-800">
      
      {/* ──────────────────────────────────────────────────────────── */}
      {/* LEFT SIDEBAR NAVIGATION */}
      {/* ──────────────────────────────────────────────────────────── */}
      <aside className={`bg-white border-r border-slate-200 flex flex-col transition-all duration-300 z-30 ${sidebarOpen ? 'w-64' : 'w-20'}`}>
        
        {/* Logo & Role Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center font-bold text-lg shadow-sm">
              L
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="font-bold text-base text-slate-900 tracking-tight flex items-center gap-1.5">
                  LEAMSS <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold uppercase">CRM</span>
                </h1>
                <p className="text-xs text-slate-500 truncate max-w-[140px]">{currentUser?.name || 'Sales Consultant'}</p>
              </div>
            )}
          </div>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100">
            {sidebarOpen ? <ChevronLeft className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1 text-sm">
          
          {/* Main Dashboard */}
          <button
            onClick={() => setView('dashboard')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-colors ${view === 'dashboard' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <LayoutDashboard className={`w-5 h-5 ${view === 'dashboard' ? 'text-emerald-600' : 'text-slate-400'}`} />
            {sidebarOpen && <span>My CRM Dashboard</span>}
          </button>

          {/* Leads Section */}
          <div className="pt-2">
            {sidebarOpen && <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Lead Management</p>}
            <button
              onClick={() => { setView('table'); setStageFilter('all'); }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'table' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <div className="flex items-center gap-3">
                <ListChecks className="w-4 h-4 text-slate-400" />
                {sidebarOpen && <span>All Leads</span>}
              </div>
              {sidebarOpen && <Badge variant="secondary" className="text-xs">{leads.length}</Badge>}
            </button>

            <button
              onClick={() => setView('kanban')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'kanban' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <div className="flex items-center gap-3">
                <LayoutGrid className="w-4 h-4 text-slate-400" />
                {sidebarOpen && <span>Leads Board</span>}
              </div>
              {sidebarOpen && <Badge variant="secondary" className="text-xs">{leads.length}</Badge>}
            </button>

            <button
              onClick={() => { setView('table'); setStageFilter('converted'); }}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'table' && stageFilter === 'converted' ? 'bg-emerald-50 text-emerald-700 font-semibold border-l-2 border-emerald-500' : 'text-slate-600 hover:bg-slate-100'}`}
              data-testid="sidebar-converted-clients-btn"
            >
              <div className="flex items-center gap-3">
                <UserCheck className={`w-4 h-4 ${view === 'table' && stageFilter === 'converted' ? 'text-emerald-600' : 'text-emerald-500'}`} />
                {sidebarOpen && <span>Converted Clients</span>}
              </div>
              {sidebarOpen && (
                <Badge variant="secondary" className="text-xs bg-emerald-100 text-emerald-800">
                  {leads.filter(l => l.stage === 'converted' || l.status === 'converted' || l.converted || ['won', 'closed_won', 'case_created'].includes(String(l.stage || l.status || '').toLowerCase())).length}
                </Badge>
              )}
            </button>

            {/* Website Leads Expandable Category Tree (Ref Image 1 & 2) */}
            {isAdmin && (
              <div className="space-y-0.5">
                <button
                  onClick={() => {
                    setWebsiteMenuOpen(!websiteMenuOpen);
                    if (view !== 'website_leads') setView('website_leads');
                  }}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'website_leads' ? 'bg-sky-50 text-sky-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
                  data-testid="sidebar-website-leads-btn"
                >
                  <div className="flex items-center gap-3">
                    <Globe className={`w-4 h-4 ${view === 'website_leads' ? 'text-sky-600' : 'text-sky-500'}`} />
                    {sidebarOpen && <span>Website Leads</span>}
                  </div>
                  {sidebarOpen && (
                    <div className="flex items-center gap-1.5">
                      {websiteLeadsUnassignedCount > 0 && (
                        <Badge className="bg-amber-500 hover:bg-amber-600 text-white text-[10px] px-1.5 py-0" title="Unassigned website leads">
                          {websiteLeadsUnassignedCount}
                        </Badge>
                      )}
                      <Badge variant="secondary" className="text-xs bg-slate-100 text-slate-700">
                        {websiteLeadsCount}
                      </Badge>
                      <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${websiteMenuOpen ? '' : '-rotate-90'}`} />
                    </div>
                  )}
                </button>

                {/* Collapsible Category Sub-items in Exact Order */}
                {sidebarOpen && websiteMenuOpen && (
                  <div className="pl-4 pr-1 space-y-0.5 pt-0.5 border-l-2 border-slate-100 ml-4">
                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('all');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'all'
                          ? 'bg-sky-50 text-sky-800 font-semibold border-l-2 border-sky-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-sky-600 font-bold">↳</span>
                        <span>All Enquiries</span>
                      </div>
                      {websiteLeadsCount !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-sky-700 border border-sky-100">
                          {websiteLeadsCount}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('PR');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'PR'
                          ? 'bg-emerald-50 text-emerald-800 font-semibold border-l-2 border-emerald-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-emerald-600 font-bold">↳</span>
                        <span>PR Enquiries</span>
                      </div>
                      {websiteCategoriesData?.PR?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-emerald-700 border border-emerald-100">
                          {websiteCategoriesData.PR.count}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('TR');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'TR'
                          ? 'bg-indigo-50 text-indigo-800 font-semibold border-l-2 border-indigo-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-indigo-600 font-bold">↳</span>
                        <span>TR Enquiries</span>
                      </div>
                      {websiteCategoriesData?.TR?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-indigo-700 border border-indigo-100">
                          {websiteCategoriesData.TR.count}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('Work');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'Work'
                          ? 'bg-blue-50 text-blue-800 font-semibold border-l-2 border-blue-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-blue-600 font-bold">↳</span>
                        <span>Work Enquiries</span>
                      </div>
                      {websiteCategoriesData?.Work?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-blue-700 border border-blue-100">
                          {websiteCategoriesData.Work.count}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('Study');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'Study'
                          ? 'bg-purple-50 text-purple-800 font-semibold border-l-2 border-purple-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-purple-600 font-bold">↳</span>
                        <span>Study Enquiries</span>
                      </div>
                      {websiteCategoriesData?.Study?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-purple-700 border border-purple-100">
                          {websiteCategoriesData.Study.count}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('Tourist');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'Tourist'
                          ? 'bg-teal-50 text-teal-800 font-semibold border-l-2 border-teal-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-teal-600 font-bold">↳</span>
                        <span>Tourist Enquiries</span>
                      </div>
                      {websiteCategoriesData?.Tourist?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-teal-700 border border-teal-100">
                          {websiteCategoriesData.Tourist.count}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('Family');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'Family'
                          ? 'bg-rose-50 text-rose-800 font-semibold border-l-2 border-rose-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-rose-600 font-bold">↳</span>
                        <span>Family Enquiries</span>
                      </div>
                      {websiteCategoriesData?.Family?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-rose-700 border border-rose-100">
                          {websiteCategoriesData.Family.count}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('General');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'General'
                          ? 'bg-amber-50 text-amber-800 font-semibold border-l-2 border-amber-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-amber-600 font-bold">↳</span>
                        <span>General Enquiries</span>
                      </div>
                      {websiteCategoriesData?.General?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-amber-700 border border-amber-100">
                          {websiteCategoriesData.General.count}
                        </Badge>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        setView('website_leads');
                        setSelectedWebsiteCategory('Atlas');
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors ${
                        view === 'website_leads' && selectedWebsiteCategory === 'Atlas'
                          ? 'bg-cyan-50 text-cyan-800 font-semibold border-l-2 border-cyan-500'
                          : 'text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-cyan-600 font-bold">↳</span>
                        <span>Atlas Enquiries</span>
                      </div>
                      {websiteCategoriesData?.Atlas?.count !== undefined && (
                        <Badge variant="secondary" className="text-[10px] px-1 py-0 bg-white text-cyan-700 border border-cyan-100">
                          {websiteCategoriesData.Atlas.count}
                        </Badge>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}

            {isAdmin && (
              <button
                onClick={() => { setShowImportModal(true); setImportResults(null); setImportFile(null); }}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
                data-testid="admin-bulk-import-sidebar-btn"
              >
                <Upload className="w-4 h-4 text-emerald-600" />
                {sidebarOpen && <span>Bulk Import</span>}
              </button>
            )}

            {isAdmin && (
              <button
                onClick={() => navigate('/sales/integrations')}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-indigo-700 bg-indigo-50/60 hover:bg-indigo-100/70 transition-colors font-medium"
                data-testid="crm-integrations-hub-sidebar-btn"
              >
                <Layers className="w-4 h-4 text-indigo-600" />
                {sidebarOpen && <span>Integrations Hub</span>}
              </button>
            )}

            <button
              onClick={() => navigate(isAdmin ? '/admin/product-master' : '/sales/pitch-guide')}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-emerald-800 bg-emerald-50/70 hover:bg-emerald-100/70 transition-colors font-medium"
              data-testid="crm-product-master-sidebar-btn"
            >
              <Globe className="w-4 h-4 text-emerald-600" />
              {sidebarOpen && (
                <span>{isAdmin ? 'Product Master Hub' : 'Pitch Guide & Sales Handbook'}</span>
              )}
            </button>
          </div>

          {/* Communication Section */}
          <div className="pt-3">
            {sidebarOpen && <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Communication</p>}
            <button
              onClick={() => setView('calls')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'calls' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <div className="flex items-center gap-3">
                <Phone className="w-4 h-4 text-slate-400" />
                {sidebarOpen && <span>Calls & History</span>}
              </div>
              {sidebarOpen && <Badge variant="secondary" className="text-xs">{scopedCalls.length}</Badge>}
            </button>

            <button
              onClick={() => setView('whatsapp')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'whatsapp' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <div className="flex items-center gap-3">
                <MessageCircle className="w-4 h-4 text-emerald-500" />
                {sidebarOpen && <span>WhatsApp Inbox</span>}
              </div>
              {actionsWaiting.whatsapp_replies > 0 && (
                <Badge className="bg-emerald-600 text-white text-[10px] px-1.5 py-0">{actionsWaiting.whatsapp_replies}</Badge>
              )}
            </button>

            <button
              onClick={() => setView('emails')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'emails' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <div className="flex items-center gap-3">
                <Mail className="w-4 h-4 text-slate-400" />
                {sidebarOpen && <span>Email Center</span>}
              </div>
              {sidebarOpen && <Badge variant="secondary" className="text-xs">{allEmails.length}</Badge>}
            </button>
          </div>

          {/* Activities Section */}
          <div className="pt-3">
            {sidebarOpen && <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Activities & Tasks</p>}
            <button
              onClick={() => setView('followups')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'followups' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <div className="flex items-center gap-3">
                <Clock className="w-4 h-4 text-slate-400" />
                {sidebarOpen && <span>Follow-ups Due</span>}
              </div>
              {actionsWaiting.follow_ups_due > 0 && (
                <Badge className="bg-amber-500 text-white text-[10px] px-1.5 py-0">{actionsWaiting.follow_ups_due}</Badge>
              )}
            </button>

            <button
              onClick={() => setView('meetings')}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'meetings' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <div className="flex items-center gap-3">
                <Video className={`w-4 h-4 ${view === 'meetings' ? 'text-emerald-600' : 'text-slate-400'}`} />
                {sidebarOpen && <span>Meetings & Consultations</span>}
              </div>
              {sidebarOpen && meetings.length > 0 && (
                <Badge className="bg-indigo-600 text-white text-[10px] px-1.5 py-0">{meetings.length}</Badge>
              )}
            </button>
          </div>

          {/* Sales Team Section (Admin Only) */}
          {isAdmin && (
            <div className="pt-3">
              {sidebarOpen && <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Sales Team</p>}
              <button
                onClick={() => setView('internal_salespersons')}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'internal_salespersons' ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
                data-testid="admin-internal-salespersons-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <UserCheck className={`w-4 h-4 ${view === 'internal_salespersons' ? 'text-indigo-600' : 'text-slate-400'}`} />
                  {sidebarOpen && <span>Internal Salespersons</span>}
                </div>
              </button>

              <button
                onClick={() => setView('external_salespersons')}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'external_salespersons' ? 'bg-amber-50 text-amber-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
                data-testid="admin-external-salespersons-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <Users className={`w-4 h-4 ${view === 'external_salespersons' ? 'text-amber-600' : 'text-slate-400'}`} />
                  {sidebarOpen && <span>External Salespersons</span>}
                </div>
              </button>

              <button
                onClick={() => navigate('/admin/sales/targets')}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors text-slate-600 hover:bg-slate-100"
                data-testid="admin-sales-targets-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <Target className="w-4 h-4 text-leamss-teal-600" />
                  {sidebarOpen && <span>Target Management</span>}
                </div>
              </button>

              <button
                onClick={() => setView('salesperson_activity_audit')}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'salesperson_activity_audit' ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
                data-testid="admin-sales-activity-audit-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className={`w-4 h-4 ${view === 'salesperson_activity_audit' ? 'text-indigo-600' : 'text-slate-400'}`} />
                  {sidebarOpen && <span>Activity Audit Log</span>}
                </div>
              </button>
            </div>
          )}

          {/* For Non-Admin Sales Reps */}
          {!isAdmin && (
            <div className="pt-3">
              {sidebarOpen && <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">My Performance</p>}
              <button
                onClick={() => navigate('/sales/my-targets')}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors text-slate-600 hover:bg-slate-100"
                data-testid="my-targets-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <Target className="w-4 h-4 text-leamss-teal-600" />
                  {sidebarOpen && <span>My Targets</span>}
                </div>
              </button>
              <button
                onClick={() => setView('salesperson_activity_audit')}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'salesperson_activity_audit' ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
                data-testid="my-activity-audit-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className={`w-4 h-4 ${view === 'salesperson_activity_audit' ? 'text-indigo-600' : 'text-slate-400'}`} />
                  {sidebarOpen && <span>Activity Report / Audit</span>}
                </div>
              </button>
            </div>
          )}

          {/* Templates Section (Admin Only) */}
          {isAdmin && (
            <div className="pt-3">
              {sidebarOpen && <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Templates</p>}
              <button
                onClick={() => setView('email_templates')}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'email_templates' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
                data-testid="admin-email-templates-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <Mail className={`w-4 h-4 ${view === 'email_templates' ? 'text-emerald-600' : 'text-slate-400'}`} />
                  {sidebarOpen && <span>Email Templates</span>}
                </div>
              </button>

              <button
                onClick={() => setView('whatsapp_templates')}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${view === 'whatsapp_templates' ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
                data-testid="admin-whatsapp-templates-sidebar-btn"
              >
                <div className="flex items-center gap-3">
                  <MessageCircle className={`w-4 h-4 ${view === 'whatsapp_templates' ? 'text-emerald-600' : 'text-emerald-500'}`} />
                  {sidebarOpen && <span>WhatsApp Templates</span>}
                </div>
                {sidebarOpen && waTemplates.length > 0 && (
                  <Badge variant="secondary" className="text-xs">{waTemplates.length}</Badge>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Back to Portal Hub */}
        <div className="p-3 border-t border-slate-100">
          <button
            onClick={() => navigate('/portal/welcome')}
            className="w-full flex items-center gap-3 px-3 py-2 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg text-sm transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            {sidebarOpen && <span>Back to Main Hub</span>}
          </button>
        </div>
      </aside>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* MAIN CONTENT AREA */}
      {/* ──────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        
        {/* Top Header Bar */}
        <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between z-20">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-slate-900 capitalize tracking-tight">
              {view === 'dashboard' ? 'Sales Overview' :
               view === 'website_leads' ? 'Website Leads & Enquiries' :
               view === 'table' ? 'All Leads' :
               view === 'kanban' ? 'Leads Board' :
               view === 'pipeline' ? 'Sales Pipeline' :
               view === 'payments' ? 'Sales Payments' :
               view === 'calls' ? 'Calls & History' :
               view === 'whatsapp' ? 'WhatsApp Inbox' :
               (view === 'emails' || view === 'email') ? 'Email Center' :
               view === 'followups' ? 'Follow-ups Due' :
               view === 'meetings' ? 'Meetings' :
               view === 'email_templates' ? 'Email Templates Management' :
               view === 'whatsapp_templates' ? 'WhatsApp Templates Management' :
               view === 'internal_salespersons' ? 'Internal Salespersons' :
               view === 'external_salespersons' ? 'External Salespersons (Partners)' :
               view === 'salesperson_activity_audit' ? (isAdmin ? 'Salesperson Activity Audit Log' : 'My Activity Report & Audit History') :
               view === 'performance' ? 'Growth & Reports' :
               view.replace(/_/g, ' ')}
            </h2>
            <div className="relative hidden md:block w-72">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <Input
                placeholder="Search leads, phone, email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-9 text-xs bg-slate-50 border-slate-200 focus:bg-white"
              />
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {isAdmin && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setShowImportModal(true); setImportResults(null); setImportFile(null); }}
                className="h-9 gap-1.5 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 font-medium"
                data-testid="admin-bulk-import-header-btn"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                Bulk Import
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={fetchAllCRMData}
              disabled={loading}
              className="h-9 gap-1.5 text-xs text-slate-600"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            
            <Button
              size="sm"
              onClick={() => setShowAddLead(true)}
              className="h-9 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              Add Lead
            </Button>
          </div>
        </header>

        {/* View Switcher Container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: DASHBOARD */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'dashboard' && (
            <div className="space-y-6">

              {/* ⭐ PROMINENT BANNER: Today's New Leads Assigned by Admin */}
              {todayAssignedLeads.length > 0 ? (
                <div className="bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-indigo-500/10 border-2 border-emerald-400 rounded-2xl p-5 shadow-sm relative overflow-hidden">
                  <div className="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-emerald-400/10 rounded-full blur-2xl pointer-events-none" />
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-emerald-200/60">
                    <div className="flex items-start sm:items-center gap-3.5">
                      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white flex items-center justify-center font-bold shadow-md shadow-emerald-200 flex-shrink-0 animate-pulse">
                        <Sparkles className="w-6 h-6" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-base font-bold text-slate-900">
                            Today's New Leads Assigned by Admin
                          </h3>
                          <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-2.5 py-0.5 shadow-sm">
                            {todayAssignedLeads.length} Assigned Today
                          </Badge>
                          <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-100/80 px-2.5 py-0.5 rounded-full border border-emerald-200">
                            Immediate Outreach Required
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 mt-1">
                          Admin has assigned these prospects to you today. Quick call or WhatsApp within 15 minutes increases qualification by up to 391%.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Button
                        onClick={() => {
                          setAssignedTodayFilter(true);
                          setView('table');
                        }}
                        size="sm"
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs h-9 px-4 gap-1.5 shadow-sm"
                      >
                        <Eye className="w-3.5 h-3.5" /> View All Assigned Today ({todayAssignedLeads.length})
                      </Button>
                    </div>
                  </div>

                  {/* Quick Cards of Today's Assigned Leads */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-4">
                    {todayAssignedLeads.slice(0, 3).map((al) => {
                      const st = STAGE_MAP[al.stage] || { label: al.stage || 'New', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' };
                      return (
                        <div
                          key={al.id}
                          className="bg-white border border-emerald-200/90 rounded-xl p-3.5 hover:shadow-md hover:border-emerald-400 transition-all flex flex-col justify-between"
                        >
                          <div>
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className="font-bold text-slate-900 text-sm truncate">{al.name}</span>
                                  <Badge className="bg-purple-50 text-purple-700 border-purple-200 border text-[9px] px-1.5 py-0 font-bold">
                                    {al.assigned_by_name ? `By ${al.assigned_by_name}` : 'By Admin'}
                                  </Badge>
                                </div>
                                <p className="text-xs text-slate-500 truncate mt-0.5">
                                  {al.service_interested || al.country_of_interest || 'Immigration Consulting'}
                                </p>
                              </div>
                              <Badge className={`${st.bg} ${st.text} ${st.border} border text-[10px] font-semibold flex-shrink-0`}>
                                {st.label}
                              </Badge>
                            </div>

                            <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500">
                              <span className="truncate font-mono">{al.phone || al.email || 'No phone'}</span>
                              <span className="text-[10px] text-slate-400 font-medium">
                                {timeAgo(al.assigned_at || al.updated_at || al.created_at)}
                              </span>
                            </div>
                          </div>

                          <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center gap-1.5">
                            {al.phone && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleStartCall(al)}
                                className="flex-1 text-[11px] h-7 px-2 border-blue-200 text-blue-700 hover:bg-blue-50 gap-1 font-semibold"
                                title="Call now"
                              >
                                <PhoneCall className="w-3 h-3" /> Call
                              </Button>
                            )}
                            {al.phone && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setSelectedLead(al);
                                  setShowWhatsAppModal(true);
                                }}
                                className="flex-1 text-[11px] h-7 px-2 border-emerald-200 text-emerald-700 hover:bg-emerald-50 gap-1 font-semibold"
                                title="Send WhatsApp"
                              >
                                <MessageCircle className="w-3 h-3" /> WhatsApp
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleOpenLeadWorkspace(al)}
                              className="text-[11px] h-7 px-2 text-slate-600 hover:text-emerald-700 hover:bg-emerald-50 gap-1 font-semibold"
                              title="Open Full Profile"
                            >
                              <ExternalLink className="w-3 h-3" /> Profile
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex items-center justify-between text-xs text-slate-600">
                  <div className="flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-emerald-600" />
                    <span>
                      <strong>Admin Assignments:</strong> No new leads assigned to you today yet. Follow up on existing active leads below.
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-medium">Updated live</span>
                </div>
              )}
              
              {/* 1. Top Primary KPI Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">

                <Card
                  onClick={() => { setAssignedTodayFilter(true); setView('table'); }}
                  className={`p-4 bg-white border shadow-sm relative overflow-hidden cursor-pointer hover:shadow-md transition-all group ${
                    todayAssignedLeads.length > 0 ? 'border-emerald-300 ring-1 ring-emerald-200' : 'border-slate-200 hover:border-emerald-400'
                  }`}
                  title="Click to view all leads assigned today by Admin"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider group-hover:text-emerald-700 transition-colors">
                          Assigned Today
                        </p>
                        {todayAssignedLeads.length > 0 && (
                          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                        )}
                      </div>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">
                        {todayAssignedLeads.length}
                      </h3>
                      <p className="text-[11px] text-slate-500 mt-2">
                        {todayAssignedLeads.length > 0 ? (
                          <span className="font-semibold text-emerald-700 underline underline-offset-2">From Admin · View All</span>
                        ) : (
                          'No new leads today'
                        )}
                      </p>
                    </div>
                    <div className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold transition-colors ${
                      todayAssignedLeads.length > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                    }`}>
                      <Sparkles className="w-6 h-6" />
                    </div>
                  </div>
                </Card>
                
                <Card className="p-4 bg-white border-slate-200 shadow-sm relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Leads</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">{leads.length}</h3>
                      <p className="text-[11px] text-slate-500 mt-2">Active across sales pipeline</p>
                    </div>
                    <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                      <Users className="w-6 h-6" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4 bg-white border-slate-200 shadow-sm relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Today's Action Items</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">
                        {(Number(actionsWaiting?.calls_due) || 0) + (Number(actionsWaiting?.follow_ups_due) || 0)}
                      </h3>
                      <p className="text-[11px] text-slate-500 mt-2">
                        <span className="font-semibold text-slate-700">{Number(actionsWaiting?.calls_due) || 0}</span> calls & <span className="font-semibold text-slate-700">{Number(actionsWaiting?.follow_ups_due) || 0}</span> follow-ups due
                      </p>
                    </div>
                    <div className="w-11 h-11 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                      <CalendarClock className="w-6 h-6" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4 bg-white border-slate-200 shadow-sm relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Deals Pipeline</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">{deals.length} Active</h3>
                      <p className="text-[11px] text-slate-500 mt-2">
                        Potential Value: <span className="font-semibold text-emerald-600">₹{(deals.reduce((acc, d) => acc + (d.deal_value || 0), 0) / 100000).toFixed(1)}L</span>
                      </p>
                    </div>
                    <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
                      <TrendingUp className="w-6 h-6" />
                    </div>
                  </div>
                </Card>

                <Card
                  onClick={() => { setView('table'); setStageFilter('converted'); }}
                  className="p-4 bg-white border-slate-200 shadow-sm relative overflow-hidden cursor-pointer hover:border-emerald-400 hover:shadow-md transition-all group"
                  title="Click to view all Converted Clients"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider group-hover:text-emerald-700 transition-colors">Converted Clients</p>
                      <h3 className="text-2xl font-bold text-emerald-600 mt-1">
                        {leads.filter(l => l.stage === 'converted' || l.status === 'converted' || l.converted || ['won', 'closed_won', 'case_created'].includes(String(l.stage || l.status || '').toLowerCase())).length}
                      </h3>
                      <p className="text-[11px] text-slate-500 mt-2">
                        Rate: <span className="font-semibold text-slate-900">{stats.conversion_rate || 0}%</span> · <span className="text-emerald-600 font-semibold underline underline-offset-2">View Converted</span>
                      </p>
                    </div>
                    <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold group-hover:bg-emerald-100 transition-colors">
                      <Award className="w-6 h-6" />
                    </div>
                  </div>
                </Card>

              </div>

              {/* 2. "ACTIONS WAITING FOR YOU" INTERACTIVE SECTION */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-500 fill-amber-500" />
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide">Actions Waiting for You</h3>
                  </div>
                  <span className="text-xs text-slate-400">Click any card to view and act</span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
                  
                  {/* Card 0: Assigned Today by Admin */}
                  <button
                    onClick={() => handleActionWaitingClick('assigned_today')}
                    className="p-3 bg-white border border-emerald-200 hover:border-emerald-400 hover:shadow-md rounded-xl text-left transition-all group flex flex-col justify-between h-24 relative overflow-hidden"
                    title="Click to view today's leads assigned by Admin"
                  >
                    <div className="flex items-center justify-between w-full">
                      <Sparkles className="w-4 h-4 text-emerald-600 group-hover:scale-110 transition-transform" />
                      <Badge className="bg-emerald-50 text-emerald-700 text-xs px-1.5 py-0 font-bold">
                        {todayAssignedLeads.length}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800 leading-tight">Assigned Today</p>
                      <p className="text-[10px] text-emerald-600 font-medium">New from Admin</p>
                    </div>
                  </button>

                  {/* Card 1: Calls Due */}
                  <button
                    onClick={() => handleActionWaitingClick('calls_due')}
                    className="p-3 bg-white border border-slate-200 hover:border-blue-400 hover:shadow-md rounded-xl text-left transition-all group flex flex-col justify-between h-24"
                  >
                    <div className="flex items-center justify-between w-full">
                      <PhoneCall className="w-4 h-4 text-blue-600 group-hover:scale-110 transition-transform" />
                      <Badge className="bg-blue-50 text-blue-700 text-xs px-1.5 py-0 font-bold">{actionsWaiting.calls_due}</Badge>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800 leading-tight">Calls Due</p>
                      <p className="text-[10px] text-slate-400">Scheduled today</p>
                    </div>
                  </button>

                  {/* Card 2: Follow-ups Due */}
                  <button
                    onClick={() => handleActionWaitingClick('follow_ups_due')}
                    className="p-3 bg-white border border-slate-200 hover:border-amber-400 hover:shadow-md rounded-xl text-left transition-all group flex flex-col justify-between h-24"
                  >
                    <div className="flex items-center justify-between w-full">
                      <Clock className="w-4 h-4 text-amber-600 group-hover:scale-110 transition-transform" />
                      <Badge className="bg-amber-50 text-amber-700 text-xs px-1.5 py-0 font-bold">{actionsWaiting.follow_ups_due}</Badge>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800 leading-tight">Follow-ups Due</p>
                      <p className="text-[10px] text-slate-400">Action pending</p>
                    </div>
                  </button>

                  {/* Card 3: WhatsApp Replies */}
                  <button
                    onClick={() => handleActionWaitingClick('whatsapp_replies')}
                    className="p-3 bg-white border border-slate-200 hover:border-emerald-400 hover:shadow-md rounded-xl text-left transition-all group flex flex-col justify-between h-24"
                  >
                    <div className="flex items-center justify-between w-full">
                      <MessageCircle className="w-4 h-4 text-emerald-600 group-hover:scale-110 transition-transform" />
                      <Badge className="bg-emerald-50 text-emerald-700 text-xs px-1.5 py-0 font-bold">{actionsWaiting.whatsapp_replies}</Badge>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800 leading-tight">WhatsApp Replies</p>
                      <p className="text-[10px] text-slate-400">Unread inbound</p>
                    </div>
                  </button>

                  {/* Card 4: Emails Pending */}
                  <button
                    onClick={() => handleActionWaitingClick('emails_pending')}
                    className="p-3 bg-white border border-slate-200 hover:border-indigo-400 hover:shadow-md rounded-xl text-left transition-all group flex flex-col justify-between h-24"
                  >
                    <div className="flex items-center justify-between w-full">
                      <Mail className="w-4 h-4 text-indigo-600 group-hover:scale-110 transition-transform" />
                      <Badge className="bg-indigo-50 text-indigo-700 text-xs px-1.5 py-0 font-bold">{actionsWaiting.emails_pending}</Badge>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800 leading-tight">Emails Pending</p>
                      <p className="text-[10px] text-slate-400">Proposals/Follow-up</p>
                    </div>
                  </button>

                  {/* Card 5: Meetings Today */}
                  <button
                    onClick={() => handleActionWaitingClick('meetings_today')}
                    className="p-3 bg-white border border-slate-200 hover:border-sky-400 hover:shadow-md rounded-xl text-left transition-all group flex flex-col justify-between h-24"
                  >
                    <div className="flex items-center justify-between w-full">
                      <Video className="w-4 h-4 text-sky-600 group-hover:scale-110 transition-transform" />
                      <Badge className="bg-sky-50 text-sky-700 text-xs px-1.5 py-0 font-bold">{actionsWaiting.meetings_today}</Badge>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-800 leading-tight">Meetings Today</p>
                      <p className="text-[10px] text-slate-400">Scheduled calls</p>
                    </div>
                  </button>

                  {/* Card 8: Overdue Actions */}
                  <button
                    onClick={() => handleActionWaitingClick('overdue_actions')}
                    className="p-3 bg-white border border-rose-200 bg-rose-50/30 hover:border-rose-400 hover:shadow-md rounded-xl text-left transition-all group flex flex-col justify-between h-24"
                  >
                    <div className="flex items-center justify-between w-full">
                      <AlertCircle className="w-4 h-4 text-rose-600 group-hover:scale-110 transition-transform" />
                      <Badge className="bg-rose-100 text-rose-800 text-xs px-1.5 py-0 font-bold">{actionsWaiting.overdue_actions}</Badge>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-rose-800 leading-tight">Overdue Actions</p>
                      <p className="text-[10px] text-rose-600 font-medium">Escalate / Act now</p>
                    </div>
                  </button>

                </div>
              </div>

              {/* 3. Charts & Recent Activity Stream */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Stage Distribution Chart */}
                <Card className="p-5 bg-white border-slate-200 shadow-sm lg:col-span-2">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">Leads Pipeline by Stage</h4>
                      <p className="text-xs text-slate-500">Live active distribution across all qualification stages</p>
                    </div>
                    <Badge variant="outline" className="text-xs">Live Funnel</Badge>
                  </div>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="name" angle={-30} textAnchor="end" interval={0} tick={{ fontSize: 10, fill: '#64748b' }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                        <Tooltip />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                          {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                {/* Recent Leads Quick List */}
                <Card className="p-5 bg-white border-slate-200 shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                        <Users className="w-4 h-4 text-emerald-600" />
                        Leads Quick View
                      </h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (recentLeadsTab === 'assigned_today') {
                            setAssignedTodayFilter(true);
                          }
                          setView('table');
                        }}
                        className="text-xs text-emerald-600 h-7 p-1"
                      >
                        View All
                      </Button>
                    </div>

                    {/* Tab Switcher */}
                    <div className="flex items-center p-0.5 bg-slate-100 rounded-lg mb-3">
                      <button
                        onClick={() => setRecentLeadsTab('assigned_today')}
                        className={`flex-1 text-[11px] font-semibold py-1 rounded-md transition-all flex items-center justify-center gap-1 ${
                          recentLeadsTab === 'assigned_today' ? 'bg-white text-emerald-700 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        <Sparkles className="w-3 h-3" /> Assigned Today ({todayAssignedLeads.length})
                      </button>
                      <button
                        onClick={() => setRecentLeadsTab('all')}
                        className={`flex-1 text-[11px] font-semibold py-1 rounded-md transition-all ${
                          recentLeadsTab === 'all' ? 'bg-white text-slate-800 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        All Recent ({leads.length})
                      </button>
                    </div>

                    <div className="space-y-2.5 overflow-y-auto max-h-64">
                      {((recentLeadsTab === 'assigned_today' ? todayAssignedLeads : leads).slice(0, 4)).map(hl => {
                        const st = STAGE_MAP[hl.stage] || { label: hl.stage || 'New', bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };
                        const isAssignedToday = isLeadAssignedToday(hl);
                        return (
                          <div
                            key={hl.id}
                            onClick={() => handleOpenLeadWorkspace(hl)}
                            className="p-2.5 rounded-lg border border-slate-100 hover:border-slate-300 hover:bg-slate-50/50 cursor-pointer transition-all flex items-center justify-between"
                          >
                            <div className="min-w-0 pr-2">
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <p className="text-xs font-bold text-slate-900 truncate">{hl.name}</p>
                                {isAssignedToday && (
                                  <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 border text-[9px] px-1 py-0 font-semibold">
                                    {hl.assigned_by_name ? `By ${hl.assigned_by_name}` : 'Admin Assigned'}
                                  </Badge>
                                )}
                              </div>
                              <p className="text-[11px] text-slate-500 truncate max-w-[150px]">{hl.service_interested || hl.country_of_interest}</p>
                            </div>
                            <div className="text-right flex-shrink-0">
                              <Badge className={`${st.bg} ${st.text} ${st.border} border text-[10px] font-medium`}>
                                {st.label}
                              </Badge>
                              <p className="text-[10px] text-slate-400 mt-1">{timeAgo(hl.assigned_at || hl.updated_at || hl.created_at)}</p>
                            </div>
                          </div>
                        );
                      })}
                      {recentLeadsTab === 'assigned_today' && todayAssignedLeads.length === 0 && (
                        <p className="text-xs text-slate-400 italic py-6 text-center">No leads assigned today yet.</p>
                      )}
                      {recentLeadsTab === 'all' && leads.length === 0 && (
                        <p className="text-xs text-slate-400 italic py-6 text-center">No leads yet.</p>
                      )}
                    </div>
                  </div>

                  <Button
                    onClick={() => { setShowAddLead(true); }}
                    variant="outline"
                    className="w-full mt-4 text-xs h-9 border-dashed border-slate-300 gap-1.5 text-slate-600 hover:text-emerald-700"
                  >
                    <Plus className="w-3.5 h-3.5" /> Capture New Prospect
                  </Button>
                </Card>

              </div>

            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: LEADS TABLE */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'table' && (
            <div className="space-y-4">
              
              {/* Filter Bar */}
              <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                  <Filter className="w-4 h-4 text-slate-400" /> Filters:
                </div>

                <Select value={stageFilter} onValueChange={setStageFilter}>
                  <SelectTrigger className="w-36 h-8 text-xs bg-slate-50"><SelectValue placeholder="All Stages" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Stages</SelectItem>
                    {STAGES.map(s => <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>

                <Select value={countryFilter} onValueChange={setCountryFilter}>
                  <SelectTrigger className="w-32 h-8 text-xs bg-slate-50"><SelectValue placeholder="Country" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Countries</SelectItem>
                    {COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>

                <Select value={sourceFilter} onValueChange={setSourceFilter}>
                  <SelectTrigger className="w-36 h-8 text-xs bg-slate-50"><SelectValue placeholder="Source" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Sources ({leads.length})</SelectItem>
                    {SOURCES.map(s => {
                      const count = sourceCounts[s] || 0;
                      const label = s === 'Calendly' ? 'Calendly Bookings' : s;
                      return (
                        <SelectItem key={s} value={s}>
                          {label} ({count})
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>

                <Select value={paymentFilter} onValueChange={setPaymentFilter}>
                  <SelectTrigger className="w-32 h-8 text-xs bg-slate-50"><SelectValue placeholder="Payment" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Payments</SelectItem>
                    <SelectItem value="paid">💰 Paid Only</SelectItem>
                    <SelectItem value="unpaid">⏳ Unpaid Only</SelectItem>
                    <SelectItem value="failed">❌ Failed Only</SelectItem>
                    <SelectItem value="partially_paid">⚡ Partial Only</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={reportFilter} onValueChange={setReportFilter}>
                  <SelectTrigger className="w-36 h-8 text-xs bg-slate-50"><SelectValue placeholder="Reports" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Reports</SelectItem>
                    <SelectItem value="generated">✓ Report Generated</SelectItem>
                    <SelectItem value="paid_pending">⚡ Paid · Pending Report</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  variant={assignedTodayFilter ? "default" : "outline"}
                  size="sm"
                  onClick={() => setAssignedTodayFilter(!assignedTodayFilter)}
                  className={`h-8 text-xs font-semibold gap-1.5 transition-all ${
                    assignedTodayFilter 
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-600 shadow-sm' 
                      : 'text-slate-700 border-slate-200 hover:border-emerald-400 hover:text-emerald-700'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Assigned Today ({todayAssignedLeads.length})
                </Button>

                {(stageFilter !== 'all' || countryFilter !== 'all' || sourceFilter !== 'all' || paymentFilter !== 'all' || reportFilter !== 'all' || assignedTodayFilter || search) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => { setStageFilter('all'); setCountryFilter('all'); setSourceFilter('all'); setPaymentFilter('all'); setReportFilter('all'); setSalespersonFilter('all'); setAssignedTodayFilter(false); setSearch(''); }}
                    className="h-8 text-xs text-rose-600 hover:text-rose-700"
                  >
                    Clear Filters
                  </Button>
                )}

                <div className="ml-auto flex items-center gap-2">
                  {isAdmin && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={syncingLeads}
                        onClick={handleSyncWebsiteLeads}
                        className="h-8 text-xs gap-1.5 border-emerald-300 text-emerald-800 bg-emerald-50/70 hover:bg-emerald-100 font-semibold"
                        title="Fetch latest enquiries from leamss.com & landing forms into CRM"
                      >
                        <CloudDownload className={`w-3.5 h-3.5 text-emerald-700 ${syncingLeads ? 'animate-bounce' : ''}`} />
                        {syncingLeads ? 'Syncing...' : 'Sync Website'}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={fetchPartnerReport}
                        disabled={loadingPartnerReport}
                        className="h-8 text-xs gap-1.5 border-indigo-200 text-indigo-700 bg-indigo-50/50 hover:bg-indigo-100 font-semibold"
                        title="View Partner & Referral Sales Performance Report"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        {loadingPartnerReport ? 'Loading...' : 'Partner Report'}
                      </Button>
                    </>
                  )}
                  <Button
                    size="sm"
                    onClick={handleBulkPreAssessmentClick}
                    disabled={isCreatingBulkBatch}
                    className="h-8 text-xs gap-1.5 bg-purple-600 hover:bg-purple-700 text-white font-semibold shadow-sm transition-all"
                    title={selectedLeadIds.size > 0
                      ? `Create Bulk Pre-Assessment batch for ${selectedLeadIds.size} selected client(s)`
                      : 'Open Bulk Pre-Assessment page to view batches or upload clients'
                    }
                  >
                    <Layers className="w-3.5 h-3.5 text-purple-200" />
                    <span>Bulk Pre-Assessment Report</span>
                    {selectedLeadIds.size > 0 && (
                      <span className="ml-0.5 px-1.5 py-0.2 bg-purple-800 text-white text-[10px] rounded-full font-bold">
                        {selectedLeadIds.size}
                      </span>
                    )}
                  </Button>
                  {selectedLeadIds.size > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedLeadIds(new Set())}
                      className="h-8 text-xs text-slate-500 hover:text-slate-800"
                    >
                      Clear ({selectedLeadIds.size})
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      setLoading(true);
                      try {
                        const res = await axios.get(`${API}/leads/?limit=2000`, getAuthHeader());
                        setLeads(res.data || []);
                        toast.success('Leads refreshed');
                      } catch {
                        toast.error('Failed to refresh leads');
                      } finally {
                        setLoading(false);
                      }
                    }}
                    className="h-8 text-xs gap-1 border-slate-200 text-slate-700 hover:text-emerald-700"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
                  </Button>
                  <div className="text-xs text-slate-500 font-medium">
                    Showing <span className="font-bold text-slate-800">{filteredLeads.length}</span> of {leads.length} leads
                  </div>
                </div>
              </div>

              {/* Table Card */}
              <Card className="bg-white border-slate-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                        <th className="p-3 pl-3.5 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={filteredLeads.length > 0 && selectedLeadIds.size >= filteredLeads.length}
                            onChange={toggleSelectAllLeads}
                            title="Select / Deselect all visible leads"
                            className="rounded border-slate-300 text-purple-600 focus:ring-purple-500 w-3.5 h-3.5 cursor-pointer"
                          />
                        </th>
                        <th className="p-3 pl-2">Lead ID & Name</th>
                        <th className="p-3">Contact</th>
                        <th className="p-3">Service & Country</th>
                        <th className="p-3">Source</th>
                        <th className="p-3">Stage / Status</th>
                        <th className="p-3">Next Follow-up</th>
                        <th className="p-3 pr-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredLeads.map(lead => {
                        const st = STAGE_MAP[lead.stage] || { label: lead.stage, bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200' };
                        return (
                          <tr
                            key={lead.id}
                            className={`transition-colors group cursor-pointer ${
                              selectedLeadIds.has(lead.id) ? 'bg-purple-50/50 hover:bg-purple-50/80' : 'hover:bg-slate-50/60'
                            }`}
                            onClick={() => handleOpenLeadWorkspace(lead)}
                          >
                            <td className="p-3 pl-3.5 w-10 text-center" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="checkbox"
                                checked={selectedLeadIds.has(lead.id)}
                                onChange={() => toggleSelectLead(lead.id)}
                                title={isLeadResumeAttached(lead) ? "Resume attached" : "No resume attached"}
                                className="rounded border-slate-300 text-purple-600 focus:ring-purple-500 w-3.5 h-3.5 cursor-pointer"
                              />
                            </td>
                            <td className="p-3 pl-2">
                              <div className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-[11px]">
                                  {(lead.name || 'L')[0]}
                                </div>
                                <div>
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <p className="font-bold text-slate-900 group-hover:text-emerald-700 transition-colors">{lead.name}</p>
                                    {isLeadAssignedToday(lead) && (
                                      <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 border text-[9px] px-1.5 py-0 font-bold gap-0.5 shadow-none">
                                        <Sparkles className="w-2.5 h-2.5 text-emerald-600" /> Assigned Today
                                      </Badge>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                                    <span className="font-mono">{lead.lead_number}</span>
                                    {lead.assigned_by_name && (
                                      <span className="text-slate-500 font-medium">· by {lead.assigned_by_name}</span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="p-3">
                              {lead.phone ? (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleStartCall(lead);
                                  }}
                                  className="text-slate-800 hover:text-blue-600 font-medium flex items-center gap-1 group/phone text-left"
                                  title="Click to call this client"
                                >
                                  <PhoneCall className="w-3 h-3 text-blue-500 group-hover/phone:scale-110 transition-transform" />
                                  <span>{lead.phone}</span>
                                </button>
                              ) : (
                                <p className="text-[11px] text-slate-400">No phone</p>
                              )}
                              {lead.email ? (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleOpenEmailModal('', '', null, lead);
                                  }}
                                  className="text-[11px] text-indigo-600 hover:text-indigo-800 hover:underline flex items-center gap-1 font-mono text-left group/mail"
                                  title="Click to directly compose email to this lead"
                                >
                                  <Mail className="w-3 h-3 text-indigo-500 group-hover/mail:scale-110 transition-transform" />
                                  <span>{lead.email}</span>
                                </button>
                              ) : (
                                <p className="text-[11px] text-slate-400">No email</p>
                              )}
                            </td>
                            <td className="p-3">
                              <p className="font-medium text-slate-800">{lead.service_interested || 'Immigration'}</p>
                              <p className="text-[11px] text-slate-400">{lead.country_of_interest || lead.interested_country || 'Canada'}</p>
                              {isLeadResumeAttached(lead) ? (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleOpenResumePreview(lead);
                                  }}
                                  className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 rounded mt-1 shadow-none transition-colors"
                                  title={`Resume attached: ${lead.resume_filename || 'Candidate Resume'}`}
                                >
                                  <FileText className="w-2.5 h-2.5 text-emerald-600" /> Resume Attached
                                </button>
                              ) : (
                                <span
                                  className="inline-flex items-center gap-0.5 text-[10px] text-slate-400 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded mt-1"
                                  title="No resume attached for this client"
                                >
                                  <AlertCircle className="w-2.5 h-2.5 text-slate-400" /> No Resume
                                </span>
                              )}
                            </td>
                            <td className="p-3">
                              {(() => {
                                const srcCfg = getSourceConfig(lead.source);
                                const IconComp = srcCfg.icon || Globe;
                                const subSourceText = (lead.subsource && lead.subsource !== srcCfg.label)
                                  ? lead.subsource
                                  : (lead.campaign && lead.campaign !== 'Organic' && lead.campaign !== 'Manual Direct' && lead.campaign !== srcCfg.label)
                                    ? lead.campaign
                                    : (lead.original_source && lead.original_source !== srcCfg.label && !lead.original_source.toLowerCase().includes('unknown'))
                                      ? lead.original_source
                                      : null;

                                const lMeeting = meetings.find(m =>
                                  (m.lead_id && String(m.lead_id) === String(lead.id)) ||
                                  (lead.email && m.contact_email && String(m.contact_email).toLowerCase().trim() === String(lead.email).toLowerCase().trim())
                                );
                                const cb = lead.calendly_booking || lead.booking_details;
                                const hasBooking = Boolean(lead.has_booking || cb || lMeeting);
                                const bDate = cb?.date || lMeeting?.meeting_date;
                                const bTime = cb?.time || lMeeting?.meeting_time;
                                const bMeetLink = cb?.meeting_link || lMeeting?.meeting_link;

                                return (
                                  <div className="flex flex-col items-start gap-1">
                                    <div className="flex items-center gap-1 flex-wrap">
                                      <Badge className={`${srcCfg.bg} ${srcCfg.text} ${srcCfg.border} border text-[11px] font-semibold gap-1 px-2 py-0.5 shadow-none inline-flex items-center`}>
                                        <IconComp className="w-3 h-3 shrink-0" />
                                        <span>{srcCfg.label}</span>
                                      </Badge>
                                      {hasBooking && (
                                        <Badge className="bg-indigo-600 text-white border-transparent text-[10px] font-bold gap-1 px-1.5 py-0.5 shadow-none inline-flex items-center">
                                          <Calendar className="w-2.5 h-2.5 shrink-0" />
                                          <span>Booked</span>
                                        </Badge>
                                      )}
                                    </div>
                                    {hasBooking && (bDate || bTime) && (
                                      <div className="flex flex-col text-[10px] bg-indigo-50/80 border border-indigo-100 rounded px-1.5 py-0.5 text-indigo-900 font-medium">
                                        <span>📅 {bDate || 'Scheduled'} {bTime ? `@ ${bTime}` : ''}</span>
                                        {bMeetLink && (
                                          <a
                                            href={bMeetLink}
                                            target="_blank"
                                            rel="noreferrer"
                                            onClick={(e) => e.stopPropagation()}
                                            className="text-emerald-700 hover:text-emerald-800 hover:underline font-semibold inline-flex items-center gap-0.5 mt-0.5"
                                          >
                                            <Video className="w-2.5 h-2.5" /> Join Meet
                                          </a>
                                        )}
                                      </div>
                                    )}
                                    {subSourceText && (
                                      <span className="text-[10px] text-slate-400 font-mono truncate max-w-[125px]" title={subSourceText}>
                                        {subSourceText}
                                      </span>
                                    )}
                                  </div>
                                );
                              })()}
                            </td>
                            <td className="p-3">
                              <div className="flex flex-col gap-1 items-start">
                                <Badge className={`${st.bg} ${st.text} ${st.border} border text-[11px] font-medium`}>
                                  {st.label}
                                </Badge>
                                {/* Cockpit Payment Status Badge */}
                                {lead.payment_status === 'paid' || lead.is_paid ? (
                                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-300 rounded px-1.5 py-0.5" title={`Paid: ₹${Number(lead.amount_paid || ((lead.payment_amount && Number(lead.payment_amount) !== 999) ? lead.payment_amount : 2427)).toLocaleString('en-IN')}`}>
                                    <Check className="w-2.5 h-2.5 text-emerald-600 stroke-[3]" /> Paid (₹{Number(lead.amount_paid || ((lead.payment_amount && Number(lead.payment_amount) !== 999) ? lead.payment_amount : 2427)).toLocaleString('en-IN')})
                                  </span>
                                ) : lead.payment_status === 'failed' ? (
                                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-50 border border-rose-300 rounded px-1.5 py-0.5" title={lead.last_payment_error || 'Payment failed'}>
                                    <X className="w-2.5 h-2.5 text-rose-600 stroke-[3]" /> Failed
                                  </span>
                                ) : lead.payment_status === 'partially_paid' ? (
                                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-50 border border-amber-300 rounded px-1.5 py-0.5" title={`Partial: ₹${Number(lead.amount_paid || 0).toLocaleString('en-IN')}`}>
                                    ⚡ Partial (₹{Number(lead.amount_paid || 0).toLocaleString('en-IN')})
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-700 bg-amber-50/80 border border-amber-200 rounded px-1.5 py-0.5">
                                    <Clock className="w-2.5 h-2.5 text-amber-500" /> Unpaid
                                  </span>
                                 )}
                              </div>
                            </td>
                            <td className="p-3">
                              <p className="text-slate-700 font-medium">{lead.next_follow_up ? new Date(lead.next_follow_up).toLocaleDateString() : 'None set'}</p>
                              <p className="text-[10px] text-slate-400">{timeAgo(lead.last_contacted_at)}</p>
                            </td>
                            <td className="p-3 pr-4 text-right" onClick={(e) => e.stopPropagation()}>
                              <div className="flex items-center justify-end gap-1.5">
                                {lead.phone && (
                                  <button
                                    type="button"
                                    onClick={() => handleStartCall(lead)}
                                    className="p-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                                    title="Call client with live audio recording & duration"
                                  >
                                    <PhoneCall className="w-3.5 h-3.5" />
                                  </button>
                                )}
                                {lead.phone && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSelectedLead(lead);
                                      setShowWhatsAppModal(true);
                                    }}
                                    className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition-colors"
                                    title="Send WhatsApp message as consultant with auto-personalized templates"
                                  >
                                    <MessageCircle className="w-3.5 h-3.5" />
                                  </button>
                                )}
                                {lead.email && (
                                  <button
                                    type="button"
                                    onClick={() => handleOpenEmailModal('', '', null, lead)}
                                    className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 hover:bg-indigo-100 transition-colors"
                                    title="Directly send email to this lead (No sidebar)"
                                  >
                                    <Mail className="w-3.5 h-3.5" />
                                  </button>
                                )}
                                {lead.assessment_report_file_id || lead.pre_assessment_report_url || lead.report_generated ? (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleOpenReportPreview(lead)}
                                    className="h-7 px-2 text-xs font-semibold text-emerald-700 border-emerald-300 bg-emerald-50/70 hover:bg-emerald-100 flex items-center gap-1"
                                    title="View generated Pre-Assessment Report"
                                  >
                                    <FileText className="w-3 h-3 text-emerald-600" /> View Report
                                  </Button>
                                ) : (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleOpenPreAssessmentReport(lead)}
                                    className="h-7 px-2 text-xs font-semibold text-purple-700 border-purple-200 bg-purple-50/60 hover:bg-purple-100 flex items-center gap-1"
                                    title="Open Pre-Assessment Report creation with client details pre-populated"
                                  >
                                    <FileText className="w-3 h-3 text-purple-600" /> Pre-Assessment Report
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleOpenLeadWorkspace(lead)}
                                  className="h-7 px-2 text-xs font-medium text-slate-600 hover:text-emerald-700"
                                >
                                  View Details
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                      {filteredLeads.length === 0 && (
                        <tr>
                          <td colSpan={8} className="p-8 text-center text-slate-400 text-xs italic">
                            No leads matching current filters.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: KANBAN BOARD */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'kanban' && (
            <div className="flex gap-4 overflow-x-auto pb-4 h-[calc(100vh-180px)]">
              {STAGES.slice(0, 10).map(stage => {
                const stageLeads = leads.filter(l => l.stage === stage.key || l.status === stage.key);
                return (
                  <div key={stage.key} className="w-72 flex-shrink-0 bg-slate-100/70 rounded-xl p-3 flex flex-col border border-slate-200">
                    <div className="flex items-center justify-between mb-3 px-1">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${stage.color}`}></span>
                        <h4 className="font-bold text-xs text-slate-800 uppercase tracking-wide">{stage.label}</h4>
                      </div>
                      <Badge variant="secondary" className="text-[11px] font-bold">{stageLeads.length}</Badge>
                    </div>

                    <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                      {stageLeads.map(lead => (
                        <Card
                          key={lead.id}
                          onClick={() => handleOpenLeadWorkspace(lead)}
                          className="p-3 bg-white border-slate-200 hover:border-emerald-400 hover:shadow-md cursor-pointer transition-all space-y-2 group"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono text-slate-400">{lead.lead_number}</span>
                          </div>

                          <h5 className="font-bold text-xs text-slate-900 group-hover:text-emerald-700 transition-colors">{lead.name}</h5>
                          <p className="text-[11px] text-slate-500 truncate">{lead.service_interested || 'Immigration'}</p>

                          <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[10px] text-slate-400">
                            <span>{lead.country_of_interest || 'Canada'}</span>
                            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                              {lead.phone && (
                                <button
                                  type="button"
                                  onClick={() => handleStartCall(lead)}
                                  className="p-1 rounded hover:bg-blue-50 text-blue-600 transition-colors"
                                  title="Call Client"
                                >
                                  <PhoneCall className="w-3 h-3" />
                                </button>
                              )}
                              {lead.email && (
                                <button
                                  type="button"
                                  onClick={() => handleOpenEmailModal('', '', null, lead)}
                                  className="p-1 rounded hover:bg-indigo-50 text-indigo-600 transition-colors"
                                  title="Directly send email (No sidebar)"
                                >
                                  <Mail className="w-3 h-3" />
                                </button>
                              )}
                              {lead.phone && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setSelectedLead(lead);
                                    setShowWhatsAppModal(true);
                                  }}
                                  className="p-1 rounded hover:bg-emerald-50 text-emerald-600 transition-colors"
                                  title="Send WhatsApp as consultant"
                                >
                                  <MessageCircle className="w-3 h-3" />
                                </button>
                              )}
                              <span className="ml-1">{timeAgo(lead.last_contacted_at || lead.created_at)}</span>
                            </div>
                          </div>
                        </Card>
                      ))}
                      {stageLeads.length === 0 && (
                        <div className="h-24 border border-dashed border-slate-300 rounded-lg flex items-center justify-center text-[11px] text-slate-400 italic">
                          No leads in {stage.label}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: SALES PIPELINE & DEALS */}
          {view === 'pipeline' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div>
                  <h3 className="font-bold text-sm text-slate-900">Active Deals Pipeline</h3>
                  <p className="text-xs text-slate-500">Track deal progress, probability, and closing timelines</p>
                </div>
                <Badge className="bg-emerald-100 text-emerald-800 text-xs font-bold">
                  Total Active Value: ₹{deals.reduce((acc, d) => acc + (d.deal_value || 0), 0).toLocaleString()}
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {deals.map(deal => (
                  <Card key={deal.id} className="p-4 bg-white border-slate-200 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <Badge className="bg-indigo-50 text-indigo-700 border-indigo-200 font-semibold">{deal.stage?.toUpperCase()}</Badge>
                      <span className="text-xs font-bold text-emerald-600">₹{deal.deal_value?.toLocaleString()}</span>
                    </div>

                    <div>
                      <h4 className="font-bold text-sm text-slate-900">{deal.deal_name || deal.client_name}</h4>
                      <p className="text-xs text-slate-500">{deal.service} • {deal.country}</p>
                    </div>

                    <div className="p-2.5 rounded-lg bg-slate-50 text-xs space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>Probability:</span>
                        <span className="font-bold text-slate-800">{deal.probability || 50}%</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Paid Amount:</span>
                        <span className="font-bold text-emerald-600">₹{(deal.paid_amount || 0).toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Pending Amount:</span>
                        <span className="font-bold text-amber-600">₹{(deal.pending_amount || 0).toLocaleString()}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[10px] text-slate-400">Assigned: {deal.sales_person_name || 'You'}</span>
                      <Select
                        value={deal.stage}
                        onValueChange={async (val) => {
                          await axios.put(`${API}/crm/deals/${deal.id}/stage`, { stage: val }, getAuthHeader());
                          toast.success(`Deal moved to ${val}`);
                          fetchAllCRMData();
                        }}
                      >
                        <SelectTrigger className="w-32 h-7 text-[11px]"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {STAGES.map(s => <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </Card>
                ))}
                {deals.length === 0 && (
                  <div className="col-span-3 p-12 text-center text-slate-400 text-xs italic bg-white rounded-xl border border-slate-200">
                    No active deals in pipeline. Convert a lead or create a deal from the lead workspace.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: WHATSAPP INBOX */}
          {view === 'whatsapp' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex h-[calc(100vh-170px)] overflow-hidden">
              
              {/* Left Inbox Thread List */}
              <div className="w-80 border-r border-slate-200 flex flex-col">
                <div className="p-3 border-b border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                      <MessageCircle className="w-4 h-4 text-emerald-600" /> WhatsApp Live Chat
                    </h4>
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowWhatsAppConfigModal(true)}
                        className="h-7 w-7 p-0 text-slate-400 hover:text-emerald-600"
                        title="Meta WhatsApp Cloud API Settings"
                      >
                        <Settings className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => loadWhatsAppInbox()}
                        className="h-7 w-7 p-0 text-slate-400 hover:text-slate-700"
                        title="Refresh threads"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                  
                  {/* Tabs: All, Unread, Waiting */}
                  <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-lg text-xs">
                    {['all', 'unread', 'waiting_for_reply'].map(t => (
                      <button
                        key={t}
                        onClick={() => setWaInboxTab(t)}
                        className={`py-1 rounded capitalize font-medium transition-colors ${waInboxTab === t ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-500'}`}
                      >
                        {t === 'waiting_for_reply' ? 'Waiting' : t}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
                  {waThreads.map(th => (
                    <div
                      key={th.thread_id}
                      onClick={() => handleSelectWaThread(th)}
                      className={`p-3 cursor-pointer transition-colors ${activeWaThread?.thread_id === th.thread_id ? 'bg-emerald-50/70 border-l-4 border-emerald-600' : 'hover:bg-slate-50'}`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-xs text-slate-900 truncate max-w-[140px]">{th.contact_name}</span>
                        <span className="text-[10px] text-slate-400">{timeAgo(th.last_message_time)}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 truncate">{th.last_message_text}</p>
                      {th.unread_count > 0 && (
                        <Badge className="bg-emerald-600 text-white text-[10px] px-1.5 py-0 mt-1">{th.unread_count} new</Badge>
                      )}
                    </div>
                  ))}
                  {waThreads.length === 0 && (
                    <p className="p-6 text-center text-xs text-slate-400 italic">No WhatsApp conversations found.</p>
                  )}
                </div>
              </div>

              {/* Right Chat Window */}
              <div className="flex-1 flex flex-col bg-slate-50/50">
                {activeWaThread ? (
                  <>
                    <div className="p-3.5 bg-white border-b border-slate-200 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center">
                          {activeWaThread.contact_name?.[0]?.toUpperCase() || 'C'}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-bold text-sm text-slate-900">{activeWaThread.contact_name}</h4>
                            {whatsappSessionStatus?.is_session_active ? (
                              <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px] font-mono">
                                ⚡ 24h Window Active ({whatsappSessionStatus.remaining_hours || 24}h left)
                              </Badge>
                            ) : (
                              <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[10px]">
                                ⏳ Template Required
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 font-mono">{activeWaThread.contact_phone}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setShowWhatsAppConfigModal(true)}
                          className="h-8 px-2 text-slate-500 hover:text-emerald-700 text-xs gap-1"
                        >
                          <Settings className="w-3.5 h-3.5" /> API Setup
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            const matched = leads.find(l => l.id === activeWaThread.lead_id || l.phone === activeWaThread.contact_phone);
                            if (matched) handleOpenLeadWorkspace(matched, 'whatsapp');
                          }}
                          className="text-xs h-8"
                        >
                          Open Lead Profile
                        </Button>
                      </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                      {activeWaMessages.map(msg => {
                        const isOut = msg.direction === 'outbound';
                        return (
                          <div key={msg.id} className={`flex ${isOut ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-md p-3 rounded-xl text-xs space-y-1.5 ${isOut ? 'bg-emerald-600 text-white rounded-br-xs' : 'bg-white text-slate-800 border border-slate-200 rounded-bl-xs shadow-xs'}`}>
                              {/* Media Rendering */}
                              {msg.media_url && (
                                <div className="rounded-lg overflow-hidden my-1">
                                  {msg.media_type === 'image' ? (
                                    <img
                                      src={msg.media_url}
                                      alt="Attachment"
                                      className="max-h-52 w-full object-cover rounded cursor-pointer hover:opacity-95"
                                      onClick={() => window.open(msg.media_url, '_blank')}
                                    />
                                  ) : msg.media_type === 'audio' ? (
                                    <audio controls src={msg.media_url} className="w-full h-8 my-1" />
                                  ) : (
                                    <a
                                      href={msg.media_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className={`flex items-center gap-2 p-2 rounded text-xs font-semibold ${isOut ? 'bg-emerald-700/60 text-white' : 'bg-slate-100 text-slate-800'}`}
                                    >
                                      <Paperclip className="w-3.5 h-3.5" /> {msg.media_filename || 'View Attached Document'}
                                    </a>
                                  )}
                                </div>
                              )}

                              {msg.text && <p className="whitespace-pre-wrap">{msg.text}</p>}

                              <div className={`flex items-center justify-between text-[9px] pt-1 gap-2 ${isOut ? 'text-emerald-100' : 'text-slate-400'}`}>
                                <span>{msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</span>
                                {isOut && (
                                  <span className="flex items-center gap-1 font-semibold">
                                    {msg.status === 'read' ? (
                                      <button
                                        type="button"
                                        onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                        className="flex items-center gap-0.5 text-sky-300 hover:underline cursor-pointer"
                                        title="Click to view message verification & audit details"
                                      >
                                        <CheckCheck className="w-3.5 h-3.5 text-sky-300" /> Read
                                      </button>
                                    ) : msg.status === 'delivered' ? (
                                      <button
                                        type="button"
                                        onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                        className="flex items-center gap-0.5 text-emerald-200 hover:underline cursor-pointer"
                                        title="Click to view message verification & audit details"
                                      >
                                        <CheckCheck className="w-3.5 h-3.5 text-emerald-200" /> Delivered
                                      </button>
                                    ) : msg.status === 'sent' ? (
                                      <button
                                        type="button"
                                        onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                        className="flex items-center gap-0.5 text-emerald-200/90 hover:text-white hover:underline cursor-pointer"
                                        title="Click to view message verification & audit details"
                                      >
                                        <CheckCheck className="w-3.5 h-3.5 text-emerald-200" /> Sent (WhatsApp Web)
                                      </button>
                                    ) : msg.status === 'pending_confirmation' ? (
                                      <button
                                        type="button"
                                        onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                        className="flex items-center gap-1 bg-amber-500/25 px-1.5 py-0.5 rounded text-[9px] text-amber-200 border border-amber-400/30 hover:underline cursor-pointer"
                                        title="Awaiting confirmation — click to verify"
                                      >
                                        <Clock className="w-3 h-3 text-amber-300 animate-pulse" /> Pending Confirmation
                                      </button>
                                    ) : msg.status === 'failed' ? (
                                      <button
                                        type="button"
                                        onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                        className="flex items-center gap-0.5 text-rose-300 hover:underline cursor-pointer"
                                        title={msg.error_message || "Failed — click to view details"}
                                      >
                                        <AlertCircle className="w-3.5 h-3.5 text-rose-300" /> Failed
                                      </button>
                                    ) : (
                                      <button
                                        type="button"
                                        onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                        className="flex items-center gap-0.5 text-emerald-200/70 hover:underline cursor-pointer"
                                      >
                                        <Check className="w-3 h-3" /> Logged
                                      </button>
                                    )}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Media preview tag if selected */}
                    {waAttachedMedia && (
                      <div className="px-4 py-1.5 bg-emerald-50 border-t border-emerald-200/80 flex items-center justify-between text-xs text-emerald-900">
                        <span className="flex items-center gap-1.5 truncate">
                          <Paperclip className="w-3.5 h-3.5 text-emerald-700" /> Attached: <strong>{waAttachedMedia.filename}</strong> ({waAttachedMedia.type})
                        </span>
                        <button
                          type="button"
                          onClick={() => setWaAttachedMedia(null)}
                          className="text-slate-400 hover:text-rose-600 p-0.5"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}

                    <div className="p-3 bg-white border-t border-slate-200 flex items-center gap-2">
                      <input
                        type="file"
                        ref={waFileInputRef}
                        className="hidden"
                        onChange={handleWaMediaUpload}
                      />
                      <Button
                        size="sm"
                        variant="ghost"
                        type="button"
                        onClick={() => waFileInputRef.current?.click()}
                        disabled={waUploadingMedia || waSending}
                        className="h-9 px-2.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50"
                        title="Attach Photo or Document (Max 16MB)"
                      >
                        <Paperclip className={`w-4 h-4 ${waUploadingMedia ? 'animate-spin' : ''}`} />
                      </Button>
                      <Input
                        placeholder="Type WhatsApp message to client (press Enter to send)..."
                        value={waReplyText}
                        onChange={(e) => setWaReplyText(e.target.value)}
                        onKeyDown={async (e) => {
                          if (e.key === 'Enter' && (waReplyText.trim() || waAttachedMedia)) {
                            const leadObj = {
                              id: activeWaThread.lead_id,
                              name: activeWaThread.contact_name,
                              phone: activeWaThread.contact_phone
                            };
                            await handleSendWhatsAppMessage({
                              lead: leadObj,
                              text: waReplyText,
                              mode: 'direct'
                            });
                            setWaReplyText('');
                            if (activeWaThread) handleSelectWaThread(activeWaThread);
                          }
                        }}
                        className="text-xs h-9"
                      />
                      <Button
                        size="sm"
                        onClick={async () => {
                          if (!waReplyText.trim() && !waAttachedMedia) return;
                          const leadObj = {
                            id: activeWaThread.lead_id,
                            name: activeWaThread.contact_name,
                            phone: activeWaThread.contact_phone
                          };
                          await handleSendWhatsAppMessage({
                            lead: leadObj,
                            text: waReplyText,
                            mode: 'direct'
                          });
                          setWaReplyText('');
                          if (activeWaThread) handleSelectWaThread(activeWaThread);
                        }}
                        disabled={waSending}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white h-9 px-3.5 font-semibold gap-1.5"
                      >
                        {waSending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-xs text-slate-400 italic">
                    Select a conversation to start messaging.
                  </div>
                )}
              </div>

            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: CALLS & HISTORY */}
          {view === 'calls' && (
            <div className="space-y-4">
              {/* Header Banner & Action Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div>
                  <h3 className="font-bold text-base text-slate-900 flex items-center gap-2">
                    <PhoneCall className="w-5 h-5 text-emerald-600" /> Calls & Call Center History
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Comprehensive log of all live client calls, voice recordings, durations, consultant notes, and outcomes.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={loadAllCalls}
                    className="h-8 text-xs gap-1.5 text-slate-700"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-slate-500" /> Refresh
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => setShowQuickCallSelectModal(true)}
                    className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 shadow-sm"
                  >
                    <PhoneCall className="w-3.5 h-3.5" /> Start New Call
                  </Button>
                </div>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Calls</p>
                      <h4 className="text-xl font-bold text-slate-900 mt-1">{calls.length}</h4>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                      <Phone className="w-5 h-5" />
                    </div>
                  </div>
                </Card>

                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Connected</p>
                      <h4 className="text-xl font-bold text-emerald-600 mt-1">
                        {calls.filter(c => c.status === 'connected' || (c.duration_seconds && c.duration_seconds > 0)).length}
                      </h4>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <PhoneCall className="w-5 h-5" />
                    </div>
                  </div>
                </Card>

                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Talk Time</p>
                      <h4 className="text-xl font-bold text-indigo-600 mt-1">
                        {formatCallDuration(calls.reduce((acc, c) => acc + (c.duration_seconds || 0), 0))}
                      </h4>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                      <Clock className="w-5 h-5" />
                    </div>
                  </div>
                </Card>

                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Recordings</p>
                      <h4 className="text-xl font-bold text-amber-600 mt-1">
                        {calls.filter(c => !!c.recording_url).length}
                      </h4>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                      <Disc className="w-5 h-5" />
                    </div>
                  </div>
                </Card>
              </div>

              {/* Filters and Search Bar */}
              <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm space-y-2.5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="relative flex-1">
                    <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                    <Input
                      placeholder="Search client, phone, consultant, notes, transcript, requirements, concerns..."
                      value={callSearch}
                      onChange={(e) => setCallSearch(e.target.value)}
                      className="pl-9 h-9 text-xs"
                    />
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs">
                      {['all', 'outgoing', 'incoming'].map((dir) => (
                        <button
                          key={dir}
                          onClick={() => setCallFilterDirection(dir)}
                          className={`px-2.5 py-1 rounded capitalize font-medium transition-colors ${callFilterDirection === dir ? 'bg-white text-slate-900 shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'}`}
                        >
                          {dir}
                        </button>
                      ))}
                    </div>

                    <Select value={callFilterOutcome} onValueChange={setCallFilterOutcome}>
                      <SelectTrigger className="h-9 w-40 text-xs">
                        <SelectValue placeholder="All Outcomes" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Outcomes</SelectItem>
                        <SelectItem value="interested">Interested</SelectItem>
                        <SelectItem value="callback_requested">Callback Requested</SelectItem>
                        <SelectItem value="document_collection">Document Collection</SelectItem>
                        <SelectItem value="needs_followup">Needs Follow-up</SelectItem>
                        <SelectItem value="no_answer">No Answer / Busy</SelectItem>
                        <SelectItem value="wrong_number">Wrong Number</SelectItem>
                      </SelectContent>
                    </Select>

                    {isAdmin && (
                      <Select value={callFilterSalesperson} onValueChange={setCallFilterSalesperson}>
                        <SelectTrigger className="h-9 w-44 text-xs">
                          <User className="w-3.5 h-3.5 mr-1 text-slate-400" />
                          <SelectValue placeholder="All Salespersons" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Salespersons</SelectItem>
                          {salesReps.map((rep) => (
                            <SelectItem key={rep.id} value={rep.id}>
                              {rep.name || rep.email}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}

                    <Select value={callDatePreset} onValueChange={handleDatePresetChange}>
                      <SelectTrigger className="h-9 w-36 text-xs">
                        <Calendar className="w-3.5 h-3.5 mr-1 text-slate-400" />
                        <SelectValue placeholder="Date Range" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Time</SelectItem>
                        <SelectItem value="today">Today</SelectItem>
                        <SelectItem value="yesterday">Yesterday</SelectItem>
                        <SelectItem value="this_week">Last 7 Days</SelectItem>
                        <SelectItem value="this_month">This Month</SelectItem>
                        <SelectItem value="custom">Custom Range</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Custom Date Range Picker Bar */}
                {(callDatePreset === 'custom' || callDateFrom || callDateTo) && (
                  <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
                    <span className="font-semibold text-slate-700 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" /> Date Filter:
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-slate-500">From</span>
                      <Input
                        type="date"
                        value={callDateFrom}
                        onChange={(e) => setCallDateFrom(e.target.value)}
                        className="h-8 text-xs w-36 bg-slate-50 border-slate-300"
                      />
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-slate-500">To</span>
                      <Input
                        type="date"
                        value={callDateTo}
                        onChange={(e) => setCallDateTo(e.target.value)}
                        className="h-8 text-xs w-36 bg-slate-50 border-slate-300"
                      />
                    </div>
                    {(callDateFrom || callDateTo) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setCallDateFrom('');
                          setCallDateTo('');
                          setCallDatePreset('all');
                        }}
                        className="h-8 px-2 text-xs text-slate-500 hover:text-slate-800"
                      >
                        <X className="w-3.5 h-3.5 mr-1" /> Reset Dates
                      </Button>
                    )}
                  </div>
                )}
              </div>

              {/* Call Records List */}
              <div className="space-y-3">
                {filteredCalls.map((c) => {
                  const matchedLead = leads.find(l => l.id === c.lead_id || (c.lead_phone && l.phone === c.lead_phone));
                  const isOut = c.direction === 'outgoing' || !c.direction;
                  return (
                    <Card key={c.id} className="p-4 bg-white border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                      <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                        {/* Call Metadata & Contact Info */}
                        <div className="flex items-start gap-3">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${isOut ? 'bg-blue-50 text-blue-600' : 'bg-emerald-50 text-emerald-600'}`}>
                            {isOut ? <PhoneOutgoing className="w-5 h-5" /> : <PhoneIncoming className="w-5 h-5" />}
                          </div>

                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <button
                                onClick={() => {
                                  if (matchedLead) handleOpenLeadWorkspace(matchedLead);
                                }}
                                className="font-bold text-sm text-slate-900 hover:text-emerald-600 hover:underline text-left"
                              >
                                {c.lead_name || matchedLead?.name || 'Unknown Client'}
                              </button>
                              <Badge className={`text-[10px] px-2 py-0.5 capitalize font-semibold ${isOut ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                                {c.direction || 'outgoing'}
                              </Badge>
                              {c.outcome && (
                                <Badge variant="outline" className="text-[10px] px-2 py-0.5 capitalize font-semibold bg-slate-50 text-slate-700">
                                  {c.outcome.replace(/_/g, ' ')}
                                </Badge>
                              )}
                              {c.duration_seconds > 0 && (
                                <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                                  ⏱️ {formatCallDuration(c.duration_seconds)}
                                </span>
                              )}
                            </div>

                            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                              <span className="font-mono text-slate-700 font-medium">
                                📞 {formatPhoneNumber(c.lead_phone || matchedLead?.phone) || 'No phone'}
                              </span>
                              <span>•</span>
                              <span>Advisor: <strong className="text-slate-700">{c.sales_person_name || 'LEAMSS Consultant'}</strong></span>
                              <span>•</span>
                              <span title={c.created_at ? new Date(c.created_at).toLocaleString() : ''}>
                                {timeAgo(c.created_at)} ({c.created_at ? new Date(c.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'})
                              </span>
                            </div>

                            {/* Call Consultation Notes */}
                            {c.notes && (
                              <div className="mt-2 p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-700">
                                <span className="font-semibold text-slate-900">Notes:</span> {c.notes}
                              </div>
                            )}

                            {/* Inline Audio Player for Call Recording */}
                            {c.recording_url ? (
                              <div className="pt-2">
                                <CallAudioPlayer
                                  recordingUrl={c.recording_url}
                                  durationSeconds={c.duration_seconds}
                                  callerName={c.lead_name || matchedLead?.name}
                                />
                              </div>
                            ) : (
                              <p className="text-[11px] text-slate-400 italic pt-1">
                                No audio recording captured for this call session.
                              </p>
                            )}

                            {/* AI Call Intelligence & Summary Section */}
                            <div className="mt-3 rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/50 via-purple-50/25 to-white p-3 shadow-xs">
                              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-indigo-100/80">
                                <div className="flex items-center gap-2">
                                  <div className="w-6 h-6 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                                    <Sparkles className="w-3.5 h-3.5" />
                                  </div>
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-xs font-bold text-slate-900">
                                      AI Call Summary & Requirements
                                    </span>
                                    {c.ai_sentiment && (
                                      <Badge className={`text-[10px] px-1.5 py-0 font-semibold border ${
                                        c.ai_sentiment.toLowerCase() === 'positive' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                                        c.ai_sentiment.toLowerCase() === 'negative' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                                        'bg-slate-100 text-slate-700 border-slate-200'
                                      }`}>
                                        {c.ai_sentiment} Sentiment
                                      </Badge>
                                    )}
                                  </div>
                                </div>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={regeneratingAiCalls[c.id]}
                                  onClick={() => handleRegenerateAiSummary(c.id)}
                                  className="h-6 px-2 text-[11px] text-indigo-700 border-indigo-200 hover:bg-indigo-50 gap-1 font-semibold"
                                  title="Regenerate structured AI analysis"
                                >
                                  <RefreshCw className={`w-3 h-3 ${regeneratingAiCalls[c.id] ? 'animate-spin' : ''}`} />
                                  {regeneratingAiCalls[c.id] ? 'Analyzing...' : 'Refresh AI Summary'}
                                </Button>
                              </div>

                              {/* 4-part Structured Intelligence Grid */}
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 text-xs">
                                <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                  <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                    <span>📌</span>
                                    <span>Main Discussion</span>
                                  </div>
                                  <p className="text-slate-600 text-xs leading-relaxed">
                                    {c.ai_summary_structured?.main_discussion || c.ai_summary || c.notes || 'Discussion notes pending analysis.'}
                                  </p>
                                </div>

                                <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                  <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                    <span>🎯</span>
                                    <span>Client Requirements</span>
                                  </div>
                                  <p className="text-slate-600 text-xs leading-relaxed">
                                    {c.ai_summary_structured?.client_requirements || 'Standard consultation requirement.'}
                                  </p>
                                </div>

                                <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                  <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                    <span>⚠️</span>
                                    <span>Concerns & Objections</span>
                                  </div>
                                  <p className="text-slate-600 text-xs leading-relaxed">
                                    {c.ai_summary_structured?.concerns || 'None noted during consultation.'}
                                  </p>
                                </div>

                                <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                  <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                    <span>⏭️</span>
                                    <span>Next Steps</span>
                                  </div>
                                  <p className="text-slate-700 text-xs leading-relaxed font-semibold text-indigo-950">
                                    {c.ai_summary_structured?.next_steps || c.next_best_action || 'Follow up with client as scheduled.'}
                                  </p>
                                </div>
                              </div>
                            </div>

                            {/* Complete Call Transcript Section */}
                            <div className="mt-2.5 rounded-xl border border-slate-200 bg-slate-50/70 p-3 shadow-xs">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                  <div className="w-6 h-6 rounded-lg bg-slate-800 text-white flex items-center justify-center shadow-xs">
                                    <FileText className="w-3.5 h-3.5" />
                                  </div>
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-xs font-bold text-slate-900">Complete Call Transcript</span>
                                    {c.transcript && c.transcript.trim() ? (
                                      <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px] font-semibold px-2 py-0">
                                        ✓ Full Conversation Captured
                                      </Badge>
                                    ) : (
                                      <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-200 text-[10px] font-medium px-2 py-0">
                                        Transcript Unavailable
                                      </Badge>
                                    )}
                                  </div>
                                </div>

                                <div className="flex items-center gap-1.5 flex-wrap">
                                  {c.transcript && c.transcript.trim() ? (
                                    <>
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => {
                                          navigator.clipboard.writeText(c.transcript);
                                          toast.success('Transcript copied to clipboard!');
                                        }}
                                        className="h-6 px-2 text-[11px] text-slate-600 hover:text-slate-900 gap-1 font-semibold"
                                      >
                                        <Copy className="w-3 h-3" /> Copy
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleOpenTranscriptModal(c)}
                                        className="h-6 px-2 text-[11px] text-indigo-700 border-indigo-200 hover:bg-indigo-50 gap-1 font-semibold"
                                      >
                                        <Edit className="w-3 h-3" /> Edit
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="secondary"
                                        onClick={() => toggleTranscript(c.id)}
                                        className="h-6 px-2 text-[11px] font-bold gap-1 bg-slate-200 hover:bg-slate-300 text-slate-800"
                                      >
                                        {expandedTranscripts[c.id] ? (
                                          <>Hide Dialogue <ChevronDown className="w-3 h-3 rotate-180 transition-transform" /></>
                                        ) : (
                                          <>Read Transcript ({c.transcript.split('\n').length} lines) <ChevronDown className="w-3 h-3 transition-transform" /></>
                                        )}
                                      </Button>
                                    </>
                                  ) : (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => handleOpenTranscriptModal(c)}
                                      className="h-6 px-2.5 text-[11px] text-indigo-700 border-indigo-200 bg-white hover:bg-indigo-50 gap-1 font-bold shadow-2xs"
                                    >
                                      <Plus className="w-3 h-3" /> Add / Attach Transcript
                                    </Button>
                                  )}
                                </div>
                              </div>

                              {/* Expanded Verbatim Conversation Transcript */}
                              {c.transcript && c.transcript.trim() && expandedTranscripts[c.id] && (
                                <div className="mt-2.5 pt-2 border-t border-slate-200">
                                  <div className="max-h-60 overflow-y-auto rounded-lg bg-slate-900 text-slate-100 p-3 font-mono text-xs leading-relaxed shadow-inner border border-slate-800 whitespace-pre-wrap select-text">
                                    {c.transcript}
                                  </div>
                                </div>
                              )}

                              {/* Genuine Status Note When Transcript Unavailable (No dummy data) */}
                              {(!c.transcript || !c.transcript.trim()) && (
                                <div className="mt-2 text-[11px] text-slate-500 bg-white/80 p-2 rounded-lg border border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                                  <div className="flex items-center gap-1.5 text-amber-700">
                                    <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                                    <span>
                                      {c.transcription_status_reason || 'Audio stream not transcribed / No dialogue transcript was attached for this call.'}
                                    </span>
                                  </div>
                                  <button
                                    onClick={() => handleOpenTranscriptModal(c)}
                                    className="text-[11px] text-indigo-600 hover:underline font-semibold whitespace-nowrap self-start sm:self-auto"
                                  >
                                    Click to paste conversation →
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Quick Direct Actions on each Call Record */}
                        <div className="flex flex-wrap md:flex-col items-center gap-1.5 shrink-0 self-end md:self-auto">
                          <Button
                            size="sm"
                            onClick={() => handleStartCall(matchedLead || { id: c.lead_id, name: c.lead_name, phone: c.lead_phone, email: c.lead_email })}
                            className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1 shadow-sm w-full sm:w-auto"
                          >
                            <PhoneCall className="w-3 h-3" /> Call Again
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleOpenEmailModal('', '', null, matchedLead || { id: c.lead_id, name: c.lead_name, phone: c.lead_phone, email: c.lead_email })}
                            className="h-7 text-xs text-indigo-700 border-indigo-200 hover:bg-indigo-50 gap-1 font-semibold w-full sm:w-auto"
                          >
                            <Mail className="w-3 h-3" /> Email
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleWhatsAppCall(c.lead_phone || matchedLead?.phone)}
                            className="h-7 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 gap-1 font-semibold w-full sm:w-auto"
                          >
                            <MessageCircle className="w-3 h-3" /> WhatsApp
                          </Button>
                          {matchedLead && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleOpenLeadWorkspace(matchedLead)}
                              className="h-7 text-xs text-slate-600 hover:text-slate-900 gap-1 w-full sm:w-auto"
                            >
                              Client Profile →
                            </Button>
                          )}
                        </div>
                      </div>
                    </Card>
                  );
                })}

                {filteredCalls.length === 0 && (
                  <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-3">
                    <PhoneOff className="w-10 h-10 text-slate-300 mx-auto" />
                    <h4 className="font-bold text-slate-700 text-sm">No Call Records Found</h4>
                    <p className="text-xs text-slate-400 max-w-sm mx-auto">
                      {callSearch || callFilterOutcome !== 'all' || callFilterDirection !== 'all'
                        ? 'No calls match the selected search or filter criteria. Try resetting filters.'
                        : 'No calls have been logged yet. Click "Start New Call" above or call directly from any client profile.'}
                    </p>
                    <Button
                      size="sm"
                      onClick={() => setShowQuickCallSelectModal(true)}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs"
                    >
                      <PhoneCall className="w-3.5 h-3.5 mr-1" /> Start First Call
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: EMAIL CENTER */}
          {(view === 'emails' || view === 'email') && (
            <div className="space-y-4">
              {/* Header Banner & Action Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div>
                  <h3 className="font-bold text-base text-slate-900 flex items-center gap-2">
                    <Mail className="w-5 h-5 text-indigo-600" /> Email Center & Communication Hub
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Centralized email inbox and outbox with client threads, bidirectional sync, and fast replies.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleSyncMailbox()}
                    disabled={syncingMailbox}
                    className="h-8 text-xs gap-1.5 border-indigo-200 text-indigo-700 hover:bg-indigo-50 font-semibold"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${syncingMailbox ? 'animate-spin' : ''}`} />
                    {syncingMailbox ? 'Syncing Mailbox...' : 'Sync Mailbox (IMAP)'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      loadMyMailbox();
                      loadUserSignature();
                      setEmailSettingsTab('signature');
                      setShowMailboxModal(true);
                    }}
                    className="h-8 text-xs gap-1.5 border-slate-200 text-slate-700 hover:bg-slate-50 font-semibold shadow-2xs"
                  >
                    <Settings className="w-3.5 h-3.5 text-slate-500" />
                    Email Settings
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      const target = (activeConversation?.lead || (activeConversation?.email ? { name: activeConversation.name, email: activeConversation.email, id: activeConversation.lead_id } : null)) || selectedLead || (leads.length > 0 ? leads[0] : null);
                      if (target) {
                        handleOpenEmailModal('', '', null, target);
                      } else {
                        toast.error('No leads available to email');
                      }
                    }}
                    className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-bold gap-1.5 shadow-sm"
                  >
                    <Send className="w-3.5 h-3.5" /> Compose Email
                  </Button>
                </div>
              </div>

              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Emails</p>
                      <h4 className="text-xl font-bold text-slate-900 mt-1">{allEmails.length}</h4>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                      <Mail className="w-5 h-5" />
                    </div>
                  </div>
                </Card>

                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Client Conversations</p>
                      <h4 className="text-xl font-bold text-indigo-600 mt-1">
                        {clientConversations.length}
                      </h4>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                      <Users className="w-5 h-5" />
                    </div>
                  </div>
                </Card>

                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Inbound Replies</p>
                      <h4 className="text-xl font-bold text-emerald-600 mt-1">
                        {allEmails.filter(e => e.direction === 'inbound' || e.direction === 'incoming').length}
                      </h4>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <Inbox className="w-5 h-5" />
                    </div>
                  </div>
                </Card>

                <Card className="p-3.5 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Sync Status</p>
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        <span className="text-xs font-bold text-emerald-700">IMAP / SMTP Ready</span>
                      </div>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  </div>
                </Card>
              </div>

              {/* Master-Detail Split: Left Client Sidebar + Right Conversation View */}
              {allEmailsLoading ? (
                <div className="p-12 text-center text-slate-400 space-y-2 bg-white rounded-xl border border-slate-200">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-500" />
                  <p className="text-xs">Loading email threads and correspondence...</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                  {/* ──────────────────────────────────────────────────────── */}
                  {/* LEFT SIDEBAR: CLIENT LIST (CLEAN SEPARATE BOXES) */}
                  {/* ──────────────────────────────────────────────────────── */}
                  <div className="lg:col-span-4 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[750px] overflow-hidden">
                    {/* Sidebar Header: Search & Filters */}
                    <div className="p-3.5 border-b border-slate-200 space-y-2.5 bg-slate-50/70 shrink-0">
                      <div className="flex items-center justify-between">
                        <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                          <Users className="w-3.5 h-3.5 text-indigo-600" /> Clients ({clientConversations.length})
                        </h4>
                        <span className="text-[11px] font-medium text-slate-500">
                          {filteredClientConversations.length} shown
                        </span>
                      </div>

                      {/* Search Bar */}
                      <div className="relative">
                        <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                        <Input
                          placeholder="Search client, email, subject..."
                          value={emailCenterSearch}
                          onChange={(e) => setEmailCenterSearch(e.target.value)}
                          className="pl-8 h-8 text-xs bg-white border-slate-200"
                        />
                        {emailCenterSearch && (
                          <button
                            onClick={() => setEmailCenterSearch('')}
                            className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 text-xs"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      {/* Direction Tabs */}
                      <div className="flex items-center gap-1 bg-slate-200/60 p-1 rounded-lg text-xs">
                        {[
                          { key: 'all', label: `All (${clientConversations.length})` },
                          { key: 'inbound', label: `Replies (${clientConversations.filter(c => c.hasInboundReply).length})` },
                          { key: 'outbound', label: `Sent (${clientConversations.filter(c => c.outboundCount > 0).length})` }
                        ].map((tab) => (
                          <button
                            key={tab.key}
                            onClick={() => setEmailFilterDirection(tab.key)}
                            className={`flex-1 py-1 px-1 rounded-md font-semibold text-[11px] transition-colors ${
                              emailFilterDirection === tab.key
                                ? 'bg-white text-indigo-700 shadow-xs font-bold'
                                : 'text-slate-600 hover:text-slate-900'
                            }`}
                          >
                            {tab.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Scrollable Client Box List */}
                    <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
                      {filteredClientConversations.map((c) => {
                        const isSelected = activeConversation?.email?.toLowerCase() === c.email?.toLowerCase();
                        return (
                          <div
                            key={c.email}
                            onClick={() => {
                              setSelectedEmailClientKey(c.email);
                              if (conversationPaneRef.current && typeof window !== 'undefined' && window.innerWidth < 1024) {
                                conversationPaneRef.current.scrollIntoView({ behavior: 'smooth' });
                              }
                            }}
                            className={`p-3 rounded-xl border text-left cursor-pointer transition-all duration-150 relative ${
                              isSelected
                                ? 'bg-indigo-50/90 border-indigo-500 shadow-xs ring-1 ring-indigo-500/20'
                                : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/80 shadow-xs'
                            }`}
                          >
                            {/* Top row: Avatar + Name + Time */}
                            <div className="flex items-start gap-2.5">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
                                isSelected
                                  ? 'bg-indigo-600 text-white'
                                  : 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                              }`}>
                                {getInitials(c.name)}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-1">
                                  <h5 className="font-bold text-xs text-slate-900 truncate">
                                    {c.name}
                                  </h5>
                                  <span className="text-[10px] text-slate-400 font-medium shrink-0">
                                    {timeAgo(c.latestDate)}
                                  </span>
                                </div>
                                <p className="text-[11px] text-slate-500 truncate font-mono mt-0.5">
                                  {c.email}
                                </p>
                              </div>
                            </div>

                            {/* Middle row: Latest Subject snippet */}
                            <p className="text-xs text-slate-600 truncate mt-2 font-medium">
                              {c.latestSubject || '(No Subject)'}
                            </p>

                            {/* Bottom row: Status & Count Badges */}
                            <div className="flex flex-wrap items-center gap-1.5 mt-2">
                              {c.hasInboundReply && (
                                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                                  <Inbox className="w-2.5 h-2.5" /> Reply Received
                                </span>
                              )}
                              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                                {c.emails.length} msg{c.emails.length > 1 ? 's' : ''}
                              </span>
                              {c.lead?.status && (
                                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
                                  {c.lead.status}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}

                      {filteredClientConversations.length === 0 && (
                        <div className="p-8 text-center text-slate-400 space-y-2">
                          <Inbox className="w-8 h-8 mx-auto text-slate-300" />
                          <p className="text-xs font-semibold text-slate-700">No client conversations found</p>
                          <p className="text-[11px] text-slate-400 max-w-xs mx-auto">
                            {emailCenterSearch || emailFilterDirection !== 'all'
                              ? 'Try adjusting your search query or direction filter.'
                              : 'No emails recorded in CRM yet. Click "Compose Email" or "Sync Mailbox" to get started.'}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* ──────────────────────────────────────────────────────── */}
                  {/* RIGHT COLUMN: ACTIVE CLIENT CONVERSATION THREAD */}
                  {/* ──────────────────────────────────────────────────────── */}
                  <div ref={conversationPaneRef} className="lg:col-span-8 flex flex-col h-[750px] bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    {activeConversation ? (
                      <>
                        {/* Conversation Header: Client Name, Email, Subject, Actions */}
                        <div className="p-4 border-b border-slate-200 bg-white shrink-0">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div className="flex items-center gap-3 min-w-0">
                              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-600 text-white font-bold text-sm flex items-center justify-center shrink-0 shadow-xs">
                                {getInitials(activeConversation.name)}
                              </div>
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <h3 className="font-bold text-base text-slate-900 truncate">
                                    {activeConversation.name}
                                  </h3>
                                  {activeConversation.lead?.status && (
                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 uppercase tracking-wider">
                                      {activeConversation.lead.status}
                                    </span>
                                  )}
                                </div>
                                <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-500 mt-0.5">
                                  <span className="font-medium text-slate-600 flex items-center gap-1 font-mono">
                                    <Mail className="w-3 h-3 text-slate-400" />
                                    {activeConversation.email}
                                  </span>
                                  {activeConversation.lead?.phone && (
                                    <>
                                      <span className="text-slate-300">•</span>
                                      <span className="flex items-center gap-1 text-slate-600 font-mono">
                                        <Phone className="w-3 h-3 text-slate-400" />
                                        {activeConversation.lead.phone}
                                      </span>
                                    </>
                                  )}
                                  <span className="text-slate-300">•</span>
                                  <span className="font-medium text-indigo-700">
                                    {activeConversation.emails.length} total messages
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Header Quick Action Buttons */}
                            <div className="flex items-center gap-2 shrink-0">
                              <Button
                                size="sm"
                                onClick={() => {
                                  const subj = activeConversation.latestSubject?.startsWith('Re:')
                                    ? activeConversation.latestSubject
                                    : `Re: ${activeConversation.latestSubject || ''}`;
                                  const targetLead = activeConversation.lead || {
                                    id: activeConversation.lead_id,
                                    name: activeConversation.name,
                                    email: activeConversation.email
                                  };
                                  handleOpenEmailModal(subj, '', activeConversation.latestEmail?.thread_id, targetLead);
                                }}
                                className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-bold gap-1.5 shadow-xs"
                              >
                                <Send className="w-3.5 h-3.5" /> Compose / Reply
                              </Button>
                              {activeConversation.lead && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleStartCall(activeConversation.lead)}
                                  className="h-8 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 gap-1 font-semibold"
                                >
                                  <PhoneCall className="w-3.5 h-3.5" /> Call Client
                                </Button>
                              )}
                              {activeConversation.lead && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleOpenLeadWorkspace(activeConversation.lead, 'emails')}
                                  className="h-8 text-xs text-slate-600 hover:text-slate-900 gap-1 font-semibold"
                                >
                                  CRM Profile →
                                </Button>
                              )}
                            </div>
                          </div>

                          {/* Subject Line Strip */}
                          <div className="flex items-center justify-between gap-3 mt-3 pt-3 border-t border-slate-100 text-xs">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Subject:</span>
                              <span className="font-bold text-slate-900 truncate">
                                {activeConversation.latestSubject || '(No Subject)'}
                              </span>
                              {activeConversation.latestEmail?.thread_id && (
                                <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                                  thread: {activeConversation.latestEmail.thread_id.slice(-8)}
                                </span>
                              )}
                            </div>
                            <button
                              onClick={() => setEmailCenterThreadSortAsc(prev => !prev)}
                              className="text-[11px] font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1 shrink-0"
                            >
                              <ArrowUpDown className="w-3 h-3" />
                              {emailCenterThreadSortAsc ? 'Oldest on Top' : 'Newest on Top'}
                            </button>
                          </div>
                        </div>

                        {/* Scrollable Complete Thread Messages */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/60">
                          {(emailCenterThreadSortAsc ? activeConversation.emails : [...activeConversation.emails].reverse()).map((item) => {
                            const isInbound = item.direction === 'inbound' || item.direction === 'incoming';
                            return (
                              <div
                                key={item.id}
                                className={`rounded-xl border transition-all overflow-hidden bg-white shadow-xs ${
                                  isInbound ? 'border-emerald-200/90' : 'border-slate-200'
                                }`}
                              >
                                {/* Message Header Strip */}
                                <div className={`px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b ${
                                  isInbound ? 'bg-emerald-50/60 border-emerald-100' : 'bg-slate-50/80 border-slate-100'
                                }`}>
                                  <div className="flex items-center gap-2.5 min-w-0">
                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1 shrink-0 ${
                                      isInbound ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 'bg-blue-100 text-blue-800 border border-blue-200'
                                    }`}>
                                      {isInbound ? <Inbox className="w-3 h-3" /> : <Send className="w-3 h-3" />}
                                      {isInbound ? 'Client Reply' : 'Sent by Advisor'}
                                    </span>
                                    <div className="flex items-baseline gap-1.5 truncate">
                                      <span className="text-xs font-bold text-slate-900 truncate">
                                        {isInbound ? (item.contact_name || activeConversation.name) : (item.sales_person_name || currentUser?.name || 'Pooja')}
                                      </span>
                                      <span className="text-[11px] text-slate-500 font-mono truncate">
                                        &lt;{item.from_email}&gt;
                                      </span>
                                    </div>
                                  </div>

                                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                                    {item.notify_by_email && (
                                      <span className="text-[10px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-1.5 py-0.5 rounded">
                                        Gmail Notified
                                      </span>
                                    )}
                                    {item.status && (
                                      <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-white text-slate-600 border border-slate-200">
                                        {item.status}
                                      </span>
                                    )}
                                    <span className="text-[11px] text-slate-500 font-medium whitespace-nowrap" title={item.created_at ? new Date(item.created_at).toLocaleString() : ''}>
                                      {timeAgo(item.created_at || item.sent_at)} ({new Date(item.created_at || item.sent_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })})
                                    </span>
                                  </div>
                                </div>

                                {/* Metadata bar: To, Cc, Subject */}
                                <div className="px-4 py-2 bg-slate-50/40 border-b border-slate-100 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                                  <div>
                                    <span className="text-slate-400 font-medium">To: </span>
                                    <strong className="text-slate-800 font-mono text-[11px]">{item.to_email}</strong>
                                  </div>
                                  {item.cc && (
                                    <>
                                      <span className="text-slate-300">•</span>
                                      <div>
                                        <span className="text-slate-400 font-medium">Cc: </span>
                                        <strong className="text-slate-800 font-mono text-[11px]">{item.cc}</strong>
                                      </div>
                                    </>
                                  )}
                                  {item.subject && (
                                    <>
                                      <span className="text-slate-300">•</span>
                                      <div className="truncate max-w-lg">
                                        <span className="text-slate-400 font-medium">Subject: </span>
                                        <span className="font-semibold text-slate-800">{item.subject}</span>
                                      </div>
                                    </>
                                  )}
                                </div>

                                {/* Message Body Content */}
                                <div className="p-4 text-xs text-slate-800 leading-relaxed font-sans overflow-x-auto">
                                  {item.body_html ? (
                                    <div
                                      className="prose prose-xs max-w-none text-slate-800 space-y-2 [&_p]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_a]:text-indigo-600 [&_a]:underline"
                                      dangerouslySetInnerHTML={{ __html: item.body_html }}
                                    />
                                  ) : (
                                    <p className="whitespace-pre-wrap font-sans text-slate-800">{item.raw_text || '(No content)'}</p>
                                  )}
                                </div>

                                {/* Attachments if any */}
                                {item.attachments && item.attachments.length > 0 && (
                                  <div className="px-4 py-2 bg-slate-50/80 border-t border-slate-100 flex flex-wrap gap-2 items-center">
                                    <span className="text-[11px] font-semibold text-slate-500 flex items-center gap-1">
                                      <Paperclip className="w-3 h-3 text-slate-400" /> Attachments ({item.attachments.length}):
                                    </span>
                                    {item.attachments.map((att, attIdx) => {
                                      const attUrl = att.url || (att.saved_filename ? `${process.env.REACT_APP_BACKEND_URL || ''}/api/crm/emails/attachments/${att.saved_filename}` : null);
                                      return (
                                        <a
                                          key={att.id || attIdx}
                                          href={attUrl || '#'}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center gap-1.5 bg-white border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/40 rounded-md px-2 py-0.5 text-xs text-slate-700 transition-colors shadow-2xs font-medium"
                                        >
                                          <FileText className="w-3 h-3 text-indigo-500" />
                                          <span className="truncate max-w-[140px]">{att.filename}</span>
                                          {att.size && <span className="text-[10px] text-slate-400">({(att.size / 1024).toFixed(0)} KB)</span>}
                                        </a>
                                      );
                                    })}
                                  </div>
                                )}

                                {/* Footer info */}
                                {item.delivery_info && (
                                  <div className="px-4 py-1.5 bg-slate-50 border-t border-slate-100 text-[10px] text-slate-400 italic">
                                    Gateway info: {item.delivery_info}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>

                        {/* Quick Inline Reply Footer */}
                        <div className="p-3.5 border-t border-slate-200 bg-white shrink-0 space-y-2.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                              <MessageSquareReply className="w-3.5 h-3.5 text-indigo-600" />
                              Quick Reply to {activeConversation.name}
                            </span>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                const subj = activeConversation.latestSubject?.startsWith('Re:')
                                  ? activeConversation.latestSubject
                                  : `Re: ${activeConversation.latestSubject || ''}`;
                                const targetLead = activeConversation.lead || {
                                  id: activeConversation.lead_id,
                                  name: activeConversation.name,
                                  email: activeConversation.email
                                };
                                handleOpenEmailModal(subj, '', activeConversation.latestEmail?.thread_id, targetLead);
                              }}
                              className="h-6 text-[11px] text-indigo-700 hover:bg-indigo-50 font-semibold gap-1"
                            >
                              Use Admin Template instead →
                            </Button>
                          </div>

                          <Textarea
                            rows={2}
                            placeholder={`Type a direct reply to ${activeConversation.name}... (Delivered from your sales mailbox)`}
                            value={emailCenterQuickReplyText}
                            onChange={(e) => setEmailCenterQuickReplyText(e.target.value)}
                            className="text-xs bg-white border-slate-300 focus:border-indigo-500 font-normal resize-none"
                          />

                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-slate-700 select-none">
                              <input
                                type="checkbox"
                                checked={emailCenterQuickNotify}
                                onChange={(e) => setEmailCenterQuickNotify(e.target.checked)}
                                className="w-3.5 h-3.5 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300"
                              />
                              <span>Notify me by email (CC to my Gmail inbox)</span>
                            </label>

                            <Button
                              size="sm"
                              onClick={() => handleSendEmailCenterQuickReply(activeConversation)}
                              disabled={sendingEmailCenterReply || !emailCenterQuickReplyText.trim()}
                              className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-bold gap-1 shadow-xs self-end sm:self-auto"
                            >
                              {sendingEmailCenterReply ? (
                                <>
                                  <RefreshCw className="w-3 h-3 animate-spin" /> Sending...
                                </>
                              ) : (
                                <>
                                  <Send className="w-3 h-3" /> Send Reply
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      </>
                    ) : (
                      <div className="h-full flex items-center justify-center p-8 text-center text-slate-400">
                        <div className="space-y-3">
                          <Mail className="w-10 h-10 text-slate-300 mx-auto" />
                          <h4 className="font-bold text-slate-700 text-sm">Select a Client Conversation</h4>
                          <p className="text-xs text-slate-400 max-w-sm">
                            Choose a client from the list on the left to view their complete email thread, message details, and send replies.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: MEETINGS & CONSULTATIONS HUB */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'meetings' && (
            <div className="space-y-4">
              {/* Header Banner & Action Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div>
                  <h3 className="font-bold text-base text-slate-900 flex items-center gap-2">
                    <Video className="w-5 h-5 text-indigo-600" /> Video Consultations & Meetings Hub
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Generate real Google Meet, Zoom, and Calendly consultation links, share invitations via WhatsApp & Email, and track client attendance.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={loadMeetings}
                    className="h-8 text-xs gap-1.5 text-slate-700 bg-white"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${meetingsLoading ? 'animate-spin' : ''}`} /> Refresh
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      setSelectedLead(null);
                      setShowMeetingModal(true);
                    }}
                    className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-bold gap-1.5 shadow-sm"
                  >
                    <Plus className="w-3.5 h-3.5" /> Schedule Consultation
                  </Button>
                </div>
              </div>

              {/* KPI Summary Cards */}
              {(() => {
                const todayStr = new Date().toISOString().split('T')[0];
                const totalCount = meetings.length;
                const upcomingCount = meetings.filter(m => m.status === 'scheduled' && (!m.meeting_date || m.meeting_date >= todayStr)).length;
                const completedCount = meetings.filter(m => m.status === 'completed').length;
                const cancelledCount = meetings.filter(m => m.status === 'cancelled').length;
                const rescheduledCount = meetings.filter(m => m.status === 'rescheduled').length;

                return (
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    {/* Card 1: Total Meetings */}
                    <Card
                      onClick={() => setMeetingFilter('all')}
                      className={`p-3.5 bg-white border cursor-pointer transition-all hover:shadow-md ${
                        meetingFilter === 'all' ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Meetings</p>
                          <h4 className="text-xl font-bold text-slate-900 mt-1">{totalCount}</h4>
                        </div>
                        <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                          <Video className="w-5 h-5" />
                        </div>
                      </div>
                    </Card>

                    {/* Card 2: Upcoming Meetings */}
                    <Card
                      onClick={() => setMeetingFilter('upcoming')}
                      className={`p-3.5 bg-white border cursor-pointer transition-all hover:shadow-md ${
                        meetingFilter === 'upcoming' ? 'border-blue-500 ring-2 ring-blue-200' : 'border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Upcoming</p>
                          <h4 className="text-xl font-bold text-blue-600 mt-1">{upcomingCount}</h4>
                        </div>
                        <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                          <Calendar className="w-5 h-5" />
                        </div>
                      </div>
                    </Card>

                    {/* Card 3: Completed Meetings */}
                    <Card
                      onClick={() => setMeetingFilter('completed')}
                      className={`p-3.5 bg-white border cursor-pointer transition-all hover:shadow-md ${
                        meetingFilter === 'completed' ? 'border-emerald-500 ring-2 ring-emerald-200' : 'border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Completed</p>
                          <h4 className="text-xl font-bold text-emerald-600 mt-1">{completedCount}</h4>
                        </div>
                        <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                          <CheckCircle2 className="w-5 h-5" />
                        </div>
                      </div>
                    </Card>

                    {/* Card 4: Cancelled Meetings */}
                    <Card
                      onClick={() => setMeetingFilter('cancelled')}
                      className={`p-3.5 bg-white border cursor-pointer transition-all hover:shadow-md ${
                        meetingFilter === 'cancelled' ? 'border-rose-500 ring-2 ring-rose-200' : 'border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Cancelled</p>
                          <h4 className="text-xl font-bold text-rose-600 mt-1">{cancelledCount}</h4>
                        </div>
                        <div className="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                          <AlertCircle className="w-5 h-5" />
                        </div>
                      </div>
                    </Card>

                    {/* Card 5: Rescheduled Meetings */}
                    <Card
                      onClick={() => setMeetingFilter('rescheduled')}
                      className={`p-3.5 bg-white border cursor-pointer transition-all hover:shadow-md ${
                        meetingFilter === 'rescheduled' ? 'border-amber-500 ring-2 ring-amber-200' : 'border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Rescheduled</p>
                          <h4 className="text-xl font-bold text-amber-600 mt-1">{rescheduledCount}</h4>
                        </div>
                        <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                          <RefreshCw className="w-5 h-5" />
                        </div>
                      </div>
                    </Card>
                  </div>
                );
              })()}

              {/* Filters & Search Bar */}
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { key: 'all', label: 'All Meetings' },
                    { key: 'upcoming', label: 'Upcoming' },
                    { key: 'completed', label: 'Completed' },
                    { key: 'rescheduled', label: 'Rescheduled' },
                    { key: 'cancelled', label: 'Cancelled' },
                    { key: 'calendly', label: 'Calendly' },
                    { key: 'google_meet', label: 'Google Meet' },
                    { key: 'zoom', label: 'Zoom' }
                  ].map(tab => (
                    <button
                      key={tab.key}
                      onClick={() => setMeetingFilter(tab.key)}
                      className={`px-3 py-1.5 text-xs rounded-lg font-semibold transition-all ${
                        meetingFilter === tab.key
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="relative w-full md:w-64">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                  <Input
                    placeholder="Search by client, phone, title..."
                    value={meetingSearch}
                    onChange={(e) => setMeetingSearch(e.target.value)}
                    className="pl-8 h-8 text-xs bg-slate-50 border-slate-200"
                  />
                </div>
              </div>

              {/* Meetings List */}
              {meetingsLoading ? (
                <div className="text-center py-16 bg-white rounded-xl border border-slate-200 space-y-2">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600" />
                  <p className="text-xs text-slate-500">Loading scheduled meetings...</p>
                </div>
              ) : (() => {
                const todayStr = new Date().toISOString().split('T')[0];
                const filteredMeetings = meetings.filter(m => {
                  if (meetingSearch) {
                    const q = meetingSearch.toLowerCase();
                    const textMatch =
                      (m.title || '').toLowerCase().includes(q) ||
                      (m.contact_name || '').toLowerCase().includes(q) ||
                      (m.contact_phone || '').includes(q) ||
                      (m.contact_email || '').toLowerCase().includes(q) ||
                      (m.notes || '').toLowerCase().includes(q);
                    if (!textMatch) return false;
                  }

                  if (meetingFilter === 'upcoming') {
                    return m.status === 'scheduled' && (!m.meeting_date || m.meeting_date >= todayStr);
                  }
                  if (meetingFilter === 'completed') {
                    return m.status === 'completed';
                  }
                  if (meetingFilter === 'cancelled') {
                    return m.status === 'cancelled';
                  }
                  if (meetingFilter === 'rescheduled') {
                    return m.status === 'rescheduled';
                  }
                  if (meetingFilter === 'google_meet') {
                    return String(m.meeting_type).toLowerCase().includes('google');
                  }
                  if (meetingFilter === 'zoom') {
                    return String(m.meeting_type).toLowerCase() === 'zoom';
                  }
                  if (meetingFilter === 'calendly') {
                    return String(m.meeting_type).toLowerCase() === 'calendly' || m.source === 'calendly';
                  }
                  return true;
                });

                if (filteredMeetings.length === 0) {
                  return (
                    <div className="text-center py-16 bg-white rounded-xl border border-slate-200 p-6 space-y-3">
                      <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                        <Video className="w-6 h-6" />
                      </div>
                      <h4 className="font-bold text-slate-800 text-sm">No Consultations Found</h4>
                      <p className="text-xs text-slate-400 max-w-sm mx-auto">
                        {meetingSearch || meetingFilter !== 'all'
                          ? 'No meetings match your current filters. Try resetting the filter.'
                          : 'You have not scheduled any Google Meet, Zoom, or Calendly consultations yet.'}
                      </p>
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedLead(null);
                          setShowMeetingModal(true);
                        }}
                        className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm"
                      >
                        <Plus className="w-3.5 h-3.5" /> Schedule First Consultation
                      </Button>
                    </div>
                  );
                }

                return (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {filteredMeetings.map(m => {
                      const isZoom = String(m.meeting_type).toLowerCase() === 'zoom';
                      const isCalendly = String(m.meeting_type).toLowerCase() === 'calendly';
                      const matchedLead = leads.find(l => l.id === m.lead_id)
                        || (m.contact_phone ? leads.find(l => (l.phone && l.phone.includes(m.contact_phone)) || (l.whatsapp_number && l.whatsapp_number.includes(m.contact_phone))) : null)
                        || (m.contact_email ? leads.find(l => l.email && l.email.toLowerCase() === String(m.contact_email).toLowerCase()) : null);

                      const clientName = m.contact_name || matchedLead?.name || matchedLead?.full_name || 'Prospect';
                      const clientPhone = m.contact_phone || matchedLead?.phone || matchedLead?.whatsapp_number || '';
                      const clientEmail = m.contact_email || matchedLead?.email || '';
                      const cleanPhone = getSanitizedWhatsAppNumber(clientPhone);

                      const inviteMessage = isCalendly
                        ? `Dear ${clientName},\n\nYour consultation booking link with ${m.sales_person_name || currentUser?.name || 'LEAMSS Consultant'} is ready!\n\n📅 Date: ${m.meeting_date}\n⏰ Time: ${m.meeting_time} (${m.duration_minutes || 30} mins)\n💻 Platform: Calendly\n🔗 Book / Join Link: ${m.meeting_link}\n\nPlease select your preferred consultation slot or join at the scheduled time.\n\nBest regards,\n${m.sales_person_name || currentUser?.name || 'LEAMSS'}`
                        : `Dear ${clientName},\n\nYour consultation meeting with ${m.sales_person_name || currentUser?.name || 'LEAMSS Consultant'} is scheduled!\n\n📅 Date: ${m.meeting_date}\n⏰ Time: ${m.meeting_time} (${m.duration_minutes || 30} mins)\n💻 Platform: ${isZoom ? 'Zoom' : 'Google Meet'}\n🔗 Join Link: ${m.meeting_link}${m.meeting_password ? `\n🔑 Passcode: ${m.meeting_password}` : ''}\n\nPlease join 2 minutes prior. Let me know if you need to reschedule.\n\nBest regards,\n${m.sales_person_name || currentUser?.name || 'LEAMSS'}`;

                      return (
                        <Card key={m.id} className="p-4 bg-white border-slate-200 hover:border-slate-300 shadow-sm space-y-3 transition-all rounded-xl">
                          {/* Card Header */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2.5">
                              <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                                isCalendly
                                  ? 'bg-sky-50 text-sky-600 border border-sky-200'
                                  : isZoom
                                    ? 'bg-blue-50 text-blue-600 border border-blue-200'
                                    : 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                              }`}>
                                {isCalendly ? <Calendar className="w-5 h-5 text-sky-600" /> : <Video className="w-5 h-5" />}
                              </div>
                              <div>
                                <h4 className="font-bold text-sm text-slate-900 leading-snug">{m.title || 'Client Consultation'}</h4>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <Badge className={`text-[10px] font-semibold py-0 ${
                                    isCalendly
                                      ? 'bg-sky-100 text-sky-800 border-sky-200'
                                      : isZoom
                                        ? 'bg-blue-100 text-blue-800 border-blue-200'
                                        : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                                  }`}>
                                    {isCalendly ? 'Calendly' : (isZoom ? 'Zoom Meeting' : 'Google Meet')}
                                  </Badge>
                                  {m.source && (
                                    <Badge variant="outline" className="text-[10px] py-0 text-slate-500 border-slate-200">
                                      {m.source.toUpperCase()}
                                    </Badge>
                                  )}
                                  <span className="text-[11px] text-slate-400">
                                    Duration: <strong>{m.duration_minutes || 30}m</strong>
                                  </span>
                                </div>
                              </div>
                            </div>

                            <Badge className={`text-[10px] font-bold ${
                              m.status === 'completed' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' :
                              m.status === 'cancelled' ? 'bg-rose-100 text-rose-800 border-rose-300' :
                              m.status === 'rescheduled' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                              'bg-blue-100 text-blue-800 border-blue-300'
                            }`}>
                              {(m.status || 'Scheduled').toUpperCase()}
                            </Badge>
                          </div>

                          {/* Client Information & Communication Strip */}
                          <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200/90 space-y-2.5 text-xs">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              {/* Left: Client Contact Details */}
                              <div>
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Client / Prospect</span>
                                <div className="mt-0.5">
                                  {matchedLead ? (
                                    <button
                                      type="button"
                                      onClick={() => handleOpenLeadWorkspace(matchedLead, 'timeline')}
                                      className="font-bold text-sm text-slate-900 hover:text-indigo-600 hover:underline flex items-center gap-1 text-left"
                                    >
                                      {clientName}
                                      <ArrowUpRight className="w-3.5 h-3.5 text-indigo-500" />
                                    </button>
                                  ) : (
                                    <span className="font-bold text-sm text-slate-900 block">{clientName}</span>
                                  )}
                                </div>

                                <div className="space-y-1 mt-1.5">
                                  <div className="text-[11px] text-slate-600 font-mono flex items-center gap-1.5">
                                    <Phone className="w-3 h-3 text-slate-400 flex-shrink-0" />
                                    <span>{clientPhone ? formatPhoneNumber(clientPhone) : <span className="text-slate-400 font-sans italic">No phone on file</span>}</span>
                                  </div>
                                  <div className="text-[11px] text-slate-600 flex items-center gap-1.5 truncate">
                                    <Mail className="w-3 h-3 text-slate-400 flex-shrink-0" />
                                    <span className="truncate">{clientEmail || <span className="text-slate-400 italic">No email on file</span>}</span>
                                  </div>
                                </div>
                              </div>

                              {/* Right: Consultation Date, Time & Rep */}
                              <div>
                                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Date & Time</span>
                                <div className="mt-0.5">
                                  <span className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                                    <Calendar className="w-3.5 h-3.5 text-indigo-600" /> {m.meeting_date} at {m.meeting_time}
                                  </span>
                                </div>
                                <div className="mt-1.5 text-[11px] text-slate-500">
                                  <span>Assigned Rep: </span>
                                  <strong className="text-slate-700">{m.sales_person_name || currentUser?.name || 'Consultant'}</strong>
                                </div>
                              </div>
                            </div>

                            {/* Prominent Client Communication Bar: WhatsApp Message & Email / Mail Box */}
                            <div className="pt-2 border-t border-slate-200/70 flex flex-wrap items-center gap-2">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  if (!cleanPhone) {
                                    toast.error('No valid phone number found for this client to send WhatsApp message.');
                                    return;
                                  }
                                  const waUrl = getDirectWhatsAppWebLink(cleanPhone, inviteMessage);
                                  if (waUrl) {
                                    window.open(waUrl, '_blank');
                                    toast.success(`Opening WhatsApp Web for ${clientName}`);
                                  }
                                }}
                                disabled={!cleanPhone}
                                className={`h-7 px-2.5 text-xs font-semibold gap-1.5 shadow-2xs transition-all ${
                                  cleanPhone
                                    ? 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-300'
                                    : 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed opacity-60'
                                }`}
                                title={cleanPhone ? `Send WhatsApp consultation invite / message to ${cleanPhone}` : 'No phone number available'}
                              >
                                <MessageCircle className="w-3.5 h-3.5 text-emerald-600" />
                                <span>WhatsApp Message</span>
                              </Button>

                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  const subject = `Scheduled Consultation: ${m.title || 'LEAMSS Consultation'} - ${m.meeting_date} at ${m.meeting_time}`;
                                  handleOpenEmailModal(
                                    subject,
                                    inviteMessage,
                                    null,
                                    matchedLead || { id: m.lead_id, name: clientName, email: clientEmail, phone: clientPhone }
                                  );
                                }}
                                className="h-7 px-2.5 text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-800 border-indigo-200 gap-1.5 shadow-2xs transition-all"
                                title={clientEmail ? `Send consultation invite / email to ${clientEmail}` : 'Open CRM Email Composer'}
                              >
                                <Mail className="w-3.5 h-3.5 text-indigo-600" />
                                <span>Email / Mail Box</span>
                              </Button>
                            </div>
                          </div>

                          {/* Passcode or Agenda (if exists) */}
                          {((isZoom && m.meeting_password) || m.notes) && (
                            <div className="flex items-center justify-between text-xs bg-slate-50 p-2 rounded border border-slate-200/60">
                              {m.notes && (
                                <span className="text-slate-600 text-[11px] truncate max-w-[280px]">
                                  <strong>Agenda:</strong> {m.notes}
                                </span>
                              )}
                              {isZoom && m.meeting_password && (
                                <span className="text-[11px] font-mono text-slate-700 bg-white px-1.5 py-0.5 rounded border border-slate-200 ml-auto">
                                  Passcode: <strong>{m.meeting_password}</strong>
                                </span>
                              )}
                            </div>
                          )}

                          {/* Real Meeting Link Bar */}
                          {m.meeting_link && (
                            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between gap-2">
                              <code className="text-[11px] font-mono text-slate-700 truncate max-w-[240px]">
                                {m.meeting_link}
                              </code>
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  navigator.clipboard.writeText(m.meeting_link);
                                  toast.success('Meeting link copied to clipboard!');
                                }}
                                className="h-6 px-2 text-[11px] text-slate-600 hover:text-slate-900 gap-1"
                              >
                                <Copy className="w-3 h-3" /> Copy
                              </Button>
                            </div>
                          )}

                          {/* Action Buttons: Join, Reschedule, Notes, Edit Link, Status */}
                          <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-1.5">
                              {m.meeting_link && (
                                <Button
                                  size="sm"
                                  onClick={() => window.open(m.meeting_link, '_blank')}
                                  className="h-7 px-3 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-bold gap-1.5 shadow-sm flex-shrink-0"
                                >
                                  {isCalendly ? <Calendar className="w-3.5 h-3.5" /> : <Video className="w-3.5 h-3.5" />}
                                  <span>{isCalendly ? 'Open Calendly' : 'Join Meeting'}</span>
                                </Button>
                              )}

                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleOpenRescheduleModal(m)}
                                className="h-7 text-xs bg-white hover:bg-amber-50 text-amber-800 border-amber-300 gap-1 font-semibold flex-shrink-0"
                                title="Reschedule meeting date & time"
                              >
                                <RefreshCw className="w-3 h-3 text-amber-600" />
                                <span>Reschedule</span>
                              </Button>

                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleOpenRecapModal(m)}
                                className="h-7 text-xs bg-white hover:bg-indigo-50 text-indigo-700 border-indigo-200 gap-1 font-medium flex-shrink-0"
                                title="View or edit meeting recording, transcript & AI summary"
                              >
                                <FileText className="w-3 h-3 text-indigo-600" />
                                <span>Notes & Transcript</span>
                              </Button>

                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleOpenEditMeetingLink(m.id, m.meeting_link, m.title, m)}
                                className="h-7 text-xs bg-white hover:bg-slate-50 text-slate-700 border-slate-300 gap-1 font-medium flex-shrink-0"
                                title="Update meeting room link"
                              >
                                <Pencil className="w-3 h-3 text-slate-500" />
                                <span>Edit Link</span>
                              </Button>
                            </div>

                            <div className="flex items-center gap-1.5 ml-auto flex-shrink-0">
                              {m.status !== 'completed' && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleUpdateMeetingStatus(m.id, 'completed')}
                                  className="h-7 px-2 text-[11px] text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 gap-1 font-medium"
                                  title="Mark Completed"
                                >
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                  <span>Complete</span>
                                </Button>
                              )}
                              {m.status !== 'cancelled' && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleDeleteMeeting(m.id)}
                                  className="h-7 px-2 text-[11px] text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                                  title="Cancel Meeting"
                                >
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              )}
                            </div>
                          </div>

                          {/* Reschedule Reason Banner */}
                          {m.reschedule_reason && (
                            <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-amber-900 text-xs flex items-start gap-2">
                              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                              <div>
                                <span className="font-bold text-[10px] uppercase tracking-wide text-amber-800 block">Reschedule Reason:</span>
                                <p className="text-[11px] text-amber-950 font-medium">{m.reschedule_reason}</p>
                              </div>
                            </div>
                          )}

                          {/* Reschedule History (Audit Trail) */}
                          {Array.isArray(m.reschedule_history) && m.reschedule_history.length > 0 && (
                            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1.5">
                              <div
                                className="flex items-center justify-between cursor-pointer select-none"
                                onClick={() => setExpandedHistoryId(expandedHistoryId === m.id ? null : m.id)}
                              >
                                <span className="font-semibold text-slate-700 flex items-center gap-1.5 text-[11px]">
                                  <RefreshCw className="w-3 h-3 text-amber-600" /> Reschedule Audit History ({m.reschedule_history.length})
                                </span>
                                <span className="text-[10px] text-indigo-600 font-medium hover:underline">
                                  {expandedHistoryId === m.id ? 'Hide History ▲' : 'View Audit Trail ▼'}
                                </span>
                              </div>
                              {expandedHistoryId === m.id && (
                                <div className="space-y-1.5 pt-1 border-t border-slate-200">
                                  {m.reschedule_history.map((h, hIdx) => (
                                    <div key={hIdx} className="bg-white p-2 rounded border border-slate-200 text-[11px] space-y-0.5">
                                      <div className="flex items-center justify-between text-slate-400 text-[10px]">
                                        <span>Rescheduled by: <strong>{h.rescheduled_by_name || 'Staff'}</strong></span>
                                        <span>{h.rescheduled_at ? new Date(h.rescheduled_at).toLocaleString() : ''}</span>
                                      </div>
                                      <p className="text-slate-800">
                                        Shifted from <span className="line-through text-slate-400">{h.old_date} {h.old_time}</span> to <strong className="text-amber-800">{h.new_date} at {h.new_time}</strong>
                                      </p>
                                      <p className="text-amber-900 font-medium">
                                        <strong>Reason:</strong> {h.reason}
                                      </p>
                                      {h.notes && <p className="text-slate-500 text-[10px]">Note: {h.notes}</p>}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Meeting Recording, Transcript & AI Summary */}
                          {m.recap && (
                            <div className="p-3 bg-gradient-to-r from-indigo-50/70 via-sky-50/50 to-white rounded-lg border border-indigo-200/80 text-xs space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
                                  <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Meeting Notes, Transcript & AI Summary
                                </span>
                                <div className="flex items-center gap-2">
                                  {m.calendly_event_id && (
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant="ghost"
                                      disabled={syncingRecapId === m.id}
                                      onClick={() => handleSyncRecap(m.id)}
                                      className="h-6 px-1.5 text-[10px] text-indigo-700 hover:bg-indigo-100 gap-1 font-medium"
                                    >
                                      <RefreshCw className={`w-3 h-3 ${syncingRecapId === m.id ? 'animate-spin' : ''}`} />
                                      Sync Calendly
                                    </Button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => setExpandedRecapId(expandedRecapId === m.id ? null : m.id)}
                                    className="text-[11px] text-indigo-600 font-semibold hover:underline"
                                  >
                                    {expandedRecapId === m.id ? 'Collapse ▲' : 'View Full Details ▼'}
                                  </button>
                                </div>
                              </div>

                              {m.recap.recording_url && (
                                <div className="flex items-center justify-between bg-white p-2 rounded border border-indigo-100 text-[11px]">
                                  <span className="text-slate-700 flex items-center gap-1.5 font-medium">
                                    <Video className="w-3.5 h-3.5 text-indigo-600" /> Meeting Video Recording
                                  </span>
                                  <a
                                    href={m.recap.recording_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-indigo-600 font-bold hover:underline flex items-center gap-1"
                                  >
                                    Watch Recording <ExternalLink className="w-3 h-3" />
                                  </a>
                                </div>
                              )}

                              {m.recap.summary && (
                                <div className="bg-white p-2.5 rounded border border-indigo-100 space-y-1">
                                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide block">Executive Summary</span>
                                  <p className="text-slate-800 text-[11px] whitespace-pre-wrap leading-relaxed">{m.recap.summary}</p>
                                </div>
                              )}

                              {expandedRecapId === m.id && (
                                <div className="space-y-2 pt-1 border-t border-indigo-100">
                                  {Array.isArray(m.recap.participants) && m.recap.participants.length > 0 && (
                                    <div className="text-[11px] text-slate-700">
                                      <strong>Participants:</strong> {m.recap.participants.join(', ')}
                                    </div>
                                  )}

                                  {Array.isArray(m.recap.action_items) && m.recap.action_items.length > 0 && (
                                    <div className="bg-white p-2 rounded border border-indigo-100 space-y-1">
                                      <strong className="text-[11px] text-emerald-800 block">Action Items:</strong>
                                      <ul className="list-disc list-inside text-[11px] text-slate-700 space-y-0.5">
                                        {m.recap.action_items.map((act, aIdx) => (
                                          <li key={aIdx}>{act}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}

                                  {m.recap.transcripts && (
                                    <div className="bg-white p-2.5 rounded border border-indigo-100 space-y-1">
                                      <strong className="text-[11px] text-slate-700 block">Full Dialogue Transcript:</strong>
                                      <div className="max-h-40 overflow-y-auto text-[10px] font-mono text-slate-600 whitespace-pre-wrap bg-slate-50 p-2 rounded border border-slate-200">
                                        {m.recap.transcripts}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </Card>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: FOLLOW-UPS */}
          {view === 'followups' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div>
                  <h3 className="font-bold text-sm text-slate-900">Scheduled Follow-ups & Reminders</h3>
                  <p className="text-xs text-slate-500">Upcoming client follow-ups, payment reminders, and escalation tracking</p>
                </div>
                <Badge className="bg-amber-100 text-amber-800 text-xs font-bold">
                  {followUps.filter(f => f.status === 'pending').length} Pending Follow-ups
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {followUps.map(fu => (
                  <Card key={fu.id} className="p-4 bg-white border-slate-200 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <Badge className={`text-xs font-semibold ${fu.priority === 'urgent' ? 'bg-rose-100 text-rose-800' : 'bg-blue-100 text-blue-800'}`}>
                        {fu.type} • {fu.priority?.toUpperCase()}
                      </Badge>
                      <span className={`text-xs font-bold ${fu.is_overdue ? 'text-rose-600' : 'text-slate-600'}`}>
                        {fu.is_overdue && '⚠️ '} {fu.scheduled_at ? new Date(fu.scheduled_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'No date'}
                      </span>
                    </div>

                    <div>
                      <h4 className="font-bold text-sm text-slate-900">{fu.lead_name || 'Prospect'}</h4>
                      <p className="text-xs text-slate-600 mt-1">{fu.notes || fu.message || 'Consultation follow-up'}</p>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-[10px] text-slate-400">Assigned: {fu.assigned_to_name || 'You'}</span>
                      {fu.status === 'pending' ? (
                        <Button
                          size="sm"
                          onClick={async () => {
                            await axios.put(`${API}/crm/follow-ups/${fu.id}/status`, { status: 'completed', outcome: 'Discussion completed' }, getAuthHeader());
                            toast.success('Follow-up marked completed');
                            fetchAllCRMData();
                          }}
                          className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          <Check className="w-3.5 h-3.5 mr-1" /> Complete
                        </Button>
                      ) : (
                        <Badge className="bg-slate-100 text-slate-600 text-xs">Completed</Badge>
                      )}
                    </div>
                  </Card>
                ))}
                {followUps.length === 0 && (
                  <div className="col-span-3 p-12 text-center text-slate-400 text-xs italic bg-white rounded-xl border border-slate-200">
                    No follow-ups scheduled yet.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: PAYMENTS & INVOICES */}
          {view === 'payments' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                <div>
                  <h3 className="font-bold text-sm text-slate-900">CRM Sales Payments</h3>
                  <p className="text-xs text-slate-500">Track package payments, retainers, and invoice transactions</p>
                </div>
              </div>

              <Card className="bg-white border-slate-200 shadow-sm overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
                    <tr>
                      <th className="p-3 pl-4">Receipt #</th>
                      <th className="p-3">Client / Lead</th>
                      <th className="p-3">Package</th>
                      <th className="p-3">Total Amount</th>
                      <th className="p-3">Paid Amount</th>
                      <th className="p-3">Status</th>
                      <th className="p-3">Payment Method</th>
                      <th className="p-3 pr-4">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {payments.map(p => (
                      <tr key={p.id} className="hover:bg-slate-50/60">
                        <td className="p-3 pl-4 font-mono font-semibold text-emerald-700">{p.receipt_number || p.transaction_id}</td>
                        <td className="p-3 font-bold text-slate-900">{p.client_name}</td>
                        <td className="p-3 text-slate-600">{p.package_name}</td>
                        <td className="p-3 font-semibold text-slate-800">₹{p.final_amount?.toLocaleString()}</td>
                        <td className="p-3 font-bold text-emerald-600">₹{p.paid_amount?.toLocaleString()}</td>
                        <td className="p-3">
                          <Badge className={p.payment_status === 'paid' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}>
                            {p.payment_status?.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="p-3 text-slate-600">{p.payment_method}</td>
                        <td className="p-3 pr-4 text-slate-500">{p.payment_date}</td>
                      </tr>
                    ))}
                    {payments.length === 0 && (
                      <tr>
                        <td colSpan={8} className="p-8 text-center text-slate-400 italic">No payment records found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </Card>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: MY PERFORMANCE */}
          {view === 'performance' && performance && (
            <div className="space-y-6">
              <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl shadow-sm flex items-center justify-between">
                <div>
                  <Badge className="bg-indigo-500/30 text-indigo-200 border-indigo-400/30 font-semibold mb-2">SALES SCORECARD</Badge>
                  <h3 className="text-xl font-bold">{performance.sales_person_name}</h3>
                  <p className="text-xs text-indigo-200 mt-1">Real-time KPI tracker across calls, communications, deals won, and revenue</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-indigo-300">Conversion Rate</p>
                  <p className="text-3xl font-black text-emerald-400">{performance.conversion_rate}%</p>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Card className="p-4 bg-white border-slate-200 shadow-sm text-center">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Leads Assigned</p>
                  <h4 className="text-2xl font-bold text-slate-900 mt-1">{performance.leads_assigned}</h4>
                </Card>
                <Card className="p-4 bg-white border-slate-200 shadow-sm text-center">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Connected Calls</p>
                  <h4 className="text-2xl font-bold text-blue-600 mt-1">{performance.connected_calls}</h4>
                  <p className="text-[10px] text-slate-400 mt-1">{performance.total_call_duration_minutes} mins total</p>
                </Card>
                <Card className="p-4 bg-white border-slate-200 shadow-sm text-center">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Deals Won</p>
                  <h4 className="text-2xl font-bold text-emerald-600 mt-1">{performance.deals_won}</h4>
                </Card>
                <Card className="p-4 bg-white border-slate-200 shadow-sm text-center">
                  <p className="text-xs text-slate-500 uppercase font-semibold">Revenue Generated</p>
                  <h4 className="text-2xl font-bold text-slate-900 mt-1">₹{(performance.total_revenue / 100000).toFixed(1)}L</h4>
                </Card>
              </div>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: CAMPAIGNS ROI */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'campaigns' && (
            <div className="space-y-6">
              {/* Top Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Campaigns</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">{campaigns.length}</h3>
                      <p className="text-[11px] text-emerald-600 font-medium mt-1">
                        {campaigns.filter(c => c.status === 'active').length} Active Campaigns
                      </p>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                      <Zap className="w-5 h-5 fill-amber-500 text-amber-500" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Ad Budget</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">
                        ₹{(campaigns.reduce((acc, c) => acc + (c.budget || 0), 0) / 1000).toFixed(0)}k
                      </h3>
                      <p className="text-[11px] text-slate-500 mt-1">Across Meta & Google</p>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                      <DollarSign className="w-5 h-5 text-blue-600" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Leads Acquired</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">
                        {campaigns.reduce((acc, c) => acc + (c.lead_count || 0), 0)}
                      </h3>
                      <p className="text-[11px] text-slate-500 mt-1">
                        {campaigns.reduce((acc, c) => acc + (c.converted_leads || 0), 0)} Converted Clients
                      </p>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                      <Users className="w-5 h-5 text-emerald-600" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Revenue</p>
                      <h3 className="text-2xl font-bold text-emerald-600 mt-1">
                        ₹{(campaigns.reduce((acc, c) => acc + (c.revenue || 0), 0) / 100000).toFixed(1)}L
                      </h3>
                      <p className="text-[11px] text-emerald-700 font-semibold mt-1">
                        {campaigns.reduce((acc, c) => acc + (c.budget || 0), 0) > 0 ?
                          `${(campaigns.reduce((acc, c) => acc + (c.revenue || 0), 0) / Math.max(1, campaigns.reduce((acc, c) => acc + (c.budget || 0), 0))).toFixed(1)}x Overall ROI` : 'Positive ROI'}
                      </p>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
                      <TrendingUp className="w-5 h-5 text-purple-600" />
                    </div>
                  </div>
                </Card>
              </div>

              {/* Campaigns Table Card */}
              <Card className="bg-white border-slate-200 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-slate-900">Active & Historical Campaigns</h3>
                    <p className="text-xs text-slate-500">Live conversion tracking and return on ad spend (ROAS)</p>
                  </div>
                  <Badge className="bg-slate-100 text-slate-700 text-xs">{campaigns.length} Campaigns</Badge>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                        <th className="p-3 pl-4">Campaign Name & Source</th>
                        <th className="p-3">Target Country & Service</th>
                        <th className="p-3">Duration</th>
                        <th className="p-3">Budget</th>
                        <th className="p-3">Leads</th>
                        <th className="p-3">Converted</th>
                        <th className="p-3">Conv. Rate</th>
                        <th className="p-3">Revenue</th>
                        <th className="p-3">ROI</th>
                        <th className="p-3 pr-4 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {campaigns.map(c => {
                        const roi = c.budget > 0 ? ((c.revenue || 0) / c.budget).toFixed(1) : '—';
                        return (
                          <tr key={c.id} className="hover:bg-slate-50/60 transition-colors">
                            <td className="p-3 pl-4">
                              <p className="font-bold text-slate-900">{c.name}</p>
                              <p className="text-[11px] text-slate-500">{c.source}</p>
                            </td>
                            <td className="p-3">
                              <p className="font-medium text-slate-800">{c.target_country}</p>
                              <p className="text-[11px] text-slate-400">{c.target_service}</p>
                            </td>
                            <td className="p-3 text-slate-600">
                              <p>{c.start_date || 'Ongoing'}</p>
                              <p className="text-[10px] text-slate-400">to {c.end_date || 'Open'}</p>
                            </td>
                            <td className="p-3 font-semibold text-slate-900">₹{c.budget?.toLocaleString()}</td>
                            <td className="p-3">
                              <span className="font-bold text-slate-800">{c.lead_count || 0}</span>
                              <span className="text-[10px] text-slate-400 block">{c.qualified_leads || 0} qualified</span>
                            </td>
                            <td className="p-3 font-bold text-emerald-600">{c.converted_leads || 0}</td>
                            <td className="p-3 font-semibold text-slate-700">{c.conversion_rate || 0}%</td>
                            <td className="p-3 font-bold text-slate-900">₹{(c.revenue || 0)?.toLocaleString()}</td>
                            <td className="p-3 font-bold text-emerald-600">{roi !== '—' ? `${roi}x` : '—'}</td>
                            <td className="p-3 pr-4 text-right">
                              <Badge className={c.status === 'active' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}>
                                {c.status?.toUpperCase()}
                              </Badge>
                            </td>
                          </tr>
                        );
                      })}
                      {campaigns.length === 0 && (
                        <tr>
                          <td colSpan={10} className="p-8 text-center text-slate-400 italic">No marketing campaigns found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: SLA & AUTOMATION */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'automation' && (
            <div className="space-y-6">
              {/* Top Summary Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="p-4 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Automation Rules</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">{automationRules.length || 3}</h3>
                      <p className="text-[11px] text-emerald-600 font-medium mt-1">100% Live & Enforced</p>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
                      <Bot className="w-5 h-5 text-purple-600" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">First-Response SLA Rate</p>
                      <h3 className="text-2xl font-bold text-emerald-600 mt-1">94.8%</h3>
                      <p className="text-[11px] text-slate-500 mt-1">Target: Within 15 minutes</p>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                      <Clock className="w-5 h-5 text-emerald-600" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4 bg-white border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Auto-Routing Desk</p>
                      <h3 className="text-2xl font-bold text-slate-900 mt-1">Enabled</h3>
                      <p className="text-[11px] text-slate-500 mt-1">Round-robin & Geo-routing</p>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                      <GitMerge className="w-5 h-5 text-blue-600" />
                    </div>
                  </div>
                </Card>
              </div>

              {/* Automation Rules Grid */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-sm text-slate-900">Configured SLA & Automation Triggers</h3>
                    <p className="text-xs text-slate-500">Automated lead routing, escalation workflows, and task triggers</p>
                  </div>
                  <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-medium">All Systems Operational</Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(automationRules.length > 0 ? automationRules : [
                    {
                      id: 'rule_canada_auto_assign',
                      name: 'Canada Leads Auto-Assignment',
                      condition: 'Country = Canada or Service = Canada PR',
                      action: 'Assign to Canada Sales Team & Create Call Task',
                      enabled: true
                    },
                    {
                      id: 'rule_sla_15min_contact',
                      name: 'New Lead 15-Minute SLA',
                      condition: 'New Lead uncontacted after 15 mins',
                      action: 'Trigger Overdue Notification & Escalation to Sales Manager',
                      enabled: true
                    },
                    {
                      id: 'rule_payment_handover_trigger',
                      name: 'Full Payment Case Handover Trigger',
                      condition: 'Payment Status = Paid (100%)',
                      action: 'Auto-notify Admin and enable 1-Click Case Manager Handover',
                      enabled: true
                    },
                    {
                      id: 'rule_meeting_reminder',
                      name: 'Consultation Meeting 30-min Reminder',
                      condition: 'Scheduled Meeting starts in 30 minutes',
                      action: 'Auto-dispatch WhatsApp & Email reminder link to client',
                      enabled: true
                    }
                  ]).map(rule => (
                    <Card key={rule.id} className="p-4 bg-white border-slate-200 shadow-sm space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-bold text-xs text-slate-900 flex items-center gap-1.5">
                            <Bot className="w-3.5 h-3.5 text-indigo-600" />
                            {rule.name}
                          </h4>
                          <span className="text-[10px] font-mono text-slate-400 mt-0.5 block">{rule.id}</span>
                        </div>
                        <Badge className="bg-emerald-100 text-emerald-800 text-[10px] font-semibold">Active</Badge>
                      </div>

                      <div className="p-2.5 bg-slate-50 rounded-lg text-xs space-y-1.5 border border-slate-100">
                        <p className="text-slate-600">
                          <strong className="text-slate-800 font-semibold">IF:</strong> {rule.condition}
                        </p>
                        <p className="text-indigo-700">
                          <strong className="text-indigo-900 font-semibold">THEN:</strong> {rule.action}
                        </p>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                        <span>Trigger Mode: Instant Event-Driven</span>
                        <span className="text-emerald-600 font-medium">Automatic</span>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: EMAIL TEMPLATES (ADMIN CRM MANAGEMENT) */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'email_templates' && (
            <div className="space-y-4">
              {isAdmin ? (
                <EmailTemplatesManager isEmbedded={true} onBackToHub={() => setView('dashboard')} />
              ) : (
                <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
                  <ShieldAlert className="w-12 h-12 text-amber-500 mx-auto mb-3" />
                  <h3 className="text-base font-semibold text-slate-900">Access Restricted</h3>
                  <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">Only administrators can create and manage email templates. You can use approved templates when sending emails to clients.</p>
                  <Button className="mt-4" onClick={() => setView('dashboard')}>Return to Dashboard</Button>
                </div>
              )}
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: WHATSAPP TEMPLATES (ADMIN CRM MANAGEMENT) */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'whatsapp_templates' && (
            <div className="space-y-4">
              {isAdmin ? (
                <WhatsAppTemplatesManager isEmbedded={true} onBackToHub={() => setView('dashboard')} onTemplateSaved={loadWhatsAppTemplates} />
              ) : (
                <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
                  <ShieldAlert className="w-12 h-12 text-amber-500 mx-auto mb-3" />
                  <h3 className="text-base font-semibold text-slate-900">Access Restricted</h3>
                  <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">Only administrators can create and manage WhatsApp templates. You can use approved templates when messaging clients.</p>
                  <Button className="mt-4" onClick={() => setView('dashboard')}>Return to Dashboard</Button>
                </div>
              )}
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: INTERNAL & EXTERNAL SALESPERSONS (ADMIN CRM) */}
          {/* ──────────────────────────────────────────────────────────── */}
          {(view === 'internal_salespersons' || view === 'external_salespersons') && (
            <div className="space-y-4">
              <SalesPersonOverview
                initialTab={view === 'external_salespersons' ? 'external' : 'internal'}
                initialRepId={!isAdmin ? (currentUser?.id || currentUser?.email) : null}
                autoSelectSingleRep={!isAdmin}
                onOpenLeadWorkspace={(lead) => {
                  setSelectedLead(lead);
                }}
              />
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: WEBSITE LEADS & ENQUIRIES (ADMIN CRM) */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'website_leads' && (
            <div className="space-y-4">
              {isAdmin ? (
                <WebsiteLeadsOverview
                  salesReps={salesReps}
                  activeCategoryProp={selectedWebsiteCategory}
                  onCategoryChangeProp={(cat) => setSelectedWebsiteCategory(cat)}
                  onOpenLeadWorkspace={(lead) => {
                    setSelectedLead(lead);
                  }}
                  refreshTrigger={websiteLeadsRefreshKey}
                />
              ) : (
                <div className="p-8 text-center bg-white rounded-xl border border-slate-200">
                  <ShieldAlert className="w-12 h-12 text-amber-500 mx-auto mb-3" />
                  <h3 className="text-base font-semibold text-slate-900">Access Restricted</h3>
                  <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">Only administrators can view and assign website leads.</p>
                  <Button className="mt-4" onClick={() => setView('dashboard')}>Return to Dashboard</Button>
                </div>
              )}
            </div>
          )}

          {/* ──────────────────────────────────────────────────────────── */}
          {/* VIEW: SALESPERSON ACTIVITY AUDIT LOG (ADMIN & SALESPERSON) */}
          {/* ──────────────────────────────────────────────────────────── */}
          {view === 'salesperson_activity_audit' && (
            <div className="space-y-4">
              <CRMSalespersonActivityAudit
                currentUser={currentUser}
                isSalespersonOnly={!isAdmin}
                onOpenLeadWorkspace={(lead) => {
                  setSelectedLead(lead);
                }}
              />
            </div>
          )}

        </div>

      </main>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* LEAD 360° WORKSPACE DRAWER / MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {selectedLead && (
        <Dialog
          open={!!selectedLead}
          onOpenChange={(open) => {
            if (!open) setSelectedLead(null);
          }}
          modal={false}
        >
          <DialogContent
            onInteractOutside={(e) => {
              if (showEmailModal || showCallModal || showWhatsAppModal || showFollowUpModal || showMeetingModal || showPaymentModal || showConvertModal || showQuickCallSelectModal) {
                e.preventDefault();
              }
            }}
            onPointerDownOutside={(e) => {
              if (showEmailModal || showCallModal || showWhatsAppModal || showFollowUpModal || showMeetingModal || showPaymentModal || showConvertModal || showQuickCallSelectModal) {
                e.preventDefault();
              }
            }}
            className="max-w-4xl max-h-[92vh] flex flex-col p-0 overflow-hidden bg-slate-50"
          >
            
            {/* Header */}
            <div className="bg-white p-5 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xl flex items-center justify-center border-2 border-emerald-200">
                  {selectedLead.name ? selectedLead.name[0].toUpperCase() : 'C'}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-slate-900">{selectedLead.name}</h3>
                    <Badge className="bg-slate-100 text-slate-700 font-mono text-[10px]">{selectedLead.lead_number}</Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500 font-medium flex-wrap">
                    {selectedLead.phone ? (
                      <button
                        type="button"
                        onClick={() => handleStartCall(selectedLead)}
                        className="text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1 font-semibold group/call"
                        title="Click to call client immediately"
                      >
                        <PhoneCall className="w-3 h-3 text-blue-500 group-hover/call:scale-110 transition-transform" />
                        <span>{formatPhoneNumber(selectedLead.phone)}</span>
                      </button>
                    ) : (
                      <span>No phone registered</span>
                    )}
                    <span>•</span>
                    {selectedLead.email ? (
                      <button
                        type="button"
                        onClick={() => handleOpenEmailModal('', '', null, selectedLead)}
                        className="text-indigo-600 hover:text-indigo-800 hover:underline flex items-center gap-1 font-medium group/mail"
                        title="Click to compose email to client"
                      >
                        <Mail className="w-3 h-3 text-indigo-500 group-hover/mail:scale-110 transition-transform" />
                        <span>{selectedLead.email}</span>
                      </button>
                    ) : (
                      <span>No email registered</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Stage Selector & More Actions */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-semibold">Stage:</span>
                <Select value={selectedLead.stage} onValueChange={(val) => handleStageChange(selectedLead.id, val)}>
                  <SelectTrigger className="w-36 h-8 text-xs bg-slate-50 font-semibold"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {STAGES.map(s => <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>)}
                  </SelectContent>
                </Select>

                {/* Stage -> More Options */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs px-2.5 bg-white border-slate-300 hover:bg-slate-50 font-semibold text-slate-700 gap-1 shadow-xs"
                      title="More Stage Actions"
                    >
                      <span>More</span>
                      <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48 bg-white shadow-lg border border-slate-200 z-50">
                    <DropdownMenuItem
                      onClick={() => handleStageMoreAction('message')}
                      className="text-xs flex items-center gap-2 cursor-pointer font-medium text-emerald-700 hover:bg-emerald-50 py-2"
                    >
                      <MessageCircle className="w-4 h-4 text-emerald-600" />
                      <span>Drop a Message</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleStageMoreAction('mail')}
                      className="text-xs flex items-center gap-2 cursor-pointer font-medium text-indigo-700 hover:bg-indigo-50 py-2"
                    >
                      <Mail className="w-4 h-4 text-indigo-600" />
                      <span>Drop a Mail</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {/* QUICK ACTIONS BAR */}
            <div className="bg-slate-100/90 px-5 py-2.5 border-b border-slate-200 flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                onClick={() => handleStartCall(selectedLead)}
                className="h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white gap-1 font-bold shadow-sm"
                title="Call client using your Callyzer-enabled mobile SIM"
              >
                <PhoneCall className="w-3.5 h-3.5" /> Call Client
              </Button>
              <Button size="sm" onClick={() => setShowWhatsAppModal(true)} className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white gap-1 font-medium">
                <MessageCircle className="w-3 h-3" /> WhatsApp
              </Button>
              <Button size="sm" onClick={() => handleOpenEmailModal('', '', null, selectedLead)} className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1 font-medium shadow-sm">
                <Mail className="w-3 h-3" /> Email
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowFollowUpModal(true)} className="h-7 text-xs gap-1 bg-white">
                <Clock className="w-3 h-3" /> Follow-up
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowMeetingModal(true)} className="h-7 text-xs gap-1 bg-white">
                <Video className="w-3 h-3" /> Meeting
              </Button>
              <Button size="sm" onClick={() => setShowConvertModal(true)} className="h-7 text-xs bg-purple-600 hover:bg-purple-700 text-white gap-1 font-bold ml-auto shadow-sm">
                <ShieldCheck className="w-3.5 h-3.5" /> Convert to Client
              </Button>
            </div>

            {/* Workspace Tabs */}
            <div className="flex border-b border-slate-200 bg-white px-5 text-xs font-semibold gap-6">
              {[
                { key: 'overview', label: 'Lead Profile' },
                { key: 'calls', label: `Calls & History (${leadCalls.length})` },
                { key: 'whatsapp', label: `WhatsApp & Chat (${leadWhatsApp.length})` },
                { key: 'emails', label: `Emails & Thread (${leadEmails.length})` },
                { key: 'timeline', label: `Complete History (${leadTimeline.length})` }
              ].map(t => (
                <button
                  key={t.key}
                  onClick={() => {
                    setWorkspaceTab(t.key);
                    if (t.key === 'calls') {
                      loadLeadCalls(selectedLead.id);
                    }
                    if (t.key === 'whatsapp') {
                      loadLeadWhatsApp(selectedLead.id);
                    }
                    if (t.key === 'emails') {
                      loadLeadEmails(selectedLead.id);
                      handleSyncMailbox(selectedLead.id, selectedLead.email, true);
                    }
                  }}
                  className={`py-2.5 border-b-2 transition-colors ${workspaceTab === t.key ? 'border-emerald-600 text-emerald-700 font-bold' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              
              {/* TAB: OVERVIEW */}
              {workspaceTab === 'overview' && (
                <div className="space-y-4 text-xs">
                  {/* Scheduled Consultation / Calendly Booking Banner */}
                  {(() => {
                    const activeMeeting = meetings.find(m =>
                      (m.lead_id && String(m.lead_id) === String(selectedLead.id)) ||
                      (selectedLead.email && m.contact_email && String(m.contact_email).toLowerCase().trim() === String(selectedLead.email).toLowerCase().trim())
                    );
                    const cb = selectedLead.calendly_booking || selectedLead.booking_details;
                    const isBooked = selectedLead.has_booking || Boolean(cb) || Boolean(activeMeeting);
                    if (!isBooked) return null;

                    const meetingDate = cb?.date || activeMeeting?.meeting_date;
                    const meetingTime = cb?.time || activeMeeting?.meeting_time;
                    const meetLink = cb?.meeting_link || activeMeeting?.meeting_link;
                    const eventName = cb?.event_name || activeMeeting?.title || selectedLead.service_interested || 'Consultation Session';
                    const consultant = activeMeeting?.sales_person_name || selectedLead.assigned_to_name || 'LEAMSS Consultant';
                    const meetingStatus = activeMeeting?.status || cb?.status || 'Scheduled';

                    return (
                      <Card className="p-4 bg-gradient-to-r from-indigo-50/95 via-sky-50/80 to-purple-50/60 border-indigo-200 border shadow-sm rounded-xl space-y-2.5">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2">
                            <Badge className="bg-indigo-600 text-white font-bold text-[11px] gap-1 px-2.5 py-0.5 shadow-none inline-flex items-center">
                              <Calendar className="w-3.5 h-3.5" />
                              <span>Consultation Booked (Calendly)</span>
                            </Badge>
                            <span className="font-bold text-slate-900 text-xs">{eventName}</span>
                          </div>
                          <Badge className={`text-[10px] font-bold uppercase ${
                            meetingStatus === 'completed' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' :
                            meetingStatus === 'cancelled' ? 'bg-rose-100 text-rose-800 border-rose-300' :
                            'bg-purple-100 text-purple-800 border-purple-300'
                          }`}>
                            {meetingStatus}
                          </Badge>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs bg-white/95 p-3 rounded-lg border border-indigo-100">
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Scheduled Date & Time</span>
                            <span className="font-bold text-slate-900 text-xs">
                              📅 {meetingDate || 'Date confirmed'} {meetingTime ? `@ ${meetingTime}` : ''}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Assigned Consultant</span>
                            <span className="font-semibold text-slate-800">
                              👤 {consultant}
                            </span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Meeting Platform</span>
                            <span className="font-semibold text-indigo-700">
                              🎥 Google Meet
                            </span>
                          </div>
                        </div>

                        {/* Reschedule Reason Box if rescheduled */}
                        {(activeMeeting?.reschedule_reason || cb?.reschedule_reason) && (
                          <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-amber-900 text-xs flex items-start gap-2">
                            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                            <div>
                              <strong className="block text-[11px] uppercase tracking-wide text-amber-800">Rescheduled Consultation:</strong>
                              <p className="text-[11px] text-amber-900 font-medium">
                                Reason: {activeMeeting?.reschedule_reason || cb?.reschedule_reason}
                              </p>
                            </div>
                          </div>
                        )}

                        {meetLink && (
                          <div className="flex items-center justify-between gap-2 pt-1 flex-wrap">
                            <div className="flex items-center gap-1.5 flex-1 min-w-[220px]">
                              <code className="text-[10px] bg-white border border-slate-200 px-2 py-1 rounded text-slate-700 font-mono truncate max-w-[320px]">
                                {meetLink}
                              </code>
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  navigator.clipboard.writeText(meetLink);
                                  toast.success('Google Meet link copied to clipboard!');
                                }}
                                className="h-7 px-2 text-[11px] text-slate-600 hover:text-slate-900 gap-1"
                              >
                                <Copy className="w-3 h-3" /> Copy
                              </Button>
                            </div>

                            <div className="flex items-center gap-1.5">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => handleOpenRescheduleModal(activeMeeting || {
                                  id: selectedLead.id,
                                  title: eventName,
                                  meeting_date: meetingDate,
                                  meeting_time: meetingTime,
                                  duration_minutes: 30,
                                  contact_name: selectedLead.name,
                                  contact_email: selectedLead.email,
                                  contact_phone: selectedLead.phone,
                                  sales_person_name: consultant,
                                  meeting_link: meetLink
                                })}
                                className="h-7 text-xs bg-white hover:bg-amber-50 text-amber-800 border-amber-300 gap-1 font-semibold"
                                title="Reschedule consultation date/time"
                              >
                                <RefreshCw className="w-3 h-3 text-amber-600" /> Reschedule
                              </Button>

                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                onClick={() => handleOpenRecapModal(activeMeeting || {
                                  id: selectedLead.id,
                                  title: eventName,
                                  contact_name: selectedLead.name,
                                  sales_person_name: consultant,
                                  recap: activeMeeting?.recap
                                })}
                                className="h-7 text-xs bg-white hover:bg-indigo-50 text-indigo-700 border-indigo-200 gap-1 font-semibold"
                                title="Meeting recording & AI summary"
                              >
                                <FileText className="w-3 h-3 text-indigo-600" /> Notes & Transcript
                              </Button>

                              <Button
                                type="button"
                                size="sm"
                                onClick={() => window.open(meetLink, '_blank')}
                                className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm"
                              >
                                <Video className="w-3.5 h-3.5" /> Join Google Meet
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Meeting Recording, Transcript & AI Summary preview if present */}
                        {activeMeeting?.recap && (
                          <div className="mt-2 p-3 bg-white/95 rounded-lg border border-indigo-100 text-xs space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Meeting Notes & AI Summary
                              </span>
                              {activeMeeting.recap.recording_url && (
                                <a
                                  href={activeMeeting.recap.recording_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-[11px] text-indigo-600 font-bold hover:underline flex items-center gap-1"
                                >
                                  Watch Recording <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                            {activeMeeting.recap.summary && (
                              <p className="text-[11px] text-slate-700 bg-slate-50 p-2 rounded whitespace-pre-wrap leading-relaxed">
                                {activeMeeting.recap.summary}
                              </p>
                            )}
                          </div>
                        )}
                      </Card>
                    );
                  })()}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card className="p-4 bg-white border-slate-200 space-y-2">
                      <h5 className="font-bold text-slate-900 border-b border-slate-100 pb-1.5 uppercase tracking-wide text-[11px] flex items-center justify-between">
                        <span>Consultation Interest</span>
                        <div className="flex items-center gap-1.5">
                          {(() => {
                            const sc = getSourceConfig(selectedLead.source);
                            const IconC = sc.icon || Globe;
                            return (
                              <Badge className={`${sc.bg} ${sc.text} ${sc.border} border text-[10px] font-semibold flex items-center gap-1 px-1.5 py-0.5 shadow-none`}>
                                <IconC className="w-2.5 h-2.5" />
                                {sc.label}
                              </Badge>
                            );
                          })()}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenEditLead(selectedLead)}
                            className="h-5 px-1.5 text-[10px] text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 flex items-center gap-1"
                          >
                            <Edit className="w-3 h-3" /> Edit
                          </Button>
                        </div>
                      </h5>
                      <div className="space-y-1.5 text-slate-600">
                        <p><span className="font-semibold text-slate-800">Target Country:</span> {selectedLead.country_of_interest || selectedLead.interested_country || selectedLead.country || '—'}</p>
                        <p><span className="font-semibold text-slate-800">Service:</span> {selectedLead.service_interested || selectedLead.service || '—'}</p>
                        <p><span className="font-semibold text-slate-800">Program / Visa:</span> {selectedLead.interested_program || selectedLead.visa_type || '—'}</p>
                        <p><span className="font-semibold text-slate-800">Budget:</span> {selectedLead.budget || '—'}</p>
                        <p><span className="font-semibold text-slate-800">Lead Source:</span> {selectedLead.original_source || selectedLead.source || 'Unknown'}</p>
                        <p><span className="font-semibold text-slate-800">Campaign:</span> {selectedLead.campaign || selectedLead.utm_campaign || '—'} {selectedLead.utm_medium ? `(${selectedLead.utm_medium})` : ''}</p>
                        {selectedLead.utm_source && (
                          <p><span className="font-semibold text-slate-800">UTM Source:</span> <span className="font-mono text-[11px] bg-slate-100 px-1 py-0.5 rounded text-slate-800">{selectedLead.utm_source}</span></p>
                        )}
                        {selectedLead.website_page_url && (
                          <p className="truncate"><span className="font-semibold text-slate-800">Landing Page:</span> <a href={selectedLead.website_page_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{selectedLead.website_page_title || selectedLead.website_page_url}</a></p>
                        )}
                        <div className="flex items-center justify-between pt-1.5 border-t border-slate-100 mt-2">
                          <span className="font-semibold text-slate-800">Assigned To:</span>
                          <Select
                            value={selectedLead.assigned_to || 'unassigned'}
                            onValueChange={async (val) => {
                              const rep = salesReps.find(r => r.id === val);
                              const newAssigneeId = val === 'unassigned' ? '' : val;
                              const newAssigneeName = rep ? rep.name : '';
                              try {
                                await axios.put(`${API}/leads/${selectedLead.id}`, { assigned_to: newAssigneeId, assigned_to_name: newAssigneeName }, getAuthHeader());
                                setSelectedLead(p => ({ ...p, assigned_to: newAssigneeId, assigned_to_name: newAssigneeName, assigned_name: newAssigneeName }));
                                setLeads(prev => prev.map(l => (l.id === selectedLead.id || l._id === selectedLead.id || l.lead_number === selectedLead.lead_number || (l.email && selectedLead.email && l.email.toLowerCase() === selectedLead.email.toLowerCase())) ? { ...l, assigned_to: newAssigneeId, assigned_to_name: newAssigneeName, assigned_name: newAssigneeName } : l));
                                setMeetings(prev => prev.map(m => (m.lead_id === selectedLead.id || (m.contact_email && selectedLead.email && m.contact_email.toLowerCase() === selectedLead.email.toLowerCase())) ? { ...m, sales_person_id: newAssigneeId, sales_person_name: newAssigneeName } : m));
                                toast.success(`Assigned to ${newAssigneeName || 'Unassigned'}`);
                                fetchAllCRMData();
                              } catch (err) {
                                toast.error('Failed to update assignment');
                              }
                            }}
                          >
                            <SelectTrigger className="h-7 w-52 text-[11px] bg-slate-50 border-slate-200 font-medium text-slate-800">
                              <SelectValue placeholder="Unassigned" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="unassigned">— Unassigned —</SelectItem>
                              {salesReps.map(rep => (
                                <SelectItem key={rep.id} value={rep.id}>
                                  {rep.name} {rep.role ? `(${rep.role.replace(/_/g, ' ')})` : ''}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </Card>

                    <Card className="p-4 bg-white border-slate-200 space-y-2">
                      <h5 className="font-bold text-slate-900 border-b border-slate-100 pb-1.5 uppercase tracking-wide text-[11px] flex items-center justify-between">
                        <span>Applicant Details & Qualification</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEditLead(selectedLead)}
                          className="h-5 px-1.5 text-[10px] text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50 flex items-center gap-1"
                        >
                          <Edit className="w-3 h-3" /> Edit
                        </Button>
                      </h5>
                      <div className="space-y-1.5 text-slate-600">
                        <p><span className="font-semibold text-slate-800">Phone:</span> <strong className="text-slate-900">{formatPhoneNumber(selectedLead.phone) || '—'}</strong></p>
                        <p><span className="font-semibold text-slate-800">Email:</span> {selectedLead.email || '—'}</p>
                        <p><span className="font-semibold text-slate-800">Occupation:</span> {selectedLead.occupation || '—'}</p>
                        <p><span className="font-semibold text-slate-800">Experience:</span> {selectedLead.total_work_experience || selectedLead.experience || '—'}</p>
                        <p><span className="font-semibold text-slate-800">Qualification:</span> {selectedLead.latest_qualification || selectedLead.qualification || '—'}</p>
                        <p><span className="font-semibold text-slate-800">City / Location:</span> {[selectedLead.city, selectedLead.country].filter(Boolean).join(', ') || '—'}</p>
                        
                        <div className="flex flex-wrap items-center gap-2 pt-2.5 border-t border-slate-100 mt-2">
                          <Button
                            size="sm"
                            onClick={() => handleStartCall(selectedLead)}
                            className="h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white gap-1 font-semibold shadow-sm"
                            title="Start PC call with live microphone recording"
                          >
                            <PhoneCall className="w-3 h-3" /> Call Client
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleOpenEmailModal('', '', null, selectedLead)}
                            className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1 font-semibold shadow-sm"
                            title="Send email using Admin template from your sales mailbox"
                          >
                            <Mail className="w-3 h-3" /> Send Email
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleWhatsAppCall(selectedLead.phone)}
                            className="h-7 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 gap-1 font-semibold"
                          >
                            <MessageCircle className="w-3 h-3" /> WhatsApp
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleOpenPreAssessmentReport(selectedLead)}
                            className="h-7 text-xs bg-purple-600 hover:bg-purple-700 text-white gap-1.5 font-semibold shadow-sm"
                            title="Open Client Assessment Report creation with client details automatically populated"
                          >
                            <FileText className="w-3 h-3 text-purple-200" /> Pre-Assessment Report
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setWorkspaceTab('emails')}
                            className="h-7 text-xs text-indigo-700 hover:bg-indigo-50 gap-1 font-semibold ml-auto"
                          >
                            Email Thread ({leadEmails.length}) →
                          </Button>
                        </div>
                      </div>
                    </Card>
                  </div>

                    {/* Attached Resume & Multi-Channel Forwarding Card */}
                    <Card className="p-4 bg-white border-slate-200 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                        <h5 className="font-bold text-slate-900 uppercase tracking-wide text-[11px] flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-emerald-600" /> Candidate Resume & Forwarding
                        </h5>
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={fetchAllCRMData}
                            title="Check if client has uploaded resume"
                            className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 px-2 py-1 rounded border border-slate-300 transition-colors"
                          >
                            <RefreshCw className="w-3 h-3 text-slate-500" />
                            <span>Check Status</span>
                          </button>
                          <label className="cursor-pointer inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 px-2 py-1 rounded border border-emerald-200 transition-colors">
                            <Upload className="w-3 h-3" />
                            <span>{selectedLead.resume_file_id || selectedLead.resume_url ? 'Replace Resume' : 'Attach Resume'}</span>
                            <input
                              type="file"
                              accept=".pdf,.doc,.docx,.txt"
                              className="hidden"
                              onChange={(e) => {
                                if (e.target.files?.[0]) {
                                  handleResumeFileUpload(selectedLead, e.target.files[0]);
                                  e.target.value = '';
                                }
                              }}
                            />
                          </label>
                        </div>
                      </div>

                      {selectedLead.resume_file_id || selectedLead.resume_url ? (
                        <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-lg flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-8 h-8 rounded bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm">
                              📄
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-xs text-emerald-900 truncate">
                                {selectedLead.resume_filename || 'Candidate Resume'}
                              </p>
                              <p className="text-[10px] text-emerald-700 flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" /> Linked to Client Record & Pipeline
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Button
                              size="sm"
                              type="button"
                              onClick={() => handleOpenResumePreview(selectedLead)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                              title="Preview candidate resume in CRM"
                            >
                              <Eye className="w-3.5 h-3.5" /> View Resume
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onClick={() => handleDownloadResume(selectedLead)}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded text-slate-700 bg-white border-slate-300 hover:bg-slate-50 shadow-sm"
                              title="Download candidate resume"
                            >
                              <Download className="w-3.5 h-3.5" /> Download
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg flex flex-wrap items-center justify-between gap-2 text-xs text-amber-800">
                          <div>
                            <p className="font-semibold text-amber-900">No Resume Attached Yet</p>
                            <p className="text-[11px] text-amber-700">Attach client resume received via Email or WhatsApp, or check for client upload</p>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onClick={() => handleCheckResumeStatus(selectedLead)}
                              disabled={checkingResumeStatusId === selectedLead.id}
                              className="h-7 text-xs bg-white border-amber-300 text-amber-900 hover:bg-amber-100 gap-1 font-semibold"
                            >
                              <RefreshCw className={`w-3 h-3 text-amber-700 ${checkingResumeStatusId === selectedLead.id ? 'animate-spin' : ''}`} />
                              <span>{checkingResumeStatusId === selectedLead.id ? 'Checking...' : 'Check Resume Status'}</span>
                            </Button>
                            <Button
                              size="sm"
                              type="button"
                              onClick={() => handleSendResumeRequest(selectedLead)}
                              disabled={sendingResumeReqId === selectedLead.id}
                              className="h-7 text-xs bg-amber-600 hover:bg-amber-700 text-white gap-1 font-semibold shadow-sm"
                            >
                              <Send className="w-3 h-3" />
                              <span>{sendingResumeReqId === selectedLead.id ? 'Sending...' : 'Request Upload Link'}</span>
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Forward Candidate Details & Resume */}
                      <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wide">Forward Details:</span>
                        <Button
                          size="sm"
                          onClick={() => handleForwardLeadByEmail(selectedLead)}
                          className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1 font-semibold shadow-sm"
                          title="Forward profile details with attached resume via Email"
                        >
                          <Mail className="w-3 h-3" /> Forward via Email
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleForwardLeadByWhatsApp(selectedLead)}
                          className="h-7 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 gap-1 font-semibold"
                          title="Forward candidate summary and direct resume link via WhatsApp"
                        >
                          <MessageCircle className="w-3 h-3" /> Forward via WhatsApp
                        </Button>
                      </div>
                    </Card>

                    {/* Attached Pre-Assessment Report Card */}
                    <Card className="p-4 bg-white border-slate-200 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                        <h5 className="font-bold text-slate-900 uppercase tracking-wide text-[11px] flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-purple-600" /> Pre-Assessment Report Attachment
                        </h5>
                        <div className="flex items-center gap-1.5">
                          <label className="cursor-pointer inline-flex items-center gap-1 text-[10px] font-semibold text-purple-700 hover:text-purple-800 bg-purple-50 hover:bg-purple-100 px-2 py-1 rounded border border-purple-200 transition-colors">
                            <Upload className="w-3 h-3" />
                            <span>{(selectedLead.assessment_report_file_id || selectedLead.pre_assessment_report_url || selectedLead.latest_report_snapshot_id || selectedLead.bulk_row_id) ? 'Replace Report' : 'Attach Report'}</span>
                            <input
                              type="file"
                              accept=".pdf,.doc,.docx"
                              className="hidden"
                              onChange={(e) => {
                                if (e.target.files?.[0]) {
                                  handlePreAssessmentReportUpload(selectedLead, e.target.files[0]);
                                  e.target.value = '';
                                }
                              }}
                            />
                          </label>
                        </div>
                      </div>

                      {(selectedLead.assessment_report_file_id || selectedLead.pre_assessment_report_url || selectedLead.latest_report_snapshot_id || selectedLead.bulk_row_id) ? (
                        <div className="p-3 bg-purple-50/70 border border-purple-200 rounded-lg flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-8 h-8 rounded bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-sm">
                              📊
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-xs text-purple-900 truncate">
                                {selectedLead.assessment_report_filename || `${selectedLead.name || 'Client'}_Pre_Assessment_Report.pdf`}
                              </p>
                              <p className="text-[10px] text-purple-700 flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" /> Linked to Client Record & Assessment Pipeline
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Button
                              size="sm"
                              type="button"
                              onClick={() => handleOpenReportPreview(selectedLead)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded bg-purple-600 hover:bg-purple-700 text-white shadow-sm"
                              title="Preview Pre-Assessment Report"
                            >
                              <Eye className="w-3.5 h-3.5" /> View Report
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onClick={() => handleDownloadReport(selectedLead)}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-semibold rounded text-slate-700 bg-white border-slate-300 hover:bg-slate-50 shadow-sm"
                              title="Download Pre-Assessment Report"
                            >
                              <Download className="w-3.5 h-3.5" /> Download
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="p-3 bg-slate-50 border border-dashed border-slate-200 rounded-lg flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                          <div>
                            <p className="font-semibold text-slate-800">No Pre-Assessment Report Attached Yet</p>
                            <p className="text-[11px] text-slate-500">Attach client's Pre-Assessment Report (.pdf, .doc, .docx) directly to this record</p>
                          </div>
                          <label className="cursor-pointer inline-flex items-center gap-1 text-xs font-semibold text-purple-700 hover:text-purple-800 bg-white hover:bg-purple-50 px-3 py-1.5 rounded-md border border-purple-200 shadow-sm transition-colors">
                            <Upload className="w-3.5 h-3.5" />
                            <span>Attach Report</span>
                            <input
                              type="file"
                              accept=".pdf,.doc,.docx"
                              className="hidden"
                              onChange={(e) => {
                                if (e.target.files?.[0]) {
                                  handlePreAssessmentReportUpload(selectedLead, e.target.files[0]);
                                  e.target.value = '';
                                }
                              }}
                            />
                          </label>
                        </div>
                      )}
                    </Card>

                    {/* Pipeline Cockpit — Payment & Enrolment Card */}
                    <Card className="p-4 bg-white border-slate-200 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                        <h5 className="font-bold text-slate-900 uppercase tracking-wide text-[11px] flex items-center gap-1.5">
                          <DollarSign className="w-3.5 h-3.5 text-emerald-600" /> Payment & Enrolment Details
                        </h5>
                        {(selectedLead.payment_status === 'paid' || selectedLead.is_paid) ? (
                          <Badge className="bg-emerald-50 text-emerald-800 border-emerald-300 border text-[11px] font-bold px-2 py-0.5 shadow-none">
                            ✓ Paid · ₹{Number(selectedLead.amount_paid || ((selectedLead.payment_amount && Number(selectedLead.payment_amount) !== 999) ? selectedLead.payment_amount : 2427)).toLocaleString('en-IN')}
                          </Badge>
                        ) : selectedLead.payment_status === 'failed' ? (
                          <Badge className="bg-rose-50 text-rose-800 border-rose-300 border text-[11px] font-bold px-2 py-0.5 shadow-none">
                            ❌ Payment Failed
                          </Badge>
                        ) : selectedLead.payment_status === 'partially_paid' ? (
                          <Badge className="bg-amber-50 text-amber-800 border-amber-300 border text-[11px] font-bold px-2 py-0.5 shadow-none">
                            ⚡ Partially Paid · ₹{Number(selectedLead.amount_paid || 0).toLocaleString('en-IN')}
                          </Badge>
                        ) : (
                          <Badge className="bg-amber-50 text-amber-800 border-amber-300 border text-[11px] font-bold px-2 py-0.5 shadow-none">
                            ⏳ Payment Pending
                          </Badge>
                        )}
                      </div>

                      {/* Detail Grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
                        <div>
                          <span className="text-[10px] text-slate-400 block font-medium">Payment Status</span>
                          <span className="font-bold text-slate-900">
                            {(selectedLead.payment_status === 'paid' || selectedLead.is_paid)
                              ? '✓ Success / Captured'
                              : selectedLead.payment_status === 'failed'
                              ? '❌ Attempt Failed'
                              : selectedLead.payment_status === 'partially_paid'
                              ? '⚡ Partially Paid'
                              : '⏳ Awaiting Payment'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-medium">Total Fee / Paid Amount</span>
                          <span className="font-bold text-slate-900">
                            ₹{Number((selectedLead.payment_amount && Number(selectedLead.payment_amount) !== 999) ? selectedLead.payment_amount : 2427).toLocaleString('en-IN')}
                            {(selectedLead.payment_status === 'paid' || selectedLead.is_paid) && (
                              <span className="text-emerald-700 font-semibold ml-1">
                                (Paid: ₹{Number(selectedLead.amount_paid || ((selectedLead.payment_amount && Number(selectedLead.payment_amount) !== 999) ? selectedLead.payment_amount : 2427)).toLocaleString('en-IN')})
                              </span>
                            )}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-medium">Gateway & Method</span>
                          <span className="font-semibold text-slate-700">
                            {selectedLead.payment_vpa
                              ? `${(selectedLead.payment_method || 'UPI').toUpperCase()} (${selectedLead.payment_vpa})`
                              : (selectedLead.payment_method?.toUpperCase() || selectedLead.payment_mode || 'Razorpay / Online')}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-medium">Razorpay Payment ID</span>
                          <span className="font-mono text-xs text-slate-800 select-all">
                            {selectedLead.razorpay_payment_id || selectedLead.payment_id || '—'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-medium">Payment Link / Page ID</span>
                          <a
                            href={`https://pages.razorpay.com/${selectedLead.razorpay_payment_link_id || 'pl_TZSVimtLKxHnHx'}/view`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1 font-semibold"
                            title="Open Razorpay Payment Page"
                          >
                            {selectedLead.razorpay_payment_link_id || 'pl_TZSVimtLKxHnHx'}
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-medium">Payment / Attempt Date</span>
                          <span className="text-slate-700 font-medium text-[11px]">
                            {selectedLead.paid_at || selectedLead.payment_date || selectedLead.last_payment_attempt_at
                              ? new Date(selectedLead.paid_at || selectedLead.payment_date || selectedLead.last_payment_attempt_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
                              : '—'}
                          </span>
                        </div>
                      </div>

                      {/* Failure Banner if payment failed */}
                      {(selectedLead.payment_status === 'failed' || selectedLead.last_payment_error) && !selectedLead.is_paid && (
                        <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold">Payment Attempt Failed: </span>
                            <span>{selectedLead.last_payment_error || 'Payment was not completed by the user.'}</span>
                            {selectedLead.last_payment_error_code && (
                              <span className="font-mono text-[10px] text-rose-700 ml-1">({selectedLead.last_payment_error_code})</span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Payment Attempts History Table */}
                      {selectedLead.payment_history && selectedLead.payment_history.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                              Payment Attempts History ({selectedLead.payment_history.length})
                            </span>
                          </div>
                          <div className="max-h-36 overflow-y-auto border border-slate-200 rounded-lg bg-slate-50/50">
                            <table className="w-full text-[11px] text-left">
                              <thead className="bg-slate-100 text-slate-600 font-semibold border-b border-slate-200">
                                <tr>
                                  <th className="p-1.5 pl-2">Time</th>
                                  <th className="p-1.5">Payment ID</th>
                                  <th className="p-1.5">Amount</th>
                                  <th className="p-1.5">Method</th>
                                  <th className="p-1.5">Status</th>
                                  <th className="p-1.5 pr-2">Details</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100 font-medium">
                                {selectedLead.payment_history.map((h, i) => (
                                  <tr key={h.payment_id || i} className="hover:bg-white">
                                    <td className="p-1.5 pl-2 text-slate-500 whitespace-nowrap">
                                      {h.created_at ? new Date(h.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                                    </td>
                                    <td className="p-1.5 font-mono text-[10px] text-slate-700">{h.payment_id}</td>
                                    <td className="p-1.5 font-bold text-slate-800">₹{h.amount && Number(h.amount) !== 999 ? h.amount : 2427}</td>
                                    <td className="p-1.5 text-slate-600 uppercase text-[10px]">{h.vpa ? `UPI (${h.vpa})` : (h.method || 'online')}</td>
                                    <td className="p-1.5">
                                      {h.status === 'paid' ? (
                                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800">PAID</span>
                                      ) : (
                                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-100 text-rose-800">FAILED</span>
                                      )}
                                    </td>
                                    <td className="p-1.5 pr-2 text-slate-500 text-[10px] truncate max-w-[120px]" title={h.error_description || h.link_id}>
                                      {h.error_description || h.link_id || '—'}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCheckRazorpayPayment(selectedLead)}
                          disabled={checkingPaymentId === selectedLead.id}
                          className="h-7 text-xs border-blue-300 text-blue-700 bg-blue-50/60 hover:bg-blue-100 gap-1.5 font-semibold"
                          title="Query live Razorpay payments directly to verify payment"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${checkingPaymentId === selectedLead.id ? 'animate-spin' : ''}`} />
                          {checkingPaymentId === selectedLead.id ? 'Checking...' : 'Check Razorpay Status'}
                        </Button>
                        {!selectedLead.is_paid && (
                          <Button
                            size="sm"
                            onClick={() => handleMarkLeadPaid(selectedLead, (selectedLead.payment_amount && Number(selectedLead.payment_amount) !== 999) ? selectedLead.payment_amount : 2427.0)}
                            disabled={markingPaidId === selectedLead.id}
                            className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 font-bold shadow-sm"
                            title="Mark this client payment as verified and received"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            {markingPaidId === selectedLead.id ? 'Recording...' : `Mark as Paid (₹${(selectedLead.payment_amount && Number(selectedLead.payment_amount) !== 999) ? selectedLead.payment_amount : 2427})`}
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSendPaymentLink(selectedLead)}
                          disabled={sendingPaymentLinkId === selectedLead.id}
                          className="h-7 text-xs border-amber-300 text-amber-800 bg-amber-50/60 hover:bg-amber-100 gap-1.5 font-semibold"
                          title="Dispatch payment link via Email and WhatsApp"
                        >
                          <Send className="w-3.5 h-3.5 text-amber-600" />
                          {sendingPaymentLinkId === selectedLead.id ? 'Sending Link...' : 'Send Payment Link (Email + WA)'}
                        </Button>
                        {(!selectedLead.resume_file_id && !selectedLead.resume_url) && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSendResumeRequest(selectedLead)}
                            disabled={sendingResumeReqId === selectedLead.id}
                            className="h-7 text-xs border-indigo-200 text-indigo-700 bg-indigo-50/50 hover:bg-indigo-100 gap-1.5 font-semibold"
                            title="Dispatch secure upload link to client to upload resume"
                          >
                            <Upload className="w-3.5 h-3.5 text-indigo-600" />
                            {sendingResumeReqId === selectedLead.id ? 'Requesting...' : 'Request Resume (Upload Link)'}
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleOpenPreAssessmentReport(selectedLead)}
                          className="h-7 text-xs border-purple-300 text-purple-700 bg-purple-50/60 hover:bg-purple-100 gap-1.5 font-semibold ml-auto"
                          title="Open Client Assessment Report creation with client details automatically populated"
                        >
                          <FileText className="w-3.5 h-3.5 text-purple-600" /> Pre-Assessment Report
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleConvertToPreAssessment(selectedLead)}
                          disabled={convertingLeadId === selectedLead.id}
                          className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 font-bold shadow-sm"
                          title="Convert this lead into a Pre-Assessment record in the PA portal"
                        >
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-100" />
                          {convertingLeadId === selectedLead.id ? 'Converting...' : '⚡ Convert to Pre-Assessment'}
                        </Button>
                      </div>
                    </Card>

                    {/* Dedicated Client Notes & Remarks Card */}
                    <Card id="client-notes-remarks-section" className="p-4 bg-white border-slate-200 shadow-xs space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold">
                            <StickyNote className="w-4 h-4 text-amber-700" />
                          </div>
                          <div>
                            <h5 className="font-bold text-slate-900 uppercase tracking-wide text-[11px] flex items-center gap-1.5">
                              <span>Client Notes & Remarks</span>
                              <span className="text-[10px] font-semibold text-slate-500 font-mono">
                                ({(selectedLead.notes || []).length} logged)
                              </span>
                            </h5>
                            <p className="text-[11px] text-slate-500">
                              Record client interaction remarks with timestamp & user role identification
                            </p>
                          </div>
                        </div>

                        {/* Quick action shortcuts */}
                        <div className="flex items-center gap-1.5">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => setShowWhatsAppModal(true)}
                            className="h-6 text-[10px] font-semibold text-emerald-700 hover:bg-emerald-50 gap-1 px-2 border border-emerald-200 rounded"
                            title="Open WhatsApp chat drawer"
                          >
                            <MessageCircle className="w-3 h-3 text-emerald-600" />
                            <span>Open WhatsApp</span>
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleOpenEmailModal('', '', null, selectedLead)}
                            className="h-6 text-[10px] font-semibold text-indigo-700 hover:bg-indigo-50 gap-1 px-2 border border-indigo-200 rounded"
                            title="Compose email to client"
                          >
                            <Mail className="w-3 h-3 text-indigo-600" />
                            <span>Compose Mail</span>
                          </Button>
                        </div>
                      </div>

                      {/* Note Type Selector Pills */}
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                          Select Note / Remark Type:
                        </label>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {[
                            { key: 'Dropped a Message', label: 'Dropped a Message', icon: MessageSquare, color: 'border-emerald-300 bg-emerald-50 text-emerald-800' },
                            { key: 'Dropped a Mail', label: 'Dropped a Mail', icon: Mail, color: 'border-indigo-300 bg-indigo-50 text-indigo-800' },
                            { key: 'Called the Client', label: 'Called the Client', icon: PhoneCall, color: 'border-blue-300 bg-blue-50 text-blue-800' },
                            { key: 'Other Remarks', label: 'Other Remarks', icon: FileText, color: 'border-amber-300 bg-amber-50 text-amber-800' }
                          ].map((t) => {
                            const IconComp = t.icon;
                            const isSelected = clientNoteType === t.key;
                            return (
                              <button
                                key={t.key}
                                type="button"
                                onClick={() => setClientNoteType(t.key)}
                                className={`px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 border transition-all ${
                                  isSelected
                                    ? `${t.color} shadow-xs ring-1 ring-offset-1 ring-slate-400 font-bold`
                                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                                }`}
                              >
                                <IconComp className="w-3.5 h-3.5" />
                                <span>{t.label}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Description Input Area */}
                      <div className="space-y-2">
                        <Textarea
                          id="client-remark-textarea"
                          value={clientNoteText}
                          onChange={(e) => setClientNoteText(e.target.value)}
                          placeholder={
                            clientNoteType === 'Dropped a Message'
                              ? 'e.g., Dropped WhatsApp message regarding required educational documents...'
                              : clientNoteType === 'Dropped a Mail'
                              ? 'e.g., Dropped an email with initial assessment summary and next steps...'
                              : clientNoteType === 'Called the Client'
                              ? 'e.g., Called client to clarify work experience duration, client requested evening callback...'
                              : 'e.g., Client consultation discussion notes, specific requirements or remarks...'
                          }
                          rows={3}
                          className="text-xs bg-slate-50 border-slate-200 placeholder:text-slate-400 resize-none focus:bg-white"
                        />

                        <div className="flex items-center justify-between">
                          <div className="text-[10px] text-slate-400 font-medium">
                            Logging as <b className="text-slate-700">{currentUser?.name || 'You'}</b> ({isAdmin ? 'Admin' : (currentUser?.rbac_role || currentUser?.role || 'Salesperson')})
                          </div>
                          <Button
                            type="button"
                            size="sm"
                            onClick={handleAddClientNote}
                            disabled={isSavingNote || !clientNoteText.trim()}
                            className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm px-3"
                          >
                            {isSavingNote ? (
                              <>
                                <RefreshCw className="w-3 h-3 animate-spin" />
                                <span>Saving...</span>
                              </>
                            ) : (
                              <>
                                <Save className="w-3 h-3" />
                                <span>Save Remark</span>
                              </>
                            )}
                          </Button>
                        </div>
                      </div>

                      {/* Complete Client-Wise Log History */}
                      <div className="space-y-2 pt-2 border-t border-slate-100">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                            Activity Remarks History ({selectedLead.notes?.length || 0})
                          </span>
                          {selectedLead.notes && selectedLead.notes.length > 0 && (
                            <span className="text-[10px] text-slate-400">Chronological • Preserved without overwriting</span>
                          )}
                        </div>

                        {(!selectedLead.notes || selectedLead.notes.length === 0) ? (
                          <div className="p-4 bg-slate-50/70 border border-dashed border-slate-200 rounded-lg text-center text-slate-500 text-xs">
                            <StickyNote className="w-5 h-5 text-slate-300 mx-auto mb-1" />
                            <p className="font-semibold text-slate-700">No Remarks Recorded Yet</p>
                            <p className="text-[11px] text-slate-400 mt-0.5">Use the options above to log calls, messages, emails, or remarks.</p>
                          </div>
                        ) : (
                          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                            {(selectedLead.notes || []).map((note, idx) => {
                              const typeStr = note.note_type || note.type || 'Other Remarks';
                              const isMsg = typeStr.toLowerCase().includes('message');
                              const isMail = typeStr.toLowerCase().includes('mail') || typeStr.toLowerCase().includes('email');
                              const isCall = typeStr.toLowerCase().includes('call');

                              const badgeStyle = isMsg
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                                : isMail
                                ? 'bg-indigo-50 text-indigo-800 border-indigo-200'
                                : isCall
                                ? 'bg-blue-50 text-blue-800 border-blue-200'
                                : 'bg-amber-50 text-amber-800 border-amber-200';

                              const IconType = isMsg ? MessageSquare : isMail ? Mail : isCall ? PhoneCall : FileText;

                              const isAuthorAdmin = note.is_admin || (note.added_by_role && note.added_by_role.toLowerCase().includes('admin'));

                              const dateDisplay = note.date_display || (note.created_at ? new Date(note.created_at).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }) : '—');
                              const timeDisplay = note.time_display || (note.created_at ? new Date(note.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) : '');

                              return (
                                <div
                                  key={note.id || idx}
                                  className="p-2.5 bg-slate-50/90 border border-slate-200 rounded-lg text-xs space-y-1.5 hover:bg-slate-100/70 transition-colors"
                                >
                                  <div className="flex items-center justify-between flex-wrap gap-1.5">
                                    <div className="flex items-center gap-1.5">
                                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border ${badgeStyle}`}>
                                        <IconType className="w-3 h-3" />
                                        <span>{typeStr}</span>
                                      </span>
                                      <span className="font-bold text-slate-800 text-[11px]">
                                        {note.added_by_name || 'User'}
                                      </span>
                                      <Badge className={`text-[9px] px-1.5 py-0 font-semibold uppercase ${
                                        isAuthorAdmin
                                          ? 'bg-purple-100 text-purple-800 border-purple-200'
                                          : 'bg-slate-200/80 text-slate-700 border-slate-300'
                                      }`}>
                                        {isAuthorAdmin ? 'Admin' : (note.added_by_role || 'Salesperson')}
                                      </Badge>
                                    </div>

                                    <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                                      <Clock className="w-3 h-3 text-slate-400" />
                                      <span>{dateDisplay} {timeDisplay && `• ${timeDisplay}`}</span>
                                    </div>
                                  </div>

                                  <p className="text-slate-700 text-xs whitespace-pre-wrap leading-relaxed pl-1 border-l-2 border-slate-300">
                                    {note.text || note.description || '—'}
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </Card>

                  {/* Quick Activity Snippet on Overview Tab */}
                  <Card className="p-4 bg-white border-slate-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <h5 className="font-bold text-slate-900 uppercase tracking-wide text-[11px] flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5 text-emerald-600" /> Recent Interactions & Call Recordings
                      </h5>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setWorkspaceTab('timeline')}
                        className="h-6 text-xs text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50"
                      >
                        View Complete History →
                      </Button>
                    </div>

                    <div className="space-y-2.5">
                      {leadTimeline.slice(0, 4).map((item, idx) => (
                        <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5 text-xs">
                          <div className="mt-0.5">
                            {item.type === 'call' ? (
                              item.extra?.direction === 'incoming' ? (
                                <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center"><PhoneIncoming className="w-3.5 h-3.5" /></div>
                              ) : (
                                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center"><PhoneOutgoing className="w-3.5 h-3.5" /></div>
                              )
                            ) : item.type === 'whatsapp' ? (
                              <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center"><MessageCircle className="w-3.5 h-3.5" /></div>
                            ) : item.type === 'email' ? (
                              <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center"><Mail className="w-3.5 h-3.5" /></div>
                            ) : item.type === 'meeting' ? (
                              <div className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center"><Video className="w-3.5 h-3.5" /></div>
                            ) : item.type === 'stage_change' ? (
                              <div className="w-6 h-6 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center"><ShieldCheck className="w-3.5 h-3.5" /></div>
                            ) : item.type === 'follow_up' ? (
                              <div className="w-6 h-6 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center"><Clock className="w-3.5 h-3.5" /></div>
                            ) : (
                              <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center"><Activity className="w-3.5 h-3.5" /></div>
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-900">{item.title}</span>
                              <span className="text-[10px] text-slate-400">{timeAgo(item.timestamp)}</span>
                            </div>
                            <p className="text-[11px] text-slate-600 mt-0.5">{item.description}</p>
                            {item.type === 'call' && item.extra?.recording_url && (
                              <CallAudioPlayer
                                recordingUrl={item.extra.recording_url}
                                durationSeconds={item.extra.duration_seconds}
                                callerName={selectedLead.name}
                              />
                            )}
                          </div>
                        </div>
                      ))}
                      {leadTimeline.length === 0 && (
                        <p className="text-slate-400 text-center py-4 italic">No interactions recorded yet. Click "Call Client" to initiate first contact.</p>
                      )}
                    </div>
                  </Card>
                </div>
              )}

              {/* TAB: CALLS & HISTORY (VOICE RECORDINGS & CALL CONSOLE) */}
              {workspaceTab === 'calls' && (
                <div className="space-y-4 text-xs">
                  {/* Action Bar */}
                  <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-3.5 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      {/* Left: Identity & Destination */}
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                          <PhoneCall className="w-4 h-4 text-blue-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="font-bold text-slate-900 text-sm">Client Calling & Voice History</h4>
                            <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-[10px] font-bold font-mono px-2 py-0.5 rounded-full">
                              {leadCalls.length} {leadCalls.length === 1 ? 'call' : 'calls'} logged
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-0.5 flex-wrap">
                            <span className="text-slate-400">Phone Number:</span>
                            <span className="font-mono text-blue-700 font-semibold bg-blue-50/80 px-2 py-0.5 rounded text-[11px] border border-blue-100">
                              {formatPhoneNumber(selectedLead.phone) || 'No phone registered'}
                            </span>
                            {selectedLead.phone && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  navigator.clipboard.writeText(String(selectedLead.phone));
                                  toast.success('Phone number copied to clipboard!');
                                }}
                                className="h-5 px-1.5 text-[10px] text-slate-500 hover:text-slate-800"
                              >
                                Copy
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Right: Primary Call Action */}
                      <div className="flex items-center gap-2 self-start sm:self-center">
                        <Button
                          size="sm"
                          onClick={() => handleStartCall(selectedLead)}
                          className="h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold gap-1.5 px-3.5 shadow-sm rounded-lg transition-all"
                        >
                          <PhoneCall className="w-3.5 h-3.5" /> Call Client Now
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleWhatsAppCall(selectedLead.phone)}
                          className="h-8 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 font-semibold gap-1.5 px-3 rounded-lg"
                        >
                          <MessageCircle className="w-3.5 h-3.5" /> WhatsApp Call
                        </Button>
                      </div>
                    </div>

                    {/* Bottom Row: Calling Metrics Summary */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2.5 border-t border-slate-100">
                      <div className="bg-slate-50/80 rounded-lg p-2 border border-slate-100">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Total Calls</span>
                        <span className="text-base font-extrabold text-slate-800 font-mono">{leadCalls.length}</span>
                      </div>
                      <div className="bg-slate-50/80 rounded-lg p-2 border border-slate-100">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Total Talk Time</span>
                        <span className="text-base font-extrabold text-blue-700 font-mono">
                          {formatCallDuration(leadCalls.reduce((acc, c) => acc + (c.duration_seconds || 0), 0))}
                        </span>
                      </div>
                      <div className="bg-slate-50/80 rounded-lg p-2 border border-slate-100">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Voice Recordings</span>
                        <span className="text-base font-extrabold text-purple-700 font-mono">
                          {leadCalls.filter(c => c.recording_url).length}
                        </span>
                      </div>
                      <div className="bg-slate-50/80 rounded-lg p-2 border border-slate-100 flex items-center justify-between">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Last Call</span>
                          <span className="text-xs font-semibold text-slate-700 truncate block">
                            {leadCalls[0]?.created_at ? timeAgo(leadCalls[0].created_at) : 'None'}
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => loadLeadCalls(selectedLead.id)}
                          disabled={leadCallsLoading}
                          className="h-7 w-7 p-0 text-slate-400 hover:text-slate-700"
                          title="Refresh Calls"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${leadCallsLoading ? 'animate-spin' : ''}`} />
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Calls List */}
                  {leadCallsLoading ? (
                    <Card className="p-8 text-center bg-white border-slate-200">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto text-blue-600 mb-2" />
                      <p className="text-xs text-slate-500 font-medium">Loading call records & voice recordings...</p>
                    </Card>
                  ) : leadCalls.length === 0 ? (
                    <Card className="p-10 text-center bg-white border-slate-200 space-y-3">
                      <div className="w-14 h-14 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto shadow-sm">
                        <PhoneCall className="w-7 h-7" />
                      </div>
                      <div>
                        <h4 className="font-bold text-slate-900 text-sm">No Calls Recorded Yet</h4>
                        <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                          Initiate your first call with <strong className="text-slate-700">{selectedLead.name}</strong>. The system records call duration, advisor notes, and live audio consultation automatically.
                        </p>
                      </div>
                      <div className="flex items-center justify-center gap-2 pt-2">
                        <Button
                          size="sm"
                          onClick={() => handleStartCall(selectedLead)}
                          className="h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold gap-1.5 px-4 shadow-sm"
                        >
                          <PhoneCall className="w-3.5 h-3.5" /> Start Call with {selectedLead.name}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleWhatsAppCall(selectedLead.phone)}
                          className="h-8 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 gap-1.5"
                        >
                          <MessageCircle className="w-3.5 h-3.5" /> WhatsApp Call
                        </Button>
                      </div>
                    </Card>
                  ) : (
                    <div className="space-y-3">
                      {leadCalls.map((c) => {
                        const isOut = (c.direction || 'outgoing') === 'outgoing';
                        return (
                          <Card key={c.id} className="p-4 bg-white border-slate-200 hover:border-slate-300 transition-all shadow-sm">
                            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                              {/* Left details */}
                              <div className="flex items-start gap-3 flex-1 min-w-0">
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${isOut ? 'bg-blue-50 text-blue-600 border border-blue-100' : 'bg-emerald-50 text-emerald-600 border border-emerald-100'}`}>
                                  {isOut ? <PhoneOutgoing className="w-4 h-4" /> : <PhoneIncoming className="w-4 h-4" />}
                                </div>
                                <div className="space-y-1.5 flex-1 min-w-0">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="font-bold text-slate-900 text-xs">
                                      {isOut ? 'Outgoing Consultation Call' : 'Incoming Client Call'}
                                    </span>
                                    <Badge className={`text-[10px] px-2 py-0.5 capitalize font-semibold ${isOut ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                                      {c.direction || 'outgoing'}
                                    </Badge>
                                    {c.outcome && (
                                      <Badge variant="outline" className="text-[10px] px-2 py-0.5 capitalize font-semibold bg-slate-50 text-slate-700">
                                        {c.outcome.replace(/_/g, ' ')}
                                      </Badge>
                                    )}
                                    {c.duration_seconds > 0 && (
                                      <span className="text-[11px] font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                                        ⏱️ {formatCallDuration(c.duration_seconds)}
                                      </span>
                                    )}
                                  </div>

                                  <div className="flex flex-wrap items-center gap-2.5 text-[11px] text-slate-500">
                                    <span>Advisor: <strong className="text-slate-700">{c.sales_person_name || 'LEAMSS Consultant'}</strong></span>
                                    <span>•</span>
                                    <span title={c.created_at ? new Date(c.created_at).toLocaleString() : ''}>
                                      {timeAgo(c.created_at)} ({c.created_at ? new Date(c.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'})
                                    </span>
                                  </div>

                                  {/* Notes */}
                                  {c.notes && (
                                    <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-700 mt-1">
                                      <span className="font-semibold text-slate-900">Notes:</span> {c.notes}
                                    </div>
                                  )}

                                  {/* Audio Player */}
                                  {c.recording_url ? (
                                    <div className="pt-2">
                                      <CallAudioPlayer
                                        recordingUrl={c.recording_url}
                                        durationSeconds={c.duration_seconds}
                                        callerName={selectedLead.name}
                                      />
                                    </div>
                                  ) : (
                                    <p className="text-[11px] text-slate-400 italic pt-1">
                                      No audio recording captured for this call session.
                                    </p>
                                  )}

                                  {/* AI Call Intelligence & Summary Section */}
                                  <div className="mt-3 rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/50 via-purple-50/25 to-white p-3 shadow-xs">
                                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-indigo-100/80">
                                      <div className="flex items-center gap-2">
                                        <div className="w-6 h-6 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                                          <Sparkles className="w-3.5 h-3.5" />
                                        </div>
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                          <span className="text-xs font-bold text-slate-900">
                                            AI Call Summary & Requirements
                                          </span>
                                          {c.ai_sentiment && (
                                            <Badge className={`text-[10px] px-1.5 py-0 font-semibold border ${
                                              c.ai_sentiment.toLowerCase() === 'positive' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                                              c.ai_sentiment.toLowerCase() === 'negative' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                                              'bg-slate-100 text-slate-700 border-slate-200'
                                            }`}>
                                              {c.ai_sentiment} Sentiment
                                            </Badge>
                                          )}
                                        </div>
                                      </div>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        disabled={regeneratingAiCalls[c.id]}
                                        onClick={() => handleRegenerateAiSummary(c.id)}
                                        className="h-6 px-2 text-[11px] text-indigo-700 border-indigo-200 hover:bg-indigo-50 gap-1 font-semibold"
                                        title="Regenerate structured AI analysis"
                                      >
                                        <RefreshCw className={`w-3 h-3 ${regeneratingAiCalls[c.id] ? 'animate-spin' : ''}`} />
                                        {regeneratingAiCalls[c.id] ? 'Analyzing...' : 'Refresh AI Summary'}
                                      </Button>
                                    </div>

                                    {/* 4-part Structured Intelligence Grid */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 text-xs">
                                      <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                        <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                          <span>📌</span>
                                          <span>Main Discussion</span>
                                        </div>
                                        <p className="text-slate-600 text-xs leading-relaxed">
                                          {c.ai_summary_structured?.main_discussion || c.ai_summary || c.notes || 'Discussion notes pending analysis.'}
                                        </p>
                                      </div>

                                      <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                        <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                          <span>🎯</span>
                                          <span>Client Requirements</span>
                                        </div>
                                        <p className="text-slate-600 text-xs leading-relaxed">
                                          {c.ai_summary_structured?.client_requirements || 'Standard consultation requirement.'}
                                        </p>
                                      </div>

                                      <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                        <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                          <span>⚠️</span>
                                          <span>Concerns & Objections</span>
                                        </div>
                                        <p className="text-slate-600 text-xs leading-relaxed">
                                          {c.ai_summary_structured?.concerns || 'None noted during consultation.'}
                                        </p>
                                      </div>

                                      <div className="bg-white/90 p-2.5 rounded-lg border border-indigo-50 shadow-2xs">
                                        <div className="flex items-center gap-1.5 font-bold text-slate-800 text-[11px] mb-1">
                                          <span>⏭️</span>
                                          <span>Next Steps</span>
                                        </div>
                                        <p className="text-slate-700 text-xs leading-relaxed font-semibold text-indigo-950">
                                          {c.ai_summary_structured?.next_steps || c.next_best_action || 'Follow up with client as scheduled.'}
                                        </p>
                                      </div>
                                    </div>
                                  </div>

                                  {/* Complete Call Transcript Section */}
                                  <div className="mt-2.5 rounded-xl border border-slate-200 bg-slate-50/70 p-3 shadow-xs">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <div className="flex items-center gap-2">
                                        <div className="w-6 h-6 rounded-lg bg-slate-800 text-white flex items-center justify-center shadow-xs">
                                          <FileText className="w-3.5 h-3.5" />
                                        </div>
                                        <div className="flex items-center gap-2 flex-wrap">
                                          <span className="text-xs font-bold text-slate-900">Complete Call Transcript</span>
                                          {c.transcript && c.transcript.trim() ? (
                                            <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px] font-semibold px-2 py-0">
                                              ✓ Full Conversation Captured
                                            </Badge>
                                          ) : (
                                            <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-200 text-[10px] font-medium px-2 py-0">
                                              Transcript Unavailable
                                            </Badge>
                                          )}
                                        </div>
                                      </div>

                                      <div className="flex items-center gap-1.5 flex-wrap">
                                        {c.transcript && c.transcript.trim() ? (
                                          <>
                                            <Button
                                              size="sm"
                                              variant="ghost"
                                              onClick={() => {
                                                navigator.clipboard.writeText(c.transcript);
                                                toast.success('Transcript copied to clipboard!');
                                              }}
                                              className="h-6 px-2 text-[11px] text-slate-600 hover:text-slate-900 gap-1 font-semibold"
                                            >
                                              <Copy className="w-3 h-3" /> Copy
                                            </Button>
                                            <Button
                                              size="sm"
                                              variant="outline"
                                              onClick={() => handleOpenTranscriptModal(c)}
                                              className="h-6 px-2 text-[11px] text-indigo-700 border-indigo-200 hover:bg-indigo-50 gap-1 font-semibold"
                                            >
                                              <Edit className="w-3 h-3" /> Edit
                                            </Button>
                                            <Button
                                              size="sm"
                                              variant="secondary"
                                              onClick={() => toggleTranscript(c.id)}
                                              className="h-6 px-2 text-[11px] font-bold gap-1 bg-slate-200 hover:bg-slate-300 text-slate-800"
                                            >
                                              {expandedTranscripts[c.id] ? (
                                                <>Hide Dialogue <ChevronDown className="w-3 h-3 rotate-180 transition-transform" /></>
                                              ) : (
                                                <>Read Transcript ({c.transcript.split('\n').length} lines) <ChevronDown className="w-3 h-3 transition-transform" /></>
                                              )}
                                            </Button>
                                          </>
                                        ) : (
                                          <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => handleOpenTranscriptModal(c)}
                                            className="h-6 px-2.5 text-[11px] text-indigo-700 border-indigo-200 bg-white hover:bg-indigo-50 gap-1 font-bold shadow-2xs"
                                          >
                                            <Plus className="w-3 h-3" /> Add / Attach Transcript
                                          </Button>
                                        )}
                                      </div>
                                    </div>

                                    {/* Expanded Verbatim Conversation Transcript */}
                                    {c.transcript && c.transcript.trim() && expandedTranscripts[c.id] && (
                                      <div className="mt-2.5 pt-2 border-t border-slate-200">
                                        <div className="max-h-60 overflow-y-auto rounded-lg bg-slate-900 text-slate-100 p-3 font-mono text-xs leading-relaxed shadow-inner border border-slate-800 whitespace-pre-wrap select-text">
                                          {c.transcript}
                                        </div>
                                      </div>
                                    )}

                                    {/* Genuine Status Note When Transcript Unavailable (No dummy data) */}
                                    {(!c.transcript || !c.transcript.trim()) && (
                                      <div className="mt-2 text-[11px] text-slate-500 bg-white/80 p-2 rounded-lg border border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                                        <div className="flex items-center gap-1.5 text-amber-700">
                                          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                                          <span>
                                            {c.transcription_status_reason || 'Audio stream not transcribed / No dialogue transcript was attached for this call.'}
                                          </span>
                                        </div>
                                        <button
                                          onClick={() => handleOpenTranscriptModal(c)}
                                          className="text-[11px] text-indigo-600 hover:underline font-semibold whitespace-nowrap self-start sm:self-auto"
                                        >
                                          Click to paste conversation →
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {/* Right: Quick actions */}
                              <div className="flex items-center sm:flex-col gap-1.5 shrink-0 self-end sm:self-start">
                                <Button
                                  size="sm"
                                  onClick={() => handleStartCall(selectedLead)}
                                  className="h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white font-bold gap-1 shadow-sm"
                                >
                                  <PhoneCall className="w-3 h-3" /> Call Again
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleWhatsAppCall(selectedLead.phone)}
                                  className="h-7 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 gap-1 font-semibold"
                                >
                                  <MessageCircle className="w-3 h-3" /> WhatsApp
                                </Button>
                              </div>
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* TAB: WHATSAPP & CHAT (OMNICHANNEL DIRECT CLIENT COMMUNICATION) */}
              {workspaceTab === 'whatsapp' && (() => {
                const salesRepName = currentUser?.name || selectedLead.assigned_to_name || 'LEAMSS Consultant';
                const cleanNum = getSanitizedWhatsAppNumber(selectedLead.whatsapp_number || selectedLead.phone);
                const smartTemplates = getPersonalizedWaTemplates(selectedLead, salesRepName, waTemplates);

                return (
                  <div className="space-y-4 text-xs">
                    {/* Action Bar */}
                    <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-3.5 space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        {/* Left: Identity & WhatsApp Number */}
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                            <MessageCircle className="w-5 h-5 text-emerald-600" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4 className="font-bold text-slate-900 text-sm">WhatsApp Communication & Direct Chat</h4>
                              <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px] font-bold font-mono px-2 py-0.5 rounded-full">
                                {leadWhatsApp.length} {leadWhatsApp.length === 1 ? 'interaction' : 'interactions'}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5 flex-wrap">
                              <span className="text-slate-400">WhatsApp:</span>
                              <span className="font-mono text-emerald-700 font-semibold bg-emerald-50/80 px-2 py-0.5 rounded text-[11px] border border-emerald-100">
                                {formatPhoneNumber(selectedLead.whatsapp_number || selectedLead.phone) || 'No number'}
                              </span>
                              {(selectedLead.whatsapp_number || selectedLead.phone) && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    navigator.clipboard.writeText(String(selectedLead.whatsapp_number || selectedLead.phone));
                                    toast.success('WhatsApp number copied to clipboard!');
                                  }}
                                  className="h-5 px-1.5 text-[10px] text-slate-500 hover:text-slate-800"
                                >
                                  Copy
                                </Button>
                              )}
                              <span className="text-slate-300">•</span>
                              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-800 bg-emerald-100/60 px-2 py-0.5 rounded-md">
                                <UserCheck className="w-3 h-3 text-emerald-600" /> Sending as: <strong>{salesRepName}</strong>
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Right: Quick Actions */}
                        <div className="flex items-center gap-2 self-start sm:self-center flex-wrap">
                          <Button
                            size="sm"
                            onClick={() => handleWhatsAppCall(selectedLead.whatsapp_number || selectedLead.phone, selectedLead)}
                            className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1.5 px-3.5 shadow-sm rounded-lg transition-all"
                            title="Start WhatsApp voice call and auto-log to CRM history"
                          >
                            <PhoneCall className="w-3.5 h-3.5" /> WhatsApp Call
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => window.open(getDirectWhatsAppWebLink(cleanNum), '_blank')}
                            className="h-8 text-xs text-emerald-800 border-emerald-300 hover:bg-emerald-50 font-semibold gap-1.5 px-3 rounded-lg"
                            title="Open direct WhatsApp Web conversation"
                          >
                            <ArrowUpRight className="w-3.5 h-3.5 text-emerald-600" /> Web (Fallback)
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              loadLeadWhatsApp(selectedLead.id);
                              loadWhatsAppSessionStatus(selectedLead.id);
                            }}
                            disabled={leadWhatsAppLoading}
                            className="h-8 w-8 p-0 text-slate-400 hover:text-slate-700"
                            title="Refresh messages"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${leadWhatsAppLoading ? 'animate-spin' : ''}`} />
                          </Button>
                        </div>
                      </div>

                      {/* ──────────────────────────────────────────────────────────── */}
                      {/* AI SMART REPLY ASSISTANT (Product Master Grounded) */}
                      {/* ──────────────────────────────────────────────────────────── */}
                      <div className="pt-2 border-t border-slate-100">
                        <div className="bg-gradient-to-r from-emerald-50/90 via-teal-50/70 to-slate-50 border border-emerald-200/90 rounded-xl p-3 space-y-2.5 shadow-2xs">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="p-1 rounded-md bg-emerald-600 text-white shadow-2xs">
                                <Sparkles className="w-3.5 h-3.5 animate-pulse" />
                              </span>
                              <div>
                                <h5 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                                  AI Smart Reply Assistant
                                  <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] py-0 px-1.5 font-semibold">
                                    Product Master Grounded
                                  </Badge>
                                </h5>
                                <p className="text-[10px] text-slate-500">
                                  Instant, policy-accurate replies for {selectedLead.name} ({selectedLead.interested_country || selectedLead.country || 'Target Country'})
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setShowAiWaPanel(!showAiWaPanel)}
                                className="h-7 text-xs text-emerald-700 hover:text-emerald-900 hover:bg-emerald-100/60 font-semibold px-2"
                              >
                                {showAiWaPanel ? 'Hide Assistant' : 'Open Assistant'}
                              </Button>
                            </div>
                          </div>

                          {/* Quick Action Intent Pills */}
                          <div className="flex flex-wrap items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleGenerateAiWaReply('reply_client')}
                              disabled={aiWaLoading}
                              className="px-2.5 py-1 text-[11px] rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-medium flex items-center gap-1 shadow-2xs transition-all disabled:opacity-50"
                            >
                              <Bot className="w-3 h-3" />
                              <span>{aiWaLoading ? 'Generating...' : '✨ Reply to Latest Client Query'}</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleGenerateAiWaReply('fees_proposal', 'What are the total government fees and LEAMSS service charges?')}
                              disabled={aiWaLoading}
                              className="px-2.5 py-1 text-[11px] rounded-lg bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-medium flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              <span>💰 Fees & Installments</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleGenerateAiWaReply('eligibility_breakdown', 'What are the eligibility points, pass marks and language requirements?')}
                              disabled={aiWaLoading}
                              className="px-2.5 py-1 text-[11px] rounded-lg bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-medium flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              <span>📊 Eligibility & Points</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleGenerateAiWaReply('document_checklist', 'What documents do I need to send to start?')}
                              disabled={aiWaLoading}
                              className="px-2.5 py-1 text-[11px] rounded-lg bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-medium flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              <span>📄 Document Checklist</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleGenerateAiWaReply('objection_handling', 'Client says the fee is too high or asks if approval is 100% guaranteed.')}
                              disabled={aiWaLoading}
                              className="px-2.5 py-1 text-[11px] rounded-lg bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-medium flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              <span>🛡️ Address Objection</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleGenerateAiWaReply('process_roadmap', 'What are the step by step stages from start to visa grant?')}
                              disabled={aiWaLoading}
                              className="px-2.5 py-1 text-[11px] rounded-lg bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 font-medium flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              <span>🚀 Process Roadmap</span>
                            </button>
                          </div>

                          {/* Custom Question Bar if panel is open */}
                          {showAiWaPanel && (
                            <div className="flex items-center gap-1.5 pt-1">
                              <Input
                                placeholder="Or type specific question / objection from client..."
                                value={aiWaCustomPrompt}
                                onChange={(e) => setAiWaCustomPrompt(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter' && !aiWaLoading && aiWaCustomPrompt.trim()) {
                                    handleGenerateAiWaReply('custom_qa', aiWaCustomPrompt);
                                  }
                                }}
                                className="h-7 text-xs bg-white border-emerald-200 focus:border-emerald-400 placeholder:text-slate-400"
                              />
                              <Button
                                size="sm"
                                onClick={() => handleGenerateAiWaReply('custom_qa', aiWaCustomPrompt)}
                                disabled={aiWaLoading || !aiWaCustomPrompt.trim()}
                                className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-3 shrink-0"
                              >
                                Ask AI
                              </Button>
                            </div>
                          )}

                          {/* AI Generated Suggestion Box */}
                          {aiWaSuggestion && (
                            <div className="bg-white rounded-lg p-2.5 border border-emerald-300 shadow-xs space-y-2 text-xs">
                              <div className="flex items-center justify-between border-b border-emerald-100 pb-1.5">
                                <span className="font-semibold text-emerald-900 flex items-center gap-1.5 text-[11px]">
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                  Suggested Ready-to-Send Reply:
                                </span>
                                <div className="flex items-center gap-1.5">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => {
                                      navigator.clipboard.writeText(aiWaSuggestion);
                                      toast.success('Copied suggestion to clipboard!');
                                    }}
                                    className="h-6 text-[11px] text-slate-600 hover:text-slate-900 px-2 gap-1"
                                  >
                                    <Copy className="w-3 h-3" /> Copy
                                  </Button>
                                  <Button
                                    size="sm"
                                    onClick={() => {
                                      setWaComposerText(aiWaSuggestion);
                                      toast.success('Pasted into WhatsApp message box below!');
                                    }}
                                    className="h-6 text-[11px] bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-2.5 gap-1 rounded"
                                  >
                                    <ClipboardPaste className="w-3 h-3" /> Use in Composer
                                  </Button>
                                </div>
                              </div>

                              <div className="whitespace-pre-wrap font-sans text-slate-800 text-[11px] leading-relaxed max-h-36 overflow-y-auto bg-slate-50/60 p-2 rounded border border-slate-100">
                                {aiWaSuggestion}
                              </div>

                              {/* Talking Points / Policy Grounding */}
                              {aiWaTalkingPoints.length > 0 && (
                                <div className="flex flex-wrap items-center gap-1 pt-1 text-[10px] text-emerald-800 font-medium">
                                  <span className="font-bold text-slate-500">Key Facts:</span>
                                  {aiWaTalkingPoints.map((tp, idx) => (
                                    <span key={idx} className="bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded text-[10px]">
                                      {tp}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Approved Templates Selector & 1-Click Pills */}
                      <div className="pt-2 border-t border-slate-100 space-y-2">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <label className="text-[11px] font-semibold text-slate-700 flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Choose Approved WhatsApp Template:
                          </label>
                          <div className="flex items-center gap-2">
                            <Select
                              value={selectedWaTemplate}
                              onValueChange={(val) => {
                                setSelectedWaTemplate(val);
                                const matched = smartTemplates.find((t) => t.title === val || t.id === val);
                                if (matched) {
                                  setWaComposerText(matched.text);
                                }
                              }}
                            >
                              <SelectTrigger className="h-8 text-xs bg-slate-50 border-slate-200 min-w-[240px]">
                                <SelectValue placeholder="-- Select Approved Template --" />
                              </SelectTrigger>
                              <SelectContent>
                                {smartTemplates.map((tpl) => (
                                  <SelectItem key={tpl.id} value={tpl.title}>
                                    <span className="font-medium">{tpl.title}</span> <span className="text-[10px] text-slate-400">({tpl.category})</span>
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            {selectedWaTemplate && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  setSelectedWaTemplate('');
                                  setWaComposerText('');
                                }}
                                className="h-8 text-xs text-slate-400 hover:text-rose-600 px-2"
                              >
                                Clear
                              </Button>
                            )}
                          </div>
                        </div>

                        {/* 1-Click Fast Pill Buttons */}
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {smartTemplates.map((tpl) => {
                            const isSelected = selectedWaTemplate === tpl.title;
                            return (
                              <button
                                key={tpl.id}
                                type="button"
                                onClick={() => {
                                  setSelectedWaTemplate(tpl.title);
                                  setWaComposerText(tpl.text);
                                }}
                                className={`px-2.5 py-1 text-[11px] rounded-lg border transition-all font-medium text-left ${
                                  isSelected
                                    ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                                    : 'bg-slate-100/90 hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-200 border-slate-200 text-slate-700'
                                }`}
                              >
                                {tpl.title}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Live Message Composer */}
                      <div className="pt-2 border-t border-slate-100 space-y-2">
                        <Textarea
                          placeholder={`Type WhatsApp message to ${selectedLead.name} (or choose template above)...`}
                          value={waComposerText}
                          onChange={(e) => setWaComposerText(e.target.value)}
                          className="h-20 text-xs bg-slate-50/70 border-slate-200 focus:bg-white resize-none"
                        />

                        {/* Media attachment preview if present */}
                        {waAttachedMedia && (
                          <div className="px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between text-xs text-emerald-900">
                            <span className="flex items-center gap-1.5 truncate">
                              <Paperclip className="w-3.5 h-3.5 text-emerald-700" /> Attached: <strong>{waAttachedMedia.filename}</strong> ({waAttachedMedia.type})
                            </span>
                            <button
                              type="button"
                              onClick={() => setWaAttachedMedia(null)}
                              className="text-slate-400 hover:text-rose-600 p-0.5"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}

                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-400">
                              {waComposerText.length} chars • Sending as: <strong>{salesRepName}</strong>
                            </span>
                          </div>

                          <div className="flex items-center gap-2 flex-wrap">
                            <Button
                              size="sm"
                              onClick={() => handleSendWhatsAppMessage({
                                lead: selectedLead,
                                text: waComposerText,
                                mode: 'web',
                                template_name: selectedWaTemplate || null
                              })}
                              disabled={waSending || (!waComposerText.trim() && !waAttachedMedia)}
                              className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 px-4 rounded-lg shadow-sm"
                              title="Opens client's real WhatsApp in WhatsApp Web with this message pre-filled & records in CRM history"
                            >
                              {waSending ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                              🚀 Send via WhatsApp Web
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Conversation Message Feed */}
                    {leadWhatsAppLoading ? (
                      <Card className="p-8 text-center bg-white border-slate-200">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto text-emerald-600 mb-2" />
                        <p className="text-xs text-slate-500 font-medium">Loading WhatsApp conversation history...</p>
                      </Card>
                    ) : leadWhatsApp.length === 0 ? (
                      <Card className="p-10 text-center bg-white border-slate-200 space-y-3">
                        <div className="w-14 h-14 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto shadow-sm">
                          <MessageCircle className="w-7 h-7" />
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-900 text-sm">No WhatsApp Messages Logged Yet</h4>
                          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                            Connect with <strong className="text-slate-700">{selectedLead.name}</strong> on WhatsApp. Click any template above to compose and send directly via official Meta WhatsApp Cloud API.
                          </p>
                        </div>
                        <div className="flex items-center justify-center gap-2 pt-2 flex-wrap">
                          <Button
                            size="sm"
                            onClick={() => {
                              const tpl = smartTemplates[0];
                              setSelectedWaTemplate(tpl.title);
                              setWaComposerText(tpl.text);
                            }}
                            className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1.5 px-4 shadow-sm"
                          >
                            <Sparkles className="w-3.5 h-3.5" /> Use Welcome Template
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleWhatsAppCall(selectedLead.whatsapp_number || selectedLead.phone, selectedLead)}
                            className="h-8 text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 gap-1.5 font-semibold"
                          >
                            <PhoneCall className="w-3.5 h-3.5" /> Start WhatsApp Call
                          </Button>
                        </div>
                      </Card>
                    ) : (
                      <div className="space-y-3">
                        {leadWhatsApp.map((msg) => {
                          const isOut = (msg.direction || 'outbound') === 'outbound';
                          const isCall = msg.type === 'call' || String(msg.text || '').startsWith('📞');

                          return (
                            <div
                              key={msg.id}
                              className={`flex flex-col ${isOut ? 'items-end' : 'items-start'}`}
                            >
                              <div
                                className={`max-w-[85%] sm:max-w-[75%] p-3.5 rounded-2xl shadow-xs transition-all space-y-1.5 ${
                                  isCall
                                    ? 'bg-amber-50/90 border border-amber-200 text-amber-950 w-full max-w-none'
                                    : isOut
                                    ? 'bg-emerald-600 text-white rounded-br-xs'
                                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-xs'
                                }`}
                              >
                                <div className="flex items-center justify-between gap-3 text-[11px]">
                                  <div className="flex items-center gap-1.5 font-semibold">
                                    {isCall ? (
                                      <span className="flex items-center gap-1 text-amber-800 font-bold">
                                        <PhoneCall className="w-3.5 h-3.5 text-amber-600" /> WhatsApp Call
                                      </span>
                                    ) : isOut ? (
                                      <span className="flex items-center gap-1 text-emerald-100">
                                        <UserCheck className="w-3 h-3 text-emerald-200" /> {msg.sales_person_name || salesRepName} (Sales Person)
                                      </span>
                                    ) : (
                                      <span className="text-slate-700 font-bold">
                                        {msg.contact_name || selectedLead.name}
                                      </span>
                                    )}
                                  </div>
                                  <span className={`text-[10px] ${isCall ? 'text-amber-700' : isOut ? 'text-emerald-100' : 'text-slate-400'}`}>
                                    {msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                                  </span>
                                </div>

                                {/* Template Badge if template was used */}
                                {msg.template_name && (
                                  <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                                    isOut ? 'bg-emerald-700/80 text-emerald-100 border border-emerald-500/30' : 'bg-slate-100 text-slate-700 border border-slate-200'
                                  }`}>
                                    <FileText className="w-3 h-3 text-emerald-200" /> Template: {msg.template_name}
                                  </div>
                                )}

                                {/* Media Attachment Rendering */}
                                {msg.media_url && (
                                  <div className="rounded-lg overflow-hidden my-1">
                                    {msg.media_type === 'image' ? (
                                      <img
                                        src={msg.media_url}
                                        alt="Media Attachment"
                                        className="max-h-56 w-full object-cover rounded-lg cursor-pointer hover:opacity-95"
                                        onClick={() => window.open(msg.media_url, '_blank')}
                                      />
                                    ) : msg.media_type === 'audio' ? (
                                      <audio controls src={msg.media_url} className="w-full h-8 my-1" />
                                    ) : (
                                      <a
                                        href={msg.media_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className={`flex items-center gap-2 p-2 rounded-lg text-xs font-semibold ${isOut ? 'bg-emerald-700/60 text-white' : 'bg-slate-100 text-slate-800'}`}
                                      >
                                        <Paperclip className="w-4 h-4" /> {msg.media_filename || 'Download Document'}
                                      </a>
                                    )}
                                  </div>
                                )}

                                {msg.text && (
                                  <p className={`text-xs whitespace-pre-wrap leading-relaxed ${isCall ? 'font-medium' : ''}`}>
                                    {msg.text}
                                  </p>
                                )}

                                <div className="flex items-center justify-between pt-1 text-[10px]">
                                  <span className={isCall ? 'text-amber-700' : isOut ? 'text-emerald-200' : 'text-slate-400'}>
                                    {msg.created_at ? new Date(msg.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''}
                                  </span>
                                  {isOut && !isCall && (
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-semibold flex items-center gap-1">
                                        {msg.status === 'read' ? (
                                          <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                            className="flex items-center gap-0.5 text-sky-300 font-bold hover:underline cursor-pointer"
                                            title="Click to view message verification & audit details"
                                          >
                                            <CheckCheck className="w-3.5 h-3.5 text-sky-300" /> Read
                                          </button>
                                        ) : msg.status === 'delivered' ? (
                                          <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                            className="flex items-center gap-0.5 text-emerald-200 hover:underline cursor-pointer"
                                            title="Click to view message verification & audit details"
                                          >
                                            <CheckCheck className="w-3.5 h-3.5 text-emerald-200" /> Delivered
                                          </button>
                                        ) : msg.status === 'sent' ? (
                                          <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                            className="flex items-center gap-0.5 text-emerald-200/90 hover:text-white hover:underline cursor-pointer"
                                            title="Click to view message verification & audit details"
                                          >
                                            <CheckCheck className="w-3.5 h-3.5 text-emerald-200" /> Sent (WhatsApp Web)
                                          </button>
                                        ) : msg.status === 'pending_confirmation' ? (
                                          <div className="flex items-center gap-1 bg-amber-500/25 px-2 py-0.5 rounded text-[10px] text-amber-100 font-semibold border border-amber-400/30">
                                            <Clock className="w-3 h-3 text-amber-300 animate-pulse" />
                                            <button
                                              type="button"
                                              onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                              className="hover:underline cursor-pointer"
                                              title="Click to view verification details"
                                            >
                                              Pending Confirmation:
                                            </button>
                                            <button
                                              type="button"
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handleConfirmWhatsAppStatus(msg.id || msg._id, 'sent', selectedLead);
                                              }}
                                              className="px-1.5 py-0.5 bg-emerald-500 hover:bg-emerald-400 text-white rounded text-[9px] font-bold shadow-xs ml-0.5 cursor-pointer"
                                              title="Confirm message was sent in WhatsApp Web"
                                            >
                                              ✓ Sent
                                            </button>
                                            <button
                                              type="button"
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handleConfirmWhatsAppStatus(msg.id || msg._id, 'failed', selectedLead);
                                              }}
                                              className="px-1.5 py-0.5 bg-rose-500 hover:bg-rose-600 text-white rounded text-[9px] font-bold shadow-xs ml-0.5 cursor-pointer"
                                              title="Mark as not sent or failed"
                                            >
                                              ✕ Failed
                                            </button>
                                          </div>
                                        ) : msg.status === 'failed' ? (
                                          <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                            className="flex items-center gap-0.5 text-rose-300 font-bold hover:underline cursor-pointer"
                                            title={msg.error_message || "Delivery failed — click to view details"}
                                          >
                                            <AlertCircle className="w-3.5 h-3.5 text-rose-300" /> Failed
                                          </button>
                                        ) : (
                                          <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); setViewingWaMessage(msg); }}
                                            className="flex items-center gap-0.5 text-emerald-200/70 hover:underline cursor-pointer"
                                          >
                                            <Check className="w-3 h-3" /> Logged
                                          </button>
                                        )}
                                      </span>
                                      <button
                                        type="button"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          const webUrl = getDirectWhatsAppWebLink(selectedLead.whatsapp_number || selectedLead.phone, msg.text);
                                          if (webUrl) window.open(webUrl, '_blank');
                                        }}
                                        className="inline-flex items-center gap-0.5 text-[10px] text-emerald-200 hover:text-white underline underline-offset-2 ml-1"
                                        title="Re-open this message in WhatsApp Web"
                                      >
                                        <ArrowUpRight className="w-2.5 h-2.5" /> Re-open Web
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* TAB: EMAILS & THREAD (REAL DELIVERY & INBOUND TRACKING) */}
              {workspaceTab === 'emails' && (
                <div className="space-y-4 text-xs">
                  {/* Action Bar */}
                  <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-3.5 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      {/* Left: Identity & Destination */}
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
                          <Mail className="w-4 h-4 text-indigo-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="font-bold text-slate-900 text-sm">Client Email Communications</h4>
                            <Badge className="bg-indigo-50 text-indigo-700 border-indigo-200 text-[10px] font-bold font-mono px-2 py-0.5 rounded-full">
                              {leadEmails.length} {leadEmails.length === 1 ? 'message' : 'messages'}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-0.5 flex-wrap">
                            <span className="text-slate-400">Destination:</span>
                            <span className="font-mono text-indigo-700 font-semibold bg-indigo-50/80 px-2 py-0.5 rounded text-[11px] border border-indigo-100">
                              {selectedLead.email || 'No email registered'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Right: Primary Compose Action (Always prominent, never wrapped awkwardly) */}
                      <div className="flex items-center gap-2 self-start sm:self-center">
                        <Button
                          size="sm"
                          onClick={() => handleOpenEmailModal('', '', null, selectedLead)}
                          className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 px-3.5 shadow-sm rounded-lg transition-all"
                        >
                          <Plus className="w-3.5 h-3.5" /> Compose Email
                        </Button>
                      </div>
                    </div>

                    {/* Bottom Row: Controls Toolbar (Sort, Sync, Simulate) */}
                    <div className="flex items-center justify-between gap-2 pt-2.5 border-t border-slate-100 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-medium text-slate-400">Order:</span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            const nextSort = emailSortOrder === 'desc' ? 'asc' : 'desc';
                            setEmailSortOrder(nextSort);
                            if (selectedLead?.id) {
                              loadLeadEmails(selectedLead.id, nextSort);
                            }
                          }}
                          className="h-7 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200/80 font-medium gap-1 px-2.5 rounded-md"
                          title={emailSortOrder === 'desc' ? 'Currently: Newest First (Click to view Oldest First)' : 'Currently: Oldest First (Click to view Newest First)'}
                        >
                          <ArrowUpDown className="w-3 h-3 text-indigo-600" />
                          <span>{emailSortOrder === 'desc' ? 'Newest on Top' : 'Oldest on Top'}</span>
                        </Button>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSyncMailbox()}
                          disabled={syncingMailbox}
                          className="h-7 text-xs bg-white text-indigo-700 border-indigo-200 hover:bg-indigo-50 font-medium gap-1.5 px-2.5 rounded-md shadow-sm"
                          title="Scan your email mailbox (INBOX & Sent) via IMAP for client replies"
                        >
                          <RefreshCw className={`w-3 h-3 ${syncingMailbox ? 'animate-spin text-indigo-600' : 'text-indigo-600'}`} />
                          <span>{syncingMailbox ? 'Syncing...' : 'Sync Mailbox'}</span>
                        </Button>

                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSimulateReply()}
                          disabled={simulatingReply}
                          className="h-7 text-xs bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50 font-medium gap-1.5 px-2.5 rounded-md shadow-sm"
                          title="Simulate an incoming email reply from the client to test inbound thread capture"
                        >
                          {simulatingReply ? <RefreshCw className="w-3 h-3 animate-spin text-emerald-600" /> : <MessageSquareReply className="w-3 h-3 text-emerald-600" />}
                          <span>Simulate Reply</span>
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Messages list */}
                  {emailsLoading ? (
                    <div className="text-center py-10 text-slate-400 space-y-2">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto text-indigo-600" />
                      <p>Loading email conversation thread...</p>
                    </div>
                  ) : displayedEmails.length === 0 ? (
                    <Card className="p-8 text-center space-y-3 bg-white border-dashed border-slate-300">
                      <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto">
                        <Mail className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="font-bold text-slate-800 text-sm">No Emails Recorded Yet</h4>
                        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                          Select an Admin-created email template to send an official assessment, proposal, or onboarding guide directly to this client.
                        </p>
                      </div>
                      <div className="flex items-center justify-center gap-2">
                        <Button size="sm" onClick={() => handleOpenEmailModal('', '', null, selectedLead)} className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs gap-1 font-semibold">
                          <Plus className="w-3.5 h-3.5" /> Compose Email
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => handleSyncMailbox()} disabled={syncingMailbox} className="text-xs border-indigo-200 text-indigo-700 hover:bg-indigo-50 gap-1 font-semibold">
                          <RefreshCw className={`w-3.5 h-3.5 ${syncingMailbox ? 'animate-spin' : ''}`} /> Check Mailbox
                        </Button>
                      </div>
                    </Card>
                  ) : (
                    <div className="space-y-3">
                      {displayedEmails.map((item, idx) => (
                        <div
                          key={item.id || idx}
                          className={`p-4 rounded-xl border transition-all ${
                            item.direction === 'inbound'
                              ? 'bg-emerald-50/40 border-emerald-200/90 ml-1 sm:ml-4 shadow-sm hover:border-emerald-300'
                              : 'bg-white border-slate-200 shadow-sm mr-1 sm:mr-4 hover:border-slate-300'
                          } ${idx === 0 && emailSortOrder === 'desc' ? 'ring-2 ring-indigo-400/40' : ''}`}
                        >
                          {/* Row 1: Badges & Actions */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2 mb-2">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {idx === 0 && emailSortOrder === 'desc' && (
                                <Badge className="bg-amber-50 text-amber-800 border-amber-200 text-[10px] font-bold">
                                  Latest Message
                                </Badge>
                              )}
                              {item.direction === 'inbound' ? (
                                <Badge className="bg-emerald-50 text-emerald-800 border-emerald-200 text-[10px] font-bold gap-1">
                                  <ArrowDownLeft className="w-3 h-3 text-emerald-700" /> Client Reply Received
                                </Badge>
                              ) : (
                                <Badge className="bg-indigo-50 text-indigo-800 border-indigo-200 text-[10px] font-bold gap-1">
                                  <ArrowUpRight className="w-3 h-3 text-indigo-700" /> Sent by {item.sales_person_name || 'Advisor'}
                                </Badge>
                              )}
                              {item.notify_by_email && (
                                <Badge variant="outline" className="text-[10px] text-indigo-700 bg-indigo-50/80 border-indigo-200 font-semibold gap-1">
                                  <Bell className="w-2.5 h-2.5 text-indigo-600" /> Gmail Notified
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-slate-400">
                              {item.status && (
                                <Badge
                                  variant="outline"
                                  className={`text-[10px] font-mono uppercase font-semibold px-1.5 py-0.5 ${
                                    item.status === 'delivered' ? 'text-emerald-700 border-emerald-300 bg-emerald-50' :
                                    item.status === 'received' ? 'text-teal-700 border-teal-300 bg-teal-50' :
                                    item.status === 'failed' ? 'text-rose-700 border-rose-300 bg-rose-50' :
                                    item.delivery_provider === 'crm_recorded' ? 'text-amber-700 border-amber-300 bg-amber-50' :
                                    'text-slate-600 border-slate-300'
                                  }`}
                                  title={item.delivery_provider === 'crm_recorded' ? 'Logged in CRM timeline. Configure valid Google App Password in Mailbox Settings for live external inbox delivery.' : ''}
                                >
                                  {item.delivery_provider === 'crm_recorded' ? 'CRM Timeline' : item.status === 'delivered' ? '✓ Delivered' : item.status}
                                </Badge>
                              )}
                              <span>{timeAgo(item.created_at || item.sent_at)}</span>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => {
                                  const subj = item.subject?.toLowerCase().startsWith('re:') ? item.subject : `Re: ${item.subject || ''}`;
                                  handleOpenEmailModal(subj, '', item.thread_id, selectedLead);
                                }}
                                className="h-6 text-[11px] text-indigo-700 hover:bg-indigo-50 font-semibold gap-1 px-2 rounded-md"
                                title="Reply to this message"
                              >
                                <MessageSquareReply className="w-3 h-3" /> Reply
                              </Button>
                            </div>
                          </div>

                          {/* Row 2: Subject */}
                          <h5 className="font-bold text-slate-900 text-xs sm:text-sm mb-1.5">
                            {item.subject}
                          </h5>

                          {/* Row 3: Metadata (From, To, Cc) */}
                          <div className="flex items-center gap-2 text-[11px] text-slate-500 mb-2.5 bg-slate-50/90 px-2.5 py-1.5 rounded-md border border-slate-100 flex-wrap">
                            <span>From: <strong className="text-slate-800">{item.sales_person_name ? `${item.sales_person_name} <${item.from_email}>` : item.from_email}</strong></span>
                            <span className="text-slate-300">•</span>
                            <span>To: <strong className="text-slate-800">{item.to_email}</strong></span>
                            {item.cc && (
                              <>
                                <span className="text-slate-300">•</span>
                                <span>Cc: <strong className="text-slate-800">{item.cc}</strong></span>
                              </>
                            )}
                          </div>

                          {/* Row 4: Message Body */}
                          <div
                            className="text-xs text-slate-700 leading-relaxed space-y-1"
                            dangerouslySetInnerHTML={{
                              __html: item.body_html || `<p>${item.raw_text || ''}</p>`
                            }}
                          />

                          {/* Row 5: Gateway info & offline warning */}
                          {item.delivery_provider === 'crm_recorded' && (
                            <div className="mt-2.5 p-2 rounded-md bg-amber-50 border border-amber-200 text-amber-800 text-[11px] flex items-center justify-between gap-2">
                              <span>⚠️ <strong>Saved in CRM only (Not delivered to external Gmail):</strong> Google rejected your Mailbox App Password. Connect your 16-character App Password to deliver live to the client's Gmail inbox.</span>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setShowMailboxModal(true)}
                                className="h-6 text-[10px] border-amber-300 text-amber-900 bg-white hover:bg-amber-100 shrink-0 font-semibold"
                              >
                                Mailbox Settings
                              </Button>
                            </div>
                          )}

                          {item.delivery_info && item.delivery_provider !== 'crm_recorded' && (
                            <p className="text-[10px] text-slate-400 mt-2.5 pt-1.5 border-t border-slate-100 italic">
                              Gateway info: {item.delivery_info}
                            </p>
                          )}
                        </div>
                      ))}

                      {/* Inline Quick Reply Box */}
                      <div className="p-4 rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50/60 to-slate-50 mt-4 space-y-3 shadow-sm">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <MessageSquareReply className="w-4 h-4 text-indigo-600" />
                            <span className="font-bold text-xs text-slate-800">Quick Reply to {selectedLead.name}</span>
                            <span className="text-[11px] text-slate-400">({selectedLead.email})</span>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleOpenEmailModal('', '', null, selectedLead)}
                            className="h-6 text-[11px] text-indigo-700 hover:bg-indigo-100 font-semibold gap-1"
                          >
                            Use Admin Template instead →
                          </Button>
                        </div>

                        <Textarea
                          rows={3}
                          placeholder={`Type a direct reply to ${selectedLead.name}... It will be delivered from your sales mailbox and recorded in this thread.`}
                          value={quickReplyText}
                          onChange={(e) => setQuickReplyText(e.target.value)}
                          className="text-xs bg-white border-slate-300 focus:border-indigo-500 font-normal"
                        />

                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                            <span className="text-[11px] text-slate-500">
                              Delivers via: <strong className="text-slate-700">{currentUser?.email || 'your email'}</strong>
                            </span>
                            <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-slate-700 select-none">
                              <input
                                type="checkbox"
                                checked={quickReplyNotifyByEmail}
                                onChange={(e) => setQuickReplyNotifyByEmail(e.target.checked)}
                                className="w-3.5 h-3.5 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300"
                              />
                              <Bell className="w-3 h-3 text-indigo-600" />
                              <span>CC / Notify me by email</span>
                            </label>
                          </div>
                          <Button
                            size="sm"
                            onClick={handleQuickReplySubmit}
                            disabled={sendingQuickReply || !quickReplyText.trim()}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold gap-1.5 h-8 px-4 shadow-sm"
                          >
                            {sendingQuickReply ? (
                              <>
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                Sending Reply...
                              </>
                            ) : (
                              <>
                                <Send className="w-3.5 h-3.5" />
                                Send Reply
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB: COMPLETE 360° TIMELINE & CALL RECORDINGS */}
              {workspaceTab === 'timeline' && (
                <div className="space-y-4">
                  {/* Timeline Category Filters */}
                  <div className="flex flex-wrap gap-1.5 pb-1">
                    {[
                      { key: 'all', label: 'All Activities' },
                      { key: 'stage_change', label: 'Stage & Status' },
                      { key: 'call', label: 'Calls & Recordings' },
                      { key: 'whatsapp', label: 'WhatsApp' },
                      { key: 'email', label: 'Emails' },
                      { key: 'follow_up', label: 'Follow-ups' },
                      { key: 'meeting', label: 'Meetings' }
                    ].map(f => (
                      <button
                        key={f.key}
                        onClick={() => setTimelineFilter(f.key)}
                        className={`px-3 py-1 text-xs rounded-full font-semibold transition-all ${timelineFilter === f.key ? 'bg-emerald-700 text-white shadow-sm' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'}`}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>

                  {timelineLoading ? (
                    <div className="text-center py-12 text-xs text-slate-400 space-y-2">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto text-emerald-600" />
                      <p>Loading complete client activity history...</p>
                    </div>
                  ) : leadTimeline.filter(item => timelineFilter === 'all' || item.type === timelineFilter || (timelineFilter === 'stage_change' && (item.type === 'stage_change' || item.type === 'audit_log'))).length > 0 ? (
                    <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                      {leadTimeline
                        .filter(item => timelineFilter === 'all' || item.type === timelineFilter || (timelineFilter === 'stage_change' && (item.type === 'stage_change' || item.type === 'audit_log')))
                        .map((item, idx) => (
                          <div key={idx} className="relative group">
                            {/* Timeline Point Icon */}
                            <div className="absolute -left-6 top-1 w-5 h-5 rounded-full border-2 border-white bg-white shadow flex items-center justify-center">
                              {item.type === 'call' ? (
                                <div className={`w-3.5 h-3.5 rounded-full ${item.extra?.direction === 'incoming' ? 'bg-emerald-500' : 'bg-blue-500'}`} />
                              ) : item.type === 'whatsapp' ? (
                                <div className={`w-3.5 h-3.5 rounded-full ${item.extra?.status === 'failed' || item.action === 'whatsapp_failed' ? 'bg-rose-500' : (item.extra?.status === 'pending_confirmation' || item.extra?.status === 'pending' || item.action === 'whatsapp_pending' ? 'bg-amber-500' : 'bg-emerald-600')}`} />
                              ) : item.type === 'email' ? (
                                <div className="w-3.5 h-3.5 rounded-full bg-indigo-500" />
                              ) : item.type === 'payment' ? (
                                <div className="w-3.5 h-3.5 rounded-full bg-teal-500" />
                              ) : item.type === 'follow_up' ? (
                                <div className="w-3.5 h-3.5 rounded-full bg-amber-500" />
                              ) : item.type === 'stage_change' ? (
                                <div className="w-3.5 h-3.5 rounded-full bg-purple-500" />
                              ) : (
                                <div className="w-3.5 h-3.5 rounded-full bg-slate-400" />
                              )}
                            </div>

                            {/* Card Content */}
                            <div className="p-3.5 bg-white border border-slate-200 hover:border-slate-300 rounded-xl shadow-sm transition-all space-y-1.5">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  {item.type === 'call' && (
                                    <Badge className={`${item.extra?.direction === 'incoming' ? 'bg-emerald-100 text-emerald-800 border-emerald-200' : 'bg-blue-100 text-blue-800 border-blue-200'} text-[10px] font-bold`}>
                                      {item.extra?.direction === 'incoming' ? <PhoneIncoming className="w-3 h-3 mr-1 inline" /> : <PhoneOutgoing className="w-3 h-3 mr-1 inline" />}
                                      {item.extra?.direction === 'incoming' ? 'Incoming Call' : 'Outgoing Call'}
                                    </Badge>
                                  )}
                                  {item.type === 'whatsapp' && (
                                    item.extra?.status === 'failed' || item.action === 'whatsapp_failed' ? (
                                      <Badge className="bg-rose-100 text-rose-800 border-rose-200 text-[10px] font-bold">
                                        <AlertCircle className="w-3 h-3 mr-1 inline text-rose-600" /> WhatsApp (Failed)
                                      </Badge>
                                    ) : (item.extra?.status === 'pending_confirmation' || item.extra?.status === 'pending' || item.action === 'whatsapp_pending') ? (
                                      <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-[10px] font-bold">
                                        <Clock className="w-3 h-3 mr-1 inline text-amber-600" /> WhatsApp (Pending)
                                      </Badge>
                                    ) : (
                                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200 text-[10px] font-bold">
                                        <MessageCircle className="w-3 h-3 mr-1 inline" /> WhatsApp
                                      </Badge>
                                    )
                                  )}
                                  {item.type === 'email' && (
                                    <Badge className="bg-indigo-100 text-indigo-800 border-indigo-200 text-[10px] font-bold">
                                      <Mail className="w-3 h-3 mr-1 inline" /> Email
                                    </Badge>
                                  )}
                                  {item.type === 'payment' && (
                                    <Badge className="bg-teal-100 text-teal-800 border-teal-200 text-[10px] font-bold">
                                      <DollarSign className="w-3 h-3 mr-1 inline" /> Payment
                                    </Badge>
                                  )}
                                  {item.type === 'meeting' && (
                                    <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-[10px] font-bold">
                                      <Video className="w-3 h-3 mr-1 inline" /> Meeting
                                    </Badge>
                                  )}
                                  {item.type === 'stage_change' && (
                                    <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-[10px] font-bold">
                                      <ShieldCheck className="w-3 h-3 mr-1 inline" /> Stage Change
                                    </Badge>
                                  )}
                                  {item.type === 'follow_up' && (
                                    <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-[10px] font-bold">
                                      <Clock className="w-3 h-3 mr-1 inline" /> Follow-up
                                    </Badge>
                                  )}
                                  {item.type === 'lead_created' && (
                                    <Badge className="bg-slate-100 text-slate-800 border-slate-200 text-[10px] font-bold">
                                      <Sparkles className="w-3 h-3 mr-1 inline text-amber-500" /> Creation
                                    </Badge>
                                  )}

                                  <h5 className="font-bold text-xs text-slate-900">{item.title}</h5>
                                </div>

                                <div className="text-right text-[11px] text-slate-400">
                                  <span>{timeAgo(item.timestamp)}</span>
                                  <span className="text-[10px] text-slate-300 ml-1.5 hidden sm:inline">
                                    ({new Date(item.timestamp).toLocaleString()})
                                  </span>
                                </div>
                              </div>

                              <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>

                              {/* Interactive Call Recording Playback */}
                              {item.type === 'call' && item.extra?.recording_url && (
                                <CallAudioPlayer
                                  recordingUrl={item.extra.recording_url}
                                  durationSeconds={item.extra.duration_seconds}
                                  callerName={selectedLead.name}
                                />
                              )}

                              {/* WhatsApp Chat Message Bubble */}
                              {item.type === 'whatsapp' && (() => {
                                const isWaFailed = item.extra?.status === 'failed' || item.action === 'whatsapp_failed';
                                const isWaPending = item.extra?.status === 'pending_confirmation' || item.extra?.status === 'pending' || item.action === 'whatsapp_pending';

                                return (
                                  <div className={`mt-1 p-2.5 rounded-lg border text-xs font-sans space-y-1.5 ${
                                    isWaFailed
                                      ? 'bg-rose-50/70 border-rose-200 text-rose-950'
                                      : isWaPending
                                      ? 'bg-amber-50/70 border-amber-200 text-amber-950'
                                      : 'bg-emerald-50 border-emerald-100 text-emerald-950'
                                  }`}>
                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                      {item.extra?.template_name ? (
                                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                                          isWaFailed
                                            ? 'bg-rose-100 text-rose-900 border-rose-300'
                                            : isWaPending
                                            ? 'bg-amber-100 text-amber-900 border-amber-300'
                                            : 'bg-emerald-200/80 text-emerald-900 border-emerald-300'
                                        }`}>
                                          <FileText className="w-3 h-3" /> Template: {item.extra.template_name}
                                        </span>
                                      ) : (
                                        <span className={`text-[10px] font-semibold ${isWaFailed ? 'text-rose-700' : isWaPending ? 'text-amber-700' : 'text-emerald-700'}`}>
                                          Direct Message
                                        </span>
                                      )}

                                      {isWaFailed ? (
                                        <span className="inline-flex items-center gap-1 text-[10px] text-rose-700 font-semibold bg-rose-100/80 px-2 py-0.5 rounded border border-rose-300">
                                          <AlertCircle className="w-3 h-3 text-rose-600" />
                                          Failed (WhatsApp Web)
                                        </span>
                                      ) : isWaPending ? (
                                        <span className="inline-flex items-center gap-1 text-[10px] text-amber-700 font-semibold bg-amber-100/80 px-2 py-0.5 rounded border border-amber-300">
                                          <Clock className="w-3 h-3 text-amber-600" />
                                          Pending Confirmation
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 font-semibold bg-emerald-100/80 px-2 py-0.5 rounded border border-emerald-300">
                                          <CheckCheck className="w-3 h-3 text-emerald-600" />
                                          {item.extra?.channel === 'whatsapp_web' ? 'Sent via WhatsApp Web' : item.extra?.channel === 'meta_cloud_api' ? 'Meta Cloud API' : 'Sent'}
                                        </span>
                                      )}
                                    </div>
                                    <p className="whitespace-pre-wrap leading-relaxed text-slate-800">{item.description}</p>
                                    {isWaFailed && item.extra?.error_message && (
                                      <p className="text-[11px] text-rose-700 font-medium bg-rose-100/50 p-1.5 rounded border border-rose-200">
                                        Reason: {item.extra.error_message}
                                      </p>
                                    )}
                                    <div className={`pt-1.5 border-t flex items-center justify-between text-[10px] flex-wrap gap-2 ${
                                      isWaFailed ? 'border-rose-200 text-rose-800' : isWaPending ? 'border-amber-200 text-amber-800' : 'border-emerald-100 text-emerald-800'
                                    }`}>
                                      <span>
                                        Contact: <strong>{item.extra?.contact_name || selectedLead?.name}</strong> ({formatPhoneNumber(selectedLead?.whatsapp_number || selectedLead?.phone)})
                                        {item.user_name && ` · Rep: ${item.user_name}`}
                                      </span>
                                      <button
                                        type="button"
                                        onClick={() => {
                                          const webUrl = getDirectWhatsAppWebLink(selectedLead?.whatsapp_number || selectedLead?.phone, item.description);
                                          if (webUrl) window.open(webUrl, '_blank');
                                        }}
                                        className={`inline-flex items-center gap-1 font-bold hover:underline ${
                                          isWaFailed ? 'text-rose-700 hover:text-rose-950' : 'text-emerald-700 hover:text-emerald-950'
                                        }`}
                                      >
                                        <ArrowUpRight className="w-3 h-3" /> Re-open in WhatsApp Web
                                      </button>
                                    </div>
                                  </div>
                                );
                              })()}

                              {/* Meeting Interactive Card */}
                              {item.type === 'meeting' && (() => {
                                const isZoomMeeting = String(item.extra?.meeting_type || '').toLowerCase() === 'zoom';
                                const isCalendlyMeeting = String(item.extra?.meeting_type || '').toLowerCase() === 'calendly';
                                const p = isCalendlyMeeting ? 'Calendly' : (isZoomMeeting ? 'Zoom' : 'Google Meet');

                                return (
                                  <div className="mt-2 p-3.5 bg-gradient-to-br from-slate-50 via-indigo-50/30 to-purple-50/20 rounded-xl border border-indigo-100 text-xs space-y-2.5">
                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                      <div className="flex items-center gap-2">
                                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md font-semibold text-[11px] ${
                                          isCalendlyMeeting
                                            ? 'bg-sky-100 text-sky-800 border border-sky-200'
                                            : isZoomMeeting
                                              ? 'bg-blue-100 text-blue-800 border border-blue-200'
                                              : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                        }`}>
                                          {isCalendlyMeeting ? <Calendar className="w-3.5 h-3.5 text-sky-600" /> : <Video className="w-3.5 h-3.5" />} {isCalendlyMeeting ? 'Calendly' : (isZoomMeeting ? 'Zoom Meeting' : 'Google Meet')}
                                        </span>
                                        {item.extra?.duration_minutes && (
                                          <span className="text-[11px] text-slate-500 font-medium">
                                            ⏱️ {item.extra.duration_minutes} mins
                                          </span>
                                        )}
                                      </div>
                                      <Badge className={`text-[10px] font-bold ${
                                        item.extra?.status === 'completed' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' :
                                        item.extra?.status === 'cancelled' ? 'bg-rose-100 text-rose-800 border-rose-300' :
                                        'bg-purple-100 text-purple-800 border-purple-300'
                                      }`}>
                                        {(item.extra?.status || 'Scheduled').toUpperCase()}
                                      </Badge>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-700 bg-white p-2.5 rounded-lg border border-slate-200">
                                      <div>
                                        <span className="text-[10px] text-slate-400 block font-medium">Date & Time</span>
                                        <span className="font-semibold text-slate-900">
                                          📅 {item.extra?.meeting_date || 'N/A'} at {item.extra?.meeting_time || 'N/A'}
                                        </span>
                                      </div>
                                      {item.extra?.meeting_password ? (
                                        <div>
                                          <span className="text-[10px] text-slate-400 block font-medium">Meeting Passcode</span>
                                          <span className="font-mono font-semibold text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded">
                                            🔑 {item.extra.meeting_password}
                                          </span>
                                        </div>
                                      ) : (
                                        <div>
                                          <span className="text-[10px] text-slate-400 block font-medium">Access Type</span>
                                          <span className="text-emerald-700 font-semibold">{isCalendlyMeeting ? 'Calendly Booking Link' : 'Direct Browser Join'}</span>
                                        </div>
                                      )}
                                    </div>

                                    {item.extra?.notes && (
                                      <p className="text-[11px] text-slate-600 bg-white/80 p-2 rounded border border-slate-200">
                                        <strong>Agenda / Notes:</strong> {item.extra.notes}
                                      </p>
                                    )}

                                    {item.extra?.meeting_link && (
                                      <div className="pt-1 flex items-center justify-between gap-2 flex-wrap">
                                        <div className="flex items-center gap-1.5 flex-1 min-w-[200px]">
                                          <code className="text-[10px] bg-white border border-slate-200 px-2 py-1 rounded text-slate-700 font-mono truncate max-w-[260px]">
                                            {item.extra.meeting_link}
                                          </code>
                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => {
                                              navigator.clipboard.writeText(item.extra.meeting_link);
                                              toast.success('Meeting link copied to clipboard!');
                                            }}
                                            className="h-7 px-2 text-[11px] text-slate-600 hover:text-slate-900 gap-1"
                                          >
                                            <Copy className="w-3 h-3" /> Copy
                                          </Button>
                                        </div>

                                        <div className="flex items-center gap-1.5">
                                          <Button
                                            type="button"
                                            size="sm"
                                            onClick={() => window.open(item.extra.meeting_link, '_blank')}
                                            className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1 shadow-sm"
                                          >
                                            {isCalendlyMeeting ? <Calendar className="w-3.5 h-3.5" /> : <Video className="w-3.5 h-3.5" />} {isCalendlyMeeting ? 'Open Calendly' : 'Join Meeting'}
                                          </Button>

                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="outline"
                                            onClick={() => handleOpenRescheduleModal({
                                              id: item.extra?.meeting_id || item.id,
                                              title: item.title,
                                              meeting_date: item.extra?.meeting_date,
                                              meeting_time: item.extra?.meeting_time,
                                              duration_minutes: item.extra?.duration_minutes || 30,
                                              contact_name: selectedLead?.name,
                                              contact_email: selectedLead?.email,
                                              contact_phone: selectedLead?.phone,
                                              sales_person_name: item.user_name || currentUser?.name,
                                              meeting_link: item.extra?.meeting_link
                                            })}
                                            className="h-7 text-xs bg-white hover:bg-amber-50 text-amber-800 border-amber-300 gap-1 font-semibold"
                                            title="Reschedule meeting date & time"
                                          >
                                            <RefreshCw className="w-3.5 h-3.5 text-amber-600" /> Reschedule
                                          </Button>

                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="outline"
                                            onClick={() => handleOpenRecapModal({
                                              id: item.extra?.meeting_id || item.id,
                                              title: item.title,
                                              contact_name: selectedLead?.name,
                                              sales_person_name: item.user_name || currentUser?.name,
                                              calendly_event_id: item.extra?.calendly_event_id,
                                              recap: item.extra?.recap
                                            })}
                                            className="h-7 text-xs bg-white hover:bg-indigo-50 text-indigo-700 border-indigo-200 gap-1 font-medium"
                                            title="View or edit meeting recording, transcript & AI summary"
                                          >
                                            <FileText className="w-3.5 h-3.5 text-indigo-600" /> Notes & Transcript
                                          </Button>

                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="outline"
                                            onClick={() => handleOpenEditMeetingLink(item.extra?.meeting_id || item.id, item.extra?.meeting_link, item.title, item.extra)}
                                            className="h-7 text-xs bg-white hover:bg-slate-50 text-slate-700 border-slate-300 gap-1 font-medium"
                                            title="Update meeting link"
                                          >
                                            <Pencil className="w-3 h-3 text-slate-500" /> Edit Link
                                          </Button>

                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="outline"
                                            onClick={() => {
                                              const pass = item.extra.meeting_password ? `\n🔑 Passcode: ${item.extra.meeting_password}` : '';
                                              const invite = isCalendlyMeeting
                                                ? `Dear ${selectedLead.name},\n\nYour consultation booking link with ${currentUser?.name || 'LEAMSS Consultant'} is ready!\n\n📅 Date: ${item.extra.meeting_date}\n⏰ Time: ${item.extra.meeting_time}\n💻 Platform: Calendly\n🔗 Book / Join Link: ${item.extra.meeting_link}\n\nPlease select your preferred consultation slot or join at the scheduled time.\n\nBest regards,\n${currentUser?.name || 'LEAMSS'}`
                                                : `Dear ${selectedLead.name},\n\nYour consultation meeting with ${currentUser?.name || 'LEAMSS Consultant'} is scheduled!\n\n📅 Date: ${item.extra.meeting_date}\n⏰ Time: ${item.extra.meeting_time}\n💻 Platform: ${p}\n🔗 Join Link: ${item.extra.meeting_link}${pass}\n\nPlease join 2 minutes prior. Let me know if you need to reschedule.\n\nBest regards,\n${currentUser?.name || 'LEAMSS'}`;
                                              const wa = getDirectWhatsAppWebLink(selectedLead.whatsapp_number || selectedLead.phone, invite);
                                              if (wa) window.open(wa, '_blank');
                                              else toast.error('No phone number for client');
                                            }}
                                            className="h-7 text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border-emerald-200 gap-1 font-medium"
                                            title="Send invitation via WhatsApp"
                                          >
                                            <MessageCircle className="w-3.5 h-3.5 text-emerald-600" /> WhatsApp
                                          </Button>

                                          <Button
                                            type="button"
                                            size="sm"
                                            variant="outline"
                                            onClick={() => {
                                              const pass = item.extra.meeting_password ? `\nPasscode: ${item.extra.meeting_password}` : '';
                                              const invite = isCalendlyMeeting
                                                ? `Dear ${selectedLead.name},\n\nYour consultation booking link with ${currentUser?.name || 'LEAMSS Consultant'} is ready!\n\nDate: ${item.extra.meeting_date} at ${item.extra.meeting_time} (${item.extra.duration_minutes || 30} mins)\nPlatform: Calendly\nBooking Link: ${item.extra.meeting_link}\n\nPlease select your preferred slot or join at the scheduled time.\n\nBest regards,\n${currentUser?.name || 'LEAMSS'}`
                                                : `Dear ${selectedLead.name},\n\nYour consultation meeting with ${currentUser?.name || 'LEAMSS Consultant'} is scheduled!\n\nDate: ${item.extra.meeting_date} at ${item.extra.meeting_time} (${item.extra.duration_minutes || 30} mins)\nPlatform: ${p}\nJoin Link: ${item.extra.meeting_link}${pass}\n\nPlease join 2 minutes prior.\n\nBest regards,\n${currentUser?.name || 'LEAMSS'}`;
                                              handleOpenEmailModal(`Consultation Meeting: ${item.extra.meeting_date} at ${item.extra.meeting_time}`, invite, null, selectedLead);
                                            }}
                                            className="h-7 text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border-indigo-200 gap-1 font-medium"
                                            title="Send invitation via Email"
                                          >
                                            <Mail className="w-3.5 h-3.5 text-indigo-600" /> Email
                                          </Button>
                                        </div>
                                      </div>
                                    )}

                                    {/* Reschedule Reason Banner */}
                                    {item.extra?.reschedule_reason && (
                                      <div className="p-2.5 bg-amber-50 rounded-lg border border-amber-200 text-amber-900 text-xs flex items-start gap-2">
                                        <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                                        <div>
                                          <span className="font-bold text-[10px] uppercase tracking-wide text-amber-800 block">Reschedule Reason:</span>
                                          <p className="text-[11px] text-amber-950 font-medium">{item.extra.reschedule_reason}</p>
                                        </div>
                                      </div>
                                    )}

                                    {/* Reschedule History (Audit Trail) */}
                                    {Array.isArray(item.extra?.reschedule_history) && item.extra.reschedule_history.length > 0 && (
                                      <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1.5">
                                        <div
                                          className="flex items-center justify-between cursor-pointer select-none"
                                          onClick={() => setExpandedHistoryId(expandedHistoryId === (item.extra?.meeting_id || item.id) ? null : (item.extra?.meeting_id || item.id))}
                                        >
                                          <span className="font-semibold text-slate-700 flex items-center gap-1.5 text-[11px]">
                                            <RefreshCw className="w-3 h-3 text-amber-600" /> Reschedule Audit History ({item.extra.reschedule_history.length})
                                          </span>
                                          <span className="text-[10px] text-indigo-600 font-medium hover:underline">
                                            {expandedHistoryId === (item.extra?.meeting_id || item.id) ? 'Hide History ▲' : 'View Audit Trail ▼'}
                                          </span>
                                        </div>
                                        {expandedHistoryId === (item.extra?.meeting_id || item.id) && (
                                          <div className="space-y-1.5 pt-1 border-t border-slate-200">
                                            {item.extra.reschedule_history.map((h, hIdx) => (
                                              <div key={hIdx} className="bg-white p-2 rounded border border-slate-200 text-[11px] space-y-0.5">
                                                <div className="flex items-center justify-between text-slate-400 text-[10px]">
                                                  <span>Rescheduled by: <strong>{h.rescheduled_by_name || 'Staff'}</strong></span>
                                                  <span>{h.rescheduled_at ? new Date(h.rescheduled_at).toLocaleString() : ''}</span>
                                                </div>
                                                <p className="text-slate-800">
                                                  Shifted from <span className="line-through text-slate-400">{h.old_date} {h.old_time}</span> to <strong className="text-amber-800">{h.new_date} at {h.new_time}</strong>
                                                </p>
                                                <p className="text-amber-900 font-medium">
                                                  <strong>Reason:</strong> {h.reason}
                                                </p>
                                                {h.notes && <p className="text-slate-500 text-[10px]">Note: {h.notes}</p>}
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    )}

                                    {/* Meeting Recording, Transcript & AI Summary */}
                                    {item.extra?.recap && (
                                      <div className="p-3 bg-gradient-to-r from-indigo-50/70 via-sky-50/50 to-white rounded-lg border border-indigo-200/80 text-xs space-y-2">
                                        <div className="flex items-center justify-between">
                                          <span className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
                                            <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Meeting Notes, Transcript & AI Summary
                                          </span>
                                          <div className="flex items-center gap-2">
                                            {item.extra?.calendly_event_id && (
                                              <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                disabled={syncingRecapId === (item.extra?.meeting_id || item.id)}
                                                onClick={() => handleSyncRecap(item.extra?.meeting_id || item.id)}
                                                className="h-6 px-1.5 text-[10px] text-indigo-700 hover:bg-indigo-100 gap-1 font-medium"
                                              >
                                                <RefreshCw className={`w-3 h-3 ${syncingRecapId === (item.extra?.meeting_id || item.id) ? 'animate-spin' : ''}`} />
                                                Sync Calendly
                                              </Button>
                                            )}
                                            <button
                                              type="button"
                                              onClick={() => setExpandedRecapId(expandedRecapId === (item.extra?.meeting_id || item.id) ? null : (item.extra?.meeting_id || item.id))}
                                              className="text-[11px] text-indigo-600 font-medium hover:underline"
                                            >
                                              {expandedRecapId === (item.extra?.meeting_id || item.id) ? 'Collapse ▲' : 'Expand Notes ▼'}
                                            </button>
                                          </div>
                                        </div>

                                        {expandedRecapId === (item.extra?.meeting_id || item.id) && (
                                          <div className="space-y-2 pt-2 border-t border-indigo-100">
                                            {item.extra.recap.recording_url && (
                                              <div className="flex items-center gap-2 bg-white p-2 rounded border border-indigo-100">
                                                <Video className="w-4 h-4 text-rose-500 shrink-0" />
                                                <span className="font-medium text-slate-700 text-xs">Meeting Recording:</span>
                                                <a
                                                  href={item.extra.recap.recording_url}
                                                  target="_blank"
                                                  rel="noreferrer"
                                                  className="text-xs text-indigo-600 underline font-semibold truncate hover:text-indigo-800"
                                                >
                                                  {item.extra.recap.recording_url}
                                                </a>
                                              </div>
                                            )}
                                            {item.extra.recap.participants && (
                                              <div className="text-[11px] text-slate-600">
                                                <strong className="text-slate-800">Participants:</strong> {item.extra.recap.participants}
                                              </div>
                                            )}
                                            {item.extra.recap.summary && (
                                              <div className="bg-white/90 p-2.5 rounded border border-indigo-100">
                                                <span className="text-[10px] font-bold uppercase tracking-wide text-indigo-700 block mb-1">AI Executive Summary</span>
                                                <p className="text-slate-700 whitespace-pre-line text-xs">{item.extra.recap.summary}</p>
                                              </div>
                                            )}
                                            {item.extra.recap.action_items && (
                                              <div className="bg-amber-50/70 p-2.5 rounded border border-amber-200">
                                                <span className="text-[10px] font-bold uppercase tracking-wide text-amber-800 block mb-1">Action Items & Next Steps</span>
                                                <p className="text-slate-700 whitespace-pre-line text-xs">{item.extra.recap.action_items}</p>
                                              </div>
                                            )}
                                            {item.extra.recap.transcripts && (
                                              <div className="bg-white/90 p-2.5 rounded border border-slate-200">
                                                <span className="text-[10px] font-bold uppercase tracking-wide text-slate-600 block mb-1">Discussion Transcript / Notes</span>
                                                <p className="text-slate-600 whitespace-pre-line font-mono text-[11px] max-h-48 overflow-y-auto bg-slate-50 p-2 rounded border border-slate-100">
                                                  {item.extra.recap.transcripts}
                                                </p>
                                              </div>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })()}

                              {/* Footer Meta */}
                              <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400">
                                <span>Action by: <strong className="text-slate-600">{item.user_name || 'Sales Person'}</strong></span>
                                {item.extra?.outcome && (
                                  <span className="text-slate-500 font-medium">Outcome: <strong className="text-emerald-700">{item.extra.outcome.replace('_', ' ').toUpperCase()}</strong></span>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 bg-white rounded-xl border border-slate-200 p-6 space-y-3">
                      {timelineFilter === 'meeting' ? (
                        <>
                          <div className="w-12 h-12 rounded-full bg-purple-50 text-purple-600 flex items-center justify-center mx-auto">
                            <Video className="w-6 h-6" />
                          </div>
                          <div>
                            <p className="font-bold text-slate-800 text-sm">No meetings scheduled for this client yet</p>
                            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                              Create a Google Meet or Zoom consultation link to meet with {selectedLead.name}.
                            </p>
                          </div>
                          <div className="flex items-center justify-center pt-2">
                            <Button
                              size="sm"
                              onClick={() => setShowMeetingModal(true)}
                              className="h-8 text-xs bg-purple-600 hover:bg-purple-700 text-white font-semibold gap-1.5 shadow-sm"
                            >
                              <Video className="w-3.5 h-3.5" /> Schedule Consultation
                            </Button>
                          </div>
                        </>
                      ) : timelineFilter === 'whatsapp' ? (
                        <>
                          <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto">
                            <MessageCircle className="w-6 h-6" />
                          </div>
                          <div>
                            <p className="font-bold text-slate-800 text-sm">No WhatsApp records logged for this client yet</p>
                            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                              Start a WhatsApp conversation with {selectedLead.name} using your consultant identity ({currentUser?.name || 'Sales Consultant'}).
                            </p>
                          </div>
                          <div className="flex items-center justify-center gap-2 pt-2 flex-wrap">
                            <Button
                              size="sm"
                              onClick={() => {
                                setWorkspaceTab('whatsapp');
                                loadLeadWhatsApp(selectedLead.id);
                              }}
                              className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1.5 shadow-sm"
                            >
                              <MessageCircle className="w-3.5 h-3.5" /> Open WhatsApp & Chat Tab
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleWhatsAppCall(selectedLead.whatsapp_number || selectedLead.phone, selectedLead)}
                              className="h-8 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 font-semibold gap-1.5"
                            >
                              <PhoneCall className="w-3.5 h-3.5" /> Start WhatsApp Call
                            </Button>
                          </div>
                        </>
                      ) : (
                        <>
                          <Clock className="w-8 h-8 text-slate-300 mx-auto" />
                          <p className="font-bold text-slate-800 text-sm">No activity records found</p>
                          <p className="text-xs text-slate-400">Interactions and calls made to this client will be tracked here in real time.</p>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}



            </div>

          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* QUICK CALL SELECTION MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Dialog open={showQuickCallSelectModal} onOpenChange={setShowQuickCallSelectModal}>
        <DialogContent className="max-w-lg bg-white p-6 rounded-2xl shadow-xl">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
              <PhoneCall className="w-5 h-5 text-emerald-600" /> Start Call with Client
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Select a client to initiate an instant call with live voice recording and automatic CRM logging.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 mt-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <Input
                placeholder="Search by client name, phone number, email, or country..."
                value={callSearch}
                onChange={(e) => setCallSearch(e.target.value)}
                className="pl-9 h-9 text-xs"
              />
            </div>

            <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 rounded-lg border border-slate-200">
              {leads
                .filter(l => {
                  if (!callSearch) return true;
                  const q = callSearch.toLowerCase();
                  return (
                    (l.name || '').toLowerCase().includes(q) ||
                    (l.phone || '').includes(q) ||
                    (l.email || '').toLowerCase().includes(q) ||
                    (l.target_country || '').toLowerCase().includes(q)
                  );
                })
                .slice(0, 30)
                .map(l => (
                  <div key={l.id} className="p-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-slate-900">{l.name}</span>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 capitalize">
                          {l.stage || 'New'}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-slate-500 font-mono">{formatPhoneNumber(l.phone)} • {l.email || 'No email'}</p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => {
                        setShowQuickCallSelectModal(false);
                        handleStartCall(l);
                      }}
                      className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1 shadow-sm"
                    >
                      <PhoneCall className="w-3.5 h-3.5" /> Call Now
                    </Button>
                  </div>
                ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* PC LIVE CALL RECORDING & CONSULTATION DIALOG */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showCallModal && (callLead || selectedLead) && (() => {
        const rawCallLead = callLead || selectedLead;
        const matchedLead = leads.find(l => String(l.id || l._id) === String(rawCallLead.id || rawCallLead._id));
        const activeCallLead = {
          ...rawCallLead,
          ...(matchedLead || {}),
          ...(selectedLead && String(selectedLead.id || selectedLead._id) === String(rawCallLead.id || rawCallLead._id) ? selectedLead : {})
        };
        const cleanDigits = String(activeCallLead.phone || '').replace(/[^0-9+]/g, '');
        const qrPhone = cleanDigits.startsWith('+') ? cleanDigits : `+91${cleanDigits}`;

        const hasResume = Boolean(
          activeCallLead.resume_file_id ||
          activeCallLead.resume_url ||
          activeCallLead.resume_filename ||
          activeCallLead.has_resume
        );
        const hasReport = Boolean(
          activeCallLead.has_pre_assessment_report ||
          activeCallLead.assessment_report_file_id ||
          activeCallLead.assessment_report_id ||
          activeCallLead.pre_assessment_report_url ||
          activeCallLead.latest_report_snapshot_id ||
          activeCallLead.bulk_row_id
        );
        const resumeName = activeCallLead.resume_filename || activeCallLead.resume_name || `${activeCallLead.name || 'Candidate'}_Resume.pdf`;
        const reportName = activeCallLead.assessment_report_filename || `${activeCallLead.name || 'Client'}_Pre_Assessment_Report.pdf`;
        const clientEmail = activeCallLead.email || activeCallLead.client_email || activeCallLead.lead_email || '';

        return (
          <Dialog open={showCallModal} onOpenChange={(open) => { if (!open) handleCloseCallModal(); else setShowCallModal(true); }}>
            <DialogContent className="max-w-xl max-h-[92vh] overflow-y-auto p-0 bg-slate-950 text-white border-slate-800 shadow-2xl z-[9999]">
              <DialogHeader className="sr-only">
                <DialogTitle>Call Console - {activeCallLead.name}</DialogTitle>
                <DialogDescription>In-app calling and audio recording session with {activeCallLead.name}</DialogDescription>
              </DialogHeader>
              
              {/* Call Header */}
              <div className="p-6 text-center space-y-3 bg-gradient-to-b from-slate-900 to-slate-950 border-b border-slate-800">
                <div className="relative w-16 h-16 mx-auto">
                  <div className={`w-16 h-16 rounded-full bg-slate-800 text-emerald-400 font-bold text-2xl flex items-center justify-center border-2 shadow-lg transition-all ${isRecording ? 'border-red-500 shadow-red-500/20 animate-pulse' : 'border-emerald-500'}`}>
                    {activeCallLead.name ? activeCallLead.name[0].toUpperCase() : 'C'}
                  </div>
                  {isRecording && (
                    <span className="absolute -top-1 -right-1 flex h-4 w-4">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-4 w-4 bg-red-600 border-2 border-slate-950"></span>
                    </span>
                  )}
                </div>

                <div>
                  <h4 className="text-lg font-bold text-white">{activeCallLead.name}</h4>
                  <div className="flex items-center justify-center gap-2 mt-1">
                    <p className="text-sm font-mono text-emerald-400 font-bold">{formatPhoneNumber(activeCallLead.phone)}</p>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        if (activeCallLead.phone) {
                          navigator.clipboard.writeText(String(activeCallLead.phone));
                          toast.success('Phone number copied to clipboard!');
                        }
                      }}
                      className="h-6 px-2 text-[10px] text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700"
                      title="Copy Phone Number"
                    >
                      Copy
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowCallQR(!showCallQR)}
                      className={`h-6 px-2 text-[10px] ${showCallQR ? 'text-emerald-400 bg-emerald-950/60 border border-emerald-800' : 'text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700'}`}
                      title="Scan QR code with your Android phone to dial immediately"
                    >
                      <QrCode className="w-3 h-3 mr-1" />
                      {showCallQR ? 'Hide QR' : 'Scan on Android'}
                    </Button>
                  </div>

                  {/* Client Email / Mail ID */}
                  {clientEmail && (
                    <div className="flex items-center justify-center gap-2 mt-1.5">
                      <p className="text-xs font-mono text-cyan-300 font-medium flex items-center gap-1.5">
                        <Mail className="w-3.5 h-3.5 text-cyan-400" />
                        <span>{clientEmail}</span>
                      </p>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          navigator.clipboard.writeText(String(clientEmail));
                          toast.success('Email address copied to clipboard!');
                        }}
                        className="h-5 px-1.5 text-[9px] text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700"
                        title="Copy Email Address"
                      >
                        Copy
                      </Button>
                    </div>
                  )}

                  {/* Android Scan-to-Call QR Code */}
                  {showCallQR && activeCallLead.phone && (
                    <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-3 text-center space-y-2 mt-2.5 animate-in fade-in zoom-in-95 duration-200">
                      <div className="inline-block p-2 bg-white rounded-lg shadow-lg">
                        <img
                          src={`https://api.qrserver.com/v1/create-qr-code/?size=130x130&margin=4&data=tel:${encodeURIComponent(qrPhone)}`}
                          alt="Scan to call QR code"
                          className="w-28 h-28 mx-auto"
                        />
                      </div>
                      <p className="text-[11px] text-emerald-400 font-medium leading-tight">
                        📷 Point your Android phone camera at this QR code to dial on your SIM instantly!
                      </p>
                    </div>
                  )}
                </div>

                {/* Live PC Call Recording & Duration Status */}
                <div className={`p-3 rounded-xl border transition-all ${isRecording ? 'bg-red-950/40 border-red-800/60 text-red-200' : 'bg-slate-900 border-slate-800 text-slate-300'}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {isRecording ? (
                        <span className="flex items-center gap-1.5 text-xs font-bold text-red-400">
                          <Radio className="w-4 h-4 text-red-500 animate-pulse" />
                          LIVE PC RECORDING ACTIVE
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-400">
                          <MicOff className="w-3.5 h-3.5 text-slate-500" />
                          Microphone Ready
                        </span>
                      )}
                    </div>
                    
                    {/* Real-time Call Duration Timer */}
                    <div className="font-mono font-bold text-sm text-emerald-400 bg-slate-950/80 px-2.5 py-0.5 rounded-md border border-slate-800">
                      {Math.floor(recordingDuration / 60)}:{(recordingDuration % 60) < 10 ? '0' : ''}{recordingDuration % 60}
                    </div>
                  </div>

                  {/* Animated Waveform Visualizer */}
                  {isRecording && (
                    <div className="flex items-center justify-center gap-1 mt-2.5 h-4">
                      <span className="w-1 bg-red-500 rounded-full animate-[bounce_0.8s_infinite_100ms] h-2"></span>
                      <span className="w-1 bg-red-400 rounded-full animate-[bounce_0.8s_infinite_200ms] h-4"></span>
                      <span className="w-1 bg-red-500 rounded-full animate-[bounce_0.8s_infinite_300ms] h-3"></span>
                      <span className="w-1 bg-red-400 rounded-full animate-[bounce_0.8s_infinite_150ms] h-4"></span>
                      <span className="w-1 bg-red-500 rounded-full animate-[bounce_0.8s_infinite_250ms] h-2"></span>
                    </div>
                  )}

                  <div className="text-[11px] text-slate-400 mt-2 text-left leading-tight">
                    {isRecording ? (
                      <span>🎙️ Conversation from your PC headset/mic is being automatically recorded and will sync to this client&apos;s history timeline upon ending the call.</span>
                    ) : (
                      <span>Click &quot;Start Mic Recording&quot; below if browser permission was prompted, or continue talking via mobile SIM/FaceTime.</span>
                    )}
                  </div>
                </div>

                {/* Quick Controls & Dialing Options */}
                <div className="space-y-2 pt-1">
                  <div className="grid grid-cols-2 gap-2">
                    {isRecording ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={toggleMute}
                        className={`h-9 text-xs font-semibold border-slate-700 ${isMuted ? 'bg-amber-950/60 text-amber-300 border-amber-800' : 'bg-slate-800 text-slate-200 hover:bg-slate-700'}`}
                      >
                        {isMuted ? <MicOff className="w-3.5 h-3.5 mr-1.5 text-amber-400" /> : <Mic className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />}
                        {isMuted ? 'Unmute Mic' : 'Mute Mic'}
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={startAudioRecording}
                        className="h-9 text-xs font-semibold bg-slate-800 text-emerald-300 border-slate-700 hover:bg-slate-700"
                      >
                        <Mic className="w-3.5 h-3.5 mr-1.5" /> Start Mic Recording
                      </Button>
                    )}

                    <Button
                      type="button"
                      onClick={() => handleWhatsAppCall(activeCallLead.phone)}
                      className="h-9 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg flex items-center justify-center gap-1.5 shadow"
                      title="Open WhatsApp chat or call"
                    >
                      <MessageCircle className="w-3.5 h-3.5" /> WhatsApp Call
                    </Button>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleManualDial(activeCallLead.phone)}
                      className="flex-1 h-8 text-[11px] bg-slate-900 hover:bg-slate-800 text-slate-300 border-slate-700 flex items-center justify-center gap-1.5"
                      title="Dial via macOS FaceTime / Phone app (requires linked iPhone on same iCloud)"
                    >
                      <PhoneCall className="w-3 h-3 text-blue-400" /> Dial via Mac (FaceTime)
                    </Button>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800/80 rounded-lg p-2 text-[11px] text-slate-400 text-left">
                    <span className="text-emerald-400 font-semibold">📱 Callyzer / Mobile SIM:</span> Dial the number from your mobile SIM. The PC microphone will record your conversation and save it to the client&apos;s history.
                  </div>
                </div>
              </div>

              {/* Consultation Notes & Outcome */}
              <div className="p-5 space-y-3.5 bg-slate-900 text-xs">
                {/* ──────────────────────────────────────────────────────────── */}
                {/* 📄 ATTACHED CLIENT DOCUMENTS (Resume & Pre-Assessment Report) */}
                {/* ──────────────────────────────────────────────────────────── */}
                {(hasResume || hasReport) && (
                  <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-3 space-y-2.5 shadow-md">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
                        <Paperclip className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Attached Client Documents</span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium">
                        {activeCallLead.name || 'Client'}{clientEmail ? ` • ${clientEmail}` : ''}
                      </span>
                    </div>

                    <div className="space-y-2">
                      {hasResume && (
                        <div className="p-2.5 bg-emerald-950/30 border border-emerald-800/60 rounded-lg flex items-center justify-between gap-2 transition-all">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-7 h-7 rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center text-xs shrink-0">
                              📄
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-semibold text-emerald-300">Resume Attached</span>
                                <Badge className="bg-emerald-900/80 text-emerald-300 border-emerald-700/80 text-[9px] py-0 px-1.5 h-4">
                                  CV
                                </Badge>
                              </div>
                              <p className="text-[11px] text-slate-300 truncate max-w-[220px] sm:max-w-xs" title={resumeName}>
                                {resumeName}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Button
                              size="sm"
                              type="button"
                              onClick={() => handleOpenResumePreview(activeCallLead)}
                              className="h-7 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 gap-1 shadow-sm"
                              title="Preview candidate resume in CRM"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>View Resume</span>
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onClick={() => handleDownloadResume(activeCallLead)}
                              className="h-7 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 px-2 gap-1 shadow-sm"
                              title="Download candidate resume"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                      )}

                      {hasReport && (
                        <div className="p-2.5 bg-purple-950/30 border border-purple-800/60 rounded-lg flex items-center justify-between gap-2 transition-all">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-7 h-7 rounded-md bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center justify-center text-xs shrink-0">
                              📊
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-semibold text-purple-300">Pre-Assessment Report</span>
                                <Badge className="bg-purple-900/80 text-purple-300 border-purple-700/80 text-[9px] py-0 px-1.5 h-4">
                                  Assessment
                                </Badge>
                              </div>
                              <p className="text-[11px] text-slate-300 truncate max-w-[220px] sm:max-w-xs" title={reportName}>
                                {reportName}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Button
                              size="sm"
                              type="button"
                              onClick={() => handleOpenReportPreview(activeCallLead)}
                              className="h-7 text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white px-2.5 gap-1 shadow-sm"
                              title="Preview Pre-Assessment Report in CRM"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              <span>View Report</span>
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              type="button"
                              onClick={() => handleDownloadReport(activeCallLead)}
                              className="h-7 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700 px-2 gap-1 shadow-sm"
                              title="Download Pre-Assessment Report"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Call Outcome / Status</label>
                  <Select value={callOutcome} onValueChange={setCallOutcome}>
                    <SelectTrigger className="bg-slate-800 border-slate-700 text-white h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-slate-900 text-white border-slate-700">
                      <SelectItem value="interested">Interested in Consultation</SelectItem>
                      <SelectItem value="follow_up_required">Follow-up Required</SelectItem>
                      <SelectItem value="payment_discussion">Payment / Package Discussion</SelectItem>
                      <SelectItem value="converted">Ready to Convert</SelectItem>
                      <SelectItem value="call_back">Client Requested Call Back</SelectItem>
                      <SelectItem value="not_interested">Not Interested</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* ──────────────────────────────────────────────────────────── */}
                {/* ⚡ LIVE CALL SALES COPILOT (Product Master Grounded) */}
                {/* ──────────────────────────────────────────────────────────── */}
                <div className="bg-slate-950 border border-emerald-800/70 rounded-xl p-3 space-y-2.5 shadow-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="p-1 rounded-md bg-emerald-500 text-slate-950 font-bold">
                        <Sparkles className="w-3.5 h-3.5" />
                      </span>
                      <div>
                        <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                          ⚡ Live Call Sales Copilot
                          <Badge className="bg-emerald-950 text-emerald-300 border-emerald-700 text-[9px] py-0 px-1.5 font-semibold">
                            Grounded in Product Master
                          </Badge>
                        </h5>
                        <p className="text-[10px] text-slate-400">
                          Search answers or ask AI while talking with {activeCallLead.name}
                        </p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      type="button"
                      onClick={() => setShowCallCopilot(!showCallCopilot)}
                      className="h-6 text-[10px] text-slate-400 hover:text-white px-1.5"
                    >
                      {showCallCopilot ? 'Minimize' : 'Expand'}
                    </Button>
                  </div>

                  {showCallCopilot && (
                    <>
                      {/* Search Bar */}
                      <div className="flex items-center gap-1.5">
                        <Input
                          placeholder="Ask anything (e.g. Can you guarantee PR? What are govt fees?)..."
                          value={aiCallQuery}
                          onChange={(e) => setAiCallQuery(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !aiCallLoading && aiCallQuery.trim()) {
                              handleAskCallCopilot();
                            }
                          }}
                          className="h-8 text-xs bg-slate-900 border-slate-700 text-white placeholder:text-slate-500 focus:border-emerald-500"
                        />
                        <Button
                          size="sm"
                          type="button"
                          onClick={() => handleAskCallCopilot()}
                          disabled={aiCallLoading || !aiCallQuery.trim()}
                          className="h-8 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-3 shrink-0"
                        >
                          {aiCallLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Ask Copilot'}
                        </Button>
                      </div>

                      {/* Preset Fast Query Pills */}
                      <div className="flex flex-wrap gap-1">
                        {[
                          { label: '💰 Fees & Milestones', q: 'What are the exact statutory government fees and consulting charges?' },
                          { label: '🎯 Pass Marks & Eligibility', q: 'What is the required pass mark, age cutoff and English score?' },
                          { label: '⏳ Processing Time', q: 'What is the average timeline from nomination to visa grant?' },
                          { label: '👨‍👩‍👧 Spouse & Children', q: 'Can the client include their spouse and children, and what are the fees?' },
                          { label: '🛡️ Can you guarantee PR?', q: 'Can you guarantee my PR visa approval?' },
                        ].map((item, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              setAiCallQuery(item.q);
                              handleAskCallCopilot(item.q);
                            }}
                            disabled={aiCallLoading}
                            className="px-2 py-0.5 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
                          >
                            {item.label}
                          </button>
                        ))}
                      </div>

                      {/* Live Speaking Script & Talking Points */}
                      {aiCallSpeakingScript && (
                        <div className="bg-slate-900/90 rounded-lg p-2.5 border border-emerald-600/80 space-y-2 mt-1">
                          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                            <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1">
                              🎙️ Say This on Phone:
                            </span>
                            <div className="flex items-center gap-1.5">
                              <Button
                                size="sm"
                                variant="ghost"
                                type="button"
                                onClick={() => {
                                  navigator.clipboard.writeText(aiCallSpeakingScript);
                                  toast.success('Script copied to clipboard!');
                                }}
                                className="h-5 text-[10px] text-slate-400 hover:text-white px-1.5"
                              >
                                <Copy className="w-3 h-3 mr-1" /> Copy
                              </Button>
                              <Button
                                size="sm"
                                type="button"
                                onClick={() => {
                                  setCallNotes((prev) => (prev ? `${prev}\n\n[Client Discussion]: ${aiCallQuery}\n[Explanation Given]: ${aiCallSpeakingScript}` : `[Client Discussion]: ${aiCallQuery}\n[Explanation Given]: ${aiCallSpeakingScript}`));
                                  toast.success('Appended to consultation notes below!');
                                }}
                                className="h-5 text-[10px] bg-emerald-700 hover:bg-emerald-600 text-white font-semibold px-2 rounded"
                              >
                                + Append to Notes
                              </Button>
                            </div>
                          </div>

                          <p className="text-xs text-slate-100 font-medium leading-relaxed italic bg-slate-950/80 p-2 rounded border border-slate-800">
                            &ldquo;{aiCallSpeakingScript}&rdquo;
                          </p>

                          {aiCallTalkingPoints.length > 0 && (
                            <div className="space-y-1 pt-1">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Key Reference Facts:</span>
                              <ul className="text-[11px] text-slate-300 space-y-0.5 list-disc list-inside">
                                {aiCallTalkingPoints.map((fact, idx) => (
                                  <li key={idx} className="leading-tight">{fact}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">Consultation Discussion Notes (Optional)</label>
                  <Textarea
                    placeholder="Type discussion notes, client requirements, visa qualifications..."
                    value={callNotes}
                    onChange={(e) => setCallNotes(e.target.value)}
                    className="h-16 bg-slate-800 border-slate-700 text-white text-xs placeholder:text-slate-500 resize-none"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                    Call Transcript / Conversation Dialogue (Optional - Auto-generates AI Summary)
                  </label>
                  <Textarea
                    placeholder="Paste or type conversation dialogue: e.g.&#10;Consultant: Hello John, how can I help?&#10;Client: Hi, I want to apply for Canadian PR..."
                    value={callTranscript}
                    onChange={(e) => setCallTranscript(e.target.value)}
                    className="h-20 bg-slate-800 border-slate-700 text-white text-xs placeholder:text-slate-500 resize-none font-mono"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleCloseCallModal}
                    disabled={uploadingRecording}
                    className="h-9 bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700 font-semibold"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    disabled={uploadingRecording}
                    onClick={handleSaveCallNotes}
                    className="h-9 bg-emerald-600 hover:bg-emerald-700 text-white font-bold flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-700/20"
                  >
                    {uploadingRecording ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Saving Audio...
                      </>
                    ) : (
                      <>
                        <PhoneOff className="w-3.5 h-3.5" /> End Call & Save
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        );
      })()}



      {/* ──────────────────────────────────────────────────────────── */}
      {/* CALL TRANSCRIPT ADD / EDIT MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {transcriptModal.open && (
        <Dialog open={transcriptModal.open} onOpenChange={(open) => setTranscriptModal(prev => ({ ...prev, open }))}>
          <DialogContent className="max-w-2xl bg-white border border-slate-200 shadow-2xl z-[9999]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-base font-bold text-slate-900">
                <FileText className="w-5 h-5 text-indigo-600" />
                {transcriptModal.call?.transcript ? 'Edit Call Transcript' : 'Add Conversation Transcript'}
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-500">
                Type or paste the complete conversation dialogue. Saving will automatically trigger the AI engine to generate structured summaries, client requirements, concerns, and next steps.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3 py-2 text-xs">
              <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="text-slate-500">Client:</span>{' '}
                  <strong className="text-slate-900">{transcriptModal.call?.lead_name || transcriptModal.call?.client_name || 'Client'}</strong>
                  {transcriptModal.call?.lead_phone && (
                    <span className="text-slate-500 ml-2 font-mono">({formatPhoneNumber(transcriptModal.call.lead_phone)})</span>
                  )}
                </div>
                <div>
                  <span className="text-slate-500">Advisor:</span>{' '}
                  <strong className="text-slate-900">{transcriptModal.call?.sales_person_name || 'LEAMSS Consultant'}</strong>
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Full Conversation Transcript:
                </label>
                <Textarea
                  placeholder="Advisor: Hello Mr. Sharma, thanks for connecting with LEAMSS Immigration. How can I assist you today?&#10;Client: Hi, I'm exploring Canada PR options for my family. I have 6 years experience in software engineering.&#10;Advisor: Excellent. We can calculate your CRS score and check Provincial Nominee Program (PNP) streams..."
                  value={transcriptModal.transcriptText}
                  onChange={(e) => setTranscriptModal(prev => ({ ...prev, transcriptText: e.target.value }))}
                  className="h-64 font-mono text-xs leading-relaxed border-slate-300 resize-none"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  💡 Tip: You can paste speech-to-text outputs or typed call minutes. Dialogue format (Speaker: Words) works best for AI extraction.
                </p>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setTranscriptModal(prev => ({ ...prev, open: false }))}
                disabled={transcriptModal.saving}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={transcriptModal.saving || !transcriptModal.transcriptText.trim()}
                onClick={handleSaveTranscript}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold gap-1.5 shadow-sm"
              >
                {transcriptModal.saving ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Processing AI Summary...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" /> Save Transcript & Analyze
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* QUICK ACTION: WHATSAPP MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showWhatsAppModal && selectedLead && (() => {
        const salesRepName = currentUser?.name || selectedLead.assigned_to_name || 'LEAMSS Consultant';
        const cleanNum = getSanitizedWhatsAppNumber(selectedLead.whatsapp_number || selectedLead.phone);
        const smartTemplates = getPersonalizedWaTemplates(selectedLead, salesRepName, waTemplates);

        return (
          <Dialog open={showWhatsAppModal} onOpenChange={setShowWhatsAppModal}>
            <DialogContent className="max-w-md bg-white border border-slate-200 shadow-2xl z-[9999]">
              <DialogHeader>
                <DialogTitle className="text-base font-bold flex items-center justify-between text-emerald-800">
                  <span className="flex items-center gap-2">
                    <MessageCircle className="w-5 h-5 text-emerald-600" /> WhatsApp Message to {selectedLead.name}
                  </span>
                </DialogTitle>
                <DialogDescription className="text-xs text-slate-500">
                  Send personalized WhatsApp message or start WhatsApp direct voice call.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3.5 text-xs">
                {/* Meta Header */}
                <div className="p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-100 flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <span className="text-slate-500 block text-[11px]">Destination:</span>
                    <span className="font-bold text-slate-900 font-mono">{formatPhoneNumber(selectedLead.whatsapp_number || selectedLead.phone)}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-slate-500 block text-[11px]">Consultant Identity:</span>
                    <span className="font-bold text-emerald-800 flex items-center gap-1 justify-end">
                      <UserCheck className="w-3.5 h-3.5 text-emerald-600" /> {salesRepName}
                    </span>
                  </div>
                </div>

                {/* Template Selection */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="font-semibold text-slate-700 block text-[11px]">Select Approved Template (Auto-Personalized)</label>
                    {selectedWaTemplate && (
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedWaTemplate('');
                          setWaMessage('');
                        }}
                        className="text-[10px] text-slate-400 hover:text-rose-600"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                  <Select
                    value={selectedWaTemplate}
                    onValueChange={(val) => {
                      setSelectedWaTemplate(val);
                      const matched = smartTemplates.find((t) => t.title === val || t.id === val);
                      if (matched) {
                        setWaMessage(matched.text);
                      }
                    }}
                  >
                    <SelectTrigger className="h-8 text-xs bg-slate-50 border-slate-200"><SelectValue placeholder="Choose an approved template..." /></SelectTrigger>
                    <SelectContent className="z-[99999] bg-white border border-slate-200 shadow-2xl max-h-60 overflow-y-auto">
                      {smartTemplates.map((t) => (
                        <SelectItem key={t.id} value={t.title} className="cursor-pointer hover:bg-emerald-50 py-1.5 text-xs">
                          <span className="font-medium text-slate-800">{t.title}</span> <span className="text-[10px] text-slate-400">({t.category})</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {/* 1-Click Fast Template Buttons */}
                  <div className="flex flex-wrap gap-1.5 pt-1.5 max-h-28 overflow-y-auto pr-0.5">
                    {smartTemplates.map((t) => {
                      const isSelected = selectedWaTemplate === t.title;
                      return (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => {
                            setSelectedWaTemplate(t.title);
                            setWaMessage(t.text);
                          }}
                          className={`px-2 py-1 rounded-md text-[10px] font-medium border transition-colors cursor-pointer text-left ${
                            isSelected
                              ? 'bg-emerald-100 text-emerald-800 border-emerald-400 font-semibold shadow-xs'
                              : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200'
                          }`}
                        >
                          {t.title}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Message Body */}
                <div>
                  <label className="font-semibold text-slate-700 block mb-1 text-[11px]">Message Content</label>
                  <Textarea
                    placeholder={`Type WhatsApp message or choose template above...`}
                    value={waMessage}
                    onChange={(e) => setWaMessage(e.target.value)}
                    className="h-28 text-xs resize-none"
                  />
                  <p className="text-[10px] text-slate-400 mt-1">
                    {waMessage.length} characters • Includes consultant identity: <strong className="text-emerald-700">{salesRepName}</strong>
                  </p>
                </div>

                <div className="p-2 rounded-lg bg-emerald-50/80 border border-emerald-200/70 flex items-start gap-1.5 text-[11px] text-emerald-950">
                  <Sparkles className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <p className="text-emerald-900 leading-snug">
                    Clicking <strong>Send via WhatsApp Web</strong> opens the client's actual WhatsApp chat with this message pre-filled and automatically logs it into the CRM client history.
                  </p>
                </div>
              </div>

              <DialogFooter className="flex flex-col sm:flex-row gap-2 pt-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleWhatsAppCall(selectedLead.whatsapp_number || selectedLead.phone, selectedLead)}
                  className="text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50 font-semibold gap-1"
                >
                  <PhoneCall className="w-3.5 h-3.5" /> Call
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleSendWhatsAppMessage({
                    lead: selectedLead,
                    text: waMessage,
                    mode: 'web',
                    template_name: selectedWaTemplate || null
                  })}
                  disabled={waSending || !waMessage.trim()}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1.5 flex-1 shadow-sm text-xs"
                  title="Opens client's real WhatsApp in WhatsApp Web with this message pre-filled & records in CRM history"
                >
                  {waSending ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  🚀 Send via WhatsApp Web
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        );
      })()}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* ──────────────────────────────────────────────────────────── */}
      {/* GMAIL-STYLE EMAIL COMPOSER */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showEmailModal && (
        <GmailComposer
          isOpen={showEmailModal}
          onClose={() => setShowEmailModal(false)}
          selectedLead={selectedLead}
          recipientEmail={recipientEmail || selectedLead?.email || ''}
          initialSubject={emailData?.subject || ''}
          initialBody={emailData?.body_html || ''}
          threadId={emailData?.thread_id || null}
          emailTemplates={emailTemplates}
          emailServiceStatus={emailServiceStatus}
          currentUser={currentUser}
          onOpenMailboxConfig={() => {
            loadMyMailbox();
            loadUserSignature();
            setEmailSettingsTab('signature');
            setShowMailboxModal(true);
          }}
          onEmailSent={() => {
            if (selectedLead?.id) {
              loadLeadEmails(selectedLead.id);
            }
            loadAllEmails();
          }}
        />
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* EMAIL & MAILBOX SETTINGS MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Dialog open={showMailboxModal} onOpenChange={setShowMailboxModal}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
              <Settings className="w-4 h-4 text-indigo-600" />
              Email & Mailbox Settings
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Customize your persistent default email signature and manage personal mailbox credentials for sending and receiving client emails.
            </DialogDescription>
          </DialogHeader>

          <Tabs value={emailSettingsTab} onValueChange={setEmailSettingsTab} className="w-full">
            <TabsList className="grid grid-cols-2 mb-3 bg-slate-100 p-1">
              <TabsTrigger value="signature" className="text-xs font-semibold gap-1.5 data-[state=active]:bg-white data-[state=active]:text-indigo-700 data-[state=active]:shadow-sm">
                <PenTool className="w-3.5 h-3.5 text-indigo-600" />
                Default Email Signature
              </TabsTrigger>
              <TabsTrigger value="mailbox" className="text-xs font-semibold gap-1.5 data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm">
                <Mail className="w-3.5 h-3.5 text-slate-600" />
                Mailbox & SMTP Credentials
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: DEFAULT SIGNATURE (VISUAL FORM + LOGO UPLOAD + LIVE PREVIEW) */}
            <TabsContent value="signature" className="py-1">
              <EmailSignatureEditor
                initialSignatureHtml={signatureHtml}
                currentUser={currentUser || {}}
                onSave={async (newHtml) => {
                  setSignatureHtml(newHtml);
                  await handleSaveSignatureInSettings(newHtml);
                }}
                onClose={() => setShowMailboxModal(false)}
                isSaving={savingSig}
              />
            </TabsContent>

            {/* TAB 2: MAILBOX CREDENTIALS */}
            <TabsContent value="mailbox" className="space-y-3.5 text-xs py-1">
              {/* Quick Presets */}
              <div>
                <label className="font-semibold text-slate-700 block mb-1.5">
                  Select Email Provider Preset
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setMailboxForm(f => ({ ...f, smtp_host: 'smtp.gmail.com', smtp_port: 587 }))}
                    className={`p-2 rounded-lg border text-left text-xs transition-all ${
                      mailboxForm.smtp_host === 'smtp.gmail.com' ? 'border-indigo-600 bg-indigo-50/70 font-bold text-indigo-900 shadow-sm' : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-500"></span>
                      <span>Gmail / Workspace</span>
                    </div>
                    <span className="text-[10px] text-slate-400 block mt-0.5">smtp.gmail.com:587</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setMailboxForm(f => ({ ...f, smtp_host: 'smtp.office365.com', smtp_port: 587 }))}
                    className={`p-2 rounded-lg border text-left text-xs transition-all ${
                      mailboxForm.smtp_host === 'smtp.office365.com' ? 'border-indigo-600 bg-indigo-50/70 font-bold text-indigo-900 shadow-sm' : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                      <span>Outlook / O365</span>
                    </div>
                    <span className="text-[10px] text-slate-400 block mt-0.5">smtp.office365.com</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setMailboxForm(f => ({ ...f, smtp_host: 'smtp.zoho.com', smtp_port: 587 }))}
                    className={`p-2 rounded-lg border text-left text-xs transition-all ${
                      mailboxForm.smtp_host === 'smtp.zoho.com' ? 'border-indigo-600 bg-indigo-50/70 font-bold text-indigo-900 shadow-sm' : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                      <span>Zoho Mail</span>
                    </div>
                    <span className="text-[10px] text-slate-400 block mt-0.5">smtp.zoho.com:587</span>
                  </button>
                </div>
              </div>

              {/* Sender Name & Email */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">
                    Display Name
                  </label>
                  <Input
                    value={mailboxForm.sender_name}
                    onChange={(e) => setMailboxForm(f => ({ ...f, sender_name: e.target.value }))}
                    placeholder="e.g. Pooja Sharma"
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">
                    Your Email Address <span className="text-rose-500">*</span>
                  </label>
                  <Input
                    value={mailboxForm.sender_email || mailboxForm.smtp_user}
                    onChange={(e) => setMailboxForm(f => ({ ...f, sender_email: e.target.value, smtp_user: e.target.value }))}
                    placeholder="you@leamss.com"
                    className="h-8 text-xs font-medium"
                  />
                </div>
              </div>

              {/* App Password / SMTP Password */}
              <div>
                <label className="font-semibold text-slate-700 flex items-center justify-between mb-1">
                  <span>Mailbox App Password <span className="text-rose-500">*</span></span>
                  <span className="text-[10px] text-indigo-600 font-normal">
                    (Use 16-character Google App Password)
                  </span>
                </label>
                <Input
                  type="password"
                  value={mailboxForm.smtp_pass}
                  onChange={(e) => setMailboxForm(f => ({ ...f, smtp_pass: e.target.value }))}
                  placeholder={emailServiceStatus?.personal_mailbox?.has_mailbox ? '•••••••••••• (Leave blank to keep existing password)' : 'Enter 16-character App Password (e.g. abcd efgh ijkl mnop)'}
                  className="h-8 text-xs font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1 leading-normal">
                  💡 <strong>Tip for Gmail / Google Workspace:</strong> Go to <em>myaccount.google.com</em> → Security → 2-Step Verification → <strong>App passwords</strong> → Create name &quot;LEAMSS CRM&quot; → Paste the 16-letter code here.
                </p>
              </div>

              {/* Advanced Server Details */}
              <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-100">
                <div className="col-span-2">
                  <label className="font-semibold text-slate-600 block mb-1">
                    SMTP Host
                  </label>
                  <Input
                    value={mailboxForm.smtp_host}
                    onChange={(e) => setMailboxForm(f => ({ ...f, smtp_host: e.target.value }))}
                    className="h-8 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-600 block mb-1">
                    Port
                  </label>
                  <Input
                    type="number"
                    value={mailboxForm.smtp_port}
                    onChange={(e) => setMailboxForm(f => ({ ...f, smtp_port: e.target.value }))}
                    className="h-8 text-xs font-mono"
                  />
                </div>
              </div>

              {/* Test Result Message */}
              {mailboxTestResult && (
                <div className={`p-2.5 rounded-lg border text-xs flex items-start gap-2 ${
                  mailboxTestResult.success ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'
                }`}>
                  {mailboxTestResult.success ? <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> : <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />}
                  <div>
                    <strong className="block font-semibold">{mailboxTestResult.success ? 'Connection Verified!' : 'Connection Error'}</strong>
                    <span className="text-[11px] leading-tight block">{mailboxTestResult.message}</span>
                  </div>
                </div>
              )}

              <DialogFooter className="flex items-center justify-between sm:justify-between border-t pt-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleTestMailbox}
                  disabled={testingMailbox || (!mailboxForm.smtp_pass && !emailServiceStatus?.personal_mailbox?.has_mailbox)}
                  className="text-xs gap-1 border-slate-300"
                >
                  {testingMailbox ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-amber-500" />}
                  Test Connection
                </Button>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowMailboxModal(false)}
                    className="text-xs"
                  >
                    Close
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleSaveMailbox}
                    disabled={savingMailbox}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs gap-1"
                  >
                    {savingMailbox ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                    Save Mailbox
                  </Button>
                </div>
              </DialogFooter>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* QUICK ACTION: FOLLOW-UP MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showFollowUpModal && selectedLead && (
        <Dialog open={showFollowUpModal} onOpenChange={setShowFollowUpModal}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-600" /> Schedule Follow-up for {selectedLead.name}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-semibold text-slate-700">Type</label>
                  <Select value={followUpData.type} onValueChange={(val) => setFollowUpData(p => ({ ...p, type: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Call">Call</SelectItem>
                      <SelectItem value="WhatsApp">WhatsApp</SelectItem>
                      <SelectItem value="Email">Email</SelectItem>
                      <SelectItem value="Meeting">Meeting</SelectItem>
                      <SelectItem value="Payment Follow-up">Payment Follow-up</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Priority</label>
                  <Select value={followUpData.priority} onValueChange={(val) => setFollowUpData(p => ({ ...p, priority: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700">Scheduled Date & Time</label>
                <Input
                  type="datetime-local"
                  value={followUpData.scheduled_at}
                  onChange={(e) => setFollowUpData(p => ({ ...p, scheduled_at: e.target.value }))}
                  className="h-8 text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700">Follow-up Agenda / Notes</label>
                <Textarea
                  placeholder="Notes for the follow-up..."
                  value={followUpData.notes}
                  onChange={(e) => setFollowUpData(p => ({ ...p, notes: e.target.value }))}
                  className="h-20 text-xs"
                />
              </div>
            </div>
            <DialogFooter>
              <Button size="sm" onClick={handleScheduleFollowUpSubmit} className="bg-amber-600 hover:bg-amber-700 text-white font-bold w-full">
                Schedule Follow-up
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* QUICK ACTION: REAL MEETING MODAL (GOOGLE MEET & ZOOM) */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showMeetingModal && (
        <MeetingModal
          isOpen={showMeetingModal}
          onClose={() => setShowMeetingModal(false)}
          lead={selectedLead}
          leads={leads}
          currentUser={currentUser}
          onMeetingScheduled={(newMeeting) => {
            if (selectedLead?.id) {
              loadLeadTimeline(selectedLead.id);
            }
            loadMeetings();
          }}
          onOpenEmailModal={(subject, body, threadId, targetLead) => {
            handleOpenEmailModal(subject, body, threadId, targetLead || selectedLead);
          }}
        />
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* EDIT CONSULTATION MEETING LINK MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {editingMeeting && (() => {
        const isZoomMeeting = String(editingMeeting.platform || '').toLowerCase().includes('zoom');
        const isCalendlyMeeting = String(editingMeeting.platform || '').toLowerCase().includes('calendly');
        return (
          <Dialog open={Boolean(editingMeeting)} onOpenChange={(open) => { if (!open) setEditingMeeting(null); }}>
            <DialogContent className="max-w-md p-0 rounded-2xl border-slate-200 shadow-2xl overflow-hidden">
              <div className={`p-5 text-white ${
                isCalendlyMeeting
                  ? 'bg-gradient-to-r from-slate-900 via-sky-950 to-slate-900'
                  : isZoomMeeting
                    ? 'bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900'
                    : 'bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900'
              }`}>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20`}>
                    {isCalendlyMeeting ? (
                      <Calendar className="w-5 h-5 text-sky-400" />
                    ) : (
                      <Video className={`w-5 h-5 ${isZoomMeeting ? 'text-blue-400' : 'text-emerald-400'}`} />
                    )}
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-white">
                      Update {isCalendlyMeeting ? 'Calendly' : (isZoomMeeting ? 'Zoom' : 'Google Meet')} Link
                    </h3>
                    <p className="text-xs text-slate-300 mt-0.5">
                      {editingMeeting.title}
                      {editingMeeting.contact_name ? ` • ${editingMeeting.contact_name}` : ''}
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-5 space-y-4 text-xs text-slate-700">
                {/* Quick Launch & Paste Helper */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <span className="font-semibold text-slate-800 flex items-center gap-1.5 text-xs">
                    <Sparkles className={`w-3.5 h-3.5 ${isCalendlyMeeting ? 'text-sky-500' : (isZoomMeeting ? 'text-blue-500' : 'text-amber-500')}`} /> Need your meeting link?
                  </span>
                  <div className="flex items-center gap-2 flex-wrap">
                    {isCalendlyMeeting ? (
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => {
                          window.open('https://calendly.com', '_blank');
                          toast.info('Calendly opened in new tab! Copy your event link and paste it below.');
                        }}
                        className="h-7 text-xs bg-sky-600 hover:bg-sky-700 text-white font-semibold gap-1"
                      >
                        <ExternalLink className="w-3 h-3" /> 1. Launch Calendly
                      </Button>
                    ) : isZoomMeeting ? (
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => {
                          window.open('https://zoom.us/start/videomeeting', '_blank');
                          toast.info('Zoom opened in new tab! Once your meeting starts, copy its invite link and paste it below.');
                        }}
                        className="h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold gap-1"
                      >
                        <Video className="w-3 h-3" /> 1. Launch Instant Zoom
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => {
                          window.open('https://meet.google.com/new', '_blank');
                          toast.info('Google Meet opened in new tab! Copy its room URL and paste it below.');
                        }}
                        className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold gap-1"
                      >
                        <Video className="w-3 h-3" /> 1. Launch meet.google.com/new
                      </Button>
                    )}

                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        try {
                          const text = await navigator.clipboard.readText();
                          if (text && text.trim()) {
                            const match = text.trim().match(/https?:\/\/[^\s]+/);
                            setEditMeetingNewLink(match ? match[0] : text.trim());
                            toast.success('Pasted link from clipboard!');
                          } else {
                            toast.warning('Clipboard is empty.');
                          }
                        } catch {
                          toast.info('Please paste directly with Ctrl+V / Cmd+V');
                        }
                      }}
                      className="h-7 text-xs bg-white hover:bg-slate-100 text-slate-700 border-slate-300 font-semibold gap-1"
                    >
                      <ClipboardPaste className="w-3 h-3 text-indigo-600" /> 2. Paste Link
                    </Button>
                  </div>
                  {isCalendlyMeeting && (
                    <p className="text-[11px] text-slate-500">
                      Tip: Paste your Calendly booking link (e.g. <code>https://calendly.com/your-username/30min</code>).
                    </p>
                  )}
                  {isZoomMeeting && (
                    <p className="text-[11px] text-slate-500">
                      Tip: You can paste your Personal Meeting Room link (e.g. <code>https://us05web.zoom.us/j/1234567890</code> or <code>https://zoom.us/my/yourname</code>).
                    </p>
                  )}
                </div>

                {/* Input Field */}
                <div>
                  <label className="block text-xs font-bold text-slate-900 mb-1.5">
                    Meeting Link *
                  </label>
                  <div className="flex items-center gap-2">
                    <Input
                      value={editMeetingNewLink}
                      onChange={(e) => setEditMeetingNewLink(e.target.value)}
                      placeholder={
                        isCalendlyMeeting
                          ? 'https://calendly.com/your-username/30min'
                          : isZoomMeeting
                            ? 'https://us05web.zoom.us/j/... or https://zoom.us/my/...'
                            : 'https://meet.google.com/xxx-yyyy-zzz'
                      }
                      className="h-9 text-xs font-mono bg-white flex-1"
                    />
                    {editMeetingNewLink && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(editMeetingNewLink, '_blank')}
                        className="h-9 px-2 text-xs gap-1 bg-white"
                        title="Test room"
                      >
                        <ExternalLink className="w-3 h-3 text-indigo-600" /> Test
                      </Button>
                    )}
                  </div>
                </div>

                {/* Save as permanent default */}
                <label className="flex items-center gap-2 pt-1 text-xs cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={editMeetingSaveDefault}
                    onChange={(e) => setEditMeetingSaveDefault(e.target.checked)}
                    className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
                  />
                  <span className="text-slate-700 font-medium">
                    Also save as my permanent {isCalendlyMeeting ? 'Calendly' : (isZoomMeeting ? 'Zoom' : 'Google Meet')} link for future meetings
                  </span>
                </label>
              </div>

              <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setEditingMeeting(null)}
                  className="h-8 text-xs text-slate-600"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSaveUpdatedMeetingLink}
                  disabled={savingMeetingLink}
                  className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm"
                >
                  <Check className="w-3.5 h-3.5" /> Save & Update Link
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        );
      })()}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* RESCHEDULE CONSULTATION MEETING MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showRescheduleModal && rescheduleMeeting && (
        <Dialog open={showRescheduleModal} onOpenChange={(open) => { if (!open) { setShowRescheduleModal(false); setRescheduleMeeting(null); } }}>
          <DialogContent className="max-w-lg p-0 rounded-2xl border-slate-200 shadow-2xl overflow-hidden z-[9999]">
            <div className="p-5 text-white bg-gradient-to-r from-amber-900 via-amber-800 to-slate-900">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20">
                  <RefreshCw className="w-5 h-5 text-amber-300" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-white">
                    Reschedule Client Consultation
                  </h3>
                  <p className="text-xs text-amber-100/90 mt-0.5">
                    {rescheduleMeeting.contact_name ? `${rescheduleMeeting.contact_name} • ` : ''}
                    {rescheduleMeeting.title || 'Consultation Meeting'}
                  </p>
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmitReschedule}>
              <div className="p-5 space-y-4 text-xs text-slate-700 max-h-[70vh] overflow-y-auto">
                {/* Current / Previous Schedule Notice */}
                <div className="p-3 bg-amber-50/80 rounded-xl border border-amber-200 text-amber-900 space-y-1">
                  <span className="font-bold text-[11px] uppercase tracking-wide text-amber-800 block">Current Schedule:</span>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="flex items-center gap-1 font-semibold text-slate-800">
                      <Calendar className="w-3.5 h-3.5 text-amber-700" /> {rescheduleMeeting.meeting_date || 'Not set'}
                    </span>
                    <span className="flex items-center gap-1 font-semibold text-slate-800">
                      <Clock className="w-3.5 h-3.5 text-amber-700" /> {rescheduleMeeting.meeting_time || 'Not set'}
                    </span>
                    <span className="text-slate-500">({rescheduleMeeting.duration_minutes || 30} mins)</span>
                  </div>
                  {rescheduleMeeting.meeting_link && (
                    <p className="text-[11px] text-slate-600 truncate mt-1">
                      <strong>Room:</strong> {rescheduleMeeting.meeting_link}
                    </p>
                  )}
                </div>

                {/* New Date and Time */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1 text-[11px]">
                      New Date <span className="text-rose-500">*</span>
                    </label>
                    <Input
                      type="date"
                      required
                      value={rescheduleForm.meeting_date}
                      onChange={(e) => setRescheduleForm(prev => ({ ...prev, meeting_date: e.target.value }))}
                      className="h-9 text-xs"
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1 text-[11px]">
                      New Time <span className="text-rose-500">*</span>
                    </label>
                    <Input
                      type="time"
                      required
                      value={rescheduleForm.meeting_time}
                      onChange={(e) => setRescheduleForm(prev => ({ ...prev, meeting_time: e.target.value }))}
                      className="h-9 text-xs"
                    />
                  </div>
                </div>

                {/* Duration */}
                <div>
                  <label className="font-semibold text-slate-700 block mb-1 text-[11px]">
                    Consultation Duration
                  </label>
                  <Select
                    value={String(rescheduleForm.duration_minutes || 30)}
                    onValueChange={(val) => setRescheduleForm(prev => ({ ...prev, duration_minutes: parseInt(val, 10) }))}
                  >
                    <SelectTrigger className="h-9 text-xs bg-white">
                      <SelectValue placeholder="Select duration" />
                    </SelectTrigger>
                    <SelectContent className="z-[99999] bg-white border border-slate-200">
                      <SelectItem value="15">15 minutes (Quick intro)</SelectItem>
                      <SelectItem value="30">30 minutes (Standard consultation)</SelectItem>
                      <SelectItem value="45">45 minutes (In-depth assessment)</SelectItem>
                      <SelectItem value="60">60 minutes (Comprehensive strategy)</SelectItem>
                      <SelectItem value="90">90 minutes (Full case review)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Mandatory Reschedule Reason */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="font-semibold text-slate-800 text-[11px] flex items-center gap-1">
                      Reason for Rescheduling <span className="text-rose-500 font-bold">*</span>
                      <span className="text-[10px] text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded font-medium">Mandatory</span>
                    </label>
                    <span className="text-[10px] text-slate-400">Recorded for audit</span>
                  </div>
                  <Textarea
                    required
                    placeholder="Enter reason for changing date/time (e.g. Client requested postponement due to work schedule, consultant conflict, awaiting documents)..."
                    value={rescheduleForm.reason}
                    onChange={(e) => setRescheduleForm(prev => ({ ...prev, reason: e.target.value }))}
                    className="min-h-[72px] text-xs resize-none border-amber-300 focus:border-amber-500 focus:ring-amber-500"
                  />
                  {!rescheduleForm.reason?.trim() && (
                    <p className="text-[10px] text-rose-500 mt-1">A valid reason is required to reschedule this meeting.</p>
                  )}
                </div>

                {/* Additional Notes (Optional) */}
                <div>
                  <label className="font-semibold text-slate-700 block mb-1 text-[11px]">
                    Internal Handover / Follow-up Notes (Optional)
                  </label>
                  <Input
                    placeholder="E.g. Client confirmed on call, will bring IELTS scorecard"
                    value={rescheduleForm.notes}
                    onChange={(e) => setRescheduleForm(prev => ({ ...prev, notes: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>

                {/* Client Notification Checkbox */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rescheduleForm.notify_client}
                      onChange={(e) => setRescheduleForm(prev => ({ ...prev, notify_client: e.target.checked }))}
                      className="w-4 h-4 rounded text-amber-600 border-slate-300 focus:ring-amber-500"
                    />
                    <span className="font-semibold text-slate-800 text-xs">
                      Send updated meeting invitation & Google Meet link to client automatically
                    </span>
                  </label>
                  <p className="text-[10px] text-slate-500 ml-6">
                    Recipient: {rescheduleMeeting.contact_email || selectedLead?.email || 'No email on file'}
                  </p>
                </div>
              </div>

              <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => { setShowRescheduleModal(false); setRescheduleMeeting(null); }}
                  className="h-8 text-xs text-slate-600"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={rescheduleSubmitting || !rescheduleForm.reason?.trim() || !rescheduleForm.meeting_date || !rescheduleForm.meeting_time}
                  className="h-8 text-xs bg-amber-600 hover:bg-amber-700 text-white font-semibold gap-1.5 shadow-sm"
                >
                  {rescheduleSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Rescheduling...
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" /> Confirm Reschedule
                    </>
                  )}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* MEETING RECORDING, TRANSCRIPT & AI SUMMARY MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showRecapModal && recapMeeting && (
        <Dialog open={showRecapModal} onOpenChange={(open) => { if (!open) { setShowRecapModal(false); setRecapMeeting(null); } }}>
          <DialogContent className="max-w-2xl p-0 rounded-2xl border-slate-200 shadow-2xl overflow-hidden z-[9999]">
            <div className="p-5 text-white bg-gradient-to-r from-indigo-950 via-indigo-900 to-slate-900">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20">
                    <Sparkles className="w-5 h-5 text-amber-300" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-white">
                      Meeting Notes, Recording & AI Summary
                    </h3>
                    <p className="text-xs text-indigo-200 mt-0.5">
                      {recapMeeting.contact_name ? `${recapMeeting.contact_name} • ` : ''}
                      {recapMeeting.title || 'Consultation Meeting'}
                    </p>
                  </div>
                </div>

                {recapMeeting.calendly_event_id && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={syncingRecapId === recapMeeting.id}
                    onClick={() => handleSyncRecap(recapMeeting.id)}
                    className="h-7 text-xs bg-white/10 hover:bg-white/20 text-white border-white/20 gap-1.5"
                    title="Fetch notes and recaps from Calendly API"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${syncingRecapId === recapMeeting.id ? 'animate-spin' : ''}`} />
                    Sync Calendly
                  </Button>
                )}
              </div>
            </div>

            <form onSubmit={handleSubmitRecap}>
              <div className="p-5 space-y-4 text-xs text-slate-700 max-h-[70vh] overflow-y-auto">
                {/* Meeting Recording Link */}
                <div>
                  <label className="font-semibold text-slate-700 block mb-1 text-[11px] flex items-center gap-1.5">
                    <Video className="w-3.5 h-3.5 text-rose-500" /> Meeting Recording URL (Google Drive / Meet / Zoom)
                  </label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="url"
                      placeholder="https://drive.google.com/file/... or meet recording URL"
                      value={recapForm.recording_url}
                      onChange={(e) => setRecapForm(prev => ({ ...prev, recording_url: e.target.value }))}
                      className="h-8 text-xs font-mono"
                    />
                    {recapForm.recording_url && (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => window.open(recapForm.recording_url, '_blank')}
                        className="h-8 text-xs gap-1 bg-white shrink-0"
                      >
                        <ExternalLink className="w-3 h-3 text-indigo-600" /> Test Link
                      </Button>
                    )}
                  </div>
                </div>

                {/* Participants */}
                <div>
                  <label className="font-semibold text-slate-700 block mb-1 text-[11px] flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-indigo-500" /> Participants (Client, Consultant, Rater, Family)
                  </label>
                  <Input
                    placeholder="E.g. Rajesh Kumar (Client), Jyoti Pandey (Senior Consultant)"
                    value={recapForm.participants}
                    onChange={(e) => setRecapForm(prev => ({ ...prev, participants: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>

                {/* AI Executive Summary */}
                <div>
                  <label className="font-semibold text-slate-800 block mb-1 text-[11px] flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" /> AI Executive Summary / Key Discussion
                  </label>
                  <Textarea
                    rows={4}
                    placeholder="Enter key consultation takeaways, client's chosen visa destination, family requirements, eligibility score evaluated, and main hurdles..."
                    value={recapForm.summary}
                    onChange={(e) => setRecapForm(prev => ({ ...prev, summary: e.target.value }))}
                    className="text-xs resize-y"
                  />
                </div>

                {/* Action Items */}
                <div>
                  <label className="font-semibold text-slate-800 block mb-1 text-[11px] flex items-center gap-1.5">
                    <CheckSquare className="w-3.5 h-3.5 text-emerald-600" /> Action Items & Next Steps
                  </label>
                  <Textarea
                    rows={3}
                    placeholder="1. Send Australia PR point breakdown by 5 PM&#10;2. Client to send spouse ECA evaluation report&#10;3. Follow-up consultation scheduled for next Tuesday"
                    value={recapForm.action_items}
                    onChange={(e) => setRecapForm(prev => ({ ...prev, action_items: e.target.value }))}
                    className="text-xs resize-y"
                  />
                </div>

                {/* Meeting Transcript / Raw Notes */}
                <div>
                  <label className="font-semibold text-slate-700 block mb-1 text-[11px] flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-slate-500" /> Full Discussion Transcript or Detailed Notes
                  </label>
                  <Textarea
                    rows={6}
                    placeholder="Paste verbatim transcript from Google Meet / Otter.ai / Calendly or detailed discussion notes..."
                    value={recapForm.transcripts}
                    onChange={(e) => setRecapForm(prev => ({ ...prev, transcripts: e.target.value }))}
                    className="text-xs font-mono resize-y"
                  />
                </div>
              </div>

              <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => { setShowRecapModal(false); setRecapMeeting(null); }}
                  className="h-8 text-xs text-slate-600"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={recapSubmitting}
                  className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm"
                >
                  {recapSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Saving Notes...
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" /> Save Meeting Notes & Recap
                    </>
                  )}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* WHATSAPP MESSAGE STATUS & AUDIT VERIFICATION MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {viewingWaMessage && (
        <Dialog open={Boolean(viewingWaMessage)} onOpenChange={(open) => { if (!open) setViewingWaMessage(null); }}>
          <DialogContent className="max-w-md bg-white border border-slate-200 shadow-2xl p-0 rounded-2xl overflow-hidden z-[9999]">
            <div className={`p-5 text-white ${
              viewingWaMessage.status === 'sent' || viewingWaMessage.status === 'delivered' || viewingWaMessage.status === 'read'
                ? 'bg-gradient-to-r from-emerald-900 via-teal-950 to-slate-900'
                : viewingWaMessage.status === 'failed'
                  ? 'bg-gradient-to-r from-rose-950 via-red-900 to-slate-900'
                  : 'bg-gradient-to-r from-amber-950 via-slate-900 to-slate-900'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20">
                    <MessageSquare className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-white">
                      WhatsApp Message Verification
                    </h3>
                    <p className="text-xs text-slate-300 mt-0.5">
                      Client: <strong className="text-white">{viewingWaMessage.contact_name || selectedLead?.name || 'Client'}</strong>
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-5 space-y-4 text-xs">
              {/* Status Banner */}
              <div className={`p-3 rounded-xl border flex items-center justify-between ${
                viewingWaMessage.status === 'sent' || viewingWaMessage.status === 'delivered' || viewingWaMessage.status === 'read'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : viewingWaMessage.status === 'failed'
                    ? 'bg-rose-50 border-rose-200 text-rose-900'
                    : 'bg-amber-50 border-amber-200 text-amber-900'
              }`}>
                <div className="flex items-center gap-2">
                  {viewingWaMessage.status === 'sent' || viewingWaMessage.status === 'delivered' || viewingWaMessage.status === 'read' ? (
                    <CheckCheck className="w-5 h-5 text-emerald-600" />
                  ) : viewingWaMessage.status === 'failed' ? (
                    <AlertCircle className="w-5 h-5 text-rose-600" />
                  ) : (
                    <Clock className="w-5 h-5 text-amber-600 animate-pulse" />
                  )}
                  <div>
                    <span className="font-bold text-sm block">
                      {viewingWaMessage.status === 'sent'
                        ? 'Sent (WhatsApp Web)'
                        : viewingWaMessage.status === 'delivered'
                          ? 'Delivered'
                          : viewingWaMessage.status === 'read'
                            ? 'Read by Recipient'
                            : viewingWaMessage.status === 'failed'
                              ? 'Failed / Cancelled'
                              : 'Pending Confirmation'}
                    </span>
                    <span className="text-[11px] opacity-80">
                      {viewingWaMessage.status === 'sent' || viewingWaMessage.status === 'delivered' || viewingWaMessage.status === 'read'
                        ? '✓ Verified & logged in Salesperson Activity Audit Log'
                        : viewingWaMessage.status === 'failed'
                          ? 'Excluded from CRM Activity Audit Log'
                          : '⚠️ Unconfirmed — not recorded in Audit Log until marked Sent'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Message Metadata Grid */}
              <div className="bg-slate-50 rounded-xl p-3 border border-slate-200 grid grid-cols-2 gap-3 text-slate-700">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Client Name</span>
                  <span className="font-semibold text-slate-900 text-xs">{viewingWaMessage.contact_name || selectedLead?.name || 'Client'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Recipient Phone</span>
                  <span className="font-semibold font-mono text-slate-900 text-xs">{viewingWaMessage.phone || selectedLead?.whatsapp_number || selectedLead?.phone || '-'}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Salesperson</span>
                  <span className="font-semibold text-slate-900 text-xs flex items-center gap-1">
                    <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                    {viewingWaMessage.sales_person_name || currentUser?.name || 'Sales Person'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Delivery Channel</span>
                  <span className="font-semibold text-slate-900 text-xs capitalize">
                    {viewingWaMessage.channel ? viewingWaMessage.channel.replace(/_/g, ' ') : 'WhatsApp Web'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Sent Date & Time</span>
                  <span className="font-semibold text-slate-900 text-xs">
                    {viewingWaMessage.created_at ? new Date(viewingWaMessage.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '-'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Confirmation Date & Time</span>
                  <span className="font-semibold text-slate-900 text-xs">
                    {viewingWaMessage.confirmed_at
                      ? new Date(viewingWaMessage.confirmed_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
                      : viewingWaMessage.status === 'sent'
                        ? (viewingWaMessage.created_at ? new Date(viewingWaMessage.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : 'Confirmed')
                        : 'Awaiting confirmation'}
                  </span>
                </div>
                {viewingWaMessage.template_name && (
                  <div className="col-span-2">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Template Used</span>
                    <span className="font-semibold text-emerald-700 text-xs">
                      {viewingWaMessage.template_name}
                    </span>
                  </div>
                )}
              </div>

              {/* Message Content Preview */}
              <div>
                <span className="text-[11px] font-semibold text-slate-600 block mb-1">Message Content:</span>
                <div className="p-3 bg-white border border-slate-200 rounded-xl max-h-40 overflow-y-auto whitespace-pre-wrap font-sans text-slate-800 leading-relaxed text-xs">
                  {viewingWaMessage.text || <span className="italic text-slate-400">No text body</span>}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-100 flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const phoneToUse = viewingWaMessage.phone || selectedLead?.whatsapp_number || selectedLead?.phone;
                    const webUrl = getDirectWhatsAppWebLink(phoneToUse, viewingWaMessage.text);
                    if (webUrl) window.open(webUrl, '_blank');
                  }}
                  className="text-xs text-emerald-700 border-emerald-200 hover:bg-emerald-50 gap-1 cursor-pointer"
                >
                  <ArrowUpRight className="w-3.5 h-3.5" /> Re-open in WhatsApp Web
                </Button>

                <div className="flex items-center gap-2">
                  {viewingWaMessage.status === 'pending_confirmation' && (
                    <>
                      <Button
                        type="button"
                        size="sm"
                        onClick={async () => {
                          const mId = viewingWaMessage.id || viewingWaMessage._id;
                          await handleConfirmWhatsAppStatus(mId, 'sent', selectedLead);
                        }}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs cursor-pointer"
                      >
                        ✓ Mark Sent
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="destructive"
                        onClick={async () => {
                          const mId = viewingWaMessage.id || viewingWaMessage._id;
                          await handleConfirmWhatsAppStatus(mId, 'failed', selectedLead);
                        }}
                        className="text-xs font-bold cursor-pointer"
                      >
                        ✕ Mark Failed
                      </Button>
                    </>
                  )}
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setViewingWaMessage(null)}
                    className="text-xs cursor-pointer"
                  >
                    Close
                  </Button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* RESUME PREVIEW MODAL (View first, then Download or Replace) */}
      {/* ──────────────────────────────────────────────────────────── */}
      {resumePreviewModal.open && (
        <Dialog
          open={resumePreviewModal.open}
          onOpenChange={(open) => setResumePreviewModal((prev) => ({ ...prev, open }))}
        >
          <DialogContent className="max-w-4xl h-[90vh] flex flex-col p-0 overflow-hidden bg-white rounded-2xl shadow-2xl border border-slate-200 z-[10050]">
            <DialogHeader className="p-4 bg-slate-900 text-white flex flex-row items-center justify-between border-b border-slate-800">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-base border border-emerald-500/30">
                  📄
                </div>
                <div className="min-w-0">
                  <DialogTitle className="text-sm font-bold text-white flex items-center gap-2 truncate">
                    <span>{resumePreviewModal.lead?.name || 'Candidate'} — Resume Preview</span>
                    {resumePreviewModal.lead?.lead_number && (
                      <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                        {resumePreviewModal.lead.lead_number}
                      </span>
                    )}
                  </DialogTitle>
                  <DialogDescription className="text-xs text-slate-400 truncate flex items-center gap-2 mt-0.5">
                    <span className="truncate">{resumePreviewModal.filename}</span>
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3 h-3" /> Linked to CRM Record
                    </span>
                  </DialogDescription>
                </div>
              </div>

              {/* Action Bar in Header */}
              <div className="flex items-center gap-2 mr-6">
                {/* Download Button */}
                <Button
                  size="sm"
                  type="button"
                  onClick={() => handleDownloadResume(resumePreviewModal.lead)}
                  className="h-8 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 shadow-sm"
                  title="Download candidate resume"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </Button>

                {/* Replace Resume Button */}
                <label className="cursor-pointer inline-flex items-center gap-1.5 h-8 px-2.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors shadow-sm">
                  <Upload className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Replace Resume</span>
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    className="hidden"
                    onChange={async (e) => {
                      if (e.target.files?.[0]) {
                        const file = e.target.files[0];
                        await handleResumeFileUpload(resumePreviewModal.lead, file);
                        e.target.value = '';
                      }
                    }}
                  />
                </label>

                {/* Open External Tab */}
                <a
                  href={resumePreviewModal.resumeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                  title="Open in new window"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </DialogHeader>

            {/* PDF Viewer Body */}
            <div className="flex-1 w-full bg-slate-100 relative overflow-hidden flex flex-col">
              {resumePreviewModal.resumeUrl ? (
                <iframe
                  key={resumePreviewModal.resumeUrl}
                  src={`${resumePreviewModal.resumeUrl}#toolbar=1&navpanes=0`}
                  title={resumePreviewModal.filename}
                  className="w-full h-full border-0"
                />
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-2">
                  <FileText className="w-10 h-10 text-slate-400" />
                  <p className="text-sm font-medium">No resume document loaded</p>
                </div>
              )}
            </div>

            {/* Footer with summary metadata */}
            <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
              <div className="flex items-center gap-3">
                <span>Candidate: <strong className="text-slate-800">{resumePreviewModal.lead?.name}</strong></span>
                {resumePreviewModal.lead?.email && (
                  <span>Email: <span className="text-slate-700">{resumePreviewModal.lead.email}</span></span>
                )}
                {resumePreviewModal.lead?.phone && (
                  <span>Phone: <span className="text-slate-700">{resumePreviewModal.lead.phone}</span></span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setResumePreviewModal((prev) => ({ ...prev, open: false }))}
                  className="h-7 text-xs text-slate-600 hover:text-slate-900"
                >
                  Close Preview
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* PRE-ASSESSMENT REPORT PREVIEW MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {reportPreviewModal.open && (
        <Dialog
          open={reportPreviewModal.open}
          onOpenChange={(open) => setReportPreviewModal((prev) => ({ ...prev, open }))}
        >
          <DialogContent className="max-w-4xl h-[90vh] flex flex-col p-0 overflow-hidden bg-white rounded-2xl shadow-2xl border border-slate-200 z-[10050]">
            <DialogHeader className="p-4 bg-slate-900 text-white flex flex-row items-center justify-between border-b border-slate-800">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-base border border-purple-500/30">
                  📊
                </div>
                <div className="min-w-0">
                  <DialogTitle className="text-sm font-bold text-white flex items-center gap-2 truncate">
                    <span>{reportPreviewModal.lead?.name || 'Client'} — Pre-Assessment Report Preview</span>
                    {reportPreviewModal.lead?.lead_number && (
                      <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-800 text-purple-400 border border-slate-700">
                        {reportPreviewModal.lead.lead_number}
                      </span>
                    )}
                  </DialogTitle>
                  <DialogDescription className="text-xs text-slate-400 truncate flex items-center gap-2 mt-0.5">
                    <span className="truncate">{reportPreviewModal.filename}</span>
                    <span className="inline-flex items-center gap-1 text-[10px] text-purple-400 font-medium">
                      <CheckCircle2 className="w-3 h-3" /> Attached to Client Record
                    </span>
                  </DialogDescription>
                </div>
              </div>

              {/* Action Bar in Header */}
              <div className="flex items-center gap-2 mr-6">
                {/* Download Button */}
                <Button
                  size="sm"
                  type="button"
                  onClick={() => handleDownloadReport(reportPreviewModal.lead)}
                  className="h-8 text-xs font-semibold bg-purple-600 hover:bg-purple-700 text-white gap-1.5 shadow-sm"
                  title="Download Pre-Assessment Report"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </Button>

                {/* Replace Report Button */}
                <label className="cursor-pointer inline-flex items-center gap-1.5 h-8 px-2.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors shadow-sm">
                  <Upload className="w-3.5 h-3.5 text-purple-400" />
                  <span>Replace Report</span>
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx"
                    className="hidden"
                    onChange={async (e) => {
                      if (e.target.files?.[0]) {
                        const file = e.target.files[0];
                        await handlePreAssessmentReportUpload(reportPreviewModal.lead, file);
                        e.target.value = '';
                      }
                    }}
                  />
                </label>

                {/* Open External Tab */}
                <a
                  href={reportPreviewModal.reportUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                  title="Open in new window"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </DialogHeader>

            {/* Document Viewer Body */}
            <div className="flex-1 w-full bg-slate-100 relative overflow-hidden flex flex-col">
              {reportPreviewModal.reportUrl ? (
                <iframe
                  key={reportPreviewModal.reportUrl}
                  src={`${reportPreviewModal.reportUrl}#toolbar=1&navpanes=0`}
                  title={reportPreviewModal.filename}
                  className="w-full h-full border-0"
                />
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-500 gap-2">
                  <FileText className="w-10 h-10 text-slate-400" />
                  <p className="text-sm font-medium">No report document loaded</p>
                </div>
              )}
            </div>

            {/* Footer with summary metadata */}
            <div className="px-4 py-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
              <div className="flex items-center gap-3">
                <span>Client: <strong className="text-slate-800">{reportPreviewModal.lead?.name}</strong></span>
                {reportPreviewModal.lead?.email && (
                  <span>Email: <span className="text-slate-700">{reportPreviewModal.lead.email}</span></span>
                )}
                {reportPreviewModal.lead?.phone && (
                  <span>Phone: <span className="text-slate-700">{reportPreviewModal.lead.phone}</span></span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setReportPreviewModal((prev) => ({ ...prev, open: false }))}
                  className="h-7 text-xs text-slate-600 hover:text-slate-900"
                >
                  Close Preview
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* QUICK ACTION: CONVERT TO CLIENT MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showConvertModal && selectedLead && (
        <Dialog open={showConvertModal} onOpenChange={setShowConvertModal}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2 text-purple-700">
                <ShieldCheck className="w-5 h-5 text-purple-600" /> Convert {selectedLead.name} to Client
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3 text-xs">
              <p className="text-slate-500">
                This creates a permanent Client record while <strong>preserving all Lead history</strong>, notes, calls, and communication threads.
              </p>
              
              <div>
                <label className="font-semibold text-slate-700">Package Fee (₹)</label>
                <Input
                  type="number"
                  value={convertData.package_price}
                  onChange={(e) => setConvertData(p => ({ ...p, package_price: parseFloat(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700">Discount Offered (₹)</label>
                <Input
                  type="number"
                  value={convertData.discount}
                  onChange={(e) => setConvertData(p => ({ ...p, discount: parseFloat(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700">Initial Paid Amount (₹)</label>
                <Input
                  type="number"
                  value={convertData.paid_amount}
                  onChange={(e) => setConvertData(p => ({ ...p, paid_amount: parseFloat(e.target.value) || 0 }))}
                  className="h-8 text-xs"
                />
              </div>
            </div>
            <DialogFooter>
              <Button size="sm" onClick={handleConvertLeadSubmit} className="bg-purple-600 hover:bg-purple-700 text-white font-bold w-full">
                Confirm Client Conversion
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* ADD LEAD MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showAddLead && (
        <Dialog open={showAddLead} onOpenChange={(open) => { setShowAddLead(open); if (!open) setNewLeadResumeFile(null); }}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-emerald-600" /> Add New Lead / Prospect
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateLead} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700">Full Name *</label>
                  <Input
                    required
                    placeholder="e.g. Rahul Verma"
                    value={newLead.name}
                    onChange={(e) => setNewLead(p => ({ ...p, name: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Phone Number *</label>
                  <Input
                    required
                    placeholder="+91 98765 43210"
                    value={newLead.phone}
                    onChange={(e) => setNewLead(p => ({ ...p, phone: e.target.value, whatsapp_number: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Email Address</label>
                  <Input
                    type="email"
                    placeholder="client@example.com"
                    value={newLead.email}
                    onChange={(e) => setNewLead(p => ({ ...p, email: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">WhatsApp Number</label>
                  <Input
                    placeholder="+91 98765 43210"
                    value={newLead.whatsapp_number}
                    onChange={(e) => setNewLead(p => ({ ...p, whatsapp_number: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Occupation / Job Title</label>
                  <Input
                    placeholder="e.g. Senior Software Engineer / Nurse"
                    value={newLead.occupation}
                    onChange={(e) => setNewLead(p => ({ ...p, occupation: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Total Work Experience</label>
                  <Input
                    placeholder="e.g. 5 Years / 4+ Years"
                    value={newLead.total_work_experience}
                    onChange={(e) => setNewLead(p => ({ ...p, total_work_experience: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Highest / Latest Qualification</label>
                  <Input
                    placeholder="e.g. B.Tech / Master of Science / MBA"
                    value={newLead.latest_qualification}
                    onChange={(e) => setNewLead(p => ({ ...p, latest_qualification: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">City / Location</label>
                  <Input
                    placeholder="e.g. Mumbai, Maharashtra"
                    value={newLead.city}
                    onChange={(e) => setNewLead(p => ({ ...p, city: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Country of Interest</label>
                  <Select value={newLead.country_of_interest} onValueChange={(val) => setNewLead(p => ({ ...p, country_of_interest: val, interested_country: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Service Interested</label>
                  <Input
                    placeholder="e.g. Canada PR Express Entry"
                    value={newLead.service_interested}
                    onChange={(e) => setNewLead(p => ({ ...p, service_interested: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Program / Visa Type</label>
                  <Input
                    placeholder="e.g. Federal Skilled Worker / Subclass 189"
                    value={newLead.interested_program}
                    onChange={(e) => setNewLead(p => ({ ...p, interested_program: e.target.value, visa_type: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Lead Source</label>
                  <Select value={newLead.source} onValueChange={(val) => setNewLead(p => ({ ...p, source: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {SOURCES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Budget Range</label>
                  <Input
                    placeholder="e.g. ₹75,000"
                    value={newLead.budget}
                    onChange={(e) => setNewLead(p => ({ ...p, budget: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Lead Priority</label>
                  <Select value={newLead.priority || 'medium'} onValueChange={(val) => setNewLead(p => ({ ...p, priority: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Assign To (Sales Person)</label>
                  <Select
                    value={newLead.assigned_to || 'unassigned'}
                    onValueChange={(val) => {
                      const rep = salesReps.find(r => r.id === val);
                      setNewLead(p => ({
                        ...p,
                        assigned_to: val === 'unassigned' ? '' : val,
                        assigned_to_name: rep ? rep.name : ''
                      }));
                    }}
                  >
                    <SelectTrigger className="h-8 text-xs bg-slate-50"><SelectValue placeholder="Select Sales Person" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unassigned">— Unassigned / Auto —</SelectItem>
                      {salesReps.map(rep => (
                        <SelectItem key={rep.id} value={rep.id}>
                          {rep.name} {rep.role ? `(${rep.role.replace(/_/g, ' ')})` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-emerald-600" />
                      Upload Resume / CV <span className="text-slate-400 font-normal text-[11px]">(Optional)</span>
                    </span>
                    {newLeadResumeFile && (
                      <button
                        type="button"
                        onClick={() => setNewLeadResumeFile(null)}
                        className="text-[10px] text-red-500 hover:text-red-700 inline-flex items-center gap-0.5"
                      >
                        <X className="w-3 h-3" /> Remove
                      </button>
                    )}
                  </label>
                  {newLeadResumeFile ? (
                    <div className="h-8 px-2.5 bg-emerald-50 border border-emerald-300 rounded-md flex items-center justify-between text-xs text-emerald-900 mt-0.5">
                      <div className="flex items-center gap-1.5 truncate">
                        <FileText className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                        <span className="truncate font-medium">{newLeadResumeFile.name}</span>
                        <span className="text-[10px] text-emerald-600 flex-shrink-0">
                          ({(newLeadResumeFile.size / 1024).toFixed(0)} KB)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setNewLeadResumeFile(null)}
                        className="text-emerald-700 hover:text-red-600 ml-1 p-0.5"
                        title="Remove file"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <label className="h-8 px-2.5 bg-slate-50 hover:bg-emerald-50/50 border border-dashed border-slate-300 hover:border-emerald-400 rounded-md flex items-center justify-center gap-1.5 cursor-pointer transition-colors text-xs text-slate-600 hover:text-emerald-700 mt-0.5">
                      <Upload className="w-3.5 h-3.5 text-slate-500" />
                      <span className="font-medium">Attach CV (.pdf, .doc, .docx)</span>
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx,.txt"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            if (file.size > 15 * 1024 * 1024) {
                              toast.error('Resume file exceeds maximum limit of 15MB');
                              return;
                            }
                            setNewLeadResumeFile(file);
                          }
                          e.target.value = '';
                        }}
                      />
                    </label>
                  )}
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700">Consultation Notes / Initial Message</label>
                <Textarea
                  placeholder="Applicant background, CRS score, IELTS, career goals, etc."
                  value={newLead.message}
                  onChange={(e) => setNewLead(p => ({ ...p, message: e.target.value }))}
                  className="h-16 text-xs"
                />
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={() => { setShowAddLead(false); setNewLeadResumeFile(null); }}>Cancel</Button>
                <Button type="submit" disabled={saving} size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold">
                  {saving ? 'Saving...' : 'Save Lead'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* EDIT LEAD MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showEditLead && (
        <Dialog open={showEditLead} onOpenChange={(open) => { setShowEditLead(open); if (!open) { setEditLeadResumeFile(null); setEditingLeadId(null); setEditingLead(null); } }}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <Edit className="w-5 h-5 text-emerald-600" /> Edit Lead / Profile Details
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSaveEditLead} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700">Full Name *</label>
                  <Input
                    required
                    placeholder="Full Name"
                    value={editLeadForm.name || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, name: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Phone Number *</label>
                  <Input
                    required
                    placeholder="Phone Number"
                    value={editLeadForm.phone || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, phone: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Email Address</label>
                  <Input
                    type="email"
                    placeholder="client@example.com"
                    value={editLeadForm.email || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, email: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">WhatsApp Number</label>
                  <Input
                    placeholder="WhatsApp Number"
                    value={editLeadForm.whatsapp_number || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, whatsapp_number: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Occupation / Job Title</label>
                  <Input
                    placeholder="e.g. Senior Software Engineer"
                    value={editLeadForm.occupation || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, occupation: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Total Work Experience</label>
                  <Input
                    placeholder="e.g. 5 Years"
                    value={editLeadForm.total_work_experience || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, total_work_experience: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Highest / Latest Qualification</label>
                  <Input
                    placeholder="e.g. B.Tech / MBA / Master's"
                    value={editLeadForm.latest_qualification || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, latest_qualification: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">City / Location</label>
                  <Input
                    placeholder="e.g. Mumbai, India"
                    value={editLeadForm.city || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, city: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Country of Interest</label>
                  <Select value={editLeadForm.country_of_interest || 'Canada'} onValueChange={(val) => setEditLeadForm(p => ({ ...p, country_of_interest: val, interested_country: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {COUNTRIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Service Interested</label>
                  <Input
                    placeholder="e.g. Canada PR Express Entry"
                    value={editLeadForm.service_interested || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, service_interested: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Program / Visa Type</label>
                  <Input
                    placeholder="e.g. Federal Skilled Worker"
                    value={editLeadForm.interested_program || editLeadForm.visa_type || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, interested_program: e.target.value, visa_type: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Budget Range</label>
                  <Input
                    placeholder="e.g. ₹75,000"
                    value={editLeadForm.budget || ''}
                    onChange={(e) => setEditLeadForm(p => ({ ...p, budget: e.target.value }))}
                    className="h-8 text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Lead Source</label>
                  <Select value={editLeadForm.source || 'Website'} onValueChange={(val) => setEditLeadForm(p => ({ ...p, source: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {SOURCES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Lead Priority</label>
                  <Select value={editLeadForm.priority || 'medium'} onValueChange={(val) => setEditLeadForm(p => ({ ...p, priority: val }))}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700">Assign To (Sales Person)</label>
                  <Select
                    value={editLeadForm.assigned_to || 'unassigned'}
                    onValueChange={(val) => {
                      const rep = salesReps.find(r => r.id === val);
                      setEditLeadForm(p => ({
                        ...p,
                        assigned_to: val === 'unassigned' ? '' : val,
                        assigned_to_name: rep ? rep.name : ''
                      }));
                    }}
                  >
                    <SelectTrigger className="h-8 text-xs bg-slate-50"><SelectValue placeholder="Select Sales Person" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unassigned">— Unassigned —</SelectItem>
                      {salesReps.map(rep => (
                        <SelectItem key={rep.id} value={rep.id}>
                          {rep.name} {rep.role ? `(${rep.role.replace(/_/g, ' ')})` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-emerald-600" />
                      Candidate Resume / CV <span className="text-slate-400 font-normal text-[11px]">(Optional)</span>
                    </span>
                    {editLeadResumeFile && (
                      <button
                        type="button"
                        onClick={() => setEditLeadResumeFile(null)}
                        className="text-[10px] text-red-500 hover:text-red-700 inline-flex items-center gap-0.5"
                      >
                        <X className="w-3 h-3" /> Remove
                      </button>
                    )}
                  </label>
                  {editLeadResumeFile ? (
                    <div className="h-8 px-2.5 bg-emerald-50 border border-emerald-300 rounded-md flex items-center justify-between text-xs text-emerald-900 mt-0.5">
                      <div className="flex items-center gap-1.5 truncate">
                        <FileText className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                        <span className="truncate font-medium">{editLeadResumeFile.name}</span>
                        <span className="text-[10px] text-emerald-600 flex-shrink-0">
                          ({(editLeadResumeFile.size / 1024).toFixed(0)} KB)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => setEditLeadResumeFile(null)}
                        className="text-emerald-700 hover:text-red-600 ml-1 p-0.5"
                        title="Remove file"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (selectedLead?.resume_file_id || selectedLead?.resume_url) ? (
                    <div className="h-8 px-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between text-xs mt-0.5">
                      <button
                        type="button"
                        onClick={() => handleOpenResumePreview(selectedLead)}
                        className="flex items-center gap-1.5 text-emerald-700 hover:text-emerald-800 font-medium truncate"
                        title="View current resume preview"
                      >
                        <FileText className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
                        <span className="truncate">{selectedLead.resume_filename || 'Attached Resume'}</span>
                      </button>
                      <label className="cursor-pointer text-[10px] text-blue-600 hover:text-blue-800 font-semibold ml-2 flex-shrink-0">
                        Replace
                        <input
                          type="file"
                          accept=".pdf,.doc,.docx,.txt"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              if (file.size > 15 * 1024 * 1024) {
                                toast.error('Resume file exceeds maximum limit of 15MB');
                                return;
                              }
                              setEditLeadResumeFile(file);
                            }
                            e.target.value = '';
                          }}
                        />
                      </label>
                    </div>
                  ) : (
                    <label className="h-8 px-2.5 bg-slate-50 hover:bg-emerald-50/50 border border-dashed border-slate-300 hover:border-emerald-400 rounded-md flex items-center justify-center gap-1.5 cursor-pointer transition-colors text-xs text-slate-600 hover:text-emerald-700 mt-0.5">
                      <Upload className="w-3.5 h-3.5 text-slate-500" />
                      <span className="font-medium">Attach CV (.pdf, .doc, .docx)</span>
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx,.txt"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            if (file.size > 15 * 1024 * 1024) {
                              toast.error('Resume file exceeds maximum limit of 15MB');
                              return;
                            }
                            setEditLeadResumeFile(file);
                          }
                          e.target.value = '';
                        }}
                      />
                    </label>
                  )}
                </div>
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" size="sm" onClick={() => { setShowEditLead(false); setEditLeadResumeFile(null); setEditingLeadId(null); setEditingLead(null); }}>Cancel</Button>
                <Button
                  type="submit"
                  onClick={handleSaveEditLead}
                  disabled={saving}
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                >
                  {saving ? 'Saving...' : 'Update Lead'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* ──────────────────────────────────────────────────────────── */}
      {/* BULK EXCEL / CSV IMPORT MODAL (ADMIN ONLY) */}
      {/* ──────────────────────────────────────────────────────────── */}
      {showImportModal && isAdmin && (
        <Dialog open={showImportModal} onOpenChange={(open) => { setShowImportModal(open); if (!open) setImportResults(null); }}>
          <DialogContent className="max-w-3xl max-h-[92vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex items-center justify-between">
                <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-700">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <span>Bulk Import Leads</span>
                </DialogTitle>
                <Badge className="bg-indigo-100 text-indigo-800 border-indigo-200 text-xs font-semibold px-2 py-0.5">
                  <ShieldCheck className="w-3 h-3 mr-1 inline" /> Admin Only
                </Badge>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Upload Excel (<code className="text-emerald-700 font-semibold">.xlsx</code>, <code className="text-emerald-700 font-semibold">.xls</code>) or CSV (<code className="text-emerald-700 font-semibold">.csv</code>) files, assign specific row ranges (e.g. 1–100, 101–200) to different Sales Persons, or split large datasets automatically.
              </p>
            </DialogHeader>

            <div className="space-y-4 text-xs mt-2">
              {/* Mode Selector & Template Download */}
              <div className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-slate-200">
                <div className="flex gap-1">
                  <Button
                    type="button"
                    variant={importMode === 'file' ? 'default' : 'ghost'}
                    size="sm"
                    className={`h-7 text-xs font-semibold ${importMode === 'file' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'text-slate-600'}`}
                    onClick={() => { setImportMode('file'); setImportResults(null); }}
                  >
                    <Upload className="w-3.5 h-3.5 mr-1" /> Upload File (Excel / CSV)
                  </Button>
                  <Button
                    type="button"
                    variant={importMode === 'paste' ? 'default' : 'ghost'}
                    size="sm"
                    className={`h-7 text-xs font-semibold ${importMode === 'paste' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' : 'text-slate-600'}`}
                    onClick={() => { setImportMode('paste'); setImportResults(null); }}
                  >
                    <FileText className="w-3.5 h-3.5 mr-1" /> Paste CSV Text
                  </Button>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadTemplate}
                  className="h-7 text-xs text-slate-700 border-slate-300 hover:bg-slate-100"
                >
                  <Download className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Download Template
                </Button>
              </div>

              {/* Upload File Mode */}
              {importMode === 'file' ? (
                <div className="space-y-2">
                  <label className="font-semibold text-slate-700 flex items-center gap-1.5">
                    Select Excel or CSV Spreadsheet
                  </label>
                  <div className="border-2 border-dashed border-slate-200 hover:border-emerald-500 rounded-xl p-5 text-center transition-colors bg-slate-50/50">
                    <input
                      type="file"
                      id="bulk-import-file-input"
                      accept=".xlsx, .xls, .csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, text/csv"
                      className="hidden"
                      onChange={handleFileChange}
                    />
                    {importFile ? (
                      <div className="flex items-center justify-between bg-white p-3 rounded-lg border border-emerald-300 shadow-sm">
                        <div className="flex items-center gap-3 text-left">
                          <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                            <FileCheck className="w-5 h-5" />
                          </div>
                          <div>
                            <p className="font-bold text-slate-900 text-xs">{importFile.name}</p>
                            <p className="text-[11px] text-slate-500">{(importFile.size / 1024).toFixed(1)} KB</p>
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setImportFile(null);
                            setFilePreviewStats({ total_rows: 0, headers: [], filename: '' });
                            setImportResults(null);
                          }}
                          className="h-7 px-2 text-rose-600 hover:bg-rose-50"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    ) : (
                      <label htmlFor="bulk-import-file-input" className="cursor-pointer flex flex-col items-center">
                        <div className="w-11 h-11 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mb-2">
                          <Upload className="w-5 h-5" />
                        </div>
                        <span className="font-semibold text-slate-800">Click to choose or drag & drop Excel / CSV file</span>
                        <span className="text-[11px] text-slate-400 mt-1">Supports .xlsx, .xls, and .csv up to 10MB</span>
                      </label>
                    )}
                  </div>
                </div>
              ) : (
                /* Paste CSV Mode */
                <div className="space-y-2">
                  <label className="font-semibold text-slate-700">Paste CSV Data with Headers</label>
                  <Textarea
                    placeholder="name,phone,email,country,service,budget,occupation,experience,qualification,city,source,assigned_to&#10;Amit Shah,+919988776611,amit@test.com,Canada,Canada PR,₹75000,Software Engineer,4 Years,B.Tech,Mumbai,Google Ads,partner@leamss.com&#10;Pooja Mehra,+919876543210,pooja@test.com,Australia,Skilled Visa,₹60000,Data Analyst,3 Years,M.Sc,Bangalore,Referral,"
                    value={importCsvText}
                    onChange={(e) => handleCsvTextChange(e.target.value)}
                    className="h-32 font-mono text-xs leading-relaxed"
                  />
                </div>
              )}

              {/* Data Detection & Structure Banner */}
              {previewLoading && (
                <div className="flex items-center gap-2 p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-xs font-medium">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                  <span>Inspecting spreadsheet structure and counting rows...</span>
                </div>
              )}

              {filePreviewStats.total_rows > 0 && !previewLoading && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-xs">
                      {filePreviewStats.total_rows}
                    </div>
                    <div>
                      <p className="font-bold text-emerald-950 text-xs">
                        {filePreviewStats.total_rows} Data Leads Detected
                        <span className="text-emerald-700 font-normal ml-1.5 font-mono text-[11px]">(Rows 1 to {filePreviewStats.total_rows})</span>
                      </p>
                      <p className="text-[11px] text-emerald-700">
                        Detected columns: {filePreviewStats.headers.slice(0, 5).join(', ')}{filePreviewStats.headers.length > 5 ? ` +${filePreviewStats.headers.length - 5} more` : ''}
                      </p>
                    </div>
                  </div>
                  <Badge className="bg-emerald-200/80 text-emerald-900 border-emerald-300 text-[11px] font-semibold self-start sm:self-auto">
                    Ready for Range Assignment
                  </Badge>
                </div>
              )}

              {/* Assignment Method Settings */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3">
                <div className="flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-600" />
                  <span className="font-bold text-slate-900">Lead Assignment to Sales Persons</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {/* Option 1: Row Ranges & Split */}
                  <div
                    onClick={() => setImportAssignmentMethod('row_ranges')}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all sm:col-span-2 ${importAssignmentMethod === 'row_ranges' ? 'bg-white border-emerald-500 ring-2 ring-emerald-200 shadow-sm' : 'bg-white/60 border-slate-200 hover:border-slate-300'}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          checked={importAssignmentMethod === 'row_ranges'}
                          onChange={() => setImportAssignmentMethod('row_ranges')}
                          className="text-emerald-600 focus:ring-emerald-500"
                        />
                        <span className="font-bold text-slate-900 text-xs">Assign by Row Ranges / Split by Range</span>
                      </div>
                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                        ⭐ Recommended for Bulk
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 pl-5">
                      Assign custom row ranges to different Sales Persons (e.g. Rows 1–100 to Rep A, 101–200 to Rep B), or auto-divide large spreadsheets.
                    </p>
                  </div>

                  {/* Option 2: Specific Rep */}
                  <div
                    onClick={() => setImportAssignmentMethod('specific')}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all ${importAssignmentMethod === 'specific' ? 'bg-white border-emerald-500 ring-2 ring-emerald-200 shadow-sm' : 'bg-white/60 border-slate-200 hover:border-slate-300'}`}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={importAssignmentMethod === 'specific'}
                        onChange={() => setImportAssignmentMethod('specific')}
                        className="text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="font-semibold text-slate-800 text-xs">Assign Entire Sheet to One Person</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1 pl-5">All rows in the spreadsheet will be assigned to a single selected sales representative.</p>
                  </div>

                  {/* Option 3: Round Robin */}
                  <div
                    onClick={() => setImportAssignmentMethod('round_robin')}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all ${importAssignmentMethod === 'round_robin' ? 'bg-white border-emerald-500 ring-2 ring-emerald-200 shadow-sm' : 'bg-white/60 border-slate-200 hover:border-slate-300'}`}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={importAssignmentMethod === 'round_robin'}
                        onChange={() => setImportAssignmentMethod('round_robin')}
                        className="text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="font-semibold text-slate-800 text-xs">Round-Robin Distribution</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1 pl-5">Cycles through each row and assigns sequentially across all active sales reps.</p>
                  </div>

                  {/* Option 4: Keep Unassigned */}
                  <div
                    onClick={() => setImportAssignmentMethod('unassigned')}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all sm:col-span-2 ${importAssignmentMethod === 'unassigned' ? 'bg-white border-emerald-500 ring-2 ring-emerald-200 shadow-sm' : 'bg-white/60 border-slate-200 hover:border-slate-300'}`}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={importAssignmentMethod === 'unassigned'}
                        onChange={() => setImportAssignmentMethod('unassigned')}
                        className="text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="font-semibold text-slate-800 text-xs">Keep Unassigned</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1 pl-5">Leads enter the unassigned pool for manual assignment later.</p>
                  </div>
                </div>

                {/* Specific Sales Person Dropdown */}
                {importAssignmentMethod === 'specific' && (
                  <div className="pt-2 bg-white p-3 rounded-lg border border-slate-200">
                    <label className="font-semibold text-slate-700 block mb-1 text-xs">
                      Select Target Sales Person: <span className="text-rose-500">*</span>
                    </label>
                    <Select value={importSalesPersonId} onValueChange={setImportSalesPersonId}>
                      <SelectTrigger className="bg-white border-slate-300 h-9 text-xs">
                        <SelectValue placeholder="-- Select Sales Person --" />
                      </SelectTrigger>
                      <SelectContent>
                        {salesReps && salesReps.length > 0 ? (
                          salesReps.map(rep => (
                            <SelectItem key={rep.id} value={rep.id}>
                              {rep.name} ({rep.email})
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="none" disabled>No active sales persons found</SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {/* ──────────────────────────────────────────────────────────── */}
                {/* ROW RANGE ASSIGNMENT & AUTO-SPLIT BUILDER */}
                {/* ──────────────────────────────────────────────────────────── */}
                {importAssignmentMethod === 'row_ranges' && (
                  <div className="space-y-3 pt-1">
                    {/* Coverage & Range Tools Header */}
                    <div className="bg-white p-3 rounded-xl border border-emerald-200 shadow-sm space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                        <div>
                          <p className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                            <SlidersHorizontal className="w-4 h-4 text-emerald-600" />
                            Row Range Allocation & Split Tools
                          </p>
                          <p className="text-[11px] text-slate-500">
                            Configure row segments to assign to different sales persons.
                          </p>
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setShowSplitPanel(!showSplitPanel)}
                          className={`h-7 text-xs font-semibold gap-1.5 ${showSplitPanel ? 'bg-emerald-50 text-emerald-700 border-emerald-300' : 'text-slate-700'}`}
                        >
                          <Split className="w-3.5 h-3.5 text-emerald-600" />
                          {showSplitPanel ? 'Hide Split Tools' : '⚡ Quick Auto-Split / Divide'}
                        </Button>
                      </div>

                      {/* Coverage Progress Bar */}
                      {(() => {
                        const total = filePreviewStats.total_rows || 0;
                        const covered = rowRanges.reduce((acc, r) => {
                          const f = parseInt(r.from_row, 10);
                          const t = parseInt(r.to_row, 10);
                          return acc + (f && t && t >= f ? (t - f + 1) : 0);
                        }, 0);
                        const pct = total > 0 ? Math.min(100, Math.round((covered / total) * 100)) : 0;
                        return (
                          <div className="space-y-1.5 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-medium text-slate-700">
                                Allocated Rows Coverage: <strong className="text-emerald-700 font-bold">{covered}</strong> / {total || '?'} rows
                              </span>
                              {total > 0 && (
                                <Badge className={covered === total ? 'bg-emerald-100 text-emerald-800' : covered > total ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'}>
                                  {covered === total ? '✓ Full 100% Coverage' : covered > total ? '⚠️ Overlapping / Exceeding Rows' : `${pct}% Covered (${total - covered} unassigned)`}
                                </Badge>
                              )}
                            </div>
                            {total > 0 && (
                              <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all ${covered === total ? 'bg-emerald-600' : covered > total ? 'bg-rose-500' : 'bg-amber-500'}`}
                                  style={{ width: `${Math.min(100, pct)}%` }}
                                />
                              </div>
                            )}
                          </div>
                        );
                      })()}

                      {/* Auto Split / Divide Panel */}
                      {showSplitPanel && (
                        <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3 space-y-3 animate-in fade-in duration-200">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                              <Layers className="w-3.5 h-3.5 text-emerald-600" />
                              Auto Split & Divide Tools
                            </span>
                            <div className="flex gap-1">
                              <button
                                type="button"
                                onClick={() => setSplitToolTab('equal')}
                                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${splitToolTab === 'equal' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white text-slate-600 border border-slate-200'}`}
                              >
                                Divide Equally Across Reps
                              </button>
                              <button
                                type="button"
                                onClick={() => setSplitToolTab('batch')}
                                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${splitToolTab === 'batch' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white text-slate-600 border border-slate-200'}`}
                              >
                                Divide by Batch Size
                              </button>
                            </div>
                          </div>

                          {splitToolTab === 'equal' ? (
                            <div className="space-y-2.5 bg-white p-3 rounded-lg border border-emerald-200">
                              <div className="flex items-center justify-between">
                                <label className="text-[11px] font-bold text-slate-700">
                                  Select Sales Persons to Split Leads Among: ({splitSelectedReps.length} selected)
                                </label>
                                <div className="flex gap-1.5">
                                  <button
                                    type="button"
                                    onClick={() => setSplitSelectedReps(salesReps.map(r => r.id))}
                                    className="text-[10px] text-emerald-700 font-semibold hover:underline"
                                  >
                                    Select All
                                  </button>
                                  <span className="text-slate-300">|</span>
                                  <button
                                    type="button"
                                    onClick={() => setSplitSelectedReps([])}
                                    className="text-[10px] text-slate-500 hover:underline"
                                  >
                                    Clear
                                  </button>
                                </div>
                              </div>

                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-36 overflow-y-auto p-1">
                                {salesReps.map(rep => {
                                  const isSel = splitSelectedReps.includes(rep.id);
                                  return (
                                    <div
                                      key={rep.id}
                                      onClick={() => {
                                        if (isSel) {
                                          setSplitSelectedReps(splitSelectedReps.filter(id => id !== rep.id));
                                        } else {
                                          setSplitSelectedReps([...splitSelectedReps, rep.id]);
                                        }
                                      }}
                                      className={`p-1.5 px-2 rounded-md border flex items-center justify-between cursor-pointer text-xs transition-all ${isSel ? 'bg-emerald-50 border-emerald-400 text-emerald-950 font-semibold' : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'}`}
                                    >
                                      <span className="truncate">{rep.name}</span>
                                      <input
                                        type="checkbox"
                                        checked={isSel}
                                        readOnly
                                        className="text-emerald-600 rounded pointer-events-none"
                                      />
                                    </div>
                                  );
                                })}
                              </div>

                              <Button
                                type="button"
                                size="sm"
                                disabled={splitSelectedReps.length === 0 || (filePreviewStats.total_rows || 0) <= 0}
                                onClick={handleAutoSplitEqually}
                                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-8 gap-1.5"
                              >
                                <Split className="w-3.5 h-3.5" /> Divide {filePreviewStats.total_rows || 0} Leads Equally Across {splitSelectedReps.length} Reps
                              </Button>
                            </div>
                          ) : (
                            <div className="space-y-2.5 bg-white p-3 rounded-lg border border-emerald-200">
                              <div className="flex items-center gap-3">
                                <div className="flex-1">
                                  <label className="text-[11px] font-bold text-slate-700 block mb-1">
                                    Number of Leads per Batch / Rep:
                                  </label>
                                  <Input
                                    type="number"
                                    min="1"
                                    value={splitBatchSize}
                                    onChange={(e) => setSplitBatchSize(e.target.value)}
                                    className="h-8 text-xs font-mono"
                                    placeholder="e.g. 50, 100, 200"
                                  />
                                </div>
                                <div className="text-[11px] text-slate-500 pt-4">
                                  Estimated: {filePreviewStats.total_rows > 0 ? Math.ceil(filePreviewStats.total_rows / (parseInt(splitBatchSize, 10) || 1)) : 0} batch ranges
                                </div>
                              </div>

                              <Button
                                type="button"
                                size="sm"
                                disabled={(filePreviewStats.total_rows || 0) <= 0 || !splitBatchSize}
                                onClick={handleAutoSplitByBatchSize}
                                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-8 gap-1.5"
                              >
                                <Layers className="w-3.5 h-3.5" /> Generate Batches of {splitBatchSize} Leads
                              </Button>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Row Ranges Table */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-800 text-xs">
                            Configured Row Ranges ({rowRanges.length})
                          </span>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={addRangeRow}
                            className="h-7 text-xs font-semibold text-emerald-700 border-emerald-300 hover:bg-emerald-50 gap-1"
                          >
                            <Plus className="w-3.5 h-3.5" /> Add Row Range
                          </Button>
                        </div>

                        <div className="border border-slate-200 rounded-xl overflow-hidden bg-white">
                          <div className="grid grid-cols-12 gap-2 bg-slate-100 p-2 text-[11px] font-bold text-slate-600 border-b border-slate-200">
                            <div className="col-span-1 text-center">#</div>
                            <div className="col-span-2">From Row</div>
                            <div className="col-span-2">To Row</div>
                            <div className="col-span-2 text-center">Leads Count</div>
                            <div className="col-span-4">Assign To Sales Person</div>
                            <div className="col-span-1 text-center">Action</div>
                          </div>

                          <div className="divide-y divide-slate-100 max-h-56 overflow-y-auto">
                            {rowRanges.map((rng, idx) => {
                              const f = parseInt(rng.from_row, 10) || 0;
                              const t = parseInt(rng.to_row, 10) || 0;
                              const count = Math.max(0, t - f + 1);
                              const isInvalid = !f || !t || t < f;

                              return (
                                <div key={rng.id || idx} className={`grid grid-cols-12 gap-2 p-2 items-center text-xs ${isInvalid ? 'bg-rose-50/60' : 'hover:bg-slate-50'}`}>
                                  <div className="col-span-1 text-center font-mono font-bold text-slate-500">
                                    #{idx + 1}
                                  </div>

                                  <div className="col-span-2">
                                    <Input
                                      type="number"
                                      min="1"
                                      value={rng.from_row}
                                      onChange={(e) => updateRangeRow(rng.id, 'from_row', e.target.value)}
                                      className="h-8 text-xs font-mono"
                                      placeholder="From"
                                    />
                                  </div>

                                  <div className="col-span-2">
                                    <Input
                                      type="number"
                                      min="1"
                                      value={rng.to_row}
                                      onChange={(e) => updateRangeRow(rng.id, 'to_row', e.target.value)}
                                      className="h-8 text-xs font-mono"
                                      placeholder="To"
                                    />
                                  </div>

                                  <div className="col-span-2 text-center">
                                    <Badge className={isInvalid ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-800 font-mono text-[11px]'}>
                                      {isInvalid ? 'Invalid' : `${count} leads`}
                                    </Badge>
                                  </div>

                                  <div className="col-span-4">
                                    <Select
                                      value={rng.sales_person_id || ''}
                                      onValueChange={(val) => updateRangeRow(rng.id, 'sales_person_id', val)}
                                    >
                                      <SelectTrigger className={`h-8 text-xs bg-white ${!rng.sales_person_id ? 'border-amber-400 bg-amber-50/40 text-amber-900' : 'border-slate-300'}`}>
                                        <SelectValue placeholder="-- Assign Sales Person --" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {salesReps && salesReps.length > 0 ? (
                                          salesReps.map(rep => (
                                            <SelectItem key={rep.id} value={rep.id}>
                                              {rep.name} ({rep.email})
                                            </SelectItem>
                                          ))
                                        ) : (
                                          <SelectItem value="none" disabled>No active sales persons</SelectItem>
                                        )}
                                      </SelectContent>
                                    </Select>
                                  </div>

                                  <div className="col-span-1 text-center">
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => removeRangeRow(rng.id)}
                                      className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                                      title="Remove Range"
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </Button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Import Results Summary Card */}
              {importResults && (
                <div className="p-3.5 bg-slate-900 text-white rounded-xl space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-bold flex items-center gap-1.5 text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" /> Import Complete
                    </span>
                    <span className="text-slate-400 text-[11px]">Total Processed: {importResults.total_records || importResults.total_rows || (importResults.imported_count + importResults.duplicate_count + importResults.invalid_count)}</span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-emerald-950/60 border border-emerald-800/60 p-2 rounded-lg">
                      <p className="text-lg font-bold text-emerald-400">{importResults.imported_count}</p>
                      <p className="text-[10px] text-emerald-200 uppercase tracking-wider font-semibold">Imported</p>
                    </div>
                    <div className="bg-amber-950/60 border border-amber-800/60 p-2 rounded-lg">
                      <p className="text-lg font-bold text-amber-400">{importResults.duplicate_count}</p>
                      <p className="text-[10px] text-amber-200 uppercase tracking-wider font-semibold">Duplicates</p>
                    </div>
                    <div className="bg-rose-950/60 border border-rose-800/60 p-2 rounded-lg">
                      <p className="text-lg font-bold text-rose-400">{importResults.invalid_count}</p>
                      <p className="text-[10px] text-rose-200 uppercase tracking-wider font-semibold">Invalid</p>
                    </div>
                  </div>

                  {importResults.assigned_summary && Object.keys(importResults.assigned_summary).length > 0 && (
                    <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700 text-xs">
                      <p className="font-semibold text-slate-300 mb-1.5 text-[11px]">Sales Person Distribution:</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(importResults.assigned_summary).map(([rep, count]) => (
                          <span key={rep} className="bg-slate-700 text-slate-200 px-2 py-0.5 rounded text-[11px] font-mono">
                            {rep}: <strong className="text-emerald-400">{count} leads</strong>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {importResults.errors && importResults.errors.length > 0 && (
                    <div className="text-[11px] text-rose-300 bg-rose-950/40 p-2 rounded border border-rose-900/50 max-h-24 overflow-y-auto font-mono">
                      {importResults.errors.map((err, i) => (
                        <p key={i}>• {err}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <DialogFooter className="mt-4 flex sm:justify-between items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => { setShowImportModal(false); setImportResults(null); }}
                className="text-xs"
              >
                Close
              </Button>
              <Button
                type="button"
                disabled={
                  importUploading ||
                  (importMode === 'file' && !importFile) ||
                  (importMode === 'paste' && !importCsvText.trim()) ||
                  (importAssignmentMethod === 'specific' && !importSalesPersonId) ||
                  (importAssignmentMethod === 'row_ranges' && (!rowRanges || rowRanges.length === 0 || rowRanges.some(r => !r.sales_person_id)))
                }
                onClick={handleBulkImportSubmit}
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center gap-1.5"
              >
                {importUploading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Processing Import...
                  </>
                ) : (
                  <>
                    <Upload className="w-3.5 h-3.5" /> Start Bulk Import & Assign
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* WhatsApp Cloud API & Webhook Configuration Modal */}
      <WhatsAppConfigModal
        isOpen={showWhatsAppConfigModal}
        onClose={() => setShowWhatsAppConfigModal(false)}
        onSaved={() => {
          if (selectedLead?.id) {
            loadLeadWhatsApp(selectedLead.id);
            loadWhatsAppSessionStatus(selectedLead.id);
          }
          loadWhatsAppInbox();
        }}
      />

      {/* Partner Performance Report Modal (Pipeline Cockpit Integration) */}
      <Dialog open={showPartnerReportModal} onOpenChange={setShowPartnerReportModal}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold text-slate-900">
              <FileText className="w-5 h-5 text-indigo-600" /> Partner & Referral Performance Report
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Comprehensive report of partner conversions, fee collections, commissions, and pending receivables.
            </DialogDescription>
          </DialogHeader>

          {loadingPartnerReport ? (
            <div className="py-12 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-indigo-600" /> Loading partner report...
            </div>
          ) : partnerReportData ? (
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] text-slate-400 block font-medium uppercase">Total Sales / PAs</span>
                  <span className="text-lg font-bold text-slate-900">{partnerReportData.total_sales || 0}</span>
                </div>
                <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                  <span className="text-[10px] text-emerald-600 block font-medium uppercase">Total Revenue</span>
                  <span className="text-lg font-bold text-emerald-900">₹{(partnerReportData.total_revenue || 0).toLocaleString('en-IN')}</span>
                </div>
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <span className="text-[10px] text-blue-600 block font-medium uppercase">Received Amount</span>
                  <span className="text-lg font-bold text-blue-900">₹{(partnerReportData.total_received || 0).toLocaleString('en-IN')}</span>
                </div>
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <span className="text-[10px] text-amber-600 block font-medium uppercase">Pending Amount</span>
                  <span className="text-lg font-bold text-amber-900">₹{(partnerReportData.total_pending || 0).toLocaleString('en-IN')}</span>
                </div>
              </div>

              {Array.isArray(partnerReportData.sales) && partnerReportData.sales.length > 0 ? (
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-slate-500 uppercase font-semibold text-[10px] border-b border-slate-200">
                      <tr>
                        <th className="p-2.5 pl-3">Client</th>
                        <th className="p-2.5">Partner</th>
                        <th className="p-2.5">Product</th>
                        <th className="p-2.5">Fee</th>
                        <th className="p-2.5">Received</th>
                        <th className="p-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {partnerReportData.sales.slice(0, 50).map((s, idx) => (
                        <tr key={s.id || idx} className="hover:bg-slate-50">
                          <td className="p-2.5 pl-3 font-semibold text-slate-900">{s.client_name}</td>
                          <td className="p-2.5 text-slate-600">{s.partner_name}</td>
                          <td className="p-2.5 text-slate-600">{s.product_name}</td>
                          <td className="p-2.5 font-bold text-slate-800">₹{Number(s.fee_amount || 0).toLocaleString('en-IN')}</td>
                          <td className="p-2.5 text-emerald-700 font-semibold">₹{Number(s.amount_received || 0).toLocaleString('en-IN')}</td>
                          <td className="p-2.5">
                            <Badge className={`text-[10px] font-semibold ${s.status === 'approved' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                              {s.status}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-6 text-center text-slate-400">No partner sales records found.</div>
              )}
            </div>
          ) : null}

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShowPartnerReportModal(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}