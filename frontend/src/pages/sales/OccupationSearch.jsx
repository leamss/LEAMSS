/**
 * Smart Sales Helper — Phase 6 v2 Part 1B
 *
 * Route: /sales/occupations
 *
 * Searchable, filterable occupation database across AU/CA/NZ.
 * Type-ahead autocomplete + fuzzy matching + grid view.
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import {
  Search, ArrowLeft, Sparkles, MapPin, Briefcase, Layers, X, Filter,
  GitCompare, ChevronRight, Globe, Star, TrendingUp, Loader2,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_META = {
  AU: { flag: '🇦🇺', name: 'Australia', color: 'bg-blue-50 border-blue-200 text-blue-800' },
  CA: { flag: '🇨🇦', name: 'Canada', color: 'bg-red-50 border-red-200 text-red-800' },
  NZ: { flag: '🇳🇿', name: 'New Zealand', color: 'bg-emerald-50 border-emerald-200 text-emerald-800' },
};

export default function OccupationSearch() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filters, setFilters] = useState({
    country: ['AU', 'CA', 'NZ'],
    skill_level: '',
    pathway: '',
    in_demand: false,
    skill_body: '',
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [results, setResults] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filterMeta, setFilterMeta] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [compareIds, setCompareIds] = useState([]);
  const searchInputRef = useRef(null);

  // Load filter meta once
  useEffect(() => {
    axios.get(`${API}/sales/occupations/filters/meta`, { headers })
      .then(r => setFilterMeta(r.data))
      .catch(e => console.warn('Filter meta load failed', e));
  }, [headers]);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 250);
    return () => clearTimeout(t);
  }, [query]);

  // Run search whenever debouncedQuery or filters change
  const runSearch = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (debouncedQuery) params.append('q', debouncedQuery);
      filters.country.forEach(c => params.append('country', c));
      if (filters.skill_level) params.append('skill_level', filters.skill_level);
      if (filters.pathway) params.append('pathway', filters.pathway);
      if (filters.in_demand) params.append('in_demand', 'true');
      if (filters.skill_body) params.append('skill_body', filters.skill_body);
      params.append('limit', '60');
      const r = await axios.get(`${API}/sales/occupations/search?${params}`, { headers });
      setResults(r.data.items || []);
      setCount(r.data.count || 0);
    } catch (e) {
      toast.error(formatApiError(e, 'Search failed'));
    } finally { setLoading(false); }
  }, [debouncedQuery, filters, headers]);

  useEffect(() => { runSearch(); }, [runSearch]);

  // Typeahead suggestions (only when query is short and focused)
  useEffect(() => {
    if (query.length < 2 || !showSuggestions) { setSuggestions([]); return; }
    const params = new URLSearchParams();
    params.append('q', query);
    filters.country.forEach(c => params.append('country', c));
    axios.get(`${API}/sales/occupations/typeahead?${params}`, { headers })
      .then(r => setSuggestions(r.data.items || []))
      .catch(() => setSuggestions([]));
  }, [query, filters.country, showSuggestions, headers]);

  const toggleCountry = (code) => {
    setFilters(f => ({
      ...f,
      country: f.country.includes(code) ? f.country.filter(c => c !== code) : [...f.country, code],
    }));
  };

  const toggleCompare = (item) => {
    const id = `${item.country_code}:${item.code}`;
    setCompareIds(ids => ids.includes(id) ? ids.filter(x => x !== id) : ids.length >= 4 ? ids : [...ids, id]);
  };

  const runCompare = () => {
    if (compareIds.length < 2) {
      toast.error('Pick at least 2 codes to compare');
      return;
    }
    sessionStorage.setItem('compare_ids', JSON.stringify(compareIds));
    navigate('/sales/occupations/compare');
  };

  const clearAll = () => {
    setQuery('');
    setFilters({ country: ['AU', 'CA', 'NZ'], skill_level: '', pathway: '', in_demand: false, skill_body: '' });
    setCompareIds([]);
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6" data-testid="occupation-search-page">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
              <ArrowLeft className="h-4 w-4 mr-1" />Back
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Sparkles className="h-7 w-7 text-indigo-600" />Smart Sales Helper
              </h1>
              <p className="text-sm text-slate-500">Search 200+ occupation codes across AU, CA, NZ · Deterministic + rule-based · No AI guessing</p>
            </div>
          </div>
          <div className="flex gap-2">
            {compareIds.length > 0 && (
              <Button variant="outline" onClick={runCompare} data-testid="compare-btn">
                <GitCompare className="h-4 w-4 mr-1" />Compare ({compareIds.length})
              </Button>
            )}
          </div>
        </div>

        {/* Big Search Bar */}
        <Card className="p-4 bg-white shadow-sm">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
            <Input
              ref={searchInputRef}
              placeholder="Search by code, title, alternative title, or industry — e.g., 'marketing', 'software engineer', '225113', 'operations head'…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
              className="pl-11 pr-10 text-base h-12"
              data-testid="occupation-search-input"
            />
            {query && (
              <button onClick={() => setQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700">
                <X className="h-4 w-4" />
              </button>
            )}
            {/* Typeahead dropdown */}
            {showSuggestions && suggestions.length > 0 && query.length >= 2 && (
              <div className="absolute left-0 right-0 top-14 z-30 bg-white border rounded-lg shadow-lg max-h-72 overflow-y-auto" data-testid="typeahead-dropdown">
                {suggestions.map(s => (
                  <button
                    key={`${s.country_code}-${s.code}`}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => navigate(`/sales/occupations/${s.country_code}/${s.code}`)}
                    className="w-full text-left px-3 py-2 hover:bg-indigo-50 border-b last:border-b-0 flex items-center gap-2"
                  >
                    <span className="text-lg">{COUNTRY_META[s.country_code]?.flag}</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{s.code} · {s.title}</p>
                      <p className="text-[10px] text-slate-500">{s.assessing_body} · {s.pathway}</p>
                    </div>
                    <Badge className="bg-indigo-100 text-indigo-700 text-[9px]">{s.score}%</Badge>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Country pills */}
          <div className="flex flex-wrap gap-2 mt-3">
            <span className="text-[11px] uppercase font-bold text-slate-500 self-center mr-1">Countries:</span>
            {Object.entries(COUNTRY_META).map(([code, meta]) => (
              <button
                key={code}
                onClick={() => toggleCountry(code)}
                data-testid={`country-pill-${code}`}
                className={`px-3 py-1 text-xs rounded-full border-2 transition ${
                  filters.country.includes(code)
                    ? `${meta.color} font-semibold`
                    : 'bg-white border-slate-200 text-slate-400'
                }`}
              >
                {meta.flag} {meta.name}
              </button>
            ))}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              data-testid="advanced-filters-toggle"
              className="ml-auto text-xs text-indigo-600 hover:underline flex items-center gap-1"
            >
              <Filter className="h-3 w-3" />{showAdvanced ? 'Hide' : 'Advanced'} Filters
            </button>
          </div>

          {/* Advanced filters */}
          {showAdvanced && (
            <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 pt-3 border-t" data-testid="advanced-filters">
              <div>
                <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Skill Level</label>
                <Select value={filters.skill_level || 'all'} onValueChange={v => setFilters(f => ({ ...f, skill_level: v === 'all' ? '' : v }))}>
                  <SelectTrigger className="h-8 text-xs" data-testid="filter-skill-level"><SelectValue placeholder="Any" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Any Level</SelectItem>
                    {[1, 2, 3, 4, 5].map(l => <SelectItem key={l} value={String(l)}>Level {l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Pathway</label>
                <Select value={filters.pathway || 'all'} onValueChange={v => setFilters(f => ({ ...f, pathway: v === 'all' ? '' : v }))}>
                  <SelectTrigger className="h-8 text-xs" data-testid="filter-pathway"><SelectValue placeholder="Any" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Any Pathway</SelectItem>
                    {(filterMeta?.pathways || []).map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-[10px] uppercase font-bold text-slate-500 block mb-1">Skill Body</label>
                <Select value={filters.skill_body || 'all'} onValueChange={v => setFilters(f => ({ ...f, skill_body: v === 'all' ? '' : v }))}>
                  <SelectTrigger className="h-8 text-xs" data-testid="filter-skill-body"><SelectValue placeholder="Any" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Any Body</SelectItem>
                    {(filterMeta?.skill_bodies || []).map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2 pt-5">
                <Switch checked={filters.in_demand} onCheckedChange={v => setFilters(f => ({ ...f, in_demand: v }))} data-testid="filter-in-demand" />
                <label className="text-xs flex items-center gap-1">
                  <TrendingUp className="h-3 w-3 text-emerald-600" />In Demand Only
                </label>
              </div>
              <Button variant="ghost" size="sm" onClick={clearAll} className="col-span-2 md:col-span-4 text-xs">
                <X className="h-3 w-3 mr-1" />Clear all filters
              </Button>
            </div>
          )}
        </Card>

        {/* Results header */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-600">
            {loading
              ? <span className="flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />Searching…</span>
              : <><strong className="text-slate-900">{count}</strong> code{count !== 1 ? 's' : ''} {debouncedQuery && <>for "<em>{debouncedQuery}</em>"</>}</>}
          </p>
          {compareIds.length > 0 && (
            <p className="text-[11px] text-indigo-600">
              {compareIds.length} selected for compare (max 4) ·{' '}
              <button onClick={() => setCompareIds([])} className="underline">Clear</button>
            </p>
          )}
        </div>

        {/* Results grid */}
        {results.length === 0 && !loading ? (
          <Card className="p-10 text-center text-slate-400" data-testid="no-results">
            <Search className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p className="font-medium">No matching codes found</p>
            <p className="text-xs mt-1">Try a different search term or remove some filters</p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="results-grid">
            {results.map(item => {
              const id = `${item.country_code}:${item.code}`;
              const selected = compareIds.includes(id);
              const meta = COUNTRY_META[item.country_code] || COUNTRY_META.AU;
              return (
                <Card
                  key={id}
                  className={`p-4 cursor-pointer transition hover:shadow-md ${selected ? 'border-indigo-500 ring-2 ring-indigo-200' : ''}`}
                  onClick={() => navigate(`/sales/occupations/${item.country_code}/${item.code}`)}
                  data-testid={`occupation-card-${item.code}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <Badge className={`${meta.color} text-[10px] border`}>
                      {meta.flag} {item.code}
                    </Badge>
                    <div className="flex items-center gap-1">
                      {item.in_demand && (
                        <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">
                          <TrendingUp className="h-2.5 w-2.5 mr-0.5" />In Demand
                        </Badge>
                      )}
                      {item.confidence !== null && item.confidence !== undefined && (
                        <Badge className="bg-indigo-100 text-indigo-700 text-[9px]">{item.confidence}%</Badge>
                      )}
                    </div>
                  </div>
                  <h3 className="text-sm font-bold leading-tight">{item.title}</h3>
                  <p className="text-[10px] text-slate-500 mt-1">{item.group}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {item.pathway && <Badge variant="outline" className="text-[9px]">{item.pathway}</Badge>}
                    {item.assessing_body && <Badge variant="outline" className="text-[9px]">{item.assessing_body}</Badge>}
                    {item.skill_level && <Badge variant="outline" className="text-[9px]">Level {item.skill_level}</Badge>}
                  </div>
                  {item.state_demand && Object.keys(item.state_demand).length > 0 && (
                    <div className="mt-2 flex items-start gap-1">
                      <MapPin className="h-3 w-3 text-slate-400 mt-0.5 flex-shrink-0" />
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(item.state_demand)
                          .filter(([, d]) => typeof d === 'string' && d)
                          .slice(0, 4)
                          .map(([st, d]) => (
                          <span
                            key={st}
                            className={`text-[9px] px-1.5 py-0.5 rounded ${
                              d === 'very_high' || d === 'high'
                                ? 'bg-emerald-100 text-emerald-700'
                                : d === 'medium' ? 'bg-amber-100 text-amber-700'
                                : 'bg-slate-100 text-slate-500'
                            }`}
                          >
                            {st}: {d.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {item.alternative_titles && item.alternative_titles.length > 0 && (
                    <p className="text-[10px] text-slate-500 mt-2 italic line-clamp-1">
                      Also: {item.alternative_titles.slice(0, 3).join(' · ')}
                    </p>
                  )}
                  <div className="flex items-center justify-between mt-3 pt-2 border-t">
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleCompare(item); }}
                      className={`text-[10px] flex items-center gap-1 px-2 py-1 rounded transition ${
                        selected ? 'bg-indigo-100 text-indigo-700' : 'text-slate-500 hover:bg-slate-100'
                      }`}
                      data-testid={`compare-toggle-${item.code}`}
                    >
                      <GitCompare className="h-3 w-3" />
                      {selected ? 'Selected' : 'Compare'}
                    </button>
                    <span className="text-[10px] text-indigo-600 flex items-center gap-0.5">
                      Details<ChevronRight className="h-3 w-3" />
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
