# Arkham Project Brief and Master Todo

Last updated: 2026-04-23

## Project Brief

Arkham is now best understood as an AI operating platform with a real control plane, a governed workflow layer, a growing shared data layer, and a set of product and vertical surfaces that can turn infrastructure into revenue. The platform is no longer in the “idea plus scattered prototypes” phase. It has crossed into a more serious stage where the main challenge is no longer whether the system can be assembled, but whether it can be turned into stable product usage, clean operations, and repeatable commercial offers.

The current company-level priority is to convert platform progress into product gravity. In practical terms, that means the team should stop defaulting to new architecture work every time the system becomes more coherent. The platform already has enough substance to support real usage. The focus now should be on three things: keeping the control plane reliable, keeping Worldgraph stable enough to stay useful, and turning PapaBase plus the strongest existing verticals into live operator and customer-facing value.

The business logic behind the current priority order is straightforward. The CTO control plane exists to reduce uncertainty and govern change. Worldgraph exists to become a reusable shared data layer, but only after its current staging-valid footprint remains stable. PapaBase is the first real non-AEC product loop with obvious operator utility, so it should become the first place where the company proves product gravity outside of internal infrastructure work. In parallel, the strongest AEC verticals should be packaged into a small number of clearly sellable services rather than left as disconnected technical capabilities.

## Current Platform Position and What It Means Operationally

The current build has reached a mixed but usable operational state. The CTO control plane is active and already useful for read-only audits, remediation planning, artifact creation, and gated workflow handling. That means the system can already inspect the codebase, persist its findings, classify risk, stop at approval boundaries, and resume in a controlled way. This is enough to treat it as an operational governance tool, even though it is not yet approved for broad mutation-capable execution.

Worldgraph travel version 1 is staging-valid and now has a deterministic smoke path. This matters because the team no longer needs to argue about whether Worldgraph “exists.” It does exist. It has a service, a worker, a schema, a smoke path, a runbook, and a clear operator footprint. The main job now is to keep that state stable and resist unnecessary churn until product surfaces actually need more from it.

The controlled rename program has also moved out of theory and into verified execution. Dual-tagging is active. The new registry path is now the default. Controlled-tier deploys have been proven on `arkham-containers`, and the legacy path remains in place as rollback insurance. That means the safe part of the rename work is largely done. What remains is the high-risk, breaking-tier work around physical infrastructure names, networking, and database cutover.

PapaBase is the clearest product opportunity in the current system. Its minimum viable loop has already been proven locally: create a user, create a lead, move it through a sales and fulfillment pipeline, create tasks, complete tasks, and retrieve the resulting state. That is enough to justify immediate live deployment and real operator usage. PapaBase does not need to wait for the whole platform to become perfect.

The breaking infrastructure migration is the main technical risk sitting in the background. Wave 1 has already been completed through Terraform state movement. Wave 3, the database migration, has been fully scripted and passed pre-flight review, but is intentionally in `HOLD` pending the execution window. That means the team should treat the migration plan as frozen and avoid introducing unrelated changes before the cutover occurs.

## Work That Requires Immediate Attention Right Now

### Deploy the PapaBase Minimum Viable Product to a Live Environment

The first immediate priority is to deploy the current PapaBase MVP into a real hosted environment and verify that the lead-to-paid loop works outside local testing. The local proof is already good enough to justify this move. What matters now is whether the loop behaves cleanly under live conditions, with real requests, real sessions, and the latency or deployment quirks that do not show up during local development.

This work should remain narrow. The goal is not to turn PapaBase into a fully formed life-and-business operating system this week. The goal is to get the proven minimum viable loop live: user creation, lead entry, pipeline transitions, task creation, task completion, and basic retrieval. If that path works in a live environment, the product moves from “promising internal prototype” to “real system that can support field usage.”

### Build the Minimum Mobile-Friendly PapaBase Frontend for Real Usage

The second immediate priority is the minimum mobile-friendly interface for PapaBase. The product is not going to teach the company anything useful if it only exists as an API. The first real operator will not experience “the architecture”; they will experience whether it is fast and clear to enter a lead, tap a stage change, add a follow-up task, and see what is next.

