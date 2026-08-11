import { apiScenarios, apiSessions } from '@/shared/api/baseApiConfig';
import type { CreateSessionRequest, CreateSessionResponse, Scenario } from './scenario.types';
import type { AiSessionAnalysis } from '@/features/ai-analysis/model/aiAnalysis.types';

import type { ScenarioResult } from '@/features/summary/model/result.types';

export const scenarioApi = {
  getAllScenarios: () => apiScenarios.get<Scenario[]>('/'),

  createSession: (data: CreateSessionRequest) => apiSessions.post<CreateSessionResponse>('/', data),

  startSession: (sessionId: string) => apiSessions.post(`/${sessionId}/start`),

  getSessionResult: (sessionId: string) => apiSessions.get<ScenarioResult>(`/${sessionId}/result`),

  aiAnalysis: (sessionId: string) =>
    apiSessions.post<AiSessionAnalysis>(`/${sessionId}/ai-analysis`),
};
