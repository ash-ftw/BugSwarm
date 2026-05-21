import { api } from './client';

export type AgentStatus = {
  id: string;
  agent_type: string;
  status: string;
  browser: string;
  viewport_width: number | null;
  viewport_height: number | null;
  current_url: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
};

export type DiscoveredPage = {
  id: string;
  url: string;
  title: string | null;
  status_code: number | null;
  page_type: string | null;
  forms_count: number | null;
  links_count: number | null;
  buttons_count: number | null;
  first_seen_at: string;
  last_seen_at: string;
};

export type TestRun = {
  id: string;
  project_id: string;
  name: string;
  status: string;
  agent_count: number;
  max_depth: number;
  max_duration_minutes: number;
  test_intensity: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  summary: Record<string, unknown> | null;
  agents: AgentStatus[];
  discovered_pages: DiscoveredPage[];
  discovered_pages_count: number;
  agent_steps_count: number;
  browser_logs_count: number;
  network_logs_count: number;
  bugs_count: number;
  test_cases_count: number;
};

export type TestRunEvent = {
  event: string;
  test_run_id: string;
  created_at?: string;
  agent_id?: string;
  agent_type?: string;
  agents?: Array<{
    agent_id: string;
    agent_type: string;
    status: string;
    current_url: string | null;
  }>;
  status?: string;
  action?: string;
  url?: string;
  title?: string | null;
  message?: string;
  target?: string | null;
  progress?: {
    pages_discovered?: number;
    steps_completed?: number;
    browser_logs?: number;
    network_logs?: number;
    bugs_found?: number;
    test_cases?: number;
    status_counts?: Record<string, number>;
  };
  current_url?: string;
  end_reason?: string;
  visited_count?: number;
  queued_count?: number;
  agent_steps_completed?: number;
  agent_action_limit?: number;
  agent_progress_percent?: number;
  pages_discovered?: number;
  steps_completed?: number;
  bugs_found?: number;
  test_cases_created?: number;
};

export type StartTestRunPayload = {
  name: string;
  agent_count: number;
  max_depth: number;
  max_actions: number;
  max_duration_minutes: number;
  test_intensity: 'low' | 'medium' | 'high';
  agent_types: string[];
  viewports: string[];
  llm_council_enabled: boolean;
  llm_providers: string[];
  llm_consensus_mode: 'majority_vote' | 'strict_unanimous' | 'rule_weighted';
  auth_profile_id: string | null;
  safe_mode: boolean;
};

export async function startTestRun(projectId: string, payload: StartTestRunPayload) {
  const response = await api.post<{ test_run_id: string; status: string }>(`/projects/${projectId}/test-runs`, payload);
  return response.data;
}

export async function listTestRuns(projectId: string) {
  const response = await api.get<{ test_runs: TestRun[] }>(`/projects/${projectId}/test-runs`);
  return response.data.test_runs;
}

export async function getTestRun(testRunId: string) {
  const response = await api.get<TestRun>(`/test-runs/${testRunId}`);
  return response.data;
}

export async function stopTestRun(testRunId: string) {
  const response = await api.post<TestRun>(`/test-runs/${testRunId}/stop`);
  return response.data;
}

export function openTestRunEventsSocket(testRunId: string, onEvent: (event: TestRunEvent) => void) {
  const token = window.localStorage.getItem('bugswarm_token') ?? '';
  const baseUrl = new URL(api.defaults.baseURL ?? 'http://localhost:8000/api', window.location.origin);
  const wsProtocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsPath = baseUrl.pathname.replace(/\/api\/?$/, '');
  const socketUrl = `${wsProtocol}//${baseUrl.host}${wsPath}/ws/test-runs/${testRunId}?token=${encodeURIComponent(token)}`;
  const socket = new WebSocket(socketUrl);

  socket.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as TestRunEvent);
    } catch {
      onEvent({ event: 'message', test_run_id: testRunId, message: message.data });
    }
  };

  return socket;
}
