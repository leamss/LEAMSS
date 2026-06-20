import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  CheckCircle, ArrowRight, ArrowLeft, User, FileText, Upload, Brain, PartyPopper, ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STEPS = [
  { id: 'welcome', title: 'Welcome', icon: PartyPopper, desc: 'Welcome to LEAMSS Immigration' },
  { id: 'profile', title: 'Profile Check', icon: User, desc: 'Verify your profile details' },
  { id: 'info-sheet', title: 'Info Sheet', icon: FileText, desc: 'Fill your information sheet' },
  { id: 'documents', title: 'Documents', icon: Upload, desc: 'Upload required documents' },
  { id: 'tips', title: 'AI Tips', icon: Brain, desc: 'Get AI-powered tips for your case' },
];

const OnboardingWizard = ({ user, caseData, onComplete, onNavigate }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [profileData, setProfileData] = useState(null);
  const [aiTips, setAiTips] = useState([]);
  const [loadingTips, setLoadingTips] = useState(false);
  const [completedSteps, setCompletedSteps] = useState(new Set());

  const getAuthHeader = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } });
  const progress = ((currentStep + 1) / STEPS.length) * 100;

  useEffect(() => {
    // Check if user has completed onboarding before
    const done = localStorage.getItem(`onboarding_done_${user?.id}`);
    if (done) onComplete?.();
  }, [user]);

  const markComplete = () => {
    localStorage.setItem(`onboarding_done_${user?.id}`, 'true');
    onComplete?.();
  };

  const next = () => {
    setCompletedSteps(prev => new Set([...prev, STEPS[currentStep].id]));
    if (currentStep < STEPS.length - 1) setCurrentStep(currentStep + 1);
  };
  const prev = () => { if (currentStep > 0) setCurrentStep(currentStep - 1); };

  const fetchAiTips = async () => {
    if (aiTips.length > 0) return;
    setLoadingTips(true);
    try {
      const res = await axios.get(`${API}/ai/chat?message=Give me 5 quick tips to speed up my immigration case processing. Be concise and practical.&case_id=${caseData?.id || ''}`, getAuthHeader());
      const tips = (res.data?.response || '').split('\n').filter(t => t.trim().length > 5);
      setAiTips(tips.length > 0 ? tips.slice(0, 5) : ['Complete your information sheet fully', 'Upload all documents early', 'Keep your passport valid', 'Respond to requests promptly', 'Track document expiry dates']);
    } catch {
      setAiTips(['Complete your information sheet fully', 'Upload all documents early', 'Keep your passport valid', 'Respond to Case Manager requests promptly', 'Track document expiry dates']);
    }
    setLoadingTips(false);
  };

  useEffect(() => { if (currentStep === 4) fetchAiTips(); }, [currentStep]);

  const step = STEPS[currentStep];
  const StepIcon = step.icon;

  return (
    <div className="fixed inset-0 z-[100] bg-gradient-to-br from-[#2a777a]/95 to-[#1a5456]/95 flex items-center justify-center p-4" data-testid="onboarding-wizard">
      <Card className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Progress */}
        <div className="px-6 pt-5 pb-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Step {currentStep + 1} of {STEPS.length}</p>
            <button onClick={markComplete} className="text-xs text-gray-400 hover:text-gray-600" data-testid="skip-onboarding">Skip</button>
          </div>
          <Progress value={progress} className="h-1.5" />
          <div className="flex justify-between mt-2">
            {STEPS.map((s, i) => (
              <div key={s.id} className={`flex items-center justify-center h-6 w-6 rounded-full text-[10px] font-bold ${
                completedSteps.has(s.id) ? 'bg-green-500 text-white' :
                i === currentStep ? 'bg-[#2a777a] text-white' : 'bg-gray-100 text-gray-400'
              }`}>
                {completedSteps.has(s.id) ? <CheckCircle className="h-3.5 w-3.5" /> : i + 1}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6 min-h-[280px]">
          {/* Welcome Step */}
          {currentStep === 0 && (
            <div className="text-center" data-testid="step-welcome">
              <div className="w-16 h-16 mx-auto mb-4 bg-[#2a777a]/10 rounded-full flex items-center justify-center">
                <PartyPopper className="h-8 w-8 text-[#2a777a]" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome, {user?.name}!</h2>
              <p className="text-gray-500 mb-4">Let's get your immigration journey started. We'll guide you through a few quick steps to set everything up.</p>
              {caseData && (
                <Card className="p-3 bg-[#2a777a]/5 border border-[#2a777a]/20 text-left">
                  <p className="text-sm font-semibold text-gray-800">Your Case: {caseData.case_id}</p>
                  <p className="text-xs text-gray-500">{caseData.product_name}</p>
                </Card>
              )}
            </div>
          )}

          {/* Profile Check Step */}
          {currentStep === 1 && (
            <div data-testid="step-profile">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 bg-[#2a777a]/10 rounded-lg flex items-center justify-center"><User className="h-5 w-5 text-[#2a777a]" /></div>
                <div>
                  <h3 className="font-bold text-gray-900">Profile Check</h3>
                  <p className="text-xs text-gray-500">Make sure your details are correct</p>
                </div>
              </div>
              <div className="space-y-3 bg-gray-50 rounded-lg p-4">
                <div className="flex justify-between"><span className="text-sm text-gray-500">Name</span><span className="text-sm font-medium">{user?.name}</span></div>
                <div className="flex justify-between"><span className="text-sm text-gray-500">Email</span><span className="text-sm font-medium">{user?.email}</span></div>
                <div className="flex justify-between"><span className="text-sm text-gray-500">Role</span><span className="text-sm font-medium capitalize">{user?.role}</span></div>
                {caseData && <div className="flex justify-between"><span className="text-sm text-gray-500">Case Manager</span><span className="text-sm font-medium">{caseData.case_manager_name || 'Pending Assignment'}</span></div>}
              </div>
              <p className="text-xs text-green-600 mt-3 flex items-center gap-1"><CheckCircle className="h-3.5 w-3.5" /> Profile looks good!</p>
            </div>
          )}

          {/* Info Sheet Step */}
          {currentStep === 2 && (
            <div data-testid="step-info-sheet">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 bg-[#f7620b]/10 rounded-lg flex items-center justify-center"><FileText className="h-5 w-5 text-[#f7620b]" /></div>
                <div>
                  <h3 className="font-bold text-gray-900">Information Sheet</h3>
                  <p className="text-xs text-gray-500">Fill in your personal, education, and work details</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mb-4">Your information sheet helps your case manager process your application faster. The more complete it is, the quicker your case moves forward.</p>
              <div className="space-y-2">
                {['Personal Details', 'Family Information', 'Qualifications', 'Employment History'].map((section) => (
                  <div key={section} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-700">{section}</span>
                  </div>
                ))}
              </div>
              <Button onClick={() => { onNavigate?.('info-sheet'); markComplete(); }} size="sm" className="w-full mt-4 bg-[#f7620b] hover:bg-[#e55a09]" data-testid="go-to-info-sheet">
                Fill Info Sheet Now <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          )}

          {/* Documents Step */}
          {currentStep === 3 && (
            <div data-testid="step-documents">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 bg-leamss-orange-100 rounded-lg flex items-center justify-center"><Upload className="h-5 w-5 text-leamss-orange-600" /></div>
                <div>
                  <h3 className="font-bold text-gray-900">Upload Documents</h3>
                  <p className="text-xs text-gray-500">Upload your passport, photos, and other required documents</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mb-4">Your case workflow will tell you exactly which documents are needed at each step. Start by uploading basic documents like:</p>
              <div className="space-y-2">
                {['Passport Copy', 'Passport-size Photographs', 'Resume/CV', 'IELTS/Language Test Score'].map((doc) => (
                  <div key={doc} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <Upload className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-700">{doc}</span>
                  </div>
                ))}
              </div>
              <Button onClick={() => { onNavigate?.('uploaded'); markComplete(); }} size="sm" className="w-full mt-4 bg-leamss-orange-600 hover:bg-leamss-orange-700" data-testid="go-to-documents">
                Upload Documents <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          )}

          {/* AI Tips Step */}
          {currentStep === 4 && (
            <div data-testid="step-tips">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center"><Brain className="h-5 w-5 text-blue-600" /></div>
                <div>
                  <h3 className="font-bold text-gray-900">AI Tips for Success</h3>
                  <p className="text-xs text-gray-500">Personalized tips to speed up your case</p>
                </div>
              </div>
              <div className="space-y-2">
                {aiTips.map((tip, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                    <span className="h-5 w-5 rounded-full bg-blue-500 text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                    <p className="text-sm text-gray-700">{tip}</p>
                  </div>
                ))}
                {loadingTips && <div className="text-center py-4"><span className="text-sm text-gray-400">Loading AI tips...</span></div>}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-between items-center bg-gray-50">
          <Button onClick={prev} variant="ghost" size="sm" disabled={currentStep === 0} data-testid="onboarding-prev">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          {currentStep < STEPS.length - 1 ? (
            <Button onClick={next} size="sm" className="bg-[#2a777a] hover:bg-[#236466]" data-testid="onboarding-next">
              Next <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button onClick={markComplete} size="sm" className="bg-green-600 hover:bg-green-700" data-testid="onboarding-finish">
              <CheckCircle className="h-4 w-4 mr-1" /> Get Started!
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
};

export default OnboardingWizard;
