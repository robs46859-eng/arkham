# Master Architecture Document

## 1. Purpose

This document defines the target architecture for a modular AI operating system built around a centralized inference gateway, persistent orchestration, low-cost model routing, semantic caching, evolving memory, and reusable vertical applications. The goal is to create a shared backbone that powers multiple products without duplicating infrastructure, while keeping cost, latency, and operational complexity under control.

The architecture is designed to support products such as Stelar, MamaNav, BIM workflows, and future vertical systems through the same core platform. Each product should consume the shared services instead of rebuilding its own routing, memory, or state management.

---

## 2. Architectural Principles

1. **Centralize intelligence infrastructure.** Inference, routing, caching, memory, auth, observability, and billing belong in the platform layer, not inside vertical apps.
2. **Keep verticals thin.** Vertical applications should focus on domain workflows, user interfaces, and structured data models.
3. **Use the cheapest model that satisfies the task.** Model selection must be policy-driven, not hardcoded per feature.
4. **Treat state as a first-class system concern.** Workflow state, operational state, and cognitive state must be separated.
5. **Persist everything required for recovery.** The system must survive crashes, retries, partial execution, and provider outages without losing control.
6. **Normalize all model access behind one interface.** Every provider should be accessed through the same internal contract.
7. **Design for multi-tenancy from the start.** Isolation, quotas, logs, and billing should all be tenant-aware.
8. **Prefer low-cost execution before premium escalation.** Small or cheap models should handle classification, extraction, rewriting, ranking, and light reasoning before premium models are invoked.
9. **Make expensive steps observable and auditable.** Costly reasoning, fallback escalation, and side-effecting actions must be traceable.
10. **Do not let memory become a hidden liability.** Memory must be deliberate, scoped, retrievable, and prunable.

---

## 3. Target System Overview

The platform consists of six major layers:

1. **Client and Vertical Application Layer**
2. **Gateway and Control Plane Layer (Layer8)**
3. **Orchestration Layer**
4. **Memory and Semantic Context Layer**
5. **Shared Data and Domain Systems Layer**
6. **Operations, Security, and Billing Layer**

At runtime, vertical apps send requests through the centralized gateway. The gateway authenticates the tenant, applies routing and policy logic, checks semantic cache, selects the lowest-cost viable model, and either serves a response directly or hands execution to an orchestration flow. Flows coordinate multi-step jobs, retrieve memory and domain data, call models, validate outputs, and persist state transitions. Shared operational systems provide logging, metrics, billing, anomaly detection, and access control.

---

## 4. Core Components

### 4.1 Client and Vertical Application Layer

This layer contains product-specific interfaces and workflows, including:

- Stelar Med Spa
- MamaNav
- FULLSTACK BIM
- Workflow Architect
- Future specialized verticals

Responsibilities:

- Present user interfaces and workflows
- Collect structured inputs
- Render outputs and progress states
- Call platform APIs
- Store product-specific business data
- Avoid direct coupling to model vendors

Non-responsibilities:

- Direct provider integrations
- Custom memory systems
- Custom semantic cache logic
- Duplicated auth or billing logic

### 4.2 Gateway and Control Plane Layer

The gateway is the platform entry point and policy engine. It should be implemented as a FastAPI service with a normalized inference contract and a provider abstraction registry.

Responsibilities:

- Accept all inference requests through a unified endpoint
- Authenticate tenant API keys or OAuth tokens
- Enforce quotas, rate limits, and policy constraints
- Perform request normalization
- Apply semantic cache lookup
- Route requests to the lowest-cost acceptable model
- Escalate to stronger models when confidence or policy requires it
- Emit logs, traces, and billing events
- Return responses in a standardized schema

Subcomponents:

- Request normalizer
- Tenant auth middleware
- Provider registry
- Routing policy engine
- Semantic cache adapter
- Response schema validator
- Cost and usage meter
- Fallback manager

### 4.3 Orchestration Layer

The orchestration layer manages multi-step work using event-driven flows rather than rigid graph wiring. This layer should support resumability, branching, retries, and human checkpoints where needed.

Responsibilities:

- Run long-horizon tasks
- Persist workflow progress
- Coordinate tool calls, model calls, and data access
- Handle branching and escalation
- Separate side effects from reasoning steps
- Support idempotent recovery after failure

Recommended execution model:

- Start event
- Validate request
- Retrieve domain context
- Retrieve memory context
- Run cheap model first
- Evaluate confidence and policy
- Escalate if needed
- Validate output schema
- Commit side effects
- Persist trace and result

### 4.4 Memory and Semantic Context Layer

This layer contains two distinct systems: semantic caching and evolving memory.

#### A. Semantic Cache

Purpose:

Reduce repeated model spend and latency by serving prior responses when query intent is sufficiently similar.

Responsibilities:

- Normalize incoming requests
- Generate embeddings for cacheable requests
- Perform vector similarity lookup
- Apply threshold policy by task type
- Return cached response when safe
- Track hit rate, drift, and savings

Guidance:

- Use conservative thresholds for technical or regulated tasks
- Use more permissive thresholds for FAQ, support, and repeated conversational work
- Exclude highly sensitive or tenant-specific unsafe reuse patterns

#### B. Agentic Memory (A-MEM)

Purpose:

Create a persistent, evolving memory system that stores atomic notes, links related context, and improves future retrieval without dumping raw transcript history into every prompt.

Responsibilities:

- Convert interactions into structured notes
- Tag, summarize, and link notes
- Retrieve relevant notes by task and context
- Evolve note relationships over time
- Enforce scope, retention, and deletion rules
- Keep memory tenant-aware and product-aware

Memory should not be treated as a single blob. It should be separated into:

- User memory
n- Task memory
- Workflow memory
- Domain memory
- Operational memory

### 4.5 Shared Data and Domain Systems Layer

This layer contains structured systems of record used by vertical applications.

Examples:

- Postgres/PostGIS BIM schema
- Med spa CRM and scheduling data
- User profiles and notification preferences
- Billing and subscription records
- Tenant configurations and policy rules

Responsibilities:

- Provide durable structured storage
- Support audit trails and event logs
- Maintain version histories where needed
- Expose domain APIs for orchestration flows

### 4.6 Operations, Security, and Billing Layer

This layer hardens the platform for production.

Responsibilities:

- Observability: logs, metrics, traces, dashboards, alerts
- Security: RBAC, OAuth, service auth, anomaly detection, secrets management
- Billing: usage metering, quotas, plan enforcement, Stripe integration
- Reliability: retries, timeouts, circuit breakers, dead-letter queues, health checks
- Queueing: asynchronous execution for heavy workloads such as BIM parsing or bulk enrichment

---

## 5. Low-Cost Model Strategy

The platform should follow a cost ladder rather than a single-model pattern.

### 5.1 Routing Philosophy

Use the cheapest model that can complete the task correctly. Premium models should be reserved for only the work that actually requires them.

### 5.2 Task-Based Cost Tiers

**Tier 0: Deterministic or non-LLM first**

