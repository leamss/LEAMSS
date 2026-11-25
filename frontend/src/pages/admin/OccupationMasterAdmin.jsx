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
            <TabsTrigger value="settings" data-testid="tab-settings"><Settings2 className="h-4 w-4 mr-1" />Status &amp; Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="browse"><BrowseAndVerify headers={headers} /></TabsContent>
          <TabsContent value="import"><BulkImport headers={headers} /></TabsContent>
          <TabsContent value="templates"><CountryTemplates headers={headers} /></TabsContent>
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
  const [limit, setLimit] = useState('1500');
  const [total, setTotal] = useState(0);
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
      p.append('limit', limit);
      const r = await axios.get(`${API}/occupation-master?${p}`, { headers });
      setList(r.data.items || []);
      setTotal(r.data.total ?? (r.data.items?.length || 0));
    } catch (e) {
      toast.error(formatApiError(e, 'Failed to load occupations'));
    } finally { setLoading(false); }
  }, [filters, limit, headers]);

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
          <Select value={limit} onValueChange={(v) => setLimit(v)}>
            <SelectTrigger className="w-32 h-9" data-testid="browse-limit"><SelectValue placeholder="Display Limit" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="100">100 codes</SelectItem>
              <SelectItem value="300">300 codes</SelectItem>
              <SelectItem value="500">500 codes</SelectItem>
              <SelectItem value="1070">1070 codes</SelectItem>
              <SelectItem value="1500">All (1070+)</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" className="h-9" onClick={load} data-testid="browse-refresh">
            <RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh
          </Button>
          <span className="text-xs text-slate-500 ml-auto font-medium">
            Showing {list.length} of {total || list.length} codes
          </span>
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
        const targetId = item.occupation_id || (item.country_code ? `${item.country_code}-${item.code}` : item.code);
        const r = await axios.get(`${API}/occupation-master/${targetId}`, { headers });
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
      min_invitation_points: edit.min_invitation_points,
      visa_pathways: edit.visa_pathways,
      state_territory_eligibility: edit.state_territory_eligibility,
      state_demand: edit.state_demand,
      skill_assessment_details: edit.skill_assessment_details,
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
      const targetId = item.occupation_id || (item.country_code ? `${item.country_code}-${item.code}` : item.code);
      await axios.put(`${API}/occupation-master/${targetId}`, payload, { headers });
      toast.success('Draft saved successfully', { description: 'All fields and checklists have been updated.' });
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e, 'Save failed'));
    } finally { setSaving(false); }
  };

  const verify = async () => {
    if (!sourceRef.trim()) {
      toast.error('Official Source URL required for verification (e.g. ABS ANZSCO, IRCC NOC)');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...buildPayload(),
        source_reference: sourceRef.trim(),
        review_notes: reviewNotes.trim(),
      };
      const targetId = item.occupation_id || (item.country_code ? `${item.country_code}-${item.code}` : item.code);
      await axios.post(`${API}/occupation-master/${targetId}/verify`, payload, { headers });
      toast.success('✓ Verified & published', { description: 'All fields verified and published for sales consultants.' });
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
        ...s.sample_cases,
        { id: `case_${Date.now()}`, client_age: 32, visa_subclass: '190', outcome: 'Approved', timeline_months: 6, profile_summary: '', notes: '' }
      ]
    }));
  };

  const updateSampleCase = (idx, patch) => {
    setEdit((s) => {
      const cases = [...s.sample_cases];
      cases[idx] = { ...cases[idx], ...patch };
      return { ...s, sample_cases: cases };
    });
  };

  const removeSampleCase = (idx) => {
    setEdit((s) => {
      const cases = [...s.sample_cases];
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
          <Button variant="outline" size="sm" onClick={onCancel} data-testid="editor-cancel">
            <ArrowLeft className="h-4 w-4 mr-1" />Back
          </Button>
          <Button size="sm" onClick={save} disabled={saving} className="bg-slate-800 hover:bg-slate-900 text-white font-medium shadow-sm" data-testid="editor-save-draft">
            {saving ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
            Save Draft
          </Button>
          <Button size="sm" onClick={() => setVerifyOpen(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm" data-testid="editor-open-verify">
            <CheckCircle2 className="h-3.5 w-3.5 mr-1" />Verify &amp; Publish
          </Button>
        </div>
      </div>

      {/* 3-Column Responsive Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* ──────────────────────────────────────────────────────────── */}
        {/* COLUMN 1: AI DRAFT PANEL (3 cols) */}
        {/* ──────────────────────────────────────────────────────────── */}
        <Card className="lg:col-span-3 p-3.5 bg-gradient-to-br from-purple-50/60 to-indigo-50/40 border-purple-200 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-purple-200 flex-wrap gap-2">
            <div>
              <h3 className="text-xs font-bold uppercase text-purple-900 flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-purple-600" /> AI Draft
              </h3>
              <p className="text-[10px] text-purple-600">Claude Sonnet 4.5</p>
            </div>
            <div className="flex items-center gap-1.5">
              <Button size="sm" variant="outline" onClick={generate} disabled={genLoading} className="h-7 px-2 text-[10px] border-purple-300 text-purple-800 bg-white hover:bg-purple-100 font-semibold" data-testid="generate-ai-draft">
                {genLoading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Sparkles className="h-3 w-3 mr-1 text-purple-600" />}
                Generate
              </Button>
            </div>
          </div>

          {aiDraft.generated_at ? (
            <div className="space-y-3 text-xs">
              <Button onClick={applyAllAiDraft} size="sm" className="w-full bg-purple-700 hover:bg-purple-800 text-white text-[11px] h-8 shadow-sm font-semibold flex items-center justify-center gap-1.5">
                <Copy className="h-3.5 w-3.5" /> Apply All Draft to Form
              </Button>

              <div className="bg-white p-2.5 rounded-lg border border-purple-200 space-y-1">
                <div className="flex items-center justify-between">
                  <p className="font-bold text-purple-900 text-[11px]">Description</p>
                  <button type="button" onClick={() => copyAiField('description', aiDraft.description || '')} className="text-[10px] text-purple-700 hover:text-purple-900 font-semibold underline">
                    Use this
                  </button>
                </div>
                <p className="text-[11px] text-slate-700 whitespace-pre-wrap max-h-36 overflow-y-auto leading-relaxed">{aiDraft.description || '—'}</p>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-purple-200 space-y-1">
                <div className="flex items-center justify-between">
                  <p className="font-bold text-purple-900 text-[11px]">Typical Tasks ({(aiDraft.typical_tasks || []).length})</p>
                  <button type="button" onClick={() => copyAiField('typical_tasks', aiDraft.typical_tasks || [])} className="text-[10px] text-purple-700 hover:text-purple-900 font-semibold underline">
                    Use these
                  </button>
                </div>
                <ul className="list-disc list-inside text-[11px] text-slate-700 space-y-1 max-h-40 overflow-y-auto">
                  {(aiDraft.typical_tasks || []).map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>

              {aiDraft.qualification_rules && (
                <div className="bg-white p-2.5 rounded-lg border border-purple-200 space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="font-bold text-purple-900 text-[11px]">Qualification Rules</p>
                    <button type="button" onClick={() => copyAiField('qualification_rules', aiDraft.qualification_rules || '')} className="text-[10px] text-purple-700 hover:text-purple-900 font-semibold underline">
                      Use this
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-700 whitespace-pre-wrap max-h-32 overflow-y-auto leading-relaxed">{aiDraft.qualification_rules}</p>
                </div>
              )}

              {aiDraft.ai_confidence_note && (
                <div className="bg-amber-50 border border-amber-200 p-2 rounded text-[10px] text-amber-800">
                  <strong>⚠️ Note:</strong> {aiDraft.ai_confidence_note}
                </div>
              )}

              <p className="text-[9px] text-slate-500 text-center">
                Generated {new Date(aiDraft.generated_at).toLocaleString()}
                {aiDraft.generated_by_model ? ` · ${aiDraft.generated_by_model}` : ''}
              </p>
            </div>
          ) : (
            <div className="text-xs text-slate-500 text-center py-10 space-y-2">
              <Sparkles className="h-8 w-8 mx-auto text-purple-400 opacity-60 animate-pulse" />
              <p className="font-semibold text-slate-700">No AI Draft Yet</p>
              <p className="text-[10px] text-slate-500 leading-normal">
                Click &quot;Generate&quot; to draft baseline description, tasks, and assessment rules with Claude Sonnet.
              </p>
            </div>
          )}
        </Card>

        {/* ──────────────────────────────────────────────────────────── */}
        {/* COLUMN 2: FULL ADMIN EDIT WORKSPACE (6 cols) */}
        {/* ──────────────────────────────────────────────────────────── */}
        <Card className="lg:col-span-6 p-4 bg-white border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b pb-2 flex-wrap gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <Briefcase className="h-4 w-4 text-emerald-600" />
                All Occupation Fields (Editable)
              </h3>
              <p className="text-[11px] text-slate-500">Edit, polish, and configure all details before publishing.</p>
            </div>
            <div className="flex items-center gap-1">
              <Badge className="bg-slate-100 text-slate-700 text-[10px]">
                {edit.required_documents.length} Docs · {edit.sample_cases.length} Cases
              </Badge>
            </div>
          </div>

          {/* Sub-Tabs for clean categorization */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full space-y-3">
            <TabsList className="bg-slate-100 p-1 flex flex-wrap h-auto gap-1 border border-slate-200">
              <TabsTrigger value="core" className="text-xs py-1 px-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <FileText className="h-3.5 w-3.5 mr-1" /> Core &amp; Tasks
              </TabsTrigger>
              <TabsTrigger value="skill" className="text-xs py-1 px-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <Award className="h-3.5 w-3.5 mr-1" /> Skill Assessment
              </TabsTrigger>
              <TabsTrigger value="visas" className="text-xs py-1 px-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <Globe2 className="h-3.5 w-3.5 mr-1" /> Visas &amp; Hierarchy
              </TabsTrigger>
              <TabsTrigger value="docs" className="text-xs py-1 px-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <FileCheck className="h-3.5 w-3.5 mr-1" /> Docs ({edit.required_documents.length})
              </TabsTrigger>
              <TabsTrigger value="cases" className="text-xs py-1 px-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <BookOpen className="h-3.5 w-3.5 mr-1" /> Cases ({edit.sample_cases.length})
              </TabsTrigger>
              <TabsTrigger value="sections" className="text-xs py-1 px-2.5 data-[state=active]:bg-white data-[state=active]:shadow-sm">
                <Layers className="h-3.5 w-3.5 mr-1" /> Notes ({edit.custom_sections.length})
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: CORE DETAILS & TASKS */}
            <TabsContent value="core" className="space-y-3 pt-1">
              <Field label={<>Official Title <PolishBtn loading={polishLoading === 'title'} onClick={() => polish('title', 'Title')} /></>}>
                <Input value={edit.title || ''} onChange={(e) => setEdit({ ...edit, title: e.target.value })} className="h-9 text-xs font-semibold" placeholder="e.g. Chief Executive or Managing Director" data-testid="edit-title" />
              </Field>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5">
                <Field label="Skill Level (1–5)">
                  <Select value={String(edit.skill_level || '1')} onValueChange={(v) => setEdit({ ...edit, skill_level: v })}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Skill Level" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Level 1 · Bachelor / higher</SelectItem>
                      <SelectItem value="2">Level 2 · Associate / Diploma</SelectItem>
                      <SelectItem value="3">Level 3 · Cert IV / III</SelectItem>
                      <SelectItem value="4">Level 4 · Cert II / III</SelectItem>
                      <SelectItem value="5">Level 5 · Cert I / Secondary</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="SkillSelect Tier">
                  <Select
                    value={typeof edit.skillselect_tier === 'object' && edit.skillselect_tier !== null
                      ? (edit.skillselect_tier.tier || 'tier_4')
                      : (edit.skillselect_tier || 'tier_4')}
                    onValueChange={(v) => setEdit({ ...edit, skillselect_tier: v })}
                  >
                    <SelectTrigger className="h-8 text-xs bg-white"><SelectValue placeholder="Tier" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="tier_1">Tier 1 (Priority Health & Education)</SelectItem>
                      <SelectItem value="tier_2">Tier 2 (Core Skills / CSOL)</SelectItem>
                      <SelectItem value="tier_3">Tier 3 (MLTSSL Trades & Mgmt)</SelectItem>
                      <SelectItem value="tier_4">Tier 4 (Short-Term / Regional)</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Classification Type">
                  <Input value={edit.classification_type || ''} onChange={(e) => setEdit({ ...edit, classification_type: e.target.value })} className="h-8 text-xs" placeholder="ANZSCO / NOC / TEER" />
                </Field>
                <Field label="Classification Version">
                  <Input value={edit.classification_version || ''} onChange={(e) => setEdit({ ...edit, classification_version: e.target.value })} className="h-8 text-xs" placeholder="e.g. ANZSCO 2013 v1.3" />
                </Field>
              </div>

              <Field label={<>Description / Overview <PolishBtn loading={polishLoading === 'description'} onClick={() => polish('description', 'Description')} /></>}>
                <Textarea value={edit.description || ''} onChange={(e) => setEdit({ ...edit, description: e.target.value })} className="text-xs min-h-[85px] leading-relaxed" placeholder="Detailed occupation overview and core scope of practice…" data-testid="edit-description" />
              </Field>

              <Field label={<>Typical Tasks (one per line) <PolishBtn loading={polishLoading === 'typical_tasks'} onClick={() => polish('typical_tasks', 'Typical Tasks')} /></>}>
                <Textarea value={(edit.typical_tasks || []).join('\n')} onChange={(e) => setEdit({ ...edit, typical_tasks: e.target.value.split('\n').filter(Boolean) })} className="text-xs min-h-[100px] leading-relaxed font-mono" placeholder="Determining overall policy and strategy&#10;Organising and directing general management&#10;Consulting with other executive managers" data-testid="edit-tasks" />
              </Field>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                <Field label="Alternative Titles (comma-separated)">
                  <Input value={(edit.alternative_titles || []).join(', ')} onChange={(e) => setEdit({ ...edit, alternative_titles: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })} className="h-8 text-xs" placeholder="e.g. CEO, Director-General, Executive Officer" data-testid="edit-alt-titles" />
                </Field>
                <Field label="Specialisations (comma-separated)">
                  <Input value={(edit.specialisations || []).join(', ')} onChange={(e) => setEdit({ ...edit, specialisations: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })} className="h-8 text-xs" placeholder="e.g. Managing Director, Chief Executive Officer" />
                </Field>
              </div>

              <Field label="Caveats / Regulatory Notes">
                <Textarea
                  value={typeof edit.caveats === 'string' ? edit.caveats : Array.isArray(edit.caveats) ? edit.caveats.join('\n') : (edit.caveats?.notes || '')}
                  onChange={(e) => setEdit({ ...edit, caveats: e.target.value })}
                  placeholder="e.g. Caveat 1: Minimum annual remuneration AUD $73,150 or regional limitations..."
                  className="text-xs min-h-[50px] bg-white"
                />
              </Field>
            </TabsContent>

            {/* TAB 2: SKILL ASSESSMENT */}
            <TabsContent value="skill" className="space-y-3 pt-1">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                <Field label="Assessing Authority Name">
                  <Input value={edit.assessing_authority?.name || ''} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, name: e.target.value } })} className="h-8 text-xs font-semibold" placeholder="e.g. AIM, VETASSESS, ACS, TRA, CPA" />
                </Field>
                <Field label="Authority Code / Slug">
                  <Input value={edit.assessing_authority?.code || edit.assessing_authority?.body_id || ''} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, code: e.target.value, body_id: e.target.value } })} className="h-8 text-xs" placeholder="e.g. aim, vetassess, acs, tra" />
                </Field>
              </div>

              <Field label="Full Official Authority Name">
                <Input value={edit.assessing_authority?.full_name || ''} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, full_name: e.target.value } })} className="h-8 text-xs" placeholder="e.g. Australian Institute of Management" />
              </Field>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                <Field label="Authority Website URL">
                  <div className="flex gap-1">
                    <Input value={edit.assessing_authority?.website || ''} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, website: e.target.value } })} className="h-8 text-xs flex-1" placeholder="https://..." />
                    {edit.assessing_authority?.website && (
                      <a href={edit.assessing_authority.website} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded border border-slate-200 hover:bg-slate-100 flex items-center justify-center">
                        <ExternalLink className="h-3.5 w-3.5 text-slate-600" />
                      </a>
                    )}
                  </div>
                </Field>
                <Field label="Processing Time (Weeks)">
                  <Input type="number" min="1" max="104" value={edit.assessing_authority?.processing_time_weeks || ''} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, processing_time_weeks: e.target.value } })} className="h-8 text-xs" placeholder="e.g. 6" />
                </Field>
                <Field label="Assessment Fee & Currency">
                  <div className="flex gap-1">
                    <Input type="number" value={edit.assessing_authority?.fee_native || ''} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, fee_native: e.target.value } })} className="h-8 text-xs flex-1" placeholder="e.g. 1050" />
                    <Input value={edit.assessing_authority?.fee_currency || 'AUD'} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, fee_currency: e.target.value.toUpperCase() } })} className="h-8 text-xs w-16 text-center font-bold" placeholder="AUD" />
                  </div>
                </Field>
              </div>

              <Field label="Contact Details (Email / Phone / Address)">
                <Input value={edit.assessing_authority?.contact_details || ''} onChange={(e) => setEdit({ ...edit, assessing_authority: { ...edit.assessing_authority, contact_details: e.target.value } })} className="h-8 text-xs" placeholder="e.g. assessments@aim.com.au · +61 2 9299 1234" />
              </Field>

              <Field label={<>Qualification Rules &amp; Assessment Criteria <PolishBtn loading={polishLoading === 'qualification_rules'} onClick={() => polish('qualification_rules', 'Qualification Rules')} /></>}>
                <Textarea value={edit.qualification_rules || ''} onChange={(e) => setEdit({ ...edit, qualification_rules: e.target.value })} className="text-xs min-h-[90px] leading-relaxed" placeholder="e.g. Requires a Bachelor degree or higher qualification comparable to the educational level of an AQF Bachelor degree + minimum 3 years of highly relevant post-qualification employment at the appropriate senior management level within the last 5 years." />
              </Field>
            </TabsContent>

            {/* TAB 3: VISAS & HIERARCHY */}
            <TabsContent value="visas" className="space-y-3 pt-1">
              <Field label="Recommended Visa Subclasses (e.g. 189, 190, 491, 482)">
                <Input value={typeof edit.recommended_visa_subclass === 'string' ? edit.recommended_visa_subclass : (edit.recommended_visa_subclass?.[item.country_code] || '')} onChange={(e) => setEdit({ ...edit, recommended_visa_subclass: e.target.value })} className="h-8 text-xs font-semibold" placeholder="e.g. 189, 190, 491, 482, 186" />
              </Field>

              <Field label="Similar / Related Occupation Codes Override (comma-separated)">
                <Input value={(edit.similar_codes_override || []).join(', ')} onChange={(e) => setEdit({ ...edit, similar_codes_override: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} className="h-8 text-xs" placeholder="e.g. 111211, 111212, 111411" />
              </Field>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-2.5">
                <p className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-indigo-600" />
                  Classification Hierarchy (ANZSCO / NOC Groups)
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <Field label="Unit Group Code">
                    <Input value={edit.hierarchy?.unit_group || ''} onChange={(e) => setEdit({ ...edit, hierarchy: { ...edit.hierarchy, unit_group: e.target.value } })} className="h-8 text-xs" placeholder="e.g. 1111" />
                  </Field>
                  <Field label="Unit Group Name">
                    <Input value={edit.hierarchy?.unit_group_name || ''} onChange={(e) => setEdit({ ...edit, hierarchy: { ...edit.hierarchy, unit_group_name: e.target.value } })} className="h-8 text-xs" placeholder="e.g. Chief Executives and Managing Directors" />
                  </Field>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <Field label="Minor Group">
                    <Input value={edit.hierarchy?.minor_group || ''} onChange={(e) => setEdit({ ...edit, hierarchy: { ...edit.hierarchy, minor_group: e.target.value } })} className="h-8 text-xs" placeholder="e.g. 111" />
                  </Field>
                  <Field label="Sub-Major Group">
                    <Input value={edit.hierarchy?.sub_major_group || ''} onChange={(e) => setEdit({ ...edit, hierarchy: { ...edit.hierarchy, sub_major_group: e.target.value } })} className="h-8 text-xs" placeholder="e.g. 11" />
                  </Field>
                  <Field label="Major Group">
                    <Input value={edit.hierarchy?.major_group || ''} onChange={(e) => setEdit({ ...edit, hierarchy: { ...edit.hierarchy, major_group: e.target.value } })} className="h-8 text-xs" placeholder="e.g. 1 Managers" />
                  </Field>
                </div>
              </div>
            </TabsContent>

            {/* TAB 4: REQUIRED DOCUMENTS CHECKLIST */}
            <TabsContent value="docs" className="space-y-3 pt-1">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-800">Document Checklist</h4>
                  <p className="text-[10px] text-slate-500">Configure what documents clients must provide for this occupation.</p>
                </div>
                <Button size="sm" onClick={addDocument} className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium">
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add Document
                </Button>
              </div>

              {edit.required_documents.length === 0 ? (
                <div className="text-center py-6 bg-slate-50 rounded-lg border border-dashed border-slate-300 text-slate-500 text-xs">
                  <FileCheck className="h-7 w-7 mx-auto mb-1 text-slate-400 opacity-60" />
                  No documents configured yet.
                  <br />
                  <button type="button" onClick={addDocument} className="text-indigo-600 font-semibold underline mt-1">
                    Add standard required document
                  </button>
                </div>
              ) : (
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                  {edit.required_documents.map((doc, idx) => (
                    <div key={doc.id || idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-2">
                      <Input
                        value={doc.name || ''}
                        onChange={(e) => updateDocument(idx, { name: e.target.value })}
                        placeholder="Document Name (e.g. Degree Certificate, Work Reference)"
                        className="h-8 text-xs flex-1 bg-white"
                      />
                      <Select value={doc.category || 'Qualification'} onValueChange={(v) => updateDocument(idx, { category: v })}>
                        <SelectTrigger className="h-8 text-xs w-36 bg-white"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Identity">Identity</SelectItem>
                          <SelectItem value="Qualification">Qualification</SelectItem>
                          <SelectItem value="Employment">Employment</SelectItem>
                          <SelectItem value="Assessment">Assessment</SelectItem>
                          <SelectItem value="Financial">Financial</SelectItem>
                          <SelectItem value="Other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                      <button
                        type="button"
                        onClick={() => updateDocument(idx, { required: !doc.required })}
                        className={`text-[10px] font-bold px-2 py-1 rounded border ${doc.required ? 'bg-rose-50 text-rose-700 border-rose-300' : 'bg-slate-100 text-slate-600 border-slate-300'}`}
                      >
                        {doc.required ? 'Mandatory' : 'Optional'}
                      </button>
                      <button
                        type="button"
                        onClick={() => removeDocument(idx)}
                        className="p-1 rounded text-slate-400 hover:text-rose-600 transition"
                        title="Remove Document"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* TAB 5: SAMPLE CASES */}
            <TabsContent value="cases" className="space-y-3 pt-1">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-800">Sample Client Cases / Outcomes</h4>
                  <p className="text-[10px] text-slate-500">Add anonymised success profiles to guide sales consultants.</p>
                </div>
                <Button size="sm" onClick={addSampleCase} className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium">
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add Case Study
                </Button>
              </div>

              {edit.sample_cases.length === 0 ? (
                <div className="text-center py-6 bg-slate-50 rounded-lg border border-dashed border-slate-300 text-slate-500 text-xs">
                  <BookOpen className="h-7 w-7 mx-auto mb-1 text-slate-400 opacity-60" />
                  No sample cases added yet.
                  <br />
                  <button type="button" onClick={addSampleCase} className="text-indigo-600 font-semibold underline mt-1">
                    Add a client profile outcome
                  </button>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                  {edit.sample_cases.map((sc, idx) => (
                    <div key={sc.id || idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-wrap flex-1">
                          <Input
                            type="number"
                            min="18"
                            max="70"
                            value={sc.client_age || ''}
                            onChange={(e) => updateSampleCase(idx, { client_age: e.target.value })}
                            placeholder="Age"
                            className="h-7 text-xs w-16"
                          />
                          <Input
                            value={sc.visa_subclass || ''}
                            onChange={(e) => updateSampleCase(idx, { visa_subclass: e.target.value })}
                            placeholder="Visa (e.g. 190)"
                            className="h-7 text-xs w-24"
                          />
                          <Select value={sc.outcome || 'Approved'} onValueChange={(v) => updateSampleCase(idx, { outcome: v })}>
                            <SelectTrigger className="h-7 text-xs w-28"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Approved">Approved</SelectItem>
                              <SelectItem value="Pending">Pending</SelectItem>
                              <SelectItem value="Refused">Refused</SelectItem>
                              <SelectItem value="Withdrawn">Withdrawn</SelectItem>
                            </SelectContent>
                          </Select>
                          <Input
                            type="number"
                            value={sc.timeline_months || ''}
                            onChange={(e) => updateSampleCase(idx, { timeline_months: e.target.value })}
                            placeholder="Timeline (mos)"
                            className="h-7 text-xs w-28"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeSampleCase(idx)}
                          className="p-1 rounded text-slate-400 hover:text-rose-600 transition"
                          title="Remove Case"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      <Input
                        value={sc.profile_summary || ''}
                        onChange={(e) => updateSampleCase(idx, { profile_summary: e.target.value })}
                        placeholder="Profile Summary (e.g. 8 years as CEO of mid-sized enterprise, IELTS 8.0)"
                        className="h-7 text-xs"
                      />
                      <Input
                        value={sc.notes || ''}
                        onChange={(e) => updateSampleCase(idx, { notes: e.target.value })}
                        placeholder="Outcome notes / Key success factors"
                        className="h-7 text-xs"
                      />
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* TAB 6: CUSTOM SECTIONS */}
            <TabsContent value="sections" className="space-y-3 pt-1">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-800">Custom Sections &amp; Markdown Notes</h4>
                  <p className="text-[10px] text-slate-500">Free-form extra knowledge or state-specific criteria.</p>
                </div>
                <Button size="sm" onClick={addCustomSection} className="h-7 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium">
                  <Plus className="h-3.5 w-3.5 mr-1" /> Add Section
                </Button>
              </div>

              {edit.custom_sections.length === 0 ? (
                <div className="text-center py-6 bg-slate-50 rounded-lg border border-dashed border-slate-300 text-slate-500 text-xs">
                  <Layers className="h-7 w-7 mx-auto mb-1 text-slate-400 opacity-60" />
                  No custom sections added yet.
                </div>
              ) : (
                <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                  {edit.custom_sections.map((sec, idx) => (
                    <div key={sec.id || idx} className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <Input
                          value={sec.title || ''}
                          onChange={(e) => updateCustomSection(idx, { title: e.target.value })}
                          placeholder="Section Title (e.g. Victoria State Nomination Requirements)"
                          className="h-7 text-xs font-semibold flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => removeCustomSection(idx)}
                          className="p-1 rounded text-slate-400 hover:text-rose-600 transition"
                          title="Remove Section"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                      <Textarea
                        value={sec.body_markdown || ''}
                        onChange={(e) => updateCustomSection(idx, { body_markdown: e.target.value })}
                        placeholder="Content (Markdown supported)…"
                        className="text-xs min-h-[60px]"
                      />
                      <Input
                        value={sec.source_url || ''}
                        onChange={(e) => updateCustomSection(idx, { source_url: e.target.value })}
                        placeholder="Reference URL (optional, e.g. https://...)"
                        className="h-7 text-xs"
                      />
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </Card>

        {/* ──────────────────────────────────────────────────────────── */}
        {/* COLUMN 3: OFFICIAL SOURCE, ASSESSING BODY & AUDIT (3 cols) */}
        {/* ──────────────────────────────────────────────────────────── */}
        <Card className="lg:col-span-3 p-3.5 bg-gradient-to-br from-blue-50/60 to-slate-50 border-blue-200 space-y-3">
          <div className="pb-2 border-b border-blue-200">
            <h3 className="text-xs font-bold uppercase text-blue-900 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-blue-700" /> Verification Hub &amp; Assessing Body
            </h3>
            <p className="text-[10px] text-blue-700 mt-0.5">
              Designated body fees, official gazettes, and publication control.
            </p>
          </div>

          <div className="space-y-3">
            <Field label="Assessing Authority (Designated Body)">
              <Select value={selectedAuthCode} onValueChange={handleAuthorityChange}>
                <SelectTrigger className="h-8 text-xs bg-white font-medium text-slate-800">
                  <SelectValue placeholder="Select assessing body…" />
                </SelectTrigger>
                <SelectContent className="max-h-72">
                  {authorities.map((a) => (
                    <SelectItem key={a.code} value={a.code}>
                      <span className="font-bold">{a.code}</span> — {a.full_name || a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>

            {/* Live Authority Details & Cascaded Fees */}
            {currentAuthDoc && (
              <div className="p-2.5 rounded border border-blue-200 bg-white space-y-1.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-blue-950">{currentAuthDoc.full_name}</span>
                  <Badge className="text-[9px] bg-blue-100 text-blue-800">{currentAuthDoc.code}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-1 text-[11px] pt-1 border-t border-slate-100">
                  <div>
                    <span className="text-slate-500">Standard Fee:</span>{' '}
                    <strong className="text-emerald-700">AUD ${currentAuthDoc.fees?.msa_fee_aud || '—'}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">RPL Fee:</span>{' '}
                    <strong className="text-emerald-700">AUD ${currentAuthDoc.fees?.rpl_fee_aud || '—'}</strong>
                  </div>
                  <div className="col-span-2">
                    <span className="text-slate-500">Turnaround:</span>{' '}
                    <strong>{Math.round((currentAuthDoc.processing?.standard_days_min || 60) / 7)}–{Math.round((currentAuthDoc.processing?.standard_days_max || 90) / 7)} weeks</strong>
                  </div>
                </div>
                {currentAuthDoc.website && (
                  <a href={currentAuthDoc.website} target="_blank" rel="noreferrer" className="text-[10px] text-blue-600 hover:underline flex items-center gap-1 pt-1">
                    <ExternalLink className="h-2.5 w-2.5" /> Official Website
                  </a>
                )}
              </div>
            )}

            <Field label="Official Source URL (ABS ANZSCO / IRCC NOC)">
              <div className="flex gap-1">
                <Input
                  value={sourceRef}
                  onChange={(e) => setSourceRef(e.target.value)}
                  placeholder="https://www.abs.gov.au/anzsco/..."
                  className="h-8 text-xs flex-1 bg-white font-mono"
                  data-testid="source-ref"
                />
                {sourceRef && (
                  <a href={sourceRef} target="_blank" rel="noopener noreferrer" className="p-1.5 bg-white rounded border border-blue-200 hover:bg-blue-50 flex items-center justify-center" title="Open Link">
                    <ExternalLink className="h-3.5 w-3.5 text-blue-600" />
                  </a>
                )}
              </div>
            </Field>

            <Field label="Review Notes (Audit Record)">
              <Textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                className="text-xs min-h-[70px] bg-white leading-relaxed"
                placeholder="What official gazette or criteria did you double-check…"
                data-testid="review-notes"
              />
            </Field>

            {item.verification?.source_reference && (
              <p className="text-[10px] text-slate-500 italic bg-white p-1.5 rounded border border-slate-200">
                Last verified: {item.verification.source_reference}
              </p>
            )}

            {verifyOpen && (
              <div className="mt-3 pt-3 border-t border-blue-200 space-y-2 bg-blue-100/50 p-2.5 rounded">
                <p className="text-xs font-bold text-blue-950">Confirm Verification &amp; Publishing</p>
                <p className="text-[11px] text-blue-800">All changes will immediately cascade to Smart Sales and Knowledge Hub.</p>
                <Button size="sm" className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold" onClick={verify} disabled={saving || !sourceRef.trim()} data-testid="confirm-verify">
                  {saving ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <CheckCircle2 className="h-3 w-3 mr-1" />}
                  Publish Changes Now
                </Button>
                <Button size="sm" variant="outline" className="w-full bg-white" onClick={() => setVerifyOpen(false)}>Cancel</Button>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-blue-200 space-y-2">
            <Button
              size="sm"
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold h-9 shadow-sm"
              onClick={verify}
              disabled={saving || !sourceRef.trim()}
              data-testid="confirm-verify-btn"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />}
              Verify &amp; Publish
            </Button>
            <p className="text-[9px] text-slate-500 text-center">
              Requires valid Source URL. Creates an immutable audit snapshot.
            </p>
          </div>
        </Card>
      </div>
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
