import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { MainPage } from '@/pages/MainPage/ui/MainPage';
import { ScenarioPreparationPage } from '@/pages/ScenarioPreparation/ui/ScenarioPreparation';
import { SimlatorPage } from '@/pages/SimlatorPage/ui/SimlatorPage';
import { SummaryResultPage } from '@/pages/SummaryResultPage/ui/SummaryResultPage';

import { LoginPage } from '@/pages/LoginPage/ui/LoginPage';
import { ProtectedRoute } from './ProtectedRouter';
import { InstructorPage } from '@/pages/InstructoPage/ui/InstrucotrPage';

export const AppRouter = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute allowedRole="user" />}>
          <Route path="/" element={<MainPage />} />
          <Route path="/preparation" element={<ScenarioPreparationPage />} />
          <Route path="/simulator" element={<SimlatorPage />} />
          <Route path="/summary-results" element={<SummaryResultPage />} />
        </Route>

        <Route element={<ProtectedRoute allowedRole="instructor" />}>
          <Route path="/instructor" element={<InstructorPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

AppRouter.displayName = 'AppRouter';
