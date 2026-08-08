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
  mode: 'training';
}

export interface CreateSessionResponse {
  sessionId: string;
}
