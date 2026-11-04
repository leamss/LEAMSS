// AI Occupation Suggester — opens from Step 3, calls /sales/ai/suggest-occupation
import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Bot, ChevronRight, Loader2, Check, AlertTriangle, FileText, Award, Scale, HelpCircle, ListChecks, Building2, Search, Layers, Plus } from 'lucide-react';
import { formatApiError } from '@/lib/apiErrors';
import { API, COUNTRIES } from './constants';

export default function SuggesterModal({
  onClose,
  onSelect,
  onSelectMultiple,
  headers,
  initialDescription = '',
  initialCountry = 'AU',
  initialQualification = '',
  initialFieldOfStudy = '',
  initialExpYears = 0,
  initialProfile = null,
  autoRun = false,
}) {
  const [description, setDescription] = useState(initialDescription);
  const [country, setCountry] = useState(initialCountry || 'AU');
  const [profession, setProfession] = useState(initialProfile?.current_profession || initialProfile?.profession || '');
  const [qualification, setQualification] = useState(initialQualification || initialProfile?.qualification || '');
  const [fieldOfStudy, setFieldOfStudy] = useState(initialFieldOfStudy || initialProfile?.field_of_study || '');
  const [expYears, setExpYears] = useState(initialExpYears || initialProfile?.years_experience_total || '');
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchedCountry, setSearchedCountry] = useState(null);
  const [selected, setSelected] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedSubclasses, setSelectedSubclasses] = useState([]);
  const [targetFramework, setTargetFramework] = useState('ALL');
  const [activeFilterSubclass, setActiveFilterSubclass] = useState('ALL');

  const ALL_GSM = ['189', '190', '491', '494'];
  const ALL_EMPLOYER = ['482', '186', '407', '485'];
  const ALL_AU_SUBCLASSES = [...ALL_GSM, ...ALL_EMPLOYER];

  const toggleSubclass = (scId) => {
    setSelectedSubclasses(prev => (
      prev.includes(scId) ? prev.filter(x => x !== scId) : [...prev, scId]
    ));
  };

  const selectAllGsm = () => {
    setSelectedSubclasses(ALL_GSM);
    setTargetFramework('ANZSCO_2013');
  };

  const selectAllEmployer = () => {
    setSelectedSubclasses(ALL_EMPLOYER);
    setTargetFramework('OSCA_2022');
  };

  const selectAllSubclasses = () => {
    setSelectedSubclasses(ALL_AU_SUBCLASSES);
    setTargetFramework('ALL');
  };

  const clearSubclasses = () => {
    setSelectedSubclasses([]);
    setTargetFramework('ALL');
  };

  const isGsmPresetActive = ALL_GSM.every(sc => selectedSubclasses.includes(sc)) && selectedSubclasses.length === ALL_GSM.length;
  const isEmployerPresetActive = ALL_EMPLOYER.every(sc => selectedSubclasses.includes(sc)) && selectedSubclasses.length === ALL_EMPLOYER.length;
  const isAllPresetActive = ALL_AU_SUBCLASSES.every(sc => selectedSubclasses.includes(sc)) && selectedSubclasses.length === ALL_AU_SUBCLASSES.length;

  useEffect(() => {
    if (initialDescription && !description) {
      setDescription(initialDescription);
    }
    if ((initialProfile?.current_profession || initialProfile?.profession) && !profession) {
      setProfession(initialProfile.current_profession || initialProfile.profession);
    }
  }, [initialDescription, description, initialProfile, profession]);

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

  const executeSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const cc = searchedCountry === 'ALL' ? undefined : (searchedCountry || country);
      const r = await axios.get(`${API}/sales/occupations/search`, {
        params: {
          q: searchQuery.trim(),
          country: cc ? [cc] : undefined,
          limit: 10,
        },
        headers,
      });
      let items = r.data.items || [];
      // For Australia, strictly require official 6-digit codes
      if (cc === 'AU' || (!cc && country === 'AU')) {
        items = items.filter(it => String(it.code || '').length === 6 && /^\d+$/.test(String(it.code)));
      }
      setSearchResults(items);
      if (!items.length) {
        toast.info('No 6-digit occupations found matching your query.');
      }
    } catch (e) {
      toast.error('Search failed: ' + formatApiError(e));
    } finally {
      setSearching(false);
    }
  };

  const addSearchedOccupation = (item) => {
    const cc = item.country_code || searchedCountry || country || 'AU';
    const codeStr = String(item.code || '');
    
    // Check if code is already in suggestions list
    const alreadyExists = (suggestions?.suggestions || []).some(
      s => String(s.code) === codeStr && (s.country_code || cc) === cc
    );

    const isAu = cc === 'AU';
    const anzSubclasses = ['189', '190', '491', '494'].filter(v => (item.eligible_visas || []).includes(v) || true);
    const oscaSubclasses = ['482', '186', '407', '485'].filter(v => (item.eligible_visas || []).includes(v) || true);

    const newItem = {
      country_code: cc,
      code: codeStr,
      title: item.title || 'Occupation',
      confidence: 'medium',
      assessing_body: item.assessing_body || 'Designated Assessing Authority',
      pathway: item.pathway || 'Core Skills / GSM',
      reasoning: `Manually searched and added occupation ${codeStr} (${item.title}).`,
      considerations: `Selected via quick search. Official assessing body: ${item.assessing_body || 'Designated Authority'}.`,
      _verified: true,
      _user_added: true,
      skills_assessment: {
        authority_name: item.assessing_body || 'Designated Assessing Authority',
        pathway_name: item.pathway || 'Skilled Migration',
        assessment_outcome: 'Likely Positive (Review Required)',
        is_positive: true,
        deducted_years: 0,
        points_claimable_years: expYears ? Number(expYears) : 0,
        points_claimable_points: 0,
        conditions_summary: 'Verify assessing authority criteria and work references before submitting EOI.',
      },
      classification_versions: isAu ? {
        anzsco_2013: {
          version_name: 'ANZSCO 2013',
          framework: 'General Skilled Migration (GSM)',
          is_eligible: true,
          active_subclasses: ['189', '190', '491', '494'],
        },
        osca_2022: {
          version_name: 'OSCA 2022',
          framework: 'Employer-Sponsored & Core Skills (CSOL)',
          is_eligible: true,
          active_subclasses: ['482', '186', '407', '485'],
        },
      } : undefined,
    };

    if (!alreadyExists) {
      setSuggestions(prev => ({
        ...prev,
        suggestions: [newItem, ...(prev?.suggestions || [])],
      }));
    }

    // Immediately toggle select this item
    setSelected(prev => {
      const exists = prev.some(x => keyOf(x) === keyOf(newItem));
      return exists ? prev : [newItem, ...prev];
    });

    toast.success(`Added ${codeStr} · ${item.title} to selection!`);
    setSearchQuery('');
    setSearchResults([]);
  };

  const submit = async (overrideCountry) => {
    const override = typeof overrideCountry === 'string' ? overrideCountry : null;
    const cc = override || country;
    if (description.trim().length < 15) {
      toast.error('Please enter at least 15 characters describing the profession');
      return;
    }
    if (override) setCountry(override);
    setLoading(true);
    setError(null);
    try {
      const rawWorkHist = (initialProfile && initialProfile.work_history) ||
        (initialProfile && initialProfile.primary_applicant && initialProfile.primary_applicant.work_history) || [];

      const outgoingProfile = {
        ...(initialProfile || {}),
        qualification: qualification || initialProfile?.qualification,
        field_of_study: fieldOfStudy || initialProfile?.field_of_study,
        years_experience_total: expYears ? Number(expYears) : (initialProfile?.years_experience_total || 0),
        current_profession: profession || initialProfile?.current_profession,
        profession: profession || initialProfile?.profession,
        designation: profession || initialProfile?.designation,
        roles_and_responsibilities: description,
        work_history: rawWorkHist,
        primary_applicant: {
          ...((initialProfile && initialProfile.primary_applicant) || {}),
          work_history: rawWorkHist,
          professional: {
            ...((initialProfile && initialProfile.primary_applicant && initialProfile.primary_applicant.professional) || {}),
            current_profession: profession || initialProfile?.current_profession,
            designation: profession || initialProfile?.designation,
            years_experience_total: expYears ? Number(expYears) : 0,
          },
          education: {
            ...((initialProfile && initialProfile.primary_applicant && initialProfile.primary_applicant.education) || {}),
            highest_qualification: qualification,
            field_of_study: fieldOfStudy,
          },
        },
      };

      const r = await axios.post(`${API}/sales/ai/suggest-occupation`, {
        description,
        country_codes: cc === 'ALL' ? null : [cc],
        max_suggestions: 5,
        qualification: qualification || undefined,
        field_of_study: fieldOfStudy || undefined,
        years_experience_total: expYears ? Number(expYears) : undefined,
        target_subclasses: selectedSubclasses.length > 0 ? selectedSubclasses : undefined,
        target_framework: targetFramework !== 'ALL' ? targetFramework : undefined,
        profile: outgoingProfile,
      }, { headers, timeout: 120000 });
      setSuggestions(r.data);
      setSearchedCountry(cc);
    } catch (e) {
      const errText = formatApiError(e, 'Could not retrieve occupation suggestions. Please retry or adjust description.');
      setError(errText);
    } finally { setLoading(false); }
  };

  // We intentionally do not auto-run on mount so the user can review and select
  // their target visa subclasses and framework before the AI analysis runs.
  useEffect(() => {
    // Keep idle awaiting user selection & submit click
  }, []);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose} data-testid="suggester-modal">
      <Card className="max-w-3xl w-full bg-white p-5 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b pb-3 mb-3">
          <h3 className="text-base font-bold flex items-center gap-2">
            <Bot className="h-5 w-5 text-indigo-600" />AI Occupation &amp; Skills Assessment Suggester
            <Badge className="bg-amber-100 text-amber-700 text-[9px]">AI suggests — you verify &amp; decide</Badge>
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-7 w-7 p-0 text-slate-400 hover:text-slate-600">✕</Button>
        </div>

        <p className="text-[11px] text-slate-500 mb-3">
          Evaluates the candidate's profile, job duties, qualification, and experience against official assessing body rules (ACS, VETASSESS, TRA, Engineers Australia) to suggest matching occupation codes with exact deductions and points.
        </p>

        {!suggestions ? (
          <>
            <p className="text-[10px] font-semibold text-slate-500 mb-1">1. Target country <span className="font-normal text-slate-400">— codes &amp; criteria differ per country</span></p>
            <div className="grid grid-cols-4 gap-2 mb-3">
              {COUNTRIES.map(c => (
                <button key={c.code} onClick={() => setCountry(c.code)}
                  className={`p-2 rounded border-2 text-xs font-medium transition ${country === c.code ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-600'}`}
                  data-testid={`suggester-country-${c.code}`}>
                  {c.flag} {c.name}
                </button>
              ))}
              <button onClick={() => setCountry('ALL')}
                className={`p-2 rounded border-2 text-xs font-medium transition ${country === 'ALL' ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-600'}`}
                data-testid="suggester-country-ALL">
                🌐 All
              </button>
            </div>

            {country === 'AU' && (
              <div className="mb-4 p-3.5 bg-gradient-to-r from-sky-50/70 via-indigo-50/50 to-purple-50/70 border-2 border-indigo-200 rounded-xl space-y-2.5 shadow-xs" data-testid="suggester-target-subclass-section">
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-600 text-white text-[11px] font-bold">2</span>
                    <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                      <Layers className="h-4 w-4 text-indigo-600" />
                      Select Target Visa Subclass &amp; Framework (Before Analyzing)
                    </span>
                  </div>
                  <Badge className="bg-indigo-100 text-indigo-800 font-semibold text-[10px] border border-indigo-200">
                    Dual Framework (ANZSCO 2013 + OSCA 2022)
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-600 leading-tight">
                  Choose the visa subclass(es) or migration framework you want to target. The AI will strictly verify whether candidate duties and experience match eligible 6-digit occupation codes under <b>ANZSCO 2013 (GSM)</b> and <b>OSCA 2022 (Employer Sponsored)</b>.
                </p>

                {/* Quick Presets */}
                <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-indigo-100/80">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mr-1">Quick Presets:</span>
                  <button
                    type="button"
                    onClick={selectAllGsm}
                    className={`px-2.5 py-1 rounded-md text-[10.5px] font-semibold transition border ${
                      isGsmPresetActive ? 'bg-sky-600 text-white border-sky-600 shadow-sm' : 'bg-white text-sky-800 border-sky-200 hover:bg-sky-50'
                    }`}
                    data-testid="preset-gsm"
                  >
                    🏛️ All GSM Subclasses (189, 190, 491, 494)
                  </button>
                  <button
                    type="button"
                    onClick={selectAllEmployer}
                    className={`px-2.5 py-1 rounded-md text-[10.5px] font-semibold transition border ${
                      isEmployerPresetActive ? 'bg-purple-600 text-white border-purple-600 shadow-sm' : 'bg-white text-purple-800 border-purple-200 hover:bg-purple-50'
                    }`}
                    data-testid="preset-employer"
                  >
                    🚀 All Employer Subclasses (482, 186, 407, 485)
                  </button>
                  <button
                    type="button"
                    onClick={selectAllSubclasses}
                    className={`px-2.5 py-1 rounded-md text-[10.5px] font-semibold transition border ${
                      isAllPresetActive ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm' : 'bg-white text-indigo-800 border-indigo-200 hover:bg-indigo-50'
                    }`}
                    data-testid="preset-all"
                  >
                    🌐 All Subclasses (189, 190, 491, 494, 482, 186, 407, 485)
                  </button>
                  {selectedSubclasses.length > 0 && (
                    <button
                      type="button"
                      onClick={clearSubclasses}
                      className="text-[10px] text-slate-500 hover:text-slate-700 underline ml-auto font-medium"
                      data-testid="reset-subclasses"
                    >
                      Clear Selection
                    </button>
                  )}
                </div>

                {/* Subclass Selection Grids: GSM vs Employer */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                  {/* GSM ANZSCO 2013 */}
                  <div className="bg-white p-2.5 rounded-lg border border-sky-200 shadow-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-sky-900 flex items-center gap-1">
                        🏛️ ANZSCO 2013 — GSM Points-Tested
                      </span>
                      <span className="text-[9.5px] text-sky-700 font-medium">PR &amp; Regional</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5">
                      {[
                        { id: '189', name: '189 - Skilled Independent (PR)' },
                        { id: '190', name: '190 - Skilled Nominated (PR)' },
                        { id: '491', name: '491 - Skilled Work Regional' },
                        { id: '494', name: '494 - Regional Employer' },
                      ].map(sc => {
                        const checked = selectedSubclasses.includes(sc.id);
                        return (
                          <button
                            key={sc.id}
                            type="button"
                            onClick={() => toggleSubclass(sc.id)}
                            className={`flex items-center gap-1.5 p-1.5 rounded text-[10.5px] text-left font-medium transition border ${
                              checked ? 'bg-sky-50 border-sky-500 text-sky-900 font-bold ring-1 ring-sky-400' : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                            }`}
                            data-testid={`subclass-checkbox-${sc.id}`}
                          >
                            <span className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[9px] border shrink-0 ${
                              checked ? 'bg-sky-600 border-sky-600 text-white font-bold' : 'border-slate-300 bg-white'
                            }`}>
                              {checked ? '✓' : ''}
                            </span>
                            <span className="truncate">{sc.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* OSCA 2022 Employer */}
                  <div className="bg-white p-2.5 rounded-lg border border-purple-200 shadow-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-purple-900 flex items-center gap-1">
                        🚀 OSCA 2022 — Employer Sponsored / CSOL
                      </span>
                      <span className="text-[9.5px] text-purple-700 font-medium">Core Skills &amp; TSS</span>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5">
                      {[
                        { id: '482', name: '482 - Skills in Demand / TSS' },
                        { id: '186', name: '186 - Employer Nom PR' },
                        { id: '407', name: '407 - Training Visa' },
                        { id: '485', name: '485 - Temporary Graduate' },
                      ].map(sc => {
                        const checked = selectedSubclasses.includes(sc.id);
                        return (
                          <button
                            key={sc.id}
                            type="button"
                            onClick={() => toggleSubclass(sc.id)}
                            className={`flex items-center gap-1.5 p-1.5 rounded text-[10.5px] text-left font-medium transition border ${
                              checked ? 'bg-purple-50 border-purple-500 text-purple-900 font-bold ring-1 ring-purple-400' : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                            }`}
                            data-testid={`subclass-checkbox-${sc.id}`}
                          >
                            <span className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[9px] border shrink-0 ${
                              checked ? 'bg-purple-600 border-purple-600 text-white font-bold' : 'border-slate-300 bg-white'
                            }`}>
                              {checked ? '✓' : ''}
                            </span>
                            <span className="truncate">{sc.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Subclass Selection Status */}
                <div className="text-[10.5px] text-slate-600 flex items-center justify-between pt-1">
                  <span>
                    {selectedSubclasses.length === 0 ? (
                      <span className="italic text-slate-500">Searching all subclasses across ANZSCO 2013 &amp; OSCA 2022</span>
                    ) : (
                      <span>Targeting <b>{selectedSubclasses.length}</b> subclass{selectedSubclasses.length > 1 ? 'es' : ''}: <strong className="text-indigo-700">{selectedSubclasses.join(', ')}</strong></span>
                    )}
                  </span>
                  {selectedSubclasses.length > 0 && (
                    <Badge className="bg-emerald-100 text-emerald-800 text-[9.5px]">
                      {selectedSubclasses.length} Subclass{selectedSubclasses.length > 1 ? 'es' : ''} Selected
                    </Badge>
                  )}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3">
              <div>
                <label className="text-[10px] font-semibold text-slate-500 block mb-0.5">Candidate Career Titles / Roles</label>
                <Input
                  value={profession}
                  onChange={e => setProfession(e.target.value)}
                  placeholder="e.g. Software Developer, Systems Analyst"
                  className="h-8 text-xs font-semibold"
                  data-testid="suggester-profession-input"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-500 block mb-0.5">Total Career Exp (Years)</label>
                <Input
                  type="number"
                  step="0.5"
                  value={expYears}
                  onChange={e => setExpYears(e.target.value)}
                  placeholder="e.g. 5.0"
                  className="h-8 text-xs font-semibold"
                  data-testid="suggester-exp-input"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-500 block mb-0.5">Highest Qualification</label>
                <Input
                  value={qualification}
                  onChange={e => setQualification(e.target.value)}
                  placeholder="e.g. Bachelor / B.Com / B.Tech"
                  className="h-8 text-xs"
                  data-testid="suggester-qual-input"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-500 block mb-0.5">Field of Study</label>
                <Input
                  value={fieldOfStudy}
                  onChange={e => setFieldOfStudy(e.target.value)}
                  placeholder="e.g. Computer Science / Commerce"
                  className="h-8 text-xs"
                  data-testid="suggester-field-input"
                />
              </div>
            </div>

            <p className="text-[10px] font-semibold text-slate-500 mb-1">{country === 'AU' ? '3' : '2'}. Career Chronology &amp; Job Duties (Past &amp; Present Roles)</p>
            <Textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={5}
              placeholder="e.g. 3 years as Software Developer at TechCorp designing backend APIs with Python/Django and React. 2 years as Systems Analyst at DataSoft gathering system specifications, database schemas, and cloud deployments."
              data-testid="suggester-description"
              className="text-xs"
            />
            <p className="text-[10px] text-slate-400 mt-1">Evaluates candidate's entire career chronology across all roles to suggest matching occupation codes for each eligible career stage.</p>
            {error && (
              <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded p-2.5 text-xs flex items-center justify-between mt-3">
                <span className="flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                  {error}
                </span>
                <Button size="sm" variant="ghost" className="h-7 text-xs text-amber-800 hover:bg-amber-100" onClick={() => submit()}>
                  Retry
                </Button>
              </div>
            )}
            <div className="flex gap-2 justify-end mt-3">
              <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
              <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700 font-semibold" onClick={() => submit()} disabled={loading} data-testid="suggester-submit">
                {loading ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Bot className="h-3 w-3 mr-1" />}
                {loading
                  ? 'Analyzing ANZSCO 2013 & OSCA 2022 Rules…'
                  : selectedSubclasses.length > 0
                  ? `Analyze & Find Codes for Subclass ${selectedSubclasses.join(', ')}`
                  : targetFramework === 'ANZSCO_2013'
                  ? 'Analyze & Find Codes for ANZSCO 2013 (GSM)'
                  : targetFramework === 'OSCA_2022'
                  ? 'Analyze & Find Codes for OSCA 2022 (Employer)'
                  : 'Analyze & Find Matching Codes & Deductions'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between mb-2">
              <div>
                <p className="text-[11px] text-slate-700 font-medium">
                  Suggested codes for: <b>{countryName(searchedCountry)}</b>
                  {qualification && <span className="ml-1 text-slate-500">· {qualification} ({fieldOfStudy || 'General'}) · {expYears || 0} yrs exp</span>}
                </p>
                {selectedSubclasses.length > 0 && (
                  <p className="text-[10px] text-indigo-700 font-semibold flex items-center gap-1 mt-0.5">
                    <Layers className="h-3 w-3 text-indigo-600" />
                    Targeted Subclasses: {selectedSubclasses.join(', ')} ({targetFramework !== 'ALL' ? (targetFramework === 'ANZSCO_2013' ? 'ANZSCO 2013 GSM' : 'OSCA 2022 Employer') : 'Dual Framework'})
                  </p>
                )}
              </div>
              {searchedCountry !== 'ALL' && (
                <Button size="sm" variant="outline" className="h-7 text-[10px]" onClick={() => submit('ALL')} disabled={loading} data-testid="suggester-search-all">
                  🌐 Search all countries
                </Button>
              )}
            </div>

            {/* Search Bar above suggestions for missing codes */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 mb-3 space-y-2 shadow-sm" data-testid="suggester-search-section">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5">
                  <Search className="h-3.5 w-3.5 text-indigo-600" />
                  Cannot find your target occupation? Search &amp; add any code:
                </span>
                <span className="text-[10px] text-slate-400">Strictly 6-digit codes for Australia</span>
              </div>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') executeSearch(); }}
                    placeholder={searchedCountry === 'AU' || country === 'AU'
                      ? 'Search by 6-digit code or title (e.g. 261313 or Software Engineer)...'
                      : 'Search by code or occupation title...'}
                    className="h-8 text-xs pl-8 bg-white"
                    data-testid="suggester-search-input"
                  />
                  <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                  {searchQuery && (
                    <button
                      onClick={() => { setSearchQuery(''); setSearchResults([]); }}
                      className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 text-xs px-1"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <Button
                  size="sm"
                  onClick={executeSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="h-8 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-medium"
                  data-testid="suggester-search-submit"
                >
                  {searching ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Search className="h-3 w-3 mr-1" />}
                  Search
                </Button>
              </div>

              {/* Render Search Results Dropdown/Card List */}
              {searchResults.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-200/80 space-y-1.5 max-h-48 overflow-y-auto">
                  <span className="text-[10px] font-semibold uppercase text-slate-500 block">
                    Found {searchResults.length} matching occupation{searchResults.length > 1 ? 's' : ''}:
                  </span>
                  <div className="space-y-1">
                    {searchResults.map((item, sidx) => (
                      <div
                        key={sidx}
                        className="flex items-center justify-between p-2 bg-white rounded border border-slate-200 hover:border-indigo-300 transition text-xs"
                      >
                        <div>
                          <span className="font-bold text-slate-800">{item.code} · {item.title}</span>
                          <span className="text-[10px] text-slate-400 ml-2">({item.assessing_body || 'Assessing Body'} · {item.pathway || 'Core Skills'})</span>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 text-[10px] border-indigo-300 text-indigo-700 hover:bg-indigo-50"
                          onClick={() => addSearchedOccupation(item)}
                          data-testid={`add-searched-occ-${sidx}`}
                        >
                          <Plus className="h-3 w-3 mr-1" /> Add &amp; Select
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Filter by Visa Subclass & Framework */}
            {(searchedCountry === 'AU' || country === 'AU') && (suggestions.suggestions || []).length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap mb-2.5 text-[11px] bg-slate-50 p-2 rounded-lg border border-slate-200" data-testid="suggester-subclass-filter-bar">
                <span className="font-bold text-slate-700 flex items-center gap-1">
                  <Layers className="h-3.5 w-3.5 text-indigo-600" /> Filter by Visa Subclass:
                </span>
                <button
                  type="button"
                  onClick={() => setActiveFilterSubclass('ALL')}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${activeFilterSubclass === 'ALL' ? 'bg-indigo-600 text-white' : 'bg-white border text-slate-600 hover:bg-slate-100'}`}
                  data-testid="filter-subclass-ALL"
                >
                  All ({(suggestions.suggestions || []).length})
                </button>
                {['189', '190', '491', '482', '186', '494', '485'].map(sc => {
                  const cnt = (suggestions.suggestions || []).filter(s => (s.eligible_visas || []).includes(sc)).length;
                  if (cnt === 0) return null;
                  return (
                    <button
                      key={sc}
                      type="button"
                      onClick={() => setActiveFilterSubclass(sc)}
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${activeFilterSubclass === sc ? 'bg-sky-600 text-white' : 'bg-white border text-slate-700 hover:bg-sky-50'}`}
                      data-testid={`filter-subclass-${sc}`}
                    >
                      Subclass {sc} ({cnt})
                    </button>
                  );
                })}
                <button
                  type="button"
                  onClick={() => setActiveFilterSubclass('ANZSCO_2013')}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${activeFilterSubclass === 'ANZSCO_2013' ? 'bg-sky-700 text-white' : 'bg-white border text-sky-800 hover:bg-sky-50'}`}
                  data-testid="filter-framework-ANZSCO_2013"
                >
                  🏛️ ANZSCO 2013 GSM
                </button>
                <button
                  type="button"
                  onClick={() => setActiveFilterSubclass('OSCA_2022')}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${activeFilterSubclass === 'OSCA_2022' ? 'bg-purple-700 text-white' : 'bg-white border text-purple-800 hover:bg-purple-50'}`}
                  data-testid="filter-framework-OSCA_2022"
                >
                  🚀 OSCA 2022 Employer
                </button>
              </div>
            )}

            <div className="space-y-3">
              {((suggestions.suggestions || []).filter(s => {
                if (activeFilterSubclass === 'ALL') return true;
                if (activeFilterSubclass === 'ANZSCO_2013') {
                  return Boolean(s.classification_versions?.anzsco_2013?.is_eligible);
                }
                if (activeFilterSubclass === 'OSCA_2022') {
                  return Boolean(s.classification_versions?.osca_2022?.is_eligible);
                }
                return (s.eligible_visas || []).includes(activeFilterSubclass);
              })).map((s, i) => {
                const sel = isSelected(s);
                const sa = s.skills_assessment || {};
                const isPositive = sa.is_positive !== false;
                const rplReq = Boolean(sa.rpl_required);
                const cdrReq = Boolean(sa.cdr_required);
                const deducted = sa.deducted_years != null ? Number(sa.deducted_years) : 0;
                const claimableYrs = sa.points_claimable_years != null ? Number(sa.points_claimable_years) : 0;
                const claimablePts = sa.points_claimable_points != null ? Number(sa.points_claimable_points) : 0;

                return (
                  <Card
                    key={`${s.code}-${s.country_code || 'X'}`}
                    className={`p-3.5 transition rounded-lg border ${sel ? 'ring-2 ring-indigo-500 border-indigo-500 bg-indigo-50/20' : 'border-slate-200 hover:border-slate-300'}`}
                    data-testid={`suggestion-${i}`}
                  >
                    {/* Header: Rank + Code + Title + Country */}
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-sm font-bold text-slate-800">
                            {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '•'} {s.code} · {s.title}
                          </span>
                          {s.country_code && (
                            <Badge className="bg-slate-800 text-white text-[9px]" data-testid={`suggestion-country-${i}`}>
                              {(COUNTRIES.find(c => c.code === s.country_code)?.flag || '')} {s.country_code}
                            </Badge>
                          )}
                          <Badge className={s.confidence === 'high' ? 'bg-emerald-100 text-emerald-800 text-[9px]' : s.confidence === 'medium' ? 'bg-amber-100 text-amber-800 text-[9px]' : 'bg-slate-100 text-slate-600 text-[9px]'}>
                            {s.confidence?.toUpperCase()} MATCH
                          </Badge>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Assessing Authority: <strong className="text-slate-700">{s.assessing_body}</strong> · Pathway: <span className="text-indigo-600 font-medium">{sa.pathway_name || s.pathway || 'General Migration'}</span>
                        </p>

                        {/* Quick Eligible Subclasses Badges */}
                        {s.subclass_summary && (
                          <div className="flex items-center gap-1.5 flex-wrap my-1 text-[10px]" data-testid={`subclass-badges-${i}`}>
                            <span className="font-semibold text-slate-500">Eligible Subclasses:</span>
                            {s.classification_versions?.anzsco_2013?.active_subclasses?.map(sc => (
                              <Badge key={`anz-${sc}`} className="bg-sky-100 text-sky-800 border border-sky-300 font-bold text-[9px]">
                                🏛️ 2013: Subclass {sc}
                              </Badge>
                            ))}
                            {s.classification_versions?.osca_2022?.active_subclasses?.map(sc => (
                              <Badge key={`osca-${sc}`} className="bg-purple-100 text-purple-800 border border-purple-300 font-bold text-[9px]">
                                🚀 2022: Subclass {sc}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>

                      <Button
                        size="sm"
                        variant={sel ? 'default' : 'outline'}
                        className={`text-xs h-8 px-3 shrink-0 ${sel ? 'bg-indigo-600 hover:bg-indigo-700 text-white font-semibold' : 'hover:border-indigo-400'}`}
                        onClick={() => toggleSelect(s)}
                        data-testid={`select-suggestion-${i}`}
                      >
                        {sel ? <><Check className="h-3.5 w-3.5 mr-1" />Selected{selected.length > 1 && selected[0] && keyOf(selected[0]) === keyOf(s) ? ' · Primary' : ''}</> : <>Select Code <ChevronRight className="h-3.5 w-3.5 ml-1" /></>}
                      </Button>
                    </div>

                    {/* AI Job Alignment Reasoning */}
                    <p className="text-[11px] text-slate-600 bg-slate-50 p-2 rounded border border-slate-100 mb-2">
                      <strong className="text-slate-700">Role Alignment:</strong> {s.reasoning}
                    </p>

                    {/* Core Duty & Task Alignment against ABS ANZSCO */}
                    {s.duty_alignment && (
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 mb-2 space-y-1.5" data-testid={`duty-alignment-${i}`}>
                        <div className="flex items-center justify-between text-[11px]">
                          <div className="flex items-center gap-1.5 font-bold text-slate-800">
                            <ListChecks className="h-3.5 w-3.5 text-emerald-600" />
                            <span>Core Duty &amp; Task Alignment</span>
                          </div>
                          <Badge className="bg-emerald-100 text-emerald-800 text-[9px] font-semibold border border-emerald-200">
                            {s.duty_alignment.match_percentage}% Match ({s.duty_alignment.matched_tasks_count}/{s.duty_alignment.total_tasks_count} tasks)
                          </Badge>
                        </div>
                        <p className="text-[10.5px] text-slate-600 leading-tight">
                          {s.duty_alignment.summary}
                        </p>
                        {s.duty_alignment.matched_tasks && s.duty_alignment.matched_tasks.length > 0 && (
                          <div className="space-y-1 pt-1 border-t border-slate-200/60">
                            <span className="text-[9px] font-semibold uppercase text-slate-400 block">Matched Official ABS ANZSCO Tasks:</span>
                            <div className="space-y-0.5">
                              {s.duty_alignment.matched_tasks.map((t, tidx) => (
                                <div key={tidx} className="flex items-start gap-1.5 text-[10.5px] text-slate-700 bg-white/90 p-1.5 rounded border border-slate-100 leading-tight">
                                  <span className="text-emerald-600 font-bold shrink-0">✓</span>
                                  <span>{t}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Company Sector & Age GSM Points Evaluation */}
                    {(s.company_alignment || s.age_evaluation) && (
                      <div className="grid grid-cols-2 gap-2 mb-2 text-[10.5px]">
                        {s.company_alignment && (
                          <div className="bg-slate-50 border border-slate-200 rounded p-2 flex items-start gap-1.5">
                            <Building2 className="h-3.5 w-3.5 text-indigo-600 shrink-0 mt-0.5" />
                            <div>
                              <span className="font-bold text-slate-700 block">Employer &amp; Sector Fit</span>
                              <span className="text-slate-600 leading-tight block">{s.company_alignment.summary}</span>
                            </div>
                          </div>
                        )}
                        {s.age_evaluation && (
                          <div className="bg-slate-50 border border-slate-200 rounded p-2 flex items-start gap-1.5">
                            <Award className="h-3.5 w-3.5 text-amber-600 shrink-0 mt-0.5" />
                            <div>
                              <span className="font-bold text-slate-700 block">Age GSM Migration Points</span>
                              <span className="text-slate-600 leading-tight block">{s.age_evaluation.summary}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Assessing Body Deductions & Rules Analysis Box */}
                    <div className="bg-gradient-to-r from-amber-50/80 to-indigo-50/80 border border-indigo-100 rounded-lg p-2.5 space-y-1.5">
                      <div className="flex items-center justify-between flex-wrap gap-1">
                        <div className="flex items-center gap-1.5">
                          <Scale className="h-3.5 w-3.5 text-indigo-700" />
                          <span className="text-[11px] font-bold text-slate-800">
                            Assessment Criteria &amp; Experience Deductions
                          </span>
                        </div>
                        <Badge className={
                          rplReq
                            ? 'bg-amber-600 text-white text-[9px]'
                            : isPositive
                            ? 'bg-emerald-600 text-white text-[9px]'
                            : 'bg-rose-600 text-white text-[9px]'
                        }>
                          {sa.assessment_outcome || (isPositive ? 'Likely Positive' : 'Review Required')}
                        </Badge>
                      </div>

                      {/* 3-Pill Metric Comparison */}
                      <div className="grid grid-cols-3 gap-1.5 text-center pt-0.5">
                        <div className="bg-white/90 border border-slate-200 rounded p-1.5 shadow-sm">
                          <span className="text-[9px] text-slate-400 block uppercase font-semibold">Qualifying Deduction</span>
                          <span className={`text-xs font-bold ${deducted > 0 ? 'text-rose-600' : 'text-slate-700'}`}>
                            {deducted > 0 ? `-${deducted.toFixed(1)} yrs` : '0.0 yrs'}
                          </span>
                        </div>
                        <div className="bg-white/90 border border-slate-200 rounded p-1.5 shadow-sm">
                          <span className="text-[9px] text-slate-400 block uppercase font-semibold">Claimable Experience</span>
                          <span className="text-xs font-bold text-emerald-700">
                            {claimableYrs.toFixed(1)} yrs
                          </span>
                        </div>
                        <div className="bg-white/90 border border-slate-200 rounded p-1.5 shadow-sm">
                          <span className="text-[9px] text-slate-400 block uppercase font-semibold">GSM Points Claim</span>
                          <span className="text-xs font-bold text-indigo-700">
                            +{claimablePts} Points
                          </span>
                        </div>
                      </div>

                      {/* Specific Deduction Rationale & Conditions */}
                      <div className="text-[10px] text-slate-700 space-y-0.5 pt-0.5 leading-snug">
                        {rplReq && (
                          <div className="flex items-center gap-1 text-amber-800 font-semibold bg-amber-100/70 px-2 py-0.5 rounded">
                            <FileText className="h-3 w-3 shrink-0" />
                            <span>RPL Pathway Required: 6 years deducted for Non-ICT degree + 2 Project Reports required.</span>
                          </div>
                        )}
                        {cdrReq && (
                          <div className="flex items-center gap-1 text-blue-800 font-semibold bg-blue-100/70 px-2 py-0.5 rounded">
                            <Award className="h-3 w-3 shrink-0" />
                            <span>Engineers Australia: CDR Pathway required (3 Career Episodes + CPD) for non-accredited degrees.</span>
                          </div>
                        )}
                        {sa.justification ? (
                          <p className="text-slate-600 line-clamp-2">
                            <strong className="text-slate-700">Adviser note:</strong> {sa.justification}
                          </p>
                        ) : sa.conditions_summary ? (
                          <p className="text-slate-600">
                            <strong className="text-slate-700">Criteria:</strong> {sa.conditions_summary}
                          </p>
                        ) : null}
                      </div>
                    </div>

                    {/* Dual Australian Classification Versions (ANZSCO 2013 vs OSCA 2022) */}
                    {s.classification_versions && (
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 space-y-1.5" data-testid={`classification-versions-${i}`}>
                        <div className="flex items-center justify-between text-[11px]">
                          <div className="flex items-center gap-1.5 font-bold text-slate-800">
                            <Layers className="h-3.5 w-3.5 text-indigo-600" />
                            <span>Classification Versions &amp; Eligible Visas</span>
                          </div>
                          <Badge className="bg-indigo-100 text-indigo-800 text-[9px] font-semibold">Dual Framework</Badge>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[10.5px]">
                          {/* ANZSCO 2013 Card */}
                          <div className="bg-white p-2 rounded border border-sky-200">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-sky-900 flex items-center gap-1">
                                🏛️ ANZSCO 2013
                              </span>
                              <Badge className="bg-sky-100 text-sky-800 text-[8.5px]">GSM Points-Tested</Badge>
                            </div>
                            <p className="text-slate-600 text-[10px] mb-1">
                              {s.classification_versions.anzsco_2013?.summary || 'Governs Subclasses 189, 190, 491, 494'}
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {(s.classification_versions.anzsco_2013?.active_subclasses || []).map(sc => (
                                <Badge key={sc} className="bg-sky-600 text-white text-[8.5px]">
                                  Subclass {sc}
                                </Badge>
                              ))}
                              {(!s.classification_versions.anzsco_2013?.active_subclasses || s.classification_versions.anzsco_2013.active_subclasses.length === 0) && (
                                <span className="text-[10px] text-slate-400 italic">No active subclasses</span>
                              )}
                            </div>
                          </div>

                          {/* OSCA 2022 Card */}
                          <div className="bg-white p-2 rounded border border-purple-200">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-purple-900 flex items-center gap-1">
                                🚀 OSCA 2022
                              </span>
                              <Badge className="bg-purple-100 text-purple-800 text-[8.5px]">Core Skills / Employer</Badge>
                            </div>
                            <p className="text-slate-600 text-[10px] mb-1">
                              {s.classification_versions.osca_2022?.summary || 'Governs Subclasses 482, 186, 407, 485'}
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {(s.classification_versions.osca_2022?.active_subclasses || []).map(sc => (
                                <Badge key={sc} className="bg-purple-600 text-white text-[8.5px]">
                                  Subclass {sc}
                                </Badge>
                              ))}
                              {(!s.classification_versions.osca_2022?.active_subclasses || s.classification_versions.osca_2022.active_subclasses.length === 0) && (
                                <span className="text-[10px] text-slate-400 italic">No active subclasses</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>

            {suggestions.general_advice && (
              <p className="text-[11px] italic mt-3 text-slate-600 bg-slate-50 p-2 rounded border border-slate-200">
                💡 {suggestions.general_advice}
              </p>
            )}

            <div className="flex gap-2 justify-between items-center mt-3 pt-2 border-t">
              <p className="text-[10px] text-slate-500" data-testid="suggester-selected-count">
                {selected.length > 0
                  ? `${selected.length} selected · first will be primary occupation`
                  : 'Select one or more codes to apply them to the assessment'}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => { setSuggestions(null); setSelected([]); }}>
                  Modify Inputs
                </Button>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
                  onClick={useSelected}
                  disabled={selected.length === 0}
                  data-testid="suggester-use-selected"
                >
                  {selected.length > 1 ? `Use ${selected.length} Selected Codes` : 'Use Selected Code'}
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}

