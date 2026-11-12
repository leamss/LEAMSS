import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  Globe2, ExternalLink, TrendingUp, DollarSign, MapPin, Sparkles, CheckCircle2,
  AlertCircle, ShieldCheck, Flag, Compass, BarChart3, Search, Landmark, Award,
  ChevronDown, ChevronRight, FileCheck, BookOpen, Layers, Trash2, Plus, Wand2, Loader2, Save,
  HelpCircle, Briefcase, Users, FileText, Star, Pin, X,
  Share2, Eye, Check, Copy, Code, Tag, Hash, RefreshCw
} from 'lucide-react';

const AU_STATES = [
  { code: 'NSW', name: 'New South Wales' },
  { code: 'VIC', name: 'Victoria' },
  { code: 'WA', name: 'Western Australia' },
  { code: 'QLD', name: 'Queensland' },
  { code: 'SA', name: 'South Australia' },
  { code: 'TAS', name: 'Tasmania' },
  { code: 'ACT', name: 'Canberra (ACT)' },
  { code: 'NT', name: 'Northern Territory' },
];

const CA_PROVINCES = [
  { code: 'ON', name: 'Ontario (OINP)' },
  { code: 'BC', name: 'British Columbia (BC PNP)' },
  { code: 'AB', name: 'Alberta (AAIP)' },
  { code: 'SK', name: 'Saskatchewan (SINP)' },
  { code: 'MB', name: 'Manitoba (MPNP)' },
  { code: 'NS', name: 'Nova Scotia (NSNP)' },
  { code: 'NB', name: 'New Brunswick (NBPNP)' },
  { code: 'PE', name: 'Prince Edward Island (PEI PNP)' },
  { code: 'NL', name: 'Newfoundland & Labrador' },
];

const NZ_REGIONS = [
  { code: 'AKL', name: 'Auckland Region' },
  { code: 'WGN', name: 'Wellington Region' },
  { code: 'CAN', name: 'Canterbury Region' },
  { code: 'WKO', name: 'Waikato Region' },
  { code: 'BOP', name: 'Bay of Plenty' },
  { code: 'OTA', name: 'Otago Region' },
  { code: 'MWT', name: 'Manawatu-Whanganui' },
  { code: 'HKB', name: 'Hawke\'s Bay' },
];

const CA_AUTHORITIES = [
  { code: 'WES', full_name: 'World Education Services (WES Canada)', website: 'https://www.wes.org/ca/' },
  { code: 'ICAS', full_name: 'International Credential Assessment Service of Canada', website: 'https://www.icascanada.ca/' },
  { code: 'CES', full_name: 'Comparative Education Service – University of Toronto', website: 'https://learn.utoronto.ca/comparative-education-service' },
  { code: 'IQAS', full_name: 'International Qualifications Assessment Service (Alberta)', website: 'https://www.alberta.ca/iqas-overview' },
  { code: 'ICES', full_name: 'International Credential Evaluation Service (BCIT)', website: 'https://www.bcit.ca/ices/' },
  { code: 'MCC', full_name: 'Medical Council of Canada (Physicians / Doctors)', website: 'https://mcc.ca/' },
  { code: 'PEBC', full_name: 'Pharmacy Examining Board of Canada (Pharmacists)', website: 'https://www.pebc.ca/' },
  { code: 'Red Seal', full_name: 'Provincial Apprenticeship & Trade Certification / Red Seal', website: 'https://www.red-seal.ca/' },
];

const NZ_AUTHORITIES = [
  { code: 'NZQA', full_name: 'New Zealand Qualifications Authority (IQA)', website: 'https://www.nzqa.govt.nz/' },
  { code: 'Engineering NZ', full_name: 'Engineering New Zealand Te Ao Rangahau', website: 'https://www.engineeringnz.org/' },
  { code: 'MCNZ', full_name: 'Medical Council of New Zealand (Registered Doctors)', website: 'https://www.mcnz.org.nz/' },
  { code: 'NCNZ', full_name: 'Nursing Council of New Zealand (Registered Nurses)', website: 'https://www.nursingcouncil.org.nz/' },
  { code: 'Teaching Council', full_name: 'Teaching Council of Aotearoa New Zealand', website: 'https://teachingcouncil.nz/' },
  { code: 'CA ANZ', full_name: 'Chartered Accountants Australia and New Zealand', website: 'https://www.charteredaccountantsanz.com/' },
  { code: 'EWRB', full_name: 'Electrical Workers Registration Board', website: 'https://www.ewrb.govt.nz/' },
];

const COUNTRY_VISA_CONFIG = {
  AU: {
    label: 'Australian Skilled Visas',
    countryName: 'Australia',
    currency: 'AUD',
    currencySymbol: 'A$',
    feeEstimate: 'AUD $4,770',
    authorityLabel: 'Designated Assessing Authority (MSA)',
    subclasses: [
      { code: '189', name: 'Skilled Independent (PR)' },
      { code: '190', name: 'State Nominated (PR)' },
      { code: '491', name: 'Regional Provisional' },
      { code: '485', name: 'Graduate Work' },
      { code: '482', name: 'Skills in Demand (TSS)' },
      { code: '186', name: 'Employer Nomination (ENS)' },
      { code: '494', name: 'Regional Sponsored (SESR)' },
    ],
    lists: ['MLTSSL', 'CSOL', 'STSOL', 'ROL'],
  },
  CA: {
    label: 'Canadian Economic Immigration Streams',
    countryName: 'Canada',
    currency: 'CAD',
    currencySymbol: 'C$',
    feeEstimate: 'CAD $1,525',
    authorityLabel: 'Designated ECA Body (WES / ICAS / MCC)',
    subclasses: [
      { code: 'FSWP', name: 'Federal Skilled Worker (Express Entry)' },
      { code: 'CEC', name: 'Canadian Experience Class (Express Entry)' },
      { code: 'PNP', name: 'Provincial Nominee Program (PR)' },
      { code: 'FSTP', name: 'Federal Skilled Trades' },
      { code: 'LMIA', name: 'TFWP Employer-Sponsored Work Permit' },
      { code: 'ICT', name: 'Intra-Company Transferee Work Permit' },
      { code: 'PGWP', name: 'Post-Graduation Work Permit' },
      { code: 'GSS', name: 'Global Skills Strategy (Fast-Track)' },
    ],
    lists: ['Express Entry', 'Category-Based STEM', 'Category-Based Healthcare', 'Category-Based Trades', 'Category-Based Transport', 'Category-Based French'],
  },
  NZ: {
    label: 'New Zealand Resident & Work Visas',
    countryName: 'New Zealand',
    currency: 'NZD',
    currencySymbol: 'NZ$',
    feeEstimate: 'NZD $4,290',
    authorityLabel: 'NZQA / Statutory Registration Body',
    subclasses: [
      { code: 'SMC', name: 'Skilled Migrant Category Resident Visa' },
      { code: 'Green-T1', name: 'Green List Straight to Residence' },
      { code: 'Green-T2', name: 'Green List Work to Residence' },
      { code: 'AEWV', name: 'Accredited Employer Work Visa' },
      { code: 'Care-WTR', name: 'Care Sector Work to Residence' },
      { code: 'PSWV', name: 'Post Study Work Visa' },
    ],
    lists: ['Green List Tier 1', 'Green List Tier 2', 'Care Workforce', 'Sector Agreement', 'Non-Green List'],
  },
};

const SKILLED_VISA_SUBCLASSES = COUNTRY_VISA_CONFIG.AU.subclasses;
const MIGRATION_LISTS = COUNTRY_VISA_CONFIG.AU.lists;

