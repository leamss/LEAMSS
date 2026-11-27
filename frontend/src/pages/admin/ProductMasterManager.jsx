import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import {
  ArrowLeft, Plus, Search, Sparkles, Globe, Briefcase, TrendingUp,
  AlertCircle, CheckCircle2, ShieldCheck, ExternalLink, ListChecks,
  DollarSign, BookOpen, Trash2, Save, Copy, RefreshCw, FileText,
  Layers, Package, CheckCircle, Clock, Eye, SlidersHorizontal, UserCheck,
  ChevronRight, Zap, RotateCcw
} from 'lucide-react';

import Flag from 'react-world-flags';
import ProductAiResearchModal from '@/components/admin/ProductAiResearchModal';
import EligibilityTab from '@/components/admin/product-master/EligibilityTab';
import TimelineChecklistTab from '@/components/admin/product-master/TimelineChecklistTab';
import GovernmentCostsTab from '@/components/admin/product-master/GovernmentCostsTab';
import LEAMSSPricingTab from '@/components/admin/product-master/LEAMSSPricingTab';
import SalesPlaybookTab from '@/components/admin/product-master/SalesPlaybookTab';
import SalesPerspectiveView from '@/components/admin/product-master/SalesPerspectiveView';
import CaseManagerPerspectiveView from '@/components/admin/product-master/CaseManagerPerspectiveView';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ISO_CODES = {
  argentina: 'AR', australia: 'AU', austria: 'AT', bahrain: 'BH', belgium: 'BE', brazil: 'BR',
  canada: 'CA', chile: 'CL', china: 'CN', colombia: 'CO', costa_rica: 'CR', czech_republic: 'CZ',
  denmark: 'DK', egypt: 'EG', finland: 'FI', france: 'FR', germany: 'DE', greece: 'GR', hong_kong: 'HK',
  india: 'IN', indonesia: 'ID', ireland: 'IE', italy: 'IT', japan: 'JP', kenya: 'KE', malaysia: 'MY',
  mauritius: 'MU', mexico: 'MX', netherlands: 'NL', new_zealand: 'NZ', nigeria: 'NG', norway: 'NO',
  oman: 'OM', panama: 'PA', philippines: 'PH', poland: 'PL', portugal: 'PT', qatar: 'QA',
  saudi_arabia: 'SA', singapore: 'SG', south_africa: 'ZA', south_korea: 'KR', spain: 'ES',
  sweden: 'SE', switzerland: 'CH', thailand: 'TH', turkey: 'TR', uae: 'AE', uk: 'GB', united_kingdom: 'GB',
  usa: 'US', united_states: 'US', vietnam: 'VN',
};

const getISO = (nameOrCode) => {
  if (!nameOrCode) return 'UN';
  const clean = nameOrCode.toLowerCase().replace(/[\s_-]+/g, '_');
  return ISO_CODES[clean] || (nameOrCode.length === 2 ? nameOrCode.toUpperCase() : 'UN');
};

