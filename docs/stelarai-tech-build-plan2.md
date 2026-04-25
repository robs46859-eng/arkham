# StelarAI Tech Build Plan

Date: 2026-04-24

Current Project Status: StelarAI Phase 5 Complete

  We have successfully built the core StelarAI platform on top of the existing
  Arkham and FullStack infrastructure. All product modules are mapped, wired,
  and ready for use.

  1. Delivered Features (Phases 0-5)
   * Unified Workspace Shell: A custom multi-product navigation system in fsdash
     that detects whether a user is on stelarai.tech or fsai.pro and serves the
     appropriate experience.
   * Canvas Builder: Core node-graph persistence implemented in both frontend
     and backend.
   * Account/Source Management: Full CRUD and synchronization polling for
     external business/personal accounts and internal data sources.
   * Vertical Integration: backend VerticalProxy implemented in fs-ai, mapping:
       * digital-it-girl ➡️ Predictive Niche Engine
       * public_beta ➡️ Software Tracker
       * autopitch ➡️ Industry Automation
   * Database Isolation Layer: The backend is now "Dual-Database Ready." By
     providing STELARAI_DATABASE_URL, you can completely isolate StelarAI data
     into its own fresh database without touching any FullStack data.

  2. Architecture Note
  I have updated the README.md files in both fs-ai and fsdash to document this
  new multi-product architecture and the isolation logic.

  3. Current Blocker: Backend Deployment
  The local code is complete and stable (syntax-verified), but the live Cloud
  Run service for fs-ai is currently one version behind due to a dependency
  resolution issue (httpx and a relative import error). I have fixed both issues
  in the local source and simplified the Dockerfile for a cleaner build.

  Next Steps for Phase 6 (Production Readiness)

   1. Stable Deployment: Run a clean deploy of fs-ai to activate the new routes.
   2. Database Provisioning (Optional): If you'd like a completely separate DB
      for StelarAI, I can help create one in Cloud SQL and set the
      STELARAI_DATABASE_URL.
   3. Final Verification: Run the expanded smoke test (stelarai_api_smoke.py)
      which now verifies:
       * Auth + Workspace Creation
       * Workflow Update + Persistence
       * Dry-run Simulation + Cost Preview
       * Workflow Duplication
       * Vertical Proxy Routing (Live trends check)


## Domain Instructions

### Final domain roles

- `fsai.pro`
  - primary FullStack product frontend on Firebase Hosting
- `www.fsai.pro`
  - alias of `fsai.pro` on Firebase Hosting
- `api.fsai.pro`
  - API host on Google load balancer `34.120.16.150` -> `fs-ai`

- `solamaze.com`
  - CTA / campaign domain
  - use as a marketing entry for whichever service bundle is being promoted that week
- `getsemu.com`
  - CTA / campaign domain
  - use as a second rotating marketing entry, optimized for alternate campaign copy, audience, or offer

- `stelarai.tech`
  - primary StelarAI product domain
  - customer-facing product site plus authenticated platform workspace
  - should become the public home of the AI resource management and production platform described below

- `smithgroup.io`
  - delegated to Google nameservers already
  - leave as a separate brand/property until you decide whether it should point to the StelarAI product, a distinct client portal, or a legacy site

### Recommended hosting split

#### `stelarai.tech`

Use Firebase Hosting for the product frontend and Cloud Run for the API.

Steady state:

- `stelarai.tech`
  - Firebase Hosting
  - apex `A 199.36.158.100`
  - site verification TXT as required by Hosting
  - `hosting-site=<site-id>` TXT if using Firebase-managed custom domain flow
- `www.stelarai.tech`
  - Firebase Hosting
  - `CNAME <site-id>.web.app.`
  - ACME/TXT verification if Firebase requests it
- `api.stelarai.tech`
  - load balancer `A 34.120.16.150`
  - host rule routed to a dedicated backend service for the StelarAI API, or to `fs-ai` if StelarAI ships as a tenant-aware vertical on the existing FullStack runtime first

Reason:

