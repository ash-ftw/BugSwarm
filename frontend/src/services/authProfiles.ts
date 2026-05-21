import { api } from './client';

export type AuthProfile = {
  id: string;
  project_id: string;
  name: string;
  auth_type: 'form' | 'storage_state';
  login_url: string | null;
  username_selector: string | null;
  password_selector: string | null;
  submit_selector: string | null;
  username_value: string | null;
  storage_state_path: string | null;
  is_active: boolean;
  password_configured: boolean;
  created_at: string;
};

export type AuthProfilePayload = {
  name: string;
  auth_type: 'form' | 'storage_state';
  login_url?: string | null;
  username_selector?: string | null;
  password_selector?: string | null;
  submit_selector?: string | null;
  username_value?: string | null;
  password_value?: string | null;
  storage_state_path?: string | null;
  is_active: boolean;
};

export async function listAuthProfiles(projectId: string) {
  const response = await api.get<{ auth_profiles: AuthProfile[] }>(`/projects/${projectId}/auth-profiles`);
  return response.data.auth_profiles;
}

export async function createAuthProfile(projectId: string, payload: AuthProfilePayload) {
  const response = await api.post<AuthProfile>(`/projects/${projectId}/auth-profiles`, payload);
  return response.data;
}

export async function updateAuthProfile(profileId: string, payload: Partial<AuthProfilePayload>) {
  const response = await api.patch<AuthProfile>(`/auth-profiles/${profileId}`, payload);
  return response.data;
}

export async function deleteAuthProfile(profileId: string) {
  await api.delete(`/auth-profiles/${profileId}`);
}
