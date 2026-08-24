// AI Occupation Suggester — opens from Step 3, calls /sales/ai/suggest-occupation
import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Bot, ChevronRight, Loader2, Check } from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';
import { API, COUNTRIES } from './constants';

export default function SuggesterModal({ onClose, onSelect, onSelectMultiple, headers, initialDescription = '', initialCountry = 'AU', autoRun = false }) {
  const [description, setDescription] = useState(initialDescription);
  const [country, setCountry] = useState(initialCountry || 'AU');
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchedCountry, setSearchedCountry] = useState(null);
  const [selected, setSelected] = useState([]);
  const autoRanRef = useRef(false);

  const keyOf = (s) => `${s.code}-${s.country_code || searchedCountry || 'X'}`;
  const isSelected = (s) => selected.some(x => keyOf(x) === keyOf(s));
  const toggleSelect = (s) => {
    setSelected(prev => (
      prev.some(x => keyOf(x) === keyOf(s))
        ? prev.filter(x => keyOf(x) !== keyOf(s))
        : [...prev, s]
    ));
  };
  const useSelected = () => {
    if (!selected.length) return;
    if (onSelectMultiple) onSelectMultiple(selected);
    else if (onSelect) onSelect(selected[0]);
  };

  const countryName = (code) => (code === 'ALL' ? 'All countries' : (COUNTRIES.find(c => c.code === code)?.name || code));

  const submit = async (overrideCountry) => {
    // Guard: only treat overrideCountry as a country code when it's a string.
    // (Prevents a click event being passed in via onClick={submit} from
    // leaking a DOM node into the request payload → circular JSON crash.)
    const override = typeof overrideCountry === 'string' ? overrideCountry : null;
    const cc = override || country;
    if (description.trim().length < 20) {
      toast.error('Please enter at least 20 characters describing the profession');
      return;
    }
    if (override) setCountry(override);
    setLoading(true);
    try {
      const r = await axios.post(`${API}/sales/ai/suggest-occupation`, {
        description, country_codes: cc === 'ALL' ? null : [cc], max_suggestions: 5,
      }, { headers, timeout: 60000 });
      setSuggestions(r.data);
      setSearchedCountry(cc);
    } catch (e) {
      toast.error(formatApiError(e, 'AI suggestion failed'));
    } finally { setLoading(false); }
  };

  // When opened pre-filled from the resume flow, auto-run the suggestion once.
  useEffect(() => {
    if (autoRun && !autoRanRef.current && (initialDescription || '').trim().length >= 20) {
      autoRanRef.current = true;
      submit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="suggester-modal">
      <Card className="max-w-2xl w-full bg-white p-5 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <h3 className="text-base font-bold flex items-center gap-2 mb-3">
          <Bot className="h-5 w-5 text-indigo-600" />AI Occupation Helper
          <Badge className="bg-amber-100 text-amber-700 text-[9px]">AI suggests — you decide</Badge>
        </h3>
        <p className="text-[11px] text-slate-500 mb-3">
          Describe the client's profession in your own words. The AI will suggest the best matching occupation codes — you verify and pick.
        </p>
        {!suggestions ? (
          <>
            <p className="text-[10px] font-semibold text-slate-500 mb-1">1. Target country <span className="font-normal text-slate-400">— codes &amp; criteria differ per country</span></p>
            <div className="grid grid-cols-4 gap-2 mb-3">
              {COUNTRIES.map(c => (
                <button key={c.code} onClick={() => setCountry(c.code)}
                  className={`p-2 rounded border-2 text-xs ${country === c.code ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200'}`}
                  data-testid={`suggester-country-${c.code}`}>
                  {c.flag} {c.name}
                </button>
              ))}
              <button onClick={() => setCountry('ALL')}
                className={`p-2 rounded border-2 text-xs ${country === 'ALL' ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200'}`}
                data-testid="suggester-country-ALL">
                🌐 All
              </button>
            </div>
            <p className="text-[10px] font-semibold text-slate-500 mb-1">2. Describe the profession</p>
            <Textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={6}
              placeholder="e.g., 8 years in digital marketing, primarily managing social media campaigns, content strategy, and brand positioning for tech companies. Bachelor's in marketing."
              data-testid="suggester-description"
            />
            <p className="text-[10px] text-slate-400 mt-1">Min 20 chars · Be specific about duties, industry, seniority</p>
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={() => submit()} disabled={loading} data-testid="suggester-submit">
                {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Bot className="h-3 w-3 mr-1" />}
                {loading ? 'Analysing…' : 'Find Matching Codes'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3">
              <p className="text-[11px] text-slate-600">
                Matches for: <b>{countryName(searchedCountry)}</b>
              </p>
              {searchedCountry !== 'ALL' && (
                <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={() => submit('ALL')} disabled={loading} data-testid="suggester-search-all">
                  🌐 Search all countries
                </Button>
              )}
            </div>
            <p className="text-[11px] text-amber-700 italic mb-3 bg-amber-50 p-2 rounded">
              ⚠️ AI suggestions are starting points. Please verify each match by reviewing the code's requirements and discussing with the client.
            </p>
            {(!suggestions.suggestions || suggestions.suggestions.length === 0) && (
              <div className="text-center py-4 bg-slate-50 rounded" data-testid="suggester-empty">
                <p className="text-xs text-slate-600 mb-3">
                  No matching occupation codes found{searchedCountry && searchedCountry !== 'ALL' ? ` in ${countryName(searchedCountry)}` : ''}.
                </p>
                {searchedCountry !== 'ALL' && (
                  <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700" onClick={() => submit('ALL')} disabled={loading} data-testid="suggester-empty-search-all">
                    {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Bot className="h-3 w-3 mr-1" />}
                    🌐 Try searching all countries
                  </Button>
                )}
              </div>
            )}
            <div className="space-y-2">
              {(suggestions.suggestions || []).map((s, i) => {
                const sel = isSelected(s);
                return (
                <Card key={`${s.code}-${s.country_code || 'X'}`} className={`p-3 transition ${sel ? 'ring-2 ring-indigo-500' : ''} ${s.confidence === 'high' ? 'border-l-4 border-l-emerald-500 bg-emerald-50' : s.confidence === 'medium' ? 'border-l-4 border-l-amber-500 bg-amber-50' : 'border-l-4 border-l-slate-400'}`} data-testid={`suggestion-${i}`}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-bold">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '•'} {s.code} · {s.title}</p>
                    <div className="flex items-center gap-1">
                      {s.country_code && (
                        <Badge className="bg-slate-800 text-white text-[9px]" data-testid={`suggestion-country-${i}`}>
                          {(COUNTRIES.find(c => c.code === s.country_code)?.flag || '')} {s.country_code}
                        </Badge>
                      )}
                      <Badge className={s.confidence === 'high' ? 'bg-emerald-100 text-emerald-700' : s.confidence === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'}>
                        {s.confidence?.toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500">{s.assessing_body} · {s.pathway}</p>
                  <p className="text-[11px] mt-1">{s.reasoning}</p>
                  {s.considerations && <p className="text-[10px] mt-1 italic text-slate-600">⚠️ {s.considerations}</p>}
                  <Button
                    size="sm"
                    variant={sel ? 'default' : 'outline'}
                    className={`mt-2 text-[10px] h-7 ${sel ? 'bg-indigo-600 hover:bg-indigo-700 text-white' : ''}`}
                    onClick={() => toggleSelect(s)}
                    data-testid={`select-suggestion-${i}`}
                  >
                    {sel ? <><Check className="h-3 w-3 mr-1" />Selected{selected.length > 1 && selected[0] && keyOf(selected[0]) === keyOf(s) ? ' · Primary' : ''}</> : <>Select this code <ChevronRight className="h-3 w-3 ml-1" /></>}
                  </Button>
                </Card>
                );
              })}
            </div>
            {suggestions.general_advice && (
              <p className="text-[11px] italic mt-3 text-slate-600 bg-slate-50 p-2 rounded">💡 {suggestions.general_advice}</p>
            )}
            <div className="flex gap-2 justify-between items-center mt-3">
              <p className="text-[10px] text-slate-500" data-testid="suggester-selected-count">
                {selected.length > 0
                  ? `${selected.length} selected · first = primary`
                  : 'Tick one or more codes to add them'}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => { setSuggestions(null); setSelected([]); }}>Try Again</Button>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700"
                  onClick={useSelected}
                  disabled={selected.length === 0}
                  data-testid="suggester-use-selected"
                >
                  {selected.length > 1 ? `Use ${selected.length} selected codes` : 'Use selected code'}
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