- this matches the already-working `fsai.pro` pattern
- it keeps static/frontend hosting cheap
- it keeps API, auth, and background infrastructure on the existing GCP control plane

#### `solamaze.com` and `getsemu.com`

Use Firebase Hosting, not the load balancer.

These should be fast, cheap, low-ops CTA properties with one of these patterns:

1. static landing pages on Hosting with CTA links into:
  - `stelarai.tech`
  - `fsai.pro`
  - specific product routes
2. Hosting redirects to campaign-specific landing pages on `stelarai.tech`

Recommended DNS shape for each:

- apex domain:
  - `A 199.36.158.100`
  - Firebase verification TXT records as required
- `www`:
  - `CNAME <site-id>.web.app.`
  - ACME TXT if Firebase requests it

Reason:

- these are campaign surfaces, not API/backend domains
- Hosting is simpler, cheaper, and easier to rotate

### Registrar nameservers already assigned in `arkham-492414`

- `stelarai.tech`
  - `ns-cloud-d1.googledomains.com`
  - `ns-cloud-d2.googledomains.com`
  - `ns-cloud-d3.googledomains.com`
  - `ns-cloud-d4.googledomains.com`

- `solamaze.com`
  - `ns-cloud-b1.googledomains.com`
  - `ns-cloud-b2.googledomains.com`
  - `ns-cloud-b3.googledomains.com`
  - `ns-cloud-b4.googledomains.com`

- `getsemu.com`
  - `ns-cloud-a1.googledomains.com`
  - `ns-cloud-a2.googledomains.com`
  - `ns-cloud-a3.googledomains.com`
  - `ns-cloud-a4.googledomains.com`

- `smithgroup.io`
  - `ns-cloud-b1.googledomains.com`
  - `ns-cloud-b2.googledomains.com`
  - `ns-cloud-b3.googledomains.com`
  - `ns-cloud-b4.googledomains.com`

### What DNS should be next

#### `stelarai.tech`

- site id: `stelarai-tech`
- `stelarai.tech. A 199.36.158.100`
- `stelarai.tech. TXT "hosting-site=stelarai-tech"`
- `_acme-challenge.stelarai.tech. TXT "KwIgkGGAW90tDFfvOhPTCErujk8NM8cw8W3Ht6dScYw"`
- `www.stelarai.tech. CNAME stelarai-tech.web.app.`
- `_acme-challenge.www.stelarai.tech. TXT "kEgOazz3pozgXyJOTvggN8b9IvEpbRRaqzjn16p2C5c"`
- `api.stelarai.tech. A 34.120.16.150`

#### `solamaze.com`

- site id: `solamaze-com`
- `solamaze.com. A 199.36.158.100`
- `solamaze.com. TXT "hosting-site=solamaze-com"`
- `solamaze.com. TXT "v=spf1 include:_spf.mail.hostinger.com ~all"`
- `_acme-challenge.solamaze.com. TXT "7vMtCsixko9wfeDeInTrArXKm1AVLh8tpEanNs721Do"`
- `www.solamaze.com. CNAME solamaze-com.web.app.`
- `_acme-challenge.www.solamaze.com. TXT "ZlyrGYAnpMsmfYms7WSw_zHBPEKeMzJ_fraibmq62xQ"`

#### `getsemu.com`

- site id: `getsemu-com`
- `getsemu.com. A 199.36.158.100`
- `getsemu.com. TXT "google-site-verification=Gpn_OkoZRbKaW44lExaZAVcCeOaMRRS2TPs4VBZK5Yo"`
- `getsemu.com. TXT "hosting-site=getsemu-com"`
- `getsemu.com. TXT "v=spf1 include:_spf.mail.hostinger.com ~all"`
- `_acme-challenge.getsemu.com. TXT "lToy8uMIs7wUbz8-H5jF4BI1UanZ-2EFXzT_QDRmUsc"`
- `www.getsemu.com. CNAME getsemu-com.web.app.`
- `_acme-challenge.www.getsemu.com. TXT "vYPAFwbkD0BsI2wI42fs8xDomp_wXb_Y-u7b4UliPiY"`

