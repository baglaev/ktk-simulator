import { makeAutoObservable, runInAction } from 'mobx';

import { scenarioApi } from '@/pages/ScenarioPreparation/model/scenario.api';

import type { ScenarioResult } from './result.types';

class ResultStore {
  result: ScenarioResult | null = null;

  isLoading = false;

  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  fetchResult = async (sessionId: string) => {
    try {
      this.isLoading = true;
      this.error = null;

      const { data } = await scenarioApi.getSessionResult(sessionId);

      runInAction(() => {
        this.result = data;
      });

      return data;
    } catch (error) {
      console.error(error);

      runInAction(() => {
        this.error = 'Не удалось получить результат сценария';
      });

      throw error;
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  reset = () => {
    this.result = null;
    this.error = null;
  };
}

export const resultStore = new ResultStore();
