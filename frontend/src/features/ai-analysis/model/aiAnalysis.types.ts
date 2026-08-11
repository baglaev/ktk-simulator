export type AiAnalysisStatus = 'success' | 'warning' | 'alert';

export interface AiAnalysisError {
  order: number;
  code: string;
  classification: string;
  status: AiAnalysisStatus;

  detectedAtMs: number;

  userAction: string;
  consequence: string;
  correctApproach: string;
  prediction: string;

  hintShownAtMs: number | null;
}

export interface AiAnalysisProvenance {
  method: string;

  llmAttempted: boolean;
  llmUsed: boolean;

  llmStatus: string;
  llmError: string | null;
  llmErrorMessage: string | null;

  requestedModel: string | null;
  resolvedModel: string | null;

  usage: Record<string, unknown>;

  scoreChanged: boolean;

  sourceRefs: string[];
}

export interface AiSessionAnalysis {
  type: 'ai.session_analysis';

  sessionId: string;

  resultStatus: string;

  totalScore: number;

  summary: string;

  strengths: string[];

  errors: AiAnalysisError[];

  recommendations: string[];

  provenance: AiAnalysisProvenance;
}
