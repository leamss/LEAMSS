import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Briefcase, Search, Check, Building2, Edit2, X, Loader2, Sparkles, Plus } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PaOccupationSelector({ pa, onSaved, getAuthHeader }) {
  const [isEditing, setIsEditing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const searchRef = useRef(null);

  // Search occupations from master table (supports code, profession name, keywords, typos)
  useEffect(() => {
    if (!isEditing || !searchQuery || searchQuery.trim().length < 2) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const country = pa.country || 'AU';
        const res = await axios.get(`${API}/sales/occupations/search`, {
          ...getAuthHeader(),
          params: { q: searchQuery.trim(), country }
        });
        
        // Extract array from response (items or results or array)
        const items = res.data?.items || res.data?.results || (Array.isArray(res.data) ? res.data : []);
        setResults(items);
      } catch (err) {
        console.error('Occupation search error:', err);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery, isEditing, pa.country]);

  const handleSelect = async (occ) => {
    const occCode = occ.code || occ.anzsco_code;
    const occTitle = occ.title || occ.name;
    const authCode = typeof occ.assessing_body === 'string'
      ? occ.assessing_body
      : typeof occ.assessing_authority === 'object'
      ? occ.assessing_authority?.short_name || occ.assessing_authority?.code
      : (occ.assessing_authority || occ.skill_body || 'Assessing Body');

    setSaving(true);
    try {
      await axios.patch(`${API}/pre-assessment/${pa.id}/occupation`, {
        occupation_code: occCode,
        occupation_title: occTitle,
        assessing_authority_code: authCode
      }, getAuthHeader());

      toast.success(`Occupation selected: ${occCode} - ${occTitle}`);
      setIsEditing(false);
      setSearchQuery('');
      if (onSaved) onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update occupation');
    } finally {
      setSaving(false);
    }
  };

  // Direct manual save if user typed a specific code
  const handleDirectAdd = async () => {
    const query = searchQuery.trim();
    if (!query) return;

    // Check if matching first result or treat as custom code
    if (results.length > 0) {
      handleSelect(results[0]);
      return;
    }

    setSaving(true);
    try {
      await axios.patch(`${API}/pre-assessment/${pa.id}/occupation`, {
        occupation_code: query,
        occupation_title: `ANZSCO ${query}`,
      }, getAuthHeader());

      toast.success(`Occupation code added: ${query}`);
      setIsEditing(false);
      setSearchQuery('');
      if (onSaved) onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save occupation code');
    } finally {
      setSaving(false);
    }
  };

  const hasOccupation = Boolean(pa.occupation_code);

  return (
    <div className="bg-slate-50 rounded-lg p-3 border border-slate-200" data-testid={`pa-occupation-selector-${pa.id}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
          <Briefcase className="h-3.5 w-3.5 text-[#2a777a]" />
          Occupation Code (ANZSCO)
        </p>
        {!isEditing && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-[11px] px-2 text-[#2a777a] hover:bg-teal-50"
            onClick={() => {
              setIsEditing(true);
              setSearchQuery(pa.occupation_code || '');
            }}
          >
            <Edit2 className="h-3 w-3 mr-1" /> {hasOccupation ? 'Change Code' : 'Select Occupation'}
          </Button>
        )}
      </div>

      {!isEditing ? (
        <div className="mt-1.5 flex items-center gap-2 flex-wrap">
          {hasOccupation ? (
            <>
              <Badge variant="outline" className="bg-white border-slate-300 text-slate-800 text-xs font-semibold">
                {pa.occupation_code} · {pa.occupation_title || 'Assigned Occupation'}
              </Badge>
              {pa.assessing_authority_code && (
                <Badge className="bg-teal-100 text-teal-800 border-teal-300 text-[11px] font-semibold flex items-center gap-1">
                  <Building2 className="h-3 w-3 text-teal-600" />
                  Assessing Body: {pa.assessing_authority_code}
                </Badge>
              )}
            </>
          ) : (
            <p className="text-xs text-slate-400 italic">No occupation code selected yet. Click to choose or search by profession.</p>
          )}
        </div>
      ) : (
        <div className="mt-2 space-y-2 relative" ref={searchRef}>
          <div className="flex items-center gap-1.5">
            <div className="relative flex-1">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <Input
                type="text"
                autoFocus
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleDirectAdd();
                  }
                }}
                placeholder="Type profession or ANZSCO code (e.g. 261313, Software Engineer, Nurse, Chef)..."
                className="h-8 text-xs pl-8 pr-2 bg-white"
              />
            </div>
            <Button
              size="sm"
              className="h-8 px-3 text-xs bg-[#2a777a] hover:bg-[#236466] text-white font-medium"
              disabled={saving || !searchQuery.trim()}
              onClick={handleDirectAdd}
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5 mr-1" />}
              {saving ? 'Saving...' : 'Add'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-2 text-xs"
              onClick={() => {
                setIsEditing(false);
                setSearchQuery('');
              }}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>

          {/* Search Dropdown Results */}
          {loading && (
            <div className="p-2 text-center text-xs text-slate-400 bg-white rounded border border-slate-200 shadow-sm">
              <Loader2 className="h-3.5 w-3.5 animate-spin mx-auto inline mr-1 text-[#2a777a]" /> Searching occupations with AI match...
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="max-h-56 overflow-y-auto bg-white border border-slate-200 rounded-md shadow-lg divide-y divide-slate-100 z-20">
              {results.slice(0, 10).map((occ, idx) => {
                const code = occ.code || occ.anzsco_code;
                const title = occ.title || occ.name;
                const auth = typeof occ.assessing_body === 'string'
                  ? occ.assessing_body
                  : typeof occ.assessing_authority === 'object'
                  ? occ.assessing_authority?.short_name || occ.assessing_authority?.code
                  : (occ.assessing_authority || occ.skill_body);

                return (
                  <button
                    key={idx}
                    type="button"
                    disabled={saving}
                    onClick={() => handleSelect(occ)}
                    className="w-full text-left p-2.5 hover:bg-teal-50 transition-colors flex items-center justify-between gap-2 group"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-xs text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded group-hover:bg-teal-100 group-hover:text-teal-900">
                          {code}
                        </span>
                        <span className="text-xs font-semibold text-slate-800 truncate">{title}</span>
                      </div>
                      {occ.pathway && (
                        <p className="text-[10px] text-slate-400 mt-0.5 pl-0.5 truncate">
                          Visa Pathway: {occ.pathway}
                        </p>
                      )}
                    </div>
                    {auth && (
                      <Badge className="bg-teal-100 text-teal-800 border-teal-200 text-[10px] shrink-0 font-medium">
                        {auth}
                      </Badge>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

