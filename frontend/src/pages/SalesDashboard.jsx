/**
 * Phase 4A — SalesDashboard
 *
 * Internal sales executives get the EXACT same workflow as external partners.
 * This file is a thin wrapper that reuses PartnerDashboard with mode="sales"
 * to inject internal-only widgets (target, commission, rank, follow-ups).
 *
 * DRY principle: Single source of truth for PA pipeline / proposal / agreement /
 * payment workflows — no duplication.
 */
import PartnerDashboard from '@/pages/PartnerDashboard';

export default function SalesDashboard() {
  return <PartnerDashboard mode="sales" />;
}