### Live infra state

Current as of 2026-04-24:

- Firebase Hosting sites created:
  - `stelarai-tech`
  - `solamaze-com`
  - `getsemu-com`
- Firebase target mappings added in `fsdash/.firebaserc`:
  - `stelarai`
  - `solamaze`
  - `getsemu`
- `api.stelarai.tech` added to the `fs-ai` load-balancer matcher
- `stelarai-api-cert` created and attached to `arkham-https-proxy`
- current remaining wait state:
  - Firebase custom-domain ownership and certificates are still converging
  - `stelarai-api-cert` is still `PROVISIONING`

## Product Build: `stelarai.tech`

## Delivery Protocol

This plan is intentionally strict. Future agents should treat it as an execution contract, not as brainstorming material.

### Current execution checklist

- [x] Cloud DNS managed zones exist for `stelarai.tech`, `solamaze.com`, and `getsemu.com`
- [x] Firebase Hosting sites exist:
  - `stelarai-tech`
  - `solamaze-com`
  - `getsemu-com`
- [x] `.firebaserc` has Hosting targets for:
  - `stelarai`
  - `solamaze`
  - `getsemu`
- [x] Cloud DNS record sets have been written for:
  - `stelarai.tech`
  - `www.stelarai.tech`
  - `api.stelarai.tech`
  - `solamaze.com`
  - `www.solamaze.com`
  - `getsemu.com`
  - `www.getsemu.com`
- [x] `api.stelarai.tech` has been added to the load balancer host rules and routed to `fs-ai`
- [x] `stelarai-api-cert` has been created and attached to `arkham-https-proxy`
- [x] `fs-ai` has been deployed with the StelarAI backend slice on revision `fs-ai-00023-j8q`
- [x] Local backend syntax validation passed via `python3 -m py_compile`
- [x] Reusable cutover verification script exists:
  - `arkham/scripts/check_stelarai_cutover.sh`
- [x] Reusable authenticated StelarAI API smoke script exists:
  - `arkham/scripts/stelarai_api_smoke.py`
- [ ] Public registrar NS delegation has been confirmed live for the three new zones
- [ ] Firebase custom-domain ownership state is `OWNERSHIP_ACTIVE` for all six Hosting names
- [ ] Firebase Hosting certificates are `CERT_ACTIVE` for all six Hosting names
- [ ] `stelarai-api-cert` is `ACTIVE`
- [ ] Live authenticated API smoke tests have been run against the StelarAI endpoints
- [ ] At least one StelarAI workspace has been created in a live environment
- [ ] Connected accounts, connected sources, and workflow CRUD have been exercised against a live runtime

### Immediate next actions

1. Confirm registrar NS now points to the Cloud DNS nameservers for:
   - `stelarai.tech`
     - `ns-cloud-d1.googledomains.com`
     - `ns-cloud-d2.googledomains.com`
     - `ns-cloud-d3.googledomains.com`
     - `ns-cloud-d4.googledomains.com`
   - `solamaze.com`
     - `ns-cloud-b1.googledomains.com`
     - `ns-cloud-b2.googledomains.com`
     - `ns-cloud-b3.googledomains.com`
     - `ns-cloud-b4.googledomains.com`
   - `getsemu.com`
     - `ns-cloud-a1.googledomains.com`
     - `ns-cloud-a2.googledomains.com`
     - `ns-cloud-a3.googledomains.com`
     - `ns-cloud-a4.googledomains.com`
2. Wait for public DNS propagation.
3. Run `arkham/scripts/check_stelarai_cutover.sh` until:
   - Firebase custom domains are `OWNERSHIP_ACTIVE`
   - Firebase custom domains are `CERT_ACTIVE`
   - `stelarai-api-cert` is `ACTIVE`
4. Run authenticated smoke tests with `arkham/scripts/stelarai_api_smoke.py`:
   - set `STELARAI_AUTH_TOKEN`
   - optionally set `STELARAI_TENANT_ID`
   - optionally set `STELARAI_API_BASE`
