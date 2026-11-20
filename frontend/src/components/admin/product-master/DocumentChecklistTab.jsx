import React from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Trash2, ListChecks, FileText } from 'lucide-react';

const CATEGORIES = ['Identity', 'Education', 'Work Experience', 'Language', 'Financial', 'Character', 'Health', 'Family', 'Other'];
const REQUIRED_FOR = [
  { val: 'all_applicants', label: 'All Applicants' },
  { val: 'primary_applicant', label: 'Primary Applicant Only' },
  { val: 'spouse', label: 'Spouse / Partner' },
  { val: 'dependents', label: 'Dependents / Children' },
  { val: 'applicants_16_plus', label: 'Applicants 16+' },
];

export default function DocumentChecklistTab({ checklist, onChangeChecklist }) {
  const items = checklist || [];

  const addItem = () => {
    onChangeChecklist([
      ...items,
      {
        category: 'Identity',
        document_name: '',
        required_for: 'all_applicants',
        description: '',
      },
    ]);
  };

  const updateItem = (idx, patch) => {
    const next = [...items];
    next[idx] = { ...next[idx], ...patch };
    onChangeChecklist(next);
  };

  const removeItem = (idx) => {
    onChangeChecklist(items.filter((_, i) => i !== idx));
  };

  return (
    <Card className="p-4 space-y-3 text-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 font-bold text-slate-800 text-sm">
          <ListChecks className="h-4 w-4 text-emerald-600" />
          Document Checklist Template ({items.length})
        </div>
        <Button size="sm" variant="outline" onClick={addItem} className="h-7 text-xs">
          <Plus className="h-3.5 w-3.5 mr-1" />Add Document
        </Button>
      </div>

      <p className="text-[11px] text-slate-500">
        This template defines the default checklist items auto-generated in the client portal and case manager workspace when a client purchases this visa product.
      </p>

      {items.length === 0 ? (
        <p className="text-slate-400 italic">No checklist items defined yet.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item, idx) => (
            <div key={idx} className="p-2.5 bg-slate-50 border rounded-lg flex items-start gap-2">
              <div className="flex-1 space-y-1.5">
                <div className="grid grid-cols-12 gap-2">
                  <div className="col-span-3">
                    <select
                      value={item.category || 'Identity'}
                      onChange={(e) => updateItem(idx, { category: e.target.value })}
                      className="h-7 w-full rounded border border-input bg-white px-2 text-xs font-semibold"
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-span-6">
                    <Input
                      className="h-7 text-xs font-bold"
                      placeholder="Document Name (e.g. Valid Passport, Degree Certificate)"
                      value={item.document_name || ''}
                      onChange={(e) => updateItem(idx, { document_name: e.target.value })}
                    />
                  </div>
                  <div className="col-span-3">
                    <select
                      value={item.required_for || 'all_applicants'}
                      onChange={(e) => updateItem(idx, { required_for: e.target.value })}
                      className="h-7 w-full rounded border border-input bg-white px-2 text-[11px]"
                    >
                      {REQUIRED_FOR.map((r) => (
                        <option key={r.val} value={r.val}>
                          {r.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <Input
                  className="h-7 text-xs text-slate-600"
                  placeholder="Instructions for client (e.g. Color scan of all pages including stamps)"
                  value={item.description || ''}
                  onChange={(e) => updateItem(idx, { description: e.target.value })}
                />
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeItem(idx)}
                className="h-7 text-rose-500 hover:bg-rose-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
