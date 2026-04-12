import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Brain, TrendingUp, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EligibilityChecker = ({ token }) => {
  const [form, setForm] = useState({
    age: '', education: '', work_experience_years: '', ielts_overall: '',
    country_preference: '', has_job_offer: false, has_relatives_abroad: false,
    marital_status: '', funds_available_inr: '',
  });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const handleCheck = async () => {
    if (!form.age || !form.education) { toast.error('Please fill age and education'); return; }
    setLoading(true);
    try {
      const endpoint = token ? `${API}/client-tools/eligibility-check` : `${API}/client-tools/eligibility-check/public`;
      const res = await axios.post(endpoint, {
        ...form,
        age: parseInt(form.age) || 0,
        work_experience_years: parseFloat(form.work_experience_years) || 0,
        ielts_overall: parseFloat(form.ielts_overall) || 0,
        funds_available_inr: parseFloat(form.funds_available_inr) || 0,
      }, { headers });
      setResults(res.data.results);
      toast.success('Eligibility check complete!');
    } catch (e) {
      toast.error('Check failed');
    }
    setLoading(false);
  };

  const statusIcon = (status) => {
    if (status === 'highly_eligible') return <CheckCircle className="h-6 w-6 text-emerald-500" />;
    if (status === 'eligible') return <TrendingUp className="h-6 w-6 text-blue-500" />;
    if (status === 'needs_improvement') return <AlertTriangle className="h-6 w-6 text-amber-500" />;
    return <XCircle className="h-6 w-6 text-red-500" />;
  };

  const statusColor = (status) => {
    if (status === 'highly_eligible') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (status === 'eligible') return 'bg-blue-100 text-blue-700 border-blue-200';
    if (status === 'needs_improvement') return 'bg-amber-100 text-amber-700 border-amber-200';
    return 'bg-red-100 text-red-700 border-red-200';
  };

  const scoreBarColor = (score) => {
    if (score >= 70) return 'bg-emerald-500';
    if (score >= 50) return 'bg-blue-500';
    if (score >= 30) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-6" data-testid="eligibility-checker">
      {!results ? (
        <>
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Brain className="h-5 w-5 text-[#2a777a]" />Your Profile
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <Label>Age</Label>
                <Input type="number" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} placeholder="e.g. 28" data-testid="elig-age" />
              </div>
              <div>
                <Label>Education</Label>
                <Select value={form.education} onValueChange={(v) => setForm({ ...form, education: v })}>
                  <SelectTrigger data-testid="elig-education"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high_school">High School / 12th</SelectItem>
                    <SelectItem value="diploma">Diploma</SelectItem>
                    <SelectItem value="bachelors">Bachelor's Degree</SelectItem>
                    <SelectItem value="masters">Master's Degree</SelectItem>
                    <SelectItem value="phd">PhD / Doctorate</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Work Experience (years)</Label>
                <Input type="number" step="0.5" value={form.work_experience_years} onChange={(e) => setForm({ ...form, work_experience_years: e.target.value })} placeholder="e.g. 4" data-testid="elig-work-exp" />
              </div>
              <div>
                <Label>IELTS Overall Score</Label>
                <Input type="number" step="0.5" value={form.ielts_overall} onChange={(e) => setForm({ ...form, ielts_overall: e.target.value })} placeholder="e.g. 7.0" data-testid="elig-ielts" />
              </div>
              <div>
                <Label>Country Preference</Label>
                <Select value={form.country_preference} onValueChange={(v) => setForm({ ...form, country_preference: v })}>
                  <SelectTrigger data-testid="elig-country"><SelectValue placeholder="Any" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="canada">Canada</SelectItem>
                    <SelectItem value="australia">Australia</SelectItem>
                    <SelectItem value="uk">UK</SelectItem>
                    <SelectItem value="usa">USA</SelectItem>
                    <SelectItem value="germany">Germany</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Marital Status</Label>
                <Select value={form.marital_status} onValueChange={(v) => setForm({ ...form, marital_status: v })}>
                  <SelectTrigger data-testid="elig-marital"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="single">Single</SelectItem>
                    <SelectItem value="married">Married</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Available Funds (₹)</Label>
                <Input type="number" value={form.funds_available_inr} onChange={(e) => setForm({ ...form, funds_available_inr: e.target.value })} placeholder="e.g. 1500000" data-testid="elig-funds" />
              </div>
              <div className="flex items-end gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.has_job_offer} onChange={(e) => setForm({ ...form, has_job_offer: e.target.checked })} className="rounded" data-testid="elig-job-offer" />
                  <span className="text-sm">Job Offer Abroad</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.has_relatives_abroad} onChange={(e) => setForm({ ...form, has_relatives_abroad: e.target.checked })} className="rounded" />
                  <span className="text-sm">Relatives Abroad</span>
                </label>
              </div>
            </div>
            <Button onClick={handleCheck} disabled={loading} className="mt-6 bg-[#2a777a] hover:bg-[#236466] text-white w-full md:w-auto" data-testid="check-eligibility-btn">
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Brain className="h-4 w-4 mr-2" />}
              Check My Eligibility
            </Button>
          </Card>
        </>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-slate-800">Your Eligibility Results</h3>
            <Button variant="outline" onClick={() => setResults(null)} data-testid="check-again-btn">Check Again</Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {results.map((r, idx) => (
              <Card key={idx} className={`p-5 border-2 ${statusColor(r.status)}`} data-testid={`result-card-${idx}`}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {statusIcon(r.status)}
                    <div>
                      <h4 className="font-semibold text-slate-800">{r.program}</h4>
                      <p className="text-xs text-slate-500">{r.country}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-slate-800">{r.score}%</p>
                    <Badge className={statusColor(r.status)}>{r.status.replace('_', ' ')}</Badge>
                  </div>
                </div>
                {/* Score Bar */}
                <div className="w-full bg-slate-200 rounded-full h-3 mb-3">
                  <div className={`h-3 rounded-full transition-all duration-700 ${scoreBarColor(r.score)}`} style={{ width: `${r.score}%` }} />
                </div>
                {/* Tips */}
                {r.tips && r.tips.length > 0 && (
                  <div className="space-y-1 mt-2">
                    {r.tips.map((tip, ti) => (
                      <p key={ti} className="text-xs text-slate-600 flex items-start gap-1">
                        <AlertTriangle className="h-3 w-3 mt-0.5 text-amber-500 flex-shrink-0" />{tip}
                      </p>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default EligibilityChecker;
