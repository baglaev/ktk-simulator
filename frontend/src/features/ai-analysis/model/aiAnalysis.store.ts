import { makeAutoObservable, runInAction } from 'mobx';

import { scenarioApi } from '@/pages/ScenarioPreparation/model/scenario.api';

import type { AiSessionAnalysis } from './aiAnalysis.types';

class AiAnalysisStore {
  analysis: AiSessionAnalysis | null = null;

  isLoading = false;
  isReportLoading = false;
  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  fetchAnalysis = async (sessionId: string) => {
    try {
      this.isLoading = true;
      this.error = null;

      const { data } = await scenarioApi.aiAnalysis(sessionId);

      runInAction(() => {
        this.analysis = data;
      });

      return data;
    } catch (error) {
      console.error(error);

      runInAction(() => {
        this.error = 'Не удалось получить ИИ-разбор';
      });

      throw error;
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  reset = () => {
    this.analysis = null;
    this.error = null;
  };

  downloadReport = async (sessionId: string) => {
    try {
      this.isReportLoading = true;
      this.error = null;

      const { data } = await scenarioApi.downloadAiAnalysisReport(sessionId);

      const url = window.URL.createObjectURL(data);

      const link = document.createElement('a');

      link.href = url;
      link.download = `ai-analysis-${sessionId}.pdf`;

      document.body.appendChild(link);

      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);

      runInAction(() => {
        this.error = 'Не удалось скачать PDF-отчёт';
      });

      throw error;
    } finally {
      runInAction(() => {
        this.isReportLoading = false;
      });
    }
  };
}

export const aiAnalysisStore = new AiAnalysisStore();
