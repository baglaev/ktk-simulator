import { makeAutoObservable, runInAction } from 'mobx';
import axios from 'axios';

import { authApi, type UserRole } from './auth.api';

class AuthStore {
  isAuthenticated = false;
  role: UserRole | null = null;
  username: string | null = null;
  displayName: string | null = null;
  assignedInstructorId: string | null = null;
  isLoading = false;
  error = '';

  constructor() {
    makeAutoObservable(this);

    this.restoreAuth();
  }

  restoreAuth = () => {
    const role = localStorage.getItem('role') as UserRole | null;
    const username = localStorage.getItem('username');
    const displayName = localStorage.getItem('displayName');
    const assignedInstructorId = localStorage.getItem('assignedInstructorId');

    if ((role === 'user' || role === 'instructor') && username && displayName) {
      this.role = role;
      this.username = username;
      this.displayName = displayName;
      this.assignedInstructorId = assignedInstructorId;
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
        this.username = data.username;
        this.displayName = data.displayName;
        this.assignedInstructorId = data.assignedInstructorId;
      });

      localStorage.setItem('role', data.role);
      localStorage.setItem('username', data.username);
      localStorage.setItem('displayName', data.displayName);
      if (data.assignedInstructorId) {
        localStorage.setItem('assignedInstructorId', data.assignedInstructorId);
      } else {
        localStorage.removeItem('assignedInstructorId');
      }

      return data.redirectTo;
    } catch (error) {
      console.error(error);

      runInAction(() => {
        this.error =
          axios.isAxiosError(error) && error.response?.status === 401
            ? 'Неверный логин или пароль'
            : 'Ошибка авторизации';
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
    this.username = null;
    this.displayName = null;
    this.assignedInstructorId = null;

    localStorage.removeItem('role');
    localStorage.removeItem('username');
    localStorage.removeItem('displayName');
    localStorage.removeItem('assignedInstructorId');
  };
}

export const authStore = new AuthStore();