Use code, rules, templates, regex, SQL, vector similarity, search, and precomputed mappings before calling any model.

Good for:

- Validation
- Field mapping
- Status checks
- Structured routing
- Template filling
- Cache lookup
- Threshold checks

**Tier 1: Very cheap small models**

Use low-cost models or local SLMs for:

- Classification
- Intent detection
- Tagging
- Summarization of short text
- Rewriting
- Extraction into known schemas
- Memory note creation
- Lightweight routing decisions

**Tier 2: Mid-cost models**

Use for:

- Moderate reasoning
- Multi-field extraction from messy text
- Controlled drafting
- Tool selection
- Multi-step planning under schema constraints

**Tier 3: Premium models**

Reserve for:

- High-stakes reasoning
- Complex synthesis
- Ambiguous planning
- Safety-sensitive decisions
- Deep cross-document analysis
- High-value user-facing outputs

### 5.3 Escalation Rules

Escalate only when:

- Confidence is below threshold
- Output fails validation
- User tier or workflow policy requires premium handling
- Context length exceeds small-model capacity
- Task is explicitly high-risk or business-critical

### 5.4 Cost Controls

- Default every workflow to low-cost mode
- Require policy-based premium escalation
- Cache embeddings and reusable notes
- Use batch jobs for non-urgent processing
- Track cost per tenant, workflow, and feature
- Create alerts for unusual premium-model usage

---

## 6. State Management Model

State must be explicitly separated into three categories.

### 6.1 Workflow State

What step the flow is currently in.

Examples:

- started
- waiting_for_data
- retrieved_memory
- awaiting_validation
- complete
- failed

### 6.2 Operational State

Execution guarantees and recovery metadata.

Examples:

- retry count
- idempotency key
- timeout budget
- queue status
- last successful checkpoint

### 6.3 Cognitive State

What context is available to the model.

Examples:

- retrieved memory notes
- domain records
- user preferences
- relevant prior actions

This separation is mandatory. It prevents hidden state drift and makes retry behavior safe.

---

## 7. Request Lifecycle

1. Client submits request to gateway.
2. Gateway authenticates tenant and validates quota.
3. Request is normalized and classified.
4. Semantic cache is checked.
5. If cache hit is valid, response is returned.
6. If cache miss, routing policy selects cheapest viable execution path.
7. If task is simple, gateway invokes model directly.
8. If task is multi-step, orchestration flow is triggered.
9. Flow retrieves memory and domain context.
10. Cheap model executes first.
11. Output is validated against schema or policy.
12. If validation fails, escalate or repair.
13. If side effects are required, commit them idempotently.
14. Persist workflow state, trace, cost, and result.
15. Optionally write a memory note.
16. Return normalized response.

---

## 8. Data Stores

### 8.1 Postgres

Primary structured system of record.

Use for:

- tenants
- users
- subscriptions
- workflow records
- domain entities
- audit logs
- billing summaries

### 8.2 Redis

Operational state and high-speed control data.

Use for:

- rate limits
- locks
- short TTL sessions
- queue coordination
- temporary execution state

### 8.3 Vector Store

Use FAISS or LanceDB for:

- semantic cache lookup
- memory retrieval
- similarity search
- embedding-based recommendations

### 8.4 Object Storage

Use for:

- artifacts
- uploads
- generated files
- logs or snapshots when needed

---

## 9. Security Model

### 9.1 Tenant Isolation

Every request, cache entry, memory note, workflow, and billing record must be tenant-scoped.

### 9.2 Access Control

Implement RBAC for platform admins, tenant admins, staff users, and service roles.

### 9.3 Secrets Management

No provider keys or secrets should live in application code or frontend clients.

### 9.4 Sensitive Data Handling

Sensitive verticals such as maternal, medical, and regulated business flows must enforce:

- restricted logging
- redaction rules
- scoped retention
- explicit data sharing rules
- encrypted storage where needed

### 9.5 Anomaly Detection

Track:

- unusual cost spikes
- auth failures
- routing failures
- abnormal premium model usage
- suspicious cross-tenant access attempts

---

## 10. Reliability Requirements

The platform must be able to survive provider failures, partial executions, and restarts.

Required controls:

- health checks
- readiness checks
- startup validation
- request timeouts
- retry policy
- fallback policy
- circuit breakers
- dead-letter queue
- durable checkpoints
- idempotent side effects

---

## 11. Observability Requirements

Every request and workflow should emit:

- request id
- tenant id
- workflow id
- model used
- tokens or usage estimate
- cost estimate
- latency
- cache hit or miss
- escalation event
- validation result
- failure reason

Dashboards should expose:

- cost by tenant
- cost by workflow
- cache hit rate
- premium escalation rate
- workflow success rate
- provider failure rate
- latency percentiles
- memory retrieval usefulness

---

## 12. Delivery Roadmap

### Phase 1: Core Foundation

- Stand up Postgres, Redis, vector store, object storage
- Implement gateway skeleton
- Build provider registry
- Define normalized inference schema
- Add tenant auth and rate limiting
- Add health and readiness endpoints

### Phase 2: Cost Discipline

- Add semantic cache
- Add cheap-model routing rules
- Add usage tracking and billing events
- Add fallback and escalation logic

### Phase 3: Persistent Intelligence

- Implement orchestration flows
- Add workflow state persistence
- Implement A-MEM note creation and retrieval
- Add schema validation and repair passes

### Phase 4: Production Hardening

- Add RBAC and OAuth
- Add metrics, traces, and alerts
- Add queueing for heavy jobs
- Add anomaly detection
- Add admin control plane

### Phase 5: First Vertical Proof

- Connect one vertical product end to end
- Launch one real workflow through the shared backbone
- Test tenant isolation, recovery, and cost behavior
- Expand only after shared services are stable

---

## 13. Recommended First Vertical Rule

Choose the vertical that gives the cleanest proof of value with the fewest special-case requirements. The first vertical should validate:

- gateway routing
- semantic cache
- one orchestration flow
- memory write and retrieval
- billing and tenant metering
- observability

Do not launch multiple verticals until one complete loop works cleanly.

---

## 14. Non-Negotiable Build Rules

1. No direct model calls from vertical apps.
2. No duplicated auth, memory, or caching logic in products.
3. No premium model by default.
4. No side effects without idempotency.
5. No unscoped memory.
6. No cross-tenant cache or retrieval leakage.
7. No workflow without persisted checkpoints.
8. No production release without logs, metrics, and failure visibility.
9. No schema-free outputs at critical boundaries.
10. No expansion into multiple verticals before the first one proves the backbone.

---

## 15. Initial Open Decisions

The following implementation choices are now set for the first build:

- **Routing strategy:** Hybrid model stack with local routing and classification as the default first layer
- **Primary first vertical:** BIM
- **Gateway role:** Central policy and inference control plane for BIM and future verticals
- **Cost discipline:** Local and low-cost paths must be exhausted before premium escalation

Remaining decisions to finalize:

