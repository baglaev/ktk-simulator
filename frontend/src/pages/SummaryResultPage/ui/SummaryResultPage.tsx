import { SimulatorSummary } from '@/features/summary/SimulatorSummary/ui/SimulatorSummary';
import { SimulatorLayout } from '@/widgets/layouts/SimulatoLayout/ui/SimulatorLayout';

export const SummaryResultPage = () => {
  return (
    <div>
      <SimulatorLayout>
        <SimulatorSummary />
      </SimulatorLayout>
    </div>
  );
};

SummaryResultPage.displayName = 'SummaryResultPage';