That means the frontend should stay brutally simple. It needs lead entry, visible pipeline buttons, a task list, and a small number of list views that are usable on a phone. This is not the moment to design a broad dashboard with settings, multi-role complexity, or deep platform abstractions. The frontend’s only job right now is to make operator-zero testing real.

### Run Founder-Led Operator-Zero Validation on the Actual Product Loop

Before the company pushes PapaBase into outside hands, it should be used seriously by the founder in real work. This matters because founder usage is the fastest way to find the kind of friction that architecture diagrams hide: the missing field, the awkward status transition, the task that should have been automatic, the mobile tap target that is too small, or the ambiguity about when a lead is really “done.”

The target should be at least ten real loops. Not ten synthetic test flows. Ten actual loops through real work. The point is to learn where the product saves time, where it creates drag, and what has to be fixed before asking even friendly users to trust it.

### Package the Most Mature Vertical Capabilities Into a Sellable Offer

The platform has matured enough that one side workstream should now be revenue-oriented rather than purely architectural. The strongest current verticals are already obvious: `AutoPitch`, `Cyberscribe`, `Omniscale`, and `AI Consistency`. The immediate commercial move is not to present those as a platform constellation. The immediate commercial move is to package them into a few sharply defined AEC services that a buyer can understand quickly.

The first menu should stay narrow. The best current anchor offer is `Proposal Sprint`, with `Scope + Spec Starter` and `Coordination Risk Review` as adjacent offers. PapaBase should support this commercially as the internal operator loop for lead, quote, schedule, invoice, and follow-up. That way, the company is using one new product to help sell and deliver the outputs of the more mature verticals.

### Preserve the Wave 3 Database Migration Plan in a Stable Ready-to-Execute State

The Wave 3 cutover plan is ready enough that the main job is now discipline, not more invention. Until the execution window begins, this plan should be treated as stable. The team should avoid unrelated Terraform edits, unrelated secret changes, or casual deploys that would move the operational ground under the cutover process.

In practical terms, this means keeping the incident log ready, keeping the rollback path intact, and avoiding the temptation to “clean up one more thing” before the window. The risk now is not lack of planning. The risk is introducing fresh variables into a plan that has finally become mechanical.

### Maintain Worldgraph Travel v1 as a Stable and Deterministic Staging Service

Worldgraph has reached the point where reliability matters more than additional features. The service, worker, trigger job, and verify job now form a stable footprint. The fixture-backed smoke path is the canonical staging mode because it is deterministic. The live `http` path remains useful, but it should not be allowed to destabilize the staging contract.

Operationally, the right move is simple: keep the current staging shape stable, keep the runbook accurate, keep auxiliary jobs classified but not proliferating, and avoid opening new Worldgraph workstreams until product demand justifies them.

## Work That Should Happen Immediately After the Current Priorities Are Stable

### Decide Whether PapaBase Needs Durable Persistence Before External Pilot Use

Once founder usage has revealed whether PapaBase behaves cleanly in live conditions, the next question is whether the MVP can tolerate in-memory persistence for a short period or whether real pilot usage requires durable storage immediately. The answer should not be ideological. It should depend on whether live operator use makes container restarts, state loss, or audit gaps unacceptable.

If the product is still in short demo mode, durable persistence can wait briefly. If the company is about to recruit real operators and ask them to trust the loop, then persistence should be added before wider pilot use. That is when Firestore or another appropriate storage layer becomes operationally necessary rather than architecturally attractive.

### Run a Small Friendly-Operator Pilot After Founder Usage Stabilizes

The first external pilot should stay small and warm. The goal is not to “launch.” The goal is to expose the loop to a handful of real operators who will tolerate rough edges and still tell the truth. One to three users is enough for this stage. The product does not need volume yet; it needs signal.

The pilot should look for simple proof: can one real lead move through the loop, can one real task get completed, can the operator describe whether this saved time, and would they want to use it again. That is enough to decide whether the loop deserves another week of product effort or requires a correction first.

### Convert PapaBase From a Proved Loop Into a Clear Product Contract

