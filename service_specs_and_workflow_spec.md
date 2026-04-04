# Service Specification Set and Workflow Specification

## Purpose

This document defines the implementation-facing service specifications for the BIM-first platform and the first end-to-end workflow specification. It is intended to be used by build agents and developers as a direct build reference, separate from the master architecture document.

This document covers:

- gateway service
- BIM ingestion service
- orchestration service
- memory service
- semantic cache service
- billing service
- notifications service
- worker services
- first BIM workflow end to end

---

# 1. Service Specification: Gateway

## 1.1 Purpose

The gateway is the centralized control plane for all inference, routing, policy enforcement, tenant authentication, cost discipline, schema validation, and workflow initiation. It is the only service allowed to directly broker model access for product-facing requests.

## 1.2 Responsibilities

The gateway must:

- expose normalized APIs for inference and workflow entry
- authenticate tenant requests
- enforce quotas, plan rules, and request policy
- classify request type
- perform semantic cache checks
- select the cheapest valid execution path
- invoke local models directly for low-cost tasks when appropriate
- escalate to API providers only when policy permits
- invoke orchestration for multi-step jobs
- validate output against schemas
- emit usage and observability events

The gateway must not:

- own BIM parsing logic
- own long-running workflow logic
- store authoritative BIM facts
- embed product-specific business logic that belongs in vertical workflows

## 1.3 Inputs

Primary request types:

- direct inference requests
- workflow initiation requests
- status lookup requests
- admin or internal policy requests

## 1.4 Outputs

The gateway returns only normalized responses, including:

- request metadata
- model tier used
- cache status
- validated output
- workflow handoff metadata when asynchronous execution is required

## 1.5 Core Endpoints

Suggested v1 endpoints:

- `POST /v1/infer`
- `POST /v1/workflows/start`
- `GET /v1/workflows/{workflow_id}`
- `GET /healthz`
- `GET /readyz`
- `GET /metrics`

## 1.6 Internal Modules

Suggested modules:

- auth
- provider registry
- routing policy engine
- semantic cache adapter
- output validator
- workflow client
- usage metering
- observability

## 1.7 Dependencies

- Redis for rate limiting and short-lived operational state
- semantic cache service
- orchestration service
- local inference runtime
- optional external model providers
- billing service for usage events
- shared schemas package

## 1.8 Required Config

- database or usage event sink
- redis url
- local model runtime host
- provider credentials if enabled
- signing key
- feature flags for premium escalation and cache usage

## 1.9 Success Criteria

- requests are authenticated and tenant-scoped
- outputs are normalized and schema-valid
- low-cost routing occurs by default
- workflow handoff is stable and traceable
- metrics and cost data are emitted for every request path

## 1.10 Required Tests

- auth and tenant isolation tests
- routing policy tests
- cache hit and miss tests
- schema validation tests
- escalation policy tests
- workflow handoff tests

---

# 2. Service Specification: BIM Ingestion

## 2.1 Purpose

The BIM ingestion service receives uploaded project files, validates them, normalizes them, and coordinates parsing into structured records and extraction artifacts. It is the system boundary for IFC, PDFs, schedules, and markups.

## 2.2 Responsibilities

The ingestion service must:

- accept uploaded files and metadata
- validate file type, size, and source metadata
- register project files
- dispatch heavy parsing to workers
- normalize extracted records into shared schemas
- persist extraction status and confidence
- link extracted records back to file and page or source position
- expose job status for downstream workflows

The ingestion service must not:

- create final stakeholder-facing reports directly
- act as the source of truth for project billing
- store ad hoc schemas per file type

## 2.3 Supported Inputs

- IFC files
- PDFs
- schedule files such as CSV, XLSX, and schedule PDFs
- markup exports and annotated documents or images where parseable

## 2.4 Outputs

- project file records
- ingestion jobs
- normalized building elements
- document chunks
- schedule records
- markup records
- extraction warnings and confidence flags

## 2.5 Core Endpoints

Suggested v1 endpoints:

- `POST /v1/files/register`
- `POST /v1/files/{file_id}/ingest`
- `GET /v1/ingestion/jobs/{job_id}`
- `GET /v1/projects/{project_id}/files`
- `GET /healthz`
- `GET /readyz`

## 2.6 Internal Modules

Suggested modules:

- file validators
- parser dispatch
- IFC normalization
- PDF chunking and extraction
- schedule normalization
- markup extraction
- storage adapters
- job state manager

## 2.7 Dependencies

- object storage
- Postgres/PostGIS
- Redis or queue backend
- worker services
- shared schemas package

## 2.8 Required Config

- storage endpoint and buckets
- database url
- queue url
- feature flags by source type
- file size and mime limits

## 2.9 Success Criteria

- all ingested outputs are structured and linked to source files
- job status is observable and restartable
- no extracted record is accepted without validation and normalization
- parsing failures are visible, not silent

## 2.10 Required Tests

- fixture-based IFC ingestion tests
- PDF extraction tests with page references
- schedule normalization tests
- markup parsing tests
- ingestion retry tests
- source trace persistence tests

---

# 3. Service Specification: Orchestration

## 3.1 Purpose

The orchestration service coordinates multi-step workflows, manages checkpoints, ensures retry-safe execution, and tracks long-running project operations.

## 3.2 Responsibilities

The orchestration service must:

- start workflows from explicit workflow specs
- persist workflow state and checkpoint data
- coordinate calls to ingestion, memory, semantic cache, and gateway logic where appropriate
- route tasks to worker services
- manage retries and dead-letter paths
- expose workflow status and step-level progress
- support resumability after failure or restart

The orchestration service must not:

- become the source of truth for BIM entities
- hide logic in opaque chains with no checkpoint visibility
- bypass service contracts to access internal modules from other services

## 3.3 Supported Workflow Types

- project package ingestion
- project analysis
- issue register generation
- deliverable generation
- future compliance or change analysis workflows

## 3.4 Outputs

- workflow runs
- workflow checkpoints
- step-level status events
- final workflow result records

## 3.5 Core Endpoints

Suggested v1 endpoints:

- `POST /v1/workflows/start`
- `GET /v1/workflows/{workflow_id}`
- `GET /v1/workflows/{workflow_id}/steps`
- `POST /v1/workflows/{workflow_id}/retry`
- `GET /healthz`
- `GET /readyz`

## 3.6 Internal Modules

Suggested modules:

- workflow registry
- step runner
- checkpoint store
- retry manager
- dead-letter handler
- event emitter
- worker dispatch client

## 3.7 Dependencies

- Postgres for workflow persistence
- Redis or queue backend
- ingestion service
- memory service
- semantic cache service
- report generator worker
- shared schemas package

## 3.8 Required Config

- queue url
- database url
- max retry settings
- workflow timeout settings
- dead-letter handling settings

## 3.9 Success Criteria

- workflows are restartable from checkpoints
- side effects are idempotent
- failures are visible with exact step attribution
- workflow state matches real execution state

## 3.10 Required Tests

- checkpoint and replay tests
- retry safety tests
- workflow timeout tests
- dead-letter path tests
- multi-service contract tests

---

# 4. Service Specification: Memory

## 4.1 Purpose

The memory service stores scoped project-aware notes and relationships that improve retrieval and continuity across workflows without becoming the source of truth for BIM facts.

## 4.2 Responsibilities

The memory service must:

- create structured memory notes from workflow summaries, analyst notes, and project context
- tag and link notes
- retrieve relevant notes by project and task
- support pruning and retention policies
- preserve source relationships where useful

The memory service must not:

- override building element facts
- store uncontrolled transcript dumps as authoritative project state

## 4.3 Inputs

- memory write requests from workflows
- note creation requests from summaries or analyst actions
- retrieval requests from workflows or search features

## 4.4 Outputs

- memory notes
- note links
- retrieval result sets
- pruning events

## 4.5 Core Endpoints

Suggested v1 endpoints:

- `POST /v1/notes`
- `POST /v1/retrieve`
- `GET /v1/projects/{project_id}/notes`
- `POST /v1/prune`
- `GET /healthz`
- `GET /readyz`

