import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Globe, Plus, X, IndianRupee, Clock, GraduationCap, Briefcase, Scale } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function VisaCompare() {
  const navigate = useNavigate();
  const [allPathways, setAllPathways] = useState([]);
  const [picked, setPicked] = useState([]);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/visa-compare/pathways`);
      setAllPathways(r.data.pathways || []);
    } catch (e) { toast.error('Failed to load pathways'); }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const togglePick = (slug) => {
    if (picked.includes(slug)) {
      setPicked(picked.filter(s => s !== slug));
    } else {
      if (picked.length >= 4) {
        toast.warning('Max 4 pathways at a time');
        return;
      }
      setPicked([...picked, slug]);
    }
  };

  const compare = async () => {
    if (picked.length < 2) {
      toast.error('Select at least 2 pathways');
      return;
    }
    setLoading(true);
    try {
      const r = await axios.get(`${API}/visa-compare/compare?slugs=${picked.join(',')}`);
      setData(r.data.pathways || []);
    } catch (e) { toast.error(e.response?.data?.detail || 'Compare failed'); }
    setLoading(false);
  };

  const inr = (v) => v ? `₹${(v / 100000).toFixed(1)}L` : '—';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <div className="bg-white border-b shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#2a777a] to-[#1d5658] flex items-center justify-center">
              <Scale className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-bold text-slate-800">Visa Pathway Comparison</p>
              <p className="text-[11px] text-slate-500">Side-by-side · Public · Free</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate('/eligibility')} data-testid="goto-eligibility">
            Check My Eligibility →
          </Button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        <div className="text-center max-w-2xl mx-auto">
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-2">Compare Visa Pathways Side-by-Side</h1>
          <p className="text-slate-600 text-sm">Pick 2-4 pathways → compare fees, timelines, eligibility, post-arrival jobs.</p>
        </div>

        {/* Pathway picker */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <p className="font-semibold text-slate-800 text-sm">Select pathways ({picked.length}/4)</p>
            <Button onClick={compare} disabled={picked.length < 2 || loading} className="bg-[#2a777a] hover:bg-[#1d5658] text-white" data-testid="run-compare">
              {loading ? 'Loading…' : `Compare ${picked.length} pathway${picked.length === 1 ? '' : 's'}`}
            </Button>
          </div>
          <div className="flex gap-2 flex-wrap">
            {allPathways.map(p => (
              <button key={p.slug} onClick={() => togglePick(p.slug)}
                className={`px-3 py-1.5 rounded-full text-xs border flex items-center gap-1.5 transition ${picked.includes(p.slug) ? 'bg-[#2a777a] text-white border-[#2a777a]' : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'}`}
                data-testid={`pick-${p.slug}`}>
                {picked.includes(p.slug) ? <X className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                {p.name}
              </button>
            ))}
          </div>
        </Card>

        {/* Comparison grid */}
        {data.length >= 2 && (
          <div className="overflow-x-auto" data-testid="compare-results">
            <div className="grid gap-4 min-w-[800px]" style={{ gridTemplateColumns: `repeat(${data.length}, minmax(280px, 1fr))` }}>
              {data.map(p => (
                <Card key={p.slug} className="p-5 border-t-4" style={{ borderTopColor: '#2a777a' }} data-testid={`compare-${p.slug}`}>
                  <Badge className="bg-slate-100 text-slate-700 mb-2 text-[10px]">{p.country}</Badge>
                  <h3 className="font-bold text-slate-900 leading-tight mb-1">{p.name}</h3>
                  <p className="text-xs text-slate-500 mb-4">{p.category}</p>

                  <div className="space-y-3 text-sm">
                    <div className="flex items-start gap-2">
                      <Clock className="h-4 w-4 text-blue-600 mt-0.5" />
                      <div>
                        <p className="text-[11px] text-slate-500">Timeline</p>
                        <p className="font-semibold text-slate-800">{p.timeline_months} months</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <IndianRupee className="h-4 w-4 text-emerald-600 mt-0.5" />
                      <div>
                        <p className="text-[11px] text-slate-500">Total Cost (Govt + LEAMSS)</p>
                        <p className="font-semibold text-slate-800">{inr((p.govt_fee_inr || 0) + (p.leamss_fee_inr || 0))}</p>
                        <p className="text-[10px] text-slate-500">+ {inr(p.min_funds_inr)} settlement funds</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <GraduationCap className="h-4 w-4 text-leamss-orange-600 mt-0.5" />
                      <div>
                        <p className="text-[11px] text-slate-500">Min Education</p>
                        <p className="font-semibold text-slate-800">{p.min_education}</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2">
                      <Briefcase className="h-4 w-4 text-amber-600 mt-0.5" />
                      <div>
                        <p className="text-[11px] text-slate-500">Work Experience</p>
                        <p className="font-semibold text-slate-800">{p.min_work_exp_years}+ years</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-[11px] text-slate-500">Age Range</p>
                      <p className="font-semibold text-slate-800 text-sm">{p.min_age} – {p.max_age} years</p>
                    </div>
                    <div>
                      <p className="text-[11px] text-slate-500">Language</p>
                      <p className="font-semibold text-slate-800 text-xs">{p.language_required}</p>
                    </div>

                    {p.key_benefits?.length > 0 && (
                      <div className="pt-3 border-t border-slate-100">
                        <p className="text-[11px] font-semibold text-emerald-700 mb-1">✓ Key Benefits</p>
                        <ul className="text-[11px] text-slate-600 space-y-1 ml-3">
                          {p.key_benefits.map((b, i) => <li key={i} className="list-disc">{b}</li>)}
                        </ul>
                      </div>
                    )}
                    {p.key_drawbacks?.length > 0 && (
                      <div>
                        <p className="text-[11px] font-semibold text-rose-700 mb-1">⚠ Drawbacks</p>
                        <ul className="text-[11px] text-slate-600 space-y-1 ml-3">
                          {p.key_drawbacks.map((b, i) => <li key={i} className="list-disc">{b}</li>)}
                        </ul>
                      </div>
                    )}
                    {p.post_arrival_jobs && (
                      <div>
                        <p className="text-[11px] font-semibold text-blue-700 mb-1">💼 Post-Arrival Jobs</p>
                        <p className="text-[11px] text-slate-600">{p.post_arrival_jobs}</p>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {data.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <Globe className="h-12 w-12 mx-auto mb-2 text-slate-300" />
            <p className="text-sm">Select at least 2 pathways to compare side-by-side.</p>
          </div>
        )}

        <div className="text-center pt-4">
          <p className="text-xs text-slate-500 mb-2">Need a personalised score across all pathways?</p>
          <Button onClick={() => navigate('/eligibility')} variant="outline">
            Get AI Eligibility Score →
          </Button>
        </div>
      </div>
    </div>
  );
}
