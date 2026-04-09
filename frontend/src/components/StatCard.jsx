import { Card } from '@/components/ui/card';

const StatCard = ({ label, value, color = 'text-gray-900', subtext, icon: Icon, onClick, testId }) => (
  <Card
    className={`p-5 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-all ${onClick ? 'cursor-pointer' : ''}`}
    onClick={onClick}
    data-testid={testId}
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.05em] text-gray-500">{label}</p>
        <p className={`text-2xl md:text-3xl font-bold tracking-tight mt-1.5 ${color}`}>{value}</p>
        {subtext && <p className="text-xs text-gray-400 mt-1">{subtext}</p>}
      </div>
      {Icon && (
        <div className="h-9 w-9 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0">
          <Icon className="h-4.5 w-4.5 text-gray-400" />
        </div>
      )}
    </div>
  </Card>
);

const StatGrid = ({ children, cols = 4 }) => (
  <div className={`grid grid-cols-2 md:grid-cols-${cols} gap-4`}>
    {children}
  </div>
);

export { StatCard, StatGrid };
export default StatCard;
