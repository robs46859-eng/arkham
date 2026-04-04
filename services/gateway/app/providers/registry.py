"""
Provider registry — contract-aligned stub.
Implements: Master Architecture §4.2 — provider abstraction registry.
Model ladder (Build Rules §6): deterministic → local → mid → premium.
STUB: provider implementations (local runtime, OpenAI, Anthropic, Gemini adapters)
are the next step after this skeleton is verified.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ModelTier(str, Enum):
    local = "local"
    mid = "mid"
    premium = "premium"


class ProviderRegistry:
    """
    Central registry for all model providers.
    Routes to the lowest-cost tier that satisfies the request policy.
    """

    def select_tier(self, allow_premium: bool = False) -> ModelTier:
        """
        Select the cheapest valid execution tier.
        STUB: real routing policy checks local model availability, confidence
        thresholds, task type suitability, and plan-level constraints.
        """
        # Default: local (lowest cost). Escalation only if policy permits.
        return ModelTier.local

    async def infer(
        self,
        tier: ModelTier,
        task_type: str,
        input_text: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Route an inference request to the appropriate model provider.
        STUB: returns placeholder until local model runtime is wired.
        Records: model_tier, model_name, latency, cost_estimate per observability rules.
        """
        # STUB — replace with real provider dispatch
        return {
            "model_tier": tier.value,
            "model_name": "stub",
            "result": f"[STUB] {task_type} inference not yet implemented",
            "cost_estimate": 0.0,
        }


registry = ProviderRegistry()