## 4.6 Dependencies

- vector store
- Postgres or note metadata store
- shared schemas package

## 4.7 Success Criteria

- notes are tenant- and project-scoped
- retrieval returns relevant assistive context
- memory never becomes authoritative over structured BIM records

## 4.8 Required Tests

- note creation tests
- retrieval relevance tests
- scoping tests
- pruning and retention tests

---

# 5. Service Specification: Semantic Cache

## 5.1 Purpose

The semantic cache service reduces model cost and latency by reusing prior responses when a new request is sufficiently similar and safe to serve from cache.

## 5.2 Responsibilities

The semantic cache service must:

- normalize cacheable requests
- generate or retrieve embeddings
- perform similarity lookup
- apply threshold policy by task type
- return cache hit metadata and stored response payloads
- preserve tenant and project scoping

The semantic cache service must not:

- cross tenant boundaries
- serve cached content when policy forbids it
- become a general-purpose storage dump

## 5.3 Inputs

- normalized request payloads
- embeddings or texts for embedding generation
- cache write requests
- cache lookup requests

## 5.4 Outputs

- cache hit or miss
- matched entry metadata
- reusable output payload
- confidence or similarity metadata

## 5.5 Core Endpoints

Suggested v1 endpoints:

- `POST /v1/cache/lookup`
- `POST /v1/cache/write`
- `GET /v1/cache/{entry_id}`
- `GET /healthz`
- `GET /readyz`

## 5.6 Dependencies

- vector store
- optional embedding runtime
- shared schemas package

## 5.7 Success Criteria

- safe cache reuse for appropriate tasks
- observable hit rates and similarity thresholds
- no cache leakage across tenants or projects

## 5.8 Required Tests

- threshold policy tests
- cache scoping tests
- hit and miss correctness tests
- invalid reuse prevention tests

---

# 6. Service Specification: Billing

## 6.1 Purpose

The billing service records usage, maps it to tenant plans, and emits billable or internal cost events.

## 6.2 Responsibilities

The billing service must:

- receive usage events from gateway and workflows
- aggregate metering data
- map usage to plans
- support Stripe integration later
- expose usage summaries to admin surfaces

The billing service must not:

- make routing decisions
- own raw workflow logic

## 6.3 Outputs

- usage events
- usage summaries
- plan enforcement signals
- billing export records

## 6.4 Required Tests

- usage ingestion tests
- aggregation tests
- plan mapping tests
- tenant isolation tests

---

# 7. Service Specification: Notifications

## 7.1 Purpose

The notifications service delivers workflow and system status updates to downstream channels such as email, webhook endpoints, or internal event consumers.

## 7.2 Responsibilities

The notifications service must:

- receive status events
- format delivery-safe payloads
- send notifications through configured channels
- preserve idempotency for repeated events

## 7.3 Outputs

- delivery attempts
- delivery receipts
- failed delivery records

## 7.4 Required Tests

- event formatting tests
- delivery retry tests
- idempotency tests

---

# 8. Worker Specifications

## 8.1 BIM Parser Worker

Purpose:

- parse IFC and extract structured building entities and relationships

Must produce:

- normalized element payloads
- extraction warnings
- parse metrics

## 8.2 PDF Extractor Worker

Purpose:

- extract text and structured references from PDFs

Must produce:

- page-level chunks
- page references
- extraction confidence

## 8.3 Schedule Normalizer Worker

Purpose:

- normalize raw schedule inputs into structured rows and milestone records

Must produce:

- schedule rows
- standardized status and date values
- extraction warnings

## 8.4 Report Generator Worker

Purpose:

- generate reproducible deliverable artifacts from validated workflow outputs

Must produce:

- HTML or PDF report artifacts
- machine-readable exports
- source trace metadata

---

# 9. Workflow Specification: First BIM Pipeline

## 9.1 Workflow Name

Project Intake to Deliverable Package

## 9.2 Workflow Goal

Take a BIM project package containing IFC, PDFs, schedules, and markups, ingest it into structured systems, run an initial analysis pass, and produce the first versioned deliverable package with source traceability.

## 9.3 Workflow Trigger

