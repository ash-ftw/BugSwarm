import { api } from './client';

export type TestStep = {
  id: string;
  test_case_id: string;
  step_order: number;
  action_type: string;
  selector_hint: string | null;
  selector_resolved: string | null;
  input_value: string | null;
  expected_observation: string | null;
  timeout_ms: number | null;
  created_at: string;
};

export type TestCase = {
  id: string;
  project_id: string;
  test_run_id: string | null;
  name: string;
  description: string | null;
  source: string;
  priority: string;
  status: string;
  expected_result: string | null;
  ai_prompt_hash: string | null;
  created_at: string;
  steps: TestStep[];
};

export type LLMModelResponse = {
  id: string;
  reasoning_session_id: string;
  provider_key: string;
  model_name: string;
  status: string;
  confidence: number | null;
  vote: string | null;
  rationale_summary: string | null;
  output: Record<string, unknown> | null;
  error_message: string | null;
  latency_ms: number | null;
  token_usage: Record<string, unknown> | null;
  created_at: string;
};

export type LLMReasoningSession = {
  id: string;
  test_run_id: string | null;
  bug_id: string | null;
  task_type: string;
  prompt_fingerprint: string;
  consensus_status: string;
  consensus_mode: string;
  final_rationale: string | null;
  requires_human_review: boolean;
  session_metadata: Record<string, unknown> | null;
  created_at: string;
  model_responses: LLMModelResponse[];
};

export type TestCaseResponse = {
  test_cases: TestCase[];
  reasoning_sessions: LLMReasoningSession[];
};

export async function listTestCases(testRunId: string) {
  const response = await api.get<TestCaseResponse>(`/test-runs/${testRunId}/test-cases`);
  return response.data;
}
