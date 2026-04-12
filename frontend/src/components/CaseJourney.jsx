import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Plane, MapPin, CheckCircle, Clock, Lock, ArrowRight, 
  FileText, Calendar, AlertTriangle, ChevronDown, ChevronUp 
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CaseJourney = ({ caseData, documents = [] }) => {
  const [expandedStep, setExpandedStep] = useState(null);
  const [timeline, setTimeline] = useState([]);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  });

  useEffect(() => {
    if (caseData?.id) {
      axios.get(`${API}/timeline/case/${caseData.id}`, getAuthHeader())
        .then(res => setTimeline(res.data?.events || []))
        .catch(() => {});
    }
  }, [caseData?.id]);

  if (!caseData) return null;

  const steps = caseData.steps || [];
  const completedSteps = steps.filter(s => s.status === 'completed');
  const currentStep = steps.find(s => s.status === 'in_progress' || (!s.is_locked && s.status !== 'completed'));
  const progress = steps.length ? (completedSteps.length / steps.length) * 100 : 0;

  const getStepDocs = (stepName) => documents.filter(d => d.step_name === stepName);

  const getStepIcon = (step, idx) => {
    if (step.status === 'completed') return <CheckCircle className="h-6 w-6 text-white" />;
    if (step === currentStep) return <span className="text-white font-bold text-sm">{idx + 1}</span>;
    if (step.is_locked) return <Lock className="h-5 w-5 text-white" />;
    return <Clock className="h-5 w-5 text-white" />;
  };

  const getStepColor = (step) => {
    if (step.status === 'completed') return 'from-emerald-500 to-emerald-600';
    if (step === currentStep) return 'from-[#2a777a] to-[#236466]';
    if (step.is_locked) return 'from-slate-300 to-slate-400';
    return 'from-amber-500 to-amber-600';
  };

  const getDaysSinceCreated = () => {
    if (!caseData.created_at) return 0;
    return Math.floor((Date.now() - new Date(caseData.created_at).getTime()) / 86400000);
  };

  return (
    <div className="space-y-6" data-testid="case-journey">
      {/* Journey Header - Flight Tracker Style */}
      <Card className="p-0 bg-white shadow-xl border-0 overflow-hidden">
        <div className="bg-gradient-to-r from-[#2a777a] via-[#236466] to-[#1a4e50] p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-white/70 text-sm mb-1">Your Immigration Journey</p>
              <h2 className="text-2xl font-bold">{caseData.product_name}</h2>
            </div>
            <Badge className="bg-white/20 text-white border-0 text-sm px-3 py-1">{caseData.case_id}</Badge>
          </div>

          {/* Visual Progress Bar */}
          <div className="relative mt-6 mb-2">
            <div className="flex items-center justify-between relative">
              {/* Origin */}
              <div className="flex flex-col items-center z-10">
                <div className="w-10 h-10 bg-emerald-400 rounded-full flex items-center justify-center border-2 border-white shadow-lg">
                  <MapPin className="h-5 w-5 text-white" />
                </div>
                <p className="text-xs text-white/80 mt-2 font-medium">Start</p>
              </div>

              {/* Flight Path */}
              <div className="absolute left-10 right-10 top-5 h-0.5 bg-white/20">
                <div className="h-full bg-emerald-400 transition-all duration-1000" 
                  style={{ width: `${progress}%` }} />
                {/* Airplane indicator */}
                <div className="absolute top-1/2 -translate-y-1/2 transition-all duration-1000"
                  style={{ left: `${Math.min(progress, 95)}%` }}>
                  <Plane className="h-5 w-5 text-white -rotate-0 drop-shadow-lg" />
                </div>
              </div>

              {/* Destination */}
              <div className="flex flex-col items-center z-10">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 border-white shadow-lg ${
                  progress === 100 ? 'bg-emerald-400' : 'bg-white/20'
                }`}>
                  <CheckCircle className={`h-5 w-5 ${progress === 100 ? 'text-white' : 'text-white/50'}`} />
                </div>
                <p className="text-xs text-white/80 mt-2 font-medium">Approved</p>
              </div>
            </div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-4 gap-4 mt-6 bg-white/10 rounded-xl p-4 backdrop-blur-sm">
            <div className="text-center">
              <p className="text-2xl font-bold">{Math.round(progress)}%</p>
              <p className="text-xs text-white/70">Complete</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{completedSteps.length}/{steps.length}</p>
              <p className="text-xs text-white/70">Steps Done</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{documents.length}</p>
              <p className="text-xs text-white/70">Documents</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{getDaysSinceCreated()}</p>
              <p className="text-xs text-white/70">Days Active</p>
            </div>
          </div>
        </div>

        {/* Current Step Highlight */}
        {currentStep && (
          <div className="px-6 py-4 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-[#f7620b] rounded-full flex items-center justify-center animate-pulse">
                <ArrowRight className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-xs text-amber-600 font-semibold uppercase tracking-wider">Current Step</p>
                <p className="font-bold text-slate-800">{currentStep.step_name}</p>
              </div>
              {currentStep.required_documents?.length > 0 && (
                <Badge className="bg-amber-100 text-amber-700 ml-auto">
                  {currentStep.required_documents.length} docs needed
                </Badge>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Step-by-Step Timeline */}
      <Card className="p-6 bg-white shadow-md border-0">
        <h3 className="text-lg font-bold text-slate-800 mb-6">Step-by-Step Progress</h3>
        <div className="relative">
          {steps.map((step, idx) => {
            const stepDocs = getStepDocs(step.step_name);
            const isExpanded = expandedStep === idx;
            const isCurrent = step === currentStep;

            return (
              <div key={idx} className="relative pl-10 pb-8 last:pb-0" data-testid={`journey-step-${idx}`}>
                {/* Vertical Line */}
                {idx < steps.length - 1 && (
                  <div className={`absolute left-[19px] top-10 w-0.5 h-[calc(100%-2.5rem)] ${
                    step.status === 'completed' ? 'bg-emerald-300' : 'bg-slate-200'
                  }`} />
                )}

                {/* Step Node */}
                <div className={`absolute left-0 top-0 w-10 h-10 rounded-full bg-gradient-to-br ${getStepColor(step)} flex items-center justify-center shadow-md ${
                  isCurrent ? 'ring-4 ring-[#2a777a]/20' : ''
                }`}>
                  {getStepIcon(step, idx)}
                </div>

                {/* Step Content */}
                <div className={`rounded-xl border p-4 transition-all cursor-pointer hover:shadow-md ${
                  isCurrent ? 'border-[#2a777a]/30 bg-[#2a777a]/5 shadow-md' :
                  step.status === 'completed' ? 'border-emerald-200 bg-emerald-50/50' :
                  'border-slate-200 bg-slate-50/50'
                }`} onClick={() => setExpandedStep(isExpanded ? null : idx)}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div>
                        <p className="font-semibold text-slate-800">
                          Step {step.step_order}: {step.step_name}
                        </p>
                        {step.description && <p className="text-xs text-slate-500 mt-0.5">{step.description}</p>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={`text-xs ${
                        step.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                        isCurrent ? 'bg-[#2a777a]/10 text-[#2a777a]' :
                        step.is_locked ? 'bg-slate-100 text-slate-500' : 'bg-amber-100 text-amber-700'
                      }`}>
                        {step.status === 'completed' ? 'Completed' : isCurrent ? 'In Progress' : step.is_locked ? 'Locked' : 'Pending'}
                      </Badge>
                      {stepDocs.length > 0 && (
                        <Badge variant="outline" className="text-xs">{stepDocs.length} docs</Badge>
                      )}
                      {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-slate-200 space-y-3">
                      {/* Required Documents */}
                      {step.required_documents?.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1">
                            <FileText className="h-3 w-3" /> Required Documents
                          </p>
                          <div className="space-y-1.5">
                            {step.required_documents.map((doc, di) => {
                              const uploaded = documents.find(d => 
                                d.step_name === step.step_name && 
                                (d.document_type === doc.doc_name || d.document_type === 'workflow')
                              );
                              return (
                                <div key={di} className="flex items-center gap-2 text-sm">
                                  {uploaded ? (
                                    <CheckCircle className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                                  ) : (
                                    <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0" />
                                  )}
                                  <span className={uploaded ? 'text-emerald-700' : 'text-amber-700'}>{doc.doc_name}</span>
                                  {uploaded && <Badge className="bg-emerald-100 text-emerald-700 text-xs ml-auto">Uploaded</Badge>}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Timeline Events for this step */}
                      {timeline.filter(e => e.step_name === step.step_name || e.details?.includes?.(step.step_name)).length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1">
                            <Calendar className="h-3 w-3" /> Activity
                          </p>
                          {timeline.filter(e => e.step_name === step.step_name || (typeof e.details === 'string' && e.details.includes(step.step_name))).slice(0, 3).map((event, ei) => (
                            <div key={ei} className="flex items-center gap-2 text-xs text-slate-500">
                              <div className="w-1.5 h-1.5 bg-slate-300 rounded-full flex-shrink-0" />
                              <span>{event.action || event.event_type}</span>
                              <span className="ml-auto">{new Date(event.created_at || event.timestamp).toLocaleDateString()}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {step.is_locked && (
                        <div className="bg-slate-100 rounded-lg p-3 text-center">
                          <Lock className="h-5 w-5 text-slate-400 mx-auto mb-1" />
                          <p className="text-sm text-slate-500">Complete previous steps to unlock</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Recent Activity from Timeline */}
      {timeline.length > 0 && (
        <Card className="p-6 bg-white shadow-md border-0">
          <h3 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5 text-[#2a777a]" /> Recent Case Activity
          </h3>
          <div className="space-y-3">
            {timeline.slice(0, 8).map((event, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg" data-testid={`timeline-event-${idx}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  event.type === 'step_completed' ? 'bg-emerald-100 text-emerald-600' :
                  event.type === 'document_uploaded' ? 'bg-blue-100 text-blue-600' :
                  event.type === 'chat_message' ? 'bg-teal-100 text-teal-600' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {event.type === 'step_completed' ? <CheckCircle className="h-4 w-4" /> :
                   event.type === 'document_uploaded' ? <FileText className="h-4 w-4" /> :
                   <Clock className="h-4 w-4" />}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-800">{event.title || event.action || event.type?.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-slate-500">{event.description || (typeof event.details === 'string' ? event.details : '')}</p>
                </div>
                <p className="text-xs text-slate-400 flex-shrink-0">
                  {new Date(event.timestamp || event.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default CaseJourney;
