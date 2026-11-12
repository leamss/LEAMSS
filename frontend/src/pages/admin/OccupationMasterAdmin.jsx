/**
 * Phase 6.9 — Occupation Master Admin Console.
 *
 * Single page with 4 tabs covering 6.9.2 → 6.9.5:
 *   • Browse & Verify (6.9.3) — list all draft codes, open 3-panel editor
 *   • Bulk Import   (6.9.2) — CSV/Excel upload + preview + commit
 *   • Country Templates (6.9.5) — view/edit factor lists, add new country
 *   • Status & Settings (6.9.4) — verification threshold + auto-flag outdated
 *
 * Route: /admin/kb/occupation-master
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  ArrowLeft, Search, Upload, Sparkles, Globe2, Settings2, FileText,
  CheckCircle2, AlertCircle, Loader2, Wand2, Save, RefreshCw, Trash2,
  ExternalLink, Plus, ShieldCheck, Award, Briefcase, BookOpen, Layers,
  Copy, Check, FileCheck, HelpCircle, ChevronRight, X, Clock, Landmark,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';
import { handleSafeBack } from '@/lib/navigation';
import PublicAtlasUnifiedEditor from './components/PublicAtlasUnifiedEditor';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function OccupationMasterAdmin() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);
  const tab = params.get('tab') || 'browse';

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="kb-admin-page">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => handleSafeBack(navigate, '/admin/eligibility/knowledge-base')} data-testid="back-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />KB Home
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Globe2 className="h-7 w-7 text-indigo-600" />
              Occupation Master Admin Console
              <Badge className="bg-indigo-600 text-white text-[9px]">Phase 6.9</Badge>
            </h1>
            <p className="text-sm text-slate-500">AI drafts · Admin verifies · Sales uses verified data</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="ml-auto border-teal-300 text-teal-700 hover:bg-teal-50"
            onClick={() => navigate('/admin/kb/eoi-backlog')}
            data-testid="open-eoi-backlog"
          >
            <FileText className="h-4 w-4 mr-1" />EOI Backlog Data
          </Button>
        </div>

        <Tabs value={tab} onValueChange={(v) => setParams({ tab: v })}>
          <TabsList className="bg-white border" data-testid="kb-tabs">
            <TabsTrigger value="browse" data-testid="tab-browse"><FileText className="h-4 w-4 mr-1" />Browse &amp; Verify</TabsTrigger>
            <TabsTrigger value="import" data-testid="tab-import"><Upload className="h-4 w-4 mr-1" />Bulk Import</TabsTrigger>
            <TabsTrigger value="templates" data-testid="tab-templates"><Globe2 className="h-4 w-4 mr-1" />Country Templates</TabsTrigger>
            <TabsTrigger value="classifications" data-testid="tab-classifications"><Layers className="h-4 w-4 mr-1" />AU Classification Versions</TabsTrigger>
            <TabsTrigger value="settings" data-testid="tab-settings"><Settings2 className="h-4 w-4 mr-1" />Status &amp; Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="browse"><BrowseAndVerify headers={headers} /></TabsContent>
          <TabsContent value="import"><BulkImport headers={headers} /></TabsContent>
          <TabsContent value="templates"><CountryTemplates headers={headers} /></TabsContent>
          <TabsContent value="classifications"><AUClassificationVersionsAdmin headers={headers} /></TabsContent>
          <TabsContent value="settings"><StatusSettings headers={headers} /></TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// 6.9.3 — Browse & Verify (with 3-panel editor)
// ════════════════════════════════════════════════════════════════
function BrowseAndVerify({ headers }) {
  const [list, setList] = useState([]);
  const [filters, setFilters] = useState({ status: 'all', country: 'AU', search: '' });
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams();
      if (filters.status && filters.status !== 'all') p.append('status', filters.status);
      else p.append('status', 'all');
      if (filters.country && filters.country !== 'all') p.append('country', filters.country);
      if (filters.search) p.append('search', filters.search);
      p.append('limit', '300');
      const r = await axios.get(`${API}/occupation-master?${p}`, { headers });
      setList(r.data.items || []);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load occupations'));
    } finally { setLoading(false); }
  }, [filters, headers]);

  useEffect(() => { load(); }, [load]);

  if (editing) {
    return <ThreePanelEditor item={editing} headers={headers}
      onSaved={() => { setEditing(null); load(); }}
      onCancel={() => setEditing(null)} />;
  }

  return (
    <div className="space-y-3">
      <Card className="p-3">
        <div className="flex flex-wrap gap-2 items-center">
          <Input placeholder="Search code / title…" value={filters.search}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="max-w-xs h-9" data-testid="browse-search" />
          <Select value={filters.country || 'all'} onValueChange={(v) => setFilters({ ...filters, country: v === 'all' ? '' : v })}>
            <SelectTrigger className="w-32 h-9" data-testid="browse-country"><SelectValue placeholder="Country" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All countries</SelectItem>
              <SelectItem value="AU">🇦🇺 AU (Australia)</SelectItem>
              <SelectItem value="CA">🇨🇦 CA (Canada)</SelectItem>
              <SelectItem value="NZ">🇳🇿 NZ (New Zealand)</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filters.status || 'all'} onValueChange={(v) => setFilters({ ...filters, status: v === 'all' ? 'all' : v })}>
            <SelectTrigger className="w-32 h-9" data-testid="browse-status"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="verified">Verified (Active)</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="outdated">Outdated</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" className="h-9" onClick={load} data-testid="browse-refresh">
            <RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh
          </Button>
          <span className="text-xs text-slate-500 ml-auto font-medium">{list.length} codes shown</span>
        </div>
      </Card>

      {loading ? (
        <Card className="p-10 text-center text-slate-400"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></Card>
      ) : list.length === 0 ? (
        <Card className="p-10 text-center text-slate-400 text-sm">No codes match these filters.</Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2" data-testid="codes-grid">
          {list.map((it) => <CodeCard key={it.occupation_id} item={it} onOpen={() => setEditing(it)} />)}
        </div>
      )}
    </div>
  );
}

function CodeCard({ item, onOpen }) {
  const statusColor = {
    verified: 'bg-emerald-100 text-emerald-700',
    draft: 'bg-amber-100 text-amber-700',
    outdated: 'bg-rose-100 text-rose-700',
    superseded: 'bg-slate-100 text-slate-500',
  }[item.status] || 'bg-slate-100';
  return (
    <Card className="p-3 hover:shadow-md transition cursor-pointer" onClick={onOpen} data-testid={`code-card-${item.occupation_id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-mono text-slate-500">{item.country_code} · {item.code}</p>
          <p className="text-sm font-bold truncate">{item.title}</p>
          <p className="text-[10px] text-slate-500 truncate">
            {(item.assessing_authority || {}).name || '—'} · Skill Lv {item.skill_level || '?'}
          </p>
        </div>
        <Badge className={`${statusColor} text-[9px]`} data-testid={`status-${item.occupation_id}`}>
          {item.status}
        </Badge>
      </div>
      <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500">
        <span>{item.classification_type}</span>
        {item.ai_draft?.generated_at && <span title="AI draft cached"><Sparkles className="h-2.5 w-2.5 inline" /> AI draft</span>}
      </div>
    </Card>
  );
}

function ThreePanelEditor({ item, headers, onSaved, onCancel }) {
  const [edit, setEdit] = useState(() => ({
    title: item.title || '',
    code: item.code || '',
    country_code: item.country_code || 'AU',
    classification_type: item.classification_type || (item.country_code === 'AU' ? 'ANZSCO' : item.country_code === 'CA' ? 'NOC' : 'ANZSCO'),
    classification_version: item.classification_version || '',
    skill_level: item.skill_level != null ? String(item.skill_level) : '1',
    skillselect_tier: item.skillselect_tier || 'tier_4',
    caveats: item.caveats || '',
    min_invitation_points: item.min_invitation_points || {},
    visa_pathways: item.visa_pathways || [],
    state_territory_eligibility: item.state_territory_eligibility || {},
    state_demand: item.state_demand || {},
    skill_assessment_details: item.skill_assessment_details || {},
    assessing_authority_id: item.assessing_authority_id || '',
    description: item.description || '',
    typical_tasks: Array.isArray(item.typical_tasks) ? item.typical_tasks : [],
    alternative_titles: Array.isArray(item.alternative_titles) ? item.alternative_titles : [],
    specialisations: Array.isArray(item.specialisations) ? item.specialisations : [],
    qualification_rules: item.qualification_rules || '',
    assessing_authority: {
      code: item.assessing_authority?.code || '',
      short_name: item.assessing_authority?.short_name || '',
      name: item.assessing_authority?.name || '',
      full_name: item.assessing_authority?.full_name || '',
      body_id: item.assessing_authority?.body_id || '',
      website: item.assessing_authority?.website || item.assessing_authority?.url || '',
      processing_time_weeks: item.assessing_authority?.processing_time_weeks != null ? String(item.assessing_authority.processing_time_weeks) : '',
      fee_native: item.assessing_authority?.fee_native != null ? String(item.assessing_authority.fee_native) : '',
      fee_currency: item.assessing_authority?.fee_currency || (item.country_code === 'AU' ? 'AUD' : item.country_code === 'CA' ? 'CAD' : item.country_code === 'NZ' ? 'NZD' : 'AUD'),
      contact_details: item.assessing_authority?.contact_details || '',
      rules_summary: item.assessing_authority?.rules_summary || '',
    },
    hierarchy: {
      major_group: item.hierarchy?.major_group || '',
      sub_major_group: item.hierarchy?.sub_major_group || '',
      minor_group: item.hierarchy?.minor_group || '',
      unit_group: item.hierarchy?.unit_group || '',
      unit_group_name: item.hierarchy?.unit_group_name || '',
    },
    recommended_visa_subclass: typeof item.recommended_visa_subclass === 'object' && item.recommended_visa_subclass
      ? (item.recommended_visa_subclass[item.country_code] || Object.values(item.recommended_visa_subclass)[0] || '')
      : (typeof item.recommended_visa_subclass === 'string' ? item.recommended_visa_subclass : ''),
    similar_codes_override: Array.isArray(item.similar_codes_override) ? item.similar_codes_override : [],
    required_documents: Array.isArray(item.required_documents) ? item.required_documents : [],
    sample_cases: Array.isArray(item.sample_cases) ? item.sample_cases : [],
    custom_sections: Array.isArray(item.custom_sections) ? item.custom_sections : [],
    ai_draft: item.ai_draft || {},
    migroto_synced: item.migroto_synced || false,
    migroto_last_update: item.migroto_last_update || null,
    pathway_list: item.pathway_list || 'MLTSSL',
    pathway_lists: Array.isArray(item.pathway_lists) ? item.pathway_lists : (item.pathway_list ? [item.pathway_list] : ['MLTSSL']),
    min_invitation_points: item.min_invitation_points || { subclass_189: 75, subclass_190: 70, subclass_491: 65, as_of_program_year: '2025-26', notes: '' },
    state_territory_eligibility: item.state_territory_eligibility || {},
    state_demand: item.state_demand || {},
    state_ratings: item.state_ratings || {},
    anzsco_profile: item.anzsco_profile || {},
    abs_data: item.abs_data || {},
    jsa_data: item.jsa_data || {},
    abs_labour_market: item.abs_labour_market || {},
    demand_rationale: item.demand_rationale || '',
    national_shortage_status: item.national_shortage_status || '',
    state_distribution: item.state_distribution || {},
    industries_ranked: Array.isArray(item.industries_ranked) ? item.industries_ranked : [],
    faqs: Array.isArray(item.faqs) ? item.faqs : [],
    strong_regions: Array.isArray(item.strong_regions) ? item.strong_regions : [],
    ee_eligibility: item.ee_eligibility || { fswp_eligible: true, cec_eligible: true, fstp_eligible: false, categories: [] },
    teer_category: item.teer_category != null ? String(item.teer_category) : '',
    nz_green_list_tier: item.nz_green_list_tier != null ? String(item.nz_green_list_tier) : '',
    aewv_eligibility: item.aewv_eligibility || { eligible: true, occupational_band: 'Level 1', max_stay_years: 5 },
    smc_points_breakdown: item.smc_points_breakdown || { skill_points_base: 6, pass_mark: 6, green_list_auto_pass: false },
    seo_meta: item.seo_meta || {},
  }));

  const [activeTab, setActiveTab] = useState('core');
  const [authorities, setAuthorities] = useState([]);
  const [genLoading, setGenLoading] = useState(false);
  const [polishLoading, setPolishLoading] = useState(null);
  const [saving, setSaving] = useState(false);
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [sourceRef, setSourceRef] = useState(item.verification?.source_reference || '');
  const [reviewNotes, setReviewNotes] = useState(item.verification?.review_notes || '');
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [migrotoLoading, setMigrotoLoading] = useState(false);

  // Fetch full details from backend on mount to ensure all nested arrays & models are populated
  useEffect(() => {
    let unmounted = false;
    const fetchFull = async () => {
      setLoadingDetails(true);
      try {
        const r = await axios.get(`${API}/occupation-master/${item.occupation_id}`, { headers });
        if (unmounted) return;
        const full = r.data;
        if (full) {
          setEdit((prev) => ({
            ...prev,
            title: full.title || prev.title,
            code: full.code || prev.code,
            country_code: full.country_code || prev.country_code,
            classification_type: full.classification_type || prev.classification_type,
            classification_version: full.classification_version || prev.classification_version,
            skill_level: full.skill_level != null ? String(full.skill_level) : prev.skill_level,
            skillselect_tier: full.skillselect_tier || prev.skillselect_tier,
            caveats: full.caveats || prev.caveats,
            min_invitation_points: full.min_invitation_points || prev.min_invitation_points,
            visa_pathways: full.visa_pathways || prev.visa_pathways,
            state_territory_eligibility: full.state_territory_eligibility || prev.state_territory_eligibility,
            state_demand: full.state_demand || prev.state_demand,
            skill_assessment_details: full.skill_assessment_details || prev.skill_assessment_details,
            assessing_authority_id: full.assessing_authority_id || prev.assessing_authority_id,
            description: full.description || prev.description,
            typical_tasks: Array.isArray(full.typical_tasks) && full.typical_tasks.length ? full.typical_tasks : prev.typical_tasks,
            alternative_titles: Array.isArray(full.alternative_titles) && full.alternative_titles.length ? full.alternative_titles : prev.alternative_titles,
            specialisations: Array.isArray(full.specialisations) && full.specialisations.length ? full.specialisations : prev.specialisations,
            qualification_rules: full.qualification_rules || prev.qualification_rules,
            assessing_authority: {
              code: full.assessing_authority?.code || prev.assessing_authority.code,
              short_name: full.assessing_authority?.short_name || prev.assessing_authority.short_name,
              name: full.assessing_authority?.name || prev.assessing_authority.name,
              full_name: full.assessing_authority?.full_name || prev.assessing_authority.full_name,
              body_id: full.assessing_authority?.body_id || prev.assessing_authority.body_id,
              website: full.assessing_authority?.website || full.assessing_authority?.url || prev.assessing_authority.website,
              processing_time_weeks: full.assessing_authority?.processing_time_weeks != null ? String(full.assessing_authority.processing_time_weeks) : prev.assessing_authority.processing_time_weeks,
              fee_native: full.assessing_authority?.fee_native != null ? String(full.assessing_authority.fee_native) : prev.assessing_authority.fee_native,
              fee_currency: full.assessing_authority?.fee_currency || prev.assessing_authority.fee_currency,
              contact_details: full.assessing_authority?.contact_details || prev.assessing_authority.contact_details,
              rules_summary: full.assessing_authority?.rules_summary || prev.assessing_authority.rules_summary,
            },
            hierarchy: {
              major_group: full.hierarchy?.major_group || prev.hierarchy.major_group,
              sub_major_group: full.hierarchy?.sub_major_group || prev.hierarchy.sub_major_group,
              minor_group: full.hierarchy?.minor_group || prev.hierarchy.minor_group,
              unit_group: full.hierarchy?.unit_group || prev.hierarchy.unit_group,
              unit_group_name: full.hierarchy?.unit_group_name || prev.hierarchy.unit_group_name,
            },
            recommended_visa_subclass: typeof full.recommended_visa_subclass === 'object' && full.recommended_visa_subclass
              ? (full.recommended_visa_subclass[full.country_code] || Object.values(full.recommended_visa_subclass)[0] || prev.recommended_visa_subclass)
              : (typeof full.recommended_visa_subclass === 'string' ? full.recommended_visa_subclass : prev.recommended_visa_subclass),
            similar_codes_override: Array.isArray(full.similar_codes_override) ? full.similar_codes_override : prev.similar_codes_override,
            required_documents: Array.isArray(full.required_documents) ? full.required_documents : prev.required_documents,
            sample_cases: Array.isArray(full.sample_cases) ? full.sample_cases : prev.sample_cases,
            custom_sections: Array.isArray(full.custom_sections) ? full.custom_sections : prev.custom_sections,
            ai_draft: full.ai_draft || prev.ai_draft,
            migroto_synced: full.migroto_synced || prev.migroto_synced,
            migroto_last_update: full.migroto_last_update || prev.migroto_last_update,
            pathway_list: full.pathway_list || prev.pathway_list,
            min_invitation_points: full.min_invitation_points || prev.min_invitation_points,
            state_territory_eligibility: full.state_territory_eligibility || prev.state_territory_eligibility,
            state_demand: full.state_demand || prev.state_demand,
            state_ratings: full.state_ratings || prev.state_ratings,
            anzsco_profile: full.anzsco_profile || prev.anzsco_profile,
            abs_data: full.abs_data || prev.abs_data,
            jsa_data: full.jsa_data || prev.jsa_data,
            abs_labour_market: full.abs_labour_market || prev.abs_labour_market,
            demand_rationale: full.demand_rationale != null ? full.demand_rationale : prev.demand_rationale,
            national_shortage_status: full.national_shortage_status != null ? full.national_shortage_status : prev.national_shortage_status,
            state_distribution: full.state_distribution || prev.state_distribution,
            industries_ranked: Array.isArray(full.industries_ranked) && full.industries_ranked.length ? full.industries_ranked : prev.industries_ranked,
            faqs: Array.isArray(full.faqs) && full.faqs.length ? full.faqs : prev.faqs,
            strong_regions: Array.isArray(full.strong_regions) && full.strong_regions.length ? full.strong_regions : prev.strong_regions,
            pathway_lists: Array.isArray(full.pathway_lists) && full.pathway_lists.length ? full.pathway_lists : prev.pathway_lists,
            ee_eligibility: full.ee_eligibility || prev.ee_eligibility,
            teer_category: full.teer_category != null ? String(full.teer_category) : prev.teer_category,
            nz_green_list_tier: full.nz_green_list_tier != null ? String(full.nz_green_list_tier) : prev.nz_green_list_tier,
            aewv_eligibility: full.aewv_eligibility || prev.aewv_eligibility,
            smc_points_breakdown: full.smc_points_breakdown || prev.smc_points_breakdown,
            seo_meta: full.seo_meta || prev.seo_meta,
          }));
          if (full.verification?.source_reference) {
            setSourceRef(full.verification.source_reference);
          }
          if (full.verification?.review_notes) {
            setReviewNotes(full.verification.review_notes);
          }
        }
      } catch (e) {
        // quiet fallback
      } finally {
        if (!unmounted) setLoadingDetails(false);
      }
    };
    fetchFull();
    return () => { unmounted = true; };
  }, [item.occupation_id, headers]);

  // Fetch authorities list
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const r = await axios.get(`${API}/assessing-authorities?country=${item.country_code || 'AU'}`, { headers });
        if (active) setAuthorities(r.data.items || []);
      } catch (e) {
        console.error('Failed to load authorities', e);
      }
    })();
    return () => { active = false; };
  }, [item.country_code, headers]);

  const aiDraft = edit.ai_draft || {};

  const handleAuthorityChange = (authCode) => {
    const selected = authorities.find((a) => a.code === authCode);
    if (!selected) return;
    setEdit((s) => ({
      ...s,
      assessing_authority_id: selected.id,
      assessing_authority: {
        code: selected.code,
        short_name: selected.code,
        name: selected.full_name || selected.name,
        full_name: selected.full_name,
        website: selected.website,
        fee_native: selected.fees?.msa_fee_aud != null ? String(selected.fees.msa_fee_aud) : s.assessing_authority.fee_native,
        fee_currency: 'AUD',
        processing_time_weeks: selected.processing?.standard_days_max ? String(Math.round(selected.processing.standard_days_max / 7)) : s.assessing_authority.processing_time_weeks,
      },
      skill_assessment_details: {
        ...(s.skill_assessment_details || {}),
        authority: selected.code,
        msa_fee_aud: selected.fees?.msa_fee_aud,
        rpl_fee_aud: selected.fees?.rpl_fee_aud,
        processing_weeks: selected.processing?.standard_days_max ? `${Math.round(selected.processing.standard_days_min / 7)}–${Math.round(selected.processing.standard_days_max / 7)} weeks` : '8–12 weeks',
      },
    }));
  };

  const generate = async () => {
    setGenLoading(true);
    try {
      const r = await axios.post(`${API}/occupation-master/${item.occupation_id}/ai-draft`, {}, { headers });
      setEdit((s) => ({ ...s, ai_draft: r.data.ai_draft }));
      toast.success('AI draft generated', { description: 'Review the left panel and click "Apply to Form" or copy items across.' });
    } catch (e) {
      toast.error(formatApiError(e, 'AI draft failed'));
    } finally { setGenLoading(false); }
  };

  const applyAllAiDraft = () => {
    if (!aiDraft.generated_at) {
      toast.error('Generate an AI draft first');
      return;
    }
    setEdit((s) => ({
      ...s,
      description: aiDraft.description || s.description,
      typical_tasks: Array.isArray(aiDraft.typical_tasks) && aiDraft.typical_tasks.length ? aiDraft.typical_tasks : s.typical_tasks,
      qualification_rules: aiDraft.qualification_rules || s.qualification_rules,
    }));
    toast.success('AI Draft applied to edit form!', { description: 'Description, Tasks, and Qualification Rules updated.' });
  };

  const copyAiField = (fieldKey, aiValue) => {
    setEdit((s) => ({ ...s, [fieldKey]: aiValue }));
    toast.success(`Copied AI ${fieldKey.replace('_', ' ')} to editor`);
  };

  const polish = async (fieldKey, fieldLabel) => {
    const text = edit[fieldKey];
    if (!text || (Array.isArray(text) && !text.length)) {
      toast.error('Field is empty');
      return;
    }
    const payload = Array.isArray(text) ? text.join('\n') : text;
    setPolishLoading(fieldKey);
    try {
      const r = await axios.post(`${API}/kb/polish-text`, {
        text: payload, field_label: fieldLabel,
        context: `Occupation: ${item.code} ${item.title}, ${item.country_code}`,
      }, { headers });
      const polished = Array.isArray(text) ? r.data.polished.split('\n').filter(Boolean) : r.data.polished;
      setEdit((s) => ({ ...s, [fieldKey]: polished }));
      toast.success('Text polished', { description: 'Facts preserved · grammar and clarity improved.' });
    } catch (e) {
      toast.error(formatApiError(e, 'Polish failed'));
    } finally { setPolishLoading(null); }
  };

  const syncMigroto = async () => {
    if (item.country_code !== 'AU') {
      toast.error('Migroto live sync is available for Australia (ANZSCO) occupations');
      return;
    }
    setMigrotoLoading(true);
    try {
      const r = await axios.post(`${API}/migroto/sync/${item.code}`, {}, { headers });
      if (r.data.status === 'success') {
        const details = await axios.get(`${API}/migroto/occupation/${item.code}`, { headers });
        const insight = details.data?.data;
        if (insight) {
          setEdit((s) => ({
            ...s,
            classification_version: insight.occupation?.version || r.data.migroto_info?.classification_version || s.classification_version,
            skillselect_tier: insight.occupation?.tier || s.skillselect_tier,
            typical_tasks: insight.occupation?.essential_tasks ? insight.occupation.essential_tasks.split('\n').filter(Boolean) : s.typical_tasks,
            migroto_synced: true,
            migroto_last_update: insight.eoi_backlog_last_update,
          }));
        }
        toast.success('✓ Synced with Migroto Skilled Migration Registry', {
          description: `Verified ANZSCO code ${item.code} (${r.data.migroto_info?.classification_version || 'v1.3, v2022'}). Tier & backlog updated.`
        });
      } else {
        toast.error(r.data.error || 'Migroto sync failed');
      }
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to sync with Migroto'));
    } finally {
      setMigrotoLoading(false);
    }
  };

  const buildPayload = () => {
    return {
      title: edit.title?.trim() || '',
      classification_type: edit.classification_type?.trim() || 'ANZSCO',
      classification_version: edit.classification_version?.trim() || '',
      description: edit.description?.trim() || '',
      typical_tasks: Array.isArray(edit.typical_tasks) ? edit.typical_tasks.filter(Boolean) : [],
      alternative_titles: Array.isArray(edit.alternative_titles) ? edit.alternative_titles.filter(Boolean) : [],
      specialisations: Array.isArray(edit.specialisations) ? edit.specialisations.filter(Boolean) : [],
      skill_level: edit.skill_level ? parseInt(edit.skill_level, 10) : null,
      skillselect_tier: typeof edit.skillselect_tier === 'object' && edit.skillselect_tier !== null
        ? (edit.skillselect_tier.tier || 'tier_4')
        : (edit.skillselect_tier || 'tier_4'),
      caveats: edit.caveats,
      pathway_list: edit.pathway_list?.trim() || 'MLTSSL',
      min_invitation_points: {
        subclass_189: edit.min_invitation_points?.subclass_189 ? parseInt(edit.min_invitation_points.subclass_189, 10) : null,
        subclass_190: edit.min_invitation_points?.subclass_190 ? parseInt(edit.min_invitation_points.subclass_190, 10) : null,
        subclass_491: edit.min_invitation_points?.subclass_491 ? parseInt(edit.min_invitation_points.subclass_491, 10) : null,
        as_of_program_year: edit.min_invitation_points?.as_of_program_year || '2025-26',
        notes: edit.min_invitation_points?.notes || '',
      },
      visa_pathways: Array.isArray(edit.visa_pathways)
        ? {
            visa_eligibility: edit.visa_pathways,
            pathway_lists: Array.isArray(edit.pathway_lists) ? edit.pathway_lists : (edit.pathway_list ? [edit.pathway_list] : ['MLTSSL']),
          }
        : {
            ...(edit.visa_pathways || {}),
            pathway_lists: Array.isArray(edit.pathway_lists) ? edit.pathway_lists : (edit.visa_pathways?.pathway_lists || ['MLTSSL']),
          },
      state_territory_eligibility: edit.state_territory_eligibility || {},
      state_demand: edit.state_demand || {},
      state_ratings: edit.state_ratings || {},
      anzsco_profile: {
        ...(edit.anzsco_profile || {}),
        median_salary_aud: edit.anzsco_profile?.median_salary_aud ? parseFloat(edit.anzsco_profile.median_salary_aud) : (edit.abs_data?.median_ft_annual_aud ? parseFloat(edit.abs_data.median_ft_annual_aud) : null),
        workforce_size: edit.anzsco_profile?.workforce_size ? parseInt(edit.anzsco_profile.workforce_size, 10) : null,
        employed_count: edit.anzsco_profile?.employed_count ? parseInt(edit.anzsco_profile.employed_count, 10) : null,
        median_weekly_earnings_aud: edit.anzsco_profile?.median_weekly_earnings_aud ? parseFloat(edit.anzsco_profile.median_weekly_earnings_aud) : null,
      },
      abs_data: edit.abs_data ? {
        ...edit.abs_data,
        median_ft_annual_aud: edit.abs_data.median_ft_annual_aud ? parseFloat(edit.abs_data.median_ft_annual_aud) : null,
        median_ft_weekly_earnings_aud: edit.abs_data.median_ft_weekly_earnings_aud ? parseFloat(edit.abs_data.median_ft_weekly_earnings_aud) : null,
        median_ft_hourly_earnings_aud: edit.abs_data.median_ft_hourly_earnings_aud ? parseFloat(edit.abs_data.median_ft_hourly_earnings_aud) : null,
      } : null,
      jsa_data: edit.jsa_data ? {
        ...edit.jsa_data,
        future_growth: edit.jsa_data.future_growth || 'Moderate',
        growth_pct_2025_to_2035: edit.jsa_data.growth_pct_2025_to_2035 != null && edit.jsa_data.growth_pct_2025_to_2035 !== '' ? parseFloat(edit.jsa_data.growth_pct_2025_to_2035) : null,
        employment_2025: edit.jsa_data.employment_2025 ? parseInt(edit.jsa_data.employment_2025, 10) : null,
        projected_employment_2030: edit.jsa_data.projected_employment_2030 ? parseInt(edit.jsa_data.projected_employment_2030, 10) : null,
        projected_employment_2035: edit.jsa_data.projected_employment_2035 ? parseInt(edit.jsa_data.projected_employment_2035, 10) : null,
      } : null,
      abs_labour_market: edit.abs_labour_market ? {
        ...edit.abs_labour_market,
        employed_count: edit.abs_labour_market.employed_count != null && edit.abs_labour_market.employed_count !== '' ? parseInt(edit.abs_labour_market.employed_count, 10) : null,
        median_age: edit.abs_labour_market.median_age != null && edit.abs_labour_market.median_age !== '' ? parseInt(edit.abs_labour_market.median_age, 10) : null,
        part_time_share_pct: edit.abs_labour_market.part_time_share_pct != null && edit.abs_labour_market.part_time_share_pct !== '' ? parseFloat(edit.abs_labour_market.part_time_share_pct) : null,
        female_share_pct: edit.abs_labour_market.female_share_pct != null && edit.abs_labour_market.female_share_pct !== '' ? parseFloat(edit.abs_labour_market.female_share_pct) : null,
        median_weekly_earnings_aud: edit.abs_labour_market.median_weekly_earnings_aud != null && edit.abs_labour_market.median_weekly_earnings_aud !== '' ? parseFloat(edit.abs_labour_market.median_weekly_earnings_aud) : null,
      } : null,
      demand_rationale: edit.demand_rationale != null ? edit.demand_rationale.trim() : '',
      national_shortage_status: edit.national_shortage_status != null ? edit.national_shortage_status.trim() : '',
      state_distribution: edit.state_distribution || {},
      industries_ranked: Array.isArray(edit.industries_ranked) ? edit.industries_ranked : (typeof edit.industries_ranked === 'string' ? edit.industries_ranked.split('\n').map(s => s.trim()).filter(Boolean) : []),
      faqs: Array.isArray(edit.faqs) ? edit.faqs.filter(f => f.q || f.question) : [],
      strong_regions: Array.isArray(edit.strong_regions) ? edit.strong_regions : (typeof edit.strong_regions === 'string' ? edit.strong_regions.split('\n').map(s => s.trim()).filter(Boolean) : []),
      pathway_lists: Array.isArray(edit.pathway_lists) ? edit.pathway_lists : (edit.pathway_list ? [edit.pathway_list] : []),
      ee_eligibility: edit.ee_eligibility ? {
        ...edit.ee_eligibility,
        fswp_eligible: Boolean(edit.ee_eligibility.fswp_eligible),
        cec_eligible: Boolean(edit.ee_eligibility.cec_eligible),
        fstp_eligible: Boolean(edit.ee_eligibility.fstp_eligible),
      } : null,
      teer_category: edit.teer_category !== '' && edit.teer_category != null ? parseInt(edit.teer_category, 10) : null,
      nz_green_list_tier: edit.nz_green_list_tier !== '' && edit.nz_green_list_tier != null ? parseInt(edit.nz_green_list_tier, 10) : null,
      aewv_eligibility: edit.aewv_eligibility || null,
      smc_points_breakdown: edit.smc_points_breakdown || null,
      seo_meta: edit.seo_meta || null,
      skill_assessment_details: {
        ...(edit.skill_assessment_details || {}),
        website: edit.assessing_authority?.website || edit.skill_assessment_details?.website || '',
        msa_fee_aud: edit.assessing_authority?.fee_native ? parseFloat(edit.assessing_authority.fee_native) : edit.skill_assessment_details?.msa_fee_aud,
        full_name: edit.assessing_authority?.full_name || edit.assessing_authority?.name || edit.skill_assessment_details?.full_name || '',
        short_name: edit.assessing_authority?.code || edit.assessing_authority?.short_name || edit.skill_assessment_details?.short_name || '',
      },
      assessing_authority_id: edit.assessing_authority_id,
      qualification_rules: edit.qualification_rules?.trim() || '',
      assessing_authority: {
        code: edit.assessing_authority?.code?.trim() || '',
        short_name: edit.assessing_authority?.short_name?.trim() || '',
        name: edit.assessing_authority?.name?.trim() || '',
        full_name: edit.assessing_authority?.full_name?.trim() || '',
        body_id: edit.assessing_authority?.body_id?.trim() || '',
        website: edit.assessing_authority?.website?.trim() || '',
        url: edit.assessing_authority?.website?.trim() || '',
        processing_time_weeks: edit.assessing_authority?.processing_time_weeks ? parseInt(edit.assessing_authority.processing_time_weeks, 10) : null,
        fee_native: edit.assessing_authority?.fee_native ? parseFloat(edit.assessing_authority.fee_native) : null,
        fee_currency: edit.assessing_authority?.fee_currency || 'AUD',
        contact_details: edit.assessing_authority?.contact_details?.trim() || '',
        rules_summary: edit.assessing_authority?.rules_summary?.trim() || '',
      },
      hierarchy: {
        major_group: edit.hierarchy?.major_group?.trim() || '',
        sub_major_group: edit.hierarchy?.sub_major_group?.trim() || '',
        minor_group: edit.hierarchy?.minor_group?.trim() || '',
        unit_group: edit.hierarchy?.unit_group?.trim() || '',
        unit_group_name: edit.hierarchy?.unit_group_name?.trim() || '',
      },
      recommended_visa_subclass: {
        [item.country_code || 'AU']: typeof edit.recommended_visa_subclass === 'string'
          ? edit.recommended_visa_subclass.trim()
          : (edit.recommended_visa_subclass?.[item.country_code] || '')
      },
      similar_codes_override: Array.isArray(edit.similar_codes_override)
        ? edit.similar_codes_override.filter(Boolean)
        : (typeof edit.similar_codes_override === 'string' ? edit.similar_codes_override.split(',').map(s => s.trim()).filter(Boolean) : []),
      required_documents: (edit.required_documents || []).map(d => ({
        id: d.id || undefined,
        name: d.name?.trim() || 'Document',
        category: d.category || 'Other',
        required: Boolean(d.required),
        country_override: d.country_override || null,
      })),
      sample_cases: (edit.sample_cases || []).map(c => ({
        id: c.id || undefined,
        client_age: c.client_age ? parseInt(c.client_age, 10) : null,
        profile_summary: c.profile_summary?.trim() || '',
        visa_subclass: c.visa_subclass?.trim() || '',
        outcome: c.outcome?.trim() || 'Approved',
        timeline_months: c.timeline_months ? parseInt(c.timeline_months, 10) : null,
        notes: c.notes?.trim() || '',
      })),
      custom_sections: (edit.custom_sections || []).map(s => ({
        id: s.id || undefined,
        title: s.title?.trim() || 'Custom Section',
        body_markdown: s.body_markdown?.trim() || '',
        source_url: s.source_url?.trim() || '',
      })),
    };
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = buildPayload();
      await axios.put(`${API}/occupation-master/${item.occupation_id}`, payload, { headers });
      toast.success('Draft saved successfully', { description: 'All fields and checklists have been updated.' });
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  const verify = async () => {
    const effectiveSourceRef = sourceRef?.trim()
      || edit.assessing_authority?.website
      || `https://www.abs.gov.au/statistics/classifications/anzsco-australian-and-new-zealand-standard-classification-occupations/latest-release`
      || 'https://www.abs.gov.au';
    setSaving(true);
    try {
      const payload = {
        ...buildPayload(),
        source_reference: effectiveSourceRef,
        review_notes: reviewNotes.trim() || 'Verified for Public Atlas',
      };
      await axios.post(`${API}/occupation-master/${item.occupation_id}/verify`, payload, { headers });
      toast.success('✓ Verified & published live', { description: 'Public Atlas page and Smart Sales have been updated immediately.' });
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Verify failed'));
    } finally { setSaving(false); }
  };

  // Required Document helpers
  const addDocument = () => {
    setEdit((s) => ({
      ...s,
      required_documents: [
        ...s.required_documents,
        { id: `doc_${Date.now()}`, name: '', category: 'Qualification', required: true }
      ]
    }));
  };

  const updateDocument = (idx, patch) => {
    setEdit((s) => {
      const docs = [...s.required_documents];
      docs[idx] = { ...docs[idx], ...patch };
      return { ...s, required_documents: docs };
    });
  };

  const removeDocument = (idx) => {
    setEdit((s) => {
      const docs = [...s.required_documents];
      docs.splice(idx, 1);
      return { ...s, required_documents: docs };
    });
  };

  // Sample Case helpers
  const addSampleCase = () => {
    setEdit((s) => ({
      ...s,
      sample_cases: [
        ...(s.sample_cases || []),
        { id: `case_${Date.now()}`, client_age: 32, visa_subclass: '190', outcome: 'Approved', timeline_months: 6, profile_summary: '', notes: '' }
      ]
    }));
  };

  const updateSampleCase = (idx, patch) => {
    setEdit((s) => {
      const cases = [...(s.sample_cases || [])];
      cases[idx] = { ...cases[idx], ...patch };
      return { ...s, sample_cases: cases };
    });
  };

  const removeSampleCase = (idx) => {
    setEdit((s) => {
      const cases = [...(s.sample_cases || [])];
      cases.splice(idx, 1);
      return { ...s, sample_cases: cases };
    });
  };

  // Custom Section helpers
  const addCustomSection = () => {
    setEdit((s) => ({
      ...s,
      custom_sections: [
        ...s.custom_sections,
        { id: `sec_${Date.now()}`, title: '', body_markdown: '', source_url: '' }
      ]
    }));
  };

  const updateCustomSection = (idx, patch) => {
    setEdit((s) => {
      const secs = [...s.custom_sections];
      secs[idx] = { ...secs[idx], ...patch };
      return { ...s, custom_sections: secs };
    });
  };

  const removeCustomSection = (idx) => {
    setEdit((s) => {
      const secs = [...s.custom_sections];
      secs.splice(idx, 1);
      return { ...s, custom_sections: secs };
    });
  };

  const countryFlag = item.country_code === 'AU' ? '🇦🇺' : item.country_code === 'CA' ? '🇨🇦' : item.country_code === 'NZ' ? '🇳🇿' : '🌐';
  const selectedAuthCode = edit.assessing_authority?.code || edit.assessing_authority?.short_name || edit.skill_assessment_details?.authority || '';
  const currentAuthDoc = authorities.find((a) => a.code === selectedAuthCode);

  return (
    <Card className="p-4 space-y-4 shadow-sm" data-testid="three-panel-editor">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base">{countryFlag}</span>
            <p className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
              {item.country_code} · {item.code}
            </p>
            <Badge className={`text-[10px] font-bold ${item.status === 'verified' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' : 'bg-amber-100 text-amber-800 border-amber-300'}`}>
              {item.status}
            </Badge>
            <Badge className="text-[10px] bg-indigo-100 text-indigo-700 border-indigo-200">
              {edit.classification_version || edit.classification_type || item.classification_type}
            </Badge>
            {edit.skill_level && (
              <Badge className="text-[10px] bg-slate-100 text-slate-700 border-slate-200">
                Skill Level {edit.skill_level}
              </Badge>
            )}
            {edit.skillselect_tier && (
              <Badge className="text-[10px] bg-teal-100 text-teal-800 border-teal-300">
                {String(typeof edit.skillselect_tier === 'object' && edit.skillselect_tier !== null ? edit.skillselect_tier.tier : edit.skillselect_tier).replace('_', ' ').toUpperCase()}
              </Badge>
            )}
            {(edit.migroto_synced || item.migroto_synced) && (
              <Badge className="text-[10px] bg-teal-600 text-white border-teal-700" title="Synchronized with Migroto Australian Skilled Migration Registry">
                Migroto Live ✓
              </Badge>
            )}
            {edit.assessing_authority?.name && (
              <Badge className="text-[10px] bg-teal-50 text-teal-700 border-teal-200">
                <Landmark className="h-3 w-3 mr-1 inline" /> {edit.assessing_authority.name}
              </Badge>
            )}
            {loadingDetails && <Loader2 className="h-3.5 w-3.5 text-slate-400 animate-spin" title="Loading full details…" />}
          </div>
          <h2 className="text-xl font-extrabold text-slate-900 mt-1">{edit.title || item.title}</h2>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {item.country_code === 'AU' && (
            <Button
              variant="outline"
              size="sm"
              onClick={syncMigroto}
              disabled={migrotoLoading}
              className="border-teal-400 text-teal-700 hover:bg-teal-50"
              data-testid="editor-migroto-sync"
              title="Pull latest ANZSCO version, SkillSelect tier, and invitation data from Migroto"
            >
              {migrotoLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <RefreshCw className="h-3 w-3 mr-1 text-teal-600" />}
              Migroto Live Sync
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.open(`/atlas/${(item.country_code || 'AU').toLowerCase()}/${item.code}`, '_blank')}
            className="border-emerald-400 bg-emerald-50/60 text-emerald-800 hover:bg-emerald-100 font-semibold shadow-xs"
            data-testid="editor-view-public-atlas"
            title="Open the live public SEO money page in a new tab"
          >
            <Globe2 className="h-3.5 w-3.5 mr-1 text-emerald-600" />
            View Public Atlas ↗
          </Button>
          <Button variant="outline" size="sm" onClick={onCancel} data-testid="editor-cancel">
            <ArrowLeft className="h-4 w-4 mr-1" />Back
          </Button>
          <Button size="sm" onClick={save} disabled={saving} className="bg-slate-800 hover:bg-slate-900 text-white font-medium shadow-sm" data-testid="editor-save-draft">
            {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
            Save Draft
          </Button>
          <Button size="sm" onClick={verify} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm" data-testid="editor-open-verify">
            {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1" />}
            Save &amp; Publish Live
          </Button>
        </div>
      </div>

      {/* ── UNIFIED PUBLIC ATLAS PAGE EDITOR ── */}
      <PublicAtlasUnifiedEditor
        item={item}
        edit={edit}
        setEdit={setEdit}
        authorities={authorities}
        handleAuthorityChange={handleAuthorityChange}
        selectedAuthCode={selectedAuthCode}
        sourceRef={sourceRef}
        setSourceRef={setSourceRef}
        reviewNotes={reviewNotes}
        setReviewNotes={setReviewNotes}
        polish={polish}
        polishLoading={polishLoading}
        generate={generate}
        genLoading={genLoading}
        aiDraft={aiDraft}
        applyAllAiDraft={applyAllAiDraft}
        save={save}
        verify={verify}
        saving={saving}
        addDocument={addDocument}
        updateDocument={updateDocument}
        removeDocument={removeDocument}
        addSampleCase={addSampleCase}
        updateSampleCase={updateSampleCase}
        removeSampleCase={removeSampleCase}
        addCustomSection={addCustomSection}
        updateCustomSection={updateCustomSection}
        removeCustomSection={removeCustomSection}
      />
    </Card>
  );
}


