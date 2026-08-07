import { MainPage } from '@/pages/MainPage/ui/MainPage';
import { ScenarioPreparationPage } from '@/pages/ScenarioPreparation/ui/ScenarioPreparation';
import { SimlatorPage } from '@/pages/SimlatorPage/ui/SimlatorPage';
import { SummaryResultPage } from '@/pages/SummaryResultPage/ui/SummaryResultPage';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

export const AppRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/preparation" element={<ScenarioPreparationPage />} />
        <Route path="/simulator" element={<SimlatorPage />} />
        <Route path="/summary-results" element={<SummaryResultPage />} />
      </Routes>
    </BrowserRouter>
  );
};

AppRouter.displayName = 'AppRouter';
