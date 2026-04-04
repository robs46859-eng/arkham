"""
Usage/billing event contract schema.
Implements: System Contracts Document — Usage Contract
Emitted by gateway and workflows for every model invocation and billable operation.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UsageEvent(BaseModel):
    """Usage event emitted per model invocation or billable operation."""

    usage_id: str  # format: usage_<ulid>
    tenant_id: str  # format: tenant_<ulid>
    service: str
    cost: float
    timestamp: datetime
