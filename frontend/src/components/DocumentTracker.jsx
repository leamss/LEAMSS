import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, FileCheck, CheckCircle, Clock, AlertCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DocumentTracker = ({ token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${API}/client-tools/document-tracker`, { headers: { Authorization: `Bearer ${token}` } });
        setData(res.data);
      } catch (e) { /* no data */ }
      setLoading(false);
    };
    load();
  }, []);

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  if (!data || (data.cases || []).length === 0) {
    return (
      <Card className="p-12 text-center" data-testid="doc-tracker">
        <FileCheck className="h-12 w-12 text-slate-300 mx-auto mb-4" />
        <p className="text-lg font-semibold text-slate-600">No Active Cases</p>
        <p className="text-sm text-slate-400 mt-1">Document tracker will appear when you have an active case</p>
      </Card>
    );
  }

  const overallColor = data.overall_completion >= 80 ? 'text-emerald-600' : data.overall_completion >= 50 ? 'text-blue-600' : 'text-amber-600';
  const overallBg = data.overall_completion >= 80 ? 'bg-emerald-500' : data.overall_completion >= 50 ? 'bg-blue-500' : 'bg-amber-500';

  return (
    <div className="space-y-6" data-testid="doc-tracker">
      {/* Overall Progress */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-[#2a777a]" />Document Completion
          </h3>
          <p className={`text-3xl font-bold ${overallColor}`}>{data.overall_completion}%</p>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-3">
          <div className={`h-3 rounded-full transition-all duration-700 ${overallBg}`} style={{ width: `${data.overall_completion}%` }} />
        </div>
      </Card>

      {data.cases.map((c, cIdx) => (
        <Card key={cIdx} className="p-6" data-testid={`doc-case-${cIdx}`}>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-semibold text-slate-800">{c.case_id}</h4>
              <p className="text-sm text-slate-500">{c.product_name}</p>
            </div>
            <Badge className={c.completion >= 80 ? 'bg-emerald-100 text-emerald-700' : c.completion >= 50 ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}>
              {c.completion}% complete
            </Badge>
          </div>

          <div className="space-y-3">
            {(c.steps || []).map((step, sIdx) => (
              <div key={sIdx} className="border rounded-lg p-3" data-testid={`doc-step-${cIdx}-${sIdx}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-[#2a777a] text-white text-xs flex items-center justify-center">{step.step_order}</span>
                    <h5 className="font-medium text-slate-800 text-sm">{step.step_name}</h5>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">{step.uploaded}/{step.required}</span>
                    {step.completion >= 100 ? <CheckCircle className="h-4 w-4 text-emerald-500" /> : step.uploaded > 0 ? <Clock className="h-4 w-4 text-blue-500" /> : <AlertCircle className="h-4 w-4 text-slate-300" />}
                  </div>
                </div>
                {step.required > 0 && (
                  <div className="w-full bg-slate-100 rounded-full h-1.5 mb-2">
                    <div className={`h-1.5 rounded-full ${step.completion >= 100 ? 'bg-emerald-500' : step.completion > 0 ? 'bg-blue-500' : 'bg-slate-200'}`} style={{ width: `${step.completion}%` }} />
                  </div>
                )}
                {(step.documents || []).length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {step.documents.map((doc, dIdx) => (
                      <span key={dIdx} className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                        doc.uploaded ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : doc.is_mandatory ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-slate-50 text-slate-500 border border-slate-200'
                      }`}>
                        {doc.uploaded ? <CheckCircle className="h-3 w-3" /> : doc.is_mandatory ? <AlertCircle className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
                        {doc.doc_name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
};

export default DocumentTracker;
