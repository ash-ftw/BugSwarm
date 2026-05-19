import { useQuery } from '@tanstack/react-query';

import { api } from './client';

export type ProviderStatus = {
  provider_key: string;
  model: string;
  configured: boolean;
  enabled: boolean;
  free_mode: boolean;
  base_url?: string | null;
  status_label?: string;
};

export type SystemConfig = {
  environment: string;
  ai_free_mode: boolean;
  providers: ProviderStatus[];
  default_agent_count: number;
  default_max_depth: number;
};

export function useSystemConfig() {
  return useQuery({
    queryKey: ['system-config'],
    queryFn: async () => {
      const response = await api.get<SystemConfig>('/system/config');
      return response.data;
    },
    retry: false,
  });
}
