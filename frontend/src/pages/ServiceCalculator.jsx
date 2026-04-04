import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ArrowLeft, Calculator, CheckCircle, Star, ArrowRight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const ServiceCalculator = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    age: 30, education: 'bachelors', work_experience_years: 3,
    language_score: 6.5, country_of_interest: '', has_spouse: false, funds_available_usd: 10000
  });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAssess = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API}/marketing-tools/calculator/assess`, form);
      setResults(res.data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const eligibilityColors = {
    high: 'bg-emerald-100 text-emerald-700 border-emerald-300',
    medium: 'bg-amber-100 text-amber-700 border-amber-300',
    low: 'bg-orange-100 text-orange-700 border-orange-300',
    unlikely: 'bg-red-100 text-red-700 border-red-300'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f9f9] to-[#e8f4f4]">
      <header className="bg-white border-b sticky top-0 z-20 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}><ArrowLeft className="h-5 w-5" /></Button>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Immigration Eligibility Calculator</h1>
            <p className="text-sm text-slate-500">Check which programs you qualify for</p>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Input Form */}
          <div className="lg:col-span-2">
            <Card className="p-6 sticky top-24">
              <div className="flex items-center gap-2 mb-6">
                <Calculator className="h-5 w-5 text-[#2a777a]" />
                <h2 className="text-lg font-semibold text-slate-800">Your Profile</h2>
              </div>
              <div className="space-y-4">
                <div><Label>Age</Label><Input type="number" min="18" max="65" value={form.age} onChange={(e) => setForm({ ...form, age: parseInt(e.target.value) || 18 })} /></div>
                <div><Label>Education Level</Label>
                  <Select value={form.education} onValueChange={(v) => setForm({ ...form, education: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="phd">PhD / Doctorate</SelectItem>
                      <SelectItem value="masters">Master's Degree</SelectItem>
                      <SelectItem value="bachelors">Bachelor's Degree</SelectItem>
                      <SelectItem value="diploma">Diploma / Associate</SelectItem>
                      <SelectItem value="high_school">High School</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div><Label>Work Experience (Years)</Label><Input type="number" min="0" max="30" value={form.work_experience_years} onChange={(e) => setForm({ ...form, work_experience_years: parseInt(e.target.value) || 0 })} /></div>
                <div><Label>Language Score (IELTS 0-9)</Label><Input type="number" step="0.5" min="0" max="9" value={form.language_score} onChange={(e) => setForm({ ...form, language_score: parseFloat(e.target.value) || 0 })} /></div>
                <div><Label>Country of Interest</Label><Input placeholder="e.g., Canada, Australia" value={form.country_of_interest} onChange={(e) => setForm({ ...form, country_of_interest: e.target.value })} /></div>
                <Button onClick={handleAssess} disabled={loading} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white h-12 text-base" data-testid="assess-btn">
                  {loading ? 'Analyzing...' : 'Check Eligibility'}
                </Button>
              </div>
            </Card>
          </div>

          {/* Results */}
          <div className="lg:col-span-3">
            {!results ? (
              <div className="flex flex-col items-center justify-center h-96 text-center">
                <Calculator className="h-16 w-16 text-slate-300 mb-4" />
                <h3 className="text-xl font-semibold text-slate-600">Enter your details</h3>
                <p className="text-slate-400 mt-2">Fill in the form and click "Check Eligibility" to see which immigration programs match your profile.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-slate-800">Your Recommendations ({results.recommendations?.length || 0} programs)</h3>
                {results.recommendations?.map((rec, idx) => (
                  <Card key={idx} className={`p-5 hover:shadow-md transition-shadow ${idx === 0 ? 'border-[#2a777a] border-2' : ''}`} data-testid={`recommendation-${idx}`}>
                    {idx === 0 && <Badge className="bg-[#2a777a] text-white mb-2">Best Match</Badge>}
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="text-lg font-bold text-slate-800">{rec.product_name}</h4>
                        <p className="text-sm text-slate-500 mt-1">{rec.description}</p>
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-3xl font-bold text-[#2a777a]">{rec.score}%</div>
                        <Badge className={`${eligibilityColors[rec.eligibility]} mt-1`}>{rec.eligibility_label}</Badge>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center gap-4 text-sm text-slate-600">
                      <span>Est. Fee: {rec.base_fee?.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}</span>
                      <span>Timeline: {rec.estimated_timeline}</span>
                    </div>
                    <div className="mt-3 space-y-1">
                      {rec.reasons?.map((reason, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0" />
                          <span className="text-slate-600">{reason}</span>
                        </div>
                      ))}
                    </div>
                    <Button className="mt-4 bg-[#2a777a] hover:bg-[#236466] text-white" onClick={() => navigate('/inquiry?service=' + encodeURIComponent(rec.product_name))} data-testid={`enquire-${idx}`}>
                      Enquire Now <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServiceCalculator;
