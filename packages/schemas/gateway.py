"""
Gateway contract schemas.
Implements: System Contracts Document — Gateway Contract
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    classification = "classification"
    extraction = "extraction"
    summary = "summary"
    workflow = "workflow"


class ModelTier(str, Enum):
    local = "local"
    mid = "mid"
    premium = "premium"


class InferenceInput(BaseModel):
    text: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    references: list[str] = Field(default_factory=list)


class InferenceOptions(BaseModel):
    allow_premium: bool = False
    require_schema: bool = True


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)


class InferenceRequest(BaseModel):
    """Normalized inference request. All gateway calls must use this shape."""

    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    task_type: TaskType
    input: InferenceInput = Field(default_factory=InferenceInput)
    options: InferenceOptions = Field(default_factory=InferenceOptions)


class InferenceResponse(BaseModel):
    """Normalized inference response returned by the gateway."""

    request_id: str  # format: req_<ulid>
    tenant_id: str
    model_used: ModelTier
    cache_hit: bool
    latency_ms: int
    cost_estimate: float
    output: dict[str, Any] = Field(default_factory=dict)
    validation: ValidationResult = Field(default_factory=ValidationResult)
