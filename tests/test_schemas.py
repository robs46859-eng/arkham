"""
Schema contract tests.
Implements: Build Rules §8 — schema change → contract tests.
Verifies: all system contract schemas instantiate correctly with required fields.
"""

from datetime import datetime

from packages.schemas import (
    HealthResponse,
    InferenceRequest,
    InferenceResponse,
    IngestionRequest,
    IngestionResponse,
    BuildingElement,
    DocumentChunk,
    Issue,
    WorkflowRun,
    WorkflowStatus,
    Deliverable,
    MemoryNote,
    UsageEvent,
)
from packages.schemas.gateway import TaskType, ModelTier, ValidationResult
from packages.schemas.ingestion import FileType, JobStatus
from packages.schemas.domain import IssueSeverity


def test_health_response_contract():
    r = HealthResponse(status="ok", service="gateway", environment="test")
    assert r.status == "ok"
    assert r.service == "gateway"


def test_inference_request_contract():
    req = InferenceRequest(
        tenant_id="tenant_abc123",
        project_id="proj_abc123",
        task_type=TaskType.classification,
    )
    assert req.tenant_id == "tenant_abc123"
    assert req.options.allow_premium is False  # default: cheapest tier


def test_inference_response_contract():
    resp = InferenceResponse(
        request_id="req_abc123",
        tenant_id="tenant_abc123",
        model_used=ModelTier.local,
        cache_hit=False,
        latency_ms=42,
        cost_estimate=0.0,
        output={},
        validation=ValidationResult(passed=True),
    )
    assert resp.model_used == ModelTier.local
    assert resp.validation.passed is True


def test_ingestion_request_contract():
    req = IngestionRequest(
        tenant_id="tenant_abc123",
        project_id="proj_abc123",
        file_id="file_abc123",
        file_type=FileType.ifc,
        storage_path="s3://bim-files/proj_abc123/model.ifc",
    )
    assert req.file_type == FileType.ifc


def test_ingestion_response_contract():
    resp = IngestionResponse(
        job_id="job_abc123",
        status=JobStatus.queued,
    )
    assert resp.status == JobStatus.queued
    assert resp.entities_created == 0
    assert resp.errors == []


def test_building_element_contract():
    elem = BuildingElement(
        element_id="elem_abc123",
        project_id="proj_abc123",
        category="Wall",
        source_file_id="file_abc123",
        created_at=datetime.utcnow(),
    )
    assert elem.category == "Wall"
    assert elem.properties == {}


def test_document_chunk_contract():
    chunk = DocumentChunk(
        chunk_id="chunk_abc123",
        file_id="file_abc123",
        page=1,
        text="The building has 5 stories.",
        confidence=0.95,
    )
    assert chunk.confidence == 0.95


def test_issue_contract():
    issue = Issue(
        issue_id="issue_abc123",
        project_id="proj_abc123",
        type="clash",
        severity=IssueSeverity.high,
        confidence=0.87,
    )
    assert issue.severity == IssueSeverity.high
    assert issue.source_refs == []


def test_workflow_run_contract():
    now = datetime.utcnow()
    run = WorkflowRun(
        workflow_id="wf_abc123",
        type="project_intake",
        tenant_id="tenant_abc123",
        project_id="proj_abc123",
        status=WorkflowStatus.running,
        current_step="file_registration",
        created_at=now,
        updated_at=now,
    )
    assert run.status == WorkflowStatus.running
    assert run.checkpoint == {}


def test_deliverable_contract():
    d = Deliverable(
        deliverable_id="deliv_abc123",
        project_id="proj_abc123",
        type="project_intake_summary",
        artifact_path="s3://artifacts/proj_abc123/v1/summary.pdf",
        source_trace=["file_abc123"],
        created_at=datetime.utcnow(),
    )
    assert len(d.source_trace) == 1


def test_memory_note_contract():
    note = MemoryNote(
        note_id="mem_abc123",
        tenant_id="tenant_abc123",
        project_id="proj_abc123",
        content="Project has 3 unresolved structural clashes.",
        tags=["structural", "clash"],
    )
    assert note.tags == ["structural", "clash"]


def test_usage_event_contract():
    event = UsageEvent(
        usage_id="usage_abc123",
        tenant_id="tenant_abc123",
        service="gateway",
        cost=0.002,
        timestamp=datetime.utcnow(),
    )
    assert event.cost == 0.002
