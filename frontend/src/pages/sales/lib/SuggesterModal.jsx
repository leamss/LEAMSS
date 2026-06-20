// AI Occupation Suggester — opens from Step 3, calls /sales/ai/suggest-occupation
import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Bot, ChevronRight, Loader2 } from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';
import { API, COUNTRIES } from './constants';

export default function SuggesterModal({ onClose, onSelect, headers }) {
  const [description, setDescription] = useState('');
  const [country, setCountry] = useState('AU');
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (description.trim().length < 20) {
      toast.error('Please enter at least 20 characters describing the profession');
      return;
    }
    setLoading(true);
    try {
      const r = await axios.post(`${API}/sales/ai/suggest-occupation`, {
        description, country_codes: [country], max_suggestions: 5,
      }, { headers, timeout: 60000 });
      setSuggestions(r.data);
    } catch (e) {
      toast.error(formatApiError(e, 'AI suggestion failed'));
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="suggester-modal">
      <Card className="max-w-2xl w-full bg-white p-5 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <h3 className="text-base font-bold flex items-center gap-2 mb-3">
          <Bot className="h-5 w-5 text-leamss-teal-600" />AI Occupation Helper
          <Badge className="bg-amber-100 text-amber-700 text-[9px]">AI suggests — you decide</Badge>
        </h3>
        <p className="text-[11px] text-slate-500 mb-3">
          Describe the client's profession in your own words. The AI will suggest the best matching occupation codes — you verify and pick.
        </p>
        {!suggestions ? (
          <>
            <div className="grid grid-cols-3 gap-2 mb-3">
              {COUNTRIES.map(c => (
                <button key={c.code} onClick={() => setCountry(c.code)}
                  className={`p-2 rounded border-2 text-xs ${country === c.code ? 'border-leamss-teal-500 bg-leamss-teal-50' : 'border-slate-200'}`}>
                  {c.flag} {c.name}
                </button>
              ))}
            </div>
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
              <Button size="sm" className="bg-leamss-teal-600 hover:bg-leamss-teal-700" onClick={submit} disabled={loading} data-testid="suggester-submit">
                {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Bot className="h-3 w-3 mr-1" />}
                {loading ? 'Analysing…' : 'Find Matching Codes'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="text-[11px] text-amber-700 italic mb-3 bg-amber-50 p-2 rounded">
              ⚠️ AI suggestions are starting points. Please verify each match by reviewing the code's requirements and discussing with the client.
            </p>
            <div className="space-y-2">
              {(suggestions.suggestions || []).map((s, i) => (
                <Card key={`${s.code}-${s.country_code || 'X'}`} className={`p-3 ${s.confidence === 'high' ? 'border-l-4 border-l-emerald-500 bg-emerald-50' : s.confidence === 'medium' ? 'border-l-4 border-l-amber-500 bg-amber-50' : 'border-l-4 border-l-slate-400'}`} data-testid={`suggestion-${i}`}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-bold">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '•'} {s.code} · {s.title}</p>
                    <Badge className={s.confidence === 'high' ? 'bg-emerald-100 text-emerald-700' : s.confidence === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'}>
                      {s.confidence?.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-[10px] text-slate-500">{s.assessing_body} · {s.pathway}</p>
                  <p className="text-[11px] mt-1">{s.reasoning}</p>
                  {s.considerations && <p className="text-[10px] mt-1 italic text-slate-600">⚠️ {s.considerations}</p>}
                  <Button size="sm" variant="outline" className="mt-2 text-[10px] h-7" onClick={() => onSelect(s)} data-testid={`select-suggestion-${i}`}>
                    Select this code <ChevronRight className="h-3 w-3 ml-1" />
                  </Button>
                </Card>
              ))}
            </div>
            {suggestions.general_advice && (
              <p className="text-[11px] italic mt-3 text-slate-600 bg-slate-50 p-2 rounded">💡 {suggestions.general_advice}</p>
            )}
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={() => setSuggestions(null)}>Try Again</Button>
              <Button size="sm" variant="ghost" onClick={onClose}>Close</Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
