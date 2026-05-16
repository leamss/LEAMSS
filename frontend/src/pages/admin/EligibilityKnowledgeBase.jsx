/**
 * Phase 6.1 — Eligibility Knowledge Base Admin UI
 *
 * Comprehensive country-rules management for the AI Eligibility Engine.
 *
 * Tabs:
 *   1. Countries  — list / activate / view stats
 *   2. Visas      — per-country visa categories CRUD
 *   3. Skill Bodies — per-country assessment bodies CRUD
 *   4. Occupations  — per-country occupation codes + bulk CSV import
 *   5. Points System — visual editor for points/CRS systems
 *   6. Document Templates — visa-specific / common doc lists
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from '@/components/ui/select';
import {
  ArrowLeft, Globe, Briefcase, Award, ListChecks, Sparkles, FileText,
  Plus, Trash2, Edit, Search, Upload, Download, RefreshCw, AlertCircle,
  CheckCircle2,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────
function useApi() {
  const token = localStorage.getItem('token');
  return useMemo(() => ({ headers: { Authorization: `Bearer ${token}` } }), [token]);
}

function PathwayBadge({ value }) {
  const map = {
    MLTSSL: 'bg-emerald-100 text-emerald-700',
    STSOL: 'bg-amber-100 text-amber-700',
    ROL: 'bg-rose-100 text-rose-700',
    Federal: 'bg-sky-100 text-sky-700',
    'Green List': 'bg-emerald-100 text-emerald-700',
    Provincial: 'bg-indigo-100 text-indigo-700',
    Temporary: 'bg-slate-100 text-slate-700',
  };
  return <Badge className={`${map[value] || 'bg-slate-100 text-slate-700'} text-[10px]`}>{value || '—'}</Badge>;
}


// ═════════════════════════════════════════════════════════════════
// Main Page
// ═════════════════════════════════════════════════════════════════
export default function EligibilityKnowledgeBase() {
  const navigate = useNavigate();
  const cfg = useApi();
  const [countries, setCountries] = useState([]);
  const [stats, setStats] = useState(null);
  const [activeCountry, setActiveCountry] = useState(null);  // country code
  const [activeCountryDoc, setActiveCountryDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('countries');

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        axios.get(`${API}/eligibility/kb/countries`, cfg),
        axios.get(`${API}/eligibility/kb/stats`, cfg),
      ]);
      setCountries(c.data.items || []);
      setStats(s.data);
      if (!activeCountry && c.data.items?.length) {
        setActiveCountry(c.data.items[0].country_code);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to load knowledge base');
    } finally { setLoading(false); }
  }, [cfg, activeCountry]);

  const loadCountryDoc = useCallback(async (code) => {
    if (!code) return;
    try {
      const r = await axios.get(`${API}/eligibility/kb/countries/${code}`, cfg);
      setActiveCountryDoc(r.data);
    } catch (e) { toast.error('Failed to load country'); }
  }, [cfg]);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { if (activeCountry) loadCountryDoc(activeCountry); }, [activeCountry, loadCountryDoc]);

  const refresh = () => { loadList(); if (activeCountry) loadCountryDoc(activeCountry); };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="eligibility-kb-page">
      <div className="max-w-7xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate('/admin')} data-testid="back-btn">
              <ArrowLeft className="h-4 w-4 mr-1" />Back
            </Button>
            <div>
              <h1 className="text-2xl font-semibold flex items-center gap-2">
                <Sparkles className="h-7 w-7 text-indigo-600" /> Eligibility Knowledge Base
              </h1>
              <p className="text-sm text-slate-500">
                Country rules, visa categories, skill bodies, occupation codes, points systems & document templates.
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={refresh} data-testid="refresh-btn">
            <RefreshCw className="h-3.5 w-3.5 mr-1" />Refresh
          </Button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="Countries" value={`${stats.active_countries} / ${stats.total_countries}`} icon={Globe} color="indigo" />
            <StatCard label="Visa Categories" value={stats.total_visa_categories} icon={Briefcase} color="emerald" />
            <StatCard label="Skill Bodies" value={stats.total_skill_bodies} icon={Award} color="amber" />
            <StatCard label="Occupation Codes" value={stats.total_occupations} icon={ListChecks} color="sky" />
            <StatCard label="Avg per Country" value={stats.active_countries ? Math.round(stats.total_occupations / stats.active_countries) : 0} icon={FileText} color="rose" />
          </div>
        )}

        {/* Country selector */}
        {countries.length > 0 && (
          <Card className="p-3">
            <Label className="text-[11px] uppercase font-bold text-slate-500 mb-2 block">Select Country</Label>
            <div className="flex flex-wrap gap-2">
              {countries.map(c => (
                <button
                  key={c.country_code}
                  onClick={() => setActiveCountry(c.country_code)}
                  className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition flex items-center gap-2 ${
                    activeCountry === c.country_code
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-900'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  } ${!c.is_active ? 'opacity-50' : ''}`}
                  data-testid={`country-tab-${c.country_code}`}
                >
                  <span className="text-xl">{c.country_flag_emoji}</span>
                  <span>{c.country}</span>
                  <Badge className="bg-slate-100 text-slate-700 text-[10px]">
                    {c.visa_count}V · {c.skill_body_count}B · {c.occupation_count}O
                  </Badge>
                  {!c.is_active && <span className="text-[9px] text-rose-600 ml-1">DISABLED</span>}
                </button>
              ))}
            </div>
          </Card>
        )}

        {loading && <p className="text-sm text-slate-400 text-center py-10">Loading…</p>}

        {!loading && activeCountryDoc && (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-3">
            <TabsList className="grid grid-cols-6">
              <TabsTrigger value="countries" data-testid="tab-countries"><Globe className="h-3.5 w-3.5 mr-1" />Countries</TabsTrigger>
              <TabsTrigger value="visas" data-testid="tab-visas"><Briefcase className="h-3.5 w-3.5 mr-1" />Visas</TabsTrigger>
              <TabsTrigger value="bodies" data-testid="tab-bodies"><Award className="h-3.5 w-3.5 mr-1" />Skill Bodies</TabsTrigger>
              <TabsTrigger value="occupations" data-testid="tab-occupations"><ListChecks className="h-3.5 w-3.5 mr-1" />Occupations</TabsTrigger>
              <TabsTrigger value="points" data-testid="tab-points"><Sparkles className="h-3.5 w-3.5 mr-1" />Points</TabsTrigger>
              <TabsTrigger value="docs" data-testid="tab-docs"><FileText className="h-3.5 w-3.5 mr-1" />Docs</TabsTrigger>
            </TabsList>

            <TabsContent value="countries"><CountriesTab countries={countries} onRefresh={refresh} /></TabsContent>
            <TabsContent value="visas"><VisasTab country={activeCountryDoc} onRefresh={refresh} /></TabsContent>
            <TabsContent value="bodies"><SkillBodiesTab country={activeCountryDoc} onRefresh={refresh} /></TabsContent>
            <TabsContent value="occupations"><OccupationsTab country={activeCountryDoc} onRefresh={refresh} /></TabsContent>
            <TabsContent value="points"><PointsTab country={activeCountryDoc} onRefresh={refresh} /></TabsContent>
            <TabsContent value="docs"><DocsTab country={activeCountryDoc} /></TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}


function StatCard({ label, value, icon: Icon, color }) {
  const ring = {
    indigo: 'border-l-indigo-500',
    emerald: 'border-l-emerald-500',
    amber: 'border-l-amber-500',
    sky: 'border-l-sky-500',
    rose: 'border-l-rose-500',
  }[color];
  return (
    <Card className={`p-3 border-l-4 ${ring}`}>
      <div className="flex items-center gap-2">
        <Icon className={`h-5 w-5 text-${color}-600`} />
        <p className="text-[10px] font-bold uppercase text-slate-500">{label}</p>
      </div>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </Card>
  );
}


// ─────────────────────────────────────────────────────────────────
// Tab 1 · Countries (list + add new)
// ─────────────────────────────────────────────────────────────────
function CountriesTab({ countries, onRefresh }) {
  const cfg = useApi();
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ country: '', country_code: '', country_flag_emoji: '', priority: 99 });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!form.country || !form.country_code) { toast.error('Country and code required'); return; }
    setSaving(true);
    try {
      await axios.post(`${API}/eligibility/kb/countries`, form, cfg);
      toast.success(`${form.country} added`);
      setAdding(false);
      setForm({ country: '', country_code: '', country_flag_emoji: '', priority: 99 });
      onRefresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    } finally { setSaving(false); }
  };

  const toggleActive = async (c) => {
    try {
      await axios.patch(`${API}/eligibility/kb/countries/${c.country_code}`,
        { is_active: !c.is_active }, cfg);
      toast.success(`${c.country} ${!c.is_active ? 'activated' : 'deactivated'}`);
      onRefresh();
    } catch (e) { toast.error('Update failed'); }
  };

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold">All Countries</h2>
          <p className="text-xs text-slate-500">Manage country activation status and add new countries to the knowledge base.</p>
        </div>
        <Button size="sm" onClick={() => setAdding(true)} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-country-btn">
          <Plus className="h-4 w-4 mr-1" /> Add Country
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {countries.map(c => (
          <Card key={c.country_code} className={`p-4 ${c.is_active ? 'bg-white' : 'bg-slate-50 opacity-75'}`} data-testid={`country-card-${c.country_code}`}>
            <div className="flex items-center gap-3 mb-3">
              <span className="text-4xl">{c.country_flag_emoji}</span>
              <div className="flex-1">
                <p className="font-bold">{c.country}</p>
                <p className="text-[10px] uppercase text-slate-400">{c.country_code}</p>
              </div>
              <Switch
                checked={!!c.is_active}
                onCheckedChange={() => toggleActive(c)}
                data-testid={`toggle-${c.country_code}`}
              />
            </div>
            <div className="grid grid-cols-3 gap-1 text-center text-[10px]">
              <div className="bg-emerald-50 rounded p-1.5">
                <p className="font-bold text-emerald-700">{c.visa_count}</p>
                <p className="text-emerald-600">Visas</p>
              </div>
              <div className="bg-amber-50 rounded p-1.5">
                <p className="font-bold text-amber-700">{c.skill_body_count}</p>
                <p className="text-amber-600">Bodies</p>
              </div>
              <div className="bg-sky-50 rounded p-1.5">
                <p className="font-bold text-sky-700">{c.occupation_count}</p>
                <p className="text-sky-600">Codes</p>
              </div>
            </div>
            {c.last_updated && (
              <p className="text-[10px] text-slate-400 mt-2">
                Updated: {new Date(c.last_updated).toLocaleDateString('en-IN')}
              </p>
            )}
          </Card>
        ))}
      </div>

      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>Add New Country</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label className="text-xs">Country Name *</Label><Input value={form.country} onChange={e => setForm({ ...form, country: e.target.value })} placeholder="e.g., United Kingdom" data-testid="new-country-name" /></div>
            <div><Label className="text-xs">Country Code (2-3 letters) *</Label><Input value={form.country_code} onChange={e => setForm({ ...form, country_code: e.target.value.toUpperCase() })} maxLength={3} placeholder="UK" data-testid="new-country-code" /></div>
            <div><Label className="text-xs">Flag Emoji</Label><Input value={form.country_flag_emoji} onChange={e => setForm({ ...form, country_flag_emoji: e.target.value })} placeholder="🇬🇧" data-testid="new-country-flag" /></div>
            <div><Label className="text-xs">Display Priority (lower = first)</Label><Input type="number" value={form.priority} onChange={e => setForm({ ...form, priority: Number(e.target.value) })} data-testid="new-country-priority" /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAdding(false)}>Cancel</Button>
            <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-new-country">
              {saving ? 'Saving…' : 'Add Country'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}


