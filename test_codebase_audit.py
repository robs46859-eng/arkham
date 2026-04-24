"""
Test script for Codebase Audit durable workflow.
1. Seeds a test tenant, project, and memory note.
2. Starts a codebase_audit workflow.
3. Runs the worker for a few cycles to see it hit 'pending' approval.
"""

import asyncio
import logging
from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session
from packages.db import transactional_session
from packages.models.tenant import Tenant
from packages.models.project import Project
from packages.models.workflow import WorkflowRunRecord, WorkflowStepRecord
from packages.models.domain import CodebaseAuditRecord, RemediationPlanRecord
from packages.models.memory import MemoryNoteRecord
from packages.schemas import WorkflowStatus, WorkflowApprovalState

from services.orchestration.app.worker import CodebaseAuditWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_data():
    """Seed a test tenant, project, and memory note."""
    tenant_id = "tenant_test_01"
    project_id = "proj_test_01"
    
    with transactional_session() as db:
        # Check if tenant exists
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            logger.info(f"Seeding tenant {tenant_id}")
            tenant = Tenant(
                id=tenant_id,
                name="Test Architecture Corp",
                created_at=datetime.now(timezone.utc)
            )
            db.add(tenant)
            db.flush()  # Ensure tenant is in DB before project refers to it
        
        # Check if project exists
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.info(f"Seeding project {project_id}")
            project = Project(
                id=project_id,
                tenant_id=tenant_id,
                name="Arkham Core Audit",
                created_at=datetime.now(timezone.utc)
            )
            db.add(project)
            db.flush()

        # Add technical memory note
        note_id = "mem_tech_01"
        note = db.query(MemoryNoteRecord).filter(MemoryNoteRecord.id == note_id).first()
        if not note:
            logger.info(f"Seeding technical memory note {note_id}")
            note = MemoryNoteRecord(
                id=note_id,
                tenant_id=tenant_id,
                project_id=project_id,
                note_type="technical",
                content="Architecture Rule: All new services must use Arkham prefixes, not Robco.",
                tags=["architecture", "branding"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(note)
        
        db.commit()
    return tenant_id, project_id

async def start_workflow(tenant_id, project_id):
    """Start a codebase_audit workflow."""
    workflow_id = f"wf_{uuid.uuid4().hex}"
    logger.info(f"Starting workflow {workflow_id}")
    
    with transactional_session() as db:
        run = WorkflowRunRecord(
            id=workflow_id,
            tenant_id=tenant_id,
            project_id=project_id,
            type="codebase_audit",
            status=WorkflowStatus.running.value,
            approval_state=WorkflowApprovalState.not_required.value,
            current_step="ingest_context",
            checkpoint={"inputs": {"repo_ref": "main"}},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(run)
        
        step = WorkflowStepRecord(
            id=f"step_{uuid.uuid4().hex}",
            workflow_id=workflow_id,
            step_name="ingest_context",
            status=WorkflowStatus.running.value,
            started_at=datetime.now(timezone.utc),
            checkpoint={}
        )
        db.add(step)
        db.commit()
    return workflow_id

async def monitor_workflow(workflow_id):
    """Monitor workflow progress and resolve approval."""
    worker = CodebaseAuditWorker(poll_interval=1)
    
    logger.info("Running worker to reach PENDING state...")
    for i in range(10):
        await worker.process_pending_runs()
        
        with transactional_session() as db:
            run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
            logger.info(f"Cycle {i}: Workflow {run.id} Status={run.status} Approval={run.approval_state} Step={run.current_step}")
            
            if run.status == WorkflowStatus.paused.value and run.approval_state == WorkflowApprovalState.pending.value:
                logger.info("Workflow reached PENDING approval state successfully.")
                break
        await asyncio.sleep(0.1)

    # Simulate Approval
    logger.info(f"Resolving approval for {workflow_id}...")
    with transactional_session() as db:
        run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
        run.approval_state = WorkflowApprovalState.approved.value
        run.status = WorkflowStatus.running.value
        run.approval_resolved_at = datetime.now(timezone.utc)
        run.approval_actor_id = "test_operator_01"
        
        step = db.query(WorkflowStepRecord).filter(
            WorkflowStepRecord.workflow_id == workflow_id,
            WorkflowStepRecord.step_name == "human_approval",
            WorkflowStepRecord.status == WorkflowStatus.paused.value
        ).first()
        if step:
            step.status = WorkflowStatus.running.value
        db.commit()

    logger.info("Running worker to complete workflow...")
    for i in range(5):
        await worker.process_pending_runs()
        
        with transactional_session() as db:
            run = db.query(WorkflowRunRecord).filter(WorkflowRunRecord.id == workflow_id).first()
            logger.info(f"Resume Cycle {i}: Workflow {run.id} Status={run.status} Approval={run.approval_state} Step={run.current_step}")
            
            if run.status == WorkflowStatus.complete.value:
                logger.info("Workflow COMPLETED successfully after approval.")
                # Verify Audit Artifact
                audit = db.query(CodebaseAuditRecord).filter(CodebaseAuditRecord.workflow_id == workflow_id).first()
                if audit:
                    logger.info(f"Verified CodebaseAuditRecord: {audit.summary}")
                    logger.info(f"Findings count: {len(audit.findings)}")
                break
        await asyncio.sleep(0.1)

async def main():
    tenant_id, project_id = await seed_data()
    workflow_id = await start_workflow(tenant_id, project_id)
    await monitor_workflow(workflow_id)

if __name__ == "__main__":
    asyncio.run(main())