function Field({ label, children }) {
  return (
    <div>
      <Label className="text-[10px] uppercase font-bold text-slate-600 mb-1 flex items-center justify-between">{label}</Label>
      {children}
    </div>
  );
}

function PolishBtn({ onClick, loading }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="text-[10px] px-2 py-0.5 rounded bg-purple-100 text-purple-700 hover:bg-purple-200 disabled:opacity-50 inline-flex items-center gap-1"
      title="Polish text with AI (no fact changes)"
      data-testid="polish-btn"
    >
      {loading ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : <Wand2 className="h-2.5 w-2.5" />}
      Polish
    </button>
  );
}


// ════════════════════════════════════════════════════════════════
// 6.9.2 — Bulk Import
// ════════════════════════════════════════════════════════════════
function BulkImport({ headers }) {
  const [file, setFile] = useState(null);
  const [country, setCountry] = useState('AU');
  const [classification, setClassification] = useState('ANZSCO');
  const [version, setVersion] = useState('ANZSCO 2013 v1.3');
  const [onDuplicate, setOnDuplicate] = useState('skip');
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [committed, setCommitted] = useState(null);

  const onPreview = async () => {
    if (!file) { toast.error('Pick a CSV/Excel file first'); return; }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('country_code', country);
      fd.append('classification_type', classification);
      const r = await axios.post(`${API}/occupation-master/import/preview`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      setPreview(r.data);
      setCommitted(null);
      if (!r.data.ok) toast.error(r.data.error);
      else toast.success(`Parsed ${r.data.total_rows} rows`);
    } catch (e) {
      toast.error(formatApiError(e, 'Preview failed'));
    } finally { setLoading(false); }
  };

  const onCommit = async () => {
    if (!file || !preview?.ok) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('country_code', country);
      fd.append('classification_type', classification);
      fd.append('classification_version', version);
      fd.append('on_duplicate', onDuplicate);
      const r = await axios.post(`${API}/occupation-master/import/commit`, fd, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      setCommitted(r.data);
      toast.success(`Imported ${r.data.imported}, updated ${r.data.updated}, skipped ${r.data.skipped}`,
        { description: r.data.errors.length > 0 ? `${r.data.errors.length} warnings — see below` : 'All clean' });
    } catch (e) {
      toast.error(formatApiError(e, 'Commit failed'));
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-3">
      <Card className="p-4 space-y-3" data-testid="import-form">
        <h3 className="text-sm font-bold flex items-center gap-2"><Upload className="h-4 w-4" />Upload ANZSCO / NOC dataset</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <Field label="File (CSV / XLSX)">
            <Input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="import-file" />
          </Field>
          <Field label="Country">
            <Select value={country} onValueChange={setCountry}>
              <SelectTrigger className="h-9" data-testid="import-country"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="AU">🇦🇺 Australia</SelectItem>
                <SelectItem value="CA">🇨🇦 Canada</SelectItem>
                <SelectItem value="NZ">🇳🇿 New Zealand</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Classification">
            <Select value={classification} onValueChange={setClassification}>
              <SelectTrigger className="h-9" data-testid="import-classification"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ANZSCO">ANZSCO</SelectItem>
                <SelectItem value="OSCA">OSCA</SelectItem>
                <SelectItem value="NOC">NOC</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Version label">
            <Input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="e.g. ANZSCO 2013 v1.3" className="h-9" data-testid="import-version" />
          </Field>
        </div>
        <div className="flex gap-2">
          <Button onClick={onPreview} disabled={!file || loading} className="bg-slate-700" data-testid="import-preview-btn">
            {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Search className="h-3 w-3 mr-1" />}
            Preview
          </Button>
          {preview?.ok && (
            <>
              <Select value={onDuplicate} onValueChange={setOnDuplicate}>
                <SelectTrigger className="w-40 h-9" data-testid="import-on-dup"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="skip">On duplicate: Skip</SelectItem>
                  <SelectItem value="update">On duplicate: Update</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={onCommit} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700" data-testid="import-commit-btn">
                {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <CheckCircle2 className="h-3 w-3 mr-1" />}
                Commit Import
              </Button>
            </>
          )}
        </div>
      </Card>

      {preview && preview.ok && (
        <Card className="p-3 space-y-3" data-testid="import-preview">
          <h3 className="text-sm font-bold">Preview · {preview.total_rows} rows detected</h3>
          {preview.duplicates_in_db_count > 0 && (
            <div className="bg-amber-50 border border-amber-200 p-2 rounded text-xs">
              ⚠️ <strong>{preview.duplicates_in_db_count}</strong> codes already exist in {country}.
              {' '}On Commit they will be {onDuplicate === 'skip' ? 'SKIPPED' : 'UPDATED (verification block preserved)'}.
            </div>
          )}
          {preview.duplicates_in_file.length > 0 && (
            <div className="bg-rose-50 border border-rose-200 p-2 rounded text-xs">
              ⚠️ {preview.duplicates_in_file.length} duplicate codes WITHIN the file — first occurrence wins.
            </div>
          )}
          <div className="bg-slate-50 p-2 rounded text-[10px] font-mono">
            <p className="font-semibold mb-1">Detected column mapping:</p>
            <pre>{JSON.stringify(preview.detected_mapping, null, 2)}</pre>
          </div>
          <div className="overflow-x-auto">
            <table className="text-[10px] w-full border-collapse">
              <thead className="bg-slate-100">
                <tr>
                  <th className="text-left p-1.5 border">Code</th>
                  <th className="text-left p-1.5 border">Title</th>
                  <th className="text-left p-1.5 border">Skill Lv</th>
                  <th className="text-left p-1.5 border">Unit group</th>
                  <th className="text-left p-1.5 border">Tasks (count)</th>
                </tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((r, i) => (
                  <tr key={i} className="border-b">
                    <td className="p-1.5 border font-mono">{r.code}</td>
                    <td className="p-1.5 border">{r.title}</td>
                    <td className="p-1.5 border">{r.skill_level ?? '—'}</td>
                    <td className="p-1.5 border">{r.hierarchy?.unit_group_name || r.hierarchy?.unit_group || '—'}</td>
                    <td className="p-1.5 border">{(r.typical_tasks || []).length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {committed && (
        <Card className="p-3 bg-emerald-50/40 border-emerald-200" data-testid="import-result">
          <h3 className="text-sm font-bold text-emerald-800">Import committed</h3>
          <div className="grid grid-cols-4 gap-2 mt-2">
            <Stat label="Imported" value={committed.imported} color="emerald" />
            <Stat label="Updated" value={committed.updated} color="blue" />
            <Stat label="Skipped" value={committed.skipped} color="slate" />
            <Stat label="Warnings" value={committed.errors.length} color="amber" />
          </div>
          {committed.errors.length > 0 && (
            <details className="mt-2 text-[10px]">
              <summary className="cursor-pointer font-semibold">Show warnings</summary>
              <ul className="list-disc list-inside mt-1 space-y-0.5">
                {committed.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </details>
          )}
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value, color }) {
  const map = { emerald: 'bg-emerald-100 text-emerald-700', blue: 'bg-blue-100 text-blue-700',
    slate: 'bg-slate-100 text-slate-700', amber: 'bg-amber-100 text-amber-700' };
  return (
    <div className={`p-2 rounded ${map[color]}`}>
      <p className="text-[9px] uppercase font-bold">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// 6.9.5 — Country Templates
// ════════════════════════════════════════════════════════════════
function CountryTemplates({ headers }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/country-templates`, { headers });
      setTemplates(r.data.items || []);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load templates'));
    } finally { setLoading(false); }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-3">
      <Card className="p-3 bg-amber-50/40 border-amber-300">
        <p className="text-xs">
          <strong>📋 Status:</strong> {templates.length} templates loaded. CA + NZ flagged for full
          admin rebuild against current IRCC CRS / NZ SMC 6-points rules.
          AU is template-mirrored from the legacy Schedule 6 points and needs verification.
          Once a template is verified, the calculator can be wired to read from it.
        </p>
      </Card>

      {loading ? (
        <Card className="p-10 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="templates-grid">
          {templates.map((t) => <TemplateCard key={t.country_code} t={t} headers={headers} onReload={load} />)}
        </div>
      )}
    </div>
  );
}

function TemplateCard({ t, headers, onReload }) {
  const [expanded, setExpanded] = useState(false);
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [sourceRef, setSourceRef] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [verifying, setVerifying] = useState(false);
  const statusColor = {
    verified: 'bg-emerald-100 text-emerald-700',
    draft: 'bg-amber-100 text-amber-700',
    outdated: 'bg-rose-100 text-rose-700',
  }[t.status] || 'bg-slate-100';

  const submitVerify = async () => {
    if (!sourceRef.trim() || sourceRef.trim().length < 5) {
      toast.error('Source URL required (min 5 chars) — paste the official link you verified against');
      return;
    }
    setVerifying(true);
    try {
      await axios.post(`${API}/country-templates/${t.country_code}/verify`, {
        source_reference: sourceRef.trim(),
        review_notes: reviewNotes.trim() || null,
      }, { headers });
      toast.success(`${t.country_code} template verified · Calculator + Reports will use these factors now`);
      setVerifyOpen(false);
      setSourceRef('');
      setReviewNotes('');
      onReload();
    } catch (e) {
      toast.error(formatApiError(e, 'Verify failed'));
    } finally { setVerifying(false); }
  };

  return (
    <Card className="p-3" data-testid={`template-card-${t.country_code}`}>
      <div className="flex items-start justify-between">
        <div>
          <h4 className="text-base font-bold">{t.flag} {t.country_name}</h4>
          <p className="text-[10px] text-slate-500">{t.classification_system} · pass mark {t.pass_mark}</p>
        </div>
        <Badge className={`${statusColor} text-[9px]`}>{t.status}</Badge>
      </div>
      <div className="mt-2 space-y-1">
        <p className="text-[10px]"><strong>{t.factors.length}</strong> factors · <strong>{t.visa_subclasses.length}</strong> visa subclasses</p>
        {t.notes && <p className="text-[10px] italic text-amber-700 bg-amber-50 p-1.5 rounded">{t.notes}</p>}
      </div>
      {t.status === 'verified' && t.verification?.verified_at && (
        <div className="mt-2 p-1.5 rounded bg-emerald-50 border border-emerald-200">
          <p className="text-[10px] text-emerald-800 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Verified {new Date(t.verification.verified_at).toLocaleDateString()}
          </p>
          {t.verification.source_reference && (
            <a href={t.verification.source_reference} target="_blank" rel="noopener noreferrer"
               className="text-[9px] text-emerald-700 hover:underline break-all"
               data-testid={`template-source-${t.country_code}`}>
              ↗ {t.verification.source_reference.slice(0, 60)}…
            </a>
          )}
        </div>
      )}
      <div className="flex gap-2 mt-2">
        <Button size="sm" variant="outline" className="flex-1 h-7 text-[10px]"
                onClick={() => setExpanded(!expanded)}
                data-testid={`template-expand-${t.country_code}`}>
          {expanded ? 'Collapse' : 'View factors'}
        </Button>
        {t.status !== 'verified' && (
          <Button size="sm" className="flex-1 h-7 text-[10px] bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => setVerifyOpen(true)}
                  data-testid={`template-verify-${t.country_code}`}>
            <ShieldCheck className="h-3 w-3 mr-1" />Verify
          </Button>
        )}
      </div>
      {verifyOpen && (
        <div className="mt-2 p-2 bg-blue-50 border border-blue-300 rounded space-y-2"
             data-testid={`template-verify-form-${t.country_code}`}>
          <p className="text-[10px] font-semibold text-blue-900">Verify Template — paste official URL</p>
          <Input
            placeholder="https://immi.gov.au/visas/..."
            value={sourceRef}
            onChange={(e) => setSourceRef(e.target.value)}
            className="h-7 text-[10px]"
            data-testid={`template-source-input-${t.country_code}`}
          />
          <Textarea
            placeholder="Review notes (optional) — what did you cross-check?"
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            className="text-[10px] min-h-[40px]"
            rows={2}
            data-testid={`template-notes-input-${t.country_code}`}
          />
          <div className="flex gap-2">
            <Button size="sm" className="flex-1 h-7 text-[10px] bg-emerald-600"
                    onClick={submitVerify} disabled={verifying || !sourceRef.trim()}
                    data-testid={`template-confirm-verify-${t.country_code}`}>
              {verifying ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <CheckCircle2 className="h-3 w-3 mr-1" />}
              Confirm Verify
            </Button>
            <Button size="sm" variant="outline" className="flex-1 h-7 text-[10px]"
                    onClick={() => { setVerifyOpen(false); setSourceRef(''); setReviewNotes(''); }}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {expanded && (
        <div className="mt-2 space-y-1 text-[10px] max-h-64 overflow-y-auto">
          {t.factors.map((f) => (
            <div key={f.factor_id} className="bg-slate-50 p-1.5 rounded border">
              <p className="font-semibold">{f.factor_name}</p>
              <p className="text-slate-500">{f.options?.length || 0} options · {f.is_additional_factor ? 'Additional' : 'Core'}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

// ════════════════════════════════════════════════════════════════
// 6.9.4 — Status & Settings
// ════════════════════════════════════════════════════════════════
function StatusSettings({ headers }) {
  const [settings, setSettings] = useState(null);
  const [stats, setStats] = useState(null);
  const [saving, setSaving] = useState(false);
  const [flagging, setFlagging] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, st] = await Promise.all([
        axios.get(`${API}/kb/settings`, { headers }),
        axios.get(`${API}/occupation-master/stats`, { headers }),
      ]);
      setSettings(s.data);
      setStats(st.data);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load settings'));
    }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  const updateField = (k, v) => setSettings((s) => ({ ...s, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/kb/settings`, {
        outdated_threshold_months: parseInt(settings.outdated_threshold_months, 10),
        verification_gate_percent: parseInt(settings.verification_gate_percent, 10),
        enforce_verified_only: !!settings.enforce_verified_only,
      }, { headers });
      toast.success('Settings saved');
      load();
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  const autoFlag = async () => {
    setFlagging(true);
    try {
      const r = await axios.post(`${API}/kb/auto-flag-outdated`, {}, { headers });
      toast.success(`Flagged ${r.data.occupations_flagged_outdated} occupations + ${r.data.bodies_flagged_outdated} bodies as outdated`,
        { description: `Threshold: ${r.data.threshold_months} months` });
      load();
    } catch (e) {
      toast.error(formatApiError(e, 'Auto-flag failed'));
    } finally { setFlagging(false); }
  };

  if (!settings) return <Card className="p-10 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></Card>;

  return (
    <div className="space-y-3">
      {stats && (
        <Card className="p-3" data-testid="stats-summary">
          <h3 className="text-sm font-bold mb-2">Current State</h3>
          <div className="grid grid-cols-4 gap-2">
            <Stat label="Total" value={stats.total} color="slate" />
            <Stat label="Verified" value={stats.by_status.verified} color="emerald" />
            <Stat label="Draft" value={stats.by_status.draft} color="amber" />
            <Stat label="Outdated" value={stats.by_status.outdated} color="blue" />
          </div>
          <p className="text-[10px] text-slate-500 mt-2">{stats.pending_percent}% pending verification</p>
        </Card>
      )}

      <Card className="p-4 space-y-3" data-testid="settings-form">
        <h3 className="text-sm font-bold">Verification Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field label="Outdated threshold (months)">
            <Input type="number" min="1" max="60" value={settings.outdated_threshold_months}
              onChange={(e) => updateField('outdated_threshold_months', e.target.value)} className="h-9" data-testid="setting-threshold" />
            <p className="text-[10px] text-slate-500 mt-1">Verified records older than this auto-flag as outdated when admin runs the sweep.</p>
          </Field>
          <Field label="Verification gate (%)">
            <Input type="number" min="50" max="100" value={settings.verification_gate_percent}
              onChange={(e) => updateField('verification_gate_percent', e.target.value)} className="h-9" data-testid="setting-gate" />
            <p className="text-[10px] text-slate-500 mt-1">Hide drafts from sales once ≥ this % of records are verified.</p>
          </Field>
          <Field label="Enforce verified-only (sales)">
            <Select value={String(!!settings.enforce_verified_only)}
              onValueChange={(v) => updateField('enforce_verified_only', v === 'true')}>
              <SelectTrigger className="h-9" data-testid="setting-enforce"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="false">Off — sales sees drafts (transition)</SelectItem>
                <SelectItem value="true">On — drafts hidden from sales</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-[10px] text-slate-500 mt-1">Once verification reaches the threshold, switch this ON.</p>
          </Field>
        </div>
        <div className="flex gap-2 pt-2 border-t">
          <Button onClick={save} disabled={saving} className="bg-slate-700" data-testid="settings-save">
            {saving ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Save className="h-3 w-3 mr-1" />}Save settings
          </Button>
          <Button onClick={autoFlag} disabled={flagging} variant="outline" className="border-amber-400 text-amber-800" data-testid="settings-auto-flag">
            {flagging ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <AlertCircle className="h-3 w-3 mr-1" />}
            Sweep & Flag Outdated
          </Button>
        </div>
      </Card>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
// AU Classification Versions (ANZSCO 2013 vs OSCA 2022) Admin
// ════════════════════════════════════════════════════════════════
function AUClassificationVersionsAdmin({ headers }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newSubclass, setNewSubclass] = useState({ ANZSCO_2013: '', OSCA_2022: '' });
  const [acting, setActing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/sales/au-classification-versions`, { headers });
      setData(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load classification versions'));
    } finally {
      setLoading(false);
    }
  }, [headers]);

  useEffect(() => { load(); }, [load]);

  const handleSubclassAction = async (versionKey, subclass, action) => {
    if (!subclass || !subclass.trim()) return;
    setActing(true);
    try {
      const r = await axios.post(`${API}/sales/au-classification-versions/subclasses`, {
        version_key: versionKey,
        subclass: subclass.trim(),
        action,
      }, { headers });
      toast.success(r.data.message || `Subclass ${subclass} ${action}ed successfully`);
      if (action === 'add') {
        setNewSubclass(prev => ({ ...prev, [versionKey]: '' }));
      }
      load();
    } catch (e) {
      toast.error(formatApiError(e, `Failed to ${action} subclass`));
    } finally {
      setActing(false);
    }
  };

  if (loading) {
    return <Card className="p-10 text-center"><Loader2 className="h-6 w-6 animate-spin mx-auto text-slate-400" /></Card>;
  }

  const versions = data?.versions || {};
  const meta = data?.subclass_metadata || {};

  return (
    <div className="space-y-4" data-testid="au-classifications-admin">
      <Card className="p-4 bg-gradient-to-r from-sky-50 to-indigo-50 border-sky-200">
        <div className="flex items-start gap-3">
          <Layers className="h-6 w-6 text-indigo-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-bold text-slate-800">
              Australia Dual-Classification Framework Configuration
            </h3>
            <p className="text-xs text-slate-600 mt-1">
              Australia operates two distinct occupation classification standards: <b>ANZSCO 2013</b> for points-tested General Skilled Migration (GSM), and <b>OSCA 2022</b> (Core Skills / CSOL) for employer-sponsored and skills shortage visas.
              Admins can dynamically configure and manage the active visa subclasses linked to both versions.
              Changes update the AI code suggester and client assessment rules in real time.
            </p>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {['ANZSCO_2013', 'OSCA_2022'].map((vKey) => {
          const v = versions[vKey] || {};
          const isAnz = vKey === 'ANZSCO_2013';
          const subclasses = v.subclasses || [];
          const inputVal = newSubclass[vKey] || '';

          return (
            <Card key={vKey} className="p-4 space-y-3 border-2" data-testid={`version-card-${vKey}`}>
              <div className="flex items-center justify-between pb-2 border-b">
                <div>
                  <h4 className="text-base font-bold text-slate-800 flex items-center gap-1.5">
                    {isAnz ? '🏛️' : '🚀'} {v.name || vKey}
                  </h4>
                  <Badge className={isAnz ? 'bg-sky-100 text-sky-800 text-[10px]' : 'bg-purple-100 text-purple-800 text-[10px]'}>
                    {v.framework || (isAnz ? 'GSM Points-Tested' : 'Core Skills / Employer')}
                  </Badge>
                </div>
                <Badge variant="outline" className="text-[10px]">
                  {subclasses.length} Subclasses Configured
                </Badge>
              </div>

              <p className="text-xs text-slate-600">
                {v.description}
              </p>

              {v.notes && (
                <p className="text-[11px] italic bg-slate-50 p-2 rounded text-slate-500 border border-slate-100">
                  ℹ️ {v.notes}
                </p>
              )}

              {/* Subclasses List with Remove Action */}
              <div>
                <label className="text-[11px] font-semibold text-slate-600 block mb-1.5 uppercase">
                  Active Visa Subclasses ({v.name})
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {subclasses.map((sc) => {
                    const m = meta[sc] || {};
                    return (
                      <span
                        key={sc}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold ${
                          isAnz
                            ? 'bg-sky-50 text-sky-900 border border-sky-200'
                            : 'bg-purple-50 text-purple-900 border border-purple-200'
                        }`}
                        data-testid={`subclass-badge-${vKey}-${sc}`}
                      >
                        <span>Subclass {sc}</span>
                        {m.name && <span className="text-[9.5px] font-normal text-slate-500">({m.type || m.name})</span>}
                        <button
                          type="button"
                          onClick={() => handleSubclassAction(vKey, sc, 'remove')}
                          disabled={acting}
                          className="ml-1 text-slate-400 hover:text-rose-600 p-0.5 rounded transition"
                          title={`Remove subclass ${sc}`}
                          data-testid={`remove-subclass-${vKey}-${sc}`}
                        >
                          ✕
                        </button>
                      </span>
                    );
                  })}
                  {subclasses.length === 0 && (
                    <span className="text-xs text-slate-400 italic">No subclasses linked. Add one below.</span>
                  )}
                </div>
              </div>

              {/* Add Subclass Input Field */}
              <div className="pt-2 border-t flex gap-2 items-center">
                <Input
                  value={inputVal}
                  onChange={(e) => setNewSubclass({ ...newSubclass, [vKey]: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSubclassAction(vKey, inputVal, 'add');
                  }}
                  placeholder="Enter subclass number (e.g. 189, 491, 482)..."
                  className="h-8 text-xs flex-1"
                  data-testid={`input-subclass-${vKey}`}
                />
                <Button
                  size="sm"
                  onClick={() => handleSubclassAction(vKey, inputVal, 'add')}
                  disabled={acting || !inputVal.trim()}
                  className={`h-8 text-xs text-white ${
                    isAnz ? 'bg-sky-600 hover:bg-sky-700' : 'bg-purple-600 hover:bg-purple-700'
                  }`}
                  data-testid={`btn-add-subclass-${vKey}`}
                >
                  <Plus className="h-3 w-3 mr-1" /> Add Subclass
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      <Card className="p-3 bg-slate-50 text-[11px] text-slate-600">
        <p className="font-semibold text-slate-700 mb-0.5">ℹ️ How the AI &amp; Assessment Engine Use This Rule:</p>
        <ul className="list-disc list-inside space-y-0.5">
          <li><b>ANZSCO 2013:</b> Evaluates candidates for Points-tested Independent (189), State Nominated (190), Regional (491), and Regional Employer (494) pathways.</li>
          <li><b>OSCA 2022:</b> Evaluates candidates against modern Core Skills Occupations List (CSOL), Skills in Demand Subclass 482, and Employer Nomination Subclass 186.</li>
          <li>Removing a subclass immediately updates the SuggesterModal and Assessment report to hide that subclass from eligibility calculations.</li>
        </ul>
      </Card>
    </div>
  );
}
