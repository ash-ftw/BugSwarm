import {
  Activity,
  AlertTriangle,
  Bot,
  Bug,
  CircleStop,
  ChevronRight,
  Database,
  ExternalLink,
  FileJson,
  FlaskConical,
  KeyRound,
  LayoutDashboard,
  Play,
  Plus,
  Radio,
  RefreshCw,
  Save,
  Settings,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { getMe, login, register } from './services/auth';
import type { LoginPayload, User } from './services/auth';
import { createAuthProfile, deleteAuthProfile, updateAuthProfile } from './services/authProfiles';
import type { AuthProfile, AuthProfilePayload } from './services/authProfiles';
import {
  getBugArtifact,
  getBugValidationHistory,
  getPlaywrightScript,
  getReplayHistory,
  getRunReport,
  listBugs,
  replayBug,
  updateBug,
  validateBug,
} from './services/bugs';
import type { BugRecord } from './services/bugs';
import {
  createDemoProject,
  createProject,
  deleteProject,
  listProjects,
  updateProject,
} from './services/projects';
import type { Project, ProjectPayload } from './services/projects';
import { listTestCases } from './services/testCases';
import type { TestCaseResponse } from './services/testCases';
import {
  getTestRun,
  listTestRuns,
  openTestRunEventsSocket,
  startTestRun,
  stopTestRun,
} from './services/testRuns';
import type { StartTestRunPayload, TestRun, TestRunEvent } from './services/testRuns';
import { queueRetentionCleanup, useQueueAutoscaleStatus, useRetentionPolicy, useSystemConfig } from './services/system';
import type { ProviderStatus, QueueAutoscaleStatus } from './services/system';

const providers: ProviderStatus[] = [
  {
    provider_key: 'groq',
    model: 'qwen/qwen3-32b',
    configured: false,
    enabled: false,
    free_mode: true,
    status_label: 'Needs key',
  },
  {
    provider_key: 'gptoss',
    model: 'gpt-oss-20b',
    configured: true,
    enabled: true,
    free_mode: true,
    status_label: 'Local endpoint',
  },
  {
    provider_key: 'openrouter',
    model: 'openrouter/auto',
    configured: false,
    enabled: false,
    free_mode: true,
    status_label: 'Needs key',
  },
  {
    provider_key: 'gemini',
    model: 'gemini-2.0-flash-lite',
    configured: false,
    enabled: false,
    free_mode: true,
    status_label: 'Needs key',
  },
];

type AppView = 'dashboard' | 'projects' | 'create' | 'detail' | 'settings' | 'runs' | 'startRun' | 'runDetail' | 'bugs';

function App() {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(() => window.localStorage.getItem('bugswarm_token'));
  const [user, setUser] = useState<User | null>(() => {
    const stored = window.localStorage.getItem('bugswarm_user');
    return stored ? JSON.parse(stored) as User : null;
  });
  const [view, setView] = useState<AppView>('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [bugSeverityFilter, setBugSeverityFilter] = useState<string>('all');
  const { data: systemConfig } = useSystemConfig();
  const queueStatusQuery = useQueueAutoscaleStatus();
  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: getMe,
    enabled: Boolean(token) && !user,
    retry: false,
  });
  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: listProjects,
    enabled: Boolean(token),
  });
  const demoProjectMutation = useMutation({
    mutationFn: createDemoProject,
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setSelectedProjectId(project.id);
      setView('detail');
    },
  });

  useEffect(() => {
    if (meQuery.data) {
      setUser(meQuery.data);
      window.localStorage.setItem('bugswarm_user', JSON.stringify(meQuery.data));
    }
  }, [meQuery.data]);

  const projects = projectsQuery.data ?? [];
  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? projects[0] ?? null,
    [projects, selectedProjectId],
  );
  const testRunsQuery = useQuery({
    queryKey: ['test-runs', selectedProject?.id],
    queryFn: () => listTestRuns(selectedProject!.id),
    enabled: Boolean(token && selectedProject),
    refetchInterval: 5000,
  });
  const selectedRunQuery = useQuery({
    queryKey: ['test-run', selectedRunId],
    queryFn: () => getTestRun(selectedRunId!),
    enabled: Boolean(token && selectedRunId),
    refetchInterval: 3000,
  });
  const bugsQuery = useQuery({
    queryKey: ['bugs', selectedProject?.id, bugSeverityFilter],
    queryFn: () => listBugs(selectedProject!.id, { severity: bugSeverityFilter === 'all' ? undefined : bugSeverityFilter }),
    enabled: Boolean(token && selectedProject),
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (!selectedProjectId && projects[0]) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  useEffect(() => {
    setSelectedRunId(null);
  }, [selectedProject?.id]);

  function storeSession(nextToken: string, nextUser: User | null) {
    window.localStorage.setItem('bugswarm_token', nextToken);
    if (nextUser) {
      window.localStorage.setItem('bugswarm_user', JSON.stringify(nextUser));
      setUser(nextUser);
    } else {
      window.localStorage.removeItem('bugswarm_user');
      setUser(null);
    }
    setToken(nextToken);
  }

  function logout() {
    window.localStorage.removeItem('bugswarm_token');
    window.localStorage.removeItem('bugswarm_user');
    setToken(null);
    setUser(null);
    setSelectedProjectId(null);
    setSelectedRunId(null);
    queryClient.clear();
  }

  if (!token) {
    return <AuthScreen onAuthenticated={storeSession} />;
  }

  const testRuns = testRunsQuery.data ?? [];
  const projectBugs = bugsQuery.data ?? [];
  const selectedRun = selectedRunQuery.data ?? testRuns.find((run) => run.id === selectedRunId) ?? testRuns[0] ?? null;
  const dashboardRun = testRuns.find((run) => ['queued', 'running'].includes(run.status)) ?? testRuns[0] ?? null;
  const metrics = [
    { label: 'Projects', value: String(projects.length), detail: `${projects.filter((p) => p.status === 'active').length} active`, tone: 'neutral' },
    { label: 'Active runs', value: String(testRuns.filter((run) => ['queued', 'running'].includes(run.status)).length), detail: `${testRuns.length} total runs`, tone: 'running' },
    { label: 'Pages found', value: String(testRuns.reduce((total, run) => total + run.discovered_pages_count, 0)), detail: 'Stored from agents', tone: 'success' },
    { label: 'Open bugs', value: String(projectBugs.filter((bug) => bug.status === 'open').length), detail: `${projectBugs.length} total findings`, tone: 'danger' },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <div className="brand">
          <span className="brand-mark">B</span>
          <div>
            <strong>BugSwarm</strong>
            <span>QA command center</span>
          </div>
        </div>
        <nav>
          <button className={view === 'dashboard' ? 'active' : ''} onClick={() => setView('dashboard')}><LayoutDashboard size={18} />Dashboard</button>
          <button className={view === 'projects' ? 'active' : ''} onClick={() => setView('projects')}><FlaskConical size={18} />Projects</button>
          <button className={view === 'runs' || view === 'startRun' || view === 'runDetail' ? 'active' : ''} onClick={() => setView('runs')}><Activity size={18} />Test Runs</button>
          <button className={view === 'bugs' ? 'active' : ''} onClick={() => setView('bugs')}><Bug size={18} />Bugs</button>
          <button onClick={() => setView('bugs')}><FileJson size={18} />Reports</button>
          <button className={view === 'settings' ? 'active' : ''} onClick={() => setView('settings')}><Settings size={18} />Settings</button>
        </nav>
        <div className="sidebar-footer">
          <ShieldCheck size={18} />
          <span>Safe mode enabled</span>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Swarm monitor</p>
            <h1>{viewTitle(view)}</h1>
            <span className="user-line">{user?.name} / {user?.email}</span>
          </div>
          <div className="actions">
            <button className="icon-button" title="Refresh dashboard" aria-label="Refresh dashboard" onClick={() => projectsQuery.refetch()}>
              <RefreshCw size={18} />
            </button>
            <button className="secondary-action" onClick={logout}>
              Logout
            </button>
            <button className="primary-action" onClick={() => setView('create')}>
              <Plus size={18} /> New project
            </button>
          </div>
        </header>

        {view === 'dashboard' && (
          <DashboardView
            metrics={metrics}
            providers={systemConfig?.providers ?? providers}
            queueStatus={queueStatusQuery.data ?? null}
            queueStatusLoading={queueStatusQuery.isLoading}
            selectedProject={selectedProject}
            currentRun={dashboardRun}
            bugs={projectBugs.slice(0, 5)}
            onOpenProjects={() => setView('projects')}
            onStartRun={() => setView('startRun')}
          />
        )}
        {view === 'projects' && (
          <ProjectsView
            projects={projects}
            isLoading={projectsQuery.isLoading}
            isCreatingDemo={demoProjectMutation.isPending}
            onCreate={() => setView('create')}
            onCreateDemo={() => demoProjectMutation.mutate()}
            onSelect={(projectId) => {
              setSelectedProjectId(projectId);
              setView('detail');
            }}
          />
        )}
        {view === 'create' && (
          <ProjectForm
            onCancel={() => setView(projects.length ? 'projects' : 'dashboard')}
            onSaved={(project) => {
              setSelectedProjectId(project.id);
              setView('detail');
            }}
          />
        )}
        {view === 'detail' && selectedProject && (
          <ProjectDetail
            project={selectedProject}
            onEdit={() => setView('settings')}
            onDeleted={() => {
              setSelectedProjectId(null);
              setView('projects');
            }}
          />
        )}
        {view === 'settings' && selectedProject && (
          <ProjectSettings project={selectedProject} onSaved={() => setView('detail')} />
        )}
        {view === 'runs' && selectedProject && (
          <TestRunsView
            project={selectedProject}
            testRuns={testRuns}
            isLoading={testRunsQuery.isLoading}
            onStart={() => setView('startRun')}
            onOpen={(runId) => {
              setSelectedRunId(runId);
              setView('runDetail');
            }}
          />
        )}
        {view === 'startRun' && selectedProject && (
          <StartRunForm
            project={selectedProject}
            onCancel={() => setView('runs')}
            onStarted={(runId) => {
              setSelectedRunId(runId);
              setView('runDetail');
            }}
          />
        )}
        {view === 'runDetail' && selectedRun && (
          <RunMonitor
            run={selectedRun}
            onStop={() => selectedRun.id && stopTestRun(selectedRun.id).then((run) => queryClient.setQueryData(['test-run', selectedRun.id], run))}
          />
        )}
        {view === 'bugs' && selectedProject && (
          <BugsView
            project={selectedProject}
            bugs={projectBugs}
            isLoading={bugsQuery.isLoading}
            severityFilter={bugSeverityFilter}
            onSeverityFilter={setBugSeverityFilter}
            testRuns={testRuns}
          />
        )}
      </main>
    </div>
  );
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (token: string, user: User | null) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [error, setError] = useState<string | null>(null);
  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: (data) => onAuthenticated(data.token, data.user),
    onError: () => setError('Authentication failed. Check the email and password.'),
  });
  const registerMutation = useMutation({
    mutationFn: register,
    onSuccess: (data) => onAuthenticated(data.token, null),
    onError: () => setError('Registration failed. Use a valid email and a stronger password.'),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);
    const payload = {
      email: String(form.get('email') ?? ''),
      password: String(form.get('password') ?? ''),
    };
    if (mode === 'register') {
      registerMutation.mutate({ ...payload, name: String(form.get('name') ?? '') });
    } else {
      loginMutation.mutate(payload as LoginPayload);
    }
  }

  return (
    <div className="auth-shell">
      <section className="auth-panel">
        <div className="brand auth-brand">
          <span className="brand-mark">B</span>
          <div>
            <strong>BugSwarm</strong>
            <span>QA command center</span>
          </div>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <h1>{mode === 'login' ? 'Login' : 'Register'}</h1>
          {mode === 'register' && (
            <label>
              Name
              <input name="name" autoComplete="name" required minLength={2} />
            </label>
          )}
          <label>
            Email
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            Password
            <input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 8 : 1} />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-action full-width" type="submit" disabled={loginMutation.isPending || registerMutation.isPending}>
            {mode === 'login' ? 'Login' : 'Create account'}
          </button>
        </form>
        <button className="text-button" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Create an account' : 'Use existing account'}
        </button>
      </section>
    </div>
  );
}

