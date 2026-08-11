import { AiAnalysis } from '@/features/ai-analysis/ui/AiAnalysis';
import { SimulatorLayout } from '@/widgets/layouts/SimulatoLayout/ui/SimulatorLayout';

export const AiAnalysisPage = () => {
  return (
    <SimulatorLayout>
      <AiAnalysis />
    </SimulatorLayout>
  );
};

AiAnalysisPage.displayName = 'AiAnalysisPage';
