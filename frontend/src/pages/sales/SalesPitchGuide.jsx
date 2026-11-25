import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  ArrowLeft, Search, Sparkles, Globe, Copy, ExternalLink, DollarSign,
  MessageSquare, Target, UserCheck, HelpCircle, Bot, Send, ListChecks,
  CheckCircle, CheckCircle2, ChevronRight, RefreshCw, Phone, ShieldCheck,
  FileText, Compass, Award, Clock, Coins, BookOpen, AlertCircle, Edit3, Zap,
  PhoneCall, Volume2, ShieldAlert, Layers, X, Download, Printer, Briefcase,
  Languages, ShieldX
} from 'lucide-react';

import Flag from 'react-world-flags';
import PackageRefundBadge from '@/components/admin/product-master/PackageRefundBadge';

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

const normalizeCountry = (c) => {
  if (!c) return 'Other';
  const clean = c.trim().toLowerCase();
  if (['usa', 'us', 'united states', 'united states of america'].includes(clean)) return 'United States';
  if (['uk', 'united kingdom', 'great britain'].includes(clean)) return 'United Kingdom';
  if (['nz', 'new zealand'].includes(clean)) return 'New Zealand';
  if (['uae', 'united arab emirates'].includes(clean)) return 'United Arab Emirates';
  if (clean === 'canada') return 'Canada';
  if (clean === 'australia') return 'Australia';
  if (clean === 'germany') return 'Germany';
  return c.charAt(0).toUpperCase() + c.slice(1);
};

const getCountryCode = (countryName, itemCode) => {
  if (itemCode && itemCode.length <= 4) return itemCode.toUpperCase();
  const norm = normalizeCountry(countryName);
  if (norm === 'United States') return 'US';
  if (norm === 'United Kingdom') return 'GB';
  if (norm === 'Australia') return 'AU';
  if (norm === 'Canada') return 'CA';
  if (norm === 'Germany') return 'DE';
  if (norm === 'New Zealand') return 'NZ';
  if (norm === 'United Arab Emirates') return 'AE';
  const clean = countryName.toLowerCase().replace(/[\s_-]+/g, '_');
  return ISO_CODES[clean] || (norm.length <= 3 ? norm.toUpperCase() : norm.slice(0, 2).toUpperCase());
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
};

const ALL_CATEGORY_OPTIONS = [
  { id: 'all', name: 'All Categories', icon: '📁' },
  { id: 'skilled_migration', name: 'Skilled Migration / PR', icon: '🌟' },
  { id: 'work', name: 'Work Visas', icon: '💼' },
  { id: 'student', name: 'Student Visas', icon: '🎓' },
  { id: 'visitor', name: 'Visitor Visas', icon: '✈️' },
  { id: 'family', name: 'Family & Partner', icon: '👨‍👩‍👧' },
  { id: 'business', name: 'Business & Investor', icon: '🏢' },
];

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

function renderFormattedInline(text) {
  if (!text) return null;
  const parts = [];
  const regex = /(\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }
    if (match[2] && match[3]) {
      parts.push(
        <a
          key={match.index}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
          className="text-emerald-700 hover:text-emerald-900 underline font-semibold inline-flex items-center gap-1"
        >
          {match[2]}
          <ExternalLink className="w-2.5 h-2.5 inline" />
        </a>
      );
    } else if (match[4]) {
      parts.push(
        <strong key={match.index} className="font-extrabold text-slate-900">
          {match[4]}
        </strong>
      );
    } else if (match[5]) {
      parts.push(
        <code key={match.index} className="bg-slate-200 text-slate-800 px-1 py-0.5 rounded text-[11px] font-mono">
          {match[5]}
        </code>
      );
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }
  return parts.length > 0 ? parts : text;
}