- Which exact local models will handle routing, classification, extraction, and summarization
- Which API providers will act as mid-tier and premium escalation targets
- Which vector store is canonical for cache and memory
- Which BIM workflows are phase-one priorities
- Which BIM data classes require stricter validation and auditability
- Which admin controls belong in the first release

## 16. BIM-First Hybrid Implementation Profile

This architecture will be implemented as a **hybrid model system**.

### 16.1 Hybrid Execution Policy

The execution ladder for the first build is:

1. **Deterministic systems first**
   - Rules
   - schema validation
   - SQL queries
   - template generation
   - geometric checks
   - direct BIM data retrieval
2. **Local models second**
   - routing
   - classification
   - tagging
   - note creation
   - lightweight extraction
   - short summarization
3. **Low-cost API models third**
   - moderate reasoning
   - messy document extraction
   - controlled drafting
   - structured transformation of BIM context
4. **Premium API models last**
   - ambiguous reasoning
   - complex cross-document synthesis
   - high-value client-facing outputs
   - difficult planning or repair after failed validation

This means the platform should not treat every BIM interaction as a premium LLM task. Many BIM workflows are better handled by structured data operations plus local model assistance.

### 16.2 Why BIM is the Right First Vertical

BIM is the strongest first proof because it forces the platform to stay grounded in structured data instead of drifting into vague chat behavior. It is a good first vertical for a control-plane architecture because it naturally requires:

- strict schemas
- versioning
- audit trails
- heavy structured retrieval
- large file and artifact handling
- workflow checkpoints
- long-lived task state
- queueing for expensive jobs

A BIM-first launch will validate the backbone more rigorously than a lighter marketing or CRM workflow because it stresses ingestion, parsing, enrichment, retrieval, orchestration, and artifact generation.

### 16.3 BIM-First Phase One Scope

The first BIM release should stay narrow and prove one complete loop. Recommended phase-one scope:

- ingest IFC or related building data
- parse and normalize building elements into structured records
- persist entities and change history in Postgres/PostGIS
- enable semantic retrieval across building elements, notes, and model metadata
- support one orchestration workflow for analysis or reporting
- generate one reliable end output such as a compliance summary, model issue summary, or project status artifact

Avoid trying to solve every BIM use case in version one. The first goal is a stable end-to-end backbone.

### 16.4 BIM-Specific Core Services

#### A. BIM Ingestion Service

Responsibilities:

- accept uploaded IFC and related project files
- validate format and metadata
- extract core entities
- create normalized records
- push heavy parsing into queues when needed

#### B. BIM Domain Store

Responsibilities:

- store building elements
- store relationships between elements
- track location, materials, quantities, and classifications
- preserve version history and change logs
- expose queryable APIs for orchestration and UI layers

#### C. BIM Semantic Layer

Responsibilities:

- create embeddings for selected descriptive content
- support semantic search over notes, issues, model summaries, and linked project context
- avoid embedding raw data that is better queried deterministically

#### D. BIM Workflow Engine

Responsibilities:

- run analysis and reporting jobs
- coordinate retrieval across structured and semantic systems
- manage retries and checkpoints
- write auditable outputs

### 16.5 BIM Task Routing Policy

Use deterministic systems or local models for:

- element classification
- property extraction into known schema
- issue tagging
- naming cleanup
- short summaries of single records
- routing a user request to the right workflow

Use low-cost API models for:

- converting messy notes into structured BIM issues
- drafting project summaries from selected records
- moderate synthesis across a bounded set of model elements

Use premium API models only for:

- ambiguous cross-document reasoning
- difficult compliance interpretation
- high-stakes narrative outputs for clients or stakeholders
- repair when lower-cost outputs fail structured validation

### 16.6 BIM Data Discipline Rules

1. Structured BIM facts must come from the domain store, not from model memory.
2. Memory may summarize or relate BIM work, but it must not become the source of truth for geometry, quantities, or compliance-critical attributes.
3. Every generated BIM output should reference the underlying records or artifacts used to create it.
4. Heavy parsing and enrichment must run through queues and checkpointed workflows.
5. Validation must occur before any client-facing report is released.

### 16.7 Recommended First BIM Workflow

The cleanest first workflow is:

- user uploads IFC or project package
- ingestion service validates and parses it
- records are written to the BIM domain store
- orchestration flow builds summaries and detects a narrow class of issues
- semantic layer stores searchable notes and summaries
- gateway returns a project analysis result through a normalized response contract
- admin layer records usage, cost, status, and artifacts

This first loop proves the gateway, queueing, orchestration, structured storage, retrieval, memory, and reporting path in one vertical.

## 17. BIM Repository Specification

This repository should be organized as a workspace-based monorepo so the gateway, BIM services, orchestration layer, shared schemas, and frontend can evolve together without becoming tightly coupled. The repo should separate platform services from product-specific interfaces while preserving shared contracts.

### 17.1 Monorepo Top Level

This repo should be optimized for a team structure now, even if one person starts it. That means clear service boundaries, shared contracts, strict package ownership, and enough separation that services can be extracted later without a rewrite.