// ─────────────────────────────────────────────────────────────────
// Tab 2 · Visas
// ─────────────────────────────────────────────────────────────────
function VisasTab({ country, onRefresh }) {
  const cfg = useApi();
  const [editing, setEditing] = useState(null);

  const remove = async (visa) => {
    if (!window.confirm(`Delete visa ${visa.code} - ${visa.name}?`)) return;
    try {
      await axios.delete(`${API}/eligibility/kb/countries/${country.country_code}/visas/${visa.visa_id}`, cfg);
      toast.success('Visa deleted');
      onRefresh();
    } catch (e) { toast.error('Delete failed'); }
  };

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold">{country.country_flag_emoji} {country.country} · Visa Categories ({country.visa_categories?.length || 0})</h2>
          <p className="text-xs text-slate-500">Define visa types, eligibility thresholds, processing times, and costs.</p>
        </div>
        <Button size="sm" onClick={() => setEditing({})} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-visa-btn">
          <Plus className="h-4 w-4 mr-1" /> Add Visa
        </Button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-[10px] uppercase text-slate-600">
            <tr>
              <th className="text-left px-3 py-2">Code</th>
              <th className="text-left px-3 py-2">Name / Type</th>
              <th className="text-center px-3 py-2">Pathway</th>
              <th className="text-center px-3 py-2">Min Points</th>
              <th className="text-center px-3 py-2">Processing</th>
              <th className="text-center px-3 py-2">Cost (₹)</th>
              <th className="text-center px-3 py-2">Status</th>
              <th className="text-right px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(country.visa_categories || []).map(v => (
              <tr key={v.visa_id} className="border-t hover:bg-slate-50" data-testid={`visa-row-${v.visa_id}`}>
                <td className="px-3 py-2 font-bold">{v.code}</td>
                <td className="px-3 py-2">
                  <p className="font-medium">{v.name}</p>
                  <p className="text-[10px] text-slate-500">{v.type}</p>
                </td>
                <td className="px-3 py-2 text-center"><PathwayBadge value={v.pathway_type} /></td>
                <td className="px-3 py-2 text-center">{v.eligibility?.points_minimum ?? '—'}</td>
                <td className="px-3 py-2 text-center text-xs">{v.processing_time?.average_months ? `${v.processing_time.average_months}mo` : '—'}</td>
                <td className="px-3 py-2 text-center text-xs">
                  {v.cost?.average_total_inr ? `₹${(v.cost.average_total_inr/100000).toFixed(1)}L` : '—'}
                </td>
                <td className="px-3 py-2 text-center">
                  <Badge className={v.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}>
                    {v.is_active ? 'Active' : 'Off'}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-right">
                  <Button size="sm" variant="outline" className="h-7 w-7 p-0 mr-1" onClick={() => setEditing(v)} data-testid={`edit-visa-${v.visa_id}`}>
                    <Edit className="h-3 w-3" />
                  </Button>
                  <Button size="sm" variant="outline" className="h-7 w-7 p-0 text-rose-600 border-rose-200" onClick={() => remove(v)} data-testid={`del-visa-${v.visa_id}`}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing !== null && (
        <VisaEditor
          countryCode={country.country_code}
          visa={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); onRefresh(); }}
        />
      )}
    </Card>
  );
}


