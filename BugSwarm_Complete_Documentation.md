# BugSwarm: AI-Powered Software Testing Swarm

## Document Set

This single Markdown file contains the complete planning and technical documentation for **BugSwarm**, an AI-powered software testing swarm platform where multiple autonomous agents test a web application like real users, discover bugs, capture evidence, and generate replayable reports.

Included documents:

1. Product Requirements Document  
2. Technical Requirements Document  
3. Backend Schema  
4. UI/UX Design Specification  
5. Application Flow  
6. Implementation Plan  

---

# 1. Product Requirements Document

## 1.1 Product Name

**BugSwarm: AI-Powered Software Testing Swarm**

## 1.2 Product Summary

BugSwarm is a software testing automation platform that deploys multiple AI-assisted browser agents to explore, interact with, and test web applications. These agents behave like real users by navigating pages, filling forms, clicking buttons, submitting flows, checking visual states, and attempting edge cases.

The system automatically generates test cases, executes them through Playwright or Selenium, detects broken flows and UI issues, captures screenshots and logs, and produces detailed bug reports with replayable failed paths.

BugSwarm also includes a three-model reasoning council where Groq, GPT-OSS, and Gemini independently analyze the same page context or bug evidence, challenge each other's conclusions through structured summaries, and produce a consensus testing decision. The MVP must use free-tier or free-to-run model options by default, with paid API usage disabled unless the user explicitly configures it.

## 1.3 Problem Statement

Modern web applications are complex, dynamic, and frequently updated. Traditional manual testing is slow, repetitive, and expensive, while conventional automated tests require developers to manually write and maintain test scripts.

Common problems include:

- Broken user flows after frequent deployments.
- Forms failing silently or accepting invalid data.
- Buttons, links, and navigation paths breaking.
- UI regressions across viewports.
- Missing validation, incorrect error messages, and inconsistent states.
- Test coverage gaps caused by manually written test cases.
- Difficulty reproducing bugs without screenshots, logs, or user path history.

BugSwarm solves these problems by combining AI-based test planning with browser automation and multi-agent exploration.

## 1.4 Vision

To create an intelligent testing swarm that continuously explores web applications, discovers bugs, explains failures, and helps developers reproduce issues faster.

## 1.5 Goals

### Product Goals

- Allow users to register a web application for testing.
- Automatically crawl and understand the structure of the target application.
- Generate test scenarios using AI.
- Execute tests with multiple parallel agents.
- Detect UI, form, navigation, and crash-related issues.
- Capture screenshots, console logs, network errors, and replay paths.
- Generate structured bug reports.
- Provide a dashboard for monitoring test runs and discovered issues.

### Technical Goals

- Build a scalable agent execution engine.
- Support Playwright as the primary browser automation layer.
- Use FastAPI or Node.js for backend APIs.
- Store projects, test runs, agents, bugs, screenshots, and replay steps in PostgreSQL.
- Provide a React dashboard for project management, test monitoring, and reports.
- Keep AI integration modular so different LLM providers or local models can be added later.
- Implement exactly three default LLM reasoning providers for MVP: Groq, GPT-OSS, and Gemini.
- Keep the default AI configuration compatible with free tiers or locally runnable open-weight models.

## 1.6 Target Users

### Primary Users

- Software developers
- QA engineers
- MCA/B.Tech final-year project evaluators
- Startup teams
- DevOps engineers
- Product teams

### Secondary Users

- Students learning software testing
- Open-source maintainers
- Freelance web developers
- Small teams without dedicated QA staff

## 1.7 User Personas

### Persona 1: QA Engineer

**Name:** Nisha  
**Goal:** Find bugs before release.  
**Pain Point:** Manual regression testing takes too much time.  
**BugSwarm Benefit:** Automatically explores flows, finds broken states, and creates reproducible bug reports.

### Persona 2: Full-Stack Developer

**Name:** Arjun  
**Goal:** Quickly test new features after deployment.  
**Pain Point:** Does not have time to write full end-to-end tests for every flow.  
**BugSwarm Benefit:** AI generates practical test paths and exposes regressions.

### Persona 3: Student Project Builder

**Name:** Ashish  
**Goal:** Build an innovative software engineering project with AI agents and automation.  
**Pain Point:** Needs a project that is more advanced than a normal dashboard or management system.  
**BugSwarm Benefit:** Combines AI, automation, backend engineering, database design, and UI/UX.

## 1.8 Core Features

## 1.8.1 Project Management

Users can create projects for web applications they want to test.

Each project contains:

- Project name
- Base URL
- Authentication configuration
- Testing scope
- Excluded routes
- Viewport settings
- Test intensity
- AI test-generation settings
- LLM reasoning council settings
- Free-tier usage limits and per-provider API keys

## 1.8.2 Website Exploration Agents

Agents crawl and explore the target website by interacting with UI elements.

Agent capabilities:

- Visit pages.
- Click buttons and links.
- Fill forms.
- Submit forms.
- Open menus and modals.
- Follow navigation paths.
- Detect dead ends.
- Detect repeated loops.
- Capture DOM snapshots.
- Record screenshots.
- Record console errors.
- Record failed network requests.

## 1.8.3 AI Test Generation

AI generates test cases from discovered page structure and user goals.

Generated tests may include:

- Login tests.
- Registration tests.
- Form validation tests.
- Navigation tests.
- Checkout or booking flow tests.
- Search and filter tests.
- Role-based access tests.
- Negative input tests.
- Boundary value tests.
- Broken-link tests.
- Accessibility sanity checks.

## 1.8.3.1 Tri-Model Reasoning Council

BugSwarm must support exactly three active LLM reasoning members in the MVP:

| Reasoning Member | Default Free-Compatible Option | Purpose |
|---|---|---|
| Groq | Groq free-plan model such as `qwen/qwen3-32b` or another configured free-plan model | Fast reasoning pass for broad coverage and quick test ideas |
| GPT-OSS | `gpt-oss-20b` running locally through Ollama, LM Studio, vLLM, or a compatible local endpoint | Open-weight reasoning pass that can run without paid API usage |
| Gemini | Gemini free-tier Flash/Flash-Lite model configured through Google AI Studio | Cross-provider reasoning pass for alternate test ideas and bug interpretation |

The exact model IDs should be environment-configurable because free-tier availability, rate limits, and model names can change. The application must ship with safe defaults, but the setup screen must allow users to update model IDs without code changes.

Reasoning council workflow:

1. The backend builds a shared evidence packet from DOM summaries, screenshots, console logs, network failures, replay steps, and project scope.
2. Groq, GPT-OSS, and Gemini each generate an independent JSON response.
3. Each response includes proposed test cases, suspected bugs, severity, confidence, and a short rationale summary.
4. The council runs a comparison step that identifies agreements, conflicts, missing evidence, and risky suggestions.
5. A deterministic consensus layer selects the final test actions or bug report recommendation using model votes, confidence scores, replay evidence, and safety rules.
6. The system stores each model's concise rationale summary, vote, confidence, and final consensus result for auditability.

The system should not store or expose private chain-of-thought. It should store concise reasoning summaries that explain the decision in user-readable terms.

## 1.8.4 Multi-Agent Test Execution

BugSwarm runs multiple agents in parallel.

Agent types:

| Agent Type | Purpose |
|---|---|
| Explorer Agent | Crawls unknown pages and maps flows |
| Form Agent | Focuses on forms, validation, and input fields |
| Navigation Agent | Tests links, menus, routing, and page transitions |
| Regression Agent | Replays existing test cases |
| Chaos Agent | Uses unusual inputs, rapid clicks, invalid states, and edge cases |
| Visual Agent | Detects screenshots, layout shifts, and viewport problems |
| Auth Agent | Tests login/logout/session-related flows |

## 1.8.5 Bug Detection

The platform detects bugs using rules, automation results, and AI analysis.

Bug categories:

- Broken link
- Page crash
- Console error
- HTTP 4xx/5xx error
- Failed form submission
- Missing validation
- Incorrect validation
- UI overlap
- Element not clickable
- Element hidden unexpectedly
- Infinite loading state
- Broken navigation
- Authentication failure
- Permission bypass suspicion
- Accessibility warning
- Visual regression
- Unexpected blank page

## 1.8.6 Screenshot Evidence

For each failed test, BugSwarm captures:

- Screenshot before the bug
- Screenshot at the failure point
- Optional video recording
- DOM snapshot
- Console logs
- Network errors
- Agent action trace
- Browser and viewport details

## 1.8.7 Replay Failed Test Paths

Each bug report includes replayable steps.

Example:

1. Open `https://example.com/login`
2. Click `Sign Up`
3. Enter invalid email `abc`
4. Enter password `123`
5. Click `Create Account`
6. Expected validation message did not appear
7. Console error detected: `Cannot read property 'message' of undefined`

