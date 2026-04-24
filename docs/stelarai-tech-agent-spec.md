# StelarAI Agent Spec

Date: 2026-04-24

## Purpose

This file is the hard execution contract for StelarAI work. It exists to prevent future coding agents from misreading the build plan, expanding scope without evidence, or claiming completion too early.

## Product target

Build `stelarai.tech` as a tenant-scoped AI resource management and production platform by extending the existing stack:

- backend: `Projects/fs-ai`
- frontend: `Projects/fsdash`
- reusable vertical services: `arkham/services/verticals/*`

Do not replace these systems with a new standalone monolith.

## Non-negotiable constraints

- Reuse existing auth, tenants, providers, prompts, and billing posture.
- Keep all StelarAI state tenant-scoped.
- Keep Anthropic available as a first-class provider lane.
- Keep at least one cheap or free path available for each workflow class.
- Prefer persisted records over inferred or mock UI state.
- Do not invent progress metrics, usage, costs, or workflow outputs.

## Current baseline

Already delivered:

- backend schema for StelarAI workspaces, modules, accounts, sources, and workflows
- backend endpoints:
  - `GET /api/v1/stelarai/blueprint`
  - `GET /api/v1/stelarai/workspaces`
  - `POST /api/v1/stelarai/workspaces`
  - `GET /api/v1/stelarai/workspaces/{workspace_id}`
  - `GET /api/v1/stelarai/workspaces/{workspace_id}/accounts`
  - `POST /api/v1/stelarai/workspaces/{workspace_id}/accounts`
  - `GET /api/v1/stelarai/workspaces/{workspace_id}/sources`
  - `POST /api/v1/stelarai/workspaces/{workspace_id}/sources`
  - `GET /api/v1/stelarai/workspaces/{workspace_id}/workflows`
  - `POST /api/v1/stelarai/workspaces/{workspace_id}/workflows`
  - `GET /api/v1/stelarai/workflows/{workflow_id}`
- frontend StelarAI control-plane surface in `fsdash`

Future work must build on this baseline.

## Required phases

### 1. Finish domain routing

Done means:

- `stelarai.tech` and `www.stelarai.tech` serve from Firebase Hosting
- `api.stelarai.tech` serves from the Google load balancer
- certificate coverage is active

Evidence required:

- `dig`
- `curl`
- certificate status

### 2. Finish persisted workspace primitives

Done means:

- connected accounts, sources, workflows, and simulation runs have CRUD paths
- all reads come from persisted state

Evidence required:

- endpoint test output
- backend compile pass

### 3. Finish workspace shell

Done means:

- users can enter a StelarAI workspace and navigate module surfaces
- each visible panel is backed by a real endpoint

Evidence required:

- frontend build success
- route-level smoke checks

### 4. Finish workflow authoring

Done means:

- workflow canvas state can be saved and reloaded
- simulator can execute dry runs without side effects
- provider lane can be selected per workflow

Evidence required:

- save and reload test
- dry-run output

### 5. Finish connected account execution

Done means:

- a workflow can reference an allowed account or source
- tenant isolation is enforced

Evidence required:

- positive and negative tenant-scope tests

### 6. Finish vertical reuse

Done means:

- Digital IT Girl, Public Beta, and AutoPitch each have a real workspace entry point and persisted output path

Evidence required:

- one successful integration test per module

### 7. Finish production readiness

Done means:

- auth, workspace load, workflow save, simulator, and provider lanes all pass in deployment

Evidence required:

- smoke run log
- health and readiness checks

## Stop rules

Stop and fix before moving on when:

- DNS delegation is wrong
- a route depends on fake data
- a module has navigation but no backend execution
- a simulation path can trigger live side effects
- a tenant can read another tenant’s StelarAI state
- the cheap or free model lane is missing
- Anthropic access is removed or narrowed

## Completion definition

The StelarAI project is complete only when:

- domains are live and routed correctly
- operator and customer auth both work
- at least one workspace exists and loads
- at least one workflow can be saved and simulated
- cheap/free and Anthropic model lanes both work
- at least one reused Arkham module produces a persisted result
- smoke tests pass in deployment
