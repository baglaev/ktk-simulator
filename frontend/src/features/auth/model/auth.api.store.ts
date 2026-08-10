import { makeAutoObservable, runInAction } from 'mobx';

import { authApi } from './auth.api';

export type UserRole = 'user' | 'instructor';

class AuthStore {
  isAuthenticated = false;
  role: UserRole | null = null;
  isLoading = false;
  error = '';

  constructor() {
    makeAutoObservable(this);

    this.restoreAuth();
  }

  restoreAuth = () => {
    const role = localStorage.getItem('role') as UserRole | null;

    if (role === 'user' || role === 'instructor') {
      this.role = role;
      this.isAuthenticated = true;
    }
  };

  login = async (username: string, password: string) => {
    this.isLoading = true;
    this.error = '';

    try {
      const { data } = await authApi.login({
        username,
        password,
      });

      if (!data.login) {
        runInAction(() => {
          this.error = 'Неверный логин или пароль';
        });

        return null;
      }

      const role: UserRole = data.path === '/instructor-page' ? 'instructor' : 'user';

      runInAction(() => {
        this.isAuthenticated = true;
        this.role = role;
      });

      localStorage.setItem('role', role);

      return data.path;
    } catch (error) {
      console.error(error);

      runInAction(() => {
        this.error = 'Ошибка авторизации';
      });

      return null;
    } finally {
      runInAction(() => {
        this.isLoading = false;
      });
    }
  };

  logout = () => {
    this.isAuthenticated = false;
    this.role = null;

    localStorage.removeItem('role');
  };
}

export const authStore = new AuthStore();