The replay system should convert these steps into executable Playwright scripts.

## 1.8.8 Bug Reports

Bug reports include:

- Bug title
- Severity
- Category
- Status
- Affected URL
- Reproduction steps
- Expected result
- Actual result
- Screenshots
- Logs
- Network failures
- Replay script
- Assigned user
- Timestamps
- AI-generated explanation
- Suggested fix hints

## 1.8.9 Dashboard

Dashboard modules:

- Project overview
- Test run history
- Agent activity monitor
- Bug list
- Bug detail view
- Screenshot gallery
- Replay viewer
- Test coverage map
- Settings
- Reports export

## 1.8.10 Report Export

Users can export reports as:

- Markdown
- PDF
- JSON
- CSV
- Playwright script

## 1.9 Functional Requirements

### FR-1: User Authentication

The system shall allow users to register, log in, and manage their own projects.

### FR-2: Project Creation

The system shall allow users to create a test project by entering a project name and target URL.

### FR-3: Scope Configuration

The system shall allow users to define allowed URLs, excluded URLs, maximum crawl depth, and test intensity.

### FR-4: Agent Launch

The system shall allow users to start a test run with configurable agent count and agent types.

### FR-5: Web Exploration

The system shall allow agents to explore web pages using browser automation.

### FR-6: Test Case Generation

The system shall generate test cases automatically using AI from discovered page information.

### FR-6A: Multi-LLM Reasoning

The system shall use Groq, GPT-OSS, and Gemini as three independent reasoning members for AI-generated test cases, bug interpretation, severity classification, and fix suggestions.

The system shall compare the three outputs, detect disagreements, and produce a final consensus decision before executing generated tests or publishing AI-assisted bug conclusions.

### FR-7: Test Execution

The system shall execute generated test cases through browser automation.

### FR-8: Bug Detection

The system shall detect failed flows, browser errors, network errors, UI issues, and invalid application states.

### FR-9: Evidence Capture

The system shall capture screenshots, logs, network traces, DOM snapshots, and replay steps for each failure.

### FR-10: Bug Report Generation

The system shall create structured bug reports for detected problems.

### FR-11: Replay

The system shall allow users to replay failed test paths.

### FR-12: Dashboard

The system shall display project status, active agents, test runs, and discovered bugs.

### FR-13: Export

The system shall allow exporting reports and generated test scripts.

### FR-14: Role Management

The system should support at least two roles:

- Admin
- Tester

### FR-15: Notification

The system may notify users when a test run finishes or when critical bugs are found.

## 1.10 Non-Functional Requirements

### Performance

- The dashboard should load within 3 seconds under normal conditions.
- The backend should support multiple parallel test agents.
- A test run should support configurable concurrency.

### Scalability

- Agent workers should be horizontally scalable.
- Test execution should be queue-based.
- Screenshots and logs should be stored separately from relational metadata.

### Reliability

- Failed agents should not crash the entire test run.
- Test progress should be persisted.
- Interrupted test runs should be marked properly.

### Security

- Target credentials must be encrypted or securely stored.
- Users should only access their own projects.
- Uploaded artifacts must be validated.
- The system must avoid testing URLs outside the configured scope.
- The platform must include rate limiting to avoid unintentionally harming target sites.

### Maintainability

- The backend, agent worker, AI service, and frontend should be modular.
- Test execution logic should be isolated from API logic.
- AI provider integration should be replaceable.
- LLM provider adapters should share one interface so Groq, GPT-OSS, and Gemini can be configured independently.
- Provider rate limits, disabled providers, and fallback behavior should be handled without crashing active test runs.

### Usability

- Users should be able to start a basic test run in less than 5 minutes.
- Bug reports should be readable without technical deep-diving.
- Replay steps should be clear and deterministic.

## 1.11 MVP Scope

The Minimum Viable Product should include:

- User login
- Project creation
- URL scope configuration
- Playwright-based crawling
- Basic AI test case generation
- Tri-model reasoning using Groq, GPT-OSS, and Gemini free-compatible defaults
- Parallel agent execution
- Screenshot capture
- Console and network error capture
- Bug report generation
- Bug dashboard
- Replay step viewer
- Markdown/JSON report export

## 1.12 Out of Scope for MVP

The following are not required in the first version:

- Mobile app testing
- Native desktop app testing
- Full accessibility audit
- Advanced visual regression with pixel comparison
- Enterprise SSO
- Real-time collaboration
- CI/CD integration
- Browser farm infrastructure
- AI self-healing test maintenance

## 1.13 Future Enhancements

- GitHub issue creation.
- Jira integration.
- Slack or Discord notifications.
- CI/CD pipeline integration.
- Scheduled nightly testing.
- Visual regression comparison.
- Accessibility testing.
- API testing agent.
- Security testing agent.
- Kubernetes-based agent scaling.
- Additional local LLM support beyond GPT-OSS.
- Test prioritization using historical bug data.
- Self-healing selectors.
- Natural language test creation.
- Browser video recording.
- Multi-browser testing.

## 1.14 Success Metrics

| Metric | Target |
|---|---|
| Time to create first project | Under 5 minutes |
| Test run setup completion | Under 3 steps |
| Bug report usefulness | 80% of reports contain reproducible steps |
| Replay success rate | 70% or higher for deterministic flows |
| False positive rate | Below 25% in MVP |
| Average screenshot capture success | 95% |
| Agent crash recovery | 90% of failed agents should not stop test run |

---

# 2. Technical Requirements Document

## 2.1 System Overview

BugSwarm consists of the following major components:

1. React frontend dashboard
2. Backend API server
3. Agent orchestration service
4. Browser automation worker service
5. AI test generation service
6. PostgreSQL database
7. Artifact storage
8. Queue system
9. Reporting engine

## 2.2 Recommended Tech Stack

## 2.2.1 Frontend

| Layer | Technology |
|---|---|
| UI Framework | React |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Component Library | shadcn/ui or Material UI |
| State Management | Zustand or Redux Toolkit |
| API Client | Axios or TanStack Query |
| Charts | Recharts |
| Routing | React Router |
| Build Tool | Vite |

## 2.2.2 Backend

Two backend options are possible.

### Option A: FastAPI Backend

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Language | Python |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Authentication | JWT |
| Background Jobs | Celery or RQ |
| Queue | Redis |
| Database | PostgreSQL |

Best when the project wants stronger Python AI/automation integration.

### Option B: Node.js Backend

| Layer | Technology |
|---|---|
| API Framework | Express.js or NestJS |
| Language | TypeScript |
| ORM | Prisma |
| Authentication | JWT |
| Queue | BullMQ |
| Database | PostgreSQL |
| Worker Runtime | Node.js |

Best when the project wants a full TypeScript stack.

### Recommended Choice

For BugSwarm, the recommended stack is:

- **FastAPI** for API and AI integration.
- **Playwright Python** for browser automation.
- **PostgreSQL** for structured data.
- **Redis + Celery/RQ** for background execution.
- **React + TypeScript** for dashboard.
- **Provider adapters** for Groq, GPT-OSS, and Gemini.
- **Tri-model reasoning council** for consensus-based AI decisions.

## 2.3 High-Level Architecture

```text
+-------------------+
| React Dashboard   |
+---------+---------+
          |
          | REST/WebSocket
          v
+-------------------+
| FastAPI Backend   |
+---------+---------+
          |
          | writes/reads
          v
+-------------------+
| PostgreSQL DB     |
+-------------------+

          |
          | enqueue jobs
          v
+-------------------+
| Redis Queue       |
+---------+---------+
          |
          | consume jobs
          v
+-----------------------------+
| Agent Worker Service        |
| - Playwright Browser Agents |
| - AI Test Generator         |
| - LLM Reasoning Council     |
| - Bug Detector              |
+-------------+---------------+
              |
              | screenshots/logs/videos
              v
+-----------------------------+
| Artifact Storage            |
| Local FS / S3-compatible    |
+-----------------------------+
```

## 2.4 Component Responsibilities

## 2.4.1 React Dashboard

Responsibilities:

- User login and project management.
- Display test run status.
- Show live agent activity.
- Present bugs and reports.
- Provide replay viewer.
- Configure testing options.
- Export reports.

## 2.4.2 FastAPI Backend

Responsibilities:

- Authentication and authorization.
- Project CRUD.
- Test run creation.
- Agent job scheduling.
- Bug report API.
- Artifact metadata management.
- WebSocket updates.
- Report export.

## 2.4.3 Agent Worker Service

Responsibilities:

- Start Playwright browser contexts.
- Execute exploration logic.
- Execute AI-generated test cases.
- Coordinate LLM reasoning council jobs.
- Capture screenshots and logs.
- Detect failures.
- Save action traces.
- Submit bug findings to backend/database.

## 2.4.4 AI Test Generator

Responsibilities:

- Analyze page metadata.
- Generate test ideas.
- Convert test ideas into structured steps.
- Generate negative test values.
- Suggest expected outcomes.
- Summarize bug causes.
- Suggest possible fixes.
- Request independent reasoning from Groq, GPT-OSS, and Gemini.
- Merge model votes into one executable test plan.

AI input examples:

- Page URL
- DOM summary
- Form fields
- Buttons and links
- Previous agent actions
- Console/network errors

AI output format:

```json
{
  "test_name": "Invalid login validation test",
  "goal": "Check whether login form validates invalid credentials",
  "steps": [
    {
      "action": "goto",
      "target": "https://example.com/login"
    },
    {
      "action": "fill",
      "selector_hint": "email input",
      "value": "invalid-email"
    },
    {
      "action": "fill",
      "selector_hint": "password input",
      "value": "123"
    },
    {
      "action": "click",
      "selector_hint": "Login button"
    }
  ],
  "expected_result": "Validation error should be visible"
}
```

## 2.4.4.1 LLM Reasoning Council

The LLM Reasoning Council coordinates the three free-compatible model providers.

Council members:

| Provider Key | Provider Type | Default Model Strategy |
|---|---|---|
| `groq` | Hosted API through GroqCloud | Use a free-plan compatible reasoning model configured by `GROQ_MODEL` |
| `gptoss` | Local or self-hosted open-weight model endpoint | Use `gpt-oss-20b` by default through `GPTOSS_BASE_URL` |
| `gemini` | Gemini Developer API | Use a free-tier Flash or Flash-Lite model configured by `GEMINI_MODEL` |

Responsibilities:

- Build one normalized prompt/evidence packet.
- Call the three providers independently.
- Enforce provider timeouts and per-provider retry limits.
- Validate each provider response against the same JSON schema.
- Normalize confidence, severity, and test-priority values.
- Compare agreements and disagreements.
- Produce a final consensus result before actions are executed.
- Store model votes and rationale summaries for later audit.

Consensus rules:

- If at least two providers agree on a safe test action, the action may be queued.
- If one provider flags a destructive or out-of-scope action, the action must be blocked until the safety classifier clears it.
- If all three providers disagree, the system should prefer replay evidence, deterministic browser signals, and rule-based checks over AI claims.
- If a provider is unavailable or rate-limited, the run may continue with the remaining providers but the report must mark consensus confidence as degraded.

## 2.4.5 Bug Detection Engine

Bug detection layers:

1. Rule-based detection
2. Browser event detection
3. AI-assisted interpretation
4. Replay validation

Rule-based checks:

- HTTP status >= 400
- Console error level
- Navigation timeout
- Element not found
- Element not clickable
- Page title or body indicates error
- Blank page
- Form submits but no result
- Unexpected redirect
- Infinite spinner
- Missing validation text

## 2.5 API Design

## 2.5.1 Authentication APIs

### Register User

```http
POST /api/auth/register
```

Request:

```json
{
  "name": "Ashish",
  "email": "ashish@example.com",
  "password": "password123"
}
```

Response:

```json
{
  "user_id": "uuid",
  "email": "ashish@example.com",
  "token": "jwt-token"
}
```

### Login

```http
POST /api/auth/login
```

Request:

```json
{
  "email": "ashish@example.com",
  "password": "password123"
}
```

Response:

```json
{
  "token": "jwt-token",
  "user": {
    "id": "uuid",
    "name": "Ashish",
    "email": "ashish@example.com"
  }
}
```

## 2.5.2 Project APIs

### Create Project

```http
POST /api/projects
```

Request:

```json
{
  "name": "Demo Shop App",
  "base_url": "https://demo-shop.example.com",
  "description": "E-commerce app testing project"
}
```

### Get Projects

```http
GET /api/projects
```

### Get Project by ID

```http
GET /api/projects/{project_id}
```

### Update Project

```http
PATCH /api/projects/{project_id}
```

### Delete Project

```http
DELETE /api/projects/{project_id}
```

## 2.5.3 Test Run APIs

### Start Test Run

```http
POST /api/projects/{project_id}/test-runs
```

Request:

```json
{
  "name": "Regression Test - Build 12",
  "agent_count": 5,
  "max_depth": 3,
  "max_duration_minutes": 30,
  "test_intensity": "medium",
  "agent_types": ["explorer", "form", "navigation", "chaos"],
  "viewports": ["desktop", "mobile"],
  "llm_council_enabled": true,
  "llm_providers": ["groq", "gptoss", "gemini"],
  "llm_consensus_mode": "majority_vote",
  "auth_profile_id": null
}
```

Response:

```json
{
  "test_run_id": "uuid",
  "status": "queued"
}
```

### List Test Runs

```http
GET /api/projects/{project_id}/test-runs
```

### Get Test Run Details

```http
GET /api/test-runs/{test_run_id}
```

### Stop Test Run

```http
POST /api/test-runs/{test_run_id}/stop
```

## 2.5.4 Bug APIs

### List Bugs

```http
GET /api/projects/{project_id}/bugs
```

Query parameters:

```text
severity=critical
status=open
category=form_validation
test_run_id=uuid
```

### Get Bug Details

```http
GET /api/bugs/{bug_id}
```

### Update Bug Status

```http
PATCH /api/bugs/{bug_id}
```

Request:

```json
{
  "status": "resolved",
  "assigned_to": "uuid"
}
```

## 2.5.5 Artifact APIs

### Get Screenshot

```http
GET /api/artifacts/{artifact_id}
```

### Download Report

```http
GET /api/test-runs/{test_run_id}/report?format=markdown
```

## 2.5.6 Replay APIs

### Get Replay Steps

```http
GET /api/bugs/{bug_id}/replay
```

### Generate Playwright Script

```http
GET /api/bugs/{bug_id}/playwright-script
```

## 2.5.7 LLM Provider APIs

### List Provider Configs

```http
GET /api/projects/{project_id}/llm-providers
```

### Update Provider Config

```http
PATCH /api/projects/{project_id}/llm-providers/{provider_key}
```

Request:

```json
{
  "model_name": "string",
  "base_url": "string|null",
  "is_enabled": true,
  "is_free_mode": true,
  "timeout_seconds": 30
}
```

### Test Provider Connection

```http
POST /api/projects/{project_id}/llm-providers/{provider_key}/test
```

### Get Reasoning Session

```http
GET /api/llm-reasoning-sessions/{session_id}
```

## 2.6 WebSocket Events

Endpoint:

```http
/ws/test-runs/{test_run_id}
```

Events:

```json
{
  "event": "agent_started",
  "agent_id": "uuid",
  "message": "Explorer Agent started"
}
```

```json
{
  "event": "step_completed",
  "agent_id": "uuid",
  "url": "https://example.com/login",
  "action": "click",
  "status": "success"
}
```

```json
{
  "event": "bug_found",
  "bug_id": "uuid",
  "severity": "high",
  "title": "Login form crashes on invalid email"
}
```

```json
{
  "event": "llm_consensus_completed",
  "reasoning_session_id": "uuid",
  "providers": ["groq", "gptoss", "gemini"],
  "consensus_status": "approved",
  "agreement_count": 2
}
```

```json
{
  "event": "test_run_completed",
  "test_run_id": "uuid",
  "bugs_found": 12
}
```

## 2.7 Agent Execution Model

## 2.7.1 Agent Lifecycle

```text
Queued -> Starting -> Running -> Reporting -> Completed
                         |
                         v
                      Failed
```

## 2.7.2 Agent Inputs

Each agent receives:

- Project ID
- Test run ID
- Base URL
- Allowed scope
- Excluded routes
- Agent type
- Max depth
- Max actions
- Browser configuration
- Authentication profile
- AI configuration
- LLM council provider configuration

## 2.7.3 Agent Outputs

Each agent returns:

- Visited URLs
- Performed actions
- Discovered elements
- Generated test cases
- LLM model votes and consensus result
- Detected bugs
- Screenshots
- Logs
- Replay steps

## 2.8 Playwright Automation Requirements

The Playwright service must support:

- Chromium browser execution
- Optional Firefox/WebKit support later
- Headless and headed modes
- Screenshot capture
- Console log capture
- Network request monitoring
- DOM extraction
- Selectors by role, label, placeholder, text, CSS, XPath fallback
- Tracing
- Browser context isolation per agent
- Authentication state reuse

## 2.9 AI Requirements

## 2.9.1 AI Use Cases

- Generate test cases.
- Generate edge-case input values.
- Summarize page purpose.
- Classify bug severity.
- Explain bug reason.
- Generate human-readable bug title.
- Suggest developer fix hints.
- Generate Playwright replay script comments.

## 2.9.2 AI Guardrails