function VisaEditor({ countryCode, visa, onClose, onSaved }) {
  const cfg = useApi();
  const [form, setForm] = useState({
    visa_id: visa.visa_id || null,
    code: visa.code || '',
    name: visa.name || '',
    type: visa.type || '',
    description: visa.description || '',
    pathway_type: visa.pathway_type || '',
    eligibility: visa.eligibility || { age_min: 18, age_max: 45, points_minimum: 65 },
    processing_time: visa.processing_time || { average_months: 10 },
    cost: visa.cost || { average_total_inr: 500000 },
    required_skill_assessment: visa.required_skill_assessment ?? true,
    is_active: visa.is_active ?? true,
    success_factors: visa.success_factors || [],
  });
  const [saving, setSaving] = useState(false);

  const setEli = (k, v) => setForm(f => ({ ...f, eligibility: { ...f.eligibility, [k]: v } }));

  const save = async () => {
    if (!form.code || !form.name) { toast.error('Code and name required'); return; }
    setSaving(true);
    try {
      await axios.post(`${API}/eligibility/kb/countries/${countryCode}/visas`, form, cfg);
      toast.success('Visa saved');
      onSaved();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{visa.visa_id ? 'Edit Visa' : 'Add New Visa'}</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div><Label className="text-xs">Visa Code *</Label><Input value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} placeholder="189" data-testid="visa-code-input" /></div>
          <div><Label className="text-xs">Pathway Type</Label>
            <Select value={form.pathway_type} onValueChange={v => setForm({ ...form, pathway_type: v })}>
              <SelectTrigger data-testid="visa-pathway-select"><SelectValue placeholder="—" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="MLTSSL">MLTSSL</SelectItem>
                <SelectItem value="STSOL">STSOL</SelectItem>
                <SelectItem value="ROL">ROL</SelectItem>
                <SelectItem value="Federal">Federal</SelectItem>
                <SelectItem value="Green List">Green List</SelectItem>
                <SelectItem value="Provincial">Provincial</SelectItem>
                <SelectItem value="Temporary">Temporary</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2"><Label className="text-xs">Name *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Subclass 189" data-testid="visa-name-input" /></div>
          <div className="col-span-2"><Label className="text-xs">Type / Category</Label><Input value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} placeholder="Skilled Independent (PR)" data-testid="visa-type-input" /></div>
          <div className="col-span-2"><Label className="text-xs">Description</Label><Textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={2} data-testid="visa-desc-input" /></div>

          <div className="col-span-2 border-t pt-2 text-xs font-bold text-slate-600">Eligibility</div>
          <div><Label className="text-xs">Age Min</Label><Input type="number" value={form.eligibility.age_min ?? ''} onChange={e => setEli('age_min', Number(e.target.value))} data-testid="visa-age-min" /></div>
          <div><Label className="text-xs">Age Max</Label><Input type="number" value={form.eligibility.age_max ?? ''} onChange={e => setEli('age_max', Number(e.target.value))} data-testid="visa-age-max" /></div>
          <div><Label className="text-xs">Min Points</Label><Input type="number" value={form.eligibility.points_minimum ?? ''} onChange={e => setEli('points_minimum', Number(e.target.value))} data-testid="visa-min-points" /></div>
          <div><Label className="text-xs">Min Years Experience</Label><Input type="number" value={form.eligibility.experience_minimum_years ?? 0} onChange={e => setEli('experience_minimum_years', Number(e.target.value))} data-testid="visa-min-exp" /></div>

          <div className="col-span-2 border-t pt-2 text-xs font-bold text-slate-600">Timing & Cost</div>
          <div><Label className="text-xs">Avg Processing (months)</Label><Input type="number" value={form.processing_time.average_months ?? ''} onChange={e => setForm({ ...form, processing_time: { ...form.processing_time, average_months: Number(e.target.value) } })} /></div>
          <div><Label className="text-xs">Avg Cost (₹)</Label><Input type="number" value={form.cost.average_total_inr ?? ''} onChange={e => setForm({ ...form, cost: { ...form.cost, average_total_inr: Number(e.target.value) } })} /></div>
          <div className="flex items-center gap-2"><Switch checked={form.required_skill_assessment} onCheckedChange={v => setForm({ ...form, required_skill_assessment: v })} /><Label className="text-xs">Skill Assessment Required</Label></div>
          <div className="flex items-center gap-2"><Switch checked={form.is_active} onCheckedChange={v => setForm({ ...form, is_active: v })} data-testid="visa-active-switch" /><Label className="text-xs">Active</Label></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="visa-save-btn">
            {saving ? 'Saving…' : 'Save Visa'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ─────────────────────────────────────────────────────────────────
// Tab 3 · Skill Bodies
// ─────────────────────────────────────────────────────────────────
function SkillBodiesTab({ country, onRefresh }) {
  const cfg = useApi();
  const [editing, setEditing] = useState(null);

  const remove = async (body) => {
    if (!window.confirm(`Delete ${body.name}?`)) return;
    try {
      await axios.delete(`${API}/eligibility/kb/countries/${country.country_code}/skill-bodies/${body.body_id}`, cfg);
      toast.success('Body deleted');
      onRefresh();
    } catch (e) { toast.error('Delete failed'); }
  };

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold">{country.country_flag_emoji} {country.country} · Skill Assessment Bodies ({country.skill_assessment_bodies?.length || 0})</h2>
          <p className="text-xs text-slate-500">Bodies that assess foreign qualifications for visa applications.</p>
        </div>
        <Button size="sm" onClick={() => setEditing({})} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-body-btn">
          <Plus className="h-4 w-4 mr-1" /> Add Skill Body
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {(country.skill_assessment_bodies || []).map(b => (
          <Card key={b.body_id} className="p-3" data-testid={`body-card-${b.body_id}`}>
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <p className="font-bold text-sm">{b.name}</p>
                <p className="text-[11px] text-slate-500">{b.full_name}</p>
                {b.website && (
                  <a href={b.website} target="_blank" rel="noreferrer" className="text-[10px] text-indigo-600 hover:underline">
                    {b.website.replace(/^https?:\/\//, '')}
                  </a>
                )}
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" className="h-7 w-7 p-0" onClick={() => setEditing(b)} data-testid={`edit-body-${b.body_id}`}>
                  <Edit className="h-3 w-3" />
                </Button>
                <Button size="sm" variant="outline" className="h-7 w-7 p-0 text-rose-600 border-rose-200" onClick={() => remove(b)}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
            <div className="text-[11px] space-y-1">
              <p><span className="text-slate-500">Occupations assessed:</span> <strong>{(b.assesses_occupations || []).length}</strong></p>
              <p><span className="text-slate-500">Fee:</span> <strong>₹{((b.assessment_fee_inr || 0) / 1000).toFixed(0)}K</strong></p>
              <p><span className="text-slate-500">Processing:</span> <strong>{b.processing_time_weeks || '—'} weeks</strong></p>
              <p><span className="text-slate-500">Docs required:</span> <strong>{(b.documents_required || []).length}</strong></p>
            </div>
          </Card>
        ))}
      </div>

      {editing !== null && (
        <SkillBodyEditor
          countryCode={country.country_code}
          body={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); onRefresh(); }}
        />
      )}
    </Card>
  );
}


function SkillBodyEditor({ countryCode, body, onClose, onSaved }) {
  const cfg = useApi();
  const [form, setForm] = useState({
    body_id: body.body_id || null,
    name: body.name || '',
    full_name: body.full_name || '',
    website: body.website || '',
    assesses_occupations: (body.assesses_occupations || []).join(', '),
    documents_required: (body.documents_required || []).join('\n'),
    assessment_fee_inr: body.assessment_fee_inr || 0,
    processing_time_weeks: body.processing_time_weeks || 0,
    criteria_general: body.criteria_general || {},
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!form.name) { toast.error('Body name required'); return; }
    setSaving(true);
    try {
      const payload = {
        ...form,
        assesses_occupations: form.assesses_occupations.split(',').map(s => s.trim()).filter(Boolean),
        documents_required: form.documents_required.split('\n').map(s => s.trim()).filter(Boolean),
      };
      await axios.post(`${API}/eligibility/kb/countries/${countryCode}/skill-bodies`, payload, cfg);
      toast.success('Body saved');
      onSaved();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{body.body_id ? 'Edit Skill Body' : 'Add Skill Body'}</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div><Label className="text-xs">Name (abbreviation) *</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="ACS" data-testid="body-name-input" /></div>
          <div><Label className="text-xs">Full Name</Label><Input value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} placeholder="Australian Computer Society" data-testid="body-full-name" /></div>
          <div className="col-span-2"><Label className="text-xs">Website</Label><Input value={form.website} onChange={e => setForm({ ...form, website: e.target.value })} placeholder="https://acs.org.au" /></div>
          <div><Label className="text-xs">Fee (₹)</Label><Input type="number" value={form.assessment_fee_inr} onChange={e => setForm({ ...form, assessment_fee_inr: Number(e.target.value) })} /></div>
          <div><Label className="text-xs">Processing Time (weeks)</Label><Input type="number" value={form.processing_time_weeks} onChange={e => setForm({ ...form, processing_time_weeks: Number(e.target.value) })} /></div>
          <div className="col-span-2"><Label className="text-xs">Occupations assessed (comma-separated codes)</Label><Input value={form.assesses_occupations} onChange={e => setForm({ ...form, assesses_occupations: e.target.value })} placeholder="261313, 261311, 261312" /></div>
          <div className="col-span-2"><Label className="text-xs">Documents Required (one per line)</Label><Textarea value={form.documents_required} onChange={e => setForm({ ...form, documents_required: e.target.value })} rows={5} placeholder="Bachelor's degree certificate&#10;Transcripts&#10;Employment letters" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="body-save-btn">
            {saving ? 'Saving…' : 'Save Body'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ─────────────────────────────────────────────────────────────────
// Tab 4 · Occupations (with bulk CSV import)
// ─────────────────────────────────────────────────────────────────
function OccupationsTab({ country, onRefresh }) {
  const cfg = useApi();
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState('');
  const [importing, setImporting] = useState(false);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return (country.occupation_codes || []).filter(o =>
      !q || o.code?.toLowerCase().includes(q) || o.title?.toLowerCase().includes(q)
    );
  }, [country, search]);

  const remove = async (o) => {
    if (!window.confirm(`Delete ${o.code} - ${o.title}?`)) return;
    try {
      await axios.delete(`${API}/eligibility/kb/countries/${country.country_code}/occupations/${o.code}`, cfg);
      toast.success('Occupation deleted');
      onRefresh();
    } catch (e) { toast.error('Delete failed'); }
  };

  const handleImport = async (file) => {
    if (!file) return;
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/eligibility/kb/countries/${country.country_code}/bulk-import-occupations`, fd, {
        headers: { ...cfg.headers, 'Content-Type': 'multipart/form-data' },
      });
      const { inserted, updated, total_errors } = r.data;
      toast.success(`Imported ${inserted} new, updated ${updated}${total_errors ? `, ${total_errors} errors` : ''}`);
      if (r.data.errors?.length) console.warn('CSV errors:', r.data.errors);
      onRefresh();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Import failed'); }
    finally { setImporting(false); }
  };

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h2 className="text-lg font-bold">{country.country_flag_emoji} {country.country} · Occupation Codes ({country.occupation_codes?.length || 0})</h2>
          <p className="text-xs text-slate-500">ANZSCO / NOC / NZ codes mapped to skill bodies and eligible visas.</p>
        </div>
        <div className="flex gap-2">
          <label className="cursor-pointer">
            <input type="file" accept=".csv" hidden onChange={e => handleImport(e.target.files?.[0])} disabled={importing} data-testid="bulk-import-input" />
            <span className="inline-flex items-center gap-1.5 h-9 px-3 bg-emerald-600 text-white text-sm font-medium rounded hover:bg-emerald-700">
              <Upload className="h-4 w-4" />{importing ? 'Importing…' : 'Bulk CSV Import'}
            </span>
          </label>
          <Button size="sm" onClick={() => setEditing({})} className="bg-indigo-600 hover:bg-indigo-700" data-testid="add-occ-btn">
            <Plus className="h-4 w-4 mr-1" /> Add Code
          </Button>
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded p-2 mb-3 text-[11px] text-amber-800 flex items-start gap-2">
        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
        <span>
          <strong>CSV columns:</strong> <code className="bg-white px-1 rounded">code, title, group, group_code, skill_level, assessing_body, pathway, eligible_visas, alternative_titles</code> (pipe-separated for arrays). State demand columns optional (<code>state_demand_NSW, state_demand_VIC, ...</code>). Max 2 MB.
        </span>
      </div>

      <div className="relative mb-3">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by code or title…" className="pl-9" data-testid="occ-search" />
      </div>

      <div className="overflow-x-auto border rounded">
        <table className="w-full text-xs">
          <thead className="bg-slate-100 text-[10px] uppercase text-slate-600">
            <tr>
              <th className="text-left px-3 py-2">Code</th>
              <th className="text-left px-3 py-2">Title</th>
              <th className="text-left px-3 py-2">Group</th>
              <th className="text-center px-3 py-2">Skill</th>
              <th className="text-left px-3 py-2">Body</th>
              <th className="text-center px-3 py-2">Pathway</th>
              <th className="text-left px-3 py-2">Eligible Visas</th>
              <th className="text-right px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={8} className="text-center text-slate-400 py-6">No occupations match.</td></tr>
            )}
            {filtered.slice(0, 200).map(o => (
              <tr key={o.code} className="border-t hover:bg-slate-50" data-testid={`occ-row-${o.code}`}>
                <td className="px-3 py-2 font-bold">{o.code}</td>
                <td className="px-3 py-2">{o.title}</td>
                <td className="px-3 py-2 text-[10px] text-slate-500">{o.group || '—'}</td>
                <td className="px-3 py-2 text-center">{o.skill_level ?? '—'}</td>
                <td className="px-3 py-2">{o.assessing_body || '—'}</td>
                <td className="px-3 py-2 text-center"><PathwayBadge value={o.pathway} /></td>
                <td className="px-3 py-2 text-[10px]">{(o.eligible_visas || []).join(', ') || '—'}</td>
                <td className="px-3 py-2 text-right">
                  <Button size="sm" variant="outline" className="h-6 w-6 p-0 mr-1" onClick={() => setEditing(o)} data-testid={`edit-occ-${o.code}`}>
                    <Edit className="h-3 w-3" />
                  </Button>
                  <Button size="sm" variant="outline" className="h-6 w-6 p-0 text-rose-600 border-rose-200" onClick={() => remove(o)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 200 && (
          <p className="text-[11px] text-slate-400 text-center p-2 bg-slate-50">
            Showing first 200 of {filtered.length}. Use search to narrow down.
          </p>
        )}
      </div>

      {editing !== null && (
        <OccupationEditor
          countryCode={country.country_code}
          occ={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); onRefresh(); }}
        />
      )}
    </Card>
  );
}


function OccupationEditor({ countryCode, occ, onClose, onSaved }) {
  const cfg = useApi();
  const [form, setForm] = useState({
    code: occ.code || '',
    title: occ.title || '',
    group: occ.group || '',
    group_code: occ.group_code || '',
    skill_level: occ.skill_level || 1,
    assessing_body: occ.assessing_body || '',
    pathway: occ.pathway || '',
    alternative_titles: (occ.alternative_titles || []).join(', '),
    eligible_visas: (occ.eligible_visas || []).join(', '),
    description: occ.description || '',
  });
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!form.code || !form.title) { toast.error('Code and title required'); return; }
    setSaving(true);
    try {
      const payload = {
        ...form,
        alternative_titles: form.alternative_titles.split(',').map(s => s.trim()).filter(Boolean),
        eligible_visas: form.eligible_visas.split(',').map(s => s.trim()).filter(Boolean),
        skill_level: form.skill_level === '' ? null : Number(form.skill_level),
      };
      await axios.post(`${API}/eligibility/kb/countries/${countryCode}/occupations`, payload, cfg);
      toast.success('Occupation saved');
      onSaved();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle>{occ.code ? 'Edit Occupation' : 'Add Occupation'}</DialogTitle></DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div><Label className="text-xs">Code *</Label><Input value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} placeholder="261313" data-testid="occ-code-input" /></div>
          <div><Label className="text-xs">Title *</Label><Input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Software Engineer" data-testid="occ-title-input" /></div>
          <div><Label className="text-xs">Group</Label><Input value={form.group} onChange={e => setForm({ ...form, group: e.target.value })} placeholder="ICT Professionals" /></div>
          <div><Label className="text-xs">Group Code</Label><Input value={form.group_code} onChange={e => setForm({ ...form, group_code: e.target.value })} placeholder="261" /></div>
          <div><Label className="text-xs">Skill Level (1-5)</Label><Input type="number" min={1} max={5} value={form.skill_level} onChange={e => setForm({ ...form, skill_level: e.target.value })} /></div>
          <div><Label className="text-xs">Assessing Body</Label><Input value={form.assessing_body} onChange={e => setForm({ ...form, assessing_body: e.target.value })} placeholder="ACS" /></div>
          <div><Label className="text-xs">Pathway</Label><Input value={form.pathway} onChange={e => setForm({ ...form, pathway: e.target.value })} placeholder="MLTSSL" /></div>
          <div className="col-span-2"><Label className="text-xs">Alternative Titles (comma-separated)</Label><Input value={form.alternative_titles} onChange={e => setForm({ ...form, alternative_titles: e.target.value })} placeholder="Software Developer, Application Programmer" /></div>
          <div className="col-span-2"><Label className="text-xs">Eligible Visas (comma-separated)</Label><Input value={form.eligible_visas} onChange={e => setForm({ ...form, eligible_visas: e.target.value })} placeholder="189, 190, 491, 482" /></div>
          <div className="col-span-2"><Label className="text-xs">Description</Label><Textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={3} /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="occ-save-btn">
            {saving ? 'Saving…' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


// ─────────────────────────────────────────────────────────────────
// Tab 5 · Points System (read-only visual + JSON editor)
// ─────────────────────────────────────────────────────────────────
function PointsTab({ country, onRefresh }) {
  const cfg = useApi();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  const ps = country.points_system || {};

  const startEdit = () => { setDraft(JSON.stringify(ps, null, 2)); setEditing(true); };

  const save = async () => {
    try {
      const parsed = JSON.parse(draft);
      setSaving(true);
      await axios.patch(`${API}/eligibility/kb/countries/${country.country_code}`, { points_system: parsed }, cfg);
      toast.success('Points system updated');
      setEditing(false);
      onRefresh();
    } catch (e) {
      if (e instanceof SyntaxError) toast.error('Invalid JSON');
      else toast.error(e?.response?.data?.detail || 'Save failed');
    } finally { setSaving(false); }
  };

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold">{country.country_flag_emoji} {country.country} · Points System</h2>
          <p className="text-xs text-slate-500">Categories and point values used for eligibility scoring.</p>
        </div>
        {!editing && (
          <Button size="sm" variant="outline" onClick={startEdit} data-testid="edit-points-btn">
            <Edit className="h-4 w-4 mr-1" />Edit JSON
          </Button>
        )}
      </div>

      {!editing ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(ps).map(([category, values]) => (
            <Card key={category} className="p-3 bg-slate-50">
              <p className="text-[10px] font-bold uppercase text-indigo-700 mb-2">{category.replace(/_/g, ' ')}</p>
              {typeof values === 'object' ? (
                <div className="space-y-1 text-xs">
                  {Object.entries(values).map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-slate-200 py-0.5">
                      <span className="text-slate-600">{k.replace(/_/g, ' ')}</span>
                      <strong className="text-slate-800">{String(v)}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs">{String(values)}</p>
              )}
            </Card>
          ))}
          {Object.keys(ps).length === 0 && (
            <Card className="p-6 col-span-2 text-center text-sm text-slate-400">
              No points system configured. Click "Edit JSON" to add one.
            </Card>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <Textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={20}
            className="font-mono text-xs"
            data-testid="points-json-editor"
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            <Button onClick={save} disabled={saving} className="bg-indigo-600 hover:bg-indigo-700" data-testid="save-points-json">
              <CheckCircle2 className="h-4 w-4 mr-1" />{saving ? 'Saving…' : 'Save Points'}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}


// ─────────────────────────────────────────────────────────────────
// Tab 6 · Document Templates (read-only summary)
// ─────────────────────────────────────────────────────────────────
function DocsTab({ country }) {
  const dt = country.document_templates || {};
  return (
    <Card className="p-5">
      <h2 className="text-lg font-bold mb-1">{country.country_flag_emoji} {country.country} · Document Templates</h2>
      <p className="text-xs text-slate-500 mb-4">Common identity, visa-specific, body-specific, and occupation-specific documents.</p>

      {dt.common_identity?.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-bold text-slate-700 mb-2">Common Identity Documents</p>
          <ul className="text-xs space-y-1">
            {dt.common_identity.map((d, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className={d.required ? 'text-rose-500 font-bold' : 'text-slate-300'}>●</span>
                <span>{d.name}{d.required && <span className="text-rose-500 text-[10px]"> (required)</span>}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {dt.visa_specific && Object.keys(dt.visa_specific).length > 0 && (
        <div>
          <p className="text-xs font-bold text-slate-700 mb-2">Visa-Specific Documents</p>
          {Object.entries(dt.visa_specific).map(([visaCode, docs]) => (
            <div key={visaCode} className="mb-3 bg-slate-50 rounded p-2">
              <p className="text-[11px] font-bold text-indigo-700 mb-1">{visaCode}</p>
              <ul className="text-xs space-y-0.5">
                {(docs || []).map((d, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className={d.required ? 'text-rose-500 font-bold' : 'text-slate-300'}>●</span>
                    <span>{d.name}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {(!dt.common_identity?.length && !Object.keys(dt.visa_specific || {}).length) && (
        <p className="text-sm text-slate-400 italic text-center py-6">
          No document templates configured. These will be populated as the Phase 6.5 (Checklist Integration) is built.
        </p>
      )}
    </Card>
  );
}
