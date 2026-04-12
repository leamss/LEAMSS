import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  Zap, CheckCircle, Loader2, MessageSquare, FileText,
  Bell, ArrowRight, Square, CheckSquare
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const BatchCaseOps = ({ token }) => {
  const [cases, setCases] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [actionDialog, setActionDialog] = useState({ open: false, action: '', value: '', notes: '' });

  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get(`${API}/cm-tools/my-cases-summary`, { headers });
        setCases(res.data || []);
      } catch (e) {
        toast.error('Failed to load cases');
      }
      setLoading(false);
    };
    load();
  }, []);

  const toggleCase = (id) => {
    const s = new Set(selected);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setSelected(s);
  };

  const toggleAll = () => {
    if (selected.size === cases.length) setSelected(new Set());
    else setSelected(new Set(cases.map(c => c.id)));
  };

  const handleBatchAction = async () => {
    if (selected.size === 0) {
      toast.error('Select at least one case');
      return;
    }
    if (actionDialog.action === 'change_status' && !actionDialog.value) {
      toast.error('Select a status');
      return;
    }
    if ((actionDialog.action === 'add_note' || actionDialog.action === 'send_notification' || actionDialog.action === 'request_documents') && !actionDialog.notes.trim()) {
      toast.error('Message/note cannot be empty');
      return;
    }

    setProcessing(true);
    try {
      const res = await axios.post(`${API}/cm-tools/batch-operations`, {
        case_ids: [...selected],
        action: actionDialog.action,
        value: actionDialog.value,
        notes: actionDialog.notes.trim(),
      }, { headers });
      toast.success(res.data.message);
      setActionDialog({ open: false, action: '', value: '', notes: '' });
      setSelected(new Set());
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Batch operation failed');
    }
    setProcessing(false);
  };

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-[#2a777a]" /></div>;

  return (
    <div className="space-y-4" data-testid="batch-case-ops">
      {/* Actions Bar */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Zap className="h-5 w-5 text-[#2a777a]" />
            <span className="font-medium text-slate-800">{selected.size} of {cases.length} selected</span>
            <Button variant="outline" size="sm" onClick={toggleAll} data-testid="select-all-btn">
              {selected.size === cases.length ? 'Deselect All' : 'Select All'}
            </Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={selected.size === 0}
              onClick={() => setActionDialog({ open: true, action: 'add_note', value: '', notes: '' })}
              data-testid="batch-add-note"
            ><FileText className="h-4 w-4 mr-1" />Add Note</Button>
            <Button variant="outline" size="sm" disabled={selected.size === 0}
              onClick={() => setActionDialog({ open: true, action: 'send_notification', value: '', notes: '' })}
              data-testid="batch-notify"
            ><Bell className="h-4 w-4 mr-1" />Notify Clients</Button>
            <Button variant="outline" size="sm" disabled={selected.size === 0}
              onClick={() => setActionDialog({ open: true, action: 'request_documents', value: '', notes: '' })}
              data-testid="batch-doc-request"
            ><MessageSquare className="h-4 w-4 mr-1" />Request Docs</Button>
            <Button size="sm" disabled={selected.size === 0}
              onClick={() => setActionDialog({ open: true, action: 'change_status', value: '', notes: '' })}
              className="bg-[#2a777a] hover:bg-[#236466] text-white"
              data-testid="batch-status"
            ><ArrowRight className="h-4 w-4 mr-1" />Change Status</Button>
          </div>
        </div>
      </Card>

      {/* Cases List */}
      {cases.length === 0 ? (
        <Card className="p-12 text-center">
          <CheckCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <p className="text-slate-600">No active cases</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {cases.map((c, idx) => (
            <Card key={c.id}
              className={`p-4 cursor-pointer transition-all ${selected.has(c.id) ? 'border-[#2a777a] bg-[#2a777a]/5 shadow-sm' : 'hover:bg-slate-50'}`}
              onClick={() => toggleCase(c.id)}
              data-testid={`batch-case-${idx}`}
            >
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  {selected.has(c.id) ? <CheckSquare className="h-5 w-5 text-[#2a777a]" /> : <Square className="h-5 w-5 text-slate-300" />}
                </div>
                <div className="flex-1 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">{c.case_id}</span>
                      <Badge variant="outline" className="text-xs">{c.status}</Badge>
                    </div>
                    <p className="text-sm text-slate-600">{c.client_name} - {c.product_name}</p>
                  </div>
                  <p className="text-xs text-slate-500">Step: {c.current_step}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Action Dialog */}
      <Dialog open={actionDialog.open} onOpenChange={(o) => setActionDialog({ ...actionDialog, open: o })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionDialog.action === 'add_note' ? 'Add Note to Cases' :
               actionDialog.action === 'send_notification' ? 'Notify Clients' :
               actionDialog.action === 'request_documents' ? 'Request Documents' :
               actionDialog.action === 'change_status' ? 'Change Case Status' : 'Batch Action'}
            </DialogTitle>
            <DialogDescription>This action will apply to {selected.size} selected case(s)</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <p className="text-sm text-slate-600">Applying to <strong>{selected.size}</strong> case(s)</p>

            {actionDialog.action === 'change_status' && (
              <div>
                <Label>New Status</Label>
                <Select value={actionDialog.value} onValueChange={(v) => setActionDialog({ ...actionDialog, value: v })}>
                  <SelectTrigger data-testid="batch-status-select"><SelectValue placeholder="Select status" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="on_hold">On Hold</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {(actionDialog.action === 'add_note' || actionDialog.action === 'send_notification' || actionDialog.action === 'request_documents') && (
              <div>
                <Label>{actionDialog.action === 'add_note' ? 'Note' : actionDialog.action === 'request_documents' ? 'Document(s) Required' : 'Notification Message'}</Label>
                <Textarea value={actionDialog.notes} onChange={(e) => setActionDialog({ ...actionDialog, notes: e.target.value })}
                  placeholder={actionDialog.action === 'request_documents' ? 'e.g. Updated passport copy, Bank statements for last 6 months...' : 'Enter your message...'}
                  rows={3} data-testid="batch-notes-input" />
              </div>
            )}

            <div className="flex gap-3 justify-end">
              <Button variant="outline" onClick={() => setActionDialog({ ...actionDialog, open: false })}>Cancel</Button>
              <Button onClick={handleBatchAction} disabled={processing} className="bg-[#2a777a] hover:bg-[#236466] text-white" data-testid="confirm-batch-btn">
                {processing ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Zap className="h-4 w-4 mr-1" />}
                Apply to {selected.size} Cases
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BatchCaseOps;
