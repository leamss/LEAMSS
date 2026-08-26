import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Briefcase, Search, Check, Building2, Edit2, X, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PaOccupationSelector({ pa, onSaved, getAuthHeader }) {
  const [isEditing, setIsEditing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const searchRef = useRef(null);

  // Search occupations from master table
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
        setResults(res.data?.results || res.data || []);
      } catch (err) {
        console.error('Occupation search error:', err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery, isEditing, pa.country]);

  const handleSelect = async (occ) => {
    const occCode = occ.code || occ.anzsco_code;
    const occTitle = occ.title || occ.name;
    const authCode = typeof occ.assessing_authority === 'object'
      ? occ.assessing_authority?.short_name || occ.assessing_authority?.code
      : occ.assessing_authority;

    setSaving(true);
    try {
      await axios.patch(`${API}/pre-assessment/${pa.id}/occupation`, {
        occupation_code: occCode,
        occupation_title: occTitle,
        assessing_authority_code: authCode
      }, getAuthHeader());

      toast.success(`Occupation saved: ${occCode} - ${occTitle}`);
      setIsEditing(false);
      setSearchQuery('');
      if (onSaved) onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update occupation');
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
            <p className="text-xs text-slate-400 italic">No occupation code selected yet. Click to choose.</p>
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
                placeholder="Search occupation code or title (e.g. 261313 or Software)..."
                className="h-8 text-xs pl-8 pr-2 bg-white"
              />
            </div>
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
            <div className="p-2 text-center text-xs text-slate-400 bg-white rounded border border-slate-200">
              <Loader2 className="h-3.5 w-3.5 animate-spin mx-auto inline mr-1 text-[#2a777a]" /> Searching...
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="max-h-48 overflow-y-auto bg-white border border-slate-200 rounded-md shadow-lg divide-y divide-slate-100 z-10">
              {results.map((occ, idx) => {
                const code = occ.code || occ.anzsco_code;
                const title = occ.title || occ.name;
                const auth = typeof occ.assessing_authority === 'object'
                  ? occ.assessing_authority?.short_name || occ.assessing_authority?.code
                  : occ.assessing_authority;

                return (
                  <button
                    key={idx}
                    type="button"
                    disabled={saving}
                    onClick={() => handleSelect(occ)}
                    className="w-full text-left p-2 hover:bg-teal-50 transition-colors flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <span className="font-bold text-xs text-slate-900">{code}</span>
                      <span className="text-xs text-slate-700 ml-1.5 truncate">{title}</span>
                    </div>
                    {auth && (
                      <Badge className="bg-teal-100 text-teal-800 border-teal-200 text-[10px] shrink-0">
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
