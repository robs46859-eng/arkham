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


from enum import Enum
from typing import Any, Protocol, runtime_checkable

import httpx

from ..settings import settings


class ModelTier(str, Enum):
    local = "local"
    mid = "mid"
    premium = "premium"


@runtime_checkable
class Provider(Protocol):
    async def infer(
        self,
        task_type: str,
        input_text: str,
        context: dict[str, Any],
        model_name: str | None = None,
    ) -> dict[str, Any]:
        ...


class OllamaProvider:
    def __init__(self, host: str):
        self.host = host

    async def infer(
        self,
        task_type: str,
        input_text: str,
        context: dict[str, Any],
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if not model_name:
            # Simple mapping for local models
            if task_type == "classification":
                model_name = settings.local_classifier_model
            elif task_type == "summary":
                model_name = settings.local_summary_model
            elif task_type == "extraction":
                model_name = settings.local_extraction_model
            else:
                model_name = settings.local_router_model

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": input_text,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "model_tier": "local",
                    "model_name": model_name,
                    "result": data.get("response", ""),
                    "cost_estimate": 0.0,
                }
        except Exception as exc:
            return {
                "model_tier": "local",
                "model_name": model_name,
                "result": f"Error calling Ollama: {exc}",
                "cost_estimate": 0.0,
            }


class OpenAIProvider:
    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"

    async def infer(
        self,
        task_type: str,
        input_text: str,
        context: dict[str, Any],
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if not model_name:
            model_name = settings.openai_mid_tier_model

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": input_text}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                # Rough cost estimate for gpt-4o-mini (approximate)
                tokens = data.get("usage", {}).get("total_tokens", 0)
                cost = (tokens / 1000000.0) * 0.15 # $0.15 per 1M tokens approx
                return {
                    "model_tier": "mid" if model_name == settings.openai_mid_tier_model else "premium",
                    "model_name": model_name,
                    "result": content,
                    "cost_estimate": cost,
                }
        except Exception as exc:
            return {
                "model_tier": "mid",
                "model_name": model_name,
                "result": f"Error calling OpenAI: {exc}",
                "cost_estimate": 0.0,
            }


class GeminiProvider:
    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url or "https://generativelanguage.googleapis.com/v1beta/models"

    async def infer(
        self,
        task_type: str,
        input_text: str,
        context: dict[str, Any],
        model_name: str | None = None,
    ) -> dict[str, Any]:
        if not model_name:
            model_name = settings.gemini_mid_tier_model

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/{model_name}:generateContent?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": input_text}]}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                # Gemini 1.5 Flash is very cheap, Pro is mid-cost. 
                # Roughly estimating cost based on characters (Gemini is often priced per 1M characters/tokens)
                cost = 0.0001 # Placeholder
                return {
                    "model_tier": "mid" if model_name == settings.gemini_mid_tier_model else "premium",
                    "model_name": model_name,
                    "result": content,
                    "cost_estimate": cost,
                }
        except Exception as exc:
            return {
                "model_tier": "mid",
                "model_name": model_name,
                "result": f"Error calling Gemini: {exc}",
                "cost_estimate": 0.0,
            }


class ProviderRegistry:
    """
    Central registry for all model providers.
    Routes to the lowest-cost tier that satisfies the request policy.
    """

    def __init__(self):
        self.local = OllamaProvider(host=settings.ollama_host)
        self.mid: Provider | None = None
        self.premium: Provider | None = None

        if settings.openai_api_key:
            self.mid = OpenAIProvider(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
            self.premium = OpenAIProvider(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        elif settings.gemini_api_key:
            self.mid = GeminiProvider(api_key=settings.gemini_api_key, base_url=settings.gemini_base_url)
            self.premium = GeminiProvider(api_key=settings.gemini_api_key, base_url=settings.gemini_base_url)

    def select_tier(self, allow_premium: bool = False) -> ModelTier:
        """
        Select the cheapest valid execution tier.
        """
        if allow_premium and self.premium and settings.enable_premium_escalation:
            return ModelTier.premium
        
        # If we have a mid tier and premium not allowed or not enabled
        if self.mid:
            # Some tasks might prefer mid tier over local even if local exists
            # For now, default to local if available, as it's cheapest.
            return ModelTier.local
        
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
        """
        if tier == ModelTier.premium and self.premium:
            model_name = settings.openai_premium_model if settings.openai_api_key else settings.gemini_premium_model
            return await self.premium.infer(task_type, input_text, context, model_name=model_name)
        
        if tier == ModelTier.mid and self.mid:
            model_name = settings.openai_mid_tier_model if settings.openai_api_key else settings.gemini_mid_tier_model
            return await self.mid.infer(task_type, input_text, context, model_name=model_name)
        
        # Default fallback to local
        return await self.local.infer(task_type, input_text, context)


registry = ProviderRegistry()
