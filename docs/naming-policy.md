# Arkham Naming Policy

Last updated: 2026-04-23

## Purpose

This document separates:

- brand architecture
- product architecture
- platform architecture
- technical naming

The goal is to stop business-layer names from leaking into infrastructure by default, while preserving the correct long-term company and product structure.

## Naming Hierarchy

### 1. Ownership Layer

`RobCo` is the capital, ownership, and portfolio layer.

Use `RobCo` for:

- holding company language
- investor and ownership framing
- portfolio-level brand architecture
- umbrella product ecosystem language when intentional, such as `RobCoFamily`

Do not use `RobCo` as the default prefix for every service, database, VPC, registry, or Terraform resource.

### 2. Platform Layer

`FullStack` is the shared execution engine.

Use `FullStack` for:

- shared runtime and execution platform language
- shared orchestration and product-operating substrate
- internal platform documentation
- cross-product systems that are not themselves products

`FullStack` is the correct conceptual owner of shared execution capability, but it does not need to appear in every low-level cloud resource name.

### 3. Governance Layer

`Arkham` is the external trust, governance, and security orbit.

Use `Arkham` for:

- governance services
- trust and review systems
- control-plane oversight
- external security and safety framing
- policy, parole, audit, and consistency systems

Examples:

- `arkham`
- `arkham-sidecar`
- `arkham-worldgraph` if treated as a governed platform-adjacent shared service

### 4. Product Layer

Product names should appear directly where a service or user-facing system is actually product-specific.

Current examples:

- `PapaBase`
- `NavFam Global`
- `ParkNow`
- `Dad AI`

Use product names for:

- product services
- product routes
- product UI labels
- product-specific storage and workflows
- revenue-facing systems

## Technical Naming Rules

### Rule 1: Do not use ownership names as default infra prefixes

`RobCo` should not be the automatic prefix for:

- Cloud Run services
- Artifact Registry repositories
- Cloud SQL instances
- Redis instances
- VPCs and subnets
- Terraform resource names
- deployment scripts

If `RobCo` appears in infra, it must be intentional and documented.

### Rule 2: Name resources by operational role, not company mythology

Use the narrowest correct namespace:

- governance resources -> `arkham-*`
- product resources -> product name
- shared platform resources -> neutral platform name or documented shared namespace

Good:

- `arkham-worldgraph`
- `papabase-api`
- `papabase-web`
- `parknow-worker`

Bad:

- `robco-everything`
- mixed `robco-*` and `arkham-*` with no policy

### Rule 3: Product names win over umbrella names at the service boundary

If a service exists to power a specific product, use the product name first.

Examples:

- `papabase-api`
- `navfam-api`
- `parknow-api`

Not:

- `robco-family-api` unless it truly serves the entire ecosystem as one product boundary

### Rule 4: Governance systems may use Arkham names

If a service exists primarily for trust, safety, review, consistency, audit, or control-plane governance, `arkham-*` naming is appropriate.

Examples:

- `arkham`
- `arkham-sidecar`
- `arkham-governance`

### Rule 5: Shared registries should use a neutral or platform-approved name

Artifact Registry and similar shared delivery resources should not stay on legacy naming by accident.

Preferred:

- `arkham-containers` if that is the approved shared registry name

Allowed temporarily:

- `robco-containers` during controlled migration only

### Rule 6: Databases and network resources require extra stability

For Cloud SQL, Redis, VPC, subnet, and similar infra state:

- avoid renaming casually
- treat renames as migration work
- require explicit rollback planning
- never fold these into broad branding cleanup

## Namespace Mapping

### Business and Brand Mapping

- `RobCo` -> ownership, capital, portfolio
- `RobCoFamily` -> product ecosystem / portfolio grouping
- `FullStack` -> execution engine
- `Arkham` -> governance, trust, control
- product names -> actual application and revenue surfaces

### Runtime Mapping

- governance service names -> `arkham-*`
- product service names -> product-specific
- shared registry -> `arkham-containers`
- legacy registry -> `robco-containers` during migration only
- Terraform resource names -> stable, migration-controlled, not brand-cleanup targets

## Examples

### Good examples

- `arkham`
- `arkham-sidecar`
- `arkham-worldgraph`
- `papabase-api`
- `papabase-web`
- `navfam-api`
- `parknow-worker`
- `arkham-containers`

### Acceptable transitional examples

- `robco-containers`
- `robco-gateway`
- `robco-core`

These are acceptable only while they are covered by a documented controlled migration plan.

### Bad examples

- using `robco` as the prefix for every new service by habit
- renaming Cloud SQL, Redis, and VPC resources as part of routine branding cleanup
- mixing `Arkham`, `FullStack`, `RobCo`, and product names inside one service boundary without a clear reason

## Decision Rules

When naming a new thing, ask:

1. Is this ownership, platform, governance, or product?
2. Is this user-facing or internal?
3. Is this stable infrastructure state or replaceable delivery/runtime surface?
4. Does this name need migration planning if changed later?

Apply these defaults:

- ownership concept -> `RobCo`
- governance/control -> `Arkham`
- product surface -> product name
- stable infra -> choose carefully once, then freeze

## Current Policy Decision

As of now:

- `RobCo` remains valid at the ownership and product-ecosystem layer
- `Arkham` remains valid for governance and selected shared systems
- product names should expand at the service boundary
- legacy `robco-*` technical naming should only be changed through staged, risk-tiered migration

This means previous cleanup work should be interpreted as technical naming control, not removal of `RobCo` from the actual business architecture.
