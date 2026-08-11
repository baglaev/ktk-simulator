export type ScenarioMode = 'training' | 'control';

export interface Scenario {
  scenarioId: string;
  scenarioVersion: string;
  name: string;
  description: string;
}

export interface CreateSessionRequest {
  scenarioId: string;
  traineeId: string;
  instructorId: string;
  mode: ScenarioMode;
}

export interface CreateSessionResponse {
  sessionId: string;
}