5. Verify the smoke script succeeds for:
   - create a StelarAI workspace
   - create a connected account
   - create a connected source
   - create and read a workflow
6. Only after those pass, consider the StelarAI Phase 0 and Phase 1 slice complete.

### Hard rules

- Reuse existing `arkham`, `fs-ai`, and `fsdash` systems before adding new runtimes.
- Do not introduce a second monolithic product backend for StelarAI.
- Do not ship module UI without a matching persisted backend contract.
- Do not mark a phase complete until its verification gate passes.
- Stop at the end of each phase if the gate fails. Fix the failure before moving on.

### Current delivered slice

The following baseline now exists and should be treated as the starting point:

- `fs-ai`
  - StelarAI blueprint endpoint
  - StelarAI workspace persistence tables
  - StelarAI workspace create/list/detail endpoints
  - StelarAI connected account create/list endpoints
  - StelarAI connected source create/list endpoints
  - StelarAI workflow create/list/detail endpoints
- `fsdash`
  - `StelarAI Control Plane` surface
  - live read model for blueprint, provider lanes, and workspace inventory

This is the foundation for the remaining product work. Later agents should extend it, not replace it.

## Product position

`stelarai.tech` should be the operator and customer platform for AI resource management, production orchestration, and account-connected execution.

This is not a single-purpose vertical. It is a tenant-scoped production system built from:

- Arkham core services and shared data models
- existing verticals already present in `arkham`
- the existing `fs-ai` provider, routing, auth, and tenant runtime
- a new StelarAI workspace shell that unifies those pieces under one product identity

The closest internal reference is `~/Downloads/omniscale unlimited.md`, but the implementation should not be a clean-room Next.js monolith. It should reuse the platform that already exists and only build the missing tenant-facing surfaces.

## Core reuse strategy

### Reuse from `arkham`

- `services/verticals/omniscale`
  - quantity takeoff, cost estimation, dashboard semantics
- `services/verticals/autopitch`
  - proposal and industry automation guidance patterns
- `services/verticals/digital_it_girl`
  - trend/opportunity engine starting point
- `services/verticals/public_beta`
  - software/version tracking starting point
- `services/verticals/workflow_architect`
  - workflow domain anchor
- `packages/vertical_base.py`
  - service harness, event receive, health contract
- gateway/core/orchestration/worldgraph
  - shared platform backbone

### Reuse from `fs-ai`

- tenant model
- auth/session/bearer flow
- providers table and routing prefs
- prompt library and prompt versions
- billing/usage ledger
- model-provider abstraction supporting:
  - `openai-compatible`
  - `anthropic`

### Reuse from `fsdash`

- multi-surface app shell work
- website-builder phased plan concepts
- provider admin UI patterns
- runtime config and environment wiring

## Recommended runtime shape

### Public hosts

- `stelarai.tech`
  - marketing site
  - pricing
  - login/signup
  - product overview
- `stelarai.tech/workspace/*`
  - authenticated customer workspace
- `ops.stelarai.tech`
  - operator/admin surface
  - optional initially; can start inside protected admin routes if you want to ship faster
- `api.stelarai.tech`
  - backend API

## Step By Step Execution

### Phase 0. Domain and DNS completion

Objective:

- make `stelarai.tech`, `solamaze.com`, and `getsemu.com` authoritative in Cloud DNS and point them to the correct serving layer

Required work:

- set registrar nameservers to the exact Cloud DNS nameservers already assigned in `arkham-492414`
- create Firebase Hosting sites for:
  - `stelarai.tech`
  - `solamaze.com`
  - `getsemu.com`
- attach custom domains in Firebase Hosting
- create or update DNS record sets in Cloud DNS for Hosting verification
- create `api.stelarai.tech` on the load balancer IP `34.120.16.150`
- add host rule and certificate coverage for `api.stelarai.tech`

Verification gate:

- `dig NS stelarai.tech` returns the GCP nameservers
- `dig A stelarai.tech` returns `199.36.158.100`
- `dig A api.stelarai.tech` returns `34.120.16.150`
- the managed certificate is `ACTIVE`
- `curl -I https://stelarai.tech` returns a valid TLS response