export default function SalesPitchGuide() {
  const navigate = useNavigate();

  const currentUser = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem('user') || '{}');
    } catch {
      return {};
    }
  }, []);

  const isAdmin = useMemo(() => {
    return (
      currentUser.role === 'admin' ||
      currentUser.role === 'super_admin' ||
      currentUser.role === 'admin_owner' ||
      (currentUser.permissions || []).includes('product_cost.manage.any') ||
      (currentUser.permissions || []).includes('system.user_manage.any')
    );
  }, [currentUser]);

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const selectedIdRef = useRef(selectedId);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  // Top Main Tab Navigation: 'ai_copilot' | 'subclass_directory'
  const [activeMainTab, setActiveMainTab] = useState('ai_copilot');

  // Interactive Country Detail Sub-Tab: 'packages' | 'eligibility' | 'timeline' | 'pitch' | 'objections'
  const [countryDetailTab, setCountryDetailTab] = useState('packages');

  // Progressive Selection: 1. Country -> 2. Subclass
  const [selectedCountry, setSelectedCountry] = useState('United States');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [countrySearch, setCountrySearch] = useState('');

  // AI Assistant State
  const [aiQuestion, setAiQuestion] = useState('');
  const [aiAnswer, setAiAnswer] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiModel, setAiModel] = useState('');
  const [aiTopic, setAiTopic] = useState('');
  const [aiSources, setAiSources] = useState(null);
  const [aiTargetCountry, setAiTargetCountry] = useState('');

  // Multi-Language Translation State (English | Marathi | Hindi)
  const [activeLanguage, setActiveLanguage] = useState('English');
  const [originalAiAnswer, setOriginalAiAnswer] = useState('');
  const [translatedAnswers, setTranslatedAnswers] = useState({});
  const [translatingLang, setTranslatingLang] = useState(null);

  // Quick Eligibility Checker State
  const [clientAge, setClientAge] = useState(29);
  const [clientExp, setClientExp] = useState(4);
  const [clientIelts, setClientIelts] = useState('7.0');
  const [clientDegree, setClientDegree] = useState('bachelor');

  // Objections search state
  const [objectionSearch, setObjectionSearch] = useState('');
  const [copiedPitch, setCopiedPitch] = useState(false);

  const token = localStorage.getItem('token');
  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/product-master?include_archived=false`, { headers: authHeaders });
      const raw = res.data?.items || [];
      const seen = new Set();
      const fetchedItems = [];
      raw.forEach((it) => {
        if (!it.id || seen.has(it.id)) return;
        seen.add(it.id);
        const normCountry = normalizeCountry(it.country);
        const normCode = it.country_code || getCountryCode(normCountry, it.country_code);
        fetchedItems.push({
          ...it,
          country: normCountry,
          country_code: normCode,
        });
      });
      setItems(fetchedItems);

      if (fetchedItems.length > 0) {
        let currentMatch = null;
        const targetId = selectedIdRef.current || selectedId;
        if (targetId) {
          currentMatch = fetchedItems.find((it) => it.id === targetId);
        }
        if (!currentMatch) {
          currentMatch = fetchedItems.find((it) => it.country?.toLowerCase() === selectedCountry?.toLowerCase()) || fetchedItems[0];
        }
        if (currentMatch) {
          setSelectedCountry(currentMatch.country || 'United States');
          setSelectedId(currentMatch.id);
          setSelectedProduct(currentMatch);
        }
      }
    } catch (err) {
      console.error('Failed to load pitch guide:', err);
      toast.error('Failed to load Sales Handbook');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []); // eslint-disable-line

  // When selectedId changes, update selectedProduct
  useEffect(() => {
    if (!selectedId) return;
    const found = items.find((it) => it.id === selectedId);
    if (found) {
      setSelectedProduct(found);
    }
  }, [selectedId, items]);

  // Distinct Countries Summary with Counts & Codes
  const countriesSummary = useMemo(() => {
    const map = {};
    items.forEach((it) => {
      const cName = it.country || 'Other';
      if (!map[cName]) {
        map[cName] = {
          name: cName,
          code: it.country_code || getCountryCode(cName, it.country_code),
          count: 0,
          categories: new Set(),
        };
      }
      map[cName].count += 1;
      if (it.category) map[cName].categories.add(it.category);
    });

    const priority = ['Australia', 'Canada', 'United Kingdom', 'United States', 'New Zealand', 'Germany'];
    return Object.values(map)
      .map((c) => ({ ...c, categoryList: Array.from(c.categories) }))
      .filter((c) => {
        if (!countrySearch.trim()) return true;
        const q = countrySearch.toLowerCase();
        return c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q);
      })
      .sort((a, b) => {
        const idxA = priority.indexOf(a.name);
        const idxB = priority.indexOf(b.name);
        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        if (idxA !== -1) return -1;
        if (idxB !== -1) return 1;
        return b.count - a.count;
      });
  }, [items, countrySearch]);

  // Categories available specifically for the currently selected country
  const availableCategoriesForCountry = useMemo(() => {
    const list = selectedCountry === 'all'
      ? items
      : items.filter((it) => it.country?.toLowerCase() === selectedCountry.toLowerCase());

    const counts = { all: list.length };
    list.forEach((it) => {
      const c = it.category || 'skilled_migration';
      const key = (c === 'pr' ? 'skilled_migration' : c);
      counts[key] = (counts[key] || 0) + 1;
    });

    return ALL_CATEGORY_OPTIONS.filter((cat) => cat.id === 'all' || (counts[cat.id] || 0) > 0)
      .map((cat) => ({
        ...cat,
        count: counts[cat.id] || 0,
      }));
  }, [items, selectedCountry]);

  // Subclasses for selected country and category
  const countrySubclasses = useMemo(() => {
    let list = items.filter((it) => it.country?.toLowerCase() === selectedCountry.toLowerCase());
    if (selectedCategory !== 'all') {
      list = list.filter((it) => {
        const cat = it.category || 'skilled_migration';
        return cat === selectedCategory || (selectedCategory === 'skilled_migration' && cat === 'pr');
      });
    }
    return list;
  }, [items, selectedCountry, selectedCategory]);

  // Subclasses filtered for directory 3-column view:
  const displayedSubclasses = useMemo(() => {
    if (search.trim()) {
      const q = search.toLowerCase();
      return items.filter((it) => {
        const n = (it.name || '').toLowerCase();
        const c = (it.country || '').toLowerCase();
        const cc = (it.country_code || getCountryCode(it.country, it.country_code)).toLowerCase();
        const v = (it.visa_type || '').toLowerCase();
        const s = (it.visa_subclass || '').toLowerCase();
        const sum = (it.summary || it.description || '').toLowerCase();
        return n.includes(q) || c.includes(q) || cc.includes(q) || v.includes(q) || s.includes(q) || sum.includes(q);
      });
    }

    let list = items;
    if (selectedCountry !== 'all') {
      list = list.filter((it) => it.country?.toLowerCase() === selectedCountry.toLowerCase());
    }

    if (selectedCategory !== 'all') {
      list = list.filter((it) => {
        const cat = it.category || 'skilled_migration';
        return cat === selectedCategory || (selectedCategory === 'skilled_migration' && cat === 'pr');
      });
    }

    return list;
  }, [items, selectedCountry, selectedCategory, search]);

  const handleSelectCountry = (countryName) => {
    setSelectedCountry(countryName);
    setSelectedCategory('all');

    const inCountry = countryName === 'all'
      ? items
      : items.filter((it) => it.country?.toLowerCase() === countryName.toLowerCase());

    if (inCountry.length > 0) {
      setSelectedId(inCountry[0].id);
      setSelectedProduct(inCountry[0]);
    } else {
      setSelectedId(null);
      setSelectedProduct(null);
    }
  };

  const handleSelectCategory = (catId) => {
    setSelectedCategory(catId);
    let list = items.filter((it) => it.country?.toLowerCase() === selectedCountry.toLowerCase());
    if (catId !== 'all') {
      list = list.filter((it) => {
        const cat = it.category || 'skilled_migration';
        return cat === catId || (catId === 'skilled_migration' && cat === 'pr');
      });
    }
    if (list.length > 0) {
      const stillInList = list.some((it) => it.id === (selectedIdRef.current || selectedId));
      if (!stillInList) {
        setSelectedId(list[0].id);
        setSelectedProduct(list[0]);
      }
    }
  };

  const handleSelectSubclass = (item) => {
    setSelectedId(item.id);
    setSelectedProduct(item);
    if (item.country && item.country !== selectedCountry) {
      setSelectedCountry(item.country);
    }
  };

  // Commercials & Pricing (Product Master as Single Source of Truth)
  const baseFee = parseFloat(selectedProduct?.service_price || selectedProduct?.base_fee || 0);
  const retainerGstApplicable = selectedProduct?.gst_applicable !== undefined
    ? Boolean(selectedProduct?.gst_applicable)
    : (selectedProduct?.commercials?.gst_applicable !== undefined
        ? Boolean(selectedProduct?.commercials?.gst_applicable)
        : true);
  const gstAmount = retainerGstApplicable ? Math.round(baseFee * 0.18) : 0;
  const totalWithGst = baseFee + gstAmount;

  const packageGstApplicable = selectedProduct?.package_gst_applicable !== undefined
    ? Boolean(selectedProduct?.package_gst_applicable)
    : false;

  const milestones = useMemo(() => {
    const raw = selectedProduct?.commercials?.milestones;
    if (raw && Array.isArray(raw) && raw.length > 0) {
      return raw.map((m, idx) => {
        const pct = parseFloat(m.percentage) || 0;
        const amt = parseFloat(m.amount) || Math.round(baseFee * (pct / 100));
        return {
          milestone_order: m.milestone_order || idx + 1,
          name: m.name || `Milestone ${idx + 1}`,
          percentage: pct,
          amount: amt,
          trigger: m.trigger || '',
        };
      });
    }
    return [
      { milestone_order: 1, name: 'Milestone 1: Retainer & Case Onboarding', percentage: 40, amount: Math.round(baseFee * 0.4), trigger: 'Signing engagement agreement' },
      { milestone_order: 2, name: 'Milestone 2: Skills Assessment Filing', percentage: 30, amount: Math.round(baseFee * 0.3), trigger: 'Dossier ready & assessment lodged' },
      { milestone_order: 3, name: 'Milestone 3: State EOI / Visa Lodgement', percentage: 30, amount: Math.round(baseFee * 0.3), trigger: 'Invitation received & final lodgement' },
    ];
  }, [selectedProduct?.commercials?.milestones, baseFee]);

  const packages = useMemo(() => {
    const rawPkgs = selectedProduct?.packages;
    if (rawPkgs && Array.isArray(rawPkgs) && rawPkgs.length > 0) {
      return rawPkgs.filter((p) => p.is_active !== false);
    }
    if (baseFee > 0) {
      return [
        { package_type: 'standard', name: 'Standard Package', price: baseFee, description: 'Core visa application guidance & assessment filing', is_active: true },
        { package_type: 'smart', name: 'Smart Package', price: Math.round(baseFee * 1.25), description: 'Includes documentation prep, priority reviews & exam support', is_active: true },
        { package_type: 'premium', name: 'Premium Package', price: Math.round(baseFee * 1.5), description: 'Full concierge, dedicated senior case manager & resume rebuild', is_active: true },
      ];
    }
    return [];
  }, [selectedProduct?.packages, baseFee]);

  const costAllocations = useMemo(() => {
    return selectedProduct?.cost_allocations || [];
  }, [selectedProduct?.cost_allocations]);

  const refundPolicy = useMemo(() => {
    return selectedProduct?.refund_policy || null;
  }, [selectedProduct?.refund_policy]);

  const isRefundEnabled = useMemo(() => {
    if (!refundPolicy) return false;
    return refundPolicy.enabled !== false;
  }, [refundPolicy]);

  const playbook = selectedProduct?.sales_playbook || {};
  const pitchPoints = playbook?.pitch_points || [];
  const elevatorPitch = playbook?.elevator_pitch || (
    pitchPoints.length > 0
      ? pitchPoints.join(' ')
      : `${selectedProduct?.name || 'This visa'} provides legal residence, employment authorization, and a recognized path to permanent settlement.`
  );

  const objs = selectedProduct?.objections_rebuttals || [];
  const faqs = selectedProduct?.faqs || [];
  const govCosts = selectedProduct?.government_costs || {};
  const checklist = selectedProduct?.document_checklist_template || [];
  const processTimeline = selectedProduct?.process_timeline || {};

  const copyText = (text, label) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard!`);
  };

  const copyElevatorPitch = () => {
    copyText(elevatorPitch, 'Elevator Pitch');
    setCopiedPitch(true);
    setTimeout(() => setCopiedPitch(false), 2000);
  };

  // Eligibility Calculation
  const pointsTested = selectedProduct?.eligibility_criteria?.points_based?.is_points_tested;
  const minPoints = selectedProduct?.eligibility_criteria?.points_based?.minimum_points || 65;

  let estPoints = 0;
  if (clientAge >= 25 && clientAge < 33) estPoints += 30;
  else if (clientAge >= 18 && clientAge < 25) estPoints += 25;
  else if (clientAge >= 33 && clientAge < 40) estPoints += 25;
  else if (clientAge >= 40 && clientAge < 45) estPoints += 15;

  if (clientIelts === '8.0') estPoints += 20;
  else if (clientIelts === '7.0') estPoints += 10;

  if (clientDegree === 'phd') estPoints += 20;
  else if (clientDegree === 'master' || clientDegree === 'bachelor') estPoints += 15;

  if (clientExp >= 8) estPoints += 15;
  else if (clientExp >= 5) estPoints += 10;
  else if (clientExp >= 3) estPoints += 5;

  const qualifies = !pointsTested || estPoints >= minPoints;

  const filteredObjs = objs.filter((o) => {
    if (!objectionSearch.trim()) return true;
    const q = objectionSearch.toLowerCase();
    return (o.objection || '').toLowerCase().includes(q) || (o.rebuttal || '').toLowerCase().includes(q);
  });

  const filteredFaqs = faqs.filter((f) => {
    if (!objectionSearch.trim()) return true;
    const q = objectionSearch.toLowerCase();
    return (f.question || '').toLowerCase().includes(q) || (f.answer || '').toLowerCase().includes(q);
  });

  // Dynamic Quick Scenarios based on Selected Country
  const countryScenarios = useMemo(() => {
    const norm = normalizeCountry(selectedCountry);
    if (norm === 'United States') {
      return [
        'US H-1B specialty occupation criteria, lottery cap and USCIS fee breakdown',
        'Can EB-2 NIW candidate self-petition without an employer job offer?',
        'L-1 Intracompany transferee requirements for executive vs specialized knowledge',
        'US B-1/B-2 visitor visa 10-year validity and DS-160 interview preparation',
        'F-1 student visa OPT 3-year STEM extension and H-1B transition path',
      ];
    }
    if (norm === 'Canada') {
      return [
        'Canada Express Entry FSW 67-point grid and CRS draw cutoff trends',
        'Can Canada FSW candidate include spouse & children? What are spouse work rights?',
        'Provincial Nominee Program (PNP) 600-point boost eligibility and streams',
        'Canada Study Permit proof of funds and Post-Graduation Work Permit (PGWP)',
        'Canada Super Visa medical insurance and multi-entry stay requirements',
      ];
    }
    if (norm === 'United Kingdom') {
      return [
        'UK Skilled Worker minimum salary threshold and Certificate of Sponsorship (CoS)',
        'UK shortage occupation list and Health and Care Worker visa fee exemption',
        'UK Indefinite Leave to Remain (ILR) 5-year route continuous residence rules',
        'Can UK Skilled Worker bring dependent spouse and children under current rules?',
      ];
    }
    if (norm === 'Germany') {
      return [
        'Germany Chancenkarte Opportunity Card 6-point criteria and job seeker rules',
        'EU Blue Card minimum gross salary threshold for STEM and shortage roles',
        'German language proficiency (A1/B1) and accelerated permanent settlement',
        'Recognition of foreign university degrees under Germany Anabin database',
      ];
    }
    if (norm === 'New Zealand') {
      return [
        'New Zealand 6-point Skilled Migrant Category (SMC) threshold and job offer',
        'Accredited Employer Work Visa (AEWV) median wage rate and employer accreditation',
        'Transition from NZ work visa to Permanent Resident Visa (PRV)',
      ];
    }
    // Default Australia
    return [
      'Australia Subclass 189 points calculation for client age 31 with 5 yrs exp',
      'Subclass 190 state nomination 5-point boost and Regional 491 15-point boost',
      'Subclass 482 employer sponsorship vs Subclass 189 direct PR pathway',
      'Partner visa Subclass 820/801 genuine relationship evidence checklist',
      'Skills assessment criteria for IT (ACS) and Engineers (Engineers Australia)',
    ];
  }, [selectedCountry]);

  // Ask AI Assistant (connected to Product Master Ground Truth)
  const handleAskAi = async (customPrompt) => {
    const q = (customPrompt || aiQuestion).trim();
    if (!q) {
      toast.error('Please enter a question or client scenario');
      return;
    }
    setAiLoading(true);
    setAiTopic(q);
    try {
      const res = await axios.post(
        `${API}/product-master/sales-ai-query`,
        {
          product_id: selectedProduct?.id || selectedId || null,
          country: selectedProduct?.country || selectedCountry || '',
          visa_name: selectedProduct?.name || '',
          visa_subclass: selectedProduct?.visa_subclass || '',
          client_scenario_or_question: q,
        },
        { headers: authHeaders }
      );
      const rawAns = res.data.answer;
      setAiAnswer(rawAns);
      setOriginalAiAnswer(rawAns);
      setAiModel(res.data.model || 'Verified Product Master AI');
      setAiSources(res.data.sources || null);
      if (res.data.target_country) {
        setAiTargetCountry(res.data.target_country);
      }

      // Detect initial answer language (if Devanagari script is present, identify Marathi/Hindi; otherwise English)
      const hasDevanagari = /[\u0900-\u097F]/.test(rawAns);
      let initialLang = 'English';
      if (hasDevanagari) {
        const isMarathi = /\b(?:आहे|नाही|करावे|साठी|मध्ये|मिळेल|लागेल|करा|कसा|काय|यावे)\b/.test(rawAns);
        initialLang = isMarathi ? 'Marathi' : 'Hindi';
      }
      setActiveLanguage(initialLang);
      setTranslatedAnswers({ [initialLang]: rawAns });

      // Auto-switch country & subclass if AI detects a different country from query (only when not a code mismatch)
      if (!res.data.occupation_detected?.is_mismatch && res.data.target_country && res.data.target_country.toLowerCase() !== selectedCountry.toLowerCase()) {
        setSelectedCountry(res.data.target_country);
      }
      if (!res.data.occupation_detected?.is_mismatch && res.data.target_product_id) {
        setSelectedId(res.data.target_product_id);
      }

      toast.success(`AI Advisory ready for ${res.data.target_country || selectedCountry}!`);
    } catch (err) {
      console.error('AI query error:', err);
      const detail = err.response?.data?.detail || err.message || 'AI query failed';
      toast.error(`AI Copilot: ${detail}`);
    } finally {
      setAiLoading(false);
    }
  };

  // Instant Multi-Language Translation Handler (English | Marathi | Hindi)
  const handleSelectLanguage = async (targetLang) => {
    if (activeLanguage === targetLang) return;
    const currentBase = originalAiAnswer || aiAnswer;
    if (!currentBase) return;

    // 1. Instant cache hit: Switch in 0ms!
    if (translatedAnswers[targetLang]) {
      setAiAnswer(translatedAnswers[targetLang]);
      setActiveLanguage(targetLang);
      toast.success(`Switched to ${targetLang}!`);
      return;
    }

    // 2. Fetch high-accuracy translation from backend
    setTranslatingLang(targetLang);
    try {
      const res = await axios.post(
        `${API}/product-master/sales-ai-translate`,
        {
          text: currentBase,
          target_language: targetLang,
          source_language: activeLanguage,
          country: aiTargetCountry || selectedCountry || '',
          visa_subclass: selectedProduct?.visa_subclass || '',
        },
        { headers: authHeaders }
      );
      const translated = res.data?.translated_text || currentBase;
      setTranslatedAnswers((prev) => ({
        ...prev,
        [targetLang]: translated,
      }));
      setAiAnswer(translated);
      setActiveLanguage(targetLang);
      toast.success(`Advisory translated to ${targetLang}!`);
    } catch (err) {
      console.error('Translation error:', err);
      toast.error(`Translation error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setTranslatingLang(null);
    }
  };

  // Print Document Utility
  const handlePrintDocument = () => {
    if (!aiAnswer) return;
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      toast.error('Please allow popups to print the advisory document');
      return;
    }

    const title = aiTopic || `LEAMSS Pitch Advisory - ${selectedCountry}`;
    const formattedHtml = aiAnswer
      .replace(/^### (.*$)/gim, '<h3 style="color:#0f172a; margin-top:18px; margin-bottom:6px; font-size:15px; font-weight:800;">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 style="color:#065f46; margin-top:22px; margin-bottom:8px; font-size:18px; font-weight:900; border-bottom:1px solid #cbd5e1; padding-bottom:4px;">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 style="color:#065f46; margin-top:24px; margin-bottom:12px; font-size:20px; font-weight:900;">$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote style="border-left:4px solid #059669; background:#f0fdf4; padding:10px 14px; margin:12px 0; border-radius:4px; color:#166534; font-style:italic;">$1</blockquote>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code style="background:#f1f5f9; padding:2px 5px; border-radius:4px; font-family:monospace; font-size:11px;">$1</code>')
      .replace(/^- (.*$)/gim, '<li style="margin-bottom:4px;">$1</li>')
      .replace(/\n\n/g, '<p style="margin: 8px 0;"></p>')
      .replace(/\n/g, '<br/>');

    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>${title}</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #0f172a; padding: 36px; margin: 0; }
            .header { border-bottom: 3px solid #059669; padding-bottom: 14px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: flex-end; }
            .logo { font-size: 22px; font-weight: 900; color: #059669; letter-spacing: -0.5px; }
            .sub { font-size: 12px; font-weight: 600; color: #475569; margin-top: 3px; }
            .meta { font-size: 11px; color: #64748b; text-align: right; }
            ul { padding-left: 20px; margin: 8px 0; }
            .footer { margin-top: 36px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #94a3b8; text-align: center; }
            @media print { body { padding: 15px; } }
          </style>
        </head>
        <body>
          <div class="header">
            <div>
              <div class="logo">LEAMSS IMMIGRATION CONSULTING</div>
              <div class="sub">Sales Pitch Advisory & Statutory Client Guidance Document</div>
            </div>
            <div class="meta">
              <div><strong>Date:</strong> ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
              <div><strong>Model:</strong> ${aiModel || 'Verified Product Master AI'}</div>
              <div><strong>Consultant:</strong> ${currentUser?.name || 'Sales Consultant'}</div>
            </div>
          </div>
          <div>${formattedHtml}</div>
          <div class="footer">
            CONFIDENTIAL • FOR AUTHORIZED LEAMSS SALES CONSULTANTS ONLY • STATUTORY ACCREDITED CRITERIA
          </div>
          <script>
            window.onload = function() { window.print(); }
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
  };

  // Download Document as HTML / PDF exportable file
  const handleDownloadDocument = () => {
    if (!aiAnswer) return;
    const title = aiTopic || `LEAMSS_Pitch_Advisory_${selectedCountry}`;
    const cleanFilename = `${title.replace(/[^a-zA-Z0-9_-]/g, '_')}.html`;

    const formattedHtml = aiAnswer
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^- (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/g, '<p></p>')
      .replace(/\n/g, '<br/>');

    const fullHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"/><title>${title}</title><style>body{font-family:sans-serif;line-height:1.6;color:#0f172a;max-width:850px;margin:30px auto;padding:24px;border:1px solid #cbd5e1;border-radius:12px;}h1,h2,h3{color:#065f46;}blockquote{border-left:4px solid #059669;background:#f0fdf4;padding:12px;margin:12px 0;font-style:italic;}code{background:#f1f5f9;padding:2px 4px;border-radius:4px;}</style></head><body><h1>LEAMSS Immigration Pitch Advisory</h1><p><strong>Topic:</strong> ${aiTopic}</p><hr/><div>${formattedHtml}</div><hr/><p style="font-size:11px;color:#94a3b8;text-align:center;">LEAMSS Internal Sales Advisory • Grounded in Verified Product Master</p></body></html>`;

    const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = cleanFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Document downloaded! Open in browser and choose Print -> Save as PDF to export.');
  };

  const activeCountryObj = countriesSummary.find((c) => c.name?.toLowerCase() === selectedCountry?.toLowerCase());
  const activeCountryCode = activeCountryObj?.code || getCountryCode(selectedCountry);

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto space-y-4">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. TOP HEADER & METADATA BAR                                   */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-1">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/sales/my-crm')}
            className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 transition shadow-sm"
            data-testid="sales-pitch-back-btn"
            title="Return to CRM"
          >
            <ArrowLeft className="h-4 w-4 text-slate-700" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-emerald-600 text-white shadow-sm inline-flex items-center justify-center">
                <Globe className="w-4 h-4" />
              </span>
              <h1 className="text-xl font-black text-slate-900 tracking-tight">
                Pitch Guide & Sales Handbook
              </h1>
              <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold uppercase tracking-wider">
                Sales Intelligence
              </Badge>
            </div>
            {/* Live Breadcrumb */}
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mt-1 font-medium">
              <span
                onClick={() => handleSelectCountry('all')}
                className="hover:text-emerald-700 cursor-pointer font-semibold"
              >
                Destinations
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              <span
                onClick={() => handleSelectCountry(selectedCountry)}
                className="inline-flex items-center gap-1 text-slate-800 font-bold hover:text-emerald-700 cursor-pointer"
              >
                <Flag code={getISO(selectedCountry)} style={{ width: '14px', height: '10px', objectFit: 'cover' }} />
                {selectedCountry} ({activeCountryCode})
              </span>
              {selectedProduct && (
                <>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-emerald-700 font-extrabold font-mono">
                    {selectedProduct.country_code || getCountryCode(selectedProduct.country)} • Subclass {selectedProduct.visa_subclass || selectedProduct.name}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs font-semibold px-3 py-1 bg-white border-slate-200 shadow-sm">
            👤 Consultant: {currentUser?.name || 'Sales Consultant'}
          </Badge>
          <Button
            size="sm"
            variant="ghost"
            onClick={loadData}
            className="h-8 px-2.5 text-slate-600 hover:bg-slate-100"
            title="Refresh Handbook Data"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. LARGE PROMINENT MAIN TABS SWITCHER                          */}
      {/* ───────────────────────────────────────────────────────────── */}
      <div className="p-1.5 bg-slate-100/90 rounded-2xl border border-slate-200/80 shadow-inner flex flex-col sm:flex-row items-center gap-2">
        <button
          onClick={() => setActiveMainTab('ai_copilot')}
          data-testid="main-tab-ai-copilot"
          className={`w-full sm:flex-1 py-3 px-5 rounded-xl font-black text-xs md:text-sm flex items-center justify-center gap-2.5 transition-all shadow-sm ${
            activeMainTab === 'ai_copilot'
              ? 'bg-gradient-to-r from-emerald-600 to-teal-700 text-white shadow-emerald-200'
              : 'text-slate-600 hover:text-slate-900 hover:bg-white/70'
          }`}
        >
          <Sparkles className="w-4 h-4 text-amber-300" />
          <span>AI Visa Pitch Copilot & Client Query Assistant</span>
          <Badge className="bg-white/20 text-white text-[10px] font-bold uppercase tracking-wider hidden md:inline-flex">
            Interactive
          </Badge>
        </button>

        <button
          onClick={() => setActiveMainTab('subclass_directory')}
          data-testid="main-tab-subclass-directory"
          className={`w-full sm:flex-1 py-3 px-5 rounded-xl font-black text-xs md:text-sm flex items-center justify-center gap-2.5 transition-all ${
            activeMainTab === 'subclass_directory'
              ? 'bg-white text-slate-900 shadow-sm border border-slate-200'
              : 'text-slate-600 hover:text-slate-900 hover:bg-white/70'
          }`}
        >
          <Layers className="w-4 h-4 text-emerald-600" />
          <span>Visa Subclass Directory & Deep-Dive Handbook</span>
          <Badge variant="outline" className="text-[10px] text-slate-600 border-slate-300 hidden md:inline-flex">
            {items.length} Visas
          </Badge>
        </button>
      </div>

      {/* ═════════════════════════════════════════════════════════════ */}
      {/* VIEW A: AI VISA PITCH COPILOT & CLIENT QUERY ASSISTANT         */}
      {/* ═════════════════════════════════════════════════════════════ */}
      {activeMainTab === 'ai_copilot' && (
        <div className="space-y-4">
          {/* ───────────────────────────────────────────────────────── */}
          {/* A1. LARGE HERO AI SEARCH & QUERY BOX                     */}
          {/* ───────────────────────────────────────────────────────── */}
          <Card className="p-4 md:p-5 bg-gradient-to-br from-indigo-50/70 via-white to-emerald-50/50 border-2 border-indigo-200 rounded-2xl shadow-sm space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-indigo-100/80 pb-2.5">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-indigo-600 text-white shadow-sm">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm md:text-base font-black text-slate-900 tracking-tight flex items-center gap-1.5">
                    AI Visa Pitch Copilot & Client Query Assistant
                    <Sparkles className="w-4 h-4 text-amber-500" />
                  </h2>
                  <p className="text-xs text-slate-500 font-medium">
                    Ask any question, objection scenario, or points dilemma during calls to receive instant verified regulatory guidance.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                  🛡️ Source of Truth: Product Master
                </Badge>
                {selectedProduct && (
                  <Badge variant="outline" className="text-[10px] font-semibold border-indigo-300 text-indigo-700 bg-white">
                    🎯 Context: {selectedCountry} • {selectedProduct.visa_subclass || selectedProduct.name}
                  </Badge>
                )}
              </div>
            </div>

            {/* Large Search Input */}
            <div className="flex flex-col sm:flex-row items-center gap-2">
              <div className="relative flex-1 w-full">
                <Search className="h-4 w-4 absolute left-3.5 top-3.5 text-slate-400" />
                <Input
                  placeholder="Search countries, visa categories, subclasses or ask client questions (e.g. client age 42 with 7 yrs exp for Australia 189, or H-1B timeline & USCIS fee)..."
                  value={aiQuestion}
                  onChange={(e) => setAiQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAskAi()}
                  className="pl-10 pr-9 text-xs md:text-sm h-11 bg-white focus:bg-white border-indigo-200 focus:border-indigo-500 rounded-xl font-medium shadow-sm w-full"
                  data-testid="ai-copilot-search-input"
                />
                {aiQuestion && (
                  <button
                    onClick={() => setAiQuestion('')}
                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 p-1"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>

              <Button
                onClick={() => handleAskAi()}
                disabled={aiLoading || !aiQuestion.trim()}
                className="w-full sm:w-auto h-11 px-5 bg-indigo-600 hover:bg-indigo-700 text-white font-extrabold text-xs md:text-sm gap-2 rounded-xl shrink-0 shadow-md shadow-indigo-100 transition-all"
                data-testid="ai-copilot-ask-btn"
              >
                {aiLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                {aiLoading ? 'Synthesizing...' : 'Ask AI Copilot'}
              </Button>
            </div>

            {/* Quick Scenario Chips - dynamically tailored to Selected Country */}
            <div className="flex items-center gap-1.5 flex-wrap pt-1">
              <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
                Quick {selectedCountry} Scenarios:
              </span>
              {countryScenarios.map((chipPrompt, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setAiQuestion(chipPrompt);
                    handleAskAi(chipPrompt);
                  }}
                  className="text-[11px] bg-white hover:bg-indigo-50 text-indigo-700 font-semibold px-2.5 py-1 rounded-lg border border-indigo-200 hover:border-indigo-300 transition text-left shadow-2xs"
                >
                  💡 {chipPrompt.length > 55 ? `${chipPrompt.slice(0, 55)}...` : chipPrompt}
                </button>
              ))}
            </div>
          </Card>

          {/* ───────────────────────────────────────────────────────── */}
          {/* A2. ATTRACTIVE COMPACT COUNTRY CARDS                     */}
          {/*     (Display compact country cards right below search box)*/}
          {/* ───────────────────────────────────────────────────────── */}
          <div className="space-y-2">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-emerald-600" />
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-700">
                  Select Country Destination ({countriesSummary.length})
                </h3>
              </div>
              <span className="text-xs text-slate-400 font-medium">
                Click any country to load its verified subclasses & AI pitch data
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {countriesSummary.map((c) => {
                const isSelected = selectedCountry?.toLowerCase() === c.name.toLowerCase();
                const iso = getISO(c.name);
                return (
                  <Card
                    key={c.name}
                    onClick={() => handleSelectCountry(c.name)}
                    data-testid={`country-card-${c.code.toLowerCase()}`}
                    className={`p-3.5 cursor-pointer rounded-2xl transition-all border-2 text-left relative overflow-hidden group ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-50/80 shadow-md ring-2 ring-emerald-300'
                        : 'border-slate-200 bg-white hover:border-emerald-300 hover:shadow-sm'
                    }`}
                  >
                    {/* Top Row: Flag + Code Badge */}
                    <div className="flex items-center justify-between gap-1 mb-2">
                      <div className="w-7 h-5 rounded overflow-hidden shadow-xs border border-slate-200 shrink-0">
                        <Flag code={iso} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      </div>
                      <Badge
                        variant={isSelected ? 'default' : 'outline'}
                        className={`text-[10px] font-black px-1.5 py-0 ${
                          isSelected
                            ? 'bg-emerald-600 text-white'
                            : 'border-slate-300 text-slate-700 bg-slate-50'
                        }`}
                      >
                        {c.code}
                      </Badge>
                    </div>

                    {/* Country Name */}
                    <div className="font-extrabold text-xs md:text-sm text-slate-900 group-hover:text-emerald-700 truncate">
                      {c.name}
                    </div>

                    {/* Bottom Metadata: Subclass Count */}
                    <div className="flex items-center justify-between mt-1 text-[11px] text-slate-500 font-semibold">
                      <span>{c.count} {c.count === 1 ? 'Visa' : 'Visas'}</span>
                      {isSelected ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-emerald-500" />
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* ───────────────────────────────────────────────────────── */}
          {/* A3. PROFESSIONAL AI ADVISORY DOCUMENT VIEWER             */}
          {/* ───────────────────────────────────────────────────────── */}
          {aiAnswer && (
            <Card className="p-5 md:p-6 bg-white border-2 border-emerald-500 rounded-2xl shadow-lg space-y-4 animate-in fade-in duration-200">
              {/* Document Header & Action Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-100 pb-3">
                <div className="flex items-center gap-2.5">
                  <span className="p-2 rounded-xl bg-emerald-600 text-white shadow-sm">
                    <FileText className="w-4 h-4" />
                  </span>
                  <div>
                    <h3 className="text-sm md:text-base font-black text-slate-900 tracking-tight">
                      LEAMSS Statutory Sales Advisory & Pitch Guidance
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500 font-medium">
                      <span>Destination: <strong className="text-emerald-800">{aiTargetCountry || selectedCountry}</strong></span>
                      <span>•</span>
                      <span>Topic: <em>"{aiTopic || 'Client Consultation Query'}"</em></span>
                      <span>•</span>
                      <Badge className="bg-emerald-50 text-emerald-800 border-emerald-200 text-[10px] font-bold">
                        Engine: {aiModel}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Document Actions: Copy, Print, Download */}
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyText(aiAnswer, 'Advisory Document')}
                    className="h-8 px-3 text-xs font-bold text-slate-700 border-slate-300 hover:bg-slate-50 gap-1.5"
                    data-testid="ai-doc-copy-btn"
                  >
                    <Copy className="w-3.5 h-3.5 text-emerald-600" />
                    Copy
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleDownloadDocument}
                    className="h-8 px-3 text-xs font-bold text-slate-700 border-slate-300 hover:bg-slate-50 gap-1.5"
                    data-testid="ai-doc-download-btn"
                  >
                    <Download className="w-3.5 h-3.5 text-blue-600" />
                    Download PDF
                  </Button>

                  <Button
                    size="sm"
                    onClick={handlePrintDocument}
                    className="h-8 px-3 text-xs font-bold bg-emerald-700 hover:bg-emerald-800 text-white gap-1.5 shadow-sm"
                    data-testid="ai-doc-print-btn"
                  >
                    <Printer className="w-3.5 h-3.5" />
                    Print
                  </Button>

                  <button
                    onClick={() => {
                      setAiAnswer('');
                      setOriginalAiAnswer('');
                      setTranslatedAnswers({});
                      setActiveLanguage('English');
                    }}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 ml-1"
                    title="Dismiss Document"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Multi-Language Translation Bar (English | Marathi | Hindi) */}
              <div className="flex flex-wrap items-center justify-between gap-2.5 p-2.5 bg-gradient-to-r from-emerald-50/90 via-sky-50/50 to-emerald-50/90 border border-emerald-200 rounded-xl shadow-2xs">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black text-slate-800 uppercase tracking-wide flex items-center gap-1.5">
                    <Languages className="w-4 h-4 text-emerald-700" />
                    Translate AI Answer:
                  </span>
                  <span className="text-[11px] text-slate-500 hidden sm:inline font-medium">
                    (Select language to instantly translate the complete answer)
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  {[
                    { id: 'English', label: 'English', flag: '🇬🇧' },
                    { id: 'Marathi', label: 'मराठी (Marathi)', flag: '🇮🇳' },
                    { id: 'Hindi', label: 'हिंदी (Hindi)', flag: '🇮🇳' },
                  ].map((l) => {
                    const isSelected = activeLanguage === l.id;
                    const isLoading = translatingLang === l.id;
                    return (
                      <button
                        key={l.id}
                        onClick={() => handleSelectLanguage(l.id)}
                        disabled={translatingLang !== null}
                        className={`px-3 py-1.5 rounded-lg text-xs font-extrabold transition flex items-center gap-1.5 cursor-pointer ${
                          isSelected
                            ? 'bg-emerald-700 text-white shadow-sm ring-2 ring-emerald-500/30'
                            : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-100 hover:text-slate-900'
                        }`}
                        data-testid={`ai-lang-btn-${l.id.toLowerCase().split(' ')[0]}`}
                      >
                        <span>{l.flag}</span>
                        <span>{l.label}</span>
                        {isLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-700" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Verified Sources Quick-Access Action Bar */}
              {aiSources && (
                <div className="flex flex-wrap items-center gap-2 p-2.5 bg-slate-50 border border-slate-200 rounded-xl">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Verified Sources:
                  </span>
                  {aiSources.government_portal && (
                    <a
                      href={aiSources.government_portal}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 text-[11px] font-bold text-emerald-800 transition"
                      title="Open official sovereign immigration government website"
                    >
                      <Globe className="w-3 h-3 text-emerald-600" />
                      🏛️ Official Gov Portal ({aiSources.government_authority || 'Immigration Authority'})
                      <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                    </a>
                  )}
                  {aiSources.migrate_page_url && (
                    <a
                      href={aiSources.migrate_page_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 border border-blue-300 text-[11px] font-bold text-blue-800 transition"
                      title="Open LEAMSS Migrate client page"
                    >
                      <Globe className="w-3 h-3 text-blue-600" />
                      🌐 LEAMSS Migrate Page
                      <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                    </a>
                  )}
                  {aiSources.atlas_page_url && (
                    <a
                      href={aiSources.atlas_page_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-50 hover:bg-purple-100 border border-purple-300 text-[11px] font-bold text-purple-800 transition"
                      title="Open LEAMSS Migration Atlas"
                    >
                      <Compass className="w-3 h-3 text-purple-600" />
                      🗺️ LEAMSS Migration Atlas
                      <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                    </a>
                  )}
                  {aiSources.vfs_url && (
                    <a
                      href={aiSources.vfs_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 border border-amber-300 text-[11px] font-bold text-amber-800 transition"
                    >
                      🏢 VFS Global Center
                      <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                    </a>
                  )}
                </div>
              )}

              {/* Formatted Structured Document Content */}
              <div className="bg-slate-50/70 p-4 md:p-5 rounded-xl border border-slate-200/80 space-y-4 text-xs md:text-sm text-slate-800 leading-relaxed">
                {aiAnswer
                  .replace(/\n*[_*]*Sources(?:\s*\(.*?\))?:?[_*]*\s*\n+(?:[-*]\s*https?:\/\/\S+\n*)+/gi, '')
                  .replace(/\n*### 🔗\s*(?:6\.)?[\s\S]*?(?=\n*###|\n*>|\Z)/gi, '')
                  .split(/(?:\n|^)(?=###\s+|> \*\*LEAMSS Statutory Disclaimer|\[!NOTE\])/)
                  .map((block, bIdx) => {
                    const trimmed = block.trim();
                    if (!trimmed) return null;

                    // Filter out raw sources or URL lines
                    if (
                      trimmed.toLowerCase().startsWith('_sources') ||
                      trimmed.toLowerCase().startsWith('sources:') ||
                      trimmed.startsWith('http://') ||
                      trimmed.startsWith('https://')
                    ) {
                      return null;
                    }

                    // 1. Speaking Script Block (Section 1 - Primary Callout)
                    if (
                      trimmed.includes('Speaking Script') ||
                      trimmed.includes('Recommended Phone Pitch') ||
                      trimmed.includes('Recommended Call Script') ||
                      trimmed.startsWith('### 💬 1') ||
                      trimmed.startsWith('### 💬')
                    ) {
                      const lines = trimmed.split('\n');
                      const contentLines = lines.slice(1).filter((l) => l.trim().length > 0);
                      const scriptLines = contentLines.filter(
                        (l) => !l.trim().startsWith('- ') && !l.trim().startsWith('* ')
                      );
                      const rawScript = (scriptLines.length > 0 ? scriptLines : contentLines)
                        .join(' ')
                        .replace(/^>\s*/gm, '')
                        .replace(/^[*_"\s]+|[*_"\s]+$/g, '')
                        .trim();
                      const displayScript = rawScript || 'Review statutory eligibility criteria with the client.';

                      // Other sub-bullets in this block (like objections if grouped)
                      const otherLines = contentLines.filter((l) => l.trim().startsWith('- ') || l.trim().startsWith('* '));

                      return (
                        <div
                          key={bIdx}
                          className="p-4 md:p-5 bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50/80 border-2 border-emerald-500 rounded-xl shadow-sm space-y-3"
                        >
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <span className="text-xs md:text-sm font-black text-emerald-950 uppercase tracking-wide flex items-center gap-2">
                              <PhoneCall className="w-4 h-4 text-emerald-600" />
                              Live Call Speaking Script (Read Directly to Client)
                            </span>
                            <button
                              onClick={() => copyText(displayScript, 'Speaking Script')}
                              className="px-3 py-1 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition"
                            >
                              <Copy className="w-3.5 h-3.5" /> Copy Script
                            </button>
                          </div>
                          <div className="p-3.5 bg-white rounded-lg border border-emerald-200/80 shadow-2xs">
                            <p className="font-semibold text-emerald-950 text-xs md:text-sm leading-relaxed italic">
                              "{displayScript}"
                            </p>
                          </div>
                          {otherLines.length > 0 && (
                            <div className="space-y-1.5 pt-1">
                              {otherLines.map((ol, oIdx) => (
                                <div key={oIdx} className="text-xs text-slate-700 font-medium">
                                  {renderFormattedInline(ol)}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    }

                    // 2. Direct Quick Answer & Key Facts Card
                    if (
                      trimmed.includes('Direct Quick Answer') ||
                      trimmed.includes('⚡ Quick Answer') ||
                      trimmed.includes('Key Facts & Eligibility')
                    ) {
                      const lines = trimmed.split('\n');
                      const heading = lines[0].replace(/^###\s*/, '');
                      const contentLines = lines.slice(1).filter((l) => l.trim().length > 0);
                      const plainContent = contentLines.map((l) => l.replace(/^[-*]\s*/, '')).join(' ');

                      return (
                        <div
                          key={bIdx}
                          className="p-4 bg-gradient-to-r from-sky-50 via-indigo-50/40 to-sky-50 border-2 border-sky-300 rounded-xl shadow-xs space-y-2.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs md:text-sm font-black text-slate-900 flex items-center gap-1.5">
                              <Zap className="w-4 h-4 text-sky-600 fill-sky-500" />
                              {heading}
                            </span>
                            <button
                              onClick={() => copyText(plainContent, 'Quick Facts')}
                              className="px-2.5 py-1 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-[11px] font-bold flex items-center gap-1 shadow-xs transition"
                            >
                              <Copy className="w-3 h-3" /> Copy Facts
                            </button>
                          </div>
                          <ul className="space-y-1.5 pl-1">
                            {contentLines.map((cl, cIdx) => (
                              <li key={cIdx} className="text-xs md:text-sm font-medium text-slate-800 flex items-start gap-2">
                                <CheckCircle2 className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
                                <span>{renderFormattedInline(cl.replace(/^[-*]\s*/, ''))}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      );
                    }

                    // 3. Statutory Compliance Disclaimer Block (Clean discreet footer)
                    if (
                      trimmed.includes('Statutory Disclaimer') ||
                      trimmed.includes('LEAMSS Statutory Disclaimer') ||
                      trimmed.includes('[!NOTE]')
                    ) {
                      const cleanDisclaimer = trimmed
                        .replace(/\[!NOTE\]\s*/g, '')
                        .replace(/^>\s*/gm, '')
                        .replace(/\*\*/g, '')
                        .trim();
                      return (
                        <div
                          key={bIdx}
                          className="p-3 bg-slate-100 rounded-xl border border-slate-200 text-slate-600 text-[11px] flex items-start gap-2.5 leading-relaxed"
                        >
                          <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                          <div>
                            <strong className="text-slate-800">LEAMSS Statutory Compliance:</strong>{' '}
                            {cleanDisclaimer.replace(/^LEAMSS Statutory Disclaimer:\s*/i, '')}
                          </div>
                        </div>
                      );
                    }

                    // 4. Heading Level 2
                    if (trimmed.startsWith('## ')) {
                      return (
                        <h2 key={bIdx} className="text-sm md:text-base font-black text-slate-900 border-b border-slate-200 pb-1 pt-2">
                          {renderFormattedInline(trimmed.replace(/^## /, ''))}
                        </h2>
                      );
                    }

                    // 5. Heading Level 3 (Sections)
                    if (trimmed.startsWith('### ')) {
                      const lines = trimmed.split('\n');
                      const heading = lines[0].replace(/^###\s*/, '');
                      return (
                        <div key={bIdx} className="space-y-2 pt-1">
                          <h3 className="text-xs md:text-sm font-extrabold text-slate-900 flex items-center gap-1.5">
                            {renderFormattedInline(heading)}
                          </h3>
                          {lines.slice(1).map((subLine, sIdx) => {
                            const sl = subLine.trim();
                            if (!sl) return null;
                            if (sl.startsWith('- ') || sl.startsWith('* ')) {
                              return (
                                <div key={sIdx} className="flex items-start gap-2 py-0.5 pl-2 text-xs md:text-sm font-medium text-slate-700">
                                  <span className="text-indigo-600 font-bold shrink-0">•</span>
                                  <span>{renderFormattedInline(sl.replace(/^[-*]\s*/, ''))}</span>
                                </div>
                              );
                            }
                            return (
                              <p key={sIdx} className="text-xs md:text-sm text-slate-700 leading-relaxed font-medium pl-2">
                                {renderFormattedInline(sl)}
                              </p>
                            );
                          })}
                        </div>
                      );
                    }

                    // 6. Bullet List Block
                    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                      const items = trimmed.split('\n').filter((l) => l.trim().startsWith('- ') || l.trim().startsWith('* '));
                      return (
                        <ul key={bIdx} className="space-y-1.5 pl-4 list-disc marker:text-emerald-600">
                          {items.map((it, iIdx) => {
                            const text = it.replace(/^[-*]\s+/, '');
                            return (
                              <li key={iIdx} className="font-medium text-slate-700 text-xs md:text-sm">
                                {renderFormattedInline(text)}
                              </li>
                            );
                          })}
                        </ul>
                      );
                    }

                    // 7. Standard Paragraph
                    return (
                      <p key={bIdx} className="text-slate-800 font-medium whitespace-pre-line leading-relaxed text-xs md:text-sm">
                        {renderFormattedInline(trimmed)}
                      </p>
                    );
                  })}
              </div>
            </Card>
          )}

          {/* ───────────────────────────────────────────────────────── */}
          {/* A4. INTERACTIVE COUNTRY DETAILS CONSOLE                  */}
          {/* ───────────────────────────────────────────────────────── */}
          <Card className="p-4 md:p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-5">
            {/* Country Banner & Subclass Picker Header */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-7 rounded-md overflow-hidden shadow-sm border border-slate-200 shrink-0">
                  <Flag code={getISO(selectedCountry)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base md:text-lg font-black text-slate-900 tracking-tight">
                      {selectedCountry} ({activeCountryCode})
                    </h2>
                    <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                      {countrySubclasses.length} Available Subclasses
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 font-medium">
                    Authority: {selectedProduct?.authority_name || 'Statutory Immigration Department'}
                  </p>
                </div>
              </div>

              {/* Category Filters */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {availableCategoriesForCountry.map((cat) => (
                  <button
                    key={cat.id}
                    onClick={() => handleSelectCategory(cat.id)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition flex items-center gap-1 ${
                      selectedCategory === cat.id
                        ? 'bg-slate-900 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    <span>{cat.icon}</span>
                    <span>{cat.name}</span>
                    <span className="text-[10px] opacity-70">({cat.count})</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Subclasses Selection Chips */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
                Select Visa Subclass:
              </span>
              <div className="flex items-center gap-2 flex-wrap">
                {countrySubclasses.map((item) => {
                  const isCur = selectedProduct?.id === item.id;
                  const cCode = item.country_code || getCountryCode(item.country);
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelectSubclass(item)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-black transition-all flex items-center gap-2 border ${
                        isCur
                          ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-800 border-slate-200'
                      }`}
                    >
                      <span className={`text-[10px] font-mono px-1 rounded ${isCur ? 'bg-emerald-700 text-white' : 'bg-slate-200 text-slate-700'}`}>
                        {cCode} • {item.visa_subclass || item.name}
                      </span>
                      <span>{item.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Subclass Detail Interactive Tabs */}
            {selectedProduct ? (
              <div className="space-y-4 pt-2">
                {/* Tab Strip */}
                <div className="flex items-center gap-1 border-b border-slate-200 overflow-x-auto pb-px">
                  {[
                    { id: 'packages', label: '📦 Commercial Packages & Fees', icon: DollarSign },
                    { id: 'eligibility', label: '🎯 Statutory Eligibility & Points', icon: UserCheck },
                    { id: 'timeline', label: '🗺️ Process Milestones & Timeline', icon: Clock },
                    { id: 'pitch', label: '📣 Sales Pitch & 30-Sec Scripts', icon: Target },
                    { id: 'objections', label: '🛡️ Client Objections & FAQs', icon: HelpCircle },
                  ].map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setCountryDetailTab(t.id)}
                      className={`py-2 px-3 text-xs font-bold border-b-2 transition whitespace-nowrap flex items-center gap-1.5 ${
                        countryDetailTab === t.id
                          ? 'border-emerald-600 text-emerald-800 bg-emerald-50/50 rounded-t-lg'
                          : 'border-transparent text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      <span>{t.label}</span>
                    </button>
                  ))}
                </div>

                {/* TAB 1: COMMERCIAL PACKAGES & FEES */}
                {countryDetailTab === 'packages' && (
                  <div className="space-y-4">
                    {/* Top Row: LEAMSS Retainer & Official Government Fees */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* LEAMSS Retainer & 18% GST */}
                      <Card className="p-4 bg-slate-50/60 border border-slate-200 rounded-xl space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                          <div className="flex items-center gap-2">
                            <DollarSign className="w-4 h-4 text-emerald-600" />
                            <h4 className="text-xs font-black uppercase tracking-wide text-slate-900">
                              LEAMSS Professional Retainer Package
                            </h4>
                          </div>
                          <Badge className={retainerGstApplicable ? "bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold" : "bg-slate-100 text-slate-700 border-slate-300 text-[10px] font-bold"}>
                            {retainerGstApplicable ? "18% GST Compliant" : "GST Not Applicable (0%)"}
                          </Badge>
                        </div>

                        <div className={`grid ${retainerGstApplicable ? 'grid-cols-3' : 'grid-cols-2'} gap-2 text-center`}>
                          <div className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
                            <div className="text-[10px] text-slate-500 font-semibold">Base Retainer</div>
                            <div className="text-sm font-black text-slate-900">{formatINR(baseFee)}</div>
                          </div>
                          {retainerGstApplicable && (
                            <div className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-2xs">
                              <div className="text-[10px] text-slate-500 font-semibold">18% GST</div>
                              <div className="text-sm font-bold text-slate-700">{formatINR(gstAmount)}</div>
                            </div>
                          )}
                          <div className="p-2.5 bg-emerald-50 rounded-lg border border-emerald-200 shadow-2xs">
                            <div className="text-[10px] text-emerald-800 font-semibold">
                              {retainerGstApplicable ? 'Total Client Investment' : 'Total Investment (Net)'}
                            </div>
                            <div className="text-sm font-black text-emerald-700">{formatINR(totalWithGst)}</div>
                          </div>
                        </div>

                        {/* Milestones Schedule */}
                        <div className="space-y-1.5 pt-1">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-extrabold uppercase text-slate-500">
                              Retainer Milestone Payment Schedule:
                            </span>
                            <span className="text-[10px] text-slate-400 font-medium">
                              Linked to Operational Delivery
                            </span>
                          </div>
                          {milestones.map((m, idx) => (
                            <div key={idx} className="p-2.5 bg-white rounded-lg border border-slate-200 text-xs space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-slate-800">{m.name}</span>
                                <span className="font-mono font-black text-emerald-700">
                                  {m.percentage}% ({formatINR(m.amount)})
                                </span>
                              </div>
                              {m.trigger && (
                                <p className="text-[10px] text-slate-500 italic flex items-center gap-1">
                                  <Clock className="w-2.5 h-2.5 text-slate-400 shrink-0" />
                                  <span>Delivery Trigger: {m.trigger}</span>
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </Card>

                      {/* Official Statutory Government Fees */}
                      <Card className="p-4 bg-slate-50/60 border border-slate-200 rounded-xl space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                          <div className="flex items-center gap-2">
                            <Coins className="w-4 h-4 text-blue-600" />
                            <h4 className="text-xs font-black uppercase tracking-wide text-slate-900">
                              Statutory Government Fee Slabs
                            </h4>
                          </div>
                          <Badge variant="outline" className="text-[10px] font-bold border-blue-300 text-blue-700 bg-white">
                            Currency: {govCosts.currency || 'USD'}
                          </Badge>
                        </div>

                        <div className="space-y-2 text-xs">
                          <div className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-slate-200">
                            <span className="font-semibold text-slate-800">Primary Applicant Lodgement:</span>
                            <span className="font-mono font-black text-blue-900">
                              {govCosts.currency || 'USD'} {Number(govCosts.primary_applicant || 0).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-slate-200">
                            <span className="font-semibold text-slate-800">Secondary Adult Applicant (Spouse):</span>
                            <span className="font-mono font-bold text-slate-700">
                              {govCosts.currency || 'USD'} {Number(govCosts.secondary_adult || 0).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex items-center justify-between p-2.5 bg-white rounded-lg border border-slate-200">
                            <span className="font-semibold text-slate-800">Child Applicant (Under 18):</span>
                            <span className="font-mono font-bold text-slate-700">
                              {govCosts.currency || 'USD'} {Number(govCosts.secondary_child || 0).toLocaleString()}
                            </span>
                          </div>
                        </div>

                        <p className="text-[11px] text-slate-500 italic pt-1">
                          * Note: Statutory government lodgement fees are paid directly to the destination immigration authority ({selectedProduct?.authority_name || 'Government Authority'}).
                        </p>
                      </Card>
                    </div>

                    {/* Client Portal Package Tiers (Standard / Smart / Premium / Custom) */}
                    {packages.length > 0 && (
                      <Card className="p-4 bg-white border border-slate-200 rounded-xl space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                          <div className="flex items-center gap-2">
                            <Layers className="w-4 h-4 text-purple-600" />
                            <h4 className="text-xs font-black uppercase tracking-wide text-slate-900">
                              Client Portal Package Tiers ({packages.length} Configured)
                            </h4>
                          </div>
                          <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-[10px] font-bold">
                            Product Master Tiers
                          </Badge>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {packages.map((pkg, idx) => {
                            const pPrice = Number(pkg.price || 0);
                            const isTierGst = pkg.gst_applicable !== undefined
                              ? Boolean(pkg.gst_applicable)
                              : packageGstApplicable;
                            const pGst = isTierGst ? Math.round(pPrice * 0.18) : 0;
                            const pTotal = pPrice + pGst;
                            const isStd = (pkg.package_type || '').toLowerCase() === 'standard';
                            const isSmart = (pkg.package_type || '').toLowerCase() === 'smart';
                            const isPrem = (pkg.package_type || '').toLowerCase() === 'premium';

                            const effectivePkg = {
                              ...pkg,
                              price: pPrice,
                              refund_policy: pkg.refund_policy || (selectedProduct?.refund_policy ? {
                                ...selectedProduct.refund_policy,
                                enabled: true,
                              } : null),
                            };

                            const hasRefundPolicy = Boolean(
                              effectivePkg.refund_policy &&
                              effectivePkg.refund_policy.enabled !== false &&
                              effectivePkg.refund_policy.policy_type !== 'none'
                            );

                            return (
                              <div
                                key={idx}
                                className={`p-3.5 rounded-xl border transition-all flex flex-col justify-between space-y-3 ${
                                  isPrem
                                    ? 'bg-amber-50/40 border-amber-300 ring-1 ring-amber-300/50'
                                    : isSmart
                                    ? 'bg-indigo-50/40 border-indigo-200'
                                    : 'bg-slate-50/70 border-slate-200'
                                }`}
                              >
                                <div className="space-y-2.5">
                                  <div className="flex items-center justify-between">
                                    <span className="font-extrabold text-xs text-slate-900">{pkg.name}</span>
                                    <Badge
                                      variant="outline"
                                      className={`text-[9px] uppercase font-bold ${
                                        isPrem
                                          ? 'bg-amber-100 text-amber-800 border-amber-300'
                                          : isSmart
                                          ? 'bg-indigo-100 text-indigo-800 border-indigo-300'
                                          : 'bg-slate-200 text-slate-800 border-slate-300'
                                      }`}
                                    >
                                      {pkg.package_type || 'Tier'}
                                    </Badge>
                                  </div>

                                  <div className="space-y-0.5">
                                    <div className="text-base font-black text-slate-900">{formatINR(pPrice)}</div>
                                    {isTierGst ? (
                                      <div className="text-[10px] text-purple-700 font-medium">
                                        + 18% GST ({formatINR(pGst)}) = <strong className="text-slate-800 font-extrabold">{formatINR(pTotal)}</strong>
                                      </div>
                                    ) : (
                                      <div className="text-[10px] text-slate-500 font-medium">
                                        Net Package Investment <span className="text-slate-400 font-normal">(No GST)</span>
                                      </div>
                                    )}
                                  </div>

                                  {pkg.description && (
                                    <p className="text-[11px] text-slate-600 leading-snug bg-white/80 p-2 rounded-lg border border-slate-100">
                                      {pkg.description}
                                    </p>
                                  )}
                                </div>

                                {/* Package-level Refund Policy & Guarantees for Salesperson */}
                                <div className="pt-2 border-t border-slate-200/70 mt-auto space-y-1.5">
                                  <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wide flex items-center justify-between">
                                    <span className="flex items-center gap-1">
                                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                                      <span>Package Refund Safeguard</span>
                                    </span>
                                    {hasRefundPolicy && (
                                      <Badge variant="outline" className="text-[8px] font-bold py-0 text-slate-500">
                                        Active
                                      </Badge>
                                    )}
                                  </div>

                                  {hasRefundPolicy ? (
                                    <PackageRefundBadge pkg={effectivePkg} compact={false} showConditions={true} />
                                  ) : (
                                    <div className="p-2 rounded-lg bg-slate-100/70 border border-dashed border-slate-200 text-center">
                                      <span className="text-[10px] font-semibold text-slate-400 flex items-center justify-center gap-1">
                                        <ShieldAlert className="h-3 w-3 text-slate-400" />
                                        No Refund Policy Configured
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </Card>
                    )}

                    {/* Commissions, Partner Splits & Sales Economics */}
                    {costAllocations.length > 0 && (
                      <Card className="p-4 bg-white border border-slate-200 rounded-xl space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                          <div className="flex items-center gap-2">
                            <Briefcase className="w-4 h-4 text-emerald-700" />
                            <h4 className="text-xs font-black uppercase tracking-wide text-slate-900">
                              Commissions, Partner Splits & Sales Economics
                            </h4>
                          </div>
                          <Badge className="bg-emerald-50 text-emerald-800 border-emerald-200 text-[10px] font-bold">
                            Internal & Partner Allocations
                          </Badge>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                          {costAllocations.map((a, idx) => {
                            const isPct = a.payment_type === 'percentage';
                            const rateVal = parseFloat(a.rate !== undefined && a.rate !== null && a.rate !== '' ? a.rate : a.amount) || 0;
                            const amtVal = parseFloat(a.amount !== undefined && a.amount !== null && a.amount !== '' ? a.amount : a.rate) || 0;
                            const calcAmount = isPct ? Math.round(baseFee * (rateVal / 100)) : amtVal;

                            const isInternalSales = a.vendor_category === 'internal_partner' || (a.label || '').toLowerCase().includes('internal salesperson');

                            return (
                              <div
                                key={idx}
                                className={`p-2.5 rounded-lg border text-xs flex items-center justify-between gap-2 ${
                                  isInternalSales
                                    ? 'bg-emerald-50/80 border-emerald-300'
                                    : 'bg-slate-50 border-slate-200'
                                }`}
                              >
                                <div className="space-y-0.5 min-w-0">
                                  <div className="font-bold text-slate-900 truncate flex items-center gap-1">
                                    {a.label || a.vendor_category}
                                    {isInternalSales && (
                                      <Badge className="bg-emerald-600 text-white text-[8px] py-0 px-1">Your Split</Badge>
                                    )}
                                  </div>
                                  <div className="text-[10px] text-slate-500">
                                    {isPct ? `${rateVal}% of Retainer` : 'Flat Fee'}
                                  </div>
                                </div>
                                <div className="text-right shrink-0">
                                  <div className="font-extrabold text-emerald-800">{formatINR(calcAmount)}</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </Card>
                    )}

                    {/* Refund Policy Master & Statutory Safeguards */}
                    {refundPolicy && (
                      <Card className="p-4 bg-white border border-slate-200 rounded-xl space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                          <div className="flex items-center gap-2">
                            <ShieldCheck className="w-4 h-4 text-emerald-700" />
                            <h4 className="text-xs font-black uppercase tracking-wide text-slate-900">
                              Refund Policy Master & Statutory Safeguards
                            </h4>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Badge
                              className={`text-[10px] font-bold ${
                                isRefundEnabled
                                  ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                                  : 'bg-amber-100 text-amber-800 border-amber-300'
                              }`}
                            >
                              {isRefundEnabled ? 'Active for Sales' : 'Restricted by Admin'}
                            </Badge>
                            {refundPolicy.version && (
                              <Badge variant="outline" className="text-[9px] text-slate-500">v{refundPolicy.version}</Badge>
                            )}
                          </div>
                        </div>

                        {isRefundEnabled ? (
                          <div className="space-y-3">
                            {/* Model Banner */}
                            <div className="p-3 rounded-lg bg-emerald-50/60 border border-emerald-200 flex items-center justify-between flex-wrap gap-2">
                              <div>
                                <span className="text-[10px] font-bold text-emerald-800 uppercase block">Selected Policy Model</span>
                                <h5 className="text-xs font-black text-emerald-950">
                                  {refundPolicy.name || (refundPolicy.policy_type === 'protection' ? 'LEAMSS Protection Policy Guarantee' : refundPolicy.policy_type === 'standard' ? 'Standard Tiered Refund Policy' : 'No Refund Policy')}
                                </h5>
                              </div>
                              <div className="flex items-center gap-3 text-xs">
                                <div className="text-right">
                                  <span className="text-[10px] text-slate-500 font-medium block">Service Fee Refundable</span>
                                  <span className="font-black text-emerald-700 text-sm">{refundPolicy.refundable_service_fee_pct ?? 100}%</span>
                                </div>
                                <div className="text-right">
                                  <span className="text-[10px] text-slate-500 font-medium block">Claim Window</span>
                                  <span className="font-bold text-slate-800">{refundPolicy.claim_window_days || 30} days</span>
                                </div>
                                <div className="text-right">
                                  <span className="text-[10px] text-slate-500 font-medium block">Payout SLA</span>
                                  <span className="font-bold text-slate-800">{refundPolicy.payout_time_days || 14} days</span>
                                </div>
                              </div>
                            </div>

                            {/* Terms & Triggers Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
                                <span className="text-[10px] font-extrabold uppercase text-slate-500">Guaranteed Triggers & Approvals</span>
                                <ul className="space-y-1 text-[11px] text-slate-700">
                                  {refundPolicy.negative_skills_assessment_guarantee && (
                                    <li className="flex items-center gap-1.5 font-medium text-emerald-800">
                                      <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                                      Negative Skills Assessment Guarantee (100% refund)
                                    </li>
                                  )}
                                  {refundPolicy.visa_refusal_guarantee && (
                                    <li className="flex items-center gap-1.5 font-medium text-emerald-800">
                                      <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                                      Official Visa Refusal Guarantee
                                    </li>
                                  )}
                                  {refundPolicy.voluntary_withdrawal_milestones && (
                                    <li className="flex items-center gap-1.5 font-medium text-slate-700">
                                      <CheckCircle2 className="w-3 h-3 text-blue-600 shrink-0" />
                                      Voluntary Withdrawal Pre-Lodgement Milestones
                                    </li>
                                  )}
                                  {(refundPolicy.custom_guaranteed_triggers || []).map((ct, i) => (
                                    <li key={i} className="flex items-center gap-1.5 font-medium text-emerald-800">
                                      <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                                      {ct.trigger_name || 'Guaranteed Trigger'} ({ct.refundable_pct || 100}%)
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
                                <span className="text-[10px] font-extrabold uppercase text-slate-500">Fee Breakdown & Tax Treatment</span>
                                <div className="space-y-1 text-[11px]">
                                  <div className="flex items-center justify-between">
                                    <span className="text-slate-600">Statutory Government Fees:</span>
                                    <span className="font-bold text-slate-800">
                                      {refundPolicy.govt_fees_handling === 'reimbursed' ? 'Reimbursed' : refundPolicy.govt_fees_handling === 'subsidized' ? 'Subsidized' : 'Non-refundable (Standard)'}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between">
                                    <span className="text-slate-600">GST Treatment:</span>
                                    <span className="font-bold text-slate-800">
                                      {refundPolicy.gst_treatment === 'credit_note' ? 'Credit Note issued (Full GST refunded)' : 'GST Retained'}
                                    </span>
                                  </div>
                                  {(refundPolicy.custom_fee_components || []).length > 0 && (
                                    <div className="flex items-center justify-between pt-0.5 border-t border-slate-200">
                                      <span className="text-slate-600">Administrative Deductions:</span>
                                      <span className="font-bold text-rose-700">
                                        {refundPolicy.custom_fee_components.map((c) => `${c.label}: ₹${c.amount}`).join(', ')}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Conditions & Exclusions */}
                            {((refundPolicy.conditions && refundPolicy.conditions.length > 0) || (refundPolicy.exclusions && refundPolicy.exclusions.length > 0)) && (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
                                {refundPolicy.conditions && refundPolicy.conditions.length > 0 && (
                                  <div className="p-2.5 bg-emerald-50/40 rounded-lg border border-emerald-100">
                                    <span className="text-[10px] font-bold text-emerald-800 uppercase block mb-1">Mandatory Client Conditions</span>
                                    <ul className="list-disc list-inside space-y-0.5 text-[10px] text-slate-600">
                                      {refundPolicy.conditions.slice(0, 3).map((c, i) => (
                                        <li key={i}>{c}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {refundPolicy.exclusions && refundPolicy.exclusions.length > 0 && (
                                  <div className="p-2.5 bg-rose-50/40 rounded-lg border border-rose-100">
                                    <span className="text-[10px] font-bold text-rose-800 uppercase block mb-1">Policy Exclusions</span>
                                    <ul className="list-disc list-inside space-y-0.5 text-[10px] text-slate-600">
                                      {refundPolicy.exclusions.slice(0, 3).map((e, i) => (
                                        <li key={i}>{e}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="p-3 bg-amber-50/60 rounded-lg border border-amber-200 text-xs text-amber-900">
                            Refund policy terms for this product are currently set to discretionary review by Admin. Contact operations/compliance before quoting refund commitments to clients.
                          </div>
                        )}
                      </Card>
                    )}
                  </div>
                )}

                {/* TAB 2: STATUTORY ELIGIBILITY & POINTS */}
                {countryDetailTab === 'eligibility' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                        <span className="text-[10px] font-extrabold text-slate-400 uppercase">Points Assessment</span>
                        <div className="text-xs font-bold text-slate-900 mt-0.5">
                          {pointsTested ? `Points-Tested Visa (Pass Mark: ${minPoints} pts)` : 'Direct Statutory Criteria (Non-points)'}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                        <span className="text-[10px] font-extrabold text-slate-400 uppercase">Age Threshold</span>
                        <div className="text-xs font-bold text-slate-900 mt-0.5">
                          {selectedProduct?.eligibility_criteria?.age_limit?.maximum_age
                            ? `Up to ${selectedProduct.eligibility_criteria.age_limit.maximum_age} years`
                            : 'Standard working age threshold'}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                        <span className="text-[10px] font-extrabold text-slate-400 uppercase">Language Competency</span>
                        <div className="text-xs font-bold text-slate-900 mt-0.5">
                          {selectedProduct?.eligibility_criteria?.language_requirements?.minimum_band
                            ? `Minimum Band ${selectedProduct.eligibility_criteria.language_requirements.minimum_band} (IELTS/PTE)`
                            : 'Competent English (IELTS 6.0 / PTE 50 minimum)'}
                        </div>
                      </div>
                    </div>

                    {/* Live Call Quick Eligibility Calculator */}
                    <Card className="p-4 bg-emerald-50/50 border border-emerald-200 rounded-xl space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <UserCheck className="w-4 h-4 text-emerald-700" />
                          <h4 className="text-xs font-black uppercase text-emerald-950">
                            Live Call Points Quick-Checker
                          </h4>
                        </div>
                        <Badge className={`${qualifies ? 'bg-emerald-600 text-white' : 'bg-amber-600 text-white'} text-[10px] font-bold`}>
                          {pointsTested ? `Estimated: ${estPoints} / ${minPoints} pts` : 'General Statutory Check'}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                        <div>
                          <Label className="text-[11px] font-semibold text-slate-600">Client Age ({clientAge} yrs)</Label>
                          <Input
                            type="number"
                            min="18"
                            max="65"
                            value={clientAge}
                            onChange={(e) => setClientAge(parseInt(e.target.value) || 25)}
                            className="h-8 text-xs bg-white mt-1"
                          />
                        </div>
                        <div>
                          <Label className="text-[11px] font-semibold text-slate-600">Experience ({clientExp} yrs)</Label>
                          <Input
                            type="number"
                            min="0"
                            max="25"
                            value={clientExp}
                            onChange={(e) => setClientExp(parseInt(e.target.value) || 0)}
                            className="h-8 text-xs bg-white mt-1"
                          />
                        </div>
                        <div>
                          <Label className="text-[11px] font-semibold text-slate-600">English Competency</Label>
                          <select
                            value={clientIelts}
                            onChange={(e) => setClientIelts(e.target.value)}
                            className="w-full h-8 text-xs bg-white border border-slate-200 rounded-md px-2 mt-1"
                          >
                            <option value="8.0">IELTS 8.0 / PTE 79 (Superior - 20 pts)</option>
                            <option value="7.0">IELTS 7.0 / PTE 65 (Proficient - 10 pts)</option>
                            <option value="6.0">IELTS 6.0 / PTE 50 (Competent - 0 pts)</option>
                          </select>
                        </div>
                        <div>
                          <Label className="text-[11px] font-semibold text-slate-600">Highest Education</Label>
                          <select
                            value={clientDegree}
                            onChange={(e) => setClientDegree(e.target.value)}
                            className="w-full h-8 text-xs bg-white border border-slate-200 rounded-md px-2 mt-1"
                          >
                            <option value="phd">Doctorate / PhD (20 pts)</option>
                            <option value="master">Master's Degree (15 pts)</option>
                            <option value="bachelor">Bachelor's Degree (15 pts)</option>
                            <option value="diploma">Trade Diploma / Certificate (10 pts)</option>
                          </select>
                        </div>
                      </div>

                      <div className="p-2.5 bg-white rounded-lg border border-emerald-200 text-xs flex items-center justify-between">
                        <span className="font-semibold text-slate-800">
                          {qualifies ? '✅ Candidate meets primary statutory threshold! Proceed with booking case assessment.' : '⚠️ Candidate is below benchmark pass mark. Pitch state nomination or language score booster.'}
                        </span>
                        <Button
                          size="sm"
                          onClick={() => handleAskAi(`Client profile: Age ${clientAge}, Experience ${clientExp} years, English band ${clientIelts}, Degree ${clientDegree}. Evaluate eligibility and alternatives for ${selectedProduct.name} (${selectedProduct.visa_subclass}).`)}
                          className="h-6 px-2.5 text-[10px] font-bold bg-emerald-600 hover:bg-emerald-700 text-white gap-1"
                        >
                          <Sparkles className="w-3 h-3" /> Ask AI to Evaluate Gap
                        </Button>
                      </div>
                    </Card>
                  </div>
                )}

                {/* TAB 3: PROCESS MILESTONES & TIMELINE */}
                {countryDetailTab === 'timeline' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                      <div>
                        <span className="font-bold text-slate-900">Total Statutory Turnaround:</span>{' '}
                        <span className="text-emerald-700 font-extrabold">{processTimeline.total_estimated_duration || '6 to 12 months'}</span>
                      </div>
                      <Badge variant="outline" className="text-[10px] font-semibold border-slate-300">
                        Authority: {selectedProduct.authority_name || 'Immigration Authority'}
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      {(processTimeline.milestones || [
                        { step: 1, name: 'Phase 1: Retainer Onboarding & Document Audit', duration: '15-30 days' },
                        { step: 2, name: 'Phase 2: Formal Skills Assessment & Equivalency Filing', duration: '60-90 days' },
                        { step: 3, name: 'Phase 3: State / Federal Expression of Interest (EOI) Lodgement', duration: '30-60 days' },
                        { step: 4, name: 'Phase 4: Statutory Invitation to Apply (ITA) & Visa Lodgement', duration: '60-120 days' },
                      ]).map((m, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 bg-white rounded-xl border border-slate-200 text-xs">
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-black text-[10px] flex items-center justify-center">
                              {idx + 1}
                            </span>
                            <span className="font-bold text-slate-800">{m.name}</span>
                          </div>
                          <span className="font-mono text-slate-600 font-semibold">{m.duration}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* TAB 4: SALES PITCH & 30-SEC SCRIPTS */}
                {countryDetailTab === 'pitch' && (
                  <div className="space-y-4">
                    {/* 30-Second Elevator Pitch */}
                    <Card className="p-4 bg-amber-50/60 border border-amber-200 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black uppercase text-amber-900 flex items-center gap-1.5">
                          <Target className="w-4 h-4 text-amber-600" />
                          30-Second Elevator Pitch (Read to Client)
                        </span>
                        <div className="flex items-center gap-1.5">
                          {isAdmin && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigate('/admin/product-master')}
                              className="h-7 px-2 text-xs font-bold text-blue-700 bg-blue-50 border-blue-200 hover:bg-blue-100 gap-1"
                              title="Edit this sales pitch in Product Master"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                              Edit Pitch (Admin)
                            </Button>
                          )}
                          <Button
                            size="sm"
                            onClick={copyElevatorPitch}
                            className="h-7 px-2.5 text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white gap-1"
                          >
                            <Copy className="w-3.5 h-3.5" />
                            {copiedPitch ? 'Copied!' : 'Copy Script'}
                          </Button>
                        </div>
                      </div>
                      <p className="text-xs md:text-sm text-slate-800 font-medium italic bg-white p-3 rounded-lg border border-amber-200 leading-relaxed">
                        "{elevatorPitch}"
                      </p>
                    </Card>

                    {/* Standard Discovery Questions */}
                    <div className="space-y-2">
                      <span className="text-xs font-black uppercase tracking-wide text-slate-700">
                        Standard Client Discovery Questions:
                      </span>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        {(playbook?.discovery_questions && playbook.discovery_questions.length > 0
                          ? playbook.discovery_questions
                          : [
                              'What is your target country and timeline for overseas relocation?',
                              'Have you appeared for IELTS, PTE, or TOEFL? What is your overall band score?',
                              'How many years of post-qualification continuous work experience do you hold?',
                              'What is your highest degree and was it evaluated for equivalency?',
                            ]
                        ).map((q, idx) => (
                          <div key={idx} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between gap-2">
                            <span className="font-medium text-slate-800">{idx + 1}. {q}</span>
                            <button
                              onClick={() => copyText(q, 'Question')}
                              className="text-slate-400 hover:text-emerald-600 shrink-0 p-1"
                              title="Copy Question"
                            >
                              <Copy className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB 5: CLIENT OBJECTIONS & FAQS */}
                {countryDetailTab === 'objections' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-black uppercase tracking-wide text-slate-700">
                        Pre-Approved Client Objection Rebuttals
                      </h4>
                      <Input
                        placeholder="Search objections (fee, timeline, points)..."
                        value={objectionSearch}
                        onChange={(e) => setObjectionSearch(e.target.value)}
                        className="text-xs h-7 w-60"
                      />
                    </div>

                    <div className="space-y-2">
                      {(filteredObjs.length > 0
                        ? filteredObjs
                        : [
                            {
                              objection: 'Your professional fees are higher than other local immigration consultancies.',
                              rebuttal: 'LEAMSS provides end-to-end case filing with dedicated licensed immigration lawyers, 3-tranche milestone billing, and a 100% tax-compliant invoice with zero risk of misrepresentation bans.',
                            },
                            {
                              objection: 'The processing time is too long. Can I get a faster pathway?',
                              rebuttal: 'Statutory processing times are set directly by the immigration department, but our legal filing team ensures all documentation is audit-ready on Day 1 to avoid delay requests (RFEs).',
                            },
                          ]
                      ).map((obj, idx) => (
                        <div key={idx} className="p-3 bg-purple-50/40 rounded-xl border border-purple-200 space-y-1.5 text-xs">
                          <div className="font-extrabold text-purple-950 flex items-start justify-between gap-2">
                            <span>❌ Client: "{obj.objection}"</span>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => copyText(obj.rebuttal, 'Rebuttal')}
                              className="h-6 px-2 text-[10px] text-purple-700 hover:bg-purple-100 font-bold shrink-0"
                            >
                              <Copy className="w-3 h-3 mr-1" />
                              Copy Script
                            </Button>
                          </div>
                          <p className="text-slate-800 leading-relaxed bg-white p-2.5 rounded-lg border border-purple-200/60 font-medium">
                            💬 <strong className="text-purple-900">Say this:</strong> "{obj.rebuttal}"
                          </p>
                        </div>
                      ))}
                    </div>

                    {/* FREQUENTLY ASKED CLIENT QUESTIONS (FAQS) */}
                    <div className="space-y-3 pt-5 border-t border-slate-200">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <HelpCircle className="w-4 h-4 text-indigo-600" />
                          <div>
                            <h4 className="text-xs font-black uppercase tracking-wide text-slate-800 flex items-center gap-2">
                              Frequently Asked Client Questions (FAQs)
                              <Badge className="bg-indigo-50 text-indigo-700 border-indigo-200 text-[10px] font-bold">
                                {filteredFaqs.length} Available
                              </Badge>
                            </h4>
                            <p className="text-[11px] text-slate-500">
                              Official answers configured for {selectedProduct?.name || 'this subclass'}.
                            </p>
                          </div>
                        </div>
                        {isAdmin && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate('/admin/product-master')}
                            className="h-7 px-2 text-xs font-bold text-blue-700 bg-blue-50 border-blue-200 hover:bg-blue-100 gap-1"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            Edit FAQs in Admin
                          </Button>
                        )}
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {(filteredFaqs.length > 0
                          ? filteredFaqs
                          : [
                              {
                                question: `Can I bring my spouse and dependent children under ${selectedProduct?.name || 'this visa'}?`,
                                answer: 'Yes. All eligible dependent family members (spouse and children) receive identical residency and work authorizations.',
                              },
                              {
                                question: 'How long is the initial visa valid and how does citizenship work?',
                                answer: 'The initial visa provides direct legal residency with a guaranteed statutory milestone path towards citizenship.',
                              },
                            ]
                        ).map((f, idx) => (
                          <div
                            key={idx}
                            className="p-3.5 bg-indigo-50/50 hover:bg-indigo-50/80 rounded-xl border border-indigo-200 space-y-2 text-xs transition shadow-2xs flex flex-col justify-between"
                          >
                            <div className="space-y-1.5">
                              <div className="flex items-start justify-between gap-2">
                                <span className="font-extrabold text-indigo-950 flex items-start gap-1 leading-snug">
                                  <span className="text-indigo-600 font-black">Q{idx + 1}:</span> {f.question}
                                </span>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => copyText(f.answer, 'FAQ Answer')}
                                  className="h-6 px-2 text-[10px] text-indigo-700 hover:bg-indigo-100 font-bold shrink-0 gap-1"
                                  title="Copy official answer"
                                >
                                  <Copy className="w-3 h-3" />
                                  Copy Answer
                                </Button>
                              </div>
                              <p className="text-slate-800 leading-relaxed bg-white p-2.5 rounded-lg border border-indigo-100 font-medium">
                                <strong className="text-indigo-900 block mb-0.5 text-[10px] uppercase font-bold tracking-wider">
                                  Official Answer:
                                </strong>
                                {f.answer}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300">
                <Briefcase className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-xs font-bold text-slate-600">Select a subclass above to view complete sales handbook</p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ═════════════════════════════════════════════════════════════ */}
      {/* VIEW B: VISA SUBCLASS DIRECTORY & DEEP-DIVE HANDBOOK           */}
      {/* ═════════════════════════════════════════════════════════════ */}
      {activeMainTab === 'subclass_directory' && (
        <div className="space-y-4">
          {/* Top Search Bar */}
          <Card className="p-3 bg-white border border-slate-200 shadow-sm rounded-xl">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3.5 top-3 text-slate-400" />
              <Input
                placeholder="Search any visa subclass (e.g. 189, H-1B, L-1, EB-1, F-1, FSW, Chancenkarte), country code (US, AU, CA, DE, UK, NZ), or keyword..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 pr-9 text-xs h-10 bg-slate-50 focus:bg-white border-slate-200 focus:border-emerald-500 rounded-xl font-medium"
                data-testid="sales-pitch-search-input"
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </Card>

          {/* 3-Column Workstation */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* COLUMN 1: SELECT COUNTRY (Tier 1) */}
            <div className="lg:col-span-3 xl:col-span-2 space-y-2">
              <div className="flex items-center justify-between px-1 mb-1">
                <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
                  1. Destination ({countriesSummary.length})
                </span>
                {selectedCountry !== 'all' && (
                  <button
                    onClick={() => handleSelectCountry('all')}
                    className="text-[10px] text-emerald-600 hover:underline font-bold"
                  >
                    Reset
                  </button>
                )}
              </div>

              {/* Country Filter Box */}
              <div className="relative mb-2">
                <Search className="h-3 w-3 absolute left-2.5 top-2.5 text-slate-400" />
                <Input
                  placeholder="Filter countries..."
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  className="pl-7 pr-7 text-[11px] h-8 bg-white border-slate-200 rounded-lg"
                />
                {countrySearch && (
                  <button
                    onClick={() => setCountrySearch('')}
                    className="absolute right-2 top-2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>

              <div className="space-y-1">
                <button
                  onClick={() => handleSelectCountry('all')}
                  className={`w-full p-2.5 rounded-xl border text-left text-xs font-bold transition flex items-center justify-between ${
                    selectedCountry === 'all'
                      ? 'bg-slate-900 text-white border-slate-900 shadow-sm'
                      : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Globe className="w-3.5 h-3.5 text-emerald-400" />
                    <span>All Destinations</span>
                  </span>
                  <Badge variant={selectedCountry === 'all' ? 'secondary' : 'outline'} className="text-[10px]">
                    {items.length}
                  </Badge>
                </button>

                {countriesSummary.map((c) => {
                  const isCur = selectedCountry?.toLowerCase() === c.name.toLowerCase();
                  const iso = getISO(c.name);
                  return (
                    <button
                      key={c.name}
                      onClick={() => handleSelectCountry(c.name)}
                      className={`w-full p-2.5 rounded-xl border text-left transition flex items-center justify-between ${
                        isCur
                          ? 'bg-emerald-50 border-emerald-500 text-emerald-950 font-black shadow-xs ring-1 ring-emerald-400'
                          : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-800 font-bold'
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <div className="w-5 h-3.5 rounded overflow-hidden shadow-2xs border border-slate-200 shrink-0">
                          <Flag code={iso} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        </div>
                        <div className="truncate">
                          <div className="text-xs truncate">{c.name}</div>
                          <div className="text-[10px] text-slate-400 font-mono">CODE: {c.code}</div>
                        </div>
                      </div>
                      <Badge
                        variant={isCur ? 'default' : 'secondary'}
                        className={`text-[10px] px-1.5 py-0 font-bold ${
                          isCur ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {c.count}
                      </Badge>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* COLUMN 2: COUNTRY CODE & SUBCLASS (Tier 2) */}
            <div className="lg:col-span-4 xl:col-span-4 space-y-3">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-1.5 truncate">
                  <Flag code={getISO(selectedCountry)} style={{ width: '16px', height: '11px', objectFit: 'cover' }} />
                  <span className="text-[11px] font-black uppercase tracking-wider text-slate-700 truncate">
                    {selectedCountry} ({activeCountryCode}) • {displayedSubclasses.length} Visas
                  </span>
                </div>
              </div>

              {/* Subclass Cards List */}
              <div className="space-y-2 max-h-[calc(100vh-250px)] overflow-y-auto pr-1">
                {displayedSubclasses.length > 0 ? (
                  displayedSubclasses.map((item) => {
                    const isSelected = selectedProduct?.id === item.id;
                    const cCode = item.country_code || getCountryCode(item.country);
                    const catMeta = CATEGORY_META[item.category] || CATEGORY_META.skilled_migration;
                    const fee = parseFloat(item.service_price || item.base_fee || 0);
                    const priCost = item.government_costs?.primary_applicant;

                    return (
                      <Card
                        key={item.id}
                        onClick={() => handleSelectSubclass(item)}
                        className={`p-3.5 cursor-pointer rounded-2xl transition-all border-2 text-left relative overflow-hidden group ${
                          isSelected
                            ? 'border-emerald-600 bg-emerald-50/40 shadow-sm ring-1 ring-emerald-400'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-2xs'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-1 mb-1.5">
                          <span className="inline-flex items-center gap-1 font-mono text-[11px] font-black px-2 py-0.5 rounded-md bg-emerald-800 text-emerald-50 shadow-2xs">
                            <Flag code={getISO(item.country)} style={{ width: '12px', height: '9px', objectFit: 'cover' }} />
                            <span>{cCode} • Subclass {item.visa_subclass || item.name}</span>
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${catMeta.badge}`}>
                            {catMeta.icon} {catMeta.name.split('/')[0].trim()}
                          </span>
                        </div>

                        <div className="font-extrabold text-xs text-slate-900 group-hover:text-emerald-700 leading-tight">
                          {item.name}
                        </div>

                        <div className="flex items-center justify-between pt-2 mt-2 border-t border-slate-100 text-[11px]">
                          <span className="text-slate-500 font-medium">
                            Gov: {item.government_costs?.currency || '$'} {priCost ? Number(priCost).toLocaleString() : 'N/A'}
                          </span>
                          <span className="font-extrabold text-emerald-700">
                            LEAMSS: {formatINR(fee)}
                          </span>
                        </div>
                      </Card>
                    );
                  })
                ) : (
                  <Card className="p-8 text-center bg-white border-dashed rounded-2xl">
                    <p className="text-xs text-slate-500 font-semibold">No subclasses found matching filter.</p>
                  </Card>
                )}
              </div>
            </div>

            {/* COLUMN 3: SUBCLASS SALES HANDBOOK & PITCH (Tier 3) */}
            <div className="lg:col-span-5 xl:col-span-6 space-y-4">
              {selectedProduct ? (
                <div className="space-y-4">
                  {/* Elevator Pitch Card */}
                  <Card className="p-4 bg-amber-50/60 border border-amber-200 rounded-2xl shadow-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black uppercase text-amber-900 flex items-center gap-1.5">
                        <Target className="w-4 h-4 text-amber-600" />
                        Client Call Elevator Pitch • Subclass {selectedProduct.visa_subclass || selectedProduct.name}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {isAdmin && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate('/admin/product-master')}
                            className="h-7 px-2 text-xs font-bold text-blue-700 bg-blue-50 border-blue-200 hover:bg-blue-100 gap-1"
                            title="Edit this sales pitch in Product Master"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            Edit Pitch (Admin)
                          </Button>
                        )}
                        <Button
                          size="sm"
                          onClick={copyElevatorPitch}
                          className="h-7 px-2.5 text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white gap-1"
                        >
                          <Copy className="w-3.5 h-3.5" />
                          {copiedPitch ? 'Copied!' : 'Copy Elevator Pitch'}
                        </Button>
                      </div>
                    </div>
                    <p className="text-xs md:text-sm text-slate-800 font-medium italic bg-white p-3 rounded-lg border border-amber-200 leading-relaxed">
                      "{elevatorPitch}"
                    </p>
                  </Card>

                  {/* AI Copilot & Query Card */}
                  <Card className="p-4 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 rounded-lg bg-indigo-600 text-white">
                          <Bot className="w-4 h-4" />
                        </div>
                        <div>
                          <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                            AI Visa Pitch Copilot & Query Assistant
                          </h3>
                        </div>
                      </div>
                      <Badge className="bg-indigo-50 text-indigo-700 border-indigo-200 text-[10px] font-bold">
                        Ground Truth Sync
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <Input
                        placeholder={`Ask anything about Subclass ${selectedProduct.visa_subclass || selectedProduct.name}...`}
                        value={aiQuestion}
                        onChange={(e) => setAiQuestion(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAskAi()}
                        className="text-xs h-9 bg-slate-50 focus:bg-white"
                      />
                      <Button
                        onClick={() => handleAskAi()}
                        disabled={aiLoading || !aiQuestion.trim()}
                        className="h-9 px-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs gap-1.5 rounded-xl shrink-0"
                      >
                        {aiLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                        {aiLoading ? 'Thinking...' : 'Ask AI'}
                      </Button>
                    </div>

                    {aiAnswer && (
                      <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-200 space-y-2 text-xs">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <span className="font-bold text-indigo-900 flex items-center gap-1">
                            <Sparkles className="w-3 h-3 text-indigo-600" /> AI Consultation Advice:
                          </span>
                          <div className="flex items-center gap-1">
                            {['English', 'Marathi', 'Hindi'].map((langKey) => (
                              <button
                                key={langKey}
                                onClick={() => handleSelectLanguage(langKey)}
                                disabled={translatingLang !== null}
                                className={`px-2 py-0.5 rounded text-[10px] font-bold transition cursor-pointer ${
                                  activeLanguage === langKey
                                    ? 'bg-indigo-700 text-white shadow-2xs'
                                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                                }`}
                              >
                                {langKey === 'English' && '🇬🇧 EN'}
                                {langKey === 'Marathi' && '🇮🇳 MR'}
                                {langKey === 'Hindi' && '🇮🇳 HI'}
                              </button>
                            ))}
                            <button
                              onClick={() => copyText(aiAnswer, 'AI Advice')}
                              className="text-[10px] font-bold text-indigo-700 hover:underline flex items-center gap-0.5 ml-1"
                            >
                              <Copy className="w-3 h-3" /> Copy
                            </button>
                            <button
                              onClick={handlePrintDocument}
                              className="text-[10px] font-bold text-indigo-700 hover:underline flex items-center gap-0.5 ml-1"
                            >
                              <Printer className="w-3 h-3" /> Print
                            </button>
                          </div>
                        </div>
                        <p className="text-slate-800 leading-relaxed whitespace-pre-line font-medium bg-white p-2.5 rounded-lg border border-indigo-100">
                          {aiAnswer}
                        </p>
                      </div>
                    )}
                  </Card>

                  {/* Pricing Breakdown & Product Master Sync */}
                  <Card className="p-4 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <span className="text-xs font-black uppercase text-slate-800">LEAMSS Fee & Product Master Commercials</span>
                      <span className="text-xs font-extrabold text-emerald-700 font-mono">
                        {retainerGstApplicable ? `Total with 18% GST: ${formatINR(totalWithGst)}` : `Total (Net): ${formatINR(baseFee)}`}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 bg-slate-50 rounded-lg">
                        <span className="text-[10px] text-slate-500 font-semibold block">LEAMSS Professional Retainer</span>
                        <span className="font-black text-slate-900">
                          {formatINR(baseFee)} {retainerGstApplicable ? `(+ 18% GST: ${formatINR(gstAmount)})` : '(GST Not Applicable)'}
                        </span>
                      </div>
                      <div className="p-2.5 bg-slate-50 rounded-lg">
                        <span className="text-[10px] text-slate-500 font-semibold block">Statutory Lodgement Fee</span>
                        <span className="font-black text-blue-900">
                          {govCosts.currency || 'USD'} {Number(govCosts.primary_applicant || 0).toLocaleString()}
                        </span>
                      </div>
                    </div>

                    {/* Packages Preview in View B */}
                    {packages.length > 0 && (
                      <div className="pt-1 border-t border-slate-100 space-y-1">
                        <div className="flex items-center justify-between text-[10px] font-extrabold text-slate-500 uppercase">
                          <span>Available Package Tiers ({packages.length}):</span>
                        </div>
                        <div className="grid grid-cols-3 gap-1.5">
                          {packages.slice(0, 3).map((pkg, i) => {
                            const effectivePkg = {
                              ...pkg,
                              price: pkg.price,
                              refund_policy: pkg.refund_policy || (selectedProduct?.refund_policy ? { ...selectedProduct.refund_policy, enabled: true } : null),
                            };
                            return (
                              <div key={i} className="p-1.5 bg-slate-50 rounded border border-slate-200 text-[11px] text-center space-y-1">
                                <span className="font-bold text-slate-800 block truncate">{pkg.name}</span>
                                <span className="font-extrabold text-emerald-700 block">{formatINR(pkg.price)}</span>
                                <PackageRefundBadge pkg={effectivePkg} compact={true} />
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Refund Policy Status Badge in View B */}
                    {refundPolicy && (
                      <div className="pt-1 border-t border-slate-100 flex items-center justify-between text-xs">
                        <span className="text-[10px] font-bold text-slate-500 uppercase flex items-center gap-1">
                          <ShieldCheck className="w-3 h-3 text-emerald-600" />
                          Refund Safeguard:
                        </span>
                        <Badge
                          className={`text-[9px] font-bold ${
                            isRefundEnabled
                              ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                              : 'bg-amber-100 text-amber-800 border-amber-300'
                          }`}
                        >
                          {isRefundEnabled
                            ? `${refundPolicy.policy_type === 'protection' ? 'Protection Guarantee' : 'Milestone Policy'} (${refundPolicy.refundable_service_fee_pct ?? 100}%)`
                            : 'Admin Restricted'}
                        </Badge>
                      </div>
                    )}
                  </Card>

                  {/* Frequently Asked Client Questions (FAQs) in View B */}
                  <Card className="p-4 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <div className="flex items-center gap-2">
                        <HelpCircle className="w-4 h-4 text-indigo-600" />
                        <span className="text-xs font-black uppercase text-slate-800">
                          Frequently Asked Client Questions (FAQs)
                        </span>
                      </div>
                      <Badge className="bg-indigo-50 text-indigo-700 border-indigo-200 text-[10px] font-bold">
                        {faqs.length > 0 ? `${faqs.length} FAQs` : 'Verified FAQs'}
                      </Badge>
                    </div>

                    <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                      {(faqs.length > 0
                        ? faqs
                        : [
                            {
                              question: `Can I bring my family / spouse under ${selectedProduct?.name || 'this visa'}?`,
                              answer: 'Yes. All eligible dependent family members (spouse and children) receive identical residency and work privileges.',
                            },
                            {
                              question: 'How long is the initial visa valid and how does citizenship work?',
                              answer: 'The initial visa provides direct legal residency with a guaranteed statutory milestone path towards citizenship.',
                            },
                          ]
                      ).map((f, idx) => (
                        <div key={idx} className="p-3 bg-indigo-50/40 rounded-xl border border-indigo-100 space-y-1.5 text-xs">
                          <div className="flex items-start justify-between gap-2">
                            <span className="font-extrabold text-indigo-950">Q{idx + 1}: {f.question}</span>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => copyText(f.answer, 'FAQ Answer')}
                              className="h-5 px-1.5 text-[9px] text-indigo-700 hover:bg-indigo-100 font-bold shrink-0"
                            >
                              <Copy className="w-2.5 h-2.5 mr-0.5" />
                              Copy
                            </Button>
                          </div>
                          <p className="text-slate-700 text-[11px] leading-relaxed bg-white p-2 rounded border border-indigo-50">
                            {f.answer}
                          </p>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              ) : (
                <Card className="p-10 text-center bg-white border-dashed rounded-2xl">
                  <Briefcase className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                  <h3 className="text-xs font-bold text-slate-700">Select a Visa Subclass to View Handbook</h3>
                </Card>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
