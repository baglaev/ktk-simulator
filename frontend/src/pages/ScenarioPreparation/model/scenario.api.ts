import { apiScenarios, apiSessions } from '@/shared/api/baseApiConfig';
import type { CreateSessionRequest, CreateSessionResponse, Scenario } from './scenario.types';

export const scenarioApi = {
  getAllScenarios: () => apiScenarios.get<Scenario[]>('/'),

  createSession: (data: CreateSessionRequest) => apiSessions.post<CreateSessionResponse>('/', data),

  startSession: (sessionId: string) => apiSessions.post(`/${sessionId}/start`),
};
