export type InstructorResultMode = 'training' | 'control';

export type InstructorJournalKind = 'action' | 'hint' | string;

export interface InstructorJournalItem {
  time: string;
  virtualTimeMs: number;
  kind: InstructorJournalKind;
  description: string;
}

export interface InstructorResultItem {
  sessionId: string;

  traineeId: string;
  traineeName: string;

  instructorId: string;

  scenarioId: string;
  scenarioVersion: string;

  mode: InstructorResultMode;

  sessionStatus: string;
  resultStatus: string;
  outcome: string;

  totalScore: number;
  maxScore: number;

  elapsedTimeMs: number;

  completedAt: string;

  journal: InstructorJournalItem[];
}

export interface InstructorResultsResponse {
  items: InstructorResultItem[];
  total: number;
}
