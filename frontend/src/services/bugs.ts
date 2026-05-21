import { api } from './client';

export type BugArtifact = {
  id: string;
  bug_id: string;
  artifact_type: string;
  file_path: string;
  mime_type: string | null;
  file_size_bytes: number | null;
  label: string | null;
  created_at: string;
};

export type ReplayStep = {
  id: string;
  bug_id: string;
  step_order: number;
  action_type: string;
  selector: string | null;
  selector_hint: string | null;
  input_value: string | null;
  url: string | null;
  expected_result: string | null;
  created_at: string;
};

export type EvidenceLog = {
  id: string;
  log_level?: string | null;
  message?: string | null;
  source_url?: string | null;
  request_url?: string;
  method?: string | null;
  status_code?: number | null;
  resource_type?: string | null;
  failure_text?: string | null;
  duration_ms?: number | null;
  created_at: string;
};

export type BugRecord = {
  id: string;
  project_id: string;
  test_run_id: string | null;
  agent_id: string | null;
  test_case_id: string | null;
  title: string;
  description: string | null;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | string;
  status: 'open' | 'triaged' | 'resolved' | 'ignored' | string;
  affected_url: string | null;
  expected_result: string | null;
  actual_result: string | null;
  ai_summary: string | null;
  suggested_fix: string | null;
  ai_consensus_status: string | null;
  ai_confidence: number | null;
  reasoning_session_id: string | null;
  fingerprint: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  artifacts: BugArtifact[];
  replay_steps: ReplayStep[];
  browser_logs: EvidenceLog[];
  network_logs: EvidenceLog[];
};

export type BugListResponse = {
  bugs: BugRecord[];
};

export type ReplayAttempt = {
  report_id?: string;
  generated_at?: string;
  bug_id: string;
  status: string;
  duration_ms?: number;
  steps?: Array<{
    step_order: number;
    action_type: string;
    target: string | null;
    status: string;
    message: string | null;
    screenshot_path: string | null;
    duration_ms: number;
  }>;
};

export type ReplayHistory = {
  bug_id: string;
  replay_steps: ReplayStep[];
  attempts: ReplayAttempt[];
};

export type BugValidationSession = {
  id: string;
  consensus_status: string;
  final_rationale: string | null;
  requires_human_review: boolean;
  metadata: Record<string, unknown> | null;
  created_at: string;
  model_responses: Array<{
    id: string;
    provider_key: string;
    model_name: string;
    status: string;
    confidence: number | null;
    vote: string | null;
    rationale_summary: string | null;
    output: Record<string, unknown> | null;
    error_message: string | null;
    latency_ms: number | null;
    created_at: string;
  }>;
};

export type BugValidationHistory = {
  bug_id: string;
  sessions: BugValidationSession[];
};

export async function listBugs(projectId: string, filters: { severity?: string; status?: string } = {}) {
  const response = await api.get<BugListResponse>(`/projects/${projectId}/bugs`, { params: filters });
  return response.data.bugs;
}

export async function getBug(bugId: string) {
  const response = await api.get<BugRecord>(`/bugs/${bugId}`);
  return response.data;
}

export async function updateBug(bugId: string, payload: { status?: string; severity?: string }) {
  const response = await api.patch<BugRecord>(`/bugs/${bugId}`, payload);
  return response.data;
}

export async function getReplayHistory(bugId: string) {
  const response = await api.get<ReplayHistory>(`/bugs/${bugId}/replay`);
  return response.data;
}

export async function replayBug(bugId: string) {
  const response = await api.post<{ bug_id: string; status: string; task_id: string | null }>(`/bugs/${bugId}/replay`);
  return response.data;
}

export async function validateBug(bugId: string) {
  const response = await api.post<{ bug_id: string; status: string; task_id: string | null }>(`/bugs/${bugId}/validate`);
  return response.data;
}

export async function getBugValidationHistory(bugId: string) {
  const response = await api.get<BugValidationHistory>(`/bugs/${bugId}/validation`);
  return response.data;
}

export async function getPlaywrightScript(bugId: string) {
  const response = await api.get<{ bug_id: string; script: string }>(`/bugs/${bugId}/playwright-script`);
  return response.data.script;
}

export async function getRunReport(testRunId: string, format: 'json' | 'markdown') {
  const response = await api.get(`/test-runs/${testRunId}/report`, { params: { format }, responseType: 'text' });
  return response.data as string;
}

export async function getBugArtifact(artifactId: string) {
  const response = await api.get<Blob>(`/bug-artifacts/${artifactId}`, { responseType: 'blob' });
  return response.data;
}
