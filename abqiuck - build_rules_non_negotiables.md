# Build Rules / Non-Negotiables Document

## Purpose

This document defines how any build agent, coding assistant, or developer must behave while working inside this repository. Its purpose is to prevent architectural drift, hidden coupling, false completion, and expensive technical debt during fast iteration.

These rules apply to all generated code, refactors, migrations, tests, documentation updates, and repo structure changes.

---

## 1. Build Philosophy

The platform is not a loose collection of features. It is a controlled multi-service system with strict contracts, explicit state, source traceability, and durable operational behavior.

All work in this repo must follow these principles:

- prefer explicit structure over convenience
- prefer deterministic logic before model-based logic
- prefer local and low-cost execution before premium escalation
- prefer restartability over optimistic execution
- prefer traceability over shortcuts
- prefer modular service boundaries over convenience helpers
- prefer documented assumptions over silent assumptions

No code should be written as if this were a disposable prototype.

---

## 2. Agent Operating Mode

Any build agent working in this repo must behave like a constrained systems engineer, not an improvisational app builder.

Required behavior:

- read the relevant spec documents before writing code
- obey the system contracts before inventing new shapes
- use shared schemas instead of redefining structures locally
- create typed, explicit, inspectable code
- update docs when setup, behavior, or contracts change
- add tests for every material contract, workflow, parser, or policy change
- mark stubs, shells, placeholders, and unfinished paths clearly

Forbidden behavior:

- silently inventing new schemas
- bypassing shared packages because local duplication is faster
- hardcoding premium models into product features
- embedding business logic inside UI components
- writing directly across service database boundaries
- declaring anything complete, production-ready, or finished without verification

---

## 3. Definition of Done

A change is not done unless all of the following are true:

- the code runs or builds
- the change follows the system contracts
- tests exist for the affected behavior where appropriate
- migration or config changes are included if needed
- docs are updated if behavior or setup changed
- the change can recover safely if interrupted
- tenant isolation and source trace rules are preserved

A page rendering, endpoint responding, or mock flow working is not enough.

---

## 4. Repository Discipline Rules

1. No direct model provider calls from frontend apps.
2. No duplicated schema definitions across services.
3. No service may depend on another service’s internal modules.
4. No untyped environment access; all settings must pass through typed config.
5. No side effects without idempotency or retry design.
6. No workflow without checkpointing and restart behavior.
7. No parser may write final facts without validation and normalization.
8. No deliverable may be generated without source trace metadata.
9. No cross-tenant cache, memory, or retrieval leakage.
10. No breaking contract change without versioning notes.
11. No premium model by default.
12. No hidden operational state.

---

## 5. Service Boundary Rules

### Gateway

The gateway may:

- authenticate requests
- enforce policy
- classify request type
- route requests
- invoke local or external model providers through the provider layer
- call semantic cache
- hand off long-running work to orchestration
- validate outputs
- meter usage

The gateway may not:

- contain BIM parsing logic
- contain long-running workflow implementations
- own stakeholder-facing deliverable generation
- become a general dumping ground for cross-service logic

### BIM Ingestion

The ingestion service may:

- accept and validate files
- dispatch parsing jobs
- normalize extracted records
- persist extraction status and warnings
- link outputs back to source artifacts

The ingestion service may not:

- generate final stakeholder-facing reports directly
- make billing decisions
- bypass shared schemas

### Orchestration

The orchestration service may:

- coordinate multi-step workflows
- manage checkpoints and retries
- call services through explicit contracts
- record workflow state and step progress

The orchestration service may not:

- become the source of truth for structured BIM data
- hide side effects inside opaque chains
- access other services by reaching into their internals

### Memory

The memory service may:

- store structured notes
- create links between notes
- retrieve relevant project context
- prune or expire notes according to policy

The memory service may not:

- override BIM facts
- replace structured domain records
- become a raw transcript dumping ground

### Semantic Cache

The semantic cache may:

- perform scoped similarity lookups
- return reusable prior results for permitted tasks
- store cache metadata and reusable outputs

The semantic cache may not:

- cross tenant boundaries
- serve forbidden content types from cache
- act as an unbounded storage sink

---

## 6. Model Usage Rules

The model ladder must always be respected.

Required execution order:

1. deterministic logic
2. local models
3. low-cost API models
4. premium API models

Before using a more expensive tier, the system must check whether the task can be completed through a cheaper tier.

Approved local model tasks:

- routing
- classification
- tagging
- short summarization
- light extraction
- note creation
- repair of minor formatting or schema issues

Approved low-cost API tasks:

- bounded synthesis
- structured drafting from validated records
- moderate transformation of messy input into schema-aligned output

Approved premium tasks:

- ambiguous reasoning after cheaper attempts fail
- difficult multi-source synthesis
- high-stakes stakeholder narrative outputs
- repair after lower-cost outputs fail validation and policy allows escalation

Forbidden model behavior:

- premium by default
- model-generated BIM facts stored without validation
- provider-specific logic hardcoded inside UI or workflow steps

---

## 7. Data Truth Hierarchy

Truth must follow this order:

1. structured domain records
2. validated extracted records
3. workflow state
4. memory notes
5. generated narrative

This means:

- building elements come from normalized structured storage
- citations come from extracted and validated sources
- issues must link to source records or files
- memory is assistive context, not authoritative truth
- narrative outputs are summaries, not system truth

---

## 8. Testing Rules

Every material change must include the right class of test.

Required mapping:

- schema change -> contract tests
- gateway change -> API and routing tests
- parser change -> fixture ingestion tests
- workflow change -> checkpoint and replay tests
- auth or tenancy change -> tenant isolation tests
- cache change -> threshold correctness tests
- deliverable change -> artifact validation tests
- config change -> startup validation tests where relevant

No parser, workflow, or contract path should be merged based only on visual inspection.

---

## 9. Documentation Rules

Docs must be updated when code changes:

- service responsibilities
- environment variables
- startup flow
- contract structures
- workflow behavior
- deliverable format
- architecture decisions

Docs that must be updated when relevant:

- root README
- service README
- docs/api
- docs/workflows
- docs/deliverables
- docs/decisions
- docs/runbooks

---

## 10. Migration Rules

If a change affects persistent data, the author must:

- define the migration explicitly
- state whether the change is backward compatible
- provide rollback notes where feasible
- update affected schemas and fixtures
- note any required backfill or reseed steps

No silent schema drift is allowed.

---

## 11. Workflow Safety Rules

All workflows must be safe to interrupt and resume.

Required workflow properties:

- explicit state names
- persisted checkpoints
- retry-safe operations
- idempotent side effects
- visible failed state
- dead-letter path for unrecoverable failure
- status visibility in admin surfaces

A workflow is invalid if retrying it can produce duplicate artifacts, duplicate charges, or corrupted project state.

---

## 12. Deliverable Rules

Every deliverable must:

- identify project and version
- identify the source files used
- include trace metadata
- state unresolved gaps or confidence where applicable
- be reproducible from the same inputs
- be persisted as an artifact record

No black-box report generation is allowed.

---

## 13. UI Build Rules

Frontend apps must remain thin.

The UI may:

- collect input
- display state and progress
- trigger workflows
- render outputs and source references
- consume shared SDK and shared schemas

The UI may not:

- contain secret keys
- call providers directly
- reimplement backend policy logic
- define local contract copies that drift from shared schemas
- own authoritative business logic

---

## 14. Observability Rules

Every service must emit enough information to debug and operate safely.

Minimum required telemetry:

- request ID or workflow ID
- tenant ID
- project ID where applicable
- service name
- operation name
- latency
- success or failure status
- exact error reason where possible

For model-invoking paths also record:

- model tier
- model name
- cache hit or miss
- token or usage estimate
- cost estimate
- escalation reason when applicable

---

## 15. Build Agent Prompting Rules

If a build agent is instructed to create or modify code, it must:

- state which spec or contract it is implementing
- state assumptions when they exist
- mark incomplete paths explicitly
- avoid claiming completeness where placeholders, mocks, or gaps remain

Forbidden status language unless proven:

- production-ready
- complete
- fully functional
- enterprise-grade
- finished

Preferred status language:

- scaffolded
- initial implementation
- contract-aligned stub
- partial path complete
- ready for next integration step

---

## 16. Change Review Checklist

Before a significant change is accepted, verify:

- does it honor service boundaries
- does it reuse shared schemas
- does it preserve tenant isolation
- does it preserve source traceability
- does it obey the model cost ladder
- does it include tests
- does it update docs
- can it recover safely after interruption

If any answer is no, the change is not done.

---

## 17. Summary

This document exists to keep the build from collapsing into fast but brittle code. It enforces discipline across service boundaries, cost control, state safety, truth hierarchy, testing, documentation, and change review so the system can scale as a real team-managed platform instead of a pile of disconnected generated code.

