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

export type QueueDepth = {
  name: string;
  pending_tasks: number;
};

export type QueueAutoscaleStatus = {
  redis_connected: boolean;
  queues: QueueDepth[];
  total_pending_tasks: number;
  target_pending_tasks_per_replica: number;
  min_worker_replicas: number;
  max_worker_replicas: number;
  recommended_worker_replicas: number;
  scale_direction: string;
  generated_at: string;
  error?: string | null;
};

export type RetentionPolicy = {
  screenshot_days: number;
  trace_days: number;
  report_days: number;
  browser_log_days: number;
  network_log_days: number;
};

export type RetentionCleanupResponse = {
  queued: boolean;
  task_id: string | null;
  dry_run: boolean;
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

export function useRetentionPolicy() {
  return useQuery({
    queryKey: ['retention-policy'],
    queryFn: async () => {
      const response = await api.get<RetentionPolicy>('/system/retention');
      return response.data;
    },
    retry: false,
  });
}

export function useQueueAutoscaleStatus() {
  return useQuery({
    queryKey: ['queue-autoscale-status'],
    queryFn: async () => {
      const response = await api.get<QueueAutoscaleStatus>('/system/queue');
      return response.data;
    },
    refetchInterval: 5000,
    retry: false,
  });
}

export async function queueRetentionCleanup(dryRun = false) {
  const response = await api.post<RetentionCleanupResponse>('/system/retention/cleanup', { dry_run: dryRun });
  return response.data;
}