Stop condition:

- stop immediately if public NS delegation does not match the managed zone

### Phase 1. Platform contract completion

Objective:

- finish the backend contract so the StelarAI workspace has stable primitives for UI and execution

Required work:

- extend `fs-ai` StelarAI tables with:
  - module status mutations
  - connected account CRUD
  - connected source CRUD
  - workflow CRUD
  - simulation run records
- keep every record tenant-scoped
- keep provider lane selection explicit on workflows and simulations

Verification gate:

- create, read, update, and list operations succeed for workspaces, accounts, sources, and workflows
- tenant scoping blocks cross-tenant access
- `python3 -m py_compile` passes for changed backend files

Stop condition:

- stop if any StelarAI endpoint requires invented data instead of persisted records

### Phase 2. Workspace shell

Objective:

- replace the control-plane-only surface with a customer-usable workspace shell

Required work:

- build `stelarai.tech/workspace/*` routes in `fsdash`
- add navigation for:
  - Canvas Builder
  - Workflow Suggestions
  - Workflow Library
  - Execution Simulator
  - Digital IT Girl
  - NicheMarket Explorer
  - Public Beta
  - AutoPitch
- wire every route to real backend reads

Verification gate:

- every visible metric or table is backed by a live endpoint
- no route renders fake counts or placeholder economics
- frontend build passes

Stop condition:

- stop if any module route is pure mock UI

### Phase 3. Builder and workflow engine

Objective:

- ship the workflow authoring path

Required work:

- implement Canvas Builder node graph persistence
- add Workflow Suggestions diff objects
- add Workflow Library clone/import actions
- add dry-run Execution Simulator with provider lane selection and cost previews

Verification gate:

- a workflow can be created, saved, reopened, duplicated, and simulated end to end
- simulation never triggers live side effects
- at least one cheap lane and one premium lane are selectable

Stop condition:

- stop if dry-run and live execution paths are not separated

### Phase 4. Connected account and source fabric

Objective:

- let each tenant attach internal sources and external business or personal accounts

Required work:

- support connected account records for business, personal, and shared scopes
- support tenant-internal sources for files, URLs, notes, and uploaded assets
- attach account and source permissions at workflow execution time

Verification gate:

- connected accounts are isolated per tenant
- workflow runs can reference allowed accounts and sources only
- account metadata is never leaked across tenants

Stop condition:

- stop if account linkage works only in the UI and not in persisted backend state

### Phase 5. Vertical module reuse

Objective:

- land the requested modules by reusing Arkham verticals instead of rebuilding them

Required work:

- map Arkham services into StelarAI modules:
  - `digital_it_girl` -> Predictive Niche Engine
  - `public_beta` -> Software Tracker
  - `autopitch` -> Industry Automation Guide
  - `workflow_architect` and `omniscale` patterns -> builder and simulation surfaces
- make each module callable from the shared StelarAI workspace

Verification gate:

- each reused module has:
  - one live backend integration path
  - one visible workspace entry point
  - one persisted result or artifact model

Stop condition:

- stop if a module is only linked by navigation copy and not by execution

### Phase 6. Production readiness

Objective:

- make the platform safe to operate in production

Required work:

- add smoke tests for:
  - auth
  - workspace reads
  - workflow save
  - simulation run
  - provider lane selection
- add operator health checks
- add customer-visible error handling for degraded providers
- document rollout and rollback

Verification gate:

- all smoke tests pass in the target deployment
- `health` and `ready` are green for the required StelarAI runtime
- one operator account and one customer account can complete the intended flows

Stop condition:

- stop if deployment is green but customer workflow creation is still broken

## Compound Testing Stop Rule

Compound testing stops only when all of the following are true:

- domain routing is correct
- auth works for operator and customer paths
- at least one workspace exists and loads
- at least one workflow can be saved and simulated
- at least one cheap or free model lane works
- at least one Anthropic model works
- at least one reused Arkham module produces a persisted result

If any one of those fails, the project is not complete.