PapaBase is already moving beyond “family CRM” or “simple operator loop.” It is increasingly clear that the company wants it to become a father-led life and business operating system with support for household operations, founder planning, business suite automations, document generation, web development support, and brand identity support. That is fine, but it has to be written down as a proper product contract before the surface area sprawls.

The next step is to formalize the product definition: core workflows, required entities, approval boundaries, artifact types, and success metrics. The platform can support a wider ambition, but the product should still be explicit about what it is trying to do first.

### Validate the Database Cutover Thoroughly After the Wave 3 Execution Window

If the Wave 3 cutover executes successfully, the immediate next work should not be “move on.” It should be validation. The platform needs row-parity confidence, service connectivity confidence, workflow and memory write confidence, and specific confirmation that Worldgraph still behaves correctly against the new database path.

Only after that post-cutover validation is clean should the program reopen discussion of Wave 2 network work. Anything else would turn a hard-earned clean cutover into another unstable transition.

### Improve Worldgraph Live-Data Reliability Without Destabilizing the Smoke Path

Worldgraph’s deterministic smoke path is now a strength. The next work should improve live-data reliability without compromising that strength. That means keeping `fixture` as the staging default, keeping `http` as a higher-fidelity option, and deciding whether `gcs` snapshot mode should become the standard non-live staging path.

This is not glamorous work, but it is important. If Worldgraph becomes more useful while becoming less reliable, the platform will end up with another technical showcase rather than a dependable shared service.

### Clean Up Legacy and Auxiliary Worldgraph Jobs Only Through Deliberate Review

The remaining Worldgraph auxiliary jobs should not be deleted casually. The right approach has already been established: classify them, keep what still serves an operational purpose, mark what is superseded, and remove only what can be shown to be genuinely dead.

That means `arkham-worldgraph-migrate` and `arkham-worldgraph-dbcheck` should remain until they are clearly replaced, while superseded job paths should be removed only in explicit cleanup passes. The goal is not aesthetic tidiness. The goal is clear operational intent.

## Work That Matters, But Should Be Deferred Until the Current Critical Path Is Finished

### Expand PapaBase Into a Broader External Pilot Only After the First Real Learning Loop

PapaBase should absolutely expand if the early loop proves useful. But it should not expand before the company has real founder usage and a small friendly-user pilot. The larger pilot, five to ten real operators, is the next meaningful step only after the first learning loop has stabilized.

At that point the company can test higher-value product questions: loop completion, time saved, willingness to pay, and referral intent. Until then, broader pilot activity is more likely to produce noise than truth.

### Roll Out Additional Product and Vertical Integrations in the Correct Sequence

The broader product roadmap still makes sense, but it should remain subordinate to PapaBase proving itself as the first real anchor. The intended order remains coherent: PapaBase first, then MamaNav, then RentOut, then ParkNow, then Travel India, then the BIM young adult track. That order reflects both platform leverage and product realism.

The point of the sequence is not perfection. It is compounding. PapaBase should teach the platform how to become a product. The later rollouts should benefit from that learning instead of repeating its mistakes.

### Expand Worldgraph Beyond the Current Travel v1 Scope

Worldgraph has obvious future growth ahead of it. Property namespace support, richer normalization and promotion flows, and broader enrichment pipelines all belong on the roadmap. But they should remain “later” work until either product demand or platform demand forces them forward.

Right now, Worldgraph’s highest-value job is to stay stable and useful in its current shape. Expansion should happen because it is needed, not because it is possible.

### Move the CTO Control Plane From Read-Only Audits Into Approved Mutating Actions

The CTO control plane is already useful in a read-first mode. The long-term move is obvious: allow it to make approved code, deploy, and infrastructure changes through gated workflows. But that is a second-order problem. The current first-order value is that it can already inspect, classify, pause, document, and hand work back safely.

Mutation-capable execution should come later, after the platform has more evidence that its audit logic, approval logic, and rollback logic behave well under real operational pressure.

### Complete the Remaining Breaking Infrastructure Migration After the Database Move Is Proven

