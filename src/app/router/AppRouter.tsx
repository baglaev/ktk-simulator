import { MainPage } from '@/pages/MainPage/ui/MainPage';
import { ScenarioPreparationPage } from '@/pages/ScenarioPreparation/ui/ScenarioPreparation';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

export const AppRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/preparation" element={<ScenarioPreparationPage />} />
      </Routes>
    </BrowserRouter>
  );
};

AppRouter.displayName = 'AppRouter';
