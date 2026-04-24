# Arkham / Robco AI Monorepo

The centralized control plane and vertical service ecosystem for the Arkham platform.

## 1. Company & Identity
- **Company:** Arkham (formerly Robco)
- **Identity:** A BIM-first AI platform for architectural, engineering, and construction (AEC) automation.
- **Status:** **Active / Controlled Migration.** We are currently migrating all "Robco" legacy branding to "Arkham" across all tiers.

## 2. Live Infrastructure (`arkham-492414`)
Hosted on Google Cloud Platform:
- **Registry:** `arkham-containers` (Primary), `robco-containers` (Legacy/Mirror).
- **Compute:** Cloud Run (Serverless microservices).
- **Database:** Cloud SQL PostgreSQL (PITR enabled, `arkham-db` target).
- **Network:** VPC with Private Services Access (PSA).
- **State:** Terraform-managed (`gs://arkham-tf-state`).

## 3. Core Products & Services

### **The Control Plane (Hub)**
- **Gateway:** Central API entry point, auth, and intelligent inference routing.
- **Arkham Governance:** Central persona governance, fingerprinting, and QA batteries.
- **Orchestration:** Durable workflow engine with checkpointing and manual approval gates.
- **A-MEM:** Cross-service semantic memory for technical and architectural context.

### **AI Verticals (Spokes)**
- **Omniscale:** Quantity takeoffs and structured cost estimation.
- **AutoPitch:** Architectural business development and proposal generation.
- **AI Consistency:** Quality control and cross-document verification.
- **Cyberscribe:** Technical documentation and specification writing.
- **Digital It Girl:** Brand guidelines and marketing asset generation.

### **Applications**
- **Arkham Web:** Main platform dashboard for AEC teams.
- **ArkhamPrison:** Specialized governance and jailbreaking/consistency testbed.
- **PapaBase (External):** Solo operator control plane for field service businesses.

## 4. Agent Skills
Specialized skills for interacting with this repository:

- **`arkham-governance`:** Guidance on running codebase audits, resolving approval gates, and maintaining architectural alignment via the Arkham sidecar.
- **`durable-ops`:** Procedures for managing `WorkflowRun` states, retries, and checkpointing.

*Find skill definitions in `docs/skills/`.*

## 5. Maintenance & Operations
- **Current Blocker:** Wave 3 Database Migration (Execution Window: April 24, 02:00 UTC).
- **Ops Log:** See `docs/migration_wave3_exec.log` during cutover.
- **Naming Rule:** All new services MUST use the `arkham-` prefix.
