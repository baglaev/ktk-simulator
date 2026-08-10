import { makeAutoObservable, runInAction } from 'mobx';

import { authApi, type UserRole } from './auth.api';

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

  login = async (login: string, password: string) => {
    this.isLoading = true;
    this.error = '';

    try {
      const { data } = await authApi.login({
        login,
        password,
      });

      if (!data.login) {
        runInAction(() => {
          this.error = 'Неверный логин или пароль';
        });

        return null;
      }

      runInAction(() => {
        this.isAuthenticated = true;
        this.role = data.role;
      });

      localStorage.setItem('role', data.role);

      return data.redirectTo;
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