function DashboardView({
  metrics,
  providers,
  queueStatus,
  queueStatusLoading,
  selectedProject,
  currentRun,
  bugs,
  onOpenProjects,
  onStartRun,
}: {
  metrics: { label: string; value: string; detail: string; tone: string }[];
  providers: ProviderStatus[];
  queueStatus: QueueAutoscaleStatus | null;
  queueStatusLoading: boolean;
  selectedProject: Project | null;
  currentRun: TestRun | null;
  bugs: BugRecord[];
  onOpenProjects: () => void;
  onStartRun: () => void;
}) {
  return (
    <>
      <section className="metric-grid" aria-label="Project metrics">
        {metrics.map((metric) => (
          <article className={`metric-card ${metric.tone}`} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
          </article>
        ))}
      </section>
      <section className="content-grid">
        <div className="panel wide">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Live execution</p>
              <h2>Agent activity</h2>
            </div>
            <button className="primary-action" onClick={onStartRun} disabled={!selectedProject}>
              <Play size={18} /> Start run
            </button>
          </div>
          <div className="agent-list">
            {!currentRun && <p className="empty-state">No swarm activity yet. Start a run to see live agents here.</p>}
            {currentRun?.agents.map((agent) => (
              <div className="agent-row" key={agent.id}>
                <div className="agent-type">
                  <Bot size={18} />
                  <div>
                    <strong>{agent.agent_type} Agent</strong>
                    <span>{agent.current_url ?? currentRun.name}</span>
                  </div>
                </div>
                <span className={`status ${agent.status}`}>{agent.status}</span>
                <span>{agent.viewport_width ?? '-'}px</span>
                <span>{agent.viewport_height ?? '-'}px</span>
                <ChevronRight size={18} />
              </div>
            ))}
          </div>
        </div>
        <ProviderPanel providers={providers} />
        <AutoscalePanel queueStatus={queueStatus} isLoading={queueStatusLoading} />
        <div className="panel wide">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Current target</p>
              <h2>{selectedProject?.name ?? 'No project selected'}</h2>
            </div>
            <button className="secondary-action" onClick={onOpenProjects}>
              <Database size={18} /> Projects
            </button>
          </div>
          {selectedProject ? (
            <div className="target-summary">
              <span>{selectedProject.base_url}</span>
              <span>{selectedProject.default_agent_count} agents</span>
              <span>{selectedProject.default_max_depth} depth</span>
              <span>{selectedProject.default_test_intensity} intensity</span>
            </div>
          ) : (
            <p className="empty-state">No projects yet. Add your first web application to start swarm testing.</p>
          )}
        </div>
        <BugQueue bugs={bugs} />
      </section>
    </>
  );
}