The remaining breaking migration work still matters. Wave 2 network migration, runtime renaming, and the deeper removal of legacy `robco-*` physical names are all still on the path. But they should remain deferred until the database move succeeds and stabilizes. The database cutover is the more important risk. It should not be crowded by additional high-risk transitions.

## Work That Is Intentionally Blocked Until Other Conditions Are Met

### Keep the Wave 2 Network and Connectivity Migration Frozen Until the Database Cutover Is Stable

Wave 2 should stay frozen. This is not caution for its own sake. It is fault isolation. A network and connectivity migration becomes much harder to diagnose if it is introduced before the database cutover has proven itself under real conditions. The correct dependency is now clear: the DB move executes first, the DB move validates cleanly, and only then does Wave 2 become a live workstream again.

### Delay Higher-Integrity Database Evolution Until the Postgres Collation Issue Is Addressed

The Postgres collation mismatch is now known infrastructure debt. That does not mean it blocks the immediate Wave 3 cutover, but it does mean it should continue to block the next layer of high-integrity database work. If the company later needs stronger guarantees around schema evolution, index integrity, or migration hygiene, this mismatch should be resolved before that work begins.

### Do Not Make Full Live External Ingest the Default for Worldgraph Staging Yet

Worldgraph has already taught the platform an important lesson: a higher-fidelity staging path is not the same as a better staging path. Live external fetches are useful, but they are less deterministic and more failure-prone than fixture-backed smoke. Until the team explicitly wants a higher-risk staging mode, the canonical smoke path should stay deterministic.

## Workstream-by-Workstream Summary of the Entire Current Program

### The CTO Control Plane and Governance Workstream

This workstream is active and already valuable. Its current role is to inspect, classify, and gate change rather than to mutate the system directly. It has proven that it can create durable workflows, persist artifacts, remember technical context, and stop at approval boundaries. The next move is not to overreach. The next move is to keep it useful, reliable, and disciplined while the rest of the platform becomes more operational.

### The Worldgraph Shared Data Layer Workstream

Worldgraph is now a real shared service rather than a speculative architecture box. Travel v1 is staging-valid. The smoke path is reliable. The operational footprint is documented. The current job is not reinvention. The current job is to protect that state, let it support real needs, and only expand it when platform or product demand makes the next step obvious.

### The Controlled Rename and Registry Migration Workstream

This workstream has crossed an important threshold: the controlled tier is complete. Dual-tagging is active, the new registry path is the default, and controlled services have proven deploys using the new path. That means the remaining rename work is no longer “easy hygiene.” It is breaking-tier migration work. The correct next move is to leave that work frozen until the database cutover is behind the team.

### The PapaBase Product Workstream

PapaBase is the most important product workstream now. It has already proved the minimum viable operator loop locally. It has also expanded conceptually from a simple loop into the likely foundation for a broader life-and-business operating product. The right next move is not more concept work. The right next move is live deployment, mobile-friendly usage, and actual founder-led loops in production conditions.

### The Sellable Vertical Packaging and Early Revenue Workstream

The platform has enough mature vertical capability that it should now support a direct revenue workstream. The strongest current offer is the AEC services bundle built from AutoPitch, Cyberscribe, Omniscale, and AI Consistency. The correct commercial move is not to sell “the platform.” It is to sell a small number of productized offers, starting with Proposal Sprint and then layering in adjacent scope and coordination services.

### The Broader Product Expansion Workstream

The broader roadmap remains intact, but it should stay in sequence. There is no prize for starting every product at once. PapaBase should become the first real product anchor. Then the later products can inherit lessons from something that has already survived contact with users.

## Decision Rule for Choosing What to Work on When Tradeoffs Appear

When choosing between two plausible pieces of work, the deciding question should be simple: which option moves the platform closer to real user loops, stable operations, or near-term revenue without creating avoidable risk?

Right now, that means the order is clear. PapaBase deployment and use matter more than new architecture. Keeping the Wave 3 cutover plan stable matters more than opening new migration workstreams. Keeping Worldgraph stable matters more than feature expansion. Packaging the strongest verticals into sellable offers matters more than abstract roadmap growth.
