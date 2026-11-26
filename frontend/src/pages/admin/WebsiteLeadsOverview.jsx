import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import {
  Globe, Search, RefreshCw, ExternalLink, UserCheck, ShieldAlert,
  Phone, Mail, Calendar, ArrowUpRight, CheckCircle2, AlertCircle,
  Filter, User, ChevronRight, Layers, Tag, Copy, Check, Sparkles,
  HelpCircle, ArrowRightLeft, Users, FileText, Eye, Trash2, Download,
  FileSpreadsheet, ArrowUpDown, ChevronLeft, Database, Upload, Paperclip
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

const CATEGORIES = [
  {
    key: 'all',
    label: 'All Enquiries',
    shortLabel: 'All',
    enquiryListTitle: 'All Website Enquiry List',
    enquiryDetailsTitle: 'Enquiry Details',
    description: 'All enquiries received across all visa pathways and categories.',
    badgeClass: 'bg-sky-100 text-sky-800 border-sky-200',
    color: 'sky'
  },
  {
    key: 'PR',
    label: 'PR (Permanent Residency)',
    shortLabel: 'PR',
    enquiryListTitle: 'PR Enquiry List',
    enquiryDetailsTitle: 'PR Enquiry Details',
    description: 'Permanent residence pathways (Subclass 189/190/491, Express Entry, FSWP, PNP, SMC).',
    badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    color: 'emerald'
  },
  {
    key: 'TR',
    label: 'TR (Temporary Residency)',
    shortLabel: 'TR',
    enquiryListTitle: 'TR Enquiry List',
    enquiryDetailsTitle: 'TR Enquiry Details',
    description: 'Temporary residence, work permits, TSS Subclass 482/485, student & visitor visas.',
    badgeClass: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    color: 'indigo'
  },
  {
    key: 'Work',
    label: 'Work',
    shortLabel: 'Work',
    enquiryListTitle: 'Work Enquiry List',
    enquiryDetailsTitle: 'Work Enquiry Details',
    description: 'Employer-sponsored work visas, TSS Subclass 482/186/400, UK Skilled Worker, LMIA & AEWV.',
    badgeClass: 'bg-blue-100 text-blue-800 border-blue-200',
    color: 'blue'
  },
  {
    key: 'Study',
    label: 'Study',
    shortLabel: 'Study',
    enquiryListTitle: 'Study Enquiry List',
    enquiryDetailsTitle: 'Study Enquiry Details',
    description: 'Student visas, Subclass 500, UK Student Visa, Canada Study Permit, SDS & university admissions.',
    badgeClass: 'bg-purple-100 text-purple-800 border-purple-200',
    color: 'purple'
  },
  {
    key: 'Tourist',
    label: 'Tourist',
    shortLabel: 'Tourist',
    enquiryListTitle: 'Tourist Enquiry List',
    enquiryDetailsTitle: 'Tourist Enquiry Details',
    description: 'Visitor and tourist visas, Subclass 600, UK Standard Visitor, US B1/B2 & tourist visas.',
    badgeClass: 'bg-teal-100 text-teal-800 border-teal-200',
    color: 'teal'
  },
  {
    key: 'Family',
    label: 'Family',
    shortLabel: 'Family',
    enquiryListTitle: 'Family Enquiry List',
    enquiryDetailsTitle: 'Family Enquiry Details',
    description: 'Partner & spouse visas (Subclass 309/100, 820/801), UK Family, child & parent sponsorship.',
    badgeClass: 'bg-rose-100 text-rose-800 border-rose-200',
    color: 'rose'
  },
  {
    key: 'General',
    label: 'General',
    shortLabel: 'General',
    enquiryListTitle: 'General Enquiry List',
    enquiryDetailsTitle: 'General Enquiry Details',
    description: 'General visa consultations, skill assessments & profile evaluations.',
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-200',
    color: 'amber'
  },
  {
    key: 'Atlas',
    label: 'Atlas',
    shortLabel: 'Atlas',
    enquiryListTitle: 'Atlas Enquiry List',
    enquiryDetailsTitle: 'Atlas Enquiry Details',
    description: 'Migration Atlas occupation pathway enquiries (ANZSCO/NOC consultations) and free immigration points calculator submissions.',
    badgeClass: 'bg-cyan-100 text-cyan-800 border-cyan-200',
    color: 'cyan'
  }
];

const formatPhoneNumber = (phone) => {
  if (!phone) return 'No phone';
  let p = String(phone).trim();
  if (p.includes('E') || p.includes('e')) {
    try {
      const num = Number(p);
      if (!isNaN(num)) p = num.toLocaleString('fullwide', { useGrouping: false });
    } catch (e) {}
  }
  return p;
};

const formatDisplayDate = (iso) => {
  if (!iso) return '-';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  } catch (e) {
    return iso;
  }
};

const formatCountryName = (country) => {
  const c = String(country || '').trim();
  if (!c || c.toLowerCase() === 'global / other' || c.toLowerCase() === 'global') return 'Other';
  return c;
};

const getCountryBadgeColor = (country) => {
  const c = String(country || '').toLowerCase();
  if (c.includes('australia')) return 'bg-sky-50 text-sky-700 border-sky-200';
  if (c.includes('canada')) return 'bg-rose-50 text-rose-700 border-rose-200';
  if (c.includes('united kingdom') || c.includes('uk')) return 'bg-purple-50 text-purple-700 border-purple-200';
  if (c.includes('united states') || c.includes('usa')) return 'bg-blue-50 text-blue-700 border-blue-200';
  if (c.includes('new zealand') || c.includes('nz')) return 'bg-teal-50 text-teal-700 border-teal-200';
  if (c.includes('germany')) return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-slate-50 text-slate-700 border-slate-200';
};

