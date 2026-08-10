import { VITE_BASE_API } from '@/shared/api/baseApiConfig';
import axios from 'axios';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  login: boolean;
  path: string;
}

export const authApi = {
  login: (data: LoginRequest) => axios.post<LoginResponse>(`${VITE_BASE_API}/login`, data),
};