The workflow starts when a user uploads or registers a new project package and requests initial analysis.

## 9.4 Inputs

Required:

- tenant ID
- project ID
- at least one registered project file

Preferred:

- IFC model
- supporting PDFs
- schedules
- markups

## 9.5 Workflow Steps

### Step 1: Project and File Registration

The system creates or verifies:

- project record
- project file records
- source metadata
- initial ingestion jobs

Outputs:

- project exists in domain store
- files are traceable and ready for ingestion

### Step 2: Source Validation

The ingestion service validates source file types, sizes, and supported input status.

Outputs:

- valid files proceed
- invalid files are flagged with reasons

Checkpoint:

- validation complete status persisted

### Step 3: Parsing and Extraction Dispatch

The ingestion service dispatches workers by file type:

- IFC -> BIM parser worker
- PDF -> PDF extractor worker
- schedules -> schedule normalizer worker
- markups -> markup extraction path

Outputs:

- asynchronous jobs launched
- job IDs persisted

Checkpoint:

- dispatch status persisted

### Step 4: Structured Record Normalization

Parsed outputs are normalized into shared contracts and written to the structured domain store.

Outputs:

- building elements
- document chunks
- schedule records
- markup records
- extraction warnings

Checkpoint:

- normalization status persisted

### Step 5: Initial Analysis Trigger

The orchestration service starts an analysis pass once required ingestion outputs exist.

Analysis scope for v1:

- project intake summary
- model element summary
- document and markup summary
- initial issue register draft

The system should use deterministic logic first and local models for low-cost classification or issue grouping where useful.

Checkpoint:

- analysis start persisted

### Step 6: Memory Note Creation

The workflow writes scoped memory notes summarizing project state, unresolved gaps, and workflow outcomes.

Outputs:

- project memory notes
- retrieval links for later workflows

Checkpoint:

- memory write status persisted

### Step 7: Deliverable Assembly

The report generator worker builds the v1 deliverable package.

Required outputs:

- project intake summary
- model element summary
- document and markup summary
- issue register
- machine-readable export
- HTML or PDF report

Each output must include source trace metadata and confidence or unresolved gaps where applicable.

Checkpoint:

- deliverable generation persisted

### Step 8: Finalization and Notification

The workflow marks the run complete, stores artifact records, emits usage events, and optionally notifies the user or admin surface.

Outputs:

- workflow complete status
- artifact records
- usage events
- notification events

Checkpoint:

- final state persisted

## 9.6 Failure Handling Rules

If any step fails:

- the workflow must record exact step failure
- the workflow must persist checkpoint state
- retry-safe steps may be retried
- unrecoverable steps must move to a visible failed state
- no duplicate artifact generation is allowed on retry

## 9.7 v1 Deliverables Defined by This Workflow

The first workflow must produce:

1. Project Intake Summary
2. Model Element Summary
3. Document and Markup Summary
4. Issue Register
5. Project Deliverable Package

## 9.8 v1 Success Criteria

The workflow is considered successful only when:

- all accepted source files are registered and traceable
- structured records are written for ingested content
- project summaries are generated from validated records
- deliverables exist as persisted artifacts
- artifact outputs include source traceability
- workflow state is resumable and auditable

## 9.9 Required Workflow Tests

- end-to-end fixture workflow test
- interruption and resume test
- duplicate retry prevention test
- missing file failure test
- source trace validation test
- deliverable artifact existence test

---

# 10. Recommended Build Order from This Document

1. shared schemas package
2. gateway skeleton
3. BIM ingestion service
4. core workers
5. orchestration service
6. report generator worker
7. semantic cache service
8. memory service
9. billing and notifications
10. workflow implementation and end-to-end tests

---

# 11. Summary

This document is the implementation specification set for the BIM-first platform. The gateway controls access and cost discipline. Ingestion and workers turn source files into structured records. Orchestration coordinates the long-running pipeline. Memory and semantic cache improve continuity and efficiency without replacing structured truth. Billing and notifications provide operational completeness.

The first workflow defined here gives the system one complete proof path from project package intake to a versioned deliverable package.