export default function PublicAtlasUnifiedEditor({
  item,
  edit,
  setEdit,
  authorities,
  handleAuthorityChange,
  selectedAuthCode,
  sourceRef,
  setSourceRef,
  reviewNotes,
  setReviewNotes,
  polish,
  polishLoading,
  generate,
  genLoading,
  aiDraft,
  applyAllAiDraft,
  save,
  verify,
  saving,
  addDocument,
  updateDocument,
  removeDocument,
  addSampleCase,
  updateSampleCase,
  removeSampleCase,
  addCustomSection,
  updateCustomSection,
  removeCustomSection,
  syncMigroto,
  migrotoLoading,
}) {
  const [showInternal, setShowInternal] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [seoTab, setSeoTab] = useState('serp');
  const [copiedKey, setCopiedKey] = useState(null);
  const country = (item.country_code || 'AU').toUpperCase();
  const countryCfg = COUNTRY_VISA_CONFIG[country] || COUNTRY_VISA_CONFIG.AU;
  const publicUrl = `/atlas/${country.toLowerCase()}/${item.code}`;

  const handleAddSampleCase = () => {
    if (typeof addSampleCase === 'function') {
      addSampleCase();
    } else {
      setEdit((prev) => ({
        ...prev,
        sample_cases: [
          ...(prev.sample_cases || []),
          { id: `case_${Date.now()}`, client_age: 32, visa_subclass: '190', outcome: 'Approved', timeline_months: 6, profile_summary: '', notes: '' },
        ],
      }));
    }
  };

  const handleUpdateSampleCase = (idx, patch) => {
    if (typeof updateSampleCase === 'function') {
      updateSampleCase(idx, patch);
    } else {
      setEdit((prev) => {
        const cases = [...(prev.sample_cases || [])];
        cases[idx] = { ...cases[idx], ...patch };
        return { ...prev, sample_cases: cases };
      });
    }
  };

  const handleRemoveSampleCase = (idx) => {
    if (typeof removeSampleCase === 'function') {
      removeSampleCase(idx);
    } else {
      setEdit((prev) => {
        const cases = [...(prev.sample_cases || [])];
        cases.splice(idx, 1);
        return { ...prev, sample_cases: cases };
      });
    }
  };

  const handleAddPinCode = (codeToAdd) => {
    const raw = (codeToAdd || pinInput || '').trim();
    if (!raw) return;
    const current = Array.isArray(edit.similar_codes_override)
      ? [...edit.similar_codes_override]
      : (typeof edit.similar_codes_override === 'string' ? edit.similar_codes_override.split(',').map(s => s.trim()).filter(Boolean) : []);

    const formatted = raw.toUpperCase().startsWith(`${country}-`) || raw.includes('-')
      ? raw.toUpperCase()
      : `${country}-${raw}`;

    if (!current.some(c => c.toLowerCase() === formatted.toLowerCase() || c.toLowerCase() === raw.toLowerCase())) {
      setEdit((prev) => ({
        ...prev,
        similar_codes_override: [...current, formatted],
      }));
    }
    setPinInput('');
  };

  const handleRemovePinCode = (codeToRemove) => {
    const current = Array.isArray(edit.similar_codes_override)
      ? [...edit.similar_codes_override]
      : (typeof edit.similar_codes_override === 'string' ? edit.similar_codes_override.split(',').map(s => s.trim()).filter(Boolean) : []);
    const filtered = current.filter(c => c !== codeToRemove && c.toLowerCase() !== codeToRemove.toLowerCase());
    setEdit((prev) => ({
      ...prev,
      similar_codes_override: filtered,
    }));
  };

  const handleSuggestPeers = () => {
    const occCode = String(edit.code || item.code || '').trim();
    const current = Array.isArray(edit.similar_codes_override)
      ? [...edit.similar_codes_override]
      : (typeof edit.similar_codes_override === 'string' ? edit.similar_codes_override.split(',').map(s => s.trim()).filter(Boolean) : []);

    let peerCodes = [];
    if (country === 'AU' && occCode.length >= 4) {
      const prefix = occCode.slice(0, 4);
      if (prefix === '2241') {
        peerCodes = ['224112', '224113', '224114', '224115'];
      } else {
        peerCodes = [`${prefix}12`, `${prefix}13`, `${prefix}14`];
      }
    } else if (country === 'CA' && occCode.length >= 4) {
      const prefix = occCode.slice(0, 4);
      peerCodes = [`${prefix}0`, `${prefix}1`, `${prefix}2`].filter((p) => p !== occCode);
    } else if (country === 'NZ' && occCode.length >= 4) {
      const prefix = occCode.slice(0, 4);
      peerCodes = [`${prefix}12`, `${prefix}13`, `${prefix}14`];
    } else if (occCode.length >= 3) {
      const prefix = occCode.slice(0, 3);
      peerCodes = [`${prefix}1`, `${prefix}2`];
    }

    const toAdd = peerCodes
      .filter(p => p !== occCode)
      .map(p => `${country}-${p}`)
      .filter(p => !current.some(c => c.toLowerCase() === p.toLowerCase() || c.toLowerCase() === p.replace(`${country}-`, '').toLowerCase()));

    if (toAdd.length > 0) {
      setEdit((prev) => ({
        ...prev,
        similar_codes_override: [...current, ...toAdd],
      }));
    }
  };

  // Helper updaters
  const upMinPoints = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      min_invitation_points: {
        ...(prev.min_invitation_points || {}),
        [k]: v,
      },
    }));
  };

  const handleAddRound = () => {
    setEdit((prev) => ({
      ...prev,
      invitation_rounds: [
        ...(prev.invitation_rounds || []),
        { date: new Date().toISOString().slice(0, 10), subclass: '190', score: 75, invitations: 100 }
      ]
    }));
  };

  const handleLoadDefaultRounds = () => {
    setEdit((prev) => ({
      ...prev,
      invitation_rounds: [
        { date: '2026-06-15', subclass: '189', score: prev.min_invitation_points?.subclass_189 ? Number(prev.min_invitation_points.subclass_189) : 80, invitations: 120 },
        { date: '2026-05-10', subclass: '190', score: prev.min_invitation_points?.subclass_190 ? Number(prev.min_invitation_points.subclass_190) : 75, invitations: 95 },
        { date: '2026-04-20', subclass: '491', score: prev.min_invitation_points?.subclass_491 ? Number(prev.min_invitation_points.subclass_491) : 65, invitations: 65 },
      ]
    }));
  };

  const handleUpdateRound = (index, field, value) => {
    setEdit((prev) => {
      const list = [...(prev.invitation_rounds || [])];
      list[index] = {
        ...list[index],
        [field]: field === 'score' || field === 'invitations' ? (value === '' ? '' : Number(value)) : value
      };
      return { ...prev, invitation_rounds: list };
    });
  };

  const handleRemoveRound = (index) => {
    setEdit((prev) => {
      const list = [...(prev.invitation_rounds || [])];
      list.splice(index, 1);
      return { ...prev, invitation_rounds: list };
    });
  };

  const upState = (stCode, field, val) => {
    setEdit((prev) => {
      const ste = { ...(prev.state_territory_eligibility || {}) };
      ste[stCode] = { ...(ste[stCode] || {}), [field]: val };
      return { ...prev, state_territory_eligibility: ste };
    });
  };

  const upAnzscoProfile = (k, v) => {
    setEdit((prev) => {
      const numVal = parseFloat(v);
      const isNum = !isNaN(numVal) && v !== '';
      const weeklyVal = k === 'median_salary_aud' && isNum ? Math.round(numVal / 52) : undefined;
      return {
        ...prev,
        anzsco_profile: {
          ...(prev.anzsco_profile || {}),
          [k]: v,
          ...(weeklyVal !== undefined ? { median_weekly_earnings_aud: weeklyVal } : {}),
        },
        abs_data: {
          ...(prev.abs_data || {}),
          [k === 'median_salary_aud' ? 'median_ft_annual_aud' : k]: v,
          ...(weeklyVal !== undefined ? { median_ft_weekly_earnings_aud: weeklyVal } : {}),
        },
        abs_labour_market: {
          ...(prev.abs_labour_market || {}),
          ...(k === 'median_salary_aud' ? { median_annual_earnings_aud: v } : {}),
          ...(weeklyVal !== undefined ? { median_weekly_earnings_aud: weeklyVal } : {}),
        },
      };
    });
  };

  const upJsaData = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      jsa_data: {
        ...(prev.jsa_data || {}),
        [k]: v,
      },
      abs_labour_market: {
        ...(prev.abs_labour_market || {}),
        ...(k === 'growth_pct_2025_to_2035' ? { growth_pct_2025_to_2035: v } : {}),
        ...(k === 'future_growth' ? { future_growth_rating: v } : {}),
      },
    }));
  };

  const upLabourMarket = (k, v) => {
    setEdit((prev) => {
      const numVal = parseFloat(v);
      const isNum = !isNaN(numVal) && v !== '';
      const annualVal = k === 'median_weekly_earnings_aud' && isNum ? Math.round(numVal * 52) : undefined;
      return {
        ...prev,
        abs_labour_market: {
          ...(prev.abs_labour_market || {}),
          [k]: v,
          ...(annualVal !== undefined ? { median_annual_earnings_aud: annualVal } : {}),
        },
        abs_data: {
          ...(prev.abs_data || {}),
          ...(k === 'median_weekly_earnings_aud' ? { median_ft_weekly_earnings_aud: v } : {}),
          ...(annualVal !== undefined ? { median_ft_annual_aud: annualVal } : {}),
        },
        anzsco_profile: {
          ...(prev.anzsco_profile || {}),
          ...(k === 'median_weekly_earnings_aud' ? { median_weekly_earnings_aud: v } : {}),
          ...(annualVal !== undefined ? { median_salary_aud: annualVal } : {}),
        },
      };
    });
  };

  const upSad = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      skill_assessment_details: {
        ...(prev.skill_assessment_details || {}),
        [k]: v,
      },
    }));
  };

  const getSkillPathways = () => {
    const list = edit.skill_assessment_details?.pathways;
    if (Array.isArray(list) && list.length > 0) return list;
    if (edit.skill_assessment_details?.standard_pathway || edit.skill_assessment_details?.pathway_requirement) {
      return [{
        pathway: edit.skill_assessment_details?.standard_pathway || 'Standard Pathway',
        requirement: edit.skill_assessment_details?.pathway_requirement || '',
      }];
    }
    return [];
  };

  const addSkillPathway = () => {
    const curr = getSkillPathways();
    const updated = [...curr, { pathway: '', requirement: '' }];
    setEdit((prev) => ({
      ...prev,
      skill_assessment_details: {
        ...(prev.skill_assessment_details || {}),
        pathways: updated,
        standard_pathway: updated[0]?.pathway || '',
        pathway_requirement: updated[0]?.requirement || '',
      },
    }));
  };

  const updateSkillPathway = (index, field, value) => {
    const curr = [...getSkillPathways()];
    if (!curr[index]) curr[index] = { pathway: '', requirement: '' };
    curr[index] = { ...curr[index], [field]: value };
    setEdit((prev) => ({
      ...prev,
      skill_assessment_details: {
        ...(prev.skill_assessment_details || {}),
        pathways: curr,
        ...(index === 0 ? {
          standard_pathway: curr[0]?.pathway || '',
          pathway_requirement: curr[0]?.requirement || '',
        } : {}),
      },
    }));
  };

  const removeSkillPathway = (index) => {
    const curr = [...getSkillPathways()];
    curr.splice(index, 1);
    setEdit((prev) => ({
      ...prev,
      skill_assessment_details: {
        ...(prev.skill_assessment_details || {}),
        pathways: curr,
        standard_pathway: curr[0]?.pathway || '',
        pathway_requirement: curr[0]?.requirement || '',
      },
    }));
  };

  const loadStandardSkillPathways = () => {
    const grp = edit.skill_assessment_details?.group || 'Group B';
    const stdPathways = [
      {
        pathway: `${grp} Standard Pathway`,
        requirement: edit.skill_assessment_details?.qualification_requirement
          ? `${edit.skill_assessment_details.qualification_requirement} + ${edit.skill_assessment_details?.employment_requirement || 'At least 1 year of post-qualification employment in a highly relevant occupation'}`
          : 'AQF Bachelor degree or higher (relevant or unrelated field) + At least 1 year of post-qualification employment in a highly relevant occupation',
      },
      {
        pathway: 'Priority Processing',
        requirement: 'Available for urgent assessment (fast-tracked within 10 business days)',
      },
    ];
    setEdit((prev) => ({
      ...prev,
      skill_assessment_details: {
        ...(prev.skill_assessment_details || {}),
        pathways: stdPathways,
        standard_pathway: stdPathways[0].pathway,
        pathway_requirement: stdPathways[0].requirement,
      },
    }));
  };

  const getAuthorityDocs = () => {
    const list = edit.skill_assessment_details?.documents_required;
    if (Array.isArray(list) && list.length > 0) return list;
    return [];
  };

  const addAuthorityDoc = () => {
    const curr = getAuthorityDocs();
    const updated = [...curr, ''];
    upSad('documents_required', updated);
  };

  const updateAuthorityDoc = (index, value) => {
    const curr = [...getAuthorityDocs()];
    curr[index] = value;
    upSad('documents_required', curr);
  };

  const removeAuthorityDoc = (index) => {
    const curr = [...getAuthorityDocs()];
    curr.splice(index, 1);
    upSad('documents_required', curr);
  };

  const loadStandardAuthorityDocs = () => {
    const stdDocs = [
      'Passport bio-data page (colour scan)',
      'Official Degree / Diploma Certificate',
      'Full Academic Transcripts for all completed qualifications',
      'Formal Statement of Service on company letterhead (with duties, hours & dates)',
      'Payment evidence (payslips, tax returns, bank statements for all claimed periods)',
      'Organisational Chart on company letterhead (for Managerial / Group A occupations)',
      'Detailed Professional CV / Résumé',
      'Official English translations for any non-English documents',
    ];
    upSad('documents_required', stdDocs);
  };

  const upStateRating = (stCode, rating) => {
    setEdit((prev) => ({
      ...prev,
      state_ratings: {
        ...(prev.state_ratings || {}),
        [stCode]: rating,
      },
      state_territory_eligibility: {
        ...(prev.state_territory_eligibility || {}),
        [stCode]: {
          ...((prev.state_territory_eligibility || {})[stCode] || {}),
          rating: rating,
        },
      },
    }));
  };

  const upStateDist = (stCode, val) => {
    setEdit((prev) => ({
      ...prev,
      state_distribution: {
        ...(prev.state_distribution || {}),
        [stCode]: val === '' ? '' : (isNaN(parseFloat(val)) ? 0 : parseFloat(val)),
      },
    }));
  };

  const getVisaSubclassList = () => {
    const el = edit.visa_pathways?.visa_eligibility;
    if (Array.isArray(el) && el.length > 0) return el;
    return [];
  };

  const updateVisaSubclassItem = (index, field, value) => {
    setEdit((prev) => {
      const pw = prev.visa_pathways || {};
      const el = Array.isArray(pw.visa_eligibility) ? [...pw.visa_eligibility] : [];
      if (!el[index]) return prev;
      el[index] = { ...el[index], [field]: value };
      return {
        ...prev,
        visa_pathways: { ...pw, visa_eligibility: el },
      };
    });
  };

  const addVisaSubclassItem = () => {
    setEdit((prev) => {
      const pw = prev.visa_pathways || {};
      const el = Array.isArray(pw.visa_eligibility) ? [...pw.visa_eligibility] : [];
      el.push({
        visa_subclass: '',
        name: '',
        stream: 'General Skilled Migration',
        pathway_type: 'General Skilled Migration',
        description: '',
        eligible: true,
        age_limit: 44,
        points_minimum: 65,
        experience_required: '1+ yr',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'MLTSSL',
      });
      return {
        ...prev,
        visa_pathways: { ...pw, visa_eligibility: el },
      };
    });
  };

  const removeVisaSubclassItem = (index) => {
    setEdit((prev) => {
      const pw = prev.visa_pathways || {};
      const el = Array.isArray(pw.visa_eligibility) ? [...pw.visa_eligibility] : [];
      el.splice(index, 1);
      return {
        ...prev,
        visa_pathways: { ...pw, visa_eligibility: el },
      };
    });
  };

  const loadStandardAustralianVisaPathways = () => {
    const stdVisas = [
      {
        visa_subclass: '189',
        name: 'Subclass 189',
        stream: 'Skilled Independent (PR)',
        pathway_type: 'Skilled Independent (PR)',
        description: 'Permanent residence for skilled workers not sponsored by employer/family/state.',
        eligible: true,
        age_limit: 44,
        points_minimum: 65,
        experience_required: '1+ yr',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'MLTSSL',
      },
      {
        visa_subclass: '186',
        name: 'Subclass 186',
        stream: 'Employer Nomination Scheme (PR)',
        pathway_type: 'Employer Nomination Scheme (PR)',
        description: 'Permanent residency via employer sponsorship.',
        eligible: true,
        age_limit: 44,
        points_minimum: 0,
        experience_required: '3 yrs',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'MLTSSL',
      },
      {
        visa_subclass: '190',
        name: 'Subclass 190',
        stream: 'Skilled Nominated (PR)',
        pathway_type: 'Skilled Nominated (PR)',
        description: 'Permanent visa requiring nomination from an Australian state/territory.',
        eligible: true,
        age_limit: 44,
        points_minimum: 65,
        experience_required: '1+ yr',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'MLTSSL',
      },
      {
        visa_subclass: '482',
        name: 'Subclass 482',
        stream: 'Temporary Skill Shortage (Employer-Sponsored)',
        pathway_type: 'Temporary Skill Shortage (Employer-Sponsored)',
        description: 'Temporary work visa (up to 4 years) sponsored by an Australian employer.',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '2 yrs',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'CSOL',
      },
      {
        visa_subclass: '485',
        name: 'Subclass 485',
        stream: 'General Skilled Migration',
        pathway_type: 'General Skilled Migration',
        description: 'Post-study work visa for international qualification holders in MLTSSL occupations.',
        eligible: true,
        age_limit: 44,
        points_minimum: 65,
        experience_required: '1+ yr',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'MLTSSL',
      },
      {
        visa_subclass: '491',
        name: 'Subclass 491',
        stream: 'Skilled Work Regional (Provisional, 5 years)',
        pathway_type: 'Skilled Work Regional (Provisional, 5 years)',
        description: '5-year provisional visa for regional skilled workers; pathway to PR via 191.',
        eligible: true,
        age_limit: 44,
        points_minimum: 65,
        experience_required: '1+ yr',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'MLTSSL',
      },
      {
        visa_subclass: '494',
        name: 'Subclass 494',
        stream: 'Regional Sponsored (SESR)',
        pathway_type: 'Regional Sponsored (SESR)',
        description: 'Regional employer sponsored visa with PR pathway via Subclass 191.',
        eligible: true,
        age_limit: 44,
        points_minimum: 0,
        experience_required: '3 yrs',
        processing_time_months: '3–6 mo',
        fee_native: 'AUD $4,770',
        list: 'MLTSSL',
      },
    ];

    setEdit((prev) => ({
      ...prev,
      visa_pathways: {
        ...(prev.visa_pathways || {}),
        visa_eligibility: stdVisas,
        pathway_lists: prev.pathway_lists && prev.pathway_lists.length ? prev.pathway_lists : ['MLTSSL', 'CSOL'],
      },
    }));
  };

  const loadStandardCanadianVisaPathways = () => {
    const stdVisas = [
      {
        visa_subclass: 'FSWP',
        name: 'Express Entry - FSWP',
        stream: 'Federal Skilled Worker Program (PR)',
        pathway_type: 'Federal Skilled Worker (PR)',
        description: 'Direct permanent residency for skilled foreign workers with university degrees and international experience.',
        eligible: true,
        age_limit: 46,
        points_minimum: 67,
        experience_required: '1+ yr',
        processing_time_months: '5–6 mo',
        fee_native: 'CAD $1,525',
        list: 'Express Entry',
      },
      {
        visa_subclass: 'CEC',
        name: 'Express Entry - CEC',
        stream: 'Canadian Experience Class (PR)',
        pathway_type: 'Canadian Experience Class (PR)',
        description: 'Fast-track permanent residency for skilled workers with at least 1 year of Canadian full-time work experience.',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '1 yr in Canada',
        processing_time_months: '4–5 mo',
        fee_native: 'CAD $1,525',
        list: 'Express Entry',
      },
      {
        visa_subclass: 'PNP',
        name: 'Provincial Nominee Program',
        stream: 'Provincial Nomination (Enhanced / Base PR)',
        pathway_type: 'Provincial Nominee Program (PR)',
        description: 'Provincial nomination offering 600 bonus CRS points for Express Entry candidates or direct paper-based PR nomination.',
        eligible: true,
        age_limit: 49,
        points_minimum: 60,
        experience_required: '2 yrs',
        processing_time_months: '6–9 mo',
        fee_native: 'CAD $1,525',
        list: 'Provincial Nominee',
      },
      {
        visa_subclass: 'LMIA',
        name: 'TFWP Work Permit',
        stream: 'Temporary Foreign Worker (Employer-Sponsored)',
        pathway_type: 'LMIA Employer Work Permit',
        description: 'Employer-specific work permit supported by positive Labour Market Impact Assessment (LMIA).',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '1+ yr',
        processing_time_months: '2–3 mo',
        fee_native: 'CAD $155',
        list: 'Temporary Worker',
      },
      {
        visa_subclass: 'ICT',
        name: 'Intra-Company Transferee',
        stream: 'International Mobility Program (C12 / ICT)',
        pathway_type: 'Intra-Company Transferee (LMIA-Exempt)',
        description: 'Transfer senior executive or specialized knowledge staff from foreign affiliate to Canadian entity without LMIA.',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '1 yr continuous',
        processing_time_months: '2–4 mo',
        fee_native: 'CAD $155',
        list: 'LMIA-Exempt',
      },
      {
        visa_subclass: 'PGWP',
        name: 'Post-Graduation Work Permit',
        stream: 'Post-Study Open Work Permit',
        pathway_type: 'Post-Graduation Open Work Permit',
        description: 'Open work permit up to 3 years for graduates from eligible Canadian Designated Learning Institutions (DLIs).',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '0 yrs (Graduate)',
        processing_time_months: '2–3 mo',
        fee_native: 'CAD $255',
        list: 'Open Work Permit',
      },
      {
        visa_subclass: 'GSS',
        name: 'Global Skills Strategy',
        stream: 'Global Skills Strategy (Fast-Track 2-Week Processing)',
        pathway_type: 'Global Skills Strategy (GSS)',
        description: 'Two-week work permit processing for highly skilled talent in NOC TEER 0 or 1 positions.',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '2 yrs',
        processing_time_months: '1 mo',
        fee_native: 'CAD $155',
        list: 'Fast-Track',
      },
    ];

    setEdit((prev) => ({
      ...prev,
      visa_pathways: {
        ...(prev.visa_pathways || {}),
        visa_eligibility: stdVisas,
        pathway_lists: prev.pathway_lists && prev.pathway_lists.length ? prev.pathway_lists : ['Express Entry', 'Category-Based STEM', 'Provincial Nominee'],
      },
    }));
  };

  const loadStandardNewZealandVisaPathways = () => {
    const stdVisas = [
      {
        visa_subclass: 'Green-T1',
        name: 'Straight to Residence',
        stream: 'Green List Tier 1 Resident Visa',
        pathway_type: 'Green List Tier 1 (Straight to PR)',
        description: 'Direct permanent residency for qualified professionals with an accredited employer job offer in Tier 1 roles.',
        eligible: true,
        age_limit: 55,
        points_minimum: 0,
        experience_required: 'Job offer',
        processing_time_months: '2–3 mo',
        fee_native: 'NZD $4,290',
        list: 'Green List Tier 1',
      },
      {
        visa_subclass: 'SMC',
        name: 'Skilled Migrant Category',
        stream: 'SMC Resident Visa (6-Point System)',
        pathway_type: 'Skilled Migrant Category (PR)',
        description: 'Points-based residency requiring 6 points from NZ registration, recognized qualifications, or high income.',
        eligible: true,
        age_limit: 55,
        points_minimum: 6,
        experience_required: '1–3 yrs in NZ',
        processing_time_months: '4–6 mo',
        fee_native: 'NZD $4,290',
        list: 'Skilled Migrant',
      },
      {
        visa_subclass: 'Green-T2',
        name: 'Work to Residence',
        stream: 'Green List Tier 2 Resident Visa',
        pathway_type: 'Green List Tier 2 (2 Years Work to PR)',
        description: 'Pathway to residence after working for 24 months in a Green List Tier 2 occupation for an accredited employer.',
        eligible: true,
        age_limit: 55,
        points_minimum: 0,
        experience_required: '2 yrs in NZ role',
        processing_time_months: '3–5 mo',
        fee_native: 'NZD $4,290',
        list: 'Green List Tier 2',
      },
      {
        visa_subclass: 'AEWV',
        name: 'Accredited Employer Work Visa',
        stream: 'Temporary Work Visa (Up to 5 Years)',
        pathway_type: 'Accredited Employer Work Visa (AEWV)',
        description: 'Temporary work visa supported by an accredited employer with approved Job Check at or above median wage.',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '3 yrs / relevant qual',
        processing_time_months: '1–2 mo',
        fee_native: 'NZD $750',
        list: 'Temporary Work',
      },
      {
        visa_subclass: 'Care-WTR',
        name: 'Care Sector Work to Residence',
        stream: 'Care Workforce Resident Visa',
        pathway_type: 'Care Sector Pathway to PR',
        description: 'Work to residence pathway for health and care workers earning at or above level 4 wage threshold.',
        eligible: true,
        age_limit: 55,
        points_minimum: 0,
        experience_required: '24 months in care',
        processing_time_months: '3–5 mo',
        fee_native: 'NZD $4,290',
        list: 'Care Workforce',
      },
      {
        visa_subclass: 'PSWV',
        name: 'Post Study Work Visa',
        stream: 'Open Work Visa for NZ Graduates',
        pathway_type: 'Post-Study Open Work Visa',
        description: 'Open work visa up to 3 years for international students who completed degree level qualifications in New Zealand.',
        eligible: true,
        age_limit: 99,
        points_minimum: 0,
        experience_required: '0 yrs (NZ Grad)',
        processing_time_months: '1–2 mo',
        fee_native: 'NZD $700',
        list: 'Open Work',
      },
    ];

    setEdit((prev) => ({
      ...prev,
      visa_pathways: {
        ...(prev.visa_pathways || {}),
        visa_eligibility: stdVisas,
        pathway_lists: prev.pathway_lists && prev.pathway_lists.length ? prev.pathway_lists : ['Green List Tier 1', 'Skilled Migrant'],
      },
    }));
  };

  const loadStandardVisaPathwaysByCountry = () => {
    if (country === 'CA') {
      loadStandardCanadianVisaPathways();
    } else if (country === 'NZ') {
      loadStandardNewZealandVisaPathways();
    } else {
      loadStandardAustralianVisaPathways();
    }
  };

  const toggleVisaSubclass = (subclass) => {
    setEdit((prev) => {
      const pw = prev.visa_pathways || {};
      const el = Array.isArray(pw.visa_eligibility) ? [...pw.visa_eligibility] : [];
      const idx = el.findIndex((x) => String(x.visa_subclass || x.code) === String(subclass));
      if (idx >= 0) {
        el[idx] = { ...el[idx], eligible: !el[idx].eligible };
      } else {
        const countryCfg = COUNTRY_VISA_CONFIG[country] || COUNTRY_VISA_CONFIG.AU;
        const stdMatch = countryCfg.subclasses.find((m) => m.code === String(subclass));
        el.push({
          visa_subclass: String(subclass),
          name: stdMatch?.name || `Subclass ${subclass}`,
          stream: stdMatch?.name || 'Skilled Migration',
          pathway_type: stdMatch?.name || 'Skilled Migration',
          description: '',
          eligible: true,
          age_limit: country === 'CA' ? 49 : country === 'NZ' ? 55 : 44,
          points_minimum: country === 'CA' ? 67 : country === 'NZ' ? 6 : 65,
          experience_required: '1+ yr',
          processing_time_months: '3–6 mo',
          fee_native: countryCfg.feeEstimate || 'AUD $4,770',
          list: (countryCfg.lists || [])[0] || 'General',
        });
      }
      return {
        ...prev,
        visa_pathways: { ...pw, visa_eligibility: el },
      };
    });
  };

  const isSubclassEligible = (subclass) => {
    const el = edit.visa_pathways?.visa_eligibility;
    if (!Array.isArray(el) || el.length === 0) {
      const defs = (COUNTRY_VISA_CONFIG[country]?.subclasses || COUNTRY_VISA_CONFIG.AU.subclasses).map((s) => s.code);
      return defs.includes(String(subclass));
    }
    const found = el.find((x) => String(x.visa_subclass || x.code) === String(subclass));
    return found ? Boolean(found.eligible) : false;
  };

  const togglePathwayList = (listName) => {
    setEdit((prev) => {
      const current = Array.isArray(prev.pathway_lists) && prev.pathway_lists.length
        ? [...prev.pathway_lists]
        : (prev.pathway_list ? [prev.pathway_list] : ['MLTSSL']);
      const exists = current.includes(listName);
      const updated = exists ? current.filter((x) => x !== listName) : [...current, listName];
      return {
        ...prev,
        pathway_lists: updated,
        pathway_list: updated[0] || 'MLTSSL',
      };
    });
  };

  const addFaqItem = () => {
    setEdit((prev) => ({
      ...prev,
      faqs: [...(prev.faqs || []), { question: '', answer: '', q: '', a: '' }],
    }));
  };

  const updateFaqItem = (idx, field, val) => {
    setEdit((prev) => {
      const copy = [...(prev.faqs || [])];
      copy[idx] = {
        ...copy[idx],
        [field]: val,
        [field === 'question' ? 'q' : 'a']: val,
      };
      return { ...prev, faqs: copy };
    });
  };

  const removeFaqItem = (idx) => {
    setEdit((prev) => {
      const copy = [...(prev.faqs || [])];
      copy.splice(idx, 1);
      return { ...prev, faqs: copy };
    });
  };

  const generateDefaultFaqs = () => {
    const title = edit.title || item.title || 'this occupation';
    const code = edit.code || item.code || '';
    const countryCfg = COUNTRY_VISA_CONFIG[country] || COUNTRY_VISA_CONFIG.AU;
    const body = edit.assessing_authority?.short_name || edit.assessing_authority?.name || (country === 'CA' ? 'WES' : country === 'NZ' ? 'NZQA' : 'the designated authority');
    const weeks = edit.assessing_authority?.processing_time_weeks || (country === 'CA' ? '4–8' : country === 'NZ' ? '5–10' : '8–16');
    const recVisa = (typeof edit.recommended_visa_subclass === 'object'
      ? edit.recommended_visa_subclass?.[country]
      : edit.recommended_visa_subclass) || (country === 'CA' ? 'FSWP' : country === 'NZ' ? 'Green-T1' : '190');
    const classificationName = country === 'CA' ? `NOC ${code}` : `ANZSCO ${code}`;

    setEdit((prev) => ({
      ...prev,
      faqs: [
        {
          question: `How long does ${classificationName} assessment take?`,
          answer: `${body} typically processes ${title} assessments in ${weeks} weeks once all documents are submitted.`,
          q: `How long does ${classificationName} assessment take?`,
          a: `${body} typically processes ${title} assessments in ${weeks} weeks once all documents are submitted.`,
        },
        {
          question: `Which visa is recommended for ${title} in ${countryCfg.countryName}?`,
          answer: `The recommended visa pathway for ${title} in ${countryCfg.countryName} is ${recVisa}. Multiple pathways are available based on eligibility benchmarks, state/provincial allocations, and points scores.`,
          q: `Which visa is recommended for ${title} in ${countryCfg.countryName}?`,
          a: `The recommended visa pathway for ${title} in ${countryCfg.countryName} is ${recVisa}. Multiple pathways are available based on eligibility benchmarks, state/provincial allocations, and points scores.`,
        },
        {
          question: `What documents are required for ${title}?`,
          answer: `Identity proof (passport), qualifications (degree certificates + academic transcripts), employment evidence (work reference letters + pay slips + tax records), language test scores, and ${body}-specific verification requirements.`,
          q: `What documents are required for ${title}?`,
          a: `Identity proof (passport), qualifications (degree certificates + academic transcripts), employment evidence (work reference letters + pay slips + tax records), language test scores, and ${body}-specific verification requirements.`,
        },
        {
          question: `Is ${title} on the skilled occupation list?`,
          answer: `${title} (${code}) is currently an active verified occupation on the ${countryCfg.countryName} migration atlas eligible for skilled migration and employer sponsorship.`,
          q: `Is ${title} on the skilled occupation list?`,
          a: `${title} (${code}) is currently an active verified occupation on the ${countryCfg.countryName} migration atlas eligible for skilled migration and employer sponsorship.`,
        },
      ],
    }));
  };

  const loadStandardDocTemplate = () => {
    let std = [];
    if (country === 'CA') {
      std = [
        { id: `doc_${Date.now()}_1`, name: "Passport Bio Page (Certified Color Copy)", category: "Identity", required: true },
        { id: `doc_${Date.now()}_2`, name: "National ID / PAN / Aadhaar Card", category: "Identity", required: true },
        { id: `doc_${Date.now()}_3`, name: "ECA Credential Evaluation Report (WES / ICAS / IQAS / CES)", category: "Education", required: true },
        { id: `doc_${Date.now()}_4`, name: "Degree & Diploma Certificates + Academic Transcripts", category: "Education", required: true },
        { id: `doc_${Date.now()}_5`, name: "IELTS General / CELPIP Score Report (CLB 7+)", category: "Education", required: true },
        { id: `doc_${Date.now()}_6`, name: "Employment Reference Letters (Detailed NOC Job Duties & Hours)", category: "Employment", required: true },
        { id: `doc_${Date.now()}_7`, name: "Pay Stubs & T4 / Income Tax Returns / Notice of Assessment", category: "Employment", required: true },
        { id: `doc_${Date.now()}_8`, name: "Salary Bank Account Statements (Last 12 Months)", category: "Employment", required: true },
        { id: `doc_${Date.now()}_9`, name: "Official Bank Letter & Proof of Unencumbered Settlement Funds", category: "Financial", required: true },
        { id: `doc_${Date.now()}_10`, name: "Police Clearance Certificates (PCC) for Countries Lived 6+ Months", category: "Police / Medical", required: true },
        { id: `doc_${Date.now()}_11`, name: "Upfront eMedical Health Examination Confirmation", category: "Police / Medical", required: true },
        { id: `doc_${Date.now()}_12`, name: "Canadian Style Detailed Professional Résumé / Curriculum Vitae", category: "Other", required: true },
      ];
    } else if (country === 'NZ') {
      std = [
        { id: `doc_${Date.now()}_1`, name: "Passport Bio-data Page (Certified Colour Copy)", category: "Identity", required: true },
        { id: `doc_${Date.now()}_2`, name: "NZQA International Qualifications Assessment (IQA)", category: "Education", required: true },
        { id: `doc_${Date.now()}_3`, name: "Official Degree Certificates & Academic Transcripts", category: "Education", required: true },
        { id: `doc_${Date.now()}_4`, name: "English Language Test Results (IELTS General / PTE Academic)", category: "Education", required: true },
        { id: `doc_${Date.now()}_5`, name: "Accredited Employer Job Offer & Signed Employment Agreement", category: "Employment", required: true },
        { id: `doc_${Date.now()}_6`, name: "Employer Approved Job Check Token / INZ Confirmation", category: "Employment", required: true },
        { id: `doc_${Date.now()}_7`, name: "Work Reference Letters on Letterhead with ANZSCO Duties", category: "Employment", required: true },
        { id: `doc_${Date.now()}_8`, name: "IRD Tax Records / Payslips Demonstrating Median Wage Rate", category: "Employment", required: true },
        { id: `doc_${Date.now()}_9`, name: "General Medical Certificate & Chest X-Ray (INZ 1007)", category: "Police / Medical", required: true },
        { id: `doc_${Date.now()}_10`, name: "National Police Clearance Certificates (PCC)", category: "Police / Medical", required: true },
        { id: `doc_${Date.now()}_11`, name: "Comprehensive Professional CV / Résumé (NZ Format)", category: "Other", required: true },
      ];
    } else {
      std = [
        { id: `doc_${Date.now()}_1`, name: "Passport Bio Page (Certified Color Copy)", category: "Identity", required: true },
        { id: `doc_${Date.now()}_2`, name: "National Identity Card / Aadhaar / PAN", category: "Identity", required: true },
        { id: `doc_${Date.now()}_3`, name: "Degree / Qualification Certificate", category: "Education", required: true },
        { id: `doc_${Date.now()}_4`, name: "Official Academic Transcripts (All Semesters)", category: "Education", required: true },
        { id: `doc_${Date.now()}_5`, name: "Course Syllabus / Unit Outlines (if required)", category: "Education", required: false },
        { id: `doc_${Date.now()}_6`, name: "Work Reference Letters (Company Letterhead + Roles & Duties)", category: "Employment", required: true },
        { id: `doc_${Date.now()}_7`, name: "Pay Slips (First & Last 3 Months of Each Year)", category: "Employment", required: true },
        { id: `doc_${Date.now()}_8`, name: "Income Tax Returns (ITR / Form 16 / Notice of Assessment)", category: "Employment", required: true },
        { id: `doc_${Date.now()}_9`, name: "Bank Account Statements Showing Salary Deposits", category: "Employment", required: true },
        { id: `doc_${Date.now()}_10`, name: "Organizational Chart / Hierarchy Diagram", category: "Employment", required: false },
        { id: `doc_${Date.now()}_11`, name: "PTE Academic / IELTS Test Report Form (Within 3 Years)", category: "English", required: true },
        { id: `doc_${Date.now()}_12`, name: "Police Clearance Certificate (PCC) for Countries Lived 12+ Months", category: "Character", required: true },
        { id: `doc_${Date.now()}_13`, name: "Department Form 80 & Form 1221 Declaration", category: "Character", required: true },
        { id: `doc_${Date.now()}_14`, name: "eMedical Health Examination Assessment (HAP ID)", category: "Health", required: true },
        { id: `doc_${Date.now()}_15`, name: "Detailed Professional Resume / Curriculum Vitae", category: "Professional", required: true },
        { id: `doc_${Date.now()}_16`, name: "Professional Registrations / Board Licenses (if applicable)", category: "Professional", required: false },
      ];
    }
    setEdit((prev) => ({
      ...prev,
      required_documents: std,
    }));
  };

  const loadStandardSampleCases = () => {
    const title = edit.title || item.title || "Professional";
    const codeStr = String(edit.code || item.code || "Code");
    const authCode = edit.assessing_authority?.code || edit.assessing_authority?.short_name || edit.assessing_authority_name || (country === 'CA' ? 'WES' : country === 'NZ' ? 'NZQA' : 'Assessing Authority');

    let stdCases = [];
    if (country === 'CA') {
      stdCases = [
        {
          id: `case_${Date.now()}_1`,
          client_age: 31,
          visa_subclass: "FSWP",
          outcome: "Express Entry ITA & Permanent Residence Approved",
          timeline_months: 5,
          profile_summary: `Bachelor's degree evaluated via ${authCode} ECA. 4 years of foreign experience as ${title}. CRS score of 494 achieved with CLB 9 IELTS.`,
          notes: `Category-based draw ITA received within 6 weeks of pool entry. Complete employment reference letters with NOC ${codeStr} duties submitted without RFI.`,
        },
        {
          id: `case_${Date.now()}_2`,
          client_age: 28,
          visa_subclass: "CEC",
          outcome: "Canadian Experience Class PR Granted",
          timeline_months: 4,
          profile_summary: `Canadian Master's graduate with 2 years of skilled Canadian work experience as ${title}. CLB 10 in English.`,
          notes: `Transitioned seamlessly from Post-Graduation Work Permit (PGWP) to Canadian PR. Fast-track processing approved in 3.5 months.`,
        },
        {
          id: `case_${Date.now()}_3`,
          client_age: 35,
          visa_subclass: "PNP",
          outcome: "Provincial Nomination (600 Pts) & PR Approved",
          timeline_months: 8,
          profile_summary: `Senior ${title} with 7 years industry tenure. Received Notification of Interest (NOI) from Ontario OINP Human Capital Priorities stream.`,
          notes: `Secured 600 bonus CRS points via provincial nomination stream. Invitation to Apply (ITA) received on subsequent Express Entry round.`,
        },
      ];
    } else if (country === 'NZ') {
      stdCases = [
        {
          id: `case_${Date.now()}_1`,
          client_age: 32,
          visa_subclass: "Green-T1",
          outcome: "Green List Tier 1 Straight to Residence Granted",
          timeline_months: 3,
          profile_summary: `Recognised university qualification with ${authCode} comparability. Accredited employer job offer in Auckland as ${title}.`,
          notes: `Green List Straight to Residence pathway leveraged. Resident visa approved without stand-down period within 9 weeks.`,
        },
        {
          id: `case_${Date.now()}_2`,
          client_age: 29,
          visa_subclass: "SMC",
          outcome: "Skilled Migrant Category Resident Visa Approved",
          timeline_months: 5,
          profile_summary: `Master's degree holder claiming 6 skill points across qualification and skilled NZ employment in ${title}.`,
          notes: `Met full 6-point SMC threshold. Expression of Interest (EOI) selected and approved directly by Immigration New Zealand.`,
        },
        {
          id: `case_${Date.now()}_3`,
          client_age: 36,
          visa_subclass: "AEWV",
          outcome: "AEWV Work Visa Approved (5 Years)",
          timeline_months: 2,
          profile_summary: `Experienced ${title} sponsored by an Accredited New Zealand corporate employer at or above median wage rate.`,
          notes: `Employer Job Check approved in 8 business days. Strategic stepping stone towards Tier 2 Work to Residence application.`,
        },
      ];
    } else {
      stdCases = [
        {
          id: `case_${Date.now()}_1`,
          client_age: 32,
          visa_subclass: "190",
          outcome: "Positive Skills Assessment & Subclass 190 PR Granted",
          timeline_months: 5,
          profile_summary: `Bachelor's degree with 6 years of post-qualification experience in ${title}. Positive ${authCode} assessment achieved on first submission.`,
          notes: `Full documentation of roles, salary bank credits and tax filings aligned to ANZSCO ${codeStr} descriptor. Nomination invitation received within 90 days.`,
        },
        {
          id: `case_${Date.now()}_2`,
          client_age: 29,
          visa_subclass: "491",
          outcome: "Positive Skills Assessment & Regional Nomination Approved",
          timeline_months: 4,
          profile_summary: `Master's graduate with 3.5 years verified overseas experience as ${title}. English Proficient (PTE 79+ across all bands).`,
          notes: `Leveraged 15 points regional sponsorship bonus. Fast-track skill assessment completed in 6 weeks.`,
        },
        {
          id: `case_${Date.now()}_3`,
          client_age: 36,
          visa_subclass: "186",
          outcome: "Direct Entry Permanent Residency Approved",
          timeline_months: 7,
          profile_summary: `Senior ${title} with 10+ years industry leadership and multi-country tenure. Employer-sponsored transition.`,
          notes: `Full skills assessment exemption pathway navigated with accredited Australian corporate sponsor.`,
        },
      ];
    }

    setEdit((prev) => ({
      ...prev,
      sample_cases: stdCases,
    }));
  };

  const upEe = (k, v) => {
    setEdit((prev) => ({
      ...prev,
      ee_eligibility: {
        ...(prev.ee_eligibility || {}),
        [k]: v,
      },
    }));
  };

  const upNz = (field, val) => {
    setEdit((prev) => ({
      ...prev,
      aewv_eligibility: {
        ...(prev.aewv_eligibility || {}),
        [field]: val,
      },
    }));
  };

  const upSmc = (field, val) => {
    setEdit((prev) => ({
      ...prev,
      smc_points_breakdown: {
        ...(prev.smc_points_breakdown || {}),
        [field]: val,
      },
    }));
  };

  const upSeo = (field, val) => {
    setEdit((prev) => ({
      ...prev,
      seo_meta: {
        ...(prev.seo_meta || {}),
        [field]: val,
      },
    }));
  };

  const handleCopySeoText = (key, text) => {
    if (!text) return;
    try {
      navigator.clipboard?.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch {
      // fallback
    }
  };

  const isValidJson = (str) => {
    if (!str || !str.trim()) return true;
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  };

  const handleAutoGenerateSeo = () => {
    const occTitle = edit.title || item.title || 'Skilled Professional';
    const occCode = edit.code || item.code || '';
    const cMeta = country === 'CA'
      ? { name: 'Canada', classification: 'NOC 2021' }
      : country === 'NZ'
        ? { name: 'New Zealand', classification: 'ANZSCO' }
        : { name: 'Australia', classification: 'ANZSCO' };
    
    const aaName = edit.assessing_authority?.short_name || edit.assessing_authority?.code || edit.assessing_authority?.name || (country === 'CA' ? 'WES' : country === 'NZ' ? 'NZQA' : 'VETASSESS');
    
    const genTitle = `${occTitle} (${occCode}) — ${cMeta.name} ${cMeta.classification} Migration Guide | LEAMSS`;
    
    let genDesc = '';
    if (country === 'CA') {
      const teerStr = edit.teer_category != null ? `TEER ${edit.teer_category}` : 'TEER 1';
      genDesc = `Complete migration guide for ${occTitle} (NOC ${occCode}, ${teerStr}) in Canada. Check Express Entry category draws, ${aaName} ECA assessment, and provincial nomination options.`;
    } else if (country === 'NZ') {
      const glStr = edit.nz_green_list_tier ? `Green List Tier ${edit.nz_green_list_tier}` : 'Skilled Migrant Category';
      genDesc = `Migrate to New Zealand as ${occTitle} (${occCode}). Check ${glStr} residence pathways, ${aaName} qualification assessment, and AEWV accredited employer rules.`;
    } else {
      genDesc = `Comprehensive migration evaluation for ${occTitle} (ANZSCO ${occCode}) in Australia. Check 189/190/491 visa points, ${aaName} skill assessment, and state shortage lists.`;
    }

    const focusKw = `${occTitle} ${cMeta.name} PR`;
    const kwList = [
      occTitle,
      occCode,
      `${occTitle} ${cMeta.name}`,
      `${cMeta.classification} ${occCode}`,
      `${occTitle} ${cMeta.name} PR`,
      `migrate to ${cMeta.name} as ${occTitle}`,
      `${occTitle} skill assessment`,
      `${aaName} assessment criteria`,
      `${occTitle} visa pathways`,
      'immigration consultant India',
      'LEAMSS'
    ].join(', ');

    const canonical = `https://leamss.com/atlas/${(country || 'au').toLowerCase()}/${occCode}`;
    const defaultOgImage = 'https://leamss.com/leamss-logo.png';
    const loc = country === 'AU' ? 'en_AU' : country === 'CA' ? 'en_CA' : country === 'NZ' ? 'en_NZ' : 'en_IN';

    setEdit((prev) => ({
      ...prev,
      seo_meta: {
        ...(prev.seo_meta || {}),
        meta_title: genTitle,
        meta_description: genDesc,
        focus_keyword: focusKw,
        keywords: kwList,
        canonical_url: canonical,
        meta_robots: 'index, follow, max-image-preview:large, max-snippet:-1',
        og_title: genTitle,
        og_description: genDesc,
        og_image: defaultOgImage,
        og_locale: loc,
        twitter_card: 'summary_large_image',
        twitter_title: genTitle,
        twitter_description: genDesc,
        twitter_image: defaultOgImage,
        schema_type: 'Occupation',
      },
    }));
  };

  const minPts = edit.min_invitation_points || {};
  const anzscoProf = edit.anzsco_profile || {};
  const absD = edit.abs_data || {};
  const jsaD = edit.jsa_data || {};
  const absM = edit.abs_labour_market || {};
  const ste = edit.state_territory_eligibility || {};
  const sad = edit.skill_assessment_details || {};
  const stDist = edit.state_distribution || {};
  const ee = edit.ee_eligibility || {};
  const aewv = edit.aewv_eligibility || {};
  const smc = edit.smc_points_breakdown || {};
  const seo = edit.seo_meta || {};

  // Country-aware regions and authorities
  const regionsList = country === 'CA' ? CA_PROVINCES : country === 'NZ' ? NZ_REGIONS : AU_STATES;
  const jurisdictionLabel = country === 'CA' ? 'Provincial' : country === 'NZ' ? 'Regional' : 'State & Territory';
  const authorityBodyName = country === 'CA' ? 'ESDC & Job Bank Canada' : country === 'NZ' ? 'MBIE & Immigration New Zealand' : 'Jobs & Skills Australia (JSA)';
  const availableAuthorities = (country === 'CA')
    ? CA_AUTHORITIES
    : (country === 'NZ')
      ? NZ_AUTHORITIES
      : (authorities && authorities.length > 0 ? authorities : [
          { code: 'VETASSESS', name: 'Vocational Education and Training Assessment Services' },
          { code: 'ACS', name: 'Australian Computer Society' },
          { code: 'EA', name: 'Engineers Australia' },
          { code: 'TRA', name: 'Trades Recognition Australia' },
          { code: 'CPA', name: 'CPA Australia' },
          { code: 'ANMAC', name: 'Australian Nursing and Midwifery Accreditation Council' },
          { code: 'IML', name: 'Institute of Managers and Leaders' },
        ]);

  // Compute total state distribution share
  const totalStateShare = regionsList.reduce((acc, st) => {
    const val = parseFloat(stDist[st.code] || 0);
    return acc + (isNaN(val) ? 0 : val);
  }, 0);

  // Strong regions list string
  const strongRegionsText = Array.isArray(edit.strong_regions) && edit.strong_regions.length
    ? edit.strong_regions.map((r) => typeof r === 'string' ? r : `${r.region_name || r.sa4_name || ''} · ${r.state || 'AU'}`).join('\n')
    : '';

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12" data-testid="public-atlas-unified-editor">
      {/* ── TOP LIVE PREVIEW & PUBLISH BANNER ── */}
      <div className="rounded-xl border border-emerald-300 bg-gradient-to-r from-emerald-50 via-teal-50 to-white p-4 shadow-sm flex items-center justify-between flex-wrap gap-3 sticky top-2 z-30">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow shrink-0 font-bold">
            <Globe2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-emerald-950">Public Atlas Live Page Editor</span>
              <Badge className="bg-emerald-100 text-emerald-900 border-emerald-300 font-mono text-xs">
                {country} · {item.code}
              </Badge>
              <span className="text-xs text-slate-500 font-mono bg-white px-2 py-0.5 rounded border">
                {publicUrl}
              </span>
            </div>
            <p className="text-xs text-emerald-800 mt-1">
              Every section displayed on the client-facing Public Atlas page is editable here. Changes update the public site when you click <strong>"Save &amp; Publish Live"</strong>.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => window.open(publicUrl, '_blank')}
            className="border-emerald-600 text-emerald-800 hover:bg-emerald-100 font-semibold text-xs h-9 bg-white"
            data-testid="unified-open-public-btn"
          >
            <ExternalLink className="w-4 h-4 mr-1.5 text-emerald-600" />
            View Public Page ↗
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={verify}
            disabled={saving}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-9 shadow-sm px-4"
            data-testid="unified-publish-top-btn"
          >
            {saving ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-1.5" />}
            Save &amp; Publish Live
          </Button>
        </div>
      </div>

      {/* ── CARD 1: HEADER & OVERVIEW ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">🏷️</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">1. Occupation Header &amp; Overview</h3>
              <p className="text-xs text-slate-500">Public Hero heading, ANZSCO skill level, description, tasks and alternative titles.</p>
            </div>
          </div>
          <Badge className="text-[10px] bg-slate-100 text-slate-700 font-semibold">Public Hero &amp; Overview</Badge>
        </div>

        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1">
            Official Occupation Title (Public Heading 1) *
          </Label>
          <Input
            value={edit.title || ''}
            onChange={(e) => setEdit({ ...edit, title: e.target.value })}
            placeholder="e.g. Chief Executive or Managing Director"
            className="h-10 text-sm font-bold text-slate-900 bg-slate-50/50"
            data-testid="public-edit-title"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {country === 'CA' ? (
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                NOC 2021 TEER Category (0 to 5) *
              </Label>
              <Select value={String(edit.teer_category !== '' && edit.teer_category != null ? edit.teer_category : '1')} onValueChange={(v) => setEdit({ ...edit, teer_category: v })}>
                <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">TEER 0 · Management Occupations</SelectItem>
                  <SelectItem value="1">TEER 1 · Degree Completion (Bachelor+)</SelectItem>
                  <SelectItem value="2">TEER 2 · College Diploma / 2+ yrs Apprenticeship</SelectItem>
                  <SelectItem value="3">TEER 3 · College Diploma &lt;2 yrs / On-the-job training</SelectItem>
                  <SelectItem value="4">TEER 4 · Secondary School Diploma</SelectItem>
                  <SelectItem value="5">TEER 5 · Work Demonstration / No Formal Ed</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-[10px] text-slate-400">Determines Express Entry &amp; PNP eligibility</span>
            </div>
          ) : (
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                ANZSCO Skill Level (1 to 5) *
              </Label>
              <Select value={String(edit.skill_level || '1')} onValueChange={(v) => setEdit({ ...edit, skill_level: v })}>
                <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Level 1 · Bachelor Degree or Higher</SelectItem>
                  <SelectItem value="2">Level 2 · Associate Degree / Advanced Diploma</SelectItem>
                  <SelectItem value="3">Level 3 · Certificate IV / III (Trades)</SelectItem>
                  <SelectItem value="4">Level 4 · Certificate II / III</SelectItem>
                  <SelectItem value="5">Level 5 · Certificate I / Secondary</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-[10px] text-slate-400">Displayed in Eligibility badge</span>
            </div>
          )}

          {country === 'CA' ? (
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Express Entry Selection Priority
              </Label>
              <Select
                value={edit.ee_priority || 'fswp_cec'}
                onValueChange={(v) => setEdit({ ...edit, ee_priority: v })}
              >
                <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="fswp_cec">Category-Based Selection Eligible</SelectItem>
                  <SelectItem value="stem">STEM Priority Category</SelectItem>
                  <SelectItem value="healthcare">Healthcare Priority Category</SelectItem>
                  <SelectItem value="trades">Trade Occupations Category</SelectItem>
                  <SelectItem value="transport">Transport Occupations Category</SelectItem>
                  <SelectItem value="agriculture">Agriculture &amp; Agri-Food Category</SelectItem>
                  <SelectItem value="french">French-Language Proficiency Category</SelectItem>
                  <SelectItem value="general">General Express Entry (FSWP/CEC)</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-[10px] text-slate-400">IRCC Category-Based Draw priority</span>
            </div>
          ) : country === 'NZ' ? (
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                New Zealand Green List &amp; SMC
              </Label>
              <Select
                value={edit.nz_green_list_tier !== '' && edit.nz_green_list_tier != null ? String(edit.nz_green_list_tier) : '0'}
                onValueChange={(v) => setEdit({ ...edit, nz_green_list_tier: v === '0' ? null : v })}
              >
                <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">Not on Green List (Standard SMC)</SelectItem>
                  <SelectItem value="1">Tier 1 · Straight to Residence (Fast-Track)</SelectItem>
                  <SelectItem value="2">Tier 2 · Work to Residence (2 Years)</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-[10px] text-slate-400">INZ Operational Manual schedule</span>
            </div>
          ) : (
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                SkillSelect Priority Tier
              </Label>
              <Select
                value={typeof edit.skillselect_tier === 'object' && edit.skillselect_tier !== null
                  ? (edit.skillselect_tier.tier || 'tier_3')
                  : (edit.skillselect_tier || 'tier_3')}
                onValueChange={(v) => setEdit({ ...edit, skillselect_tier: v })}
              >
                <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="tier_1">Tier 1 · Priority Healthcare &amp; Education</SelectItem>
                  <SelectItem value="tier_2">Tier 2 · Core Skills / CSOL High Demand</SelectItem>
                  <SelectItem value="tier_3">Tier 3 · MLTSSL Professional &amp; Management</SelectItem>
                  <SelectItem value="tier_4">Tier 4 · Short-Term / Regional (STSOL)</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-[10px] text-slate-400">Determines invitation priority</span>
            </div>
          )}

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Classification Standard Version
            </Label>
            <Input
              value={edit.classification_version || (country === 'CA' ? 'NOC 2021 Version 1.0' : country === 'NZ' ? 'ANZSCO Version 1.3' : 'ANZSCO 2013 / 2022')}
              onChange={(e) => setEdit({ ...edit, classification_version: e.target.value })}
              placeholder={country === 'CA' ? 'e.g. NOC 2021 Version 1.0' : country === 'NZ' ? 'e.g. ANZSCO Version 1.3' : 'e.g. ANZSCO 2013 / 2022'}
              className="h-9 text-xs"
            />
            <span className="text-[10px] text-slate-400">Displayed in official registry seal</span>
          </div>
        </div>

        {/* AU SkillSelect & Migroto Live Quick Card */}
        {country === 'AU' && (
          <div className="p-3 bg-teal-50/70 border border-teal-200 rounded-lg flex items-center justify-between flex-wrap gap-2 text-xs">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-teal-700 shrink-0" />
              <div>
                <span className="font-bold text-slate-900">SkillSelect Cutoff Benchmarks: </span>
                <span className="font-mono text-emerald-800 font-semibold">
                  189: {edit.min_invitation_points?.subclass_189 ?? 80} pts · 190: {edit.min_invitation_points?.subclass_190 ?? 75} pts · 491: {edit.min_invitation_points?.subclass_491 ?? 65} pts
                </span>
                <span className="text-slate-500 text-[11px] ml-1">
                  ({(edit.invitation_rounds || []).length} rounds recorded · Section 5)
                </span>
              </div>
            </div>
            {syncMigroto && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={syncMigroto}
                disabled={migrotoLoading}
                className="h-6 text-xs bg-white text-teal-800 border-teal-300 hover:bg-teal-100 font-bold"
                data-testid="unified-sync-migroto-quick-btn"
                title="Pull latest invitation cutoffs and round archives directly from Migroto live registry"
              >
                {migrotoLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCw className="h-3 w-3 mr-1 text-teal-700" />}
                Sync from Migroto Live
              </Button>
            )}
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-1">
            <Label className="text-xs font-semibold text-slate-700">
              Occupation Description (Shown under "About this Occupation")
            </Label>
            {aiDraft?.description && (
              <button
                type="button"
                onClick={() => setEdit({ ...edit, description: aiDraft.description })}
                className="text-xs text-purple-600 hover:text-purple-800 font-semibold"
              >
                ✨ Insert AI Suggestion
              </button>
            )}
          </div>
          <Textarea
            value={edit.description || ''}
            onChange={(e) => setEdit({ ...edit, description: e.target.value })}
            rows={4}
            placeholder="Comprehensive overview of what this professional does, scope of practice, and duties..."
            className="text-xs leading-relaxed"
          />
        </div>

        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1">
            Typical Tasks &amp; Duties (One per line — shown as numbered items on public page)
          </Label>
          <Textarea
            value={(edit.typical_tasks || []).join('\n')}
            onChange={(e) => setEdit({ ...edit, typical_tasks: e.target.value.split('\n').filter(Boolean) })}
            rows={6}
            placeholder="Determining objectives, strategies, policies and programs&#10;Providing overall direction and management&#10;Authorising material, human and financial resources..."
            className="text-xs font-mono leading-relaxed"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Alternative Job Titles (comma-separated)
            </Label>
            <Input
              value={(edit.alternative_titles || []).join(', ')}
              onChange={(e) => setEdit({ ...edit, alternative_titles: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
              placeholder="e.g. Director-General, Managing Director"
              className="h-8 text-xs"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Recognised Specialisations (comma-separated — shown with green star pills)
            </Label>
            <Input
              value={(edit.specialisations || []).join(', ')}
              onChange={(e) => setEdit({ ...edit, specialisations: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
              placeholder="e.g. Chief Executive Officer (CEO), Chief Operating Officer (COO)"
              className="h-8 text-xs"
            />
          </div>
        </div>
      </Card>

      {/* ── CARD 2: SKILL ASSESSMENT ESSENTIALS & CRITERIA ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-5" data-testid="card-skill-assessment-editor">
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-sm">
              🏛️
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">2. Skill Assessment Essentials &amp; Criteria</h3>
              <p className="text-xs text-slate-500">Configures Assessment card on Public Atlas and Sales tabs: Assessing Body, Official Portal URL, Fees, Processing, Validity, Framework, Benchmarks, Pathways, and Required Documents Checklist.</p>
            </div>
          </div>
          <Badge className="text-[10px] bg-amber-50 text-amber-900 border-amber-300 font-semibold">Public Atlas &amp; Sales Unified</Badge>
        </div>

        {/* 2A: Designated Assessing Authority & Official Portal */}
        <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <Landmark className="h-3.5 w-3.5 text-amber-600" />
              Designated Assessing Authority &amp; Official Portal
            </span>
            <Badge variant="outline" className="text-[10px] font-mono bg-white">Statutory Body</Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                {country === 'CA' ? 'ECA Assessing Body Code *' : country === 'NZ' ? 'NZQA / Assessing Authority *' : 'Assessing Body Code / Short Name *'}
              </Label>
              <Select
                value={selectedAuthCode || edit.assessing_authority?.code || sad.short_name || (country === 'CA' ? 'WES' : country === 'NZ' ? 'NZQA' : 'VETASSESS')}
                onValueChange={(val) => {
                  const match = availableAuthorities.find((a) => a.code === val);
                  if (match) {
                    setEdit((prev) => ({
                      ...prev,
                      assessing_authority: {
                        ...(prev.assessing_authority || {}),
                        code: match.code,
                        short_name: match.code,
                        full_name: match.full_name || match.name,
                        name: match.full_name || match.name,
                        website: match.website || (prev.assessing_authority || {}).website || '',
                        url: match.website || (prev.assessing_authority || {}).url || '',
                      },
                    }));
                    upSad('short_name', match.code);
                    upSad('code', match.code);
                    upSad('full_name', match.full_name || match.name);
                    if (match.website) upSad('website', match.website);
                  } else {
                    upSad('short_name', val);
                    upSad('code', val);
                  }
                  if (handleAuthorityChange) handleAuthorityChange(val);
                }}
              >
                <SelectTrigger className="h-9 text-xs font-bold text-slate-800 bg-white">
                  <SelectValue placeholder="Select assessing body..." />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {availableAuthorities.map((a) => (
                    <SelectItem key={a.code} value={a.code}>
                      <span className="font-bold">{a.code}</span> — {a.full_name || a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="sm:col-span-2">
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Full Official Authority Name
              </Label>
              <Input
                value={edit.assessing_authority?.full_name || edit.assessing_authority?.name || sad.full_name || ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setEdit((prev) => ({
                    ...prev,
                    assessing_authority: {
                      ...(prev.assessing_authority || {}),
                      full_name: val,
                      name: val,
                    },
                  }));
                  upSad('full_name', val);
                }}
                placeholder="e.g. Vocational Education and Training Assessment Services (VETASSESS)"
                className="h-9 text-xs font-semibold bg-white"
              />
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Official Assessment Portal URL (Official Site / Application Link)
            </Label>
            <div className="flex gap-2">
              <Input
                value={edit.assessing_authority?.website || sad.website || ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setEdit((prev) => ({
                    ...prev,
                    assessing_authority: {
                      ...(prev.assessing_authority || {}),
                      website: val,
                      url: val,
                    },
                  }));
                  upSad('website', val);
                }}
                placeholder="https://www.vetassess.com.au/"
                className="h-9 text-xs font-mono bg-white flex-1"
              />
              {(edit.assessing_authority?.website || sad.website) && (
                <a
                  href={(edit.assessing_authority?.website || sad.website).startsWith('http') ? (edit.assessing_authority?.website || sad.website) : `https://${edit.assessing_authority?.website || sad.website}`}
                  target="_blank"
                  rel="noreferrer"
                  className="h-9 px-3 rounded-md border border-indigo-200 bg-white hover:bg-indigo-50 text-indigo-700 text-xs font-bold flex items-center gap-1.5 transition shrink-0"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>Test Link</span>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* 2B: Commercial Fees, Processing, Validity & Framework */}
        <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <DollarSign className="h-3.5 w-3.5 text-emerald-600" />
              Fees, Turnaround Processing, Validity &amp; Framework
            </span>
            <Badge variant="outline" className="text-[10px] font-mono bg-white">4 Metric Tiles</Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Official Standard Fee ({countryCfg.currency})
              </Label>
              <Input
                type="number"
                value={edit.assessing_authority?.fee_native || sad.msa_fee_aud || sad.fee_native || ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setEdit((prev) => ({
                    ...prev,
                    assessing_authority: {
                      ...(prev.assessing_authority || {}),
                      fee_native: val,
                    },
                  }));
                  upSad('msa_fee_aud', val ? parseFloat(val) : '');
                  upSad('fee_native', val);
                }}
                placeholder={country === 'CA' ? 'e.g. 260' : country === 'NZ' ? 'e.g. 746' : 'e.g. 1188'}
                className="h-9 text-xs font-bold text-emerald-800 font-mono bg-white"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">
                Live INR est: ~₹{Math.round((parseFloat(edit.assessing_authority?.fee_native || sad.msa_fee_aud || (country === 'CA' ? 260 : country === 'NZ' ? 746 : 1188)) || (country === 'CA' ? 260 : country === 'NZ' ? 746 : 1188)) * (country === 'CA' ? 62 : country === 'NZ' ? 51 : 55)).toLocaleString()} INR
              </span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Turnaround / Processing Time
              </Label>
              <Input
                value={sad.processing_time || (edit.assessing_authority?.processing_time_weeks ? `${edit.assessing_authority.processing_time_weeks} weeks` : '9–13 weeks')}
                onChange={(e) => {
                  const val = e.target.value;
                  upSad('processing_time', val);
                  const weeksMatch = val.match(/(\d+)\s*(?:–|-|\sto\s)?\s*(\d+)?\s*weeks?/i);
                  const weeks = weeksMatch ? (weeksMatch[2] || weeksMatch[1]) : val.replace(/[^0-9]/g, '');
                  if (weeks) {
                    setEdit((prev) => ({
                      ...prev,
                      assessing_authority: { ...(prev.assessing_authority || {}), processing_time_weeks: weeks }
                    }));
                  }
                }}
                placeholder="e.g. 9–13 weeks or 60–90 days"
                className="h-9 text-xs font-mono bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Shown on Processing Timeframe tile</span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Fast-track / Priority Processing
              </Label>
              <Input
                value={sad.fast_track_days || (sad.priority_days_min ? `${sad.priority_days_min}–${sad.priority_days_max || 20} days` : '10–20 days')}
                onChange={(e) => {
                  const val = e.target.value;
                  upSad('fast_track_days', val);
                  const nums = val.match(/\d+/g);
                  if (nums && nums.length > 0) {
                    upSad('priority_days_min', parseInt(nums[0], 10));
                    upSad('priority_days_max', parseInt(nums[1] || nums[0], 10));
                  }
                }}
                placeholder="e.g. 10–20 days or 10 business days"
                className="h-9 text-xs font-mono bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Fast-track sub-label</span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Assessment Validity
              </Label>
              <Input
                value={sad.validity_years ? `${sad.validity_years} years` : (sad.validity || (country === 'CA' ? '5 years' : country === 'NZ' ? 'Permanent' : '3 years'))}
                onChange={(e) => {
                  const val = e.target.value;
                  upSad('validity', val);
                  const num = parseInt(val.replace(/[^0-9]/g, ''), 10);
                  if (!isNaN(num)) upSad('validity_years', num);
                }}
                placeholder="e.g. 3 years or 5 years"
                className="h-9 text-xs font-semibold bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">
                {country === 'CA' ? 'Recognised for Express Entry & PNP' : country === 'NZ' ? 'Recognised for SMC & Green List' : 'Recognised for SkillSelect EOI'}
              </span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                {country === 'CA' ? 'ECA Tier / Credential Stream' : country === 'NZ' ? 'NZQA Level / Stream' : 'Assessing Body Group (Group A/B/C/D)'}
              </Label>
              <Input
                value={sad.group || (country === 'CA' ? 'Standard ECA' : country === 'NZ' ? 'Level 7+' : 'Group B')}
                onChange={(e) => upSad('group', e.target.value)}
                placeholder={country === 'CA' ? 'e.g. Standard ECA or Professional' : country === 'NZ' ? 'e.g. Level 7+' : 'e.g. Group B or Group A'}
                className="h-9 text-xs font-bold text-amber-900 bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">
                {country === 'CA' ? 'IRCC ECA Credential Stream' : country === 'NZ' ? 'NZQF Qualification Level' : 'VETASSESS / Authority Group classification'}
              </span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Official Authority Framework Title
              </Label>
              <Input
                value={sad.framework || sad.framework_title || (sad.group ? `Group ${sad.group} Occupation` : 'Group B Occupation')}
                onChange={(e) => {
                  upSad('framework', e.target.value);
                  upSad('framework_title', e.target.value);
                }}
                placeholder="e.g. Group B Occupation or VETASSESS General Professional Occupations Assessment — Group B"
                className="h-9 text-xs font-semibold bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Header of Framework tile &amp; benchmark</span>
            </div>
          </div>
        </div>

        {/* 2C: Assessment Criteria Benchmarks */}
        <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <Award className="h-3.5 w-3.5 text-indigo-600" />
              Assessment Criteria &amp; Education/Experience Benchmarks
            </span>
            <Badge variant="outline" className="text-[10px] font-mono bg-white">Criteria Grid</Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                🎓 Educational Requirement
              </Label>
              <Input
                value={sad.qualification_requirement || sad.educational_requirement || ''}
                onChange={(e) => {
                  upSad('qualification_requirement', e.target.value);
                  upSad('educational_requirement', e.target.value);
                }}
                placeholder="e.g. AQF Bachelor degree or higher (relevant or unrelated field)"
                className="h-9 text-xs font-semibold text-slate-800 bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Degree level and field of study requirement</span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                💼 Employment Requirement
              </Label>
              <Input
                value={sad.employment_requirement || ''}
                onChange={(e) => upSad('employment_requirement', e.target.value)}
                placeholder="e.g. At least 1 year of post-qualification employment in a highly relevant occupation"
                className="h-9 text-xs font-semibold text-slate-800 bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Post-qualification relevant work experience</span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                🗣️ English Language Requirement
              </Label>
              <Input
                value={sad.english_required || sad.english_requirement || ''}
                onChange={(e) => {
                  upSad('english_required', e.target.value);
                  upSad('english_requirement', e.target.value);
                }}
                placeholder="e.g. Competent English (IELTS 6.0 / PTE 50 or exempt)"
                className="h-9 text-xs font-semibold text-slate-800 bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Minimum English test score required</span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Standard Pathway Title (Overview Sub-label)
              </Label>
              <Input
                value={sad.standard_pathway || (sad.pathways?.[0]?.pathway) || ''}
                onChange={(e) => {
                  upSad('standard_pathway', e.target.value);
                  const pws = [...getSkillPathways()];
                  if (pws.length > 0) {
                    pws[0] = { ...pws[0], pathway: e.target.value };
                  } else {
                    pws.push({ pathway: e.target.value, requirement: sad.pathway_requirement || '' });
                  }
                  upSad('pathways', pws);
                }}
                placeholder="e.g. Group B Standard Pathway or General Skills Assessment"
                className="h-9 text-xs font-semibold bg-white"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Main summary pathway title</span>
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              📜 Full Qualification Rules &amp; Statutory Criteria (Textarea)
            </Label>
            <Textarea
              value={edit.qualification_rules || sad.qualification_rules || ''}
              onChange={(e) => {
                setEdit({ ...edit, qualification_rules: e.target.value });
                upSad('qualification_rules', e.target.value);
              }}
              rows={3}
              placeholder="Detailed rules: degree level, minimum post-qualification years, RPL alternative options, assessing body specific guidelines..."
              className="text-xs leading-relaxed bg-white"
            />
          </div>
        </div>

        {/* 2D: Assessment Pathways & Application Streams */}
        <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Briefcase className="h-3.5 w-3.5 text-amber-600" />
                Assessment Pathways &amp; Application Streams
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Application streams displayed under Assessment Pathways on Public and Sales pages.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={loadStandardSkillPathways}
                className="h-7 text-xs bg-white text-slate-700 border-slate-300 hover:bg-amber-50 hover:text-amber-900"
              >
                <Wand2 className="w-3 h-3 mr-1 text-amber-600" />
                Load Standard Pathways
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={addSkillPathway}
                className="h-7 text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold"
              >
                <Plus className="w-3 h-3 mr-1" />
                Add Pathway
              </Button>
            </div>
          </div>

          <div className="space-y-2.5">
            {getSkillPathways().length === 0 ? (
              <div className="p-4 bg-white rounded-lg border border-dashed border-slate-300 text-center text-xs text-slate-500">
                No custom pathways added yet. Click <strong>"Load Standard Pathways"</strong> to auto-populate standard and priority processing pathways.
              </div>
            ) : (
              getSkillPathways().map((pw, idx) => (
                <div key={idx} className="p-3 bg-white rounded-lg border border-slate-200 flex items-start gap-2.5 shadow-2xs">
                  <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-800 text-[11px] font-bold flex items-center justify-center shrink-0 mt-1">
                    {idx + 1}
                  </span>
                  <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div>
                      <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Pathway Title</Label>
                      <Input
                        value={pw.pathway || ''}
                        onChange={(e) => updateSkillPathway(idx, 'pathway', e.target.value)}
                        placeholder="e.g. Group B Standard Pathway"
                        className="h-8 text-xs font-bold text-slate-800"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Requirement &amp; Description</Label>
                      <Input
                        value={pw.requirement || ''}
                        onChange={(e) => updateSkillPathway(idx, 'requirement', e.target.value)}
                        placeholder="e.g. AQF Bachelor degree or higher + At least 1 year of post-qualification employment"
                        className="h-8 text-xs text-slate-700"
                      />
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeSkillPathway(idx)}
                    className="h-8 w-8 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50 mt-4 shrink-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 2E: Documents Required for Skills Assessment (Authority Checklist) */}
        <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <FileCheck className="h-3.5 w-3.5 text-emerald-600" />
                Documents Required for Skills Assessment
                <Badge className="ml-1.5 text-[10px] bg-emerald-100 text-emerald-900 border-emerald-300 font-mono">
                  {getAuthorityDocs().length} items
                </Badge>
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Official authority document checklist displayed on Public Atlas and Sales views.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={loadStandardAuthorityDocs}
                className="h-7 text-xs bg-white text-slate-700 border-slate-300 hover:bg-emerald-50 hover:text-emerald-900"
              >
                <Wand2 className="w-3 h-3 mr-1 text-emerald-600" />
                Load Standard 8-Doc Authority Checklist
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={addAuthorityDoc}
                className="h-7 text-xs bg-emerald-700 hover:bg-emerald-800 text-white font-bold"
              >
                <Plus className="w-3 h-3 mr-1" />
                Add Document
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            {getAuthorityDocs().length === 0 ? (
              <div className="p-4 bg-white rounded-lg border border-dashed border-slate-300 text-center text-xs text-slate-500">
                No authority documents specified yet. Click <strong>"Load Standard 8-Doc Authority Checklist"</strong> to add the standard 8 statutory documents.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {getAuthorityDocs().map((doc, idx) => (
                  <div key={idx} className="p-2 bg-white rounded-lg border border-slate-200 flex items-center gap-2 shadow-2xs">
                    <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <Input
                      value={typeof doc === 'string' ? doc : (doc?.name || '')}
                      onChange={(e) => updateAuthorityDoc(idx, e.target.value)}
                      placeholder="e.g. Passport bio-data page (colour scan)"
                      className="h-7 text-xs flex-1"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeAuthorityDoc(idx)}
                      className="h-7 w-7 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50 shrink-0"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* ── CARD 3: 10-YEAR EMPLOYMENT OUTLOOK & DEMOGRAPHICS (JSA & ABS) ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">📈</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                {country === 'CA' ? '3. 10-Year Employment Outlook & Demographics (Job Bank / ESDC)'
                : country === 'NZ' ? '3. 10-Year Employment Outlook & Demographics (MBIE Projections)'
                : '3. 10-Year Employment Outlook & Demographics (JSA Projections)'}
              </h3>
              <p className="text-xs text-slate-500">
                {country === 'CA' ? 'Configures Canadian workforce (2025), 2030/2035 projections, median age, FT/PT split, and female share % from Statistics Canada and Job Bank COPS.'
                : country === 'NZ' ? 'Configures New Zealand workforce (2025), 2030/2035 projections, median age, FT/PT split, and female share % from Stats NZ and MBIE.'
                : 'Configures Card 3: 2025 workforce, 2030/2035 projections, median age, FT/PT split, and female share %.'}
              </p>
            </div>
          </div>
          <Badge className="text-[10px] bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold">Public Projections Card</Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Future Growth Demand Rating
            </Label>
            <Select
              value={jsaD.future_growth || 'Strong Growth'}
              onValueChange={(v) => upJsaData('future_growth', v)}
            >
              <SelectTrigger className="h-9 text-xs font-bold"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Very Strong Growth">Very Strong Growth</SelectItem>
                <SelectItem value="Strong Growth">Strong Growth</SelectItem>
                <SelectItem value="Moderate Growth">Moderate Growth</SelectItem>
                <SelectItem value="Stable / Low Growth">Stable / Low Growth</SelectItem>
                <SelectItem value="Declining">Declining</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-[10px] text-slate-400">Pill in Outlook card header</span>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              10-Year Growth Rate % (2025–2035)
            </Label>
            <Input
              type="number"
              step="0.1"
              value={jsaD.growth_pct_2025_to_2035 ?? ''}
              onChange={(e) => upJsaData('growth_pct_2025_to_2035', e.target.value)}
              placeholder="e.g. 14.1"
              className="h-9 text-xs font-mono font-bold text-forest"
            />
            <span className="text-[10px] text-slate-400">e.g. +14.1% by 2035</span>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Workers in 2025 (National Workforce)
            </Label>
            <Input
              type="number"
              value={jsaD.employment_2025 || absM.employed_count || ''}
              onChange={(e) => {
                upJsaData('employment_2025', e.target.value);
                upLabourMarket('employed_count', e.target.value);
              }}
              placeholder="e.g. 63000"
              className="h-9 text-xs font-mono font-bold"
            />
            <span className="text-[10px] text-slate-400">Current national employed count</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Projected 2030 (5-Year Outlook)
            </Label>
            <Input
              type="number"
              value={jsaD.projected_employment_2030 || ''}
              onChange={(e) => upJsaData('projected_employment_2030', e.target.value)}
              placeholder="e.g. 67442"
              className="h-9 text-xs font-mono"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Projected 2035 (10-Year Outlook)
            </Label>
            <Input
              type="number"
              value={jsaD.projected_employment_2035 || ''}
              onChange={(e) => upJsaData('projected_employment_2035', e.target.value)}
              placeholder="e.g. 71883"
              className="h-9 text-xs font-mono text-burnt font-bold"
            />
          </div>
        </div>

        <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
            <Users className="w-4 h-4 text-slate-500" />
            <span>Worker Demographics (ABS Census Profile)</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Median Age (Years)
              </Label>
              <Input
                type="number"
                value={absM.median_age ?? ''}
                onChange={(e) => upLabourMarket('median_age', e.target.value)}
                placeholder="e.g. 50"
                className="h-8 text-xs font-mono bg-white"
              />
              <span className="text-[10px] text-slate-400">e.g. 50 years</span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Part-Time Share % (Workforce Split)
              </Label>
              <Input
                type="number"
                step="0.1"
                value={absM.part_time_share_pct ?? ''}
                onChange={(e) => upLabourMarket('part_time_share_pct', e.target.value)}
                placeholder="e.g. 15"
                className="h-8 text-xs font-mono bg-white"
              />
              <span className="text-[10px] text-slate-400">
                Shows: {absM.part_time_share_pct != null ? `${Math.round(100 - parseFloat(absM.part_time_share_pct || 0))}% FT (${Math.round(parseFloat(absM.part_time_share_pct || 0))}% part-time)` : '85% FT (15% part-time)'}
              </span>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Female Share %
              </Label>
              <Input
                type="number"
                step="0.1"
                value={absM.female_share_pct ?? ''}
                onChange={(e) => upLabourMarket('female_share_pct', e.target.value)}
                placeholder="e.g. 31"
                className="h-8 text-xs font-mono bg-white"
              />
              <span className="text-[10px] text-slate-400">e.g. 31% gender balance</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Full-Time Median Annual Salary (AUD)
            </Label>
            <Input
              type="number"
              placeholder="e.g. 180000"
              value={anzscoProf.median_salary_aud || absD.median_ft_annual_aud || ''}
              onChange={(e) => upAnzscoProfile('median_salary_aud', e.target.value)}
              className="h-8 text-xs font-bold text-amber-900 bg-amber-50/30 border-amber-200 font-mono"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Weekly Full-Time Earnings (AUD)
            </Label>
            <Input
              type="number"
              placeholder="e.g. 3460"
              value={absM.median_weekly_earnings_aud || absD.median_ft_weekly_earnings_aud || ''}
              onChange={(e) => upLabourMarket('median_weekly_earnings_aud', e.target.value)}
              className="h-8 text-xs font-mono"
            />
          </div>
        </div>
      </Card>

      {/* ── CARD 4: WHERE TO SETTLE (STRONGEST LABOUR MARKETS) ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-3">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">📍</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                4. Where to Settle (Strongest Labour Markets in {countryCfg.countryName})
              </h3>
              <p className="text-xs text-slate-500">Configures the "Where to Settle" green pills card on the public page.</p>
            </div>
          </div>
          <Badge className="text-[10px] bg-slate-100 text-slate-700 font-semibold">Public Settle Card</Badge>
        </div>

        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1">
            Custom Settlement Regions (One per line — leave blank to auto-calculate from labour statistics)
          </Label>
          <Textarea
            value={strongRegionsText}
            onChange={(e) => {
              const lines = e.target.value.split('\n').map((l) => l.trim()).filter(Boolean);
              setEdit({ ...edit, strong_regions: lines });
            }}
            rows={4}
            placeholder={
              country === 'CA'
                ? 'Toronto - Greater Area · ON\nVancouver - Lower Mainland · BC\nCalgary - Central · AB\nOttawa - National Capital · ON\nMontreal - Metropolitan · QC'
                : country === 'NZ'
                ? 'Auckland Central · AKL\nWellington Urban · WGN\nChristchurch · CAN\nHamilton · WKO\nTauranga · BOP'
                : 'Sydney - Sutherland · NSW\nSydney - Eastern Suburbs · NSW\nSydney - Northern Beaches · NSW\nWarrnambool and South West · VIC\nGold Coast · QLD'
            }
            className="text-xs font-mono leading-relaxed"
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Format: <code>Region Name · {country === 'CA' ? 'Province' : country === 'NZ' ? 'Region' : 'State'}</code>. When empty, the system automatically pulls the lowest-unemployment regions matching the occupation.
          </p>
        </div>
      </Card>

      {/* ── CARD 5: VISA PATHWAYS & SKILLED MIGRATION LISTS ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-5" data-testid="card-visa-pathways-editor">
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-800 flex items-center justify-center font-bold text-sm">
              🛂
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">5. {countryCfg.label}</h3>
              <p className="text-xs text-slate-500">Configures the "Visa subclasses you can apply under" cards on Public Atlas and Sales views: subclasses, streams, descriptions, max age, min points, experience, and filing fees.</p>
            </div>
          </div>
          <Badge className="text-[10px] bg-indigo-50 text-indigo-900 border-indigo-300 font-semibold">{countryCfg.countryName} Unified Pathways</Badge>
        </div>

        {/* 5A: Quick Eligibility Toggles & Lists */}
        <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-3">
          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1.5">
              Eligible Visa Pathways / Subclasses (Click to toggle ✓ / ✗ on public page)
            </Label>
            <div className="flex flex-wrap gap-2">
              {(countryCfg.subclasses || []).map((v) => {
                const eligible = isSubclassEligible(v.code);
                return (
                  <button
                    key={v.code}
                    type="button"
                    onClick={() => toggleVisaSubclass(v.code)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-bold transition flex items-center gap-1.5 ${
                      eligible
                        ? 'bg-emerald-50 text-emerald-900 border-emerald-300 shadow-xs hover:bg-emerald-100'
                        : 'bg-slate-100 text-slate-400 border-slate-200 line-through hover:bg-slate-200'
                    }`}
                  >
                    <span>{eligible ? '✓' : '✗'}</span>
                    <span>{country === 'AU' ? `Subclass ${v.code}` : v.code}</span>
                    <span className="text-[10px] font-normal text-slate-500">({v.name})</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1.5">
                Immigration / Migration Category Lists (Click to include in list pills)
              </Label>
              <div className="flex flex-wrap gap-2">
                {(countryCfg.lists || []).map((listName) => {
                  const active = (Array.isArray(edit.pathway_lists) ? edit.pathway_lists : [edit.pathway_list || (countryCfg.lists || [])[0]]).includes(listName);
                  return (
                    <button
                      key={listName}
                      type="button"
                      onClick={() => togglePathwayList(listName)}
                      className={`px-3 py-1 rounded-md border text-xs font-bold transition ${
                        active
                          ? 'bg-slate-900 text-white border-slate-900'
                          : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-100'
                      }`}
                    >
                      {listName}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Recommended Primary Visa / Pathway (Star badge)
              </Label>
              <Input
                value={typeof edit.recommended_visa_subclass === 'object' ? (edit.recommended_visa_subclass?.[country] || (countryCfg.subclasses || [])[0]?.code || '190') : (edit.recommended_visa_subclass || (countryCfg.subclasses || [])[0]?.code || '190')}
                onChange={(e) => setEdit({ ...edit, recommended_visa_subclass: e.target.value })}
                placeholder={country === 'CA' ? 'e.g. FSWP or CEC' : country === 'NZ' ? 'e.g. Green-T1 or SMC' : 'e.g. 190 or 189'}
                className="h-8 text-xs font-bold text-forest font-mono bg-white"
              />
              <span className="text-[10px] text-slate-400">Receives the gold star ⭐ chip</span>
            </div>
          </div>

          {/* SkillSelect Cutoff Scorecard & Round History */}
          <div className="p-4 rounded-xl border border-teal-200 bg-teal-50/50 space-y-3.5" data-testid="unified-invitation-rounds-card">
            <div className="flex items-center justify-between flex-wrap gap-2 border-b border-teal-200/70 pb-2.5">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-teal-800" />
                <span className="text-xs font-bold text-teal-950 block">DHA SkillSelect Invitation Cutoff Points &amp; Rounds History</span>
              </div>
              <div className="flex items-center gap-2">
                {syncMigroto && country === 'AU' && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={syncMigroto}
                    disabled={migrotoLoading}
                    className="h-7 text-xs bg-white text-teal-800 border-teal-300 hover:bg-teal-100 font-bold"
                    data-testid="unified-sync-migroto-btn"
                    title="Pull latest invitation cutoffs and round archives directly from Migroto live registry"
                  >
                    {migrotoLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCw className="h-3 w-3 mr-1 text-teal-700" />}
                    Sync from Migroto Live
                  </Button>
                )}
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleLoadDefaultRounds}
                  className="h-7 text-xs bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
                >
                  <Wand2 className="h-3 w-3 mr-1 text-teal-700" />Default Rounds
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleAddRound}
                  className="h-7 text-xs bg-teal-700 hover:bg-teal-800 text-white font-bold"
                >
                  <Plus className="h-3 w-3 mr-1" />Add Round
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div>
                <Label className="text-[11px] font-semibold text-teal-900 block mb-1">Subclass 189 Pass Mark</Label>
                <Input
                  type="number"
                  value={minPts.subclass_189 ?? ''}
                  onChange={(e) => upMinPoints('subclass_189', e.target.value)}
                  placeholder="e.g. 80"
                  className="h-8 text-xs font-mono font-bold bg-white"
                />
              </div>
              <div>
                <Label className="text-[11px] font-semibold text-teal-900 block mb-1">Subclass 190 Pass Mark</Label>
                <Input
                  type="number"
                  value={minPts.subclass_190 ?? ''}
                  onChange={(e) => upMinPoints('subclass_190', e.target.value)}
                  placeholder="e.g. 75"
                  className="h-8 text-xs font-mono font-bold bg-white"
                />
              </div>
              <div>
                <Label className="text-[11px] font-semibold text-teal-900 block mb-1">Subclass 491 Pass Mark</Label>
                <Input
                  type="number"
                  value={minPts.subclass_491 ?? ''}
                  onChange={(e) => upMinPoints('subclass_491', e.target.value)}
                  placeholder="e.g. 65"
                  className="h-8 text-xs font-mono font-bold bg-white"
                />
              </div>
              <div>
                <Label className="text-[11px] font-semibold text-teal-900 block mb-1">Program Year</Label>
                <Input
                  type="text"
                  value={minPts.as_of_program_year ?? '2025-26'}
                  onChange={(e) => upMinPoints('as_of_program_year', e.target.value)}
                  placeholder="e.g. 2025-26"
                  className="h-8 text-xs font-mono font-bold bg-white"
                />
              </div>
            </div>

            {/* Editable Rounds Table */}
            <div className="pt-2 border-t border-teal-200/60">
              <span className="text-[11px] font-bold text-teal-950 uppercase tracking-wider block mb-1.5">
                Invitation Rounds Records ({(edit.invitation_rounds || []).length})
              </span>
              {(!edit.invitation_rounds || edit.invitation_rounds.length === 0) ? (
                <div className="p-3 text-center bg-white rounded-lg border border-dashed border-teal-300 text-xs text-slate-500">
                  No custom round records stored yet. Click &quot;Sync from Migroto Live&quot; or &quot;Default Rounds&quot; to populate.
                </div>
              ) : (
                <div className="space-y-2">
                  {(edit.invitation_rounds || []).map((rnd, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-white p-2 rounded-lg border border-teal-200/80 shadow-2xs">
                      <div className="col-span-3">
                        <Label className="text-[10px] text-slate-500 block mb-0.5">Date</Label>
                        <Input
                          type="text"
                          value={rnd.date || ''}
                          onChange={(e) => handleUpdateRound(idx, 'date', e.target.value)}
                          placeholder="e.g. 2026-06-15"
                          className="h-7 text-xs font-mono bg-slate-50"
                        />
                      </div>
                      <div className="col-span-3">
                        <Label className="text-[10px] text-slate-500 block mb-0.5">Subclass</Label>
                        <Input
                          type="text"
                          value={rnd.subclass || ''}
                          onChange={(e) => handleUpdateRound(idx, 'subclass', e.target.value)}
                          placeholder="e.g. 189 or 190"
                          className="h-7 text-xs font-mono font-bold bg-slate-50"
                        />
                      </div>
                      <div className="col-span-2">
                        <Label className="text-[10px] text-slate-500 block mb-0.5">Cutoff Pts</Label>
                        <Input
                          type="number"
                          value={rnd.score ?? ''}
                          onChange={(e) => handleUpdateRound(idx, 'score', e.target.value)}
                          placeholder="80"
                          className="h-7 text-xs font-mono font-bold text-emerald-700 bg-slate-50"
                        />
                      </div>
                      <div className="col-span-3">
                        <Label className="text-[10px] text-slate-500 block mb-0.5">Total Invitations</Label>
                        <Input
                          type="number"
                          value={rnd.invitations ?? ''}
                          onChange={(e) => handleUpdateRound(idx, 'invitations', e.target.value)}
                          placeholder="120"
                          className="h-7 text-xs font-mono bg-slate-50"
                        />
                      </div>
                      <div className="col-span-1 flex justify-end pt-3.5">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveRound(idx)}
                          className="h-7 w-7 p-0 text-rose-500 hover:text-rose-700 hover:bg-rose-50"
                          title="Remove round"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 5B: Detailed Subclass Visa Cards & Requirements Editor */}
        <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Compass className="h-3.5 w-3.5 text-indigo-600" />
                Detailed Visa Pathway Subclasses &amp; Requirements
                <Badge className="ml-1.5 text-[10px] bg-indigo-100 text-indigo-900 border-indigo-300 font-mono">
                  {getVisaSubclassList().length} subclasses
                </Badge>
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Every visa card shown on Sales Tab 3 and Public Atlas is customizable here (Stream, description, max age, min points, experience, and fee).
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={loadStandardVisaPathwaysByCountry}
                className="h-7 text-xs bg-white text-slate-700 border-slate-300 hover:bg-indigo-50 hover:text-indigo-900"
              >
                <Wand2 className="w-3 h-3 mr-1 text-indigo-600" />
                Load Standard {countryCfg.countryName} Visa Pathways ({(countryCfg.subclasses || []).length})
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={addVisaSubclassItem}
                className="h-7 text-xs bg-indigo-700 hover:bg-indigo-800 text-white font-bold"
              >
                <Plus className="w-3 h-3 mr-1" />
                Add Subclass
              </Button>
            </div>
          </div>

          <div className="space-y-3">
            {getVisaSubclassList().length === 0 ? (
              <div className="p-4 bg-white rounded-lg border border-dashed border-slate-300 text-center text-xs text-slate-500">
                No visa subclass pathways configured yet. Click <strong>"Load Standard Australian Visa Pathways (7)"</strong> to auto-fill the standard 7 Australian visa streams (189, 186, 190, 482, 485, 491, 494).
              </div>
            ) : (
              getVisaSubclassList().map((v, idx) => {
                const subStr = String(v.visa_subclass || v.code || '');
                const isRec = typeof edit.recommended_visa_subclass === 'object'
                  ? edit.recommended_visa_subclass?.AU === subStr
                  : edit.recommended_visa_subclass === subStr;
                return (
                  <div key={idx} className={`p-4 rounded-xl border transition shadow-xs space-y-3 bg-white ${v.eligible !== false ? 'border-slate-200' : 'border-slate-200 opacity-60'}`}>
                    {/* Header bar of visa card */}
                    <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-100">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge className="bg-slate-900 text-white font-mono text-xs font-bold px-2.5 py-0.5">
                          Subclass {subStr || '—'}
                        </Badge>
                        <Badge variant="outline" className="text-[10px] font-bold bg-indigo-50 text-indigo-700 border-indigo-200">
                          {v.stream || v.pathway_type || 'Visa Stream'}
                        </Badge>
                        {isRec && (
                          <Badge className="bg-amber-100 text-amber-900 border-amber-300 text-[10px] font-bold">
                            ⭐ Recommended
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => updateVisaSubclassItem(idx, 'eligible', !v.eligible)}
                          className={`px-2.5 py-0.5 rounded text-[11px] font-bold border transition ${
                            v.eligible !== false
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                              : 'bg-slate-100 text-slate-500 border-slate-300 line-through'
                          }`}
                        >
                          {v.eligible !== false ? '✓ Eligible' : '✗ Inactive'}
                        </button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeVisaSubclassItem(idx)}
                          className="h-7 w-7 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>

                    {/* Subclass Code, Stream Name, Card Title */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Subclass Code *
                        </Label>
                        <Input
                          value={v.visa_subclass || v.code || ''}
                          onChange={(e) => updateVisaSubclassItem(idx, 'visa_subclass', e.target.value)}
                          placeholder="e.g. 189"
                          className="h-8 text-xs font-mono font-bold"
                        />
                      </div>
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Pathway Stream Name
                        </Label>
                        <Input
                          value={v.stream || v.pathway_type || ''}
                          onChange={(e) => {
                            updateVisaSubclassItem(idx, 'stream', e.target.value);
                            updateVisaSubclassItem(idx, 'pathway_type', e.target.value);
                          }}
                          placeholder="e.g. Skilled Independent (PR)"
                          className="h-8 text-xs font-semibold"
                        />
                      </div>
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Card Title
                        </Label>
                        <Input
                          value={v.name || (v.visa_subclass ? `Subclass ${v.visa_subclass}` : '')}
                          onChange={(e) => updateVisaSubclassItem(idx, 'name', e.target.value)}
                          placeholder="e.g. Subclass 189"
                          className="h-8 text-xs font-bold"
                        />
                      </div>
                    </div>

                    {/* Description */}
                    <div>
                      <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                        Pathway Description &amp; Scope
                      </Label>
                      <Input
                        value={v.description || v.notes || ''}
                        onChange={(e) => {
                          updateVisaSubclassItem(idx, 'description', e.target.value);
                          updateVisaSubclassItem(idx, 'notes', e.target.value);
                        }}
                        placeholder="e.g. Permanent residence for skilled workers not sponsored by employer/family/state."
                        className="h-8 text-xs"
                      />
                    </div>

                    {/* 4 Metric Boxes: Max Age, Min Points, Min Exp, Processing Time */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Max Age (yrs)
                        </Label>
                        <Input
                          type="number"
                          value={v.age_limit ?? 44}
                          onChange={(e) => updateVisaSubclassItem(idx, 'age_limit', e.target.value ? parseInt(e.target.value, 10) : '')}
                          placeholder="e.g. 44 or 99"
                          className="h-7 text-xs font-bold bg-white"
                        />
                      </div>
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Min Points (pts)
                        </Label>
                        <Input
                          type="number"
                          value={v.points_minimum ?? 65}
                          onChange={(e) => updateVisaSubclassItem(idx, 'points_minimum', e.target.value ? parseInt(e.target.value, 10) : '')}
                          placeholder="e.g. 65 or 0"
                          className="h-7 text-xs font-bold text-indigo-700 bg-white"
                        />
                      </div>
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Min Experience
                        </Label>
                        <Input
                          value={v.experience_required || v.experience_minimum_years || '1+ yr'}
                          onChange={(e) => {
                            updateVisaSubclassItem(idx, 'experience_required', e.target.value);
                            updateVisaSubclassItem(idx, 'experience_minimum_years', e.target.value);
                          }}
                          placeholder="e.g. 1+ yr or 3 yrs"
                          className="h-7 text-xs font-semibold bg-white"
                        />
                      </div>
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Processing
                        </Label>
                        <Input
                          value={v.processing_time_months || v.processing_time || '3–6 mo'}
                          onChange={(e) => {
                            updateVisaSubclassItem(idx, 'processing_time_months', e.target.value);
                            updateVisaSubclassItem(idx, 'processing_time', e.target.value);
                          }}
                          placeholder="e.g. 3–6 mo"
                          className="h-7 text-xs font-semibold bg-white"
                        />
                      </div>
                    </div>

                    {/* Department Filing Fee & List */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Department Filing Fee (AUD)
                        </Label>
                        <Input
                          value={v.fee_native || 'AUD $4,770'}
                          onChange={(e) => updateVisaSubclassItem(idx, 'fee_native', e.target.value)}
                          placeholder="e.g. AUD $4,770"
                          className="h-7 text-xs font-bold text-emerald-800"
                        />
                      </div>
                      <div>
                        <Label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">
                          Skilled List Designation
                        </Label>
                        <Input
                          value={v.list || 'MLTSSL'}
                          onChange={(e) => updateVisaSubclassItem(idx, 'list', e.target.value)}
                          placeholder="e.g. MLTSSL or CSOL"
                          className="h-7 text-xs font-semibold"
                        />
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </Card>

      {/* ── CARD 6: OFFICIAL RATINGS & DEMAND RATIONALE ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">⚖️</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                {country === 'CA' ? '6. ESDC & Job Bank Official Provincial Ratings & Demand Analysis'
                : country === 'NZ' ? '6. MBIE & INZ Official Regional Ratings & Demand Analysis'
                : '6. JSA Official Ratings & Demand Analysis'}
              </h3>
              <p className="text-xs text-slate-500">
                Configures the {regionsList.length}-{jurisdictionLabel.toLowerCase()} shortage status grid (S, R, NS) and "Why This Occupation Is In Demand" narrative.
              </p>
            </div>
          </div>
          <Badge className="text-[10px] bg-rose-50 text-rose-800 border-rose-200 font-semibold">
            {country === 'CA' ? 'Public ESDC Ratings' : country === 'NZ' ? 'Public MBIE Ratings' : 'Public JSA Ratings'}
          </Badge>
        </div>

        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1">
            National / Priority Shortage Status (Header Pill)
          </Label>
          <Input
            value={edit.national_shortage_status || ''}
            onChange={(e) => setEdit({ ...edit, national_shortage_status: e.target.value })}
            placeholder={country === 'CA' ? 'e.g. Category-Based Draw (STEM) or High National Demand' : country === 'NZ' ? 'e.g. Green List Tier 1 (Straight to Residence) or Regional Shortage' : 'e.g. Core Skills Occupation List (CSOL) or No National Shortage (NS)'}
            className="h-8 text-xs font-semibold"
          />
        </div>

        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1.5">
            {regionsList.length}-{jurisdictionLabel} Shortage Priority ({country === 'CA' ? 'S = In-Demand / PNP Priority, R = Regional Stream, NS = General Stream' : country === 'NZ' ? 'S = Green List Priority, R = Regional Shortage, NS = General AEWV' : 'S = Shortage, R = Regional Shortage, NS = No Metro Shortage'})
          </Label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {regionsList.map((st) => {
              const currentRating = (edit.state_ratings && edit.state_ratings[st.code])
                || (ste[st.code]?.rating)
                || 'NS';
              return (
                <div key={st.code} className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/70 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-900">{st.code}</span>
                    <span className="text-[10px] text-slate-400 block truncate max-w-[80px]">{st.name.split(' ')[0]}</span>
                  </div>
                  <div className="flex gap-1">
                    {['S', 'R', 'NS'].map((r) => {
                      const isSelected = currentRating === r;
                      return (
                        <button
                          key={r}
                          type="button"
                          onClick={() => upStateRating(st.code, r)}
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold transition ${
                            isSelected
                              ? (r === 'S' ? 'bg-rose-600 text-white' : r === 'R' ? 'bg-amber-600 text-white' : 'bg-slate-700 text-white')
                              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100'
                          }`}
                        >
                          {r}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1">
            Why This Occupation Is In Demand (Labour Intelligence &amp; Migration Analysis)
          </Label>
          <Textarea
            value={edit.demand_rationale || ''}
            onChange={(e) => setEdit({ ...edit, demand_rationale: e.target.value })}
            rows={4}
            placeholder={country === 'CA'
              ? 'e.g. Evaluated as in High Demand across Ontario, British Columbia, and Alberta under category-based Express Entry draws and Provincial Nominee Programs...'
              : country === 'NZ'
                ? 'e.g. Listed on Immigration New Zealand\'s Green List Tier 1 eligible for immediate residence under the Straight to Residence pathway...'
                : 'e.g. Evaluated as No National Shortage (NS) on the Jobs and Skills Australia (JSA) Skills Priority List across all Australian states and territories. Eligible for skilled migration under the Short-term Skilled Occupation List (MLTSSL) and Core Skills streams subject to individual state nomination allocation quotas and employer sponsorship.'}
            className="text-xs leading-relaxed"
          />
          <span className="text-[10px] text-slate-400">Displayed in the highlighted green labour intelligence banner on the public page</span>
        </div>
      </Card>

      {/* ── CARD 7: OPPORTUNITY MAP (HIRING DISTRIBUTION) ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-3">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">🗺️</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                {country === 'CA' ? '7. Provincial Opportunity Map (Canadian Hiring Distribution)'
                : country === 'NZ' ? '7. Regional Opportunity Map (New Zealand Hiring Distribution)'
                : '7. State Opportunity Map (Hiring Distribution)'}
              </h3>
              <p className="text-xs text-slate-500">Configures the {regionsList.length} {jurisdictionLabel.toLowerCase()} cards showing national employment share percentages.</p>
            </div>
          </div>
          <Badge className={`text-[10px] font-mono font-bold ${Math.round(totalStateShare) === 100 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
            Sum: {totalStateShare.toFixed(1)}%
          </Badge>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {regionsList.map((st) => (
            <div key={st.code} className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/70">
              <Label className="text-[11px] font-bold text-slate-700 block mb-1">
                {st.code} ({st.name.split(' ')[0]}) %
              </Label>
              <Input
                type="number"
                step="0.1"
                value={stDist[st.code] ?? ''}
                onChange={(e) => upStateDist(st.code, e.target.value)}
                placeholder="e.g. 25.0"
                className="h-8 text-xs font-mono font-bold bg-white"
              />
            </div>
          ))}
        </div>
      </Card>

      {/* ── CARD 8: TOP EMPLOYING INDUSTRIES ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-3">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">🏭</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">8. Top Employing Industries</h3>
              <p className="text-xs text-slate-500">Ranked list of top employing industries shown in the "Where workers go" card.</p>
            </div>
          </div>
          <Badge className="text-[10px] bg-slate-100 text-slate-700 font-semibold">Public Industry Card</Badge>
        </div>

        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1">
            Top 5 Industries (One per line — ranked by share)
          </Label>
          <Textarea
            value={Array.isArray(edit.industries_ranked) ? edit.industries_ranked.join('\n') : (edit.industries_ranked || '')}
            onChange={(e) => setEdit({ ...edit, industries_ranked: e.target.value.split('\n').filter(Boolean) })}
            rows={5}
            placeholder={'Professional, Scientific and Technical Services\nFinancial and Insurance Services\nPublic Administration and Safety\nManufacturing'}
            className="text-xs font-mono leading-relaxed"
          />
        </div>
      </Card>

      {/* ── CARD 9: FREQUENTLY ASKED QUESTIONS (FAQ) ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">❓</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">9. Frequently Asked Questions (FAQ Editor)</h3>
              <p className="text-xs text-slate-500">Client-facing questions and answers shown in the accordion FAQ card.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={generateDefaultFaqs}
              className="h-7 text-xs border-slate-300 text-slate-700 hover:bg-slate-100"
            >
              <Sparkles className="w-3 h-3 mr-1 text-purple-600" /> Pre-fill Standard FAQs
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={addFaqItem}
              className="h-7 text-xs bg-slate-900 text-white hover:bg-slate-800"
            >
              <Plus className="w-3 h-3 mr-1" /> Add FAQ
            </Button>
          </div>
        </div>

        {(!edit.faqs || edit.faqs.length === 0) ? (
          <div className="p-6 text-center border border-dashed rounded-lg bg-slate-50 space-y-2">
            <p className="text-xs text-slate-500">No custom FAQs defined yet. Automatic system FAQs are currently generated for this occupation.</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={generateDefaultFaqs}
              className="text-xs font-semibold"
            >
              Pre-fill 4 Standard FAQs to customize
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {edit.faqs.map((f, idx) => (
              <div key={idx} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/70 space-y-2 relative">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700">FAQ #{idx + 1}</span>
                  <button
                    type="button"
                    onClick={() => removeFaqItem(idx)}
                    className="text-slate-400 hover:text-rose-600 transition"
                    title="Remove question"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <Input
                  value={f.question || f.q || ''}
                  onChange={(e) => updateFaqItem(idx, 'question', e.target.value)}
                  placeholder="e.g. How long does ANZSCO 111111 assessment take?"
                  className="h-8 text-xs font-semibold bg-white"
                />
                <Textarea
                  value={f.answer || f.a || ''}
                  onChange={(e) => updateFaqItem(idx, 'answer', e.target.value)}
                  rows={2}
                  placeholder="Comprehensive answer explaining requirements, timelines, and LEAMSS guidance..."
                  className="text-xs leading-relaxed bg-white"
                />
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── CARD 10: 8-STATE / PROVINCE / REGIONAL NOMINATION RADAR ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">🌐</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                10. {country === 'CA' ? 'Canadian Provincial Nominee (PNP) Radar' : country === 'NZ' ? 'New Zealand Regional Allocation Radar' : '8-State Australian Nomination Radar (Program Streams)'}
              </h3>
              <p className="text-xs text-slate-500">
                {country === 'CA'
                  ? 'Configures provincial nominee streams (OINP, BC PNP, AAIP), tech/in-demand draws, target cutoffs and offshore availability.'
                  : country === 'NZ'
                  ? 'Configures New Zealand regional demand statuses, accredited employer quotas, and regional bonus point availability.'
                  : 'Configures individual state migration streams, 190/491 status, offshore eligibility and badge text.'}
              </p>
            </div>
          </div>
          <Badge className="text-[10px] bg-slate-100 text-slate-700 font-semibold">
            {country === 'CA' ? 'Provincial Radar (9)' : country === 'NZ' ? 'Regional Radar (8)' : 'State Radar (8)'}
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {(country === 'CA' ? CA_PROVINCES : country === 'NZ' ? NZ_REGIONS : AU_STATES).map((st) => {
            const s = ste[st.code] || {};
            const stStatus = s.status || (s.rating === 'S' ? 'open' : s.rating === 'R' ? 'conditional' : s.eligible_190 !== false ? 'open' : 'conditional');
            const stSubclass = s.subclass || (country === 'CA' ? 'Express Entry PNP' : country === 'NZ' ? 'Accredited Employer' : (s.eligible_190 && s.eligible_491 ? '190 & 491' : s.eligible_190 ? '190 Nominated' : '491 Regional'));
            const stBadge = s.badge || (country === 'CA' ? (stStatus === 'open' ? 'Targeted Tech / In Demand' : 'General Draw') : country === 'NZ' ? (stStatus === 'open' ? 'Regional Shortage' : 'Standard Quota') : (stStatus === 'open' ? 'Priority Open' : stStatus === 'conditional' ? '491 Regional Only' : 'Closed / Restricted'));

            return (
              <div key={st.code} className="p-3 rounded-lg border border-slate-200 bg-slate-50/60 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-slate-900">{st.code} — {st.name}</span>
                  <span className={`w-2.5 h-2.5 rounded-full ${stStatus === 'open' ? 'bg-emerald-500' : stStatus === 'conditional' ? 'bg-amber-500' : 'bg-rose-500'}`} />
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500">Stream Status</Label>
                  <Select value={stStatus} onValueChange={(v) => upState(st.code, 'status', v)}>
                    <SelectTrigger className="h-7 text-xs bg-white mt-0.5"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">🟢 Open (Active)</SelectItem>
                      <SelectItem value="conditional">🟡 Conditional / Regional</SelectItem>
                      <SelectItem value="closed">🔴 Closed / Restricted</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500">Badge Text</Label>
                  <Input
                    value={stBadge}
                    onChange={(e) => upState(st.code, 'badge', e.target.value)}
                    placeholder={country === 'CA' ? 'e.g. In-Demand Stream' : country === 'NZ' ? 'e.g. Regional Priority' : 'e.g. Priority Open'}
                    className="h-7 text-xs bg-white mt-0.5"
                  />
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500">{country === 'CA' ? 'Nomination Route' : country === 'NZ' ? 'Pathway Route' : 'Subclass Route'}</Label>
                  <Input
                    value={stSubclass}
                    onChange={(e) => upState(st.code, 'subclass', e.target.value)}
                    placeholder={country === 'CA' ? 'e.g. Express Entry PNP' : country === 'NZ' ? 'e.g. Accredited Employer' : 'e.g. 190 Nominated'}
                    className="h-7 text-xs bg-white mt-0.5"
                  />
                </div>

                <label className="flex items-center gap-1.5 text-[10px] text-slate-700 cursor-pointer pt-0.5">
                  <input
                    type="checkbox"
                    checked={s.offshore ?? true}
                    onChange={(e) => upState(st.code, 'offshore', e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span>{country === 'CA' ? 'Out-of-Province / Foreign' : country === 'NZ' ? 'Offshore Candidates' : 'Offshore Eligible'}</span>
                </label>
              </div>
            );
          })}
        </div>
      </Card>

      {/* ── CARD 11: COUNTRY-SPECIFIC CLASSIFICATION & MIGRATION RULES ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-base">{country === 'CA' ? '🇨🇦' : country === 'NZ' ? '🇳🇿' : '🇦🇺 🇨🇦 🇳🇿'}</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                {country === 'CA'
                  ? '11. Canada Express Entry, Category-Based Draws & Provincial Nominee Streams'
                  : country === 'NZ'
                  ? '11. New Zealand Green List, AEWV & Skilled Migrant Category (SMC)'
                  : '11. Cross-Country Migration Equivalence (AU ↔ CA ↔ NZ)'}
              </h3>
              <p className="text-xs text-slate-500">
                {country === 'CA'
                  ? 'Configures Canadian TEER, Express Entry eligibility, category-based selection targets, and provincial streams.'
                  : country === 'NZ'
                  ? 'Configures New Zealand Green List tiers, AEWV occupational bands, and SMC 6-point criteria.'
                  : 'Configures cross-country occupation mappings to Canadian NOC and New Zealand ANZSCO.'}
              </p>
            </div>
          </div>
          <Badge className="text-[10px] bg-indigo-50 text-indigo-800 border-indigo-200">
            {country === 'CA' ? 'Canada IRCC Rules' : country === 'NZ' ? 'New Zealand INZ Rules' : 'Cross-Country Equivalence'}
          </Badge>
        </div>

        {country === 'CA' ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50/60">
                <p className="text-xs font-bold text-slate-800">🇨🇦 NOC 2021 &amp; Express Entry Programs</p>
                <div>
                  <Label className="text-[11px] text-slate-600 block mb-1">TEER Category (0–5)</Label>
                  <Select
                    value={edit.teer_category !== '' && edit.teer_category != null ? String(edit.teer_category) : '1'}
                    onValueChange={(v) => setEdit({ ...edit, teer_category: v })}
                  >
                    <SelectTrigger className="h-8 text-xs bg-white"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">TEER 0 — Executive &amp; Management Occupations</SelectItem>
                      <SelectItem value="1">TEER 1 — University Degree Occupations (Bachelor+)</SelectItem>
                      <SelectItem value="2">TEER 2 — College Diploma (2–3 yrs) or Apprenticeship</SelectItem>
                      <SelectItem value="3">TEER 3 — College Diploma (&lt;2 yrs) or On-the-job training</SelectItem>
                      <SelectItem value="4">TEER 4 — Secondary School Occupations</SelectItem>
                      <SelectItem value="5">TEER 5 — No formal education requirements</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex gap-4 pt-1">
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                    <input type="checkbox" checked={ee.fswp_eligible !== false} onChange={(e) => upEe('fswp_eligible', e.target.checked)} className="rounded text-emerald-600" />
                    <span className="font-semibold">FSWP Eligible</span>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                    <input type="checkbox" checked={ee.cec_eligible !== false} onChange={(e) => upEe('cec_eligible', e.target.checked)} className="rounded text-emerald-600" />
                    <span className="font-semibold">CEC Eligible</span>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                    <input type="checkbox" checked={Boolean(ee.fstp_eligible)} onChange={(e) => upEe('fstp_eligible', e.target.checked)} className="rounded text-emerald-600" />
                    <span className="font-semibold">FSTP Eligible</span>
                  </label>
                </div>
              </div>

              <div className="space-y-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50/60">
                <p className="text-xs font-bold text-slate-800">🎯 Category-Based Draw Selection (Targeted Pools)</p>
                <div>
                  <Label className="text-[11px] text-slate-600 block mb-1">Target Category Draw Priority</Label>
                  <Select
                    value={edit.ee_priority || 'fswp_cec'}
                    onValueChange={(v) => setEdit({ ...edit, ee_priority: v })}
                  >
                    <SelectTrigger className="h-8 text-xs bg-white"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fswp_cec">Category-Based Selection Eligible</SelectItem>
                      <SelectItem value="stem">🔬 STEM Category (Science, Tech, Engineering, Math)</SelectItem>
                      <SelectItem value="healthcare">🩺 Healthcare Occupations Category</SelectItem>
                      <SelectItem value="trades">🔨 Trade Occupations Category</SelectItem>
                      <SelectItem value="transport">🚚 Transport Occupations Category</SelectItem>
                      <SelectItem value="agriculture">🌾 Agriculture &amp; Agri-Food Category</SelectItem>
                      <SelectItem value="french">⚜️ French-Language Proficiency Category</SelectItem>
                      <SelectItem value="general">🌐 General Express Entry (Non-Category)</SelectItem>
                    </SelectContent>
                  </Select>
                  <span className="text-[10px] text-slate-400 mt-1 block">Lowers CRS cutoff by 60–120 points</span>
                </div>
                <div>
                  <Label className="text-[11px] text-slate-600 block mb-1">Provincial Nominee (PNP) Priority Note</Label>
                  <Input
                    value={edit.pnp_notes || ''}
                    onChange={(e) => setEdit({ ...edit, pnp_notes: e.target.value })}
                    placeholder="e.g. Priority on Ontario OINP Tech Draw, BC PNP Tech, and Alberta AAIP"
                    className="h-8 text-xs bg-white"
                  />
                </div>
              </div>
            </div>
          </div>
        ) : country === 'NZ' ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50/60">
                <p className="text-xs font-bold text-slate-800">🇳🇿 New Zealand Green List Schedule</p>
                <div>
                  <Label className="text-[11px] text-slate-600 block mb-1">Green List Tier</Label>
                  <Select
                    value={edit.nz_green_list_tier !== '' && edit.nz_green_list_tier != null ? String(edit.nz_green_list_tier) : '0'}
                    onValueChange={(v) => setEdit({ ...edit, nz_green_list_tier: v === '0' ? null : v })}
                  >
                    <SelectTrigger className="h-8 text-xs bg-white"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">Not on Green List (Standard AEWV &amp; SMC)</SelectItem>
                      <SelectItem value="1">Tier 1 — Straight to Residence (Immediate Fast-Track)</SelectItem>
                      <SelectItem value="2">Tier 2 — Work to Residence (Eligible after 24 mo)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer pt-1">
                  <input type="checkbox" checked={smc.green_list_auto_pass !== false} onChange={(e) => upSmc('green_list_auto_pass', e.target.checked)} className="rounded text-emerald-600" />
                  <span className="font-semibold">SMC Green List 6-Point Auto-Pass</span>
                </label>
              </div>

              <div className="space-y-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50/60">
                <p className="text-xs font-bold text-slate-800">📋 AEWV &amp; Skilled Migrant (SMC) Criteria</p>
                <div>
                  <Label className="text-[11px] text-slate-600 block mb-1">AEWV Occupational Band</Label>
                  <Select
                    value={aewv.occupational_band || 'Core Skills'}
                    onValueChange={(v) => upAewv('occupational_band', v)}
                  >
                    <SelectTrigger className="h-8 text-xs bg-white"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Tier 1 High Skilled">Tier 1 High Skilled (Median Wage +)</SelectItem>
                      <SelectItem value="Core Skills">Core Skills (ANZSCO Skill Level 1-3)</SelectItem>
                      <SelectItem value="Sector Agreement">Sector Agreement (Care / Tourism / Transport)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-[11px] text-slate-600 block mb-1">Median Wage Requirement (NZD/hr)</Label>
                  <Input
                    value={aewv.median_wage_hourly || 'NZD $31.61/hr'}
                    onChange={(e) => upAewv('median_wage_hourly', e.target.value)}
                    placeholder="e.g. NZD $31.61/hr or 1.5x Median ($47.41/hr)"
                    className="h-8 text-xs bg-white"
                  />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50/60">
              <p className="text-xs font-bold text-slate-800">🇨🇦 Canadian NOC Equivalent</p>
              <div>
                <Label className="text-[11px] text-slate-600 block mb-1">Equivalent Canadian NOC 2021 Code</Label>
                <Input
                  value={edit.noc_code || ''}
                  onChange={(e) => setEdit({ ...edit, noc_code: e.target.value })}
                  placeholder="e.g. 21231"
                  className="h-8 text-xs bg-white"
                />
                <span className="text-[10px] text-slate-400 mt-1 block">Cross-links to Canadian Migration Atlas</span>
              </div>
              <div>
                <Label className="text-[11px] text-slate-600 block mb-1">NOC TEER Category</Label>
                <Select
                  value={edit.teer_category !== '' && edit.teer_category != null ? String(edit.teer_category) : '1'}
                  onValueChange={(v) => setEdit({ ...edit, teer_category: v })}
                >
                  <SelectTrigger className="h-8 text-xs bg-white"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">TEER 0 — Management</SelectItem>
                    <SelectItem value="1">TEER 1 — University Degree (Bachelor+)</SelectItem>
                    <SelectItem value="2">TEER 2 — College Diploma (2–3 yrs)</SelectItem>
                    <SelectItem value="3">TEER 3 — College Diploma (&lt;2 yrs)</SelectItem>
                    <SelectItem value="4">TEER 4 — Secondary School</SelectItem>
                    <SelectItem value="5">TEER 5 — No formal education</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3 p-3.5 rounded-lg border border-slate-200 bg-slate-50/60">
              <p className="text-xs font-bold text-slate-800">🇳🇿 New Zealand ANZSCO Equivalent</p>
              <div>
                <Label className="text-[11px] text-slate-600 block mb-1">NZ ANZSCO Code (Usually identical to AU)</Label>
                <Input
                  value={edit.nz_code || item.code}
                  onChange={(e) => setEdit({ ...edit, nz_code: e.target.value })}
                  placeholder="e.g. 261313"
                  className="h-8 text-xs bg-white"
                />
                <span className="text-[10px] text-slate-400 mt-1 block">Cross-links to New Zealand Migration Atlas</span>
              </div>
              <div>
                <Label className="text-[11px] text-slate-600 block mb-1">Green List Tier Status in New Zealand</Label>
                <Select
                  value={edit.nz_green_list_tier !== '' && edit.nz_green_list_tier != null ? String(edit.nz_green_list_tier) : '0'}
                  onValueChange={(v) => setEdit({ ...edit, nz_green_list_tier: v === '0' ? null : v })}
                >
                  <SelectTrigger className="h-8 text-xs bg-white"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Not on Green List</SelectItem>
                    <SelectItem value="1">Tier 1 — Straight to Residence</SelectItem>
                    <SelectItem value="2">Tier 2 — Work to Residence (2 yrs)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* ── CARD 12: GOOGLE SEARCH & SEO META ATTRIBUTES ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-200 text-teal-700 flex items-center justify-center font-bold text-sm">
              🔍
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-slate-900">12. Search Engine Optimization (SEO) &amp; Social Meta Attributes</h3>
                <Badge className="text-[10px] bg-teal-50 text-teal-700 border-teal-200 font-semibold">SEO Suite</Badge>
                <Badge className="text-[10px] bg-slate-100 text-slate-600 font-mono font-medium">{country}</Badge>
              </div>
              <p className="text-xs text-slate-500">Configure search snippets (Google SERP), Open Graph social tags, robots indexing directives, and Schema.org rich markup.</p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleAutoGenerateSeo}
            className="h-8 text-xs font-semibold text-teal-700 border-teal-300 hover:bg-teal-50 flex items-center gap-1.5 shrink-0"
            title="Auto-generate optimized meta tags, keywords, and description based on current occupation data"
          >
            <Sparkles className="w-3.5 h-3.5 text-teal-600" />
            Auto-Generate SEO
          </Button>
        </div>

        {/* Sub-tabs Selector */}
        <div className="flex items-center gap-1.5 border-b pb-2 text-xs font-medium overflow-x-auto">
          <button
            type="button"
            onClick={() => setSeoTab('serp')}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
              seoTab === 'serp'
                ? 'bg-teal-700 text-white font-semibold shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Globe2 className="w-3.5 h-3.5" />
            Google SERP Meta
          </button>
          <button
            type="button"
            onClick={() => setSeoTab('social')}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
              seoTab === 'social'
                ? 'bg-teal-700 text-white font-semibold shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            Social Open Graph &amp; X
          </button>
          <button
            type="button"
            onClick={() => setSeoTab('schema')}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-colors ${
              seoTab === 'schema'
                ? 'bg-teal-700 text-white font-semibold shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            Schema.org JSON-LD
          </button>
        </div>

        {/* ── TAB 1: GOOGLE SERP META ── */}
        {seoTab === 'serp' && (
          <div className="space-y-4 pt-1">
            {/* Title */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  Page Title (Google SERP Title Tag)
                  <span className="text-[10px] text-slate-400 font-normal">(`&lt;title&gt;` tag)</span>
                </Label>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    (seo.meta_title || '').length > 60
                      ? 'bg-rose-100 text-rose-700 font-bold'
                      : (seo.meta_title || '').length >= 45
                        ? 'bg-emerald-100 text-emerald-700 font-bold'
                        : (seo.meta_title || '').length > 0
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-500'
                  }`}>
                    {(seo.meta_title || '').length} / 60 chars {
                      (seo.meta_title || '').length > 60
                        ? '(May Truncate)'
                        : (seo.meta_title || '').length >= 45
                          ? '(Optimal)'
                          : (seo.meta_title || '').length > 0
                            ? '(Short)'
                            : '(Default)'
                    }
                  </span>
                  {seo.meta_title && (
                    <button
                      type="button"
                      onClick={() => handleCopySeoText('title', seo.meta_title)}
                      className="text-slate-400 hover:text-slate-700 text-xs p-0.5"
                      title="Copy page title"
                    >
                      {copiedKey === 'title' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>
              </div>
              <Input
                value={seo.meta_title || ''}
                onChange={(e) => upSeo('meta_title', e.target.value)}
                placeholder={`e.g. ${edit.title || item.title} (${item.code}) — ${country === 'CA' ? 'Canada NOC' : country === 'NZ' ? 'New Zealand ANZSCO' : 'Australia ANZSCO'} Migration Guide | LEAMSS`}
                className="h-8 text-xs font-medium"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Leave blank to automatically use standard branding: <span className="font-mono text-slate-600 text-[10px]">{`"${edit.title || item.title} (${item.code}) — ${country === 'CA' ? 'Canada NOC 2021' : country === 'NZ' ? 'New Zealand ANZSCO' : 'Australia ANZSCO'} Migration Guide | LEAMSS"`}</span>
              </p>
            </div>

            {/* Description */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  Meta Description
                  <span className="text-[10px] text-slate-400 font-normal">(`&lt;meta name="description"&gt;`)</span>
                </Label>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    (seo.meta_description || '').length > 160
                      ? 'bg-rose-100 text-rose-700 font-bold'
                      : (seo.meta_description || '').length >= 130
                        ? 'bg-emerald-100 text-emerald-700 font-bold'
                        : (seo.meta_description || '').length > 0
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-500'
                  }`}>
                    {(seo.meta_description || '').length} / 160 chars {
                      (seo.meta_description || '').length > 160
                        ? '(May Truncate)'
                        : (seo.meta_description || '').length >= 130
                          ? '(Optimal)'
                          : (seo.meta_description || '').length > 0
                            ? '(Short)'
                            : '(Dynamic Auto-Generated)'
                    }
                  </span>
                  {seo.meta_description && (
                    <button
                      type="button"
                      onClick={() => handleCopySeoText('desc', seo.meta_description)}
                      className="text-slate-400 hover:text-slate-700 text-xs p-0.5"
                      title="Copy meta description"
                    >
                      {copiedKey === 'desc' ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>
              </div>
              <Textarea
                value={seo.meta_description || ''}
                onChange={(e) => upSeo('meta_description', e.target.value)}
                placeholder={`e.g. Comprehensive guide for migrating to ${country === 'CA' ? 'Canada' : country === 'NZ' ? 'New Zealand' : 'Australia'} as a ${edit.title || item.title} (${item.code}). Check skill assessment criteria, points cutoffs, top regions, and visa pathways.`}
                className="text-xs min-h-[75px] leading-relaxed"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                A compelling, 130–160 character description increases Google click-through rates (CTR).
              </p>
            </div>

            {/* Focus Keyword & Robots */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="text-xs font-semibold text-slate-700">Primary Focus Keyword</Label>
                  {seo.focus_keyword && (
                    <div className="flex items-center gap-1.5 text-[10px]">
                      <span className={`px-1.5 py-0.2 rounded font-medium ${
                        (seo.meta_title || '').toLowerCase().includes(seo.focus_keyword.toLowerCase())
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-500'
                      }`}>
                        Title: {(seo.meta_title || '').toLowerCase().includes(seo.focus_keyword.toLowerCase()) ? '✓' : '—'}
                      </span>
                      <span className={`px-1.5 py-0.2 rounded font-medium ${
                        (seo.meta_description || '').toLowerCase().includes(seo.focus_keyword.toLowerCase())
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-slate-100 text-slate-500'
                      }`}>
                        Desc: {(seo.meta_description || '').toLowerCase().includes(seo.focus_keyword.toLowerCase()) ? '✓' : '—'}
                      </span>
                    </div>
                  )}
                </div>
                <Input
                  value={seo.focus_keyword || ''}
                  onChange={(e) => upSeo('focus_keyword', e.target.value)}
                  placeholder={`e.g. ${edit.title || item.title} ${country === 'CA' ? 'Canada PR' : country === 'NZ' ? 'New Zealand PR' : 'Australia PR'}`}
                  className="h-8 text-xs"
                />
                <p className="text-[11px] text-slate-500 mt-1">Core keyword this page is optimized to rank for on organic search.</p>
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 block mb-1">
                  Search Engine Indexing Directive (`meta name="robots"`)
                </Label>
                <Select
                  value={seo.meta_robots || 'index, follow, max-image-preview:large, max-snippet:-1'}
                  onValueChange={(val) => upSeo('meta_robots', val)}
                >
                  <SelectTrigger className="h-8 text-xs bg-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="index, follow, max-image-preview:large, max-snippet:-1">
                      index, follow (Standard — Full Search Engine Visibility)
                    </SelectItem>
                    <SelectItem value="noindex, follow">
                      noindex, follow (Hide from SERP, follow links)
                    </SelectItem>
                    <SelectItem value="index, nofollow">
                      index, nofollow (Index page, do not follow internal links)
                    </SelectItem>
                    <SelectItem value="noindex, nofollow">
                      noindex, nofollow (Exclude entirely from search engines)
                    </SelectItem>
                    <SelectItem value="noarchive, nosnippet">
                      noarchive, nosnippet (Index without caching or snippets)
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-slate-500 mt-1">Controls how Google, Bing, and other crawlers index this specific page.</p>
              </div>
            </div>

            {/* Target Keywords (Comma-separated) */}
            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Target Keywords &amp; LSI Terms (Comma-Separated)
              </Label>
              <Textarea
                value={seo.keywords || ''}
                onChange={(e) => upSeo('keywords', e.target.value)}
                placeholder={`e.g. ${edit.title || item.title}, ${item.code}, ${country === 'CA' ? 'Canada NOC' : country === 'NZ' ? 'New Zealand ANZSCO' : 'Australia ANZSCO'}, migrate to ${country}, PR points cutoff, skill assessment`}
                className="text-xs min-h-[55px]"
              />
              <p className="text-[11px] text-slate-500 mt-1">Secondary and long-tail organic search keywords stored in `&lt;meta name="keywords"&gt;`.</p>
            </div>

            {/* Canonical URL */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  Canonical URL Override
                  <span className="text-[10px] text-slate-400 font-normal">(`&lt;link rel="canonical"&gt;`)</span>
                </Label>
                {seo.canonical_url && (
                  <a
                    href={seo.canonical_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-teal-600 hover:text-teal-800 text-[11px] flex items-center gap-1"
                  >
                    Test Link <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
              <Input
                value={seo.canonical_url || ''}
                onChange={(e) => upSeo('canonical_url', e.target.value)}
                placeholder={`https://leamss.com/atlas/${(country || 'au').toLowerCase()}/${item.code}`}
                className="h-8 text-xs font-mono"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Leave blank to automatically default to <span className="font-mono text-slate-600 text-[10px]">{`https://leamss.com/atlas/${(country || 'au').toLowerCase()}/${item.code}`}</span>.
              </p>
            </div>
          </div>
        )}

        {/* ── TAB 2: SOCIAL OPEN GRAPH & X ── */}
        {seoTab === 'social' && (
          <div className="space-y-4 pt-1">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-600">
              Open Graph tags power social cards when links are shared on <strong>LinkedIn, WhatsApp, Facebook, iMessage, and Twitter/X</strong>.
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label className="text-xs font-semibold text-slate-700 block mb-1">
                  Open Graph Title (`og:title`)
                </Label>
                <Input
                  value={seo.og_title || ''}
                  onChange={(e) => upSeo('og_title', e.target.value)}
                  placeholder={seo.meta_title || `${edit.title || item.title} (${item.code}) — Migration Guide | LEAMSS`}
                  className="h-8 text-xs"
                />
                <p className="text-[11px] text-slate-500 mt-1">Defaults to Page Title if left empty.</p>
              </div>

              <div>
                <Label className="text-xs font-semibold text-slate-700 block mb-1">
                  Target Locale (`og:locale`)
                </Label>
                <Select
                  value={seo.og_locale || (country === 'AU' ? 'en_AU' : country === 'CA' ? 'en_CA' : country === 'NZ' ? 'en_NZ' : 'en_IN')}
                  onValueChange={(val) => upSeo('og_locale', val)}
                >
                  <SelectTrigger className="h-8 text-xs bg-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en_AU">en_AU (English — Australia)</SelectItem>
                    <SelectItem value="en_CA">en_CA (English — Canada)</SelectItem>
                    <SelectItem value="en_NZ">en_NZ (English — New Zealand)</SelectItem>
                    <SelectItem value="en_IN">en_IN (English — India / Global)</SelectItem>
                    <SelectItem value="en_US">en_US (English — United States)</SelectItem>
                    <SelectItem value="en_GB">en_GB (English — United Kingdom)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-slate-500 mt-1">Locale identifier for geographic search indexing.</p>
              </div>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Open Graph Description (`og:description`)
              </Label>
              <Textarea
                value={seo.og_description || ''}
                onChange={(e) => upSeo('og_description', e.target.value)}
                placeholder={seo.meta_description || `Complete guide to migrating to ${country === 'CA' ? 'Canada' : country === 'NZ' ? 'New Zealand' : 'Australia'} as a ${edit.title || item.title}. Check points, eligibility, and assessment criteria.`}
                className="text-xs min-h-[60px]"
              />
              <p className="text-[11px] text-slate-500 mt-1">Defaults to Meta Description if left empty.</p>
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Social Card Banner Image URL (`og:image`)
              </Label>
              <div className="flex gap-2">
                <Input
                  value={seo.og_image || ''}
                  onChange={(e) => upSeo('og_image', e.target.value)}
                  placeholder="https://leamss.com/leamss-logo.png"
                  className="h-8 text-xs font-mono flex-1"
                />
                {seo.og_image && (
                  <a
                    href={seo.og_image}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 rounded border border-slate-300 flex items-center justify-center text-xs font-medium text-slate-700"
                    title="Preview image"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">Recommended size: 1200 × 630 pixels (PNG/JPEG) for crisp rendering on LinkedIn &amp; Facebook.</p>
            </div>

            {/* Twitter Specific Card Options */}
            <div className="border-t pt-3 space-y-3">
              <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <span>𝕏</span> Twitter / X Card Specification
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-semibold text-slate-700 block mb-1">
                    Card Format (`twitter:card`)
                  </Label>
                  <Select
                    value={seo.twitter_card || 'summary_large_image'}
                    onValueChange={(val) => upSeo('twitter_card', val)}
                  >
                    <SelectTrigger className="h-8 text-xs bg-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="summary_large_image">summary_large_image (Large Hero Card — Recommended)</SelectItem>
                      <SelectItem value="summary">summary (Compact Square Thumbnail)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs font-semibold text-slate-700 block mb-1">
                    Twitter Image Override (Optional)
                  </Label>
                  <Input
                    value={seo.twitter_image || ''}
                    onChange={(e) => upSeo('twitter_image', e.target.value)}
                    placeholder="Defaults to Open Graph Image"
                    className="h-8 text-xs font-mono"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 3: SCHEMA.ORG & JSON-LD ── */}
        {seoTab === 'schema' && (
          <div className="space-y-4 pt-1">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs text-slate-600 leading-relaxed">
              Google rich snippets are generated from structured JSON-LD (`https://schema.org`).
              The atlas page automatically builds an <strong>Occupation</strong> entity, <strong>BreadcrumbList</strong>, <strong>Organization</strong>, and <strong>FAQPage</strong> schema.
            </div>

            <div>
              <Label className="text-xs font-semibold text-slate-700 block mb-1">
                Primary Schema.org Entity Type (`@type`)
              </Label>
              <Select
                value={seo.schema_type || 'Occupation'}
                onValueChange={(val) => upSeo('schema_type', val)}
              >
                <SelectTrigger className="h-8 text-xs bg-white max-w-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Occupation">Occupation (Standard Schema.org/Occupation — Recommended)</SelectItem>
                  <SelectItem value="Course">Course (Educational Course Profile)</SelectItem>
                  <SelectItem value="Guide">Guide (Specialist Guide / Article)</SelectItem>
                  <SelectItem value="WebPage">WebPage (General WebPage Entity)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  Custom Additional JSON-LD Schema Snippet
                  <span className="text-[10px] text-slate-400 font-normal">(Injected into `@graph`)</span>
                </Label>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-medium ${
                  isValidJson(seo.custom_json_ld)
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                }`}>
                  {isValidJson(seo.custom_json_ld) ? '✓ Valid JSON' : '⚠ Invalid JSON syntax'}
                </span>
              </div>
              <Textarea
                value={seo.custom_json_ld || ''}
                onChange={(e) => upSeo('custom_json_ld', e.target.value)}
                placeholder='{\n  "@type": "SpecialAnnouncement",\n  "name": "State Nomination Quota Open",\n  "text": "Priority invitations for onshore and offshore applicants."\n}'
                className="text-xs font-mono min-h-[110px]"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Enter valid JSON object or array to merge into the structured JSON-LD graph.
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* ── CARD 13: GAZETTE REFERENCE & AUDIT NOTES ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-3">
        <div className="flex items-center justify-between border-b pb-2">
          <div className="flex items-center gap-2">
            <span className="text-base">🛡️</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">13. Official Gazette Reference &amp; Audit Notes</h3>
              <p className="text-xs text-slate-500">Official gazette or assessing authority source link supporting this verification.</p>
            </div>
          </div>
          <Badge className="text-[10px] bg-slate-100 text-slate-600 font-semibold">Audit Trail</Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Official Source URL (ABS ANZSCO / IRCC NOC / Gazetted URL)
            </Label>
            <div className="flex gap-2">
              <Input
                value={sourceRef || ''}
                onChange={(e) => setSourceRef?.(e.target.value)}
                placeholder="https://www.abs.gov.au/statistics/classifications/anzsco..."
                className="h-8 text-xs font-mono flex-1"
                data-testid="unified-source-ref"
              />
              {sourceRef && (
                <a
                  href={sourceRef}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 rounded border border-slate-300 flex items-center justify-center text-xs font-medium text-slate-700"
                  title="Open source reference in new tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">If blank, defaults automatically to the assessing authority website or ABS ANZSCO registry.</p>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-700 block mb-1">
              Audit Review Notes (Optional)
            </Label>
            <Textarea
              value={reviewNotes || ''}
              onChange={(e) => setReviewNotes?.(e.target.value)}
              placeholder="e.g. Verified points cutoffs against May 2025 DHA SkillSelect invitation round."
              className="text-xs min-h-[60px]"
              data-testid="unified-review-notes"
            />
          </div>
        </div>
      </Card>

      {/* ── CARD 14: REQUIRED DOCUMENTS CHECKLIST (TAB 4 IN SALES & PUBLIC) ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-base">📋</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">14. Required Documents Checklist (Tab 4 in Sales &amp; Public)</h3>
              <p className="text-xs text-slate-500">Configures the 16-item categorized checklist (Identity, Education, Employment, English, Character, Health, Professional).</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className="text-[10px] bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold">
              {(edit.required_documents || []).length} Documents Configured
            </Badge>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={loadStandardDocTemplate}
              className="h-7 text-xs border-emerald-300 text-emerald-700 bg-emerald-50/60 hover:bg-emerald-100"
              title="Replace or populate with standard Australian 16-document checklist"
            >
              <Wand2 className="h-3 w-3 mr-1" /> Load Standard 16-Doc Template
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={addDocument}
              className="h-7 text-xs bg-slate-900 text-white font-medium hover:bg-slate-800"
            >
              <Plus className="h-3 w-3 mr-1" /> Add Document
            </Button>
          </div>
        </div>

        {(!edit.required_documents || edit.required_documents.length === 0) ? (
          <div className="p-6 text-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50">
            <FileText className="h-8 w-8 mx-auto text-slate-400 mb-2" />
            <p className="text-xs font-semibold text-slate-700">No custom documents listed</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Click "Load Standard 16-Doc Template" to automatically populate official immigration checklists.</p>
            <Button
              type="button"
              size="sm"
              onClick={loadStandardDocTemplate}
              className="mt-3 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
            >
              <Wand2 className="h-3.5 w-3.5 mr-1" /> Populate Standard 16-Document Template
            </Button>
          </div>
        ) : (
          <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
            {(edit.required_documents || []).map((doc, idx) => (
              <div key={doc.id || idx} className="p-3 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-2.5 flex-wrap md:flex-nowrap">
                <div className="w-full md:w-36 shrink-0">
                  <Select
                    value={doc.category || 'Employment'}
                    onValueChange={(val) => updateDocument(idx, { category: val })}
                  >
                    <SelectTrigger className="h-8 text-xs bg-white font-bold text-slate-800">
                      <SelectValue placeholder="Category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Identity">🪪 Identity</SelectItem>
                      <SelectItem value="Education">🎓 Education</SelectItem>
                      <SelectItem value="Employment">💼 Employment</SelectItem>
                      <SelectItem value="English">🗣️ English</SelectItem>
                      <SelectItem value="Character">⚖️ Character</SelectItem>
                      <SelectItem value="Health">🩺 Health</SelectItem>
                      <SelectItem value="Professional">📜 Professional</SelectItem>
                      <SelectItem value="Other">📁 Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Input
                  value={doc.name || ''}
                  onChange={(e) => updateDocument(idx, { name: e.target.value })}
                  placeholder="e.g. Official Work Reference Letters on Company Letterhead"
                  className="h-8 text-xs flex-1 bg-white font-medium"
                />

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => updateDocument(idx, { required: !doc.required })}
                    className={`text-[10px] font-bold px-2.5 py-1 rounded border transition ${
                      doc.required
                        ? 'bg-rose-100 text-rose-800 border-rose-300'
                        : 'bg-slate-200 text-slate-700 border-slate-300'
                    }`}
                  >
                    {doc.required ? 'Mandatory' : 'Optional'}
                  </button>

                  <button
                    type="button"
                    onClick={() => removeDocument(idx)}
                    className="text-slate-400 hover:text-rose-600 p-1.5 rounded transition hover:bg-rose-50"
                    title="Remove document item"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── CARD 15: SAMPLE SUCCESS CASES & REFERENCE SCENARIOS (TAB 6 IN SALES) ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-base">🏆</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">15. Sample Success Cases &amp; Reference Scenarios (Tab 6 in Sales)</h3>
              <p className="text-xs text-slate-500">Configures real applicant scenarios, approval timelines, visa subclasses and outcome strategies shown on Sales Tab 6.</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className="text-[10px] bg-indigo-50 text-indigo-800 border-indigo-200 font-semibold">
              {(edit.sample_cases || []).length} Cases Configured
            </Badge>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={loadStandardSampleCases}
              className="h-7 text-xs border-indigo-300 text-indigo-700 bg-indigo-50/60 hover:bg-indigo-100"
              title="Populate realistic sample cases tailored to this occupation"
            >
              <Wand2 className="h-3 w-3 mr-1" /> Load Standard Cases
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleAddSampleCase}
              className="h-7 text-xs bg-slate-900 text-white font-medium hover:bg-slate-800"
            >
              <Plus className="h-3 w-3 mr-1" /> Add Case
            </Button>
          </div>
        </div>

        {(!edit.sample_cases || edit.sample_cases.length === 0) ? (
          <div className="p-6 text-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50">
            <BookOpen className="h-8 w-8 mx-auto text-slate-400 mb-2" />
            <p className="text-xs font-semibold text-slate-700">No sample cases configured</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Click "Load Standard Cases" or "Add Case" to provide real reference profiles for sales and client pitches.</p>
            <Button
              type="button"
              size="sm"
              onClick={loadStandardSampleCases}
              className="mt-3 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
            >
              <Wand2 className="h-3.5 w-3.5 mr-1" /> Populate Realistic Success Cases
            </Button>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {(edit.sample_cases || []).map((sc, idx) => (
              <div key={sc.id || idx} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-800">Case #{idx + 1}</span>
                    <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-[10px] font-bold">
                      {sc.outcome || 'Approved'}
                    </Badge>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveSampleCase(idx)}
                    className="text-slate-400 hover:text-rose-600 p-1 rounded transition hover:bg-rose-50 text-xs flex items-center gap-1 font-semibold"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Remove Case
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2.5">
                  <div>
                    <Label className="text-[10px] text-slate-500 uppercase font-bold">Client Age</Label>
                    <Input
                      type="number"
                      value={sc.client_age ?? ''}
                      onChange={(e) => handleUpdateSampleCase(idx, { client_age: e.target.value })}
                      placeholder="e.g. 32"
                      className="h-8 text-xs bg-white font-mono mt-0.5"
                    />
                  </div>

                  <div>
                    <Label className="text-[10px] text-slate-500 uppercase font-bold">Visa Subclass</Label>
                    <Input
                      value={sc.visa_subclass || ''}
                      onChange={(e) => handleUpdateSampleCase(idx, { visa_subclass: e.target.value })}
                      placeholder="e.g. 190 / 189 / 491"
                      className="h-8 text-xs bg-white font-mono mt-0.5"
                    />
                    <div className="flex items-center gap-1 mt-1 flex-wrap">
                      {['189', '190', '491', '186', '482'].map((sub) => (
                        <button
                          key={sub}
                          type="button"
                          onClick={() => handleUpdateSampleCase(idx, { visa_subclass: sub })}
                          className={`text-[9px] px-1 py-0.2 rounded font-mono font-bold transition border ${
                            sc.visa_subclass === sub
                              ? 'bg-slate-900 text-white border-slate-900'
                              : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
                          }`}
                        >
                          {sub}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Label className="text-[10px] text-slate-500 uppercase font-bold">Timeline (Months)</Label>
                    <Input
                      type="number"
                      value={sc.timeline_months ?? ''}
                      onChange={(e) => handleUpdateSampleCase(idx, { timeline_months: e.target.value })}
                      placeholder="e.g. 5"
                      className="h-8 text-xs bg-white font-mono mt-0.5"
                    />
                  </div>

                  <div>
                    <Label className="text-[10px] text-slate-500 uppercase font-bold">Outcome Status</Label>
                    <Input
                      value={sc.outcome || ''}
                      onChange={(e) => handleUpdateSampleCase(idx, { outcome: e.target.value })}
                      placeholder="e.g. Positive Assessment & PR Granted"
                      className="h-8 text-xs bg-white font-semibold mt-0.5"
                    />
                  </div>
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500 uppercase font-bold">Client Profile &amp; Educational Background</Label>
                  <Textarea
                    value={sc.profile_summary || ''}
                    onChange={(e) => handleUpdateSampleCase(idx, { profile_summary: e.target.value })}
                    placeholder="e.g. Bachelor's degree with 6 years of post-qualification experience in Actuarial Science. Positive VETASSESS assessment achieved on first submission."
                    rows={2}
                    className="text-xs bg-white mt-0.5"
                  />
                </div>

                <div>
                  <Label className="text-[10px] text-slate-500 uppercase font-bold">Strategy &amp; Case Officer Notes</Label>
                  <Textarea
                    value={sc.notes || ''}
                    onChange={(e) => handleUpdateSampleCase(idx, { notes: e.target.value })}
                    placeholder="e.g. Full documentation of roles, salary bank credits and tax filings aligned to ANZSCO 224111 descriptor. Nomination invitation received within 90 days."
                    rows={2}
                    className="text-xs bg-white mt-0.5"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── CARD 16: SIMILAR OCCUPATIONS & PINNED CODES OVERRIDE (TAB 5 IN SALES & PUBLIC) ── */}
      <Card className="p-5 border-slate-200 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b pb-2.5 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-base">🔀</span>
            <div>
              <h3 className="text-sm font-bold text-slate-900">16. Similar Occupations &amp; Pinned Codes Override (Tab 5 in Sales &amp; Public)</h3>
              <p className="text-xs text-slate-500">Explicitly pin similar occupation codes (e.g. AU-224112, 224113). Pinned codes are displayed at the top with a 100% match rating; remaining slots are automatically filled from the same ANZSCO unit group.</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className="text-[10px] bg-purple-50 text-purple-800 border-purple-200 font-semibold">
              {(Array.isArray(edit.similar_codes_override) ? edit.similar_codes_override : []).length} Pinned Codes
            </Badge>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={handleSuggestPeers}
              className="h-7 text-xs border-purple-300 text-purple-700 bg-purple-50/60 hover:bg-purple-100"
              title="Auto-detect and pin sibling occupations from the same 4-digit ANZSCO unit group"
            >
              <Sparkles className="h-3 w-3 mr-1" /> Suggest Unit Group Peers
            </Button>
          </div>
        </div>

        {/* Visual Pinned Badges */}
        <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5">
          <div className="flex items-center justify-between">
            <Label className="text-[11px] font-bold text-slate-700 uppercase">
              Pinned Similar Occupation Cards (100% Match on Sales &amp; Atlas)
            </Label>
            <span className="text-[11px] text-slate-400">Click &times; to unpin</span>
          </div>

          {(Array.isArray(edit.similar_codes_override) ? edit.similar_codes_override : []).length === 0 ? (
            <div className="p-3 text-center border border-dashed border-slate-200 rounded-lg bg-white">
              <p className="text-xs text-slate-500">No codes pinned yet. Top similar occupations will be auto-calculated using unit group and assessing authority match.</p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleSuggestPeers}
                className="mt-2 text-xs border-purple-300 text-purple-700 bg-purple-50 hover:bg-purple-100 h-7"
              >
                <Sparkles className="h-3 w-3 mr-1" /> Pin Common Unit Group Occupations
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              {(Array.isArray(edit.similar_codes_override) ? edit.similar_codes_override : []).map((code) => (
                <span
                  key={code}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-purple-100/80 text-purple-900 border border-purple-200 font-mono text-xs font-bold shadow-2xs"
                >
                  <Pin className="h-3 w-3 text-purple-600" />
                  {code}
                  <button
                    type="button"
                    onClick={() => handleRemovePinCode(code)}
                    className="ml-1 text-purple-400 hover:text-rose-600 p-0.5 rounded transition hover:bg-white/60"
                    title={`Unpin ${code}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Quick Add Code Row */}
          <div className="flex items-center gap-2 pt-2 border-t border-slate-200">
            <Input
              value={pinInput}
              onChange={(e) => setPinInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddPinCode();
                }
              }}
              placeholder={`Enter code to pin, e.g. 224112 or ${country}-224112`}
              className="h-8 text-xs font-mono bg-white flex-1"
            />
            <Button
              type="button"
              size="sm"
              onClick={() => handleAddPinCode()}
              disabled={!pinInput.trim()}
              className="h-8 text-xs bg-slate-900 hover:bg-slate-800 text-white font-medium px-3"
            >
              <Pin className="h-3 w-3 mr-1" /> Pin Code
            </Button>
          </div>
        </div>

        {/* Comma-separated Bulk Input */}
        <div>
          <Label className="text-xs font-semibold text-slate-700 block mb-1">
            Raw Comma-separated Codes (Direct Bulk Edit)
          </Label>
          <Input
            value={
              Array.isArray(edit.similar_codes_override)
                ? edit.similar_codes_override.join(', ')
                : (edit.similar_codes_override || '')
            }
            onChange={(e) => {
              const val = e.target.value;
              const codes = val.split(',').map((c) => c.trim()).filter(Boolean);
              setEdit({ ...edit, similar_codes_override: codes });
            }}
            placeholder="e.g. AU-224112, AU-224113, AU-224199 or 224112, 224113"
            className="h-9 text-xs font-mono font-bold bg-white"
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Format: <code>AU-XXXXXX</code> or 6-digit code. These will be pinned at 100% similarity at the top of Tab 5 ("Similar Occupations"). Remaining slots up to 8 will be automatically populated from the same ANZSCO unit group.
          </p>
        </div>
      </Card>

      {/* ── STICKY BOTTOM ACTIONS BAR ── */}
      <div className="sticky bottom-4 z-30 rounded-xl border border-slate-300 bg-white p-3.5 shadow-xl flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => window.open(publicUrl, '_blank')}
            className="border-emerald-600 text-emerald-800 hover:bg-emerald-50 font-semibold text-xs h-9"
          >
            <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
            View Public Atlas ↗
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={save}
            disabled={saving}
            className="border-slate-300 text-slate-700 hover:bg-slate-100 font-medium text-xs h-9"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Save className="w-3.5 h-3.5 mr-1.5" />}
            Save Draft
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={verify}
            disabled={saving}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-9 shadow-md px-5"
            data-testid="unified-publish-bottom-btn"
          >
            {saving ? <Loader2 className="w-4 h-4 mr-1.5 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-1.5" />}
            Save &amp; Publish Live to Atlas
          </Button>
        </div>
      </div>
    </div>
  );
}
