import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Sparkles,
  Globe,
  Loader2,
  CheckCircle,
  ExternalLink,
  ShieldCheck,
  FileText,
  DollarSign,
  HelpCircle,
  Clock,
  ListChecks,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ProductAiResearchModal({ isOpen, onClose, onApply, initialCountry = '', initialVisa = '' }) {
  const [country, setCountry] = useState(initialCountry);
  const [visaName, setVisaName] = useState(initialVisa);
  const [subclass, setSubclass] = useState('');
  const [category, setCategory] = useState('skilled_migration');
  const [governmentUrl, setGovernmentUrl] = useState('');
  const [migrateUrl, setMigrateUrl] = useState('https://leamss.com/migrate');
  const [context, setContext] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [researchedData, setResearchedData] = useState(null);
  const [previewTab, setPreviewTab] = useState('summary');

  useEffect(() => {
    if (isOpen) {
      if (initialCountry) setCountry(initialCountry);
      if (initialVisa) setVisaName(initialVisa);
    }
  }, [isOpen, initialCountry, initialVisa]);

  const handleResearch = async () => {
    if (!country.trim() || !visaName.trim()) {
      toast.error('Country and Visa Name are required.');
      return;
    }

    setLoading(true);
    setResearchedData(null);
    try {
      const token = localStorage.getItem('token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.post(
        `${API}/product-master/ai-research`,
        {
          country: country.trim(),
          visa_name: visaName.trim(),
          visa_subclass: subclass.trim() || undefined,
          category: category || 'skilled_migration',
          government_url: governmentUrl.trim() || undefined,
          migrate_page_url: migrateUrl.trim() || undefined,
          additional_context: context.trim() || undefined,
        },
        { headers }
      );

      setResearchedData(res.data);
      toast.success('AI research completed successfully from official sources!');
    } catch (err) {
      console.error('AI Research Error:', err);
      const detail = err.response?.data?.detail || err.message || 'AI Research failed';
      toast.error(`Research error: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (!researchedData) return;
    onApply(researchedData);
    toast.success('AI-researched details applied to Product Master form!');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-bold text-slate-800">
            <Sparkles className="h-5 w-5 text-amber-500" />
            AI Product Master Generator & Official Web Research
          </DialogTitle>
          <p className="text-xs text-slate-500">
            Researches official government immigration websites and LEAMSS Migrate data via Perplexity AI to automatically structure eligibility, official costs, sales playbooks, and checklists.
          </p>
        </DialogHeader>

        {!researchedData ? (
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold">Destination Country *</Label>
                <Input
                  placeholder="e.g. Australia, Canada, United Kingdom"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs font-semibold">Visa Name / Title *</Label>
                <Input
                  placeholder="e.g. Skilled Independent Visa, Express Entry FSW"
                  value={visaName}
                  onChange={(e) => setVisaName(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs font-semibold">Visa Subclass / Stream Code</Label>
                <Input
                  placeholder="e.g. 189, 190, 482, FSW"
                  value={subclass}
                  onChange={(e) => setSubclass(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs font-semibold">Category</Label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors"
                >
                  <option value="skilled_migration">Skilled Migration / PR</option>
                  <option value="work">Work Visa</option>
                  <option value="student">Student / Education</option>
                  <option value="visitor">Visitor / Tourist</option>
                  <option value="business">Business / Investment</option>
                  <option value="family">Family / Spouse</option>
                </select>
              </div>
            </div>

            <div className="space-y-3 pt-1">
              <div>
                <Label className="text-xs font-semibold flex items-center gap-1">
                  <Globe className="h-3.5 w-3.5 text-blue-500" />
                  Official Government Source URL (optional)
                </Label>
                <Input
                  placeholder="e.g. https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189"
                  value={governmentUrl}
                  onChange={(e) => setGovernmentUrl(e.target.value)}
                  className="mt-1 text-xs"
                />
                <span className="text-[10px] text-slate-400">
                  AI directly consults this link or official portal for verified fees, conditions, and processing times.
                </span>
              </div>

              <div>
                <Label className="text-xs font-semibold flex items-center gap-1">
                  <ExternalLink className="h-3.5 w-3.5 text-emerald-500" />
                  LEAMSS Migrate Page URL (optional)
                </Label>
                <Input
                  placeholder="e.g. https://leamss.com/migrate/australia/subclass-189"
                  value={migrateUrl}
                  onChange={(e) => setMigrateUrl(e.target.value)}
                  className="mt-1 text-xs"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold">Additional Context / Special Focus</Label>
                <Textarea
                  placeholder="e.g. Focus on points test threshold of 65, recent changes to state allocation, fast-track occupation lists."
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  rows={2}
                  className="mt-1 text-xs"
                />
              </div>
            </div>

            {loading && (
              <Card className="p-4 bg-amber-50 border-amber-200 flex items-center gap-3">
                <Loader2 className="h-5 w-5 text-amber-600 animate-spin" />
                <div className="text-xs text-amber-800">
                  <p className="font-bold">Researching Official Government Portals...</p>
                  <p className="text-[11px] text-amber-700 mt-0.5">
                    Consulting official immigration guidelines, government fee schedules, points test matrices, and processing timelines. This takes 10-20 seconds.
                  </p>
                </div>
              </Card>
            )}
          </div>
        ) : (
          /* Preview Mode */
          <div className="space-y-4 py-2">
            <div className="flex items-center justify-between p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-emerald-600" />
                <div>
                  <h4 className="font-bold text-sm text-emerald-900">{researchedData.name}</h4>
                  <p className="text-[11px] text-emerald-700">
                    Researched with {researchedData._ai_model || 'Perplexity AI'} • {researchedData.country} ({researchedData.category})
                  </p>
                </div>
              </div>
              <Button size="sm" variant="outline" onClick={() => setResearchedData(null)} className="h-8 text-xs">
                Re-run Search
              </Button>
            </div>

            <Tabs value={previewTab} onValueChange={setPreviewTab}>
              <TabsList className="grid grid-cols-5 text-xs">
                <TabsTrigger value="summary">Summary & URLs</TabsTrigger>
                <TabsTrigger value="eligibility">Eligibility</TabsTrigger>
                <TabsTrigger value="costs">Costs & Time</TabsTrigger>
                <TabsTrigger value="playbook">Playbook & FAQs</TabsTrigger>
                <TabsTrigger value="checklist">Checklist</TabsTrigger>
              </TabsList>

              <TabsContent value="summary" className="space-y-3 pt-2 text-xs">
                <div>
                  <Label className="font-bold text-slate-700">Summary:</Label>
                  <p className="p-2 bg-slate-50 border rounded mt-1 text-slate-800 leading-relaxed">
                    {researchedData.summary}
                  </p>
                </div>
                <div>
                  <Label className="font-bold text-slate-700">Official URLs & Allowlist Domains:</Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {(researchedData.official_domains || []).map((d, i) => (
                      <Badge key={i} variant="secondary" className="text-[11px]">
                        {d}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <Label className="font-bold text-slate-700">Visa Conditions:</Label>
                  <ul className="list-disc pl-4 mt-1 space-y-1 text-slate-700">
                    {(researchedData.visa_conditions || []).map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              </TabsContent>

              <TabsContent value="eligibility" className="space-y-3 pt-2 text-xs">
                <div>
                  <Label className="font-bold text-slate-700">Mandatory Criteria:</Label>
                  <div className="space-y-1 mt-1">
                    {(researchedData.eligibility_criteria?.mandatory || []).map((m, i) => (
                      <div key={i} className="p-2 border rounded bg-slate-50">
                        <span className="font-bold text-slate-800">{m.criterion}</span>
                        <p className="text-slate-600 mt-0.5">{m.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
                {researchedData.eligibility_criteria?.points_based?.is_points_tested && (
                  <div>
                    <Label className="font-bold text-slate-700">Points Testing Factors (Minimum: {researchedData.eligibility_criteria?.points_based?.minimum_points} pts):</Label>
                    <div className="grid grid-cols-2 gap-2 mt-1">
                      {(researchedData.eligibility_criteria?.points_based?.scoring_factors || []).map((f, i) => (
                        <div key={i} className="p-2 border rounded bg-blue-50/50">
                          <div className="flex justify-between font-bold text-slate-800">
                            <span>{f.factor}</span>
                            <span className="text-blue-700">Up to {f.max_points} pts</span>
                          </div>
                          <p className="text-[10px] text-slate-600 mt-0.5">{f.details}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="costs" className="space-y-3 pt-2 text-xs">
                <div>
                  <Label className="font-bold text-slate-700">
                    Official Government Fee Schedule ({researchedData.government_costs?.currency}):
                  </Label>
                  <div className="border rounded mt-1 overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-100 font-semibold text-slate-700 border-b">
                        <tr>
                          <th className="p-2">Applicant Type</th>
                          <th className="p-2">Amount</th>
                          <th className="p-2">Approx INR</th>
                          <th className="p-2">Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(researchedData.government_costs?.line_items || []).map((it, i) => (
                          <tr key={i} className="border-b last:border-b-0">
                            <td className="p-2 font-medium">{it.applicant_type}</td>
                            <td className="p-2 font-bold text-slate-800">{it.amount} {it.currency}</td>
                            <td className="p-2 text-slate-600">₹{(it.inr_approx || 0).toLocaleString('en-IN')}</td>
                            <td className="p-2 text-slate-500">{it.notes || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div>
                  <Label className="font-bold text-slate-700">Processing Timeline:</Label>
                  <p className="font-semibold text-slate-800 mt-1">
                    Standard: {researchedData.processing_timeline?.standard_duration}
                  </p>
                  <div className="space-y-1 mt-1">
                    {(researchedData.processing_timeline?.stages || []).map((st, i) => (
                      <div key={i} className="flex justify-between p-1.5 bg-slate-50 border rounded text-[11px]">
                        <span className="font-medium text-slate-700">{st.stage}</span>
                        <span className="text-slate-500">{st.duration}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="playbook" className="space-y-3 pt-2 text-xs">
                <div>
                  <Label className="font-bold text-slate-700">Key Pitch Points:</Label>
                  <ul className="list-disc pl-4 mt-1 space-y-1 text-slate-700">
                    {(researchedData.sales_playbook?.pitch_points || []).map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <Label className="font-bold text-slate-700">Objections & Rebuttals:</Label>
                  <div className="space-y-1.5 mt-1">
                    {(researchedData.objections_rebuttals || []).map((ob, i) => (
                      <div key={i} className="p-2 border rounded bg-slate-50">
                        <span className="font-bold text-rose-800">Objection: "{ob.objection}"</span>
                        <p className="text-emerald-800 mt-0.5 font-medium">Rebuttal: {ob.rebuttal}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <Label className="font-bold text-slate-700">Frequently Asked Questions:</Label>
                  <div className="space-y-1.5 mt-1">
                    {(researchedData.faqs || []).map((f, i) => (
                      <div key={i} className="p-2 border rounded bg-slate-50">
                        <span className="font-bold text-slate-800">Q: {f.question}</span>
                        <p className="text-slate-600 mt-0.5">A: {f.answer}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="checklist" className="space-y-3 pt-2 text-xs">
                <Label className="font-bold text-slate-700">Document Checklist Template:</Label>
                <div className="space-y-1 mt-1">
                  {(researchedData.document_checklist_template || []).map((doc, i) => (
                    <div key={i} className="p-2 border rounded bg-slate-50 flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <Badge variant="outline" className="text-[10px]">{doc.category}</Badge>
                          <span className="font-bold text-slate-800">{doc.document_name}</span>
                        </div>
                        <p className="text-slate-500 text-[11px] mt-0.5">{doc.description}</p>
                      </div>
                      <Badge className="bg-slate-200 text-slate-700 text-[9px] shrink-0">
                        {doc.required_for}
                      </Badge>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        )}

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          {!researchedData ? (
            <Button
              onClick={handleResearch}
              disabled={loading || !country.trim() || !visaName.trim()}
              className="bg-amber-600 hover:bg-amber-700 text-white gap-1.5"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {loading ? 'Researching Portals...' : 'Research & Generate with AI'}
            </Button>
          ) : (
            <Button
              onClick={handleApply}
              className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
            >
              <CheckCircle className="h-4 w-4" />
              Apply to Product Form
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