```text
fullstackai-bim/
├── apps/
│   ├── web/
│   │   ├── src/
│   │   │   ├── app/
│   │   │   ├── components/
│   │   │   ├── features/
│   │   │   │   ├── projects/
│   │   │   │   ├── uploads/
│   │   │   │   ├── issues/
│   │   │   │   ├── deliverables/
│   │   │   │   └── search/
│   │   │   ├── lib/
│   │   │   ├── styles/
│   │   │   └── types/
│   │   ├── public/
│   │   ├── package.json
│   │   └── README.md
│   ├── admin/
│   │   ├── src/
│   │   │   ├── app/
│   │   │   ├── components/
│   │   │   ├── features/
│   │   │   │   ├── tenants/
│   │   │   │   ├── workflows/
│   │   │   │   ├── usage/
│   │   │   │   └── alerts/
│   │   │   └── lib/
│   │   ├── package.json
│   │   └── README.md
│   └── docs/
│       ├── content/
│       ├── package.json
│       └── README.md
├── services/
│   ├── gateway/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── v1/
│   │   │   │   └── health/
│   │   │   ├── auth/
│   │   │   ├── middleware/
│   │   │   ├── policies/
│   │   │   ├── providers/
│   │   │   ├── routing/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   ├── observability/
│   │   │   ├── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── bim_ingestion/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── parsers/
│   │   │   │   ├── ifc/
│   │   │   │   ├── pdf/
│   │   │   │   ├── schedules/
│   │   │   │   └── markups/
│   │   │   ├── normalization/
│   │   │   ├── validators/
│   │   │   ├── mappers/
│   │   │   ├── storage/
│   │   │   ├── jobs/
│   │   │   ├── schemas/
│   │   │   ├── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── orchestration/
│   │   ├── app/
│   │   │   ├── flows/
│   │   │   ├── tasks/
│   │   │   ├── checkpoints/
│   │   │   ├── queues/
│   │   │   ├── policies/
│   │   │   ├── schemas/
│   │   │   ├── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── memory/
│   │   ├── app/
│   │   │   ├── notes/
│   │   │   ├── links/
│   │   │   ├── retrieval/
│   │   │   ├── pruning/
│   │   │   ├── schemas/
│   │   │   ├── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── semantic-cache/
│   │   ├── app/
│   │   │   ├── embeddings/
│   │   │   ├── lookup/
│   │   │   ├── policies/
│   │   │   ├── storage/
│   │   │   ├── schemas/
│   │   │   ├── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── billing/
│   │   ├── app/
│   │   │   ├── metering/
│   │   │   ├── plans/
│   │   │   ├── stripe/
│   │   │   ├── webhooks/
│   │   │   ├── schemas/
│   │   │   ├── settings.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   └── notifications/
│       ├── app/
│       │   ├── email/
│       │   ├── webhooks/
│       │   ├── events/
│       │   ├── schemas/
│       │   ├── settings.py
│       │   └── main.py
│       ├── tests/
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── README.md
├── workers/
│   ├── bim-parser/
│   │   ├── app/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── pdf-extractor/
│   │   ├── app/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── schedule-normalizer/
│   │   ├── app/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── report-generator/
│       ├── app/
│       ├── tests/
│       ├── Dockerfile
│       └── pyproject.toml
├── packages/
│   ├── schemas/
│   │   ├── python/
│   │   ├── typescript/
│   │   └── README.md
│   ├── sdk/
│   │   ├── src/
│   │   ├── package.json
│   │   └── README.md
│   ├── ui/
│   │   ├── src/
│   │   ├── package.json
│   │   └── README.md
│   ├── config/
│   │   ├── python/
│   │   ├── typescript/
│   │   └── README.md
│   ├── prompts/
│   │   ├── routing/
│   │   ├── extraction/
│   │   ├── reporting/
│   │   └── README.md
│   └── test-fixtures/
│       ├── ifc/
│       ├── pdf/
│       ├── schedules/
│       ├── markups/
│       └── README.md
├── infra/
│   ├── docker/
│   │   ├── docker-compose.local.yml
│   │   └── docker-compose.observability.yml
│   ├── k8s/
│   ├── terraform/
│   ├── monitoring/
│   │   ├── grafana/
│   │   ├── prometheus/
│   │   └── alerts/
│   └── scripts/
├── data/
│   ├── sample-projects/
│   ├── seeds/
│   └── migrations/
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── workflows/
│   ├── deliverables/
│   ├── runbooks/
│   └── decisions/
├── .github/
│   └── workflows/
├── Makefile
├── pnpm-workspace.yaml
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

### 17.1.1 Team Ownership Model

The folder tree is designed so teams can own clear surfaces:

- **Platform team:** `services/gateway`, `services/semantic-cache`, `services/memory`, `packages/schemas`, `packages/config`
- **BIM systems team:** `services/bim_ingestion`, `workers/bim-parser`, `workers/pdf-extractor`, `workers/schedule-normalizer`, `workers/report-generator`
- **Workflow team:** `services/orchestration`, `packages/prompts`
- **Product/UI team:** `apps/web`, `apps/admin`, `packages/ui`, `packages/sdk`
- **Infra/ops team:** `infra`, `.github`, root tooling

This makes later service extraction easier because ownership lines already exist in the repo.

### 17.1.2 Starter Files

The following files should exist on day one.

#### Root `README.md`

Use the following as the actual starter `README.md` content:

```md
# FullStackAi BIM

FullStackAi BIM is a BIM-first AI platform built as a team-oriented monorepo. It combines a centralized inference gateway, structured BIM ingestion, event-driven orchestration, semantic caching, agentic memory, and deliverable generation into one shared backbone.

The first implementation supports IFC, PDFs, schedules, and markups. The system is designed so services can split out later without changing the platform contract model.

## Goals

- keep BIM facts grounded in structured systems, not freeform model memory
- use deterministic logic and local models wherever possible
- escalate to API models only when needed
- preserve tenant isolation, workflow recoverability, and auditability
- generate explicit BIM deliverables from traceable source data

## Repository Layout

```text
apps/           Product interfaces such as the BIM dashboard and admin UI
services/       Core platform services
workers/        Heavy async jobs such as IFC parsing and PDF extraction
packages/       Shared schemas, SDKs, UI, config, prompts, and test fixtures
infra/          Docker, deployment, monitoring, and operational scripts
data/           Seeds, migrations, and sample projects
docs/           Architecture, API references, workflows, decisions, and runbooks
```

## Core Services

- `gateway` — Layer8-style control plane for auth, routing, policy, usage metering, and normalized inference
- `bim-ingestion` — intake and normalization for IFC, PDFs, schedules, and markups
- `orchestration` — event-driven workflows, checkpoints, retries, and long-running tasks
- `memory` — project-aware memory notes, linking, retrieval, and pruning
- `semantic-cache` — embeddings, lookup, threshold policy, and cache reuse
- `billing` — usage metering and Stripe integration
- `notifications` — event delivery, webhook fanout, and user-facing status notifications

## First Deliverables

The v1 system is expected to produce:

- Project Intake Summary
- Model Element Summary
- Document and Markup Summary
- Issue Register
- Project Deliverable Package

All deliverables must be traceable back to source files and structured records.

## Technology Direction

### Backend
- Python services with FastAPI and typed settings
- Postgres/PostGIS for domain data
- Redis for operational state and queues
- LanceDB or FAISS for semantic cache and memory retrieval
- Docker Compose for local development

### Frontend
- TypeScript apps for the BIM dashboard and admin console
- shared UI and SDK packages in `packages/`

### Model Strategy
- deterministic systems first
- local models for routing, classification, tagging, and light extraction
- low-cost API models for bounded synthesis
- premium API models only for ambiguous or high-stakes tasks

## Local Development Prerequisites

Install the following before starting:

- Docker and Docker Compose
- Python 3.11+
- Node.js 20+
- pnpm 9+
- Make
- Ollama or another local model runtime

## Quick Start

1. Copy environment defaults:

   ```bash
   cp .env.example .env
   ```

2. Start local infrastructure:

   ```bash
   make up
   ```

3. Run database migrations:

   ```bash
   make migrate
   ```

4. Start backend services:

   ```bash
   make dev-backend
   ```

5. Start frontend apps:

   ```bash
   make dev-frontend
   ```

6. Open the BIM web app and admin app.

## Common Commands

```bash
make up               # start local infra and core services
make down             # stop local stack
make logs             # stream docker logs
make migrate          # run database migrations
make lint             # run python and typescript linting
make test             # run all tests
make dev-backend      # start python services in dev mode
make dev-frontend     # start frontend apps in dev mode
make seed             # seed local dev data
```

## Configuration

Primary environment values live in `.env`.

Important groups:

- database and redis
- object storage
- vector store
- gateway auth
- local model runtime
- API provider credentials
- observability
- billing

Each service should validate its required settings at startup and fail fast if they are missing.

## Team Ownership

