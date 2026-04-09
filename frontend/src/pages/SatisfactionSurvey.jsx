import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Star, ThumbsUp, Send, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function SatisfactionSurvey({ token, role, caseId = null }) {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(caseId || '');
  const [survey, setSurvey] = useState(null);
  const [form, setForm] = useState({ overall_rating: 0, communication_rating: 0, speed_rating: 0, documentation_rating: 0, feedback: '', would_recommend: true });
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (role === 'client') fetchCases();
    if (role === 'admin' || role === 'case_manager') fetchStats();
  }, []);

  useEffect(() => { if (selectedCase) checkSurvey(); }, [selectedCase]);

  const fetchCases = async () => {
    try {
      const res = await fetch(`${API}/api/cases/my-cases`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setCases(Array.isArray(data) ? data : []);
    } catch (e) { console.error(e); }
  };

  const checkSurvey = async () => {
    try {
      const res = await fetch(`${API}/api/surveys/case/${selectedCase}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.id) setSurvey(data);
      else setSurvey(null);
    } catch (e) { console.error(e); }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API}/api/surveys/stats`, { headers: { Authorization: `Bearer ${token}` } });
      setStats(await res.json());
    } catch (e) { console.error(e); }
  };

  const submitSurvey = async () => {
    if (!selectedCase || form.overall_rating === 0) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/surveys/submit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ case_id: selectedCase, ...form })
      });
      if (res.ok) { setSubmitted(true); checkSurvey(); }
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const StarRating = ({ value, onChange, label }) => (
    <div className="space-y-1">
      <label className="text-sm font-medium text-gray-700">{label}</label>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map(i => (
          <button key={i} onClick={() => onChange(i)} className="focus:outline-none">
            <Star className={`w-6 h-6 transition-colors ${i <= value ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`} />
          </button>
        ))}
      </div>
    </div>
  );

  // Admin/CM View - Stats
  if (role === 'admin' || role === 'case_manager') {
    return (
      <div className="space-y-6" data-testid="survey-stats">
        {stats && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-4 text-center">
                  <p className="text-3xl font-bold text-yellow-500">{stats.avg_rating || 0}</p>
                  <p className="text-sm text-gray-600">Avg Rating</p>
                  <div className="flex justify-center mt-1">
                    {[1,2,3,4,5].map(i => <Star key={i} className={`w-4 h-4 ${i <= Math.round(stats.avg_rating || 0) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-300'}`} />)}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 text-center">
                  <p className="text-3xl font-bold text-green-500">{stats.recommend_pct || 0}%</p>
                  <p className="text-sm text-gray-600">Would Recommend</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 text-center">
                  <p className="text-3xl font-bold text-blue-500">{stats.total || 0}</p>
                  <p className="text-sm text-gray-600">Total Surveys</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 text-center">
                  <p className="text-3xl font-bold text-purple-500">{stats.avg_communication || 0}</p>
                  <p className="text-sm text-gray-600">Communication</p>
                </CardContent>
              </Card>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Card>
                <CardContent className="pt-4 text-center">
                  <p className="text-2xl font-bold">{stats.avg_speed || 0}</p>
                  <p className="text-sm text-gray-600">Speed Rating</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 text-center">
                  <p className="text-2xl font-bold">{stats.avg_documentation || 0}</p>
                  <p className="text-sm text-gray-600">Documentation Rating</p>
                </CardContent>
              </Card>
            </div>
          </>
        )}
        {(!stats || stats.total === 0) && (
          <Card><CardContent className="py-8 text-center text-gray-500"><Star className="w-12 h-12 mx-auto mb-3 text-gray-300" /><p>No surveys submitted yet.</p></CardContent></Card>
        )}
      </div>
    );
  }

  // Client View - Submit Survey
  return (
    <div className="space-y-6" data-testid="survey-form">
      {submitted && <Card className="border-green-200 bg-green-50"><CardContent className="pt-4"><p className="text-green-800 font-medium flex items-center gap-2"><ThumbsUp className="w-5 h-5" /> Thank you for your feedback!</p></CardContent></Card>}

      {!caseId && (
        <select className="w-full border rounded-md p-2 text-sm" value={selectedCase} onChange={e => setSelectedCase(e.target.value)} data-testid="survey-case-select">
          <option value="">Select a case to review</option>
          {cases.map(c => <option key={c.id} value={c.id}>{c.case_id} — {c.product_name}</option>)}
        </select>
      )}

      {selectedCase && survey && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-4">
            <p className="text-blue-800">Survey already submitted. Rating: {survey.overall_rating}/5</p>
          </CardContent>
        </Card>
      )}

      {selectedCase && !survey && !submitted && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Rate Your Experience</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <StarRating label="Overall Experience" value={form.overall_rating} onChange={v => setForm({ ...form, overall_rating: v })} />
            <StarRating label="Communication" value={form.communication_rating} onChange={v => setForm({ ...form, communication_rating: v })} />
            <StarRating label="Speed of Service" value={form.speed_rating} onChange={v => setForm({ ...form, speed_rating: v })} />
            <StarRating label="Documentation Support" value={form.documentation_rating} onChange={v => setForm({ ...form, documentation_rating: v })} />
            <div>
              <label className="text-sm font-medium text-gray-700">Additional Feedback</label>
              <textarea className="w-full border rounded-md p-2 mt-1 text-sm" rows={3} placeholder="Tell us about your experience..." value={form.feedback} onChange={e => setForm({ ...form, feedback: e.target.value })} data-testid="survey-feedback" />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.would_recommend} onChange={e => setForm({ ...form, would_recommend: e.target.checked })} />
              I would recommend LEAMSS to others
            </label>
            <Button onClick={submitSurvey} disabled={loading || form.overall_rating === 0} data-testid="survey-submit-btn">
              {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              Submit Feedback
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
