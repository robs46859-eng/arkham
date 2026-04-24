import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from packages.db import transactional_session
from packages.models.workflow import WorkflowRunRecord, WorkflowStepRecord
from packages.models.domain import CodebaseAuditRecord, RemediationPlanRecord
from packages.models.memory import MemoryNoteRecord
from packages.schemas import WorkflowApprovalState, WorkflowStatus
from .settings import settings

logger = logging.getLogger(__name__)

# Steps for the codebase_audit workflow
AUDIT_STEPS = [
    "ingest_context",
    "memory_recall",
    "analyze_synthesize",
    "governance_check",
    "persist_artifact",
    "human_approval"
]

class CodebaseAuditWorker:
    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.running = True
        # Base path for audit (project root)
        self.base_path = Path("/Users/joeiton/arkham")

    async def run(self):
        logger.info("CodebaseAuditWorker starting...")
        while self.running:
            try:
                await self.process_pending_runs()
            except Exception as e:
                logger.exception(f"Error in worker loop: {e}")
            await asyncio.sleep(self.poll_interval)

    async def process_pending_runs(self):
        with transactional_session() as db:
            runs = (
                db.query(WorkflowRunRecord)
                .filter(WorkflowRunRecord.type == "codebase_audit")
                .filter(WorkflowRunRecord.status == WorkflowStatus.running.value)
                .all()
            )
            for run in runs:
                await self.process_run(run, db)

    async def process_run(self, run: WorkflowRunRecord, db: Session):
        logger.info(f"Processing workflow {run.id} at step {run.current_step}")
        
        # Find the active step
        step = (
            db.query(WorkflowStepRecord)
            .filter(WorkflowStepRecord.workflow_id == run.id)
            .filter(WorkflowStepRecord.step_name == run.current_step)
            .filter(WorkflowStepRecord.status == WorkflowStatus.running.value)
            .first()
        )
        
        if not step:
            logger.warning(f"No active step record found for {run.id}:{run.current_step}")
            return

        try:
            # Execute step logic
            new_checkpoint = await self.execute_step_logic(run, step, db)
            
            # Update current step as complete
            step.status = WorkflowStatus.complete.value
            step.completed_at = datetime.utcnow()
            step.checkpoint = new_checkpoint
            
            # Transition to next step
            current_idx = AUDIT_STEPS.index(run.current_step)
            if current_idx < len(AUDIT_STEPS) - 1:
                next_step_name = AUDIT_STEPS[current_idx + 1]
                run.current_step = next_step_name
                
                # Explicitly re-assign to trigger SQLAlchemy mutation tracking
                updated_checkpoint = dict(run.checkpoint)
                updated_checkpoint.update(new_checkpoint)
                run.checkpoint = updated_checkpoint
                
                # Special case: transition to paused for human_approval
                if next_step_name == "human_approval":
                    if run.status != WorkflowStatus.paused.value:
                        run.status = WorkflowStatus.paused.value
                        run.approval_state = WorkflowApprovalState.pending.value
                        run.approval_requested_at = datetime.utcnow()
                        run.approval_resolved_at = None
                        run.approval_actor_id = None
                        run.approval_notes = "Awaiting operator review before any mutation-capable follow-up."
                        run.checkpoint["approval"] = {
                            "state": WorkflowApprovalState.pending.value,
                            "requested_at": run.approval_requested_at.isoformat(),
                            "notes": run.approval_notes,
                        }
                        logger.info(f"Workflow {run.id} paused for human approval")
                
                # Create next step record (idempotent)
                existing_next = db.query(WorkflowStepRecord).filter(
                    WorkflowStepRecord.workflow_id == run.id,
                    WorkflowStepRecord.step_name == next_step_name
                ).first()
                
                if not existing_next:
                    next_step = WorkflowStepRecord(
                        id=f"step_{uuid.uuid4().hex}",
                        workflow_id=run.id,
                        step_name=next_step_name,
                        status=WorkflowStatus.running.value if next_step_name != "human_approval" else WorkflowStatus.paused.value,
                        started_at=datetime.utcnow() if next_step_name != "human_approval" else None,
                        checkpoint=run.checkpoint.copy()
                    )
                    db.add(next_step)
            else:
                run.status = WorkflowStatus.complete.value
                run.approval_state = WorkflowApprovalState.not_required.value
                logger.info(f"Workflow {run.id} completed successfully")
                
            run.updated_at = datetime.utcnow()
            
        except Exception as e:
            logger.exception(f"Step {run.current_step} failed for run {run.id}")
            step.status = WorkflowStatus.failed.value
            step.error = str(e)
            run.status = WorkflowStatus.failed.value
            run.updated_at = datetime.utcnow()

    async def execute_step_logic(self, run: WorkflowRunRecord, step: WorkflowStepRecord, db: Session) -> dict[str, Any]:
        """Real read-only logic for each step of the codebase audit."""
        checkpoint = step.checkpoint.copy()
        step_name = step.step_name
        audit_scope = run.checkpoint.get("inputs", {}).get("audit_scope", "general")
        
        if step_name == "ingest_context":
            # Real file scan with size limits and improved exclusion
            files = []
            max_size = 1 * 1024 * 1024  # 1MB limit for analysis
            for root, _, filenames in os.walk(self.base_path):
                if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", ".venv", "artifacts", "dist", "audit.log"]):
                    continue
                for f in filenames:
                    path = Path(root) / f
                    try:
                        if path.stat().st_size < max_size:
                            files.append(str(path))
                    except Exception:
                        continue
            
            checkpoint["files_count"] = len(files)
            checkpoint["languages"] = list(set(f.split(".")[-1] for f in files if "." in f))
            checkpoint["repo_ref"] = run.checkpoint.get("inputs", {}).get("repo_ref", "main")
            
        elif step_name == "memory_recall":
            # Real recall from A-MEM
            notes = db.query(MemoryNoteRecord).filter(
                MemoryNoteRecord.project_id == run.project_id,
                MemoryNoteRecord.note_type == "technical"
            ).all()
            checkpoint["recalled_notes"] = [
                {"id": n.id, "content": n.content, "tags": n.tags} for n in notes
            ]
            
        elif step_name == "analyze_synthesize":
            # Advanced read-only analysis
            findings = []
            evidence = {}

            # 1. Infrastructure Analysis (Terraform, Cloud Build, Docker)
            infra_findings = self._analyze_infrastructure()
            findings.extend(infra_findings["findings"])
            evidence.update(infra_findings["evidence"])

            # 2. Branding drift (general)
            if audit_scope != "infra_only":
                robco_refs = self._find_pattern(r"robco", exclude_self=True)
                if robco_refs:
                    findings.append({"issue": "Branding drift: 'robco' references persist", "severity": "medium", "count": len(robco_refs), "tier": "safe_rename"})
                    evidence["robco_refs"] = robco_refs[:20]

            # 3. Security Check
            secret_patterns = [r"api[_-]key\s*=\s*['\"][\w-]{20,}['\"]", r"password\s*=\s*['\"][\w-]{8,}['\"]"]
            secrets = []
            for p in secret_patterns:
                secrets.extend(self._find_pattern(p))
            
            real_secrets = [s for s in secrets if not any(safe in s["file"] for safe in ["docker-compose", "test_", "settings.py", "alembic/env.py", "scripts/"])]
            if real_secrets:
                findings.append({"issue": "Potential hardcoded secrets found", "severity": "high", "count": len(real_secrets), "tier": "security_sensitive"})
                evidence["secrets"] = real_secrets[:10]

            # 4. Missing docstrings in services (non-infra audits)
            if audit_scope != "infra_only":
                missing_docs = self._find_missing_docstrings("services")
                if missing_docs:
                    findings.append({"issue": "Missing module docstrings in services", "severity": "low", "count": len(missing_docs), "tier": "deferred_debt"})
                    evidence["missing_docs"] = missing_docs[:10]

            checkpoint["findings"] = findings
            checkpoint["evidence"] = evidence
            
        elif step_name == "governance_check":
            # Automated policy check
            high_sev = [f for f in checkpoint.get("findings", []) if f["severity"] == "high"]
            checkpoint["governance_verdict"] = "fail" if high_sev else "pass"
            checkpoint["governance_reasoning"] = f"Found {len(high_sev)} high-severity issues." if high_sev else "No high-severity architectural violations found."
            
        elif step_name == "persist_artifact":
            # 1. Save CodebaseAuditRecord
            audit_id = f"audit_{uuid.uuid4().hex}"
            findings = checkpoint.get("findings", [])
            evidence = checkpoint.get("evidence", {})
            
            audit = CodebaseAuditRecord(
                id=audit_id,
                project_id=run.project_id,
                workflow_id=run.id,
                summary=f"Staged remediation audit of {checkpoint.get('files_count', 0)} files. Tiered findings: {len(findings)}",
                findings=findings,
                evidence=evidence,
                proposed_actions=[
                    {"action": "Review Tier 1 (Safe) renames for batch execution", "priority": "medium", "tier": 1},
                    {"action": "Plan Tier 2 (Security) remediation", "priority": "high", "tier": 2},
                    {"action": "Coordinate Tier 3 (Breaking) infra migration", "priority": "low", "tier": 3}
                ],
                created_at=datetime.utcnow()
            )
            db.add(audit)
            
            # 2. Generate Detailed Remediation Plan Artifact
            inventory = self._build_inventory(findings, evidence)
            risk_tiers = self._group_by_risk(inventory)
            dependencies = self._build_dependency_chain(inventory)
            
            plan_id = f"plan_{uuid.uuid4().hex}"
            plan = RemediationPlanRecord(
                id=plan_id,
                audit_id=audit_id,
                project_id=run.project_id,
                workflow_id=run.id,
                inventory=inventory,
                risk_tiers=risk_tiers,
                dependency_chain=dependencies,
                rollback_notes=(
                    "Tier 1: Revert via Git (Safe).\n"
                    "Tier 2: Rotate secrets and update documentation.\n"
                    "Tier 3: Use 'terraform state mv' for rename revert; coordinate with active Cloud Run revisions."
                ),
                created_at=datetime.utcnow()
            )
            db.add(plan)
            
            checkpoint["artifact_id"] = audit_id
            checkpoint["remediation_plan_id"] = plan_id
            checkpoint["remediation_map"] = risk_tiers # Backward compatibility for previous schema
            
        return checkpoint

    def _build_inventory(self, findings: list[dict], evidence: dict) -> list[dict]:
        """Flatten findings and evidence into a queryable inventory with owners."""
        inventory = []
        for finding in findings:
            issue_key = None
            if "Terraform" in finding["issue"]: issue_key = "terraform_refs"
            elif "Cloud Build" in finding["issue"]: issue_key = "cloudbuild_refs"
            elif "branding" in finding["issue"]: issue_key = "robco_refs"
            elif "secrets" in finding["issue"]: issue_key = "secrets"
            elif "docstrings" in finding["issue"]: issue_key = "missing_docs"
            
            if not issue_key or issue_key not in evidence:
                continue
                
            for item in evidence[issue_key]:
                path = item.get("file", "unknown")
                inventory.append({
                    "issue": finding["issue"],
                    "file": path,
                    "line": item.get("line"),
                    "snippet": item.get("snippet"),
                    "owner": self._infer_owner(path),
                    "tier": finding.get("tier", "untiered"),
                    "mechanism": self._infer_mechanism(path, finding.get("tier"))
                })
        return inventory

    def _infer_owner(self, path: str) -> str:
        if path.startswith("services/core"): return "Core Team"
        if path.startswith("services/gateway"): return "API Team"
        if path.startswith("infra"): return "Platform/SRE"
        if path.startswith("services/verticals"): return "Product Teams"
        return "General"

    def _infer_mechanism(self, path: str, tier: str) -> str:
        if tier == "safe_rename": return "direct edit"
        if path.endswith(".tf"): return "terraform state mv"
        if "cloudbuild" in path: return "coordinated deploy"
        if tier == "security_sensitive": return "recreate-and-migrate"
        return "manual review"

    def _group_by_risk(self, inventory: list[dict]) -> dict:
        return {
            "safe": [i for i in inventory if i["tier"] == "safe_rename"],
            "controlled": [i for i in inventory if i["tier"] == "deploy_breaking" and not i["file"].endswith(".tf")],
            "breaking": [i for i in inventory if i["tier"] == "deploy_breaking" and i["file"].endswith(".tf")]
        }

    def _build_dependency_chain(self, inventory: list[dict]) -> dict:
        return {
            "must_change_first": ["Documentation", "Metadata labels"],
            "must_not_change_yet": ["Cloud Run Service Names", "Cloud SQL Instance Names"],
            "blockers": [i["file"] for i in inventory if i["tier"] == "security_sensitive"]
        }

    def _analyze_infrastructure(self) -> dict[str, Any]:
        """Specialized sensing for Terraform, Cloud Build, Docker, and IAM."""
        findings = []
        evidence = {}

        # 1. Terraform (Deploy-Breaking / Breaking Renames)
        tf_refs = self._find_pattern(r'robco', include_extensions=(".tf", ".tfvars"))
        if tf_refs:
            findings.append({
                "issue": "Terraform contains 'robco' references (resource names, labels, or defaults)",
                "severity": "medium",
                "count": len(tf_refs),
                "tier": "deploy_breaking"
            })
            evidence["terraform_refs"] = tf_refs[:20]

        # 2. Cloud Build (Deploy-Breaking)
        cb_refs = self._find_pattern(r'robco', include_extensions=(".yaml", ".yml"))
        # Filter for cloudbuild files specifically
        cb_refs = [f for f in cb_refs if "cloudbuild" in f["file"]]
        if cb_refs:
            findings.append({
                "issue": "Cloud Build configuration contains 'robco' references",
                "severity": "medium",
                "count": len(cb_refs),
                "tier": "deploy_breaking"
            })
            evidence["cloudbuild_refs"] = cb_refs[:20]

        # 3. Dockerfile (Safe-ish Rename)
        docker_branding = self._find_pattern(r'robco', include_extensions=("Dockerfile",))
        if docker_branding:
            findings.append({
                "issue": "Dockerfile metadata/branding drift",
                "severity": "low",
                "count": len(docker_branding),
                "tier": "safe_rename"
            })
            evidence["docker_branding"] = docker_branding[:10]

        # 4. IAM / Security Sensitive
        iam_refs = self._find_pattern(r'(member|user|serviceAccount|role):.*robco', include_extensions=(".tf", ".yaml"))
        if iam_refs:
            findings.append({
                "issue": "IAM policy or roles referencing 'robco' identities",
                "severity": "high",
                "count": len(iam_refs),
                "tier": "security_sensitive"
            })
            evidence["iam_references"] = iam_refs[:10]

        return {"findings": findings, "evidence": evidence}

    def _find_pattern(self, pattern: str, exclude_self: bool = False, include_extensions: tuple[str, ...] = None, root_filter: str = None) -> list[dict[str, Any]]:
        results = []
        import re
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except Exception:
            return []
        
        target_extensions = include_extensions or (".py", ".ts", ".tsx", ".md", ".yaml", ".yml", ".tf", ".tfvars", "Dockerfile")
        
        for root, _, filenames in os.walk(self.base_path):
            if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", ".venv", "audit.log", "artifacts"]):
                continue
            if root_filter and root_filter not in root:
                continue
            for f in filenames:
                if f.endswith(target_extensions) or f == "Dockerfile":
                    path = Path(root) / f
                    if exclude_self and "services/orchestration/app/worker.py" in str(path):
                        continue
                    try:
                        content = path.read_text(errors="replace")
                        for i, line in enumerate(content.splitlines()):
                            if regex.search(line):
                                results.append({
                                    "file": str(path.relative_to(self.base_path)),
                                    "line": i + 1,
                                    "snippet": line.strip()[:100]
                                })
                    except Exception:
                        continue
        return results

    def _find_missing_docstrings(self, subdir: str) -> list[dict[str, Any]]:
        results = []
        target_dir = self.base_path / subdir
        if not target_dir.exists():
            return []
        for root, _, filenames in os.walk(target_dir):
            if "__pycache__" in root: continue
            for f in filenames:
                if f.endswith(".py") and f != "__init__.py":
                    path = Path(root) / f
                    try:
                        content = path.read_text(errors="replace").strip()
                        if not (content.startswith('"""') or content.startswith("'''")):
                            results.append({"file": str(path.relative_to(self.base_path))})
                    except Exception:
                        continue
        return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = CodebaseAuditWorker()
    asyncio.run(worker.run())
