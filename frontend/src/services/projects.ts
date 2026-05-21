import { api } from './client';
import type { AuthProfile } from './authProfiles';

export type ProjectScope = {
  id: string;
  scope_type: 'allow' | 'exclude';
  pattern: string;
  created_at: string;
};

export type LLMProviderConfig = {
  id: string;
  provider_key: 'groq' | 'gptoss' | 'gemini' | 'openrouter';
  model_name: string;
  base_url: string | null;
  is_enabled: boolean;
  is_free_mode: boolean;
  timeout_seconds: number;
  max_retries: number;
};

export type Project = {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  base_url: string;
  status: string;
  default_max_depth: number;
  default_agent_count: number;
  default_test_intensity: 'low' | 'medium' | 'high';
  llm_council_enabled: boolean;
  llm_consensus_mode: string;
  free_ai_mode: boolean;
  scopes: ProjectScope[];
  llm_provider_configs: LLMProviderConfig[];
  auth_profiles: AuthProfile[];
  created_at: string;
  updated_at: string;
};

export type ProjectPayload = {
  name: string;
  description?: string | null;
  base_url: string;
  default_max_depth: number;
  default_agent_count: number;
  default_test_intensity: 'low' | 'medium' | 'high';
  llm_council_enabled: boolean;
  llm_consensus_mode: 'majority_vote' | 'strict_unanimous' | 'rule_weighted';
  free_ai_mode: boolean;
  allowed_paths: string[];
  excluded_paths: string[];
};

export async function listProjects() {
  const response = await api.get<{ projects: Project[] }>('/projects');
  return response.data.projects;
}

export async function createProject(payload: ProjectPayload) {
  const response = await api.post<Project>('/projects', payload);
  return response.data;
}

export async function createDemoProject() {
  const response = await api.post<Project>('/projects/demo');
  return response.data;
}

export async function updateProject(projectId: string, payload: Partial<ProjectPayload> & { status?: string }) {
  const response = await api.patch<Project>(`/projects/${projectId}`, payload);
  return response.data;
}

export async function deleteProject(projectId: string) {
  await api.delete(`/projects/${projectId}`);
}
