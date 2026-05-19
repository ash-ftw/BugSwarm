import { api } from './client';

export type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = LoginPayload & {
  name: string;
};

export type LoginResponse = {
  token: string;
  user: User;
};

export type RegisterResponse = {
  token: string;
  user_id: string;
  email: string;
};

export async function login(payload: LoginPayload) {
  const response = await api.post<LoginResponse>('/auth/login', payload);
  return response.data;
}

export async function register(payload: RegisterPayload) {
  const response = await api.post<RegisterResponse>('/auth/register', payload);
  return response.data;
}

export async function getMe() {
  const response = await api.get<User>('/auth/me');
  return response.data;
}