- AI output must follow strict JSON schema.
- AI should not execute arbitrary code.
- AI should not test outside the allowed scope.
- AI should not generate destructive tests unless explicitly allowed.
- AI should not submit real payments, delete real data, or trigger irreversible actions.
- AI reasoning output should be stored as concise rationale summaries, votes, and confidence scores, not private chain-of-thought.
- External providers must receive only the minimum page context needed for test generation and bug interpretation.

## 2.9.3 Supported MVP Providers

The MVP must include these three provider adapters:

| Provider | Required Configuration | Free-Compatible Default |
|---|---|---|
| Groq | `GROQ_API_KEY`, `GROQ_MODEL` | A Groq free-plan model such as `qwen/qwen3-32b` |
| GPT-OSS | `GPTOSS_BASE_URL`, `GPTOSS_MODEL` | Local `gpt-oss-20b` through Ollama, LM Studio, vLLM, or compatible OpenAI-style endpoint |
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL` | A Gemini free-tier Flash or Flash-Lite model |

Provider behavior:

- Each provider adapter must implement `generate_test_plan`, `classify_bug`, `summarize_bug`, and `suggest_fix`.
- Model IDs must be configurable through environment variables and project settings.
- Missing API keys should disable only that provider, not the full test run.
- Rate-limit responses should trigger exponential backoff and mark provider confidence as unavailable for that round.
- Free mode should be enabled by default and should prevent accidental use of paid-only models.
- Provider defaults should be rechecked during setup because free-tier quotas and supported model IDs change over time.
- Gemini free-tier data handling should be disclosed in the settings screen because free-tier usage may be used to improve provider products.

## 2.9.4 Multi-Model Reasoning Output

Each provider must return this normalized shape:

```json
{
  "provider": "groq|gptoss|gemini",
  "model": "string",
  "task_type": "test_generation|bug_classification|fix_suggestion",
  "confidence": 0.82,
  "vote": "approve|reject|needs_more_evidence",
  "rationale_summary": "Short explanation suitable for users.",
  "risks": ["string"],
  "test_cases": [],
  "bug_assessment": {}
}
```

The consensus result must include:

```json
{
  "consensus_status": "approved|rejected|degraded|needs_review",
  "winning_vote": "approve",
  "agreement_count": 2,
  "provider_votes": ["groq", "gptoss", "gemini"],
  "final_rationale": "Why the system selected this action.",
  "requires_human_review": false
}
```

## 2.10 Security Requirements

- JWT-based authentication.
- Password hashing using bcrypt or Argon2.
- Project isolation by user ID.
- Encrypted auth profiles.
- URL allowlist enforcement.
- SSRF protection.
- Request rate limiting.
- Test-run timeout enforcement.
- Artifact access authorization.
- Audit logging for test run creation and deletion.

## 2.11 Deployment Requirements

## 2.11.1 Local Development

Recommended local services:

- React frontend
- FastAPI backend
- PostgreSQL
- Redis
- Agent worker
- Local artifact folder

Docker Compose should run:

```yaml
services:
  frontend:
    build: ./frontend

  backend:
    build: ./backend

  worker:
    build: ./worker

  postgres:
    image: postgres:16

  redis:
    image: redis:7
```

## 2.11.2 Production

Production may use:

- Frontend on Vercel/Netlify/Nginx
- Backend on cloud VM/container
- PostgreSQL managed database
- Redis managed service
- Object storage for artifacts
- Worker containers
- Optional Kubernetes deployment

## 2.12 System Constraints

- The system should only test applications owned by or authorized for the user.
- Public websites should not be aggressively crawled.
- Test intensity must be controlled.
- Destructive actions must be disabled by default.
- Target URLs must be validated before testing.
- Browser automation consumes CPU and RAM, so concurrency should be configurable.

---

# 3. Backend Schema

The following schema is designed for PostgreSQL.

## 3.1 Entity Relationship Overview

```text
users
  |
  | 1-to-many
  v
projects
  |
  | 1-to-many
  v
test_runs
  |
  | 1-to-many
  v
agents
  |
  | 1-to-many
  v
agent_steps

projects
  |
  | 1-to-many
  v
bugs
  |
  | 1-to-many
  v
bug_artifacts

test_runs
  |
  | 1-to-many
  v
test_cases

projects
  |
  | 1-to-many
  v
llm_provider_configs

test_runs
  |
  | 1-to-many
  v
llm_reasoning_sessions
  |
  | 1-to-many
  v
llm_model_responses

test_cases
  |
  | 1-to-many
  v
test_steps

bugs
  |
  | 1-to-many
  v
replay_steps
```

## 3.2 Table: users

Stores registered users.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'tester',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.3 Table: projects

Stores web applications registered for testing.

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    description TEXT,
    base_url TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    default_max_depth INT NOT NULL DEFAULT 3,
    default_agent_count INT NOT NULL DEFAULT 3,
    default_test_intensity VARCHAR(30) NOT NULL DEFAULT 'medium',
    llm_council_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    llm_consensus_mode VARCHAR(50) NOT NULL DEFAULT 'majority_vote',
    free_ai_mode BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.4 Table: project_scopes

Stores allowed and excluded routes.

```sql
CREATE TABLE project_scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scope_type VARCHAR(30) NOT NULL,
    pattern TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Example scope types:

- `allow`
- `exclude`

## 3.5 Table: auth_profiles

Stores optional authentication data for testing logged-in flows.

```sql
CREATE TABLE auth_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    auth_type VARCHAR(50) NOT NULL,
    login_url TEXT,
    username_selector TEXT,
    password_selector TEXT,
    submit_selector TEXT,
    username_value TEXT,
    encrypted_password_value TEXT,
    storage_state_path TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.6 Table: test_runs

Stores execution sessions.

```sql
CREATE TABLE test_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'queued',
    agent_count INT NOT NULL,
    max_depth INT NOT NULL,
    max_duration_minutes INT NOT NULL,
    test_intensity VARCHAR(30) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    summary JSONB
);
```

Valid statuses:

- `queued`
- `running`
- `paused`
- `completed`
- `failed`
- `cancelled`

## 3.6.1 Table: llm_provider_configs

Stores per-project provider configuration metadata. API keys should be stored through the application's secret manager or encrypted environment configuration, not as plaintext in this table.

```sql
CREATE TABLE llm_provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    provider_key VARCHAR(30) NOT NULL,
    model_name VARCHAR(120) NOT NULL,
    base_url TEXT,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_free_mode BOOLEAN NOT NULL DEFAULT TRUE,
    timeout_seconds INT NOT NULL DEFAULT 30,
    max_retries INT NOT NULL DEFAULT 2,
    rate_limit_policy JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, provider_key)
);
```

Valid provider keys:

- `groq`
- `gptoss`
- `gemini`

## 3.6.2 Table: llm_reasoning_sessions

Stores each multi-model reasoning round for test generation, bug classification, or fix suggestion.

```sql
CREATE TABLE llm_reasoning_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_run_id UUID REFERENCES test_runs(id) ON DELETE CASCADE,
    bug_id UUID,
    task_type VARCHAR(50) NOT NULL,
    prompt_fingerprint VARCHAR(128) NOT NULL,
    consensus_status VARCHAR(50) NOT NULL,
    consensus_mode VARCHAR(50) NOT NULL DEFAULT 'majority_vote',
    final_rationale TEXT,
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Valid task types:

- `test_generation`
- `bug_classification`
- `severity_scoring`
- `fix_suggestion`

`bug_id` may be filled after a bug record is created from the consensus result.

## 3.6.3 Table: llm_model_responses

Stores normalized responses from each council member.

```sql
CREATE TABLE llm_model_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reasoning_session_id UUID NOT NULL REFERENCES llm_reasoning_sessions(id) ON DELETE CASCADE,
    provider_key VARCHAR(30) NOT NULL,
    model_name VARCHAR(120) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'completed',
    confidence NUMERIC(4,3),
    vote VARCHAR(40),
    rationale_summary TEXT,
    output JSONB,
    error_message TEXT,
    latency_ms INT,
    token_usage JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.7 Table: agents

Stores each agent involved in a test run.

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_run_id UUID NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'queued',
    browser VARCHAR(50) NOT NULL DEFAULT 'chromium',
    viewport_width INT,
    viewport_height INT,
    current_url TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Agent types:

- `explorer`
- `form`
- `navigation`
- `chaos`
- `visual`
- `auth`
- `regression`

## 3.8 Table: agent_steps

Stores every action performed by an agent.

```sql
CREATE TABLE agent_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    target_selector TEXT,
    target_text TEXT,
    input_value TEXT,
    url_before TEXT,
    url_after TEXT,
    status VARCHAR(30) NOT NULL,
    error_message TEXT,
    screenshot_artifact_id UUID,
    dom_snapshot_artifact_id UUID,
    duration_ms INT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Action types:

- `goto`
- `click`
- `fill`
- `select`
- `submit`
- `wait`
- `assert`
- `screenshot`
- `scroll`
- `hover`

