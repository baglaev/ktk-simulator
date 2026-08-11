import { VITE_BASE_API } from '@/shared/api/baseApiConfig';
import axios from 'axios';

export type UserRole = 'user' | 'instructor';

export interface LoginRequest {
  login: string;
  password: string;
}

export interface LoginResponse {
  login: boolean;
  role: UserRole;
  username: string;
  displayName: string;
  assignedInstructorId: string | null;
  redirectTo: string;
}

export const authApi = {
  login: (data: LoginRequest) => axios.post<LoginResponse>(`${VITE_BASE_API}/auth/login`, data),
};
