import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle, Clock, AlertCircle, XCircle, FileText, Upload, ChevronDown, ChevronRight } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_CONFIG = {
  uploaded: { icon: Clock, color: 'bg-blue-100 text-blue-700', label: 'Uploaded' },
  approved: { icon: CheckCircle, color: 'bg-green-100 text-green-700', label: 'Approved' },
  rejected: { icon: XCircle, color: 'bg-red-100 text-red-700', label: 'Rejected' },
  pending: { icon: Clock, color: 'bg-amber-100 text-amber-700', label: 'Pending Upload' },
  missing: { icon: AlertCircle, color: 'bg-gray-100 text-gray-500', label: 'Not Uploaded' },
};

const DocumentChecklist = ({ caseId, caseSteps = [], documents = [], workflowSteps = [] }) => {
  const [expandedSteps, setExpandedSteps] = useState({});

  const toggleStep = (idx) => setExpandedSteps(prev => ({ ...prev, [idx]: !prev[idx] }));

  // Build checklist from workflow steps' required documents
  const buildChecklist = () => {
    const checklist = [];
    const sortedSteps = [...(caseSteps || [])].sort((a, b) => (a.step_order || 0) - (b.step_order || 0));

    for (const step of sortedSteps) {
      // Find matching workflow step to get required docs
      const wfStep = (workflowSteps || []).find(ws =>
        ws.step_name === step.step_name || ws.step_order === step.step_order
      );
      const requiredDocs = wfStep?.required_documents || [];

      const docItems = requiredDocs.map(rd => {
        const docName = typeof rd === 'string' ? rd : (rd.doc_name || rd.name || rd);
        const isMandatory = typeof rd === 'object' ? (rd.is_mandatory !== false && rd.mandatory !== false) : true;

        // Find matching uploaded document
        const uploaded = (documents || []).find(d =>
          (d.document_type || '').toLowerCase().includes(docName.toString().toLowerCase()) ||
          docName.toString().toLowerCase().includes((d.document_type || '').toLowerCase())
        );

        return {
          name: docName.toString(),
          mandatory: isMandatory,
          status: uploaded ? uploaded.status : 'missing',
          uploadedDoc: uploaded || null,
          description: typeof rd === 'object' ? rd.description : '',
        };
      });

      checklist.push({
        step_name: step.step_name,
        step_order: step.step_order,
        step_status: step.status,
        documents: docItems,
        total: docItems.length,
        completed: docItems.filter(d => d.status === 'approved').length,
        uploaded: docItems.filter(d => ['uploaded', 'approved', 'pending'].includes(d.status)).length,
      });
    }
    return checklist;
  };

  const checklist = buildChecklist();
  const totalDocs = checklist.reduce((sum, s) => sum + s.total, 0);
  const completedDocs = checklist.reduce((sum, s) => sum + s.completed, 0);
  const uploadedDocs = checklist.reduce((sum, s) => sum + s.uploaded, 0);
  const overallProgress = totalDocs > 0 ? (completedDocs / totalDocs) * 100 : 0;

  if (checklist.length === 0 || totalDocs === 0) {
    return (
      <Card className="p-5 border border-gray-200" data-testid="doc-checklist-empty">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-gray-400" />
          <p className="text-sm text-gray-500">No document requirements defined for this case workflow.</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="document-checklist">
      {/* Overall Progress */}
      <Card className="p-4 border border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-900 text-sm">Document Progress</h3>
          <Badge variant="outline" className="text-xs">{completedDocs}/{totalDocs} approved</Badge>
        </div>
        <Progress value={overallProgress} className="h-2 mb-2" />
        <div className="flex gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-500" /> {completedDocs} Approved</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-500" /> {uploadedDocs - completedDocs} Pending Review</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-gray-300" /> {totalDocs - uploadedDocs} Not Uploaded</span>
        </div>
      </Card>

      {/* Per-Step Checklists */}
      {checklist.map((step, idx) => {
        const stepProgress = step.total > 0 ? (step.completed / step.total) * 100 : 0;
        const isExpanded = expandedSteps[idx] !== false; // Default expanded
        const isActive = step.step_status === 'in_progress';
        const isCompleted = step.step_status === 'completed';

        return (
          <Card key={idx} className={`border overflow-hidden ${isActive ? 'border-[#2a777a]/30 bg-[#2a777a]/[0.02]' : 'border-gray-200'}`}>
            <div className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50/50" onClick={() => toggleStep(idx)}>
              <div className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                isCompleted ? 'bg-green-500 text-white' : isActive ? 'bg-[#2a777a] text-white' : 'bg-gray-200 text-gray-500'
              }`}>
                {isCompleted ? <CheckCircle className="h-4 w-4" /> : step.step_order}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900">{step.step_name}</p>
                <p className="text-xs text-gray-500">{step.completed}/{step.total} documents approved</p>
              </div>
              <div className="w-20">
                <Progress value={stepProgress} className="h-1.5" />
              </div>
              {isExpanded ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
            </div>

            {isExpanded && step.documents.length > 0 && (
              <div className="border-t border-gray-100 divide-y divide-gray-50">
                {step.documents.map((doc, di) => {
                  const cfg = STATUS_CONFIG[doc.status] || STATUS_CONFIG.missing;
                  const StatusIcon = cfg.icon;
                  return (
                    <div key={di} className="flex items-center gap-3 px-4 py-2.5 pl-14">
                      <StatusIcon className={`h-4 w-4 flex-shrink-0 ${cfg.color.split(' ')[1]}`} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-800">{doc.name}</p>
                        {doc.description && <p className="text-xs text-gray-400">{doc.description}</p>}
                      </div>
                      <div className="flex items-center gap-2">
                        {doc.mandatory && <Badge variant="outline" className="text-[9px] px-1 py-0 border-red-200 text-red-500">Required</Badge>}
                        <Badge className={`text-[10px] px-1.5 py-0 ${cfg.color}`}>{cfg.label}</Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
};

export default DocumentChecklist;
