# Design Document: Control-Plane CTO Agent

## 1. Vision & Purpose
The **CTO Agent** is a centralized control-plane product designed to manage the technical lifecycle of the Arkham platform. It operates as an autonomous engineering leader capable of analyzing code, planning architectures, and (eventually) executing gated mutations.

Unlike standard vertical personas, the CTO Agent has cross-cutting visibility and is governed by a dedicated **Action Governance** layer to ensure system integrity.

## 2. Core Architectural Principles
- **Read-First, Execute-Later:** All initial capabilities are read-only (audits, analysis, planning).
- **Durable Orchestration:** Every action is a persisted `WorkflowRun` with checkpoints and resumability.
- **Dual Governance:**
    - **Persona Governance (Arkham Sidecar):** Validates that the agent's *recommendations* and *style* align with core principles.
    - **Action Governance (Execution Policy):** A strict gatekeeper for *mutations* (commits, deploys, infra changes) requiring human approval.
- **Unified A-MEM:** A global memory layer for technical decisions and architectural context, separated from vertical-specific business memory.

## 3. System Components

### 3.1 CTO Agent Vertical (`services/verticals/cto_agent`)
- **Role:** UI/API surface for developer interaction and coordination.
- **Responsibilities:**
    - Accept operator requests.
    - Trigger and monitor orchestration flows.
    - Present findings and proposed actions for approval.

### 3.2 Durable Orchestration Layer (`services/orchestration`)
- **Responsibility:** Managing long-lived execution state.
- **Data Models:** `WorkflowRunRecord`, `WorkflowStepRecord`.
- **Logic:** Step-level persistence, idempotent retries, and manual approval states.

### 3.3 A-MEM Service (`services/memory`)
- **Responsibility:** Storing atomic technical notes and decision history.
- **Logic:** Embedding-based retrieval of prior architectural patterns and rationale.

### 3.4 Action Governance Layer (Future)
- **Responsibility:** Secure execution of mutations.
- **Permissions:** Restricted access to Git, Cloud Run, Secret Manager, and Terraform.
- **Requirement:** Mandatory `approval_state` for all non-idempotent or high-risk actions.

## 4. First Prototype: Codebase Audit
A read-only, durable workflow to prove the orchestration and governance model.

### 4.1 Workflow Specification
- **Trigger:** Manual operator request via CTO Agent API.
- **Inputs:** `repo_ref`, `audit_scope` (e.g., security, tech-debt, architecture), `tenant_id`, `project_id`.
- **Execution Steps:**
    1.  **Ingest Context:** Analyze the target codebase/ref.
    2.  **Memory Recall:** Retrieve relevant prior technical notes from A-MEM.
    3.  **Analyze & Synthesize:** Generate findings based on the audit scope.
    4.  **Governance Check:** Run findings through Arkham Sidecar for alignment validation.
    5.  **Persist Artifacts:** Save the structured audit report and proposed action list.
    6.  **Human Approval:** Transition to `pending_approval` state for operator review.

### 4.2 Forbidden Actions (Phase 1)
- No `git commit` or `push`.
- No `gcloud deploy` or infra mutations.
- No `SECRET_MANAGER` read access.
- No schema migrations.

### 4.3 Success Metrics
- Full persistence of all workflow steps and checkpoints.
- Successful recovery from a simulated step failure.
- Traceability of findings back to specific codebase locations and A-MEM notes.

## 5. Deployment & Naming (Iterative)
- **Namespace:** Maintain `arkham` as the primary project identity.
- **Cleanup:** Limited, non-disruptive metadata updates to reduce ambiguity in the prototype logs and schemas.
- **Infrastructure:** Deploy to `arkham-492414` using existing Cloud Build patterns, isolated from production verticals.
