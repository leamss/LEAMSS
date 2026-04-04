import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ArrowLeft, Send, CheckCircle, Globe, Phone, Mail } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const LeadCapture = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefilledService = searchParams.get('service') || '';
  
  const [form, setForm] = useState({
    name: '', email: '', phone: '', service_interested: prefilledService,
    country_of_interest: '', message: '', source: 'website'
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.email) { toast.error('Name and email are required'); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/leads/capture`, form);
      setSubmitted(true);
    } catch (e) { toast.error('Something went wrong. Please try again.'); }
    setLoading(false);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#f0f9f9] to-[#e8f4f4] flex items-center justify-center px-4">
        <Card className="max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="h-8 w-8 text-emerald-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Thank You!</h2>
          <p className="text-slate-600 mb-6">We've received your inquiry. Our team will contact you within 24 hours.</p>
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={() => navigate('/calculator')}>Try Eligibility Calculator</Button>
            <Button className="bg-[#2a777a] hover:bg-[#236466] text-white" onClick={() => navigate('/')}>Back to Home</Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f0f9f9] to-[#e8f4f4]">
      <header className="bg-white border-b sticky top-0 z-20 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate(-1)}><ArrowLeft className="h-5 w-5" /></Button>
            <div>
              <h1 className="text-xl font-bold text-slate-800">Get Started with LEAMSS</h1>
              <p className="text-sm text-slate-500">Free consultation for your immigration journey</p>
            </div>
          </div>
          <Button variant="outline" onClick={() => navigate('/calculator')}>Eligibility Calculator</Button>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Info Panel */}
          <div className="lg:col-span-2 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-slate-800 mb-2">Start Your Immigration Journey</h2>
              <p className="text-slate-600">Fill out the form and our experts will guide you through the best immigration pathways.</p>
            </div>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-[#2a777a]/10 rounded-lg mt-0.5"><Globe className="h-5 w-5 text-[#2a777a]" /></div>
                <div><p className="font-medium text-slate-800">Expert Guidance</p><p className="text-sm text-slate-500">15+ years of immigration experience across 20+ countries</p></div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-2 bg-[#2a777a]/10 rounded-lg mt-0.5"><CheckCircle className="h-5 w-5 text-[#2a777a]" /></div>
                <div><p className="font-medium text-slate-800">High Success Rate</p><p className="text-sm text-slate-500">95%+ application approval rate with our guidance</p></div>
              </div>
              <div className="flex items-start gap-3">
                <div className="p-2 bg-[#2a777a]/10 rounded-lg mt-0.5"><Phone className="h-5 w-5 text-[#2a777a]" /></div>
                <div><p className="font-medium text-slate-800">24-Hour Response</p><p className="text-sm text-slate-500">We'll contact you within 24 hours of your inquiry</p></div>
              </div>
            </div>
          </div>

          {/* Form */}
          <div className="lg:col-span-3">
            <Card className="p-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>Full Name *</Label><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Your name" data-testid="lead-name" /></div>
                  <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+91 9876543210" data-testid="lead-phone" /></div>
                </div>
                <div><Label>Email *</Label><Input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@email.com" data-testid="lead-email" /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>Service Interested In</Label>
                    <Select value={form.service_interested} onValueChange={(v) => setForm({ ...form, service_interested: v })}>
                      <SelectTrigger><SelectValue placeholder="Select a service" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Canada PR">Canada PR</SelectItem>
                        <SelectItem value="Student Visa">Student Visa</SelectItem>
                        <SelectItem value="Work Permit">Work Permit</SelectItem>
                        <SelectItem value="Australia PR">Australia PR</SelectItem>
                        <SelectItem value="UK Visa">UK Visa</SelectItem>
                        <SelectItem value="Other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div><Label>Country of Interest</Label><Input value={form.country_of_interest} onChange={(e) => setForm({ ...form, country_of_interest: e.target.value })} placeholder="e.g., Canada" /></div>
                </div>
                <div><Label>Tell us about your requirements</Label><Textarea rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Describe your immigration goals, timeline, and any specific questions..." /></div>
                <Button type="submit" disabled={loading} className="w-full bg-[#2a777a] hover:bg-[#236466] text-white h-12 text-base" data-testid="submit-inquiry-btn">
                  {loading ? 'Submitting...' : 'Submit Inquiry'} <Send className="ml-2 h-4 w-4" />
                </Button>
                <p className="text-xs text-slate-400 text-center">By submitting, you agree to be contacted by LEAMSS regarding your inquiry.</p>
              </form>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LeadCapture;
