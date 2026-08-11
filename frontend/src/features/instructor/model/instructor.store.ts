import { makeAutoObservable, runInAction } from 'mobx';

import { instructorApi } from './instructor.api';

import type { InstructorResultItem } from './instructor.types';

class InstructorStore {
  results: InstructorResultItem[] = [];

  total = 0;

  isLoading = false;

  error: string | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  fetchResults = async () => {
    try {
      this.isLoading = true;
      this.error = null;

      const { data } = await instructorApi.getResults();

      runInAction(() => {
        this.results = data.items;
        this.total = data.total;
      });
    } catch (error) {
      console.error(error);

      runInAction(() => {
        this.error = 'Не удалось загрузить результаты';
      });
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };
}

export const instructorStore = new InstructorStore();
