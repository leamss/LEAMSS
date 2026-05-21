/**
 * Smart Sales Helper — Phase 6.8.3
 * Side-by-side Occupation Comparison view.
 *
 * Route: /sales/occupations/compare
 *
 * Reads `compare_ids` from sessionStorage (set by OccupationSearch.jsx when the
 * user clicks "Compare ({count})"). Calls POST /api/sales/occupations/compare
 * and renders 2-4 occupation cards as a responsive grid + a row-wise diff table.
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, GitCompare, Loader2, Search, Briefcase, MapPin, TrendingUp, FileText,
  CheckCircle2, XCircle,
} from 'lucide-react';

import { formatApiError } from '@/lib/apiErrors';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COUNTRY_META = {
  AU: { flag: '🇦🇺', name: 'Australia', color: 'bg-blue-50 border-blue-200 text-blue-800' },
  CA: { flag: '🇨🇦', name: 'Canada', color: 'bg-red-50 border-red-200 text-red-800' },
  NZ: { flag: '🇳🇿', name: 'New Zealand', color: 'bg-emerald-50 border-emerald-200 text-emerald-800' },
};


export default function OccupationCompare() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const raw = sessionStorage.getItem('compare_ids');
    let ids = [];
    try { ids = JSON.parse(raw || '[]'); } catch { ids = []; }
    if (!Array.isArray(ids) || ids.length < 2) {
      setLoading(false);
      setError('Pick at least 2 occupation codes first');
      return;
    }
    const payload = {
      items: ids.map(id => {
        const [country_code, code] = String(id).split(':');
        return { country_code, code };
      }),
    };
    axios.post(`${API}/sales/occupations/compare`, payload, { headers })
      .then(r => setItems(r.data.items || []))
      .catch(e => {
        setError(formatApiError(e, 'Compare failed'));
        toast.error(formatApiError(e, 'Compare failed'));
      })
      .finally(() => setLoading(false));
  }, [headers]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400" data-testid="compare-loading">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />Loading comparison…
      </div>
    );
  }
  if (error || items.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 p-6" data-testid="compare-error-state">
        <Card className="max-w-2xl mx-auto p-10 text-center">
          <Search className="h-12 w-12 mx-auto mb-3 opacity-40 text-slate-300" />
          <p className="font-medium text-slate-700">{error || 'Nothing to compare yet'}</p>
          <p className="text-xs text-slate-500 mt-1">Go back to Occupation Search and pick at least 2 codes using the “Compare” button on each card.</p>
          <Button className="mt-4" onClick={() => navigate('/sales/occupations')} data-testid="back-to-search">
            <ArrowLeft className="h-4 w-4 mr-1" />Back to Search
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-5" data-testid="compare-page">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={() => navigate('/sales/occupations')} data-testid="back-btn">
              <ArrowLeft className="h-4 w-4 mr-1" />Search
            </Button>
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <GitCompare className="h-7 w-7 text-indigo-600" />Compare Occupations
              </h1>
              <p className="text-sm text-slate-500">{items.length} codes side-by-side · Pick the strongest pathway</p>
            </div>
          </div>
        </div>

        {/* Card grid */}
        <div className={`grid gap-3 grid-cols-1 ${items.length === 2 ? 'md:grid-cols-2' : items.length === 3 ? 'md:grid-cols-3' : 'md:grid-cols-2 lg:grid-cols-4'}`} data-testid="compare-cards">
          {items.map(it => <CompareCard key={`${it.country_code}-${it.code}`} item={it} navigate={navigate} />)}
        </div>

        {/* Comparison Table */}
        <Card className="p-3 overflow-x-auto" data-testid="compare-table">
          <h2 className="text-sm font-bold flex items-center gap-2 mb-3 px-1">
            <FileText className="h-4 w-4 text-indigo-600" />Detailed Comparison
          </h2>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left p-2 font-bold text-slate-700 w-44">Attribute</th>
                {items.map(it => (
                  <th key={`th-${it.country_code}-${it.code}`} className="text-left p-2 font-bold text-slate-700 min-w-[160px]">
                    {(COUNTRY_META[it.country_code] || {}).flag} {it.code}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <Row label="Title" items={items} render={it => <span className="font-semibold">{it.title}</span>} />
              <Row label="Country" items={items} render={it => `${(COUNTRY_META[it.country_code] || {}).flag} ${it.country || it.country_code}`} />
              <Row label="Occupation Group" items={items} render={it => it.group || '—'} />
              <Row label="Skill Level" items={items} render={it => it.skill_level != null ? `Level ${it.skill_level}` : '—'} />
              <Row label="Pathway" items={items} render={it => it.pathway ? <Badge variant="outline" className="text-[9px]">{it.pathway}</Badge> : '—'} />
              <Row label="Assessing Body" items={items} render={it => it.assessing_body ? <Badge className="bg-indigo-100 text-indigo-700 text-[9px]">{it.assessing_body}</Badge> : '—'} />
              <Row label="Min Points Required" items={items} render={it => it.min_points_required != null ? <Badge className="bg-amber-100 text-amber-700">{it.min_points_required}</Badge> : '—'} />
              <Row label="Age Limit" items={items} render={it => it.age_limit ? `${it.age_limit} yrs` : '—'} />
              <Row label="Eligible Visa Subclasses" items={items} render={it => it.eligible_visas_count ?? 0} />
              <Row label="In Demand" items={items} render={it => it.in_demand
                ? <Badge className="bg-emerald-100 text-emerald-700 text-[9px]"><TrendingUp className="h-2.5 w-2.5 mr-0.5" />In Demand</Badge>
                : <Badge className="bg-slate-100 text-slate-500 text-[9px]">Standard</Badge>} />
              <Row label="Skill-Body Fee (Native)" items={items} render={it => formatFee(it.body_fee_native)} />
              <Row label="Skill-Body Processing" items={items} render={it => it.body_processing_weeks ? `${it.body_processing_weeks} weeks` : '—'} />
              <Row
                label="State / Province Demand"
                items={items}
                render={it => {
                  const sd = it.state_demand || {};
                  const states = Object.entries(sd);
                  if (states.length === 0) return '—';
                  return (
                    <div className="flex flex-wrap gap-1">
                      {states.slice(0, 6).map(([st, d]) => (
                        <span
                          key={st}
                          className={`text-[9px] px-1.5 py-0.5 rounded ${
                            d === 'very_high' || d === 'high'
                              ? 'bg-emerald-100 text-emerald-700'
                              : d === 'medium' ? 'bg-amber-100 text-amber-700'
                              : 'bg-slate-100 text-slate-500'
                          }`}
                        >
                          {st}: {String(d).replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  );
                }}
              />
            </tbody>
          </table>
        </Card>

        <div className="flex items-center justify-end gap-2 pb-6">
          <Button variant="outline" onClick={() => navigate('/sales/occupations')} data-testid="back-to-search-2">
            <ArrowLeft className="h-4 w-4 mr-1" />Back to Search
          </Button>
        </div>
      </div>
    </div>
  );
}


function Row({ label, items, render }) {
  return (
    <tr className="border-b last:border-b-0">
      <td className="p-2 font-semibold text-slate-600 bg-slate-50 align-top">{label}</td>
      {items.map(it => (
        <td key={`td-${label}-${it.country_code}-${it.code}`} className="p-2 align-top" data-testid={`cell-${label.replace(/\s+/g, '-').toLowerCase()}-${it.code}`}>
          {render(it)}
        </td>
      ))}
    </tr>
  );
}


function CompareCard({ item, navigate }) {
  const meta = COUNTRY_META[item.country_code] || COUNTRY_META.AU;
  return (
    <Card
      className="p-3 cursor-pointer hover:shadow-md transition border-2 border-slate-100 hover:border-indigo-300"
      onClick={() => navigate(`/sales/occupations/${item.country_code}/${item.code}`)}
      data-testid={`compare-card-${item.code}`}
    >
      <div className="flex items-start justify-between mb-2">
        <Badge className={`${meta.color} text-[10px] border`}>{meta.flag} {item.code}</Badge>
        {item.in_demand && (
          <Badge className="bg-emerald-100 text-emerald-700 text-[9px]">
            <TrendingUp className="h-2.5 w-2.5 mr-0.5" />In Demand
          </Badge>
        )}
      </div>
      <h3 className="text-sm font-bold leading-tight">{item.title}</h3>
      <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">{item.group || '—'}</p>
      <div className="flex flex-wrap gap-1 mt-2">
        {item.pathway && <Badge variant="outline" className="text-[9px]">{item.pathway}</Badge>}
        {item.assessing_body && <Badge variant="outline" className="text-[9px]">{item.assessing_body}</Badge>}
        {item.skill_level != null && <Badge variant="outline" className="text-[9px]">Lv {item.skill_level}</Badge>}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1 text-[10px]">
        <div className="bg-slate-50 rounded p-1.5">
          <p className="text-[9px] text-slate-500 uppercase font-bold">Min Pts</p>
          <p className="font-bold">{item.min_points_required != null ? item.min_points_required : '—'}</p>
        </div>
        <div className="bg-slate-50 rounded p-1.5">
          <p className="text-[9px] text-slate-500 uppercase font-bold">Age Limit</p>
          <p className="font-bold">{item.age_limit ? `${item.age_limit}` : '—'}</p>
        </div>
      </div>
    </Card>
  );
}


function formatFee(fee) {
  if (!fee || typeof fee !== 'object') return '—';
  const cur = fee.currency || '';
  const std = fee.standard;
  const label = fee.label;
  if (label) return <span className="text-[10px]">{label}</span>;
  if (std) return <span className="text-[10px]">{cur} {std}</span>;
  return '—';
}
