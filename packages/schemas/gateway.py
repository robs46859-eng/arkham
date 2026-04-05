"""
Gateway contract schemas.
Implements: System Contracts Document — Gateway Contract
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Summarize the BIM coordination notes and highlight blocking issues.",
                "context": {
                    "project_name": "Denver Tower",
                    "privacy_tier": "enterprise",
                },
                "references": ["gs://robco-staging-bucket/coordination/week-14.pdf"],
            }
        }
    )


class InferenceOptions(BaseModel):
    allow_premium: bool = False
    require_schema: bool = True

    model_config = ConfigDict(
        json_schema_extra={"example": {"allow_premium": True, "require_schema": True}}
    )


class ValidationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)

    model_config = ConfigDict(json_schema_extra={"example": {"passed": True, "errors": []}})


class InferenceRequest(BaseModel):
    """Normalized inference request. All gateway calls must use this shape."""

    tenant_id: str  # format: tenant_<ulid>
    project_id: str  # format: proj_<ulid>
    task_type: TaskType
    input: InferenceInput = Field(default_factory=InferenceInput)
    options: InferenceOptions = Field(default_factory=InferenceOptions)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tenant_id": "tenant_01hv6n6j6h8x7m4r9k2p1q3s4t",
                "project_id": "proj_01hv6n8h0q9x2r4s6t8u1v3w5y",
                "task_type": "summary",
                "input": {
                    "text": "Summarize the BIM coordination notes and highlight blocking issues.",
                    "context": {
                        "project_name": "Denver Tower",
                        "privacy_tier": "enterprise",
                    },
                    "references": ["gs://robco-staging-bucket/coordination/week-14.pdf"],
                },
                "options": {"allow_premium": True, "require_schema": True},
            }
        }
    )


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req_01hv6nm2q6q9k7n8p1r2s3t4u5",
                "tenant_id": "tenant_01hv6n6j6h8x7m4r9k2p1q3s4t",
                "model_used": "mid",
                "cache_hit": False,
                "latency_ms": 842,
                "cost_estimate": 0.014,
                "output": {
                    "result": "Two blocking issues were identified: unresolved duct clashes and a missing fireproofing submittal.",
                    "model_tier": "mid",
                },
                "validation": {"passed": True, "errors": []},
            }
        }
    )
