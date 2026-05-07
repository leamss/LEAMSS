import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';

/**
 * PaForwardForm — Forward-to-Admin remarks form (partner_review stage).
 */
export default function PaForwardForm({ pa, forwardRemarks, setForwardRemarks, handleForwardToAdmin, onCancel }) {
  return (
    <div className="bg-pink-50 rounded-lg p-4 border border-pink-200">
      <p className="text-sm font-semibold text-pink-800 mb-2 flex items-center gap-2">
        <Send className="h-4 w-4" /> Forward to Admin for 1st Approval
      </p>
      <label className="text-xs font-medium text-slate-600 block mb-1">Your remarks (optional — admin will see these)</label>
      <textarea value={forwardRemarks} onChange={e => setForwardRemarks(e.target.value)}
        className="w-full border rounded-md px-3 py-2 text-sm h-20"
        placeholder="e.g. All docs verified. Client seems eligible for Express Entry."
        data-testid="forward-remarks" />
      <div className="flex justify-end gap-2 mt-3">
        <Button variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => handleForwardToAdmin(pa.id)}
          className="bg-pink-600 hover:bg-pink-700" data-testid="confirm-forward">
          <Send className="h-4 w-4 mr-1" /> Forward to Admin
        </Button>
      </div>
    </div>
  );
}