export default function WebsiteLeadsOverview({
  salesReps = [],
  activeCategoryProp = 'all',
  onCategoryChangeProp,
  onOpenLeadWorkspace,
  refreshTrigger
}) {
  const [activeCategory, setActiveCategory] = useState(activeCategoryProp || 'all');
  const [activeCountry, setActiveCountry] = useState('all');
  const [assignmentFilter, setAssignmentFilter] = useState('all'); // 'all', 'unassigned', 'assigned'
  const [searchQuery, setSearchQuery] = useState('');
  const [entriesPerPage, setEntriesPerPage] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);

  const [overview, setOverview] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);
  const [allSalesReps, setAllSalesReps] = useState(salesReps);

  // Modal States (Ref Image 4)
  const [viewingLead, setViewingLead] = useState(null);
  const [deletingLead, setDeletingLead] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Database Sync Modal States
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [syncTab, setSyncTab] = useState('live_url'); // 'live_url' | 'mysql' | 'json' | 'webhook'
  const [liveWebsiteUrl, setLiveWebsiteUrl] = useState('https://leamss.com/api/crm-website-leads-export');
  const [mysqlCreds, setMysqlCreds] = useState({
    host: 'leader.herosite.pro',
    database: 'hosldwuh_staging',
    user: '',
    password: '',
    port: 3306
  });
  const [isSyncing, setIsSyncing] = useState(false);
  const [jsonRowsText, setJsonRowsText] = useState('');
  const [jsonTableType, setJsonTableType] = useState('general_enquiries');

  // Single Inline Assigning State
  const [assigningLeadId, setAssigningLeadId] = useState(null);
  const [copiedPhoneId, setCopiedPhoneId] = useState(null);
  const [uploadingResumeId, setUploadingResumeId] = useState(null);

  const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return token ? { headers: { Authorization: `Bearer ${token}` } } : {};
  };

  const handleResumeUpload = async (lead, file) => {
    if (!file) return;
    if (file.size > 15 * 1024 * 1024) {
      toast.error('Resume file exceeds maximum limit of 15MB');
      return;
    }
    const leadId = lead?.id || lead?._id || lead?.lead_number;
    if (!leadId) {
      toast.error('Unable to determine lead reference ID');
      return;
    }
    setUploadingResumeId(leadId);
    const formData = new FormData();
    formData.append('file', file);

    const toastId = toast.loading('Uploading and synchronizing candidate resume...');
    try {
      const res = await axios.post(`${API}/leads/${leadId}/resume`, formData, {
        headers: {
          ...getAuthHeader().headers,
          'Content-Type': 'multipart/form-data',
        },
      });
      toast.success(res.data?.message || 'Resume attached successfully', { id: toastId });

      const updatedLead = {
        ...lead,
        resume_file_id: res.data?.resume_file_id,
        resume_filename: res.data?.resume_filename || file.name,
        resume_url: res.data?.resume_url || `/cockpit/resume/${res.data?.resume_file_id}`,
        resume_uploaded: true,
      };

      setLeads((prev) => prev.map((l) => ((l.id === lead.id || l._id === lead._id) ? updatedLead : l)));
      if (viewingLead && (viewingLead.id === lead.id || viewingLead._id === lead._id)) {
        setViewingLead(updatedLead);
      }
    } catch (err) {
      console.error('Error uploading resume for website lead:', err);
      toast.error(err.response?.data?.detail || err.message || 'Failed to upload resume', { id: toastId });
    } finally {
      setUploadingResumeId(null);
    }
  };

  // Sync external prop if changed
  useEffect(() => {
    if (activeCategoryProp && activeCategoryProp !== activeCategory) {
      setActiveCategory(activeCategoryProp);
      setActiveCountry('all');
      setCurrentPage(1);
    }
  }, [activeCategoryProp]);

  // Fetch sales reps if not provided
  useEffect(() => {
    if (!salesReps || salesReps.length === 0) {
      Promise.all([
        axios.get(`${API}/users/`, getAuthHeader()).catch(() => ({ data: [] })),
        axios.get(`${API}/crm/sales-reps/overview`, getAuthHeader()).catch(() => ({ data: [] }))
      ]).then(([usersRes, repsOverviewRes]) => {
        const repMap = new Map();
        if (Array.isArray(repsOverviewRes.data)) {
          repsOverviewRes.data.forEach(r => {
            if (r && r.id) {
              repMap.set(String(r.id), {
                id: String(r.id),
                name: r.name || r.email || 'Salesperson',
                email: r.email || '',
                role: r.role || r.role_label || 'salesperson',
                salesperson_type: r.salesperson_type || (r.is_external ? 'external' : 'internal')
              });
            }
          });
        }
        if (Array.isArray(usersRes.data)) {
          usersRes.data.forEach(u => {
            if (!u || !u.id || u.role === 'client' || u.user_type === 'client') return;
            const r = String(u.role || '').toLowerCase().trim();
            const rbac = String(u.rbac_role || '').toLowerCase().trim();
            const dept = String(u.department || '').toLowerCase().trim();
            const desig = String(u.designation || '').toLowerCase().trim();
            const isSales = (
              r.includes('sales') ||
              rbac.includes('sales') ||
              r.includes('partner') ||
              rbac.includes('partner') ||
              r.includes('admin') ||
              rbac.includes('admin') ||
              dept === 'sales' ||
              desig.includes('sales') ||
              u.user_type === 'external'
            );
            if (isSales && !repMap.has(String(u.id))) {
              repMap.set(String(u.id), {
                id: String(u.id),
                name: u.name || u.email || 'Salesperson',
                email: u.email || '',
                role: u.role || u.rbac_role || 'salesperson',
                salesperson_type: (u.role === 'partner' || u.user_type === 'external') ? 'external' : 'internal'
              });
            }
          });
        }
        setAllSalesReps(Array.from(repMap.values()));
      }).catch(err => console.error('Failed to fetch sales reps for website leads:', err));
    } else {
      setAllSalesReps(salesReps);
    }
  }, [salesReps]);

  // Fetch Overview Stats
  const fetchOverview = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/crm/website-leads/overview`, getAuthHeader());
      setOverview(res.data);
    } catch (err) {
      console.error('Error fetching website leads overview:', err);
      toast.error('Failed to load website leads overview');
    }
  }, []);

  // Fetch Leads List
  const fetchLeads = useCallback(async () => {
    setListLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeCategory && activeCategory !== 'all') params.append('category', activeCategory);
      if (activeCountry && activeCountry !== 'all') params.append('country', activeCountry);
      if (assignmentFilter && assignmentFilter !== 'all') params.append('assignment', assignmentFilter);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());
      params.append('limit', '500'); // fetch batch for client-side pagination / export

      const res = await axios.get(`${API}/crm/website-leads/list?${params.toString()}`, getAuthHeader());
      setLeads(res.data?.leads || []);
    } catch (err) {
      console.error('Error fetching website leads list:', err);
      toast.error('Failed to load website leads list');
    } finally {
      setListLoading(false);
    }
  }, [activeCategory, activeCountry, assignmentFilter, searchQuery]);

  // Initial Load
  useEffect(() => {
    setLoading(true);
    Promise.all([fetchOverview(), fetchLeads()]).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // External refresh trigger (e.g. new lead added or resume attached)
  useEffect(() => {
    if (refreshTrigger) {
      Promise.all([fetchOverview(), fetchLeads()]);
    }
  }, [refreshTrigger, fetchOverview, fetchLeads]);

  // Re-fetch list when category/country/assignment/search changes
  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Reset page when entriesPerPage or filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [entriesPerPage, activeCategory, activeCountry, searchQuery, assignmentFilter]);

  // Switch category
  const handleSelectCategory = (catKey) => {
    setActiveCategory(catKey);
    setActiveCountry('all');
    setCurrentPage(1);
    if (onCategoryChangeProp) onCategoryChangeProp(catKey);
  };

  // Assign single lead
  const handleAssignLead = async (leadId, salesPersonId) => {
    if (!salesPersonId) return;
    setAssigningLeadId(leadId);
    try {
      const res = await axios.post(
        `${API}/crm/website-leads/${leadId}/assign`,
        { sales_person_id: salesPersonId },
        getAuthHeader()
      );
      toast.success(res.data?.message || 'Lead assigned successfully');
      fetchOverview();
      fetchLeads();
      if (viewingLead && viewingLead.id === leadId) {
        const rep = allSalesReps.find(r => r.id === salesPersonId);
        setViewingLead(prev => ({
          ...prev,
          assigned_to: salesPersonId,
          assigned_to_name: rep?.name || 'Assigned',
          is_unassigned: false
        }));
      }
    } catch (err) {
      console.error('Error assigning website lead:', err);
      toast.error(err.response?.data?.detail || 'Failed to assign lead');
    } finally {
      setAssigningLeadId(null);
    }
  };

  // Delete lead (Ref Image 3 trash action)
  const handleDeleteLead = async () => {
    if (!deletingLead) return;
    setIsDeleting(true);
    try {
      const res = await axios.delete(
        `${API}/crm/website-leads/${deletingLead.id}`,
        getAuthHeader()
      );
      toast.success(res.data?.message || 'Enquiry successfully deleted');
      setDeletingLead(null);
      if (viewingLead && viewingLead.id === deletingLead.id) {
        setViewingLead(null);
      }
      fetchOverview();
      fetchLeads();
    } catch (err) {
      console.error('Error deleting website lead:', err);
      toast.error(err.response?.data?.detail || 'Failed to delete lead');
    } finally {
      setIsDeleting(false);
    }
  };

  // Sync directly from cPanel MySQL database
  const handleSyncMysql = async () => {
    if (!mysqlCreds.user || !mysqlCreds.password) {
      toast.error('Please enter your cPanel database username and password');
      return;
    }
    setIsSyncing(true);
    try {
      const res = await axios.post(
        `${API}/crm/website-leads/sync-mysql`,
        mysqlCreds,
        getAuthHeader()
      );
      if (res.data?.success) {
        toast.success(res.data?.message || 'Database leads synced successfully!');
        setShowSyncModal(false);
        fetchOverview();
        fetchLeads();
      }
    } catch (err) {
      console.error('Error syncing MySQL:', err);
      toast.error(err.response?.data?.detail || 'Failed to connect to MySQL database. Check credentials or firewall.');
    } finally {
      setIsSyncing(false);
    }
  };

  // Import batch of enquiry rows (JSON export from phpMyAdmin)
  const handleImportJson = async () => {
    if (!jsonRowsText.trim()) {
      toast.error('Please paste exported JSON data from phpMyAdmin');
      return;
    }
    setIsSyncing(true);
    try {
      let parsed;
      try {
        parsed = JSON.parse(jsonRowsText.trim());
      } catch (e) {
        toast.error('Invalid JSON. Please paste a valid JSON array exported from phpMyAdmin.');
        setIsSyncing(false);
        return;
      }
      const rows = Array.isArray(parsed) ? parsed : (parsed.data || parsed.rows || [parsed]);
      const res = await axios.post(
        `${API}/crm/website-leads/import-rows`,
        {
          table_type: jsonTableType,
          rows: rows
        },
        getAuthHeader()
      );
      if (res.data?.success) {
        toast.success(res.data?.message || 'Enquiry rows successfully imported into CRM!');
        setShowSyncModal(false);
        setJsonRowsText('');
        fetchOverview();
        fetchLeads();
      }
    } catch (err) {
      console.error('Error importing rows:', err);
      toast.error(err.response?.data?.detail || 'Failed to import JSON rows');
    } finally {
      setIsSyncing(false);
    }
  };

  // Sync via live website export route (e.g. https://leamss.com/api/crm-website-leads-export)
  const handleSyncUrl = async () => {
    setIsSyncing(true);
    try {
      const res = await axios.post(
        `${API}/crm/website-leads/sync-url`,
        { url: liveWebsiteUrl || 'https://leamss.com/api/crm-website-leads-export' },
        getAuthHeader()
      );
      if (res.data?.success) {
        toast.success(res.data?.message || 'Successfully synced leads from website!');
        setShowSyncModal(false);
        fetchOverview();
        fetchLeads();
      }
    } catch (err) {
      console.error('Error syncing website URL:', err);
      toast.error(err.response?.data?.detail || 'Failed to fetch leads from website. Ensure route is added to routes/web.php.');
    } finally {
      setIsSyncing(false);
    }
  };

  // Export to Excel / CSV (Ref Image 3 Excel button)
  const handleExportExcel = () => {
    if (leads.length === 0) {
      toast.error('No enquiries to export');
      return;
    }

    const headers = [
      '#',
      'Name',
      'Email',
      'Mobile',
      'Country',
      'Category',
      'Enquiry For',
      'Original Page Title',
      'Website Page URL',
      'Enquiry Date',
      'Assigned Sales Person'
    ];

    const rows = leads.map((l, idx) => [
      idx + 1,
      `"${(l.name || '').replace(/"/g, '""')}"`,
      `"${(l.email || '').replace(/"/g, '""')}"`,
      `"${(l.phone || '').replace(/"/g, '""')}"`,
      `"${(formatCountryName(l.country) || '').replace(/"/g, '""')}"`,
      `"${(l.category || '').replace(/"/g, '""')}"`,
      `"${(l.visa_pathway || l.service_interested || '').replace(/"/g, '""')}"`,
      `"${(l.website_page_title || '').replace(/"/g, '""')}"`,
      `"${(l.website_page_url || '').replace(/"/g, '""')}"`,
      `"${formatDisplayDate(l.created_at || l.enquiry_date)}"`,
      `"${(l.assigned_to_name || 'Unassigned').replace(/"/g, '""')}"`
    ]);

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${activeCategory}_Enquiry_List_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success(`Exported ${leads.length} enquiries to Excel CSV`);
  };

  const handleCopyPhone = (phone, id) => {
    navigator.clipboard.writeText(phone);
    setCopiedPhoneId(id);
    toast.success('Phone copied to clipboard');
    setTimeout(() => setCopiedPhoneId(null), 2000);
  };

  // Available countries under active category
  const activeCategoryCountries = useMemo(() => {
    if (!overview) return [];
    let rawList = [];
    if (activeCategory === 'all') {
      if (overview.all_countries_list && overview.all_countries_list.length > 0) {
        rawList = overview.all_countries_list;
      } else {
        const map = {};
        Object.values(overview.categories || {}).forEach(c => {
          (c.countries_list || []).forEach(item => {
            const cName = formatCountryName(item.country);
            if (!map[cName]) map[cName] = { country: cName, count: 0, unassigned_count: 0 };
            map[cName].count = Math.max(map[cName].count, item.count);
            map[cName].unassigned_count = Math.max(map[cName].unassigned_count, item.unassigned_count);
          });
        });
        return Object.values(map).sort((a, b) => b.count - a.count);
      }
    } else {
      rawList = overview.categories?.[activeCategory]?.countries_list || [];
    }

    const merged = {};
    rawList.forEach(item => {
      const cName = formatCountryName(item.country);
      if (!merged[cName]) {
        merged[cName] = { country: cName, count: 0, unassigned_count: 0 };
      }
      merged[cName].count += item.count;
      merged[cName].unassigned_count += (item.unassigned_count || 0);
    });

    return Object.values(merged).sort((a, b) => b.count - a.count);
  }, [overview, activeCategory]);

  const activeCategoryTotalCount = useMemo(() => {
    if (activeCategory === 'all') {
      return overview?.total_website_leads ?? leads.length;
    }
    return overview?.categories?.[activeCategory]?.count ?? leads.length;
  }, [overview, activeCategory, leads.length]);

  // Active category display titles (Ref Image 3 & 4)
  const currentCategoryMeta = useMemo(() => {
    return CATEGORIES.find(c => c.key === activeCategory) || CATEGORIES[0];
  }, [activeCategory]);

  // Client-side pagination based on entriesPerPage
  const totalPages = Math.ceil(leads.length / entriesPerPage) || 1;
  const paginatedLeads = useMemo(() => {
    const start = (currentPage - 1) * entriesPerPage;
    return leads.slice(start, start + entriesPerPage);
  }, [leads, currentPage, entriesPerPage]);

  return (
    <div className="space-y-4">
      {/* ──────────────────────────────────────────────────────────── */}
      {/* 1. TOP HEADER & BREADCRUMB (REF IMAGE 3) */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="bg-white px-6 py-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <span className="text-slate-400">Welcome Admin</span>
            <span>•</span>
            <span className="text-emerald-700 font-medium">Dashboard</span>
            <span>/</span>
            <span className="text-slate-700 font-semibold">{currentCategoryMeta.enquiryListTitle}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <span>{currentCategoryMeta.enquiryListTitle}</span>
            <Badge variant="outline" className={`text-xs ${currentCategoryMeta.badgeClass} font-semibold`}>
              {leads.length} Records
            </Badge>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            List Of {currentCategoryMeta.enquiryListTitle}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => { fetchOverview(); fetchLeads(); }}
            disabled={listLoading}
            className="text-xs h-8 text-slate-700 hover:text-slate-900"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${listLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 2. CATEGORY TABS SELECTOR (REF IMAGE 2 & 3) */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="bg-white p-2 rounded-xl border border-slate-200 flex flex-wrap items-center gap-1.5">
        {CATEGORIES.map(cat => {
          const isSelected = activeCategory === cat.key;
          const count = cat.key === 'all'
            ? overview?.total_website_leads ?? 0
            : overview?.categories?.[cat.key]?.count ?? 0;
          const unassigned = cat.key === 'all'
            ? overview?.unassigned_count ?? 0
            : overview?.categories?.[cat.key]?.unassigned_count ?? 0;

          return (
            <button
              key={cat.key}
              type="button"
              onClick={() => handleSelectCategory(cat.key)}
              className={`px-3.5 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-2 ${
                isSelected
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <span>{cat.label}</span>
              <Badge
                variant="secondary"
                className={`text-[10px] px-1.5 py-0 ${
                  isSelected ? 'bg-slate-800 text-white border border-slate-700' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {count}
              </Badge>
              {unassigned > 0 && (
                <span className={`w-2 h-2 rounded-full ${isSelected ? 'bg-amber-400' : 'bg-amber-500'}`} title={`${unassigned} unassigned`} />
              )}
            </button>
          );
        })}
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 3. COUNTRY DRILLDOWN FOR SELECTED CATEGORY */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mr-1">
          Country Filter:
        </span>
        <button
          type="button"
          onClick={() => setActiveCountry('all')}
          className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
            activeCountry === 'all'
              ? 'bg-sky-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          All Countries
          <span className="ml-1 opacity-75">
            ({activeCategoryTotalCount})
          </span>
        </button>

        {activeCategoryCountries.map(c => {
          const isSelected = activeCountry.toLowerCase() === c.country.toLowerCase();
          return (
            <button
              key={c.country}
              type="button"
              onClick={() => setActiveCountry(c.country)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                isSelected
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              <span>{c.country}</span>
              <Badge
                variant="secondary"
                className={`text-[10px] px-1.5 py-0 ${
                  isSelected ? 'bg-sky-700 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {c.count}
              </Badge>
            </button>
          );
        })}
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 4. TOOLBAR: SHOW ENTRIES, EXCEL EXPORT & SEARCH (REF IMAGE 3) */}
      {/* ──────────────────────────────────────────────────────────── */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs">
        {/* Left: Show Entries & Excel Export (Ref Image 3) */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span>Show</span>
            <Select
              value={String(entriesPerPage)}
              onValueChange={(val) => setEntriesPerPage(Number(val))}
            >
              <SelectTrigger className="w-18 h-8 text-xs bg-white border-slate-200">
                <SelectValue placeholder="10" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="25">25</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
            <span>entries</span>
          </div>

          {/* Excel Export Button (Ref Image 3) */}
          <Button
            size="sm"
            onClick={handleExportExcel}
            className="h-8 bg-slate-600 hover:bg-slate-700 text-white text-xs font-medium shadow-xs px-3"
            title="Export to Excel / CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
            Excel
          </Button>

          {/* Website DB Sync Button */}
          <Button
            size="sm"
            onClick={() => setShowSyncModal(true)}
            className="h-8 bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium shadow-xs px-3"
            title="Sync leads from live website MySQL database"
          >
            <Database className="w-3.5 h-3.5 mr-1.5 text-sky-200" />
            Sync Website DB
          </Button>

          {/* Assignment Filter */}
          <div className="hidden sm:flex items-center gap-1 border border-slate-200 p-0.5 rounded-lg bg-slate-50 text-xs ml-2">
            <button
              type="button"
              onClick={() => setAssignmentFilter('all')}
              className={`px-2 py-0.5 rounded-md text-[11px] transition-colors ${
                assignmentFilter === 'all'
                  ? 'bg-white text-slate-900 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => setAssignmentFilter('unassigned')}
              className={`px-2 py-0.5 rounded-md text-[11px] transition-colors ${
                assignmentFilter === 'unassigned'
                  ? 'bg-amber-500 text-white font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Unassigned
            </button>
            <button
              type="button"
              onClick={() => setAssignmentFilter('assigned')}
              className={`px-2 py-0.5 rounded-md text-[11px] transition-colors ${
                assignmentFilter === 'assigned'
                  ? 'bg-white text-slate-900 font-semibold shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Assigned
            </button>
          </div>
        </div>

        {/* Right: Search Box (Ref Image 3) */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-600 font-medium">Search:</span>
          <div className="relative w-64">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search name, phone, email..."
              className="text-xs h-8 pr-7"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 5. ENQUIRY TABLE (MATCHING REF IMAGE 3) */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Card className="border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-3 w-12 text-center text-slate-500 font-mono">#</th>
                <th className="py-3 px-3 font-semibold">Name</th>
                <th className="py-3 px-3 font-semibold">Email</th>
                <th className="py-3 px-3 font-semibold">Mobile</th>
                <th className="py-3 px-3 font-semibold">Country</th>
                <th className="py-3 px-3 font-semibold min-w-[160px]">Enquiry For</th>
                <th className="py-3 px-3 font-semibold min-w-[200px]">Original Website Page</th>
                <th className="py-3 px-3 font-semibold whitespace-nowrap">Enquiry Date</th>
                <th className="py-3 px-3 font-semibold min-w-[170px]">Sales Person Assignment</th>
                <th className="py-3 px-3 text-center w-24 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {listLoading ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
                    Loading enquiries...
                  </td>
                </tr>
              ) : paginatedLeads.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center">
                    <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
                      <Globe className="w-6 h-6" />
                    </div>
                    <div className="text-sm font-semibold text-slate-900">No enquiries found</div>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                      No records match the category <strong>{activeCategory}</strong>
                      {activeCountry !== 'all' ? ` for ${activeCountry}` : ''}
                      {searchQuery ? ` matching "${searchQuery}"` : ''}.
                    </p>
                  </td>
                </tr>
              ) : (
                paginatedLeads.map((lead, index) => {
                  const globalIndex = (currentPage - 1) * entriesPerPage + index + 1;
                  const isUnassigned = lead.is_unassigned;

                  return (
                    <tr
                      key={lead.id}
                      className="hover:bg-slate-50/70 transition-colors"
                    >
                      {/* # (Ref Image 3) */}
                      <td className="py-3 px-3 text-center align-middle font-mono text-slate-500 font-medium">
                        {globalIndex}
                      </td>

                      {/* Name (Ref Image 3) */}
                      <td className="py-3 px-3 align-middle font-medium text-slate-900">
                        <button
                          type="button"
                          onClick={() => setViewingLead(lead)}
                          className="hover:text-cyan-700 hover:underline text-left font-semibold text-slate-900 block"
                          title="Click to view details"
                        >
                          {lead.name || 'Unknown Client'}
                        </button>
                        {lead.lead_number && (
                          <span className="text-[10px] text-slate-400 font-mono">
                            #{lead.lead_number}
                          </span>
                        )}
                      </td>

                      {/* Email (Ref Image 3) */}
                      <td className="py-3 px-3 align-middle text-slate-600 truncate max-w-[200px]">
                        {lead.email || '-'}
                      </td>

                      {/* Mobile (Ref Image 3) */}
                      <td className="py-3 px-3 align-middle text-slate-700 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 font-mono">
                          <span>{formatPhoneNumber(lead.phone)}</span>
                          {lead.phone && (
                            <button
                              type="button"
                              onClick={() => handleCopyPhone(lead.phone, lead.id)}
                              className="text-slate-400 hover:text-slate-600"
                              title="Copy phone"
                            >
                              {copiedPhoneId === lead.id ? (
                                <Check className="w-3 h-3 text-emerald-600" />
                              ) : (
                                <Copy className="w-2.5 h-2.5" />
                              )}
                            </button>
                          )}
                        </div>
                      </td>

                      {/* Country */}
                      <td className="py-3 px-3 align-middle">
                        <Badge
                          variant="outline"
                          className={`text-[11px] font-semibold ${getCountryBadgeColor(lead.country)}`}
                        >
                          {formatCountryName(lead.country)}
                        </Badge>
                      </td>

                      {/* Enquiry For (Ref Image 3) */}
                      <td className="py-3 px-3 align-middle text-slate-800 font-medium">
                        <div className="line-clamp-2">
                          {lead.visa_pathway || lead.service_interested || 'Migration Inquiry'}
                        </div>
                        {lead.resume_file_id || lead.resume_url ? (
                          <div className="mt-1">
                            <a
                              href={`${API}/cockpit/resume/${lead.resume_file_id || lead.id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 rounded shadow-none"
                              title={`View ${lead.resume_filename || 'Candidate Resume'}`}
                            >
                              <FileText className="w-3 h-3 text-emerald-600" /> Resume Attached
                            </a>
                          </div>
                        ) : (
                          <div className="mt-1">
                            <label
                              onClick={(e) => e.stopPropagation()}
                              className="cursor-pointer inline-flex items-center gap-1 text-[10px] font-semibold text-slate-500 hover:text-emerald-700 bg-slate-50 hover:bg-emerald-50 border border-slate-200 hover:border-emerald-200 px-1.5 py-0.5 rounded transition-colors"
                              title="Attach candidate resume"
                            >
                              <Upload className="w-2.5 h-2.5" />
                              <span>{uploadingResumeId === (lead.id || lead._id) ? 'Uploading...' : '+ Attach CV'}</span>
                              <input
                                type="file"
                                accept=".pdf,.doc,.docx,.txt"
                                className="hidden"
                                disabled={uploadingResumeId === (lead.id || lead._id)}
                                onChange={(e) => {
                                  if (e.target.files?.[0]) {
                                    handleResumeUpload(lead, e.target.files[0]);
                                    e.target.value = '';
                                  }
                                }}
                              />
                            </label>
                          </div>
                        )}
                      </td>

                      {/* Original Website Page */}
                      <td className="py-3 px-3 align-middle">
                        <div className="space-y-0.5 max-w-[240px]">
                          <div className="font-medium text-slate-800 line-clamp-1 text-[11px]">
                            {lead.website_page_title || 'LEAMSS Official Page'}
                          </div>
                          {lead.website_page_url ? (
                            <a
                              href={lead.website_page_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[10px] text-sky-600 hover:text-sky-800 hover:underline flex items-center gap-1 truncate"
                              title={lead.website_page_url}
                            >
                              <span className="truncate">{lead.website_page_url}</span>
                              <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                            </a>
                          ) : (
                            <span className="text-[10px] text-slate-400 italic">No URL</span>
                          )}
                        </div>
                      </td>

                      {/* Enquiry Date (Ref Image 3) */}
                      <td className="py-3 px-3 align-middle whitespace-nowrap text-slate-700">
                        {formatDisplayDate(lead.created_at || lead.enquiry_date)}
                      </td>

                      {/* Sales Person Assignment */}
                      <td className="py-3 px-3 align-middle">
                        {isUnassigned ? (
                          <div className="space-y-1">
                            <Badge className="bg-amber-100 text-amber-800 border-amber-200 font-medium text-[10px] py-0">
                              ● Unassigned
                            </Badge>
                            <Select
                              disabled={assigningLeadId === lead.id}
                              onValueChange={(val) => handleAssignLead(lead.id, val)}
                            >
                              <SelectTrigger className="h-6 text-[11px] bg-white border-amber-300 text-slate-700 w-full focus:ring-emerald-500">
                                <SelectValue placeholder="Assign Sales Rep" />
                              </SelectTrigger>
                              <SelectContent>
                                {allSalesReps.map((rep) => (
                                  <SelectItem key={rep.id} value={rep.id} className="text-xs">
                                    {rep.name} {rep.role ? `(${rep.role})` : ''}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        ) : (
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1 text-slate-800 font-semibold text-xs">
                              <UserCheck className="w-3 h-3 text-emerald-600 shrink-0" />
                              <span className="truncate">{lead.assigned_to_name}</span>
                            </div>
                            <Select
                              disabled={assigningLeadId === lead.id}
                              onValueChange={(val) => handleAssignLead(lead.id, val)}
                            >
                              <SelectTrigger className="h-5 text-[10px] bg-slate-50 border-slate-200 text-slate-500 w-full py-0">
                                <SelectValue placeholder="Re-assign..." />
                              </SelectTrigger>
                              <SelectContent>
                                {allSalesReps.map((rep) => (
                                  <SelectItem key={rep.id} value={rep.id} className="text-xs">
                                    {rep.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        )}
                      </td>

                      {/* Actions: Red Trash Icon & Cyan Eye Icon (Ref Image 3) */}
                      <td className="py-3 px-3 align-middle text-center whitespace-nowrap">
                        <div className="flex items-center justify-center gap-2">
                          {/* Trash Icon (Red) */}
                          <button
                            type="button"
                            onClick={() => setDeletingLead(lead)}
                            className="p-1 rounded text-rose-500 hover:text-rose-700 hover:bg-rose-50 transition-colors"
                            title="Delete enquiry"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>

                          {/* Eye Icon (Cyan/Teal - Ref Image 3) */}
                          <button
                            type="button"
                            onClick={() => setViewingLead(lead)}
                            className="p-1 rounded text-cyan-600 hover:text-cyan-800 hover:bg-cyan-50 transition-colors"
                            title="View enquiry details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer: Pagination controls */}
        {leads.length > entriesPerPage && (
          <div className="bg-slate-50/70 px-4 py-3 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-500">
            <div>
              Showing {Math.min((currentPage - 1) * entriesPerPage + 1, leads.length)} to{' '}
              {Math.min(currentPage * entriesPerPage, leads.length)} of {leads.length} entries
            </div>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="h-7 px-2 text-xs"
              >
                <ChevronLeft className="w-3.5 h-3.5 mr-0.5" />
                Previous
              </Button>
              <span className="px-2 text-slate-700 font-semibold">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="h-7 px-2 text-xs"
              >
                Next
                <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 6. GENERAL ENQUIRY DETAILS MODAL (MATCHING REF IMAGE 4) */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Dialog open={!!viewingLead} onOpenChange={(open) => { if (!open) setViewingLead(null); }}>
        <DialogContent className="max-w-xl p-0 overflow-hidden rounded-xl border border-slate-200 shadow-xl">
          <DialogHeader className="px-6 pt-5 pb-3 border-b border-slate-100 bg-white">
            <DialogTitle className="text-xl font-bold text-slate-900 tracking-tight">
              {viewingLead ? `${viewingLead.category || 'General'} Enquiry Details` : 'Enquiry Details'}
            </DialogTitle>
          </DialogHeader>

          {viewingLead && (
            <div className="p-6 bg-white space-y-4">
              {/* Structured Key : Value Display (Ref Image 4) */}
              <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100 text-sm">
                {/* Name */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-slate-50/50">
                  <div className="col-span-4 font-bold text-slate-800">Name</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 font-medium text-slate-900">{viewingLead.name || '-'}</div>
                </div>

                {/* Mobile */}
                <div className="grid grid-cols-12 px-4 py-2.5">
                  <div className="col-span-4 font-bold text-slate-800">Mobile</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 font-mono text-slate-900 flex items-center gap-2">
                    <span>{formatPhoneNumber(viewingLead.phone)}</span>
                    {viewingLead.phone && (
                      <button
                        type="button"
                        onClick={() => handleCopyPhone(viewingLead.phone, 'modal')}
                        className="text-slate-400 hover:text-slate-600 text-xs"
                      >
                        {copiedPhoneId === 'modal' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                </div>

                {/* Email */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-slate-50/50">
                  <div className="col-span-4 font-bold text-slate-800">Email</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 text-slate-900 break-all">{viewingLead.email || '-'}</div>
                </div>

                {/* Qualification */}
                <div className="grid grid-cols-12 px-4 py-2.5">
                  <div className="col-span-4 font-bold text-slate-800">Qualification</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 text-slate-900">
                    {viewingLead.latest_qualification || viewingLead.qualification || 'Masters / Bachelor'}
                  </div>
                </div>

                {/* Country */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-slate-50/50">
                  <div className="col-span-4 font-bold text-slate-800">Country</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 font-medium text-slate-900">{formatCountryName(viewingLead.country)}</div>
                </div>

                {/* Services */}
                <div className="grid grid-cols-12 px-4 py-2.5">
                  <div className="col-span-4 font-bold text-slate-800">Services</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 font-medium text-slate-900">
                    {viewingLead.service_interested || viewingLead.visa_pathway || 'PR Australia'}
                  </div>
                </div>

                {/* Work Experience */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-slate-50/50">
                  <div className="col-span-4 font-bold text-slate-800">Work Experience</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 text-slate-900">
                    {viewingLead.total_work_experience || viewingLead.work_experience || '3+ years'}
                  </div>
                </div>

                {/* Attached Resume */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-emerald-50/40 items-center">
                  <div className="col-span-4 font-bold text-slate-800 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-emerald-600" /> Attached Resume
                  </div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7">
                    <div className="flex flex-wrap items-center gap-2">
                      {viewingLead.resume_file_id || viewingLead.resume_url ? (
                        <>
                          <a
                            href={`${API}/cockpit/resume/${viewingLead.resume_file_id || viewingLead.id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
                          >
                            <Eye className="w-3.5 h-3.5" /> View / Download ({viewingLead.resume_filename || 'Candidate Resume'})
                          </a>
                          <label className="cursor-pointer inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded border border-emerald-300 bg-white hover:bg-emerald-50 text-emerald-700 shadow-sm transition-colors">
                            <Upload className="w-3 h-3" />
                            <span>{uploadingResumeId === (viewingLead.id || viewingLead._id) ? 'Uploading...' : 'Replace Resume'}</span>
                            <input
                              type="file"
                              accept=".pdf,.doc,.docx,.txt"
                              className="hidden"
                              disabled={uploadingResumeId === (viewingLead.id || viewingLead._id)}
                              onChange={(e) => {
                                if (e.target.files?.[0]) {
                                  handleResumeUpload(viewingLead, e.target.files[0]);
                                  e.target.value = '';
                                }
                              }}
                            />
                          </label>
                        </>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-slate-400 italic text-xs">No resume attached</span>
                          <label className="cursor-pointer inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors">
                            <Upload className="w-3 h-3" />
                            <span>{uploadingResumeId === (viewingLead.id || viewingLead._id) ? 'Uploading...' : 'Upload / Attach Resume'}</span>
                            <input
                              type="file"
                              accept=".pdf,.doc,.docx,.txt"
                              className="hidden"
                              disabled={uploadingResumeId === (viewingLead.id || viewingLead._id)}
                              onChange={(e) => {
                                if (e.target.files?.[0]) {
                                  handleResumeUpload(viewingLead, e.target.files[0]);
                                  e.target.value = '';
                                }
                              }}
                            />
                          </label>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Message */}
                <div className="grid grid-cols-12 px-4 py-2.5">
                  <div className="col-span-4 font-bold text-slate-800">Message</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 text-slate-700 italic">
                    {viewingLead.message || 'Call me to discuss migration eligibility and visa criteria'}
                  </div>
                </div>

                {/* Enquired For */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-slate-50/50">
                  <div className="col-span-4 font-bold text-slate-800">Enquired For</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 font-semibold text-emerald-800">
                    {viewingLead.enquired_for || viewingLead.visa_pathway || viewingLead.service_interested || 'General Consultation'}
                  </div>
                </div>

                {/* Original Page Title */}
                <div className="grid grid-cols-12 px-4 py-2.5">
                  <div className="col-span-4 font-bold text-slate-800">Page Title</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 text-slate-900 font-medium">
                    {viewingLead.website_page_title || 'Find Your Migration Pathway in 60 Seconds - LEAMSS'}
                  </div>
                </div>

                {/* Website Page URL */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-slate-50/50">
                  <div className="col-span-4 font-bold text-slate-800">Page URL</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 text-sky-600 break-all">
                    {viewingLead.website_page_url ? (
                      <a
                        href={viewingLead.website_page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline flex items-center gap-1 text-xs"
                      >
                        <span>{viewingLead.website_page_url}</span>
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                    ) : (
                      'https://leamss.com/start'
                    )}
                  </div>
                </div>

                {/* Enquired On */}
                <div className="grid grid-cols-12 px-4 py-2.5">
                  <div className="col-span-4 font-bold text-slate-800">Enquired On</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 font-medium text-slate-900">
                    {formatDisplayDate(viewingLead.created_at || viewingLead.enquiry_date)}
                  </div>
                </div>

                {/* Assigned Sales Person */}
                <div className="grid grid-cols-12 px-4 py-2.5 bg-slate-50/50">
                  <div className="col-span-4 font-bold text-slate-800">Assigned To</div>
                  <div className="col-span-1 text-slate-400 font-bold">:</div>
                  <div className="col-span-7 flex items-center gap-2">
                    {viewingLead.is_unassigned ? (
                      <Badge className="bg-amber-100 text-amber-800 border-amber-200">
                        ● Unassigned
                      </Badge>
                    ) : (
                      <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200 font-semibold">
                        {viewingLead.assigned_to_name}
                      </Badge>
                    )}
                    <Select
                      disabled={assigningLeadId === viewingLead.id}
                      onValueChange={(val) => handleAssignLead(viewingLead.id, val)}
                    >
                      <SelectTrigger className="h-7 text-xs bg-white border-slate-300 w-44">
                        <SelectValue placeholder="Assign Sales Rep" />
                      </SelectTrigger>
                      <SelectContent>
                        {allSalesReps.map((rep) => (
                          <SelectItem key={rep.id} value={rep.id} className="text-xs">
                            {rep.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Modal Footer (Ref Image 4 Close Button) */}
          <DialogFooter className="px-6 py-3.5 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
            <div>
              {onOpenLeadWorkspace && viewingLead && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const lead = viewingLead;
                    setViewingLead(null);
                    onOpenLeadWorkspace(lead);
                  }}
                  className="text-xs text-slate-700"
                >
                  <ArrowUpRight className="w-3.5 h-3.5 mr-1" />
                  Open Full CRM Workspace
                </Button>
              )}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setViewingLead(null)}
              className="text-xs px-4"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 7. DELETE CONFIRMATION MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Dialog open={!!deletingLead} onOpenChange={(open) => { if (!open) setDeletingLead(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-rose-700 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-rose-600" />
              Delete Website Enquiry
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500 mt-1">
              Are you sure you want to delete the enquiry for <strong>{deletingLead?.name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="gap-2 sm:gap-0 mt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeletingLead(null)}
              disabled={isDeleting}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleDeleteLead}
              disabled={isDeleting}
              className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium"
            >
              {isDeleting ? 'Deleting...' : 'Delete Enquiry'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* 8. DATABASE SYNC & IMPORT MODAL */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Dialog open={showSyncModal} onOpenChange={setShowSyncModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Database className="w-5 h-5 text-sky-600" />
              Sync Website Leads Database
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500 mt-1">
              Synchronize leads from your live website database (<code>hosldwuh_staging</code>) or paste exported records from phpMyAdmin.
            </DialogDescription>
          </DialogHeader>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-200 mt-2 gap-2">
            <button
              type="button"
              onClick={() => setSyncTab('live_url')}
              className={`pb-2 px-3 text-xs font-semibold border-b-2 transition-colors ${
                syncTab === 'live_url'
                  ? 'border-sky-600 text-sky-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Live Website URL (Recommended)
            </button>
            <button
              type="button"
              onClick={() => setSyncTab('mysql')}
              className={`pb-2 px-3 text-xs font-semibold border-b-2 transition-colors ${
                syncTab === 'mysql'
                  ? 'border-sky-600 text-sky-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Direct MySQL Sync
            </button>
            <button
              type="button"
              onClick={() => setSyncTab('json')}
              className={`pb-2 px-3 text-xs font-semibold border-b-2 transition-colors ${
                syncTab === 'json'
                  ? 'border-sky-600 text-sky-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Paste phpMyAdmin JSON
            </button>
            <button
              type="button"
              onClick={() => setSyncTab('webhook')}
              className={`pb-2 px-3 text-xs font-semibold border-b-2 transition-colors ${
                syncTab === 'webhook'
                  ? 'border-sky-600 text-sky-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              Laravel Controller Code
            </button>
          </div>

          {/* Tab 0: Live Website URL (Recommended) */}
          {syncTab === 'live_url' && (
            <div className="space-y-3 py-3 text-xs">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-900 text-[11px] leading-relaxed">
                <strong>Zero-Configuration Sync:</strong> Add the small 5-line route to your <code>routes/web.php</code> on <code>leamss.com</code>, then click the button below to fetch all leads directly over standard HTTPS!
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-700 mb-1">Live Website Route URL:</label>
                <Input
                  value={liveWebsiteUrl}
                  onChange={(e) => setLiveWebsiteUrl(e.target.value)}
                  className="h-8 text-xs bg-white font-mono"
                  placeholder="https://leamss.com/api/crm-website-leads-export"
                />
              </div>

              <div className="flex justify-end pt-1">
                <Button
                  size="sm"
                  onClick={handleSyncUrl}
                  disabled={isSyncing}
                  className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-4"
                >
                  {isSyncing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      Fetching Leads from Website...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                      Fetch & Sync Leads Now
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* Tab 1: Direct MySQL */}
          {syncTab === 'mysql' && (
            <div className="space-y-3 py-3 text-xs">
              <div className="p-3 bg-sky-50 border border-sky-100 rounded-lg text-sky-800 text-[11px] leading-relaxed">
                Enter your cPanel MySQL user credentials for database <strong>hosldwuh_staging</strong>. Both <strong>general_enquiries</strong> and <strong>popup_enquiries</strong> will be automatically fetched and classified.
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-slate-700 mb-1">Server Host</label>
                  <Input
                    value={mysqlCreds.host}
                    onChange={(e) => setMysqlCreds({ ...mysqlCreds, host: e.target.value })}
                    className="h-8 text-xs bg-white"
                    placeholder="leader.herosite.pro"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-700 mb-1">Database Name</label>
                  <Input
                    value={mysqlCreds.database}
                    onChange={(e) => setMysqlCreds({ ...mysqlCreds, database: e.target.value })}
                    className="h-8 text-xs bg-white"
                    placeholder="hosldwuh_staging"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-700 mb-1">Database Username *</label>
                  <Input
                    value={mysqlCreds.user}
                    onChange={(e) => setMysqlCreds({ ...mysqlCreds, user: e.target.value })}
                    className="h-8 text-xs bg-white"
                    placeholder="e.g. hosldwuh_admin"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-700 mb-1">Database Password *</label>
                  <Input
                    type="password"
                    value={mysqlCreds.password}
                    onChange={(e) => setMysqlCreds({ ...mysqlCreds, password: e.target.value })}
                    className="h-8 text-xs bg-white"
                    placeholder="••••••••••••"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  size="sm"
                  onClick={handleSyncMysql}
                  disabled={isSyncing}
                  className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-4"
                >
                  {isSyncing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      Syncing with MySQL...
                    </>
                  ) : (
                    <>
                      <Database className="w-3.5 h-3.5 mr-1.5" />
                      Connect & Sync All Enquiries
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* Tab 2: Paste phpMyAdmin JSON */}
          {syncTab === 'json' && (
            <div className="space-y-3 py-3 text-xs">
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-[11px] leading-relaxed">
                <strong>Fast 1-Click Import:</strong> In phpMyAdmin, click <code>general_enquiries</code> or <code>popup_enquiries</code> &rarr; click <strong>Export</strong> tab &rarr; choose <strong>JSON</strong> format &rarr; click <strong>Go</strong>. Open the file, copy all and paste below!
              </div>

              <div className="flex items-center gap-3">
                <label className="text-[11px] font-semibold text-slate-700">Table Type:</label>
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    name="table_type"
                    checked={jsonTableType === 'general_enquiries'}
                    onChange={() => setJsonTableType('general_enquiries')}
                  />
                  <span>general_enquiries (Migrate Form)</span>
                </label>
                <label className="flex items-center gap-1 cursor-pointer">
                  <input
                    type="radio"
                    name="table_type"
                    checked={jsonTableType === 'popup_enquiries'}
                    onChange={() => setJsonTableType('popup_enquiries')}
                  />
                  <span>popup_enquiries (Popup Consultations)</span>
                </label>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-700 mb-1">Paste JSON Array:</label>
                <textarea
                  value={jsonRowsText}
                  onChange={(e) => setJsonRowsText(e.target.value)}
                  rows={6}
                  placeholder='[ { "id": 1, "name": "John Doe", "phone": "9876543210", "email": "john@example.com", "services": "PR Australia", ... } ]'
                  className="w-full p-2.5 text-xs font-mono border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-sky-500 bg-white"
                />
              </div>

              <div className="flex justify-end pt-1">
                <Button
                  size="sm"
                  onClick={handleImportJson}
                  disabled={isSyncing}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4"
                >
                  {isSyncing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      Importing Records...
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5 mr-1.5" />
                      Import Enquiries into CRM
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {/* Tab 3: Laravel Webhook Guide */}
          {syncTab === 'webhook' && (
            <div className="space-y-3 py-3 text-xs">
              <p className="text-slate-600 text-[11px]">
                To automatically send every new enquiry to this CRM in real-time when a visitor submits the form on <code>https://leamss.com</code>, add this snippet to <code>GeneralEnquiryController.php</code>:
              </p>
              <pre className="p-3 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-x-auto max-h-48">
{`use Illuminate\\Support\\Facades\\Http;

// Inside store() right after GeneralEnquiry::create([...])
try {
    Http::timeout(3)->post('https://api.leamss.com/api/crm/website-leads/capture', [
        'name'               => $request->name,
        'phone'              => $request->phone,
        'email'              => $request->email,
        'country'            => $request->country,
        'services'           => $request->services,
        'qualification'      => $request->qualification,
        'work_exp'           => $request->work_exp,
        'msg'                => $request->msg,
        'enquired_for'       => $request->enquired_for ?? 'Migrate',
        'website_page_title' => 'Migrate Abroad - LEAMSS',
        'website_page_url'   => url()->previous() ?? 'https://leamss.com/migrate',
        'source'             => 'Website'
    ]);
} catch (\\Exception $e) {
    \\Log::warning('CRM push notice: ' . $e->getMessage());
}`}
              </pre>

              <p className="text-slate-600 text-[11px] font-semibold pt-2">
                For Migration Atlas & Points Calculator (in <code>web.php</code> or Controller):
              </p>
              <pre className="p-3 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-x-auto max-h-48">
{`use Illuminate\\Support\\Facades\\Http;

// When visitor submits Atlas occupation consultation or /start calculator:
try {
    Http::timeout(3)->post('https://api.leamss.com/api/crm/website-leads/capture', [
        'name'               => $request->name,
        'email'              => $request->email,
        'phone'              => $request->phone ?? $request->mobile,
        'country'            => $request->country ?? 'Australia',
        'enquired_for'       => $request->enquired_for ?? ($request->atlas_title ? $request->atlas_title . ' (' . ($request->atlas_code ?? '') . ')' : 'Immigration Points Calculator'),
        'service_interested' => $request->services ?? 'Migration Atlas',
        'qualification'      => $request->qualification ?? '',
        'work_exp'           => $request->work_exp ?? '',
        'msg'                => $request->msg ?? $request->message ?? '',
        'atlas_code'         => $request->atlas_code ?? null,
        'atlas_title'        => $request->atlas_title ?? null,
        'lead_category'      => 'ATLAS',
        'website_page_title' => $request->website_page_title ?? ($request->atlas_title ? $request->atlas_title . ' - Migration Atlas | LEAMSS' : 'Free Immigration Points Calculator - LEAMSS'),
        'website_page_url'   => url()->previous() ?? url()->current() ?? 'https://leamss.com/start',
        'source'             => 'public_atlas'
    ]);
} catch (\\Exception $e) {
    \\Log::warning('Atlas CRM push notice: ' . $e->getMessage());
}`}
              </pre>
            </div>
          )}

          <DialogFooter className="border-t border-slate-100 pt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSyncModal(false)}
              className="text-xs"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