- Platform team owns `services/gateway`, `services/memory`, `services/semantic-cache`, `packages/schemas`, and `packages/config`
- BIM systems team owns `services/bim_ingestion` and BIM workers
- Workflow team owns `services/orchestration` and `packages/prompts`
- Product team owns `apps/web`, `apps/admin`, `packages/ui`, and `packages/sdk`
- Infra team owns `infra/`, root tooling, CI, and deployment workflows

## Non-Negotiable Rules

- no direct model calls from frontend apps
- no duplicated schema definitions across services
- no premium model by default
- no side effects without idempotency
- no deliverable generation without source traceability
- no production release without logs, metrics, and health checks

## Documentation

- architecture docs: `docs/architecture/`
- API references: `docs/api/`
- workflow docs: `docs/workflows/`
- deliverable specs: `docs/deliverables/`
- runbooks: `docs/runbooks/`
- architecture decisions: `docs/decisions/`

## Current Build Order

1. root repo and config
2. shared schemas
3. local infra
4. gateway skeleton
5. BIM ingestion with IFC first
6. PDF, schedule, and markup ingestion
7. orchestration workflows
8. memory and semantic cache
9. web UI and admin UI
10. deliverables and operational hardening
```

#### Root `.env.example`

Use the following as the actual starter `.env.example` content:

```env
# -----------------------------------------------------------------------------
# Core Application
# -----------------------------------------------------------------------------
ENV=local
APP_NAME=fullstackai-bim
LOG_LEVEL=info
DEFAULT_TIMEZONE=America/Denver

# -----------------------------------------------------------------------------
# Network / Ports
# -----------------------------------------------------------------------------
WEB_PORT=3000
ADMIN_PORT=3001
GATEWAY_PORT=8000
INGESTION_PORT=8001
ORCHESTRATION_PORT=8002
MEMORY_PORT=8003
SEMANTIC_CACHE_PORT=8004
BILLING_PORT=8005
NOTIFICATIONS_PORT=8006
OLLAMA_PORT=11434
POSTGRES_PORT=5432
REDIS_PORT=6379
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
POSTGRES_DB=fullstackai_bim
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fullstackai_bim

# -----------------------------------------------------------------------------
# Redis
# -----------------------------------------------------------------------------
REDIS_HOST=localhost
REDIS_URL=redis://localhost:6379/0
QUEUE_URL=redis://localhost:6379/1

# -----------------------------------------------------------------------------
# Object Storage
# -----------------------------------------------------------------------------
S3_ENDPOINT=http://localhost:9000
S3_REGION=us-east-1
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET_RAW_UPLOADS=raw-uploads
S3_BUCKET_ARTIFACTS=artifacts
S3_BUCKET_REPORTS=reports

# -----------------------------------------------------------------------------
# Vector Store
# -----------------------------------------------------------------------------
VECTOR_STORE=lancedb
VECTOR_STORE_PATH=./.local/lancedb
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=nomic-embed-text

# -----------------------------------------------------------------------------
# Gateway Auth / Platform Policy
# -----------------------------------------------------------------------------
GATEWAY_SIGNING_KEY=replace-me
TENANT_API_KEY_PREFIX=fsbim_
DEFAULT_MODEL_POLICY=hybrid_local_first
DEFAULT_PREMIUM_ESCALATION=false
STRICT_SCHEMA_VALIDATION=true

# -----------------------------------------------------------------------------
# Local Model Runtime
# -----------------------------------------------------------------------------
OLLAMA_HOST=http://localhost:11434
LOCAL_ROUTER_MODEL=qwen2.5:7b
LOCAL_CLASSIFIER_MODEL=qwen2.5:3b
LOCAL_SUMMARY_MODEL=qwen2.5:7b
LOCAL_EXTRACTION_MODEL=qwen2.5:7b
LOCAL_REPAIR_MODEL=qwen2.5:7b

# -----------------------------------------------------------------------------
# External Model Providers
# -----------------------------------------------------------------------------
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MID_TIER_MODEL=
OPENAI_PREMIUM_MODEL=

GEMINI_API_KEY=
GEMINI_BASE_URL=
GEMINI_MID_TIER_MODEL=
GEMINI_PREMIUM_MODEL=

ANTHROPIC_API_KEY=
ANTHROPIC_BASE_URL=
ANTHROPIC_MID_TIER_MODEL=
ANTHROPIC_PREMIUM_MODEL=

# -----------------------------------------------------------------------------
# Billing
# -----------------------------------------------------------------------------
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
BILLING_ENABLED=false

# -----------------------------------------------------------------------------
# Observability
# -----------------------------------------------------------------------------
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
PROMETHEUS_ENABLED=true
TRACE_SAMPLE_RATE=1.0

# -----------------------------------------------------------------------------
# Deliverables / Reporting
# -----------------------------------------------------------------------------
DEFAULT_REPORT_FORMAT=html
ENABLE_PDF_REPORTS=true
SOURCE_TRACE_REQUIRED=true
ISSUE_CONFIDENCE_THRESHOLD=0.80

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------
ENABLE_IFC_INGESTION=true
ENABLE_PDF_INGESTION=true
ENABLE_SCHEDULE_INGESTION=true
ENABLE_MARKUP_INGESTION=true
ENABLE_MEMORY_WRITES=true
ENABLE_SEMANTIC_CACHE=true
ENABLE_PREMIUM_ESCALATION=false
```

#### Root `Makefile`

Use the following as the actual starter `Makefile` content:

```make
COMPOSE_FILE=infra/docker/docker-compose.local.yml

up:
	docker compose -f $(COMPOSE_FILE) up -d --build

down:
	docker compose -f $(COMPOSE_FILE) down

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

ps:
	docker compose -f $(COMPOSE_FILE) ps

migrate:
	python data/migrations/run.py

seed:
	python data/seeds/seed_dev.py

lint:
	ruff check . && pnpm -r lint

format:
	ruff format . && pnpm -r format

test:
	pytest && pnpm -r test

smoke:
	pytest -m smoke

dev-backend:
	@echo "Start backend services individually from their service folders or via your process manager."

dev-frontend:
	pnpm --filter web dev & pnpm --filter admin dev

pull-models:
	ollama pull qwen2.5:3b && ollama pull qwen2.5:7b && ollama pull nomic-embed-text

check-env:
	python infra/scripts/check_env.py
