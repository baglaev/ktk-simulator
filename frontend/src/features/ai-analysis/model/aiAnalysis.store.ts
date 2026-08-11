import { makeAutoObservable, runInAction } from 'mobx';

import { scenarioApi } from '@/pages/ScenarioPreparation/model/scenario.api';

import type { AiSessionAnalysis } from './aiAnalysis.types';

class AiAnalysisStore {
  analysis: AiSessionAnalysis | null = null;

  isLoading = false;

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
}

export const aiAnalysisStore = new AiAnalysisStore();
