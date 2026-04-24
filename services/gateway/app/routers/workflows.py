"""
Workflow entry endpoints on the gateway.
Implements: Service Spec §1.5 — POST /v1/workflows/start, GET /v1/workflows/{workflow_id}.
The gateway initiates workflows and proxies status — orchestration service owns execution.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.schemas import WorkflowRun
from ..middleware.auth import require_tenant
from ..settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/workflows", tags=["workflows"])


class WorkflowStartRequest(BaseModel):
    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    workflow_type: str  # e.g. "project_intake", "codebase_audit"
    inputs: dict[str, Any] = {}


class ApprovalRequest(BaseModel):
    actor_id: str
    notes: str | None = None


@router.post("/start", response_model=WorkflowRun)
async def start_workflow(
    request: WorkflowStartRequest,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> WorkflowRun:
    """Initiate a workflow via the orchestration service."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.orchestration_url}/v1/workflows/start",
                json=request.model_dump(),
                timeout=10.0,
            )
            response.raise_for_status()
            return WorkflowRun(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail"))
        except Exception as e:
            logger.exception("Failed to start workflow")
            raise HTTPException(status_code=500, detail=f"Orchestration service error: {e}")


@router.get("/{workflow_id}", response_model=WorkflowRun)
async def get_workflow(
    workflow_id: str,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> WorkflowRun:
    """Look up workflow status from the orchestration service."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.orchestration_url}/v1/workflows/{workflow_id}",
                timeout=5.0,
            )
            response.raise_for_status()
            return WorkflowRun(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail"))
        except Exception as e:
            logger.exception(f"Failed to fetch workflow {workflow_id}")
            raise HTTPException(status_code=500, detail=f"Orchestration service error: {e}")


@router.get("/{workflow_id}/artifacts", response_model=list[dict[str, Any]])
async def get_workflow_artifacts(
    workflow_id: str,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> list[dict[str, Any]]:
    """Retrieve artifacts produced by this workflow."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.orchestration_url}/v1/workflows/{workflow_id}/artifacts",
                timeout=5.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail"))
        except Exception as e:
            logger.exception(f"Failed to fetch artifacts for {workflow_id}")
            raise HTTPException(status_code=500, detail=f"Orchestration service error: {e}")


@router.post("/{workflow_id}/approve", response_model=WorkflowRun)
async def approve_workflow(
    workflow_id: str,
    request: ApprovalRequest,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> WorkflowRun:
    """Approve a paused workflow via the orchestration service."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.orchestration_url}/v1/workflows/{workflow_id}/approve",
                json=request.model_dump(),
                timeout=10.0,
            )
            response.raise_for_status()
            return WorkflowRun(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail"))
        except Exception as e:
            logger.exception(f"Failed to approve workflow {workflow_id}")
            raise HTTPException(status_code=500, detail=f"Orchestration service error: {e}")


@router.post("/{workflow_id}/reject", response_model=WorkflowRun)
async def reject_workflow(
    workflow_id: str,
    request: ApprovalRequest,
    _auth: tuple[str, str] = Depends(require_tenant),
) -> WorkflowRun:
    """Reject a paused workflow via the orchestration service."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.orchestration_url}/v1/workflows/{workflow_id}/reject",
                json=request.model_dump(),
                timeout=10.0,
            )
            response.raise_for_status()
            return WorkflowRun(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.json().get("detail"))
        except Exception as e:
            logger.exception(f"Failed to reject workflow {workflow_id}")
            raise HTTPException(status_code=500, detail=f"Orchestration service error: {e}")
