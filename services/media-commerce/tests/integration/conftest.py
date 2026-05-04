"""
Integration Test Fixtures

Shared fixtures for integration tests across media-commerce and orchestration.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator
from uuid import uuid4

import pytest

# Add service roots to path
ORCHESTRATION_ROOT = Path(__file__).resolve().parents[3] / "orchestration"
MEDIA_COMMERCE_ROOT = Path(__file__).resolve().parents[3] / "media-commerce"

if str(ORCHESTRATION_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATION_ROOT))
if str(MEDIA_COMMERCE_ROOT) not in sys.path:
    sys.path.insert(0, str(MEDIA_COMMERCE_ROOT))


@pytest.fixture
def test_tenant_id() -> str:
    """Generate unique tenant ID for test isolation"""
    return f"test-tenant-{uuid4()}"


@pytest.fixture
def test_lead_id() -> str:
    """Generate unique lead ID for test isolation"""
    return f"test-lead-{uuid4()}"


@pytest.fixture
def test_content_id() -> str:
    """Generate unique content ID for test isolation"""
    return f"test-content-{uuid4()}"


@pytest.fixture
def test_page_id() -> str:
    """Generate unique page ID for test isolation"""
    return f"test-page-{uuid4()}"


@pytest.fixture
def staffing_lead_signals() -> list[str]:
    """Staffing vertical intent signals"""
    return [
        "Need nurse staffing support",
        "Fill shifts urgently",
        "Credentialing backlog",
    ]


@pytest.fixture
def ecom_lead_signals() -> list[str]:
    """E-commerce vertical intent signals"""
    return [
        "Shopify checkout optimization",
        "Abandoned cart recovery",
        "Product feed cleanup",
    ]


@pytest.fixture
def media_lead_signals() -> list[str]:
    """Media vertical intent signals"""
    return [
        "Affiliate program setup",
        "EPC tracking needed",
        "Content monetization",
    ]


@pytest.fixture
def content_strategy_input() -> Dict[str, Any]:
    """Content strategy workflow input"""
    return {
        "topic": "affiliate marketing optimization",
        "vertical": "media",
        "goals": ["revenue", "awareness"],
    }


@pytest.fixture
def page_cro_input(test_page_id: str) -> Dict[str, Any]:
    """Page CRO workflow input"""
    return {
        "page_id": test_page_id,
        "page_type": "landing_page",
    }


@pytest.fixture
def epc_monitoring_input() -> Dict[str, Any]:
    """EPC monitoring workflow input"""
    return {
        "vertical": "media",
    }


class WorkflowState:
    """Track workflow state across integration test steps"""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.workflow_ids: list[str] = []
        self.lead_id: str | None = None
        self.content_id: str | None = None
        self.page_id: str | None = None
        self.routing_result: Dict[str, Any] | None = None
        self.epc_result: Dict[str, Any] | None = None
        self.optimization_actions: list[Dict[str, Any]] = []

    def add_workflow(self, workflow_id: str):
        self.workflow_ids.append(workflow_id)

    def set_routed_vertical(self, vertical: str):
        self.routed_vertical = vertical


@pytest.fixture
def workflow_state(test_tenant_id: str) -> WorkflowState:
    """Track workflow state across test steps"""
    return WorkflowState(test_tenant_id)


# Mock checkpoint store for integration tests
class MockCheckpointStore:
    """In-memory checkpoint store for integration tests"""

    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._saved_count = 0

    async def save_workflow(self, workflow: Dict[str, Any]):
        workflow_id = workflow.get("workflow_id")
        if workflow_id:
            self._workflows[workflow_id] = workflow.copy()
            self._saved_count += 1

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any] | None:
        return self._workflows.get(workflow_id)

    @property
    def saved_count(self) -> int:
        return self._saved_count

    def clear(self):
        self._workflows.clear()
        self._saved_count = 0


# Mock task queue for integration tests
class MockTaskQueue:
    """In-memory task queue for integration tests"""

    def __init__(self):
        self._tasks: list[Dict[str, Any]] = []
        self._enqueued_count = 0

    async def enqueue(self, **kwargs) -> str:
        task_id = f"task-{uuid4()}"
        task = {
            "task_id": task_id,
            "workflow_id": kwargs.get("workflow_id"),
            "task_type": kwargs.get("task_type"),
            "step_name": kwargs.get("step_name"),
            "step_data": kwargs.get("step_data", {}),
            "status": "pending",
        }
        self._tasks.append(task)
        self._enqueued_count += 1
        return task_id

    async def dequeue(self) -> Dict[str, Any] | None:
        for task in self._tasks:
            if task["status"] == "pending":
                task["status"] = "processing"
                return task
        return None

    async def complete_task(self, task_id: str, output: Dict[str, Any]):
        for task in self._tasks:
            if task["task_id"] == task_id:
                task["status"] = "completed"
                task["output"] = output
                break

    @property
    def pending_count(self) -> int:
        return sum(1 for t in self._tasks if t["status"] == "pending")

    @property
    def completed_count(self) -> int:
        return sum(1 for t in self._tasks if t["status"] == "completed")

    @property
    def enqueued_count(self) -> int:
        return self._enqueued_count

    def clear(self):
        self._tasks.clear()
        self._enqueued_count = 0

    def get_tasks_by_workflow(self, workflow_id: str) -> list[Dict[str, Any]]:
        return [t for t in self._tasks if t["workflow_id"] == workflow_id]


@pytest.fixture
def mock_checkpoint_store() -> MockCheckpointStore:
    """Provide mock checkpoint store for integration tests"""
    return MockCheckpointStore()


@pytest.fixture
def mock_task_queue() -> MockTaskQueue:
    """Provide mock task queue for integration tests"""
    return MockTaskQueue()


@pytest.fixture
def integration_context(
    mock_checkpoint_store: MockCheckpointStore,
    mock_task_queue: MockTaskQueue,
) -> Dict[str, Any]:
    """Provide integration test context with all mocks"""
    return {
        "checkpoint_store": mock_checkpoint_store,
        "task_queue": mock_task_queue,
    }