## 3.9 Table: discovered_pages

Stores pages discovered during crawling.

```sql
CREATE TABLE discovered_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    test_run_id UUID REFERENCES test_runs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    status_code INT,
    content_hash TEXT,
    page_type VARCHAR(80),
    forms_count INT DEFAULT 0,
    links_count INT DEFAULT 0,
    buttons_count INT DEFAULT 0,
    discovered_by_agent_id UUID REFERENCES agents(id),
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.10 Table: page_elements

Stores extracted interactive elements.

```sql
CREATE TABLE page_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discovered_page_id UUID NOT NULL REFERENCES discovered_pages(id) ON DELETE CASCADE,
    element_type VARCHAR(50) NOT NULL,
    selector TEXT,
    role TEXT,
    label TEXT,
    placeholder TEXT,
    text_content TEXT,
    href TEXT,
    is_visible BOOLEAN,
    is_enabled BOOLEAN,
    bounding_box JSONB,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.11 Table: test_cases

Stores generated or manually created test cases.

```sql
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    test_run_id UUID REFERENCES test_runs(id) ON DELETE SET NULL,
    name VARCHAR(220) NOT NULL,
    description TEXT,
    source VARCHAR(50) NOT NULL DEFAULT 'ai',
    priority VARCHAR(30) NOT NULL DEFAULT 'medium',
    status VARCHAR(40) NOT NULL DEFAULT 'generated',
    expected_result TEXT,
    ai_prompt_hash TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Source values:

- `ai`
- `manual`
- `replay`
- `imported`

## 3.12 Table: test_steps

Stores structured steps for test cases.

```sql
CREATE TABLE test_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_case_id UUID NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    selector_hint TEXT,
    selector_resolved TEXT,
    input_value TEXT,
    expected_observation TEXT,
    timeout_ms INT DEFAULT 5000,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.13 Table: bugs

Stores detected issues.

```sql
CREATE TABLE bugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    test_run_id UUID REFERENCES test_runs(id) ON DELETE SET NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    test_case_id UUID REFERENCES test_cases(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(80) NOT NULL,
    severity VARCHAR(30) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    affected_url TEXT,
    expected_result TEXT,
    actual_result TEXT,
    ai_summary TEXT,
    suggested_fix TEXT,
    ai_consensus_status VARCHAR(50),
    ai_confidence NUMERIC(4,3),
    reasoning_session_id UUID REFERENCES llm_reasoning_sessions(id) ON DELETE SET NULL,
    fingerprint TEXT,
    assigned_to UUID REFERENCES users(id),
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Severity values:

- `critical`
- `high`
- `medium`
- `low`
- `info`

Status values:

- `open`
- `triaged`
- `in_progress`
- `resolved`
- `ignored`
- `duplicate`

## 3.14 Table: bug_artifacts

Stores screenshots, videos, traces, logs, and DOM snapshots.

```sql
CREATE TABLE bug_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bug_id UUID NOT NULL REFERENCES bugs(id) ON DELETE CASCADE,
    artifact_type VARCHAR(50) NOT NULL,
    file_path TEXT NOT NULL,
    mime_type VARCHAR(120),
    file_size_bytes BIGINT,
    label VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Artifact types:

- `screenshot`
- `video`
- `console_log`
- `network_log`
- `dom_snapshot`
- `trace`
- `playwright_script`

## 3.15 Table: replay_steps

Stores replayable bug reproduction paths.