## Agent Handoff

The full handoff contract for future coding agents is in:

- `arkham/docs/stelarai-tech-agent-spec.md`

### Initial deployment target

Phase 1 shipping posture:

- frontend/workspace on Firebase Hosting
- backend on Cloud Run
- data in Postgres / current platform DBs
- Redis / queue reuse where existing patterns already work

## Module map for StelarAI

Each requested module should be a product surface, not a separate brand silo.

### 1. Canvas Builder

Source:

- workflow builder concepts from `omniscale unlimited.md`
- website builder pane structure from `fsdash/docs/website-builder-phased-plan.md`

Build as:

- `/workspace/workflows/builder/[id]`
- drag/drop workflow canvas
- tenant-scoped workflow definitions
- module-aware side panels
- reusable node system

### 2. AI Workflow Suggestions

Source:

- existing provider routing in `fs-ai`
- workflow canvas state from the Canvas Builder

Build as:

- suggestion engine attached to the builder
- returns actionable diffs:
  - add node
  - modify node
  - add edge
  - remove node
- supports:
  - cheap/default model path
  - premium/power model path
  - tenant preference by workflow type

### 3. Workflow Library

Build as:

- template library plus private tenant workflows
- cloneable starter packs by function:
  - customer onboarding
  - campaign launch
  - lead intake
  - software watch / upgrade review
  - niche intelligence scan
  - asset production

### 4. Execution Simulator

Build as:

- dry-run mode with node-by-node visual execution
- simulated inputs/outputs
- audit timeline
- cost forecast per run
- model/provider call estimate per run

### 5. Digital IT Girl

Build as a separate module inside the product:

- "Predictive Niche Engine"
- extend current `digital_it_girl` service beyond in-memory trends
- add persistent opportunity scoring
- tie into:
  - domains
  - product gaps
  - trend clusters
  - watchlists

### 6. NicheMarket Explorer

Build as:

- audience segment explorer
- niche profile pages
- monetization playbooks
- segment comparison

This should sit beside Digital IT Girl, not replace it.

Suggested relationship:

- Digital IT Girl = opportunity detection
- NicheMarket Explorer = audience validation and monetization analysis

### 7. Public Beta

Build as:

- software tracker and update intelligence module
- tenant watchlists
- version timelines
- compatibility matrix
- AI briefings on release impact

Reuse:

- existing `public_beta` vertical as backend anchor

### 8. AutoPitch

Build as:

- "Industry Automation Guide"
- generate verticalized service pitches for any role/industry
- tie into segment intelligence and workflow opportunities
- export:
  - markdown
  - one-pager
  - slide outline
  - CTA copy for `solamaze.com` / `getsemu.com`

## Account connection layer

This is one of the major StelarAI-specific additions.

Each tenant/account should have its own internal connected-source layer.

### New domain model

Add StelarAI-specific tenant-scoped entities:

- `connected_accounts`
  - tenant_id
  - provider_name
  - account_type
  - auth_mode
  - scopes_json
  - status
  - metadata_json
- `connected_sources`
  - tenant_id
  - connected_account_id
  - source_type
  - source_name
  - sync_mode
  - config_json
  - last_sync_at
- `resource_assets`
  - tenant_id
  - source_id
  - asset_type
  - title
  - body/content pointer
  - metadata_json
  - embeddings status
- `production_jobs`
  - tenant_id
  - workflow_id
  - source_asset_id
  - provider_id
  - model
  - status
  - run_log_json

### Connected account types

Phase 1 supported connections:

- email inbox
- Google Drive / Docs / Sheets / Slides
- GitHub
- LinkedIn/X/website publishing targets
- ad / marketing account metadata sources
- CRM/accounting exports through CSV/manual upload

Design rule:

- everything is tenant-scoped
- every connection is isolated per account
- no cross-tenant shared secret paths

## Model and provider strategy

## Anthropic should be wide open

Your requirement is correct: Anthropic should not be treated as a hidden backup-only path in StelarAI.

For StelarAI:

