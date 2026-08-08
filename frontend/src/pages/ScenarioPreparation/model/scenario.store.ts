import { makeAutoObservable, runInAction } from 'mobx';
import { scenarioApi } from './scenario.api';
import type { Scenario } from './scenario.types';

class ScenarioStore {
  scenarios: Scenario[] = [];

  selectedScenario: Scenario | null = null;

  sessionId: string | null = null;

  isLoading = false;
  isStarting = false;

  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  fetchAllScenarios = async () => {
    try {
      this.isLoading = true;
      this.error = null;

      const { data } = await scenarioApi.getAllScenarios();

      runInAction(() => {
        this.scenarios = data;

        // Если пока используется первый сценарий
        this.selectedScenario = data[0] ?? null;
      });
    } catch (e) {
      console.error(e);

      runInAction(() => {
        this.error = 'Не удалось загрузить сценарии';
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  createSession = async () => {
    if (!this.selectedScenario) {
      throw new Error('Сценарий не выбран');
    }

    try {
      this.isLoading = true;
      this.error = null;

      const { data } = await scenarioApi.createSession({
        scenarioId: this.selectedScenario.scenarioId,
        traineeId: 'trainee-1',
        instructorId: 'instructor-1',
        mode: 'training',
      });

      runInAction(() => {
        this.sessionId = data.sessionId;
      });

      return data.sessionId;
    } catch (e) {
      console.error(e);

      runInAction(() => {
        this.error = 'Не удалось создать сессию';
      });

      throw e;
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  startSession = async () => {
    if (!this.sessionId) {
      throw new Error('Сессия не создана');
    }

    try {
      this.isStarting = true;
      this.error = null;

      await scenarioApi.startSession(this.sessionId);
    } catch (e) {
      console.error(e);

      runInAction(() => {
        this.error = 'Не удалось запустить сценарий';
      });

      throw e;
    } finally {
      runInAction(() => {
        this.isStarting = false;
      });
    }
  };

  initialize = async () => {
    try {
      await this.fetchAllScenarios();

      if (!this.selectedScenario) {
        throw new Error('Сценарии не найдены');
      }

      await this.createSession();
    } catch (e) {
      console.error(e);
    }
  };
}

export const scenarioStore = new ScenarioStore();
