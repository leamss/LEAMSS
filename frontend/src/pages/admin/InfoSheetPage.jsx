/**
 * Phase 20.4 — Universal Info Sheet host page.
 * Mountable at /admin/info-sheets/:entityType/:entityId
 * Standalone admin entry point. Also serves as demo for Sir to verify the flow.
 */
import { useParams } from 'react-router-dom';
import InfoSheet from '@/components/InfoSheet/InfoSheet';
import { Card } from '@/components/ui/card';

export default function InfoSheetPage() {
  const { entityType = 'standalone', entityId } = useParams();
  if (!entityId) {
    return <Card className="p-6">Entity ID missing in URL.</Card>;
  }
  return (
    <div className="max-w-6xl mx-auto p-6">
      <header className="mb-4">
        <h1 className="text-3xl font-bold text-leamss-teal">Information Sheet</h1>
        <p className="text-sm text-slate-600 mt-1">
          Phase 20.4 · Universal 6-section schema · Auto-save · AI resume extraction (Claude Sonnet 4.5)
        </p>
      </header>
      <InfoSheet entityType={entityType} entityId={entityId} />
    </div>
  );
}
