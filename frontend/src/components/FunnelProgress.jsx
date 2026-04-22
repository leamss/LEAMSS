import { Check } from 'lucide-react';

// 5-step funnel visible everywhere
export const FUNNEL_STEPS = [
  { key: 'created', label: 'PA Created', match: ['new', 'payment_pending', 'payment_received', 'partner_review', 'documents_submitted', 'under_review', 'approved', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'approved', label: 'Admin Approved', match: ['approved', 'proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'proposal', label: 'Proposal Sent', match: ['proposal_sent', 'proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'paid', label: 'Main Fee Paid', match: ['proposal_paid', 'awaiting_final_approval', 'case_created'] },
  { key: 'case', label: 'Case Active', match: ['case_created'] },
];

export default function FunnelProgress({ stage, compact = false }) {
  const activeIdx = FUNNEL_STEPS.reduce((acc, s, i) => s.match.includes(stage) ? i : acc, -1);

  if (compact) {
    return (
      <div className="flex items-center gap-1.5 text-[10px]">
        {FUNNEL_STEPS.map((s, i) => {
          const done = i <= activeIdx;
          return (
            <div key={s.key} className="flex items-center gap-1">
              <span className={`h-1.5 w-1.5 rounded-full ${done ? 'bg-emerald-500' : 'bg-slate-300'}`} />
              {i < FUNNEL_STEPS.length - 1 && <span className={`w-3 h-px ${done && i < activeIdx ? 'bg-emerald-500' : 'bg-slate-200'}`} />}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 w-full overflow-x-auto" data-testid="funnel-progress">
      {FUNNEL_STEPS.map((s, i) => {
        const done = i <= activeIdx;
        const current = i === activeIdx;
        return (
          <div key={s.key} className="flex items-center gap-1 flex-1 min-w-0">
            <div className={`flex items-center gap-1.5 ${current ? 'font-bold text-[#2a777a]' : done ? 'text-emerald-700' : 'text-slate-400'}`}>
              <span className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${done ? 'bg-emerald-500 text-white' : current ? 'bg-[#2a777a] text-white' : 'bg-slate-200 text-slate-500'}`}>
                {done && !current ? <Check className="h-3 w-3" /> : i + 1}
              </span>
              <span className="text-[11px] whitespace-nowrap hidden sm:inline">{s.label}</span>
            </div>
            {i < FUNNEL_STEPS.length - 1 && (
              <div className={`flex-1 h-px ${done && i < activeIdx ? 'bg-emerald-500' : 'bg-slate-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
