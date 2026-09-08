import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { 
  Briefcase, CheckCircle2, AlertTriangle, Search, 
  Send, Sparkles, Clock, ShieldCheck, ChevronRight, X
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || (typeof window !== 'undefined' && window.location.hostname.includes('leamss.com') ? 'https://api.leamss.com' : 'http://localhost:8001');
const API = `${BACKEND_URL}/api`;

export default function ClientOccupationReviewCard({ caseData, onUpdated, getAuthHeader }) {
  const [showSuggestModal, setShowSuggestModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [customCode, setCustomCode] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [customAssessingBody, setCustomAssessingBody] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!caseData) return null;

  const occCode = caseData.occupation_code || caseData.suggested_occupation_code || 'Not Set';
  const occTitle = caseData.occupation_title || caseData.suggested_occupation_title || caseData.product_name || caseData.service_type || 'General Skilled Profile';
  const assessingBody = caseData.assessing_authority_code || caseData.suggested_assessing_authority_code || caseData.assessing_body || (caseData.country === 'AU' ? 'VETASSESS / ACS' : (caseData.country === 'CA' ? 'WES / ECA' : 'Skills Authority'));
  const reviewStatus = caseData.client_occupation_review_status || 'pending_client_review';

  const getAuth = () => {
    if (typeof getAuthHeader === 'function') {
      try { return getAuthHeader(); } catch (e) {}
    }
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : '';
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const handleAccept = async () => {
    setSubmitting(true);
    const targetId = caseData.id || caseData.pre_assessment_number || caseData.custom_id;
    try {
      try {
        await axios.post(
          `${API}/pre-assessment/${targetId}/client-occupation-decision`,
          { decision: 'accepted' },
          getAuth()
        );
      } catch (err1) {
        try {
          await axios.post(
            `${API}/pre-assess-portal/client/occupation-decision/${targetId}`,
            { decision: 'accepted' },
            getAuth()
          );
        } catch (err2) {
          await axios.post(
            `${API}/cases/${targetId}/client-occupation-decision`,
            { decision: 'accepted' },
            getAuth()
          );
        }
      }
      toast.success('Occupation profile confirmed! Profile and document checklist unlocked.');
      if (onUpdated) onUpdated();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to accept occupation code');
    }
    setSubmitting(false);
  };

  const handleSearchOcc = async (query) => {
    setSearchQuery(query);
    if (!query || query.trim().length < 1) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    try {
      const countryRaw = String(caseData.country || (caseData.product_name?.includes('Canada') ? 'CA' : 'AU'));
      const countryCode = countryRaw.length === 2 ? countryRaw.toUpperCase() : (countryRaw.toUpperCase().includes('CA') ? 'CA' : 'AU');
      const res = await axios.get(
        `${API}/sales/occupations/search?q=${encodeURIComponent(query.trim())}&country=${countryCode}`,
        getAuth()
      );
      const items = res.data?.items || res.data?.results || (Array.isArray(res.data) ? res.data : []);
      setSearchResults(items.slice(0, 10));
    } catch (e) {
      console.error('Occupation search error:', e);
      setSearchResults([]);
    }
    setSearching(false);
  };

  const selectItem = (item) => {
    setSelectedSuggestion(item);
    setCustomCode(item.code || '');
    setCustomTitle(item.title || '');
    setCustomAssessingBody(item.assessing_body || item.assessing_authority_code || '');
    setSearchResults([]);
  };

  const handleSubmitSuggestion = async () => {
    const code = selectedSuggestion?.code || customCode.trim();
    const title = selectedSuggestion?.title || customTitle.trim();
    const body = selectedSuggestion?.assessing_body || customAssessingBody.trim();

    if (!code && !notes.trim()) {
      toast.error('Please enter a suggested occupation code/title or specify your remarks.');
      return;
    }

    setSubmitting(true);
    const targetId = caseData.id || caseData.pre_assessment_number || caseData.custom_id;
    const payload = {
      decision: 'rejected',
      suggested_code: code,
      suggested_title: title,
      suggested_assessing_body: body,
      notes: notes.trim()
    };
    try {
      try {
        await axios.post(
          `${API}/pre-assessment/${targetId}/client-occupation-decision`,
          payload,
          getAuth()
        );
      } catch (err1) {
        try {
          await axios.post(
            `${API}/pre-assess-portal/client/occupation-decision/${targetId}`,
            payload,
            getAuth()
          );
        } catch (err2) {
          await axios.post(
            `${API}/cases/${targetId}/client-occupation-decision`,
            payload,
            getAuth()
          );
        }
      }
      toast.success('Your suggestion has been submitted to your Migration Partner & Case Manager.');
      setShowSuggestModal(false);
      if (onUpdated) onUpdated();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to submit suggestion');
    }
    setSubmitting(false);
  };

  // Shared Suggestion Modal
  const renderSuggestModal = () => {
    if (!showSuggestModal) return null;
    return (
      <div className="fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden border-0 animate-in fade-in zoom-in-95 duration-200">
          <div className="bg-gradient-to-r from-teal-800 to-slate-900 text-white p-5 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold">Suggest Alternate Occupation Code</h3>
              <p className="text-xs text-teal-200 mt-0.5">
                Assigned: <span className="font-mono text-amber-300">{occCode}</span> ({occTitle})
              </p>
            </div>
            <button
              onClick={() => setShowSuggestModal(false)}
              className="p-1 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
            {/* Search Box */}
            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wide block mb-1">
                Search Desired Profession / Code
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Type title or code (e.g. 261312, Nurse, Chef, Developer)..."
                  value={searchQuery}
                  onChange={(e) => handleSearchOcc(e.target.value)}
                  className="pl-9 text-sm rounded-xl border-slate-200 h-10"
                  data-testid="client-occ-search-input"
                />
                {searching && (
                  <div className="absolute right-3 top-2.5 text-xs text-slate-400">
                    Searching...
                  </div>
                )}
              </div>

              {/* Search Results Dropdown */}
              {searchResults.length > 0 && (
                <div className="mt-2 bg-slate-50 border border-slate-200 rounded-xl max-h-48 overflow-y-auto divide-y shadow-inner">
                  {searchResults.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => selectItem(item)}
                      className="p-2.5 hover:bg-teal-50 cursor-pointer flex items-center justify-between text-xs transition"
                    >
                      <div>
                        <span className="font-mono font-bold text-teal-700 mr-2">{item.code}</span>
                        <span className="font-medium text-slate-800">{item.title}</span>
                      </div>
                      {item.assessing_body && (
                        <Badge variant="outline" className="text-[10px] text-slate-600 bg-white">
                          {item.assessing_body}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Selected Suggestion Box */}
            {selectedSuggestion ? (
              <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase font-bold text-teal-600">Selected Suggestion</p>
                  <p className="text-sm font-bold text-teal-900">
                    {selectedSuggestion.code} · {selectedSuggestion.title}
                  </p>
                  {selectedSuggestion.assessing_body && (
                    <p className="text-xs text-teal-700">Authority: {selectedSuggestion.assessing_body}</p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => { setSelectedSuggestion(null); setCustomCode(''); setCustomTitle(''); }}
                  className="text-xs text-teal-700 hover:bg-teal-100"
                >
                  Change
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-[11px] font-semibold text-slate-600 block mb-1">Direct Code (Optional)</label>
                  <Input
                    placeholder="e.g. 261312"
                    value={customCode}
                    onChange={(e) => setCustomCode(e.target.value)}
                    className="text-xs rounded-lg h-9 font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-600 block mb-1">Occupation Title (Optional)</label>
                  <Input
                    placeholder="e.g. Developer Programmer"
                    value={customTitle}
                    onChange={(e) => setCustomTitle(e.target.value)}
                    className="text-xs rounded-lg h-9"
                  />
                </div>
              </div>
            )}

            {/* Reason / Notes */}
            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wide block mb-1">
                Reason for Request (Why this fits better?)
              </label>
              <textarea
                rows={3}
                placeholder="Explain why you feel this code fits your qualification and work experience..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full p-3 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-teal-500 outline-none resize-none"
                data-testid="client-occ-notes"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2.5">
              <Button
                variant="outline"
                onClick={() => setShowSuggestModal(false)}
                className="rounded-xl text-xs h-9"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSubmitSuggestion}
                disabled={submitting}
                className="bg-[#f7620b] hover:bg-[#e55a09] text-white font-semibold text-xs h-9 px-4 rounded-xl flex items-center gap-1.5"
                data-testid="submit-client-occ-suggestion-btn"
              >
                <Send className="h-3.5 w-3.5" />
                {submitting ? 'Submitting...' : 'Submit Suggestion'}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  };

  // State: Accepted
  if (reviewStatus === 'accepted') {
    return (
      <>
        <Card className="p-4 bg-emerald-50/90 border-2 border-emerald-300 shadow-sm rounded-2xl mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-md">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-bold text-emerald-950 text-base">Confirmed Occupation Profile</span>
                  <Badge className="bg-emerald-600 text-white text-xs px-2.5 py-0.5 font-bold font-mono">
                    {occCode}
                  </Badge>
                  <Badge variant="outline" className="border-emerald-600 text-emerald-800 text-xs font-semibold bg-white">
                    {assessingBody}
                  </Badge>
                </div>
                <p className="text-xs text-emerald-800 font-medium mt-0.5">
                  {occTitle} · Confirmed for your migration application
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-100 px-3 py-1.5 rounded-lg border border-emerald-300 shadow-sm">
                <CheckCircle2 className="h-4 w-4" /> Verified by You
              </div>
              <Button
                onClick={() => setShowSuggestModal(true)}
                variant="outline"
                size="sm"
                className="h-8 text-xs font-semibold border-emerald-400 text-emerald-900 bg-white hover:bg-emerald-100/70 shadow-sm flex items-center gap-1.5"
                data-testid="suggest-different-code-accepted-btn"
              >
                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                Suggest Different Code
              </Button>
            </div>
          </div>
        </Card>
        {renderSuggestModal()}
      </>
    );
  }

  // State: Rejected by client / Change requested
  if (reviewStatus === 'rejected_by_client') {
    return (
      <>
        <Card className="p-5 bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300 shadow-md rounded-2xl mb-6">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow">
                <Clock className="h-6 w-6" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-bold text-amber-950 text-base">Occupation Change Request In Progress</h3>
                  <Badge className="bg-amber-600 text-white text-xs font-semibold">Under Review</Badge>
                </div>
                <p className="text-xs text-amber-900 mt-1">
                  You requested a change from <strong>{occCode} ({occTitle})</strong> to:{' '}
                  <strong className="text-amber-950">
                    {caseData.client_suggested_occupation_code ? `${caseData.client_suggested_occupation_code} · ${caseData.client_suggested_occupation_title || ''}` : 'Custom Suggestion'}
                  </strong>
                </p>
                {caseData.client_suggested_occupation_notes && (
                  <p className="text-xs text-amber-800 bg-amber-100/80 p-2.5 rounded-lg border border-amber-200 mt-2 italic">
                    "{caseData.client_suggested_occupation_notes}"
                  </p>
                )}
                <p className="text-[11px] text-amber-700 mt-2">
                  Your Migration Partner & Admin are reviewing your requested occupation change. You will be notified once confirmed.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0 flex-wrap">
              <Button
                onClick={() => setShowSuggestModal(true)}
                variant="outline"
                size="sm"
                className="h-8 text-xs font-semibold border-amber-400 text-amber-900 bg-white hover:bg-amber-100"
              >
                Modify Suggestion
              </Button>
              <Button
                onClick={handleAccept}
                disabled={submitting}
                size="sm"
                className="h-8 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
              >
                Accept Assigned Code
              </Button>
            </div>
          </div>
        </Card>
        {renderSuggestModal()}
      </>
    );
  }

  // State: Pending Client Review (Default on first open)
  return (
    <>
      <Card className="p-5 bg-gradient-to-r from-teal-900 via-teal-800 to-slate-900 text-white shadow-xl rounded-2xl mb-6 border-0 relative overflow-hidden">
        {/* Subtle decorative glow */}
        <div className="absolute -top-16 -right-16 w-48 h-48 bg-teal-400/20 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
            <div className="space-y-2 max-w-2xl">
              <div className="flex items-center gap-2">
                <Badge className="bg-[#f7620b] text-white font-semibold text-xs px-2.5 py-0.5 uppercase tracking-wide">
                  Action Required
                </Badge>
                <span className="text-xs text-teal-200 flex items-center gap-1 font-medium">
                  <Sparkles className="h-3.5 w-3.5 text-amber-400" /> Confirm Assigned Skills Assessment Profile
                </span>
              </div>

              <h2 className="text-xl font-bold text-white tracking-tight">
                Review &amp; Accept Your Migration Occupation Code
              </h2>

              <p className="text-xs text-teal-100/90 leading-relaxed">
                Your Case Manager and Partner have mapped your qualifications and experience to the following official ANZSCO occupation profile. 
                Please accept to confirm your profile and proceed with your package selection.
              </p>

              {/* Code Box */}
              <div className="bg-white/10 backdrop-blur-md rounded-xl p-3.5 border border-white/20 flex flex-wrap items-center gap-4 mt-3">
                <div>
                  <p className="text-[10px] text-teal-200 uppercase tracking-wider font-semibold">ANZSCO Code</p>
                  <p className="text-lg font-extrabold text-amber-300 tracking-wide font-mono">{occCode}</p>
                </div>
                <div className="h-8 w-px bg-white/20 hidden sm:block" />
                <div className="flex-1 min-w-[200px]">
                  <p className="text-[10px] text-teal-200 uppercase tracking-wider font-semibold">Occupation Title</p>
                  <p className="text-sm font-bold text-white truncate">{occTitle}</p>
                </div>
                <div className="h-8 w-px bg-white/20 hidden sm:block" />
                <div>
                  <p className="text-[10px] text-teal-200 uppercase tracking-wider font-semibold">Assessing Authority</p>
                  <Badge className="bg-white text-teal-900 font-bold text-xs shadow-sm mt-0.5">
                    {assessingBody}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row lg:flex-col gap-2.5 shrink-0 lg:min-w-[220px]">
              <Button
                onClick={handleAccept}
                disabled={submitting}
                className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold h-11 px-5 rounded-xl shadow-lg shadow-emerald-900/30 transition-all flex items-center justify-center gap-2"
                data-testid="accept-occupation-code-btn"
              >
                <CheckCircle2 className="h-5 w-5" />
                {submitting ? 'Confirming...' : 'Accept Occupation Code'}
              </Button>

              <Button
                onClick={() => setShowSuggestModal(true)}
                disabled={submitting}
                variant="outline"
                className="bg-white/10 hover:bg-white/20 text-white border-white/30 font-medium h-10 px-4 rounded-xl text-xs flex items-center justify-center gap-1.5"
                data-testid="suggest-different-code-btn"
              >
                <AlertTriangle className="h-4 w-4 text-amber-300" />
                Suggest Different Code
              </Button>
            </div>
          </div>
        </div>
      </Card>
      {renderSuggestModal()}
    </>
  );
}
