/**
 * Upgraded Centralized Integrations Hub for LEAMSS CRM
 * Multi-company support for:
 * - Lead Capture & Ads: Google Ads, Facebook Lead Ads, Instagram, LinkedIn, Google Sheets, Zoho, Apollo, HubSpot, ActiveCampaign
 * - Communication & Meetings: WhatsApp Business API, Google Gmail, Google Calendar & Meet, Calendly, Zoom, Slack
 * - Payments & Billing: Razorpay, Cashfree, PayPal, QuickBooks
 * - Storage & Docs: Google Drive
 * - Analytics & SEO: Google Analytics 4, Google Search Console
 * - Automation & APIs: Zapier, Make, Custom REST API, Webhooks
 * - AI Tools: LEAMSS AI Lead Assistant
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import {
  ArrowLeft, RefreshCw, CheckCircle2, AlertCircle, Plus, Copy, Check,
  Link2, Unlink, Settings2, Shield, Users, Database, FileSpreadsheet,
  Mail, Calendar, Instagram, Facebook, Globe, Play, ExternalLink,
  HelpCircle, Eye, EyeOff, Layers, Building2, Sliders, ShieldCheck,
  Search, Download, Upload, CreditCard, DollarSign, MessageSquare,
  Video, Share2, Sparkles, Code2, Webhook, Bot, HardDrive, BarChart3,
  TrendingUp, Zap, Linkedin, Slack, FileText, ChevronRight, Filter, Clock, GitPullRequest, XCircle
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const CATEGORIES = [
  { id: 'all', label: 'All Platforms' },
  { id: 'lead_capture', label: 'Lead Capture & Ads' },
  { id: 'communication', label: 'Communication & Meetings' },
  { id: 'payments', label: 'Payments & Billing' },
  { id: 'storage', label: 'Storage & Docs' },
  { id: 'analytics', label: 'Analytics & SEO' },
  { id: 'automation', label: 'Automation & APIs' },
  { id: 'ai', label: 'AI Tools' },
];

const PROVIDER_METADATA = {
  // ── Lead Capture & Marketing ─────────────────────────────
  zoho: {
    key: 'zoho',
    name: 'Zoho CRM & Forms',
    category: 'lead_capture',
    icon: Database,
    color: 'bg-red-500',
    badgeColor: 'bg-red-50 text-red-700 border-red-200',
    tagline: 'Sync leads & deals bi-directionally with Zoho CRM and capture Zoho form submissions in real time.',
    statusType: 'connect'
  },
  google_sheets: {
    key: 'google_sheets',
    name: 'Google Sheets',
    category: 'lead_capture',
    icon: FileSpreadsheet,
    color: 'bg-emerald-600',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    tagline: 'Continuously ingest new spreadsheet rows as CRM leads and export closed deals back to your team sheet.',
    statusType: 'connect'
  },
  google_ads: {
    key: 'google_ads',
    name: 'Google Ads',
    category: 'lead_capture',
    icon: Sparkles,
    color: 'bg-amber-500',
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    tagline: 'Capture lead form extension submissions and sync offline conversion stages back to Google Ads.',
    statusType: 'connect'
  },
  facebook: {
    key: 'facebook',
    name: 'Meta Ads (Facebook)',
    category: 'lead_capture',
    icon: Facebook,
    color: 'bg-blue-700',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    tagline: 'Capture instant lead submissions from Facebook Lead Ad campaigns into the sales pipeline with zero delay.',
    statusType: 'connect'
  },
  instagram: {
    key: 'instagram',
    name: 'Instagram Lead Generation',
    category: 'lead_capture',
    icon: Instagram,
    color: 'bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600',
    badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    tagline: 'Route enquiries and Instagram story/feed lead ads instantly to your company sales executives.',
    statusType: 'connect'
  },
  linkedin: {
    key: 'linkedin',
    name: 'LinkedIn Lead Gen Forms',
    category: 'lead_capture',
    icon: Linkedin,
    color: 'bg-blue-600',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    tagline: 'Sync high-intent professional and skilled visa inquiries directly from LinkedIn Sponsored Content forms.',
    statusType: 'connect'
  },
  apollo: {
    key: 'apollo',
    name: 'Apollo.io Leads',
    category: 'lead_capture',
    icon: Zap,
    color: 'bg-yellow-500',
    badgeColor: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    tagline: 'Source verified B2B contacts and institutional migration leads from Apollo data search.',
    statusType: 'request_tool'
  },
  hubspot: {
    key: 'hubspot',
    name: 'HubSpot CRM',
    category: 'lead_capture',
    icon: Share2,
    color: 'bg-orange-600',
    badgeColor: 'bg-orange-50 text-orange-700 border-orange-200',
    tagline: 'Sync marketing contacts, email subscription activity, and pipeline deals with HubSpot.',
    statusType: 'request_tool'
  },
  activecampaign: {
    key: 'activecampaign',
    name: 'ActiveCampaign',
    category: 'lead_capture',
    icon: ChevronRight,
    color: 'bg-blue-600',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    tagline: 'Automate marketing email nurture sequences and trigger CRM updates based on lead engagement.',
    statusType: 'request_tool'
  },

  // ── Communication & Meetings ──────────────────────────────
  whatsapp_business: {
    key: 'whatsapp_business',
    name: 'WhatsApp Business API',
    category: 'communication',
    icon: MessageSquare,
    color: 'bg-emerald-600',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    tagline: 'Official Meta WhatsApp Cloud API for automated lead replies, template notifications, and 2-way chat.',
    statusType: 'connect'
  },
  google_gmail: {
    key: 'google_gmail',
    name: 'Google Gmail',
    category: 'communication',
    icon: Mail,
    color: 'bg-rose-500',
    badgeColor: 'bg-rose-50 text-rose-700 border-rose-200',
    tagline: 'Sync client email threads, track incoming enquiries, and send messages directly through company Gmail.',
    statusType: 'connect'
  },
  google_calendar: {
    key: 'google_calendar',
    name: 'Google Calendar & Meet',
    category: 'communication',
    icon: Calendar,
    color: 'bg-blue-600',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    tagline: 'Schedule consultations with auto-generated Google Meet video links synced directly with Google Calendar.',
    statusType: 'connect'
  },
  calendly: {
    key: 'calendly',
    name: 'Calendly Appointments',
    category: 'communication',
    icon: Clock,
    color: 'bg-sky-500',
    badgeColor: 'bg-sky-50 text-sky-700 border-sky-200',
    tagline: 'Embed online scheduling widgets and automatically capture booking details into CRM leads.',
    statusType: 'connect'
  },
  zoom: {
    key: 'zoom',
    name: 'Zoom Video Consultations',
    category: 'communication',
    icon: Video,
    color: 'bg-blue-500',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    tagline: 'Auto-create Zoom meeting rooms for client assessments and log attendance timestamps.',
    statusType: 'connect'
  },
  slack: {
    key: 'slack',
    name: 'Slack Alerts',
    category: 'communication',
    icon: Slack,
    color: 'bg-purple-600',
    badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    tagline: 'Broadcast instant notifications to #sales-leads channels when high-intent or converted deals arrive.',
    statusType: 'connect'
  },

  // ── Payments & Invoicing ─────────────────────────────────
  razorpay: {
    key: 'razorpay',
    name: 'Razorpay Payment Gateway',
    category: 'payments',
    icon: CreditCard,
    color: 'bg-blue-600',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    tagline: 'Collect retainer fees, pre-assessment charges, and installments via UPI, cards, and NetBanking.',
    statusType: 'connect'
  },
  cashfree: {
    key: 'cashfree',
    name: 'Cashfree Payments',
    category: 'payments',
    icon: DollarSign,
    color: 'bg-violet-600',
    badgeColor: 'bg-violet-50 text-violet-700 border-violet-200',
    tagline: 'Instant payment links, auto-reconciliation, and multi-currency billing for international clients.',
    statusType: 'connect'
  },
  paypal: {
    key: 'paypal',
    name: 'PayPal International',
    category: 'payments',
    icon: DollarSign,
    color: 'bg-indigo-700',
    badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    tagline: 'Accept cross-border consultation payments in USD, AUD, CAD, and GBP from clients abroad.',
    statusType: 'connect'
  },
  quickbooks: {
    key: 'quickbooks',
    name: 'QuickBooks Accounting',
    category: 'payments',
    icon: FileText,
    color: 'bg-emerald-700',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    tagline: 'Sync client invoices, GST receipts, and payment settlements directly with your accounting books.',
    statusType: 'request_tool'
  },

  // ── Storage & Docs ───────────────────────────────────────
  google_drive: {
    key: 'google_drive',
    name: 'Google Drive Storage',
    category: 'storage',
    icon: HardDrive,
    color: 'bg-amber-600',
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    tagline: 'Organize client passports, qualification transcripts, and visa case files into dedicated Drive folders.',
    statusType: 'connect'
  },

  // ── Analytics & SEO ──────────────────────────────────────
  google_analytics: {
    key: 'google_analytics',
    name: 'Google Analytics 4',
    category: 'analytics',
    icon: BarChart3,
    color: 'bg-amber-500',
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    tagline: 'Track website visitor conversion funnels, landing page bounce rates, and lead source journeys.',
    statusType: 'connect'
  },
  google_search_console: {
    key: 'google_search_console',
    name: 'Google Search Console',
    category: 'analytics',
    icon: TrendingUp,
    color: 'bg-teal-600',
    badgeColor: 'bg-teal-50 text-teal-700 border-teal-200',
    tagline: 'Monitor organic search clicks, ranking keywords, and landing page indexing performance.',
    statusType: 'connect'
  },

  // ── Automation & APIs ────────────────────────────────────
  zapier: {
    key: 'zapier',
    name: 'Zapier Automation',
    category: 'automation',
    icon: Zap,
    color: 'bg-orange-500',
    badgeColor: 'bg-orange-50 text-orange-700 border-orange-200',
    tagline: 'Connect LEAMSS CRM to 5,000+ business apps through automated multi-step trigger zaps.',
    statusType: 'connect'
  },
  make: {
    key: 'make',
    name: 'Make.com (Integromat)',
    category: 'automation',
    icon: Layers,
    color: 'bg-purple-600',
    badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    tagline: 'Build visual automation workflows, conditional routers, and scheduled sync jobs with Make scenarios.',
    statusType: 'connect'
  },
  rest_api: {
    key: 'rest_api',
    name: 'Custom REST API',
    category: 'automation',
    icon: Code2,
    color: 'bg-slate-800',
    badgeColor: 'bg-slate-100 text-slate-800 border-slate-300',
    tagline: 'Secure REST endpoints with bearer token auth to integrate external portals, mobile apps, or custom forms.',
    statusType: 'connect'
  },
  webhooks: {
    key: 'webhooks',
    name: 'Universal Inbound Webhooks',
    category: 'automation',
    icon: Webhook,
    color: 'bg-cyan-600',
    badgeColor: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    tagline: 'Real-time JSON endpoint for receiving lead payloads from any custom landing page or third-party CRM.',
    statusType: 'connect'
  },

  // ── AI Tools ─────────────────────────────────────────────
  ai_tools: {
    key: 'ai_tools',
    name: 'LEAMSS AI Lead Assistant',
    category: 'ai',
    icon: Bot,
    color: 'bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500',
    badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    tagline: 'AI evaluation of client qualifications, automated lead scoring, and instant personalized sales proposals.',
    statusType: 'connect'
  },

  // ── Other Requestable ────────────────────────────────────
  odoo: {
    key: 'odoo',
    name: 'Odoo ERP',
    category: 'lead_capture',
    icon: Building2,
    color: 'bg-purple-700',
    badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    tagline: 'ERP connector for enterprise clients and multi-branch operations management.',
    statusType: 'request_tool'
  }
};

export default function IntegrationsHub() {
  const navigate = useNavigate();
  const [companies, setCompanies] = useState([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState('');
  const [integrations, setIntegrations] = useState([]);
  const [salesReps, setSalesReps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState(null);
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [activeProvider, setActiveProvider] = useState(null);
  const [editingIntegration, setEditingIntegration] = useState(null);
  const [newCompanyModalOpen, setNewCompanyModalOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyDomain, setNewCompanyDomain] = useState('');
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [logs, setLogs] = useState([]);
  const [testLeadModalOpen, setTestLeadModalOpen] = useState(false);
  const [aiResultModalOpen, setAiResultModalOpen] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [requestData, setRequestData] = useState({
    tool_name: '',
    category: 'lead_capture',
    use_case: '',
    priority: 'medium'
  });
  const [submittingRequest, setSubmittingRequest] = useState(false);
  const [requestsCount, setRequestsCount] = useState(0);
  const [integrationRequests, setIntegrationRequests] = useState([]);

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    credentials: {},
    lead_assignment_rules: {
      mode: 'round_robin',
      rep_ids: [],
      specific_rep_id: '',
      default_tags: [],
      default_service: 'Immigration & Visa Consultation'
    },
    duplicate_prevention: {
      strategy: 'skip',
      match_fields: ['phone', 'email', 'whatsapp_number']
    },
    sync_settings: {
      auto_sync: true,
      direction: 'inbound'
    }
  });

  const [testLeadData, setTestLeadData] = useState({
    name: 'Test Lead from Integration',
    email: 'test.integration@example.com',
    phone: '+919988776655',
    city: 'Mumbai',
    country: 'Canada',
    service_interested: 'Canada Express Entry',
    message: 'Simulated lead enquiry for verifying duplicate detection and assignment rules.'
  });

  const [copiedKey, setCopiedKey] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);

  const token = localStorage.getItem('token');
  const authHeaders = useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);

  // Copy helper
  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // 1. Fetch Companies
  const fetchCompanies = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/integrations/companies`, authHeaders);
      setCompanies(res.data || []);
      if (res.data?.length > 0 && !selectedCompanyId) {
        setSelectedCompanyId(res.data[0].id);
      }
    } catch (e) {
      toast.error('Failed to load companies');
    }
  }, [authHeaders, selectedCompanyId]);

  // 2. Fetch Integrations for selected Company
  const fetchIntegrations = useCallback(async () => {
    if (!selectedCompanyId) return;
    setLoading(true);
    try {
      const [integRes, repsRes] = await Promise.all([
        axios.get(`${API}/integrations?company_id=${selectedCompanyId}`, authHeaders),
        axios.get(`${API}/users?status=active`, authHeaders).catch(() => ({ data: [] }))
      ]);
      setIntegrations(integRes.data || []);
      // Filter sales reps
      const reps = (repsRes.data || []).filter(u =>
        ['partner', 'sales_executive', 'sales_rep', 'sales_person', 'sales', 'internal_salesperson'].includes(u.role) ||
        ['partner', 'sales_executive', 'sales_rep', 'sales_person', 'sales', 'internal_salesperson'].includes(u.rbac_role)
      );
      setSalesReps(reps);
    } catch (e) {
      toast.error('Failed to load integrations');
    } finally {
      setLoading(false);
    }
  }, [selectedCompanyId, authHeaders]);

  const fetchRequestsCount = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/integrations/requests`, authHeaders);
      if (res.data?.success) {
        setIntegrationRequests(res.data.requests || []);
        if (res.data?.counts) {
          setRequestsCount(res.data.counts.total || 0);
        }
      }
    } catch (e) {
      // quiet fail for counter
    }
  }, [authHeaders]);

  const getProviderRequest = useCallback((providerKey, providerName) => {
    if (!integrationRequests || integrationRequests.length === 0) return null;
    const normKey = (providerKey || '').toLowerCase().replace(/^custom_/, '').replace(/[^a-z0-9]/g, '');
    const normName = (providerName || '').toLowerCase().replace(/[^a-z0-9]/g, '');

    return integrationRequests.find(r => {
      const rTool = (r.tool_name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
      if (!rTool) return false;
      return (
        rTool === normKey ||
        rTool === normName ||
        rTool.includes(normKey) ||
        normName.includes(rTool) ||
        (normKey.includes('apollo') && rTool.includes('apollo')) ||
        (normKey.includes('hubspot') && rTool.includes('hubspot')) ||
        (normKey.includes('activecampaign') && rTool.includes('activecampaign')) ||
        (normKey.includes('quickbooks') && rTool.includes('quickbooks')) ||
        (normKey.includes('odoo') && rTool.includes('odoo'))
      );
    });
  }, [integrationRequests]);

  // Compute dynamic custom providers from approved integration requests + connected custom integrations
  const customProviders = useMemo(() => {
    const builtInKeys = new Set(Object.keys(PROVIDER_METADATA).map(k => k.toLowerCase().replace(/[^a-z0-9]/g, '')));
    const builtInNames = new Set(Object.values(PROVIDER_METADATA).map(p => p.name.toLowerCase().replace(/[^a-z0-9]/g, '')));

    const customList = [];
    const seenKeys = new Set();

    // 1. From integration requests (approved or requested)
    if (integrationRequests && integrationRequests.length > 0) {
      // Sort so 'approved' requests come first
      const sortedRequests = [...integrationRequests].sort((a, b) => {
        if (a.status === 'approved' && b.status !== 'approved') return -1;
        if (b.status === 'approved' && a.status !== 'approved') return 1;
        return 0;
      });

      for (const req of sortedRequests) {
        if (!req.tool_name) continue;
        const normName = req.tool_name.toLowerCase().replace(/[^a-z0-9]/g, '');
        if (builtInKeys.has(normName) || builtInNames.has(normName)) {
          continue; // matches a built-in provider
        }
        const customKey = `custom_${normName}`;
        if (seenKeys.has(customKey)) {
          continue;
        }
        seenKeys.add(customKey);

        customList.push({
          key: customKey,
          name: req.tool_name,
          category: req.category || 'lead_capture',
          icon: Sparkles,
          color: 'bg-gradient-to-tr from-indigo-500 to-purple-600',
          badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
          tagline: req.use_case || `Approved integration connector for ${req.tool_name}. Configure API credentials to link with LEAMSS CRM.`,
          statusType: 'connect',
          isCustom: true,
          requestId: req.id,
          requestStatus: req.status || 'approved'
        });
      }
    }

    // 2. From connected custom integrations in database
    if (integrations && integrations.length > 0) {
      for (const integ of integrations) {
        if (!integ.provider) continue;
        const normKey = integ.provider.toLowerCase().replace(/^custom_/, '').replace(/[^a-z0-9]/g, '');
        if (builtInKeys.has(normKey) || builtInNames.has(normKey)) {
          continue;
        }
        const customKey = integ.provider.startsWith('custom_') ? integ.provider : `custom_${normKey}`;
        if (seenKeys.has(customKey)) {
          continue;
        }
        seenKeys.add(customKey);

        customList.push({
          key: customKey,
          name: integ.name || normKey.toUpperCase(),
          category: integ.category || 'lead_capture',
          icon: Sparkles,
          color: 'bg-gradient-to-tr from-emerald-500 to-teal-600',
          badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          tagline: `Configured integration connector for ${integ.name || normKey}.`,
          statusType: 'connect',
          isCustom: true,
          requestId: integ.request_id
        });
      }
    }

    return customList;
  }, [integrationRequests, integrations]);

  // Combined providers list (built-in + custom approved/requested)
  const allProviders = useMemo(() => {
    return [...Object.values(PROVIDER_METADATA), ...customProviders];
  }, [customProviders]);

  // Safe provider metadata lookup
  const getProviderMeta = useCallback((key) => {
    if (!key) return null;
    return allProviders.find(p => p.key === key) || PROVIDER_METADATA[key] || {
      key,
      name: key.replace(/^custom_/, '').toUpperCase(),
      category: 'lead_capture',
      icon: Sparkles,
      color: 'bg-indigo-600',
      badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
      tagline: `Integration connector for ${key}.`,
      statusType: 'connect'
    };
  }, [allProviders]);

  // Enforce Admin-only access to Integrations Hub
  useEffect(() => {
    const checkAdmin = async () => {
      try {
        const res = await axios.get(`${API}/auth/me`, authHeaders);
        const role = String(res.data?.rbac_role || res.data?.role || '').toLowerCase();
        if (!['admin', 'admin_owner', 'super_admin'].includes(role)) {
          toast.error('Access denied — Integrations Hub is restricted exclusively to Administrators.');
          navigate('/sales/my-crm');
        }
      } catch {
        navigate('/');
      }
    };
    if (token) {
      checkAdmin();
    } else {
      navigate('/');
    }
  }, [token, authHeaders, navigate]);

  useEffect(() => {
    fetchCompanies();
    fetchRequestsCount();
  }, [fetchCompanies, fetchRequestsCount]);

  useEffect(() => {
    if (selectedCompanyId) {
      fetchIntegrations();
    }
  }, [selectedCompanyId, fetchIntegrations]);

  // Handle Open Connect / Edit Modal
  const handleOpenConfig = (providerKey, providerObj = null) => {
    setActiveProvider(providerKey);
    const meta = providerObj || getProviderMeta(providerKey);
    const existing = integrations.find(i => i.provider === providerKey);

    if (existing) {
      setEditingIntegration(existing);
      setFormData({
        id: existing.id,
        name: existing.name || meta?.name || providerKey,
        credentials: existing.credentials || {},
        lead_assignment_rules: existing.lead_assignment_rules || {
          mode: 'round_robin',
          rep_ids: [],
          specific_rep_id: '',
          default_tags: [providerKey],
          default_service: 'Immigration & Visa Consultation'
        },
        duplicate_prevention: existing.duplicate_prevention || {
          strategy: 'skip',
          match_fields: ['phone', 'email', 'whatsapp_number']
        },
        sync_settings: existing.sync_settings || {
          auto_sync: true,
          direction: 'inbound'
        }
      });
    } else {
      setEditingIntegration(null);
      setFormData({
        name: meta?.name || providerKey,
        credentials: {},
        lead_assignment_rules: {
          mode: 'round_robin',
          rep_ids: salesReps.map(r => r.id),
          specific_rep_id: salesReps[0]?.id || '',
          default_tags: [providerKey],
          default_service: 'Immigration & Visa Consultation'
        },
        duplicate_prevention: {
          strategy: 'skip',
          match_fields: ['phone', 'email', 'whatsapp_number']
        },
        sync_settings: {
          auto_sync: true,
          direction: 'inbound'
        }
      });
    }
    setConfigModalOpen(true);
  };

  // Open Request Modal
  const handleOpenRequest = (providerKey = null) => {
    if (providerKey && PROVIDER_METADATA[providerKey]) {
      const p = PROVIDER_METADATA[providerKey];
      setRequestData({
        tool_name: p.name,
        category: p.category || 'lead_capture',
        use_case: `Need ${p.name} integration for automated workflow.`,
        priority: 'high'
      });
    } else {
      setRequestData({
        tool_name: '',
        category: 'lead_capture',
        use_case: '',
        priority: 'medium'
      });
    }
    setRequestModalOpen(true);
  };

  const handleSubmitRequest = async () => {
    if (!requestData.tool_name.trim()) {
      toast.error('Please enter a tool or platform name');
      return;
    }
    setSubmittingRequest(true);
    try {
      const res = await axios.post(`${API}/integrations/requests`, {
        ...requestData,
        company_id: selectedCompanyId
      }, authHeaders);

      // Verify response success and database ID before showing success message
      if (res.data?.success && res.data?.id) {
        toast.success(`Request for "${requestData.tool_name}" saved to database and submitted to CRM Engineering!`);
        setRequestModalOpen(false);
        fetchRequestsCount();
      } else {
        toast.error(res.data?.message || 'Failed to save request to database.');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to submit request to database. Please check connection and try again.');
    } finally {
      setSubmittingRequest(false);
    }
  };

  // Save Integration
  const handleSaveIntegration = async () => {
    try {
      const meta = getProviderMeta(activeProvider);
      const existingReq = getProviderRequest(activeProvider, meta?.name);

      const payload = {
        id: editingIntegration?.id,
        company_id: selectedCompanyId,
        provider: activeProvider,
        name: formData.name || meta?.name || activeProvider,
        credentials: formData.credentials,
        lead_assignment_rules: formData.lead_assignment_rules,
        duplicate_prevention: formData.duplicate_prevention,
        sync_settings: formData.sync_settings,
        status: 'connected',
        is_custom: Boolean(meta?.isCustom || activeProvider.startsWith('custom_')),
        category: meta?.category || 'lead_capture',
        request_id: existingReq?.id || meta?.requestId
      };

      const res = await axios.post(`${API}/integrations`, payload, authHeaders);
      toast.success(res.data?.message || 'Integration saved successfully');
      setConfigModalOpen(false);
      fetchIntegrations();
      fetchRequestsCount();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save integration');
    }
  };

  // Disconnect
  const handleDisconnect = async (integrationId, providerName) => {
    if (!window.confirm(`Are you sure you want to disconnect ${providerName}? Historical leads will remain in your CRM.`)) {
      return;
    }
    try {
      await axios.delete(`${API}/integrations/${integrationId}`, authHeaders);
      toast.success(`${providerName} disconnected.`);
      fetchIntegrations();
    } catch (e) {
      toast.error('Failed to disconnect integration');
    }
  };

  // Test Connection
  const handleTestConnection = async (integrationId) => {
    setTestingConnection(true);
    try {
      const res = await axios.post(`${API}/integrations/${integrationId}/test`, {}, authHeaders);
      if (res.data?.success) {
        toast.success(res.data.message || 'Connection test successful!');
      } else {
        toast.error(res.data?.message || 'Connection test failed.');
      }
      fetchIntegrations();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Test connection request failed');
    } finally {
      setTestingConnection(false);
    }
  };

  // Manual Trigger Sync
  const handleTriggerSync = async (integrationId) => {
    setSyncingId(integrationId);
    try {
      const res = await axios.post(`${API}/integrations/${integrationId}/sync`, {}, authHeaders);
      toast.success(res.data?.message || 'Sync completed successfully');
      fetchIntegrations();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Manual sync failed');
    } finally {
      setSyncingId(null);
    }
  };

  // View Logs
  const handleViewLogs = async (integrationId) => {
    try {
      const res = await axios.get(`${API}/integrations/${integrationId}/logs`, authHeaders);
      setLogs(res.data || []);
      setLogsModalOpen(true);
    } catch (e) {
      toast.error('Failed to load execution logs');
    }
  };

  // Simulate Inbound Lead
  const handleSimulateLead = async (integrationId) => {
    try {
      const res = await axios.post(`${API}/integrations/${integrationId}/sample-lead`, testLeadData, authHeaders);
      if (res.data?.status === 'created') {
        if (res.data?.ai_qualification) {
          const q = res.data.ai_qualification;
          toast.success(`Success! Created lead ${res.data?.lead_number} [${q.category} — Score ${q.score}/100]. Matched: ${q.matched_occupation}! Proposal draft generated.`);
          setAiResult(res.data);
          setAiResultModalOpen(true);
        } else {
          toast.success(`Success! Created lead ${res.data?.lead_number} assigned to ${res.data?.assigned_to_name}`);
        }
      } else if (res.data?.status === 'skipped') {
        toast.info(`Duplicate detected: Lead skipped as per rule and note logged on existing record.`);
      } else {
        toast.success(`Processed: ${res.data?.message || 'Lead ingested'}`);
      }
      setTestLeadModalOpen(false);
      fetchIntegrations();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Simulation failed');
    }
  };

  // Download Sample CSV
  const handleDownloadSample = () => {
    window.open(`${API}/integrations/sample-file?format=csv`, '_blank');
  };

  // Filtered providers
  const filteredProviders = useMemo(() => {
    return allProviders.filter(p => {
      // Category filter
      if (activeCategory !== 'all' && p.category !== activeCategory) {
        return false;
      }
      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = (p.name || '').toLowerCase().includes(q);
        const matchesTagline = (p.tagline || '').toLowerCase().includes(q);
        const matchesKey = (p.key || '').toLowerCase().includes(q);
        if (!matchesName && !matchesTagline && !matchesKey) return false;
      }
      return true;
    });
  }, [allProviders, activeCategory, searchQuery]);

  const currentCompany = useMemo(() => {
    return companies.find(c => c.id === selectedCompanyId) || { name: 'LEAMSS Global', id: 'comp_leamss_primary' };
  }, [companies, selectedCompanyId]);

  const getWebhookUrl = (providerKey) => {
    if (providerKey === 'google_sheets') {
      return `${API}/integrations/webhooks/sheets/${selectedCompanyId}`;
    } else if (providerKey === 'zoho') {
      return `${API}/integrations/webhooks/zoho/${selectedCompanyId}`;
    } else if (['facebook', 'instagram'].includes(providerKey)) {
      return `${API}/integrations/webhooks/meta/${selectedCompanyId}`;
    } else if (providerKey === 'whatsapp_business') {
      return `${API}/integrations/webhooks/whatsapp/${selectedCompanyId}`;
    } else if (providerKey === 'linkedin') {
      return `${API}/integrations/webhooks/linkedin/${selectedCompanyId}`;
    } else if (providerKey === 'calendly') {
      return `${API}/integrations/webhooks/calendly/${selectedCompanyId}`;
    } else {
      return `${API}/integrations/webhooks/generic/${selectedCompanyId}`;
    }
  };

  const getSheetsScript = (webhookUrl) => {
    return `// ====================================================
// LEAMSS CRM — Real-Time Google Sheet Sync
// ====================================================
var LEAMSS_WEBHOOK_URL = "${webhookUrl}";

// 1. Triggers automatically when a new Google Form response is submitted
function onFormSubmit(e) {
  try {
    var payload = e && e.namedValues ? e.namedValues : {};
    sendToLeamss(payload);
  } catch (err) {
    Logger.log("Error in onFormSubmit: " + err);
  }
}

// 2. Triggers automatically when any cell is edited
function onEdit(e) {
  try {
    if (!e || !e.range) return;
    var sheet = e.range.getSheet();
    var row = e.range.getRow();
    if (row <= 1) return; // Header row
    
    var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
    var rowValues = sheet.getRange(row, 1, 1, sheet.getLastColumn()).getValues()[0];
    
    var rowData = {};
    for (var i = 0; i < headers.length; i++) {
      if (headers[i]) rowData[headers[i]] = rowValues[i];
    }
    sendToLeamss(rowData);
  } catch (err) {
    Logger.log("Error in onEdit: " + err);
  }
}

// 3. Adds menu to toolbar: 'LEAMSS CRM' > 'Sync All Rows to CRM'
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('LEAMSS CRM')
    .addItem('🚀 Sync All Rows to CRM Now', 'syncAllRowsToLeamss')
    .addToUi();
}

// 4. One-click sync all existing rows into CRM
function syncAllRowsToLeamss() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var data = sheet.getDataRange().getValues();
  if (data.length < 2) {
    SpreadsheetApp.getUi().alert('No client data rows found to sync.');
    return;
  }
  var headers = data[0];
  var rows = [];
  for (var r = 1; r < data.length; r++) {
    var rowObj = {};
    for (var c = 0; c < headers.length; c++) {
      if (headers[c]) rowObj[headers[c]] = data[r][c];
    }
    rows.push(rowObj);
  }
  
  var options = {
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify(rows),
    'muteHttpExceptions': true
  };
  var response = UrlFetchApp.fetch(LEAMSS_WEBHOOK_URL, options);
  SpreadsheetApp.getUi().alert('Sync complete! ' + rows.length + ' leads sent to LEAMSS CRM. Status: ' + response.getResponseCode());
}

function sendToLeamss(payload) {
  var options = {
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  };
  UrlFetchApp.fetch(LEAMSS_WEBHOOK_URL, options);
}`;
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* ── TOP HEADER BAR ── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/sales/my-crm')}
                className="h-8 w-8 p-0 text-slate-500 hover:text-slate-800"
                title="Return to CRM"
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
                <span>Integrations</span>
                <Badge className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300 font-semibold text-xs border-indigo-200">
                  LEAMSS Hub
                </Badge>
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 pl-11">
              Connect external advertising campaigns, spreadsheets, communication tools, and payment gateways for <span className="font-semibold text-slate-800 dark:text-slate-200">{currentCompany.name}</span>.
            </p>
          </div>

          <div className="flex items-center gap-3 pl-11 md:pl-0 flex-wrap">
            {/* Company Context Selector */}
            <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-900 p-1.5 rounded-xl border border-slate-200 dark:border-slate-700">
              <Building2 className="w-4 h-4 text-slate-400 ml-1.5" />
              <Select value={selectedCompanyId} onValueChange={setSelectedCompanyId}>
                <SelectTrigger className="w-44 h-8 text-xs border-0 bg-transparent shadow-none font-semibold focus:ring-0">
                  <SelectValue placeholder="Select Company" />
                </SelectTrigger>
                <SelectContent>
                  {companies.map(c => (
                    <SelectItem key={c.id} value={c.id} className="text-xs font-medium">
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              size="sm"
              variant="outline"
              onClick={() => navigate('/admin/integration-requests')}
              className="h-9 text-xs border-slate-200 text-slate-700 hover:bg-slate-50 font-semibold gap-1.5 shadow-xs"
              title="View all integration requests submitted by team members"
            >
              <GitPullRequest className="w-3.5 h-3.5 text-indigo-600" />
              <span>Requests</span>
              {requestsCount > 0 && (
                <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 text-[10px] px-1.5 py-0 h-4">
                  {requestsCount}
                </Badge>
              )}
            </Button>

            <Button
              size="sm"
              onClick={() => handleOpenRequest()}
              className="h-9 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" /> Request Integration
            </Button>
          </div>
        </div>

        {/* ── SEARCH & CATEGORY FILTER BAR ── */}
        <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <Input
                placeholder="Search integrations (e.g. Google Ads, WhatsApp, Razorpay, Make...)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-9 text-xs bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-700"
              />
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={fetchIntegrations}
                disabled={loading}
                className="h-9 text-xs gap-1.5 border-slate-200 text-slate-700 hover:text-emerald-700"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Status
              </Button>
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs scrollbar-none">
            {CATEGORIES.map(cat => {
              const count = cat.id === 'all'
                ? allProviders.length
                : allProviders.filter(p => p.category === cat.id).length;
              const isActive = activeCategory === cat.id;

              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-indigo-600 text-white font-semibold shadow-xs'
                      : 'bg-slate-100 hover:bg-slate-200/80 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300'
                  }`}
                >
                  <span>{cat.label}</span>
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${isActive ? 'bg-indigo-700 text-white' : 'bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200'}`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── MAIN CONTENT LAYOUT: INTEGRATIONS GRID + MANUAL CSV UPLOAD CARD ── */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">

          {/* Left Column (3 cols): Cards Grid */}
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
                Import Leads from
              </h2>
              <span className="text-xs text-slate-400">
                Showing {filteredProviders.length} tools
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredProviders.map(provider => {
                const Icon = provider.icon || Sparkles;
                const existing = integrations.find(i => i.provider === provider.key);
                const isConnected = existing?.status === 'connected';
                const isSyncing = syncingId === existing?.id;
                const isRequestTool = provider.statusType === 'request_tool';
                const existingRequest = getProviderRequest(provider.key, provider.name);
                const isApproved = (existingRequest?.status === 'approved' || provider.requestStatus === 'approved') && !isConnected;
                const isRequested = (existingRequest?.status === 'pending_review' || existingRequest?.status === 'pending' || provider.requestStatus === 'pending_review' || provider.requestStatus === 'pending') && !isConnected && !isApproved;
                const isRejected = (existingRequest?.status === 'rejected' || provider.requestStatus === 'rejected') && !isConnected && !isApproved;

                return (
                  <Card
                    key={provider.key}
                    className="bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm hover:shadow-md transition-all p-5 flex flex-col justify-between space-y-4"
                  >
                    {/* Top Row: Logo, Name & Action Button */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-xl ${provider.color || 'bg-indigo-600'} text-white flex items-center justify-center shadow-xs shrink-0`}>
                          <Icon className="w-6 h-6" />
                        </div>
                        <div>
                          <h3 className="font-bold text-slate-900 dark:text-white text-sm leading-snug">
                            {provider.name}
                          </h3>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            {isConnected ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                Connected
                              </span>
                            ) : isApproved ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                                Approved (API Setup Required)
                              </span>
                            ) : isRequested ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-600 dark:text-amber-400">
                                <Clock className="w-3.5 h-3.5 text-amber-500" />
                                Requested (Under Review)
                              </span>
                            ) : isRejected ? (
                              <button
                                onClick={() => handleOpenRequest(provider.key)}
                                className="text-[11px] text-rose-600 hover:text-rose-700 hover:underline font-medium inline-flex items-center gap-1"
                                title={existingRequest?.admin_notes || 'Request rejected. Click to re-request.'}
                              >
                                <XCircle className="w-3.5 h-3.5 text-rose-500" />
                                Rejected (Re-request)
                              </button>
                            ) : isRequestTool ? (
                              <button
                                onClick={() => handleOpenRequest(provider.key)}
                                className="text-[11px] text-blue-600 hover:text-blue-700 hover:underline font-medium inline-flex items-center gap-1"
                              >
                                Request Tool
                              </button>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] text-slate-400">
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-300" />
                                Not connected
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Action Button on the Right */}
                      <div>
                        {isConnected ? (
                          <div className="flex items-center gap-1">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleOpenConfig(provider.key, provider)}
                              className="h-8 text-xs gap-1 border-slate-200"
                              title="Settings & Assignment"
                            >
                              <Settings2 className="w-3.5 h-3.5" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleTriggerSync(existing.id)}
                              disabled={isSyncing}
                              className="h-8 text-xs gap-1 border-slate-200 text-emerald-700 hover:bg-emerald-50"
                              title="Sync Now"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
                            </Button>
                          </div>
                        ) : isApproved ? (
                          <div className="flex items-center gap-1.5">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigate('/admin/integration-requests')}
                              className="h-8 px-2.5 text-xs border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 font-semibold gap-1 shadow-xs"
                              title={existingRequest?.admin_notes ? `Approved: ${existingRequest.admin_notes}` : 'Approved by Admin! Configure API credentials below.'}
                            >
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                              Approved
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleOpenConfig(provider.key, provider)}
                              className="h-8 px-3 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg shadow-sm"
                              title="Configure API credentials and connect"
                            >
                              Connect
                            </Button>
                          </div>
                        ) : isRequested ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate('/admin/integration-requests')}
                            className="h-8 px-2.5 text-xs border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100 font-semibold gap-1 shadow-xs"
                            title="Request is currently under review by Admin and CRM Engineering"
                          >
                            <Clock className="w-3.5 h-3.5 text-amber-500" />
                            Requested
                          </Button>
                        ) : isRejected ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleOpenRequest(provider.key)}
                            className="h-8 px-2.5 text-xs border-rose-200 text-rose-700 hover:bg-rose-50 font-semibold gap-1 shadow-xs"
                            title="Request was rejected. Click to submit a new request"
                          >
                            <XCircle className="w-3.5 h-3.5 text-rose-500" />
                            Re-request
                          </Button>
                        ) : isRequestTool ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleOpenRequest(provider.key)}
                            className="h-8 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50 font-semibold"
                          >
                            Request Tool
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => handleOpenConfig(provider.key, provider)}
                            className="h-8 px-4 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm"
                          >
                            Connect
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Tagline / Capability */}
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed min-h-[34px]">
                      {provider.tagline}
                    </p>

                    {/* Connected Stats Row */}
                    {isConnected && (
                      <div className="bg-slate-50 dark:bg-slate-900/60 rounded-xl p-2.5 border border-slate-100 dark:border-slate-800 text-[11px] flex items-center justify-between text-slate-600">
                        <span>
                          {provider.key === 'ai_tools' ? 'Leads Evaluated: ' : 'Leads Ingested: '}
                          <b className="text-slate-900 dark:text-white">{existing.total_leads_synced || 0}</b>
                        </span>
                        <button
                          onClick={() => handleViewLogs(existing.id)}
                          className="text-indigo-600 hover:underline font-medium inline-flex items-center gap-0.5"
                        >
                          View Logs →
                        </button>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Right Column (1 col): Upload CSV File Manually & Custom Request (Reference Mock) */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-sm font-bold text-slate-700 uppercase tracking-wider">
              Upload CSV File Manually
            </h2>

            {/* Manual CSV Download & Upload Card (Exact Match to User Reference Image) */}
            <Card className="bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm p-5 space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                  <Download className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 dark:text-white text-sm">
                    Download sample files
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Choose the right format before uploading leads.
                  </p>
                </div>
              </div>

              <div className="space-y-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadSample}
                  className="w-full h-8 text-xs justify-center gap-2 border-slate-200 text-slate-700 hover:bg-slate-50 font-medium"
                >
                  <Download className="w-3.5 h-3.5 text-blue-600" /> Download Sample CSV
                </Button>
                <Button
                  size="sm"
                  onClick={() => navigate('/sales/my-crm')}
                  className="w-full h-8 text-xs justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                >
                  <Upload className="w-3.5 h-3.5" /> Start Bulk Import in CRM
                </Button>
              </div>

              <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-400">
                Supports .csv, .xlsx, and .xls files up to 20MB with auto-mapping for LEAMSS migration services.
              </div>
            </Card>

            {/* Request Another Tool Banner */}
            <Card className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-slate-800 dark:to-slate-800 border-indigo-100 dark:border-slate-700 rounded-2xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-400 font-bold text-xs uppercase tracking-wider">
                <Sparkles className="w-4 h-4" /> Custom Integrations
              </div>
              <h4 className="font-bold text-slate-900 dark:text-white text-sm">
                Need another integration?
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-300">
                Request any CRM, telephony dialer, or marketing platform to connect with your LEAMSS workspace.
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleOpenRequest()}
                className="w-full h-8 text-xs bg-white text-indigo-700 border-indigo-200 hover:bg-indigo-50 font-semibold"
              >
                + Request Integration
              </Button>
            </Card>
          </div>
        </div>

        {/* ── MODAL: CONNECT / CONFIGURE INTEGRATION ── */}
        <Dialog open={configModalOpen} onOpenChange={setConfigModalOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            {(() => {
              const meta = getProviderMeta(activeProvider);
              const Icon = meta?.icon || Sparkles;
              return (
                <DialogHeader>
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl ${meta?.color || 'bg-indigo-600'} text-white flex items-center justify-center shrink-0`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <DialogTitle className="text-base font-bold">
                        {editingIntegration ? 'Configure' : 'Connect'} {meta?.name || activeProvider}
                      </DialogTitle>
                      <DialogDescription className="text-xs">
                        Multi-company configuration for <b>{currentCompany.name}</b>
                      </DialogDescription>
                    </div>
                  </div>
                </DialogHeader>
              );
            })()}

            <Tabs defaultValue="credentials" className="pt-2">
              <TabsList className="grid grid-cols-4 h-9 text-xs">
                <TabsTrigger value="credentials">Credentials & Keys</TabsTrigger>
                <TabsTrigger value="assignment">Lead Assignment</TabsTrigger>
                <TabsTrigger value="duplicates">Duplicate Control</TabsTrigger>
                <TabsTrigger value="webhook">Webhook & Setup</TabsTrigger>
              </TabsList>

              {/* TAB 1: CREDENTIALS */}
              <TabsContent value="credentials" className="space-y-4 pt-3">
                <div>
                  <Label className="text-xs font-medium">Integration Display Name</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData(f => ({ ...f, name: e.target.value }))}
                    placeholder={getProviderMeta(activeProvider)?.name || 'Integration Name'}
                    className="h-8 text-xs mt-1"
                  />
                </div>

                {/* Zoho CRM Fields */}
                {activeProvider === 'zoho' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs font-medium">Zoho Data Center Domain</Label>
                        <Select
                          value={formData.credentials.domain || 'accounts.zoho.com'}
                          onValueChange={(val) => setFormData(f => ({ ...f, credentials: { ...f.credentials, domain: val } }))}
                        >
                          <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="accounts.zoho.com">zoho.com (US / Global)</SelectItem>
                            <SelectItem value="accounts.zoho.in">zoho.in (India)</SelectItem>
                            <SelectItem value="accounts.zoho.eu">zoho.eu (Europe)</SelectItem>
                            <SelectItem value="accounts.zoho.com.au">zoho.com.au (Australia)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs font-medium">Client ID</Label>
                        <Input
                          placeholder="1000.XXXXX"
                          value={formData.credentials.client_id || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, client_id: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs font-medium">Client Secret</Label>
                      <Input
                        type="password"
                        placeholder="••••••••••••••••"
                        value={formData.credentials.client_secret || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, client_secret: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-medium">Refresh Token</Label>
                      <Input
                        type="password"
                        placeholder="1000.XXXX.XXXX"
                        value={formData.credentials.refresh_token || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, refresh_token: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* Google Sheets Fields */}
                {activeProvider === 'google_sheets' && (
                  <div className="space-y-3">
                    <div className="bg-emerald-50 dark:bg-emerald-950/30 p-3 rounded-lg border border-emerald-200 dark:border-emerald-800 text-xs space-y-1.5">
                      <p className="font-semibold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        How to Connect Your Google Sheet
                      </p>
                      <p className="text-emerald-700 dark:text-emerald-300 text-[11px] leading-relaxed">
                        <b>Step 1 (Link Sharing):</b> In your Google Sheet, click <b>Share</b> (top right) → Change <i>Restricted</i> to <b>"Anyone with the link can view"</b>.
                      </p>
                      <p className="text-emerald-700 dark:text-emerald-300 text-[11px] leading-relaxed">
                        <b>Step 2:</b> Paste your Sheet URL or ID below. All new client responses will automatically sync into <b>All Leads</b> every minute.
                      </p>
                      <p className="text-emerald-700 dark:text-emerald-300 text-[11px] leading-relaxed">
                        <b>Step 3 (Optional for Real-time):</b> To push submissions the instant a client fills out a form, copy our ready-made script in the <b>Webhook & Setup</b> tab!
                      </p>
                    </div>

                    <div>
                      <Label className="text-xs font-medium">Google Spreadsheet ID (or full Sheet URL)</Label>
                      <Input
                        placeholder="https://docs.google.com/spreadsheets/d/1byFipgFkXYRACcgMCk4jD0tPlM54kXEbhfbLyRwBtJY/edit"
                        value={formData.credentials.spreadsheet_id || ''}
                        onChange={(e) => {
                          let val = e.target.value.trim();
                          const match = val.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
                          if (match) val = match[1];
                          setFormData(f => ({ ...f, credentials: { ...f.credentials, spreadsheet_id: val } }));
                        }}
                        className="h-8 text-xs mt-1"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">
                        Paste the full link from your browser address bar. The ID is automatically extracted.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs font-medium">Sheet Tab Name</Label>
                        <Input
                          placeholder="Sheet1"
                          value={formData.credentials.sheet_name || 'Sheet1'}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, sheet_name: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                        <p className="text-[10px] text-slate-400 mt-1">
                          Name of the tab at the bottom (e.g. Sheet1, Form Responses 1).
                        </p>
                      </div>
                      <div>
                        <Label className="text-xs font-medium">Google API Key (Optional)</Label>
                        <Input
                          type="password"
                          placeholder="Leave blank if sheet has link sharing"
                          value={formData.credentials.api_key || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, api_key: e.target.value.trim() } }))}
                          className="h-8 text-xs mt-1"
                        />
                        <p className="text-[10px] text-slate-400 mt-1">
                          Only needed if your Google Sheet cannot be shared with link.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Google Ads Fields */}
                {activeProvider === 'google_ads' && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs font-medium">Google Ads Customer ID (XXX-XXX-XXXX)</Label>
                      <Input
                        placeholder="e.g. 123-456-7890"
                        value={formData.credentials.customer_id || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, customer_id: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-medium">Developer Token (Optional)</Label>
                      <Input
                        type="password"
                        placeholder="Developer token from Google Ads Manager"
                        value={formData.credentials.developer_token || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, developer_token: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* WhatsApp Business API Fields */}
                {activeProvider === 'whatsapp_business' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs font-medium">Phone Number ID</Label>
                        <Input
                          placeholder="100657291234567"
                          value={formData.credentials.phone_number_id || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, phone_number_id: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-xs font-medium">WhatsApp Business Account ID</Label>
                        <Input
                          placeholder="100657299876543"
                          value={formData.credentials.waba_id || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, waba_id: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs font-medium">System User Access Token</Label>
                      <Input
                        type="password"
                        placeholder="EAAB••••••••"
                        value={formData.credentials.system_access_token || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, system_access_token: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* LinkedIn Lead Gen Forms */}
                {activeProvider === 'linkedin' && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs font-medium">LinkedIn Ad Account ID</Label>
                      <Input
                        placeholder="e.g. 501234567"
                        value={formData.credentials.ad_account_id || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, ad_account_id: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-medium">OAuth Access Token</Label>
                      <Input
                        type="password"
                        placeholder="AQV••••••••"
                        value={formData.credentials.access_token || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, access_token: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* Razorpay Gateway Fields */}
                {activeProvider === 'razorpay' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs font-medium">Key ID</Label>
                        <Input
                          placeholder="rzp_live_... or rzp_test_..."
                          value={formData.credentials.key_id || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, key_id: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-xs font-medium">Key Secret</Label>
                        <Input
                          type="password"
                          placeholder="••••••••••••••••"
                          value={formData.credentials.key_secret || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, key_secret: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Cashfree Payments Fields */}
                {activeProvider === 'cashfree' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs font-medium">App ID</Label>
                        <Input
                          placeholder="CF_APP_ID"
                          value={formData.credentials.app_id || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, app_id: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-xs font-medium">Secret Key</Label>
                        <Input
                          type="password"
                          placeholder="••••••••••••••••"
                          value={formData.credentials.secret_key || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, secret_key: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* PayPal Fields */}
                {activeProvider === 'paypal' && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs font-medium">PayPal Client ID</Label>
                      <Input
                        placeholder="Client ID from PayPal Developer Dashboard"
                        value={formData.credentials.client_id || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, client_id: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-medium">Secret Key</Label>
                      <Input
                        type="password"
                        placeholder="••••••••••••••••"
                        value={formData.credentials.secret || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, secret: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* Slack Fields */}
                {activeProvider === 'slack' && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs font-medium">Incoming Webhook URL</Label>
                      <Input
                        placeholder="https://hooks.slack.com/services/..."
                        value={formData.credentials.webhook_url || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, webhook_url: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-medium">Channel Name (Optional)</Label>
                      <Input
                        placeholder="#sales-leads"
                        value={formData.credentials.channel || '#sales-leads'}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, channel: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* Calendly Fields */}
                {activeProvider === 'calendly' && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs font-medium">Primary Calendly Booking Link</Label>
                      <Input
                        placeholder="https://calendly.com/rohit-leamss/permanent-residency-visa"
                        value={formData.credentials.primary_link || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, primary_link: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">
                        Main booking URL included in outbound email templates and consultation proposals.
                      </p>
                    </div>

                    <div>
                      <Label className="text-xs font-medium">Secondary / Additional Calendly Links (Optional)</Label>
                      <Input
                        placeholder="e.g. https://calendly.com/rohit-leamss/study-visa, https://calendly.com/..."
                        value={formData.credentials.additional_links || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, additional_links: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">
                        Separate multiple links with commas. All bookings from any of your links will sync automatically via your webhook.
                      </p>
                    </div>

                    <div>
                      <Label className="text-xs font-medium">Personal Access Token (PAT) — Optional</Label>
                      <Input
                        type="password"
                        placeholder="calendly_pat_••••••••"
                        value={formData.credentials.api_token || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, api_token: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">
                        Found in Calendly → Integrations → API and Webhooks → Personal Access Tokens.
                      </p>
                    </div>
                  </div>
                )}

                {/* Meta (Facebook/Instagram) */}
                {['facebook', 'instagram'].includes(activeProvider) && (
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs font-medium">Page Access Token</Label>
                      <Input
                        type="password"
                        placeholder="EAAB••••••••"
                        value={formData.credentials.page_access_token || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, page_access_token: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                    <div>
                      <Label className="text-xs font-medium">Verify Token</Label>
                      <Input
                        value={formData.credentials.verify_token || 'leamss_meta_verify_token'}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, verify_token: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>
                  </div>
                )}

                {/* AI Tools / LEAMSS AI Lead Assistant */}
                {activeProvider === 'ai_tools' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs font-medium">AI Provider</Label>
                        <Select
                          value={formData.credentials.provider || 'system_default'}
                          onValueChange={(val) => {
                            const defaultModel = val === 'openai' ? 'gpt-4o-mini' : val === 'anthropic' ? 'claude-3-5-haiku-latest' : val === 'perplexity' ? 'sonar' : val === 'gemini' ? 'gemini-1.5-flash' : 'sonar';
                            setFormData(f => ({
                              ...f,
                              credentials: {
                                ...f.credentials,
                                provider: val,
                                model: defaultModel
                              }
                            }));
                          }}
                        >
                          <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="system_default">LEAMSS System Default (Anthropic/Sonar)</SelectItem>
                            <SelectItem value="anthropic">Anthropic Claude</SelectItem>
                            <SelectItem value="openai">OpenAI</SelectItem>
                            <SelectItem value="perplexity">Perplexity AI</SelectItem>
                            <SelectItem value="gemini">Google Gemini</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs font-medium">Model</Label>
                        <Input
                          placeholder="e.g. sonar, gpt-4o-mini, claude-3-5-haiku"
                          value={formData.credentials.model || 'sonar'}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, model: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <Label className="text-xs font-medium">API Key (Optional if using System Default)</Label>
                        <span className="text-[10px] text-emerald-600 font-medium">AES-256 Encrypted</span>
                      </div>
                      <Input
                        type="password"
                        placeholder="sk-•••••••••••••••• (Leave blank to inherit server keys)"
                        value={formData.credentials.api_key || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, api_key: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                      <p className="text-[10px] text-slate-400 mt-1">
                        If left blank, the assistant automatically utilizes the pre-configured server keys for Claude & Perplexity Sonar.
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <div>
                        <Label className="text-xs font-medium">Creativity / Temperature</Label>
                        <Select
                          value={String(formData.credentials.temperature ?? '0.5')}
                          onValueChange={(val) => setFormData(f => ({ ...f, credentials: { ...f.credentials, temperature: parseFloat(val) } }))}
                        >
                          <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="0.2">0.2 — Strict & Analytical</SelectItem>
                            <SelectItem value="0.5">0.5 — Balanced Assessment</SelectItem>
                            <SelectItem value="0.7">0.7 — Expressive Sales Pitch</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs font-medium">Automated Lead Scoring</Label>
                        <Select
                          value={formData.credentials.auto_score !== false ? 'true' : 'false'}
                          onValueChange={(val) => setFormData(f => ({ ...f, credentials: { ...f.credentials, auto_score: val === 'true' } }))}
                        >
                          <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="true">Enabled (0–100, Hot/Warm/Cold)</SelectItem>
                            <SelectItem value="false">Manual Only</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                )}

                {/* Generic / Approved Request Tools (Apollo.io, HubSpot, ActiveCampaign, QuickBooks, etc.) */}
                {!['zoho', 'sheets', 'google_sheets', 'facebook', 'meta', 'google_ads', 'instagram', 'linkedin', 'whatsapp_business', 'google_gmail', 'google_calendar', 'calendly', 'zoom', 'razorpay', 'cashfree', 'paypal', 'slack', 'zapier', 'make', 'rest_api', 'webhooks', 'google_drive', 'analytics4', 'search_console', 'leamss_ai'].includes(activeProvider) && (
                  <div className="space-y-3">
                    <div className="bg-emerald-50 dark:bg-emerald-950/30 p-3 rounded-lg border border-emerald-200 dark:border-emerald-800 text-xs">
                      <p className="font-semibold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        Approved Integration Connector
                      </p>
                      <p className="text-emerald-700 dark:text-emerald-300 text-[11px] mt-0.5">
                        Enter credentials for <strong>{getProviderMeta(activeProvider)?.name || 'Integration'}</strong> to link directly with LEAMSS CRM.
                      </p>
                    </div>

                    <div>
                      <div className="flex items-center justify-between">
                        <Label className="text-xs font-medium">API Key / Access Token</Label>
                        <span className="text-[10px] text-emerald-600 font-medium">AES-256 Encrypted</span>
                      </div>
                      <Input
                        type="password"
                        placeholder="••••••••••••••••••••••••"
                        value={formData.credentials.api_key || ''}
                        onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, api_key: e.target.value } }))}
                        className="h-8 text-xs mt-1"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs font-medium">Account ID / Org ID (Optional)</Label>
                        <Input
                          placeholder="e.g. org_12345"
                          value={formData.credentials.account_id || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, account_id: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-xs font-medium">Webhook URL / Endpoint (Optional)</Label>
                        <Input
                          placeholder="https://api..."
                          value={formData.credentials.endpoint || ''}
                          onChange={(e) => setFormData(f => ({ ...f, credentials: { ...f.credentials, endpoint: e.target.value } }))}
                          className="h-8 text-xs mt-1"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Test Connection Button */}
                {editingIntegration && (
                  <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestConnection(editingIntegration.id)}
                      disabled={testingConnection}
                      className="text-xs"
                    >
                      <Play className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                      {testingConnection ? 'Testing...' : 'Test Connection'}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setTestLeadModalOpen(true)}
                      className="text-xs text-indigo-600"
                    >
                      Simulate Inbound Lead →
                    </Button>
                  </div>
                )}
              </TabsContent>

              {/* TAB 2: LEAD ASSIGNMENT */}
              <TabsContent value="assignment" className="space-y-4 pt-3">
                <div>
                  <Label className="text-xs font-medium">Assignment Method</Label>
                  <Select
                    value={formData.lead_assignment_rules.mode}
                    onValueChange={(val) => setFormData(f => ({
                      ...f,
                      lead_assignment_rules: { ...f.lead_assignment_rules, mode: val }
                    }))}
                  >
                    <SelectTrigger className="h-8 text-xs mt-1">
                      <SelectValue placeholder="Assignment Mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="round_robin">Round Robin (Sequential team distribution)</SelectItem>
                      <SelectItem value="specific_rep">Assign to Specific Representative</SelectItem>
                      <SelectItem value="unassigned">Unassigned Pool (Admin allocates manually)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {formData.lead_assignment_rules.mode === 'specific_rep' && (
                  <div>
                    <Label className="text-xs font-medium">Dedicated Sales Representative</Label>
                    <Select
                      value={formData.lead_assignment_rules.specific_rep_id || ''}
                      onValueChange={(val) => setFormData(f => ({
                        ...f,
                        lead_assignment_rules: { ...f.lead_assignment_rules, specific_rep_id: val }
                      }))}
                    >
                      <SelectTrigger className="h-8 text-xs mt-1"><SelectValue placeholder="Select Rep" /></SelectTrigger>
                      <SelectContent>
                        {salesReps.map(rep => (
                          <SelectItem key={rep.id} value={rep.id} className="text-xs">
                            {rep.name} ({rep.role})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div>
                    <Label className="text-xs font-medium">Default Visa Service</Label>
                    <Input
                      placeholder="Immigration Consultation"
                      value={formData.lead_assignment_rules.default_service || ''}
                      onChange={(e) => setFormData(f => ({
                        ...f,
                        lead_assignment_rules: { ...f.lead_assignment_rules, default_service: e.target.value }
                      }))}
                      className="h-8 text-xs mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-xs font-medium">Auto-Tag Ingested Leads</Label>
                    <Input
                      placeholder="e.g. ad_lead, express_entry"
                      value={(formData.lead_assignment_rules.default_tags || []).join(', ')}
                      onChange={(e) => setFormData(f => ({
                        ...f,
                        lead_assignment_rules: {
                          ...f.lead_assignment_rules,
                          default_tags: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                        }
                      }))}
                      className="h-8 text-xs mt-1"
                    />
                  </div>
                </div>
              </TabsContent>

              {/* TAB 3: DUPLICATE PREVENTION */}
              <TabsContent value="duplicates" className="space-y-4 pt-3">
                <div>
                  <Label className="text-xs font-medium">Action When Duplicate Lead Detected</Label>
                  <Select
                    value={formData.duplicate_prevention.strategy}
                    onValueChange={(val) => setFormData(f => ({
                      ...f,
                      duplicate_prevention: { ...f.duplicate_prevention, strategy: val }
                    }))}
                  >
                    <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="skip">Skip Lead & Append Timestamped Note to Existing (Recommended)</SelectItem>
                      <SelectItem value="update_existing">Update Existing Record with New Contact / Query</SelectItem>
                      <SelectItem value="always_create">Always Create Separate Record</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1.5">
                  <p className="font-semibold text-slate-800 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-indigo-600" /> Multi-Field Match Rules:
                  </p>
                  <p className="text-slate-600 text-[11px]">
                    Evaluates incoming leads within <b>{currentCompany.name}</b> by:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-slate-500 text-[11px]">
                    <li>Phone Number (international & local digit match)</li>
                    <li>Email Address (case-insensitive)</li>
                    <li>WhatsApp Number</li>
                  </ul>
                </div>
              </TabsContent>

              {/* TAB 4: WEBHOOK & INSTRUCTIONS */}
              <TabsContent value="webhook" className="space-y-3 pt-3">
                {activeProvider === 'ai_tools' ? (
                  <div className="space-y-3">
                    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-4 border border-indigo-100 text-xs space-y-2 text-indigo-950">
                      <p className="font-bold flex items-center gap-1.5 text-sm text-indigo-900">
                        <Sparkles className="w-4 h-4 text-indigo-600" /> LEAMSS AI Lead Assistant Workflow
                      </p>
                      <p className="text-[11px] leading-relaxed text-indigo-800">
                        The AI Lead Assistant operates directly inside your CRM pipeline to automate qualification and empower consultants:
                      </p>
                      <div className="grid grid-cols-2 gap-2 pt-1 text-[11px]">
                        <div className="p-2.5 bg-white/80 rounded-lg border border-indigo-100/60 shadow-sm">
                          <b className="text-slate-800 flex items-center gap-1">🎯 Multi-Dimensional Scoring</b>
                          <span className="text-slate-500 text-[10px]">Evaluates contact completeness, target country demand, education seniority, budget, and source intent (0–100, HOT/WARM/COLD).</span>
                        </div>
                        <div className="p-2.5 bg-white/80 rounded-lg border border-indigo-100/60 shadow-sm">
                          <b className="text-slate-800 flex items-center gap-1">📋 ANZSCO & NOC Matching</b>
                          <span className="text-slate-500 text-[10px]">Maps job titles to official Australian & Canadian immigration codes and assessing bodies (ACS, VETASSESS, CPA, EA).</span>
                        </div>
                        <div className="p-2.5 bg-white/80 rounded-lg border border-indigo-100/60 shadow-sm">
                          <b className="text-slate-800 flex items-center gap-1">✍️ 1-Click Proposal Generation</b>
                          <span className="text-slate-500 text-[10px]">Drafts an individualized 3-part sales proposal letter tailored to the client's eligibility strengths and target visa stream.</span>
                        </div>
                        <div className="p-2.5 bg-white/80 rounded-lg border border-indigo-100/60 shadow-sm">
                          <b className="text-slate-800 flex items-center gap-1">🔄 On-Demand Lead Evaluation</b>
                          <span className="text-slate-500 text-[10px]">Click the <b>Refresh</b> button on the integration card anytime to batch-evaluate new and pending inquiries.</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-600 space-y-1">
                      <p className="font-semibold text-slate-800 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-emerald-600" /> Security & Privacy
                      </p>
                      <p className="text-[11px]">
                        All API keys and client data are isolated per company context (<b>{currentCompany.name}</b>). Credentials are encrypted with AES-256 at rest and masked in all client responses.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div>
                      <Label className="text-xs font-medium">Your Dedicated Webhook Endpoint</Label>
                      <div className="flex items-center gap-2 mt-1">
                        <Input
                          readOnly
                          value={getWebhookUrl(activeProvider)}
                          className="h-8 text-xs bg-slate-50 font-mono text-slate-700"
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => copyToClipboard(getWebhookUrl(activeProvider), 'webhook_url')}
                          className="h-8 px-2.5 text-xs"
                        >
                          {copiedKey === 'webhook_url' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        </Button>
                      </div>
                    </div>

                    <div className="bg-indigo-50/70 rounded-lg p-3 border border-indigo-100 text-xs space-y-1.5 text-indigo-950">
                      <p className="font-bold flex items-center gap-1.5">
                        <HelpCircle className="w-3.5 h-3.5 text-indigo-600" /> Setup Guide:
                      </p>
                      <p className="text-[11px] leading-relaxed">
                        Paste this endpoint into your {getProviderMeta(activeProvider)?.name || 'Platform'} webhook or automation settings. New incoming inquiries will be instantly captured, de-duplicated, scored, and assigned to your sales team in real time.
                      </p>
                    </div>

                    {activeProvider === 'google_sheets' && (
                      <div className="space-y-3 pt-1">
                        <div className="bg-emerald-50 dark:bg-emerald-950/30 rounded-lg p-3.5 border border-emerald-200 dark:border-emerald-800 text-xs space-y-2 text-emerald-950 dark:text-emerald-200">
                          <p className="font-bold flex items-center gap-1.5 text-emerald-900 dark:text-emerald-100 text-sm">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Real-Time Google Sheet Sync (Google Apps Script)
                          </p>
                          <p className="text-[11px] leading-relaxed text-emerald-800 dark:text-emerald-300">
                            Whenever a client submits a row in your Google Sheet (or connected Google Form), this script instantly sends it into LEAMSS CRM. It also adds a convenient <b>"LEAMSS CRM → 🚀 Sync All Rows Now"</b> menu directly inside your Google Sheet toolbar!
                          </p>
                          
                          <div className="space-y-1.5 pt-1">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-[11px] text-emerald-900 dark:text-emerald-200 flex items-center gap-1">
                                <Code2 className="w-3.5 h-3.5 text-emerald-700 dark:text-emerald-400" /> Ready-to-Use Google Apps Script:
                              </span>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => copyToClipboard(getSheetsScript(getWebhookUrl(activeProvider)), 'sheets_script')}
                                className="h-7 px-2.5 text-[11px] bg-white dark:bg-slate-800 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200 hover:bg-emerald-100"
                              >
                                {copiedKey === 'sheets_script' ? (
                                  <>
                                    <Check className="w-3.5 h-3.5 text-emerald-600 mr-1" /> Copied Script!
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3.5 h-3.5 mr-1" /> Copy Apps Script
                                  </>
                                )}
                              </Button>
                            </div>
                            
                            <pre className="bg-slate-900 text-emerald-400 text-[10px] p-2.5 rounded-md overflow-x-auto max-h-48 font-mono border border-slate-800 select-all">
                              {getSheetsScript(getWebhookUrl(activeProvider))}
                            </pre>
                          </div>

                          <div className="bg-white/80 dark:bg-slate-900/60 rounded-md p-2.5 border border-emerald-200/80 dark:border-emerald-800/80 text-[11px] space-y-1 text-slate-700 dark:text-slate-300">
                            <p className="font-semibold text-slate-800 dark:text-slate-200">Quick 3-Step Setup Instructions:</p>
                            <ol className="list-decimal pl-4 space-y-1 text-slate-600 dark:text-slate-400">
                              <li>In your Google Sheet top menu, click <b>Extensions</b> → <b>Apps Script</b>.</li>
                              <li>Delete any default code, paste the copied script above, and click <b>Save</b> (💾 icon).</li>
                              <li>Reload your Google Sheet. You will see a new menu: <b>LEAMSS CRM</b> → click <b>🚀 Sync All Rows to CRM Now</b> to immediately pull in all current client entries!</li>
                            </ol>
                          </div>
                        </div>

                        <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-3 border border-blue-200 dark:border-blue-800 text-xs space-y-1 text-blue-950 dark:text-blue-200">
                          <p className="font-bold flex items-center gap-1.5 text-blue-900 dark:text-blue-100">
                            <RefreshCw className="w-3.5 h-3.5 text-blue-600" /> Automatic Background Poller is Active
                          </p>
                          <p className="text-[11px] leading-relaxed text-blue-800 dark:text-blue-300">
                            As long as your sheet's share setting is <b>"Anyone with the link can view"</b>, LEAMSS checks for new rows automatically every 60 seconds without needing any script!
                          </p>
                        </div>
                      </div>
                    )}

                    {activeProvider === 'calendly' && (
                      <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-100 text-xs space-y-1.5 text-emerald-950">
                        <p className="font-bold flex items-center gap-1.5 text-emerald-900">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Connecting Multiple Calendly Links:
                        </p>
                        <p className="text-[11px] leading-relaxed text-emerald-800">
                          Calendly webhooks cover your entire organization/account. When you register this webhook in Calendly, <b>all your event links</b> (e.g. <i>https://calendly.com/rohit-leamss/permanent-residency-visa</i> and your other event links) will automatically forward new bookings directly into LEAMSS CRM.
                        </p>
                      </div>
                    )}
                  </>
                )}
              </TabsContent>
            </Tabs>

            <DialogFooter className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
              {editingIntegration && (
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    setConfigModalOpen(false);
                    handleDisconnect(editingIntegration.id, getProviderMeta(activeProvider)?.name || activeProvider);
                  }}
                  className="text-xs"
                >
                  <Unlink className="w-3.5 h-3.5 mr-1" /> Disconnect
                </Button>
              )}
              <div className="flex gap-2 ml-auto">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setConfigModalOpen(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleSaveIntegration}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold"
                >
                  Save Integration
                </Button>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── MODAL: REQUEST INTEGRATION ── */}
        <Dialog open={requestModalOpen} onOpenChange={setRequestModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-600" /> Request New Integration
              </DialogTitle>
              <DialogDescription className="text-xs">
                Suggest an integration for LEAMSS CRM. Our engineering team reviews and implements top-requested platforms.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3 pt-2">
              <div>
                <Label className="text-xs font-medium">Tool / Platform Name</Label>
                <Input
                  placeholder="e.g. Apollo.io, QuickBooks, ActiveCampaign, HubSpot..."
                  value={requestData.tool_name}
                  onChange={(e) => setRequestData(d => ({ ...d, tool_name: e.target.value }))}
                  className="h-8 text-xs mt-1"
                />
              </div>

              <div>
                <Label className="text-xs font-medium">Category</Label>
                <Select
                  value={requestData.category}
                  onValueChange={(val) => setRequestData(d => ({ ...d, category: val }))}
                >
                  <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="lead_capture">Lead Capture & Ads</SelectItem>
                    <SelectItem value="communication">Communication & Meetings</SelectItem>
                    <SelectItem value="payments">Payments & Billing</SelectItem>
                    <SelectItem value="storage">Storage & Documents</SelectItem>
                    <SelectItem value="analytics">Analytics & Reporting</SelectItem>
                    <SelectItem value="automation">Automation & APIs</SelectItem>
                    <SelectItem value="ai">AI Tools</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-xs font-medium">Primary Business Use-Case</Label>
                <Textarea
                  placeholder="How will this tool help your admissions and sales workflows?"
                  value={requestData.use_case}
                  onChange={(e) => setRequestData(d => ({ ...d, use_case: e.target.value }))}
                  className="text-xs h-20 mt-1"
                />
              </div>

              <div>
                <Label className="text-xs font-medium">Priority for LEAMSS</Label>
                <Select
                  value={requestData.priority}
                  onValueChange={(val) => setRequestData(d => ({ ...d, priority: val }))}
                >
                  <SelectTrigger className="h-8 text-xs mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high">High — Needed immediately for daily operations</SelectItem>
                    <SelectItem value="medium">Medium — Helpful for quarterly optimization</SelectItem>
                    <SelectItem value="low">Low — Exploratory / nice to have</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Where is it stored & who receives it */}
              <div className="bg-slate-50 dark:bg-slate-900 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 space-y-0.5">
                <div className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Storage & Delivery Transparency</span>
                </div>
                <p>
                  Requests are saved directly into database <code className="font-mono text-indigo-600 font-semibold">leamss.integration_requests</code> and queued for review in <strong>Admin → Integration Requests</strong>.
                </p>
              </div>
            </div>

            <DialogFooter className="mt-4">
              <Button size="sm" variant="outline" onClick={() => setRequestModalOpen(false)} className="text-xs">
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitRequest}
                disabled={submittingRequest}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold gap-1.5"
              >
                {submittingRequest && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                {submittingRequest ? 'Saving to Database...' : 'Submit Request'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── MODAL: SYNC & ERROR LOGS ── */}
        <Dialog open={logsModalOpen} onOpenChange={setLogsModalOpen}>
          <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-base font-bold flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-600" /> Sync History & Execution Logs
              </DialogTitle>
              <DialogDescription className="text-xs">
                Audited connection events, lead ingestions, and background sync statuses.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-2 pt-2">
              {logs.length === 0 ? (
                <p className="text-xs text-slate-400 italic text-center py-8">No sync logs recorded yet.</p>
              ) : (
                logs.map(log => (
                  <div key={log.id} className="p-3 rounded-lg border border-slate-100 bg-slate-50 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 capitalize">
                        {(log.event_type || log.action || 'Sync Event').replace(/_/g, ' ')}
                      </span>
                      <Badge className={log.status === 'success' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}>
                        {log.status}
                      </Badge>
                    </div>
                    <p className="text-slate-600 text-[11px]">
                      {log.detail || log.message || `${log.leads_imported || 0} leads processed`}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      {log.timestamp || log.created_at}
                    </span>
                  </div>
                ))
              )}
            </div>
          </DialogContent>
        </Dialog>

        {/* ── MODAL: SIMULATE LEAD ── */}
        <Dialog open={testLeadModalOpen} onOpenChange={setTestLeadModalOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-base font-bold">Simulate Inbound Lead</DialogTitle>
              <DialogDescription className="text-xs">
                Simulate an incoming lead to verify assignment and duplicate prevention rules.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3 pt-2">
              <div>
                <Label className="text-xs">Full Name</Label>
                <Input
                  value={testLeadData.name}
                  onChange={e => setTestLeadData(d => ({ ...d, name: e.target.value }))}
                  className="h-8 text-xs mt-1"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs">Email</Label>
                  <Input
                    value={testLeadData.email}
                    onChange={e => setTestLeadData(d => ({ ...d, email: e.target.value }))}
                    className="h-8 text-xs mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs">Phone</Label>
                  <Input
                    value={testLeadData.phone}
                    onChange={e => setTestLeadData(d => ({ ...d, phone: e.target.value }))}
                    className="h-8 text-xs mt-1"
                  />
                </div>
              </div>
              <div>
                <Label className="text-xs">Service</Label>
                <Input
                  value={testLeadData.service_interested}
                  onChange={e => setTestLeadData(d => ({ ...d, service_interested: e.target.value }))}
                  className="h-8 text-xs mt-1"
                />
              </div>
            </div>

            <DialogFooter className="mt-4">
              <Button size="sm" variant="outline" onClick={() => setTestLeadModalOpen(false)} className="text-xs">
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => handleSimulateLead(editingIntegration.id)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold"
              >
                Send Test Lead
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── MODAL: AI QUALIFICATION & PROPOSAL RESULT ── */}
        <Dialog open={aiResultModalOpen} onOpenChange={setAiResultModalOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <DialogTitle className="text-base font-bold">
                    LEAMSS AI Qualification & Proposal Result
                  </DialogTitle>
                  <DialogDescription className="text-xs">
                    Automated lead evaluation for <b>{aiResult?.name || 'Applicant'}</b> (Lead: {aiResult?.lead_number})
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            {aiResult?.ai_qualification && (
              <div className="space-y-4 pt-2">
                {/* Score & Category Hero */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 border border-indigo-100 flex items-center justify-between">
                  <div>
                    <span className="text-[11px] font-semibold text-indigo-700 uppercase tracking-wider">AI Lead Score</span>
                    <div className="flex items-baseline gap-2 mt-0.5">
                      <span className="text-3xl font-extrabold text-slate-900">{aiResult.ai_qualification.score}</span>
                      <span className="text-xs text-slate-500">/ 100</span>
                      <Badge className={
                        aiResult.ai_qualification.category === 'HOT' ? 'bg-rose-500 text-white' :
                        aiResult.ai_qualification.category === 'WARM' ? 'bg-amber-500 text-white' :
                        'bg-slate-500 text-white'
                      }>
                        {aiResult.ai_qualification.category} Priority
                      </Badge>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[11px] text-slate-500 block">Assigned Sales Executive</span>
                    <span className="text-xs font-bold text-slate-800">{aiResult.assigned_to_name || 'Round-Robin Pool'}</span>
                  </div>
                </div>

                {/* Occupation & Pathway Matching */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Matched Occupation & Authority</span>
                    <p className="font-bold text-slate-800 mt-1">{aiResult.ai_qualification.code_identifier}</p>
                    <p className="text-[11px] text-slate-600 mt-0.5">Assessing Body: <b>{aiResult.ai_qualification.assessing_authority}</b></p>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70">
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Recommended Pathway</span>
                    <p className="font-bold text-indigo-700 mt-1">{aiResult.ai_qualification.recommended_pathway}</p>
                    <p className="text-[11px] text-slate-600 mt-0.5">{aiResult.ai_qualification.action_recommendation}</p>
                  </div>
                </div>

                {/* Qualification Insights */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 text-xs space-y-1">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Evaluation Highlights</span>
                  <ul className="list-disc list-inside space-y-1 text-slate-600 text-[11px] pt-1">
                    {(aiResult.ai_qualification.insights || []).map((ins, i) => (
                      <li key={i}>{ins}</li>
                    ))}
                  </ul>
                </div>

                {/* Draft Proposal */}
                {aiResult.ai_proposal_draft && (
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-indigo-600" /> Instant Personalized Proposal Pitch
                      </Label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyToClipboard(aiResult.ai_proposal_draft, 'proposal_text')}
                        className="h-6 text-[10px] px-2 text-indigo-600"
                      >
                        {copiedKey === 'proposal_text' ? <Check className="w-3 h-3 text-emerald-600 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                        Copy Pitch
                      </Button>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-slate-200 text-xs text-slate-700 font-sans leading-relaxed whitespace-pre-line max-h-56 overflow-y-auto">
                      {aiResult.ai_proposal_draft}
                    </div>
                  </div>
                )}
              </div>
            )}

            <DialogFooter className="mt-4">
              <Button size="sm" onClick={() => setAiResultModalOpen(false)} className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs">
                Close Preview
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </div>
    </div>
  );
}