const CATEGORY_META = {
  skilled_migration: { name: 'Skilled Migration / PR', icon: '🌟', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  pr: { name: 'Skilled Migration / PR', icon: '🌟', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  work: { name: 'Work Visas', icon: '💼', badge: 'bg-blue-50 text-blue-700 border-blue-200' },
  student: { name: 'Student Visas', icon: '🎓', badge: 'bg-purple-50 text-purple-700 border-purple-200' },
  visitor: { name: 'Visitor Visas', icon: '✈️', badge: 'bg-amber-50 text-amber-700 border-amber-200' },
  family: { name: 'Family & Partner', icon: '👨‍👩‍👧', badge: 'bg-rose-50 text-rose-700 border-rose-200' },
  partner: { name: 'Family & Partner', icon: '👨‍👩‍👧', badge: 'bg-rose-50 text-rose-700 border-rose-200' },
  business: { name: 'Business & Investor', icon: '🏢', badge: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  investor: { name: 'Business & Investor', icon: '🏢', badge: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  immigration: { name: 'Skilled Migration / PR', icon: '🌟', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  residence: { name: 'Skilled Migration / PR', icon: '🌟', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
};

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

export default function ProductMasterManager() {
  const navigate = useNavigate();

  // Current user detection
  const currentUser = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem('user') || '{}');
    } catch {
      return {};
    }
  }, []);

  const isAdmin = currentUser.role === 'admin' || currentUser.role === 'super_admin' || currentUser.role === 'admin_owner' || (currentUser.permissions || []).includes('product_cost.manage.any') || (currentUser.permissions || []).includes('system.user_manage.any');
  const isSales = currentUser.role === 'salesperson' || currentUser.role === 'sales' || (currentUser.permissions || []).includes('lead.view.own');
  const isCaseManager = currentUser.role === 'case_manager' || (currentUser.permissions || []).includes('case.view.own');

  // Role perspective: 'admin' | 'sales' | 'cm'
  const [viewMode, setViewMode] = useState(() => {
    if (isAdmin) return 'admin';
    if (isCaseManager) return 'cm';
    return 'sales';
  });

  // Strict role enforcement: Non-admins can NEVER view or edit in admin mode
  const effectiveViewMode = isAdmin ? viewMode : (isCaseManager ? 'cm' : 'sales');

  useEffect(() => {
    if (!isAdmin && isSales) {
      navigate('/sales/pitch-guide', { replace: true });
    }
  }, [isAdmin, isSales, navigate]);

  const [items, setItems] = useState([]);
  const [taxonomyCountries, setTaxonomyCountries] = useState([]);
  const [stats, setStats] = useState({ total: 0, active: 0, draft: 0, archived: 0, verified: 0, countries_count: 0 });
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedProductData, setSelectedProductData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Hierarchical Progressive Drill-Down Navigation:
  // Step 1: 'countries' -> Step 2: 'categories' -> Step 3: 'subclasses' -> Step 4: 'detail'
  const [navStep, setNavStep] = useState('countries');
  const [selectedCountry, setSelectedCountry] = useState('Australia');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Modals
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [newDialogOpen, setNewDialogOpen] = useState(false);

  const token = localStorage.getItem('token');
  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [listRes, statsRes, taxRes] = await Promise.all([
        axios.get(`${API}/product-master?include_archived=true`, { headers: authHeaders }),
        axios.get(`${API}/product-master/summary-stats`, { headers: authHeaders }),
        axios.get(`${API}/product-master/taxonomy`, { headers: authHeaders }),
      ]);
      const fetchedItems = listRes.data?.items || [];
      const countriesList = taxRes.data?.countries || [];
      setItems(fetchedItems);
      setStats(statsRes.data || {});
      setTaxonomyCountries(countriesList);

      // Determine initial selection
      if (countriesList.length > 0) {
        const hasAus = countriesList.find((c) => c.name.toLowerCase() === 'australia');
        const initialCountry = hasAus ? 'Australia' : countriesList[0].name;
        setSelectedCountry((prev) => prev || initialCountry);

        if (!selectedId) {
          const countryItems = fetchedItems.filter(
            (it) => it.country?.toLowerCase() === (hasAus ? 'australia' : initialCountry.toLowerCase()) && it.status !== 'archived'
          );
          if (countryItems.length > 0) {
            setSelectedId(countryItems[0].id);
          } else if (fetchedItems.length > 0) {
            setSelectedId(fetchedItems[0].id);
          }
        }
      } else if (!selectedId && fetchedItems.length > 0) {
        setSelectedId(fetchedItems[0].id);
      }
    } catch (err) {
      console.error('Failed to load product masters:', err);
      toast.error('Failed to load Product Master records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []); // eslint-disable-line

  // Fetch full single product detail when selectedId changes
  useEffect(() => {
    if (!selectedId) {
      setSelectedProductData(null);
      return;
    }
    let cancelled = false;
    const fetchDetail = async () => {
      setDetailLoading(true);
      try {
        const res = await axios.get(`${API}/product-master/${selectedId}`, { headers: authHeaders });
        if (!cancelled) {
          setSelectedProductData(res.data);
          // Sync selected country and category to match active product if changed externally
          if (res.data?.country && res.data.country !== selectedCountry && !search.trim()) {
            setSelectedCountry(res.data.country);
          }
        }
      } catch (err) {
        console.error('Failed to fetch product master detail:', err);
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    };
    fetchDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedId, authHeaders]); // eslint-disable-line

  const handleDetailSaved = async (savedId, savedProduct) => {
    const targetId = savedId || selectedId;
    if (savedProduct) {
      setSelectedProductData(savedProduct);
    }
    await loadData();
    if (targetId) {
      try {
        const res = await axios.get(`${API}/product-master/${targetId}`, { headers: authHeaders });
        setSelectedProductData(res.data);
      } catch (err) {
        console.error('Failed to refresh product detail after save:', err);
      }
    }
  };

  // Active Country metadata
  const currentCountryObj = useMemo(() => {
    return taxonomyCountries.find(
      (c) => c.name?.toLowerCase() === (selectedCountry || '').toLowerCase()
    ) || taxonomyCountries[0] || null;
  }, [taxonomyCountries, selectedCountry]);

  // Categories available for the currently selected country
  const countryCategories = useMemo(() => {
    if (!currentCountryObj?.categories) return [];
    return Object.values(currentCountryObj.categories);
  }, [currentCountryObj]);

  // Helper to get subclasses under a specific category in current country
  const getSubclassesForCategory = (catId) => {
    return items.filter(
      (it) =>
        it.country?.toLowerCase() === currentCountryObj?.name?.toLowerCase() &&
        it.status !== 'archived' &&
        (catId === 'all' || it.category === catId || (catId === 'skilled_migration' && it.category === 'pr'))
    );
  };

  // Sibling subclasses under the same country & category for quick-switching in detail view
  const siblingSubclasses = useMemo(() => {
    if (!selectedProductData) return [];
    return items.filter(
      (it) =>
        it.country?.toLowerCase() === selectedProductData.country?.toLowerCase() &&
        it.status !== 'archived' &&
        (selectedCategory === 'all' || it.category === selectedProductData.category)
    );
  }, [items, selectedProductData, selectedCategory]);

  const uniqueCountries = useMemo(() => {
    if (taxonomyCountries?.length > 0) return taxonomyCountries.map((c) => c.name);
    const set = new Set();
    items.forEach((it) => {
      if (it.country) set.add(it.country);
    });
    return Array.from(set).sort();
  }, [taxonomyCountries, items]);

  // Subclasses filtered by Country, Category, Status, and Search
  const filteredSubclasses = useMemo(() => {
    return items.filter((it) => {
      if (statusFilter === 'all') {
        if (it.status === 'archived') return false;
      } else if (statusFilter === 'archived') {
        if (it.status !== 'archived') return false;
      } else {
        if (it.status !== statusFilter) return false;
      }

      // If user typed search, search globally across all countries
      if (search.trim()) {
        const q = search.toLowerCase();
        const n = (it.name || '').toLowerCase();
        const c = (it.country || '').toLowerCase();
        const v = (it.visa_type || '').toLowerCase();
        const s = (it.visa_subclass || '').toLowerCase();
        return n.includes(q) || c.includes(q) || v.includes(q) || s.includes(q);
      }

      // Hierarchy level 1: Country
      if (selectedCountry && it.country?.toLowerCase() !== selectedCountry.toLowerCase()) {
        return false;
      }

      // Hierarchy level 2: Category
      if (selectedCategory !== 'all') {
        const itCat = it.category || 'skilled_migration';
        if (itCat !== selectedCategory && itCat !== (selectedCategory === 'skilled_migration' ? 'pr' : selectedCategory)) {
          return false;
        }
      }

      return true;
    });
  }, [items, selectedCountry, selectedCategory, statusFilter, search]);

  const handleCreatedFromAi = async (aiData) => {
    try {
      const res = await axios.post(`${API}/product-master`, aiData, { headers: authHeaders });
      toast.success('Product Master created via AI research!');
      await loadData();
      if (res.data?.country) setSelectedCountry(res.data.country);
      if (res.data?.category) setSelectedCategory(res.data.category);
      setSelectedId(res.data.id);
      setNavStep('detail');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create Product Master');
    }
  };

  if (!isAdmin && isSales) {
    return null;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* TOP HEADER WITH ROLE PERSPECTIVE SWITCHER                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(isAdmin ? '/admin' : '/sales/crm')}
            className="p-2 rounded-lg hover:bg-slate-200 transition"
            data-testid="back-btn"
          >
            <ArrowLeft className="h-5 w-5 text-slate-700" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-extrabold text-slate-900 flex items-center gap-2">
                <Globe className="h-6 w-6 text-emerald-600" />
                {isAdmin ? 'Product Master Hub' : 'Visa Pitch Guide & Sales Handbook'}
              </h1>
              <Badge className="bg-emerald-100 text-emerald-800 text-xs font-bold">
                {isAdmin ? 'Single Source of Truth' : 'Sales Enablement'}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {isAdmin
                ? 'Comprehensive product architecture: criteria, process timeline, statutory fees, pricing & sales playbook.'
                : 'Official visa specifications, elevator pitches, client discovery questions, fees & objection handling.'}
            </p>
          </div>
        </div>

        {/* Role Perspective Switcher & Admin Actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Perspective Switcher: ONLY ADMIN CAN SWITCH TO FULL EDIT */}
          {isAdmin ? (
            <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
              <button
                onClick={() => setViewMode('admin')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition flex items-center gap-1.5 ${
                  viewMode === 'admin'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
                data-testid="viewmode-admin-btn"
              >
                <SlidersHorizontal className="h-3.5 w-3.5 text-indigo-600" />
                Admin View (Full Edit)
              </button>
              <button
                onClick={() => setViewMode('sales')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition flex items-center gap-1.5 ${
                  viewMode === 'sales'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
                data-testid="viewmode-sales-btn"
              >
                <Briefcase className="h-3.5 w-3.5 text-amber-600" />
                Sales Pitch Mode
              </button>
              <button
                onClick={() => setViewMode('cm')}
                className={`px-3 py-1.5 rounded-md text-xs font-bold transition flex items-center gap-1.5 ${
                  viewMode === 'cm'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
                data-testid="viewmode-cm-btn"
              >
                <Clock className="h-3.5 w-3.5 text-blue-600" />
                Case Delivery Mode
              </button>
            </div>
          ) : (
            <Badge className="bg-amber-50 text-amber-800 text-xs font-bold px-3 py-1 border border-amber-200 flex items-center gap-1.5">
              <Briefcase className="h-3.5 w-3.5 text-amber-600" />
              Salesperson Pitch & Handbook Mode
            </Badge>
          )}

          {/* Admin Creation Buttons - STRICTLY ADMIN ONLY */}
          {isAdmin && (
            <div className="flex items-center gap-1.5">
              <Button
                onClick={() => setAiModalOpen(true)}
                className="bg-amber-600 hover:bg-amber-700 text-white text-xs gap-1.5 shadow-sm h-8"
                data-testid="ai-create-btn"
              >
                <Sparkles className="h-3.5 w-3.5" />
                New with AI Research
              </Button>
              <Button
                onClick={() => setNewDialogOpen(true)}
                variant="outline"
                className="text-xs gap-1.5 h-8"
                data-testid="manual-create-btn"
              >
                <Plus className="h-3.5 w-3.5" />
                Manual Create
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* STATS TILES                                                   */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card className="p-3 bg-slate-50 border-slate-200">
          <p className="text-[10px] uppercase font-bold text-slate-500">Total Masters</p>
          <p className="text-xl font-extrabold text-slate-900 mt-0.5">{stats.total || 0}</p>
        </Card>
        <Card className="p-3 bg-emerald-50 border-emerald-200">
          <p className="text-[10px] uppercase font-bold text-emerald-700">Active / Published</p>
          <p className="text-xl font-extrabold text-emerald-900 mt-0.5">{stats.active || 0}</p>
        </Card>
        <Card className="p-3 bg-amber-50 border-amber-200">
          <p className="text-[10px] uppercase font-bold text-amber-700">Drafts</p>
          <p className="text-xl font-extrabold text-amber-900 mt-0.5">{stats.draft || 0}</p>
        </Card>
        <Card className="p-3 bg-blue-50 border-blue-200">
          <p className="text-[10px] uppercase font-bold text-blue-700">Verified Compliance</p>
          <p className="text-xl font-extrabold text-blue-900 mt-0.5">{stats.verified || 0}</p>
        </Card>
        <Card className="p-3 bg-purple-50 border-purple-200">
          <p className="text-[10px] uppercase font-bold text-purple-700">Countries Served</p>
          <p className="text-xl font-extrabold text-purple-900 mt-0.5">{stats.countries_count || taxonomyCountries.length || 0}</p>
        </Card>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* HIERARCHICAL DRILL-DOWN BREADCRUMB & UTILITY BAR             */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-white border border-slate-200 rounded-xl shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold flex-wrap">
          {/* 1-Step Back Button */}
          {navStep !== 'countries' && !search.trim() && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                if (navStep === 'detail') setNavStep('subclasses');
                else if (navStep === 'subclasses') setNavStep('categories');
                else if (navStep === 'categories') setNavStep('countries');
              }}
              className="h-7 px-2.5 text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 gap-1 mr-1 text-xs"
              data-testid="drilldown-back-btn"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              {navStep === 'detail'
                ? 'Back to Subclasses'
                : navStep === 'subclasses'
                ? 'Back to Categories'
                : 'Back to Countries'}
            </Button>
          )}

          {/* Breadcrumb Steps */}
          <button
            onClick={() => {
              setNavStep('countries');
              setSelectedCategory('all');
            }}
            className={`flex items-center gap-1.5 transition ${
              navStep === 'countries'
                ? 'text-emerald-700 font-extrabold bg-emerald-50 px-2 py-0.5 rounded'
                : 'text-slate-500 hover:text-slate-900 font-medium'
            }`}
            data-testid="breadcrumb-countries"
          >
            <Globe className="h-3.5 w-3.5 text-emerald-600" />
            <span>All Countries</span>
          </button>

          {(navStep === 'categories' || navStep === 'subclasses' || navStep === 'detail') && currentCountryObj && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
              <button
                onClick={() => {
                  setNavStep('categories');
                  setSelectedCategory('all');
                }}
                className={`flex items-center gap-1.5 transition ${
                  navStep === 'categories'
                    ? 'text-emerald-700 font-extrabold bg-emerald-50 px-2 py-0.5 rounded'
                    : 'text-slate-500 hover:text-slate-900 font-medium'
                }`}
                data-testid="breadcrumb-country"
              >
                <div className="w-4 h-4 rounded-full overflow-hidden border border-slate-200 inline-flex items-center justify-center shrink-0">
                  <Flag
                    code={getISO(currentCountryObj.name || currentCountryObj.country_code)}
                    style={{ width: '16px', height: '16px', objectFit: 'cover' }}
                  />
                </div>
                <span>{currentCountryObj.name}</span>
              </button>
            </>
          )}

          {(navStep === 'subclasses' || navStep === 'detail') && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
              <button
                onClick={() => setNavStep('subclasses')}
                className={`flex items-center gap-1 transition ${
                  navStep === 'subclasses'
                    ? 'text-emerald-700 font-extrabold bg-emerald-50 px-2 py-0.5 rounded'
                    : 'text-slate-500 hover:text-slate-900 font-medium'
                }`}
                data-testid="breadcrumb-category"
              >
                <span>{selectedCategory === 'all' ? '📁' : CATEGORY_META[selectedCategory]?.icon || '📄'}</span>
                <span>{selectedCategory === 'all' ? 'All Categories' : CATEGORY_META[selectedCategory]?.name || selectedCategory}</span>
              </button>
            </>
          )}

          {navStep === 'detail' && selectedProductData && (
            <>
              <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
              <span className="text-slate-900 font-extrabold flex items-center gap-1.5 truncate max-w-[280px]">
                {selectedProductData.visa_subclass && (
                  <Badge className="bg-emerald-600 text-white font-mono text-[10px] py-0 px-1.5 shrink-0">
                    Subclass {selectedProductData.visa_subclass}
                  </Badge>
                )}
                <span className="truncate">{selectedProductData.name}</span>
              </span>
            </>
          )}
        </div>

        {/* Global Search Bar */}
        <div className="flex items-center gap-2">
          <div className="relative w-64 md:w-80">
            <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <Input
              placeholder="Search subclass, name, country..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 text-xs h-8 bg-slate-50 focus:bg-white"
              data-testid="global-subclass-search-input"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-slate-600 text-xs"
              >
                ✕
              </button>
            )}
          </div>
          <Button size="sm" variant="ghost" onClick={loadData} className="h-8 px-2 text-slate-500" title="Refresh">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* GLOBAL SEARCH RESULTS (OVERRIDE VIEW WHEN USER SEARCHES)      */}
      {/* ───────────────────────────────────────────────────────────── */}
      {search.trim() ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                <Search className="h-4 w-4 text-emerald-600" />
                Search Results for "{search}"
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Showing matching visa subclasses across all destination countries.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                {filteredSubclasses.length} Matches Found
              </Badge>
              <Button size="sm" variant="outline" onClick={() => setSearch('')} className="h-7 text-xs">
                Clear Search
              </Button>
            </div>
          </div>

          {filteredSubclasses.length === 0 ? (
            <Card className="p-12 text-center bg-slate-50 border-dashed rounded-2xl">
              <Briefcase className="h-10 w-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-700">No matching subclasses found</p>
              <p className="text-xs text-slate-400 mt-1">Try another keyword or country name.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredSubclasses.map((item) => {
                const catMeta = CATEGORY_META[item.category] || {
                  name: item.category || 'Visa',
                  icon: '📄',
                  badge: 'bg-slate-100 text-slate-700',
                };
                return (
                  <Card
                    key={item.id}
                    onClick={() => {
                      setSelectedCountry(item.country);
                      setSelectedCategory(item.category || 'all');
                      setSelectedId(item.id);
                      setNavStep('detail');
                      setSearch('');
                    }}
                    className="group cursor-pointer p-5 bg-white border border-slate-200 hover:border-emerald-500 hover:shadow-lg transition-all rounded-2xl flex flex-col justify-between"
                    data-testid={`search-card-${item.id}`}
                  >
                    <div>
                      <div className="flex items-center gap-1.5 flex-wrap mb-2">
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                          <Flag
                            code={getISO(item.country)}
                            style={{ width: '14px', height: '14px', objectFit: 'cover', borderRadius: '50%' }}
                          />
                          {item.country}
                        </span>
                        {item.visa_subclass && (
                          <Badge className="bg-emerald-600 text-white font-mono text-[10px] py-0 px-1.5">
                            Subclass {item.visa_subclass}
                          </Badge>
                        )}
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold border ${catMeta.badge}`}>
                          {catMeta.icon} {catMeta.name}
                        </span>
                      </div>
                      <h4 className="text-sm font-extrabold text-slate-900 group-hover:text-emerald-700 transition">
                        {item.name}
                      </h4>
                      {(item.summary || item.description) && (
                        <p className="text-xs text-slate-500 mt-1.5 line-clamp-2 leading-relaxed">
                          {item.summary || item.description}
                        </p>
                      )}
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-emerald-700 group-hover:text-emerald-800">
                      <span>Open Subclass Information</span>
                      <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <>
          {/* ───────────────────────────────────────────────────────── */}
          {/* STEP 1: ALL COUNTRIES GRID (navStep === 'countries')      */}
          {/* ───────────────────────────────────────────────────────── */}
          {navStep === 'countries' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
                    <Globe className="h-5 w-5 text-emerald-600" />
                    Step 1: Select Destination Country
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Browse official visa subclasses, statutory criteria, fees, and timelines across all supported immigration destinations.
                  </p>
                </div>
                <Badge variant="outline" className="text-xs font-semibold px-2.5 py-1">
                  {taxonomyCountries.length} Destination Countries
                </Badge>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-5">
                {taxonomyCountries.map((c) => {
                  const cats = c.categories ? Object.values(c.categories) : [];
                  return (
                    <Card
                      key={c.id || c.name}
                      onClick={() => {
                        setSelectedCountry(c.name);
                        setSelectedCategory('all');
                        setNavStep('categories');
                      }}
                      className="group cursor-pointer p-5 bg-white border border-slate-200 hover:border-emerald-500 hover:shadow-lg transition-all rounded-2xl flex flex-col justify-between"
                      data-testid={`country-card-${c.id || c.name}`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <div className="w-14 h-14 rounded-2xl overflow-hidden border-2 border-slate-100 shadow-sm flex items-center justify-center bg-slate-50 group-hover:scale-105 transition-transform">
                            <Flag
                              code={getISO(c.name || c.country_code)}
                              style={{ width: '56px', height: '56px', objectFit: 'cover' }}
                              fallback={<Globe className="h-7 w-7 text-slate-400" />}
                            />
                          </div>
                          <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold py-1 px-2.5">
                            {c.total_subclasses || 0} Subclasses
                          </Badge>
                        </div>

                        <h3 className="text-base font-extrabold text-slate-900 group-hover:text-emerald-700 transition">
                          {c.name}
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5 font-medium line-clamp-1">
                          {c.authority_name || 'Official Immigration Authority'}
                        </p>

                        {/* Categories breakdown pills */}
                        <div className="mt-4 flex flex-wrap gap-1.5">
                          {cats.slice(0, 4).map((cat) => (
                            <span
                              key={cat.id}
                              className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium border border-slate-200/60"
                            >
                              <span>{cat.icon}</span>
                              <span>{cat.name}</span>
                              <span className="text-[10px] text-slate-400 font-mono">({cat.count})</span>
                            </span>
                          ))}
                          {cats.length > 4 && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-medium">
                              +{cats.length - 4} more
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-emerald-700 group-hover:text-emerald-800">
                        <span>Explore Visa Categories</span>
                        <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {/* ───────────────────────────────────────────────────────── */}
          {/* STEP 2: COUNTRY CATEGORIES (navStep === 'categories')     */}
          {/* ───────────────────────────────────────────────────────── */}
          {navStep === 'categories' && (
            <div className="space-y-5">
              {/* Country Showcase Banner */}
              {currentCountryObj && (
                <Card className="p-5 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl shadow-md border-0">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 rounded-2xl overflow-hidden border-2 border-white/20 shadow-md flex items-center justify-center bg-white/10 shrink-0">
                        <Flag
                          code={getISO(currentCountryObj.name || currentCountryObj.country_code)}
                          style={{ width: '64px', height: '64px', objectFit: 'cover' }}
                          fallback={<Globe className="h-8 w-8 text-white/50" />}
                        />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-extrabold text-white">{currentCountryObj.name}</h2>
                          <Badge className="bg-emerald-500 text-white text-xs font-bold py-0.5 px-2">
                            {currentCountryObj.total_subclasses} Total Subclasses
                          </Badge>
                        </div>
                        <p className="text-xs text-slate-300 mt-1">
                          Immigration Authority: <span className="font-semibold text-white">{currentCountryObj.authority_name || 'Official Authority'}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {currentCountryObj.official_portal_url && (
                        <a
                          href={currentCountryObj.official_portal_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          Official Government Portal
                        </a>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setSelectedCategory('all');
                          setNavStep('subclasses');
                        }}
                        className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-bold"
                      >
                        View All Subclasses
                      </Button>
                    </div>
                  </div>
                </Card>
              )}

              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
                    <Layers className="h-5 w-5 text-emerald-600" />
                    Step 2: Select Visa Category in {selectedCountry}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Choose a visa pathway to browse all subclasses under this category.
                  </p>
                </div>
              </div>

              {/* Category Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {countryCategories.map((cat) => {
                  const catSubclasses = getSubclassesForCategory(cat.id);
                  return (
                    <Card
                      key={cat.id}
                      onClick={() => {
                        setSelectedCategory(cat.id);
                        setNavStep('subclasses');
                      }}
                      className="group cursor-pointer p-5 bg-white border border-slate-200 hover:border-emerald-500 hover:shadow-lg transition-all rounded-2xl flex flex-col justify-between"
                      data-testid={`category-card-${cat.id}`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <span className="text-3xl p-2.5 rounded-xl bg-slate-100 group-hover:bg-emerald-50 transition">
                            {cat.icon || '📄'}
                          </span>
                          <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold py-1 px-2.5">
                            {cat.count} {cat.count === 1 ? 'Subclass' : 'Subclasses'}
                          </Badge>
                        </div>

                        <h4 className="text-base font-extrabold text-slate-900 group-hover:text-emerald-700 transition mt-2">
                          {cat.name}
                        </h4>

                        {/* Subclasses Preview Pills */}
                        <div className="mt-3 space-y-1.5">
                          <span className="text-[10px] uppercase font-bold text-slate-400">Available Subclasses:</span>
                          <div className="flex flex-wrap gap-1">
                            {catSubclasses.slice(0, 4).map((sub) => (
                              <Badge key={sub.id} variant="outline" className="text-[11px] font-mono bg-slate-50 text-slate-700">
                                {sub.visa_subclass ? `Subclass ${sub.visa_subclass}` : sub.name}
                              </Badge>
                            ))}
                            {catSubclasses.length > 4 && (
                              <Badge variant="outline" className="text-[10px] bg-slate-50 text-slate-500">
                                +{catSubclasses.length - 4} more
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-emerald-700 group-hover:text-emerald-800">
                        <span>View Subclasses</span>
                        <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {/* ───────────────────────────────────────────────────────── */}
          {/* STEP 3: SUBCLASSES GRID (navStep === 'subclasses')         */}
          {/* ───────────────────────────────────────────────────────── */}
          {navStep === 'subclasses' && (
            <div className="space-y-4">
              {/* Category Filter Pills / Switcher */}
              <div className="flex items-center justify-between gap-2 flex-wrap pb-2 border-b border-slate-200">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mr-1">Filter Category:</span>
                  <button
                    onClick={() => setSelectedCategory('all')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                      selectedCategory === 'all'
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                    }`}
                  >
                    All Categories ({currentCountryObj?.total_subclasses || items.length})
                  </button>
                  {countryCategories.map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => setSelectedCategory(cat.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 ${
                        selectedCategory === cat.id
                          ? 'bg-emerald-600 text-white shadow-sm'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                      }`}
                    >
                      <span>{cat.icon}</span>
                      <span>{cat.name}</span>
                      <span className="text-[11px] font-mono opacity-80">({cat.count})</span>
                    </button>
                  ))}
                </div>

                {/* Status Filter */}
                <div className="flex rounded-lg bg-slate-100 p-0.5">
                  {[
                    { id: 'all', label: 'All Active & Drafts' },
                    { id: 'active', label: 'Active' },
                    { id: 'draft', label: 'Draft' },
                    { id: 'archived', label: 'Archived' },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setStatusFilter(tab.id)}
                      className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
                        statusFilter === tab.id ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
                    <Layers className="h-5 w-5 text-emerald-600" />
                    Step 3: Visa Subclasses in {selectedCountry}
                    {selectedCategory !== 'all' && ` - ${CATEGORY_META[selectedCategory]?.name || selectedCategory}`}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Click on any subclass card to inspect its complete eligibility criteria, process timeline, statutory costs, and pricing.
                  </p>
                </div>
                <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                  {filteredSubclasses.length} Subclasses Available
                </Badge>
              </div>

              {/* Subclasses Grid */}
              {filteredSubclasses.length === 0 ? (
                <Card className="p-12 text-center bg-slate-50 border-dashed rounded-2xl">
                  <Briefcase className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-bold text-slate-700">No subclasses found in this category</p>
                  <p className="text-xs text-slate-400 mt-1">Try selecting "All Categories" or create one with AI research.</p>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filteredSubclasses.map((item) => {
                    const catMeta = CATEGORY_META[item.category] || {
                      name: item.category || 'Visa',
                      icon: '📄',
                      badge: 'bg-slate-100 text-slate-700',
                    };
                    const govFees = item.government_costs?.primary_applicant
                      ? `${item.government_costs.currency || 'AUD'} ${Number(item.government_costs.primary_applicant).toLocaleString()}`
                      : item.estimated_fees || '';

                    return (
                      <Card
                        key={item.id}
                        onClick={() => {
                          setSelectedId(item.id);
                          setNavStep('detail');
                        }}
                        className="group cursor-pointer p-5 bg-white border border-slate-200 hover:border-emerald-500 hover:shadow-lg transition-all rounded-2xl flex flex-col justify-between"
                        data-testid={`subclass-grid-card-${item.id}`}
                      >
                        <div>
                          {/* Badges Bar */}
                          <div className="flex items-center justify-between gap-2 mb-2.5">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              {item.visa_subclass && (
                                <Badge className="bg-emerald-600 text-white font-mono text-xs font-bold py-0.5 px-2">
                                  Subclass {item.visa_subclass}
                                </Badge>
                              )}
                              <span className={`text-[11px] px-2 py-0.5 rounded font-semibold border ${catMeta.badge}`}>
                                {catMeta.icon} {catMeta.name}
                              </span>
                            </div>
                            {item.status === 'archived' ? (
                              <Badge className="bg-slate-100 text-slate-600 border border-slate-300 text-[10px]">
                                Archived
                              </Badge>
                            ) : item.last_verified_at ? (
                              <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] gap-1">
                                <ShieldCheck className="h-3 w-3" />Verified
                              </Badge>
                            ) : (
                              <Badge className="bg-amber-50 text-amber-700 border border-amber-200 text-[10px]">
                                Draft
                              </Badge>
                            )}
                          </div>

                          {/* Title & Summary */}
                          <h4 className="text-sm font-extrabold text-slate-900 group-hover:text-emerald-700 transition leading-snug">
                            {item.name}
                          </h4>
                          {(item.summary || item.description) && (
                            <p className="text-xs text-slate-500 mt-2 line-clamp-3 leading-relaxed">
                              {item.summary || item.description}
                            </p>
                          )}

                          {/* Key Specs Matrix */}
                          <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-slate-100 text-xs">
                            <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                              <span className="text-[10px] uppercase font-bold text-slate-400 block">Govt Fee:</span>
                              <span className="font-extrabold text-slate-800 text-xs">
                                {govFees || 'Official Slabs'}
                              </span>
                            </div>
                            <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                              <span className="text-[10px] uppercase font-bold text-slate-400 block">LEAMSS Fee:</span>
                              <span className="font-extrabold text-emerald-700 text-xs">
                                {formatINR(item.pricing?.base_fee ? item.pricing.base_fee / 100 : item.service_price || 0)}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-emerald-700 group-hover:text-emerald-800">
                          <span>View Full Specs & Workflow</span>
                          <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
                        </div>
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ───────────────────────────────────────────────────────── */}
          {/* STEP 4: SUBCLASS INFORMATION (navStep === 'detail')       */}
          {/* ───────────────────────────────────────────────────────── */}
          {navStep === 'detail' && (
            <div className="space-y-4">
              {detailLoading ? (
                <Card className="p-16 text-center bg-slate-50/50 rounded-2xl">
                  <RefreshCw className="h-6 w-6 text-slate-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs font-bold text-slate-600">Loading Subclass details...</p>
                </Card>
              ) : selectedProductData ? (
                <div className="space-y-4">
                  {/* Sibling Subclasses Quick Switcher Bar */}
                  {siblingSubclasses.length > 1 && (
                    <div className="flex items-center gap-2 p-2.5 bg-slate-100/80 border border-slate-200 rounded-xl overflow-x-auto">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider shrink-0 pl-1">
                        Other {CATEGORY_META[selectedProductData.category]?.name || selectedProductData.category || 'Category'} Visas:
                      </span>
                      <div className="flex items-center gap-1.5 flex-nowrap">
                        {siblingSubclasses.map((sib) => {
                          const isCurrent = sib.id === selectedId;
                          return (
                            <button
                              key={sib.id}
                              onClick={() => setSelectedId(sib.id)}
                              className={`px-3 py-1 rounded-lg text-xs font-bold transition shrink-0 border ${
                                isCurrent
                                  ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                                  : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
                              }`}
                            >
                              {sib.visa_subclass ? `Subclass ${sib.visa_subclass}` : sib.name}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Perspective View Content */}
                  {effectiveViewMode === 'cm' ? (
                    <CaseManagerPerspectiveView product={selectedProductData} />
                  ) : effectiveViewMode === 'admin' ? (
                    <MasterDetailPane
                      key={selectedProductData.id}
                      product={selectedProductData}
                      allProducts={items}
                      onSaved={handleDetailSaved}
                      onDeleted={() => {
                        setSelectedId(null);
                        setNavStep('subclasses');
                        loadData();
                      }}
                    />
                  ) : (
                    <SalesPerspectiveView
                      product={selectedProductData}
                      isAdmin={isAdmin}
                      onSaved={handleDetailSaved}
                    />
                  )}
                </div>
              ) : (
                <Card className="p-16 text-center bg-slate-50/50 border-dashed rounded-2xl">
                  <Briefcase className="h-10 w-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm font-bold text-slate-700">No Subclass selected</p>
                  <Button
                    onClick={() => setNavStep('subclasses')}
                    className="mt-3 bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                  >
                    Browse Subclasses
                  </Button>
                </Card>
              )}
            </div>
          )}
        </>
      )}

      {/* AI Research Creation Modal */}
      <ProductAiResearchModal
        isOpen={aiModalOpen}
        onClose={() => setAiModalOpen(false)}
        onApply={handleCreatedFromAi}
      />

      {/* Manual Create Dialog */}
      <ManualCreateDialog
        open={newDialogOpen}
        onClose={() => setNewDialogOpen(false)}
        onCreated={(id) => {
          loadData();
          setSelectedId(id);
          setNavStep('detail');
        }}
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// RIGHT PANE: ADMIN MASTER DETAIL EDITOR (6 COMPLETE SECTIONS)
// ═══════════════════════════════════════════════════════════════════════
function MasterDetailPane({ product, onSaved, onDeleted, allProducts = [] }) {
  const [form, setForm] = useState({ ...product });
  const [activeTab, setActiveTab] = useState('basic');
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [aiModalOpen, setAiModalOpen] = useState(false);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    setForm({ ...product });
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id, product?.version, product?.updated_at, JSON.stringify(product?.refund_policy)]);

  const token = localStorage.getItem('token');
  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const patch = (patchObj) => {
    setForm((prev) => ({ ...prev, ...patchObj }));
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await axios.put(`${API}/product-master/${product.id}`, form, { headers: authHeaders });
      toast.success('Product Master updated successfully!');
      setDirty(false);
      const updatedProduct = res.data?.product || form;
      if (res.data?.product) {
        setForm({ ...res.data.product });
      }
      if (onSaved) {
        await onSaved(product.id, updatedProduct);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save Product Master');
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await axios.post(`${API}/product-master/${product.id}/verify`, {}, { headers: authHeaders });
      toast.success('Product Master verified for compliance!');
      patch({ last_verified_at: res.data.last_verified_at, status: 'active' });
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Verification failed');
    } finally {
      setVerifying(false);
    }
  };

  const handleClone = async () => {
    try {
      const res = await axios.post(`${API}/product-master/${product.id}/clone`, {}, { headers: authHeaders });
      toast.success(`Cloned as draft: ${res.data.name}`);
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Clone failed');
    }
  };

  const [autoEnriching, setAutoEnriching] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [deletingPermanent, setDeletingPermanent] = useState(false);

  const handleArchive = async () => {
    if (!window.confirm(`Archive "${product.name}"? This will soft-delete the record.`)) return;
    try {
      await axios.delete(`${API}/product-master/${product.id}`, { headers: authHeaders });
      toast.success('Product Master archived');
      onDeleted();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Archive failed');
    }
  };

  const handleRestore = async () => {
    setRestoring(true);
    try {
      await axios.post(`${API}/product-master/${product.id}/restore`, {}, { headers: authHeaders });
      toast.success('Product restored to active status!');
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Restore failed');
    } finally {
      setRestoring(false);
    }
  };

  const handlePermanentDelete = async () => {
    if (!window.confirm(`Permanently delete "${product.name}"? This action CANNOT be undone.`)) return;
    setDeletingPermanent(true);
    try {
      await axios.delete(`${API}/product-master/${product.id}?permanent=true`, { headers: authHeaders });
      toast.success('Product permanently deleted');
      onDeleted();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Delete failed');
    } finally {
      setDeletingPermanent(false);
    }
  };

  const handleAutoEnrich = async () => {
    setAutoEnriching(true);
    try {
      const res = await axios.post(`${API}/product-master/${product.id}/auto-enrich`, {}, { headers: authHeaders });
      toast.success(res.data.message || 'Auto-filled specs from canonical knowledge base!');
      if (res.data?.product) {
        setForm(res.data.product);
        setDirty(false);
      }
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Auto-fill failed');
    } finally {
      setAutoEnriching(false);
    }
  };

  const handleApplyAi = (aiData) => {
    patch({
      name: aiData.name || form.name,
      summary: aiData.summary || form.summary,
      description: aiData.summary || form.description,
      country: aiData.country || form.country,
      category: aiData.category || form.category,
      visa_type: aiData.visa_type || form.visa_type,
      visa_subclass: aiData.visa_subclass || form.visa_subclass,
      migrate_page_url: aiData.migrate_page_url || form.migrate_page_url,
      official_urls: aiData.official_urls || form.official_urls,
      official_domains: aiData.official_domains || form.official_domains,
      eligibility_criteria: aiData.eligibility_criteria || form.eligibility_criteria,
      visa_conditions: aiData.visa_conditions || form.visa_conditions,
      government_costs: aiData.government_costs || form.government_costs,
      processing_timeline: aiData.processing_timeline || form.processing_timeline,
      sales_playbook: aiData.sales_playbook || form.sales_playbook,
      objections_rebuttals: aiData.objections_rebuttals || form.objections_rebuttals,
      faqs: aiData.faqs || form.faqs,
      document_checklist_template: aiData.document_checklist_template || form.document_checklist_template,
    });
  };

  return (
    <Card className="p-6 bg-white shadow-sm border border-slate-200">
      {/* Pane Header */}
      <div className="flex items-start justify-between gap-4 mb-4 pb-4 border-b">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-xl font-extrabold text-slate-900 truncate">{form.name}</h2>
            {form.last_verified_at ? (
              <Badge className="bg-emerald-100 text-emerald-800 text-[10px] gap-1 shrink-0">
                <ShieldCheck className="h-3 w-3" />
                Verified {new Date(form.last_verified_at).toLocaleDateString()}
              </Badge>
            ) : (
              <Badge className="bg-amber-100 text-amber-800 text-[10px] shrink-0">Unverified</Badge>
            )}
            <Badge variant="outline" className="text-[10px] font-mono">v{form.version || 1}</Badge>
          </div>

          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            {form.country && (
              <Badge className="bg-slate-100 text-slate-700 text-[10px] gap-1">
                <Globe className="h-2.5 w-2.5" />{form.country}
              </Badge>
            )}
            {form.visa_subclass && (
              <Badge className="bg-blue-50 text-blue-700 text-[10px]">
                Subclass {form.visa_subclass}
              </Badge>
            )}
            {form.migrate_page_url && (
              <a
                href={form.migrate_page_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:underline bg-blue-50 px-2 py-0.5 rounded"
              >
                <ExternalLink className="h-2.5 w-2.5" />Migrate Page
              </a>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={handleAutoEnrich}
            disabled={autoEnriching}
            className="text-amber-800 bg-amber-50 hover:bg-amber-100 border-amber-300 text-xs gap-1.5"
            data-testid="auto-enrich-detail-btn"
            title="Auto-fill official subclass specs from canonical immigration knowledge base"
          >
            <Zap className="h-3.5 w-3.5 text-amber-600" />
            {autoEnriching ? 'Auto-Filling...' : '⚡ Auto-Fill Specs'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setAiModalOpen(true)}
            className="text-blue-800 bg-blue-50 hover:bg-blue-100 border-blue-200 text-xs gap-1.5"
            data-testid="ai-enrich-detail-btn"
          >
            <Sparkles className="h-3.5 w-3.5 text-blue-600" />
            AI Enrich
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleVerify}
            disabled={verifying}
            className="text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border-emerald-300 text-xs gap-1"
            data-testid="verify-detail-btn"
          >
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
            {verifying ? 'Verifying...' : 'Verify'}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleClone}
            className="text-slate-700 text-xs gap-1"
            data-testid="clone-detail-btn"
          >
            <Copy className="h-3.5 w-3.5" />
            Clone
          </Button>
          {dirty && (
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs gap-1"
              data-testid="save-master-btn"
            >
              <Save className="h-3.5 w-3.5" />
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          )}
          {form.status === 'archived' ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={handleRestore}
                disabled={restoring}
                className="text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border-emerald-300 text-xs gap-1"
                data-testid="restore-detail-btn"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                {restoring ? 'Restoring...' : 'Restore'}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handlePermanentDelete}
                disabled={deletingPermanent}
                className="text-rose-600 border-rose-300 hover:bg-rose-50 text-xs gap-1"
                data-testid="permanent-delete-btn"
                title="Permanently remove from database"
              >
                <Trash2 className="h-3.5 w-3.5" />
                {deletingPermanent ? 'Deleting...' : 'Delete Permanently'}
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={handleArchive}
              className="text-rose-600 border-rose-200 hover:bg-rose-50 text-xs"
              data-testid="archive-detail-btn"
              title="Archive / Soft-Delete"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Draft / Incomplete Specs Alert Banner */}
      {(!form.visa_subclass || !form.summary || !form.eligibility_criteria?.min_points || !form.government_costs?.primary_applicant) && (
        <div className="mb-4 p-3.5 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2.5 text-xs text-amber-900">
            <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
            <span>
              <strong>Draft / Incomplete Subclass:</strong> This subclass is missing statutory criteria, official fee slabs, or timeline specs.
            </span>
          </div>
          <Button
            size="sm"
            onClick={handleAutoEnrich}
            disabled={autoEnriching}
            className="bg-amber-600 hover:bg-amber-700 text-white text-xs gap-1.5 h-7 px-3 shrink-0 shadow-sm"
            data-testid="auto-fill-banner-btn"
          >
            <Zap className="h-3.5 w-3.5" />
            {autoEnriching ? 'Auto-Filling...' : '⚡ Auto-Fill Specs Now'}
          </Button>
        </div>
      )}

      <ProductAiResearchModal
        isOpen={aiModalOpen}
        onClose={() => setAiModalOpen(false)}
        onApply={handleApplyAi}
        initialCountry={form.country}
        initialVisa={form.name || form.visa_type}
      />

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 6 STANDARDIZED SECTIONS                                       */}
      {/* ───────────────────────────────────────────────────────────── */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-6 mb-4 text-[11px]">
          <TabsTrigger value="basic">1. Basic Info</TabsTrigger>
          <TabsTrigger value="eligibility">2. Eligibility</TabsTrigger>
          <TabsTrigger value="timeline">3. Timeline & Steps</TabsTrigger>
          <TabsTrigger value="govt_fees">4. Govt Fees</TabsTrigger>
          <TabsTrigger value="pricing">5. LEAMSS Pricing</TabsTrigger>
          <TabsTrigger value="playbook">6. Sales Playbook</TabsTrigger>
        </TabsList>

        {/* 1. Basic Product Information */}
        <TabsContent value="basic" className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-bold">Visa Product Name *</Label>
              <Input
                value={form.name || ''}
                onChange={(e) => patch({ name: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs font-bold">Destination Country *</Label>
              <Input
                value={form.country || ''}
                onChange={(e) => patch({ country: e.target.value })}
                className="mt-1"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label className="text-xs font-bold">Visa Category</Label>
              <select
                value={form.category || 'skilled_migration'}
                onChange={(e) => patch({ category: e.target.value })}
                className="mt-1 flex h-9 w-full rounded-md border border-input bg-white px-2.5 text-xs font-semibold"
              >
                <option value="skilled_migration">Skilled Migration / PR</option>
                <option value="work">Work Visa</option>
                <option value="student">Student / Education</option>
                <option value="visitor">Visitor / Tourist</option>
                <option value="business">Business / Investment</option>
                <option value="family">Family / Spouse</option>
              </select>
            </div>
            <div>
              <Label className="text-xs font-bold">Visa Subclass / Code</Label>
              <Input
                value={form.visa_subclass || ''}
                onChange={(e) => patch({ visa_subclass: e.target.value })}
                placeholder="e.g. 189, 482, Express Entry"
                className="mt-1 font-bold"
              />
            </div>
            <div>
              <Label className="text-xs font-bold">Status</Label>
              <select
                value={form.status || 'draft'}
                onChange={(e) => patch({ status: e.target.value })}
                className="mt-1 flex h-9 w-full rounded-md border border-input bg-white px-2.5 text-xs font-semibold"
              >
                <option value="draft">Draft</option>
                <option value="active">Active (Published)</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-bold flex items-center gap-1">
                <ExternalLink className="h-3 w-3 text-blue-600" />
                Migrate Page URL (leamss.com/migrate/...)
              </Label>
              <Input
                value={form.migrate_page_url || ''}
                onChange={(e) => patch({ migrate_page_url: e.target.value })}
                placeholder="https://leamss.com/migrate/australia/subclass-189"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs font-bold flex items-center gap-1">
                <Globe className="h-3 w-3 text-emerald-600" />
                Official Allowed Domains
              </Label>
              <Input
                value={(form.official_domains || []).join(', ')}
                onChange={(e) =>
                  patch({ official_domains: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })
                }
                placeholder="e.g. immi.homeaffairs.gov.au, cic.gc.ca"
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <Label className="text-xs font-bold">Official Government Source URLs</Label>
            <Input
              value={(form.official_urls || []).join(', ')}
              onChange={(e) =>
                patch({ official_urls: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })
              }
              placeholder="e.g. https://immi.homeaffairs.gov.au/visas/getting-a-visa/..."
              className="mt-1"
            />
          </div>

          <div>
            <Label className="text-xs font-bold">Executive Summary</Label>
            <Textarea
              value={form.summary || ''}
              onChange={(e) => patch({ summary: e.target.value })}
              rows={2}
              placeholder="High-level overview of this visa for sales cards and client portal"
              className="mt-1"
            />
          </div>

          <div>
            <Label className="text-xs font-bold">Detailed Program Description</Label>
            <Textarea
              value={form.description || ''}
              onChange={(e) => patch({ description: e.target.value })}
              rows={3}
              placeholder="Full program details"
              className="mt-1"
            />
          </div>
        </TabsContent>

        {/* 2. Eligibility Criteria */}
        <TabsContent value="eligibility">
          <EligibilityTab
            product={form}
            eligibility={form.eligibility_criteria}
            conditions={form.visa_conditions}
            onChangeEligibility={(el) => patch({ eligibility_criteria: el })}
            onChangeConditions={(cd) => patch({ visa_conditions: cd })}
          />
        </TabsContent>

        {/* 3. Visa Process Timeline & Document Checklist */}
        <TabsContent value="timeline">
          <TimelineChecklistTab
            timeline={form.processing_timeline}
            checklist={form.document_checklist_template}
            workflowSteps={form.workflow_steps}
            onChangeTimeline={(t) => patch({ processing_timeline: t })}
            onChangeChecklist={(cl) => patch({ document_checklist_template: cl })}
            onChangeWorkflowSteps={(steps) => patch({ workflow_steps: steps })}
          />
        </TabsContent>

        {/* 4. Statutory Government Fees */}
        <TabsContent value="govt_fees">
          <GovernmentCostsTab
            costs={form.government_costs}
            onChangeCosts={(c) => patch({ government_costs: c })}
          />
        </TabsContent>

        {/* 5. LEAMSS Package & Pricing */}
        <TabsContent value="pricing">
          <LEAMSSPricingTab
            product={form}
            onChange={(patchObj) => patch(patchObj)}
            onSaved={async (id, prod) => {
              if (prod) setForm({ ...prod });
              setDirty(false);
              if (onSaved) await onSaved(id, prod);
            }}
            allProducts={allProducts}
          />
        </TabsContent>

        {/* 6. Sales Playbook */}
        <TabsContent value="playbook">
          <SalesPlaybookTab
            playbook={form.sales_playbook}
            objections={form.objections_rebuttals}
            faqs={form.faqs}
            onChangePlaybook={(pb) => patch({ sales_playbook: pb })}
            onChangeObjections={(ob) => patch({ objections_rebuttals: ob })}
            onChangeFaqs={(fq) => patch({ faqs: fq })}
          />
        </TabsContent>
      </Tabs>
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// MANUAL CREATE DIALOG
// ═══════════════════════════════════════════════════════════════════════
function ManualCreateDialog({ open, onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '',
    country: '',
    visa_type: '',
    visa_subclass: '',
    category: 'skilled_migration',
    service_price: 150000,
    summary: '',
  });
  const [saving, setSaving] = useState(false);
  const [aiModalOpen, setAiModalOpen] = useState(false);

  const handleApplyAi = (aiData) => {
    setForm((prev) => ({
      ...prev,
      name: aiData.name || prev.name,
      country: aiData.country || prev.country,
      visa_type: aiData.visa_type || prev.visa_type,
      visa_subclass: aiData.visa_subclass || prev.visa_subclass,
      category: aiData.category || prev.category,
      summary: aiData.summary || '',
      description: aiData.summary || '',
      migrate_page_url: aiData.migrate_page_url || '',
      official_urls: aiData.official_urls || [],
      official_domains: aiData.official_domains || [],
      eligibility_criteria: aiData.eligibility_criteria,
      visa_conditions: aiData.visa_conditions,
      government_costs: aiData.government_costs,
      processing_timeline: aiData.processing_timeline,
      sales_playbook: aiData.sales_playbook,
      objections_rebuttals: aiData.objections_rebuttals,
      faqs: aiData.faqs,
      document_checklist_template: aiData.document_checklist_template,
    }));
  };

  const save = async () => {
    if (!form.name.trim() || !form.country.trim()) {
      toast.error('Product Name and Country are required');
      return;
    }
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.post(`${API}/product-master`, form, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success('Product Master created!');
      onCreated(res.data.id);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Creation failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-emerald-600" />
              New Product Master
            </DialogTitle>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setAiModalOpen(true)}
              className="h-7 text-xs border-amber-300 text-amber-800 bg-amber-50 hover:bg-amber-100 gap-1.5"
            >
              <Sparkles className="h-3.5 w-3.5 text-amber-600" />
              Auto-fill with AI Research
            </Button>
          </div>
        </DialogHeader>

        <ProductAiResearchModal
          isOpen={aiModalOpen}
          onClose={() => setAiModalOpen(false)}
          onApply={handleApplyAi}
          initialCountry={form.country}
          initialVisa={form.name || form.visa_type}
        />

        <div className="space-y-3 py-2 text-xs">
          <div>
            <Label className="font-bold">Visa Product Name *</Label>
            <Input
              placeholder="e.g. Australia Skilled Independent Subclass 189"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="mt-1"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="font-bold">Country *</Label>
              <Input
                placeholder="e.g. Australia"
                value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="font-bold">Visa Subclass / Code</Label>
              <Input
                placeholder="e.g. 189"
                value={form.visa_subclass}
                onChange={(e) => setForm({ ...form, visa_subclass: e.target.value })}
                className="mt-1"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="font-bold">Category</Label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="mt-1 flex h-9 w-full rounded-md border border-input bg-white px-2.5 text-xs font-semibold"
              >
                <option value="skilled_migration">Skilled Migration / PR</option>
                <option value="work">Work Visa</option>
                <option value="student">Student / Education</option>
                <option value="visitor">Visitor / Tourist</option>
                <option value="business">Business / Investment</option>
                <option value="family">Family / Spouse</option>
              </select>
            </div>
            <div>
              <Label className="font-bold">Base Professional Fee (₹)</Label>
              <Input
                type="number"
                value={form.service_price}
                onChange={(e) => setForm({ ...form, service_price: parseFloat(e.target.value) || 0 })}
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <Label className="font-bold">Executive Summary</Label>
            <Textarea
              placeholder="Brief overview of this visa product..."
              value={form.summary}
              onChange={(e) => setForm({ ...form, summary: e.target.value })}
              rows={2}
              className="mt-1"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={save} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700 text-white">
            {saving ? 'Creating...' : 'Create Master'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
