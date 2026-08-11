export type ResultStatus = 'success' | 'warning' | 'alert';

export interface ScoreBlock {
  score: number;
  maxScore: number;
}

export interface TaskExecutionItem {
  taskId: string;
  title: string;
  status: ResultStatus;
  completedAtMs: number | null;
  description: string;
}

export interface ControlledParameter {
  parameterId: string;
  name: string;
  finalValue: number;
  minimumValue: number;
  unit: string;
  status: ResultStatus;
}

export interface ResultRemark {
  code: string;
  status: ResultStatus;
  title: string;
  description: string;
}

export interface ScenarioResult {
  sessionId: string;
  rubricVersion: string;

  status: string;
  outcome: string;
  mode: 'training' | 'control';

  completionReason: string;
  summary: string;

  elapsedTimeMs: number;

  totalScore: number;
  maxScore: number;

  diagnosis: ScoreBlock;
  stabilization: ScoreBlock;
  consequenceControl: ScoreBlock;
  timeliness: ScoreBlock;

  penalties: number;

  errorCodes: string[];

  criticalFailureReasons: string[];

  taskExecution: TaskExecutionItem[];

  controlledParameters: ControlledParameter[];

  remarks: ResultRemark[];

  completedAt: string;
}
