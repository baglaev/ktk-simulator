import { makeAutoObservable, runInAction } from 'mobx';
import { scenarioApi } from './scenario.api';
import type { Scenario, ScenarioMode } from './scenario.types';

class ScenarioStore {
  scenarios: Scenario[] = [];

  selectedScenario: Scenario | null = null;

  sessionId: string | null = null;

  mode: ScenarioMode = 'training';

  isLoading = false;
  isStarting = false;

  error: string | null = null;

  constructor() {
    makeAutoObservable(this);

    this.sessionId = localStorage.getItem('sessionId');
  }

  setMode = (mode: ScenarioMode) => {
    this.mode = mode;
  };

  fetchAllScenarios = async () => {
    try {
      this.isLoading = true;
      this.error = null;

      const { data } = await scenarioApi.getAllScenarios();

      runInAction(() => {
        this.scenarios = data;
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

    const { data } = await scenarioApi.createSession({
      scenarioId: this.selectedScenario.scenarioId,
      traineeId: 'trainee-1',
      instructorId: 'instructor-1',
      mode: this.mode,
    });

    runInAction(() => {
      this.sessionId = data.sessionId;
    });

    localStorage.setItem('sessionId', data.sessionId);
    return data.sessionId;
  };

  startSession = async (sessionId: string) => {
    await scenarioApi.startSession(sessionId);
  };

  startScenario = async () => {
    try {
      this.isStarting = true;
      this.error = null;

      const sessionId = await this.createSession();

      await this.startSession(sessionId);
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
    } catch (e) {
      console.error(e);
    }
  };
}

export const scenarioStore = new ScenarioStore();
