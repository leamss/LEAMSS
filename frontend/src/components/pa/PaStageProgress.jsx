/**
 * PaStageProgress — bottom horizontal stage indicator (numbered dots).
 */
const STAGES = ['new', 'payment_pending', 'payment_received', 'under_review', 'approved', 'proposal_sent', 'case_created'];

export default function PaStageProgress({ stage }) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto py-2">
      {STAGES.map((s, idx) => {
        const isCurrent = stage === s;
        const isPast = STAGES.indexOf(stage) > idx;
        return (
          <div key={s} className="flex items-center">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
              isPast ? 'bg-emerald-500 text-white' : isCurrent ? 'bg-[#2a777a] text-white ring-2 ring-[#2a777a]/20' : 'bg-slate-200 text-slate-400'
            }`}>{isPast ? '✓' : idx + 1}</div>
            {idx < STAGES.length - 1 && <div className={`w-6 h-0.5 ${isPast ? 'bg-emerald-300' : 'bg-slate-200'}`} />}
          </div>
        );
      })}
    </div>
  );
}