function AutoscalePanel({
  queueStatus,
  isLoading,
}: {
  queueStatus: QueueAutoscaleStatus | null;
  isLoading: boolean;
}) {
  const hasBacklog = (queueStatus?.total_pending_tasks ?? 0) > 0;

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Autoscaling</p>
          <h2>Worker queue</h2>
        </div>
        <Activity size={18} />
      </div>
      {isLoading && <p className="empty-state">Loading queue depth...</p>}
      {queueStatus && (
        <>
          <div className="autoscale-summary">
            <div>
              <strong>{queueStatus.total_pending_tasks}</strong>
              <span>pending tasks</span>
            </div>
            <span className={`status ${queueStatus.redis_connected ? (hasBacklog ? 'queued' : 'completed') : 'offline'}`}>
              {queueStatus.redis_connected ? queueStatus.scale_direction.replace(/_/g, ' ') : 'offline'}
            </span>
          </div>
          <div className="autoscale-grid">
            <span>
              Recommended
              <strong>{queueStatus.recommended_worker_replicas}</strong>
            </span>
            <span>
              Target
              <strong>{queueStatus.target_pending_tasks_per_replica}/pod</strong>
            </span>
            <span>
              Minimum
              <strong>{queueStatus.min_worker_replicas}</strong>
            </span>
            <span>
              Maximum
              <strong>{queueStatus.max_worker_replicas}</strong>
            </span>
          </div>
          <div className="queue-list">
            {queueStatus.queues.map((queue) => (
              <div className="queue-row" key={queue.name}>
                <span>{queue.name}</span>
                <strong>{queue.pending_tasks}</strong>
              </div>
            ))}
          </div>
          {queueStatus.error && <p className="form-error">{queueStatus.error}</p>}
        </>
      )}
    </div>
  );
}