```sql
CREATE TABLE replay_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bug_id UUID NOT NULL REFERENCES bugs(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    selector TEXT,
    selector_hint TEXT,
    input_value TEXT,
    url TEXT,
    expected_result TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.16 Table: browser_logs

Stores console logs.

```sql
CREATE TABLE browser_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_run_id UUID REFERENCES test_runs(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    bug_id UUID REFERENCES bugs(id) ON DELETE SET NULL,
    log_level VARCHAR(30),
    message TEXT,
    source_url TEXT,
    line_number INT,
    column_number INT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.17 Table: network_logs

Stores network request and response data.

```sql
CREATE TABLE network_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_run_id UUID REFERENCES test_runs(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    bug_id UUID REFERENCES bugs(id) ON DELETE SET NULL,
    request_url TEXT NOT NULL,
    method VARCHAR(20),
    status_code INT,
    resource_type VARCHAR(50),
    failure_text TEXT,
    duration_ms INT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.18 Table: reports

Stores generated reports.

```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_run_id UUID NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL,
    file_path TEXT,
    content JSONB,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 3.19 Recommended Indexes

```sql
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_test_runs_project_id ON test_runs(project_id);
CREATE INDEX idx_agents_test_run_id ON agents(test_run_id);
CREATE INDEX idx_agent_steps_agent_id ON agent_steps(agent_id);
CREATE INDEX idx_bugs_project_id ON bugs(project_id);
CREATE INDEX idx_bugs_test_run_id ON bugs(test_run_id);
CREATE INDEX idx_bugs_severity ON bugs(severity);
CREATE INDEX idx_bugs_status ON bugs(status);
CREATE INDEX idx_discovered_pages_project_id ON discovered_pages(project_id);
CREATE INDEX idx_browser_logs_agent_id ON browser_logs(agent_id);
CREATE INDEX idx_network_logs_agent_id ON network_logs(agent_id);
CREATE INDEX idx_llm_provider_configs_project_id ON llm_provider_configs(project_id);
CREATE INDEX idx_llm_reasoning_sessions_test_run_id ON llm_reasoning_sessions(test_run_id);
CREATE INDEX idx_llm_model_responses_session_id ON llm_model_responses(reasoning_session_id);
```

## 3.20 Bug Fingerprinting Strategy

To avoid duplicate bugs, generate a fingerprint using:

```text
hash(category + affected_url + normalized_error_message + failing_selector)
```

Example:

```text
form_validation:https://example.com/login:missing_email_validation:#email
```

## 3.21 Data Retention Rules

Recommended MVP retention:

| Data Type | Retention |
|---|---|
| Test run metadata | Permanent until deleted |
| Bugs | Permanent until deleted |
| Screenshots | 90 days by default |
| Videos | 30 days by default |
| Console logs | 90 days |
| Network logs | 90 days |
| DOM snapshots | 30 days |

---

# 4. UI/UX Design Specification

## 4.1 Design Goal

The interface should feel like a modern QA command center: clean, technical, fast, and evidence-focused. The user should understand:

- What application is being tested.
- What agents are doing.
- What bugs were found.
- How serious each bug is.
- How to reproduce each bug.

## 4.2 Visual Style

### Theme

Recommended theme:

- Dark-first dashboard
- Optional light mode later
- Technical and modern interface
- High contrast for bug severity
- Card-based layout
- Compact data tables
- Timeline-based replay views

### Suggested Color Semantics

| Meaning | Suggested Use |
|---|---|
| Critical | Red |
| High | Orange |
| Medium | Yellow |
| Low | Blue |
| Info | Gray |
| Success | Green |
| Running | Purple or cyan |

## 4.3 Main Navigation

Sidebar navigation:

1. Dashboard
2. Projects
3. Test Runs
4. Bugs
5. Replay
6. Reports
7. Settings

## 4.4 Page: Login

### Purpose

Allow users to securely access the platform.

### UI Elements

- Email input
- Password input
- Login button
- Register link
- Forgot password link, optional

### Validation

- Email required
- Valid email format
- Password required
- Show authentication errors clearly

## 4.5 Page: Main Dashboard

### Purpose

Show the overall testing health across projects.

### Components

- Total projects
- Active test runs
- Bugs found today
- Critical bugs
- Recent test runs
- Bug severity chart
- Agent activity summary

### Example Layout

```text
+---------------------------------------------------+
| BugSwarm Dashboard                                |
+----------------+----------------+-----------------+
| Projects       | Active Runs    | Critical Bugs   |
+----------------+----------------+-----------------+

+-----------------------------+---------------------+
| Recent Test Runs            | Severity Breakdown  |
+-----------------------------+---------------------+

+---------------------------------------------------+
| Latest Bugs                                        |
+---------------------------------------------------+
```

## 4.6 Page: Projects

### Purpose

Manage applications registered for testing.

### Components

- Project cards
- Search projects
- Create project button
- Project status
- Base URL
- Last test run
- Bug count

### Project Card Information

- Project name
- Base URL
- Last tested date
- Open bugs
- Critical bugs
- Start test button

## 4.7 Page: Create Project

### Purpose

Create a new test target.

### Fields

- Project name
- Base URL
- Description
- Allowed paths
- Excluded paths
- Default max crawl depth
- Default agent count
- Test intensity
- Authentication profile, optional

### Validation

- Base URL must be valid.
- Base URL must use `http` or `https`.
- Max depth must be positive.
- Agent count must be within allowed limits.

## 4.8 Page: Project Detail

### Purpose

Show complete project-level information.

### Tabs

1. Overview
2. Test Runs
3. Bugs
4. Discovered Pages
5. Test Cases
6. Settings

### Overview Widgets

- Last test status
- Open bugs by severity
- Total pages discovered
- Total tests generated
- Average run duration
- Most unstable flows

## 4.9 Page: Start Test Run

### Purpose

Configure and launch a new swarm run.

### Fields

- Run name
- Agent count
- Max crawl depth
- Max run duration
- Test intensity
- Agent type selection
- Viewport selection
- Authentication profile
- LLM reasoning council toggle
- Provider checklist: Groq, GPT-OSS, Gemini
- Consensus mode selector
- Safe mode toggle
- Destructive action toggle, disabled by default

### Agent Type Selection UI

Checkboxes:

- Explorer Agent
- Form Agent
- Navigation Agent
- Chaos Agent
- Visual Agent
- Auth Agent
- Regression Agent

## 4.10 Page: Test Run Monitor

### Purpose

Display real-time test execution.

### Components

- Test run status
- Progress bar
- Active agents list
- Live event stream
- URLs visited
- Bugs found
- Console errors
- Network errors
- Stop run button

### Agent Activity Card

Each agent card should show:

- Agent type
- Current URL
- Current action
- Steps completed
- Bugs found
- Status
- Runtime

## 4.11 Page: Bugs List

### Purpose

Allow users to review and filter bugs.

### Components

- Bug table
- Severity filter
- Status filter
- Category filter
- Test run filter
- Search
- Export button

### Columns

| Column | Description |
|---|---|
| Severity | Critical, high, medium, low, info |
| Title | Bug title |
| Category | Type of bug |
| URL | Affected page |
| Status | Open, resolved, ignored |
| Found By | Agent type |
| First Seen | Timestamp |
| Actions | View, replay, export |

## 4.12 Page: Bug Detail

### Purpose

Show complete evidence and reproduction information.

### Sections

1. Header
2. Summary
3. Screenshot evidence
4. Replay steps
5. Console logs
6. Network logs
7. DOM snapshot
8. AI explanation
9. Suggested fix
10. Export/replay actions

### Header

- Bug title
- Severity badge
- Status dropdown
- Category
- Affected URL
- Assign button

### Screenshot Viewer

Features:

- Before screenshot
- Failure screenshot
- Fullscreen mode
- Download button
- Timestamp label

### Replay Steps Component

Example UI:

```text
1. Go to /login
2. Fill email with "invalid-email"
3. Fill password with "123"
4. Click "Login"
5. Expected validation message did not appear
```

Buttons:

- Replay in browser
- Generate Playwright script
- Copy steps
- Export bug report

## 4.13 Page: Replay Viewer

### Purpose

Allow users to replay bug paths visually.

### Components

- Step timeline
- Screenshot panel
- Current action details
- Browser viewport preview
- Logs panel
- Play/pause controls
- Step forward/backward

## 4.14 Page: Reports

### Purpose

Generate and download project/test reports.

### Components

- Test run selector
- Report type selector
- Summary preview
- Export format buttons

Formats:

- Markdown
- PDF
- JSON
- CSV

## 4.15 Page: Settings

### Project Settings

- Base URL
- Scope rules
- Default agent count
- Default max depth
- LLM reasoning council toggle
- Groq provider settings
- GPT-OSS local endpoint settings
- Gemini provider settings
- Free AI mode
- Consensus mode
- Artifact retention
- Safe mode

### Account Settings

- Name
- Email
- Password update
- Theme preference

## 4.16 UX Principles

- Always show evidence for every bug.
- Never hide replay steps behind technical logs.
- Keep test launch flow simple.
- Use severity badges consistently.
- Provide clear empty states.
- Distinguish AI-generated conclusions from raw evidence.
- Warn users before enabling destructive tests.
- Show progress during long test runs.

## 4.17 Empty States

### No Projects

Message:

```text
No projects yet. Add your first web application to start swarm testing.
```

### No Bugs

Message:

```text
No bugs found in this run. Review coverage to confirm explored flows.
```

### No Test Runs

Message:

```text
No test runs yet. Start a swarm run to begin automated exploration.
```

## 4.18 Important UI States

### Loading State

Use skeleton cards and table placeholders.

### Error State

Show:

- Error title
- Human-readable explanation
- Retry button

### Running State

Use:

- Animated status badge
- Live agent feed
- Progress bar

### Completed State

Show:

- Total bugs
- Severity breakdown
- Export report button

---

# 5. Application Flow

## 5.1 Overall User Flow

```text
User registers/logs in
        |
        v
Creates project
        |
        v
Configures target URL and scope
        |
        v
Starts test run
        |
        v
Backend creates test run
        |
        v
Jobs are added to queue
        |
        v
Agents start browser automation
        |
        v
Agents explore website and generate tests
        |
        v
Bugs are detected and stored
        |
        v
Dashboard receives live updates
        |
        v
User reviews bug reports
        |
        v
User replays failed paths
        |
        v
User exports report or generated script
```

## 5.2 Project Creation Flow

```text
Open Projects Page
        |
        v
Click "Create Project"
        |
        v
Enter name and base URL
        |
        v
Configure scope
        |
        v
Optional: add authentication profile
        |
        v
Save project
        |
        v
Project appears in dashboard
```

## 5.3 Test Run Flow

```text
Open Project Detail
        |
        v
Click "Start Test Run"
        |
        v
Select agents, depth, duration, intensity
        |
        v
Select LLM council providers
        |
        v
Confirm safe mode
        |
        v
Backend validates configuration
        |
        v
Create test_run record
        |
        v
Create agent records
        |
        v
Queue agent jobs
        |
        v
Workers execute agents
        |
        v
Dashboard receives WebSocket updates
        |
        v
Run completes or fails
```

## 5.4 Agent Exploration Flow

```text
Agent receives job
        |
        v
Launch browser context
        |
        v
Navigate to base URL
        |
        v
Capture initial page data
        |
        v
Extract links, forms, buttons, inputs
        |
        v
Choose next action
        |
        v
Perform action
        |
        v
Capture result
        |
        v
Check for bugs
        |
        v
Store step
        |
        v
Repeat until max depth/duration/action limit
        |
        v
Submit final summary
```

## 5.5 AI Test Generation Flow

```text
Agent extracts page context
        |
        v
Backend builds AI prompt
        |
        v
Send evidence packet to Groq, GPT-OSS, and Gemini
        |
        v
Each model returns structured reasoning output
        |
        v
Compare model votes and disagreements
        |
        v
Create consensus test plan
        |
        v
Validate JSON schema
        |
        v
Store test cases
        |
        v
Queue test execution
        |
        v
Run Playwright steps
        |
        v
Capture results
```

## 5.6 Bug Detection Flow

```text
Agent performs action
        |
        v
Monitor browser events
        |
        v
Check page state
        |
        v
Detect abnormal behavior
        |
        v
Capture screenshot/logs/DOM
        |
        v
Create fingerprint
        |
        v
Check for duplicate bug
        |
        v
Create or update bug
        |
        v
Generate AI summary
        |
        v
Send dashboard event
```

## 5.7 Replay Flow

```text
User opens bug detail
        |
        v
Clicks "Replay"
        |
        v
Backend loads replay_steps
        |
        v
Replay runner launches browser
        |
        v
Executes steps one by one
        |
        v
Captures new screenshots
        |
        v
Shows replay result
```

## 5.8 Report Generation Flow

```text
User selects test run
        |
        v
Clicks Export Report
        |
        v
Backend gathers bugs, logs, screenshots, and summaries
        |
        v
Reporting engine builds document
        |
        v
File saved in artifact storage
        |
        v
Download link returned
```

## 5.9 Authentication Flow for Target Website

```text
User creates auth profile
        |
        v
Provides login URL and selectors
        |
        v
Worker opens login page
        |
        v
Fills credentials
        |
        v
Submits login form
        |
        v
Stores browser storage state
        |
        v
Agents reuse authenticated session
```

## 5.10 Safe Mode Flow

Safe mode should prevent destructive actions.

Examples of blocked actions:

- Clicking buttons with text like `Delete`, `Remove`, `Destroy`, `Cancel Subscription`
- Submitting payment forms
- Confirming irreversible modals
- Uploading random files
- Sending real emails

Flow:

```text
Agent identifies action
        |
        v
Safety classifier checks action
        |
        v
If safe, execute action
        |
        v
If risky, skip action and log reason
```

---

# 6. Implementation Plan

## 6.1 Recommended Development Timeline

A solid MVP can be built in **6 to 8 weeks**.

## 6.2 Phase 1: Project Setup and Architecture

### Duration

Week 1

### Goals

- Set up repository structure.
- Configure frontend, backend, database, and worker service.
- Establish local Docker Compose environment.

### Tasks

- Create Git repository.
- Create frontend using Vite + React + TypeScript.
- Create backend using FastAPI.
- Create worker service.
- Add PostgreSQL container.
- Add Redis container.
- Configure environment variables.
- Add free-mode LLM environment variables: `GROQ_API_KEY`, `GROQ_MODEL`, `GPTOSS_BASE_URL`, `GPTOSS_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `AI_FREE_MODE`.
- Add database migration tool.
- Add shared API response format.
- Add basic logging.

### Deliverables

- Running local development environment.
- Basic backend health endpoint.
- Basic frontend shell.
- Connected PostgreSQL and Redis.

### Suggested Folder Structure

```text
bugswarm/
  frontend/
    src/
      components/
      pages/
      routes/
      services/
      stores/
      types/
      utils/
    package.json

  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      workers/
      utils/
    alembic/
    requirements.txt

  worker/
    agents/
    browser/
    ai/
      providers/
      consensus/
    detection/
    reporting/
    requirements.txt

  storage/
    screenshots/
    traces/
    reports/

  docker-compose.yml
  README.md
```

## 6.3 Phase 2: Authentication and Project Management

### Duration

Week 2

### Goals

- Implement user authentication.
- Implement project CRUD.
- Implement project scope rules.

### Backend Tasks

- Create user model.
- Create project model.
- Create project scope model.
- Implement JWT authentication.
- Implement password hashing.
- Create auth APIs.
- Create project APIs.
- Add authorization checks.

### Frontend Tasks

- Login page.
- Register page.
- Dashboard layout.
- Projects page.
- Create project form.
- Project detail page.

### Deliverables

- Users can register and log in.
- Users can create projects.
- Users can configure base URL and scope.

## 6.4 Phase 3: Basic Playwright Agent

### Duration

Week 3

### Goals

- Build first working browser automation agent.
- Crawl website pages.
- Capture screenshots.
- Store discovered pages and agent steps.

### Worker Tasks

- Create Playwright browser launcher.
- Implement URL scope checker.
- Implement page extractor.
- Extract links, buttons, forms, and inputs.
- Implement basic click/navigation exploration.
- Capture screenshots.
- Store agent steps.
- Capture console errors.
- Capture network failures.

### Backend Tasks

- Create test run APIs.
- Create agent records.
- Queue worker jobs.
- Store discovered pages.
- Store page elements.

### Frontend Tasks

- Start test run page.
- Test run monitor page.
- Basic live status refresh.

### Deliverables

- User can start a test run.
- Agent opens the target URL.
- Agent explores pages.
- Screenshots and steps are stored.

## 6.5 Phase 4: Multi-Agent Swarm Execution

### Duration

Week 4

### Goals

- Run multiple agents in parallel.
- Add different agent types.
- Add WebSocket status updates.

### Worker Tasks

- Implement agent type strategies:
  - Explorer Agent
  - Form Agent
  - Navigation Agent
  - Chaos Agent
- Add action limits.
- Add max depth.
- Add timeout handling.
- Add worker crash handling.

### Backend Tasks

- Create WebSocket endpoint.
- Broadcast agent events.
- Update test run progress.
- Store agent status.

### Frontend Tasks

- Real-time test run monitor.
- Agent activity cards.
- Live event feed.
- Visited URL list.
- Stop test run button.

### Deliverables

- Multiple agents run in parallel.
- Dashboard shows live agent activity.
- Test runs can complete with summaries.

## 6.6 Phase 5: AI Test Generation

### Duration

Week 5

### Goals

- Generate structured test cases from page context.
- Execute generated tests.
- Compare Groq, GPT-OSS, and Gemini reasoning before accepting AI output.

### AI Tasks

- Design AI prompt format.
- Define JSON schema for AI output.
- Build Groq provider adapter.
- Build GPT-OSS local endpoint adapter.
- Build Gemini provider adapter.
- Add tri-model reasoning council orchestration.
- Add consensus scoring and disagreement handling.
- Add validation layer.
- Generate test names, goals, steps, and expected results.
- Add negative input generation.
- Add form-specific tests.
- Store provider votes, confidence scores, and rationale summaries.

### Worker Tasks

- Convert AI test steps to Playwright actions.
- Resolve selectors.
- Execute generated test cases.
- Store test cases and test steps.

### Backend Tasks

- Create test case models and APIs.
- Store AI-generated test cases.
- Add AI configuration settings.
- Add LLM provider configuration settings.
- Add reasoning session and model response persistence.
- Add provider rate-limit and timeout handling.

### Frontend Tasks

- Test cases tab.
- Test case detail view.
- AI-generated badge.
- Reasoning council panel with Groq, GPT-OSS, and Gemini vote summaries.
- Provider setup form for API keys, local GPT-OSS URL, and model IDs.
- Execution status display.

### Deliverables

- Groq, GPT-OSS, and Gemini independently generate or review test cases.
- Consensus logic approves the final generated tests.
- Generated tests are executed.
- Results are stored.

## 6.7 Phase 6: Bug Detection and Reporting

### Duration

Week 6

### Goals

- Detect bugs reliably.
- Generate detailed reports.
- Add bug list and bug detail views.

### Detection Tasks

- Detect HTTP errors.
- Detect console errors.
- Detect page crashes.
- Detect broken links.
- Detect form validation failures.
- Detect element interaction failures.
- Detect blank pages.
- Detect infinite loading states.
- Generate bug fingerprints.
- Deduplicate bugs.

### Evidence Tasks

- Capture failure screenshot.
- Store logs.
- Store network traces.
- Store DOM snapshot.
- Store replay steps.

### Backend Tasks

- Create bug APIs.
- Create artifact APIs.
- Create report generator.
- Create Markdown export.
- Create JSON export.

### Frontend Tasks

- Bugs list page.
- Bug detail page.
- Screenshot viewer.
- Logs viewer.
- Severity filters.
- Status update dropdown.

### Deliverables

- Bugs are created with evidence.
- Users can view bug details.
- Reports can be exported.

## 6.8 Phase 7: Replay System

### Duration

Week 7

### Goals

- Replay failed test paths.
- Generate Playwright scripts.

### Worker Tasks

- Implement replay runner.
- Load replay steps.
- Execute replay in browser.
- Capture replay result.
- Generate Playwright script.

### Backend Tasks

- Create replay API.
- Create script generation API.
- Store replay attempt result.

### Frontend Tasks

- Replay viewer.
- Step timeline.
- Generate script button.
- Copy script button.

### Deliverables

- User can replay a failed bug path.
- User can export Playwright script.

## 6.9 Phase 8: Polish, Testing, and Final Documentation

### Duration

Week 8

### Goals

- Improve reliability.
- Finish documentation.
- Prepare final project demonstration.

### Tasks

- Add validation.
- Add better error messages.
- Improve UI responsiveness.
- Add loading and empty states.
- Add sample project/demo target app.
- Write final README.
- Add architecture diagrams.
- Add API documentation.
- Add test cases for backend.
- Add sample reports.
- Record demo video.

### Deliverables

- Stable MVP.
- Final documentation.
- Demo-ready project.

## 6.10 MVP Feature Checklist

| Feature | Status |
|---|---|
| User authentication | Required |
| Project CRUD | Required |
| Scope configuration | Required |
| Start test run | Required |
| Playwright agent | Required |
| Multi-agent execution | Required |
| AI test generation | Required |
| Screenshot capture | Required |
| Console/network log capture | Required |
| Bug detection | Required |
| Bug reports | Required |
| Replay steps | Required |
| Markdown export | Required |
| Dashboard | Required |
| WebSocket live updates | Recommended |
| PDF export | Optional |
| Video recording | Optional |
| CI/CD integration | Future |
| Jira/GitHub integration | Future |

## 6.11 Development Priority

### Highest Priority

1. Playwright exploration
2. Test run management
3. Bug detection
4. Evidence capture
5. Dashboard visualization

### Medium Priority

1. AI test generation
2. Replay generation
3. Export reports
4. WebSocket updates

### Lower Priority

1. Visual regression
2. CI/CD integration
3. GitHub/Jira integration
4. Kubernetes deployment

## 6.12 Suggested Agent Logic Pseudocode

```python
def run_agent(job):
    browser = launch_browser()
    context = browser.new_context(viewport=job.viewport)
    page = context.new_page()

    attach_console_listener(page)
    attach_network_listener(page)

    visited = set()
    queue = [job.base_url]

    while queue and within_limits(job):
        url = queue.pop(0)

        if url in visited:
            continue

        if not is_url_allowed(url, job.scope):
            continue

        visited.add(url)

        try:
            page.goto(url, timeout=job.timeout)
            capture_page_state(page)

            elements = extract_interactive_elements(page)
            save_discovered_page(url, elements)

            bugs = detect_page_bugs(page)
            save_bugs(bugs)

            next_actions = choose_actions(elements, job.agent_type)

            for action in next_actions:
                result = execute_action(page, action)
                save_agent_step(action, result)

                if result.has_bug:
                    capture_failure_evidence(page, result)
                    create_bug_report(result)

                if result.new_url and is_url_allowed(result.new_url, job.scope):
                    queue.append(result.new_url)

        except Exception as error:
            capture_failure_evidence(page, error)
            create_bug_report_from_exception(error)

    browser.close()
```

## 6.13 AI Prompt Template

```text
You are a software QA test generation agent.
You are one member of a three-model reasoning council.
Your provider key is: {provider_key}.

Target page:
URL: {url}
Title: {title}

Visible forms:
{forms}

Buttons:
{buttons}

Links:
{links}

Inputs:
{inputs}

Generate practical web UI test cases for this page.

Rules:
- Return valid JSON only.
- Do not include destructive actions.
- Stay within the given domain.
- Prefer realistic user behavior.
- Include both positive and negative tests.
- Each test must have clear steps and expected result.
- Include a concise rationale_summary, not hidden chain-of-thought.
- Vote on whether the generated plan should be approved, rejected, or reviewed.

JSON schema:
{
  "provider": "groq|gptoss|gemini",
  "model": "string",
  "confidence": 0.0,
  "vote": "approve|reject|needs_more_evidence",
  "rationale_summary": "string",
  "risks": ["string"],
  "test_cases": [
    {
      "name": "string",
      "goal": "string",
      "priority": "low|medium|high",
      "steps": [
        {
          "action": "goto|click|fill|select|assert",
          "selector_hint": "string",
          "value": "string|null",
          "expected_observation": "string|null"
        }
      ],
      "expected_result": "string"
    }
  ]
}
```

## 6.14 Risk Analysis

| Risk | Impact | Mitigation |
|---|---|---|
| AI generates invalid JSON | Test generation fails | Use schema validation and retry |
| LLM providers disagree | Confusing output | Use consensus rules and mark low-confidence decisions for review |
| Free-tier rate limits are reached | Delayed or partial AI output | Use backoff, queue throttling, and degraded consensus mode |
| GPT-OSS local model is unavailable | One council member missing | Allow local endpoint health checks and continue with degraded confidence |
| Agents leave allowed URL scope | Security issue | Strict URL allowlist |
| Too many browser agents consume RAM | System slowdown | Add concurrency limits |
| False positive bugs | Low trust | Add replay validation |
| Dynamic websites break selectors | Failed replay | Use resilient selector strategy |
| Testing causes destructive actions | Data loss | Safe mode and blocked action classifier |
| Large screenshots consume storage | Storage growth | Add retention policy |
| Network instability causes false bugs | Incorrect reports | Retry before bug creation |

## 6.15 Testing Strategy

### Backend Testing

- Unit tests for services.
- API tests for authentication and project APIs.
- Database model tests.
- Authorization tests.

### Worker Testing

- Unit tests for URL scope checker.
- Unit tests for selector resolver.
- Integration tests with demo app.
- Agent timeout tests.
- Bug detection rule tests.

### Frontend Testing

- Component tests.
- Dashboard rendering tests.
- API integration tests.
- Form validation tests.

### End-to-End Testing

Use a demo target app with intentional bugs:

- Broken login validation.
- Broken links.
- HTTP 500 route.
- Hidden button.
- Infinite spinner.
- Form that accepts invalid email.
- Page with JavaScript console error.

## 6.16 Demo Target Application

For demonstration, create a small intentionally buggy web app called **BuggyShop**.

BuggyShop features:

- Home page
- Login page
- Registration page
- Product listing
- Search page
- Cart page
- Checkout page

Intentional bugs:

- Invalid email accepted
- Broken product link
- Checkout crashes with empty cart
- Search button does nothing
- Console error on product page
- Mobile layout overlap
- Infinite spinner on order history

This demo app makes the final project easier to evaluate because BugSwarm can reliably discover visible defects.

## 6.17 Final Submission Package

Recommended final submission contents:

```text
bugswarm-final/
  source-code/
  documentation/
    PRD.md
    TRD.md
    database-schema.md
    ui-ux-design.md
    app-flow.md
    implementation-plan.md
  screenshots/
  demo-video.mp4
  sample-reports/
  presentation.pptx
  README.md
```

Since this document is already combined, it may be submitted as:

```text
BugSwarm_Complete_Documentation.md
```

## 6.18 Final Project Pitch

BugSwarm is an AI-powered software testing swarm that uses multiple autonomous browser agents to test web applications like real users. It combines browser automation, AI-generated test cases, multi-agent exploration, evidence-based bug reporting, replayable test paths, and a developer-friendly dashboard. Unlike basic test automation tools, BugSwarm behaves like a swarm of intelligent QA agents that continuously explore applications, identify broken flows, and generate actionable reports with screenshots and reproduction steps.

---

# Appendix A: Recommended Severity Rules

| Severity | Rule |
|---|---|
| Critical | Data loss, app crash, auth bypass, payment failure |
| High | Broken core flow, login failure, checkout failure |
| Medium | Form validation issue, major UI issue, broken secondary flow |
| Low | Minor UI bug, typo, alignment issue |
| Info | Warning, improvement, weak accessibility issue |

---

# Appendix B: Sample Bug Report

```markdown
# Bug Report: Login form crashes on invalid email

## Severity

High

## Category

Form validation

## Affected URL

https://demo-app.com/login

## Description

The login form crashes when the user enters an invalid email and submits the form.

## Reproduction Steps

1. Open https://demo-app.com/login
2. Enter `abc` in the email field
3. Enter `123` in the password field
4. Click the Login button

## Expected Result

The page should show an email validation error.

## Actual Result

The page throws a JavaScript error and no validation message is displayed.

## Console Error

Cannot read property 'message' of undefined

## Evidence

- Failure screenshot
- Console log
- Network trace
- DOM snapshot

## Suggested Fix

Add client-side validation before submitting the login request and handle undefined error responses safely.
```

---

# Appendix C: Sample Generated Playwright Replay Script

```typescript
import { test, expect } from '@playwright/test';

test('Replay: Login form crashes on invalid email', async ({ page }) => {
  await page.goto('https://demo-app.com/login');

  await page.getByLabel('Email').fill('abc');
  await page.getByLabel('Password').fill('123');
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page.getByText('Invalid email')).toBeVisible();
});
```

---

# Appendix D: Recommended Evaluation Points

For academic evaluation, highlight these points:

1. Multi-agent testing architecture.
2. AI-generated test case design.
3. Browser automation using Playwright.
4. Bug evidence capture.
5. Replayable failed test paths.
6. PostgreSQL schema design.
7. Real-time dashboard.
8. Modular architecture.
9. Safe testing constraints.
10. Practical software engineering relevance.

---

# Appendix E: Possible Viva Questions and Answers

## Question 1: How is BugSwarm different from Selenium test automation?

Selenium or Playwright usually require manually written scripts. BugSwarm uses AI and multiple autonomous agents to explore the application, generate test cases, detect bugs, and create replayable reports automatically.

## Question 2: Why use multiple agents?

Multiple agents allow parallel exploration of different parts of the application. Different agent types can specialize in forms, navigation, visual issues, regression, and edge cases.

## Question 3: How does the system avoid duplicate bugs?

The system generates a bug fingerprint using the bug category, affected URL, error message, and failing selector. If the same fingerprint already exists, the existing bug is updated instead of creating a duplicate.

## Question 4: Why is PostgreSQL suitable?

PostgreSQL is reliable for structured relational data such as users, projects, test runs, agents, bugs, and replay steps. It also supports JSONB, which is useful for storing flexible metadata.

## Question 5: What is the role of AI?

AI is used for generating test cases, creating edge-case input values, summarizing bug reports, classifying severity, and suggesting possible fixes. In the MVP, BugSwarm uses a three-model reasoning council with Groq, GPT-OSS, and Gemini so that important AI decisions are compared before they become final.

## Question 6: What are the main limitations?

The system may produce false positives, may struggle with highly dynamic websites, and must be carefully configured to avoid destructive actions. Replay can also fail if the UI changes after the bug was found.

## Question 7: How can this project be extended?

It can be extended with CI/CD integration, GitHub issue creation, Jira sync, visual regression testing, accessibility audits, Kubernetes-based worker scaling, and additional local LLM providers beyond GPT-OSS.

## Question 8: Why use three LLM models?

Using Groq, GPT-OSS, and Gemini gives the system independent reasoning paths. If two or more models agree and browser evidence supports the claim, the system can trust the result more. If the models disagree, BugSwarm marks the result as lower confidence or asks for human review instead of blindly accepting one AI answer.

---

# End of Document
