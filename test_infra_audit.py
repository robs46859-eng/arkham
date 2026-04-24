"""
Test script for Infra-focused Codebase Audit.
Triggers an audit with 'infra_only' scope and verifies the remediation map and plan artifact.
"""

import asyncio
import logging
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from packages.db import transactional_session
from packages.models.tenant import Tenant
from packages.models.project import Project
from packages.models.workflow import WorkflowRunRecord, WorkflowStepRecord
from packages.models.domain import CodebaseAuditRecord, RemediationPlanRecord
from packages.schemas import WorkflowStatus, WorkflowApprovalState

from services.orchestration.app.worker import CodebaseAuditWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    tenant_id = "tenant_test_01"
    project_id = "proj_test_01"
    workflow_id = f"wf_infra_{uuid.uuid4().hex}"
    
    logger.info(f"Starting Infra-focused workflow {workflow_id}")
    
    with transactional_session() as db:
        run = WorkflowRunRecord(
            id=workflow_id,
            tenant_id=tenant_id,
            project_id=project_id,
            type="codebase_audit",
            status=WorkflowStatus.running.value,
            approval_state=WorkflowApprovalState.not_required.value,
            current_step="ingest_context",
            checkpoint={"inputs": {"repo_ref": "main", "audit_scope": "infra_only"}},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(run)
        
        step = WorkflowStepRecord(
            id=f"step_{uuid.uuid4().hex}",
            workflow_id=workflow_id,
            step_name="ingest_context",
            status=WorkflowStatus.running.value,
            started_at=datetime.utcnow(),
            checkpoint={}
        )
        db.add(step)
        db.commit()

    worker = CodebaseAuditWorker(poll_interval=1)
    
    logger.info("Running worker until human_approval...")
    for i in range(20):
        await worker.process_pending_runs()
        
        with transactional_session() as db:
            run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
            logger.info(f"Cycle {i}: Step={run.current_step} Status={run.status} Approval={run.approval_state}")
            
            if run.status == WorkflowStatus.paused.value:
                logger.info("Workflow reached PENDING approval state.")
                
                # Verify Audit Record
                audit = db.query(CodebaseAuditRecord).filter(CodebaseAuditRecord.workflow_id == workflow_id).first()
                if audit:
                    logger.info(f"✅ Verified CodebaseAuditRecord: {audit.summary}")
                    
                # Verify Remediation Plan Artifact
                plan = db.query(RemediationPlanRecord).filter(RemediationPlanRecord.workflow_id == workflow_id).first()
                if plan:
                    logger.info(f"✅ Verified RemediationPlanRecord: {plan.id}")
                    logger.info(f"  Inventory size: {len(plan.inventory)}")
                    logger.info(f"  Safe items: {len(plan.risk_tiers.get('safe', []))}")
                    logger.info(f"  Controlled items: {len(plan.risk_tiers.get('controlled', []))}")
                    logger.info(f"  Breaking items: {len(plan.risk_tiers.get('breaking', []))}")
                    if plan.inventory:
                        sample = plan.inventory[0]
                        logger.info(f"  Sample Item: {sample['file']} (Owner: {sample['owner']}, Mechanism: {sample['mechanism']})")
                break
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
