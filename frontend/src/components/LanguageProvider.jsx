import { createContext, useContext, useState, useEffect } from 'react';

const translations = {
  en: {
    // Common
    dashboard: 'Dashboard', login: 'Login', logout: 'Logout', email: 'Email', password: 'Password',
    save: 'Save', cancel: 'Cancel', delete: 'Delete', edit: 'Edit', search: 'Search', back: 'Back',
    loading: 'Loading...', noData: 'No data available', submit: 'Submit',
    // Nav
    cases: 'Cases', documents: 'Documents', tickets: 'Support', settings: 'Settings',
    overview: 'Overview', workflow: 'Workflow Steps', payments: 'Payments',
    knowledgeBase: 'Knowledge Base', surveys: 'Satisfaction Surveys', appointments: 'Appointments',
    referrals: 'Referral Program', greetings: 'Client Greetings', timeline: 'Case Timeline',
    bulkOps: 'Bulk Operations', slaTracker: 'SLA Tracker', caseTransfer: 'Case Transfer',
    cannedResponses: 'Canned Responses', revenueForcast: 'Revenue Forecast',
    cmPerformance: 'CM Performance', conversionFunnel: 'Conversion Funnel',
    // Dashboard
    pendingSales: 'Pending Sales', activeCases: 'Active Cases', totalClients: 'Total Clients',
    monthlyRevenue: 'Monthly Revenue', quickActions: 'Quick Actions',
    // Cases
    caseId: 'Case ID', clientName: 'Client Name', status: 'Status', product: 'Product',
    caseManager: 'Case Manager', currentStep: 'Current Step', created: 'Created',
    active: 'Active', completed: 'Completed', pending: 'Pending',
    // Documents  
    uploadDocument: 'Upload Document', fileName: 'File Name', documentType: 'Document Type',
    approved: 'Approved', rejected: 'Rejected', underReview: 'Under Review',
    // Chat
    newMessage: 'New Message', sendMessage: 'Send', typeMessage: 'Type a message...',
    // Onboarding
    welcome: 'Welcome', getStarted: 'Get Started', skip: 'Skip', next: 'Next', previous: 'Previous',
    // Survey
    rateExperience: 'Rate Your Experience', overallRating: 'Overall Rating',
    wouldRecommend: 'I would recommend LEAMSS to others',
    // Common Phrases
    noResults: 'No results found', confirmDelete: 'Are you sure you want to delete?',
    success: 'Success', error: 'Error',
  },
  hi: {
    // Common
    dashboard: 'डैशबोर्ड', login: 'लॉगिन', logout: 'लॉगआउट', email: 'ईमेल', password: 'पासवर्ड',
    save: 'सहेजें', cancel: 'रद्द करें', delete: 'हटाएं', edit: 'संपादित करें', search: 'खोजें', back: 'वापस',
    loading: 'लोड हो रहा है...', noData: 'कोई डेटा उपलब्ध नहीं', submit: 'जमा करें',
    // Nav
    cases: 'केस', documents: 'दस्तावेज़', tickets: 'सहायता', settings: 'सेटिंग्स',
    overview: 'अवलोकन', workflow: 'कार्य चरण', payments: 'भुगतान',
    knowledgeBase: 'ज्ञान केंद्र', surveys: 'संतुष्टि सर्वेक्षण', appointments: 'अपॉइंटमेंट',
    referrals: 'रेफरल कार्यक्रम', greetings: 'ग्राहक शुभकामनाएं', timeline: 'केस टाइमलाइन',
    bulkOps: 'बल्क ऑपरेशन', slaTracker: 'SLA ट्रैकर', caseTransfer: 'केस ट्रांसफर',
    cannedResponses: 'तैयार उत्तर', revenueForcast: 'राजस्व पूर्वानुमान',
    cmPerformance: 'CM प्रदर्शन', conversionFunnel: 'रूपांतरण फ़नल',
    // Dashboard
    pendingSales: 'लंबित बिक्री', activeCases: 'सक्रिय केस', totalClients: 'कुल ग्राहक',
    monthlyRevenue: 'मासिक राजस्व', quickActions: 'त्वरित कार्य',
    // Cases
    caseId: 'केस आईडी', clientName: 'ग्राहक का नाम', status: 'स्थिति', product: 'उत्पाद',
    caseManager: 'केस मैनेजर', currentStep: 'वर्तमान चरण', created: 'निर्मित',
    active: 'सक्रिय', completed: 'पूर्ण', pending: 'लंबित',
    // Documents
    uploadDocument: 'दस्तावेज़ अपलोड करें', fileName: 'फ़ाइल का नाम', documentType: 'दस्तावेज़ प्रकार',
    approved: 'स्वीकृत', rejected: 'अस्वीकृत', underReview: 'समीक्षाधीन',
    // Chat
    newMessage: 'नया संदेश', sendMessage: 'भेजें', typeMessage: 'संदेश लिखें...',
    // Onboarding
    welcome: 'स्वागत है', getStarted: 'शुरू करें', skip: 'छोड़ें', next: 'अगला', previous: 'पिछला',
    // Survey
    rateExperience: 'अपना अनुभव रेट करें', overallRating: 'समग्र रेटिंग',
    wouldRecommend: 'मैं LEAMSS की सिफारिश करूंगा',
    // Common Phrases
    noResults: 'कोई परिणाम नहीं मिला', confirmDelete: 'क्या आप वाकई हटाना चाहते हैं?',
    success: 'सफल', error: 'त्रुटि',
  }
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('leamss_lang') || 'en');

  useEffect(() => {
    localStorage.setItem('leamss_lang', lang);
  }, [lang]);

  const t = (key) => translations[lang]?.[key] || translations.en[key] || key;

  const toggleLanguage = () => setLang(prev => prev === 'en' ? 'hi' : 'en');

  return (
    <LanguageContext.Provider value={{ lang, setLang, t, toggleLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) return { lang: 'en', t: (key) => key, toggleLanguage: () => {}, setLang: () => {} };
  return context;
}

export function LanguageToggle() {
  const { lang, toggleLanguage } = useLanguage();
  return (
    <button
      onClick={toggleLanguage}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-full hover:bg-gray-50 transition-colors"
      data-testid="language-toggle"
    >
      <span className="text-base">{lang === 'en' ? '🇮🇳' : '🇬🇧'}</span>
      <span className="font-medium">{lang === 'en' ? 'हिंदी' : 'English'}</span>
    </button>
  );
}