function ProviderPanel({ providers }: { providers: ProviderStatus[] }) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Council</p>
          <h2>LLM providers</h2>
        </div>
        <Radio size={18} />
      </div>
      <div className="provider-list">
        {providers.map((provider) => (
          <div className="provider-row" key={provider.provider_key}>
            <div>
              <strong>{provider.provider_key}</strong>
              <span>{provider.model}</span>
            </div>
            <span className={provider.enabled ? 'ready' : 'needs-config'}>
              {provider.enabled ? 'Ready' : provider.status_label ?? 'Needs config'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BugQueue({ bugs }: { bugs: BugRecord[] }) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Latest findings</p>
          <h2>Bug queue</h2>
        </div>
        <AlertTriangle size={18} />
      </div>
      <div className="bug-table compact" role="table" aria-label="Latest bugs">
        {bugs.length === 0 && <p className="empty-state">No bugs recorded yet.</p>}
        {bugs.map((bug) => (
          <div className="bug-row" role="row" key={bug.title}>
            <span className={`severity ${bug.severity}`}>{bug.severity}</span>
            <strong>{bug.title}</strong>
            <span>{bug.affected_url ?? bug.category}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProjectsView({
  projects,
  isLoading,
  isCreatingDemo,
  onCreate,
  onCreateDemo,
  onSelect,
}: {
  projects: Project[];
  isLoading: boolean;
  isCreatingDemo: boolean;
  onCreate: () => void;
  onCreateDemo: () => void;
  onSelect: (projectId: string) => void;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Targets</p>
          <h2>Projects</h2>
        </div>
        <div className="actions">
          <button className="secondary-action" onClick={onCreateDemo} disabled={isCreatingDemo}>
            <FlaskConical size={18} /> Demo target
          </button>
          <button className="primary-action" onClick={onCreate}>
            <Plus size={18} /> Create project
          </button>
        </div>
      </div>
      {isLoading && <p className="empty-state">Loading projects...</p>}
      {!isLoading && projects.length === 0 && <p className="empty-state">No projects yet. Create one manually or load the BuggyShop demo target.</p>}
      <div className="project-grid">
        {projects.map((project) => (
          <article className="project-card" key={project.id}>
            <div>
              <span className={`status ${project.status}`}>{project.status}</span>
              <h3>{project.name}</h3>
              <p>{project.base_url}</p>
            </div>
            <div className="project-meta">
              <span>{project.default_agent_count} agents</span>
              <span>{project.default_max_depth} depth</span>
              <span>{project.scopes.length} scopes</span>
            </div>
            <button className="secondary-action" onClick={() => onSelect(project.id)}>
              Open <ChevronRight size={18} />
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function TestRunsView({
  project,
  testRuns,
  isLoading,
  onStart,
  onOpen,
}: {
  project: Project;
  testRuns: TestRun[];
  isLoading: boolean;
  onStart: () => void;
  onOpen: (runId: string) => void;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Run history</p>
          <h2>{project.name}</h2>
        </div>
        <button className="primary-action" onClick={onStart}>
          <Play size={18} /> Start run
        </button>
      </div>
      {isLoading && <p className="empty-state">Loading test runs...</p>}
      {!isLoading && testRuns.length === 0 && <p className="empty-state">No test runs yet. Start a swarm run to begin automated exploration.</p>}
      <div className="run-table">
        {testRuns.map((run) => (
          <button className="run-row" key={run.id} onClick={() => onOpen(run.id)}>
            <span className={`status ${run.status}`}>{run.status}</span>
            <strong>{run.name}</strong>
            <span>{run.agent_count} agents</span>
            <span>{run.discovered_pages_count} pages</span>
            <span>{run.agent_steps_count} steps</span>
            <ChevronRight size={18} />
          </button>
        ))}
      </div>
    </section>
  );
}

function StartRunForm({
  project,
  onCancel,
  onStarted,
}: {
  project: Project;
  onCancel: () => void;
  onStarted: (runId: string) => void;
}) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: StartTestRunPayload) => startTestRun(project.id, payload),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['test-runs', project.id] });
      onStarted(result.test_run_id);
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate(runPayloadFromForm(new FormData(event.currentTarget), project));
  }

  return (
    <section className="panel form-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Launch swarm</p>
          <h2>{project.name}</h2>
        </div>
      </div>
      <form className="project-form" onSubmit={submit}>
        <label>
          Run name
          <input name="name" defaultValue={`Exploration - ${new Date().toLocaleDateString()}`} required minLength={2} />
        </label>
        <label>
          Auth profile
          <select name="auth_profile_id" defaultValue="">
            <option value="">No target login</option>
            {project.auth_profiles.filter((profile) => profile.is_active).map((profile) => (
              <option value={profile.id} key={profile.id}>{profile.name}</option>
            ))}
          </select>
        </label>
        <div className="form-grid three">
          <label>
            Agent count
            <input name="agent_count" type="number" min={1} max={8} defaultValue={project.default_agent_count} />
          </label>
          <label>
            Max depth
            <input name="max_depth" type="number" min={1} max={10} defaultValue={project.default_max_depth} />
          </label>
          <label>
            Action limit
            <input name="max_actions" type="number" min={1} max={500} defaultValue={40} />
          </label>
        </div>
        <div className="form-grid three">
          <label>
            Duration minutes
            <input name="max_duration_minutes" type="number" min={1} max={240} defaultValue={30} />
          </label>
        </div>
        <div className="form-grid">
          <label>
            Intensity
            <select name="test_intensity" defaultValue={project.default_test_intensity}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <label>
            Consensus mode
            <select name="llm_consensus_mode" defaultValue={project.llm_consensus_mode}>
              <option value="majority_vote">Majority vote</option>
              <option value="strict_unanimous">Strict unanimous</option>
              <option value="rule_weighted">Rule weighted</option>
            </select>
          </label>
        </div>
        <fieldset className="checkbox-grid">
          <legend>Agent types</legend>
          {['explorer', 'form', 'navigation', 'chaos'].map((agentType) => (
            <label key={agentType}>
              <input name="agent_types" type="checkbox" value={agentType} defaultChecked />
              {agentType}
            </label>
          ))}
        </fieldset>
        <fieldset className="checkbox-grid">
          <legend>Viewports</legend>
          {['desktop', 'mobile', 'tablet'].map((viewport) => (
            <label key={viewport}>
              <input name="viewports" type="checkbox" value={viewport} defaultChecked={viewport === 'desktop'} />
              {viewport}
            </label>
          ))}
        </fieldset>
        <div className="toggle-row">
          <label>
            <input name="llm_council_enabled" type="checkbox" defaultChecked={project.llm_council_enabled} />
            LLM council
          </label>
          <label>
            <input name="safe_mode" type="checkbox" defaultChecked />
            Safe mode
          </label>
        </div>
        {mutation.isError && <p className="form-error">Could not start the run. Check that Redis and the backend are available.</p>}
        <div className="form-actions">
          <button className="secondary-action" type="button" onClick={onCancel}>Cancel</button>
          <button className="primary-action" type="submit" disabled={mutation.isPending}>
            <Play size={18} /> Queue swarm
          </button>
        </div>
      </form>
    </section>
  );
}

function RunMonitor({ run, onStop }: { run: TestRun; onStop: () => void }) {
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<TestRunEvent[]>([]);
  const [socketStatus, setSocketStatus] = useState<'connecting' | 'live' | 'offline'>('connecting');
  const progress = runProgress(run);
  const testCasesQuery = useQuery({
    queryKey: ['test-cases', run.id],
    queryFn: () => listTestCases(run.id),
    refetchInterval: ['queued', 'running'].includes(run.status) ? 5000 : false,
  });
  const testCaseData: TestCaseResponse = testCasesQuery.data ?? { test_cases: [], reasoning_sessions: [] };

  useEffect(() => {
    setEvents([]);
    setSocketStatus('connecting');
    const socket = openTestRunEventsSocket(run.id, (event) => {
      setEvents((current) => [event, ...current].slice(0, 80));
      if (event.event !== 'snapshot') {
        queryClient.invalidateQueries({ queryKey: ['test-run', run.id] });
        if (event.event.startsWith('ai_') || event.event === 'llm_consensus_completed') {
          queryClient.invalidateQueries({ queryKey: ['test-cases', run.id] });
        }
      }
    });
    socket.onopen = () => setSocketStatus('live');
    socket.onerror = () => setSocketStatus('offline');
    socket.onclose = () => setSocketStatus('offline');
    return () => socket.close();
  }, [queryClient, run.id]);

  return (
    <section className="content-grid">
      <div className="panel wide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Run monitor</p>
            <h2>{run.name}</h2>
          </div>
          <span className={`status ${socketStatus === 'live' ? 'running' : socketStatus === 'offline' ? 'offline' : 'queued'}`}>
            {socketStatus}
          </span>
          <button className="danger-action" onClick={onStop} disabled={!['queued', 'running'].includes(run.status)}>
            <CircleStop size={18} /> Stop
          </button>
        </div>
        <div className="detail-grid">
          <span>Status<strong>{run.status}</strong></span>
          <span>Agents<strong>{run.agent_count}</strong></span>
          <span>Pages<strong>{run.discovered_pages_count}</strong></span>
          <span>Steps<strong>{run.agent_steps_count}</strong></span>
          <span>Console logs<strong>{run.browser_logs_count}</strong></span>
          <span>Network logs<strong>{run.network_logs_count}</strong></span>
          <span>AI tests<strong>{run.test_cases_count}</strong></span>
        </div>
        <div className="run-progress" aria-label="Run progress">
          <div>
            <strong>{progress.completedAgents} of {run.agent_count} agents finished</strong>
            <span>{progress.label}</span>
          </div>
          <div className="progress-track">
            <span style={{ width: `${progress.percent}%` }} />
          </div>
        </div>
        <div className="agent-list">
          {run.agents.map((agent) => (
            <div className="agent-row" key={agent.id}>
              <div className="agent-type">
                <Bot size={18} />
                <div>
                  <strong>{agent.agent_type} Agent</strong>
                  <span>{agent.error_message ?? agent.current_url ?? 'Waiting for worker'}</span>
                </div>
              </div>
              <span className={`status ${agent.status}`}>{agent.status}</span>
              <span>{agent.viewport_width ?? '-'}px</span>
              <span>{agent.viewport_height ?? '-'}px</span>
              <ChevronRight size={18} />
            </div>
          ))}
        </div>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Visited URLs</p>
            <h2>Coverage</h2>
          </div>
        </div>
        <div className="page-list">
          {run.discovered_pages.length === 0 && <p className="empty-state">No pages discovered yet.</p>}
          {run.discovered_pages.map((page) => (
            <div className="page-row" key={page.id}>
              <strong>{page.title || page.url}</strong>
              <span>{page.url}</span>
              <small>{page.links_count ?? 0} links / {page.forms_count ?? 0} forms / {page.buttons_count ?? 0} buttons</small>
            </div>
          ))}
        </div>
      </div>
      <div className="panel wide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">AI generated</p>
            <h2>Test cases</h2>
          </div>
          <span className="status generated">{testCaseData.test_cases.length} cases</span>
        </div>
        <div className="test-case-list">
          {testCasesQuery.isLoading && <p className="empty-state">Loading generated tests...</p>}
          {!testCasesQuery.isLoading && testCaseData.test_cases.length === 0 && (
            <p className="empty-state">No AI-generated tests yet. They appear after agents discover suitable pages.</p>
          )}
          {testCaseData.test_cases.map((testCase) => (
            <article className="test-case-row" key={testCase.id}>
              <div>
                <span className={`status ${testCase.status}`}>{testCase.status}</span>
                <strong>{testCase.name}</strong>
                <small>{testCase.description || testCase.expected_result || 'Generated from page context'}</small>
              </div>
              <ol>
                {testCase.steps.slice(0, 4).map((step) => (
                  <li key={step.id}>
                    <span>{step.action_type}</span>
                    <small>{step.selector_hint ?? step.input_value ?? step.expected_observation ?? 'step'}</small>
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </div>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Reasoning council</p>
            <h2>Provider votes</h2>
          </div>
        </div>
        <div className="council-list">
          {testCaseData.reasoning_sessions.length === 0 && <p className="empty-state">No reasoning sessions yet.</p>}
          {testCaseData.reasoning_sessions.slice(0, 4).map((session) => (
            <div className="council-row" key={session.id}>
              <div>
                <span className={`status ${session.consensus_status}`}>{session.consensus_status.replace(/_/g, ' ')}</span>
                <strong>{session.final_rationale ?? 'Council result recorded'}</strong>
              </div>
              {session.model_responses.map((response) => (
                <small key={response.id}>
                  {response.provider_key}: {response.vote ?? response.status}
                  {typeof response.confidence === 'number' ? ` (${Math.round(response.confidence * 100)}%)` : ''}
                </small>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="panel wide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Live events</p>
            <h2>Activity feed</h2>
          </div>
        </div>
        <div className="event-feed">
          {events.length === 0 && <p className="empty-state">Waiting for agent events...</p>}
          {events.map((event, index) => (
            <div className="event-row" key={`${event.created_at ?? index}-${event.event}-${index}`}>
              <span className="event-kind">{event.event.replace(/_/g, ' ')}</span>
              <strong>{event.agent_type ? `${event.agent_type} agent` : event.status ?? 'run'}</strong>
              <small>{eventDetail(event)}</small>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function BugsView({
  project,
  bugs,
  isLoading,
  severityFilter,
  onSeverityFilter,
  testRuns,
}: {
  project: Project;
  bugs: BugRecord[];
  isLoading: boolean;
  severityFilter: string;
  onSeverityFilter: (severity: string) => void;
  testRuns: TestRun[];
}) {
  const queryClient = useQueryClient();
  const [selectedBugId, setSelectedBugId] = useState<string | null>(bugs[0]?.id ?? null);
  const [script, setScript] = useState<string>('');
  const selectedBug = bugs.find((bug) => bug.id === selectedBugId) ?? bugs[0] ?? null;
  const latestRun = testRuns[0] ?? null;
  const replayQuery = useQuery({
    queryKey: ['replay', selectedBug?.id],
    queryFn: () => getReplayHistory(selectedBug!.id),
    enabled: Boolean(selectedBug),
    refetchInterval: selectedBug ? 5000 : false,
  });
  const validationQuery = useQuery({
    queryKey: ['bug-validation', selectedBug?.id],
    queryFn: () => getBugValidationHistory(selectedBug!.id),
    enabled: Boolean(selectedBug),
    refetchInterval: selectedBug ? 5000 : false,
  });
  const updateMutation = useMutation({
    mutationFn: ({ bugId, status }: { bugId: string; status: string }) => updateBug(bugId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bugs', project.id] }),
  });
  const replayMutation = useMutation({
    mutationFn: (bugId: string) => replayBug(bugId),
    onSuccess: (_, bugId) => {
      queryClient.invalidateQueries({ queryKey: ['replay', bugId] });
    },
  });
  const validationMutation = useMutation({
    mutationFn: (bugId: string) => validateBug(bugId),
    onSuccess: (_, bugId) => {
      queryClient.invalidateQueries({ queryKey: ['bug-validation', bugId] });
      queryClient.invalidateQueries({ queryKey: ['bugs', project.id] });
    },
  });

  useEffect(() => {
    if (!selectedBugId && bugs[0]) {
      setSelectedBugId(bugs[0].id);
    }
  }, [bugs, selectedBugId]);

  useEffect(() => {
    setScript('');
  }, [selectedBug?.id]);

  async function exportReport(format: 'json' | 'markdown') {
    if (!latestRun) return;
    const content = await getRunReport(latestRun.id, format);
    const extension = format === 'json' ? 'json' : 'md';
    downloadText(`bugswarm-${latestRun.id}.${extension}`, content, format === 'json' ? 'application/json' : 'text/markdown');
  }

  async function openArtifact(artifactId: string, label: string) {
    const blob = await getBugArtifact(artifactId);
    const url = window.URL.createObjectURL(blob);
    window.open(url, label, 'noopener,noreferrer');
  }

  async function generateScript(bugId: string) {
    setScript(await getPlaywrightScript(bugId));
  }

  async function copyScript() {
    if (script) {
      await navigator.clipboard.writeText(script);
    }
  }

  return (
    <section className="content-grid">
      <div className="panel wide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Bug triage</p>
            <h2>{project.name}</h2>
          </div>
          <div className="actions">
            <select className="compact-select" value={severityFilter} onChange={(event) => onSeverityFilter(event.target.value)}>
              <option value="all">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <button className="secondary-action" disabled={!latestRun} onClick={() => exportReport('markdown')}>
              <FileJson size={18} /> Markdown
            </button>
            <button className="secondary-action" disabled={!latestRun} onClick={() => exportReport('json')}>
              <FileJson size={18} /> JSON
            </button>
          </div>
        </div>
        {isLoading && <p className="empty-state">Loading bugs...</p>}
        {!isLoading && bugs.length === 0 && <p className="empty-state">No bugs have been detected for this project.</p>}
        <div className="bug-list">
          {bugs.map((bug) => (
            <button
              className={`bug-list-row ${selectedBug?.id === bug.id ? 'active' : ''}`}
              key={bug.id}
              onClick={() => setSelectedBugId(bug.id)}
            >
              <span className={`severity ${bug.severity}`}>{bug.severity}</span>
              <strong>{bug.title}</strong>
              <span>{bug.category.replace(/_/g, ' ')}</span>
              <small>{bug.affected_url ?? 'No URL recorded'}</small>
              <span className={`status ${bug.status}`}>{bug.status}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Bug detail</p>
            <h2>{selectedBug?.title ?? 'Select a bug'}</h2>
          </div>
        </div>
        {selectedBug ? (
          <div className="bug-detail">
            <div className="detail-grid single">
              <span>Status<strong>{selectedBug.status}</strong></span>
              <span>Category<strong>{selectedBug.category.replace(/_/g, ' ')}</strong></span>
              <span>URL<strong>{selectedBug.affected_url ?? '-'}</strong></span>
            </div>
            <label>
              Status
              <select
                value={selectedBug.status}
                onChange={(event) => updateMutation.mutate({ bugId: selectedBug.id, status: event.target.value })}
              >
                <option value="open">Open</option>
                <option value="triaged">Triaged</option>
                <option value="resolved">Resolved</option>
                <option value="ignored">Ignored</option>
              </select>
            </label>
            <div className="evidence-block">
              <strong>AI validation</strong>
              <div className="actions left">
                <button className="secondary-action" onClick={() => validationMutation.mutate(selectedBug.id)} disabled={validationMutation.isPending}>
                  <Radio size={18} /> Validate
                </button>
                {selectedBug.ai_consensus_status && <span className={`status ${selectedBug.ai_consensus_status}`}>{selectedBug.ai_consensus_status.replace(/_/g, ' ')}</span>}
                {typeof selectedBug.ai_confidence === 'number' && <span className="confidence-pill">{Math.round(selectedBug.ai_confidence * 100)}%</span>}
              </div>
              <p>{selectedBug.ai_summary ?? 'No AI validation summary yet.'}</p>
              {selectedBug.suggested_fix && <p>Suggested fix: {selectedBug.suggested_fix}</p>}
              {validationQuery.data?.sessions.slice(0, 2).map((session) => (
                <div className="attempt-row" key={session.id}>
                  <span className={`status ${session.consensus_status}`}>{session.consensus_status.replace(/_/g, ' ')}</span>
                  <small>{session.final_rationale ?? 'Council result recorded'}</small>
                  {session.model_responses.map((response) => (
                    <p key={response.id}>
                      {response.provider_key}: {response.vote ?? response.status}
                      {typeof response.confidence === 'number' ? ` (${Math.round(response.confidence * 100)}%)` : ''}
                    </p>
                  ))}
                </div>
              ))}
            </div>
            <div className="evidence-block">
              <strong>Expected</strong>
              <p>{selectedBug.expected_result ?? 'Not recorded'}</p>
              <strong>Actual</strong>
              <p>{selectedBug.actual_result ?? 'Not recorded'}</p>
            </div>
            <div className="evidence-block">
              <strong>Artifacts</strong>
              {selectedBug.artifacts.length === 0 && <p>No artifacts recorded.</p>}
              {selectedBug.artifacts.map((artifact) => (
                <button className="text-button inline" key={artifact.id} onClick={() => openArtifact(artifact.id, artifact.label ?? artifact.artifact_type)}>
                  {artifact.label ?? artifact.artifact_type}
                </button>
              ))}
            </div>
            <div className="evidence-block">
              <strong>Replay</strong>
              <div className="actions left">
                <button className="secondary-action" onClick={() => replayMutation.mutate(selectedBug.id)} disabled={replayMutation.isPending}>
                  <Play size={18} /> Replay
                </button>
                <button className="secondary-action" onClick={() => generateScript(selectedBug.id)}>
                  <FileJson size={18} /> Generate script
                </button>
                <button className="secondary-action" onClick={copyScript} disabled={!script}>
                  Copy script
                </button>
              </div>
              {script && <pre className="script-preview">{script}</pre>}
            </div>
            <div className="evidence-block">
              <strong>Replay steps</strong>
              {selectedBug.replay_steps.length === 0 && <p>No replay steps recorded.</p>}
              {selectedBug.replay_steps.map((step) => (
                <p key={step.id}>{step.step_order}. {step.action_type} {step.url ?? step.selector ?? ''}</p>
              ))}
            </div>
            <div className="evidence-block">
              <strong>Replay attempts</strong>
              {replayQuery.data?.attempts.length === 0 && <p>No replay attempts yet.</p>}
              {replayQuery.data?.attempts.map((attempt) => (
                <div className="attempt-row" key={attempt.report_id ?? attempt.generated_at ?? attempt.status}>
                  <span className={`status ${attempt.status}`}>{attempt.status}</span>
                  <small>{attempt.duration_ms ?? 0} ms</small>
                  {attempt.steps?.slice(0, 4).map((step) => (
                    <p key={`${attempt.report_id}-${step.step_order}`}>
                      {step.step_order}. {step.action_type} {step.status}
                    </p>
                  ))}
                </div>
              ))}
            </div>
            <div className="evidence-block">
              <strong>Logs</strong>
              {[...selectedBug.browser_logs, ...selectedBug.network_logs].length === 0 && <p>No linked logs recorded.</p>}
              {selectedBug.browser_logs.map((log) => (
                <p key={log.id}>{log.log_level}: {log.message}</p>
              ))}
              {selectedBug.network_logs.map((log) => (
                <p key={log.id}>{log.status_code ?? 'failed'}: {log.request_url}</p>
              ))}
            </div>
          </div>
        ) : (
          <p className="empty-state">Select a finding from the list.</p>
        )}
      </div>
    </section>
  );
}

function ProjectForm({ onCancel, onSaved }: { onCancel: () => void; onSaved: (project: Project) => void }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      onSaved(project);
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = projectPayloadFromForm(new FormData(event.currentTarget));
    mutation.mutate(payload);
  }

  return (
    <section className="panel form-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Target setup</p>
          <h2>Create project</h2>
        </div>
      </div>
      <form className="project-form" onSubmit={submit}>
        <ProjectFields />
        {mutation.isError && <p className="form-error">Project creation failed. Check the base URL and scope values.</p>}
        <div className="form-actions">
          <button className="secondary-action" type="button" onClick={onCancel}>Cancel</button>
          <button className="primary-action" type="submit" disabled={mutation.isPending}>
            <Save size={18} /> Save project
          </button>
        </div>
      </form>
    </section>
  );
}

function ProjectDetail({ project, onEdit, onDeleted }: { project: Project; onEdit: () => void; onDeleted: () => void }) {
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: () => deleteProject(project.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      onDeleted();
    },
  });
  const allowed = project.scopes.filter((scope) => scope.scope_type === 'allow');
  const excluded = project.scopes.filter((scope) => scope.scope_type === 'exclude');

  return (
    <section className="content-grid">
      <div className="panel wide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Project detail</p>
            <h2>{project.name}</h2>
          </div>
          <div className="actions">
            <a className="secondary-action" href={project.base_url} target="_blank" rel="noreferrer">
              <ExternalLink size={18} /> Open target
            </a>
            <button className="primary-action" onClick={onEdit}>
              <Settings size={18} /> Settings
            </button>
          </div>
        </div>
        <div className="detail-grid">
          <span>Base URL<strong>{project.base_url}</strong></span>
          <span>Status<strong>{project.status}</strong></span>
          <span>Agent count<strong>{project.default_agent_count}</strong></span>
          <span>Max depth<strong>{project.default_max_depth}</strong></span>
          <span>Intensity<strong>{project.default_test_intensity}</strong></span>
          <span>Consensus<strong>{project.llm_consensus_mode}</strong></span>
        </div>
        <p className="description-text">{project.description || 'No description added.'}</p>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Scope</p>
            <h2>Rules</h2>
          </div>
        </div>
        <ScopeList title="Allowed" scopes={allowed} />
        <ScopeList title="Excluded" scopes={excluded} />
      </div>
      <div className="panel wide">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Council</p>
            <h2>Project providers</h2>
          </div>
        </div>
        <div className="provider-list">
          {project.llm_provider_configs.map((provider) => (
            <div className="provider-row" key={provider.id}>
              <div>
                <strong>{provider.provider_key}</strong>
                <span>{provider.model_name}</span>
              </div>
              <span className={provider.is_enabled ? 'ready' : 'needs-config'}>
                {provider.is_enabled ? 'Ready' : 'Disabled'}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="panel danger-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Project</p>
            <h2>Delete</h2>
          </div>
        </div>
        <button className="danger-action" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
          <Trash2 size={18} /> Delete project
        </button>
      </div>
    </section>
  );
}

function ProjectSettings({ project, onSaved }: { project: Project; onSaved: () => void }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (payload: ProjectPayload) => updateProject(project.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      onSaved();
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate(projectPayloadFromForm(new FormData(event.currentTarget)));
  }

  return (
    <section className="content-grid">
      <div className="panel form-panel wide">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Project settings</p>
          <h2>{project.name}</h2>
        </div>
      </div>
      <form className="project-form" onSubmit={submit}>
        <ProjectFields project={project} />
        {mutation.isError && <p className="form-error">Project update failed.</p>}
        <div className="form-actions">
          <button className="primary-action" type="submit" disabled={mutation.isPending}>
            <Save size={18} /> Save settings
          </button>
        </div>
      </form>
      </div>
      <AuthProfilesPanel project={project} />
      <RetentionPanel />
    </section>
  );
}

function AuthProfilesPanel({ project }: { project: Project }) {
  const queryClient = useQueryClient();
  const createMutation = useMutation({
    mutationFn: (payload: AuthProfilePayload) => createAuthProfile(project.id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  });
  const updateMutation = useMutation({
    mutationFn: ({ profile, payload }: { profile: AuthProfile; payload: Partial<AuthProfilePayload> }) =>
      updateAuthProfile(profile.id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteAuthProfile,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    createMutation.mutate(authProfilePayloadFromForm(new FormData(form)), {
      onSuccess: () => form.reset(),
    });
  }

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Target login</p>
          <h2>Auth profiles</h2>
        </div>
        <KeyRound size={18} />
      </div>
      <div className="auth-profile-list">
        {project.auth_profiles.length === 0 && <p className="empty-state">No target auth profiles configured.</p>}
        {project.auth_profiles.map((profile) => (
          <div className="auth-profile-row" key={profile.id}>
            <div>
              <span className={`status ${profile.is_active ? 'completed' : 'disabled'}`}>{profile.is_active ? 'active' : 'disabled'}</span>
              <strong>{profile.name}</strong>
              <small>{profile.auth_type === 'form' ? profile.login_url ?? 'No login URL' : profile.storage_state_path ?? 'No storage state'}</small>
              <small>{profile.password_configured ? 'Password saved' : 'No password saved'}</small>
            </div>
            <div className="actions left">
              <button
                className="secondary-action"
                onClick={() => updateMutation.mutate({ profile, payload: { is_active: !profile.is_active } })}
                disabled={updateMutation.isPending}
              >
                {profile.is_active ? 'Disable' : 'Enable'}
              </button>
              <button className="danger-action" onClick={() => deleteMutation.mutate(profile.id)} disabled={deleteMutation.isPending}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
      <form className="auth-profile-form" onSubmit={submit}>
        <label>
          Profile name
          <input name="name" defaultValue="Staging login" required minLength={2} />
        </label>
        <label>
          Login URL
          <input name="login_url" type="url" defaultValue={`${project.base_url}/login`} />
        </label>
        <div className="form-grid">
          <label>
            Username selector
            <input name="username_selector" defaultValue={'input[name="email"]'} />
          </label>
          <label>
            Password selector
            <input name="password_selector" defaultValue={'input[name="password"]'} />
          </label>
        </div>
        <label>
          Submit selector
          <input name="submit_selector" defaultValue={'button[type="submit"]'} />
        </label>
        <div className="form-grid">
          <label>
            Username
            <input name="username_value" autoComplete="off" />
          </label>
          <label>
            Password
            <input name="password_value" type="password" autoComplete="new-password" />
          </label>
        </div>
        <label>
          Storage state path
          <input name="storage_state_path" placeholder="/app/storage/traces/run/agent/auth-state.json" />
        </label>
        <div className="toggle-row">
          <label>
            <input name="is_active" type="checkbox" defaultChecked />
            Active
          </label>
        </div>
        {createMutation.isError && <p className="form-error">Auth profile creation failed. Keep login URLs on the project host.</p>}
        <div className="form-actions">
          <button className="primary-action" type="submit" disabled={createMutation.isPending}>
            <Save size={18} /> Add auth profile
          </button>
        </div>
      </form>
    </div>
  );
}

function RetentionPanel() {
  const retentionQuery = useRetentionPolicy();
  const cleanupMutation = useMutation({
    mutationFn: (dryRun: boolean) => queueRetentionCleanup(dryRun),
  });
  const policy = retentionQuery.data;

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Storage</p>
          <h2>Retention</h2>
        </div>
        <RefreshCw size={18} />
      </div>
      {retentionQuery.isLoading && <p className="empty-state">Loading retention policy...</p>}
      {policy && (
        <div className="retention-grid">
          <span>Screenshots<strong>{policy.screenshot_days}d</strong></span>
          <span>Traces<strong>{policy.trace_days}d</strong></span>
          <span>Reports<strong>{policy.report_days}d</strong></span>
          <span>Console logs<strong>{policy.browser_log_days}d</strong></span>
          <span>Network logs<strong>{policy.network_log_days}d</strong></span>
        </div>
      )}
      {cleanupMutation.data && (
        <p className="empty-state">Cleanup queued: {cleanupMutation.data.task_id ?? 'worker task'}.</p>
      )}
      {cleanupMutation.isError && (
        <p className="form-error">Retention cleanup could not be queued. Check Redis and the worker.</p>
      )}
      <div className="form-actions">
        <button className="secondary-action" onClick={() => cleanupMutation.mutate(true)} disabled={cleanupMutation.isPending}>
          Dry run
        </button>
        <button className="danger-action" onClick={() => cleanupMutation.mutate(false)} disabled={cleanupMutation.isPending}>
          Clean now
        </button>
      </div>
    </div>
  );
}

function ProjectFields({ project }: { project?: Project }) {
  const allowed = project?.scopes.filter((scope) => scope.scope_type === 'allow').map((scope) => scope.pattern).join('\n') ?? '';
  const excluded = project?.scopes.filter((scope) => scope.scope_type === 'exclude').map((scope) => scope.pattern).join('\n') ?? '';
  return (
    <>
      <div className="form-grid">
        <label>
          Project name
          <input name="name" defaultValue={project?.name ?? ''} required minLength={2} />
        </label>
        <label>
          Base URL
          <input name="base_url" type="url" defaultValue={project?.base_url ?? ''} required placeholder="https://example.com" />
        </label>
      </div>
      <label>
        Description
        <textarea name="description" defaultValue={project?.description ?? ''} rows={3} />
      </label>
      <div className="form-grid three">
        <label>
          Agent count
          <input name="default_agent_count" type="number" min={1} max={8} defaultValue={project?.default_agent_count ?? 3} />
        </label>
        <label>
          Max depth
          <input name="default_max_depth" type="number" min={1} max={10} defaultValue={project?.default_max_depth ?? 3} />
        </label>
        <label>
          Intensity
          <select name="default_test_intensity" defaultValue={project?.default_test_intensity ?? 'medium'}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
      </div>
      <div className="form-grid">
        <label>
          Allowed paths
          <textarea name="allowed_paths" defaultValue={allowed} rows={4} placeholder="/app/*" />
        </label>
        <label>
          Excluded paths
          <textarea name="excluded_paths" defaultValue={excluded} rows={4} placeholder="/admin/*" />
        </label>
      </div>
      <div className="toggle-row">
        <label>
          <input name="llm_council_enabled" type="checkbox" defaultChecked={project?.llm_council_enabled ?? true} />
          LLM council
        </label>
        <label>
          <input name="free_ai_mode" type="checkbox" defaultChecked={project?.free_ai_mode ?? true} />
          Free AI mode
        </label>
      </div>
      <input type="hidden" name="llm_consensus_mode" value={project?.llm_consensus_mode ?? 'majority_vote'} />
    </>
  );
}

function ScopeList({ title, scopes }: { title: string; scopes: { id: string; pattern: string }[] }) {
  return (
    <div className="scope-list">
      <strong>{title}</strong>
      {scopes.length === 0 ? <span>None</span> : scopes.map((scope) => <span key={scope.id}>{scope.pattern}</span>)}
    </div>
  );
}

function projectPayloadFromForm(form: FormData): ProjectPayload {
  return {
    name: String(form.get('name') ?? ''),
    description: String(form.get('description') ?? '') || null,
    base_url: String(form.get('base_url') ?? ''),
    default_agent_count: Number(form.get('default_agent_count') ?? 3),
    default_max_depth: Number(form.get('default_max_depth') ?? 3),
    default_test_intensity: String(form.get('default_test_intensity') ?? 'medium') as ProjectPayload['default_test_intensity'],
    llm_council_enabled: form.get('llm_council_enabled') === 'on',
    llm_consensus_mode: String(form.get('llm_consensus_mode') ?? 'majority_vote') as ProjectPayload['llm_consensus_mode'],
    free_ai_mode: form.get('free_ai_mode') === 'on',
    allowed_paths: splitPatterns(String(form.get('allowed_paths') ?? '')),
    excluded_paths: splitPatterns(String(form.get('excluded_paths') ?? '')),
  };
}

function runPayloadFromForm(form: FormData, project: Project): StartTestRunPayload {
  const agentTypes = form.getAll('agent_types').map(String);
  const viewports = form.getAll('viewports').map(String);
  return {
    name: String(form.get('name') ?? ''),
    agent_count: Number(form.get('agent_count') ?? project.default_agent_count),
    max_depth: Number(form.get('max_depth') ?? project.default_max_depth),
    max_actions: Number(form.get('max_actions') ?? 40),
    max_duration_minutes: Number(form.get('max_duration_minutes') ?? 30),
    test_intensity: String(form.get('test_intensity') ?? project.default_test_intensity) as StartTestRunPayload['test_intensity'],
    agent_types: agentTypes.length ? agentTypes : ['explorer'],
    viewports: viewports.length ? viewports : ['desktop'],
    llm_council_enabled: form.get('llm_council_enabled') === 'on',
    llm_providers: ['groq', 'gptoss', 'gemini', 'openrouter'],
    llm_consensus_mode: String(form.get('llm_consensus_mode') ?? project.llm_consensus_mode) as StartTestRunPayload['llm_consensus_mode'],
    auth_profile_id: String(form.get('auth_profile_id') ?? '') || null,
    safe_mode: form.get('safe_mode') === 'on',
  };
}

function authProfilePayloadFromForm(form: FormData): AuthProfilePayload {
  return {
    name: String(form.get('name') ?? ''),
    auth_type: String(form.get('storage_state_path') ?? '').trim() ? 'storage_state' : 'form',
    login_url: String(form.get('login_url') ?? '') || null,
    username_selector: String(form.get('username_selector') ?? '') || null,
    password_selector: String(form.get('password_selector') ?? '') || null,
    submit_selector: String(form.get('submit_selector') ?? '') || null,
    username_value: String(form.get('username_value') ?? '') || null,
    password_value: String(form.get('password_value') ?? '') || null,
    storage_state_path: String(form.get('storage_state_path') ?? '') || null,
    is_active: form.get('is_active') === 'on',
  };
}

function splitPatterns(value: string) {
  return value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
}

function downloadText(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}

function runProgress(run: TestRun) {
  const terminalStatuses = new Set(['completed', 'failed', 'cancelled']);
  const completedAgents = run.agents.filter((agent) => terminalStatuses.has(agent.status)).length;
  const maxActions = Number(run.summary?.max_actions ?? 0);
  const actionTotal = maxActions > 0 ? maxActions * Math.max(run.agent_count, 1) : 0;
  const stepPercent = actionTotal > 0 ? Math.min(100, Math.round((run.agent_steps_count / actionTotal) * 100)) : 0;
  const agentPercent = run.agent_count > 0 ? Math.round((completedAgents / run.agent_count) * 100) : 0;
  const percent = terminalStatuses.has(run.status) ? 100 : Math.max(stepPercent, agentPercent);
  const statusCounts = run.summary?.progress && typeof run.summary.progress === 'object'
    ? (run.summary.progress as { status_counts?: Record<string, number> }).status_counts
    : null;
  const label = statusCounts
    ? Object.entries(statusCounts).map(([status, count]) => `${count} ${status}`).join(' / ')
    : `${run.discovered_pages_count} pages / ${run.agent_steps_count} steps`;
  return { completedAgents, percent, label };
}

function eventDetail(event: TestRunEvent) {
  if (event.url) return event.url;
  if (event.current_url) return event.current_url;
  if (event.message) return event.message;
  if (event.target) return event.target;
  if (event.title) return event.title;
  if (event.end_reason) return event.end_reason.replace(/_/g, ' ');
  if (typeof event.test_cases_created === 'number') return `${event.test_cases_created} test cases`;
  if (typeof event.agent_progress_percent === 'number') return `${event.agent_progress_percent}% complete`;
  if (event.progress?.steps_completed !== undefined) return `${event.progress.steps_completed} steps`;
  return 'status update';
}

function viewTitle(view: AppView) {
  switch (view) {
    case 'projects':
      return 'Projects';
    case 'create':
      return 'Create project';
    case 'detail':
      return 'Project detail';
    case 'settings':
      return 'Project settings';
    case 'runs':
      return 'Test runs';
    case 'startRun':
      return 'Start test run';
    case 'runDetail':
      return 'Run monitor';
    case 'bugs':
      return 'Bugs and reports';
    default:
      return 'Testing health overview';
  }
}

export default App;