```

#### Root `pnpm-workspace.yaml`

Use the following as the actual starter `pnpm-workspace.yaml` content:

```yaml
packages:
  - apps/*
  - packages/*
```

#### Root `pyproject.toml`

Use the following as the actual starter `pyproject.toml` content:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "fullstackai-bim"
version = "0.1.0"
description = "BIM-first AI platform monorepo"
requires-python = ">=3.11"

dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "sqlalchemy>=2.0",
  "psycopg[binary]>=3.1",
  "redis>=5.0",
  "httpx>=0.27",
  "structlog>=24.1",
  "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "ruff>=0.5",
  "mypy>=1.10",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
testpaths = ["services", "workers"]
pythonpath = ["."]
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
```

#### Root `.gitignore`

Use the following as the actual starter `.gitignore` content:

```gitignore
# Python
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.venv/

# Node
node_modules/
.pnpm-store/
.next/
dist/
coverage/

# Environment
.env
.env.*
!.env.example

# Local data
.local/
*.log

# OS / Editor
.DS_Store
.vscode/
.idea/

# Build artifacts
build/
*.egg-info/
```

#### `infra/scripts/check_env.py`

Use the following as the actual starter `infra/scripts/check_env.py` content:

```python
from pathlib import Path
import sys

REQUIRED = [
    "DATABASE_URL",
    "REDIS_URL",
    "S3_ENDPOINT",
    "VECTOR_STORE",
    "OLLAMA_HOST",
]


def main() -> int:
    env_path = Path(".env")
    if not env_path.exists():
        print("Missing .env file. Copy .env.example to .env first.")
        return 1

    values = {}
    for line in env_path.read_text().splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        print("Missing required environment values:")
        for key in missing:
            print(f"- {key}")
        return 1

    print("Environment looks usable for local development.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

#### `infra/docker/docker-compose.local.yml`

Should start:

- postgres
- redis
- minio
- ollama or local model runtime
- optional lancedb-backed service wrapper if needed
- gateway
- bim-ingestion
- orchestration

Suggested initial intent:

```yaml
services:
  postgres:
    image: postgres:16
  redis:
    image: redis:7
  minio:
    image: minio/minio
  ollama:
    image: ollama/ollama
  gateway:
    build: ../../services/gateway
  bim-ingestion:
    build: ../../services/bim_ingestion
  orchestration:
    build: ../../services/orchestration
```

#### Service `README.md`

Each service should document:

- purpose
- owned data/contracts
- inbound APIs
- outbound dependencies
- local start command
- test command
- env vars used

#### Service `settings.py`

Each Python service should start with a typed settings module using Pydantic settings so environment validation happens at startup.

Suggested shape:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str
    log_level: str = "info"
    database_url: str
    redis_url: str

    class Config:
        env_file = ".env"
```

#### Service `main.py`

Each service should expose:

- app bootstrap
- startup validation
- health endpoint
- readiness endpoint

#### `packages/schemas/README.md`

Should define canonical ownership of shared contracts and versioning rules.

Suggested guidance:

```md
# Shared Schemas

This package contains canonical contracts used across gateway, ingestion, orchestration, workers, and UI clients.

Rules:
- schema changes must be versioned
- breaking changes require migration notes
- critical deliverable payloads must remain backward-compatible when possible
```

#### `packages/test-fixtures/README.md`

Should explain how fixtures are organized and what each fixture proves.

Suggested guidance:

```md
# Test Fixtures

Fixtures are grouped by source type:
- IFC
- PDF
- schedules
- markups

Each fixture should include a short note describing expected extraction and validation outcomes.
```

#### `.github/workflows/ci.yml`

Should run:

- Python lint/tests
- TypeScript lint/build
- schema compatibility checks
- fixture ingestion smoke tests

### 17.1.3 Day-One Contracts

The first schemas you should write before serious coding begins are:

- `Tenant`
- `Project`
- `ProjectFile`
- `IngestionJob`
- `BuildingElement`
- `DocumentChunk`
- `ScheduleRecord`
- `MarkupRecord`
- `IssueRecord`
- `DeliverableArtifact`
- `WorkflowRun`
- `UsageEvent`
- `MemoryNote`

Those contracts should live in `packages/schemas` and be imported everywhere else instead of redefined per service.

### 17.2 Service Responsibilities

#### apps/web

The BIM-facing product UI. It should support:

- project creation
- file upload
- parsing status
- model summaries
- issue views
- deliverables view
- search across records and notes
- export/download interfaces

#### services/gateway

FastAPI-based Layer8 control plane.

Key folders:

```text
services/gateway/
├── app/
│   ├── api/
│   ├── middleware/
│   ├── providers/
│   ├── routing/
│   ├── auth/
│   ├── policies/
│   ├── schemas/
│   ├── observability/
│   └── main.py
├── tests/
├── Dockerfile
└── pyproject.toml
```

#### services/bim_ingestion

Responsible for intake and normalization of IFC, PDFs, schedules, and markups.

Key folders:

```text
services/bim_ingestion/
├── app/
│   ├── api/
│   ├── parsers/
│   │   ├── ifc/
│   │   ├── pdf/
│   │   ├── schedules/
│   │   └── markups/
│   ├── normalization/
│   ├── validators/
│   ├── mappers/
│   ├── storage/
│   └── jobs/
├── tests/
└── pyproject.toml
```

#### services/orchestration

Runs event-driven BIM workflows.

Examples:

- parse project package
- generate project summary
- detect issue classes
- create deliverable package
- run compliance or change analysis later

#### services/memory

Stores structured memory notes and relationships for project context, prior issues, analyst notes, and workflow summaries.

#### services/semantic-cache

Performs query normalization, embeddings, similarity search, and cache retrieval with tenant and project scoping.

### 17.3 Domain Model Packages

The shared schema package should define normalized contracts for:

- tenants
- projects
- project files
- building elements
- document chunks
- schedules
- markups
- issues
- workflows
- artifacts
- deliverables
- usage events
- memory notes

This package should be the contract boundary between services.

### 17.4 Deliverables Specification

Because the first BIM release includes IFC plus PDFs, schedules, and markups, the system should define exactly what outputs it is expected to produce. The first deliverables should be narrow and auditable.

Recommended v1 deliverables:

1. **Project Intake Summary**
   - uploaded files inventory
   - detected disciplines
   - parse status by source
   - missing or invalid inputs

2. **Model Element Summary**
   - counts by category and discipline
   - key quantities if available
   - level or zone distribution
   - unresolved parse gaps

3. **Document and Markup Summary**
   - extracted document set
   - markup count and linked references
   - schedule detection and normalization status
   - unresolved extraction confidence flags

4. **Issue Register**
   - detected issues
   - issue type
   - severity
   - source reference
   - linked element or document where possible

5. **Project Deliverable Package**
   - machine-readable JSON export
   - human-readable summary PDF or HTML report
   - trace metadata for source provenance

These deliverables should be explicitly versioned so the system can evolve without breaking downstream use.

### 17.5 Ingestion Requirements by Source Type

#### IFC

Need:

- parser worker
- entity normalization
- building element mapper
- property set extraction
- relationship extraction
- optional geometry reference handling
- change log support

#### PDFs

Need:

- text extraction
- page chunking
- table detection where feasible
- source page referencing
- confidence scoring
- links back to original file and page

#### Schedules

Need:

- CSV/XLSX/PDF schedule ingestion path
- normalization into structured rows
- date and milestone standardization
- activity/status mapping
- source traceability

#### Markups

Need:

- support for uploaded markup exports or annotated PDFs/images
- extraction of comments, tags, coordinates, or page references where available
- linkage to issues and project files
- reviewer and timestamp support if present

### 17.6 Suggested Initial Tech Split

Use:

- Python for gateway, ingestion, orchestration, parsing, and workers
- TypeScript for frontend apps and shared SDK if needed
- Postgres/PostGIS for core domain data
- Redis for operational state and queues
- FAISS or LanceDB for semantic cache and memory retrieval
- Docker Compose for local development first
- Terraform only after the local system proves itself

### 17.7 CI/CD and Quality Gates

The repo should enforce:

- linting for Python and TypeScript
- schema tests
- contract tests between gateway and services
- fixture-based ingestion tests for IFC, PDFs, schedules, and markups
- workflow replay tests
- tenant isolation tests
- cache correctness tests
- artifact generation tests

A pull request should not merge if fixture ingestion or schema compatibility breaks.

### 17.8 Recommended Build Order Inside the Repo

1. create repo skeleton
2. add shared schemas package
3. stand up Postgres, Redis, and local vector store
4. build gateway skeleton
5. build BIM ingestion service with IFC first
6. add PDF, schedule, and markup ingestion paths
7. add orchestration workflows
8. add semantic cache and memory services
9. add web UI for upload, status, and outputs
10. add deliverable generation and admin monitoring

## 18. System Contracts Document

This document defines the **non-negotiable contracts** between all services. These contracts ensure that services can evolve independently, scale independently, and eventually split into separate repositories without breaking the system.

These are not suggestions. These are the rules every service must follow.

---

## 18.1 Core Philosophy

- All services communicate through **explicit schemas**
- No service depends on another service’s internal implementation
- All external-facing responses are **normalized and versioned**
- Every contract is **tenant-scoped**
- Every contract is **traceable and auditable**

---

## 18.2 Global Identifiers

Every entity in the system must follow a consistent ID structure.

Format:

```text
<type>_<ulid>
```

Examples:

- tenant_01H...
- proj_01H...
- file_01H...
- elem_01H...
- issue_01H...
- wf_01H...

Rules:

- IDs must be globally unique
- IDs must be generated at the service boundary, not inside workflows
- IDs must be passed across all services without transformation

---

## 18.3 Gateway Contract (Inference)

### Request

```json
{
  "tenant_id": "tenant_...",
  "project_id": "proj_...",
  "task_type": "classification | extraction | summary | workflow",
  "input": {
    "text": "...",
    "context": {},
    "references": []
  },
  "options": {
    "allow_premium": false,
    "require_schema": true
  }
}
```

### Response

```json
{
  "request_id": "req_...",
  "tenant_id": "tenant_...",
  "model_used": "local | mid | premium",
  "cache_hit": true,
  "latency_ms": 120,
  "cost_estimate": 0.0001,
  "output": {},
  "validation": {
    "passed": true,
    "errors": []
  }
}
```

Rules:

- Gateway always returns normalized structure
- No raw provider responses exposed
- All outputs must pass schema validation if required

---

## 18.4 Ingestion Contract

### Input

```json
{
  "tenant_id": "tenant_...",
  "project_id": "proj_...",
  "file_id": "file_...",
  "file_type": "ifc | pdf | schedule | markup",
  "storage_path": "s3://..."
}
```

### Output

```json
{
  "job_id": "job_...",
  "status": "queued | processing | complete | failed",
  "entities_created": 120,
  "errors": []
}
```

Rules:

- Ingestion must be asynchronous
- Must emit structured records only
- Must not return inferred facts as truth

---

## 18.5 Building Element Contract

```json
{
  "element_id": "elem_...",
  "project_id": "proj_...",
  "category": "wall | hvac | plumbing",
  "properties": {},
  "source_file_id": "file_...",
  "created_at": "timestamp"
}
```

Rules:

- Source of truth is always structured store
- Never generated by LLM alone

---

## 18.6 Document Chunk Contract

```json
{
  "chunk_id": "chunk_...",
  "file_id": "file_...",
  "page": 3,
  "text": "...",
  "confidence": 0.92
}
```

---

## 18.7 Issue Contract

```json
{
  "issue_id": "issue_...",
  "project_id": "proj_...",
  "type": "clash | missing_data | compliance",
  "severity": "low | medium | high",
  "source_refs": [],
  "confidence": 0.85
}
```

Rules:

- Must include traceable references
- Must include confidence

---

## 18.8 Workflow Contract

```json
{
  "workflow_id": "wf_...",
  "type": "ingestion | analysis | report",
  "status": "running | paused | complete | failed",
  "current_step": "...",
  "checkpoint": {}
}
```

Rules:

- Must be resumable
- Must be idempotent

---

## 18.9 Deliverable Contract

```json
{
  "deliverable_id": "deliv_...",
  "project_id": "proj_...",
  "type": "summary | report | export",
  "artifact_path": "s3://...",
  "source_trace": [],
  "created_at": "timestamp"
}
```

Rules:

- Must include source trace
- Must be versioned

---

## 18.10 Memory Contract

```json
{
  "note_id": "mem_...",
  "tenant_id": "tenant_...",
  "project_id": "proj_...",
  "content": "...",
  "tags": [],
  "links": []
}
```

Rules:

- Memory is assistive, not authoritative
- Must never override structured BIM data

---

## 18.11 Usage Contract

```json
{
  "usage_id": "usage_...",
  "tenant_id": "tenant_...",
  "service": "gateway | ingestion | workflow",
  "cost": 0.002,
  "timestamp": "..."
}
```

---

## 18.12 Non-Negotiable Contract Rules

1. No service returns unstructured data across boundaries
2. No service writes directly into another service’s database
3. All contracts must be versionable
4. All outputs must be traceable to inputs
5. All workflows must be restartable
6. No silent failures
7. No cross-tenant data leakage

---

## 18.13 Summary

This contract layer is what prevents the system from collapsing as it scales. If followed strictly, services can split, teams can grow, and the platform can expand beyond BIM without rewriting core logic.

The next document to define is the **Build Rules / Non-Negotiables Doc**, which governs how agents generate and modify code under this contract system.

---

## 19. Build Rules / Non-Negotiables Document

This document defines how any build agent, coding assistant, or developer must behave while working inside this repository. Its purpose is to prevent architectural drift, hidden coupling, false completion, and expensive technical debt during fast iteration.

These rules apply to all generated code, refactors, migrations, tests, and documentation updates.

---

## 19.1 Build Philosophy

The system is not a collection of pages or features. It is a controlled platform with strict service boundaries, explicit contracts, durable state, and traceable outputs.

Build behavior must follow these principles:

- favor explicit structure over convenience
- favor traceability over speed shortcuts
- favor deterministic logic before model-based logic
- favor local and low-cost execution before premium escalation
- favor modular services over tightly coupled helpers
- favor restartability and validation over optimistic execution

No code should be written as if this were a throwaway prototype.

---

## 19.2 Agent Operating Mode

Any build agent working in this repo must behave as a constrained systems engineer, not an improvisational app builder.

Required behavior:

- read the relevant spec documents before generating code
- obey existing contracts before inventing new structures
- create typed, explicit, inspectable code
- update docs when contracts, behaviors, or run instructions change
- generate tests with any new contract, workflow, or parser path
- treat TODOs as tracked gaps, not invisible assumptions

Forbidden behavior:

- silently inventing schemas
- bypassing shared packages because a local copy is faster
- calling premium models by default
- embedding business logic in UI components
- writing across service database boundaries
- declaring anything production-ready without validation, tests, and observability

---

## 19.3 Definition of Done

A task is not complete unless all of the following are true:

- the code compiles or runs
- the change follows the system contracts
- the change includes tests or fixtures where appropriate
- the change includes config or migration updates if needed
- the change includes doc updates if behavior changed
- the change can be restarted safely if interrupted
- the change does not violate tenant isolation or source trace rules

A page rendering or endpoint responding is not enough.

---

## 19.4 Repository Discipline Rules

1. No direct model provider calls from frontend apps.
2. No duplicated schema definitions across services.
3. No service may depend on another service’s internal modules.
4. No untyped environment usage; all config must pass through typed settings.
5. No side effects without idempotency or retry design.
6. No workflow without checkpointing and restart behavior.
7. No file parser may write final facts without validation and normalization.
8. No deliverable may be generated without source trace metadata.
9. No cross-tenant cache, memory, or query reuse.
10. No breaking contract change without versioning notes.

---

## 19.5 Service Boundary Rules

### Gateway

The gateway may:

- authenticate requests
- enforce policy
- perform routing
- invoke cache and orchestration
- validate output schemas
- meter usage

The gateway may not:

- own BIM parsing logic
- own deliverable generation logic
- become a dumping ground for workflow code

### BIM Ingestion

The ingestion service may:

- accept files
- validate files
- parse source content
- normalize source records
- enqueue heavy jobs

The ingestion service may not:

- generate client-facing reports directly
- decide billing behavior
- bypass shared schemas

### Orchestration

The orchestration service may:

- coordinate multi-step workflows
- manage checkpoints and retries
- call other services through explicit contracts

The orchestration service may not:

- become the source of truth for structured domain data
- hide side effects inside opaque helper chains

### Memory

The memory service may:

- store notes, links, and retrieval metadata
- summarize workflow or project context

The memory service may not:

- override BIM facts
- store uncontrolled raw transcript dumps as system truth

---

## 19.6 Model Usage Rules

The model ladder must always be respected.

Required order:

1. deterministic logic
2. local models
3. low-cost API models
4. premium API models

Before using a more expensive model, the system must check whether the task can be completed through a cheaper layer.

Approved local-model use cases:

- routing
- classification
- tagging
- short summarization
- light extraction
- note creation
- repair of minor formatting or schema errors

Approved premium-model use cases:

- ambiguous reasoning after failed cheaper attempts
- high-value synthesis across multiple source types
- difficult compliance-style interpretation
- stakeholder-ready narrative outputs where lower tiers failed validation

Forbidden model behavior:

- premium by default
- provider-specific logic hardcoded into product features
- model-generated BIM facts stored without structured validation

---

## 19.7 Data Truth Rules

The system must maintain clear truth hierarchy.

Truth order:

1. structured domain records
2. validated extracted records
3. workflow state
4. memory notes
5. generated narrative

This means:

- building elements come from normalized structured storage
- document citations come from extracted chunks and references
- issues must link back to source records
- memory helps retrieval and continuity but is never the truth source for BIM facts

---

## 19.8 Testing Rules

Every material change must be accompanied by the right class of tests.

Required test types by change:

- schema change -> contract tests
- parser change -> fixture ingestion tests
- workflow change -> replay and checkpoint tests
- gateway change -> API and policy tests
- cache change -> threshold correctness tests
- deliverable change -> artifact validation tests
- auth or tenancy change -> tenant isolation tests

No parser or workflow path should be merged based only on visual inspection.

---

## 19.9 Documentation Rules

The agent must update documentation when it changes:

- service responsibilities
- environment variables
- startup steps
- contract structures
- deliverable formats
- workflow behavior
- architecture decisions

Required docs to update when relevant:

- `README.md`
- service README
- docs/api
- docs/workflows
- docs/deliverables
- docs/decisions

---

## 19.10 Migration Rules

If a change affects persistent state, the agent must:

- define the migration explicitly
- state whether it is backward compatible
- provide rollback guidance where feasible
- update affected schemas and fixtures
- note any required reseeding or backfill

No silent schema drift.

---

## 19.11 Workflow Safety Rules

All workflows must be designed for interruption.

Required properties:

- explicit states
- checkpoints
- retry-safe operations
- idempotent side effects
- dead-letter path for unrecoverable failure
- status visibility in admin surfaces

A workflow is invalid if restarting it risks duplicate charges, duplicate artifacts, or corrupted project state.

---

## 19.12 Deliverable Rules

Every deliverable must:

- identify the project and version
- identify the source files used
- include trace metadata
- state confidence or unresolved gaps where applicable
- be reproducible from the same inputs

No black-box report generation.

---

## 19.13 UI Build Rules

Frontend apps must remain thin.

The UI may:

- collect input
- show status
n- render outputs
- trigger workflows
- display traceable source references

The UI may not:

- contain secret keys
- contain provider-specific inference logic
- reimplement backend policy logic
- invent local copies of contracts that drift from shared schemas

---

## 19.14 Observability Rules

Every service must emit enough information to debug and operate safely.

Minimum required telemetry:

- request or workflow ID
- tenant ID
- project ID where applicable
- service name
- operation name
- latency
- status
- error reason if failed

For model-invoking paths, also record:

- model tier
- model name
- cache hit or miss
- token or usage estimate
- cost estimate
- escalation reason if applicable

---

## 19.15 Build Agent Prompting Rules

If a build agent is instructed to create or modify code, it must:

- cite which spec or contract it is implementing
- state assumptions clearly in code comments or doc updates when needed
- avoid claiming completeness when placeholders, mocks, or gaps remain
- mark shells, stubs, and incomplete paths explicitly

Forbidden phrases in commit summaries, generated docs, or task status unless proven:

- production-ready
- complete
- fully functional
- enterprise-grade
- finished

Use instead:

- scaffolded
- initial implementation
- partial path complete
- contract-aligned stub
- ready for next integration step

---

## 19.16 Change Review Checklist

Before any significant change is accepted, verify:

- does it honor the service boundary
- does it reuse shared schemas
- does it preserve tenant isolation
- does it preserve source traceability
- does it obey the model cost ladder
- does it include tests
- does it update docs
- can it recover safely after interruption

If any answer is no, the change is not done.

---

## 19.17 Summary

This document exists to stop the build from collapsing into fast but brittle code. It enforces discipline across service boundaries, cost control, state safety, and documentation so the platform can grow into a team-managed system instead of becoming a pile of disconnected agent output.

The next document to define is the **Service Specification set**, starting with the `gateway` service and then the `bim-ingestion` service, because those are the first two implementation anchors in the repo.