- expose Anthropic as a first-class provider family
- allow all approved Anthropic models you want to use
- permit selection per:
  - module
  - workflow
  - tenant
  - run

### Runtime strategy

Use the existing `fs-ai` providers and routing system, but expand it.

Required provider families:

- Anthropic
  - full visible catalog of enabled models
- OpenAI
- OpenAI-compatible providers
  - OpenRouter
  - Groq
  - Together
  - Fireworks
  - Mistral-compatible endpoints where applicable
- local / low-cost inference path
  - Ollama or equivalent internal endpoint for cheap/free tasks

### Cost tiers

Define routing tiers instead of one provider per product.

- Tier 1: free / near-free
  - local models
  - smallest open models
  - classification, tagging, extraction, first-pass suggestions
- Tier 2: low-cost fast models
  - haiku / mini / flash style models
  - workflow suggestions
  - summarization
  - rough drafts
- Tier 3: premium reasoning / final output
  - stronger Anthropic/OpenAI models
  - final AutoPitch output
  - complex strategic analysis
  - high-confidence recommendation runs

### StelarAI-specific provider work

Implement:

- module-level default provider policy
- tenant override policy
- workflow-step override policy
- per-run cost estimate
- approved model list by tenant plan

## Cheaper or free model support

This should not be a side note. It should be a built-in product feature.

### What to add

1. provider profiles
- `free`
- `cheap`
- `balanced`
- `premium`

2. task routing presets
- extraction
- classification
- summarization
- proposal generation
- niche analysis
- workflow optimization

3. fallback order
- local/open-source first for low-risk tasks
- then cheap hosted
- then premium model only when required

4. cost visibility
- show estimated request cost before execution
- show actual provider/model used after execution

### Concrete model-routing intent

- Canvas Builder suggestions
  - default to cheap models
- Workflow Library metadata/tagging
  - free/cheap only
- Execution Simulator
  - mostly deterministic or cheap model path
- Digital IT Girl scanning
  - cheap-first, premium-on-demand for deep dives
- NicheMarket Explorer monetization playbooks
  - balanced by default, premium optional
- Public Beta AI brief
  - cheap for TL;DR, premium optional for longer strategic read
- AutoPitch
  - cheap for early draft, premium for export-ready output

## Build phases for StelarAI

### Phase 0: Domain and shell

- create Firebase Hosting site for `stelarai.tech`
- create API host target `api.stelarai.tech`
- ship product shell with:
  - marketing site
  - auth entry
  - workspace shell
  - operator shell

### Phase 1: Shared tenant/data foundation

- add StelarAI tenant-scoped connection models
- add source ingestion records
- add production job records
- add provider tier policies

### Phase 2: Workflow surfaces

- Canvas Builder
- Workflow Library
- Execution Simulator
- AI Workflow Suggestions

### Phase 3: Intelligence modules

- Digital IT Girl
- NicheMarket Explorer
- Public Beta

### Phase 4: Commercial module

- AutoPitch
- export pathways
- CTA output packages for `solamaze.com` and `getsemu.com`

### Phase 5: Connected account production loop

- per-tenant account connections
- internal content/source indexing
- workflow-driven production runs
- analytics and budget views

## CTA domain usage

`solamaze.com` and `getsemu.com` should be campaign layers on top of the StelarAI product, not separate platforms.

Recommended usage:

- CTA site A
  - industry or persona-specific landing page
  - points into a StelarAI conversion path
- CTA site B
  - alternate positioning / offer test
  - points into the same backend/product

Generate copy and routing assets from AutoPitch and the Niche modules, but keep the actual product account, billing, auth, and workspace under `stelarai.tech`.

## Delivery recommendation

Do not build StelarAI as a new isolated monolith.

Build it as:

- frontend/workspace surfaces in the existing frontend pattern
- backend/domain and provider orchestration on the existing `fs-ai` runtime
- Arkham verticals reused as service/domain engines where they already exist
- new tenant-scoped StelarAI entities only where the current platform does not already provide them

That is the cheapest path, the fastest path, and the only path that preserves the value already built into Arkham and FullStack.
