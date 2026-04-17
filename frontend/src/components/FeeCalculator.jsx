import { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import EstimateLeadsPanel from '@/components/EstimateLeadsPanel';
import {
  Calculator, Plane, Globe, Users, CheckCircle2, Info,
  Copy, Download, ExternalLink, Loader2, Wallet,
  IndianRupee, Sparkles, RefreshCw, Receipt, Shield,
  Share2, Link2, Eye, UserPlus, Power, Clock,
  Edit2, Plus, Trash2, Check, X as XIcon, Pencil
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CURRENCY_SYMBOL = {
  INR: '₹', USD: '$', CAD: 'C$', AUD: 'A$', GBP: '£', EUR: '€',
  NZD: 'NZ$', SGD: 'S$', JPY: '¥', SEK: 'kr', DKK: 'kr', CHF: 'Fr',
  HKD: 'HK$', MYR: 'RM', KRW: '₩', AED: 'د.إ',
};

const fmt = (num, cur = 'INR') => {
  if (num == null) return '--';
  const sym = CURRENCY_SYMBOL[cur] || '';
  const n = Number(num);
  try {
    if (cur === 'INR') return `${sym}${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    return `${sym}${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  } catch {
    return `${sym}${Math.round(n)}`;
  }
};

/**
 * FeeCalculator — Premium government fee calculator widget.
 *
 * Props:
 *   token        — auth token
 *   role         — 'partner' | 'case_manager' | 'admin' | 'client'
 *   defaultCountry, defaultCategory — optional pre-selection
 *   caseId, saleId — optional, enables 'Save to Case/Proposal'
 *   compact      — boolean; tighter layout for side panels
 */
export default function FeeCalculator({
  token,
  role = 'partner',
  defaultCountry = '',
  defaultCategory = '',
  caseId = null,
  saleId = null,
  compact = false,
}) {
  const [countries, setCountries] = useState([]);
  const [country, setCountry] = useState(defaultCountry);
  const [countryDetail, setCountryDetail] = useState(null);
  const [category, setCategory] = useState(defaultCategory);
  const [adults, setAdults] = useState(1);
  const [children, setChildren] = useState(0);
  const [serviceFee, setServiceFee] = useState(0);
  const [gstPct, setGstPct] = useState(18);
  const [selectedOptionals, setSelectedOptionals] = useState(new Set());
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showCurrency, setShowCurrency] = useState('both'); // native | inr | both
  const [rates, setRates] = useState(null);
  const [activeView, setActiveView] = useState('calculator');
  const [savedEstimates, setSavedEstimates] = useState([]);
  const [shareDialog, setShareDialog] = useState({ open: false, estimate: null, stats: null, link: '', loading: false });
  const [overrides, setOverrides] = useState({}); // { feeId: { label?, amount?, notes? } }
  const [extraLines, setExtraLines] = useState([]); // [{ id, label, amount, mandatory, per_applicant, notes }]
  const [editingLineId, setEditingLineId] = useState(null);

  // Load countries
  useEffect(() => {
    if (!token) return;
    axios.get(`${API}/fee-calculator/countries`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setCountries(r.data.countries || []))
      .catch(() => toast.error('Failed to load countries'));
    axios.get(`${API}/fee-calculator/exchange-rates`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setRates(r.data))
      .catch(() => {});
  }, [token]);

  // Load country detail on country change
  useEffect(() => {
    if (!country || !token) { setCountryDetail(null); return; }
    axios.get(`${API}/fee-calculator/country/${country}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        setCountryDetail(r.data);
        // Pick first category if none chosen or category not in this country
        if (!category || !r.data.categories?.[category]) {
          const firstCat = Object.keys(r.data.categories || {})[0] || '';
          setCategory(firstCat);
        }
      })
      .catch(() => toast.error('Failed to load country detail'));
  }, [country, token]); // eslint-disable-line

  // Load saved estimates (per-case/sale if provided, else user's own)
  const loadEstimates = useCallback(async () => {
    if (!token) return;
    try {
      const params = {};
      if (caseId) params.case_id = caseId;
      if (saleId) params.sale_id = saleId;
      const r = await axios.get(`${API}/fee-calculator/estimates`, {
        headers: { Authorization: `Bearer ${token}` }, params,
      });
      setSavedEstimates(r.data.estimates || []);
    } catch { /* ignore */ }
  }, [token, caseId, saleId]);
  useEffect(() => { loadEstimates(); }, [loadEstimates]);

  const activeCategory = countryDetail?.categories?.[category];
  const optionalFees = useMemo(() => {
    if (!activeCategory) return [];
    return (activeCategory.fees || [])
      .map((f, idx) => ({ ...f, id: f.id || `${category}_${idx}` }))
      .filter(f => !f.mandatory);
  }, [activeCategory, category]);

  // Reset overrides/extras when country or category changes
  useEffect(() => {
    setOverrides({});
    setExtraLines([]);
    setEditingLineId(null);
  }, [country, category]);

  // Auto-calculate debounce
  useEffect(() => {
    if (!country || !category || !token) return;
    const h = setTimeout(() => doCalculate(), 250);
    return () => clearTimeout(h);
    // eslint-disable-next-line
  }, [country, category, adults, children, serviceFee, gstPct, selectedOptionals, token, overrides, extraLines]);

  const doCalculate = async () => {
    if (!country || !category) return;
    setLoading(true);
    try {
      const overridesArr = Object.entries(overrides).map(([id, o]) => ({ id, ...o }));
      const r = await axios.post(`${API}/fee-calculator/calculate`, {
        country,
        category,
        adults,
        children,
        include_optional_ids: Array.from(selectedOptionals),
        service_fee_inr: Number(serviceFee) || 0,
        gst_pct: Number(gstPct) || 0,
        overrides: overridesArr,
        extra_lines: extraLines,
      }, { headers: { Authorization: `Bearer ${token}` } });
      setResult(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Calculation failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleOptional = (id) => {
    const next = new Set(selectedOptionals);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelectedOptionals(next);
  };

  const handleCopyBreakdown = () => {
    if (!result) return;
    const lines = [
      `Fee Estimate — ${result.country.name} ${result.country.flag}`,
      `Category: ${result.category.name}`,
      `Processing: ${result.category.processing_days} days`,
      `Applicants: ${result.applicants.adults} adult(s), ${result.applicants.children} child(ren)`,
      '',
      'Government Fees:',
      ...result.line_items.filter(li => li.selected).map(li =>
        `  • ${li.label}${li.multiplier > 1 ? ` (x${li.multiplier})` : ''} — ${fmt(li.total_native, result.country.currency)} / ${fmt(li.total_inr, 'INR')}`
      ),
      '',
      `Govt Total: ${fmt(result.totals.govt_fees_native, result.country.currency)} / ${fmt(result.totals.govt_fees_inr, 'INR')}`,
      `Service Fee: ${fmt(result.totals.service_fee_inr, 'INR')}`,
      `GST (${result.totals.gst_pct}%): ${fmt(result.totals.gst_amount_inr, 'INR')}`,
      '━━━━━━━━━━━━━━━━━━━━━━',
      `GRAND TOTAL: ${fmt(result.totals.grand_total_inr, 'INR')}`,
    ];
    navigator.clipboard.writeText(lines.join('\n')).then(() => toast.success('Breakdown copied to clipboard'));
  };

  const handleSave = async () => {
    if (!result) return;
    const label = `${result.country.name} — ${result.category.name}`;
    try {
      const r = await axios.post(`${API}/fee-calculator/save-estimate`, {
        label, country, category, payload: result, case_id: caseId, sale_id: saleId,
      }, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Estimate saved');
      loadEstimates();
      return r.data;
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Save failed');
    }
  };

  const handleShareNew = async () => {
    if (!result) return;
    setShareDialog(s => ({ ...s, loading: true, open: true }));
    try {
      // Save first if new
      const label = `${result.country.name} — ${result.category.name}`;
      const saved = await axios.post(`${API}/fee-calculator/save-estimate`, {
        label, country, category, payload: result, case_id: caseId, sale_id: saleId,
      }, { headers: { Authorization: `Bearer ${token}` } });
      const est = saved.data;
      await openShareForEstimate(est);
      loadEstimates();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Share failed');
      setShareDialog({ open: false, estimate: null, stats: null, link: '', loading: false });
    }
  };

  const openShareForEstimate = async (estimate, opts = { expiry_days: 30, allow_lead_capture: true, message: '' }) => {
    setShareDialog({ open: true, estimate, stats: null, link: '', loading: true });
    try {
      const r = await axios.post(`${API}/fee-calculator/share/${estimate.id}`,
        opts, { headers: { Authorization: `Bearer ${token}` } });
      const base = window.location.origin;
      const link = `${base}/shared-estimate/${r.data.share_token}`;
      const statsRes = await axios.get(`${API}/fee-calculator/share/${estimate.id}/stats`,
        { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: null }));
      setShareDialog({ open: true, estimate, stats: statsRes.data, link, loading: false });
      try {
        await navigator.clipboard.writeText(link);
        toast.success('Share link copied to clipboard');
      } catch { /* ignore */ }
      loadEstimates();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not create share link');
      setShareDialog({ open: false, estimate: null, stats: null, link: '', loading: false });
    }
  };

  const refreshShareStats = async () => {
    if (!shareDialog.estimate) return;
    try {
      const r = await axios.get(`${API}/fee-calculator/share/${shareDialog.estimate.id}/stats`,
        { headers: { Authorization: `Bearer ${token}` } });
      setShareDialog(s => ({ ...s, stats: r.data }));
      toast.success('Stats refreshed');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to refresh stats');
    }
  };

  const deactivateShare = async () => {
    if (!shareDialog.estimate) return;
    try {
      await axios.put(`${API}/fee-calculator/share/${shareDialog.estimate.id}/deactivate`,
        {}, { headers: { Authorization: `Bearer ${token}` } });
      toast.success('Share link deactivated');
      setShareDialog({ open: false, estimate: null, stats: null, link: '', loading: false });
      loadEstimates();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to deactivate');
    }
  };

  const copyShareLink = () => {
    if (!shareDialog.link) return;
    navigator.clipboard.writeText(shareDialog.link).then(() => toast.success('Link copied'));
  };

  const handlePrint = () => window.print();

  // ---- UI helpers
  const AmountCell = ({ native, inr, cur }) => {
    if (showCurrency === 'native') return <span className="font-medium">{fmt(native, cur)}</span>;
    if (showCurrency === 'inr') return <span className="font-medium">{fmt(inr, 'INR')}</span>;
    return (
      <span className="font-medium whitespace-nowrap">
        {fmt(native, cur)} <span className="text-slate-400">/</span> <span className="text-[#2a777a]">{fmt(inr, 'INR')}</span>
      </span>
    );
  };

  return (
    <div className="space-y-5" data-testid="fee-calculator">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <div className="p-2 bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] rounded-lg text-white">
              <Calculator className="h-5 w-5" />
            </div>
            Government Fee Calculator
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Live breakdown · {countries.length} countries · Official 2025-26 fees · Auto ₹INR conversion
          </p>
        </div>
        {rates?.fetched_at && (
          <div className="text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-lg border border-slate-200 flex items-center gap-2">
            <RefreshCw className="h-3 w-3 text-emerald-600" />
            <span>Rates synced <span className="font-medium">{new Date(rates.fetched_at).toLocaleTimeString()}</span></span>
          </div>
        )}
      </div>

      {role !== 'client' && (
        <Tabs value={activeView} onValueChange={setActiveView} className="space-y-0">
          <TabsList className="bg-slate-100">
            <TabsTrigger value="calculator" data-testid="fc-tab-calculator">
              <Calculator className="h-4 w-4 mr-1.5" /> Calculator
            </TabsTrigger>
            <TabsTrigger value="leads" data-testid="fc-tab-leads">
              <Sparkles className="h-4 w-4 mr-1.5" /> Captured Leads
            </TabsTrigger>
          </TabsList>
        </Tabs>
      )}

      {activeView === 'leads' && role !== 'client' ? (
        <EstimateLeadsPanel token={token} role={role} />
      ) : (
      <>
      <div className={`grid ${compact ? 'grid-cols-1' : 'lg:grid-cols-5'} gap-5`}>
        {/* Left — Inputs */}
        <Card className={`${compact ? '' : 'lg:col-span-2'} p-5 bg-white border-slate-200 space-y-4`}>
          <div>
            <Label className="text-sm font-semibold text-slate-700 flex items-center gap-1.5"><Globe className="h-3.5 w-3.5" /> Destination Country</Label>
            <Select value={country} onValueChange={(v) => { setCountry(v); setCategory(''); setSelectedOptionals(new Set()); }}>
              <SelectTrigger className="mt-1.5" data-testid="fc-country-select">
                <SelectValue placeholder="Choose country" />
              </SelectTrigger>
              <SelectContent className="max-h-80">
                {countries.map(c => (
                  <SelectItem key={c.id} value={c.id}>
                    <span className="flex items-center gap-2">
                      <span className="text-lg leading-none">{c.flag}</span>
                      <span>{c.name}</span>
                      <span className="text-xs text-slate-400">({c.currency})</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-sm font-semibold text-slate-700 flex items-center gap-1.5"><Plane className="h-3.5 w-3.5" /> Visa Category</Label>
            <Select value={category} onValueChange={(v) => { setCategory(v); setSelectedOptionals(new Set()); }} disabled={!countryDetail}>
              <SelectTrigger className="mt-1.5" data-testid="fc-category-select">
                <SelectValue placeholder={countryDetail ? 'Choose category' : 'Select country first'} />
              </SelectTrigger>
              <SelectContent className="max-h-80">
                {countryDetail && Object.entries(countryDetail.categories).map(([id, cat]) => (
                  <SelectItem key={id} value={id}>{cat.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {activeCategory?.official_url && (
              <a href={activeCategory.official_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 mt-1.5 text-xs text-[#2a777a] hover:underline">
                <ExternalLink className="h-3 w-3" /> Official source
              </a>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-sm font-semibold text-slate-700 flex items-center gap-1.5"><Users className="h-3.5 w-3.5" /> Adults</Label>
              <Input type="number" min={1} max={10} value={adults}
                onChange={(e) => setAdults(Math.max(1, Number(e.target.value) || 1))}
                className="mt-1.5" data-testid="fc-adults-input" />
            </div>
            <div>
              <Label className="text-sm font-semibold text-slate-700">Children</Label>
              <Input type="number" min={0} max={10} value={children}
                onChange={(e) => setChildren(Math.max(0, Number(e.target.value) || 0))}
                className="mt-1.5" data-testid="fc-children-input" />
            </div>
          </div>

          {optionalFees.length > 0 && (
            <div>
              <Label className="text-sm font-semibold text-slate-700">Optional Add-ons</Label>
              <div className="mt-1.5 space-y-2">
                {optionalFees.map(f => (
                  <label key={f.id} className="flex items-start gap-2 p-2 rounded-md border border-slate-200 hover:border-[#2a777a] cursor-pointer transition-colors">
                    <Checkbox
                      checked={selectedOptionals.has(f.id)}
                      onCheckedChange={() => toggleOptional(f.id)}
                      className="mt-0.5"
                      data-testid={`fc-optional-${f.id}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-700 leading-tight">{f.label}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {fmt(f.amount, countryDetail?.currency || 'USD')}{f.per_applicant ? ' / applicant' : ''}
                        {f.notes && <span className="ml-1 text-slate-400">— {f.notes}</span>}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {(role === 'partner' || role === 'admin' || role === 'case_manager') && (
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
              <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
                <Wallet className="h-4 w-4 text-[#f7620b]" /> Consultancy Service Fee
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs text-slate-600">Service Fee (₹)</Label>
                  <Input type="number" min={0} value={serviceFee}
                    onChange={(e) => setServiceFee(Number(e.target.value) || 0)}
                    placeholder="e.g. 150000" className="mt-1" data-testid="fc-service-fee" />
                </div>
                <div>
                  <Label className="text-xs text-slate-600">GST (%)</Label>
                  <Input type="number" min={0} max={50} step={0.5} value={gstPct}
                    onChange={(e) => setGstPct(Number(e.target.value) || 0)}
                    className="mt-1" data-testid="fc-gst" />
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-slate-100">
            <Label className="text-xs text-slate-600">Display Currency</Label>
            <Select value={showCurrency} onValueChange={setShowCurrency}>
              <SelectTrigger className="w-36 h-8 text-xs" data-testid="fc-display-cur">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="both">Native + ₹INR</SelectItem>
                <SelectItem value="native">Native Only</SelectItem>
                <SelectItem value="inr">₹INR Only</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </Card>

        {/* Right — Breakdown */}
        <Card className={`${compact ? '' : 'lg:col-span-3'} p-5 bg-white border-slate-200 relative overflow-hidden`}>
          {loading && <div className="absolute top-3 right-3"><Loader2 className="h-4 w-4 animate-spin text-[#2a777a]" /></div>}

          {!result ? (
            <div className="text-center py-12 text-slate-400" data-testid="fc-empty-state">
              <Calculator className="h-12 w-12 mx-auto mb-3 text-slate-200" />
              <p className="text-sm">Choose a country & visa category<br />to see live fee breakdown</p>
            </div>
          ) : (
            <div className="space-y-4" data-testid="fc-result">
              {/* Top summary */}
              <div className="bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] text-white p-5 rounded-xl shadow-lg">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-wider opacity-80">Total Estimated Cost</p>
                    <p className="text-3xl font-bold mt-1 flex items-center gap-1" data-testid="fc-grand-total">
                      <IndianRupee className="h-6 w-6" />
                      {result.totals.grand_total_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs opacity-80 mt-1">
                      {fmt(result.totals.govt_fees_native, result.country.currency)} govt fees + service charges
                    </p>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="text-5xl leading-none">{result.country.flag}</div>
                    <Badge className="bg-white/20 text-white border-white/30 hover:bg-white/20">
                      {result.category.processing_days} days
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Line items */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
                    <Receipt className="h-4 w-4 text-[#2a777a]" /> Government Fees Breakdown
                    {Object.keys(overrides).length > 0 && (
                      <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-xs">
                        <Pencil className="h-2.5 w-2.5 mr-1" /> {Object.keys(overrides).length} edited
                      </Badge>
                    )}
                  </h3>
                  <span className="text-xs text-slate-400">
                    1 {result.country.currency} = ₹{result.exchange_rate.native_to_inr.toFixed(2)}
                  </span>
                </div>
                <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100">
                  {result.line_items.filter(li => li.selected).map((li, idx) => {
                    const isEditing = editingLineId === li.id;
                    const isExtra = li.source === 'extra';
                    return (
                    <div key={li.id} className={`px-3 py-2.5 text-sm ${isEditing ? 'bg-amber-50' : 'hover:bg-slate-50'}`} data-testid={`fc-line-${idx}`}>
                      {isEditing ? (
                        <LineEditor
                          line={li}
                          isExtra={isExtra}
                          cur={result.country.currency}
                          onCancel={() => setEditingLineId(null)}
                          onSave={(patch) => {
                            if (isExtra) {
                              setExtraLines(arr => arr.map(x => x.id === li.id ? { ...x, ...patch } : x));
                            } else {
                              setOverrides(o => ({ ...o, [li.id]: { ...(o[li.id] || {}), ...patch } }));
                            }
                            setEditingLineId(null);
                          }}
                          onReset={() => {
                            if (isExtra) {
                              setExtraLines(arr => arr.filter(x => x.id !== li.id));
                            } else {
                              const next = { ...overrides };
                              delete next[li.id];
                              setOverrides(next);
                            }
                            setEditingLineId(null);
                          }}
                        />
                      ) : (
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-slate-800">{li.label}</span>
                              {li.multiplier > 1 && (
                                <Badge variant="outline" className="text-xs py-0 h-5">×{li.multiplier}</Badge>
                              )}
                              {li.mandatory ? (
                                <Badge className="bg-red-50 text-red-700 border-red-200 text-xs py-0 h-5">Required</Badge>
                              ) : (
                                <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-xs py-0 h-5">Optional</Badge>
                              )}
                              {li.overridden && (
                                <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-xs py-0 h-5">
                                  <Pencil className="h-2.5 w-2.5 mr-0.5" /> Edited
                                </Badge>
                              )}
                              {isExtra && (
                                <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-xs py-0 h-5">
                                  Custom
                                </Badge>
                              )}
                            </div>
                            {li.notes && <p className="text-xs text-slate-400 mt-0.5">{li.notes}</p>}
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="text-right">
                              <AmountCell native={li.total_native} inr={li.total_inr} cur={result.country.currency} />
                            </div>
                            {role !== 'client' && (
                              <Button variant="ghost" size="sm" className="h-7 w-7 p-0"
                                onClick={() => setEditingLineId(li.id)} data-testid={`fc-line-edit-${idx}`}>
                                <Edit2 className="h-3.5 w-3.5 text-slate-500" />
                              </Button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                  })}
                </div>

                {role !== 'client' && (
                  <div className="flex items-center justify-between mt-2">
                    <Button variant="outline" size="sm" onClick={() => {
                      const newId = `extra_${Date.now()}`;
                      setExtraLines(arr => [...arr, { id: newId, label: 'Custom charge', amount: 0, mandatory: true, per_applicant: false, notes: '' }]);
                      setEditingLineId(newId);
                    }} data-testid="fc-add-line">
                      <Plus className="h-3.5 w-3.5 mr-1" /> Add Custom Line
                    </Button>
                    {(Object.keys(overrides).length > 0 || extraLines.length > 0) && (
                      <Button variant="ghost" size="sm" className="text-slate-500 hover:text-red-600"
                        onClick={() => { setOverrides({}); setExtraLines([]); toast.success('Reverted to catalog values'); }}
                        data-testid="fc-reset-overrides">
                        <RefreshCw className="h-3.5 w-3.5 mr-1" /> Reset all edits
                      </Button>
                    )}
                  </div>
                )}
              </div>

              {/* Totals */}
              <div className="bg-slate-50 rounded-lg p-4 space-y-2 text-sm border border-slate-200">
                <Row label="Mandatory Govt Fees" value={<AmountCell native={result.totals.mandatory_native} inr={result.totals.mandatory_inr} cur={result.country.currency} />} />
                {result.totals.optional_selected_inr > 0 && (
                  <Row label="Optional Add-ons Selected" value={<AmountCell native={result.totals.optional_selected_native} inr={result.totals.optional_selected_inr} cur={result.country.currency} />} />
                )}
                <Separator className="my-1" />
                <Row label="Total Government Fees" value={<AmountCell native={result.totals.govt_fees_native} inr={result.totals.govt_fees_inr} cur={result.country.currency} />} bold />
                {result.totals.service_fee_inr > 0 && (
                  <>
                    <Row label="Consultancy Service Fee" value={<span className="font-medium">{fmt(result.totals.service_fee_inr, 'INR')}</span>} />
                    <Row label={`GST @ ${result.totals.gst_pct}%`} value={<span className="font-medium">{fmt(result.totals.gst_amount_inr, 'INR')}</span>} />
                  </>
                )}
                <Separator className="my-1" />
                <Row
                  label={<span className="text-base font-bold text-slate-800">Grand Total</span>}
                  value={<span className="text-base font-bold text-[#2a777a]">{fmt(result.totals.grand_total_inr, 'INR')}</span>}
                />
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-wrap">
                <Button variant="outline" size="sm" onClick={handleCopyBreakdown} data-testid="fc-copy-btn">
                  <Copy className="h-3.5 w-3.5 mr-1.5" /> Copy Breakdown
                </Button>
                <Button variant="outline" size="sm" onClick={handlePrint} data-testid="fc-print-btn">
                  <Download className="h-3.5 w-3.5 mr-1.5" /> Print / PDF
                </Button>
                {role !== 'client' && (
                  <Button variant="outline" size="sm" onClick={handleShareNew} className="border-[#2a777a] text-[#2a777a] hover:bg-[#2a777a]/5" data-testid="fc-share-btn">
                    <Share2 className="h-3.5 w-3.5 mr-1.5" /> Share Link
                  </Button>
                )}
                {(caseId || saleId) && role !== 'client' && (
                  <Button size="sm" className="bg-[#f7620b] hover:bg-[#e55a09]" onClick={handleSave} data-testid="fc-save-btn">
                    <Sparkles className="h-3.5 w-3.5 mr-1.5" /> Attach to {caseId ? 'Case' : 'Proposal'}
                  </Button>
                )}
              </div>

              <div className="text-xs text-slate-400 flex items-start gap-1.5 p-2 bg-blue-50 border border-blue-100 rounded">
                <Info className="h-3.5 w-3.5 mt-0.5 text-blue-500 shrink-0" />
                <span>Government fees are indicative (2025-26 official rates). Exchange rates refreshed hourly from ECB (frankfurter.dev). Third-party costs (tuition, travel, insurance) not included.</span>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Saved estimates */}
      {savedEstimates.length > 0 && (
        <Card className="p-4 bg-white border-slate-200">
          <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-3">
            <Shield className="h-4 w-4 text-emerald-600" /> Attached Estimates ({savedEstimates.length})
          </h3>
          <div className="space-y-2">
            {savedEstimates.map(est => (
              <div key={est.id} className="flex items-center justify-between text-sm p-2 bg-slate-50 rounded border border-slate-200 gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-800 truncate">{est.label}</p>
                  <p className="text-xs text-slate-500 flex items-center gap-2 flex-wrap">
                    <span>By {est.created_by_name} · {new Date(est.created_at).toLocaleDateString()}</span>
                    {est.share_active && (
                      <span className="inline-flex items-center gap-1 text-emerald-600"><Link2 className="h-3 w-3" /> Shared</span>
                    )}
                    {est.share_view_count > 0 && (
                      <span className="inline-flex items-center gap-1 text-slate-500"><Eye className="h-3 w-3" /> {est.share_view_count}</span>
                    )}
                    {est.share_lead_count > 0 && (
                      <span className="inline-flex items-center gap-1 text-[#f7620b]"><UserPlus className="h-3 w-3" /> {est.share_lead_count} lead{est.share_lead_count > 1 ? 's' : ''}</span>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge className="bg-[#2a777a] text-white">
                    {fmt(est.payload?.totals?.grand_total_inr || 0, 'INR')}
                  </Badge>
                  {role !== 'client' && (
                    <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => openShareForEstimate(est)} data-testid={`fc-est-share-${est.id}`}>
                      <Share2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
      </>
      )}

      {/* Share Dialog */}
      <Dialog open={shareDialog.open} onOpenChange={(open) => !open && setShareDialog({ open: false, estimate: null, stats: null, link: '', loading: false })}>
        <DialogContent className="max-w-lg" data-testid="fc-share-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <div className="w-9 h-9 bg-gradient-to-br from-[#2a777a] to-[#1f5c5f] rounded-lg flex items-center justify-center text-white">
                <Share2 className="h-4 w-4" />
              </div>
              Share Estimate Link
            </DialogTitle>
            <DialogDescription>
              Anyone with this link can view the estimate (no login). Lead capture is enabled.
            </DialogDescription>
          </DialogHeader>

          {shareDialog.loading ? (
            <div className="py-8 text-center">
              <Loader2 className="h-6 w-6 animate-spin text-[#2a777a] mx-auto mb-2" />
              <p className="text-sm text-slate-500">Generating link…</p>
            </div>
          ) : shareDialog.link ? (
            <div className="space-y-4">
              <div>
                <Label className="text-xs font-semibold text-slate-600">Public Link</Label>
                <div className="flex gap-2 mt-1.5">
                  <Input readOnly value={shareDialog.link} className="font-mono text-xs bg-slate-50" data-testid="fc-share-link-input" />
                  <Button size="sm" onClick={copyShareLink} className="bg-[#2a777a] hover:bg-[#236466] shrink-0" data-testid="fc-share-copy">
                    <Copy className="h-3.5 w-3.5 mr-1" /> Copy
                  </Button>
                </div>
                <p className="text-[11px] text-slate-400 mt-1.5">Share via WhatsApp, email, or SMS</p>
              </div>

              {shareDialog.stats && (
                <>
                  <Separator />
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                      <Eye className="h-4 w-4 text-blue-500 mx-auto mb-1" />
                      <p className="text-2xl font-bold text-blue-700" data-testid="fc-share-views">{shareDialog.stats.view_count || 0}</p>
                      <p className="text-[10px] text-blue-600/80 uppercase tracking-wider">Views</p>
                    </div>
                    <div className="p-3 bg-orange-50 rounded-lg border border-orange-100">
                      <UserPlus className="h-4 w-4 text-[#f7620b] mx-auto mb-1" />
                      <p className="text-2xl font-bold text-[#f7620b]" data-testid="fc-share-leads">{shareDialog.stats.lead_count || 0}</p>
                      <p className="text-[10px] text-[#f7620b]/80 uppercase tracking-wider">Leads</p>
                    </div>
                    <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                      <Clock className="h-4 w-4 text-emerald-600 mx-auto mb-1" />
                      <p className="text-xs font-bold text-emerald-700 mt-1">
                        {shareDialog.stats.expires_at ? new Date(shareDialog.stats.expires_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '—'}
                      </p>
                      <p className="text-[10px] text-emerald-600/80 uppercase tracking-wider">Expires</p>
                    </div>
                  </div>
                </>
              )}

              <div className="flex items-center gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={refreshShareStats} className="flex-1" data-testid="fc-share-refresh">
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Refresh Stats
                </Button>
                <Button variant="outline" size="sm" onClick={deactivateShare}
                  className="flex-1 border-red-200 text-red-600 hover:bg-red-50" data-testid="fc-share-deactivate">
                  <Power className="h-3.5 w-3.5 mr-1.5" /> Deactivate
                </Button>
              </div>

              <a href={shareDialog.link} target="_blank" rel="noreferrer"
                className="block text-center text-sm text-[#2a777a] hover:underline">
                <ExternalLink className="h-3 w-3 inline mr-1" /> Preview in new tab
              </a>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

const Row = ({ label, value, bold }) => (
  <div className="flex items-center justify-between">
    <span className={`text-slate-600 ${bold ? 'font-semibold text-slate-800' : ''}`}>{label}</span>
    <span>{value}</span>
  </div>
);

/** Inline editor for a fee line (per-estimate override, does NOT touch master DB) */
function LineEditor({ line, isExtra, cur, onCancel, onSave, onReset }) {
  const [label, setLabel] = useState(line.label || '');
  const [amount, setAmount] = useState(line.amount_native ?? 0);
  const [notes, setNotes] = useState(line.notes || '');

  return (
    <div className="space-y-2" data-testid="fc-line-editor">
      <div className="grid grid-cols-12 gap-2">
        <div className="col-span-7">
          <Label className="text-[10px] text-slate-500">Label</Label>
          <Input value={label} onChange={(e) => setLabel(e.target.value)} className="h-8 text-sm" data-testid="fc-edit-label" />
        </div>
        <div className="col-span-3">
          <Label className="text-[10px] text-slate-500">Amount ({cur})</Label>
          <Input type="number" min={0} step="0.01" value={amount}
            onChange={(e) => setAmount(e.target.value)} className="h-8 text-sm" data-testid="fc-edit-amount" />
        </div>
        <div className="col-span-2 flex items-end gap-1">
          <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 p-0 w-8"
            onClick={() => onSave({ label, amount: Number(amount) || 0, notes })} data-testid="fc-edit-save">
            <Check className="h-3.5 w-3.5" />
          </Button>
          <Button size="sm" variant="outline" className="h-8 p-0 w-8"
            onClick={onCancel} data-testid="fc-edit-cancel">
            <XIcon className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <Input value={notes} onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional notes for this quote" className="h-7 text-xs" data-testid="fc-edit-notes" />
      <div className="flex items-center justify-between text-[11px] text-slate-500">
        <span>This edit applies only to the current estimate. The master catalog is unchanged.</span>
        <Button variant="ghost" size="sm" onClick={onReset} className="h-6 text-red-600 hover:bg-red-50 text-[11px]" data-testid="fc-edit-reset">
          {isExtra ? <><Trash2 className="h-3 w-3 mr-1" /> Remove line</> : <><RefreshCw className="h-3 w-3 mr-1" /> Revert to catalog</>}
        </Button>
      </div>
    </div>
  );
}
