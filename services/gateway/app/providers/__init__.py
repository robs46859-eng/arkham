"""
Provider registry package.
Implements: Service Spec §1.6 — provider registry module.
All model provider access must go through this registry. Never call providers directly.
"""

from .registry import ProviderRegistry, registry

__all__ = ["ProviderRegistry", "registry"]
