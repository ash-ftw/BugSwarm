import {
  Activity,
  AlertTriangle,
  Bot,
  Bug,
  ChevronRight,
  Database,
  ExternalLink,
  FileJson,
  FlaskConical,
  Gauge,
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
import type { LoginPayload, RegisterPayload, User } from './services/auth';
import {
  createProject,
  deleteProject,
  listProjects,
  updateProject,
} from './services/projects';
import type { Project, ProjectPayload } from './services/projects';
import { useSystemConfig } from './services/system';
import type { ProviderStatus } from './services/system';

const agents = [
  { type: 'Explorer', status: 'Running', url: '/products', steps: 42, bugs: 4 },
  { type: 'Form', status: 'Queued', url: '/login', steps: 0, bugs: 0 },
  { type: 'Navigation', status: 'Running', url: '/cart', steps: 27, bugs: 2 },
  { type: 'Chaos', status: 'Paused', url: '/checkout', steps: 18, bugs: 3 },
];

const bugs = [
  { severity: 'critical', title: 'Checkout crashes with empty cart', category: 'page_crash', url: '/checkout' },
  { severity: 'high', title: 'Broken product details link', category: 'broken_link', url: '/products/42' },
  { severity: 'medium', title: 'Invalid email accepted on registration', category: 'form_validation', url: '/register' },
  { severity: 'low', title: 'Mobile product cards overlap', category: 'visual_regression', url: '/products' },
];

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
    provider_key: 'gemini',
    model: 'gemini-2.0-flash-lite',
    configured: false,
    enabled: false,
    free_mode: true,
    status_label: 'Needs key',
  },
];

type AppView = 'dashboard' | 'projects' | 'create' | 'detail' | 'settings';

function App() {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(() => window.localStorage.getItem('bugswarm_token'));
  const [user, setUser] = useState<User | null>(() => {
    const stored = window.localStorage.getItem('bugswarm_user');
    return stored ? JSON.parse(stored) as User : null;
  });
  const [view, setView] = useState<AppView>('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const { data: systemConfig } = useSystemConfig();
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

  useEffect(() => {
    if (!selectedProjectId && projects[0]) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

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
    queryClient.clear();
  }

  if (!token) {
    return <AuthScreen onAuthenticated={storeSession} />;
  }

  const metrics = [
    { label: 'Projects', value: String(projects.length), detail: `${projects.filter((p) => p.status === 'active').length} active`, tone: 'neutral' },
    { label: 'Active runs', value: '0', detail: 'Run engine pending', tone: 'running' },
    { label: 'Open bugs', value: '0', detail: 'Bug APIs start in Phase 6', tone: 'danger' },
    { label: 'Replay ready', value: '0', detail: 'Replay starts in Phase 7', tone: 'success' },
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
          <button onClick={() => setView('dashboard')}><Activity size={18} />Test Runs</button>
          <button onClick={() => setView('dashboard')}><Bug size={18} />Bugs</button>
          <button onClick={() => setView('dashboard')}><FileJson size={18} />Reports</button>
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
            <span className="user-line">{user?.name} · {user?.email}</span>
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
            selectedProject={selectedProject}
            onOpenProjects={() => setView('projects')}
          />
        )}
        {view === 'projects' && (
          <ProjectsView
            projects={projects}
            isLoading={projectsQuery.isLoading}
            onCreate={() => setView('create')}
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
  selectedProject,
  onOpenProjects,
}: {
  metrics: { label: string; value: string; detail: string; tone: string }[];
  providers: ProviderStatus[];
  selectedProject: Project | null;
  onOpenProjects: () => void;
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
            <button className="primary-action" disabled>
              <Play size={18} /> Start run
            </button>
          </div>
          <div className="agent-list">
            {agents.map((agent) => (
              <div className="agent-row" key={agent.type}>
                <div className="agent-type">
                  <Bot size={18} />
                  <div>
                    <strong>{agent.type} Agent</strong>
                    <span>{agent.url}</span>
                  </div>
                </div>
                <span className={`status ${agent.status.toLowerCase()}`}>{agent.status}</span>
                <span>{agent.steps} steps</span>
                <span>{agent.bugs} bugs</span>
                <ChevronRight size={18} />
              </div>
            ))}
          </div>
        </div>
        <ProviderPanel providers={providers} />
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
        <BugQueue />
      </section>
    </>
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

function BugQueue() {
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
        {bugs.map((bug) => (
          <div className="bug-row" role="row" key={bug.title}>
            <span className={`severity ${bug.severity}`}>{bug.severity}</span>
            <strong>{bug.title}</strong>
            <span>{bug.url}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProjectsView({
  projects,
  isLoading,
  onCreate,
  onSelect,
}: {
  projects: Project[];
  isLoading: boolean;
  onCreate: () => void;
  onSelect: (projectId: string) => void;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Targets</p>
          <h2>Projects</h2>
        </div>
        <button className="primary-action" onClick={onCreate}>
          <Plus size={18} /> Create project
        </button>
      </div>
      {isLoading && <p className="empty-state">Loading projects...</p>}
      {!isLoading && projects.length === 0 && <p className="empty-state">No projects yet. Add your first web application to start swarm testing.</p>}
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
    <section className="panel form-panel">
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
    </section>
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

function splitPatterns(value: string) {
  return value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
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
    default:
      return 'Testing health overview';
  }
}

export default App;
