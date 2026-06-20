import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  FileCheck, Plus, Loader2, CheckCircle, Clock, AlertCircle,
  FileText, Trash2, Upload, ChevronDown, ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CMDocManager = ({ token, caseId, caseName }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedStep, setExpandedStep] = useState(null);
  const [requestDialog, setRequestDialog] = useState({
    open: false, type: 'step', step_name: '',
    doc_name: '', is_mandatory: true, tag: 'mandatory', notes: ''
  });
  const [saving, setSaving] = useState(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadData = async () => {
    if (!caseId) { setLoading(false); return; }
    try {
      const res = await axios.get(`${API}/step-documents/case/${caseId}`, { headers });
      setData(res.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { loadData(); }, [caseId]);

  const handleRequest = async () => {
    if (!requestDialog.doc_name.trim()) { toast.error('Document name required'); return; }
    setSaving(true);
    try {
      if (requestDialog.type === 'step') {
        await axios.post(`${API}/step-documents/request-step-doc`, {
          case_id: caseId,
          step_name: requestDialog.step_name,
          doc_name: requestDialog.doc_name.trim(),
          is_mandatory: requestDialog.is_mandatory,
          tag: requestDialog.tag,
          notes: requestDialog.notes,
        }, { headers });
      } else {
        await axios.post(`${API}/step-documents/request-additional`, {
          case_id: caseId,
          doc_name: requestDialog.doc_name.trim(),
          is_mandatory: requestDialog.is_mandatory,
          tag: requestDialog.tag,
          notes: requestDialog.notes,
        }, { headers });
      }
      toast.success('Document requested!');
      setRequestDialog({ ...requestDialog, open: false });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
    setSaving(false);
  };

  const handleRemove = async (stepName, docName) => {
    if (!window.confirm(`Remove "${docName}" from step "${stepName}"?`)) return;
    try {
      await axios.post(`${API}/step-documents/remove-step-doc`, {
        case_id: caseId, step_name: stepName, doc_name: docName,
      }, { headers });
      toast.success('Removed');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Cannot remove');
    }
  };

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  if (!data || !caseId) {
    return (
      <Card className="p-12 text-center" data-testid="cm-doc-manager">
        <FileCheck className="h-12 w-12 text-slate-300 mx-auto mb-4" />
        <p className="text-slate-600">Select a case to manage documents</p>
      </Card>
    );
  }

  const s = data.summary || {};

  return (
    <div className="space-y-5" data-testid="cm-doc-manager">
      {/* Header + Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-[#2a777a]" />Documents — {caseName || 'Case'}
          </h3>
          <p className="text-sm text-slate-500">{s.total_uploaded}/{s.total_required} uploaded ({s.completion_pct}%)</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setRequestDialog({ open: true, type: 'additional', step_name: '', doc_name: '', is_mandatory: true, tag: 'mandatory', notes: '' })}
            data-testid="request-additional-btn">
            <Plus className="h-4 w-4 mr-1" />Additional Doc
          </Button>
        </div>
      </div>

      {/* Steps */}
      {(data.steps || []).map((step, sIdx) => {
        const isExpanded = expandedStep === step.step_name;
        return (
          <Card key={step.step_name} className="overflow-hidden" data-testid={`cm-step-${sIdx}`}>
            <div className="p-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-3" onClick={() => setExpandedStep(isExpanded ? null : step.step_name)}>
              {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
              <span className="w-6 h-6 rounded-full bg-[#2a777a] text-white text-xs flex items-center justify-center font-bold">{step.step_order}</span>
              <div className="flex-1">
                <span className="font-medium text-sm text-slate-800 dark:text-white">{step.step_name}</span>
                <Badge variant="outline" className="text-[10px] ml-2">{step.uploaded_count}/{step.required_count}</Badge>
              </div>
              <Button size="sm" variant="ghost" className="h-7 text-xs text-[#2a777a]" onClick={(e) => {
                e.stopPropagation();
                setRequestDialog({ open: true, type: 'step', step_name: step.step_name, doc_name: '', is_mandatory: true, tag: 'mandatory', notes: '' });
              }} data-testid={`add-doc-step-${sIdx}`}><Plus className="h-3 w-3 mr-1" />Add Doc</Button>
            </div>

            {isExpanded && (
              <div className="border-t p-3 space-y-2 bg-slate-50/50 dark:bg-slate-800/30">
                {step.documents.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-2">No documents required</p>
                ) : step.documents.map((doc, dIdx) => (
                  <div key={dIdx} className="flex items-center justify-between p-2 rounded border bg-white dark:bg-slate-800 text-sm">
                    <div className="flex items-center gap-2 flex-1">
                      {doc.uploaded ? <CheckCircle className="h-4 w-4 text-emerald-500" /> : <AlertCircle className="h-4 w-4 text-slate-300" />}
                      <span className="text-slate-800 dark:text-white">{doc.doc_name}</span>
                      <Badge className={`text-[9px] ${doc.is_mandatory ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>{doc.tag || 'mandatory'}</Badge>
                      {doc.source === 'cm_request' && <Badge className="text-[9px] bg-leamss-orange-100 text-leamss-orange-700">You added</Badge>}
                    </div>
                    <div className="flex items-center gap-1">
                      <Badge className={`text-[9px] ${doc.uploaded ? (doc.status === 'approved' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700') : 'bg-slate-100 text-slate-500'}`}>
                        {doc.uploaded ? doc.status : 'Pending'}
                      </Badge>
                      {doc.source === 'cm_request' && (
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-red-400 hover:text-red-600" onClick={() => handleRemove(step.step_name, doc.doc_name)}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        );
      })}

      {/* Additional Requests */}
      {(data.additional_requests || []).length > 0 && (
        <Card className="p-4" data-testid="cm-additional-section">
          <h4 className="font-semibold text-sm text-leamss-orange-700 mb-2 flex items-center gap-1"><FileText className="h-4 w-4" />Additional Requests</h4>
          {data.additional_requests.map((r, rIdx) => (
            <div key={r.id} className="flex items-center justify-between p-2 rounded border bg-white dark:bg-slate-800 text-sm mb-1">
              <div className="flex items-center gap-2">
                {r.uploaded_doc ? <CheckCircle className="h-4 w-4 text-emerald-500" /> : <Clock className="h-4 w-4 text-leamss-orange-400" />}
                <span>{r.doc_name}</span>
                <Badge className="text-[9px] bg-leamss-orange-100 text-leamss-orange-700">Additional</Badge>
              </div>
              <Badge className={r.uploaded_doc ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}>{r.uploaded_doc ? 'Uploaded' : r.status}</Badge>
            </div>
          ))}
        </Card>
      )}

      {/* Request Dialog */}
      <Dialog open={requestDialog.open} onOpenChange={(o) => setRequestDialog({ ...requestDialog, open: o })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{requestDialog.type === 'step' ? `Request Document — ${requestDialog.step_name}` : 'Request Additional Document'}</DialogTitle>
            <DialogDescription>{requestDialog.type === 'step' ? 'This will be added to the step for this client only' : 'This will appear in a separate section for the client'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-3">
            <div><Label>Document Name *</Label><Input value={requestDialog.doc_name} onChange={(e) => setRequestDialog({ ...requestDialog, doc_name: e.target.value })} placeholder="e.g. Bank Statement, Medical Report" data-testid="doc-name-input" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div><Label>Tag</Label>
                <Select value={requestDialog.tag} onValueChange={(v) => setRequestDialog({ ...requestDialog, tag: v, is_mandatory: v === 'mandatory' })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="mandatory">Mandatory</SelectItem>
                    <SelectItem value="optional">Optional</SelectItem>
                    <SelectItem value="conditional">Conditional</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div><Label>Notes for Client</Label><Textarea value={requestDialog.notes} onChange={(e) => setRequestDialog({ ...requestDialog, notes: e.target.value })} placeholder="Instructions..." rows={2} /></div>
            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setRequestDialog({ ...requestDialog, open: false })}>Cancel</Button>
              <Button onClick={handleRequest} disabled={saving} className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="confirm-doc-request">
                {saving && <Loader2 className="h-4 w-4 animate-spin mr-1" />}Request Document
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CMDocManager;
