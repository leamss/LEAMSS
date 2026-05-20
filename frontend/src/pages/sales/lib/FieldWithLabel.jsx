import { Label } from '@/components/ui/label';

export default function FieldWithLabel({ label, children }) {
  return (
    <div>
      <Label className="text-[10px] uppercase font-bold text-slate-500 mb-1 block">{label}</Label>
      {children}
    </div>
  );
}
