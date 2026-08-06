import { SimulatorMain } from '@/features/simulator/SimulatorMain/ui/SimulatorMain';
import { SimulatorLayout } from '@/widgets/layouts/SimulatoLayout/ui/SimulatorLayout';

export const SimlatorPage = () => {
  return (
    <div>
      <SimulatorLayout>
        <SimulatorMain />
      </SimulatorLayout>
    </div>
  );
};

SimlatorPage.displayName = 'SimlatorPage';
